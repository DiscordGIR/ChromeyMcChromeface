import traceback
import typing
from math import floor

import discord
from discord.ext import commands, menus


class CasesSource(menus.GroupByPageSource):
    async def format_page(self, menu, entry):
        pun_map = {
            "KICK": "Kicked",
            "BAN": "Banned",
            "UNBAN": "Unbanned",
            "MUTE": "Duration",
        }

        user = menu.ctx.args[2] or menu.ctx.author
        u = await menu.ctx.bot.settings.user(user.id)
        embed = discord.Embed(
            title=f'Cases', color=discord.Color.blurple())
        embed.set_author(name=user, icon_url=user.avatar_url)
        for case in entry.items:
            timestamp = case.date.strftime("%B %d, %Y, %I:%M %p")
            if case._type == "WARN" or case._type == "LIFTWARN":
                if case.lifted:
                    embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id} [LIFTED]',
                                    value=f'**Reason**: {case.reason}\n**Lifted by**: {case.lifted_by_tag}\n**Lift reason**: {case.lifted_reason}\n**Warned on**: {timestamp}', inline=True)
                else:
                    embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id}',
                                    value=f'**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Warned on**: {timestamp} UTC', inline=True)
            elif case._type == "MUTE":
                embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id}',
                                value=f'**{pun_map[case._type]}**: {case.punishment}\n**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Time**: {timestamp} UTC', inline=True)
            elif case._type in pun_map:
                embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id}',
                                value=f'**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**{pun_map[case._type]} on**: {timestamp} UTC', inline=True)
            else:
                embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id}',
                                value=f'**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Time**: {timestamp} UTC', inline=True)
        embed.set_footer(
            text=f"Page {menu.current_page +1} of {self.get_max_pages()} - newest cases first")
        return embed


class MenuPages(menus.MenuPages):
    async def update(self, payload):
        if self._can_remove_reactions:
            if payload.event_type == 'REACTION_ADD':
                await self.message.remove_reaction(payload.emoji, payload.member)
            elif payload.event_type == 'REACTION_REMOVE':
                return
        await super().update(payload)


class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_cache = {}

    @commands.guild_only()
    @commands.command(name="userinfo", aliases=["info"])
    async def userinfo(self, ctx: commands.Context, user: typing.Union[discord.Member, int] = None) -> None:
        """Get information about a user (join/creation date, etc.), defaults to command invoker.

        Example usage:
        --------------
        `!userinfo <@user/ID (optional)>`

        Parameters
        ----------
        user : discord.Member, optional
            User to get info about, by default the author of command, by default None
        """

        if user is None:
            user = ctx.author

        is_mod = self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 2)

        if isinstance(user, int):
            if not is_mod:
                raise commands.BadArgument("You do not have permission to use this command.")
            try:
                user = await self.bot.fetch_user(user)
            except discord.NotFound:
                raise commands.BadArgument(
                    f"Couldn't find user with ID {user}")

        if not is_mod and user.id != ctx.author.id:
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        bot_chan = self.bot.settings.guild().channel_offtopic
        if not is_mod and ctx.channel.id != bot_chan:
            raise commands.BadArgument(
                f"Command only allowed in <#{bot_chan}>")

        roles = ""

        if isinstance(user, discord.Member):
            reversed_roles = user.roles
            reversed_roles.reverse()

            for role in reversed_roles:
                if role != ctx.guild.default_role:
                    roles += role.mention + " "

            joined = user.joined_at.strftime("%B %d, %Y, %I:%M %p") + " UTC"
        else:
            roles = "No roles."
            joined = "User not in r/ChromeOS."

        created = user.created_at.strftime("%B %d, %Y, %I:%M %p") + " UTC"

        embed = discord.Embed(title="User Information")
        embed.color = user.color
        embed.set_author(name=user)
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="Username",
                        value=f'{user} ({user.mention})', inline=True)
        embed.add_field(
            name="Roles", value=roles if roles else "None", inline=False)
        embed.add_field(name="Join date", value=joined, inline=True)
        embed.add_field(name="Account creation date",
                        value=created, inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.message.reply(embed=embed)

    @commands.guild_only()
    @commands.command(name="cases")
    async def cases(self, ctx, user: typing.Union[discord.Member, int] = None):
        """Show list of cases of a user (mod only)

        Example usage:
        --------------
        `!cases <@user/ID>`

        Parameters
        ----------
        user : typing.Union[discord.Member,int]
            User we want to get cases of, doesn't have to be in guild

        """

        if user is None:
            user = ctx.author
            ctx.args[2] = user

        bot_chan = self.bot.settings.guild().channel_offtopic
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 2) and ctx.channel.id != bot_chan:
            raise commands.BadArgument(
                f"Command only allowed in <#{bot_chan}>")

        if not isinstance(user, int):
            if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 2) and user.id != ctx.author.id:
                raise commands.BadArgument(
                    f"You don't have permissions to check others' cases.")
        else:
            if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 2):
                raise commands.BadArgument(
                    f"You don't have permissions to check others' cases.")

        if isinstance(user, int):
            try:
                user = await self.bot.fetch_user(user)
            except Exception:
                raise commands.BadArgument(
                    f"Couldn't find user with ID {user}")
            ctx.args[2] = user

        results = await self.bot.settings.cases(user.id)
        if len(results.cases) == 0:
            if isinstance(user, int):
                raise commands.BadArgument(
                    f'User with ID {user.id} had no cases.')
            else:
                raise commands.BadArgument(f'{user.mention} had no cases.')
        cases = [case for case in results.cases if case._type != "UNMUTE"]
        cases.reverse()

        menus = MenuPages(source=CasesSource(
            cases, key=lambda t: 1, per_page=9), clear_reactions_after=True)
        await menus.start(ctx)

    @cases.error
    @userinfo.error
    async def info_error(self, ctx, error):
        await ctx.message.delete(delay=5)
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
                or isinstance(error, commands.NoPrivateMessage)):
            await self.bot.send_error(ctx, error)
        else:
            await self.bot.send_error(ctx, "A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


async def determine_emoji(type):
    emoji_dict = {
        "KICK": "👢",
        "BAN": "❌",
        "UNBAN": "✅",
        "MUTE": "🔇",
        "WARN": "⚠️",
        "UNMUTE": "🔈",
    }
    return emoji_dict[type]


def setup(bot):
    bot.add_cog(UserInfo(bot))
