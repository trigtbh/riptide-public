import discord
from discord import app_commands
from discord.ext import commands, tasks
import settings
import asyncio

from typing import *

import functions
from typing import *
import random
import os
import time

START = 1681012800
END = START + (24 * 60 * 60)

# START = time.time() + 10
# END = START + 60


class Easter(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        self.edb = self.bot.mdb["TrigBot"]["easter"]

        self.announcement_channel = 1057437109746663516
        self.general_channel = 1057437110132559974

        # self.announcement_channel = 1013140530890285168
        # self.general_channel = 982488812208930869

        self.reactions = []
        self.reaction_ids = []
        guild = self.bot.get_guild(982488812208930866)
        for emote in guild.emojis:
            if emote.name.startswith("egg_"):
                self.reactions.append(emote)
                self.reaction_ids.append(emote.id)

        self.first_announcement.start()
        self.second_announcement.start()

        
    @tasks.loop(count=1)
    async def first_announcement(self):
        future = START
        if future - time.time() < 0: return
        await asyncio.sleep(future - time.time())

        channel = self.bot.get_channel(self.announcement_channel) # TODO: replace with announcement channel id
        embed = functions.embed("Easter Egg Hunt", color=0x45ff76)
        embed.description = """The Easter Egg Hunt has begun! Wherever you see a colored egg emoji, react with it to collect an egg for your egg basket!

Use `/eggs` to view your egg basket, and `/eggs @user` to view someone else's egg basket.

The event will end on <t:1681099200:f>. Happy hunting!
<:egg_red:1092627296025853993> <:egg_orange:1092627292896895006> <:egg_yellow:1092627296835346544> <:egg_green:1092627291298861147> <:egg_blue:1092627289398845550> <:egg_purple:1092627293551214694>"""
        await channel.send("@everyone", embed=embed)

    @tasks.loop(count=1)
    async def second_announcement(self):
        future = END
        if future - time.time() < 0: return
        await asyncio.sleep(future - time.time())

        channel = self.bot.get_channel(self.announcement_channel) # TODO: replace with announcement channel id
        embed = functions.embed("Easter Egg Hunt", color=0x45ff76)
        # find maximum score, but if theres a tie then create a list of all the people with the max score
        max_score = 0
        max_score_users = []
        for user in self.edb.find():
            if user["eggs"] > max_score:
                max_score = user["eggs"]
                max_score_users = [user["_id"]]
            elif user["eggs"] == max_score and max_score != 0:
                max_score_users.append(user["_id"])
        if len(max_score_users) == 1:
            emoji = random.choice(self.reactions)
            embed.description = f"""The Easter Egg Hunt has ended!\nThe winner is <@{max_score_users[0]}> with {max_score} egg{'s' if max_score != 1 else ''}!\n""" + f"<:{emoji.name}:{emoji.id}>"
        elif len(max_score_users) > 1:
            emoji = random.choice(self.reactions)
            embed.description = f"""The Easter Egg Hunt has ended!\nThe winners are {', '.join([f'<@{user}>' for user in max_score_users])} with {max_score} eggs!\n""" + f"<:{emoji.name}:{emoji.id}>"
        else:
            embed.description = "The Easter Egg Hunt has ended! No one won this time."
        await channel.send("@everyone", embed=embed)

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild: return
        if message.author.bot: return
        if not START <= time.time() <= END: return

        if message.channel.id != self.general_channel: return # TODO: replace with real channel id
        
        if random.random() * 100 <= 6.5:
            await message.add_reaction(random.choice(self.reactions))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if not START <= time.time() <= END: return
        if not payload.guild_id: return
        if payload.user_id == self.bot.user.id: return
        if payload.emoji.id not in self.reaction_ids: return
        if payload.member.bot: return

        user = self.bot.get_user(payload.user_id)
        if not user: return

        if not self.edb.find_one({"_id": user.id}):
            self.edb.insert_one({"_id": user.id, "eggs": 1})
        else:
            self.edb.update_one({"_id": user.id}, {"$inc": {"eggs": 1}})

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if not START <= time.time() <= END: return
        if not payload.guild_id: return
        if payload.user_id == self.bot.user.id: return
        if payload.emoji.id not in self.reaction_ids: return

        user = self.bot.get_user(payload.user_id)
        if not user: return

        if not self.edb.find_one({"_id": user.id}):
            self.edb.insert_one({"_id": user.id, "eggs": 0})
        else:
            self.edb.update_one({"_id": user.id}, {"$inc": {"eggs": -1}})

    @app_commands.command(name="eggs")
    async def eggs(self, inter: discord.Interaction, user: Optional[discord.Member]) -> None:
        """View your egg basket! \nPart of the Easter Egg Hunt event"""
        if not START <= time.time() <= END:
            embed = functions.embed("Error: Event Not Active", color=0xff0000)
            embed.description = "This command is for the Easter Egg Hunt, which is not active at this moment."
            return await inter.response.send_message(embed=embed, ephemeral=True)
        
        if not inter.guild: return
        if inter.user.bot: return

        if user:
            id = user.id
            if user.bot:
                embed = functions.embed("Error: Invalid User", color=0xff0000)
                embed.description = "You cannot view the inventory of a bot, as they are not participating in the event."
                return await inter.response.send_message(embed=embed, ephemeral=True)
        else:
            id = inter.user.id

        data = self.edb.find_one({"_id": id})
        if not data:
            data = {"_id": id, "eggs": 0}
            self.edb.insert_one(data)
        egg_basket = data["eggs"]
        e = random.randint(0, len(self.reactions) - 1)
        emote_name = self.reactions[e].name
        emote_id = self.reactions[e].id
        if not user:
            embed = functions.embed(f"Your Egg Basket", color=0x45ff76)
            embed.description = f"<:{emote_name}:{emote_id}> You have **{egg_basket} egg{'s' if egg_basket != 1 else ''}** in your basket."
        else:
            embed = functions.embed(f"{user.name}'s Egg Basket", color=0x45ff76)
            embed.description = f"<:{emote_name}:{emote_id}> <@{user.id}> has **{egg_basket} egg{'s' if egg_basket != 1 else ''}** in their basket."
        return await inter.response.send_message(embed=embed)
        
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Easter(bot))