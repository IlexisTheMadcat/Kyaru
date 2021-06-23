import os
from io import BytesIO
from requests import post
from random import randint, choice
from urllib.request import urlretrieve as udownload
from asyncio import TimeoutError
from copy import deepcopy

from nudenet import NudeDetector
from PIL import Image, ImageDraw
from discord import Member, File
from discord.errors import NotFound
from discord.ext.commands import cooldown, BucketType, is_owner
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.core import (
    bot_has_permissions, 
    has_permissions, 
    command
)

from utils.classes import Embed

newline = "\n"

class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(aliases=["av"])
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def avatar(self, ctx: Context, userID=None):
        """Get the avatar of a user."""
        if userID:
            try: int(userID)
            except ValueError: return await ctx.send("`userID` must be a number.")

            try: user = await self.bot.fetch_user(userID)
            except NotFound: return await ctx.send("❌ No user with that ID exists.")
            
            await ctx.send(embed=Embed(
                title=f"{user}'s Avatar",
            ).set_image(url=user.avatar_url))
            
        if not userID:
            await ctx.send(embed=Embed(
                title="Your Avatar",
            ).set_image(url=ctx.author.avatar_url))
    
    @command(aliases=["auto_emb"])
    @bot_has_permissions(send_messages=True)
    async def toggle_auto_embed(self, ctx):
        if not str(ctx.author.id) in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(ctx.author.id)] = {}
        if not "Settings" in self.bot.user_data["UserData"][str(ctx.author.id)]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"] = {}
        if not "auto_embed" in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["auto_embed"] = False

        self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["auto_embed"] = \
            not self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["auto_embed"]

        await ctx.send(f'Toggled Auto-embed for you. It should now be set to {self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["auto_embed"]}.')

    @command(aliases=["upscale"])
    @bot_has_permissions(send_messages=True)
    @cooldown(1, 10, BucketType.user)
    async def waifu2x(self, ctx, url=None):
        if ctx.message.attachments:
            if len(ctx.message.attachments) > 1:
                await ctx.send("Please only attach one image at a time.")
                return
            
            conf = await ctx.channel.send("<a:loading:813237675553062954> Please wait, waiting for Waifu2x to respond...")
            attach_data = await ctx.message.attachments[0].read()

            img = Image.open(BytesIO(attach_data)).convert("RGBA")
            img.save(f"Workspace/image_{ctx.message.id}.png")

            r = post(
                "https://api.deepai.org/api/waifu2x",
                files={'image': open(f"Workspace/image_{ctx.message.id}.png", "rb")},
                headers={'api-key': self.bot.auth["DeepAI_key"]})

            os.remove(f"Workspace/image_{ctx.message.id}.png")
        
        elif url:
            conf = await ctx.channel.send("<a:loading:813237675553062954> Please wait, waiting for Waifu2x to respond...")
            r = post(
                "https://api.deepai.org/api/waifu2x",
                data={'image': url},
                headers={'api-key': self.bot.auth["DeepAI_key"]})
        
        else:
            await ctx.send("You need to attach or link an image.")
            return
        
        try:
            result = udownload(r.json()["output_url"], filename=f"Workspace/image_{ctx.message.id}.png")
        except KeyError:
            await conf.edit(content="", embed=Embed(
                color=0xff0000,
                description=f"Waifu2x at DeepAI responded with an error:\n> {r.json()['err']}"
                ).set_footer(text="ERR."))
            return
        
        else:
            img = Image.open(result[0]).convert("RGBA")
            img.save(f"Workspace/image_{ctx.message.id}.png")

            channel = self.bot.get_channel(766506735107047426)
            host_msg = await channel.send(file=File(f"Workspace/image_{ctx.message.id}.png"))
            os.remove(f"Workspace/image_{ctx.message.id}.png")

            await conf.edit(content="", embed=Embed(
                ).set_image(url=host_msg.attachments[0].url
                ).set_footer(text="This image was redrawn by a computer.\nResults may vary from image to image."))
            return
    
    @command(aliases=["nsfw"])
    @has_permissions(send_messages=True, embed_links=True)
    async def detect_nsfw(self, ctx, url=None):
        if ctx.message.attachments:
            if len(ctx.message.attachments) > 1:
                await ctx.send("Please only attach one image at a time.")
                return
            
            conf = await ctx.channel.send("<a:loading:813237675553062954> Please wait, waiting for Nudity Detection API to respond...")
            attach_data = await ctx.message.attachments[0].read()

            img = Image.open(BytesIO(attach_data)).convert("RGBA")
            img.save(f"Workspace/image_{ctx.message.id}.png")

            r = post(
                "https://api.deepai.org/api/nsfw-detector",
                files={'image': open(f"Workspace/image_{ctx.message.id}.png", "rb")},
                headers={'api-key': self.bot.auth["DeepAI_key"]})
            
            os.remove(f"Workspace/image_{ctx.message.id}.png")
        
        elif url:
            conf = await ctx.channel.send("<a:loading:813237675553062954> Please wait, waiting for Nudity Detection API to respond...")
            r = post(
                "https://api.deepai.org/api/nsfw-detector",
                data={'image': url},
                headers={'api-key': self.bot.auth["DeepAI_key"]})
        
        else:
            await ctx.send("You need to attach or link an image.")
            return
        
        #return await ctx.send(r.json())

        try:
            await conf.edit(content="", embed=Embed(
                description=f"This image is estimated to be {round(r.json()['output']['nsfw_score']*100, 2)}% NSFW."
                ).set_footer(text="This test was done by a computer and may not be accurate."))
        except KeyError:
            await conf.edit(content="", embed=Embed(
                color=0xff0000,
                description=f"Nudity Detection API at DeepAI responded with an error:\n> {r.json()['err']}"
                ).set_footer(text="ERR."))
            return

    @command(aliases=["scan", "sn"])
    @has_permissions(send_messages=True, embed_links=True)
    async def scan_nsfw(self, ctx, url=None):
        if ctx.message.attachments:
            if len(ctx.message.attachments) > 1:
                await ctx.send("Please only attach one image at a time.")
                return
            
            conf = await ctx.channel.send("<a:loading:813237675553062954> Please wait, waiting for NudeNet to respond...")
            attach_data = await ctx.message.attachments[0].read()

            img = Image.open(BytesIO(attach_data)).convert("RGBA")
            
            width, height = img.size
            if (width > height and width > 800) or (height > width and height > 800):  
                # image size will be modified by API if not reduced

                if width > height and width > 800:  # image is Landscape
                    ratio = 800/width
                    new_height = int(height*ratio)

                    img = img.resize((800, new_height))

                elif height > width and height > 800: # image is Portrait
                    ratio = 800/height
                    new_width = int(width*ratio)

                    img = img.resize((new_width, 800))
            
            img.save(f"Workspace/image_{ctx.message.id}.png")

            detector = NudeDetector()
            detections = detector.detect(f"Workspace/image_{ctx.message.id}.png")
        
        else:
            await ctx.send("You need to attach an image.")
            return
        
        try:
            #rj = __import__("json").dumps(detections, indent=4)
            #await conf.edit(content=f"```json\n{rj}```")
            
            drawing_pad = Image.new("RGBA", img.size, (0,0,0,0))
            draw = ImageDraw.Draw(drawing_pad, "RGBA")
            
            names = []
            search_for = {
                "COVERED_BREAST_F": "Covered Female Breast",
                "EXPOSED_BREAST_F": "Exposed Female Breast",
                "COVERED_GENITALIA_F": "Covered Female Genitalia",
                "EXPOSED_GENITALIA_F": "Exposed Female Genitalia",
                "EXPOSED_GENITALIA_M": "Exposed Male Genitalia",
                "EXPOSED_ANUS": "Exposed Anus",
                "EXPOSED_BUTTOCKS": "Exposed Buttocks"
            }
            for ind, finding in enumerate(detections):
                if not finding["label"] in search_for:
                    continue 
                
                names.append(f"{ind+1} - {search_for[finding['label']]} | {round(finding['score']*100)}%")

                def lin_interp(color_from, color_to, proportion):
                    r = color_to[0]*proportion + color_from[0]*(1-proportion)
                    g = color_to[1]*proportion + color_from[1]*(1-proportion)
                    b = color_to[2]*proportion + color_from[2]*(1-proportion)
                    return (round(r),round(g),round(b))

                color = lin_interp((0,255,0), (255,0,0), finding['score'])
                
                draw.rectangle(finding['box'], fill=(color)+(50,))
                draw.rectangle(finding['box'], outline=(color)+(255,), width=3)

            img.paste(drawing_pad, (0,0), mask=drawing_pad)
            img.save(f"Workspace/image_{ctx.message.id}.png", format="png")
            image_server = self.bot.get_channel(789198608175202394)
            image_container = await image_server.send(file=File(f"Workspace/image_{ctx.message.id}.png"))
            os.remove(f"Workspace/image_{ctx.message.id}.png")
            image_url = image_container.attachments[0].url

            await conf.edit(content="", embed=Embed(
                description=f"__Detections:__\n"
                            f"{newline.join(names) if names else 'No detections.'}"
                ).set_footer(text="This test was done by a computer and may not be accurate."
                ).set_image(url=image_url))
        
        except Exception as e:
            await conf.edit(content="", embed=Embed(
                color=0xff0000,
                description=f"NudeNet responded with an error:\n> {type(e).__name__}: {e}"
                ).set_footer(text="ERR."))
            return

    @command()
    @has_permissions(manage_messages=True)
    async def welcome(self, ctx, member: Member, selection="0"):
        await ctx.message.delete()
        img = Image.open(BytesIO(await member.avatar_url_as(format='png').read())).convert("RGBA")

        image_choices = {
            '1':(106, 293),
            '2':(1103, 254),
            '3':(447, 386),
            '4':(1342, 451)
        }

        if selection == "0" or selection not in ["1","2","3","4"]:
            selection = str(randint(1,4))

        background = Image.open(f"Workspace/Files/user_joined_modal{'_gif' if member.is_avatar_animated() else ''}_{selection}.png", 'r')
        img = img.resize((500,500))
        background.paste(img, image_choices[selection], mask=img)
        background.save(f"Workspace/user_joined_{member.id}.png", format="png")

        image_server = self.bot.get_channel(789198608175202394)
        image_container = await image_server.send(file=File(f"Workspace/user_joined_{member.id}.png"))
        os.remove(f"Workspace/user_joined_{member.id}.png")
        image_url = image_container.attachments[0].url

        channel = ctx.channel
        emb = Embed(
            title=f"{member.name} just joined the server!",
        ).set_image(url=image_url)
        emb.set_footer(
            text=f"UID: {member.id}{'; Animated avatars are not supported, sowwy!' if member.is_avatar_animated() else ''}"
        )
        start_the_timer = await channel.send(content=f"Welcome {member.mention}! Have fun and stay safe!", embed=emb)

        self.bot.just_joined.append(member.id)
        try:
            member = await self.bot.wait_for("member_remove", timeout=120, check=lambda member2: member2.id == member.id)
        except TimeoutError:
            self.bot.just_joined.remove(member.id)
        else:
            await start_the_timer.delete()
        
    @command()
    async def nick(self, ctx, *, new_name=None):
        if ctx.channel.id != 740671751293501592:  #🤖bot-spam
            await ctx.message.delete()
            await ctx.author.send("That command cannot be used here.", delete_after=5)
            return
        
        if ctx.author.permissions_in(ctx.channel).manage_nicknames:
            await ctx.send("Change your own nickname. No need to rely on your peers.")
            return
        
        if ctx.author.nick == new_name or ctx.author.name == new_name:
            await ctx.send("You're kidding, right?")
            return

        conf = await ctx.author.send(
            "Your nickname for Neko Heaven was submitted.\n"
            "This message will be edited with the status.")
        
        await ctx.message.add_reaction("👌")
        
        requests = await self.bot.fetch_channel(835610993178181682)  #approve-nicknames
        emb = Embed(
            title=f"{ctx.author} ({ctx.author.id})",
            description=f"Approve nickname request:\n"
                        f"```diff\n"
                        f"- {ctx.author.nick if ctx.author.nick else '[No Nickname]'}\n"
                        f"+ {new_name if new_name else '[No Nickname]'}\n"
                        f"```")
        
        control = await requests.send(embed=emb)
        
        await control.add_reaction("✅")
        await control.add_reaction("❌")

        try:
            r, u = await self.bot.wait_for("reaction_add", timeout=60,
                check=lambda r,u: u.permissions_in(requests).manage_nicknames and \
                    r.message.id==control.id and not \
                    u.bot and \
                    str(r.emoji) in ["✅", "❌"])
        except TimeoutError:
            emb.title = f"{ctx.author} ({ctx.author.id}) **(Timed out)**"
            await control.edit(embed=emb)
            await conf.edit(content="The nickname request was not answered in time. Try again later.")
            return
        
        else:
            if str(r.emoji) == "✅":
                self.bot.pause_member_update.append(ctx.author.id)
                await ctx.author.edit(nick=new_name)
                self.bot.pause_member_update.remove(ctx.author.id)
                
                emb.set_footer(text=f"Approved by {u} ({u.id})")
                await control.edit(embed=emb)
                
                await ctx.message.add_reaction("✅")
                await conf.edit(content="Your nickname request was approved and changed accordingly.")
                return
            
            elif str(r.emoji) == "❌":
                emb.set_footer(text=f"Rejected by {u} ({u.id})")
                await control.edit(embed=emb)
                inq = await requests.send("[10s] Short reason?")

                try:
                    m = await self.bot.wait_for("message", timeout=10,
                        check=lambda m: m.author.permissions_in(requests).manage_nicknames and \
                        m.author.id==u.id and \
                        m.channel.id==control.channel.id)
                except TimeoutError:
                    reason = "None provided"
                else:
                    reason = m.content
                    await m.delete()
                
                await inq.delete()
                await conf.edit(content=f"Your nickname request was rejected.\nReason: `{reason}`")
                return
    
    # EVENT related commands.
    # Code that is related to an event is commented with "EVENT".
    @command()
    async def event_leaderboard(self, ctx, select="False"):
        rankings_part = []
        bucket = []
        for userID in self.bot.user_data["UserData"]:
            if userID == "authorID": continue  # Skip default value

            user = self.bot.get_user(int(userID))
            if user is None: user = await self.bot.fetch_user(int(userID))

            try:
                if self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"]:
                    rankings_part.append(f'{self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"]} points: {user.mention}')
                    bucket = bucket + [user.id]*self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"]
            except KeyError:
                continue
        
        if not rankings_part:
            rankings_part = ["No results to show yet."]
        
        if select.lower() == "select": #and not self.bot.config["event_ongoing"]:
            selected = self.bot.get_user(choice(bucket))
            await ctx.send(content=f"The selected member is: {selected.mention}")
            return
                
        await ctx.send(embed=Embed(
            title="Current Event Leaderboard" if self.bot.config["event_ongoing"] else "Last Event Leaderboard",
            description="\n".join(rankings_part)))
    
    @command()
    @has_permissions(administrator=True)
    async def points(self, ctx, UID, mode, value=0, *, reason="None provided."):
        if mode not in ["set", "add", "remove", "view"]:
            await ctx.send(f"Invalid mode `{mode}`. Valid modes are `view`, `set`, `add`, and `remove`.")
            return
        
        try:
            value = int(value)
            UID = int(UID)
        except ValueError:
            await ctx.send("`value` and `UID` must be numbers.")
            if UID.lower() != "all":
                return
            else:  
                # Change all participants' scores
                for userID in self.bot.user_data["GlobalEventData"]["participants"]:
                    if userID == "authorID": continue  # Skip default value

                    user = self.bot.get_user(int(userID))
                    if user is None: user = await self.bot.fetch_user(int(userID))
                    
                    if not str(user.id) in self.bot.user_data["UserData"]:
                        self.bot.user_data["UserData"][str(user.id)] = {}
                    if not "EventData" in self.bot.user_data["UserData"][str(user.id)]:
                        self.bot.user_data["UserData"][str(user.id)]["EventData"] = {}
                    if not "points" in self.bot.user_data["UserData"][str(user.id)]["EventData"]:
                        self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = 0

                    if mode == "set":
                        self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = value
                        await ctx.send(f"All participants now have `{value}` points.")
                
                        log_channel = await self.bot.fetch_channel(829564482833481778)
                        await log_channel.send(content=user.mention, embed=Embed(
                            color=0x0000ff,
                            description=f'All participants now have {value} points in total.\n'
                                        f'ー Reason for change: {reason}'))

                    elif mode == "add":
                        self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = \
                            self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] + value
                        await ctx.send(f"All participants have gained {value} points.")
                
                        log_channel = await self.bot.fetch_channel(829564482833481778)
                        await log_channel.send(content=user.mention, embed=Embed(
                            color=0x0000ff,
                            description=f'All participants have gained {value} points.\n'
                                        f'ー Reason for change: {reason}'))
                    
                    elif mode == "remove":
                        self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = \
                            self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] - value
                        await ctx.send(f"All participants have lost {value} points.")
                
                        log_channel = await self.bot.fetch_channel(829564482833481778)
                        await log_channel.send(content=user.mention, embed=Embed(
                            color=0x0000ff,
                            description=f'All participants have lost {value} points.\n'
                                        f'ー Reason for change: {reason}'))
                return
        
        # Change an individual's score. UID not equal to "all"
        try:
            user = await self.bot.fetch_user(UID)
        except NotFound:
            await ctx.send(f"User with the ID `{UID}` not found.")
            return
        
        if mode == "set":
            if not str(user.id) in self.bot.user_data["UserData"]:
                self.bot.user_data["UserData"][str(user.id)] = {}
            if not "EventData" in self.bot.user_data["UserData"][str(user.id)]:
                self.bot.user_data["UserData"][str(user.id)]["EventData"] = {}
            if not "points" in self.bot.user_data["UserData"][str(user.id)]["EventData"]:
                self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = 0

            original = deepcopy(self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"])
            self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = value

            await ctx.send(f"{user} now has `{value}` points. (Original value: `{original}` -> `{value}`)")
            
            log_channel = await self.bot.fetch_channel(829564482833481778)
            await log_channel.send(content=user.mention, embed=Embed(
                color=0x0000ff,
                description=f'{user} now has {value} points in total.\n'
                            f'ー Reason for change: {reason}'))

        elif mode == "add":
            if not str(user.id) in self.bot.user_data["UserData"]:
                self.bot.user_data["UserData"][str(user.id)] = {}
            if not "EventData" in self.bot.user_data["UserData"][str(user.id)]:
                self.bot.user_data["UserData"][str(user.id)]["EventData"] = {}
            if not "points" in self.bot.user_data["UserData"][str(user.id)]["EventData"]:
                self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = 0

            original = deepcopy(self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"])
            self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = \
                self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] + value
            
            points = self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"]
            await ctx.send(f"{user} now has `{points}` points. (Original value: `{original}` plus `{value}`)")

            log_channel = await self.bot.fetch_channel(829564482833481778)
            await log_channel.send(content=user.mention, embed=Embed(
                color=0x00ff00,
                description=f'{user} gained {value} points. '
                            f'They now have {self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"]} in total.\n'
                            f'ー Reason for change: {reason}'))
        
        elif mode == "remove":
            if not str(user.id) in self.bot.user_data["UserData"]:
                self.bot.user_data["UserData"][str(user.id)] = {}
            if not "EventData" in self.bot.user_data["UserData"][str(user.id)]:
                self.bot.user_data["UserData"][str(user.id)]["EventData"] = {}
            if not "points" in self.bot.user_data["UserData"][str(user.id)]["EventData"]:
                self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = 0

            original = deepcopy(self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"])
            self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = \
                self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] - value
            
            points = self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"]
            await ctx.send(f"{user} now has `{points}` points. (Original value: `{original}` minus `{value}`)")

            log_channel = await self.bot.fetch_channel(829564482833481778)
            await log_channel.send(content=user.mention, embed=Embed(
                color=0xff0000,
                description=f'{user} lost {value} points. '
                            f'They now have {self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"]} in total.\n'
                            f'ー Reason for change: {reason}'))

        elif mode == "view":
            if not str(user.id) in self.bot.user_data["UserData"]:
                self.bot.user_data["UserData"][str(user.id)] = {}
            if not "EventData" in self.bot.user_data["UserData"][str(user.id)]:
                self.bot.user_data["UserData"][str(user.id)]["EventData"] = {}
            if not "points" in self.bot.user_data["UserData"][str(user.id)]["EventData"]:
                self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"] = 0

            value = self.bot.user_data["UserData"][str(user.id)]["EventData"]["points"]

            await ctx.send(f"{user} has `{value}` points.")

def setup(bot):
    bot.add_cog(Commands(bot))
