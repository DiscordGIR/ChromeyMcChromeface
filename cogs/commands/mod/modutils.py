import datetime
import traceback

import cogs.utils.context as context
import cogs.utils.permission_checks as permissions
import discord
import humanize
import pytz
from discord.ext import commands


class ModUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @permissions.mods_and_up()
    @commands.command(name="rundown", aliases=['rd'])
    async def rundown(self, ctx: context.Context, user: discord.Member) -> None:
        """Get information about a user (join/creation date, etc.), defaults to command invoker.

        Example usage
        --------------
        !userinfo <@user/ID (optional)>

        Parameters
        ----------
        user : discord.Member, optional
            "User to get info about, by default the author of command, by default None"
        """

        await ctx.message.reply(embed=await self.prepare_rundown_embed(ctx, user))

    @commands.guild_only()
    @permissions.admins_and_up()
    @commands.command(name="transferprofile")
    async def transferprofile(self, ctx, oldmember: permissions.ModsAndAboveExternal, newmember: discord.Member):
        """Transfer all data in the database between users (admin only)

        Example usage
        -------------
        !transferprofile <@olduser/ID> <@newuser/ID>

        Parameters
        ----------
        oldmember : typing.Union[int, discord.Member]
            "ID/@tag of the old user, optionally in the guild"
        newmember : discord.Member
            "ID/@tag of the new user, must be in the"

        """

        _, case_count = await ctx.settings.transfer_profile(oldmember.id, newmember.id)

        embed = discord.Embed(title="Transferred profile")
        embed.description = f"We transferred {oldmember.mention}'s profile to {newmember.mention}"
        embed.color = discord.Color.blurple()
        embed.add_field(name="Cases", value=f"We transfered {case_count} cases")

        await ctx.message.reply(embed=embed)
        
        try:
            await newmember.send(f"{ctx.author} has transferred your profile from {oldmember}", embed=embed)
        except Exception:
            pass

    @commands.guild_only()
    @permissions.mods_and_up()
    @commands.command(name="birthday")
    async def birthday(self, ctx: context.Context, user: discord.Member) -> None:
        """Give user birthday role for 24 hours (mod only)

        Example usage
        --------------
        !birthday <@user/ID>

        Parameters
        ----------
        user : discord.Member
            "User whose bithday to set"

        """

        if user.id == self.bot.user.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on me :(")

        eastern = pytz.timezone('US/Eastern')
        birthday_role = ctx.guild.get_role(ctx.settings.guild().role_birthday)
        if birthday_role is None:
            return
        if birthday_role in user.roles:
            return
        now = datetime.datetime.now(eastern)
        h = now.hour / 24
        m = now.minute / 60 / 24

        try:
            time = now + datetime.timedelta(days=1-h-m)
            ctx.tasks.schedule_remove_bday(user.id, time)
        except Exception as e:
            return
        await user.add_roles(birthday_role)
        await user.send(f"According to my calculations, today is your birthday! We've given you the {birthday_role} role for 24 hours.")
        
        await ctx.message.reply(f"Gave {user.mention} the birthday role for 24 hours.", allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=False))

    async def prepare_rundown_embed(self, ctx, user):
        joined = user.joined_at.strftime("%B %d, %Y, %I:%M %p")
        created = user.created_at.strftime("%B %d, %Y, %I:%M %p")
        rd = await ctx.settings.rundown(user.id)
        rd_text = ""
        for r in rd:
            rd_text += f"**{r._type}** - {r.punishment} - {r.reason} - {humanize.naturaltime(datetime.datetime.now() - r.date)}\n"

        reversed_roles = user.roles
        reversed_roles.reverse()

        roles = ""
        for role in reversed_roles[0:4]:
            if role != user.guild.default_role:
                roles += role.mention + " "
        roles = roles.strip() + "..."

        embed = discord.Embed(title="Rundown")
        embed.color = user.top_role.color
        embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(name="Member", value=f"{user} ({user.mention}, {user.id})")
        embed.add_field(name="Join date", value=f"{joined} UTC")
        embed.add_field(name="Account creation date",
                        value=f"{created} UTC")

        embed.add_field(
            name="Roles", value=roles if roles else "None", inline=False)

        if len(rd) > 0:
            embed.add_field(name=f"{len(rd)} most recent cases",
                            value=rd_text, inline=False)
        else:
            embed.add_field(name=f"Recent cases",
                            value="This user has no cases.", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}")

        return embed

    @birthday.error
    @transferprofile.error
    @rundown.error
    async def info_error(self, ctx, error):
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
    bot.add_cog(ModUtils(bot))
