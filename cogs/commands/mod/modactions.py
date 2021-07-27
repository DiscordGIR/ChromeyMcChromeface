import datetime
import traceback
import typing

import cogs.utils.context as context
import cogs.utils.logs as logging
import cogs.utils.permission_checks as permissions
import discord
import humanize
import pytimeparse
from data.case import Case
from discord.ext import commands


class ModActions(commands.Cog):
    """This cog handles all the possible moderator actions.
    - Kick
    - Ban
    - Unban
    - Warn
    - Liftwarn
    - Mute
    - Unmute
    - Purge
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.bot_has_guild_permissions(kick_members=True, ban_members=True)
    @commands.command(name="warn")
    async def warn(self, ctx: context.Context, user: permissions.ModsAndAboveExternal, *, reason: str = "No reason.") -> None:
        """Warn a user (nerds and up)

        Example usage
        --------------
        !warn <@user/ID> <reason (optional)>

        Parameters
        ----------
        user : discord.Member
            "The member to warn"
        reason : str, optional
            "Reason for warning, by default 'No reason.'"

        """

        if user.id == ctx.author.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on yourself.")
        if user.bot:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on bots :(")

        if not ctx.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 1):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        # if the ID given is of a user who isn't in the guild, try to fetch the profile
        if isinstance(user, int):
            try:
                user = await self.bot.fetch_user(user)
            except discord.NotFound:
                raise commands.BadArgument(
                    f"Couldn't find user with ID {user}")

        guild = ctx.settings.guild()

        reason = discord.utils.escape_markdown(reason)
        reason = discord.utils.escape_mentions(reason)

        # prepare the case object for database
        case = Case(
            _id=guild.case_id,
            _type="WARN",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
            punishment="WARN"
        )

        # increment case ID in database for next available case ID
        await ctx.settings.inc_caseid()
        # add new case to DB
        await ctx.settings.add_case(user.id, case)

        # prepare log embed, send to user, channel where invoked
        log = await logging.prepare_warn_log(ctx.author, user, case)
        
        dmed = True
        if isinstance(user, discord.Member):
            try:
                await user.send(f"You were warned in {ctx.guild.name}.", embed=log)
            except Exception:
                dmed = False

        # also send response in channel where command was called
        await ctx.message.reply(user.mention if not dmed else "", embed=log)
        modlog_chan = ctx.guild.get_channel(
            ctx.settings.guild().channel_modlogs)
        if modlog_chan:
            log.remove_author()
            log.set_thumbnail(url=user.avatar_url)
            await modlog_chan.send(embed=log)

    @commands.guild_only()
    @commands.command(name="liftwarn")
    async def liftwarn(self, ctx: context.Context, user: permissions.ModsAndAboveExternal, case_id: int, *, reason: str = "No reason.") -> None:
        """Mark a warn as lifted. (mod only)

        Example usage
        --------------
        !liftwarn <@user/ID> <case ID> <reason (optional)>

        Parameters
        ----------
        user : discord.Member
            "User to remove warn from"
        case_id : int
            "The ID of the case for which lift"
        reason : str, optional
            "Reason for lifting warn, by default 'No reason.'"

        """

        # retrieve user's case with given ID
        cases = await ctx.settings.get_case(user.id, case_id)
        case = cases.cases.filter(_id=case_id).first()

        reason = discord.utils.escape_markdown(reason)
        reason = discord.utils.escape_mentions(reason)

        # sanity checks
        if case is None:
            raise commands.BadArgument(
                message=f"{user} has no case with ID {case_id}")
        elif case._type != "WARN":
            raise commands.BadArgument(
                message=f"{user}'s case with ID {case_id} is not a warn case.")
        elif case.lifted:
            raise commands.BadArgument(
                message=f"Case with ID {case_id} already lifted.")

        # passed sanity checks, so update the case in DB
        case.lifted = True
        case.lifted_reason = reason
        case.lifted_by_tag = str(ctx.author)
        case.lifted_by_id = ctx.author.id
        case.lifted_date = datetime.datetime.now()
        cases.save()

        dmed = True
        # prepare log embed, send to user, channel where invoked
        log = await logging.prepare_liftwarn_log(ctx.author, user, case)
        try:
            await user.send(f"Your warn was lifted in {ctx.guild.name}.", embed=log)
        except Exception:
            dmed = False

        await ctx.message.reply(user.mention if not dmed else "", embed=log)
        modlog_chan = ctx.guild.get_channel(
        ctx.settings.guild().channel_modlogs)
        if modlog_chan:
            log.remove_author()
            log.set_thumbnail(url=user.avatar_url)
            await modlog_chan.send(embed=log)

    @commands.guild_only()
    @commands.command(name="editreason")
    async def editreason(self, ctx: context.Context, user: permissions.ModsAndAboveExternal, case_id: int, *, new_reason: str) -> None:
        """Edit case reason for a case (mod only)

        Example usage
        --------------
        !editreason <@user/ID> <case ID> <reason>

        Parameters
        ----------
        user : discord.Member
            "User to edit case of"
        case_id : int
            "The ID of the case for which we want to edit reason"
        new_reason : str
            "New reason"

        """

        # retrieve user's case with given ID
        cases = await ctx.settings.get_case(user.id, case_id)
        case = cases.cases.filter(_id=case_id).first()

        new_reason = discord.utils.escape_markdown(new_reason)
        new_reason = discord.utils.escape_mentions(new_reason)

        # sanity checks
        if case is None:
            raise commands.BadArgument(
                message=f"{user} has no case with ID {case_id}")
            
        old_reason = case.reason
        case.reason = new_reason
        case.date = datetime.datetime.now()
        cases.save()
        
        dmed = True
        log = await logging.prepare_editreason_log(ctx.author, user, case, old_reason)
        if isinstance(user, discord.Member):
            try:
                await user.send(f"Your case was updated in {ctx.guild.name}.", embed=log)
            except Exception:
                dmed = False

            
        await ctx.message.reply(f"The case has been updated.", embed=log)
        modlog_chan = ctx.guild.get_channel(
        ctx.settings.guild().channel_modlogs)
        if modlog_chan:
            log.remove_author()
            log.set_thumbnail(url=user.avatar_url)
            await modlog_chan.send(embed=log)

        
    @commands.guild_only()
    @commands.bot_has_guild_permissions(kick_members=True)
    @commands.command(name="kick")
    async def kick(self, ctx: context.Context, user: permissions.ModsAndAboveMember, *, reason: str = "No reason.") -> None:
        """Kick a user (mod only)

        Example usage
        --------------
        !kick <@user/ID> <reason (optional)>

        Parameters
        ----------
        user : discord.Member
            "User to kick"
        reason : str, optional
            "Reason for kick, by default 'No reason.'"

        """

        reason = discord.utils.escape_markdown(reason)
        reason = discord.utils.escape_mentions(reason)

        log = await self.add_kick_case(ctx, user, reason)

        try:
            await user.send(f"You were kicked from {ctx.guild.name}", embed=log)
        except Exception:
            pass

        await user.kick(reason=f'{ctx.author}: {reason}')
        await ctx.message.reply(embed=log)
        modlog_chan = ctx.guild.get_channel(
        ctx.settings.guild().channel_modlogs)
        if modlog_chan:
            log.remove_author()
            log.set_thumbnail(url=user.avatar_url)
            await modlog_chan.send(embed=log)


    async def add_kick_case(self, ctx: context.Context, user, reason):
        # prepare case for DB
        case = Case(
            _id=ctx.settings.guild().case_id,
            _type="KICK",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
        )

        # increment max case ID for next case
        await ctx.settings.inc_caseid()
        # add new case to DB
        await ctx.settings.add_case(user.id, case)

        return await logging.prepare_kick_log(ctx.author, user, case)

    @commands.guild_only()
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.command(name="ban")
    async def ban(self, ctx: context.Context, user: permissions.ModsAndAboveExternal, *, reason: str = "No reason."):
        """Ban a user (mod only)

        Example usage
        --------------
        !ban <@user/ID> <reason (optional)>

        Parameters
        ----------
        user : permissions.ModsAndAboveExternal
            "The user to be banned, doesn't have to be part of the guild"
        reason : str, optional
            "Reason for ban, by default 'No reason.'"

        """

        reason = discord.utils.escape_markdown(reason)
        reason = discord.utils.escape_mentions(reason)

        # if the ID given is of a user who isn't in the guild, try to fetch the profile
        if isinstance(user, int):
            try:
                user = await self.bot.fetch_user(user)
                previous_bans = [user for _, user in await ctx.guild.bans()]
                if user in previous_bans:
                    raise commands.BadArgument("That user is already banned!")
            except discord.NotFound:
                raise commands.BadArgument(
                    f"Couldn't find user with ID {user}")

        log = await self.add_ban_case(ctx, user, reason)

        try:
            await user.send(f"You were banned from {ctx.guild.name}", embed=log)
        except Exception:
            pass

        if isinstance(user, discord.Member):
            await user.ban(reason=f'{ctx.author}: {reason}')
        else:
            # hackban for user not currently in guild
            await ctx.guild.ban(discord.Object(id=user.id), reason=f'{ctx.author}: {reason}')

        await ctx.message.reply(embed=log)
        modlog_chan = ctx.guild.get_channel(
        ctx.settings.guild().channel_modlogs)
        if modlog_chan:
            log.remove_author()
            log.set_thumbnail(url=user.avatar_url)
            await modlog_chan.send(embed=log)


    async def add_ban_case(self, ctx: context.Context, user, reason):
        # prepare the case to store in DB
        case = Case(
            _id=ctx.settings.guild().case_id,
            _type="BAN",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            punishment="PERMANENT",
            reason=reason,
        )

        # increment DB's max case ID for next case
        await ctx.settings.inc_caseid()
        # add case to db
        await ctx.settings.add_case(user.id, case)
        # prepare log embed to send to user and context
        return await logging.prepare_ban_log(ctx.author, user, case)

    @commands.guild_only()
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.command(name="unban")
    async def unban(self, ctx: context.Context, user: int, *, reason: str = "No reason.") -> None:
        """Unban a user (must use ID) (mod only)

        Example usage
        --------------
        !unban <user ID> <reason (optional)> 

        Parameters
        ----------
        user : int
            "ID of the user to unban"
        reason : str, optional
            "Reason for unban, by default 'No reason.'"

        """

        reason = discord.utils.escape_markdown(reason)
        reason = discord.utils.escape_mentions(reason)

        try:
            user = await self.bot.fetch_user(user)
            previous_bans = [user for _, user in await ctx.guild.bans()]
            if user not in previous_bans:
                raise commands.BadArgument("That user isn't banned!")
        except discord.NotFound:
            raise commands.BadArgument(f"Couldn't find user with ID {user}")

        try:
            await ctx.guild.unban(discord.Object(id=user.id), reason=f'{ctx.author}: {reason}')
        except discord.NotFound:
            raise commands.BadArgument(f"{user} is not banned.")

        case = Case(
            _id=ctx.settings.guild().case_id,
            _type="UNBAN",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
        )
        await ctx.settings.inc_caseid()
        await ctx.settings.add_case(user.id, case)

        log = await logging.prepare_unban_log(ctx.author, user, case)
        await ctx.message.reply(embed=log)
        modlog_chan = ctx.guild.get_channel(
        ctx.settings.guild().channel_modlogs)
        if modlog_chan:
            log.remove_author()
            log.set_thumbnail(url=user.avatar_url)
            await modlog_chan.send(embed=log)


    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_messages=True)
    @commands.command(name="purge")
    async def purge(self, ctx: context.Context, limit: int = 0) -> None:
        """Purge messages from current channel (mod only)

        Example usage
        --------------
        !purge <number of messages>

        Parameters
        ----------
        limit : int, optional
            "Number of messages to purge, must be > 0, by default 0 for error handling"

        """

        if limit <= 0:
            raise commands.BadArgument(
                "Number of messages to purge must be greater than 0")
        elif limit > 100:
            limit = 100 # safety mechanism to not accidentally purge a ton of messsages if someone screws this up
        
        msgs = await ctx.channel.history(limit=limit+1).flatten()

        await ctx.channel.purge(limit=limit+1)
        await ctx.send(f'Purged {len(msgs)} messages.', delete_after=5)

    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.command(name="mute")
    async def mute(self, ctx: context.Context, user: permissions.ModsAndAboveMember, dur: str = "", *, reason: str = "No reason.") -> None:
        """Mute a user (nerds and up)

        Example usage
        --------------
        !mute <@user/ID> <duration> <reason (optional)>

        Parameters
        ----------
        user : discord.Member
            "Member to mute"
        dur : str
            "Duration of mute (i.e 1h, 10m, 1d)"
        reason : str, optional
            "Reason for mute, by default 'No reason.'"

        """

        reason = discord.utils.escape_markdown(reason)
        reason = discord.utils.escape_mentions(reason)

        now = datetime.datetime.now()
        delta = pytimeparse.parse(dur)

        if delta is None:
            if reason == "No reason." and dur == "":
                reason = "No reason."
            elif reason == "No reason.":
                reason = dur
            else:
                reason = f"{dur} {reason}"

        mute_role = ctx.settings.guild().role_mute
        mute_role = ctx.guild.get_role(mute_role)

        if mute_role in user.roles:
            raise commands.BadArgument("This user is already muted.")

        case = Case(
            _id=ctx.settings.guild().case_id,
            _type="MUTE",
            date=now,
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
        )

        if delta:
            try:
                time = now + datetime.timedelta(seconds=delta)
                case.until = time
                case.punishment = humanize.naturaldelta(
                    time - now, minimum_unit="seconds")
                ctx.tasks.schedule_unmute(user.id, time)
            except Exception:
                raise commands.BadArgument(
                    "An error occured, this user is probably already muted")
        else:
            case.punishment = "PERMANENT"

        await ctx.settings.inc_caseid()
        await ctx.settings.add_case(user.id, case)
        u = await ctx.settings.user(id=user.id)
        u.is_muted = True
        u.save()

        await user.add_roles(mute_role)

        log = await logging.prepare_mute_log(ctx.author, user, case)

        dmed = True
        try:
            await user.send(f"You have been muted in {ctx.guild.name}", embed=log)
        except Exception:
            dmed = False

        await ctx.message.reply(embed=log)
        modlog_chan = ctx.guild.get_channel(
        ctx.settings.guild().channel_modlogs)
        if modlog_chan:
            log.remove_author()
            log.set_thumbnail(url=user.avatar_url)
            await modlog_chan.send(embed=log)


    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.command(name="unmute")
    async def unmute(self, ctx: context.Context, user: permissions.ModsAndAboveMember, *, reason: str = "No reason.") -> None:
        """Unmute a user (mod only)

        Example usage
        --------------
        !unmute <@user/ID> <reason (optional)>

        Parameters
        ----------
        user : discord.Member
            "Member to unmute"
        reason : str, optional
            "Reason for unmute, by default 'No reason.'"

        """

        mute_role = ctx.settings.guild().role_mute
        mute_role = ctx.guild.get_role(mute_role)
        await user.remove_roles(mute_role)

        u = await ctx.settings.user(id=user.id)
        u.is_muted = False
        u.save()

        try:
            ctx.tasks.cancel_unmute(user.id)
        except Exception:
            pass

        case = Case(
            _id=ctx.settings.guild().case_id,
            _type="UNMUTE",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
        )
        await ctx.settings.inc_caseid()
        await ctx.settings.add_case(user.id, case)

        log = await logging.prepare_unmute_log(ctx.author, user, case)

        dmed = True
        try:
            await user.send(f"You have been unmuted in {ctx.guild.name}", embed=log)
        except Exception:
            dmed = False

        await ctx.message.reply(embed=log)
        modlog_chan = ctx.guild.get_channel(
        ctx.settings.guild().channel_modlogs)
        if modlog_chan:
            log.remove_author()
            log.set_thumbnail(url=user.avatar_url)
            await modlog_chan.send(embed=log)

    @unmute.error
    @mute.error
    @liftwarn.error
    @unban.error
    @ban.error
    @warn.error
    @purge.error
    @kick.error
    @editreason.error
    async def info_error(self, ctx: context.Context, error):
        await ctx.message.delete(delay=5)
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MissingPermissions)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error(error)
            traceback.print_exc()


def setup(bot):
    bot.add_cog(ModActions(bot))
