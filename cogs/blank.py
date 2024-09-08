# DNI

import discord
from discord import app_commands
from discord.ext import commands
import settings

from typing import *

import functions
import random
import os

class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MyCog(bot))