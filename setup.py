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
    
    guild.case_id      = 1
    
    guild.role_birthday      = 789655854466596904  # put in the role IDs for your server here
    guild.role_nerd          = 777270163589693482  # put in the role IDs for your server here
    guild.role_moderator     = 777270257772789770  # put in the role IDs for your server here
    guild.role_mute          = 777270186604101652  # put in the role IDs for your server here
    
    guild.channel_offtopic        = 778233669881561088  # put in the channel IDs for your server here
    guild.channel_private        = 777270554800422943  # put in the channel IDs for your server here
    guild.channel_reaction_roles = 790233654260793384  # put in the channel IDs for your server here
    guild.channel_reports        = 777270579719569410  # put in the channel IDs for your server here
    
    guild.logging_excluded_channels = []  # put in a channel if you want (ignored in logging)
    guild.filter_excluded_channels  = []  # put in a channel if you want (ignored in filter)
    guild.filter_excluded_guilds    = []  # put guild ID to whitelist in invite filter if you want
    guild.save()

    print("DONE")

if __name__ == "__main__":
        mongoengine.register_connection(alias="default", name="chromey")
        res = asyncio.get_event_loop().run_until_complete( setup() )
