import asyncio
import datetime
import traceback

import cogs.utils.context as context
import cogs.utils.permission_checks as permissions
import discord
from discord.ext import commands


class Nerd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot        
       
    @commands.guild_only()
    @permissions.nerds_and_up()
    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    @commands.command(name="postembed")
    async def postembed(self, ctx: context.Context, *, title: str):
        """Post an embed in the current channel (nerds and up)

        Example use:
        ------------
        !postembed This is a title (you will be prompted for a description)

        Parameters
        ----------
        title : str
            "Title for the embed"
        
        """

        if not ctx.guild.id == ctx.settings.guild_id:
            return
        
        # prompt user for body of embed
        prompt = context.PromptData(
            value_name="description",
            description="Please enter a description for this embed.",
            convertor=str)
        description = await ctx.prompt(prompt)
        
        if description is None:
            await ctx.message.delete(delay=5)
            await ctx.send_warning("Cancelled embed post.", delete_after=5)
            return

        embed, f = await self.prepare_issues_embed(title, description, ctx.message)
        await ctx.channel.send(embed=embed, file=f)
        await ctx.message.delete()

    async def prepare_issues_embed(self, title, description, message):
        embed = discord.Embed(title=title)
        embed.color = discord.Color.random()
        embed.description = description
        f = None
        if len(message.attachments) > 0:
            f = await message.attachments[0].to_file()
            embed.set_image(url=f"attachment://{f.filename}")
        embed.set_footer(text=f"Submitted by {message.author}")
        embed.timestamp = datetime.datetime.now()
        return embed, f

    @commands.guild_only()
    @permissions.mods_and_up()
    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    @commands.command(name="say")
    async def say(self, ctx: context.Context, *, message: str):
        """Post an embed in the current channel (nerds and up)

        Example use:
        ------------
        !postembed This is a title (you will be prompted for a description)

        Parameters
        ----------
        title : str
            "Title for the embed"
        
        """

        await ctx.message.delete()
        await ctx.send(message)

    @permissions.nerds_and_up()
    @commands.command(name='rules')
    async def rules(self, ctx: context.Context, member: discord.Member):
        """Put user on timeout to read rules (nerds and up)
        
        Example usage
        --------------
        !rules @SlimShadyIAm#9999

        Parameters
        ----------
        member : discord.Member
            "user to time out"
        """

        if member.id == ctx.author.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on yourself.")
        if member.id == self.bot.user.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on me :(")

        role = ctx.guild.get_role(ctx.settings.guild().role_rules)
        
        if (role is None):
            raise commands.BadArgument('rules role not found!')

        try:
            ctx.tasks.schedule_unrules(member.id, datetime.datetime.now() + datetime.timedelta(minutes=15))
        except Exception:
            raise commands.BadArgument("This user is probably already on timeout.")
        
        embed = discord.Embed(title="You have been put in timeout.", color=discord.Color(value=0xebde34), description=f'{ctx.author.name} thinks you need to review the rules. You\'ve been placed on timeout for 15 minutes. During this time, you won\'t be able to interact with the server').set_footer(text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url)
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            channel = ctx.guild.get_channel(ctx.settings.guild().channel_offtopic)
            await channel.send(f'{member.mention} I tried to DM this to you, but your DMs are closed! You\'ll be timed out in 10 seconds.', embed=embed)
            await asyncio.sleep(10)
        
        await member.add_roles(role)
        
        await ctx.message.reply(embed=discord.Embed(title="Done!", color=discord.Color(value=0x37b83b), description=f'Gave {member.mention} the rules role. We\'ll let them know and remove it in 15 minutes.').set_footer(text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url))

    @permissions.nerds_and_up()
    @commands.command(name='timeout')
    async def timeout(self, ctx: context.Context, member: discord.Member):
        """Put user on timeout (nerds and up)
        
        Example usage
        --------------
        !timeout @SlimShadyIAm#9999

        Parameters
        ----------
        member : discord.Member
            "user to time out"
        """
        
        if member.id == ctx.author.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on yourself.")
        if member.id == self.bot.user.id:
            await ctx.message.add_reaction("🤔")
            raise commands.BadArgument("You can't call that on me :(")

        role = ctx.guild.get_role(ctx.settings.guild().role_timeout)
        
        if (role is None):
            raise commands.BadArgument('timeout role not found!')

        try:
            ctx.settings.tasks.schedule_untimeout(member.id, datetime.datetime.now() + datetime.timedelta(minutes=15))
        except Exception:
            raise commands.BadArgument("This user is probably already on timeout.")
        
        embed = discord.Embed(title="You have been put in timeout.", color=discord.Color(value=0xebde34), description=f'{ctx.author.name} gave you the timeout role. We\'ll remove it in 15 minutes. Please read the message in the timeout channel and review the rules.').set_footer(text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url)
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            channel = ctx.guild.get_channel(ctx.settings.guild().channel_offtopic)
            await channel.send(f'{member.mention} I tried to DM this to you, but your DMs are closed! You\'ll be timed out in 10 seconds.', embed=embed)
            await asyncio.sleep(10)
        
        await member.add_roles(role)
        
        await ctx.message.reply(embed=discord.Embed(title="Done!", color=discord.Color(value=0x37b83b), description=f'Gave {member.mention} the timeout role. We\'ll let them know and remove it in 15 minutes.').set_footer(text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url))
        
    @permissions.nerds_and_up()
    @commands.command(name="poll")
    async def poll(self, ctx: context.Context, *, content: str):
        """Create a poll (Nerds and up)
        
        Example usage
        --------------
        !poll are u good?

        Parameters
        ----------
        content : str
            "Description"
        """

        embed = discord.Embed(title="New poll!", description=content, color=discord.Color.blurple())
        msg = await ctx.message.reply(embed=embed)
        
        await msg.add_reaction('👍')
        await msg.add_reaction('👎')
    
    @rules.error
    @say.error
    @poll.error
    @timeout.error
    @postembed.error
    async def info_error(self, ctx: context.Context, error):
        await ctx.message.delete(delay=5)
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(ctx, error)
        else:
            await ctx.send_error(ctx, "A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


def setup(bot):
    bot.add_cog(Nerd(bot))
