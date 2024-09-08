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
import json
import copy

def generate_floor_map(uuid: int, floor: int):
    # uuid: the player's discord id
    # floor: the floor number

    # this function accomplishes two tasks
    # 1: generate what each room's purpose is (encounter, loot, shop, etc.)
    # 2: generate the map of the floor by connecting rooms together

    floor_map = {
        0: [None, None, None, None] # north, east, south, west
    }

    rooms = {0: "entrance"} # starting room will always be room 0
    
    rgen = random.Random((uuid + floor)) # <-- where the magic happens
    # this ensures that the same player will always get the same set of rooms in each floor
    
    togen = []
    for _ in range(10 + floor - 1):
        togen.append("encounter")

    extras = ["loot", "shrine", "cursed"]

    # randomly add extra rooms by setting encounter rooms to the extras
    for i in range(len(togen)):
        if rgen.randint(1, 100) <= 35:
            togen[i] = rgen.choices(extras, weights=[60, 25, 15])[0]
    
    togen += ["shop", "exit", "key"] # guarantee that there will be one shop, one key room, one exit

    rgen.shuffle(togen) # add randomly

    # step 1: attach rooms to each other in a grid-like fashion
    rnum = 0
    for item in togen: # for each room to generate:
        rnum += 1
        rooms[rnum] = item 
        placement = []

        # find each open face throughout the entire map that a new room can be attached to
        for room in range(len(floor_map)):
            for direction in range(len(floor_map[room])):
                if floor_map[room][direction] is None:
                    placement.append((room, direction))

        # randomly select a location to attach it to
        location = rgen.choice(placement)
        floor_map[location[0]][location[1]] = rnum
        opposite = (location[1] + 2) % 4
        temp = [None, None, None, None]
        temp[opposite] = location[0] # make the connection the other way as well
        floor_map[rnum] = temp

    # step 2: connect rooms randomly through tunnels
    for room in floor_map: # for each room in the map
        for i in range(len(floor_map[room])): # for each face of the room
            if floor_map[room][i] == None: # if the face is open (doesn't have an attached room)
                for room_2 in floor_map: # for each room in the map (again)
                    if room == room_2: continue # skip if it's the same room
                    if floor_map[room_2][(i + 2) % 4] == None and rgen.random() < 0.15: # if the opposite face of the other room is open and a random number is less than 0.15
                        floor_map[room][i] = -1 * room_2 # connect the rooms
                        floor_map[room_2][(i + 2) % 4] = -1 * room # connect the rooms the other way as well
                        break

    return floor_map, rooms # return generated map and room types

class InventoryView(discord.ui.View):
    def __init__(self, cog, db, uuid, interaction):
        super().__init__()
        self.cog = cog
        self.db = db
        self.uuid = uuid
        self.interaction = interaction
        self.user_data = self.db.find_one({"_id": self.uuid})

        self.inventory = self.user_data['inventory']
        if len(self.inventory) > 0:
            self.select_menu = discord.ui.Select(placeholder="Select an item to use", min_values=1, max_values=1, row=0)
            for i, item in enumerate(self.inventory):
                self.select_menu.add_option(label=item['name'], value=str(i))
            self.select_menu.callback = self.select_callback
            self.add_item(self.select_menu)

        nrow = 0
        if len(self.inventory) > 0:
            nrow = 1
        self.drop_button = discord.ui.Button(label="Drop", style=discord.ButtonStyle.secondary, row=nrow)
        self.drop_button.callback = self.drop_callback
        self.drop_button.disabled = True
        self.add_item(self.drop_button)
        
        self.use_button = discord.ui.Button(label="Use", style=discord.ButtonStyle.primary, row=nrow)
        self.use_button.callback = self.use_callback
        self.use_button.disabled = True
        self.add_item(self.use_button)

        self.selected = None
    
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.uuid: 
            embed = functions.embed("Error: Invalid Session", color=0xff0000)
            embed.description = "This session is not yours to interact with."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if self.uuid not in self.cog.active or self.cog.active[self.uuid] != self:
            embed = functions.embed("Error: Invalid Session", color=0xff0000)
            embed.description = "This session has expired."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def select_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction): return
        item = self.inventory[int(interaction.data['values'][0])]
        embed = functions.embed("Dungeon - Inventory", color=0xa6753a)
        embed.description = f"```{item['name']}```\n{item['desc']}"
        if item["type"] == "key" or item["type"] == "special":
            self.drop_button.disabled = True
        else:
            self.drop_button.disabled = False
        if item["type"] == "weapon":
            self.use_button.disabled = False
            self.item = item
            embed.add_field(name="Damage", value=f"{item['attack']} Damage", inline=False)
        if item["type"] == "armor":
            self.use_button.disabled = False
            self.item = item
            embed.add_field(name="Defense", value=f"{item['defense']} Defense", inline=False)
        if item["type"] == "consumable":
            self.use_button.disabled = False
            self.item = item
        if item["type"] == "special":
            embed.description = "**This item cannot be used.**\n" + embed.description
            self.use_button.disabled = True
        if item["type"] == "item":
            if "passive" in item:
                embed.description = "**This item cannot be used.**\n" + embed.description
                self.use_button.disabled = True
            elif "combat" in item:
                embed.description = "**This item cannot be used outside of combat.**\n" + embed.description
                self.use_button.disabled = True
            else:
                self.use_button.disabled = False
                self.item = item

        await interaction.response.edit_message(embed=embed, view=self)

    async def use_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction): return
        item = self.item
        if item["type"] == "weapon":
            # swap weapon
            self.user_data["inventory"].append(self.user_data["weapon"])
            self.user_data["weapon"] = item
            self.user_data["inventory"].remove(item)
            embed = functions.embed("Dungeon - Inventory", color=0xa6753a)
            embed.description = f"You equipped the `{item['name']}`."
            
        if item["type"] == "armor":
            embed = functions.embed("Dungeon - Inventory", color=0xa6753a)
            embed.description = f"You equipped the `{item['name']}`."
            values = ["Helmet", "Chestplate", "Leggings", "Boots"]
            index = -1
            for i, value in enumerate(values):
                if value in item["name"]:
                    index = i
                    break
            temp = self.user_data["armor"][index]
            self.user_data["armor"][index] = item
            self.user_data["inventory"].remove(item)
            if temp is not None:
                self.user_data["inventory"].append(temp)
        if item["type"] == "consumable":
            self.user_data["inventory"].remove(item)
            embed = functions.embed("Dungeon - Inventory", color=0xa6753a)
            embed.description = f"You used the `{item['name']}`."
            if "Potion" in item["name"]:
                if "Powerup" in item["name"]:
                    self.user_data["effects"].append({"name": "powerup", "duration": item["data"]["duration"], "power": item["data"]["power"]})
                if "Precision" in item["name"]:
                    self.user_data["effects"].append({"name": "precision", "duration": item["data"]["duration"], "power": item["data"]["power"]})
                if "Regeneration" in item["name"]:
                    self.user_data["effects"].append({"name": "regeneration", "duration": item["data"]["duration"], "power": item["data"]["power"]})
                if "Health" in item["data"]:
                    self.user_data["health"] += item["data"]["power"]
                    self.user_data["health"] = min(self.user_data["health"], self.user_data["max_health"])
                if "Hardening" in item["name"]:
                    self.user_data["effects"].append({"name": "hardening", "duration": item["data"]["duration"], "power": item["data"]["power"]})
                if "Evasion" in item["name"]:
                    self.user_data["effects"].append({"name": "evasion", "duration": item["data"]["duration"], "power": item["data"]["power"]})
        elif item["type"] == "item":
            # remove item from inventory
            self.user_data["inventory"].remove(item)
            if item["name"] == "Smoke Bomb":
                self.active.append({"name": "smokebomb", "duration": item["data"]["duration"] + 1, "power": item["data"]["power"]})
            if item["name"] == "Bandages":
                self.user_data["health"] += item["data"]["power"]
                self.user_data["health"] = min(self.user_data["health"], self.user_data["max_health"])
                

        await interaction.response.edit_message(embed=embed, view=None)
        self.db.update_one({"_id": self.uuid}, {"$set": self.user_data})

    async def drop_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction): return
        item = self.inventory[int(interaction.data['values'][0])]
        embed = functions.embed("Dungeon - Inventory", color=0xa6753a)
        embed.description = f"You dropped the `{item['name']}`."
        self.user_data["inventory"].remove(item)
        await interaction.response.edit_message(embed=embed, view=None)
        self.db.update_one({"_id": self.uuid}, {"$set": self.user_data})

class UserView(discord.ui.View):
    def __init__(self, db, uuid, target):
        self.db = db
        self.uuid = uuid
        self.user_data = self.db.find_one({"_id": target})
        self.target = target
        super().__init__()

        options = ["Overview", "Armor", "Weapon", "Inventory", "Effects"]
        self.select_menu = discord.ui.Select(placeholder="Select a category", min_values=1, max_values=1, row=0)
        for i, option in enumerate(options):
            self.select_menu.add_option(label=option, value=str(i))
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.uuid:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = f"This menu is in use by <@{self.uuid}>."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def select_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction): return
        value = int(interaction.data['values'][0])
        if value == 0:
            embed = functions.embed("Dungeon - User", color=0xa6753a)
            embed.description = "Overview for <@{}>".format(self.target)
            embed.add_field(name="Name", value=self.user_data["name"], inline=False)
            embed.add_field(name="Level", value=self.user_data["level"], inline=False)
            level_req = 5 * (self.user_data["level"] ** 2) + 50 * self.user_data["level"] + 100
            embed.add_field(name="Experience", value="{}/{}".format(self.user_data["xp"], level_req), inline=False)
            embed.add_field(name="Health", value="{}/{}".format(self.user_data["health"], self.user_data["max_health"]), inline=False)
            embed.add_field(name="Floor", value=self.user_data["floor"], inline=False)
            await interaction.response.edit_message(embed=embed, view=self)
        elif value == 1:
            embed = functions.embed("Dungeon - User", color=0xa6753a)
            embed.description = "Armor for <@{}>".format(self.target)
            for i, piece in enumerate(["Helmet", "Chestplate", "Leggings", "Boots"]):
                if self.user_data["armor"][i] == None:
                    embed.add_field(name=piece, value=f"No {piece.lower()} equipped", inline=False)
                else:
                    embed.add_field(name=piece, value=self.user_data["armor"][i]["name"] + " - " + str(self.user_data["armor"][i]["defense"]) + " Defense", inline=False)
            await interaction.response.edit_message(embed=embed, view=self)
        elif value == 2:
            embed = functions.embed("Dungeon - User", color=0xa6753a)
            embed.description = "Weapon for <@{}>".format(self.target)
            if self.user_data["weapon"] == None:
                embed.add_field(name="Weapon", value="No weapon equipped", inline=False)
            else:
                embed.add_field(name="Weapon", value=self.user_data["weapon"]["name"], inline=False)
                embed.add_field(name="Description", value=self.user_data["weapon"]["desc"], inline=False)
                embed.add_field(name="Attack", value=self.user_data["weapon"]["attack"], inline=False)
            await interaction.response.edit_message(embed=embed, view=self)
        elif value == 3:
            embed = functions.embed("Dungeon - User", color=0xa6753a)
            embed.description = "Inventory for <@{}>\n".format(self.target)
            desc = ""
            if len(self.user_data["inventory"]) == 0:
                desc += "No items in inventory"
            else:
                for i, item in enumerate(self.user_data["inventory"]):
                    desc += f"`{i + 1}.` {item['name']}\n"
            embed.add_field(name="Inventory", value=desc, inline=False)
            await interaction.response.edit_message(embed=embed, view=self)
        elif value == 4:
            embed = functions.embed("Dungeon - User", color=0xa6753a)
            embed.description = "Effects for <@{}>".format(self.target)
            if len(self.user_data["effects"]) == 0:
                embed.add_field(name="Effects", value="No active effects", inline=False)
            else:
                # check to see if its a debuff
                for i, effect in enumerate(self.user_data["effects"]):
                    name = effect["name"]
                    if name == "hardening" and effect["power"] < 0:
                        name = "vulnerability"
                    if name == "evasion" and effect["power"] < 0:
                        name = "slowness"
                    embed.add_field(name=f"{i+1}. {name.title()}", value=f"Power: {effect['power']}%\nDuration: {effect['duration']} rooms", inline=False)
            await interaction.response.edit_message(embed=embed, view=self)

class ShopView(discord.ui.View):
    def __init__(self, cog, uuid, floor, room, purchased_already, tempembed):
        self.cog = cog
        self.uuid = uuid
        self.user_data = self.cog.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": self.uuid})
        self.floor = floor
        super().__init__()
        self.purchased_already = purchased_already
        self.room = room

        
        
        # generate items for shop to sell
        self.items = []
        self.raw_items = []
        rgen = random.Random(uuid + floor + room)
        for i in range(rgen.randint(3, 5)):
            rarities = ["common", "rare", "epic"]
            rarity = rgen.choices(rarities, weights=[70, 24, 6])[0]
            # get all items of that rarity
            items = [item for item in self.cog.items if item["rarity"] == rarity]
            item = rgen.choice(items)
            if item["type"] == "weapon":
                level = max(1, self.user_data['level'] + rgen.randint(-1, 5))
                sword = copy.deepcopy(item)
                sword['name'] = "Level " + str(level) + " " + item['name']
                sword["attack"] = max(1, level * sword["data"]["power"] + rgen.randint(0, int(sword["data"]["power"])))
                sword["cost"] = max(1, level // 2 * (rarities.index(rarity) + 1) * 4 + rgen.randint(0, int(sword["data"]["power"])))
                self.raw_items.append(sword)
            elif item["type"] == "armor":
                level = max(1, self.user_data['level'] + rgen.randint(-1, 5))
                armor = copy.deepcopy(item)
                armor['name'] = "Level " + str(level) + " " + item['name']
                armor["defense"] = max(1, level * armor["data"]["defense"] // 2 + rgen.randint(0, armor["data"]["defense"]))
                armor["cost"] = max(1, level // 2 * (rarities.index(rarity) + 1) * 4 + rgen.randint(0, armor["data"]["defense"]))
                self.raw_items.append(armor)
            else:
                item = copy.deepcopy(item)
                item["cost"] = max(1, (rarities.index(rarity) + 1) * 50 + rgen.randint(-10, 10))
                self.raw_items.append(item)
        for i, item in enumerate(self.raw_items):
            if i not in purchased_already:
                self.items.append(item)
    

        if len(self.items) > 0:
            self.select_menu = discord.ui.Select(placeholder="Select an item to buy", min_values=1, max_values=1, row=0)
                
            for i, item in enumerate(self.items):
                self.select_menu.add_option(label=item['name'], value=str(i))     
            self.select_menu.callback = self.select_callback
            self.add_item(self.select_menu)
        else:
            tempembed.description += "\n**There are no items left to buy from this shop.**"

        self.buy_button = discord.ui.Button(label="Buy", style=discord.ButtonStyle.primary, row=1)
        self.buy_button.callback = self.buy_callback
        self.buy_button.disabled = True
        self.add_item(self.buy_button)
        self.item = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.uuid:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "This shop is currently being used by <@{}>".format(self.uuid)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if self.uuid not in self.cog.active or self.cog.active[self.uuid] != self:
            embed = functions.embed("Error: Invalid Session", color=0xff0000)
            embed.description = "This session has expired."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    async def select_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction):
            return
        item = self.items[int(interaction.data["values"][0])]
        embed = functions.embed("Dungeon - Shop", color=0xa6753a)
        cost = item["cost"]
        coins = self.cog.bot.mdb["TrigBot"]["economy"].find_one({"_id": self.uuid})["balance"]
        if coins < cost:
            embed.description = "**You do not have enough coins to buy this item.**\n"
            self.buy_button.disabled = True
            self.item = None
        else:
            embed.description = ""
            self.buy_button.disabled = False
            self.item = item
        embed.description += f"**Coins**: {coins}\n**Cost**: {cost}\n---\n**{item['name']}**\n{item['desc']}"
        await interaction.response.edit_message(embed=embed, view=self)

    async def buy_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction):
            return
        item = self.item
        cost = item["cost"]
        coins = self.cog.bot.mdb["TrigBot"]["economy"].find_one({"_id": self.uuid})["balance"]
        if coins < cost:
            embed = functions.embed("Error: Not Enough Coins", color=0xff0000)
            embed.description = "You do not have enough coins to buy this item."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.cog.bot.mdb["TrigBot"]["economy"].update_one({"_id": self.uuid}, {"$inc": {"balance": -cost}})
        inventory = self.cog.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": self.uuid})["inventory"]
        inventory.append(item)
        self.cog.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$set": {"inventory": inventory}})
        embed = functions.embed("Dungeon - Shop", color=0xa6753a)
        embed.description = f"**{item['name']}** has been added to your inventory."
        # edit bought items for this shop
        #self.purchased_already.append(int(interaction.data["values"][0]))
        self.purchased_already.append(self.raw_items.index(item))
        shop_bought = self.cog.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": self.uuid})["shop_bought"]
        shop_bought[str(self.room)] = self.purchased_already
        self.cog.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$set": {"shop_bought": shop_bought}})
        self.cog.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$set": {"inventory": inventory}})
        await interaction.response.edit_message(embed=embed, view=None)
        


class CombatInventoryView(discord.ui.View):
    def __init__(self, cv, interaction: discord.Interaction):
        # here's hoping i don't get ratelimited
        super().__init__()
        self.cv = cv
        self.interaction = interaction
        self.user_data = self.cv.data

        self.inventory = self.user_data['inventory']
        if len(self.inventory) > 0:
            self.select_menu = discord.ui.Select(placeholder="Select an item to use", min_values=1, max_values=1, row=0)
            for i, item in enumerate(self.inventory):
                self.select_menu.add_option(label=item['name'], value=str(i))
            self.select_menu.callback = self.select_callback
            self.add_item(self.select_menu)

        self.back_button = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, row=1)
        self.back_button.callback = self.back_callback
        self.add_item(self.back_button)

        self.use_button = discord.ui.Button(label="Use", style=discord.ButtonStyle.primary, row=1)
        self.use_button.callback = self.use_callback
        self.use_button.disabled = True
        self.add_item(self.use_button)

        self.selected = None



    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.cv.uuid: 
            embed = functions.embed("Error: Invalid Combat Session", color=0xff0000)
            embed.description = "This session is not yours to interact with."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if self.cv.uuid not in self.cv.busy:
            embed = functions.embed("Error: Invalid Combat Session", color=0xff0000)
            embed.description = "This combat session has expired."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def select_callback(self, interaction):
        if not await self.interaction_check(interaction): return
        item = self.inventory[int(interaction.data['values'][0])]
        embed = functions.embed("Dungeon - Inventory", color=0xa6753a)
        embed.description = f"```{item['name']}```\n{item['desc']}"
        if item["type"] == "weapon":
            embed.description = "**You are unable to switch weapons during combat.**\n" + embed.description
            self.use_button.disabled = True
        if item["type"] == "armor":
            embed.description = "**You are unable to switch armor during combat.**\n" + embed.description
            self.use_button.disabled = True
        if item["type"] == "consumable":
            self.use_button.disabled = False
            self.item = item
        if item["type"] == "special":
            embed.description = "**This item cannot be used.**\n" + embed.description
            self.use_button.disabled = True
        if item["type"] == "item":
            if "passive" in item:
                embed.description = "**This item cannot be used.**\n" + embed.description
                self.use_button.disabled = True
            else:
                self.use_button.disabled = False
                self.item = item

        await interaction.response.edit_message(embed=embed, view=self)
        

    async def back_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction): return
        await self.cv.inventory_callback(interaction, None)


    async def use_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction): return
        # remove item
        self.user_data['inventory'].remove(self.item)
        await self.cv.inventory_callback(interaction, self.item)

        


class CombatView(discord.ui.View):
    def __init__(self, bot: commands.Bot, busy: set, db, interaction: discord.Interaction, uuid: int, cursed: bool, retembed):
        super().__init__()
        self.bot = bot
        self.busy = busy
        self.db = db
        self.interaction = interaction
        self.uuid = uuid
        self.cursed = cursed
        
        self.data = self.db["TrigBot"]["dungeon"].find_one({"_id": self.uuid})

        enemies = ["Skeleton", "Orc", "Spider", "Ghoul", "Troll", "Bandit", "Mummy", "Werewolf", "Dark Wizard", "Necromancer", "Minotaur", "Lich", "Gargoyle", "Demon", "Dragon"]
        
        level = self.data['level']
        floor = self.data['floor']

        if level < 5:
            self.enemy = random.choice(enemies[:5])
        elif level < 10:
            self.enemy = random.choice(enemies[:10])
        else:
            self.enemy = random.choice(enemies)

        
        self.enemy_level = max(1, level + random.randint(-2, 2))
        if self.cursed:
            self.enemy_level += random.randint(1, 10)
        self.enemy_health = 15 + (level * 2) + (floor * 2) + random.randint(-5, 5) + (self.enemy_level // 2)
        self.enemy_damage = max(1, self.enemy_level + (floor // 2) + random.randint(-2, 2))

        self.description = f"\n You encounter a **{'Cursed ' if self.cursed else ''}Level {self.enemy_level} {self.enemy}**!\nUse the buttons below to fight it."

        self.defense_chance = 20
        self.hit_chance = 70
        self.flee_chance = 35
        if self.cursed:
            self.defense_chance = 10
            self.hit_chance = 50
            self.flee_chance = 15

        self.active = []
        self.retembed = retembed

    async def inventory_callback(self, interaction: discord.Interaction, item):
        if not await self.button_check(interaction): return
        if item is None:
            await interaction.response.edit_message(embed=self.retembed, view=self)
            return
        # im sorry in advance
        if item["type"] == "consumable":
            if "Potion" in item["name"]:
                if "Powerup" in item["name"]:
                    self.data["effects"].append({"name": "powerup", "duration": item["data"]["duration"], "power": item["data"]["power"]})
                if "Precision" in item["name"]:
                    self.data["effects"].append({"name": "precision", "duration": item["data"]["duration"], "power": item["data"]["power"]})
                if "Regeneration" in item["name"]:
                    self.data["effects"].append({"name": "regeneration", "duration": item["data"]["duration"], "power": item["data"]["power"]})
                if "Health" in item["data"]:
                    self.data["health"] += item["data"]["power"]
                    self.data["health"] = min(self.data["health"], self.data["max_health"])
                if "Hardening" in item["name"]:
                    self.data["effects"].append({"name": "hardening", "duration": item["data"]["duration"], "power": item["data"]["power"]})
                if "Evasion" in item["name"]:
                    self.data["effects"].append({"name": "evasion", "duration": item["data"]["duration"], "power": item["data"]["power"]})
        elif item["type"] == "item":
            if item["name"] == "Smoke Bomb":
                self.active.append({"name": "smokebomb", "duration": item["data"]["duration"] + 1, "power": item["data"]["power"]})
            if item["name"] == "Bandages":
                self.data["health"] += item["data"]["power"]
                self.data["health"] = min(self.data["health"], self.data["max_health"])

        self.db["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$set": self.data})
        embed = function.embed("Dungeon - Combat", color=0xa6753a)
        embed.description = f"You used the `{item['name']}` item!\n\n"
        embed.add_field(name="Enemy Health", value=f"{self.enemy_health} HP", inline=False)
        embed.add_field(name="Your Health", value=f"{self.data['health']} HP", inline=False)
        embed.add_field(name="Your Weapon", value=f"{self.data['weapon']['name']} - {self.data['weapon']['attack']} Attack", inline=False)
                
        await self.do_enemy_attack(interaction, embed)


    async def button_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.uuid: 
            embed = functions.embed("Error: Invalid Combat Session", color=0xff0000)
            embed.description = "This session is not yours to interact with."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if self.uuid not in self.busy:
            embed = functions.embed("Error: Invalid Combat Session", color=0xff0000)
            embed.description = "This combat session has expired."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True    

    async def do_enemy_attack(self, interaction: discord.Interaction, embed: discord.Embed):
        tempitems = []
        for item in self.active:
            item['duration'] -= 1
            if item['duration'] > 0:
                tempitems.append(item)
        self.active = tempitems

        desc = embed.description
        ndesc = desc + "The enemy decides what to do..."
        embed.description = ndesc
        await interaction.response.edit_message(embed=embed, view=None)
        await asyncio.sleep(3)
        
        embed.description = desc + "The enemy attacks!\n"
        damage = self.enemy_damage
        for effect in self.data["effects"]:
            if effect["name"] == "hardening":
                damage *= 1 - (effect["power"] / 100)
        for item in self.data["armor"]:
            if item is None: continue
            damage -= item["defense"]

        damage = max(0, damage)

        if random.randint(1, 100) <= self.defense_chance:
            embed.description += "You successfully defended yourself!\n"
        else:
            embed.description += f"You took {damage} damage!\n"
            self.data['health'] -= damage
            if self.data['health'] <= 0:
                embed.description += f"You died!\n\n***Game over***.\nYou made it to **Floor {self.data['floor']}**.\nYour character has been moved back to the start of the dungeon.\nUse `/dungeon room` to see where you are."
                # disable all buttons
                for child in self.children:
                    child.disabled = True
                # remove all fields
                embed.clear_fields()

                await interaction.edit_original_response(embed=embed, view=None)
                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$set": {"health": self.data['max_health'], "floor": 1, "room": 0, "effects": []}})
                self.busy.remove(self.uuid)
                return
            else:
                embed.description += f"You now have **{self.data['health']} HP** left.\n"
        self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$set": {"health": self.data['health']}})
        embed.description += f"\nUse the buttons below to continue fighting."
        
        embed.clear_fields()
        embed.add_field(name="Enemy Health", value=f"{self.enemy_health} HP", inline=False)
        embed.add_field(name="Your Health", value=f"{self.data['health']} HP", inline=False)
        embed.add_field(name="Your Weapon", value=f"{self.data['weapon']['name']} - {self.data['weapon']['attack']} Attack", inline=False)
        self.retembed = embed        
        await interaction.edit_original_response(embed=embed, view=self)


    @discord.ui.button(label="Attack", style=discord.ButtonStyle.primary)
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.button_check(interaction): return
        attack_strength = self.data['weapon']['attack']
        hit_chance = self.hit_chance
        for effect in self.data['effects']:
            if effect['name'] == "powerup":
                attack_strength *= (1 + (effect['power'] / 100))
            if effect['name'] == "powerdown":
                attack_strength *= (1 - (effect['power'] / 100))
            if effect['name'] == "precision":
                hit_chance *= (1 + (effect['power'] / 100))

        incr = 0
        for item in self.data["armor"]:
            if item is None: continue
            if "Iron" in item["name"]:
                incr += 10
            elif "Dragon Scale" in item["name"]:
                incr += 12.5

        attack_strength *= (1 + (incr / 100))
        attack_strength = int(round(attack_strength))

        if random.randint(1, 100) <= hit_chance:
            self.enemy_health -= attack_strength
            if self.enemy_health <= 0:
                embed = functions.embed("Dungeon - Combat", color=0xa6753a)
                embed.description = f"You defeated the {self.enemy}!\n"
                xp = 5 + (self.enemy_level * 2 * random.randint(3, 7)) + (25 if self.cursed else 0)
                self.data['xp'] += xp
                embed.description += f"You gained **{xp} XP**!\n"
                level_req = 5 * (self.data['level'] ** 2) + 50 * self.data['level'] + 100
                if self.data['xp'] >= level_req:
                    self.data['level'] += 1
                    self.data['xp'] -= level_req
                    self.data['max_health'] += 10
                    self.data['health'] += 10
                    embed.description += f"You leveled up to **Level {self.data['level']}**!\n"
                embed.description += "You may now continue your journey.\nUse `/dungeon room` to see where you are."
                

                await interaction.response.edit_message(embed=embed, view=None)
                for child in self.children:
                    child.disabled = True
                self.busy.remove(self.uuid)
                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$set": self.data})

            else:
                embed = functions.embed("Dungeon - Combat", color=0xa6753a)
                embed.description = f"You attacked the {self.enemy} for {attack_strength} damage!\nIt now has {self.enemy_health} HP left.\n\n"
                embed.add_field(name="Enemy Health", value=f"{self.enemy_health} HP", inline=False)
                embed.add_field(name="Your Health", value=f"{self.data['health']} HP", inline=False)
                embed.add_field(name="Your Weapon", value=f"{self.data['weapon']['name']} - {self.data['weapon']['attack']} Attack", inline=False)
                await self.do_enemy_attack(interaction, embed)
        else:
            embed = functions.embed("Dungeon - Combat", color=0xa6753a)
            embed.description = f"You missed your attack!\n\n"
            embed.add_field(name="Enemy Health", value=f"{self.enemy_health} HP", inline=False)
            embed.add_field(name="Your Health", value=f"{self.data['health']} HP", inline=False)
            embed.add_field(name="Your Weapon", value=f"{self.data['weapon']['name']} - {self.data['weapon']['attack']} Attack", inline=False)
            await self.do_enemy_attack(interaction, embed)

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary)
    async def defend(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.button_check(interaction): return
        embed = functions.embed("Dungeon - Combat", color=0xa6753a)
        embed.description = f"You stood your ground!\nYour defense increased.\n\n"
        self.defense_chance += 10
        embed.add_field(name="Enemy Health", value=f"{self.enemy_health} HP", inline=False)
        embed.add_field(name="Your Health", value=f"{self.data['health']} HP", inline=False)
        embed.add_field(name="Your Weapon", value=f"{self.data['weapon']['name']} - {self.data['weapon']['attack']} Attack", inline=False)
        
        await self.do_enemy_attack(interaction, embed)
        self.defense_chance -= 10

    @discord.ui.button(label="Inventory", style=discord.ButtonStyle.primary)
    async def inventory(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.button_check(interaction): return 
        embed = functions.embed("Dungeon - Inventory", color=0xa6753a)
        embed.description = "Select an item to use in combat."
        inventory = self.data['inventory']
        if len(inventory) == 0:
            embed.description += "\n**You have no items in your inventory.**"
        view = CombatInventoryView(self, interaction)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Flee", style=discord.ButtonStyle.red)
    async def flee(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.button_check(interaction): return
        embed = functions.embed("Dungeon - Combat", color=0xa6753a)

        # detect if smokebomb is active
        for item in self.active:
            if item['name'] == "smokebomb":
                self.flee_chance += item['power']
        
        for effect in self.data['effects']:
            if effect['name'] == "flee":
                self.flee_chance += effect['power']

        for item in self.data["armor"]:
            if item is None: continue
            if "Obsidian" in item["name"]:
                self.flee_chance += 5
            if "Dragon Scale" in item["name"]:
                self.flee_chance += 7.5
        
        embed.add_field(name="Enemy Health", value=f"{self.enemy_health} HP", inline=False)
        embed.add_field(name="Your Health", value=f"{self.data['health']} HP", inline=False)
        embed.add_field(name="Your Weapon", value=f"{self.data['weapon']['name']} - {self.data['weapon']['attack']} Attack", inline=False)

        if random.randint(1, 100) <= self.flee_chance:
            embed.description = f"You successfully fled the {self.enemy}!\nYou may now continue your journey.\nUse `/dungeon room` to see where you are."
            embed.clear_fields()
            await interaction.response.edit_message(embed=embed, view=None)
            for child in self.children:
                child.disabled = True
            self.busy.remove(self.uuid)
            self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": self.uuid}, {"$set": self.data})

        else:
            embed.description = "You tried to run, but couldn't get away!\n\n"
            await self.do_enemy_attack(interaction, embed)
    
base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def get_room_description(floor, floor_map, rooms, room, uuid, interacted):
    room_detail = rooms[room]
    description = ""
    if room_detail == "entrance":
        description = "Above you is the entrance that you passed.\nLight shines down onto the ground."
    if room_detail == "encounter":
        description = "There doesn't seem to be much here..."
    elif room_detail == "shrine":
        if room not in interacted:
            description = "A golden shrine appears in the center of the room.\nUse `/dungeon interact` to worship the shrine and test your fate."
        else:
            description = "A golden shrine appears in the center of the room.\nSatisfied, it rests for the next adventurer to worship it."
    elif room_detail == "cursed":
        description = "Dark rot seeps across the floor.\nThis room is **cursed**.\nStronger enemies may spawn, and you are likely to recieve harmful effects if you stay here."
    elif room_detail == "loot":
        r = random.Random(uuid + floor + room)
        container = r.choice(['chest', 'bag', 'satchel'])
        if room not in interacted:
            description = f"An abandoned {container} sits in the corner of the room.\nUse `/dungeon interact` to loot its items."
        else:
            description = f"A {container} sits in the corner of the room.\nIts contents have already been looted."
    elif room_detail == "shop":
        description = "A trader sits off to the side, willing to sell you items.\nUse `/dungeon shop` to see what they have to offer."
    elif room_detail == "exit":
        description = "A trapdoor rests on the ground, leading the way to the next floor.\nIf you have a *Dungeon Key*, use `/dungeon interact` to descend to the next level."
    elif room_detail == "key":
        if room not in interacted:
            description = "A shiny *Dungeon Key* lies on the ground.\nUse `/dungeon interact` to pick it up."
        else:
            description = "The outline of a *Dungeon Key* appears on the ground.\nOne was sitting here for a long time..."

    connected = floor_map[room]
    indexes = [i for i, x in enumerate(connected) if x is not None]
    directions = ["north", "east", "south", "west"]
    description += "\n\n"
    for i in indexes:
        description += f"🚪 There is a {'door' if connected[i] > 0 else 'tunnel'} to the {directions[i]}.\n"

    return description

class Dungeon(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
        self.busy = set()
        self.active = {}
        super().__init__()

        with open(os.path.join(base, "assets", "dungeon", "items.json"), encoding='utf-8') as f:
            self.items = json.load(f)


    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]

    def generate_blank(self, uuid):
        return {'_id': uuid, 'balance': 0, 'low_stock': 0, 'med_stock': 0, 'high_stock': 0, 'daily_delay': 0}

    async def room_callback(self, interaction, uuid):
        data = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": uuid})
        floor, rooms = generate_floor_map(uuid, data['floor'])
        room = rooms[data['room']]
        
        base_description = "You move to room " + str(data['room']+1) + "." + ("\nYou are filled with a sense of dread.\nThis room is *cursed*." if room == 'cursed' else "")
        continue_path = True
        if room == 'encounter' or room == 'cursed':
            if random.random() < (0.9 if room == 'cursed' else 0.7):
                self.busy.add(uuid)
                view = CombatView(self.bot, self.busy, self.bot.mdb, interaction, uuid, room == 'cursed', base_description)
                embed = functions.embed("Dungeon - Combat", color=0xa6753a)
                embed.add_field(name="Enemy Health", value=f"{view.enemy_health} HP", inline=False)
                embed.add_field(name="Your Health", value=f"{view.data['health']} HP", inline=False)
                embed.add_field(name="Your Weapon", value=f"{view.data['weapon']['name']} - {view.data['weapon']['attack']} Attack", inline=False)
                embed.description = base_description + view.description
                view.retembed = embed
                await interaction.response.send_message(embed=embed, view=view)
                continue_path = False

        if continue_path:
            embed = functions.embed("Dungeon - Room", color=0xa6753a)
            embed.description = base_description + "\n" + get_room_description(data['floor'], floor, rooms, data['room'], uuid, data['interacted'])
            embed.description += "\nUse `/dungeon move` to move to a different room."
            await interaction.response.send_message(embed=embed)


    def generate_blank_dungeon(self, uuid, name):
        # get wooden sword item
        wooden_sword = None
        for item in self.items:
            if item['name'] == "Wooden Sword":
                wooden_sword = item
                break
        assert wooden_sword is not None
        wooden_sword = copy.deepcopy(wooden_sword)
        level = 1
        wooden_sword['name'] = "Level " + str(level) + " " + wooden_sword['name']
        wooden_sword["attack"] = 5 # let's make it a bit fair

        bought = {}
        # get room data
        floor, rooms = generate_floor_map(uuid, 1)
        for room in rooms:
            if rooms[room] == "shop":
                bought[str(room)] = []

        return {
            "_id": uuid,
            "name": name,
            "floor": 1,
            "room": 0,
            "health": 20,
            "max_health": 20,
            "visited": [],
            "interacted": [],
            "xp": 0,
            "level": 1,
            "effects": [],
            "inventory": [],
            "armor": [None, None, None, None],
            "weapon": wooden_sword,
            "shop_bought": bought
        }

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
        """Enter the dungeon"""
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
        embed.description = f"☠️ Welcome to the dungeon, {name}!\n\nYou have 20 health.\nUse `/dungeon room` to obtain more information about the room you are currently in.\nYou can use `/dungeon move` to move around the dungeon.\nYou can also use `/dungeon shop` to buy items, and `/dungeon inventory` to view your inventory.\n\nYour objective is to traverse the dungeon and find 5 items of extreme value:\n- *The Echoing Sphere*\n- *The Flickering Light*\n- *The Timeless Tear*\n- *The Glowing Thread*\n- *The Endless Flame*\nOnly then will you be able to escape.\n\nGood luck!"
        
        await interaction.response.send_message(embed=embed)

    @group.command(name="room") # view the room you are in
    async def dungeon_room(self, interaction: discord.Interaction) -> None:
        """View information on the room you are in"""
        if not await self.interaction_check(interaction):
            return

        if not self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id}):
            embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
            embed.description = "You do not have a character in the dungeon.\nUse `/dungeon enter` to create one."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if interaction.user.id in self.busy:
            embed = functions.embed("Error: Busy", color=0xff0000)
            embed.description = "This command cannot be used while in combat."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        dungeon = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})
        floor = dungeon["floor"]
        room = dungeon["room"]
        interacted = dungeon["interacted"]

        floor_map, rooms = generate_floor_map(interaction.user.id, floor)
        room_detail = rooms[room]

        embed = functions.embed(f"Dungeon - Floor {floor}, Room {room+1}", color=0xa6753a)

        embed.description = get_room_description(floor, floor_map, rooms, room, interaction.user.id, interacted) 
        embed.description += "\nUse `/dungeon move` to move to a different room."
        if interaction.user.id in self.active: del self.active[interaction.user.id]
        await interaction.response.send_message(embed=embed)


    @group.command(name="move") # move around the dungeon
    @app_commands.describe(direction="The direction you want to move in")
    @app_commands.choices(direction=[
        app_commands.Choice(name="North", value="0"), 
        app_commands.Choice(name="South", value="2"),
        app_commands.Choice(name="East", value="1"),
        app_commands.Choice(name="West", value="3")])
    async def dungeon_move(self, interaction: discord.Interaction, direction: str) -> None:
        """Move around the dungeon"""
        if not await self.interaction_check(interaction):
            return
        if not self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id}):
            embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
            embed.description = "You do not have a character in the dungeon.\nUse `/dungeon enter` to create one."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if interaction.user.id in self.busy:
            embed = functions.embed("Error: Busy", color=0xff0000)
            embed.description = "This command cannot be used while in combat."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return


        data = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})
        floor, rooms = generate_floor_map(interaction.user.id, data["floor"])

        
        direction = int(direction)
        connected_rooms = floor[self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})["room"]]
        if connected_rooms[direction] is None:
            embed = functions.embed("Error: No Room", color=0xff0000)
            embed.description = "There is no room in that direction.\nUse `/dungeon room` to see where you can go."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        room_to_move_to = connected_rooms[direction]
        self.bot.mdb['TrigBot']['dungeon'].update_one({'_id': interaction.user.id}, {"$set": {"room": abs(room_to_move_to)}})
        for effect in data["effects"]:
            if effect["name"] == "regeneration":
                health = data["health"]
                health += (effect["power"] / 100) * data["max_health"]
                health = min(health, data["max_health"])
                self.bot.mdb['TrigBot']['dungeon'].update_one({'_id': interaction.user.id}, {"$set": {"health": health}})
            if effect["name"] == "poison":
                health = data["health"]
                health -= effect["power"]
                health = max(health, 0)
                if health == 0:
                    embed = functions.embed("Game Over", color=0xa6753a)
                    embed.description += f"You died!\n\n***Game over***.\nYou made it to floor {self.data['floor']}.\nUse `/dungeon enter` to start a new game."
                    # remove from db
                    self.bot.mdb['TrigBot']['dungeon'].delete_one({'_id': interaction.user.id})
                    await interaction.response.send_message(embed=embed)
                self.bot.mdb['TrigBot']['dungeon'].update_one({'_id': interaction.user.id}, {"$set": {"health": health}})
            effect['duration'] -= 1
            if effect['duration'] <= 0:
                data['effects'].remove(effect)
        self.bot.mdb['TrigBot']['dungeon'].update_one({'_id': interaction.user.id}, {"$set": {"effects": data['effects']}})
        
        # passive regen
        health = data["health"]
        health += 2
        health = min(health, data["max_health"])
        self.bot.mdb['TrigBot']['dungeon'].update_one({'_id': interaction.user.id}, {"$set": {"health": health}})
        
        if interaction.user.id in self.active: del self.active[interaction.user.id]
        return await self.room_callback(interaction, interaction.user.id)

    @group.command(name="info") # view the room
    async def dungeon_info(self, interaction: discord.Interaction) -> None:
        """Get info about the dungeon"""
        embed = functions.embed("Dungeon - Info", color=0xa6753a)
        embed.description = """The **Chasm of Chaos** is a dungeon that can only be described by one word: *unpredictable*.\nIts labyrinth-like floors are seemingly randomized, with rooms connected by a series of twisting corridors and winding tunnels.\n\nBrave adventurers that choose to jump in are told that fame, fortune, and glory await them inside.\nHowever, *none have been reported to make it out alive...*\n\nThink you're up for the challenge?\nRun `/dungeon enter` to begin."""
        await interaction.response.send_message(embed=embed)

    @group.command(name="shop") # view the shop
    async def dungeon_shop(self, interaction: discord.Interaction) -> None:
        """View the shop"""
        if not await self.interaction_check(interaction):
            return
        if not self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id}):
            embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
            embed.description = "You do not have a character in the dungeon.\nUse `/dungeon enter` to create one."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if interaction.user.id in self.busy:
            embed = functions.embed("Error: Busy", color=0xff0000)
            embed.description = "This command cannot be used while in combat."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        
        # check if the room is a shop
        data = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})
        floor, rooms = generate_floor_map(interaction.user.id, data["floor"])
        room = rooms[data["room"]]
        if room != "shop":
            embed = functions.embed("Error: Not a Shop", color=0xff0000)
            embed.description = "You are not in a shop.\nUse `/dungeon room` to see where you are."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        inventory = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})["inventory"]
        if len(inventory) >= 10:
            embed = functions.embed("Error: Inventory Full", color=0xff0000)
            embed.description = "You cannot buy any more items.\nUse `/dungeon inventory` to see your inventory."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # get bought items for that specific shop
        bought_items = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})["shop_bought"][str(data["room"])]
        embed = functions.embed("Dungeon - Shop", color=0xa6753a)
        embed.description = "Select an item to buy."
        
        if interaction.user.id in self.active: del self.active[interaction.user.id]
        view = ShopView(self, interaction.user.id, data['floor'], data['room'], bought_items, embed)
        self.active[interaction.user.id] = view
        await interaction.response.send_message(embed=embed, view=view)

    @group.command(name="clear")
    async def dungeon_clear(self, interaction: discord.Interaction) -> None:
        """Clear your dungeon data"""
        if not await self.interaction_check(interaction):
            return
        if not self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id}):
            embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
            embed.description = "You do not have a character in the dungeon.\nUse `/dungeon enter` to create one."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if interaction.user.id in self.active: del self.active[interaction.user.id]

        if interaction.user.id in self.busy:
            embed = functions.embed("Error: Busy", color=0xff0000)
            embed.description = "This command cannot be used while in combat."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self.bot.mdb["TrigBot"]["dungeon"].delete_one({"_id": interaction.user.id})
        embed = functions.embed("Dungeon - Clear", color=0xa6753a)
        embed.description = "Your dungeon data has been cleared.\nUse `/dungeon enter` to start a new game."
        await interaction.response.send_message(embed=embed)
        

    @group.command(name="inventory") # view your inventory
    async def dungeon_inventory(self, interaction: discord.Interaction) -> None:
        """View your inventory"""
        if not await self.interaction_check(interaction):
            return
        if not self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id}):
            embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
            embed.description = "You do not have a character in the dungeon.\nUse `/dungeon enter` to create one."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if interaction.user.id in self.active: del self.active[interaction.user.id]

        if interaction.user.id in self.busy:
            embed = functions.embed("Error: Busy", color=0xff0000)
            embed.description = "This command cannot be used while in combat."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return


        embed = functions.embed("Dungeon - Inventory", color=0xa6753a)
        embed.description = "Select an item to interact with."
        inventory = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})["inventory"]
        if len(inventory) == 0:
            embed.description += "\n**You have no items in your inventory.**"
        view = InventoryView(self, self.bot.mdb["TrigBot"]["dungeon"], interaction.user.id, interaction)
        self.active[interaction.user.id] = view
        await interaction.response.send_message(embed=embed, view=view)



    @group.command(name="character")
    @app_commands.describe(user="The user to view the character of")
    async def dungeon_character(self, interaction: discord.Interaction, user: Optional[discord.Member]) -> None:
        """View your character, or the character of another user"""
        if not await self.interaction_check(interaction):
            return
        
        if interaction.user.id in self.active: del self.active[interaction.user.id]
        if not user:
            user = interaction.user
        data = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": user.id})
        if not data:
            if user == interaction.user:
                embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
                embed.description = "You do not have a character in the dungeon.\nUse `/dungeon enter` to create one."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            else:
                embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
                embed.description = f"{user.mention} does not have a character in the dungeon."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        embed = functions.embed("Dungeon - Character", color=0xa6753a)
        embed.description = f"Use the menu below to view the character's stats."
        view = UserView(self.bot.mdb["TrigBot"]["dungeon"], interaction.user.id, user.id)
        self.active[interaction.user.id] = view
        await interaction.response.send_message(embed=embed, view=view)

    @group.command(name="interact") # interact with the room
    async def dungeon_interact(self, interaction: discord.Interaction) -> None:
        """Interact with the room you are in"""
        
        if interaction.user.id in self.active: del self.active[interaction.user.id]
        if not await self.interaction_check(interaction):
            return
        if not self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id}):
            embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
            embed.description = "You do not have a character in the dungeon.\nUse `/dungeon enter` to create one."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not await self.interaction_check(interaction):
            return
        if not self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id}):
            embed = functions.embed("Error: Character Doesn't Exist", color=0xff0000)
            embed.description = "You do not have a character in the dungeon.\nUse `/dungeon enter` to create one."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # check if room has already been interacted with
        data = self.bot.mdb["TrigBot"]["dungeon"].find_one({"_id": interaction.user.id})
        if data["room"] in data["interacted"]:
            embed = functions.embed("Error: Already Interacted", color=0xff0000)
            embed.description = "You have already interacted with this room.\nUse `/dungeon room` to see where you are."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # check if the room is a shop
        floor, rooms = generate_floor_map(interaction.user.id, data["floor"])
        room = rooms[data["room"]]
        if room == "shop":
            embed = functions.embed("Dungeon - Room Interaction", color=0xa6753a)
            embed.description = "The shopkeeper motions to the items laid before you.\nUse `/dungeon shop` to view their wares."
            await interaction.response.send_message(embed=embed)
            return
        if room in ["encounter", "cursed", "entrance"]:
            embed = functions.embed("Dungeon - Room Interaction", color=0xa6753a)
            embed.description = "There is nothing to interact with.\nUse `/dungeon room` to see where you are."
            await interaction.response.send_message(embed=embed)
            return
        if room == "key":
            inventory = data["inventory"]
            if len(inventory) >= 10:
                embed = functions.embed("Error: Inventory Full", color=0xff0000)
                embed.description = "You cannot carry any more items.\nUse `/dungeon inventory` to view your inventory and use or drop items."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            key_item = None
            for item in self.items:
                if item["name"] == "Dungeon Key":
                    key_item = item
                    break
            if not key_item:
                raise ValueError
            inventory.append(key_item)
            interacted = data["interacted"]
            interacted.append(data['room'])
            self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": interaction.user.id}, {"$set": {"inventory": inventory}})
            embed = functions.embed("Dungeon - Room Interaction", color=0xa6753a)
            embed.description = "You picked up the dungeon key and added it to your inventory.\nUse this key to unlock the exit door."
            await interaction.response.send_message(embed=embed)
            return
        if room == "exit":
            inventory = data["inventory"]
            if not any(item["name"] == "Dungeon Key" for item in inventory):
                embed = functions.embed("Error: No Key", color=0xff0000)
                embed.description = "You do not have a dungeon key.\nUse `/dungeon room` to see where you are."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            f = data["floor"] + 1
            floor, rooms = generate_floor_map(interaction.user.id, data["floor"] + 1)

            bought = {}
            # get room data
            for room in rooms:
                if rooms[room] == "shop":
                    bought[str(room)] = []

            self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": interaction.user.id}, {"$set": {"room": 0, "floor": data["floor"] + 1, "interacted": [], "inventory": [], "shop_bought": bought}})
            embed = functions.embed("Dungeon - Room Interaction", color=0xa6753a)
            embed.description = f"You used the dungeon key to unlock the exit door.\nYou have advanced to the next floor.\nYou are now on Floor {f}.\nUse `/dungeon room` to see where you are."
            await interaction.response.send_message(embed=embed)
            return
        if room == "loot":
            inventory = data["inventory"]
            if len(inventory) >= 10:
                embed = functions.embed("Error: Inventory Full", color=0xff0000)
                embed.description = "You cannot carry any more items.\nUse `/dungeon inventory` to view your inventory and use or drop items."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            weights = [70, 24, 5, 1]
            # update interacted in db
            interacted = data["interacted"]
            interacted.append(data['room'])
            self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": interaction.user.id}, {"$set": {"interacted": interacted}})
            rarity = random.choices(["common", "rare", "epic", "special"], weights=weights)[0]
            if rarity != "special":
                item = random.choice([item for item in self.items if item["rarity"] == rarity])
            else:
                # find special items *not* in inventory
                item_names = [item["name"] for item in inventory]
                special_items = [item for item in self.items if item["rarity"] == "special" and item["name"] not in item_names]
                item = random.choice(special_items)
                inventory.append(item)
                # update db
                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": interaction.user.id}, {"$set": {"inventory": inventory}})
                if len(special_items) == 1:
                    embed = functions.embed("Dungeon - You Win!", color=0xa6753a)
                    embed.description = f"You looted the `{item['name']}`.\n\nCongratulations, {data['name']}!\nAfter {data['floor']} floor{'s' if data['floor'] != 1 else ''} of labyrinth hell, you successfully found all 5 items required to escape!\nYour ventures have ended in ***victory***.\nIf you would like to enter the dungeon again, use `/dungeon enter`."
                    await interaction.response.send_message(embed=embed)
                    return
                else:
                    embed = functions.embed("Dungeon - Room Interaction", color=0xa6753a)
                    embed.description = f"You looted the `{item['name']}`.\nUse `/dungeon inventory` to view your inventory."
                    await interaction.response.send_message(embed=embed)
                    return
            if item["type"] == "weapon":
                level = max(1, data['level'] + random.randint(-1, 5))
                sword = copy.deepcopy(item)
                sword['name'] = "Level " + str(level) + " " + item['name']
                sword["attack"] = max(1, level * sword["data"]["power"] + random.randint(0, int(sword["data"]["power"])))
                inventory = data["inventory"]
                inventory.append(sword)
                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": interaction.user.id}, {"$set": {"inventory": inventory}})
                embed = functions.embed("Dungeon - Room Interaction", color=0xa6753a)
                embed.description = f"You looted a `{item['name']}`.\nUse `/dungeon inventory` to view your inventory."
                await interaction.response.send_message(embed=embed)
                return
            elif item["type"] == "armor":
                level = max(1, data['level'] + random.randint(-1, 5))
                armor = copy.deepcopy(item)
                armor['name'] = "Level " + str(level) + " " + item['name']
                armor["defense"] = max(1, level * armor["data"]["defense"] // 2 + random.randint(0, armor["data"]["defense"]))
                inventory = data["inventory"]
                inventory.append(armor)
                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": interaction.user.id}, {"$set": {"inventory": inventory}})
                embed = functions.embed("Dungeon - Room Interaction", color=0xa6753a)
                embed.description = f"You looted a `{item['name']}`.\nUse `/dungeon inventory` to view your inventory."
                await interaction.response.send_message(embed=embed)
                return
            else:
                inventory = data["inventory"]
                inventory.append(item)
                self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": interaction.user.id}, {"$set": {"inventory": inventory}})
                embed = functions.embed("Dungeon - Room Interaction", color=0xa6753a)
                embed.description = f"You looted a `{item['name']}`.\nUse `/dungeon inventory` to view your inventory."
                await interaction.response.send_message(embed=embed)
                return
        if room == "shrine":
            # update interacted in db
            interacted = data["interacted"]
            interacted.append(data['room'])
            self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": interaction.user.id}, {"$set": {"interacted": interacted}})
            
            # 50% chance to get a good effect, 50% chance to get a bad effect
            # increases by 10% for every 4 leaf clover in the inventory

            threshold = 50
            for item in data["inventory"]:
                if item["name"] == "Four-Leaf Clover":
                    threshold += 10
            if random.randint(0, 100) <= threshold:
                good_effect = True
            else:
                good_effect = False

            options = ["health", "attack", "evasion", "defense"]
            target = random.choice(options)
            effects = data['effects']
            embed = functions.embed("Dungeon - Shrine Interaction", color=0xa6753a)
            embed.description = f"You kneel before the shrine.\n"
            if good_effect:
                embed.description += "The shrine is **satisfied**.\n"
                if target == "health":
                    embed.description += "You are blessed with **regeneration**."
                    effects.append({"name": "regeneration", "duration": 3, "power": random.choice([10, 20, 30])})
                elif target == "attack":
                    embed.description += "You are blessed with **strength**."
                    effects.append({"name": "powerup", "duration": 3, "power": random.choice([10, 20, 30])})
                elif target == "evasion":
                    embed.description += "You feel **boosted** with the breeze behind you."
                    effects.append({"name": "evasion", "duration": 3, "power": random.choice([10, 20, 30])})
                elif target == "defense":
                    embed.description += "You feel **protected**."
                    effects.append({"name": "hardening", "duration": 3, "power": random.choice([10, 20, 30])})
            else:
                embed.description += "The shrine is **displeased** by your presence.\n"
                if target == "health":
                    embed.description += "You are cursed with **poison**."
                    effects.append({"name": "poison", "duration": 3, "power": random.choice([10, 20, 30])})
                elif target == "attack":
                    embed.description += "You are cursed with **weakness**."
                    effects.append({"name": "powerdown", "duration": 3, "power": random.choice([10, 20, 30])})
                elif target == "evasion":
                    embed.description += "You feel **a weight** dragging you down."
                    effects.append({"name": "evasion", "duration": 3, "power": -random.choice([10, 20, 30])})
                elif target == "defense":
                    embed.description += "You feel **vulnerable**."
                    effects.append({"name": "hardening", "duration": 3, "power": -random.choice([10, 20, 30])})

            self.bot.mdb["TrigBot"]["dungeon"].update_one({"_id": interaction.user.id}, {"$set": {"effects": effects}})
            await interaction.response.send_message(embed=embed)

        
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Dungeon(bot))