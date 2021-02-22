import traceback

import datetime
import asyncio
import discord
import typing
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
        self.user_cache = {}
        
       
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

    @commands.command(name='getkarma', aliases=["getrank"])
    async def getkarma(self, ctx, member: typing.Union[discord.Member, int]):
        """(alias $getrank) Get a user's karma\nWorks with ID if the user has left the guild\nExample usage: `$getkarma @member` or `$getkarma 2342492304928`"""

        if not ctx.guild.id == self.bot.settings.guild_id:
            return
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 1):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        karma, rank, overall = await self.bot.settings.karma_rank(member.id)

        embed = discord.Embed(
            title=f"Karma results", color=discord.Color(value=0x37b83b))
        embed.add_field(
                name="Karma", value=f'{member.mention} has {karma} karma')
        embed.add_field(
                name="Leaderboard rank", value=f'{member.mention} is rank {rank}/{overall}')
        embed.set_footer(
            text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url)

        await ctx.message.reply(embed=embed)

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

    @commands.command(name='leaderboard', aliases=["lb"])
    async def leaderboard(self, ctx):
        """(alias $lb) Karma leaderboard in current guild"""

        ctx.user_cache = self.user_cache

        class Source(menus.GroupByPageSource):
            async def format_page(self, menu, entry):
                embed = discord.Embed(
                    title=f'Leaderboard: Page {menu.current_page +1}/{self.get_max_pages()}', color=discord.Color(value=0xfcba03))
                embed.set_footer(icon_url=ctx.author.avatar_url,
                                 text="Note: Nerds and Moderators were excluded from these results.")
                embed.description = ""

                for i, user in enumerate(entry.items):
                    member = menu.ctx.guild.get_member(user._id)
                    member_found =  member is not None
                    if not member_found:
                        if user._id not in menu.ctx.user_cache:
                            try:
                                member = await menu.ctx.bot.fetch_user(user._id)
                                menu.ctx.user_cache[user._id] = member
                            except Exception:
                                member = None

                        else:
                            member = menu.ctx.user_cache[user._id]
                                                
                    embed.add_field(name=f"Rank {i+1}", value=f"{member.display_name} with {user.karma} karma", inline=False)
                    # member_string = f'{f"({str(member)})" if member is not None else ""}'
                    # embed.description += f'**Rank {i}**: *{member.display_name}* with {user.karma} karma\n'
                # pushables = []
                # for user in entry.items:
                #     member  = ctx.guild.get_member(user._id)
                #     if member and not ctx.channel.permissions_for(member).manage_messages:
                #         pushables.append(v)

                # for i, user in enumerate(pushables, start=1):
                #     member = discord.utils.get(ctx.guild.members, id=v[0])
                #     if not member:
                #         embed.description += f'**Rank {i}**: {fetch_nick(v[0])} with {user.karma} karma\n'
                #     else:
                #         embed.description += f'**Rank {i}**: {member.mention } with {v[1]} karma\n'
                return embed

        data = await self.bot.settings.leaderboard()
        
        if (len(data) == 0):
           raise commands.BadArgument("No history in this guild!")
        else:
            data_final = []
            for u in data:
                member = ctx.guild.get_member(u._id)    
                if member:
                    if not member.guild_permissions.manage_messages:
                        data_final.append(u)
                else:
                    data_final.append(u)
                    
            pages = NewMenuPages(source=Source(
                data_final, key=lambda t: 1, per_page=10), clear_reactions_after=True)
            await pages.start(ctx)

    @leaderboard.error
    @history.error
    @getkarma.error
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
