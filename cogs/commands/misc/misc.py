import base64
import datetime
import json
import traceback
import typing
from io import BytesIO

import discord
import humanize
import pytimeparse
from discord.ext import commands
from PIL import Image


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(3, 15.0, commands.BucketType.channel)

        try:
            with open('emojis.json') as f:
                self.emojis = json.loads(f.read())
        except IOError:
            raise Exception("Could not find emojis.json. Make sure to run grab_emojis.py")
        
    @commands.command(name="remindme")
    @commands.guild_only()
    async def remindme(self, ctx, dur: str, *, reminder: str):
        """Send yourself a reminder after a given time gap

        Example usage
        -------------
        !remindme 1h bake the cake

        Parameters
        ----------
        dur : str
            After when to send the reminder
        reminder : str
            What to remind you of
        """
         
        bot_chan = self.bot.settings.guild().channel_offtopic
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 2) and ctx.channel.id != bot_chan:
            raise commands.BadArgument(f"Command only allowed in <#{bot_chan}>.")
        
        now = datetime.datetime.now()
        delta = pytimeparse.parse(dur)
        if delta is None:
            raise commands.BadArgument("Please give a valid time to remind you! (i.e 1h, 30m)")
        
        time = now + datetime.timedelta(seconds=delta)
        if time < now:
            raise commands.BadArgument("Time has to be in the future >:(")
        reminder = discord.utils.escape_markdown(reminder)
        
        self.bot.settings.tasks.schedule_reminder(ctx.author.id, reminder, time)        
        natural_time =  humanize.naturaldelta(
                    delta, minimum_unit="seconds")
        embed = discord.Embed(title="Reminder set", color=discord.Color.random(), description=f"We'll remind you in {natural_time} ")
        await ctx.message.reply(embed=embed)
        
    @commands.command(name="jumbo")
    @commands.guild_only()
    async def jumbo(self, ctx, emoji: typing.Union[discord.Emoji, discord.PartialEmoji, str]):
        """Post large version of a given emoji

        Example usage
        -------------
        !jumbo :ntwerk:

        Parameters
        ----------
        emoji : typing.Union[discord.Emoji, discord.PartialEmoji]
            Emoji to post
        """
        
        bot_chan = self.bot.settings.guild().channel_offtopic
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 2) and ctx.channel.id != bot_chan:
            if await self.ratelimit(ctx.message):
                raise commands.BadArgument("This command is on cooldown.")

        if isinstance(emoji, str):
            async with ctx.typing():
                emoji_url_file = self.emojis.get(emoji)
                if emoji_url_file is None:
                    raise commands.BadArgument("Couldn't find a suitable emoji.")

            im = Image.open(BytesIO(base64.b64decode(emoji_url_file)))
            image_container = BytesIO()
            im.save(image_container, 'png')
            image_container.seek(0)
            _file = discord.File(image_container, filename="image.png")
            await ctx.message.reply(file=_file, mention_author=False)

        else:
            await ctx.message.reply(emoji.url, mention_author=False)

    async def ratelimit(self, message):
        bucket = self.spam_cooldown.get_bucket(message)
        return bucket.update_rate_limit()

    @commands.command(name="avatar")
    @commands.guild_only()
    async def avatar(self, ctx, member: discord.Member = None):
        """Post large version of a given user's avatar

        Parameters
        ----------
        member : discord.Member, optional
            Member to get avatar of, default to command invoker
        """

        if member is None:
            member = ctx.author

        bot_chan = self.bot.settings.guild().channel_offtopic

        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 1) and ctx.channel.id != bot_chan:
            raise commands.BadArgument(
                f"Command only allowed in <#{bot_chan}>")

        embed = discord.Embed(title=f"{member}'s avatar")
        embed.set_image(url=member.avatar_url)
        embed.color = discord.Color.random()
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.message.reply(embed=embed)

    @commands.command(name='helpers')
    @commands.cooldown(type=commands.BucketType.member, rate=1, per=86400)
    async def helpers(self, ctx):
        """Tag helpers, usable in #support once every 24 hours per user"""

        if ctx.channel.id != self.bot.settings.guild().channel_support:
           self.helpers.reset_cooldown(ctx)
           raise commands.BadArgument(f'This command is only usable in <#{self.bot.settings.guild().channel_support}>!')
           
        helper_role = ctx.guild.get_role(self.bot.settings.guild().role_helpers)
        await ctx.message.reply(f'<@{ctx.author.id}> pinged {helper_role.mention}', allowed_mentions=discord.AllowedMentions(roles=True))

    @helpers.error
    @jumbo.error
    @remindme.error
    @avatar.error
    async def info_error(self, ctx, error):
        await ctx.message.delete(delay=5)
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(ctx, error)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send_error(ctx, "You can only use this command once every 24 hours.")
        else:
            await ctx.send_error(ctx, "A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


def setup(bot):
    bot.add_cog(Misc(bot))
