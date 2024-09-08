import discord
from discord import app_commands
from discord.ext import commands
import settings

from typing import *

import functions
import random
import os
import time

class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        self.steal_cooldown = {}

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]

    def generate_blank(self, uuid):
        return {'_id': uuid, 'balance': 0, 'low_stock': 0, 'med_stock': 0, 'high_stock': 0, 'daily_delay': 0}

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
    
    @app_commands.command(name="balance")
    @app_commands.describe(user="The user to check the balance of")
    async def balance(self, interaction: discord.Interaction, user: discord.Member = None) -> None:
        """Checks the balance of a user. If no user is specified, it will check the balance of the user who ran the command"""
        if not user:
            user = interaction.user
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(user.id))

        embed = functions.embed("Balance", color=0x7f2a3c )
        bal = self.bot.mdb['TrigBot']['economy'].find_one({'_id': user.id})['balance']
        embed.description = f"{user.mention} has **{bal}** coin" + ("s" if bal != 1 else "") 
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily")
    async def daily(self, interaction: discord.Interaction) -> None:
        """Recieve 25 coins every 24 hours"""
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(interaction.user.id))

        user = self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})
        if user['daily_delay'] > time.time():
            embed = functions.embed("Error: Daily Delay", color=0xff0000)
            delay = user['daily_delay'] - time.time()
            embed.description = f"You can use this command again in **{functions.readabledt(delay * 1000)}**"
            await interaction.response.send_message(embed=embed)
            return

        self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': 25}, '$set': {'daily_delay': time.time() + 86400}})
        embed = functions.embed("Daily", color=0x7f2a3c )
        embed.description = f"You have received **25** coins!"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="give")
    @app_commands.describe(user="The user to give coins to", amount="The amount of coins to give")
    async def give(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        """Give coins to another user"""
        if user.id == interaction.user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You cannot give coins to yourself."
            await interaction.response.send_message(embed=embed)
            return
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(interaction.user.id))
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(user.id))

        if amount < 1:
            embed = functions.embed("Error: Invalid Amount", color=0xff0000)
            embed.description = "You cannot give less than 1 coin."
            await interaction.response.send_message(embed=embed)
            return

        userdata = self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})
        if userdata['balance'] < amount:
            embed = functions.embed("Error: Insufficient Funds", color=0xff0000)
            embed.description = "You do not have enough coins to give.\nUse `/balance` to check your current balance."
            await interaction.response.send_message(embed=embed)
            return

        self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': -amount}})
        self.bot.mdb['TrigBot']['economy'].update_one({'_id': user.id}, {'$inc': {'balance': amount}})
        embed = functions.embed("Coins Delivered", color=0x7f2a3c )
        embed.description = f"You gave {user.mention} **{amount}** coin" + ("s" if amount != 1 else "")
        await interaction.response.send_message(embed=embed)

        embed = functions.embed("Coins Received", color=0x7f2a3c)
        embed.description = f"{interaction.user.mention} gave you **{amount}** coin" + ("s" if amount != 1 else "")
        try:
            await user.send(embed=embed)
        except:
            pass

    @app_commands.command(name="steal")
    @app_commands.describe(user="The user to steal coins from")
    async def steal(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Steal coins from another user. If the target user is online, you have a 50% chance of failing, which comes with a 75% chance of losing coins"""
        if user.id == interaction.user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You cannot steal coins from yourself."
            await interaction.response.send_message(embed=embed)
            return
        if user.bot:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You cannot steal coins from a bot."
            await interaction.response.send_message(embed=embed)
            return
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(interaction.user.id))
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(user.id))

        ucopy = user
        user = self.bot.mdb['TrigBot']['economy'].find_one({'_id': user.id})
        if user['balance'] < 1:
            embed = functions.embed("Error: Insufficient Funds", color=0xff0000)
            embed.description = "This user does not have enough coins to steal.\nUse `/balance` to check their current balance."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if interaction.user.id in self.steal_cooldown:
            if time.time() - self.steal_cooldown[interaction.user.id] < (60 * 60):
                dt = self.steal_cooldown[interaction.user.id] + (60 * 60) - time.time()
                embed = functions.embed("Error: Cooldown", color=0xff0000)
                embed.description = f"You cannot steal coins from another user for **{functions.readabledt(dt * 1000)}**."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            else:
                self.steal_cooldown[interaction.user.id] = time.time()
        else:
            self.steal_cooldown[interaction.user.id] = time.time()

        if random.randint(1, 100) > 50 and ucopy.status != discord.Status.offline:
            embed = functions.embed("Error: Failed Steal", color=0xff0000)
            embed.description = "You failed to steal any coins from this user."
            balance = self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})
            if random.randint(1, 100) > 25 and balance['balance'] > 1:
                dec = random.randint(1, balance['balance'])
                self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': -dec}})
                embed.description += f"\nYou lost **{dec}** coin" + ("s" if dec != 1 else "") + " in the process."
            await interaction.response.send_message(embed=embed)
            return

    
        amount = random.randint(1, user['balance'])
        self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': amount}})
        self.bot.mdb['TrigBot']['economy'].update_one({'_id': ucopy.id}, {'$inc': {'balance': -amount}})
        embed = functions.embed("Coins Stolen", color=0x7f2a3c )
        embed.description = f"You stole **{amount}** coin" + ("s" if amount != 1 else "") + f" from {ucopy.mention}"
        await interaction.response.send_message(embed=embed)

        embed = functions.embed("Coins Stolen", color=0x7f2a3c)
        embed.description = f"{interaction.user.mention} stole **{amount}** coin" + ("s" if amount != 1 else "") + " from you!"
        try:
            await ucopy.send(embed=embed)
        except:
            pass

        

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot))