import traceback

import datetime
import asyncio
import discord
from discord.ext import commands


class Nerd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot        
       
    @commands.command(name="postembed")
    @commands.guild_only()
    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    async def postembed(self, ctx, *, title: str):
        """Post an embed in the current channel (Nerds only)

        Example use:
        ------------
        !postembed This is a title (you will be prompted for a description)

        Parameters
        ----------
        title : str
            Title for the embed
        
        """

        if not ctx.guild.id == self.bot.settings.guild_id:
            return
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 1):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        channel = ctx.channel
        description = None

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        while True:
            prompt = await ctx.message.reply(f"Please enter a description for this embed (or cancel to cancel)")
            try:
                desc = await self.bot.wait_for('message', check=check, timeout=120)
            except asyncio.TimeoutError:
                return
            else:
                await desc.delete()
                await prompt.delete()
                if desc.content.lower() == "cancel":
                    return
                elif desc.content is not None and desc.content != "":
                    description = desc.content
                    break

        embed, f = await self.prepare_issues_embed(title, description, ctx.message)
        await channel.send(embed=embed, file=f)

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

    @commands.command(name='rules')
    async def rules(self, ctx, member: discord.Member):
        """Put user on timeout to read rules\nExample usage: `$rules @SlimShadyIAm#9999`"""
        
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 1):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        role = ctx.guild.get_role(self.bot.settings.guild().role_rules)
        
        if (role is None):
            raise commands.BadArgument('rules role not found!')

        try:
            self.bot.settings.tasks.schedule_untimeout(member.id, datetime.datetime.now() + datetime.timedelta(minutes=15))
        except Exception:
            raise commands.BadArgument("This user is probably already on timeout.")
        
        embed = discord.Embed(title="You have been put in timeout.", color=discord.Color(value=0xebde34), description=f'{ctx.author.name} thinks you need to review the rules. You\'ve been placed on timeout for 15 minutes. During this time, you won\'t be able to interact with the server').set_footer(text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url)
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            channel = ctx.guild.get_channel(self.bot.settings.guild().channel_botspam)
            await channel.send(f'{member.mention} I tried to DM this to you, but your DMs are closed! You\'ll be timed out in 10 seconds.', embed=embed)
            await asyncio.sleep(10)
        
        await member.add_roles(role)
        
        await ctx.message.reply(embed=discord.Embed(title="Done!", color=discord.Color(value=0x37b83b), description=f'Gave <@{member.id}> the rules role. We\'ll let them know and remove it in 15 minutes.').set_footer(text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url))
        
    @rules.error
    @postembed.error
    async def info_error(self, ctx, error):
        await ctx.message.delete(delay=5)
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
                or isinstance(error, commands.NoPrivateMessage)):
            await self.bot.send_error(ctx, error)
        else:
            await self.bot.send_error(ctx, "A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


def setup(bot):
    bot.add_cog(Nerd(bot))
