import discord
from discord import app_commands
from discord.ext import commands
import functions
import os
from pytimeparse.timeparse import timeparse
import datetime

from typing import *

class Admin(commands.Cog):
    """Administrator commands to manage other users, as well as the bot"""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]
        
    group = app_commands.Group(name="cog", description="...")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Checks if the user is an admin"""
        if not interaction.guild_id:
            embed = functions.embed("Error: Invalid Location", color=0xff0000)
            embed.description = "This command can only be used in a server."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if interaction.user.guild_permissions:
            if interaction.user.guild_permissions.administrator:
                return True
        embed = functions.embed("Error: Insufficient Permissions", color=0xff0000)
        embed.description = "You must be an administrator to use this command."
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False

    @group.command(name="disable")
    @app_commands.describe(cog="The cog to disable")
    async def disable(self, interaction: discord.Interaction, cog: str) -> None:
        """ Disables all commands within a cog. Admins are still allowed to run disabled commands"""
        disabled = self.bot.mdb["TrigBot"]["settings"]
        within = disabled.find_one({"_id": interaction.guild_id})

        if cog not in self.bot.cog_names:
            embed = functions.embed("Error: Invalid Cog", color=0xff0000)
            embed.description = "That cog does not exist.\n\nUse `/cogs` to see a list of cogs."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if cog in ["admin", "other"]:
            embed = functions.embed("Error: Invalid Cog", color=0xff0000)
            embed.description = f"The `{cog}` cog cannot be disabled."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if within:
            if cog in within["disabled_cogs"]:
                embed = functions.embed("Error: Cog Already Disabled", color=0xff0000)
                embed.description = "This cog is already disabled."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            disabled.update_one({"_id": interaction.guild_id}, {"$push": {"disabled_cogs": cog}})
        else:
            disabled.insert_one({"_id": interaction.guild_id, "disabled_cogs": [cog]})
        embed = functions.embed("Success!", color=0x00ff00)
        embed.description = f"Disabled the `{cog}` cog."
        await interaction.response.send_message(embed=embed)
    
    @group.command(name="enable")
    @app_commands.describe(cog="The cog to enable")
    async def enable(self, interaction: discord.Interaction, cog: str) -> None:
        """ Enables a cog"""
        disabled = self.bot.mdb["TrigBot"]["settings"]
        within = disabled.find_one({"_id": interaction.guild_id})

        if cog not in self.bot.cog_names:
            embed = functions.embed("Error: Invalid Cog", color=0xff0000)
            embed.description = "That cog does not exist.\n\nUse `/cogs` to see a list of cogs."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if within:
            if cog not in within["disabled_cogs"]:
                embed = functions.embed("Error: Cog Already Enabled", color=0xff0000)
                embed.description = "This cog is already enabled."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            disabled.update_one({"_id": interaction.guild_id}, {"$pull": {"disabled_cogs": cog}})
        else:
            disabled.insert_one({"_id": interaction.guild_id, "disabled_cogs": [cog]})
        embed = functions.embed("Success!", color=0x00ff00)
        embed.description = f"Enabled the `{cog}` cog."
        await interaction.response.send_message(embed=embed)

    @group.command(name="info")
    @app_commands.describe(cog="The cog to see all commands for")
    async def cogs(self, interaction: discord.Interaction, cog: Optional[str]) -> None:
        """View information about all cogs, or a specific cog"""
        if cog:
            if cog not in self.bot.cog_names:
                embed = functions.embed("Error: Invalid Cog", color=0xff0000)
                embed.description = "That cog does not exist.\nUse `/cogs` to see a list of cogs."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            

            if cog in self.bot.mapped_cogs:
                c = self.bot.mapped_cogs[cog]      
                embed = functions.embed(f"Cog: {cog}", color=0x00ff00)
                embed.description = f"**{c.description or 'No description provided'}**\n"
                for command in c.walk_app_commands():
                    if command.parent:
                        embed.add_field(name=f"/{command.parent.name} {command.name}", value=command.description, inline=False)
                    else:
                        embed.add_field(name=f"/{command.name}", value=command.description, inline=False)
                return await interaction.response.send_message(embed=embed)

        disabled = self.bot.mdb["TrigBot"]["settings"]
        within = disabled.find_one({"_id": interaction.guild_id})
        disabled_cogs = []

        if within:
            if "disabled_cogs" in within:
                disabled_cogs = within["disabled_cogs"]


        enabled_cogs = [c for c in self.bot.cog_names if c not in disabled_cogs]
        embed = functions.embed("Cog List", color=0x00ff00)
        
        desc = "**Enabled Cogs:**\n"
        if enabled_cogs:
            for c in enabled_cogs:
                if c in self.bot.mapped_cogs:
                    desc += f" - `{c}`: {self.bot.mapped_cogs[c].description or 'No description provided'}\n"
        else:
            desc += "None\n"
        desc += "\n**Disabled Cogs:**\n"
        if disabled_cogs:
            for c in disabled_cogs:
                if c in self.bot.mapped_cogs:
                    desc += f" - `{c}`: {self.bot.mapped_cogs[c].description or 'No description provided'}\n"
        else:
            desc += "None\n"
        embed.description = desc
        await interaction.response.send_message(embed=embed)

    


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))