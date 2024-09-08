import discord
from discord import app_commands
from discord.ext import commands
import settings

from typing import *

import functions
import random

import os


class Other(commands.Cog):
    """Miscellaneous commands"""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()  # this is now required in this context.

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]

    @app_commands.command(name="ping")
    async def ping(self, interaction: discord.Interaction) -> None:
        """Display the bot's response time"""
        embed = functions.embed("Pong!", color=0x00ff00)
        embed.description = f"Response time: `{round(self.bot.latency * 1000)}ms`"
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="invite")
    async def invite(self, interaction: discord.Interaction) -> None:
        """Invite the bot to your server!"""
        embed = functions.embed("Invite", color=0x00ff00)
        embed.description = f"Want to invite Riptide to your server? [Click here!](https://discord.com/api/oauth2/authorize?client_id=1049021618019631195&permissions=8&scope=bot%20applications.commands)"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help")
    async def _help(self, interaction: discord.Interaction) -> None:
        """Get help with Riptide"""
        embed = functions.embed("Help", color=0x00ff00)
        embed.description = "Riptide is a community-centered bot that is perfect for all servers big and small!\nCommands are operated under groups called `cogs`.\nCogs can be disabled and enabled by admins using the `/cog disable` and `/cog enable` commands.\nAdmins can also view a list of available cogs using `/cog info`.\n\nIf you need help with anything, feel free to join the [support server](https://discord.gg/qUnf4WUCPR)!\n**This bot was made by <@424991711564136448>**"
        embed.set_thumbnail(url=str(self.bot.user.avatar))
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Other(bot))