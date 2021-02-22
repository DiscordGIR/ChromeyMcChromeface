import asyncio

import discord
import feedparser
from discord.ext import commands


class CrosBlog(commands.Cog):
    """Watch Google's release feed to watch for new ChromeOS updates. Send to Discord channel if found."""

    def __init__(self, bot):
        self.bot = bot
        self.url = "http://feeds.feedburner.com/GoogleChromeReleases"
        self.prev_data = feedparser.parse(self.url)

        # create thread for loop which watches feed
        self.loop = asyncio.get_event_loop().create_task(self.watcher())

    # cancel loop when unloading cog
    def cog_unload(self):
        self.loop.cancel()

    # the watcher thread
    async def watcher(self):
        # wait for bot to start
        await self.bot.wait_until_ready()
        while not self.loop.cancelled():

            """ This commented out code doesn't work for feeds that don't support etag/last-modified headers :(
            # get args for parser -- if feed has modified and etag support, use those as parameters
            # we use modified and etag data from previous iteration to see if anything changed
            # between now and the last time we checked the feed
            kwargs = dict(modified=self.prev_data.modified if hasattr(self.prev_data, 'modified') else None, etag=self.prev_data.etag if hasattr(self.prev_data, 'modified')  else None)
            data = feedparser.parse(self.url, **{k: v for k, v in kwargs.items() if v is not None})

            # has the feed changed?
            if (data.status != 304):
                # yes, check the new entries to see if any are what we want
                await self.check_new_entries(data.entries)
            # update local cache to compare against in next iteration
            # """

            # fetch feed posts
            data = feedparser.parse(self.url)
            # determine the newest post date from the cached posts
            max_prev_date = max([something["published_parsed"]
                                 for something in self.prev_data.entries])
            # get a list of posts from the new posts where the date is newer than the max_prev_date
            new_posts = [
                post for post in data.entries if post["published_parsed"] > max_prev_date]
            # new posts?
            if (len(new_posts) > 0):
                # check each new post for matching tags
                for post in new_posts:
                    print(f'NEW BLOG ENTRY: {post.title} {post.link}')
                await self.check_new_entries(new_posts)

            # update local cache
            self.prev_data = data
            # wait 1 minute before checking feed again
            await asyncio.sleep(60)

    async def check_new_entries(self, posts):
        # loop through new entries to see if tags contain one that we want
        # if we find match, post update in channel
        print(posts)
        for post in posts:
            tags = [thing["term"] for thing in post["tags"]]
            if "Chrome OS" in tags:
                if "Stable updates" in tags:
                    await self.push_update(post, "Stable Channel")
                elif "Beta updates" in tags:
                    await self.push_update(post, "Beta Channel")
                elif "Dev updates" in tags:
                    await self.push_update(post, "Dev Channel")
                elif "Canary updates" in tags:
                    await self.push_update(post, "Canary Channel")
        pass

    async def push_update(self, post, category=None):
        # which guild to post to depending on if we're prod or dev
        # post update to channel
        guild_id = self.bot.settings.guild_id
        guild_roles = self.bot.get_guild(guild_id).roles
        channel = self.bot.get_guild(guild_id).get_channel(self.bot.settings.guild().channel_deals)
        if (category is None):
            await (channel.send(f'New blog was posted!\n{post.title}\n{post.link}'))
        else:
            role = discord.utils.get(guild_roles, name=category)
            if role:
                await (channel.send(f'{role.mention} New blog was posted for {category}!\n{post.title}\n{post.link}'))



def setup(bot):
    bot.add_cog(CrosBlog(bot))
