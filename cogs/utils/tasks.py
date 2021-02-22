import logging
from datetime import datetime

import discord
import random
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cogs.utils.logs import prepare_unmute_log
from data.case import Case

jobstores = {
    'default': MongoDBJobStore(database="chromey", collection="jobs", host="127.0.0.1"),
}

executors = {
    'default': ThreadPoolExecutor(20)
}

job_defaults = {
    # 'coalesce': True
}

BOT_GLOBAL = None


class Tasks():
    """Job scheduler for unmute, using APScheduler
    """

    def __init__(self, bot: discord.Client):
        """Initialize scheduler

        Parameters
        ----------
        bot : discord.Client
            instance of Discord client
        """

        global BOT_GLOBAL
        BOT_GLOBAL = bot

        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.DEBUG)

        self.tasks = AsyncIOScheduler(
            jobstores=jobstores, executors=executors, job_defaults=job_defaults, event_loop=bot.loop)
        self.tasks.start()

    def schedule_unmute(self, id: int, date: datetime) -> None:
        """Create a task to unmute user given by ID `id`, at time `date`

        Parameters
        ----------
        id : int
            User to unmute
        date : datetime.datetime
            When to unmute
        """

        self.tasks.add_job(unmute_callback, 'date', id=str(
            id), next_run_time=date, args=[id], misfire_grace_time=3600)
    
    def schedule_untimeout(self, id: int, date: datetime) -> None:
        """Create a task to remove timeout for user given by ID `id`, at time `date`

        Parameters
        ----------
        id : int
            User to untimeout
        date : datetime.datetime
            When to untimeout
        """

        self.tasks.add_job(untimeout_callback, 'date', id=str(
            id+3), next_run_time=date, args=[id], misfire_grace_time=3600)

    def schedule_remove_bday(self, id: int, date: datetime) -> None:
        """Create a task to remove birthday role from user given by ID `id`, at time `date`

        Parameters
        ----------
        id : int
            User to remove role
        date : datetime.datetime
            When to remove role
        """

        self.tasks.add_job(remove_bday_callback, 'date', id=str(
            id+1), next_run_time=date, args=[id], misfire_grace_time=3600)

    def cancel_unmute(self, id: int) -> None:
        """When we manually unmute a user given by ID `id`, stop the task to unmute them.

        Parameters
        ----------
        id : int
            User whose unmute task we want to cancel
        """

        self.tasks.remove_job(str(id), 'default')        

    def schedule_reminder(self, id: int, reminder: str, date: datetime) -> None:
        """Create a task to remind someone of id `id` of something `reminder` at time `date`

        Parameters
        ----------
        id : int
            User to remind
        reminder : str
            What to remind them of
        date : datetime.datetime
            When to remind
        """

        self.tasks.add_job(reminder_callback, 'date', id=str(
            id+random.randint(5, 100)), next_run_time=date, args=[id, reminder], misfire_grace_time=3600)


def unmute_callback(id: int) -> None:
    """Callback function for actually unmuting. Creates asyncio task
    to do the actual unmute.

    Parameters
    ----------
    id : int
        User who we want to unmute
    """

    BOT_GLOBAL.loop.create_task(remove_mute(id))


async def remove_mute(id: int) -> None:
    """Remove the mute role of the user given by ID `id`

    Parameters
    ----------
    id : int
        User to unmute
    """

    guild = BOT_GLOBAL.get_guild(BOT_GLOBAL.settings.guild_id)
    if guild is not None:
        mute_role = BOT_GLOBAL.settings.guild().role_mute
        mute_role = guild.get_role(mute_role)
        if mute_role is not None:
            user = guild.get_member(id)
            if user is not None:
                await user.remove_roles(mute_role)
                case = Case(
                    _id=BOT_GLOBAL.settings.guild().case_id,
                    _type="UNMUTE",
                    mod_id=BOT_GLOBAL.user.id,
                    mod_tag=str(BOT_GLOBAL.user),
                    reason="Temporary mute expired.",
                )
                await BOT_GLOBAL.settings.inc_caseid()
                await BOT_GLOBAL.settings.add_case(user.id, case)

                u = await BOT_GLOBAL.settings.user(id=user.id)
                u.is_muted = False
                u.save()

                log = await prepare_unmute_log(BOT_GLOBAL.user, user, case)

                log.remove_author()
                log.set_thumbnail(url=user.avatar_url)
                
                dmed = True
                try:
                    await user.send(embed=log)
                except Exception:
                    pass                    
            else:
                case = Case(
                    _id=BOT_GLOBAL.settings.guild().case_id,
                    _type="UNMUTE",
                    mod_id=BOT_GLOBAL.user.id,
                    mod_tag=str(BOT_GLOBAL.user),
                    reason="Temporary mute expired.",
                )
                await BOT_GLOBAL.settings.inc_caseid()
                await BOT_GLOBAL.settings.add_case(id, case)

                u = await BOT_GLOBAL.settings.user(id=id)
                u.is_muted = False
                u.save()

def reminder_callback(id: int, reminder: str):
    BOT_GLOBAL.loop.create_task(remind(id, reminder))

async def remind(id, reminder):
    """Remind the user callback

    Parameters
    ----------
    id : int
        ID of user to remind
    reminder : str
        body of reminder
    """
    
    guild = BOT_GLOBAL.get_guild(BOT_GLOBAL.settings.guild_id)
    if guild is None:
        return
    member = guild.get_member(id)
    if member is None:
        return

    embed = discord.Embed(title="Reminder!", description=f"*You wanted me to remind you something... What was it... Oh right*:\n\n{reminder}", color=discord.Color.random())
    try:
        await member.send(embed=embed)
    except Exception:
        channel = guild.get_channel(BOT_GLOBAL.settings.guild().channel_botspam)
        await channel.send(member.mention, embed=embed)

def remove_bday_callback(id: int) -> None:
    """Callback function for actually unmuting. Creates asyncio task
    to do the actual unmute.

    Parameters
    ----------
    id : int
        User who we want to unmute
    """

    BOT_GLOBAL.loop.create_task(remove_bday(id))


async def remove_bday(id: int) -> None:
    """Remove the bday role of the user given by ID `id`

    Parameters
    ----------
    id : int
        User to remove role of
    """

    guild = BOT_GLOBAL.get_guild(BOT_GLOBAL.settings.guild_id)
    if guild is None:
        return

    bday_role = BOT_GLOBAL.settings.guild().role_birthday
    bday_role = guild.get_role(bday_role)
    if bday_role is None:
        return

    user = guild.get_member(id)
    await user.remove_roles(bday_role)



def untimeout_callback(id: int) -> None:
    """Callback function for actually untimeout. Creates asyncio task
    to do the actual untimeout.

    Parameters
    ----------
    id : int
        User who we want to untimeout
    """

    BOT_GLOBAL.loop.create_task(remove_timeout(id))


async def remove_timeout(id: int) -> None:
    """Remove the timeout role of the user given by ID `id`

    Parameters
    ----------
    id : int
        User to unmute
    """

    guild = BOT_GLOBAL.get_guild(BOT_GLOBAL.settings.guild_id)
    if guild is None:
        return
    
    member = guild.get_member(id)
    if member is None:
        return

    role = guild.get_role(BOT_GLOBAL.settings.guild().role_rules)
    if role is None:
        return

    embed=discord.Embed(title="Timeout finished.", color=discord.Color(value=0x37b83b), description='Removed your timeout role. Please behave, or we will have to take further action.')
    try:
        await member.send(embed=embed)
        await member.remove_roles(role)
    except discord.Forbidden:
        channel = guild.get_channel(BOT_GLOBAL.settings.guild().channel_botspam)
        await channel.send(f'{member.mention} I tried to DM this to you, but your DMs are closed!', embed=embed)
        await member.remove_roles(role)

