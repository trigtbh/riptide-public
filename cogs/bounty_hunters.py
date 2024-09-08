# DNI

import discord
from discord import app_commands
from discord.ext import commands, tasks
import settings

from typing import *

import functions
import random
import asyncio
import os
import time

class BH(commands.Cog):
    group = app_commands.Group(name="bh", description="All Bounty Hunters commands")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        self.db = self.bot.mdb["TrigBot"]["bountyhunters"]

        self.game_end.start()

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]
    
    def get_server_data(self, id_):
        data = self.db.find_one({"_id": id_})
        if not data:
            return None
        return data
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != 424991711564136448: return
        if message.content == ">528491":
            ...

    @tasks.loop(count=1)
    async def game_end(self):
        while True:
            x = []
            for data in self.db.find():
                x.append(data["_id"])
            if len(x) == 0:
                await asyncio.sleep(60)
                continue
            x = sorted(x, key=lambda id_: self.db[id_]["run_until"])
            current = x[0]
            future = current["run_until"]
            if future - time.time() > 0:             
                await asyncio.sleep(future - time.time())

            msg = "Bounty Hunters has ended!"
            max_score = 0
            max_score_users = []
            for key, value in current.items():
                if not key.isdigit(): continue
                if value > max_score:
                    max_score = value
                    max_score_users = [key]
                elif value == max_score and max_score != 0:
                    max_score_users.append(key)

            if len(max_score_users) > 1:
                msg = msg + "\nThe winners are ", + ", ".join(f"<@{i}>" for i in max_score_users) + "!"
            elif len(max_score_users) == 1:
                msg = msg + f"\nThe winner is <@{max_score_users[0]}>"
            else:
                msg = msg + "\nNobody won this time."

            channel = self.bot.get_channel(current["general"])
            try:
                await channel.send(msg)
            except:
                pass
            self.db.delete_one({"_id": str(current["_id"])})


            

    @group.command(name="info")
    async def get_info(self, inter: discord.Interaction):
        if not inter.guild_id:
            e = functions.error("No Data Found", "Bounty Hunters has not been set up for this server yet.")
            return await inter.response.send_message(embed=e)
        d = self.get_server_data(inter.guild_id)
        embed = functions.embed("Bounty Hunters Info", color=0xfc7b03)
        desc = f"**Bounty Hunters is running until <t:{d['run_until']}:f>**\n"
        if str(inter.user.id) not in d:
            desc = desc + "**Your points: **0\n"
        else:
            desc = desc + "**Your points: **" + str(d[str(inter.user.id)]) + "\n"
        desc = desc + "\n"
        if not d['streak_holder']:
            desc = desc + "**Streak holder: **None\n"
        else:
            desc = desc + f"**Streak holder: ** <@{d['streak_holder']}>\n"
            desc = desc + "**Current streak: ** " + str(d['streak'])

        desc = desc.strip()

        embed.description = desc

        return await inter.response.send_message(embed=embed)
    

    @group.command(name="leaderboard")
    async def get_leaderboard(self, inter: discord.Interaction):
        if not inter.guild_id:
            e = functions.error("No Data Found", "Bounty Hunters has not been set up for this server yet.")
            return await inter.response.send_message(embed=e)
        d = self.get_server_data(inter.guild_id)
        await inter.response.defer()
        find = [k for k in d.keys() if k.isdigit()]
        find2 = {k: d[k] for k in find}
        x = list(find2.keys())
        n = sorted(find2.items(), key=lambda x: x[1], reverse=True)
        desc = ""
        if len(n) == 0:
            desc = "No leaderboard data available."
        else:
            desc = "**Top 10:*"
            for i, kv in enumerate(n[:10]):
                desc = f"**{i+1}: ** <@{kv[0]}> ({kv[1]} points)\n"
            if str(inter.user.id) not in x:
                desc = desc + "-----\nYou currently do not have any points."
            else:
                index = x.index(str(inter.user.id))
                points = find2[str(inter.user.id)]
                desc = desc + f"-----\n**Your place: **#{index + 1} ({points} point{'s' if abs(points) == 1 else ''})"
        embed = functions.embed("Bounty Hunters Leaderboard", color=0xfc7b03)
        embed.description = desc
        await inter.followup.send(embed=embed)    

    
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BH(bot))