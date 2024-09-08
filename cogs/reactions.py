
import discord
from discord import app_commands
from discord.ext import commands
import settings

from typing import *

import functions
import random
import os

NAME = "Reactions"
DESCRIPTION = "A bunch of reactions for users to send to others"

class Reactions(commands.Cog):
    """A bunch of reactions for users to send to others"""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]

    async def interaction_check(self, interaction: discord.Interaction):
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

    @app_commands.command(name="hug")
    @app_commands.describe(user="The user to hug")
    async def hug(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """ Sends a user a hug"""
        if interaction.user.id == user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't hug yourself!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Hug!", color=0xeb7d34)
        embed.description = f"Awww, <@{interaction.user.id}> hugged <@{user.id}>!"

        gifs = [
            "https://c.tenor.com/OXCV_qL-V60AAAAM/mochi-peachcat-mochi.gif",
            "https://c.tenor.com/jU9c9w82GKAAAAAC/love.gif",
            "https://c.tenor.com/ZzorehuOxt8AAAAM/hug-cats.gif",
            "https://c.tenor.com/sSbr1al2-KQAAAAC/so-cute.gif",
            "https://c.tenor.com/5Xdf60Rv1a4AAAAC/milk-mocha.gif"

        ]

        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(f"<@{user.id}>", embed=embed)

    @app_commands.command(name="kiss")
    @app_commands.describe(user="The user to kiss")
    async def kiss(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """ Sends a user a kiss"""
        if interaction.user.id == user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't kiss yourself!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Kiss!", color=0xeb7d34)
        embed.description = f"Awww, <@{interaction.user.id}> kissed <@{user.id}>!"
        gifs = [
            "https://c.tenor.com/gUiu1zyxfzYAAAAi/bear-kiss-bear-kisses.gif",
            "https://c.tenor.com/zFzhOAJ8rqwAAAAC/love.gif",
            "https://media.tenor.com/217aKgnf16sAAAAC/kiss.gif",
            "https://media.tenor.com/FgYExssph6MAAAAC/kiss-love.gif",
            "https://media.tenor.com/U7h-gyy--akAAAAC/kiss.gif",
            "https://media.tenor.com/QjMZ6Dx33_QAAAAC/kuss-kussi.gif"

        ]

        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(f"<@{user.id}>", embed=embed)

    @app_commands.command(name="pat")
    @app_commands.describe(user="The user to pat")
    async def pat(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """ Pats a user on the head """
        if interaction.user.id == user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't pat yourself!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Pat!", color=0xeb7d34)
        embed.description = f"Awww, <@{interaction.user.id}> patted <@{user.id}> on the head!"
        gifs = [
            "https://c.tenor.com/GU0IIlOZUQ0AAAAC/pat-pat.gif",
            "https://c.tenor.com/5MGEjar4AHcAAAAC/seal-hibo.gif",
            "https://c.tenor.com/qjHkX9X0FOQAAAAC/milk-and-mocha-pat.gif",
            "https://c.tenor.com/AZ1mlSh-fT8AAAAi/pat-duck.gif",
            "https://c.tenor.com/BWXvOyKVWU4AAAAi/potato-pat.gif"

        ]
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(f"<@{user.id}>", embed=embed)

    @app_commands.command(name="slap")
    @app_commands.describe(user="The user to slap")
    async def slap(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """ Slaps a user """
        if interaction.user.id == user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't slap yourself!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Slap!", color=0xeb7d34)
        embed.description = f"Ouch, <@{interaction.user.id}> slapped <@{user.id}>!"
        gifs = [
            "https://c.tenor.com/EzwsHlQgUo0AAAAC/slap-in-the-face-angry.gif",
            "https://c.tenor.com/ImQ3_wc8sF0AAAAM/ru-paul-slap.gif",
            "https://c.tenor.com/yJmrNruFNtEAAAAC/slap.gif",
            "https://c.tenor.com/R-fs21xH13QAAAAM/slap-kassandra-lee.gif"

        ]
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(f"<@{user.id}>", embed=embed)

    @app_commands.command(name="punch")
    @app_commands.describe(user="The user to punch")
    async def punch(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """ Punches a user """
        if interaction.user.id == user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't punch yourself!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Punch!", color=0xeb7d34)
        embed.description = f"Ouch, <@{interaction.user.id}> punched <@{user.id}>!"
        gifs = [
            "https://c.tenor.com/5iVv64OjO28AAAAC/milk-and-mocha-bear-couple.gif",
            "https://c.tenor.com/UAG36LOiVDwAAAAC/milk-and-mocha-happy.gif"

        ]
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(f"<@{user.id}>", embed=embed)

    @app_commands.command(name="poke")
    @app_commands.describe(user="The user to poke")
    async def poke(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """ Pokes a user """
        if interaction.user.id == user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't poke yourself!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Poke!", color=0xeb7d34)
        embed.description = f"Ouch, <@{interaction.user.id}> poked <@{user.id}>!"
        gifs = [
            "https://c.tenor.com/qkvoAoV4w3wAAAAC/poke-cute-bear.gif",
            "https://c.tenor.com/KyPxfr4AVFcAAAAC/poke.gif",
            "https://c.tenor.com/9bPsSkaKgVsAAAAC/poke-boop.gif",
            "https://c.tenor.com/my_TpYpdQX0AAAAC/yeah-im-hungry-milk-and-mocha.gif"

        ]
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(f"<@{user.id}>", embed=embed)

    @app_commands.command(name="boop")
    @app_commands.describe(user="The user to boop")
    async def boop(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """ Boops a user """
        if interaction.user.id == user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't boop yourself!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Boop!", color=0xeb7d34)
        embed.description = f"Awww, <@{interaction.user.id}> booped <@{user.id}>!"
        gifs = [
            "https://c.tenor.com/MQ5Kdsh3zKMAAAAM/boop-dog-high-quality.gif",
            "https://c.tenor.com/WM6gQWWPvIcAAAAC/boop-wolf.gif",
            "https://c.tenor.com/le048t71RHwAAAAC/boop.gif",
            
        ]
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(f"<@{user.id}>", embed=embed)

    @app_commands.command(name="bonk")
    @app_commands.describe(user="The user to bonk")
    async def bonk(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """ Bonks a user on the head """
        if interaction.user.id == user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't bonk yourself!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Bonk!", color=0xeb7d34)
        embed.description = f"Ouch, <@{interaction.user.id}> bonked <@{user.id}> on the head!"
        gifs = [
            "https://c.tenor.com/DMWqIb2Rdp4AAAAj/bonk-cheems.gif",
            "https://c.tenor.com/WQE5mJQSRRsAAAAj/bonk-hit.gif",
            "https://c.tenor.com/5YrUft9OXfUAAAAM/bonk-doge.gif",
            "https://c.tenor.com/Tg9jEwKCZVoAAAAd/bonk-mega-bonk.gif"
        ]
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(f"<@{user.id}>", embed=embed)

    @app_commands.command(name="cuddle")
    @app_commands.describe(user="The user to cuddle with")
    async def cuddle(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Cuddle with a user"""
        if interaction.user.id == user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't cuddle with yourself!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Cuddles!", color=0xeb7d34)
        embed.description = f"Awww, <@{interaction.user.id}> cuddled with <@{user.id}>!"
        gifs = [
            "https://media.tenor.com/kRXsnDqxCYgAAAAC/cuddle.gif",
            "https://media.tenor.com/c9tu8_KoqlUAAAAi/cuddles-panda.gif",
            "https://media.tenor.com/0VSTfZxv36AAAAAi/snuggle-cuddle.gif",
            "https://media.tenor.com/RccDmLjx_TYAAAAC/mochi-cuddle-peach.gif"
        ]
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(f"<@{user.id}>", embed=embed)

    @app_commands.command(name="pounce")
    @app_commands.describe(user="The user to pounce on")
    async def pounce(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Pounce on a user"""
        if interaction.user.id == user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You can't pounce on yourself!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = functions.embed("Pounce!", color=0xeb7d34)
        embed.description = f"Awww, <@{interaction.user.id}> pounced on <@{user.id}>!"
        gifs = [
            "https://media.tenor.com/ZT1qBLcw8WUAAAAC/a-lovely-tuji-glomp.gif",
            "https://media.tenor.com/hChX7RjUmNcAAAAd/pounce-the-chance-to-strike.gif",
            "https://media.tenor.com/epZmT3LvVP4AAAAd/red-panda-fire-ferret.gif",
            "https://media.tenor.com/glwwwW6GXjIAAAAC/kiss-tackle.gif",
            "https://media.tenor.com/tvmwrJPQbtcAAAAd/cuddles-love.gif"
        ]
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(f"<@{user.id}>", embed=embed)
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Reactions(bot))