import discord
from discord.ext import commands
from discord import app_commands
import cogs.settings as settings

import logging

discord.utils.setup_logging(level=logging.INFO, root=False)

import os, sys
import asyncio

import pymongo

path = os.path.dirname(os.path.realpath(__file__))
cogs = os.path.join(path, "cogs")
sys.path.append(os.path.join(path, "cogs"))

intents = discord.Intents.all()

intents.message_content = True
intents.presences = True
intents.members = True # redundant but it helps
intents.reactions = True
intents.voice_states = True

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.remove_command("help")

        self.mdb = pymongo.MongoClient(settings.MONGO_URI)

        self.cog_names = []
        self.mapped_cogs = {}

        self.silenced = False
        

    async def on_ready(self):
        print("Ready!")

        user = self.user
        if len(sys.argv) > 1:
            self.environment = "stable" # don't change these
        else:
            self.environment = "production" # don't change these

        print("-----")
        print(f"Logged in as: {user.name}#{user.discriminator}")
        print(f"ID: {user.id}")
        cloaded = 0
        for file in os.listdir(cogs):
            if file.endswith(".py"):
                name = file[:-3]
                with open(os.path.join(cogs, file), encoding="utf-8") as f:
                    try:
                        content = f.read()
                    except:
                        print("\tERROR LOADING COG: " + name)
                if "# DNI" not in content:  # "DNI": Do Not Import
                    await self.load_extension("cogs." + name, package=os.path.dirname(__file__))
                    
                    self.cog_names.append(name)

                    cloaded += 1
                    print("\tLoaded cog:", name)

        for cog in self.cogs.values():
            if hasattr(cog, "get_file_name"):
                self.mapped_cogs[cog.get_file_name()] = cog

        await self.load_extension("jishaku")
        cloaded += 1
        await self.tree.sync()
        print(f"{cloaded} cogs loaded")
        print("-----") # if any errors are raised before this prints, fix them before restarting
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="/help for help!"))

bot = Bot(command_prefix=settings.PREFIX, intents=intents)

async def main():
    async with bot:
        if len(sys.argv) > 1:
            t = settings.TOKEN
            os.environ["TRIGBOT_ENV"] = "stable"
        else:
            t = settings.PROD_TOKEN
            os.environ["TRIGBOT_ENV"] = "testing"
        await bot.start(t)

if __name__ == "__main__":
    asyncio.run(main()) 