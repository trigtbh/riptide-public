import discord
from discord import app_commands
from discord.ext import commands
import settings
from discord.ext import tasks

from typing import *

import functions
import random
import os

def get_value(hand): # converts a hand into a score value
    value = 0
    vs = {}
    for i in range(2, 11):
        vs[str(i)] = i
    vs["J"] = 10
    vs["Q"] = 10
    vs["K"] = 10
    vs["A2"] = 1
    vs["A"] = 11
    has_a = False
    for card in hand:
        c_v = card[1:]
        value += vs[c_v]
    return value

def is_blackjack(hand):
    return get_value(hand) == 21 and len(hand) == 2

def hit(hand, deck): # adds a card to a hand and calculates if it busted or not
    bust = False
    card = random.choice(deck)
    deck.remove(card)
    new = hand + [card]
    v = get_value(new)
    if v <= 21:
        hand = new
    else:
        if card[1] == "A":
            fixed = hand + [card+"2"]
            v = get_value(fixed)
            if v <= 21:
                hand = fixed
            else:
                bust = True
        else:
            index = [hand.index(c) for c in hand if len(c) == 2 and c[1] == "A"]
            if len(index) > 0:
                hand[index[0]] = hand[index[0]][0] + "A2"
                fixed2 = hand + [card]
                v = get_value(fixed2)
                if v <= 21:
                    hand = fixed2
                else:
                    bust = True
            else:
                hand = new
                bust = True
    return hand, deck, bust

def process_hand(hand, mask=False): # human readable hand
    h = []
    for c in hand:
        if len(c) == 3:
            if c[-1] == "2":
                c = c[:2]

        h.append(c.replace("S", "♠").replace("D", "♦").replace("C", "♣").replace("H", "♥"))
    if mask:
        h = [h[0]] + (["??"] * (len(h) - 1))
    return h

def generate_deck(num=1): # shuffles num decks of cards and returns them
    deck = []
    for suit in {"D", "C", "H", "S"}:
        for value in {"A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"}:
            deck.append(suit + value)
    deck = deck * num
    random.shuffle(deck)
    return deck

class BlackJackView(discord.ui.View):
    def __init__(self, cog, interaction, uuid, bet, deck, player_hand, dealer_hand, actions):
        super().__init__(timeout=300)
        self.cog = cog
        self.interaction = interaction
        self.uuid = uuid
        self.val = 0
        self.bet = bet
        self.deck = deck
        self.phi = 0
        self.dealer_hand = dealer_hand
        self.actions = actions

        
        self.player_hands = [player_hand]
        self.player_bets = [bet]
        self.player_bust = [False]
        self.player_finished = [False]


        self.values = {
            "A2": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10, "A": 11
        }


        self.hit_button = discord.ui.Button(label="Hit", style=discord.ButtonStyle.green, custom_id="hit", emoji="👇")
        self.stand_button = discord.ui.Button(label="Stand", style=discord.ButtonStyle.green, custom_id="stand", emoji="👋")

        self.add_item(self.hit_button)
        self.add_item(self.stand_button)

        if "dd" in actions:
            self.dd_button = discord.ui.Button(label="Double Down", style=discord.ButtonStyle.green, custom_id="dd", emoji="💵")
            self.add_item(self.dd_button)
        
        self.surrender_button = discord.ui.Button(label="Surrender", style=discord.ButtonStyle.green, custom_id="surrender", emoji="👉")
        self.add_item(self.surrender_button)

        if "split" in actions:   
            self.split_button = discord.ui.Button(label="Split", style=discord.ButtonStyle.green, custom_id="split", emoji="✌️")
            self.add_item(self.split_button)

    async def on_timeout(self):
        embed = functions.embed("Blackjack - Timeout", color=0x7f2a3c)
        embed.description = "The game has timed out.\nTo start a new game, use `/blackjack."
        await self.interaction.edit_original_response(embed=embed, view=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            embed = functions.embed("Error: Invalid User", color=0x7f2a3c)
            embed.description = "You cannot use this button, as you are not the user who started this game."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    async def do_dealer_turn(self):
        while get_value(self.dealer_hand) < 17:
            self.dealer_hand, self.deck, bust = hit(self.dealer_hand, self.deck)

        if bust:
            hand_value = get_value(self.dealer_hand)
            total = 0
            to_return = 0
            for i, bust in enumerate(self.player_bust):
                if not bust:
                    total += self.player_bets[i]
                    to_return += self.player_bets[i] * 2
            embed = functions.embed("Blackjack - Dealer Bust", color=0x7f2a3c)
            if total > 0:
                # TODO: add to balance
                embed.description = f"The dealer busted by drawing a total of {hand_value}!\nYou won {total} coin{'s' if total != 1 else ''} from your bet{'s' if len(self.player_bets) > 1 else ''}!"
            else:
                embed.description = f"The dealer busted by drawing a total of {hand_value}!\nUnfortunately, you didn't win any coins from your bet{'s' if len(self.player_bets) > 1 else ''}."
            return await self.interaction.edit_original_response(embed=embed, view=None)
        
        value = get_value(self.dealer_hand)
        total = 0
        to_return = 0
        for i, hand in enumerate(self.player_hands):
            if self.player_bust[i]:
                continue
            test_value = get_value(hand)
            if test_value > value:
                total += self.player_bets[i]
                to_return += self.player_bets[i] * 2
            elif test_value == value:
                total += self.player_bets[i]
                to_return += self.player_bets[i]
        # TODO: the rest of this


    async def hit_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction.user.id:
            return

        self.player_hands[self.phi], self.deck, bust = hit(self.player_hands[self.phi], self.deck)

        if bust:
            self.player_bust[self.phi] = True
            self.player_finished[self.phi] = True
            embed = functions.embed("Blackjack - Hit", color=0x7f2a3c)
            player_hand = self.player_hands[self.phi]
            desc = f"**Your hand ({self.phi + 1}/{len(self.player_hands)})**: `{', '.join(process_hand(player_hand))}` ({get_value(player_hand)})"
            desc += f"\n**Dealer's hand**: `{', '.join(process_hand(self.dealer_hand, mask=True))}` (??)"
            desc += "\n\nYour hand has busted!"
            if not all([self.player_finished[i] or self.player_bust[i] for i in range(len(self.player_hands))]):
                desc += "\n\nIt is now the dealer's turn.\nPress the button below to continue."
                #self.
                # TODO: ???
        





class Gambling(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()
        if self.bot.environment == "stable":
            self.stock_change.start()


    def get_file_name(self):
        return os.path.normpath(__file__).split(os.sep)[-1][:-3]

    def generate_blank(self, uuid):
        return {'_id': uuid, 'balance': 0, 'low_stock': 0, 'med_stock': 0, 'high_stock': 0, 'daily_delay': 0}

    # create a task that loops every 24 hours and changes the stock prices
    @tasks.loop(hours=24)
    async def stock_change(self):
        for guild in self.bot.guilds:
            # check if cog is disabled in guild
            disabled = self.bot.mdb["TrigBot"]["settings"]
            within = disabled.find_one({"_id": guild.id})
            if within:
                if self.get_file_name() in within["disabled_cogs"]:
                    continue
                if "economy" in within["disabled_cogs"]:
                    continue

            for user in guild.members:
                data = self.bot.mdb['TrigBot']['economy'].find_one({'_id': user.id})
                if data:
                    low = random.randint(-15, 15) / 100
                    med = random.randint(-25, 25) / 100
                    high = random.randint(-45, 45) / 100
                    # get the current stock value and multiply the change
                    low_stock = int(round(data['low_stock'] * (1 + low)))
                    med_stock = int(round(data['med_stock'] * (1 + med)))
                    high_stock = int(round(data['high_stock'] * (1 + high)))
                    # update the stock values
                    self.bot.mdb['TrigBot']['economy'].update_one({'_id': user.id}, {'$set': {'low_stock': low_stock, 'med_stock': med_stock, 'high_stock': high_stock}})


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

    @app_commands.command(name="slots")
    @app_commands.describe(bet="The amount of coins to bet")
    async def slots(self, interaction: discord.Interaction, bet: int) -> None:
        """Play a game of slots"""
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(interaction.user.id))
        if bet < 0:
            embed = functions.embed("Error: Invalid Bet", color=0xff0000)
            embed.description = "You can't bet a negative amount of coins."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})['balance'] < bet:
            embed = functions.embed("Error: Insufficient Funds", color=0xff0000)
            embed.description = "You don't have enough coins to make that bet."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if bet == 0:
            embed = functions.embed("Error: Invalid Bet", color=0xff0000)
            embed.description = "You can't bet 0 coins."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': -bet}})
        embed = functions.embed("Slots", color=0x7f2a3c)
        embed.description = f"{interaction.user.mention} bet **{bet}** coin" + ("s" if bet != 1 else "") + " and got:\n"
        slot1 = random.choice(["🍇", "🍊", "🍒", "🍋", "🍉", "🍎", "🍓", "🍐", "🍈", "🍑"])
        slot2 = random.choice(["🍇", "🍊", "🍒", "🍋", "🍉", "🍎", "🍓", "🍐", "🍈", "🍑"])
        slot3 = random.choice(["🍇", "🍊", "🍒", "🍋", "🍉", "🍎", "🍓", "🍐", "🍈", "🍑"])

        embed.description += f"{slot1} {slot2} {slot3}\n\n"
        
        if slot1 == slot2 == slot3:
            embed.description += f"You won **{bet * 5}** coins!"
            self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': bet * 5}})
        elif slot1 == slot2 or slot1 == slot3 or slot2 == slot3:
            embed.description += f"You won **{bet * 2}** coins!"
            self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': bet * 2}})
        else:
            embed.description += "You lost your bet."

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip")
    @app_commands.describe(bet="The amount of coins to bet", call="Heads or tails")
    @app_commands.choices(call=[app_commands.Choice(name="Heads", value="Heads"), app_commands.Choice(name="Tails", value="Tails")])
    async def coinflip(self, interaction: discord.Interaction, bet: int, call: str) -> None:
        """Flip a coin"""
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(interaction.user.id))
        if bet < 0:
            embed = functions.embed("Error: Invalid Bet", color=0xff0000)
            embed.description = "You can't bet a negative amount of coins."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})['balance'] < bet:
            embed = functions.embed("Error: Insufficient Funds", color=0xff0000)
            embed.description = "You don't have enough coins to make that bet."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if bet == 0:
            embed = functions.embed("Error: Invalid Bet", color=0xff0000)
            embed.description = "You can't bet 0 coins."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': -bet}})
        embed = functions.embed("Coinflip", color=0x7f2a3c)
        embed.description = f"{interaction.user.mention} bet **{bet}** coin" + ("s" if bet != 1 else "") + f" on `{call}` and got:\n"
        flip = random.choice(["Heads", "Tails"])
        embed.description += f"**{flip}**\n\n"
        if flip == call:
            embed.description += f"You won **{bet * 2}** coins!"
            self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': bet * 2}})
        else:
            embed.description += "You lost your bet."

        await interaction.response.send_message(embed=embed)

    group = app_commands.Group(name="stocks", description="...")

    @group.command(name="info")
    async def stock_info(self, interaction: discord.Interaction):
        """Get info on the three types of stocks available to trade"""
        embed = functions.embed("Stocks", color=0x7f2a3c)
        embed.add_field(name="Stock 1: $ABSA", value="A low-risk stock, with relatively low chances of significant change.\nHowever, decreases are more likely and slightly more sever than potential increases.", inline=False)
        embed.add_field(name="Stock 2: $JHAS", value="Riskier than $ABSA, with higher chances of significant change.\nIncreases are slightly more common, but also more severe.\nPurchases have a minimum of 50 coins.", inline=False)
        embed.add_field(name="Stock 3: $MFKA", value="Extremely volatile stock, with significant and severe changes almost guaranteed.", inline=False)
        await interaction.response.send_message(embed=embed)

    @group.command(name="buy")
    @app_commands.describe(stock="The stock to buy", money="The amount of money you would like to put into a stock")
    @app_commands.choices(stock=[app_commands.Choice(name="$ABSA", value="low_stock"), app_commands.Choice(name="$JHAS", value="med_stock"), app_commands.Choice(name="$MFKA", value="high_stock")])
    async def stock_buy(self, interaction: discord.Interaction, stock: str, money: int):
        """Buy stocks"""
        mapped = {"low_stock": "$ABSA", "med_stock": "$JHAS", "high_stock": "$MFKA"}
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(interaction.user.id))
        if money < 0:
            embed = functions.embed("Error: Invalid Amount", color=0xff0000)
            embed.description = "You can't buy a negative amount of stocks."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})['balance'] < money:
            embed = functions.embed("Error: Insufficient Funds", color=0xff0000)
            embed.description = "You don't have enough coins to buy that many stocks."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if money == 0:
            embed = functions.embed("Error: Invalid Amount", color=0xff0000)
            embed.description = "You can't buy 0 stocks."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if stock == "med_stock" and money < 50:
            embed = functions.embed("Error: Invalid Amount", color=0xff0000)
            embed.description = "You can't buy less than 50 coins worth of $JHAS."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': -money}})
        self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {stock: money}})
        embed = functions.embed("Stocks", color=0x7f2a3c)
        embed.description = f"{interaction.user.mention} bought **{money}** coin" + ("s" if money != 1 else "") + f" worth of `{mapped[stock]}`."
        await interaction.response.send_message(embed=embed)

    @group.command(name="sell")
    @app_commands.describe(stock="The stock to sell", money="The amount of money you would like to sell from a stock")
    @app_commands.choices(stock=[app_commands.Choice(name="$ABSA", value="low_stock"), app_commands.Choice(name="$JHAS", value="med_stock"), app_commands.Choice(name="$MFKA", value="high_stock")])
    async def stock_sell(self, interaction: discord.Interaction, stock: str, money: int):
        """Sell stocks"""
        mapped = {"low_stock": "$ABSA", "med_stock": "$JHAS", "high_stock": "$MFKA"}
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(interaction.user.id))
        if money < 0:
            embed = functions.embed("Error: Invalid Amount", color=0xff0000)
            embed.description = "You can't sell a negative amount of stocks."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})[stock] < money:
            embed = functions.embed("Error: Insufficient Stocks", color=0xff0000)
            embed.description = "You don't have enough stocks to sell that many."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if money == 0:
            embed = functions.embed("Error: Invalid Amount", color=0xff0000)
            embed.description = "You can't sell 0 stocks."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': money}})
        self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {stock: -money}})
        embed = functions.embed("Stocks", color=0x7f2a3c)
        embed.description = f"{interaction.user.mention} sold **{money}** coin" + ("s" if money != 1 else "") + f" worth of `{mapped[stock]}`."
        await interaction.response.send_message(embed=embed)

    @group.command(name="portfolio")
    async def stock_portfolio(self, interaction: discord.Interaction):
        """View your stocks"""
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(interaction.user.id))
        embed = functions.embed("Stocks", color=0x7f2a3c)
        embed.description = f"{interaction.user.mention}'s Stocks"
        ls = self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})['low_stock']
        ms = self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})['med_stock']
        hs = self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})['high_stock']
        embed.add_field(name="$ABSA", value=f"{ls} coin" + ("s" if ls != 1 else ""), inline=False)
        embed.add_field(name="$JHAS", value=f"{ms} coin" + ("s" if ms != 1 else ""), inline=False)
        embed.add_field(name="$MFKA", value=f"{hs} coin" + ("s" if hs != 1 else ""), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="blackjack")
    @app_commands.describe(bet="The amount of money you would like to bet")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        """Play a game of Blackjack against the bot"""
        
        
        if not self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id}):
            self.bot.mdb['TrigBot']['economy'].insert_one(self.generate_blank(interaction.user.id))
        data = self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})
        if bet < 1:
            embed = functions.embed("Error: Invalid Bet", color=0xff0000)
            embed.description = "You can't bet 0 coins."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if data["balance"] < bet:
            embed = functions.embed("Error: Insufficient Funds", color=0xff0000)
            embed.description = "You don't have enough coins to make that bet."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': -bet}})
        
        embed = functions.embed("Blackjack", color=0x7f2a3c)
        
        deck = generate_deck(num=5) # ty affax for telling me to have "5 decks in a shoe", then causing me to search up what that meant
        player_hand = deck[:2]
        del deck[:2]
        dealer_hand = deck[:2]
        del deck[:2]

        desc = f"**Your hand (1/1)**: `{', '.join(process_hand(player_hand))}` ({get_value(player_hand)})"
        if is_blackjack(player_hand) and is_blackjack(dealer_hand):
            desc += f"\n**Dealer's hand**: `{', '.join(process_hand(dealer_hand))}` ({get_value(dealer_hand)}\n\nBoth you and the dealer drew a blackjack!\nYour initial bet has been returned to you."
            embed.description = desc
            self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': bet}})
            await interaction.response.send_message(embed=embed)
            return
        elif is_blackjack(dealer_hand):
            desc += f"\n**Dealer's hand**: `{', '.join(process_hand(dealer_hand))}` ({get_value(dealer_hand)}\n\nThe dealer drew a Blackjack!\nYou lost this hand."
            embed.description = desc
            await interaction.response.send_message(embed=embed)
            return
        elif is_blackjack(player_hand):
            inc = int(bet * 3 / 2)
            desc += f"\n**Dealer's hand**: `{', '.join(process_hand(dealer_hand))}` ({get_value(dealer_hand)}\n\nYou drew a Blackjack!\nYou won **{inc} coins** from this hand."
            embed.description = desc
            self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': bet}})
            self.bot.mdb['TrigBot']['economy'].update_one({'_id': interaction.user.id}, {'$inc': {'balance': int(bet * 3 / 2)}})
            await interaction.response.send_message(embed=embed)
            return

        desc += f"\n**Dealer's hand**: `{', '.join(process_hand(dealer_hand, mask=True))}` (??)\nUse the buttons below to select an action."
        embed.description = desc

        available_actions = ["hit", "stand"]

        embed.add_field(name="👇 HIT", value="Draw another card.", inline=False)
        embed.add_field(name="👋 STAND", value="End your turn.", inline=False)
        current_balance = self.bot.mdb['TrigBot']['economy'].find_one({'_id': interaction.user.id})['balance']
        if current_balance >= bet:
            available_actions.append("dd")
            embed.add_field(name="💵 DOUBLE DOWN", value="Double your bet and draw one more card, then immediately end your turn.", inline=False)
        embed.add_field(name="👉 SURRENDER", value="Give up half your bet and end your turn.", inline=False)
        available_actions.append("surrender")
        if current_balance >= bet and len(player_hand) == 2 and player_hand[0][1] == player_hand[1][1]:
            available_actions.append("split")
            embed.add_field(name="💰 SPLIT", value="Split your hand into two hands and double your bet, then draw one card for each hand.", inline=False)

        
        view = BlackJackView(self, interaction, interaction.user.id, bet, deck, player_hand, dealer_hand, available_actions)
        
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Gambling(bot))