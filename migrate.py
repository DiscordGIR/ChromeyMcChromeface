import asyncio
import os

import mongoengine
from dotenv import find_dotenv, load_dotenv
import sqlite3
from data.user import User
from data.guild import Guild
from data.tag import Tag
from os.path import dirname, abspath
import os
import dateutil.parser
load_dotenv(find_dotenv())

async def setup():
    print("STARTING SETUP...")
    guild = Guild.objects(_id=int(os.environ.get("CHROMEY_MAINGUILD"))).first()
    BASE_DIR = dirname(dirname(abspath(__file__)))
    db_path = os.path.join(BASE_DIR, "ChromeyMcChromeface/commands.sqlite")
    
    # commands = None
    # users = None
    # try:
    #     conn = sqlite3.connect(db_path)
    #     c = conn.cursor()
    #     c.execute("SELECT * FROM commands ORDER BY command_name")
    #     # c.execute("SELECT * FROM commands WHERE server_id = ? ORDER BY command_name", (int(os.environ.get("CHROMEY_MAINGUILD")),))
    #     commands = c.fetchall()

    #     c.execute("SELECT * FROM users")
    #     users = c.fetchall()
    # finally:
    #     conn.close()
        
    # for command in commands:
    #     tag = Tag()
    #     tag._id = command[0]
        
    #     user_tag = None
    #     for user in users:
    #         if user[0] == int(command[2]):
    #             user_tag = user[1]
    #             tag.added_by_tag = user[1]
                
    #     if user_tag is None:
    #         tag.added_by_tag = "Unknown"
        
    #     tag.added_by_id = command[2]
    #     tag.name = command[3]
    #     tag.use_count = command[4]
    #     tag.content = command[5]
    #     tag.args = command[6] == "true"
        
    #     guild.tags.append(tag)
    #     # print(command[3], command[6])
    # # you should have this setup in the .env file beforehand
    
    # guild.save()

    karma = None
    karma_history = None
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM karma_history")
        karma_history = c.fetchall()

        c.execute("SELECT * FROM karma")
        karma = c.fetchall()
    finally:
        conn.close()

    for user in karma:
        u = User.objects(_id=user[0]).first()
        # first we ensure this user has a User document in the database before continuing
        if not u:
            u = User()
            u._id = user[0]
        u.karma = user[2]
        u.save()

    for hist in karma_history:
        receiver = User.objects(_id=hist[2]).first()
        if not receiver:
            receiver = User()
            receiver._id = user[0]
        
        giver = User.objects(_id=hist[3]).first()
        if not giver:
            giver = User()
            giver._id = user[0]

        give_action = {
            "amount": hist[4],
            "to": hist[2],
            "date": dateutil.parser.parse(hist[5]),
            "reason": hist[6]
        }
        giver.karma_given_history.append(give_action)
        giver.save()
        
        receive_action = {
            "amount": hist[4],
            "from": hist[3],
            "date": dateutil.parser.parse(hist[5]),
            "reason": hist[6]
        }
        receiver.karma_received_history.append(receive_action)
        receiver.save()
        
    print("DONE")

if __name__ == "__main__":
        mongoengine.register_connection(alias="default", name="chromey")
        res = asyncio.get_event_loop().run_until_complete( setup() )
