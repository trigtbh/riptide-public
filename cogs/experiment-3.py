import discord
from discord import app_commands
from discord.ext import commands, tasks
import settings

from typing import *

import functions
import random
import os
import asyncio

circles = {
    "🔴": "Red",
    "🟠": "Orange",
    "🟡": "Yellow",
    "🟢": "Green",
    "🔵": "Blue",
    "🟣": "Purple",
    "🟤": "Brown",
    "⚫": "Black",
    "⚪": "White",
}
circlelist = [(k, v) for k, v in circles.items()]


START = 1682085600 
END = START + (3 * 24 * 60 * 60)


import time

class CSG0(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=10.0)
        self.failed = set()
        self.answered = {}
        self.finished = False
        self.cog = cog

        data = self.cog.cdb.find_one({"_id": "stats"})
        self.top = data["streakholder"]
        self.top_points = data["streak"]
        self.top_failed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.finished: return False
        if interaction.user.bot: return False

        if interaction.user.id in self.failed:
            embed = functions.embed("Error: Already Attempted", color=0xff0000)
            embed.description = "You have already attempted this challenge. Please wait until the next one to try again."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False

        return True
    
    async def incorrect_callback(self, interaction: discord.Interaction):
        self.failed.add(interaction.user.id)
        embed = functions.embed("Color Scope: Challenge Failed", color=0xff0000)
        embed.description = "You pressed the wrong circle. Please wait until the next challenge to try again."
        await interaction.response.send_message(embed=embed, ephemeral=True)

        data = self.cog.cdb.find_one({"_id": interaction.user.id})
        if not data:
            data = {"_id": interaction.user.id, "points": 0}
        
        if interaction.user.id == self.top:
            data["points"] -= self.top_points
            self.top_failed = True

            stats = self.cog.cdb.find_one({"_id": "stats"})
            stats["streakholder"] = -interaction.user.id
            self.cog.cdb.update_one({"_id": "stats"}, {"$set": stats}, upsert=True)


        else:
            data["points"] -= 1
        

        self.cog.cdb.update_one({"_id": interaction.user.id}, {"$set": data}, upsert=True)
        

    async def completion(self, interaction):
        data = self.cog.cdb.find_one({"_id": interaction.user.id})
        if not data:
            data = {"_id": interaction.user.id, "points": 0}
        stats = self.cog.cdb.find_one({"_id": "stats"})
        streak = stats["streak"]
        score = 0
        

        
        embed = functions.embed("Color Scope: Challenge Complete!", color=0x61ff9b)

        if stats["streakholder"] == 0:
            stats["streakholder"] = interaction.user.id
            stats["streak"] = 1
            data["points"] += 1
            score = 1
            embed.description = f"<@{interaction.user.id}> has completed the challenge! They earned **{score}** point{'s' if score != 1 else ''}!\nThey now have a streak of **{stats['streak']}**!"
        elif stats["streakholder"] != interaction.user.id:
            stats["streakholder"] = interaction.user.id
            data["points"] += self.top_points
            stats["streak"] = 1
            score = streak
            embed.description = f"<@{interaction.user.id}> has completed the challenge and ended <@{self.top}>'s streak of **{self.top_points}**!\nThey earned **{self.top_points}** point{'s' if score != 1 else ''}!"
        elif stats["streakholder"] == interaction.user.id:
            stats["streak"] += 1
            data["points"] += 1
            score = 1
            embed.description = f"<@{interaction.user.id}> has completed the challenge and extended their streak to **{stats['streak']}**!\nThey earned **{score}** point{'s' if score != 1 else ''}!"
        


        self.cog.cdb.update_one({"_id": interaction.user.id}, {"$set": data}, upsert=True)
        self.cog.cdb.update_one({"_id": "stats"}, {"$set": stats}, upsert=True)

        self.finished = True
        self.cog.locked = False
        await interaction.response.edit_message(embed=embed, view=None)
    

class CSG1(CSG0):
    def __init__(self, cog, gametype, choices):
        super().__init__(cog)
        self.gametype = gametype
        self.choices = choices

        
        full_choices = choices + random.sample(circlelist[:-1], 4 - len(choices))
        temp = set(full_choices)
        while len(temp) != 4:
            temp.add(random.choice(circlelist[:-1]))
        full_choices = list(temp)
        random.shuffle(full_choices)

        for k, v in full_choices:
            button = discord.ui.Button(label=f"{k} {v}", style=discord.ButtonStyle.primary)
            if (k, v) in self.choices:
                button.callback = self.completion
            else:
                button.callback = self.incorrect_callback
            self.add_item(button)

    
    

class CSG2(CSG0):
    def __init__(self, cog, gametype, choices):
        super().__init__(cog)
        self.gametype = gametype
        self.choices = choices

        full_choices = choices + random.sample(circlelist[:-1], 4 - len(choices))
        temp = set(full_choices)
        while len(temp) != 4:
            temp.add(random.choice(circlelist[:-1]))
        full_choices = list(temp)
        random.shuffle(full_choices)

        i = 0
        for k, v in full_choices:
            button = discord.ui.Button(label=f"{k} {v}", style=discord.ButtonStyle.primary)
            button.custom_id = f"button{i}"
            if (k, v) == self.choices[0]:
                
                button.callback = self.correct_callback_1
            elif (k, v) == self.choices[1]:
                button.callback = self.correct_callback_2
            else:
                button.callback = self.incorrect_callback
            self.add_item(button)
            i += 1

    async def correct_callback_1(self, interaction: discord.Interaction):
        if interaction.user.id in self.answered:
            if 1 in self.answered[interaction.user.id]:
                embed = functions.embed("Error: Already Attempted", color=0xff0000)
                embed.description = "You pressed the same circle two times in a row. Please wait until the next challenge to try again."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                self.failed.add(interaction.user.id)
                return
            self.answered[interaction.user.id].append(1)
        else:
            self.answered[interaction.user.id] = [1]
        
        if len(self.answered[interaction.user.id]) == 2:
            await self.completion(interaction)
        else:
            embed = functions.embed("Color Scope: Correct Color", color=0x61ff9b)
            embed.description = f"You successfully presed the `{self.choices[0][0]} {self.choices[0][1]}` circle.\nPress the `{self.choices[1][0]} {self.choices[1][1]}` circle to complete the challenge."
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def correct_callback_2(self, interaction: discord.Interaction):
        if interaction.user.id in self.answered:
            if 2 in self.answered[interaction.user.id]:
                embed = functions.embed("Error: Challenge Failed", color=0xff0000)
                embed.description = "You pressed the same circle two times in a row. Please wait until the next challenge to try again."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                self.failed.add(interaction.user.id)
                return
            self.answered[interaction.user.id].append(2)
        else:
            self.answered[interaction.user.id] = [2]
        
        if len(self.answered[interaction.user.id]) == 2:
            await self.completion(interaction)
        else:
            embed = functions.embed("Color Scope: Correct Color", color=0x61ff9b)
            embed.description = f"You successfully presed the `{self.choices[1][0]} {self.choices[1][1]}` circle.\nPress the `{self.choices[0][0]} {self.choices[0][1]}` circle to complete the challenge."
            await interaction.response.send_message(embed=embed, ephemeral=True)


class CSG3(CSG0):
    def __init__(self, cog, gametype, choices):
        super().__init__(cog)
        self.gametype = gametype
        self.choices = choices

        full_choices = choices + random.sample(circlelist[:-1], 4 - len(choices))
        temp = set(full_choices)
        while len(temp) != 4:
            temp.add(random.choice(circlelist[:-1]))
        full_choices = list(temp)
        random.shuffle(full_choices)

        for k, v in full_choices:
            button = discord.ui.Button(label=f"{k} {v}", style=discord.ButtonStyle.primary)
            if (k, v) == self.choices[0]:
                button.callback = self.correct_callback_1
            elif (k, v) == self.choices[1]:
                button.callback = self.correct_callback_2
            else:
                button.callback = self.incorrect_callback
            self.add_item(button)

    async def correct_callback_1(self, interaction: discord.Interaction):
        if interaction.user.id in self.answered:
            if 1 in self.answered[interaction.user.id]:
                embed = functions.embed("Error: Already Attempted", color=0xff0000)
                embed.description = "You pressed the same circle two times in a row. Please wait until the next challenge to try again."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                self.failed.add(interaction.user.id)
                return
            self.answered[interaction.user.id].append(1)
        else:
            self.answered[interaction.user.id] = [1]
        
        if len(self.answered[interaction.user.id]) == 2:
            await self.completion(interaction)
        else:
            embed = functions.embed("Color Scope: Correct Color", color=0x61ff9b)
            embed.description = f"You successfully presed the `{self.choices[0][0]} {self.choices[0][1]}` circle.\nPress the `{self.choices[1][0]} {self.choices[1][1]}` circle to complete the challenge."
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def correct_callback_2(self, interaction: discord.Interaction):
        if interaction.user.id not in self.answered:
            embed = functions.embed("Error: Challenge Failed", color=0xff0000)
            embed.description = "You pressed the wrong circle. Please wait until the next challenge to try again."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            self.failed.add(interaction.user.id)
            return
        
        await self.completion(interaction)
    

class CSG4(CSG0):
    def __init__(self, cog, gametype, choices):
        super().__init__(cog)
        self.gametype = gametype
        self.choices = choices

        vals = [1, 0, 0, 0]
        random.shuffle(vals)
        color = circlelist[-1]
        for item in vals:
            if item == 1:
                button = discord.ui.Button(label=f"{color[0]} {color[1]}", style=discord.ButtonStyle.primary)
                button.callback = self.completion
            else:
                button = discord.ui.Button(label=f"{color[0]} {color[1]}", style=discord.ButtonStyle.primary)
                button.callback = self.incorrect_callback
            self.add_item(button)






class ColorScope(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        self.locked = False

        self.general = 1057437110132559974
        if self.bot.environment == "production":
            self.general = 982488812208930869

        self.cdb = self.bot.mdb["TrigBot"]["colorscope"]
        
        self.start_announcement.start()
        self.end_announcement.start()


    @tasks.loop(count=1)
    async def start_announcement(self, bypass=False):
        future = START
        if future - time.time() < 0: return
        if not bypass: await asyncio.sleep(future - time.time())

        embed = functions.embed("Color Scope", color=0x61ff9b)
        
        embed.description = f"Welcome to Color Scope.\nColor Scope is a hypercompetitive game with lots to win, and *so much more* to lose.\nChallenges will show up every so often in here.\nAll you need to do to win is follow the instructions that show up quickly.\nThe game starts now, and will last until <t:{END}:f>.\nUse `/leaderboard` to view your ranking.\nGood luck."
        channel = self.bot.get_channel(self.general) 
        await channel.send("@everyone", embed=embed)
        
    @tasks.loop(count=1)
    async def end_announcement(self, bypass=False):
        future = END
        if future - time.time() < 0: return
        if not bypass: await asyncio.sleep(future - time.time())

        embed = functions.embed("Color Scope", color=0x61ff9b)
        desc = "The Color Scope game has ended.\n"
        leaderboard = self.assemble_leaderboard()
        # get top person from leaderboard, accounting for ties
        top = leaderboard[0]
        if top[1] > 0:
            topcount = 1
            for i in range(1, len(leaderboard)):
                if leaderboard[i][1] == top[1]:
                    topcount += 1
                else:
                    break
            
            winners = leaderboard[:topcount]
            if topcount == 1:
                desc = desc + f"Congratulations to <@{top[0]}> for winning with {top[1]} points!\nThank you to everyone who participated."
            else:
                winstr = [f"<@{i[0]}>" for i in winners]
                winstr = ", ".join(winstr[:-1]) + f", and {winstr[-1]}"
                desc = desc + f"Congratulations to {winners} for winning with {top[1]} points each!\nThank you to everyone who participated."
            embed.description = desc
            general = self.bot.get_channel(self.general)
            await general.send("@everyone", embed=embed)
            for person in winners:
                embed = functions.embed("Color Scope", color=0x61ff9b)
                embed.description = f"**Congratulations!**\nYou won the Color Scope game with {top[1]} points!"
                user = self.bot.get_user(int(person[0]))
                try:
                    await user.send(embed=embed)
                except:
                    pass
        else:
            desc = desc + "No one won the game. Better luck next time!\nThank you to everyone who participated."
            embed.description = desc
            general = self.bot.get_channel(self.general)
            await general.send("@everyone", embed=embed)

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]


    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)
        if ctx.valid: return
        if message.author.bot: return
        if not message.guild: return
        if message.channel.id != self.general: return
        
        if self.locked: return

        if not(START <= time.time() <= END): return

        self.locked = True

        if self.bot.environment != "production":
            await asyncio.sleep(random.randint(60*3, 60*7))

        if self.bot.environment == "production" and message.content == "start_announcement":
            await self.start_announcement(bypass=True)
            self.locked = False
            return
        elif self.bot.environment == "production" and message.content == "end_announcement":
            await self.end_announcement(bypass=True)
            self.locked = False
            return
    

        gametype = random.choices([1, 2, 3, 4], weights=[4, 3, 2, 1], k=1)[0]
        embed = functions.embed("Color Scope: New Challenge", color=0x61ff9b)
        # get all items in circles
        
        if gametype == 1:
            choices = random.sample(circlelist[:-1], 1)
            embed.description = "**Single Circle**\nPress the following circle:"
        elif gametype == 2:
            choices = random.sample(circlelist[:-1], 2)
            embed.description = "**Double Circle**\nPress the following circles in any order:"
        elif gametype == 3:
            choices = random.sample(circlelist[:-1], 2)
            embed.description = "**Double Circle**\nPress the following circles in the following order:"
        elif gametype == 4:
            choices = [circlelist[-1]]
            embed.description = "**Single Circle**\nPress the following circle:"

        for k, v in choices:
            embed.description += f"\n`{k} {v}`"

        if gametype == 1:
            view = CSG1(self, gametype, choices)
        elif gametype == 2:
            view = CSG2(self, gametype, choices)
        elif gametype == 3:
            view = CSG3(self, gametype, choices)
        elif gametype == 4:
            view = CSG4(self, gametype, choices)

        temp = await message.channel.send(embed=embed, view=view)
        await asyncio.sleep(10)
        if not view.finished:
            embed = functions.embed("Color Scope: Challenge Failed", color=0xff0000)
            if view.top_failed:
                embed.description = f"Nobody completed the challenge in time.\n<@{view.top}> lost their streak of {view.top_points} points.\nPlease wait until the next one to try again."
                data = self.cdb.find_one({"_id": "stats"})
                data["streakholder"] = 0
                self.cdb.update_one({"_id": "stats"}, {"$set": data})
            else:
                embed.description = "Nobody completed the challenge in time. Please wait until the next one to try again."
            await temp.edit(embed=embed, view=None) 
            self.locked = False

    def assemble_leaderboard(self):
        leaderboard = []
        for data in self.cdb.find():
            if "points" in data:
                leaderboard.append([data["_id"], data["points"]])
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        return leaderboard

    @app_commands.command(name="leaderboard")
    @app_commands.describe(user="The user to get the rank for")
    async def leaderboard(self, inter: discord.Interaction, user: discord.Member = None):
        if not user:
            # get top 10
            leaderboard = self.assemble_leaderboard()[:10]
            embed = functions.embed("Color Scope: Leaderboard", color=0x61ff9b)
            embed.description = "The top 10 players in Color Scope are:"
            for i, item in enumerate(leaderboard):
                embed.description += f"\n`{i+1}.` <@{item[0]}> - `{item[1]}`"
            await inter.response.send_message(embed=embed)
        else:
            leaderboard = self.assemble_leaderboard()
            for i, item in enumerate(leaderboard):
                if str(item[0]) == str(user.id):
                    embed = functions.embed("Color Scope: Leaderboard", color=0x61ff9b)
                    embed.description = f"<@{user.id}> is ranked `#{i+1}` with `{item[1]}` point{'s' if abs(item[1]) != 1 else ''}."
                    await inter.response.send_message(embed=embed)
                    return
            embed = functions.embed("Color Scope: Leaderboard", color=0x61ff9b)
            embed.description = f"<@{user.id}> is not ranked yet."
            await inter.response.send_message(embed=embed)


    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ColorScope(bot))