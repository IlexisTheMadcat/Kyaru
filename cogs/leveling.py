# import os
import re
from asyncio import sleep
from asyncio.exceptions import TimeoutError
# from textwrap import shorten
from contextlib import suppress
from random import choice, randint
from copy import deepcopy

from expiringdict import ExpiringDict
from discord import Member, Forbidden, NotFound
from discord.ext.commands.cog import Cog
from discord.ext.commands.core import has_permissions, bot_has_permissions, command
from discord.ext.tasks import loop
from discord.utils import get

from utils.classes import Embed

newline = "\n"


class Leveling(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.exp_cooldown = ExpiringDict(
            max_len=float('inf'), 
            max_age_seconds=60)
        self.temp_boosted = {}  # {int(UID): int(modifier)}

        # For use in an ax+b equation
        self.a = 50
        self.b = 100

        # Shop; {"Item Name": int(Cost)}
        self.storefront = {
            "Cumulative EXP Booster +0.5x 20m": 1000,
            "Cumulative EXP Booster +1.0x 20m": 2000,
            "Cumulative EXP Booster +2.0x 30m": 3500,
            "Temporary Mute 5m": 2500,
        }

        # Channel meta
        self.rewards = {
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
            
        self.ignored_channels = [
            740923481939509258,  # c#Staff Room
            740676328935653406,  # c#Bulletin
            761793288910143498,  # t#⚠️nsfw-bots
            780654704362389535,  # c#Upstairs
            852405741402062880,  # c#NReader
        ]

        self.ignored_roles = [
            789960054970515487,  # r@⛔Leveling Paused
            741431440490627234   # r@Muted
        ]

        self.no_cd_channels = [
            740663474568560671,  # c#SFW Catgirls
            740663386500628570   # c#NSFW Catgirls
        ]

        self.modifiers = {
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

    def exp_gain(self) -> float:
        # Base gain is 30, but let's throw in a gamble.
        whole = randint(20, 40)
        tenth_decimal = randint(0, 9) / 10
        return whole+tenth_decimal

    @command(name="leveling_help", aliases=["lvl_help"])
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def leveling_help(self, ctx, member: Member = None):
        await ctx.send(
            embed=Embed(
                title="Neko Heaven Leveling System",
                description="""
Dev Update:
New or returning user? A new, custom leveling system has been implemented into Kyaru.
You can find information further on in this embed. Kyaru will be speaking from here.
---

To begin leveling up, start chatting in some topical chats like <#741381152543211550>.
When you earn your first levelup, I will send you a message detailing what you earned, your new level, and how much exp you need until the next level.

**__Cumulative EXP__**
`CuEXP` is what is used to determine your level and ranking in the server.
You can earn CuEXP by chatting. The base CuEXP gain is around 20-40, but some channels and roles have modifiers. These "modify" the amount you earn.
You can only gain CuEXP once every minute, so spamming is pointless and will result in proper discipline.
**__Spending EXP__**
`SpEXP` is the currency of the server. It is accumulated at the same rate as CuEXP.
You can spend SpEXP in the <#870360906561904651>.

**__Commands:__**
__`rank/level [user]`__
Return this user's rank in Neko Heaven. Leave blank to return your own.

__`leadarboard/lead`__
Return the top 10 ranked users in Neko Heaven.

__`toggle_lowprofile_levelup/lp_levelup`__
Turn the levelup message into a set of reactions.
"""
            ))

    @command(name="purchase")
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def purchase_shop_item(self, ctx, *, item_name):
        shop_channel = self.bot.get_channel(870360906561904651)
        
        spending_exp_copy = deepcopy(self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["Spending EXP"])
        if not item_name in self.storefront:
            await ctx.send(content=ctx.author.mention, embed=Embed(color=0xff0000, description="That item does not exist.\nNote: Item names are case sensitive."))
            return

        if spending_exp_copy < self.storefront[item_name]:
            await ctx.send(content=ctx.author.mention, embed=Embed(color=0xff0000, description="You do not have enough Spending EXP to purchase that."))
            return

        self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["inventory"].append(item_name)
        self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["Spending EXP"] -= self.storefront[item_name]
        await ctx.send(content=ctx.author.mention, embed=Embed(description=f"Purchased `{item_name}`.\nIt has been added to your inventory."))

    @command(name="use")
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def use_shop_item(self, ctx, *, item_name):
        if item_name not in self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["inventory"]:
            await ctx.send(content=ctx.author.mention, embed=Embed(color=0xff0000, description="That item is not in your inventory.\nNote: Item names are case sensitive."))
            return

        if item_name in self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["inventory"] and item_name not in self.storefront:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["inventory"].remove(item_name)
            await ctx.send(content=ctx.author.mention, embed=Embed(color=0xff0000, description="That item is depreciated and has been removed from your inventory."))
            return
        
        if item_name == "Cumulative EXP Booster +0.5x 20m":
            if ctx.author.id in self.bot.timed_shop_items["modifiers"]:
                await ctx.send(
                    content=ctx.author.mention, 
                    embed=Embed(
                        color=0xff0000, 
                        description="You already have an EXP boost active! You will get a DM when it expires."
                                    f"If you wish to cancel it, type `k-cancel_boost` anywhere I can see you."))
                return

            self.bot.timed_shop_items["modifiers"].append(ctx.author.id)
            self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["personal_modifier"] += 0.50
            await ctx.send(content=ctx.author.mention, embed=Embed(description="Used `Cumulative EXP Booster +0.5x 20m`. Enjoy your EXP boost!"))
            
            try: m = await self.bot.wait_for("message", timeout=1200, check=lambda m: m.author.id==ctx.author.id and m.content=="k-cancel_boost")
            except TimeoutError:
                self.bot.timed_shop_items["modifiers"].remove(ctx.author.id)
                self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["personal_modifier"] -= 0.50
                await ctx.author.send(embed=Embed(color=0xffbf00, description="Your `Cumulative EXP Booster +0.5x 20m` has expired."))
                return
            else: 
                self.bot.timed_shop_items["modifiers"].remove(ctx.author.id)
                self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["personal_modifier"] -= 0.50
                await m.channel.send(embed=Embed(description="Canceled `Cumulative EXP Booster +0.5x 20m`."))
                return
            

        elif item_name == "Cumulative EXP Booster +1.0x 20m":
            if ctx.author.id in self.bot.timed_shop_items["modifiers"]:
                await ctx.send(
                    content=ctx.author.mention, 
                    embed=Embed(
                        color=0xff0000, 
                        description="You already have an EXP boost active! You will get a DM when it expires."
                                    f"If you wish to cancel it, type `k-cancel_boost` anywhere I can see you."))
                return

            self.bot.timed_shop_items["modifiers"].append(ctx.author.id)
            self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["personal_modifier"] += 1.00
            await ctx.send(content=ctx.author.mention, embed=Embed(description="Used `Cumulative EXP Booster +1.0x 20m`. Enjoy your EXP boost!"))
            
            try: m = await self.bot.wait_for("message", timeout=1200, check=lambda m: m.author.id==ctx.author.id and m.content=="k-cancel_boost")
            except TimeoutError:
                self.bot.timed_shop_items["modifiers"].remove(ctx.author.id)
                self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["personal_modifier"] -= 1.00
                await ctx.author.send(content=ctx.author.mention, embed=Embed(color=0xffbf00, description="Your `Cumulative EXP Booster +1.0x 20m` has expired."))
                return
            else: 
                self.bot.timed_shop_items["modifiers"].remove(ctx.author.id)
                self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["personal_modifier"] -= 1.00
                await m.channel.send(content=ctx.author.mention, embed=Embed(description="Canceled `Cumulative EXP Booster +1.0x 20m`."))
                return

        elif item_name == "Cumulative EXP Booster +2.0x 30m":
            if ctx.author.id in self.bot.timed_shop_items["modifiers"]:
                await ctx.send(
                    content=ctx.author.mention, 
                    embed=Embed(
                        color=0xff0000, 
                        description="You already have an EXP boost active! You will get a DM when it expires."
                                    f"If you wish to cancel it, type `k-cancel_boost` anywhere I can see you."))
                return

            self.bot.timed_shop_items["modifiers"].append(ctx.author.id)
            self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["personal_modifier"] += 2.00
            await ctx.send(content=ctx.author.mention, embed=Embed(description="Used `Cumulative EXP Booster +2.0x 30m`. Enjoy your EXP boost!"))

            try: m = await self.bot.wait_for("message", timeout=1800, check=lambda m: m.author.id==ctx.author.id and m.content=="k-cancel_boost")
            except TimeoutError:
                self.bot.timed_shop_items["modifiers"].remove(ctx.author.id)
                self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["personal_modifier"] -= 2.00
                await ctx.author.send(content=ctx.author.mention, embed=Embed(color=0xffbf00, description="Your `Cumulative EXP Booster +2.0x 30m` has expired."))
                return
            else: 
                self.bot.timed_shop_items["modifiers"].remove(ctx.author.id)
                self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["personal_modifier"] -= 2.00
                await m.channel.send(content=ctx.author.mention, embed=Embed(description="Canceled `Cumulative EXP Booster +2.0x 30m`."))
                return

        elif item_name == "Temporary Mute 5m":
            if ctx.author.id in self.bot.timed_shop_items["temp_mutes"]:
                await ctx.send(content=ctx.author.mention, 
                    embed=Embed(
                        color=0xff0000, 
                        description="To prevent abuse, you cannot use multiple mutes at once.\n"
                                    "If you wish to cancel it, type `k-cancel_mute` anywhere I can see you."))
                return

            await ctx.send(f"{ctx.author.mention}", embed=Embed(description="This shop item is used in a DM. Please check it."))
            conf = await ctx.author.send(embed=Embed(description="Mention the user (or type/paste UID) you want to temporarily mute for 5 minutes, or type `k-cancel` to cancel"))

            while True:
                try: 
                    m = await self.bot.wait_for("message", timeout=30, check=lambda m: m.author.id==ctx.author.id and m.channel.id==conf.channel.id)
                
                except TimeoutError: 
                    await conf.delete()
                    return

                else:
                    if m.content == "k-cancel": 
                        await ctx.author.send(embed=Embed(description="Operation cancelled."))
                        return

                    uid = re.search(r"[0-9]{17}[0-9]*", m.content)
                    if uid: uid = uid.group()
                    else: continue
                    
                    member = ctx.guild.get_member(int(uid))
                    if member: 
                        break

                    try: member = ctx.guild.fetch_member(int(uid))
                    except NotFound: 
                        continue
                    else:
                        break

            if 741431440490627234 in [role.id for role in member.roles]:
                await ctx.author.send(embed=Embed(color=0xff0000, description="That member is already muted.\nOperation cancelled."))
                return
            
            if 767792345239519254 in [role.id for role in member.roles] or \
                740680553195372554 in [role.id for role in member.roles]:
                await ctx.author.send(embed=Embed(color=0xff0000, description="Seriously?\nOperation cancelled."))
                return

            muted = ctx.guild.get_role(741431440490627234)
            
            self.bot.timed_shop_items["temp_mutes"].update({ctx.author.id: member.id})
            await member.add_roles(muted)
            await ctx.author.send(content=ctx.author.mention, embed=Embed(description=f"Muted {member} for 5 minutes."))
            await member.send(f"You've been muted by {ctx.author.mention} in Neko Heaven for 5 minutes.\n"
                              f"This was done via a shop item used by the member.")
            
            try: m = await self.bot.wait_for("message", timeout=300, check=lambda m: m.author.id==ctx.author.id and m.content=="k-cancel_mute")
            except TimeoutError:
                self.bot.timed_shop_items["temp_mutes"].pop(ctx.author.id)
                await member.remove_roles(muted)
                await ctx.author.send(content=ctx.author.mention, embed=Embed(color=0xffbf00, description="Your `Temporary Mute 5m` has expired."))
                await member.send("Your mute has ended.")
            else: 
                self.bot.timed_shop_items["temp_mutes"].pop(ctx.author.id)
                await member.remove_roles(muted)
                await m.channel.send(content=ctx.author.mention, embed=Embed(description="Canceled `Temporary Mute 5m`."))
                await member.send("Your mute has ended early.")
            
        else:
            await ctx.send(content=ctx.author.mention, embed=Embed(description="That item doesn't have a use yet."))
            return

        self.bot.user_data["UserData"][str(ctx.author.id)]["Leveling"]["inventory"].remove(item_name)

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
        else: remaining_exp_to_next = round(remaining_exp_to_next, 1)
        if obtained_exp_to_next%1 == 0: obtained_exp_to_next = int(obtained_exp_to_next)
        else: obtained_exp_to_next = round(obtained_exp_to_next, 1)
        if full_cumulative_exp%1 == 0: full_cumulative_exp = int(full_cumulative_exp)
        else: full_cumulative_exp = round(full_cumulative_exp, 1)
        if full_spending_exp%1 == 0: full_spending_exp = int(full_spending_exp)
        else: full_spending_exp = round(full_spending_exp, 1)

        if member.id == ctx.author.id:
            await ctx.send(embed=Embed(
                title="Neko Heaven Rank",
                description=f"You are currently level {current_level} ({obtained_exp_to_next}/{total_exp_to_next}).\n"
                            f"You are {remaining_exp_to_next} EXP away from your next level.\n"
                            f"\n"
                            f"Current Spending EXP: 💳 {full_spending_exp}\n"
                            f"Total Cumulative EXP: 🐾 {full_cumulative_exp}"
            ))
        else:
            await ctx.send(embed=Embed(
                title="Neko Heaven Rank",
                description=f"{member.mention} is currently level {current_level} ({obtained_exp_to_next}/{total_exp_to_next}).\n"
                            f"They are {remaining_exp_to_next} EXP away from their next level.\n"
                            f"\n"
                            f"Current Spending EXP: 💳 {full_spending_exp}\n"
                            f"Total Cumulative EXP: 🐾 {full_cumulative_exp}"
            ))

    @command(name="leaderboard", aliases=["lead"])
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def leaderboard(self, ctx):
        users = [(uid, self.bot.user_data["UserData"][uid]["Leveling"]["Cumulative EXP"]) for uid in self.bot.user_data["UserData"]]
        users.sort(key=lambda i: i[1])
        users = users[-10:len(users)]
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
            else: remaining_exp_to_next = round(remaining_exp_to_next, 1)
            if obtained_exp_to_next%1 == 0: obtained_exp_to_next = int(obtained_exp_to_next)
            else: obtained_exp_to_next = round(obtained_exp_to_next, 1)
            if full_cumulative_exp%1 == 0: full_cumulative_exp = int(full_cumulative_exp)
            else: full_cumulative_exp = round(full_cumulative_exp, 1)
            if full_spending_exp%1 == 0: full_spending_exp = int(full_spending_exp)
            else: full_spending_exp = round(full_spending_exp, 1)

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
            description=f"Here are the top 10 ranked users for this server:\n"
                        f"----------\n"
        ).add_field(
            name="**1-5**",
            inline=True,
            value=newline.join(member_rank_list[0:5])
        ).add_field(
            name="**6-10**",
            inline=True,
            value=newline.join(member_rank_list[5:10])
        ))

    @command(aliases=["setlevel", "setrank", "sl", "sr"])
    @has_permissions(administrator=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def set_level(self, ctx, member, level=None):
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

    @command(name="setcumulative", aliases=["setexp"])
    @has_permissions(administrator=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def set_cumulative_exp(self, ctx, member, amount=None):
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

        self.bot.user_data["UserData"][str(member.id)]["Leveling"]["Cumulative EXP"] = amount

        await ctx.send(embed=Embed(
            title="Set Spending",
            description=f"✅ Set {member.mention}'s Cumulative EXP to {amount}."))

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

        await ctx.send(embed=Embed(
            description=f"✅ Low Profile Levelup is now `{'On' if self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['lp_levelup'] else 'Off'}`."))

    @Cog.listener()
    async def on_message(self, msg):
        if msg.channel.id == 870360906561904651:
            if msg.author.id == self.bot.user.id:
                await sleep(5)
                await msg.delete()
            else:
                await msg.delete()

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

        if msg.guild and msg.guild.id == 740662779106689055:
            rewards = self.rewards
            ignored_channels = self.ignored_channels
            ignored_roles = self.ignored_roles
            no_cd_channels = self.no_cd_channels
            modifiers = self.modifiers

            def calculate_earnings():
                if not ((msg.channel.id in no_cd_channels) or \
                    (msg.channel.category and msg.channel.category.id in no_cd_channels)):
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

                total = (((((self.exp_gain())*modifier_1)*modifier_2)*modifier_3)*last_modifier)
                if not total:
                    self.exp_cooldown.pop(msg.author.id)

                return total

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
                else: remaining_exp_to_next = round(remaining_exp_to_next, 1)
                if obtained_exp_to_next%1 == 0: obtained_exp_to_next = int(obtained_exp_to_next)
                else: obtained_exp_to_next = round(obtained_exp_to_next, 1)
                if full_cumulative_exp%1 == 0: full_cumulative_exp = int(full_cumulative_exp)
                else: full_cumulative_exp = round(full_cumulative_exp, 1)
                if full_spending_exp%1 == 0: full_spending_exp = int(full_spending_exp)
                else: full_spending_exp = round(full_spending_exp, 1)
                
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

                if self.bot.user_data["UserData"][str(msg.author.id)]["Settings"]["lp_levelup"] or \
                    msg.channel.category.id in [740663474568560671, 740663386500628570, 871483997786607636]:  # Media categories
                    num_to_emoji = {1:"1️⃣", 2:"2️⃣", 3:"3️⃣", 4:"4️⃣", 5:"5️⃣", 6:"6️⃣", 7:"7️⃣", 8:"8️⃣", 9:"9️⃣", 0:"0️⃣"}
                    with suppress(NotFound):
                        await msg.add_reaction(self.bot.get_emoji(870143948750979072))
                        await sleep(2)
                        for number in str(new_level):
                            await msg.add_reaction(num_to_emoji[int(number)])

                        await sleep(3)
                        await msg.clear_reactions()

                    return

                else:
                    if new_level in rewards:
                        reward = msg.guild.get_role(rewards[new_level])
                        if not reward: 
                            try: reward = await msg.guild.fetch_role(rewards[new_level])
                            except NotFound: reward = None
                    else:
                        reward = None

                    if not self.bot.user_data["UserData"][str(msg.author.id)]["Settings"]["NotificationsDue"]["LevelupMinimizeTip"]:
                        await msg.channel.send(content=msg.author.mention, embed=Embed(
                            description=f"You've leveled up! Thanks for spending your time with us.\n"
                                        f"You are now level {new_level}! Have a headpat.\n"
                                        f"{'You earned the '+role.mention+' role!'+newline if reward else ''}"
                                        f"\n"
                                        f"Current Spending EXP: 💳 {full_spending_exp}\n"
                                        f"Total Cumulative EXP: 🐾 {full_cumulative_exp}\n"
                                        f"*Tip: You can hide this message in the future by going to <#740671751293501592> and typing `k!lp_levelup`.*"
                            ).set_footer(text=f"You are {remaining_exp_to_next} EXP away from the next level."
                            ).set_image(url=choice(level_up_gifs)))

                        self.bot.user_data["UserData"][str(msg.author.id)]["Settings"]["NotificationsDue"]["LevelupMinimizeTip"] = True
                    else:
                        await msg.channel.send(content=msg.author.mention, embed=Embed(
                            description=f"You've leveled up! Thanks for spending your time with us.\n"
                                        f"You are now level {new_level}! Have a headpat.\n"
                                        f"{'You earned the '+role.mention+' role!'+newline if reward else ''}"
                                        f"\n"
                                        f"Current Spending EXP: 💳 {full_spending_exp}\n"
                                        f"Total Cumulative EXP: 🐾 {full_cumulative_exp}\n"
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
    bot.add_cog(Leveling(bot))
