import asyncio

import discord
import feedparser
from discord.ext import commands

bott = None


class DealWatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
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

    # the watcher thread
    async def watcher(self, feed):
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
                await self.check_new_entries(feed, new_posts)

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
            await self.check_new_entries(feed, new_posts)
        feed["prev_data"] = data

    async def check_new_entries(self, feed, entries):
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

    async def push_update(self, post, feed):
        guild_id = self.bot.settings.guild_id
        channel = self.bot.get_guild(guild_id).get_channel(self.bot.settings.guild().channel_deals)
        role = self.bot.get_guild(guild_id).get_role(self.bot.settings.guild().role_deals)
        await channel.send(f'{role.mention} New deal was posted!\n{post.title}\n{post.link}', allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=True))


def setup(bot):
    dw = DealWatcher(bot)
    bot.add_cog(dw)
