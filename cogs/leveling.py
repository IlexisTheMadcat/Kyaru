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

newline = "\n"


class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.exp_cooldown = ExpiringDict(
            max_len=float('inf'), 
            max_age_seconds=60)

        # ax+b
        self.a = 50
        self.b = 100
        self.exp_gain = 50
    
    @command(name="rank", aliases=["level"])
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def check_rank(self, ctx, member: Member = None):
        if not member:
            member = ctx.author

        # Working copy of new cumulative exp
        cumulative_exp_copy = deepcopy(self.bot.user_data["UserData"][str(member.id)]["Leveling"]["Cumulative EXP"])

        # Iterate through new cumulative EXP for new level
        current_level = 0
        while True:
            cumulative_exp_copy -= (self.a*(current_level+1)) + self.b
                
            if cumulative_exp_copy < 0: 
                cumulative_exp_copy += (self.a*(current_level+1)) + self.b
                break
            else:
                current_level += 1
                
            continue

        total_exp_to_next = (self.a*(current_level+1))+self.b
        remaining_exp_to_next = ((self.a*(current_level+1))+self.b) - cumulative_exp_copy
        obtained_exp_to_next = total_exp_to_next - remaining_exp_to_next

        full_cumulative_exp = deepcopy(self.bot.user_data["UserData"][str(member.id)]["Leveling"]["Cumulative EXP"])
        full_spending_exp = deepcopy(self.bot.user_data["UserData"][str(member.id)]["Leveling"]["Spending EXP"])

        if remaining_exp_to_next%1 == 0: remaining_exp_to_next = int(remaining_exp_to_next)
        if obtained_exp_to_next%1 == 0: obtained_exp_to_next = int(obtained_exp_to_next)

        if member.id == ctx.author.id:
            await ctx.send(embed=Embed(
                title="Neko Heaven Rank",
                description=f"You are currently level {current_level} ({obtained_exp_to_next}/{total_exp_to_next}).\n"
                            f"You are {remaining_exp_to_next} EXP away from your next level.\n"
                            f"\n"
                            f"Current Spending EXP: 💲 {full_spending_exp}\n"
                            f"Total Cumulative EXP: 🐾 {full_cumulative_exp}"
            ))
        else:
            await ctx.send(embed=Embed(
                title="Neko Heaven Rank",
                description=f"{member.mention} is currently level {current_level} ({obtained_exp_to_next}/{total_exp_to_next}).\n"
                            f"They are {remaining_exp_to_next} EXP away from their next level.\n"
                            f"\n"
                            f"Current Spending EXP: 💲 {full_spending_exp}\n"
                            f"Total Cumulative EXP: 🐾 {full_cumulative_exp}"
            ))

    @command(name="leaderboard", aliases=["lead"])
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def leaderboard(self, ctx):
        users = [(uid, self.bot.user_data["UserData"][uid]["Leveling"]["Cumulative EXP"]) for uid in self.bot.user_data["UserData"]]
        users.sort(key=lambda i: i[1])
        users = users[-15:len(users)]
        users.reverse()


        member_rank_list = []
        for uid, exp in users:
            # Working copy of new cumulative exp
            cumulative_exp_copy = deepcopy(self.bot.user_data["UserData"][str(uid)]["Leveling"]["Cumulative EXP"])

            # Iterate through new cumulative EXP for new level
            current_level = 0
            while True:
                cumulative_exp_copy -= (self.a*(current_level+1)) + self.b
                
                if cumulative_exp_copy < 0: 
                    cumulative_exp_copy += (self.a*(current_level+1)) + self.b
                    break
                else:
                    current_level += 1
                
                continue

            total_exp_to_next = (self.a*(current_level+1))+self.b
            remaining_exp_to_next = ((self.a*(current_level+1))+self.b) - cumulative_exp_copy
            obtained_exp_to_next = total_exp_to_next - remaining_exp_to_next

            full_cumulative_exp = deepcopy(self.bot.user_data["UserData"][str(uid)]["Leveling"]["Cumulative EXP"])
            full_spending_exp = deepcopy(self.bot.user_data["UserData"][str(uid)]["Leveling"]["Spending EXP"])

            if remaining_exp_to_next%1 == 0: remaining_exp_to_next = int(remaining_exp_to_next)
            if obtained_exp_to_next%1 == 0: obtained_exp_to_next = int(obtained_exp_to_next)

            member = ctx.guild.get_member(int(uid))
            if not member:
                try: await ctx.guild.fetch_member(int(uid))
                except NotFound: 
                    self.bot.user_data["UserData"].pop(uid)
                    continue

            member_rank_list.append(f"▄{member.mention}\n"
                                    f"__▀ Level {current_level} ({obtained_exp_to_next}/{total_exp_to_next} EXP)__")

        await ctx.send(embed=Embed(
            title="Neko Heaven Leaderboard",
            description=f"Here are the top 15 ranked users for this server:\n"
                        f"----------\n"
        ).add_field(
            name="**1-5**",
            inline=True,
            value=newline.join(member_rank_list[0:5])
        ).add_field(
            name="**6-10**",
            inline=True,
            value=newline.join(member_rank_list[5:10])
        ).add_field(
            name="**11-15**",
            inline=True,
            value=newline.join(member_rank_list[10:15])
        ))

    @command(aliases=["setlevel", "setrank", "sl", "sr"])
    @has_permissions(administrator=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def set_cumulative_exp(self, ctx, member, level=None):
        try:
            member = member.strip("<@!>")
            member = int(member)
            level = int(level)
        except ValueError:
            await ctx.send(embed=Embed(
                color=0xff0000,
                description="**Invalid argument(s).**\n"
                            "`member`  and `level` must be numbers.\n"
                            "`member` should be a UID that belongs to a member in this server."))

            return

        member = ctx.guild.get_member(member)
        if not member:
            await ctx.send(embed=Embed(
                color=0xff0000,
                description=f"No member with UID {member} found."))
            return
        
        if member.bot:
            await ctx.send(embed=Embed(
                color=0xff0000,
                description=f"Bots don't count."))
            return

        if str(member.id) not in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(member.id)] = \
                self.bot.defaults["UserData"]["UID"]

        cumulative_exp = 0
        working_level = deepcopy(level)
        while True:
            working_level -= 1

            if working_level < 0: 
                working_level += 1
                break
            else:
                cumulative_exp += (self.a*(working_level+1)) + self.b
                
            continue

        self.bot.user_data["UserData"][str(member.id)]["Leveling"]["Cumulative EXP"] = cumulative_exp

        await ctx.send(embed=Embed(
            title="Set Level",
            description=f"✅ Set {member.mention}'s level to {level}."))

    @command(name="setspending", aliases=["setmoney"])
    @has_permissions(administrator=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def set_spending_exp(self, ctx, member, amount=None):
        try:
            member = member.strip("<@!>")
            member = int(member)
            amount = int(amount)
        except ValueError:
            await ctx.send(embed=Embed(
                color=0xff0000,
                description="**Invalid argument(s).**\n"
                            "`member`  and `amount` must be numbers.\n"
                            "`member` should be a UID that belongs to a member in this server."))

            return

        member = ctx.guild.get_member(member)
        if not member:
            await ctx.send(embed=Embed(
                color=0xff0000,
                description=f"No member with UID {member} found."))
            return
        
        if member.bot:
            await ctx.send(embed=Embed(
                color=0xff0000,
                description=f"Bots don't count."))
            return

        if str(member.id) not in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(member.id)] = \
                self.bot.defaults["UserData"]["UID"]

        self.bot.user_data["UserData"][str(member.id)]["Leveling"]["Spending EXP"] = amount

        await ctx.send(embed=Embed(
            title="Set Spending",
            description=f"✅ Set {member.mention}'s Spending EXP to {amount}."))

    @command(aliases=["lp_levelup"])
    @bot_has_permissions(send_messages=True)
    async def toggle_lowprofile_levelup(self, ctx):
        self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["lp_levelup"] = \
            not self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["lp_levelup"]

        await ctx.send(f'Toggled Low Profile Levelup indicator for you. It should now be set to {self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["lp_levelup"]}.')

    @Cog.listener()
    async def on_message(self, msg):
        # Don't respond to bots.
        if msg.author.bot:
            return

        # Check if the message is a command. 
        # Terminates the event if so, so the command can run.
        verify_command = await self.bot.get_context(msg)
        if verify_command.valid:
            self.bot.inactive = 0
            return

        if msg.guild.id == 740662779106689055:
            rewards = {
                1:  851225537165918259,  # r@Interested
                3:  851236641531363338,  # r@Media Perms
                5:  851225705148841985,  # r@Neko Admirer
                10: 851225900607602700,  # r@Neko Lover
                15: 851225951161417738,  # r@Neko Addict
                20: 740677748204240980,  # r@Neko Headpatter
                22: 740677678159364147,  # r@Neko Enthusiast
                24: 740679288533024911,  # r@Neko Body Rubber
                26: 740679721385328750,  # r@Neko Pleasurer
                28: 740677950315429969,  # r@Neko Caretaker
                30: 740678012097265704,  # r@Neko Owner
                32: 755608514755428442,  # r@Neko Babysitter
                34: 830525152553992244,  # r@Neko Connoisseur
            }
            
            ignored_channels = [
                740923481939509258,  # c#Staff Room
                740676328935653406,  # c#Bulletin
                761793288910143498,  # t#⚠️nsfw-bots
                780654704362389535,  # c#Upstairs
                852405741402062880,  # c#NReader
            ]

            ignored_roles = [
                789960054970515487,  # r@⛔Leveling Paused
                741431440490627234   # r@Muted
            ]

            ignore_cooldown = [
                740663474568560671,  # c#SFW Catgirls
                740663386500628570   # c#NSFW Catgirls
            ]

            modifiers = {
                "textc": {
                    741381152543211550: 1.05,  # t#🐾general-1
                    769386184895234078: 0.75,  # t#🐾high-tier-hideout
                },
                "categoryc": {
                    816671250025021450: 0.05,  # c#Robotics Club
                    740663474568560671: 0.20,  # c#SFW Catgirls
                    740663386500628570: 0.20,  # c#NSFW Catgirls
                },
                "role": {  # Role does not stack
                    748505664472612994: 1.05,  # r@⭐Neko Bookster!⭐
                }
            }

            def calculate_earnings():
                if not ((msg.channel.id in ignore_cooldown) or \
                    (msg.channel.category and msg.channel.category.id in ignore_cooldown)):
                    if msg.author.id in self.exp_cooldown: return 0
                    else: self.exp_cooldown[msg.author.id] = "placeholder"

                if (msg.channel.id in ignored_channels) or \
                    (msg.channel.category and msg.channel.category.id in ignored_channels):
                    return 0

                if any([i in [x.id for x in msg.author.roles] for i in ignored_roles]):
                    return 0

                # check text channel
                if msg.channel.id in modifiers["textc"]: 
                    modifier_1 = modifiers["textc"][msg.channel.id]
                else: modifier_1 = 1
                
                # check category channel
                if msg.channel.category and msg.channel.category.id in modifiers["categoryc"]: 
                    # special case for neko media channels
                    if msg.channel.category.id in [740663474568560671, 740663386500628570]:
                        if not msg.attachments or len(msg.attachments) > 1:
                            return 0

                    modifier_2 = modifiers["categoryc"][msg.channel.category.id]
                else: modifier_2 = 1
                
                # check highest booster role
                modifier_3 = 0
                has_booster_role = False
                for i in [x.id for x in msg.author.roles]:
                    if i in modifiers["role"] and modifiers["role"][i] > modifier_3:
                        modifier_3 = modifiers["role"][i]
                        has_booster_role = True
                if not has_booster_role: modifier_3 = 1

                # personal modifier
                last_modifier = self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["personal_modifier"]

                total = (((((self.exp_gain)*modifier_1)*modifier_2)*modifier_3)*last_modifier)
                if not total:
                    self.exp_cooldown.pop(msg.author.id)

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
                cumulative_exp_copy -= (self.a*(current_level+1)) + self.b
                
                if cumulative_exp_copy < 0: 
                    cumulative_exp_copy += (self.a*(current_level+1)) + self.b
                    break
                else:
                    current_level += 1
                
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
                cumulative_exp_copy -= (self.a*(new_level+1)) + self.b
                
                if cumulative_exp_copy < 0: 
                    cumulative_exp_copy += (self.a*(new_level+1)) + self.b
                    break
                else:
                    new_level += 1
                
                continue

            if current_level != new_level:
                total_exp_to_next = (self.a*(new_level+1))+self.b
                remaining_exp_to_next = ((self.a*(new_level+1))+self.b) - cumulative_exp_copy
                obtained_exp_to_next = total_exp_to_next - remaining_exp_to_next
                
                full_cumulative_exp = deepcopy(self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["Cumulative EXP"])
                full_spending_exp = deepcopy(self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["Spending EXP"])

                if remaining_exp_to_next%1 == 0: remaining_exp_to_next = int(remaining_exp_to_next)
                if obtained_exp_to_next%1 == 0: obtained_exp_to_next = int(obtained_exp_to_next)
                
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
                    role = msg.guild.get_role(reward)
                    if not role:
                        raise NotFound("role not found.")

                    await msg.author.add_roles(role)

                if self.bot.user_data["UserData"][str(msg.author.id)]["Settings"]["lp_levelup"]:
                    num_to_emoji = {1:"1️⃣", 2:"2️⃣", 3:"3️⃣", 4:"4️⃣", 5:"5️⃣", 6:"6️⃣", 7:"7️⃣", 8:"8️⃣", 9:"9️⃣", 0:"0️⃣"}
                    await msg.add_reaction(self.bot.get_emoji(870095475561361458))
                    for number in str(new_level):
                        await msg.add_reaction(num_to_emoji[new_level])

                    await sleep(5)
                    await msg.clear_reactions()

                else:
                    await msg.channel.send(content=msg.author.mention, embed=Embed(
                        description=f"You've leveled up! Thanks for spending your time with us.\n"
                                    f"You are now level {new_level}! Have a headpat.\n"
                                    f"{'You earned the '+role.mention+' role!'+newline if reward else ''}"
                                    f"\n"
                                    f"Current Spending EXP: 💲 {full_spending_exp}\n"
                                    f"Total Cumulative EXP: 🐾 {full_cumulative_exp}"
                        ).set_footer(text=f"You are {remaining_exp_to_next} EXP away from the next level."
                        ).set_image(url=choice(level_up_gifs)))

    @leaderboard.before_invoke
    async def placeholder_remove(self, ctx):
        if ctx.command.name == "leaderboard":
            if "UID" in self.bot.user_data['UserData']:
                self.bot.user_data["UserData"].pop("UID")

    @leaderboard.after_invoke
    async def placeholder_add(self, ctx):
        if ctx.command.name == "leaderboard":
            if "UID" not in self.bot.user_data['UserData']:
                self.bot.user_data["UserData"].update({"UID":self.bot.defaults["UserData"]["UID"]})

def setup(bot):
    bot.add_cog(Commands(bot))
