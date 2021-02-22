import traceback

import datetime
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


class Karma(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_cache = {}
        
    @commands.group()
    async def karma(self, ctx):
        """
        Karma commands. Usage: !karma <subcommand> from below...
        
        Valid subcommands:
        ------------------
        get, set, give, take, history, modhistory
        """
        if ctx.invoked_subcommand is None:
            raise commands.BadArgument("Invalid subcommand passed. Valid subcommands: get, set, give, take, history, modhistory")
   
    @karma.command()
    async def get(self, ctx, member: typing.Union[discord.Member, int]):
        """Get a user's karma 
        
        Example usage:
        ---------------
        `!karma get @member` or `!karma get 2342492304928`

        Parameters
        ----------
        member : typing.Union[discord.Member, int]
            Member whose karma to get
        """
        

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

    @karma.command()
    async def set(self, ctx, member: discord.Member, val: int):
        """Force set a user's karma (mod only)
        
        Example Usage:
        --------------
        `!karma set @user 100`

        Parameters
        ----------
        member : discord.Member
            Member whose karma to set
        val : int
            Karma value
        """

        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 2):
            raise commands.BadArgument(
                "You do not have permission to use this command.")
            
        m = await self.bot.settings.user(member.id)
        m.karma = val
        m.save()
        
        embed = discord.Embed(title=f"Updated {member}'s karma!",
                      color=discord.Color(value=0x37b83b))
        embed.description = ""
        embed.description += f'**Current karma**: {m.karma}\n'
        embed.set_footer(
            text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url)
        await ctx.message.reply(embed=embed)
            
    @karma.command()
    async def give(self, ctx, member: discord.Member, val: int, *, reason: str = "No reason."):
        """ Give up to 3 karma to a user. Optionally, you can include a reason as an argument.
        
        Example usage:
        --------------
        `!karma give @member 3 reason blah blah blah`


        Parameters
        ----------
        member : discord.Member
            User to give karma to 
        val : int
            Amount of karma
        reason : str, optional
            Reason, by default "No reason."
        """
        
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 1):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        if val < 1 or val > 3:
            raise commands.BadArgument(
                "You can give 1-3 karma in a command!\nExample usage: `!karma give @member 3 reason blah blah blah`")

        if member.bot:
            raise commands.BadArgument(
                "You can't give a bot karma")

        if member.id == ctx.author.id and member.id != self.bot.owner_id:
            raise commands.BadArgument(
                "You can't give yourself karma")
        
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

        embed.description += f'**Karma given**: {val}\n'
        embed.description += f'**Current karma**: {receiver.karma}\n'
        embed.description += f'**Reason**: {reason}'
        embed.set_footer(
            text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url)
        await ctx.message.reply(embed=embed)

    @karma.command()
    async def take(self, ctx, member: discord.Member, val: int, *, reason: str = "No reason."):
        """ Take up to 3 karma from a user. Optionally, you can include a reason as an argument.
        
        Example usage:
        --------------
        `!karma take @member 3 reason blah blah blah`


        Parameters
        ----------
        member : discord.Member
            User take karma from 
        val : int
            Amount of karma
        reason : str, optional
            Reason, by default "No reason."
        """
        
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 1):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        if val < 1 or val > 3:
            raise commands.BadArgument(
                "You can give 1-3 karma in a command!\nExample usage: `!karma give @member 3 reason blah blah blah`")

        if member.bot:
            raise commands.BadArgument(
                "You can't give a bot karma")

        if member.id == ctx.author.id and member.id != self.bot.owner_id:
            raise commands.BadArgument(
                "You can't give yourself karma")
        
        val = (-1) * val
        
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

        embed.description += f'**Karma taken**: {(-1) * val}\n'
        embed.description += f'**Current karma**: {receiver.karma}\n'
        embed.description += f'**Reason**: {reason}'
        embed.set_footer(
            text=f'Requested by {ctx.author.name}#{ctx.author.discriminator}', icon_url=ctx.author.avatar_url)
        await ctx.message.reply(embed=embed)

    @karma.command()
    async def history(self, ctx, member: discord.Member):
        """History of a specific user's karma
        
        Example usage:
        --------------
        `!karma history @member`

        Parameters
        ----------
        member : discord.Member
            Member whose karma history to get
        """
        
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
        
    @karma.command()
    async def modhistory(self, ctx, member: discord.Member = None):
        """History of a karma given by a user
        
        Example usage:
        --------------
        `!karma modhistory @member`

        Parameters
        ----------
        member : discord.Member
            Member whose karma history to get
        """

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

    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx):
        """Get karma leaderboard for the server
        """

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
                                                
                    embed.add_field(name=f"Rank {i+1}", value=f"{member.mention} ({member})\n{user.karma} karma", inline=False)

                return embed

        data = await self.bot.settings.leaderboard()
        
        if (len(data) == 0):
           raise commands.BadArgument("No history in this guild!")
        else:
            data_final = []
            for u in data:
                member = ctx.guild.get_member(u._id)    
                if member:
                    if not self.bot.settings.permissions.hasAtLeast(member.guild, member, 1):
                        data_final.append(u)
                else:
                    data_final.append(u)
                    
            pages = NewMenuPages(source=Source(
                data_final, key=lambda t: 1, per_page=10), clear_reactions_after=True)
            await pages.start(ctx)
  
    @karma.error
    @get.error
    @set.error
    @give.error
    @take.error
    @leaderboard.error
    @history.error
    @modhistory.error 
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
    bot.add_cog(Karma(bot))
