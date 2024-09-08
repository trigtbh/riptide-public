import discord
from discord import app_commands
from discord.ext import commands
import settings

from typing import *

import functions
import random
import os
import datetime
from pytimeparse.timeparse import timeparse
import asyncio

class Moderation(commands.Cog):
    """Commands to help moderate other users"""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

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
        
        if interaction.user.guild_permissions.moderate_members:
            disabled = self.bot.mdb["TrigBot"]["settings"]
            within = disabled.find_one({"_id": interaction.guild_id})
            if within:
                if self.get_file_name() in within["disabled_cogs"]:
                    embed = functions.embed("Error: Command Disabled", color=0xff0000)
                    embed.description = f"This command is part of the `{self.get_file_name()}` cog, which has been disabled by an administrator."
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return False
            return True
        embed = functions.embed("Error: Insufficient Permissions", color=0xff0000)
        embed.description = "You do not have the permissions required to use this command."
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False

    @app_commands.command(name="ban")
    @app_commands.describe(user="The user to ban", reason="The reason for the ban")
    async def ban(self, interaction: discord.Interaction, user: discord.User, reason: Optional[str]) -> None:
        """Bans a user"""

        if interaction.user.id == user.id == 689508987644936232:
            embed = functions.embed("Nice try, Wilson.", color=0xff0000)
            embed.description = ":3"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            if not reason:
                await interaction.guild.ban(user)
            else:
                await interaction.guild.ban(user, reason=reason, delete_message_seconds=0)
        except discord.Forbidden:
            embed = functions.embed("Error: Missing Permissions", color=0xff0000)
            embed.description = "I do not have the permissions to ban this user."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Success!", color=0x00ff00)
        if reason:
            embed.description = f"Banned {user.mention} for `{reason}`."
        else:
            embed.description = f"Banned {user.mention}."
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unban")
    @app_commands.describe(user="The user to unban", reason="The reason for the unban")
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: Optional[str]) -> None:
        """Unbans a user"""
        try:
            if not reason:
                await interaction.guild.unban(user)
            else:
                await interaction.guild.unban(user, reason=reason)
        except discord.Forbidden:
            embed = functions.embed("Error: Missing Permissions", color=0xff0000)
            embed.description = "I do not have the permissions to unban this user."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Success!", color=0x00ff00)
        if reason:
            embed.description = f"Unbanned {user.mention} for `{reason}`."
        else:
            embed.description = f"Unbanned {user.mention}."
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="kick")
    @app_commands.describe(user="The user to kick", reason="The reason for the kick")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: Optional[str]) -> None:
        """Kicks a user"""
        try:
            if not reason:
                await interaction.guild.kick(user)
            else:
                await interaction.guild.kick(user, reason=reason)
        except discord.Forbidden:
            embed = functions.embed("Error: Missing Permissions", color=0xff0000)
            embed.description = "I do not have the permissions to kick this user."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Success!", color=0x00ff00)
        if reason:
            embed.description = f"Kicked {user.mention} for `{reason}`."
        else:
            embed.description = f"Kicked {user.mention}."
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="timeout")
    @app_commands.describe(user="The user to timeout", reason="The reason for the timeout", duration="The duration of the timeout")
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, duration: str, reason: Optional[str]) -> None:
        """Times out a user for a specified duration"""
        td = timeparse(duration)
        if not td:
            embed = functions.embed("Error: Invalid Duration", color=0xff0000)
            embed.description = f"`{duration}` is not a valid duration."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        try:
            if not reason:
                await user.timeout(datetime.timedelta(seconds=td))
            else:
                await user.timeout(datetime.timedelta(seconds=td), reason=reason)
        except discord.Forbidden:
            embed = functions.embed("Error: Missing Permissions", color=0xff0000)
            embed.description = "I do not have the permissions to timeout this user."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Success!", color=0x00ff00)
        if reason:  
            embed.description = f"Timed out {user.mention} for `{duration}` for `{reason}`."
        else:
            embed.description = f"Timed out {user.mention} for `{duration}`."
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="purge")
    @app_commands.describe(amount="The amount of messages to purge")
    async def purge(self, interaction: discord.Interaction, amount: int, user: Optional[discord.User], reason: Optional[str]) -> None:
        """Purges a specified amount of messages"""
        try:
            await interaction.response.defer(thinking=False)
            def check(m):
                if user:
                    return m.author == user
                else:
                    return m.author.id != self.bot.user.id
            if reason:
                await interaction.channel.purge(limit=amount+1, check=check, reason=reason, bulk=True)
            else:
                await interaction.channel.purge(limit=amount+1, check=check, bulk=True)
            embed = functions.embed("Success!", color=0x00ff00)
            embed.description = f"Purged {amount} messages."
            await interaction.followup.send(embed=embed)
        except discord.Forbidden:
            embed = functions.embed("Error: Missing Permissions", color=0xff0000)
            embed.description = "I do not have the permissions to purge messages in this channel."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))