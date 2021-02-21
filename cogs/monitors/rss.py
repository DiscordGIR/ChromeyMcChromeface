import asyncio
import os

import discord
import feedparser
from discord import Color, Embed
from discord.ext import commands


class CrosBlog(commands.Cog):
    """Watch Google's release feed to watch for new ChromeOS updates. Send to Discord channel if found."""

    def __init__(self, bot):
        self.bot = bot
        self.url = "http://feeds.feedburner.com/GoogleChromeReleases"
        self.prev_data = feedparser.parse(self.url)

        # create thread for loop which watches feed
        self.loop = asyncio.get_event_loop().create_task(self.watcher())
# all the feeds we need to watch
        self.feeds = [
            {
                'feed': "https://www.aboutchromebooks.com/feed/",
                'name': "AboutChromebooks.com",
                'profilePicture':
                    "https://cdn.discordapp.com/emojis/363434654000349184.png?v=1",
                'filters': ["deal", "deals"],
                'requiredFilters': [],
                'good_feed': False,
                'prev_data': feedparser.parse('https://www.aboutchromebooks.com/feed/')
            },
            {
                'feed': "https://www.androidpolice.com/feed/",
                'name': "AndroidPolice.com",
                'profilePicture':
                    "https://lh4.googleusercontent.com/-2lq9WcxRgB0/AAAAAAAAAAI/AAAAAAAAAQk/u15SBRi49fE/s250-c-k/photo.jpg",
                'filters': ["deal", "deals", "sale", "sales"],
                'requiredFilters': ["chromebook", "chromebooks", "chromeos", "chrome os"],
                'good_feed': True,
                'prev_data': feedparser.parse('https://www.androidpolice.com/feed/')

            },
            {
                'feed': "https://www.androidauthority.com/feed/",
                'name': "AndroidAuthority.com",
                'profilePicture':
                    "https://images-na.ssl-images-amazon.com/images/I/51L8Vd5bndL._SY355_.png",
                'filters': ["deal", "deals", "sale", "sales"],
                'requiredFilters': ["chromebook", "chromebooks", "chromeos", "chrome os" "google chrome os"],
                'good_feed': True,
                'prev_data': feedparser.parse('https://www.androidauthority.com/feed/')
            }
        ]

        # create watcher thread for all feeds, store in dict to cancel if needed
        self.loops = {}
        for feed in self.feeds:
            self.loops[feed["name"]] = asyncio.get_event_loop(
            ).create_task(self.watcher(feed))

    # before unloading cog, stop all watcher threads
    def cog_unload(self):
        [self.loops[loop].cancel() for loop in self.loops.keys()]
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

    # the watcher thread
    async def watcher_deal(self, feed):
        # wait for bot to start
        await self.bot.wait_until_ready()
        # is this thread still supposed to be running?
        while not self.loops[feed["name"]].cancelled():
            # handle feeds with/without HTTP last-modified support differently
            if feed['good_feed'] is True:
                await self.good_feed(feed)
            else:
                await self.bad_feed(feed)

            # loop every 60 seconds
            await asyncio.sleep(60)

    # feed watcher for feeds with proper etag support

    async def good_feed(self, feed):
        # determine args (from cached data)
        kwargs = dict(modified=feed["prev_data"].modified if hasattr(feed["prev_data"], 'modified')
                      else None, etag=feed["prev_data"].etag if hasattr(feed["prev_data"], 'modified') else None)
        # fetch feed data w/ args
        data = feedparser.parse(
            feed["feed"], **{k: v for k, v in kwargs.items() if v is not None})

        # has the feed changed?
        if (data.status != 304):
            # get newest post date from cached data. any new post will have a date newer than this
            max_prev_date = max([something["published_parsed"]
                                 for something in feed["prev_data"].entries])
            # get new posts
            new_posts = [
                post for post in data.entries if post["published_parsed"] > max_prev_date]
            # if there rae new posts
            if (len(new_posts) > 0):
                # check thier tags
                for post in new_posts:
                    print(f'NEW GOOD ENTRY: {post.title} {post.link}')
                await self.check_new_entries_deals(feed, new_posts)

        feed["prev_data"] = data

    # improper etag support
    async def bad_feed(self, feed):
        # fetch feed data
        data = feedparser.parse(feed["feed"])
        # get newest post date from cached data. any new post will have a date newer than this
        max_prev_date = max([something["published_parsed"]
                             for something in feed["prev_data"].entries])
        # get new posts
        new_posts = [
            post for post in data.entries if post["published_parsed"] > max_prev_date]
        # if there rae new posts
        if (len(new_posts) > 0):
            # check thier tags
            for post in new_posts:
                print(f'NEW BAD ENTRY: {post.title} {post.link}')
            await self.check_new_entries_deals(feed, new_posts)
        feed["prev_data"] = data

    async def check_new_entries_deals(self, feed, entries):
        # loop through new entries to see if tags contain one that we want
        # if we find match, post update in channel
        for entry in entries:
            post_tags = [tag.term.lower() for tag in entry.tags]
            if len(feed["requiredFilters"]) != 0:
                match = [tag for tag in feed["filters"] if tag in post_tags]
                match_required = [
                    tag for tag in feed["requiredFilters"] if tag in post_tags]
                if (len(match) > 0 and len(match_required) > 0):
                    print(
                        f'MATCH FOUND DEAL {entry.title}, {entry.link}, {entry.tags}')
                    await self.push_update(entry, feed)
            else:
                match = [tag for tag in feed["filters"] if tag in post_tags]
                if (len(match) > 0):
                    print(
                        f'MATCH FOUND DEAL {entry.title}, {entry.link}, {entry.tags}')
                    await self.push_update(entry, feed)

    async def push_update_deals(self, post, feed):
        guild_id = self.bot.settings.guild_id
        channel = self.bot.get_guild(guild_id).get_channel(self.bot.settings.guild().channel_deals)
        role = self.bot.get_guild(guild_id).get_role(self.bot.settings.guild().role_deals)
        await (channel.send(f'{role.mention} New deal was posted!\n{post.title}\n{post.link}'))


def setup(bot):
    bot.add_cog(CrosBlog(bot))
