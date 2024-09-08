# DNI

import discord
from discord import app_commands
from discord.ext import commands, tasks
import settings
import mongohelper as mh
import re

import time
import asyncio
import json

from typing import *

import functions
import random
import os


START = 1676350800
END = 1676437200

NAME = "Valentine's Day Event"
DESCRIPTION = "Commands to set up the Valentine's Day Event, which will run automatically"

COLOR = 0xa7023c

assert END - START == (24 * 3600) # sanity check


base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

with open(os.path.join(base, "assets", "valentines", "valentines_items.json"), encoding='utf-8') as f:
    items = json.load(f)


class Valentines(commands.Cog):
    """Commands for the Valentine's Day Event"""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()  # this is now required in this context.

        self.vdb = self.bot.mdb["TrigBot"]["valentines"]

        self.queued = []

        self.first_announcement.start()
        self.last_announcement.start()

        self.items = items

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]

    group = app_commands.Group(name="valentines", description="...")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild_id:
            embed = functions.embed("Error: Invalid Location", color=0xff0000)
            embed.description = "This command can only be used in a server."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if interaction.user.guild_permissions.administrator:
            return True
        disabled = self.bot.mdb["TrigBot"]["settings"]
        within = disabled.find_one({"_id": interaction.guild_id})
        if within:
            if self.get_file_name() in within["disabled_cogs"]:
                embed = functions.embed("Error: Command Disabled", color=0xff0000)
                embed.description = f"This command is part of the `{self.get_file_name()}` cog, which has been disabled by an administrator."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
        return True
        

    @tasks.loop(count=1)
    async def first_announcement(self):
        future = START
        if future - time.time() < 0: return
        await asyncio.sleep(future - time.time())

        servers = self.vdb.find({})
        for server in servers:
            try:
                embed = functions.embed("The Valentine's Day Event has started!", color=COLOR)
                embed.description = "As the day of love approaches, a Traveling Cart appears!\nThis Cart offers items for you to give to your loved ones!"
                embed.add_field(name="General Information", value=f"Every couple of minutes, a Traveling Cart will show up in **<#{server['general']}>** with items.\nReact with their corresponding emoji to obtain those items.", inline=False)
                embed.add_field(name="What do I do with these items?", value="Once you obtain an item, you then have to give it to someone else.\nYou can do so using the `/give` command.\nYou can't give items to yourself, or to bots.", inline=False)
                embed.add_field(name="How do I see what items I have?", value="You can use `/valentines inventory` to see what items you can give to others, as well as what items you have recieved from others.", inline=False)
                embed.add_field(name="What happens when the event is over?", value="Each item grants a certain amount of points.\nThe points are as follows:\n{}\nAfter the event is over, the person with the most amount of points will win!".format("\n".join(f"- {item['emote']} **{item['name']}**: {item['points']} points" for item in self.items)), inline=False)
                embed.add_field(name="Anything else I should know?", value=f"The event will run from **<t:{START}:f>** to **<t:{END}:f>**.\n\nGood luck to everyone that participates! " + random.choice([e for e in "🧡💗💖💙💓💚💝💜💛🤍"]), inline=False)
                
                message = server["start_message"]
                if message:
                    await self.bot.get_channel(server["announcements"]).send(message, embed=embed)
                else:
                    await self.bot.get_channel(server["announcements"]).send(embed=embed)
            except Exception as e:
                print(e)


    @tasks.loop(count=1)
    async def last_announcement(self):
        future = END
        if future - time.time() < 0: return
        await asyncio.sleep(future - time.time())

        servers = self.vdb.find({})
        for server in servers:
            embed = functions.embed("The Valentine's Day Event has ended!", color=COLOR)
            
            guild = self.bot.get_guild(server["_id"])
            if not guild: continue
            scores = {}
            for key in server:
                if key in {"_id", "general", "announcements", "start_message", "end_message"}: continue
                scores[key] = 0
                for item in self.items:
                    scores[key] += server[key][item["name"] + "-r"] * item["points"]
            
            # get maximum, including ties
            if len(scores) == 0:
                winners = []
                embed.description = "The event has now ended."
            else:
                embed.description = "Thank you for participating in the Valentine's Day Event!\n" 
                max_score = max(scores.values())
                winners = []
                for key in scores:
                    if scores[key] == max_score:
                        winners.append(key)
            
            if len(winners) == 0:
                embed.description += "\nNo one won this year, as no person recieved any items.\n\nHope you had a wonderful Valentine's Day! " + random.choice([e for e in "🧡💗💖💙💓💚💝💜💛🤍"])
            elif len(winners) == 1:
                w = winners[0]
                embed.description += "The winner of the Valentine's Day Event is <@{}>, with **{}**!".format(
                    winners[0],
                    ", ".join("{}x {}".format(server[w][item["name"] + "-r"], item["name"]) for item in self.items if server[w][item["name"] + "-r"] > 0) 
                    )
            else:
                embed.description += "The winners of the Valentine's Day Event are:\n"
                for w in winners:
                    embed.description += "- <@{}>, with **{}**\n".format(
                        w,
                        ", ".join("{}x {}".format(server[w][item["name"] + "-r"], item["name"]) for item in self.items if server[w][item["name"] + "-r"] > 0) 
                        )
            if len(winners) > 0:
                embed.description += "\nThank you all for participating! Hope you had a wonderful Valentine's Day! " + random.choice([e for e in "🧡💗💖💙💓💚💝💜💛🤍"])
            message = server["end_message"]
            if message:
                await guild.get_channel(server["announcements"]).send(message, embed=embed)
            else:
                await guild.get_channel(server["announcements"]).send(embed=embed)


    @group.command(name="clear")
    async def clear_valentines(self, inter: discord.Interaction):
        """Clear the Valentine's Day Event and remove all setup information"""
        if (START <= time.time() <= END):
            e_err = functions.embed("Error: Event Already Started", color=0xff0000)
            e_err.description = "The event has already started.\nYou cannot clear the event at this time."
            await inter.response.send_message(embed=e_err, ephemeral=True)
            return

        if not inter.guild_id: return

        

        if not inter.user.guild_permissions.administrator:
            embed = functions.embed("Error: Missing Permissions", color=0xff0000)
            embed.description = "You must have the `Administrator` permission to set up the Valentine's Day event."
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        if not mh.find(self.vdb, inter.guild_id):
            e_err = functions.embed("Error: Event Not Set Up", color=0xff0000)
            e_err.description = "The event has not been set up in this server.\nTo set it up, type `/valentines setup`."
            await inter.response.send_message(embed=e_err, ephemeral=True)
            return

        e0 = functions.embed("Clear Event?", color=COLOR)
        e0.description = "Are you sure you want to clear the Valentine's Day event?\nThis will remove all setup information.\n\nIf you want to have the event set up again, you will need to run `/valentines setup` again.\nIf you would like to, type `confirm`.\nIf you would like to cancel, type `cancel`.\nThis will time out in 60 seconds."
        await inter.response.send_message(embed=e0)
        def check(message):
            if not(message.author == inter.user and message.channel == inter.channel): return False
            if message.content.lower() in ["confirm", "cancel"]: return True
            return False
        try:
            message = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            e = functions.embed("Event Clear Cancelled", color=COLOR)
            e.description = "The menu has timed out.\nIf you would like to clear the event, run `/valentines clear` again."
            await inter.channel.send(embed=e)
            return
        


        self.vdb.delete_one({"_id": inter.guild_id})
        e = functions.embed("Valentine's Day Event Cleared", color=COLOR)
        e.description = "The Valentine's Day event has been cleared.\nYou can now set up the event again."
        await inter.channel.send(embed=e)

    @group.command(name="setup")
    async def setup_valentines(self, inter: discord.Interaction):
        """Set up the Valentine's Day Event"""
        if (START <= time.time() <= END):
            e_err = functions.embed("Error: Event Already Started", color=0xff0000)
            e_err.description = "The event has already started.\nYou cannot set up the event at this time."
            await inter.response.send_message(embed=e_err, ephemeral=True)
            return
        if not inter.guild_id: return
        
        if not inter.user.guild_permissions.administrator:
            embed = functions.embed("Error: Missing Permissions", color=0xff0000)
            embed.description = "You must have the `Administrator` permission to set up the Valentine's Day event."
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        first_sent = False
        
        if mh.find(self.vdb, inter.guild_id):
            e0 = functions.embed("Valentine's Day Event Setup (0/4)", color=COLOR)
            e0.description = "The Valentine's Day event has already been set up.\nWould you like to modify the setup?\n\nType `yes` to modify the setup, or `no` to cancel.\nThis menu will time out after 60 seconds."
            m = await inter.response.send_message(embed=e0)
            first_sent = True
            def check_message(message):
                if not(message.author.id == inter.user.id and message.channel.id == inter.channel_id): return False
                return message.content.lower() in ["yes", "no"]
            try:
                message = await self.bot.wait_for("message", check=check_message, timeout=60)
            except asyncio.TimeoutError:
                e_err = functions.embed("Valentine's Day Event Setup (0/4)", color=0xff0000)
                e_err.description = "The menu has timed out.\nPlease try again."
                await inter.channel.send(embed=e_err, message=m)
                return
            if message.content.lower() == "no":
                e_err = functions.embed("Valentine's Day Event Setup (0/4)", color=0xff0000)
                e_err.description = "The menu has been cancelled."
                await inter.channel.send(embed=e_err, message=m)
                return



        e1 = functions.embed("Valentine's Day Event Setup (1/4)", color=COLOR)
        e1.description = "Event setup has started.\nThe menu will automatically time out after 60 seconds\n\nFirst, type a channel to have the event interactions be sent in.\nThis should be your general channel, or wherever bots normally send messages in your server."
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
            e_err = functions.embed("Valentine's Day Event Setup (Timed Out)", color=COLOR)
            e_err.description = "The setup has timed out. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return
        
        setup_info = {"_id": inter.guild_id}

        channel = self.bot.get_channel(int(re.search(r"\d{18,19}", message.content).group(0)))
        if not channel:
            e_err = functions.embed("Valentine's Day Event Setup (Invalid Channel)", color=COLOR)
            e_err.description = "The channel you provided is invalid. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return

        setup_info["general"] = channel.id
        
        e2 = functions.embed("Valentine's Day Event Setup (2/4)", color=COLOR)
        e2.description = "Next, type a channel to have event announcements sent in.\nThese announcements will include the announcements that indicate start and end of the event."
        m2 = await inter.channel.send(embed=e2)
        try:
            message = await self.bot.wait_for("message", check=check_message, timeout=60)
        except asyncio.TimeoutError:
            e_err = functions.embed("Valentine's Day Event Setup (Timed Out)", color=COLOR)
            e_err.description = "The setup has timed out. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return

        channel = self.bot.get_channel(int(re.search(r"\d{18,19}", message.content).group(0)))
        if not channel:
            e_err = functions.embed("Valentine's Day Event Setup (Invalid Channel)", color=COLOR)
            e_err.description = "The channel you provided is invalid. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return
        
        setup_info["announcements"] = channel.id

        e3 = functions.embed("Valentine's Day Event Setup (3/4)", color=COLOR)
        e3.description = "Would you like to provide a custom announcement message for the **start** of the event?\nThis message will be sent alongside the default announcement embed.\nIt can be used if you want to ping a specific role for the event.\nType `yes` for yes, and `no` for no."
        m3 = await inter.channel.send(embed=e3)
        def check_message(message):
            if not(message.author.id == inter.user.id and message.channel.id == inter.channel_id): return False
            return message.content.strip().lower() in ["yes", "no"]
        
        try:
            message = await self.bot.wait_for("message", check=check_message, timeout=60)
        except asyncio.TimeoutError:
            e_err = functions.embed("Valentine's Day Event Setup (Timed Out)", color=COLOR)
            e_err.description = "The setup has timed out. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return
        if message.content.strip().lower() == "yes":
            e3_2 = functions.embed("Valentine's Day Event Setup (3/4)", color=COLOR)
            e3_2.description = "Type the message you would like to send for the **start** of the event."
            m3_2 = await inter.channel.send(embed=e3_2)
            def check_message(message):
                if not(message.author.id == inter.user.id and message.channel.id == inter.channel_id): return False
                return True
            try:
                message = await self.bot.wait_for("message", check=check_message, timeout=60)
            except asyncio.TimeoutError:
                e_err = functions.embed("Valentine's Day Event Setup (Timed Out)", color=COLOR)
                e_err.description = "The setup has timed out. Please run the setup command again."
                await inter.channel.send(embed=e_err)
                return
            setup_info["start_message"] = message.content
        else:
            setup_info["start_message"] = ""

        e4 = functions.embed("Valentine's Day Event Setup (4/4)", color=COLOR)
        e4.description = "Would you like to provide a custom announcement message for the **end** of the event?\nThis message will be sent alongside the default announcement embed.\nIt can be used if you want to ping a specific role for the event.\nType `yes` for yes, and `no` for no."
        m4 = await inter.channel.send(embed=e4)
        def check_message(message):
            if not(message.author.id == inter.user.id and message.channel.id == inter.channel_id): return False
            return message.content.strip().lower() in ["yes", "no"]
        try:
            message = await self.bot.wait_for("message", check=check_message, timeout=60)
        except asyncio.TimeoutError:
            e_err = functions.embed("Valentine's Day Event Setup (Timed Out)", color=COLOR)
            e_err.description = "The setup has timed out. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return
        if message.content.strip().lower() == "yes":
            e4_2 = functions.embed("Valentine's Day Event Setup (4/4)", color=COLOR)
            e4_2.description = "Type the message you would like to send for the **end** of the event."
            m4_2 = await inter.channel.send(embed=e4_2)
            def check_message(message):
                if not(message.author.id == inter.user.id and message.channel.id == inter.channel_id): return False
                return True
            try:
                message = await self.bot.wait_for("message", check=check_message, timeout=60)
            except asyncio.TimeoutError:
                e_err = functions.embed("Valentine's Day Event Setup (Timed Out)", color=COLOR)
                e_err.description = "The setup has timed out. Please run the setup command again."
                await inter.channel.send(embed=e_err)
                return
            setup_info["end_message"] = message.content
        else:
            setup_info["end_message"] = ""
        
        e5 = functions.embed("Valentine's Day Event Setup (Confirm)", color=COLOR)
        e5.description = "Please confirm that the following information is correct.\nIf it is, type `confirm`.\nIf it is not, type `cancel`."
        e5.add_field(name="General Channel", value=f"<#{setup_info['general']}>", inline=False)
        e5.add_field(name="Announcement Channel", value=f"<#{setup_info['announcements']}>", inline=False)
        e5.add_field(name="Start Message", value=setup_info["start_message"] or "None", inline=False)
        e5.add_field(name="End Message", value=setup_info["end_message"] or "None", inline=False)
        m5 = await inter.channel.send(embed=e5)
        def check_message(message):
            if not(message.author.id == inter.user.id and message.channel.id == inter.channel_id): return False
            return message.content.strip().lower() in ["confirm", "cancel"]
        try:
            message = await self.bot.wait_for("message", check=check_message, timeout=60)
        except asyncio.TimeoutError:
            e_err = functions.embed("Valentine's Day Event Setup (Timed Out)", color=COLOR)
            e_err.description = "The setup has timed out. Please run the setup command again."
            await inter.channel.send(embed=e_err)
            return
        if message.content.strip().lower() == "confirm":
            if not mh.find(self.vdb, inter.guild_id):
                self.vdb.insert_one({"_id": inter.guild_id})
            try:
                self.vdb.update_one({"_id": inter.guild_id}, {"$set": setup_info}, upsert=True)
            except Exception as e:
                raise
            e6 = functions.embed("Valentine's Day Event Setup (Complete)", color=COLOR)
            e6.description = "The event has been successfully set up.\nAll announcements and interactions will automatically run when the event starts.\n\nIf you need to modify the event setup, run `/valentines setup` again **before the event starts**.\nIf you need to clear the event setup, run `/valentines clear` **before the event starts**.\n\n" + random.choice([e for e in "🧡💗💖💙💓💚💝💜💛🤍"])
            await inter.channel.send(embed=e6)



        


    @commands.Cog.listener()
    async def on_message(self, message):
        if not(START <= time.time() <= END):
            return
        if not message.guild: return
        if message.guild.id in self.queued: return

        if message.author.bot: return

        self.queued.append(message.guild.id)

        await asyncio.sleep(random.randint(60 * 8, 60 * 10))

        data = mh.find(self.vdb, message.guild.id)
        channel_id = data["general"]

        channel = self.bot.get_channel(channel_id)
        embed = functions.embed("Traveling Cart", color=COLOR)
        
        choices = []
        for item in self.items:
            sub = int(random.random() * 100)
            if sub < item["chance"]:
                choices.append(item) 

        desc = "The Traveling Cart has stopped by!\nIt brings the following items to share:\n\n"
        for item in choices:
            desc = desc + "- " + item["emote"] + " " + item["name"] + "\n"
        desc = desc + "\nReact with the emotes within 10 seconds to get these items!"
        embed.description = desc

        m = await channel.send(embed=embed)
        for item in choices:
            await m.add_reaction(item["emote"])
        
        await asyncio.sleep(10)
        desc = "The Traveling cart must now leave elsewhere.\nAll items have been distributed.\nHappy Valentine's Day! "
        desc = desc + random.choice([e for e in "🧡💗💖💙💓💚💝💜💛🤍"])
        embed.description = desc
        await m.edit(embed=embed)
        
        m = await channel.fetch_message(m.id)
        reactions = m.reactions
        for item in choices:
            r = discord.utils.get(reactions, emoji=item["emote"])
            ids = []
            async for u in r.users():
                if u.id != self.bot.user.id:
                    ids.append(u.id)
            for id in ids:

                
                data = self.vdb.find_one({"_id": m.guild.id})
                if str(id) not in data:
                    tempdata = {}
                    for i in self.items:
                        tempdata[i["name"] + "-g"] = 0
                        tempdata[i["name"] + "-r"] = 0
                    self.vdb.update_one({"_id": m.guild.id}, {"$set": {str(id) + "." + k: tempdata[k] for k in tempdata}}, upsert=True)
                else:
                    tempdata = data[str(id)]
                self.vdb.update_one({"_id": m.guild.id}, {"$set": {str(id) + "." + item["name"] + "-g": tempdata[item["name"] + "-g"] + 1}}, upsert=True)
        self.queued.remove(message.guild.id)


    @group.command(name="give")
    @app_commands.describe(item="The item to give")
    @app_commands.describe(user="The user to give an item to")
    @app_commands.choices(item=[
        app_commands.Choice(name=i["name"], value=i["name"])
        for i in items[:25]
    ])
    async def give(self, inter: discord.Interaction, item: app_commands.Choice[str], user: discord.Member):
        """Give a user an item!\nPart of the Valentine's Day Event"""
        if not(START <= time.time() <= END):
            embed = functions.embed("Error: Event Not Active", color=0xff0000)
            embed.description = "This command is for the Valentine's Day Event, which is not active at this moment."
            return await inter.response.send_message(embed=embed, ephemeral=True)
        

        if not mh.find(self.vdb, inter.guild_id):
            embed = functions.embed("Error: Event Not Setup", color=0xff0000)
            embed.description = "This command is for the Valentine's Day Event, which has not been set up on this server."
            return await inter.response.send_message(embed=embed, ephemeral=True)

        if user.id == inter.user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't give items to yourself!"
            return await inter.response.send_message(embed=embed, ephemeral=True)
        if user.bot:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't give items to bots!"
            return await inter.response.send_message(embed=embed, ephemeral=True)

        # get item from given item name
        item = [i for i in self.items if i["name"] == item.value][0]

        # data = mh.find(self.vdb, f"{inter.guild_id}/{inter.user.id}")
        data = mh.find(self.vdb, inter.guild_id)
        if str(inter.user.id) not in data:
            tempdata = {}
            for i in self.items:
                tempdata[i["name"] + "-g"] = 0
                tempdata[i["name"] + "-r"] = 0
            
            self.vdb.update_one({"_id": inter.guild_id}, {"$set": {str(inter.user.id) + "." + k: tempdata[k] for k in tempdata}}, upsert=True)
        else:
            tempdata = data[str(inter.user.id)]

        if tempdata[item["name"] + "-g"] < 1:
            embed = functions.embed("Error: Missing Item", color=0xff0000)
            embed.description = "You don't have `" + item["name"] + "` in your inventory!\nUse `/valentines inventory` to see what items you have to give."
            return await inter.response.send_message(embed=embed, ephemeral=True)

        embed = functions.embed("Item Given!", color=COLOR)
        embed.description = "You gave `" + item["name"] + "` to " + user.mention + "!"
        embed.set_thumbnail(url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/" + hex(ord(item["emote"][0]))[2:] + ".png")
        await inter.response.send_message(embed=embed, ephemeral=True)
        # leap of faith

        if str(user.id) not in data:
            targetdata = {}
            for i in self.items:
                targetdata[i["name"] + "-g"] = 0
                targetdata[i["name"] + "-r"] = 0
            self.vdb.update_one({"_id": inter.guild_id}, {"$set": {str(user.id) + "." + k: targetdata[k] for k in targetdata}}, upsert=True)
        else:
            targetdata = data[str(user.id)]
    

        self.vdb.update_one({"_id": inter.guild_id}, {"$set": {str(inter.user.id) + "." + item["name"] + "-g": tempdata[item["name"] + "-g"] - 1}})
        self.vdb.update_one({"_id": inter.guild_id}, {"$set": {str(user.id) + "." + item["name"] + "-r": targetdata[item["name"] + "-r"] + 1}})
        embed = functions.embed("Item Received!", color=COLOR)

        embed.description = "*" + random.choice(item["poems"]) + "*\n\nYou were given `" + item["name"] + "` by " + inter.user.mention + "!\nUse `/valentines inventory` to see what items you have received.\nHappy Valentine's Day! "
        embed.description = embed.description + random.choice([e for e in "🧡💗💖💙💓💚💝💜💛🤍"])
        embed.set_thumbnail(url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/" + hex(ord(item["emote"][0]))[2:] + ".png")
        try:
            await user.send(embed=embed)
        except:
            pass


        

    @group.command(name="inventory")
    @app_commands.describe(user="The user to view the inventory of. Defaults to you")
    async def inventory(self, inter: discord.Interaction, user: Optional[discord.Member]):
        """View your inventory!\nPart of the Valentine's Day Event"""
        if not(START <= time.time() <= END):
            embed = functions.embed("Error: Event Not Active", color=0xff0000)
            embed.description = "This command is for the Valentine's Day Event, which is not active at this moment."
            return await inter.response.send_message(embed=embed, ephemeral=True)

        if not mh.find(self.vdb, inter.guild_id):
            embed = functions.embed("Error: Event Not Setup", color=0xff0000)
            embed.description = "This command is for the Valentine's Day Event, which has not been set up on this server."
            return await inter.response.send_message(embed=embed, ephemeral=True)

        

        # data = mh.find(self.vdb, f"{inter.guild_id}/{user.id if user else inter.user.id}")
        # if not data:
        #     data = {"_id": f"{inter.guild_id}/{user.id if user else inter.user.id}"}
        #     for i in self.items:
        #         data[i["name"] + "-g"] = 0
        #         data[i["name"] + "-r"] = 0
        #     self.vdb.insert_one(data)

        if user:
            id = user.id
            if user.bot:
                embed = functions.embed("Error: Invalid User", color=0xff0000)
                embed.description = "You cannot view the inventory of a bot, as they are not participating in the event."
                return await inter.response.send_message(embed=embed, ephemeral=True)
        else:
            id = inter.user.id

        data = mh.find(self.vdb, inter.guild_id)
        if str(id) not in data:
            tempdata = {}
            for i in self.items:
                tempdata[i["name"] + "-g"] = 0
                tempdata[i["name"] + "-r"] = 0
            self.vdb.update_one({"_id": inter.guild_id}, {"$set": {str(id) + "." + k: tempdata[k] for k in tempdata}}, upsert=True)
            data = tempdata
            #self.vdb.update_one({"_id": inter.guild_id}, {"$set": {str(user.id if user else inter.user.id): data[(user.id if user else inter.user.id)]}}, upsert=True)
        else:
            data = data[str(id)]

        embed = functions.embed("Inventory", color=COLOR)
        if not user:
            embed.description = "Here is your inventory!"
        elif user.id == inter.user.id:
            embed.description = "Here is your inventory!"
        else:
            embed.description = "Here is " + user.mention + "'s inventory!"
        
        if user:
            url = user.avatar.url
        else:
            url = inter.user.avatar.url
        embed.set_thumbnail(url=url)
        embed.add_field(name="Items to Give", value="\n".join([f"- {i['emote']} {i['name']} x{data[i['name'] + '-g']}" for i in self.items]), inline=False)
        embed.add_field(name="Items Received", value="\n".join([f"- {i['emote']} {i['name']} x{data[i['name'] + '-r']}" for i in self.items]), inline=False)
        await inter.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Valentines(bot))
# line 600