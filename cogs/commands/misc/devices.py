import asyncio
import json

import aiohttp
import discord
from discord import Color, Embed
from discord.ext import commands, menus
import traceback


class Source(menus.GroupByPageSource):
    async def format_page(self, menu, entry):
        embed = Embed(
            title=f'Search results: Page {menu.current_page +1}/{self.get_max_pages()}')
        for v in entry.items:
            embed.add_field(name=v[0], value=(
                v[1][:250] + '...') if len(v[1]) > 250 else v[1], inline=False)
        return embed


class NewMenuPages(menus.MenuPages):
    async def update(self, payload):
        if self._can_remove_reactions:
            if payload.event_type == 'REACTION_ADD':
                await self.message.remove_reaction(payload.emoji, payload.member)
            elif payload.event_type == 'REACTION_REMOVE':
                return
        await super().update(payload)


def setup(bot):
    bot.add_cog(Utilities(bot))


class Devices(commands.Cog):    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='board2device', aliases=['b2d'])
    async def board2device(self, ctx, board: str):
        """(alias $b2d) Retreive the brand name for a given Chromebook board name\nExample usage: `$b2d edgar`"""

        # ensure the board arg is only alphabetical chars
        if (not board.isalpha()):
            raise commands.BadArgument()

        # case insensitivity
        board = board.lower()

        # fetch data from skylar's API
        response = ""
        async with aiohttp.ClientSession() as session:
            response = await fetch(session, 'https://raw.githubusercontent.com/skylartaylor/cros-updates/master/src/data/cros-updates.json', ctx)
            if response is None:
                return

        # str -> JSON
        response = json.loads(response)
        # loop through response to find a matching board name
        for device in response:
            # if we find a match, send response
            if device["Codename"] == board:
                await ctx.send(embed=Embed(title=f'{device["Codename"]} belongs to...', color=Color(value=0x37b83b), description=device["Brand names"]).set_footer(text=f"Powered by https://cros.tech/ (by Skylar), requested by {ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.avatar_url))
                return
        
        # no match, send error response
        await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description="A board with that name was not found!"))

    # err handling
    @board2device.error
    async def b2d_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description="You need to supply a board name! Example: `$b2d coral`"))
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description="The board should only be alphabetical characters!"))
    
    @commands.command(name='device2board', aliases=['d2b'])
    async def device2board(self, ctx, *, search_term: str):
        """(alias $d2b) Retrieve the board name from a specified brand name as a search term\nExample usage: `$d2b acer chromebook 11`"""

        if search_term == "":
            await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description="You need to supply a boardname! Example: `$d2b acer chromebook`"))
            return
        pattern = re.compile("^[a-zA-Z0-9_()&,/ -]*$")

        if (not pattern.match(search_term)):
            raise commands.BadArgument("Illegal characters in search term!")

        search_term = search_term.lower()

        response = ""
        async with aiohttp.ClientSession() as session:
            response = await fetch(session, 'https://raw.githubusercontent.com/skylartaylor/cros-updates/master/src/data/cros-updates.json', ctx)
            if response is None:
                return

        devices = json.loads(response)

        search_results = [(device["Codename"], device["Brand names"])
                          for device in devices if 'Brand names' in device and search_term in device['Brand names'].lower()]
        if len(search_results) == 0:
            await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description="A board with that name was not found!"))
        else:
            pages = NewMenuPages(source=Source(
                search_results, key=lambda t: 1, per_page=8), clear_reactions_after=True)
            await pages.start(ctx)

    @commands.command(name="cros-updates", aliases=['updates'])
    @commands.guild_only()
    async def updates(self, ctx, *, board:str):
        """(alias $updates) Get ChromeOS version data for a specified Chromebook board name\nExample usage: `$updates edgar`"""
        # ensure the board arg is only alphabetical chars
        if (not board.isalpha()):
            raise commands.BadArgument()

        # case insensitivity
        board = board.lower()

        # fetch data from skylar's API
        data = ""
        async with aiohttp.ClientSession() as session:
            data = await fetch(session, 'https://raw.githubusercontent.com/skylartaylor/cros-updates/master/src/data/cros-updates.json', ctx)
            if data is None:
                return
        
        #parse response to json
        data = json.loads(data)
        # loop through response to find board
        for data_board in data:
            # did we find a match
            if data_board['Codename'] == board:
                # yes, send the data
                embed = Embed(title=f"ChromeOS update status for {board}", color=Color(value=0x37b83b))
                version = data_board["Stable"].split("<br>")
                embed.add_field(name=f'Stable Channel', value=f'**Version**: {version[1]}\n**Platform**: {version[0]}')
                
                version = data_board["Beta"].split("<br>")
                if len(version) == 2:
                    embed.add_field(name=f'Beta Channel', value=f'**Version**: {version[1]}\n**Platform**: {version[0]}')
                else:
                    embed.add_field(name=f'Beta Channel', value=f'**Version**: {data_board["Beta"]}')
                
                version = data_board["Dev"].split("<br>")
                if len(version) == 2:
                    embed.add_field(name=f'Dev Channel', value=f'**Version**: {version[1]}\n**Platform**: {version[0]}')
                else:
                    embed.add_field(name=f'Dev Channel', value=f'**Version**: {data["Dev"]}')
                
                if (data_board["Canary"] is not None):
                    version = data_board["Canary"].split("<br>")
                    if len(version) == 2:
                        embed.add_field(name=f'Canary Channel', value=f'**Version**: {version[1]}\n**Platform**: {version[0]}')
                
                embed.set_footer(text=f"Powered by https://cros.tech/ (by Skylar), requested by {ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=embed)
                return

        # board not found, error
        await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description="Couldn't find a result with that boardname!"))
        return

    # err handling
    @updates.error
    async def updates_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description="You need to supply a board name! Example: `$updates coral`"))
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description="The board should only be alphabetical characters!"))
        else:
            await ctx.send(embed=Embed(title="A fatal error occured!", color=Color(value=0xEB4634), description="Tell slim :("))
            traceback.print_exc()

    @device2board.error
    async def add_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description=f'{error}'))
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description=f'{error}'))

async def fetch(session, url, ctx):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text()
            else:
                await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description="Error connecting to the feed! Please try again later"))
                return None
    except aiohttp.ClientConnectionError:
        await ctx.send(embed=Embed(title="An error occured!", color=Color(value=0xEB4634), description="Error connecting to the feed! Please try again later"))
        return None

def setup(bot):
    bot.add_cog(Devices(bot))
