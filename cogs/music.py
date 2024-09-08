
import asyncio
import discord
from discord import app_commands
import wavelink
from discord.ext import commands
from typing import *
import functions
import random
import time
import settings
import os
import json

path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def generate_code():
    chars = "qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890"
    code = ""
    for _ in range(15):
        code = code + random.choice(chars)
    return code

def slice_n(lst, n):
    for i in range(0, len(lst), n): 
        yield lst[i:i + n] 

def botembed(title):
    embed = functions.embed("Music - " + title, color=0x03fcb1)
    return embed

def error(errormsg):
    embed = functions.error("Music", errormsg)
    return embed
    
class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.bot.loop.create_task(self.connect_nodes())
        self.players = {}
        self.queues = {}
        self.playstates = {}
        self.test = {}
        self.p = None

    async def connect_nodes(self):
        #await self.bot.wait_until_ready()

        self.node = await wavelink.NodePool.create_node(bot=self.bot,
                                            host=settings.WL_HOST,
                                            port=settings.WL_PORT,
                                            password=settings.WL_PASSWORD,
                                            https=True,
                                            identifier="PROD" if os.environ['TRIGBOT_ENV'] == 'testing' else "MAIN",)

        self.bot.node = self.node

        

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player, track, reason):
        if player.looping and reason != "STOPPED":
            await player.play(track)
            self.playstates[player.ctx.guild.id] = [time.time()]
        else:
            q = self.queues[player.guild.id]
            if not q.empty():
                track = q._queue.popleft()
                embed = functions.embed("Now Playing", color=0x03fcb1)
                embed.description = f" [{track.info['title']}]({track.info['uri']}) is now playing!"
                await player.ctx.send(embed=embed)
                self.playstates[player.ctx.guild.id] = [time.time()]
                player.current = track
                await player.play(track)
            else:
                self.playstates[player.ctx.guild.id] = []
                player.current = None

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild_id:
            embed = functions.embed("Error: Invalid Location", color=0xff0000)
            embed.description = "This command can only be used in a server."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if not(interaction.user.guild_permissions.administrator):
            disabled = self.bot.mdb["TrigBot"]["settings"]
            within = disabled.find_one({"_id": interaction.guild_id})
            if within:
                if self.get_file_name() in within["disabled_cogs"]:
                    embed = functions.embed("Error: Command Disabled", color=0xff0000)
                    embed.description = f"This command is part of the `{self.get_file_name()}` cog, which has been disabled by an administrator."
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return False
            
        if not interaction.user.voice:
            embed = functions.embed("Error: Voice Channel Not Connected", color=0xff0000)
            embed.description = "You need to be connected to a voice channel to use this command."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if interaction.guild.id not in self.players.keys():
            if str(interaction.command.name) not in ["soundboard", "play", "join"]:
                embed = functions.embed("Error: Voice Channel Not Connected", color=0xff0000)
                embed.description = "I'm not connected to a voice channel right now.\nUse `/join`, `/play`, or `/soundboard` to connect me to a voice channel."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
        else:
            player = self.players[interaction.guild.id]
            
            if player.channel.id != interaction.user.voice.channel.id:
                embed = functions.embed("Error: Different Voice Channels", color=0xff0000)
                embed.description = "You need to be connected to the same voice channel as me to use this command."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
        return True
    
    async def do_connect(self, inter: discord.Interaction):
        if inter.guild.id not in self.players: # this cannot be put into a function or changed in any way
            vc: wavelink.Player = await inter.user.voice.channel.connect(cls=wavelink.Player)
            vc.ctx = inter.channel
            vc.looping = False
            await vc.set_volume(75)
            vc.channel = inter.user.voice.channel
            self.players[inter.guild.id] = vc
            self.queues[inter.guild.id] = asyncio.Queue()
            self.playstates[inter.guild.id] = []
        else:
            vc: wavelink.Player = self.players[inter.guild.id]
        return vc

    @app_commands.command(name="join")
    async def join(self, inter: discord.Interaction):
        """Join the voice channel you are currently in"""
        vc = await self.do_connect(inter)
        embed = functions.embed("Connected", color=0x03fcb1)
        embed.description = f"I've successfully connected to `{vc.channel.name}`."
        await inter.response.send_message(embed=embed)

    #@commands.command(aliases=["p"])
    @app_commands.command(name="play")
    @app_commands.describe(search="The search term you would like to use. Can be either a YouTube URL or a search term")
    async def play(self, inter: discord.Interaction, search: str):
        """Play a video from YouTube, given a link or a search term"""
        vc = await self.do_connect(inter)

        copy = search
        search = await wavelink.YouTubeTrack.search(query=search, return_first=True)
        if not search:
            embed = functions.embed("Error: No Videos Found", color=0xff0000)
            embed.description = f"I couldn't find any videos with the search term `{copy}`."
            return await inter.response.send_message(embed=embed, ephemeral=True)
        queue = self.queues[inter.guild.id]
        if queue.empty() and not vc.is_playing():
            self.playstates[inter.guild.id] = [time.time()]
            vc.current = search
            await vc.play(search)
            embed = functions.embed("Now Playing", color=0x03fcb1)
            embed.description = f" [{search.info['title']}]({search.info['uri']}) is now playing!"
            await inter.response.send_message(embed=embed)
        else:
            await queue.put(search)
            embed = functions.embed("Song Added", color=0x03fcb1)
            embed.description = f" [{search.info['title']}]({search.info['uri']}) has been added to the queue."
            await inter.response.send_message(embed=embed)
        
    @app_commands.command(name="disconnect")
    async def disconnect(self, inter: discord.Interaction):
        """Disconnect from the voice channel"""
        vc = self.players[inter.guild.id]
        await vc.disconnect(force=True)
        embed = functions.embed("Disconnected", color=0x03fcb1)
        embed.description = f"I've disconnected from `{vc.channel.name}`."
        await inter.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id:
            if not after.channel:
                if member.guild.id in self.players:
                    vc = self.players[member.guild.id]
                    await vc.disconnect(force=True)
                    del self.players[member.guild.id]
                    del self.queues[member.guild.id]
                    del self.playstates[member.guild.id]

    @app_commands.command(name="skip")
    async def skip(self, inter: discord.Interaction):
        """Skip the current song"""
        vc = self.players[inter.guild.id]
        await vc.stop()
        if len(self.queues[inter.guild.id]._queue) == 0:
            embed = functions.embed("Queue Ended", color=0x03fcb1)
            embed.description = "Skipped the last song in the queue.\nTo play more songs, use `/play`."
            return await inter.response.send_message(embed=embed)
        else:
            embed = functions.embed("Song Skipped", color=0x03fcb1)
            embed.description = "Skipped the current song."
            return await inter.response.send_message(embed=embed)
        
    #@commands.command()
    @app_commands.command(name="loop")
    async def loop(self, inter: discord.Interaction):
        """Toggle looping of the current song"""
        vc = self.players[inter.guild.id]
        vc.looping = not vc.looping
        embed = functions.embed("Loop Toggled", color=0x03fcb1)
        embed.description = f"Looping has been turned {'on' if vc.looping else 'off'}."
        return await inter.response.send_message(embed=embed)

    @app_commands.command(name="move")    
    async def move(self, inter: discord.Interaction, frompos: int, topos: int):
        """Move a song in the queue from one position to another"""
        vc = self.players[inter.guild.id]
        q = self.queues[inter.guild.id]

        if frompos < 1 or frompos > len(q._queue):

            embed = functions.embed("Error: Invalid Position", color=0xff0000)
            embed.description = f"The position to move from (`{frompos}`) is out of range."
            return await inter.response.send_message(embed=embed, ephemeral=True)


        if topos < 1 or topos > len(q._queue):
            embed = functions.embed("Error: Invalid Position", color=0xff0000)
            embed.description = f"The position to move to (`{topos}`) is out of range."
            return await inter.response.send_message(embed=embed, ephemeral=True)

        
        song = self.queues[inter.guild.id]._queue[frompos - 1]
        self.queues[inter.guild.id]._queue[frompos - 1] = self.queues[inter.guild.id]._queue[topos - 1]
        self.queues[inter.guild.id]._queue[topos - 1] = song
        
        embed = functions.embed(title="Song Moved", color=0x03fcb1)
        embed.description = f"[{song.info['title']}]({song.info['uri']}) has been moved from `#{frompos}` to `#{topos}` in the queue."
        return await inter.response.send_message(embed=embed)

    
    @app_commands.command(name="queue")
    async def _queue(self, inter: discord.Interaction, page: Optional[int]=1):
        """View the current song queue"""
        q = self.queues[inter.guild.id]

        if q.empty():
            embed = functions.embed("Error: Queue Empty", color=0xff0000)
            embed.description = "There is nothing in the queue right now.\nTo add a song to the queue, use `/play`."
            return await inter.response.send_message(embed=embed, ephemeral=True)
        
        page = int(page)

        viewable = 5

        pages = int(len(q._queue) // viewable) + (1 if len(q._queue) % viewable > 0 else 0)

        page = min(max(page, 1), pages)
        start = (page-1) * viewable
        end = min(max(start + viewable, 1), len(q._queue))

        upcoming = list(q._queue)[start:end]

        desc = ""
        for i in range(len(upcoming)):
            desc = desc + f"\n**{start + i + 1}**: [{upcoming[i].info['title']}]({upcoming[i].info['uri']})" 

        embed = functions.embed(f"Queue (#{start + 1} - #{end})", color=0x03fcb1)

        embed.description = f"*Showing page {page} of {pages}*\n\n" + desc

        await inter.response.send_message(embed=embed)

    @app_commands.command(name="now-playing")
    async def nowplaying(self, inter: discord.Interaction):
        """View the currently playing song"""
        vc = self.players[inter.guild.id]
        if not vc.is_playing():
            #embed = error("🚫 " + self.bot.response(2) +  " there's nothing playing right now...")
            embed = functions.embed("Error: Nothing Playing", color=0xff0000)
            embed.description = "There is nothing playing right now.\nTo play a song, use `/play`."
            
            return await inter.response.send_message(embed=embed, ephemeral=True)

        temp = list(self.playstates[inter.guild.id].copy())
        if len(temp) % 2 == 1:
            temp.append(time.time())

        chunked = list(slice_n(temp, 2))
        total = sum([x[1] - x[0] for x in chunked])
        
        length = time.gmtime(vc.current.info['length'] / 1000)
        if vc.current.info['length'] / 1000 >= 3600:
            fstring = "%H:%M:%S"
        else:
            fstring = "%M:%S"
        length_r = time.strftime(fstring, length)

        dt = time.gmtime(total)
        dt_r = time.strftime(fstring, dt)

        
        #embed = botembed("Now Playing")
        #embed.description = ("🔊 " + self.bot.response(1) + f" Currently, I'm playing [{vc.current.info['title']}]({vc.current.info['uri']})\n(`{dt_r}` / `{length_r}`).")
        #await ctx.send(embed=embed)

        embed = functions.embed("Now Playing", color=0x03fcb1)
        embed.description = f"Now playing: [{vc.current.info['title']}]({vc.current.info['uri']}) ({dt_r} / {length_r})"
        return await inter.response.send_message(embed=embed)

    @app_commands.command(name="remove")
    @app_commands.describe(pos="The position of the song to remove (starting at 1)")
    async def remove(self, inter: discord.Interaction, pos: int):
        """Remove a song from the queue at a specific index"""
        q = self.queues[inter.guild.id]
        
        if pos < 1 or pos > len(q._queue):
            embed = functions.embed("Error: Invalid Position", color=0xff0000)
            embed.description = f"The position to remove (`{pos}`) is out of range."
            return await inter.response.send_message(embed=embed, ephemeral=True)
        song = q._queue[pos - 1]
        q._queue.remove(song)
        embed = functions.embed("Song Removed", color=0x03fcb1)
        embed.description = f"[{song.info['title']}]({song.info['uri']}) has been removed from the queue."
        return await inter.response.send_message(embed=embed)

    @app_commands.command(name="pause")
    async def pause(self, inter: discord.Interaction):
        """Pause the player"""
        player = self.players[inter.guild.id]
        if not player.is_playing:
            embed = functions.embed("Error: Nothing Playing", color=0xff0000)
            embed.description = "There is nothing playing right now.\nTo play a song, use `/play`."
            
            return await inter.response.send_message(embed=embed, ephemeral=True)
        embed = functions.embed("Paused", color=0x03fcb1)
        await player.set_pause(True)
        self.playstates[inter.guild.id].append(time.time())
        embed.description = "The player has now been paused.\nUse `/resume` to resume the player."
        await inter.response.send_message(embed=embed)
        
    @app_commands.command(name="resume")
    async def resume(self, inter: discord.Interaction):
        """Resume the player"""
        player = self.players[inter.guild.id]
        if not player.is_paused:
            embed = functions.embed("Error: Player Not Paused", color=0xff0000)
            embed.description = "The player is currently not paused.\nTo pause the player, use `/pause`."
            return await inter.response.send_message(embed=embed, ephemeral=True)
            #mbed = error("🚫 " + self.bot.response(2) +  " it looks like I'm not paused right now...")
            #return await ctx.send(embed=embed)

        await player.set_pause(False)
        self.playstates[inter.guild.id].append(time.time())
        embed = functions.embed("Resumed", color=0x03fcb1)
        embed.description = "The player has now been resumed.\nTo pause the player again, use `/pause`."
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="volume")
    async def volume(self, inter: discord.Interaction, vol: Optional[int]):
        """Set the volume of the player"""
        player = self.players[inter.guild.id]
        if not vol:
            embed = botembed("Current Volume")
            embed.description = f"The volume is currently set to `{player.volume}%`."
            return await inter.response.send_message(embed=embed)
        
        vol = int(vol)
        vol = max(min(vol, 500), 0)
        await player.set_volume(vol)
            

        
        embed = functions.embed("Volume Set", color=0x03fcb1)
        embed.description = f"The volume has been set to `{vol}%`."
        await inter.response.send_message(embed=embed)



    @app_commands.command(name="soundboard")
    @app_commands.describe(query="The sound to play")
    async def soundboard(self, inter: discord.Interaction, query: Optional[str]):
        """Play a sound from the soundboard (use /soundboard to list all sounds)"""
        with open(os.path.join(path, "assets", "soundboard.json")) as f:
            board = json.loads(f.read())

        if not query:
            embed = functions.embed("Soundboard List", color=0x03fcb1)
            embed.description = "The current available sounds are:\n`" + "  ".join(sorted(board.keys())) + "`"
            return await inter.response.send_message(embed=embed, ephemeral=True)
        
        query = query.lower().strip()

        if query not in board.keys():
            embed = functions.embed("Error: No Sound Found", color=0xff0000)
            embed.description = f"I couldn't find a sound named `{query}`."
            return await inter.response.send_message(embed=embed, ephemeral=True)

        if inter.guild.id in self.players.keys():
            player = self.players[inter.guild.id]
            if player:
                
                if not self.queues[inter.guild.id].empty() or player.is_playing():

                    embed = functions.embed("Error: Songs In Queue", color=0xff0000)
                    embed.description = "The soundboard cannot be used while music is playing or queued."
                    return await inter.response.send_message(embed=embed, ephemeral=True)
            
        embed = functions.embed("Now Playing Sound", color=0x03fcb1)
        embed.description = f"[{query}]({board[query]}) on the soundboard is now playing."
        await inter.response.send_message(embed=embed)

        #await ctx.invoke(self.play, search=list(await self.node.get_tracks(query=board[query], cls=wavelink.Track))[0], silent=True)

        vc = await self.do_connect(inter)
        
        try:
            track = await self.node.get_tracks(wavelink.YouTubeTrack, board[query])
            await vc.play(track[0])
        except Exception as e:
            print(e)    


async def setup(bot):
    await bot.add_cog(Music(bot))