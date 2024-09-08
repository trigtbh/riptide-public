# DNI
import discord
from discord import app_commands
from discord.ext import commands
import settings

from typing import *

import functions
import random

NAME = "Admin"
DESCRIPTION = "Admin commands to manage other users, as well as the bot"

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()  # this is now required in this context
        self.NAME = NAME
        self.DESCRIPTION = DESCRIPTION
        
    #cog_group = app_commands.Group(name="cog", description="...")

    # @app_commands.command(name="test")
    # async def test(self, interaction: discord.Interaction) -> None:
    #     """ Test command"""
    #     await interaction.response.send_message("Test")

    # @cog_group.command(name="disable")
    # @app_commands.describe(cog="The cog to disable")
    # async def disable(self, interaction: discord.Interaction, cog: str) -> None:
    #     """ Disables all commands within a cog. Admins are still allowed to run disabled commands"""
    #     disabled = self.bot.mdb["TrigBot"]["settings"]
    #     within = disabled.find_one({"_id": interaction.guild_id})

    #     if cog not in self.bot.cog_names:
    #         embed = functions.embed("Error: Invalid Cog", color=0xff0000)
    #         embed.description = "That cog does not exist.\n\nUse `/cogs` to see a list of cogs."
    #         await interaction.response.send_message(embed=embed, ephemeral=True)
    #         return
    #     name = self.bot.cog_names[cog]
    #     if name == "Admin":
    #         embed = functions.embed("Error: Invalid Cog", color=0xff0000)
    #         embed.description = "The admin cog cannot be disabled."
    #         await interaction.response.send_message(embed=embed, ephemeral=True)
    #         return
    #     if within:
    #         if cog in within["disabled_cogs"]:
    #             embed = functions.embed("Error: Cog Already Disabled", color=0xff0000)
    #             embed.description = "This cog is already disabled."
    #             await interaction.response.send_message(embed=embed, ephemeral=True)
    #             return
    #         disabled.update_one({"_id": interaction.guild_id}, {"$push": {"disabled_cogs": cog}})
    #     else:
    #         disabled.insert_one({"_id": interaction.guild_id, "disabled_cogs": [cog]})
    #     embed = functions.embed("Success!", color=0x00ff00)
    #     embed.description = f"Disabled the `{name}` cog."
    #     await interaction.response.send_message(embed=embed)
    
    # @cog_group.command(name="enable")
    # @app_commands.describe(cog="The cog to enable")
    # async def enable(self, interaction: discord.Interaction, cog: str) -> None:
    #     """ Enables a cog"""
    #     disabled = self.bot.mdb["TrigBot"]["settings"]
    #     within = disabled.find_one({"_id": interaction.guild_id})

    #     if cog not in self.bot.cog_names:
    #         embed = functions.embed("Error: Invalid Cog", color=0xff0000)
    #         embed.description = "That cog does not exist.\n\nUse `/cogs` to see a list of cogs."
    #         await interaction.response.send_message(embed=embed, ephemeral=True)
    #         return
    #     name = self.bot.cog_names[cog]
    #     if name == "Admin":
    #         embed = functions.embed("Error: Invalid Cog", color=0xff0000)
    #         embed.description = "The admin cog cannot be disabled."
    #         await interaction.response.send_message(embed=embed, ephemeral=True)
    #         return
    #     if within:
    #         if cog not in within["disabled_cogs"]:
    #             embed = functions.embed("Error: Cog Already Enabled", color=0xff0000)
    #             embed.description = "This cog is already enabled."
    #             await interaction.response.send_message(embed=embed, ephemeral=True)
    #             return
    #         disabled.update_one({"_id": interaction.guild_id}, {"$pull": {"disabled_cogs": cog}})
    #     else:
    #         disabled.insert_one({"_id": interaction.guild_id, "disabled_cogs": [cog]})
    #     embed = functions.embed("Success!", color=0x00ff00)
    #     embed.description = f"Enabled the `{name}` cog."
    #     await interaction.response.send_message(embed=embed)

    # @cog_group.command(name="info")
    # @app_commands.describe(cog="The cog to see all commands for")
    # async def cogs(self, interaction: discord.Interaction, cog: Optional[str]) -> None:
    #     """View information about all cogs, or a specific cog"""
    #     if cog:
    #         if cog not in self.bot.nti:
    #             embed = functions.embed("Error: Invalid Cog", color=0xff0000)
    #             embed.description = "That cog does not exist.\nUse `/cogs` to see a list of cogs."
    #             await interaction.response.send_message(embed=embed, ephemeral=True)
    #             return
            
    #         embed = functions.embed(f"Cog: {cog}", color=0x00ff00)
    #         embed.description = f"**{self.bot.cog_names[cog]}**\n{self.bot.cog_descriptions[self.bot.cog_names[cog]]}\n"
            
            



    #         await interaction.response.send_message(embed=embed)

    #     disabled = self.bot.mdb["TrigBot"]["settings"]
    #     within = disabled.find_one({"_id": interaction.guild_id})
    #     disabled_cogs = []

    #     if within:
    #         if "disabled_cogs" in within:
    #             disabled_cogs = within["disabled_cogs"]


    #     enabled_cogs = [c for c in self.bot.cog_names if c not in disabled_cogs]
    #     embed = functions.embed("Cog List", color=0x00ff00)
        
    #     desc = "**Enabled Cogs:**\n"
    #     if enabled_cogs:
    #         for c in enabled_cogs:
    #             desc += f" - `{c}`: {self.bot.cog_descriptions[self.bot.cog_names[c]]}\n"
    #     else:
    #         desc += "None\n"
    #     desc += "\n**Disabled Cogs:**\n"
    #     if disabled_cogs:
    #         for c in disabled_cogs:
    #             desc += f" - `{c}`: {self.bot.cog_descriptions[self.bot.cog_names[c]]}\n"
    #     else:
    #         desc += "None\n"
    #     embed.description = desc
    #     await interaction.response.send_message(embed=embed)




async def setup(bot: commands.Bot) -> None:
    #await bot.add_cog(Admin(bot))
    ...