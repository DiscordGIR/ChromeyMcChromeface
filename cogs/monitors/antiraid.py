import string
from asyncio import Lock
from datetime import datetime, timedelta, timezone

import cogs.utils.context as context
import cogs.utils.logs as logger
from cogs.utils.message_cooldown import MessageTextBucket
import discord
from data.case import Case
from discord.ext import commands
from expiringdict import ExpiringDict
from fold_to_ascii import fold


class RaidType:
    PingSpam = 1
    RaidPhrase = 2
    MessageSpam = 3
    JoinSpamOverTime = 4


class AntiRaidMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # cooldown to monitor if too many users join in a short period of time (more than 10 within 8 seconds)
        self.join_raid_detection_threshold = commands.CooldownMapping.from_cooldown(rate=10, per=8, type=commands.BucketType.guild)
        # cooldown to monitor if users are spamming a message (8 within 5 seconds)
        self.message_spam_detection_threshold = commands.CooldownMapping.from_cooldown(rate=7, per=10.0, type=commands.BucketType.member)
        # cooldown to monitor if too many accounts created on the same date are joining within a short period of time 
        # (5 accounts created on the same date joining within 45 minutes of each other)
        self.join_overtime_raid_detection_threshold = commands.CooldownMapping.from_cooldown(rate=4, per=2700, type=MessageTextBucket.custom)

        # cooldown to monitor how many times AntiRaid has been triggered (5 triggers per 15 seconds puts server in lockdown)
        self.raid_detection_threshold = commands.CooldownMapping.from_cooldown(rate=4, per=15.0, type=commands.BucketType.guild)
        # cooldown to only send one raid alert for moderators per 10 minutes
        self.raid_alert_cooldown = commands.CooldownMapping.from_cooldown(1, 600.0, commands.BucketType.guild)

        # stores the users that trigger self.join_raid_detection_threshold so we can ban them
        self.join_user_mapping = ExpiringDict(max_len=100, max_age_seconds=10)
        # stores the users that trigger self.message_spam_detection_threshold so we can ban them
        self.spam_user_mapping = ExpiringDict(max_len=100, max_age_seconds=10)
        # stores the users that trigger self.join_overtime_raid_detection_threshold so we can ban them
        self.join_overtime_mapping = ExpiringDict(max_len=100, max_age_seconds=2700)
        # stores the users that we have banned so we don't try to ban them repeatedly
        self.ban_user_mapping = ExpiringDict(max_len=100, max_age_seconds=120)
        
        # locks to prevent race conditions when banning concurrently
        self.join_overtime_lock = Lock()
        self.banning_lock = Lock()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Antiraid filter for when members join.
        This watches for when too many members join within a small period of time,
        as well as when too many users created on the same day join within a small period of time

        Parameters
        ----------
        member : discord.Member
            the member that joined
        """

        if member.guild.id != self.bot.settings.guild_id:
            return
        if member.bot:
            return
        
        
        """Detect whether more than 10 users join within 8 seconds"""
        # add user to cooldown
        current = datetime.now().timestamp()
        join_spam_detection_bucket = self.join_raid_detection_threshold.get_bucket(member)
        self.join_user_mapping[member.id] = member
        
        # if ratelimit is triggered, we should ban all the users that joined in the past 8 seconds
        if join_spam_detection_bucket.update_rate_limit(current):
            users = list(self.join_user_mapping.keys())
            for user in users:
                try:
                    user = self.join_user_mapping[user]
                except KeyError:
                    continue
                
                try:
                    await self.raid_ban(user, reason="Join spam detected.")
                except Exception:
                    pass
                
            raid_alert_bucket = self.raid_alert_cooldown.get_bucket(member)
            if not raid_alert_bucket.update_rate_limit(current):
                await self.bot.report.report_raid(member)
                await self.freeze_server(member.guild)
        
        """Detect whether more than 4 users created on the same day
        (after May 1st 2021) join within 45 minutes of each other"""
        
        # skip if the user was created within the last 15 minutes
        if member.created_at > datetime.now() - timedelta(minutes=15):
            return

        # skip user if we manually verified them, i.e they were approved by a moderator
        # using the !verify command when they appealed a ban.
        if (await self.bot.settings.user(member.id)).raid_verified:
            return

        # skip if it's an older account (before May 1st 2021)
        if member.created_at < datetime.strptime("01/05/21 00:00:00", '%d/%m/%y %H:%M:%S'):
            return 
        
        # this setting disables the filter for accounts created from "Today"
        # useful when we get alot of new users, for example when a new Jailbreak is released.
        # this setting is controlled using !spammode
        if not self.bot.settings.guild().ban_today_spam_accounts:
            now = datetime.today()
            now = [now.year, now.month, now.day]
            member_now = [ member.created_at.year, member.created_at.month, member.created_at.day]
            
            if now == member_now:
                return
        
        timestamp_bucket_for_logging = member.created_at.strftime(
            "%B %d, %Y, %I %p")
        # generate string representation for the account creation date (July 1st, 2021 for example).
        # we will use this for the cooldown mechanism, to ratelimit accounts created on this date.
        timestamp = member.created_at.strftime(
            "%B %d, %Y")
        
        # store this user with all the users that were created on this date
        async with self.join_overtime_lock:
            if self.join_overtime_mapping.get(timestamp) is None:
                self.join_overtime_mapping[timestamp] = [member]
            else:
                if member in self.join_overtime_mapping[timestamp]:
                    return
                
                self.join_overtime_mapping[timestamp].append(member)

        # handle ratelimitting. If ratelimit is triggered, ban all the users we know were created on this date.
        bucket = self.join_overtime_raid_detection_threshold.get_bucket(timestamp)
        current = member.joined_at.replace(tzinfo=timezone.utc).timestamp()
        if bucket.update_rate_limit(current):
            users = [ m for m in self.join_overtime_mapping.get(timestamp) ]
            for user in users:
                try:
                    await self.raid_ban(user, reason=f"Join spam over time detected (bucket `{timestamp_bucket_for_logging}`)", dm_user=True)
                    self.join_overtime_mapping[timestamp].remove(user)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        if message.guild.id != self.bot.settings.guild_id:
            return
        if self.bot.settings.permissions.hasAtLeast(message.guild, message.author, 1):
            return
        
        if await self.ping_spam(message):  
            await self.handle_raid_detection(message, RaidType.PingSpam)
        elif await self.raid_phrase_detected(message):
            await self.handle_raid_detection(message, RaidType.RaidPhrase)
        elif await self.message_spam(message):
            await self.handle_raid_detection(message, RaidType.MessageSpam)

    async def handle_raid_detection(self, message: discord.Message, raid_type: RaidType):
        current = message.created_at.replace(tzinfo=timezone.utc).timestamp()
        spam_detection_bucket = self.raid_detection_threshold.get_bucket(message)
        user = message.author
        
        do_freeze = False
        do_banning = False
        self.spam_user_mapping[user.id] = 1
        
        # has the antiraid filter been triggered 5 or more times in the past 10 seconds?
        if spam_detection_bucket.update_rate_limit(current):
            do_banning = True
            # yes! notify the mods and lock the server.
            raid_alert_bucket = self.raid_alert_cooldown.get_bucket(message)
            if not raid_alert_bucket.update_rate_limit(current):
                await self.bot.report.report_raid(user, message)
                do_freeze = True


        # lock the server
        if do_freeze:
            await self.freeze_server(message.guild)

        # ban all the spammers
        if raid_type in [RaidType.PingSpam, RaidType.MessageSpam]:
            if not do_banning and not do_freeze:
                if raid_type is RaidType.PingSpam:
                    title = "Ping spam detected"
                else:
                    title = "Message spam detected"
                await self.bot.report.report_spam(message, user, title=title)
            else:
                users = list(self.spam_user_mapping.keys())
                for user in users:
                    try:
                        _ = self.spam_user_mapping[user]
                    except KeyError:
                        continue
                                        
                    user = message.guild.get_member(user)
                    if user is None:
                        continue
                    
                    try:
                        await self.raid_ban(user, reason="Ping spam detected" if raid_type is RaidType.PingSpam else "Message spam detected")
                    except Exception:
                        pass

    async def ping_spam(self, message):
        """If a user pings more than 5 people, or pings more than 2 roles, mute them.
        A report is generated which a mod must review (either unmute or ban the user using a react)
        """

        if len(set(message.mentions)) > 4 or len(set(message.role_mentions)) > 2:
            mute = self.bot.get_command("mute")
            if mute is not None:
                ctx = await self.bot.get_context(message, cls=context.Context)
                user = message.author
                ctx.message.author = ctx.author = ctx.me
                await mute(ctx=ctx, user=user, reason="Ping spam")
                ctx.message.author = ctx.author = user
                return True

        return False
    
    async def message_spam(self, message):
        """If a message is spammed 8 times in 5 seconds, mute the user and generate a report.
        A mod must either unmute or ban the user.
        """

        if self.bot.settings.permissions.hasAtLeast(message.guild, message.author, 1):
            return False
                
        bucket = self.message_spam_detection_threshold.get_bucket(message)
        current = message.created_at.replace(tzinfo=timezone.utc).timestamp()

        if bucket.update_rate_limit(current):
            if message.author.id in self.spam_user_mapping:
                return True
            
            mute = self.bot.get_command("mute")
            if mute is not None:
                ctx = await self.bot.get_context(message, cls=context.Context)
                user = message.author
                ctx.message.author = ctx.author = ctx.me
                try:
                    await mute(ctx=ctx, user=user, reason="Message spam")
                except Exception:
                    pass
                ctx.message.author = ctx.author = user
                return True
    
    async def raid_phrase_detected(self, message):
        """Raid phrases are specific phrases (such as known scam URLs), and upon saying them, whitenames
        will immediately be banned. Uses the same system as filters to search messages for the phrases.
        """
        
        if self.bot.settings.permissions.hasAtLeast(message.guild, message.author, 2):
            return False

        #TODO: Unify filtering system
        symbols = (u"абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ",
                u"abBrdeex3nnKnmHonpcTyoxu4wwbbbeoRABBrDEEX3NNKNMHONPCTyOXU4WWbbbEOR")

        tr = {ord(a): ord(b) for a, b in zip(*symbols)}

        folded_message = fold(message.content.translate(tr).lower()).lower()
        folded_without_spaces = "".join(folded_message.split())
        folded_without_spaces_and_punctuation = folded_without_spaces.translate(str.maketrans('', '', string.punctuation))

        if folded_message:
            for word in self.bot.settings.guild().raid_phrases:
                if not self.bot.settings.permissions.hasAtLeast(message.guild, message.author, word.bypass):
                    if (word.word.lower() in folded_message) or \
                        (not word.false_positive and word.word.lower() in folded_without_spaces) or \
                        (not word.false_positive and word.word.lower() in folded_without_spaces_and_punctuation):
                        # remove all whitespace, punctuation in message and run filter again
                        if word.false_positive and word.word.lower() not in folded_message.split():
                            continue

                        ctx = await self.bot.get_context(message, cls=context.Context)
                        await self.raid_ban(message.author)
                        return True
        return False
            
    async def raid_ban(self, user: discord.Member, reason="Raid phrase detected", dm_user=False):
        """Helper function to ban users"""
        
        async with self.banning_lock:
            if self.ban_user_mapping.get(user.id) is not None:
                return
            else:
                self.ban_user_mapping[user.id] = 1

            case = Case(
                _id=self.bot.settings.guild().case_id,
                _type="BAN",
                date=datetime.now(),
                mod_id=self.bot.user.id,
                mod_tag=str(self.bot.user),
                punishment="PERMANENT",
                reason=reason
            )

            await self.bot.settings.inc_caseid()
            await self.bot.settings.add_case(user.id, case)
            
            log = await logger.prepare_ban_log(self.bot.user, user, case)
            
            if dm_user:
                try:
                    await user.send(f"You were banned from {user.guild.name}.\n\nThis action was performed automatically. If you think this was a mistake, please send a message here: https://www.reddit.com/message/compose?to=%2Fr%2FJailbreak", embed=log)
                except Exception:
                    pass
            
            if user.guild.get_member(user.id) is not None:
                await user.ban(reason="Raid")
            else:
                await user.guild.ban(discord.Object(id=user.id), reason="Raid")
                
            public_logs = user.guild.get_channel(self.bot.settings.guild().channel_mod_logs)
            if public_logs:
                log.remove_author()
                log.set_thumbnail(url=user.avatar)
                await public_logs.send(embed=log)

    async def freeze_server(self, guild):
        """Freeze all channels marked as freezeable during a raid, meaning only people with the Member+ role and up
        can talk (temporarily lock out whitenames during a raid)"""
        
        settings = self.bot.settings.guild()
        
        for channel in settings.locked_channels:
            channel = guild.get_channel(channel)
            if channel is None:
                continue

        default_role = guild.default_role
        # nerds = ctx.guild.get_role(settings.role_nerds)   
        
        default_perms = channel.overwrites_for(default_role)
        # nerds_perms = channel.overwrites_for(nerds)

        if default_perms.send_messages is True:
            default_perms.send_messages = False

        
            try:
                await channel.set_permissions(default_role, overwrite=default_perms, reason="Locked!")
                # await channel.set_permissions(nerds, overwrite=nerds_perms, reason="Locked!" if lock else "Unlocked!")
                return True
            except Exception:
                return


def setup(bot):
    bot.add_cog(AntiRaidMonitor(bot))
