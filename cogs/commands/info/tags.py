import random
import re
import traceback
from io import BytesIO

import aiohttp
import cogs.utils.context as context
import cogs.utils.permission_checks as permissions
import discord
from data.tag import Tag
from discord.ext import commands, menus


class TagsSource(menus.GroupByPageSource):
    async def format_page(self, menu, entry):
        embed = discord.Embed(title=f'Commands: Page {menu.current_page +1}/{self.get_max_pages()}', color=discord.Color.blurple())
        for tag in entry.items:
            res = tag.content[:50] + "..." if len(tag.content) > 50 else tag.content
            argo = " [args]" if tag.args else ""
            if (argo != ""):
                res += argo
            embed.add_field(name=f'!t {tag.name}{argo}', value=f'**ID**: {tag._id}\n**Supports arguments**: {tag.args}\n**Creator**: {tag.added_by_tag}\n**Number of uses**: {tag.use_count}')
        return embed


class MenuPages(menus.MenuPages):
    async def update(self, payload):
        if self._can_remove_reactions:
            if payload.event_type == 'REACTION_ADD':
                await self.message.remove_reaction(payload.emoji, payload.member)
            elif payload.event_type == 'REACTION_REMOVE':
                return
        await super().update(payload)


class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @permissions.nerds_and_up()
    @commands.command(name="addtag", aliases=['addt'])
    async def addtag(self, ctx: context.Context, name: str, args: bool, *, content: str) -> None:
        """Add a tag. Optionally attach an iamge. (Nerds and up)

        Example usage
        -------------
        !addtag chromeos false This is the content

        Parameters
        ----------
        name : str
            "Name of the tag"
        content : str
            "Content of the tag"
        """

        pattern = re.compile("^[a-zA-Z0-9_-]*$")
        if (not pattern.match(name)):
            raise commands.BadArgument("The command name should only be alphanumeric characters with `_` and `-`!")
        
        prev_tag = await ctx.settings.get_tag_by_name(name.lower(), args)
        if prev_tag is not None:
            raise commands.BadArgument("Tag with that name already exists.")

        tag = Tag()
        tag._id = random.randint(0, 10000000)
        tag.name = name.lower()
        tag.content = content
        tag.args = args
        tag.added_by_id = ctx.author.id
        tag.added_by_tag = str(ctx.author)
        
        if len(ctx.message.attachments) > 0:
            # ensure the attached file is an image
            image = ctx.message.attachments[0]
            _type = image.content_type
            if _type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")
            else:
                image = await image.read()
            # save image bytes
            tag.image.put(image, content_type=_type)

        await ctx.settings.add_tag(tag)

        await ctx.message.reply(f"Added new tag!")

    async def tag_response(self, tag, args):
        pattern = re.compile(r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*")
        if (pattern.match(tag.content)):
            response = tag.content + "%20".join(args.split(" "))
        else:
            response = tag.content + " " + args
        return response

    @commands.guild_only()
    @permissions.offtopic_only_unless_nerd()
    @commands.command(name="taglist", aliases=['tlist'])
    async def taglist(self, ctx):
        """List all tags
        """

        tags = sorted(ctx.settings.guild().tags, key=lambda tag: tag.name)

        if len(tags) == 0:
            raise commands.BadArgument("There are no tags defined.")
        
        menus = MenuPages(source=TagsSource(
            tags, key=lambda t: 1, per_page=12), clear_reactions_after=True)

        await menus.start(ctx)

    @commands.guild_only()
    @permissions.nerds_and_up()
    @commands.command(name="deltag", aliases=['dtag'])
    async def deltag(self, ctx: context.Context, _id: int):
        """Delete tag (Nerds and up)

        Example usage
        --------------
        !deltag <tag ID>

        Parameters
        ----------
        name : str
            "Name of tag to delete"

        """

        tag = await ctx.settings.get_tag(_id)
        if tag is None:
            raise commands.BadArgument("That tag does not exist.")

        await ctx.settings.remove_tag(_id)
        await ctx.message.reply("Deleted.")

    @commands.guild_only()
    @commands.command(name="tag", aliases=['t'])
    async def tag(self, ctx: context.Context, name: str, *, args = ""):
        """Use a tag with a given name.
        
        Example usage
        -------------
        !t roblox

        Parameters
        ----------
        name : str
            "Name of tag to use"
        """

        name = name.lower()
        tag = await ctx.settings.get_tag_by_name(name, args != "")
        
        if tag is None:
            raise commands.BadArgument("That tag does not exist.")
        
        file = tag.image.read()
        if file is not None:
            file = discord.File(BytesIO(file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")
        response = await self.tag_response(tag, args)
        await ctx.message.reply(response, file=file, mention_author=False)

    @commands.command(name='search')
    async def search(self, ctx: context.Context, command_name:str):
        """Search through commands for matching name by keyword
        
        Example usage
        --------------
        !search cros
        """
        
        # ensure command name doesn't have illegal chars
        pattern = re.compile("^[a-zA-Z0-9_-]*$")
        if (not pattern.match(command_name)):
            raise commands.BadArgument("The command name should only be alphanumeric characters with `_` and `-`!\nExample usage`!search cam-sucks`")
            
        # always store command name as lowercase for case insensitivity
        command_name = command_name.lower()

        res = sorted(ctx.settings.guild().tags, key=lambda tag: tag.name)
        match = [ command for command in res if command_name in command.name ]

        if len(match) == 0:
            raise commands.BadArgument(f'No commands found with that name!')
        #send paginated results
        pages = MenuPages(source=TagsSource(match, key=lambda t: 1, per_page=6), clear_reactions_after=True)
        await pages.start(ctx)

    @tag.error
    @taglist.error
    @deltag.error
    @addtag.error
    async def info_error(self, ctx: context.Context, error):
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(ctx, error)
        else:
            await ctx.send_error(ctx, "A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


def setup(bot):
    bot.add_cog(Tags(bot))
