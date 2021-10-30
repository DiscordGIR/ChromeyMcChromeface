import asyncio
import os

import mongoengine
from dotenv import find_dotenv, load_dotenv

from data.guild import Guild

load_dotenv(find_dotenv())

async def setup():
    print("STARTING SETUP...")
    guild = Guild()
    
    # you should have this setup in the .env file beforehand
    guild._id          = int(os.environ.get("CHROMEY_MAINGUILD"))
    
    guild.case_id      = 20
    
    guild.role_birthday      = 849926088187445269  # put in the role IDs for your server here
    guild.role_nerds         = 849926088179449909  # put in the role IDs for your server here
    guild.role_moderator     = 849926088179449914  # put in the role IDs for your server here
    guild.role_mute          = 849926088179449908  # put in the role IDs for your server here
    guild.role_helpers       = 849926088162803757
    guild.role_rules         = 849926087768670213
    guild.role_timeout       = 849926088179449907

    
    guild.channel_offtopic       = 849926088633090061  # put in the channel IDs for your server here
    guild.channel_private        = 849926088779366406  # put in the channel IDs for your server here
    guild.channel_reaction_roles = 849926088494546955  # put in the channel IDs for your server here
    guild.channel_reports        = 849926088779366405  # put in the channel IDs for your server here
    guild.channel_support        = 849926088494546962  # put in the channel IDs for your server here
    guild.channel_deals          = 849926949215797278  # put in the channel IDs for your server here
    guild.channel_modlogs        = 849926088779366407  # put in the channel IDs for your server here
    
    guild.logging_excluded_channels = []  # put in a channel if you want (ignored in logging)
    guild.filter_excluded_channels  = []  # put in a channel if you want (ignored in filter)
    guild.filter_excluded_guilds    = []  # put guild ID to whitelist in invite filter if you want
    guild.save()

    print("DONE")

if __name__ == "__main__":
        mongoengine.register_connection(alias="default", name="chromey")
        res = asyncio.get_event_loop().run_until_complete( setup() )
