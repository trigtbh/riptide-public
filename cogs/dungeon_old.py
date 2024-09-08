# DNI

import discord
from discord import app_commands
from discord.ext import commands
import settings
import math

from typing import *

import functions
import random
import os

import asyncio

# today,
# i'll demonstrate a work of art in the form of code
# i call it:
# "unnecessary abuse of random.seed() in places that it absolutely does not need to be used in"

special_items = ["Echoing Sphere", "Flickering Light", "Timeless Tear", "Glowing Thread", "Eternal Flame"]

def generate_floor_map(uuid, floor):
    floor_map = {
        0: [None, None, None, None] # north, east, south, west
    }
    rooms = {0: "entrance"}
    rgen = random.Random((uuid + floor)) # <-- where the magic happens
    
    togen = []
    for _ in range(10 + floor - 1):
        togen.append("encounter")

    extras = ["shrine", "cursed", "loot"]


    for i in range(len(togen)):
        test = rgen.randint(1, 4 * len(extras) / 0.25)
        if test < (len(extras) / 0.25):
            togen[i] = extras[test % len(extras)]
    
    togen += ["shop", "exit", "key"]

    rgen.shuffle(togen)

    rnum = 0
    for item in togen:
        rnum += 1
        rooms[rnum] = item
        placement = []
        for room in range(len(floor_map)):
            for direction in range(len(floor_map[room])):
                if floor_map[room][direction] is None:
                    placement.append((room, direction))
        location = rgen.choice(placement)
        floor_map[location[0]][location[1]] = rnum
        opposite = (location[1] + 2) % 4
        temp = [None, None, None, None]
        temp[opposite] = location[0]
        floor_map[rnum] = temp

    for room in floor_map:
        for i in range(len(floor_map[room])):
            if floor_map[room][i] == None:
                for room_2 in floor_map:
                    if room == room_2: continue
                    if floor_map[room_2][(i + 2) % 4] == None and rgen.random() < 0.15:
                        floor_map[room][i] = -1 * room_2
                        floor_map[room_2][(i + 2) % 4] = -1 * room
                        break

    return floor_map, rooms



class Inventory(discord.ui.View):
    def __init__(self, *, bot, interaction: discord.Interaction, uuid: int, timeout=300):
        super().__init__(timeout=timeout)
        self.uuid = uuid
        self.bot = bot
        self.data = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": uuid})
        self.interaction = interaction

        self.inventory_items = self.data['inventory']
        self.inventory_items.sort(key=lambda x: x['name'])

        self.select_menu = discord.ui.Select(placeholder="Select an item", min_values=1, max_values=1, options=[discord.SelectOption(label=item['name'], value=str(i)) for i, item in enumerate(self.inventory_items)], row=1)
        self.select_menu.callback = self.menu_callback
        self.use_button = discord.ui.Button(label="Use Item", style=discord.ButtonStyle.green, disabled=True, row=2)
        self.drop_button = discord.ui.Button(label="Drop Drop", style=discord.ButtonStyle.red, disabled=True, row=2)
        self.cancel = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.grey, row=2)

        self.description = "Select an item to use or drop."

    async def menu_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("You can't use someone else's inventory!", ephemeral=True)
            return False
        return True
    
    async def menu_callback(self, interaction: discord.Interaction):
        if interaction.data["values"]:
            self.use_button.disabled = False
            self.drop_button.disabled = False
        else:
            self.use_button.disabled = True
            self.drop_button.disabled = True
        await interaction.response.edit_message(view=self)
        # create an embed that displays item information
        item = self.inventory_items[int(interaction.data["values"][0])]
        embed = functions.embed("Dungeon - Inventory", color=0xa67534)
        embed.add_field(name="Name", value=item['name'], inline=False)
        embed.add_field(name="Description", value=item['description'], inline=False)
        embed.add_field(name="Type", value=item['type'], inline=False)

        if item['type'] == "weapon":
            embed.add_field(name="Damage", value=f"{item['damage']}", inline=False)
        elif item['type'] == "armor":
            embed.add_field(name="Defense", value=f"{item['defense']}", inline=False)
        elif item['type'] == "consumable":
            embed.add_field(name="Effect", value=item['effect'], inline=False)
        else: 
            embed.description = "**This item is not consumable.**"
            self.use_button.disabled = True
        if item["name"] in special_items:
            self.drop_button.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)
    
        # TODO: figure out how to use items in combat??????

class CombatInventory(discord.ui.View):
    def __init__(self, *, bot, interaction: discord.Interaction, uuid: int, combat_cog, timeout=300):
        super().__init__(timeout=timeout)
        self.uuid = uuid
        self.bot = bot
        self.data = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": uuid})
        self.interaction = interaction
        self.combat_cog = combat_cog

        self.inventory_items = self.data['inventory']
        self.inventory_items.sort(key=lambda x: x['name'])

        self.select_menu = discord.ui.Select(placeholder="Select an item", min_values=1, max_values=1, options=[discord.SelectOption(label=item['name'], value=str(i)) for i, item in enumerate(self.inventory_items)], row=1)
        self.select_menu.callback = self.menu_callback
        #self.use_button = discord.ui.Button(label="Use Item", style=discord.ButtonStyle.green, disabled=True, row=2)
        self.cancel = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.grey, row=2)


        self.description = "Select an item to use."

    async def menu_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction.user.id:
            embed = functions.embed("Error: Invalid Combat Session", color=0xff0000)
            embed.description = "This combat session is not yours to interact with."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if interaction.user.id not in self.combat_cog.cog.busy:
            embed = functions.embed("Error: Invalid Combat Session", color=0xff0000)
            embed.description = "This combat session has expired."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def menu_callback(self, interaction: discord.Interaction):
        if interaction.data["values"]:
            self.use_button.disabled = False
        else:
            self.use_button.disabled = True
        await interaction.response.edit_message(view=None)

        item = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": self.uuid})['inventory'][int(interaction.data["values"][0])]
        itemtype = item['type']
        subtype = item['subtype']
        embed = None
        if itemtype == "consumable":
            if subtype == "heal":
                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$inc": {"health": item['effect']}})
                embed = functions.embed("Dungeon - Combat", color=0xa67534)
                embed.description = f"You used **{item['name']}** and healed **{item['effect']}** health.\n\n"
                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$pull": {"inventory": {"name": item['name']}}})
            elif subtype == "damage":
                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$inc": {"health": -item['effect']}})
                self.combat.enemy_health -= item['effect']
                embed = functions.embed("Dungeon - Combat", color=0xa67534)
                embed.description = f"You used **{item['name']}** and took **{item['effect']}** damage.\nThe enemy also takes **{item['effect']}** damage.\n\n"
            elif subtype == "potion":
                effect_type = item['effect_type']
                # TODO: process effect_type

                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$inc": {"health": item['effect']}})
                embed = functions.embed("Dungeon - Combat", color=0xa67534)
                embed.description = f"You used **{item['name']}** and healed **{item['effect']}** health.\n\n"
                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$pull": {"inventory": {"name": item['name']}}})
        else:
            embed = functions.embed("Error: Invalid Item", color=0xff0000)
            embed.description = "This item is not consumable."
            await interaction.response.send_message(embed=embed, ephemeral=True)
    


class Combat(discord.ui.View):
    def __init__(self, bot, cog, interaction: discord.Interaction, uuid: int, cursed: bool, base_description: str, timeout=300):
        super().__init__(timeout=timeout)
        self.uuid = uuid
        self.bot = bot
        self.cog = cog
        self.data = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": uuid})
        self.cursed = cursed
        self.interaction = interaction

        # generate an enemy based on how high of a level the player is
        enemies = ["Skeleton", "Orc", "Spider", "Ghoul", "Troll", "Bandit", "Mummy", "Werewolf", "Dark Wizard", "Necromancer", "Minotaur", "Lich", "Gargoyle", "Demon", "Dragon"]
        
        level = self.data['level']
        floor = self.data['floor']

        

        if level < 5:
            self.enemy = random.choice(enemies[:5])
        elif level < 10:
            self.enemy = random.choice(enemies[:10])
        else:
            self.enemy = random.choice(enemies)

        
        self.enemy_level = min(1, level + random.randint(-4, 4) + (floor // 2))
        if self.cursed:
            self.enemy_level += random.randint(1, 10)
        self.enemy_health = 15 + (level * 2) + (floor * 2) + random.randint(-5, 5) + (self.enemy_level // 2)
        self.enemy_damage = min(1, 2 + (self.enemy_level * 2) + (floor * 2) + random.randint(-5, 5))

        self.bd = base_description

        self.description = f"{self.bd}\n\nYou encountered a {'Cursed ' if self.cursed else ''}Level {self.enemy_level} {self.enemy}!\nUse the buttons below to fight it."

        self.defense_chance = 20
        self.hit_chance = 70
        self.flee_chance = 35
        if self.cursed:
            self.defense_chance = 10
            self.hit_chance = 50
            self.flee_chance = 15

    

    async def do_enemy_attack(self, interaction: discord.Interaction, embed):
        embed.description += "The enemy attacks you!\n"
        if random.randint(1, 100) <= self.defense_chance:
            embed.description += "You successfully defended yourself!\n"
        else:
            embed.description += f"You took {self.enemy_damage} damage!\n"
            self.data['health'] -= self.enemy_damage
            if self.data['health'] <= 0:
                embed.description += f"You died!\n\n***Game over***.\nYou made it to floor {self.data['floor']}.\nUse `/dungeon enter` to start a new game."
                await interaction.response.send_message(embed=embed)
                self.bot.mdb["TrigBot"]["dungeon"].delete_one({"_id": self.uuid})
                self.cog.busy.remove(self.uuid)
                return
            else:
                embed.description += f"You now have **{self.data['health']} HP** left.\n"
        self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$set": {"health": self.data['health']}})
        embed.description += f"\nUse the buttons below to continue fighting."
        self.interaction = interaction
        await interaction.response.send_message(embed=embed, view=self)

    async def button_check(self, interaction: discord.Interaction):
        # TODO: render user effects here
        if interaction.user.id != self.uuid: 
            embed = functions.embed("Error: Invalid Combat Session", color=0xff0000)
            embed.description = "This session is not yours to interact with."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if self.uuid not in self.cog.busy:
            embed = functions.embed("Error: Invalid Combat Session", color=0xff0000)
            embed.description = "This combat session has expired."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def inventory_callback(self, interaction: discord.Interaction, embed):
        # if user health is 0, cause a game over
        if self.mdb["TrigBot"]["dungeon"].find_one({"_id": self.uuid})['health'] <= 0:
            embed.description += f"You died!\n\n***Game over***.\nYou made it to floor {self.data['floor']}.\nUse `/dungeon enter` to start a new game."
            await interaction.response.send_message(embed=embed)
            self.bot.mdb["TrigBot"]["dungeon"].delete_one({"_id": self.uuid})
            self.cog.busy.remove(self.uuid)
            return
        # if enemy health is 0, cause a win
        if self.enemy_health <= 0:
            await self.interaction.edit_original_response(view=None)
            embed = functions.embed("Dungeon - Combat", color=0xa6753a)
            embed.description = f"You defeated the {self.enemy}!\nYou may now continue on your journey."
            await interaction.response.send_message(embed=embed)
            self.cog.busy.remove(self.uuid)
            return
        await self.do_enemy_attack(interaction, embed)

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.primary)
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.button_check(interaction): return
        attack_strength = self.data['weapon']['attack'] # TODO: take status effects into effect
        if random.randint(1, 100) <= self.hit_chance:
            self.enemy_health -= attack_strength
            if self.enemy_health <= 0:
                await self.interaction.edit_original_response(view=None)
                embed = functions.embed("Dungeon - Combat", color=0xa6753a)
                embed.description = f"You defeated the {self.enemy}!\nYou may now continue on your journey." # TODO: xp stuff
                await interaction.response.send_message(embed=embed)
                self.cog.busy.remove(self.uuid)
            else:
                await self.interaction.edit_original_response(view=None)
                embed = functions.embed("Dungeon - Combat", color=0xa6753a)
                embed.description = f"You attacked the {self.enemy} for {attack_strength} damage!\nIt now has {self.enemy_health} HP left.\n\n"

                await self.do_enemy_attack(interaction, embed)
        else:
            await self.interaction.edit_original_response(view=None)
            embed = functions.embed("Dungeon - Combat", color=0xa6753a)
            embed.description = f"You missed your attack!\n\n"
            await self.do_enemy_attack(interaction, embed)
            


    @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary)
    async def defend(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.button_check(interaction): return
        await self.interaction.edit_original_response(view=None)
        embed = functions.embed("Dungeon - Combat", color=0xa6753a)
        embed.description = f"You stood your ground!\nYour defense increased.\n\n"
        self.defense_chance += 10
        await self.do_enemy_attack(interaction, embed)
        self.defense_chance -= 10


    @discord.ui.button(label="Inventory", style=discord.ButtonStyle.primary)
    async def inventory(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.button_check(interaction): return

        await self.interaction.edit_original_response(view=None)
        self.interaction = interaction
        
        self.inventory_items = self.data['inventory']
        self.inventory_items.sort(key=lambda x: x['name'])

        self.select_menu = discord.ui.Select(placeholder="Select an item", min_values=1, max_values=1, options=[discord.SelectOption(label=item['name'], value=str(i)) for i, item in enumerate(self.inventory_items)], row=1)
        embed = functions.embed("Dungeon - Inventory", color=0xa6753a)
        embed.description = "Select an item to use."
        self.interaction = interaction

        await interaction.response.send_message(embed=embed, view=)

    @discord.ui.button(label="Flee", style=discord.ButtonStyle.red)
    async def flee(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.button_check(interaction): return
        await self.interaction.edit_original_response(view=None)
        embed = functions.embed("Dungeon - Combat", color=0xa6753a)
        embed.description = "You tried to run away.\n"
        if random.randint(1, 100) < self.flee_chance:
            embed.description += f"You successfully fled!\nYou may now continue on your journey."
            await interaction.response.send_message(embed=embed)
        else:
            embed.description += f"You were caught!\n\n"
            await self.do_enemy_attack(interaction, embed)

    

class Dungeon(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
        self.busy = set()
        super().__init__()

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]

    def generate_blank(self, uuid):
        return {'_id': uuid, 'balance': 0, 'low_stock': 0, 'med_stock': 0, 'high_stock': 0, 'daily_delay': 0}

    def generate_blank_dungeon(self, uuid, name):
        return {"_id": uuid, "name": name, "floor": 1, "health": 20, "max_health": 20, "level": 0, "xp": 0, "inventory": [], "armor": [], "weapon": {"name": "Wooden Sword", "attack": random.randint(1, 5)}, "room": 0, "movement": 5, "max_movement": 5, "movement_delay": 0, "effects": [], "visited": [], "interacted": []}

    async def room_callback(self, interaction: discord.Interaction, uuid: int):
        # TODO: finish
        data = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": uuid})
        floor, rooms = generate_floor_map(uuid, data['floor'])
        room = rooms[data['room']]
        #base_description = f"You move to room {data['room']}.{'\nYou are filled with a sense of dread.\nThis room is *cursed*.' if room == 'cursed' else ''}"
        
        base_description = "You move to room " + str(data['room']) + ".\n" + ("You are filled with a sense of dread.\nThis room is *cursed*." if room == 'cursed' else "")
        
        continue_path = True
        if room == 'encounter' or room == 'cursed':
            if random.random() < (0.9 if room == 'cursed' else 0.7):
                view = Combat(self.bot, self, interaction, uuid, room == 'cursed', base_description)
                embed = functions.embed("Dungeon - Combat", color=0xa6753a)
                embed.description = view.description # <------ hack thing shhhhhhh
                embed.add_field(name="Enemy Health", value=f"{view.enemy_health} HP", inline=False)
                embed.add_field(name="Your Health", value=f"{view.data['health']} HP", inline=False)
                embed.add_field(name="Your Weapon", value=f"{view.data['weapon']['name']} - {view.data['weapon']['attack']} Attack", inline=False)
                await interaction.response.send_message(embed=embed, view=view)
                self.busy.add(uuid)
                continue_path = False

        if continue_path:
            embed = functions.embed("Dungeon - Room", color=0xa6753a)
            embed.description = base_description
            await interaction.response.send_message(embed=embed)



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
            if "economy" in within["disabled_cogs"]:
                embed = functions.embed("Error: Command Disabled", color=0xff0000)
                embed.description = f"This command requires the `economy` cog to be enabled, but it has been disabled by an administrator."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
        return True

    group = app_commands.Group(name="dungeon", description="...")

    @group.command(name="enter") # enter the dungeon (definitely not copied from anywhere)
    @app_commands.describe(name="The name of your character (3-32 characters)")
    async def dungeon_enter(self, interaction: discord.Interaction, name: str) -> None:

        if len(name) > 32:
            embed = functions.embed("Error: Name Too Long", color=0xff0000)
            embed.description = "Your name must be 32 characters or less."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if len(name) < 3:
            embed = functions.embed("Error: Name Too Short", color=0xff0000)
            embed.description = "Your name must be 3 characters or more."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not name.isalnum():
            embed = functions.embed("Error: Invalid Name", color=0xff0000)
            embed.description = "Your name must only contain letters and numbers."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not self.bot.mdb["TrigBot"]["economy"].find_one({"_id": interaction.user.id}):
            self.bot.mdb["TrigBot"]["economy"].insert_one(self.generate_blank(interaction.user.id))

        if self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id}):
            embed = functions.embed("Error: Character Already Exists", color=0xff0000)
            embed.description = "You already have a character in the dungeon."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self.bot.mdb["TrigBot"]["dungeon"].insert_one(self.generate_blank_dungeon(interaction.user.id, name))
        embed = functions.embed("Dungeon Entered", color=0xa6753a)
        embed.description = f"☠️ Welcome to the dungeon, {name}!\n\nYou have 20 health and 3 movement points.\nUse `/dungeon room` to obtain more information about the room you are currently in.\nYou can use `/dungeon move` to move around the dungeon.\nYou can also use `/dungeon shop` to buy items, and `/dungeon inventory` to view your inventory.\n\nGood luck!"
        
        await interaction.response.send_message(embed=embed)

    @group.command(name="room") # view the room you are in
    async def dungeon_room(self, interaction: discord.Interaction) -> None:
        if not await self.interaction_check(interaction):
            return

        if not self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id}):
            embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
            embed.description = "You do not have a character in the dungeon.\nUse `/dungeon enter` to create one."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        dungeon = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})
        floor = dungeon["floor"]
        room = dungeon["room"]
        interacted = dungeon["interacted"]
        movement = dungeon["movement"]
        max_movement = dungeon["max_movement"]
        health = dungeon["health"]
        level = dungeon["level"]
        xp = dungeon["xp"]
        name = dungeon["name"]

        floor_map, rooms = generate_floor_map(interaction.user.id, floor)
        room_detail = rooms[room]

        embed = functions.embed(f"Floor {floor} - Room {room}", color=0xa6753a)

        if room_detail == "entrance":
            embed.description = "Above you is the entrance that you passed.\nLight shines down onto the ground."
        if room_detail == "encounter":
            embed.description = "There doesn't seem to be much here..."
        elif room_detail == "shrine":
            if room not in interacted:
                embed.description = "A golden shrine appears in the center of the room.\nUse `/dungeon interact` to worship the shrine and test your fate."
            else:
                embed.description = "A golden shrine appears in the center of the room.\nSatisfied, it rests for the next adventurer to worship it."
        elif room_detail == "cursed":
            embed.description = "Dark rot seeps across the floor.\nThis room is **cursed**.\nStronger enemies may spawn, and you are likely to recieve harmful effects if you stay here."
        elif room_detail == "loot":
            r = random.Random(interaction.user.id + floor + room)
            container = r.choice(['chest', 'bag', 'satchel'])
            if room not in interacted:
                embed.description = f"An abandoned {container} sits in the corner of the room.\nUse `/dungeon interact` to loot its items."
            else:
                embed.description = f"A {container} sits in the corner of the room.\nIts contents have already been looted."
        elif room_detail == "shop":
            embed.description = "A trader sits off to the side, willing to sell you items.\nUse `/dungeon shop` to see what they have to offer."
        elif room_detail == "exit":
            embed.description = "A trapdoor rests on the ground, leading the way to the next floor.\nIf you have a *Dungeon Key*, use `/dungeon interact` to descend to the next level."
        elif room_detail == "key":
            if room not in interacted:
                embed.description = "A shiny *Dungeon Key* lies on the ground.\nUse `/dungeon interact` to pick it up."
            else:
                embed.description = "The outline of a *Dungeon Key* appears on the ground.\nOne was sitting here for a long time..."

        connected = floor_map[room]
        indexes = [i for i, x in enumerate(connected) if x is not None]
        directions = ["north", "east", "south", "west"]
        embed.description += "\n\n"
        for i in indexes:
            embed.description += f"🚪 There is a {'door' if connected[i] > 0 else 'tunnel'} to the {directions[i]}.\n"

        await interaction.response.send_message(embed=embed)
    
    @group.command(name="move") # move around the dungeon
    @app_commands.describe(direction="The direction you want to move in")
    @app_commands.choices(direction=[
        app_commands.Choice(name="North", value="0"), 
        app_commands.Choice(name="South", value="2"),
        app_commands.Choice(name="East", value="1"),
        app_commands.Choice(name="West", value="3")])
    async def dungeon_move(self, interaction: discord.Interaction, direction: str) -> None:
        if not await self.interaction_check(interaction):
            return
        if not self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id}):
            embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
            embed.description = "You do not have a character in the dungeon.\nUse `/dungeon enter` to create one."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        data = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})
        movement = data["movement"]
        floor, rooms = generate_floor_map(interaction.user.id, data["floor"])

        
        direction = int(direction)
        connected_rooms = floor[self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})["room"]]
        if connected_rooms[direction] is None:
            embed = functions.embed("Error: No Room", color=0xff0000)
            embed.description = "There is no room in that direction.\nUse `/dungeon room` to see where you can go."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if movement <= 0:
            embed = functions.embed("Error: No Movement", color=0xff0000)
            embed.description = f"You are too exhausted to keep moving.\nIf you are able, use a Potion to restock some movement energy.\nOtherwise, you must wait until <t:{data['movement_delay']}:f> to keep moving."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        room_to_move_to = connected_rooms[direction]
        if room_to_move_to < 0:
            if movement < 2:
                embed = functions.embed("Error: Insufficient Movement Energy", color=0xff0000)
                embed.description = f"You do not have enough movement energy to use this tunnel.\nTunnels in the dungeon fold space in on itself to create pathways.\nAs such, they require **2 movement energy**, while normal pathways require 1.\nIf you are able, use a Potion to restock some movement energy.\nOtherwise, you must wait until <t:{data['movement_delay']}:f> to use the tunnel."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            else:
                movement -= 2
                self.bot.mdb['TrigBot']['dungeon'].update_one({'_id': interaction.user.id}, {"$inc": {"movement": -2}})
        
        else:
            movement -= 1
            self.bot.mdb['TrigBot']['dungeon'].update_one({'_id': interaction.user.id}, {"$inc": {"movement": -1}})
        self.bot.mdb['TrigBot']['dungeon'].update_one({'_id': interaction.user.id}, {"$set": {"room": abs(room_to_move_to)}})
        return await self.room_callback(interaction, interaction.user.id)
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Dungeon(bot))