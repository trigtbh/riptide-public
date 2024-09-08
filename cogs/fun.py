import discord
from discord import app_commands
from discord.ext import commands
import settings
import json

from typing import *

import functions
import random

import os

import aiohttp
import html

class TriviaView(discord.ui.View):
    def __init__(self, inter, answers: List[str], correct: str, difficulty, embed: discord.Embed, bot, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.inter = inter
        self.answers = answers
        self.correct = correct
        self.value = None
        self.timeout = timeout
        self.responded = False
        self.embed = embed
        self.bot = bot
        self.difficulty = difficulty

        for i, answer in enumerate(answers):
            button = discord.ui.Button(label=answer, custom_id=str(i))
            button.callback = self.button_callback
            self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.inter.user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You are not the user who started this trivia session.\nIf you would like to play, use `/trivia`."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        if self.responded:
            return
        # change correct button to green
        for item in self.children:
            if item.label == self.correct:
                item.style = discord.ButtonStyle.success
            item.disabled = True

        embed = functions.embed("Trivia: Timeout!", color=0xff0000)
        embed.description = f"Time's up! The correct answer was **{html.unescape(self.correct)}**."
        await self.inter.edit_original_response(embed=embed, view=self)
    
    async def button_callback(self, interaction: discord.Interaction):
        value = int(interaction.data["custom_id"])
        answer = self.answers[int(value)]
        won = False
        if answer == self.correct:
            embed = functions.embed("Trivia: Correct!", color=0x34eb7d)
            embed.description = f"That's correct! The answer was **{html.unescape(self.correct)}**."
            won = True
            for item in self.children:
                if item.label == answer:
                    item.style = discord.ButtonStyle.success
        else:
            embed = functions.embed("Trivia: Incorrect!", color=0xff0000)
            embed.description = f"That's incorrect! The answer was **{html.unescape(self.correct)}**."
            won = False
            # change selected button to red, correct button to green
            for item in self.children:
                if item.label == answer:
                    item.style = discord.ButtonStyle.danger
                if item.label == self.correct:
                    item.style = discord.ButtonStyle.success

        # check if economy cog has been enabled in the server
        disabled = self.bot.mdb["TrigBot"]["settings"]
        within = disabled.find_one({"_id": interaction.guild_id})
        give = True
        if within:
            if "economy" in within["disabled_cogs"]:
                give = False
        if give:
            # generate blank entry for user if it doesn't exist
            if not self.bot.mdb["TrigBot"]["economy"].find_one({"_id": interaction.user.id}):
                self.bot.mdb["TrigBot"]["economy"].insert_one({'_id': interaction.user.id, 'balance': 0, 'low_stock': 0, 'med_stock': 0, 'high_stock': 0, 'daily_delay': 0})
            # give user coins based on difficulty
            if won:
                if self.difficulty == "easy":
                    self.bot.mdb["TrigBot"]["economy"].update_one({"_id": interaction.user.id}, {"$inc": {"balance": 15}})
                    embed.description += "\nYou have been awarded **15** coins for getting the question correct!"
                elif self.difficulty == "medium":
                    self.bot.mdb["TrigBot"]["economy"].update_one({"_id": interaction.user.id}, {"$inc": {"balance": 25}})
                    embed.description += "\nYou have been awarded **25** coins for getting the question correct!"
                elif self.difficulty == "hard":
                    self.bot.mdb["TrigBot"]["economy"].update_one({"_id": interaction.user.id}, {"$inc": {"balance": 50}})
                    embed.description += "\nYou have been awarded **50** coins for getting the question correct!"
            else:
                embed.description += "\nYou have not been awarded any coins for getting the question incorrect."
            


        self.responded = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

class HigherLower(discord.ui.View):
    def __init__(self, cog, uuid, value, target):
        super().__init__(timeout=30)
        self.cog = cog
        self.uuid = uuid
        self.value = value
        self.target = target
        self.responded = False

        higher_button = discord.ui.Button(label="Higher", custom_id="higher", emoji="⬆️")
        higher_button.callback = self.button_callback
        self.add_item(higher_button)

        lower_button = discord.ui.Button(label="Lower", custom_id="lower", emoji="⬇️")
        lower_button.callback = self.button_callback
        self.add_item(lower_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.uuid:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You are not the user who started this game.\nIf you would like to play, use `/higher-lower`."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False

        return True
    
    async def on_timeout(self) -> None:
        if self.responded:
            return
        embed = functions.embed("Higher Lower: Timeout!", color=0xff0000)
        embed.description = f"Time's up! The correct answer was **{'lower' if self.value < self.target else 'higher'}** ({self.value})."
        embed.description += f"\nYou lost your win streak of **{self.cog.hl_wins[self.uuid]} game{'s' if self.cog.hl_wins[self.uuid] != 1 else ''}**.\nUse `/higher-lower` to play again."
            
        self.cog.hl_wins[self.uuid] = 0
        self.cog.hl_numbers[self.uuid] = 50
        for item in self.children:
            item.disabled = True
        await self.inter.edit_original_response(embed=embed, view=self)

    async def button_callback(self, interaction: discord.Interaction):
        value = interaction.data["custom_id"]
        if value == "higher":
            if self.value > self.target:
                embed = functions.embed("Higher Lower: Correct!", color=0x34eb7d)
                embed.description = f"That's correct! The number was **{value}** ({self.value} > {self.target})."
                won = True
            else:
                embed = functions.embed("Higher Lower: Incorrect!", color=0xff0000)
                embed.description = f"That's incorrect! The number was **lower** ({self.value} < {self.target})."
                won = False
        else:
            if self.value < self.target:
                embed = functions.embed("Higher Lower: Correct!", color=0x34eb7d)
                embed.description = f"That's correct! The number was **{value}** ({self.value} < {self.target})."
                won = True
            else:
                embed = functions.embed("Higher Lower: Incorrect!", color=0xff0000)
                embed.description = f"That's incorrect! The number was **higher** ({self.value} > {self.target}). "
                won = False

        self.responded = True
        for item in self.children:
            item.disabled = True
            if won:
                if item.label.lower() == value.lower():
                    item.style = discord.ButtonStyle.success
            else:
                if item.label.lower() == value.lower():
                    item.style = discord.ButtonStyle.danger

        if won:
            if self.uuid not in self.cog.hl_wins:
                self.cog.hl_wins[self.uuid] = 0
            self.cog.hl_wins[self.uuid] += 1
            embed.description += f"\nYou now have a win streak of **{self.cog.hl_wins[self.uuid]} game{'s' if self.cog.hl_wins[self.uuid] != 1 else ''}**!\nUse `/higher-lower` to play again."
            self.cog.hl_numbers[self.uuid] = self.value
        else:
            embed.description += f"\nYou lost your win streak of **{self.cog.hl_wins[self.uuid]} game{'s' if self.cog.hl_wins[self.uuid] != 1 else ''}**.\nUse `/higher-lower` to play again."
            self.cog.hl_wins[self.uuid] = 0
            self.cog.hl_numbers[self.uuid] = 50

        await interaction.response.edit_message(embed=embed, view=self)



class Fun(commands.Cog):
    """Fun commands to play around with!"""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        self.hl_numbers = {}
        self.hl_wins = {}

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]
        
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

    @app_commands.command(name="ship")
    @app_commands.describe(user1="The first user to ship", user2="The second user to ship")
    async def ship(self, interaction: discord.Interaction, user1: str, user2: str) -> None:
        """Ships two users together """
        val = abs(hash("".join(sorted(str(user1) + str(user2)))))
        if random.random() < 0.1:
            val = round(val / 10, 3) # less than 10%
        if random.random() == 1.0:
            val = 100.000
        
        compat = round(val / (10 ** len(str(val))) * 100, 3)
        ratings = ["Never happening", "Awful", "Horrible", "Bad", "Not great", "Decent", "Fine", "Good", "Great", "Perfect"]
        embed = functions.embed("Ship", color=0xeb7d34)
        
        embed.description = f"**{user1} + {user2}**\n\nCompatibility: `{compat}%`\nRating: **{ratings[int(compat // 10)]}**"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cute")
    @app_commands.describe(user="The user to rate")
    async def cute(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Rates a user's cuteness """
        random.seed(hash(user.guild_avatar or user.avatar))
        embed = functions.embed("Cuteness rating", color=0xeb7d34)
        #if user.id == interaction.guild.owner.id:
        if user.guild_permissions.administrator:
            perc = "200.00"
        else:
            perc = str(random.randint(5000, 10000) / 100)
        avatar = (user.guild_avatar or user.avatar).url
        embed.set_thumbnail(url=avatar)
        embed.description = "<@" + str(user.id) + "> is **`" + perc + "%`** cute!"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rate")
    @app_commands.describe(thing="The thing to rate")
    async def rate(self, interaction: discord.Interaction, thing: str) -> None:
        """Rates something"""
        random.seed(hash(thing))
        embed = functions.embed("Rating", color=0xeb7d34)
        perc = str(random.randint(0, 10000) / 100)
        embed.description = f"Rating on `{thing}`:\n**`" + perc + "%`**"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dog")
    async def dog(self, interaction: discord.Interaction) -> None:
        """Sends a random dog image"""
        embed = functions.embed("Dog", color=0xeb7d34)
        embed.description = "Here's a random dog image!"
        async with aiohttp.ClientSession() as session:
            async with session.get("https://dog.ceo/api/breeds/image/random") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed.set_image(url=data["message"])
                else:
                    embed.description = "There was an error getting a random dog image."
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="trivia")
    async def trivia(self, interaction: discord.Interaction) -> None:
        """Test your knowledge with a random trivia question!"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://opentdb.com/api.php?amount=1") as resp:
                if resp.status == 200:
                    data = json.loads(await resp.text())
                    
                else:
                    embed = functions.embed("Error", color=0xff0000)
                    embed.description = "There was an error getting a random trivia question."
                    return await interaction.response.send_message(embed=embed)
        question_data = data["results"][0]
        embed = functions.embed("Trivia", color=0xeb7d34)

        durations = {
            "easy": 15,
            "medium": 20,
            "hard": 25
        }

        delay = durations[html.unescape(question_data["difficulty"])]
        question = html.unescape(question_data["question"])
        category = html.unescape(question_data["category"])
        difficulty = html.unescape(question_data["difficulty"]).title()
        answers = question_data["incorrect_answers"] + [question_data["correct_answer"]]
        answers = [html.unescape(x) for x in answers]
        if len(answers) > 2:
            random.shuffle(answers)
        else:
            answers = ["True", "False"]
            question = "True or False: " + question
        embed.description = f"**Category**: {category}\n**Difficulty**: {difficulty}\n**Duration**: {delay} seconds\n\n{question}"
        
        view = TriviaView(interaction, answers, html.unescape(question_data["correct_answer"]), html.unescape(question_data["difficulty"]), embed, self.bot, timeout=delay)


        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="higher-lower")
    async def higher_lower(self, interaction: discord.Interaction) -> None:
        """Guess if a number will be higher or lower than a target value!"""
        uuid = interaction.user.id
        if uuid not in self.hl_numbers:
            self.hl_numbers[uuid] = 50
        if uuid not in self.hl_wins:
            self.hl_wins[uuid] = 0
        
        target = self.hl_numbers[uuid]

        value = random.randint(1, 100)
        while value == target:
            value = random.randint(1, 100)


        embed = functions.embed("Higher or Lower", color=0xeb7d34)
        embed.description = f"I've chosen a random number between 1 and 100.\nDo you think this number is *higher* or *lower* than **{target}**?"
        view = HigherLower(self, uuid, value, target)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Fun(bot))
