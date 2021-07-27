# import os
# from asyncio import sleep
# from asyncio.exceptions import TimeoutError
# from textwrap import shorten
# from contextlib import suppress
from random import choice
from copy import deepcopy

from expiringdict import ExpiringDict
from discord import Member, Forbidden, NotFound
from discord.ext.commands.cog import Cog
from discord.ext.commands.core import (
    has_permissions, 
    bot_has_permissions, 
    command
)

from utils.classes import Embed

class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.exp_cooldown = ExpiringDict(
            max_len=float('inf'), 
            max_age_seconds=60)

        # ax+b
        self.a = 50
        self.b = 250
        self.subtract_value = self.b+self.a
    
    @command(name="rank")
    @has_permissions(send_messages=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def check_rank(self, ctx, member: Member = None):
        if not member:
            member = ctx.author

        # Working copy of new cumulative exp
        cumulative_exp_copy = deepcopy(self.bot.user_data["UserData"][str(member.id)]["Leveling"]["Cumulative EXP"])

        # Iterate through new cumulative EXP for new level
        current_level = 0
        while True:
            cumulative_exp_copy -= self.subtract_value
                
            if cumulative_exp_copy < 0: 
                cumulative_exp_copy += self.subtract_value
                break
            else:
                current_level += 1
                self.subtract_value += 50
                
            continue

        total_exp_to_next = (self.a*current_level)+self.b
        remaining_exp_to_next = ((self.a*current_level)+self.b)-cumulative_exp_copy

        full_cumulative_exp = deepcopy(self.bot.user_data["UserData"][str(member.id)]["Leveling"]["Cumulative EXP"])
        full_spending_exp = deepcopy(self.bot.user_data["UserData"][str(member.id)]["Leveling"]["Spending EXP"])

        await ctx.send(embed=Embed(
            title="NH Rank",
            description=f"You are level {current_level}.\n" \
                        f"You are {remaining_exp_to_next}/{total_exp_to_next} EXP away from your next level.\n"
                        f"\n"
                        f"Current Spending EXP: 💲 {full_spending_exp}\n"
                        f"Total Cumulative EXP: 🐾 {full_cumulative_exp}"
        ))

    @Cog.listener()
    async def on_message(self, msg):
        return

        # Don't respond to bots.
        if msg.author.bot:
            return

        # Check if the message is a command. 
        # Terminates the event if so, so the command can run.
        verify_command = await self.bot.get_context(msg)
        if verify_command.valid:
            self.bot.inactive = 0
            return

        if ctx.guild.id == 740662779106689055:
            exp_gain = 75

            rewards = {
                1:  851225537165918259,  # @Interested
                3:  851236641531363338,  # @Media Perms
                5:  851225705148841985,  # @Neko Admirer
                10: 851225900607602700,  # @Neko Lover
                15: 851225951161417738,  # @Neko Addict
                20: 740677748204240980,  # @Neko Headpatter
                22: 740677678159364147,  # @Neko Enthusiast
                24: 740679288533024911,  # @Neko Body Rubber
                26: 740679721385328750,  # @Neko Pleasurer
                28: 740677950315429969,  # @Neko Caretaker
                30: 740678012097265704,  # @Neko Owner
                32: 755608514755428442,  # @Neko Babysitter
                34: 830525152553992244,  # @Neko Connoisseur
            }
            
            ignored_channels = [
                740923481939509258,  # Staff Room
                740676328935653406,  # Bulletin
                761793288910143498,  # #⚠️nsfw-bots
                780654704362389535,  # Upstairs
                852405741402062880,  # NReader
            ]

            ignore_cooldown = [
                740663474568560671,  # SFW Catgirls
                740663386500628570   # NSFW Catgirls
            ]

            modifiers = {
                741381152543211550: 1.05,  # #general-1
                769386184895234078: 0.75,  # #high-tier-hideout
                816671250025021450: 0.50,  # Robotics Club
                740663474568560671: 0.20,  # SFW Catgirls
                740663386500628570: 0.20,  # NSFW Catgirls
            }

            def calculate_earnings():
                if not ((msg.channel.id in ignore_cooldown) or \
                    (msg.channel.category and msg.channel.category.id in ignore_cooldown)):
                    if msg.author.id in self.exp_cooldown: return 0
                    else: self.exp_cooldown[msg.author.id] = "placeholder"

                if (msg.channel.id in ignored_channels) or \
                    (msg.channel.category and msg.channel.category.id in ignored_channels):
                    return 0

                try: modifier_1 = modifiers[msg.channel.id]
                except KeyError: modifier_1 = 0
                if msg.channel.category:
                    try: modifier_2 = modifiers[msg.channel.category.id]
                    except KeyError: modifier_2 = 0

                total = exp_gain + (exp_gain*modifier_1) + (exp_gain*modifier_2) + \
                    (exp_gain*self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["personal_modifier"])

                return total

            if str(msg.author.id) not in self.bot.user_data["UserData"]:
                self.bot.user_data["UserData"][str(msg.author.id)] = \
                    self.bot.defaults["UserData"]["UID"]

            # Check for level up
            # Working copy of current cumulative exp
            cumulative_exp_copy = deepcopy(self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["Cumulative EXP"])

            # Iterate through current cumulative EXP for level
            current_level = 0
            while True:
                cumulative_exp_copy -= self.subtract_value
                
                if cumulative_exp_copy < 0: 
                    cumulative_exp_copy += self.subtract_value
                    break
                else:
                    current_level += 1
                    self.subtract_value += 50
                
                continue

            # Add values to account
            earnings = calculate_earnings()
            self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["Cumulative EXP"] += earnings
            self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["Spending EXP"] += earnings

            # Working copy of new cumulative exp
            cumulative_exp_copy = deepcopy(self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["Cumulative EXP"])

            # Iterate through new cumulative EXP for new level
            new_level = 0
            while True:
                cumulative_exp_copy -= self.subtract_value
                
                if cumulative_exp_copy < 0: 
                    cumulative_exp_copy += self.subtract_value
                    break
                else:
                    new_level += 1
                    self.subtract_value += 50
                
                continue

            if level1 != level2:
                total_exp_to_next = (self.a*new_level)+self.b
                remaining_exp_to_next = ((self.a*new_level)+self.b) - cumulative_exp_copy
                
                full_cumulative_exp = deepcopy(self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["Cumulative EXP"])
                full_spending_exp = deepcopy(self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["Spending EXP"])

                level_up_gifs = [
                    "https://cdn.discordapp.com/attachments/741381152543211550/869651824314052658/unknown.gif",
                    "https://i.pinimg.com/originals/2e/27/d5/2e27d5d124bc2a62ddeb5dc9e7a73dd8.gif",
                    "https://cdn.discordapp.com/attachments/722603546024869978/869650507344519270/ezgif-1-4fbad88c84891.gif",
                    "https://gifimage.net/wp-content/uploads/2017/09/anime-head-pat-gif.gif",
                    "https://media.giphy.com/media/ye7OTQgwmVuVy/giphy.gif",
                    "https://media1.tenor.com/images/0ea33070f2294ad89032c69d77230a27/tenor.gif?itemid=16053520",
                    "https://media1.tenor.com/images/ecb87fb2827a022884d5165046f6608a/tenor.gif?itemid=16042548",
                    "https://media1.tenor.com/images/63924d378cf9dbd6f78c2927dde89107/tenor.gif?itemid=15049549",
                    "https://media1.tenor.com/images/57e98242606d651cc992b9525d3de2d8/tenor.gif?itemid=17549072",
                    "https://media1.tenor.com/images/fad9a512808d29f6776e7566f474321c/tenor.gif?itemid=16917926"
                ]

                try: reward = rewards[new_level]
                except KeyError: reward = None
                if reward:
                    role = msg.guild.fetch_role(reward)

                await msg.channel.send(content=msg.author.mention, embed=Embed(
                    description=f"You've leveled up! Thanks for spending your time with us.\n"
                                f"You are now level {new_level}! Have a headpat.\n"
                                f"{'You earned the '+role.mention+' role!'+newline if reward else ''}"
                                f"\n"
                                f"Current Spending EXP: 💲 {full_spending_exp}\n"
                                f"Total Cumulative EXP: 🐾 {full_cumulative_exp}"
                    ).set_footer(text=f"You are {remaining_exp_to_next}/{total_exp_to_next} away from the next level."
                    ).set_image(url=choice(level_up_gifs)))

def setup(bot):
    bot.add_cog(Commands(bot))
