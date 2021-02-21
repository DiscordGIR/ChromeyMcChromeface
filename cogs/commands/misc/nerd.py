import traceback

import datetime
import asyncio
import discord
import humanize
from discord.ext import commands, menus


class NewMenuPages(menus.MenuPages):
    async def update(self, payload):
        if self._can_remove_reactions:
            if payload.event_type == 'REACTION_ADD':
                await self.message.remove_reaction(payload.emoji, payload.member)
            elif payload.event_type == 'REACTION_REMOVE':
                return
        await super().update(payload)


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

    @commands.command(name='karma')
    async def karma(self, ctx, action: str, member: discord.Member, val: int, *, reason: str = "No reason."):
        """Give or take karma from a user.\nYou may give or take up to 3 karma in a single command.\nOptionally, you can include a reason as an argument.\nExample usage: `$karma give @member 3 reason blah blah blah` or `$karma take <ID> 3`"""
        # print(reason)
        # if reason is not None:
        #     pattern = re.compile(r"^[a-zA-Z0-9\s_-]*$")
        #     if (not pattern.match(reason)):
        #         raise commands.BadArgument(
        #             "The reason should only be alphanumeric characters with `_` and `-`!\nExample usage:`$karma give @member 3 reason blah blah blah` or `$karma take <ID> 3`")

        if not ctx.guild.id == self.bot.settings.guild_id:
            return
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 1):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        action = action.lower()
        if action != "give" and action != "take":
            raise commands.BadArgument(
                "The action should be either \"give\" or \"take\"\nExample usage: `$karma give @member 3 reason blah blah blah` or `$karma take <ID> 3`")

        if val < 1 or val > 3:
            raise commands.BadArgument(
                "You can give or take 1-3 karma in a command!\nExample usage: `$karma give @member 3 reason blah blah blah` or `$karma take <ID> 3`")

        if member.bot:
            raise commands.BadArgument(
                "You can't give a bot karma")

        if member.id == ctx.author.id and member.id != self.bot.owner_id:
            raise commands.BadArgument(
                "You can't give yourself karma")

        if action == "take":
            val = -1 * val
        
        receiver = await self.bot.settings.user(member.id)
        receive_action = {
            "amount": val,
            "from": ctx.author.id,
            "date": datetime.datetime.now(),
            "reason": reason
        }
        receiver.karma += val
        receiver.karma_received_history.append(receive_action)
        receiver.save()
        
        giver = await self.bot.settings.user(ctx.author.id)
        give_action = {
            "amount": val,
            "to": member.id,
            "date": datetime.datetime.now(),
            "reason": reason
        }
        giver.karma_given_history.append(give_action)
        giver.save()
        
        embed = discord.Embed(title=f"Updated {member.name}#{member.discriminator}'s karma!",
                      color=discord.Color(value=0x37b83b))
        embed.description = ""
        if val < 0:
            embed.description += f'**Karma taken**: {-1 * val}\n'
        else:
            embed.description += f'**Karma given**: {val}\n'
        embed.description += f'**Current karma**: {receiver.karma}\n'
        embed.description += f'**Reason**: {reason}'
        embed.set_footer(
            text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url)
        await ctx.message.reply(embed=embed)

    @commands.command(name='history')
    async def history(self, ctx, member: discord.Member = None):
        """History of all karma, or a specific user's karma\nExample usage: `$history` or `$history @member`"""

        if not ctx.guild.id == self.bot.settings.guild_id:
            return
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 1):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        class Source(menus.GroupByPageSource):
            async def format_page(self, menu, entry):
                embed = discord.Embed(
                    title=f'History: Page {menu.current_page +1}/{self.get_max_pages()}', color=discord.Color(value=0xfcba03))
                for v in entry.items:
                    invoker_text = f"<@{v['from']}>"
                    
                    if v["amount"] < 0:
                        embed.add_field(
                            name=f'{humanize.naturaltime(v["date"])}', value=f'{invoker_text} took {v["amount"]} karma from {member.mention}\n**Reason**: {v["reason"]}', inline=False)
                    else:
                        embed.add_field(
                            name=f'{humanize.naturaltime(v["date"])}', value=f'{invoker_text} gave {v["amount"]} karma to {member.mention}\n**Reason**: {v["reason"]}', inline=False)
                return embed
        
        data = sorted((await self.bot.settings.user(member.id)).karma_received_history, key=lambda d: d['date'], reverse=True)
        
        if (len(data) == 0):
            raise commands.BadArgument("This user had no history.")
       
        pages = NewMenuPages(source=Source(
            data, key=lambda t: 1, per_page=10), clear_reactions_after=True)
        await pages.start(ctx)
        
    @commands.command(name='modhistory')
    async def modhistory(self, ctx, member: discord.Member = None):
        """History of all karma, or a specific user's karma\nExample usage: `$history` or `$history @member`"""

        if not ctx.guild.id == self.bot.settings.guild_id:
            return
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 1):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        class Source(menus.GroupByPageSource):
            async def format_page(self, menu, entry):
                embed = discord.Embed(
                    title=f'History: Page {menu.current_page +1}/{self.get_max_pages()}', color=discord.Color(value=0xfcba03))
                for v in entry.items:
                    target = f"<@{v['to']}>"
                    
                    if v["amount"] < 0:
                        embed.add_field(
                            name=f'{humanize.naturaltime(v["date"])}', value=f'{member.mention} took {v["amount"]} karma from {target}\n**Reason**: {v["reason"]}', inline=False)
                    else:
                        embed.add_field(
                            name=f'{humanize.naturaltime(v["date"])}', value=f'{member.mention} gave {v["amount"]} karma to {target}\n**Reason**: {v["reason"]}', inline=False)
                return embed
        
        data = sorted((await self.bot.settings.user(member.id)).karma_given_history, key=lambda d: d['date'], reverse=True)
        
        if (len(data) == 0):
            raise commands.BadArgument("This user had no history.")
       
        pages = NewMenuPages(source=Source(
            data, key=lambda t: 1, per_page=10), clear_reactions_after=True)
        await pages.start(ctx)


    @history.error
    @modhistory.error
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
