# DNI
import discord
from discord import app_commands
from discord.ext import commands, tasks
import settings

from typing import *

import functions
import random
import os
import json
import time
import asyncio
import re

COLOR = 0xe87a13
ORANGE = COLOR


base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

START = 1696143600

if os.environ["TRIGBOT_ENV"] == "testing":
    START = time.time() + 5

END = START + (60 * 60 * 24 * 31)

class Halloween(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

        self.hdb = self.bot.mdb["TrigBot"]["halloween"]

        self.queued = False
        with open(os.path.join(base, "assets", "halloween", "halloween_items.json")) as f:
            self.items = json.load(f)
        with open(os.path.join(base, "assets", "halloween", "sets.json")) as f:
            self.sets = json.load(f)

        self.images = [f for f in os.listdir(os.path.join(base, "assets", "halloween", "images")) if os.path.isfile(os.path.join(base, "assets", "halloween", "images", f))]
        
        self.raiseerror = True
        self.mtype = 0
        self.active = []
        self.required = []
        self.lookingfor = 0
        
        self.weights = [75, 20, 4, 1]

        self.first_announcement.start()
        self.last_announcement.start()

    @tasks.loop(count=1)
    async def first_announcement(self):
        future = START
        if future - time.time() < 0: return
        await asyncio.sleep(future - time.time())

        embed = functions.embed("Halloween Event", color=COLOR)

        for guild in self.hdb.find({"role": "guild"}):
            
            embed = functions.embed("Halloween Event", color=COLOR)
            embed.description = "The month of October is finally upon us! To celebrate, we're bringing back the month-long event of **trick-or-treating!**"
            embed.add_field(name="How does it work?", value=f"Head on over to <#{guild['general']}> and wait for trick-or-treaters to arrive.\nWhen they do, they will ask for either a **trick** or a **treat**.\nPress the corresponding button.\nThe first person to do so will be gifted a random item in return.", inline=False)
            embed.add_field(name="What do I do with these items?", value="You get points for every unique item you have.\nYou also get additional points for special bundles of items that you have.\nYou can check what items and bundles you have with `/halloween inventory`.\nDuring the event, use `/halloween leaderboard` to see who has the most points.", inline=False)
            embed.add_field(name="What happens to the people with the most points?", value="At the end of the event, the person at the top of the leaderboard will be declared the **Champion of Halloween**!\nIf there is a tie, all tied members will be declared the winners.\n", inline=False)
            embed.add_field(name="How long does it go on for?", value=f"The event starts on <t:{START}:f> and lasts until <t:{END}:f>.\n\nGood luck, and have fun! 🎃", inline=False)
            
            await self.bot.get_channel(guild["announcements"]).send("@everyone", embed=embed)


    @tasks.loop(count=1)
    async def last_announcement(self):
        future = END
        if future - time.time() < 0: return
        await asyncio.sleep(future - time.time())
        if not self.bot.enabled: return

        # TODO: Add announcement
        # kms againnnn


    group = app_commands.Group(name="halloween", description="Halloween 2023 commands")

    @group.command(name="setup")
    async def setup_halloween(self, inter: discord.Interaction) -> None:
        if (START <= time.time() <= END) and self.bot.production == "stable":
            e_err = functions.embed("Error: Event Already Started", color=0xff0000)
            e_err.description = "The event has already started.\nYou cannot set up the event at this time."
            await inter.response.send_message(embed=e_err, ephemeral=True)
            return
        if not inter.guild_id: return
        
        if not inter.user.guild_permissions.administrator:
            embed = functions.embed("Error: Missing Permissions", color=0xff0000)
            embed.description = "You must have the `Administrator` permission to set up the Halloween event."
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        first_sent = False

        if self.hdb.find_one({"_id": inter.guild_id}):
            e0 = functions.embed("Halloween Event Setup (0/2)", color=COLOR)
            e0.description = "The Halloween event has already been set up.\nWould you like to modify the setup?\n\nType `yes` to modify the setup, or `no` to cancel.\nThis menu will time out after 60 seconds."
            m = await inter.response.send_message(embed=e0)
            first_sent = True
            def check_message(message):
                if not(message.author.id == inter.user.id and message.channel.id == inter.channel_id): return False
                return message.content.strip().lower() in ["yes", "no"]
            try:
                message = await self.bot.wait_for("message", check=check_message, timeout=60)
            except asyncio.TimeoutError:
                e_err = functions.embed("Halloween Event Setup (0/2)", color=0xff0000)
                e_err.description = "The menu has timed out.\nPlease try again."
                await inter.channel.send(embed=e_err, message=m)
                return
            if message.content.strip().lower() == "no":
                e_err = functions.embed("Halloween Event Setup (0/2)", color=0xff0000)
                e_err.description = "The menu has been cancelled."
                await inter.channel.send(embed=e_err, message=m)
                return



        e1 = functions.embed("Halloween Event Setup (1/2)", color=COLOR)
        e1.description = "Event setup has started.\nThe menu will automatically time out after 60 seconds\n\nFirst, type a channel to have the event interactions be sent in.\n**To prevent unnecessary spam, it is recommended to make a completely separate channel for this event**."
        if not first_sent:
            m = await inter.response.send_message(embed=e1)
        else:
            m = await inter.channel.send(embed=e1)
        def check_message(message):
            if not(message.author.id == inter.user.id and message.channel.id == inter.channel_id): return False
            return re.search(r"\d{18,19}", message.content) is not None

        try:
            message = await self.bot.wait_for("message", check=check_message, timeout=60)
        except asyncio.TimeoutError:
            e_err = functions.embed("Halloween Event Setup (Timed Out)", color=COLOR)
            e_err.description = "The setup has timed out. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return
        
        setup_info = {"_id": inter.guild_id, "role": "guild"} # hack for mongodb

        channel = self.bot.get_channel(int(re.search(r"\d{18,19}", message.content).group(0)))
        if not channel:
            e_err = functions.embed("Halloween Event Setup (Invalid Channel)", color=COLOR)
            e_err.description = "The channel you provided is invalid. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return

        setup_info["general"] = channel.id
        
        e2 = functions.embed("Halloween Event Setup (2/2)", color=COLOR)
        e2.description = f"Next, type a channel to have event announcements sent in.\nThe bot will send two announcements: one at the start of the event (<t:{START}:f>), and another at the end (<t:{END}:f>)."
        m2 = await inter.channel.send(embed=e2)
        try:
            message = await self.bot.wait_for("message", check=check_message, timeout=60)
        except asyncio.TimeoutError:
            e_err = functions.embed("Halloween Event Setup (Timed Out)", color=COLOR)
            e_err.description = "The setup has timed out. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return

        channel = self.bot.get_channel(int(re.search(r"\d{18,19}", message.content).group(0)))
        if not channel:
            e_err = functions.embed("Halloween Event Setup (Invalid Channel)", color=COLOR)
            e_err.description = "The channel you provided is invalid. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return
        
        setup_info["announcements"] = channel.id


        e5 = functions.embed("Halloween Event Setup (Confirm)", color=COLOR)
        e5.description = "Please confirm that the following information is correct.\nIf it is, type `confirm`.\nIf it is not, type `cancel`."
        e5.add_field(name="Halloween Channel", value=f"<#{setup_info['general']}>", inline=False)
        e5.add_field(name="Announcement Channel", value=f"<#{setup_info['announcements']}>", inline=False)
        m5 = await inter.channel.send(embed=e5)
        def check_message(message):
            if not(message.author.id == inter.user.id and message.channel.id == inter.channel_id): return False
            return message.content.strip().lower() in ["confirm", "cancel"]
        try:
            message = await self.bot.wait_for("message", check=check_message, timeout=60)
        except asyncio.TimeoutError:
            e_err = functions.embed("Halloween Event Setup (Timed Out)", color=COLOR)
            e_err.description = "The setup has timed out. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return
        if message.content.strip().lower() == "confirm":
            if not self.hdb.find_one({"_id": inter.guild_id}):
                self.hdb.insert_one({"_id": inter.guild_id})
            try:
                self.hdb.update_one({"_id": inter.guild_id}, {"$set": setup_info}, upsert=True)
            except Exception as e:
                raise
            e6 = functions.embed("Halloween Event Setup (Complete)", color=COLOR)
            e6.description = "The event has been successfully set up.\nAll announcements and interactions will automatically run when the event starts.\n\nIf you need to modify the event setup, run `/halloween setup` again **before the event starts**.\nIf you need to clear the event setup, run `/halloween clear` **before the event starts**."
            await inter.channel.send(embed=e6)


    @group.command(name="clear")
    async def clear_halloween(self, inter: discord.Interaction):
        """Clear the Halloween Event setup information"""
        if (START <= time.time() <= END) and self.bot.production == "stable":
            e_err = functions.embed("Error: Event Already Started", color=0xff0000)
            e_err.description = "The event has already started.\nYou cannot clear the event at this time."
            await inter.response.send_message(embed=e_err, ephemeral=True)
            return

        if not inter.guild_id: return

        

        if not inter.user.guild_permissions.administrator:
            embed = functions.embed("Error: Missing Permissions", color=0xff0000)
            embed.description = "You must have the `Administrator` permission to set up the Halloween event."
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        if not self.hdb.find_one({"_id": inter.guild_id}):
            e_err = functions.embed("Error: Event Not Set Up", color=0xff0000)
            e_err.description = "The event has not been set up in this server.\nTo set it up, type `/halloween setup`."
            await inter.response.send_message(embed=e_err, ephemeral=True)
            return

        e0 = functions.embed("Clear Event?", color=COLOR)
        e0.description = "Are you sure you want to clear the Halloween event?\nThis will remove all setup information.\n\nIf you want to have the event set up again, you will need to run `/halloween setup` again.\nIf you would like to, type `confirm`.\nIf you would like to cancel, type `cancel`.\nThis will time out in 60 seconds."
        await inter.response.send_message(embed=e0)
        def check(message):
            if not(message.author == inter.user and message.channel == inter.channel): return False
            if message.content.strip().lower() in ["confirm", "cancel"]: return True
            return False
        try:
            message = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            e = functions.embed("Event Clear Cancelled", color=COLOR)
            e.description = "The menu has timed out.\nIf you would like to clear the event, run `/halloween clear` again."
            await inter.channel.send(embed=e)
            return
        


        self.hdb.delete_one({"_id": inter.guild_id})
        e = functions.embed("Halloween Event Cleared", color=COLOR)
        e.description = "The Halloween event has been cleared.\nYou can now set up the event again."
        await inter.channel.send(embed=e)

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if not(START <= time.time() <= END): return
        if not message.guild: return
        context = await self.bot.get_context(message)
        if context.valid: return

        guild = self.hdb.find_one({"_id": message.guild.id})
        if not guild: return

        # TODO: the rest of this

        if len(self.required) < 1 and not self.queued:
            if message.author.id not in self.required:
                self.required.append(message.author.id)
            return
        
        if not self.queued:
            self.queued = True
            self.required = []
            if os.environ["TRIGBOT_ENV"] == "testing":
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(random.randint(60*5, 60*7.5))
            
            channel = self.bot.get_channel(guild["general"])
            if not channel: return
            self.active = []
            self.lookingfor = 1
            if random.random() > .95:
                self.lookingfor = 2
            self.mtype
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Halloween(bot))