import discord
from discord import app_commands
from discord.ext import commands
from discord.interactions import Interaction
import settings

from typing import *

import functions
import random
import os
import json

import asyncio

TIME = 60
import time
import math


class Game(discord.ui.View):
    def __init__(self, cog, inter: discord.Interaction, recipe=None, customer=None) -> None:
        super().__init__(timeout=TIME + 5) # bypass
        self.cog = cog
        self.bot = cog.bot
        self.interaction = inter

        self.diy = True
        if recipe:
            self.recipe = recipe.copy()
            self.name = get_name(self.recipe)

            self.customer = customer
            rc = recipe.copy()
            
            tmp = []
            cup = ""
            for item in rc:
                if item in INGREDIENT_MAP["cup"]:
                    cup = item
                else:
                    tmp.append(item)

            ingredients = []
            tmp2 = []
            for item in tmp:
                if item not in INGREDIENT_MAP["cup"] and item not in INGREDIENT_MAP["preparation"] and item not in INGREDIENT_MAP["toppings"]:
                    ingredients.append(item)
                else:
                    tmp2.append(item)

            prep = ""
            tmp3 = []
            for item in tmp2:
                if item in INGREDIENT_MAP["preparation"]:
                    prep = item
                else:
                    tmp3.append(item)
            
            toppings = []
            for item in tmp3:
                if item in INGREDIENT_MAP["toppings"]:
                    toppings.append(item)

            self.cup = INGREDIENTS[str(cup)]
            self.ingredients = ingredients
            self.prep = INGREDIENTS[str(prep)]
            self.toppings = toppings

            self.score = 0
            self.recipe = recipe.copy()

            self.diy = False

        else:
            if self.cog.bdb.find_one({"_id": inter.user.id}) is None:
                self.cog.bdb.insert_one(generate_blank(inter.user.id))
            self.inventory = self.cog.bdb.find_one({"_id": inter.user.id})["inventory"]

        self.selections = []
        
        start_button = discord.ui.Button(label="Start!", emoji="☕", style=discord.ButtonStyle.green, custom_id="start")
        start_button.callback = self.start
        self.add_item(start_button)
        self.completed_game = False
        self.start = time.time()
        

    async def failed(self):
        self.clear_items()
        embed = functions.embed("Mocha Mayhem!", color=0x005915)
        if not self.diy:
            embed.description = f"**You ran out of time to make a {self.name}!**\nYou earned **0 points.**"
        else:
            embed.description = "**You ran out of time to make a drink!**\nYou earned **0 points.**"
        await self.interaction.edit_original_response(embed=embed, view=None)
        self.cog.ongoing.discard(self.interaction.user.id)

    async def start(self, interaction: discord.Interaction) -> None:
        if not await self.interaction_check(interaction): return
        embed = functions.embed("Mocha Mayhem!", color=0x005915)
        if self.diy:

            # find if there are any available cups
            available = False
            for item in INGREDIENT_MAP["cup"]:
                if self.inventory[str(item)] > 0:
                    available = True
                    break
            if not available:
                embed.description = "You don't have any cups to make a drink with!\n\nRun `/mm shop` to buy some."
                await interaction.response.edit_message(embed=embed, view=None)
                self.cog.ongoing.discard(interaction.user.id)
                return
            # find if there are any teas, lemonades, coffee, bases, dairy, or sweetener
            available = False
            for item in INGREDIENT_MAP["tea"]:
                if self.inventory[str(item)] > 0:
                    available = True
                    break
            for item in INGREDIENT_MAP["lemonade"]:
                if self.inventory[str(item)] > 0:
                    available = True
                    break
            for item in INGREDIENT_MAP["coffee"]:
                if self.inventory[str(item)] > 0:
                    available = True
                    break
            for item in INGREDIENT_MAP["bases"]:
                if self.inventory[str(item)] > 0:
                    available = True
                    break
            for item in INGREDIENT_MAP["dairy"]:
                if self.inventory[str(item)] > 0:
                    available = True
                    break
            for item in INGREDIENT_MAP["sweetener"]:
                if self.inventory[str(item)] > 0:
                    available = True
                    break
            if not available:
                embed.description = "You don't have any ingredients to make a drink with!\n\nRun `/mm shop` to buy some."
                await interaction.response.edit_message(embed=embed, view=None)
                self.cog.ongoing.discard(interaction.user.id)
                return
            available = False
            for item in INGREDIENT_MAP["prep"]:
                if self.inventory[str(item)] > 0:
                    available = True
                    break
            if not available:
                embed.description = "You don't have any preparation methods to make a drink with!\n\nRun `/mm shop` to buy some."
                await interaction.response.edit_message(embed=embed, view=None)
                self.cog.ongoing.discard(interaction.user.id)
                return
            
            
            


            embed.description = f"You have {TIME} seconds to make a **DIY drink**!\n\n**Start by selecting a cup.**"
        else:
            embed.description = f"{self.customer['_id']} wants a drink!\nYou have {TIME} seconds to make a **{self.name}**!\n\n**Start by selecting a cup.**"
        self.cup_select = discord.ui.Select(placeholder="Select a cup...", custom_id="cup_select")
        for item in INGREDIENT_MAP["cup"]:
            if self.diy and self.inventory[str(item)] == 0: continue
            self.cup_select.add_option(label=INGREDIENTS[str(item)]["name"], emoji=INGREDIENTS[str(item)]["emoji"], value=str(item))
        self.cup_select.callback = self.cup_selected
        self.clear_items()
        self.add_item(self.cup_select)
        await interaction.response.edit_message(embed=embed, view=self)

    async def cup_selected(self, interaction: discord.Interaction) -> None:
        if not await self.interaction_check(interaction): return
        value = int(interaction.data['values'][0])
        if self.diy:
            self.inventory[str(value)] -= 1
            self.cog.bdb.update_one({"_id": interaction.user.id}, {"$set": {"inventory": self.inventory}})
        self.selections.append(value)
        embed = functions.embed("Mocha Mayhem!", color=0x005915)
        if not self.diy:
            embed.description = f"{self.customer['_id']} wants a drink!\nYou have {TIME} seconds to make a **{self.name}**!\n\n**Next, select ingredients to make the drink, then press Continue.**"
        else:
            embed.description = f"You have {TIME} seconds to make a **DIY drink**!\n\n**Next, select ingredients to make the drink, then press Continue.**"
        embed.add_field(name="Cup", value=f"{INGREDIENTS[str(value)]['emoji']} {INGREDIENTS[str(value)]['name']}", inline=False)
        self.clear_items()

        self.ingredient_select = discord.ui.Select(placeholder="Select an ingredient...", custom_id="ingredient_select")
        for ingredient in INGREDIENTS:
            if int(ingredient) in INGREDIENT_MAP["cup"]: continue
            if int(ingredient) in INGREDIENT_MAP["preparation"]: continue
            if int(ingredient) in INGREDIENT_MAP["toppings"]: continue
            if self.diy and self.inventory[str(ingredient)] == 0: continue
            self.ingredient_select.add_option(label=INGREDIENTS[str(ingredient)]["name"], emoji=INGREDIENTS[str(ingredient)]["emoji"], value=str(ingredient))
        
        self.ingredient_select.callback = self.ingredient_selected
        self.add_item(self.ingredient_select)
        self.finished_ingredients_button = discord.ui.Button(label="Continue", emoji="✅", style=discord.ButtonStyle.green, custom_id="finished_ingredients",row=1)
        self.finished_ingredients_button.callback = self.finished_ingredients
        self.add_item(self.finished_ingredients_button)
        await interaction.response.edit_message(embed=embed, view=self)

    async def ingredient_selected(self, interaction: discord.Interaction) -> None:
        if not await self.interaction_check(interaction): return
        value = int(interaction.data['values'][0])
        if self.diy:
            self.inventory[str(value)] -= 1
            self.cog.bdb.update_one({"_id": interaction.user.id}, {"$set": {"inventory": self.inventory}})
        self.selections.append(value)
        self.ingredient_select.placeholder = "Select another ingredient..."
        embed = functions.embed("Mocha Mayhem!", color=0x005915)
        
        if self.diy:
            embed.description = f"You have {TIME} seconds to make a **DIY drink**!\n\n**Next, select ingredients to make the drink, then press Continue.**"            
        else:
            embed.description = f"{self.customer['_id']} wants a drink!\nYou have {TIME} seconds to make a **{self.name}**!\n\n**Next, select ingredients to make the drink, then press Continue.**"
        
        
        rc = self.selections.copy()
        
        tmp = []
        cup = ""
        for item in rc:
            if item in INGREDIENT_MAP["cup"]:
                cup = item
            else:
                tmp.append(item)

        ingredients = []
        tmp2 = []
        for item in tmp:
            if item not in INGREDIENT_MAP["cup"] and item not in INGREDIENT_MAP["preparation"] and item not in INGREDIENT_MAP["toppings"]:
                ingredients.append(item)
            else:
                tmp2.append(item)
        
        
        cup = INGREDIENTS[str(cup)]
        embed.add_field(name="Cup", value=f"{cup['emoji']} {cup['name']}", inline=False)
        
        text = ""
        temp = sorted(list(set(ingredients)))
        for i in temp:
            count = ingredients.count(i)
            text += f"{INGREDIENTS[str(i)]['emoji']} {INGREDIENTS[str(i)]['name']}{(' x' + str(count)) if count > 1 else ''}\n"
        text = text.strip()
        embed.add_field(name="Ingredients", value=text, inline=False)

        if self.diy:
            self.ingredient_select = discord.ui.Select(placeholder="Select an ingredient...", custom_id="ingredient_select")
            for ingredient in INGREDIENTS:
                if int(ingredient) in INGREDIENT_MAP["cup"]: continue
                if int(ingredient) in INGREDIENT_MAP["preparation"]: continue
                if int(ingredient) in INGREDIENT_MAP["toppings"]: continue
                if self.diy and self.inventory[str(ingredient)] == 0: continue
                self.ingredient_select.add_option(label=INGREDIENTS[str(ingredient)]["name"], emoji=INGREDIENTS[str(ingredient)]["emoji"], value=str(ingredient))
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def finished_ingredients(self, interaction: discord.Interaction) -> None:
        if not await self.interaction_check(interaction): return
        self.selections = sorted(self.selections)
        sc = self.selections.copy()
        self.clear_items()
        embed = functions.embed("Mocha Mayhem!", color=0x005915)
        if not self.diy:
            embed.description = f"{self.customer['_id']} wants a drink!\nYou have {TIME} seconds to make a **{self.name}**!\n\n**Next, select a preparation method.**"
        else:
            embed.description = f"You have {TIME} seconds to make a **DIY drink**!\n\n**Next, select a preparation method.**"

        rc = self.selections.copy()
        
        tmp = []
        cup = ""
        for item in rc:
            if item in INGREDIENT_MAP["cup"]:
                cup = item
            else:
                tmp.append(item)

        ingredients = []
        tmp2 = []
        for item in tmp:
            if item not in INGREDIENT_MAP["cup"] and item not in INGREDIENT_MAP["preparation"] and item not in INGREDIENT_MAP["toppings"]:
                ingredients.append(item)
            else:
                tmp2.append(item)
        
        
        cup = INGREDIENTS[str(cup)]
        embed.add_field(name="Cup", value=f"{cup['emoji']} {cup['name']}", inline=False)
        
        text = ""
        temp = sorted(list(set(ingredients)))
        for i in temp:
            count = ingredients.count(i)
            text += f"{INGREDIENTS[str(i)]['emoji']} {INGREDIENTS[str(i)]['name']}{(' x' + str(count)) if count > 1 else ''}\n"
        text = text.strip()
        embed.add_field(name="Ingredients", value=text, inline=False)
        
        self.prep_select = discord.ui.Select(placeholder="Select a preparation method...", custom_id="prep_select")
        for item in INGREDIENT_MAP["preparation"]:
            if self.diy and self.inventory[str(item)] == 0: continue
            self.prep_select.add_option(label=INGREDIENTS[str(item)]["name"], emoji=INGREDIENTS[str(item)]["emoji"], value=str(item))
        self.prep_select.callback = self.prep_selected
        self.add_item(self.prep_select)
        await interaction.response.edit_message(embed=embed, view=self)

    async def prep_selected(self, interaction: discord.Interaction) -> None:
        if not await self.interaction_check(interaction): return
        value = int(interaction.data['values'][0])
        self.selections.append(value)
        self.clear_items()
        sc = self.selections.copy()
        embed = functions.embed("Mocha Mayhem!", color=0x005915)

        if not self.diy:
            embed.description = f"{self.customer['_id']} wants a drink!\nYou have {TIME} seconds to make a **{self.name}**!\n\n**Finally, select a topping if you need it.\nOtherwise, press Finish.**"
        else:
            embed.description = f"You have {TIME} seconds to make a **DIY drink**!\n\n**Finally, select a topping if you need it.\nOtherwise, press Finish.**"

        rc = self.selections.copy()
        
        tmp = []
        cup = ""
        for item in rc:
            if item in INGREDIENT_MAP["cup"]:
                cup = item
            else:
                tmp.append(item)

        ingredients = []
        tmp2 = []
        for item in tmp:
            if item not in INGREDIENT_MAP["cup"] and item not in INGREDIENT_MAP["preparation"] and item not in INGREDIENT_MAP["toppings"]:
                ingredients.append(item)
            else:
                tmp2.append(item)

        prep = ""
        tmp3 = []
        for item in tmp2:
            if item in INGREDIENT_MAP["preparation"]:
                prep = item
            else:
                tmp3.append(item)
        
        
        cup = INGREDIENTS[str(cup)]
        embed.add_field(name="Cup", value=f"{cup['emoji']} {cup['name']}", inline=False)
        
        text = ""
        temp = sorted(list(set(ingredients)))
        for i in temp:
            count = ingredients.count(i)
            text += f"{INGREDIENTS[str(i)]['emoji']} {INGREDIENTS[str(i)]['name']}{(' x' + str(count)) if count > 1 else ''}\n"
        text = text.strip()
        embed.add_field(name="Ingredients", value=text, inline=False)


        
        prep = INGREDIENTS[str(prep)]
        embed.add_field(name="Preparation", value=f"{prep['emoji']} {prep['name']}", inline=False)
        
        goahead = True
        if self.diy:
            # check if there are any toppings
            available = False
            for item in INGREDIENT_MAP["toppings"]:
                if self.inventory[str(item)] > 0:
                    available = True
                    break
            if not available:
                goahead = False

        if goahead:
            self.topping_select = discord.ui.Select(placeholder="Select a topping...", custom_id="topping_select")
            for item in INGREDIENT_MAP["toppings"]:
                if self.diy and self.inventory[str(item)] == 0: continue
                self.topping_select.add_option(label=INGREDIENTS[str(item)]["name"], emoji=INGREDIENTS[str(item)]["emoji"], value=str(item))
            self.topping_select.callback = self.topping_selected
            self.add_item(self.topping_select)
        else:
            embed.description = f"You have {TIME} seconds to make a **DIY drink**!\n\n**You do not have any toppings for this drink. Press Finish to finish.**"

        self.finished_button = discord.ui.Button(label="Finish", emoji="✅", style=discord.ButtonStyle.green, custom_id="finished",row=1)
        self.finished_button.callback = self.finished
        self.add_item(self.finished_button)
        await interaction.response.edit_message(embed=embed, view=self)

    async def topping_selected(self, interaction: discord.Interaction) -> None:
        if not await self.interaction_check(interaction): return
        value = int(interaction.data['values'][0])
        if self.diy:
            self.inventory[str(value)] -= 1
            self.cog.bdb.update_one({"_id": interaction.user.id}, {"$set": {"inventory": self.inventory}})
        self.selections.append(value)
        await self.finished(interaction)
        
    async def finished(self, interaction: discord.Interaction) -> None:
        self.clear_items()
        self.selections = sorted(self.selections)
        correct = []
        missing = []
        extra = []
        points = 0
        
        self.completed_game = True
        dt = int(round(time.time() - self.start))
        
        if not self.diy: points += int((TIME - dt) / 10)

        if not self.diy:
            for item in self.selections:
                if item in self.recipe:
                    correct.append(item)
                    points += 1
                    self.recipe.remove(item)
                else:
                    extra.append(item)
                    points -= 1
            for item in self.recipe:
                missing.append(item)
                points -= 1

            pt = int((TIME - dt) / 10)

            points = max(0, points)
            embed = functions.embed("Mocha Mayhem!", color=0x005915)
            text = ", ".join([INGREDIENTS[str(x)]["name"] for x in correct])
            embed.add_field(name="Correct Items", value=text, inline=False)
            if len(missing) == 0 and len(extra) == 0:
                embed.description = f"You perfectly made the **{self.name}**!\n\nYou earned **{points} point{'s' if points != 1 else ''}**!"
            else:
                if len(missing) > 0:
                    text = ", ".join([INGREDIENTS[str(x)]["name"] + ((" x" + str(missing.count(x)) if (missing.count(x)) > 1 else "")) for x in sorted(list(set(missing)))])
                    embed.add_field(name="Missing Items", value=text, inline=False)
                if len(extra) > 0:
                    text = ", ".join([INGREDIENTS[str(x)]["name"] + ((" x" + str(extra.count(x)) if (extra.count(x)) > 1 else "")) for x in sorted(list(set(extra)))])
                    embed.add_field(name="Extra Items", value=text, inline=False)
                embed.description = f"You made a **{self.name}**, but it wasn't perfect.\n\nYou earned **{points} point{'s' if points != 1 else ''}.**"


            h = self.customer["happiness"]
            h += len(correct) + pt - (len(correct) + (TIME/10))/2
            h = max(min(h, 100), 1)
            self.cog.bdb.update_one({"_id": self.customer["_id"]}, {"$set": {"happiness": h}})
            self.customer["happiness"] = h
            tip = 0
            if random.randint(1, 100) <= self.customer["happiness"]:
                tip = round(self.cog.get_tip(self.customer["m"], self.customer["n"], self.customer["p"], (time.time() % 86400)/3600), 2)

            if tip > 0:
                embed.description = embed.description + "\n\nYou also earned a **$" + str(tip) + " tip**!"

            

            await interaction.response.edit_message(embed=embed, view=None)
            if self.cog.bdb.find_one({"_id": interaction.user.id}) is None:
                self.cog.bdb.insert_one(generate_blank(interaction.user.id))
            self.cog.bdb.update_one({"_id": interaction.user.id}, {"$inc": {"points": points, "cash": tip}})
        else:
            embed = functions.embed("Mocha Mayhem!", color=0x005915)
            name = get_name(self.selections)
            if name == "Unknown Drink":
                embed.description = "You made an **Unknown Drink**!\n\nYou earned **0 points.**"
                embed.add_field(name="Items", value=", ".join([INGREDIENTS[str(x)]["name"] for x in self.selections]), inline=False)
                
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                points += len(self.selections)
                points *= 2
                embed.description = f"You made a **{name}**!\n\nYou earned **{points} point{'s' if points != 1 else ''}.**"
                embed.add_field(name="Items", value=", ".join([INGREDIENTS[str(x)]["name"] for x in self.selections]), inline=False)
                await interaction.response.edit_message(embed=embed, view=None)
                if self.cog.bdb.find_one({"_id": interaction.user.id}) is None:
                    self.cog.bdb.insert_one(generate_blank(interaction.user.id))
                self.cog.bdb.update_one({"_id": interaction.user.id}, {"$inc": {"points": points}})
            
        self.cog.ongoing.discard(interaction.user.id)



    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You cannot use this button, as you are not the user who started this game."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def generate_blank(uid):
    data = {}
    data["_id"] = uid
    data["points"] = 0
    data["cash"] = 0
    data["inventory"] = {
        str(k): 0 for k in INGREDIENTS
    }
    data["inventory"]["24"] = 1
    return data

with open(os.path.join(base, "assets", "barista", "recipes.json"), encoding='utf-8') as f:
    RECIPES = json.load(f)

with open(os.path.join(base, "assets", "barista", "ingredients.json"), encoding='utf-8') as f:
    INGREDIENTS = json.load(f)

with open(os.path.join(base, "assets", "barista", "recipe_map.json"), encoding='utf-8') as f:
    RECIPE_MAP = json.load(f)

with open(os.path.join(base, "assets", "barista", "ingredient_map.json"), encoding='utf-8') as f:
    INGREDIENT_MAP = json.load(f)

class InventoryView(discord.ui.View):
    def __init__(self, cog, inter: discord.Interaction) -> None:
        super().__init__(timeout=60)
        self.interaction = inter
        self.cog = cog
        self.bot = cog.bot

        self.categories = {}
        for item in INGREDIENT_MAP:
            self.categories[item] = item.title() + ("s" if (item[-1] != "s" and item not in {"dairy", "preparation", "ice"}) else "")
        
        self.category_select = discord.ui.Select(placeholder="Select a category...", custom_id="category_select")
        for item in self.categories:
            self.category_select.add_option(label=self.categories[item], value=item)

        self.category_select.callback = self.category_selected
        self.add_item(self.category_select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You cannot use this button, as you are not the user who opened this menu."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    async def category_selected(self, interaction: discord.Interaction) -> None:
        if not(await self.interaction_check(interaction)): return
        value = interaction.data['values'][0]
        self.clear_items()
        self.category_select.placeholder = "Selected: " + self.categories[str(value)]
        self.add_item(self.category_select)

        # if user doesn't exist in db, add
        if self.cog.bdb.find_one({"_id": interaction.user.id}) is None:
            self.cog.bdb.insert_one(generate_blank(interaction.user.id))
        
        data = self.cog.bdb.find_one({"_id": interaction.user.id})
        inventory = data["inventory"]
        text = "**Inventory: " + self.categories[value] + "**\n\n"
        for item in INGREDIENT_MAP[value]:
            text += f"{INGREDIENTS[str(item)]['emoji']} **{INGREDIENTS[str(item)]['name']}**: {inventory[str(item)]}\n"
        
        embed = functions.embed("Mocha Mayhem Inventory", color=0x005915)
        embed.description = text
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        self.clear_items()
        embed = functions.embed("Mocha Mayhem Inventory", color=0x005915)
        embed.description = "This menu has timed out.\nRun `/mm inventory` to view your inventory."
        await self.interaction.edit_original_response(embed=embed, view=None)

class ShopView(discord.ui.View):
    def __init__(self, cog, inter: discord.Interaction) -> None:
        super().__init__(timeout=60)
        self.interaction = inter
        self.cog = cog
        self.bot = cog.bot

        self.categories = {}
        for item in INGREDIENT_MAP:
            self.categories[item] = item.title() + ("s" if (item[-1] != "s" and item not in {"dairy", "preparation", "ice"}) else "")
        
        self.category_select = discord.ui.Select(placeholder="Select a category...", custom_id="category_select")
        for item in self.categories:
            self.category_select.add_option(label=self.categories[item], value=item)

        self.category = ""

        self.amounts = {
            "cup": (10, 25),
            "ice": (5, 5),
            "lemonade": (5, 5),
            "tea": (10, 15),
            "coffee": (10, 10),
            "bases": (10, 15),
            "dairy": (5, 15),
            "sweetener": (10, 5),
            "preparation": (1, 20),
            "toppings": (5, 15)
        }

        self.category_select.callback = self.category_selected
        self.add_item(self.category_select)

    async def on_timeout(self):
        self.clear_items()
        embed = functions.embed("Mocha Mayhem Inventory", color=0x005915)
        embed.description = "This menu has timed out.\nRun `/mm shop` to open the shop menu."
        await self.interaction.edit_original_response(embed=embed, view=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            embed = functions.embed("Error: Invalid User", color=0xff0000)
            embed.description = "You cannot use this button, as you are not the user who opened this menu."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    async def category_selected(self, interaction: discord.Interaction) -> None:
        if not(await self.interaction_check(interaction)): return
        value = interaction.data['values'][0]
        self.category = value
        self.clear_items()
        self.category_select.placeholder = "Selected: " + self.categories[str(value)]
        self.add_item(self.category_select)

        self.item_select = discord.ui.Select(placeholder="Select an item...", custom_id="item_select", row=1)
        for item in INGREDIENT_MAP[value]:
            self.item_select.add_option(label=INGREDIENTS[str(item)]["name"], emoji=INGREDIENTS[str(item)]["emoji"], value=str(item))

        self.item_select.callback = self.item_selected
        self.add_item(self.item_select)

        embed = functions.embed("Mocha Mayhem Shop", color=0x005915)
        embed.description = "**Welcome to the Mocha Mayhem Shop!**\n\nYou have selected the **" + self.categories[str(value)] + "** category.\n\nSelect an item to purchase it."
        await interaction.response.edit_message(embed=embed, view=self)


    async def item_selected(self, interaction: discord.Interaction) -> None:
        if not(await self.interaction_check(interaction)): return
        value = int(interaction.data['values'][0])
        self.clear_items()
        self.category_select.placeholder = "Category Selected: " + self.categories[self.category]
        
        self.add_item(self.category_select)

        self.item = value

        self.item_select.placeholder = "Item Selected: " + INGREDIENTS[str(value)]["name"]
        self.add_item(self.item_select)

        
        amount, price = self.amounts[self.category]

        buy_button = discord.ui.Button(label="Buy", emoji="💰", style=discord.ButtonStyle.green, custom_id="buy", row=2)
        buy_button.callback = self.buy

        # if its a preparation method the player already has, disable the button
        if self.cog.bdb.find_one({"_id": interaction.user.id}) is None:
            self.cog.bdb.insert_one(generate_blank(interaction.user.id))

        embed = functions.embed("Mocha Mayhem Shop", color=0x005915)
        embed.description = f"**Welcome to the Mocha Mayhem Shop!**\n\n{INGREDIENTS[str(value)]['emoji']} **{INGREDIENTS[str(value)]['name']}**\n\n**Price:** ${price}\n**Amount:** {amount}\n\n**Press Buy to purchase this item.**"

        data = self.cog.bdb.find_one({"_id": interaction.user.id})
        inventory = data["inventory"]
        if self.category == "preparation":
            if value in inventory:
                buy_button.disabled = True
                buy_button.label = "Already Owned"
                embed.description = f"**Welcome to the Mocha Mayhem Shop!**\n\n{INGREDIENTS[str(value)]['emoji']} **{INGREDIENTS[str(value)]['name']}**\n\n**You already own this preparation method.**"
            else:
                embed.description = f"**Welcome to the Mocha Mayhem Shop!**\n\n{INGREDIENTS[str(value)]['emoji']} **{INGREDIENTS[str(value)]['name']}**\n\n**Price:** ${price}\n**Amount:** {amount}\n\n**Press Buy to purchase this preparation method.**"
        


        if data['cash'] < price:
            buy_button.disabled = True
            buy_button.style = discord.ButtonStyle.red
            buy_button.label = "Not Enough Cash"

        self.add_item(buy_button)
        await interaction.response.edit_message(embed=embed, view=self)

    async def buy(self, interaction: discord.Interaction) -> None:
        if not(await self.interaction_check(interaction)): return

        value = self.item
        
        amount, price = self.amounts[self.category]
        data = self.cog.bdb.find_one({"_id": interaction.user.id})
        inventory = data["inventory"]

        # assume the player has enough cash
        data['cash'] -= price
        inventory[str(value)] += amount

        self.cog.bdb.update_one({"_id": interaction.user.id}, {"$set": {"inventory": inventory, "cash": data['cash']}})

        embed = functions.embed("Mocha Mayhem Shop", color=0x005915)
        embed.description = f"**Welcome to the Mocha Mayhem Shop!**\n\nYou successfully purchased {INGREDIENTS[str(value)]['emoji']} **{INGREDIENTS[str(value)]['name']}** x{amount} for ${price}.\n\nYou now have ${data['cash']}."
        await interaction.response.edit_message(embed=embed, view=None)



def get_name(recipe):
    if 6 in recipe: # it's a type of lemonade
        s = "Lemonade"
        if 7 in recipe:
            s = "Strawberry " + s
        if 22 in recipe and 5 in recipe:
            s = "Blended " + s
        return s
    if any(x in recipe for x in INGREDIENT_MAP["tea"]): # it's a type of tea
        intersection = [x for x in recipe if x in INGREDIENT_MAP["tea"]][0]
        s = {k: INGREDIENTS[str(k)]["name"] for k in INGREDIENT_MAP["tea"]}[intersection]
        if 5 in recipe:
            s = "Iced " + s
        if any(x in recipe for x in INGREDIENT_MAP["dairy"]):
            s = s + " Latte"
        return s
    if 2 in recipe: # it's an espresso
        return "Espresso"
    if 13 in recipe and 14 in recipe: # it's a barista special
        s = "Barista Special"
        if 12 in recipe:
            s = "Decaf " + s
            if recipe.count(12) == 2:
                s = "Double Shot " + s
        else:
            if recipe.count(11) == 2:
                s = "Double Shot " + s
        if 25 in recipe:
            s = "Deluxe " + s
        
        if 1 in recipe:
            if 22 in recipe:
                s = s + " Frappe"
            else:
                s = "Iced " + s
        return s
    if 13 in recipe and any(x in recipe for x in INGREDIENT_MAP["coffee"]): # it's a mocha
        s = "Mocha"
        if 12 in recipe:
            s = "Decaf " + s
            if recipe.count(12) == 2:
                s = "Double Shot " + s
        else:
            if recipe.count(11) == 2:
                s = "Double Shot " + s
        if 25 in recipe:
            s = "Deluxe " + s
        if 1 in recipe:
            if 22 in recipe:
                s = s + " Frappe"
            else:
                s = "Iced " + s
        return s
    if 14 in recipe and any(x in recipe for x in INGREDIENT_MAP["coffee"]):
        s = "Vanilla Coffee"
        if 12 in recipe:
            s = "Decaf " + s
            if recipe.count(12) == 2:
                s = "Double Shot " + s
        else:
            if recipe.count(11) == 2:
                s = "Double Shot " + s
        if 25 in recipe:
            s = "Deluxe " + s
        if 1 in recipe:
            if 22 in recipe:
                s = s + " Frappe"
            else:
                s = "Iced " + s
        return s
    if any(x in recipe for x in INGREDIENT_MAP["coffee"]): # it's a latte or caramel macchiato
        if 26 in recipe:
            s = "Caramel Macchiato"
            if 12 in recipe:
                s = "Decaf " + s
                if recipe.count(12) == 2:
                    s = "Double Shot " + s
            else:
                if recipe.count(11) == 2:
                    s = "Double Shot " + s
            if 25 in recipe:
                s = "Deluxe " + s
        else:
            s = "Latte"
            if 12 in recipe:
                s = "Decaf " + s
                if recipe.count(12) == 2:
                    s = "Double Shot " + s
            else:
                if recipe.count(11) == 2:
                    s = "Double Shot " + s
            if 25 in recipe:
                s = "Deluxe " + s
        if 1 in recipe:
            if 22 in recipe:
                s = s + " Frappe"
            else:
                s = "Iced " + s
        return s
    if 23 in recipe and any(x in recipe for x in INGREDIENT_MAP["dairy"]):
        return "Steamed Milk"
    if 12 not in recipe and 11 not in recipe and 13 in recipe and any(x in recipe for x in INGREDIENT_MAP["dairy"]):
        return "Hot Chocolate"
    return "Unknown Drink"



def generate_recipe():
    
    r = random.randint(1, len(RECIPES.keys()))
    recipe = RECIPES[str(r)].copy()

    if 15 in recipe and r != 16: # if there is milk by default
        recipe.remove(15)
        recipe.append(random.choice(INGREDIENT_MAP["dairy"])) # replace with random dairy

    if r in {11, 14}: # if the recipe is a barista special
        recipe.remove(27) # remove default chocolate drizzle
        recipe.append(random.randint(26, 27)) # replace with random chocolate or caramel

    if r in RECIPE_MAP["tea"] or r in RECIPE_MAP["coffee"]: # if the recipe is a tea or non-frappe coffee
        x = random.randint(0, len(INGREDIENT_MAP["sweetener"])) # add random sweetener
        if x != 0:
            recipe.append(INGREDIENT_MAP["sweetener"][x-1])
        if random.randint(0, 1): # if iced:
            if 3 in recipe: recipe.remove(3) # remove tea cup if it exists
            if 4 in recipe: recipe.remove(4) # remove coffee cup if it exists
            recipe.append(1) # add iced cup
            recipe.append(5) # add ice

    if r in RECIPE_MAP["tea"]:
        x = random.randint(0, 4) # determine if there's dairy
        if x != 0:
            recipe.append(INGREDIENT_MAP["dairy"][x-1])

    if r in RECIPE_MAP["lemonade"]: # if the recipe is a lemonade
        if random.randint(0, 1): # if blended
            recipe.remove(21) # remove stir
            recipe.append(22) # add blend
        x = random.randint(0, len(INGREDIENT_MAP["sweetener"])) # add random sweetener
        if x != 0:
            recipe.append(INGREDIENT_MAP["sweetener"][x-1])
        
    if r in RECIPE_MAP["coffee"] or r in RECIPE_MAP["frappe"]:
        if random.randint(0, 1): # if it's a deluxe:
            if 26 in recipe: recipe.remove(26)
            if 27 in recipe: recipe.remove(27)
            recipe.append(25)
        if random.randint(0, 1): # if it's double shot:
            recipe.append(11)
        if random.randint(0, 1): # if it's decaf:
            while 11 in recipe:
                recipe.remove(11)
                recipe.append(12)

    return sorted(recipe)

class Barista(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        self.bdb = self.bot.mdb["TrigBot"]["barista"]

        self.customers = self.bdb.find({"role": "customer"})
        self.ongoing = set()

    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]


    group = app_commands.Group(name="mm", description="...")

    def get_tip(self, m, n, p, t):
        # m: maximum tip
        # n: minimum tip
        # p: time that the tip peaks
        # t: current time
        return (m - n)/2 * math.sin(2 * math.pi / 24 * (t + 6 - p)) + (m + n)/2

    @group.command(name="serve")
    async def serve(self, inter: discord.Interaction) -> None: # temporary command to trigger barista game
        """Serve a customer some coffee!"""
        recipe = generate_recipe()
        name = get_name(recipe)

        if inter.id in self.ongoing:
            embed = functions.embed("Error: Game Already Ongoing", color=0xff0000)
            embed.description = "You already have a game ongoing!"
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        self.ongoing.add(inter.id)

        
        self.customers = self.bdb.find({"role": "customer"})
        customer = random.choice(list(self.customers))

        embed = functions.embed("Mocha Mayhem!", color=0x005915)
        embed.description = f"{customer['_id']} wants a drink!\nYou have {TIME} seconds to make a **{name}**!\nReview the recipe below, then press Start to begin."
        
        rc = recipe.copy()
        
        tmp = []
        cup = ""
        for item in rc:
            if item in INGREDIENT_MAP["cup"]:
                cup = item
            else:
                tmp.append(item)

        ingredients = []
        tmp2 = []
        for item in tmp:
            if item not in INGREDIENT_MAP["cup"] and item not in INGREDIENT_MAP["preparation"] and item not in INGREDIENT_MAP["toppings"]:
                ingredients.append(item)
            else:
                tmp2.append(item)

        prep = ""
        tmp3 = []
        for item in tmp2:
            if item in INGREDIENT_MAP["preparation"]:
                prep = item
            else:
                tmp3.append(item)
        
        toppings = []
        for item in tmp3:
            if item in INGREDIENT_MAP["toppings"]:
                toppings.append(item)

        cup = INGREDIENTS[str(cup)]
        embed.add_field(name="Cup", value=f"{cup['emoji']} {cup['name']}", inline=False)
        
        text = ""
        temp = sorted(list(set(ingredients)))
        for i in temp:
            count = ingredients.count(i)
            text += f"{INGREDIENTS[str(i)]['emoji']} {INGREDIENTS[str(i)]['name']}{(' x' + str(count)) if count > 1 else ''}\n"
        text = text.strip()
        embed.add_field(name="Ingredients", value=text, inline=False)

        prep = INGREDIENTS[str(prep)]
        embed.add_field(name="Preparation", value=f"{prep['emoji']} {prep['name']}", inline=False)

        if len(toppings) > 0:
            text = ""
            while len(toppings) > 0:
                topping = INGREDIENTS[str(toppings.pop(0))]
                text += f"{topping['emoji']} {topping['name']}\n"
            text = text.strip()
            embed.add_field(name="Toppings", value=text, inline=False)

        game = Game(self, inter, recipe=recipe, customer=customer)


        await inter.response.send_message(embed=embed, view=game)

        
        await asyncio.sleep(TIME)
        if not game.completed_game:
            await game.failed()

    @group.command(name="points")
    async def points(self, inter: discord.Interaction, user: discord.Member = None) -> None:
        """View your Mocha Mayhem points"""
        if user is None:
            user = inter.user
        if self.bdb.find_one({"_id": user.id}) is None:
            self.bdb.insert_one(generate_blank(user.id))
            points = 0
        else:
            points = self.bdb.find_one({"_id": user.id})["points"]
        embed = functions.embed("Mocha Mayhem Points", color=0x005915)
        text = f"{user.mention if user.id != inter.user.id else 'You'} ha{'s' if user.id != user.id else 've'} **{points} point{'s' if points != 1 else ''}**."
        ranks = {
            "Master": 200,
            "Professional": 100,
            "Connoisseur": 50,
            "Casual": 30,
            "Trainee": 15,
            "Newbie": 0 
        }

        rank = ""
        next_rank = ""
        for rank in ranks:
            if points >= ranks[rank]:
                break
            else:
                next_rank = rank


        text = text + f"\n**Rank:** {rank} Barista"
        if next_rank: 
            text = text + f"\n**Points to next rank{(' (' + next_rank + ' Barista)') if next_rank else ''}:** {ranks[next_rank] - points}"

        embed.description = text
        await inter.response.send_message(embed=embed)

    @group.command(name="leaderboard")
    async def leaderboard(self, inter: discord.Interaction) -> None:
        """View the Mocha Mayhem leaderboard"""
        embed = functions.embed("Mocha Mayhem Leaderboard", color=0x005915)
        embed.description = "Loading..."
        await inter.response.send_message(embed=embed)

        leaderboard = []
        for member in inter.guild.members:
            if self.bdb.find_one({"_id": member.id}) is None:
                points = 0
            else:
                points = self.bdb.find_one({"_id": member.id})["points"]
            leaderboard.append((member, points))
        leaderboard = sorted(leaderboard, key=lambda x: x[1], reverse=True)
        text = ""
        for i, (member, points) in enumerate(leaderboard):
            text += f"{i+1}. {member.mention} - **{points} point{'s' if points != 1 else ''}**\n"
            if i == 9: break

        text = text + "\n**Your Rank:** " + str([x[0] for x in leaderboard].index(inter.user) + 1) + "\n**Your Points:** " + str(self.bdb.find_one({"_id": inter.user.id})["points"])
        embed.description = text
        await inter.edit_original_response(embed=embed)

    @group.command(name="inventory")
    async def inventory(self, inter: discord.Interaction) -> None:
        """View your Mocha Mayhem inventory"""
        embed = functions.embed("Mocha Mayhem Inventory", color=0x005915)
        embed.description = "Select an item category below."
        await inter.response.send_message(embed=embed, view=InventoryView(self, inter))

    @group.command(name="balance")
    async def balance(self, inter: discord.Interaction, user: discord.Member = None) -> None:
        """View your Mocha Mayhem balance or another user's balance"""
        if user is None:
            user = inter.user
        if self.bdb.find_one({"_id": user.id}) is None:
            self.bdb.insert_one(generate_blank(user.id))
            cash = 0
        else:
            cash = self.bdb.find_one({"_id": user.id})["cash"]
        embed = functions.embed("Mocha Mayhem Balance", color=0x005915)
        text = f"{user.mention if user.id != inter.user.id else 'You'} currently ha{'s' if user.id != user.id else 've'} **${cash}**."
        embed.description = text
        await inter.response.send_message(embed=embed)

    @group.command(name="shop")
    async def shop(self, inter: discord.Interaction) -> None:
        """View the Mocha Mayhem shop"""
        embed = functions.embed("Mocha Mayhem Shop", color=0x005915)
        embed.description = "Select an item category below."
        await inter.response.send_message(embed=embed, view=ShopView(self, inter))

    @group.command(name="practice")
    async def practice(self, inter: discord.Interaction) -> None:
        """Build a drink on your own using purchased ingredients."""
        if inter.id in self.ongoing:
            embed = functions.embed("Error: Game Already Ongoing", color=0xff0000)
            embed.description = "You already have a game ongoing!"
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        self.ongoing.add(inter.id)

        embed = functions.embed("Mocha Mayhem!", color=0x005915)
        embed.description = f"You have {TIME} seconds to make a **DIY drink**!\n\nPress Start to begin."

        game = Game(self, inter, recipe=[], customer=None)
        await inter.response.send_message(embed=embed, view=game)
        await asyncio.sleep(TIME)
        if not game.completed_game:
            await game.failed()

    @group.command(name="info")
    async def info(self, inter: discord.Interaction) -> None:
        """View information about Mocha Mayhem"""
        embed = functions.embed("Mocha Mayhem Info", color=0x005915)
        embed.description = "Welcome to Mocha Mayhem!\n\nTo play, run `/mm serve` to serve a customer a drink. You will be given a recipe, and you must select the right ingredients to make the drink within the time limit.\nCompleting drinks earns you points. To see how many points you have, run `/mm points`.\nTo see who has the most points in the server, run `/mm leaderboard`.\n\nYou also earn tips from making drinks.\nYou can view how much money you have through `/mm balance`.\nThese tips can be used to purchase ingredients using `/mm shop`.\nYou can view purchased ingredients using `/mm inventory`.\nThese ingredients can be used to practice making your own drinks, using `/mm practice`.\n\nThis game is still in development.\nIf there are any bugs, contact @trigtbh."
        await inter.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Barista(bot))