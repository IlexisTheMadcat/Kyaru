# IMPORTS
import os
import re
from sys import exc_info
from requests import post
from random import randint
from io import BytesIO
from asyncio import TimeoutError
from contextlib import suppress
from asyncio import sleep
from copy import deepcopy
from urllib.request import urlretrieve as udownload

import aiohttp
from PIL import Image
from expiringdict import ExpiringDict
from discord import File, Member, Message, MessageType, utils
from discord.errors import Forbidden, NotFound, HTTPException
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.errors import (
    BotMissingPermissions,
    CommandOnCooldown,
    CommandNotFound,
    MissingPermissions,
    MissingRequiredArgument,
    NotOwner, BadArgument,
    CheckFailure
)
from discord_components import Button
from discord.ext.tasks import loop

from utils.classes import Embed

newline = "\n"


class Events(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.pause_member_update = []
        self.just_joined = ExpiringDict(
            max_len=float('inf'), 
            max_age_seconds=600),
        self.pause_member_update = []

        # List of Message to act on. Added to by on_message event after conditions are met.
        self.upscale_image_tasks = []  
        self.upscale_image_task.start()

    @loop(seconds=1)
    async def upscale_image_task(self):
        if not self.upscale_image_tasks: return
        else: msg = self.upscale_image_tasks[0]

        def finish():
            self.upscale_image_tasks.pop(0)

        try:
            await msg.channel.fetch_message(msg.id)
        except NotFound:
            return finish()

        # Start task process
        await msg.clear_reactions()
        await msg.channel.set_permissions(msg.author, send_messages=False)
                
        # Check image size due to Discord upload limitations.
        # Upscale will not be used in this case as the file will most likely be larger.
        async def file_too_large_prompt():
            with suppress(NotFound):
                await msg.delete()

            buffer_target = self.bot.get_channel(789190968267636768)
            await buffer_target.set_permissions(msg.author, read_messages=True)

            conf = await msg.channel.send(
                content=f"{msg.author.mention}, {buffer_target.mention}", 
                embed=Embed(
                    color=0xff0000,
                    description=f"Sorry for the inconvenience, please upload your image in the mentioned channel, it is too large for me to send!\n"
                                f"\n"
                                f"To cancel, send `k-cancel` in the buffer channel.\n"
                                f"{self.bot.get_emoji(813237675553062954)} Waiting... (120s)"))

            while True:
                try:
                    m = await self.bot.wait_for("message", timeout=120, check=lambda m: m.author.id == msg.author.id and m.channel.id == 789190968267636768)
                except TimeoutError:
                    await conf.delete()
                    await buffer_target.edit(overwrites=buffer_target.category.overwrites)
                        
                    if msg.channel.id != 777189629505699850:
                        await msg.channel.edit(overwrites=msg.channel.category.overwrites)
                        
                    return

                else:
                    if m.content == "k-cancel":
                        await buffer_target.send("Alright.", delete_after=2)
                        await sleep(2)
                        await buffer_target.edit(overwrites=buffer_target.category.overwrites)
                        if msg.channel.id != 777189629505699850:
                            await self.bot.fetch_channel(740663474568560671)

                            await msg.channel.edit(overwrites=category.overwrites)

                        await conf.delete()

                        return

                    if not m.attachments:
                        await buffer_target.send("Attach a file! Please try again.", delete_after=5)
                        continue
                        
                    await buffer_target.send("Thanks!", delete_after=2)
                    await sleep(2)
                    await buffer_target.edit(overwrites=buffer_target.category.overwrites)
                                
                    await conf.edit(content="", 
                        embed=Embed(
                            color=0x32d17f, 
                            description=f"Uploaded by {msg.author.mention}"
                                        f"{newline+'[' if msg.content else ''}{msg.content}{']' if msg.content else ''}"
                        ).set_image(url=m.attachments[0].url
                        ).set_footer(text=f"UID: {msg.author.id}"))

                    await conf.add_reaction("⬆")

                    if msg.channel.id != 777189629505699850:
                        category = await self.bot.fetch_channel(740663474568560671)

                        await msg.channel.edit(overwrites=category.overwrites)

                    return
                
        attach = msg.attachments[0]
        if attach.size >= 8000000:
            await file_too_large_prompt()
            return finish()

        conf = await msg.channel.send(
            embed=Embed(
                title="Upscaling For Quality",
                description=f"{self.bot.get_emoji(813237675553062954)} {msg.author.mention} Please wait..."))

        # Copy attachment
        dcfileobj = await attach.to_file()

        # Read attachment
        attach_data = await attach.read()
                
        # Check if it's a GIF
        img = Image.open(BytesIO(attach_data))
        try:
            img.seek(1)
        except EOFError:
            is_animated = False
        else:
            img.seek(0)
            is_animated = True
                
        if is_animated:  # Skip upscaling and use original attachment
            attachment_file = dcfileobj
            has_upscaled = False
                
        else:  # Continue with checks
                    
            width, height = img.size  # Store original size
                    
            # If smaller dimension is less than 300px, deny upload. 
            # Image will look distorted.
            if ((width > height and height < 300) or \
                (height >= width and width < 300)):
                await msg.delete()
                await conf.edit(
                    embed=Embed(
                        color=0xff0000,
                        description=f"❌ That image is too small! Please use [Google Images](https://images.google.com/) or [SauceNAO](https://saucenao.com) to check for a larger resolution."
                    ), delete_after=5)

                return finish()
                    
            # If smaller dimension is greater than 1000px, skip upscaling
            if ((width > height and height > 1000) or \
                (height >= width and width > 1000)):
                        
                attachment_file = dcfileobj
                has_upscaled = False

            else:  # Start upscale process
                        
                # Store previous dimensions after upscaling to keep track
                last_width, last_height = deepcopy(width), deepcopy(height)
                has_upscaled = True

                current_data = attach_data
                retries = 3
                # Loop until image is optimal size or exceeded tries
                while retries >= 0:

                    # Upload image
                    async with aiohttp.ClientSession() as cs:
                        data = aiohttp.FormData()
                        data.add_field(
                            'image', current_data,
                            filename=f'image_{msg.id}.jpg',
                            content_type='multipart/form-data')

                        r = await cs.post(
                            "https://api.deepai.org/api/waifu2x",
                            data=data, headers={'api-key': self.bot.auth["DeepAI_key"]}
                        )

                        r.json = await r.json()
                            
                    try:
                        result = udownload(r.json["output_url"])
                    except KeyError:
                        with suppress(NotFound):
                            await msg.delete()

                        await conf.edit(
                            embed=Embed(
                                color=0xff0000,
                                description=f"❌ Upscale failed! Please choose a different image, or try [Google Images](https://images.google.com/) or [SauceNAO](https://saucenao.com) to check for a larger resolution.\n"
                                            f"`{r.json['err']}`"
                            ), delete_after=5)

                        if msg.channel.id != 777189629505699850:
                            category = await self.bot.fetch_channel(740663474568560671)

                            await msg.channel.edit(overwrites=category.overwrites)

                        return finish()
                            
                    else:
                        # Open returned image and check results
                        img = Image.open(result[0])
                        new_width, new_height = img.size

                        # Image is optimal or cannot be upscaled further
                        # as per previous dimension values
                        if ((width > height and height > 1000) or \
                            (height >= width and width > 1000)) and \
                            (width != last_width and height != last_height):

                            break
                                
                        # Image is not optimal, try upscaling again
                        else:
                            last_width, last_height = new_width, new_height
                            current_data = open(result[0], "rb")
                            await sleep(0.5)

                            retries = retries - 1
                            continue
                        
                if retries == 0:
                    await conf.edit(
                        embed=Embed(
                            color=0xff0000,
                            description=f"❌ Upscale failed! Please choose a different image or try google images for a larger resolution.\n"
                                        f"Error details: `Retries exhausted. Will not continue.`"
                        ), delete_after=5)
                    
                    return finish()

                # Upscaled image is final and ready to send
                attachment_file = File(result[0], filename=f"{msg.id}.png")
                
        # Forget posting if user already deleted message
        try:
            await msg.channel.fetch_message(msg.id)
        except NotFound:
            if msg.channel.id != 777189629505699850:
                category = await self.bot.fetch_channel(740663474568560671)

                await msg.channel.edit(overwrites=category.overwrites)

            await conf.edit( 
                embed=Embed(
                    description="❌ Operation cancelled."
            ), delete_after=2)

        else:
            buffer_target = self.bot.get_channel(789198608175202394)
            buffer_msg = await buffer_target.send(file=attachment_file)

            await msg.delete()
            
            await conf.edit(content="", 
                embed=Embed(
                    color=0x32d17f, 
                    description=f"Uploaded by {msg.author.mention}{'; Upscaled with Waifu2x.' if has_upscaled else ''}"
                                f"{newline+'[' if msg.content else ''}{msg.content}{']' if msg.content else ''}"
                    ).set_image(url=buffer_msg.attachments[0].url
                    ).set_footer(text=f"UID: {msg.author.id}"))

            await conf.add_reaction("⬆")
                
            if msg.channel.id != 777189629505699850:
                if msg.channel.is_nsfw():
                    category = await self.bot.fetch_channel(740663474568560671)

                await msg.channel.edit(overwrites=category.overwrites)

        return finish()

    async def confirm_pfp(self, member):
        user = await self.bot.fetch_user(member.id)
        guild = member.guild
        pfps = self.bot.get_channel(862146341538627604)
                
        if 767792345239519254 in [role.id for role in member.roles]:
            return True

        r = post(
            "https://api.deepai.org/api/nsfw-detector",
            data={'image': str(user.avatar_url)},
            headers={'api-key': self.bot.auth["DeepAI_key"]})
            
        if 'output' in r.json() and r.json()['output']['nsfw_score'] > 0.7:
            muted_role = utils.get(member.guild.roles, id=741431440490627234)
            await member.add_roles(muted_role)
        
            emb = Embed(
                title=f"{member} ({member.id})",
                description="Approve suspicious profile picture:"
            ).set_image(url=user.avatar_url)

            control = await pfps.send(embed=emb, 
                components=[
                    [Button(emoji="✅", style=2, id="allow", label="Allow"),
                    Button(emoji="❌", style=1, id="ban", label="Ban")]
                ])

            while True:
                try:
                    interaction = await self.bot.wait_for("button_click", timeout=600, 
                        check=lambda i: 767792345239519254 in [role.id for role in i.user.roles] and i.message.id==control.id)
                except TimeoutError:
                    emb.set_footer(text="❌ Timed out; User was banned automatically.")
                    await control.edit(embed=emb)

                    with suppress(Exception):
                        await member.send(embed=Embed(
                            color=0xFFBF00,
                            title="Warning",
                            description="I've used a computer algorithm to determine that your profile picture is considered NSFW and against Discord's Terms of Service.\n"
                                        "\n"
                                        "❌No mod was available to declare the safety of your profile picture.\n"
                                        "I cannot accept the risk of letting you stay for now.\n"
                                        "\n"
                                        "Due to this, you've been automatically soft-banned from Neko Heaven following server rules. If you believe this was in error, "
                                        "please join the appeal server [here](https://discord.gg/3RYGFrbsuJ) to discuss the situation.\n"
                                        "\n"
                                        "The below image is what was scanned for infringement."
                            ).set_image(url=str(user.avatar_url)
                            ).set_footer(text="This test was done by a computer and may not be accurate."))

                    await guild.ban(member, reason="Auto-banned for NSFW profile picture.")
                    return False
        
                else:
                    try: await interaction.respond(type=6)
                    except Exception: continue

                    if interaction.component.id == "allow":
                        emb.set_footer(text=f"✅ Approved: {interaction.user} ({interaction.user.id})")
                        await control.edit(embed=emb, components=[])

                        await member.remove_roles(muted_role)
                        return True
            
                    elif interaction.component.id == "ban":
                    
                        emb.set_footer(text=f"❌ Rejected: {interaction.user} ({interaction.user.id})\n📄 Reason: [TBD]")
                        await control.edit(embed=emb, components=[])   
                    
                        inq = await pfps.send(embed=Embed(
                            description="Please type your reason within 2 minutes.\n"
                                        "Send `skip` to leave blank.\n"
                                        "Send `nvm` to cancel and approve."))

                        try:
                            m = await self.bot.wait_for("message", timeout=120,
                                check=lambda m: 767792345239519254 in [role.id for role in m.author.roles] and \
                                    m.author.id==interaction.user.id and m.channel.id==control.channel.id)
                        except TimeoutError:
                            await inq.delete()
                            reason = "None provided"
                        else:
                            await m.delete()
                            await inq.delete()

                            if m.content in ["nvm", "Nvm", "NVM"]:
                                emb.set_footer(text=f"✅ Approved: {interaction.user} ({interaction.user.id})")
                                await control.edit(embed=emb, components=[])

                                await member.remove_roles(muted_role)
                                return True

                            elif m.content in ["skip", "Skip", "SKIP"]:
                                reason = "None provided"
                            else:
                                reason = m.content

                        emb.set_footer(text=f"❌ Rejected: {interaction.user} ({interaction.user.id})\n📄 Reason: {reason}")
                        await control.edit(embed=emb, components=[])   
         
                        with suppress(Exception):
                            await member.send(embed=Embed(
                                color=0xFFBF00,
                                title="Warning",
                                description=f"I've used a computer algorithm to determine that your profile picture is considered NSFW and against Discord's Terms of Service.\n"
                                            f"\n"
                                            f"Moderator's reason: `{reason}`\n"
                                            f"\n"
                                            "Due to this, you've been banned from Neko Heaven following server rules. If you believe this was in error, "
                                            f"please join the appeal server [here](https://discord.gg/3RYGFrbsuJ) to discuss the situation.\n"
                                            f"\n"
                                            f"The below image is what was scanned for infringement."
                                ).set_image(url=str(user.avatar_url)
                                ).set_footer(text="This test was done by a computer and may not be accurate."))

                        await guild.ban(member, reason="Moderator approved ban for NSFW profile picture.")
                        return False

        else:
            return True

    # Message events
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_message(self, msg: Message):
        # Cooldown
        if msg.author.id in self.bot.global_cooldown: return
        else: self.bot.global_cooldown.update({msg.author.id:"placeholder"})

        if msg.type == MessageType.premium_guild_subscription:
            if not self.bot.user_data["UserData"][str(msg.author.id)]["has_boosted"]:
                await msg.channel.send(
                    content=msg.author.mention,
                    embed=Embed(
                        title="Thanks For Boosting!",
                        description="Nitro boosters gain a small experience boost that lasts as long as they're a booster. "
                                    "Thanks for your patronage! Here's 💳`5000` Spending EXP and a free PREMIUM headpat!",
                    color=0xff73fa
                ).set_image(
                    url="https://i.giphy.com/l3vRd6owAhtbFIb16.gif"
                ))

                self.bot.user_data["UserData"][str(msg.author.id)]["Leveling"]["Spending EXP"] += 5000
                self.bot.user_data["UserData"][str(msg.author.id)]["has_boosted"] = True

                return
        
        # Don't respond to bots.
        if msg.author.bot:
            if msg.author.id != 742517626785497168:
                category = self.bot.get_channel(740663474568560671)
                if msg.channel.id in [channel.id for channel in category.channels]:
                    await msg.delete()

            else:
                return

        # For this bot, user data is generated on member join.
        # Checks if the message is any attempted command.
        if msg.content.startswith(self.bot.command_prefix) and not msg.content.startswith(self.bot.command_prefix+" "):  
            self.bot.inactive = 0
            await self.bot.process_commands(msg)
            return

        # Upload images only in these channels
        if msg.guild and msg.channel.id in \
            [815027417399558154, 870342656314736720, 866172671544524830]:
            if not msg.attachments:
                find_url = re.findall(r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))""", msg.content)
                if find_url:
                    if len(find_url) > 1:
                        await msg.delete()
                        await msg.channel.send(content=msg.author.mention, embed=Embed(
                            title="One Image URL",
                            description="While you can attach as many images you want here, please only send a link to one at a time.",
                        ), delete_after=5)

                        await msg.channel.set_permissions(msg.author, send_messages=False)
                        await sleep(5)
                        category = await self.bot.fetch_channel(740663474568560671)

                        await msg.channel.edit(overwrites=category.overwrites)

                    elif len(find_url) == 1:
                        await msg.delete()
                        if not find_url[0].endswith((".jpg", ".jpeg", ".png", ".gif", ".mp4")):
                            await msg.delete()
                            await msg.channel.send(content=msg.author.mention, embed=Embed(
                                title="Extension Not Allowed",
                                description="URLs must end in any of the following: [.jpg, .jpeg, .png, .gif, .mp4]",
                            ), delete_after=5)

                        await msg.channel.set_permissions(msg.author, send_messages=False)
                        await sleep(5)
                        category = await self.bot.fetch_channel(740663474568560671)

                        await msg.channel.edit(overwrites=category.overwrites)

                else:
                    await msg.delete()
                    await msg.channel.send(content=msg.author.mention, embed=Embed(
                        title="Images only",
                        description="You can only upload images or image URLS in this channel.\n"
                                    "You can comment on images by sending its **message** URL in <#742571100009136148>"
                        ), delete_after=5)

                    await msg.channel.set_permissions(msg.author, send_messages=False)
                    await sleep(5)
                    category = await self.bot.fetch_channel(740663474568560671)

                    await msg.channel.edit(overwrites=category.overwrites)
            
            else:
                for i in msg.attachments:
                    if not str(i.url).endswith((".jpg", ".jpeg", ".png", ".gif", ".mp4")):
                        await msg.delete()
                        await msg.channel.send(content=msg.author.mention, embed=Embed(
                            title="Extension Not Allowed",
                            description="Your file names must end in any of the following: [.jpg, .jpeg, .png, .gif, .mp4]",
                        ), delete_after=5)

                    await msg.channel.set_permissions(msg.author, send_messages=False)
                    await sleep(5)
                    category = await self.bot.fetch_channel(740663474568560671)

                    await msg.channel.edit(overwrites=category.overwrites)
                    break
            
            return

        # Upload videos only in these channels
        if msg.guild and msg.channel.id in \
            [906587188718866474]:
            if not msg.attachments:
                await msg.delete()
                await msg.channel.send(content=msg.author.mention, embed=Embed(
                    title="Videos only",
                    description="You can only upload videos in this channel.\n"
                                "You can comment on videos by sending its **message** URL in <#742571100009136148>"
                    ), delete_after=5)

                await msg.channel.set_permissions(msg.author, send_messages=False)
                await sleep(5)
                category = await self.bot.fetch_channel(740663474568560671)

                await msg.channel.edit(overwrites=category.overwrites)
            
            else:
                for i in msg.attachments:
                    if not str(i.url).endswith((".mp4", ".mov", ".webm")):
                        await msg.delete()
                        await msg.channel.send(content=msg.author.mention, embed=Embed(
                            title="Extension Not Allowed",
                            description="Your file names must end in any of the following: [.mp4, .mov, .webm]",
                        ), delete_after=5)

                    await msg.channel.set_permissions(msg.author, send_messages=False)
                    await sleep(5)
                    category = await self.bot.fetch_channel(740663474568560671)

                    await msg.channel.edit(overwrites=category.overwrites)
                    break
            
            return

        # Upscale media uploads in these categories
        if msg.guild and msg.channel.category and msg.channel.category.id == 740663474568560671 and \
            msg.channel.id not in [
                890646250553245726,  # Dividers
                890646335781482517, 
                890646878302126120,
                815027417399558154,  # Other channels
                870342656314736720, 
                866172671544524830,
                740725402506494072,  # image-help
                742571100009136148,  # image-comments
            ]:
            if not msg.attachments:
                await msg.delete()
                await msg.channel.send(content=msg.author.mention, embed=Embed(
                    title="Images only",
                    description="You can only upload images in this channel.\n"
                                "You can comment on images by sending its **message** URL in <#742571100009136148>"
                    ), delete_after=5)

                await msg.channel.set_permissions(msg.author, send_messages=False)
                await sleep(5)
                category = await self.bot.fetch_channel(740663474568560671)

                await msg.channel.edit(overwrites=category.overwrites)
                return

            if len(msg.attachments) > 1:
                await msg.delete()
                await msg.channel.send(
                    content=msg.author.mention,
                    embed=Embed(
                        title="Media", 
                        description="Please send one attachment at a time.",
                        color=0x32d17f),
                    delete_after=5)
            
            if not str(msg.attachments[0].url).endswith((".jpg", ".jpeg", ".png", ".gif")):
                await msg.delete()
                await msg.channel.send(content=msg.author.mention, embed=Embed(
                    title="Extension Not Allowed",
                    description="Your file names must end in any of the following: [.jpg, .jpeg, .png, .gif]",
                ), delete_after=5)
                
                await msg.channel.set_permissions(msg.author, send_messages=False)
                await sleep(5)
                category = await self.bot.fetch_channel(897696876319625286)

                await msg.channel.edit(overwrites=category.overwrites)

            else:
                if self.upscale_image_tasks:
                    await msg.add_reaction(self.bot.get_emoji(813237675553062954))
                self.upscale_image_tasks.append(msg)
            
            return

        # Search for message links and reformat.
        link_findings = re.findall("https://(?:discord|discordapp).com/channels/[0-9]{18}/[0-9]{18}/[0-9]{18}", msg.content)
        if len(link_findings) > 5:
            link_findings = []
        if link_findings:
            if str(msg.author.id) in self.bot.user_data["UserData"] and \
                "Settings" in self.bot.user_data["UserData"][str(msg.author.id)] and \
                "auto_embed" in self.bot.user_data["UserData"][str(msg.author.id)]["Settings"] and \
                self.bot.user_data["UserData"][str(msg.author.id)]["Settings"]["auto_embed"]:

                pass_conf = True
            else:
                pass_conf = False

            if not pass_conf:
                await msg.add_reaction("📩")
                
                try:
                    await self.bot.wait_for("reaction_add", timeout=10, 
                        check=lambda r, u: r.message.id==msg.id and u.id==msg.author.id and str(r.emoji)=="📩")
                except TimeoutError:
                    await msg.remove_reaction("📩", self.bot.user)
                    return
                else:
                    conf = await msg.channel.send(embed=Embed(
                        color=msg.author.color,
                        description=f"{self.bot.get_emoji(813237675553062954)} Loading..."))
            
            elif pass_conf:
                conf = await msg.channel.send(
                    embed=Embed(
                        color=msg.author.color,
                        description=f"{self.bot.get_emoji(813237675553062954)} Loading..."))

            emb = Embed(
                color=msg.author.color
            ).set_author(
                name=msg.author.display_name,
                icon_url=msg.author.avatar_url
            ).set_footer(text=f"UID: {msg.author.id}")

            if link_findings:
                messages = []
                link_jumps = []

                new_content = deepcopy(msg.content)
                for link in link_findings:
                    link_parts = link.split("/")
                    # https: / / discord.com / channels / {GID} / {CID} / {MID}
                    
                    channel = self.bot.get_channel(int(link_parts[5]))
                    if not channel: 
                        try: await self.bot.fetch_channel(int(link_parts[5]))
                        except NotFound: continue
                    
                    try: message = await channel.fetch_message(int(link_parts[6]))
                    except NotFound: continue
                    else: messages.append(message)
                    
                    # Check if message has attached image or an embedded image
                    # If msg is an NSFW channel, show image regardless. Otherwise, check message channel.
                    if (msg.channel.is_nsfw() or not message.channel.is_nsfw()) and \
                        msg.author.permissions_in(msg.channel).embed_links:
                        
                        if message.attachments:
                            # Check multiple attachments for eligibility
                            for url in [str(i.url) for i in message.attachments]:
                                # Only use supported image formats
                                if url.endswith((".png", ".jpg", ".jpeg", ".gif")):
                                    # Use first discovered
                                    if emb.image.url == Embed.Empty:  
                                        emb.set_image(url=url)
                                        break

                        elif message.embeds:
                            # Check multiple attachments for eligibility
                            for url in [str(i.image.url) for i in message.embeds]:
                                # Only use supported image formats
                                if url != Embed.Empty and url.endswith((".png", ".jpg", ".jpeg", ".gif")):
                                    # Use first discovered
                                    if emb.image.url == Embed.Empty:
                                        emb.set_image(url=url)
                                        break
                    
                    new_content = new_content.replace(link, "[NHK]")

                    # Special use case
                    if message.author.id == self.bot.user.id and \
                        message.embeds and message.embeds[0].footer.text != Embed.Empty and \
                        "UID:" in message.embeds[0].footer.text:

                        uid = int(re.search(r"[0-9]{17}[0-9]*", message.embeds[0].footer.text).group())
                        user = self.bot.get_user(uid)
                        if not user:
                            try: self.bot.fetch_user(user)
                            except NotFound: user = None

                        link_jumps.append(f"{user.mention if user else message.author.mention} | {self.bot.get_emoji(830223149340688384) if message.channel.is_nsfw() else ':white_check_mark:'} [[#{channel.name}]]({link})")
                    
                    # General use case
                    else:
                        link_jumps.append(f"{message.author.mention} | {self.bot.get_emoji(830223149340688384) if message.channel.is_nsfw() else ':white_check_mark:'} [[#{channel.name}]]({link})")

                if messages:
                    await msg.delete()
                    new_content = new_content.strip("[NHK]")
                    emb.description = f"{new_content}\n" \
                                      f"{newline.join(link_jumps)}"

                    await conf.edit(embed=emb)
                else:
                    await msg.clear_reactions()
                    await conf.delete()

            return

    # Post actions
    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = self.bot.get_user(payload.user_id)
        ctx = await self.bot.get_context(message)
        
        if ctx.guild:
            member = payload.member

        if user == self.bot.user:
            return

        if (user.id == message.author.id or \
            (message.embeds and message.embeds[0].footer.text != Embed.Empty and str(user.id) in message.embeds[0].footer.text)) and \
            message.author.id == 742517626785497168 and \
            str(payload.emoji) == "❌":
            await message.delete()
            return

        if message.channel.category and \
            message.channel.category.id in \
            [740663386500628570, 740663474568560671]:

            if str(payload.emoji) == "⬆":
                if message.embeds and message.embeds[0].footer.text != Embed.Empty and \
                str(user.id) in message.embeds[0].footer.text:
                    await message.remove_reaction(payload.emoji, member)
                    await message.channel.send(
                        content=member.mention,
                        embed=Embed(
                            title="No Self-Upvoting", 
                            description="I've already done that for you.",
                            color=0x32d17f),
                        delete_after=5)

            if str(payload.emoji) == "❌":
                await message.remove_reaction(payload.emoji, member)
                await message.channel.send(
                    content=user.mention,
                    embed=Embed(
                        title="Not Yours", 
                        description="You can't remove this post.",
                        color=0x32d17f),
                    delete_after=5)

            if str(payload.emoji) == "🔀":
                bot_spam = self.bot.get_channel(742481946030112779)
                if not bot_spam: bot_spam = await self.bot.fetch_channel(742481946030112779)
                
                if not member.permissions_in(channel).manage_messages:
                    await bot_spam.send(
                        content=user.mention,
                        embed=Embed(
                            title="Cannot Move Post", 
                            description=f"Only moderators can move posts.",
                            color=0x32d17f
                        ), delete_after=5)

                copied_embed = deepcopy(message.embeds[0])
                edit = await bot_spam.send(
                    member.mention,
                    embed=Embed(
                        title="Moving Post", 
                        description=f"Moderator, please mention the channel\n"
                                    f"you want this post to be moved into.\n"
                                    f"\n"
                                    f"{copied_embed.description}",
                        color=0x32d17f
                    ).set_image(url=copied_embed.image.url
                    ).set_footer(text=copied_embed.footer.text+" (Type `k-cancel` to cancel)"))
                    
                
                while True:
                    try:
                        msg = await self.bot.wait_for("message", timeout=60,
                            check=lambda m: m.channel.id==bot_spam.id and m.author.id==member.id)
                    
                    except TimeoutError:
                        await message.remove_reaction(payload.emoji, member)
                        await edit.edit(
                            content=member.mention,
                            embed=Embed(
                                title="Moving Post", 
                                description=f"❌ Timed out.",
                                color=0x32d17f
                            ).set_footer(text=Embed.Empty))
                
                        break

                    else:
                        if msg.content == "k-cancel":
                            await message.remove_reaction(payload.emoji, member)
                            await msg.delete()
                            await edit.delete()

                            break

                        channel_mention_search = re.search(r"<#[0-9]{18}>", msg.content)
                        if not channel_mention_search:
                            await bot_spam.send(
                                content=user.mention,
                                embed=Embed(
                                    description=f"❌ No channel mentioned. Please try again.",
                                    color=0x32d17f
                                ), delete_after=5)

                            continue

                        channel_mention = channel_mention_search.group()
                        new_channel_id = int(channel_mention.strip("<#>"))

                        new_channel = self.bot.get_channel(new_channel_id)
                        if not new_channel: 
                            try: await self.bot.fetch_channel(new_channel_id)
                            except NotFound: 
                                await bot_spam.send(
                                    content=user.mention,
                                    embed=Embed(
                                        description=f"❌ Invalid channel mentioned. Please try again.",
                                        color=0x32d17f
                                    ), delete_after=5)

                            continue

                        if new_channel.category and \
                            not new_channel.category.id in [740663386500628570, 740663474568560671]:
                            await bot_spam.send(
                                content=user.mention,
                                embed=Embed(
                                    description=f"❌ No NEKOS media channel mentioned. Please try again.",
                                    color=0x32d17f
                                ), delete_after=5)

                            continue

                        if new_channel.id == channel.id: 
                            await bot_spam.send(
                                content=user.mention,
                                embed=Embed(
                                    description=f"❌ The source and destination are the same. Please try again.",
                                    color=0x32d17f
                                ), delete_after=5)

                            continue
                        
                        await message.delete()
                        post = await new_channel.send(embed=copied_embed)
                        await post.add_reaction("⬆️")
                        await bot_spam.send(embed=Embed(description=f"Done. Moved post from {channel.mention} to {new_channel.mention}."))

                        break
                
            return

    # Neko Heaven welcome message
    @Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == 740662779106689055 and not member.bot:
            suspected_raiders = [
                889059743262453771, 
                743733203528843334, 
                889033903850016778, 
                889068106603958272, 
                889068365593866270, 
                889071295617196103, 
                888490183715082330, 
                889029844845883464, 
                889057053866344448, 
                889098995899711488, 
                889033903850016778, 
                889051656539471882, 
                889052606025052210, 
                889052325900075019, 
                889053167394889730, 
                889053378720694363, 
                889054949034586114, 
                889057250776326175, 
                889061126279688202, 
                88906185168875114, 
                889063454118395915, 
                889064836451938344, 
                889065998500646923, 
                889065326430519337, 
                889066400751181884, 
                889066568376520746, 
                889068106603958272, 
                889068106603958272, 
                889034043268661258, 
                889028476567433226, 
                88902871066830442, 
                889029844845883464, 
                889105026931363840, 
                889096426330685482, 
                889104454513721414, 
                889105798213546034, 
                889106072474878012, 
                889107495279292436, 
                889105231567265863, 
                889106331225686099, 
                889102761868804146, 
                889107278307938404
            ]
            if member.id in suspected_raiders:
                self.just_joined[0].update({member.id: "placeholder"})
                await member.send(embed=Embed(
                    color=0xFFBF00,
                    title="Ban Notice",
                    description="🚨⛔ We've gotten reports that a large group of raiders have been detected in another neko-related server. "
                                "Your user ID falls under this group of raiders. Due to this, you cannot be permitted to enter into Ilexis's Loft.\n"
                                "If you believe this was in error, please join the [ban appeals server](https://discord.gg/3RYGFrbsuJ)."
                ))
                await member.ban()
                self.just_joined[0].pop(member.id)
                return

            # Scan for NSFW
            if not await self.confirm_pfp(member):
                return

            if member.guild.id == 740662779106689055:
                try:
                    await member.send(embed=Embed(
                        title="Welcome to Ilexis's Loft!",
                        description="This is a really great place to meet others and Ilexis Nakamori herself! Soon to be a future vtuber, she wants to make people smile, despite her shortcomings when it comes to speech or anxiety. Help her out, it means alot to me and her! :3\n"
                                    "The community also evolves with community feedback. If you think something is missing or wrong, send your thoughts in <#740728594766102538> and an admin will take it into consideration."
                    ).set_thumbnail(url=str(member.guild.icon_url)))
                except Forbidden:
                    pass

            img = Image.open(BytesIO(await member.avatar_url_as(format='png').read())).convert("RGBA")
            
            image_choices = {
                '1':(106, 293),
                '2':(1103, 254),
                '3':(447, 386),
                '4':(1342, 451),
                '5':(353, 365)
            }

            selection = str(randint(1,5))

            background = Image.open(f"Files/user_joined_modal{'_gif' if member.is_avatar_animated() else ''}_{selection}.png", 'r')
            img = img.resize((500,500))
            background.paste(img, image_choices[selection], mask=img)
            background.save(f"Workspace/user_joined_{member.id}.png", format="png")

            image_server = self.bot.get_channel(789198608175202394)
            image_container = await image_server.send(file=File(f"Workspace/user_joined_{member.id}.png"))
            os.remove(f"Workspace/user_joined_{member.id}.png")
            image_url = image_container.attachments[0].url

            door_logs = self.bot.get_channel(965796356503527535)

            welcome_msg = await door_logs.send(content=f"Welcome {member.mention}! Have fun and stay safe!", 
                embed=Embed(
                    title=f"{member.name} just joined the server!",
                ).set_image(url=image_url
                ).set_footer(text=f"UID: {member.id}"))

            self.just_joined[0].update({str(member.id):welcome_msg})

            if str(member.id) not in self.bot.user_data["UserData"]:
                self.bot.user_data["UserData"][str(member.id)] = deepcopy(self.bot.defaults["UserData"]["UID"])

            await sleep(30)
            if member.guild.id == 740662779106689055:
                try:
                    await member.add_roles(
                        member.guild.get_role(829504771073114154),
                        member.guild.get_role(909302321224253460),
                        member.guild.get_role(909301337689296948),
                        member.guild.get_role(769008950611804190),
                        member.guild.get_role(909300699412709416),
                        member.guild.get_role(909300758351069244),
                        member.guild.get_role(909300823383752734),
                        member.guild.get_role(909301283310161950))

                except NotFound:
                    pass

            elif member.guild.id == 925217474654388264:
                try:
                    await member.add_roles(
                        member.guild.get_role(925415568297853039),
                        member.guild.get_role(925256282489913344))

                except NotFound:
                    pass

        elif member.guild.id == 740662779106689055 and member.bot:
            door_logs = self.bot.get_channel(965796356503527535)
            
            welcome_msg = await door_logs.send(content=f"Welcome, {member.mention} [BOT]. We hope you can do something nice.", 
                embed=Embed(
                    title=f"{member} has been added to the server.",
                ).set_image(url=member.avatar_url
                ).set_footer(text=f"UID: {member.id}"))

            self.just_joined[0].update({str(member.id):welcome_msg})

    @Cog.listener()
    async def on_member_remove(self, member):
        if member.guild.id == 740662779106689055:
            if str(member.id) in self.bot.user_data["UserData"]:
                self.bot.user_data["UserData"].pop(str(member.id))

            door_logs = self.bot.get_channel(965796356503527535)

            if str(member.id) in self.just_joined[0]:
                welcome_msg = self.just_joined[0][str(member.id)]
                general_history = await door_logs.history(limit=5).flatten()

                if welcome_msg.id == general_history[0].id:
                    await welcome_msg.delete()
                else:
                    await door_logs.send(f"Looks like `{member}` left so soon. {self.bot.get_emoji(740980255581405206)}")
                
                self.just_joined[0].pop(str(member.id))

            elif not member.bot:
                await door_logs.send(content=f"`{member}` left the server. {self.bot.get_emoji(741726607516893297)}")
            
            elif member.bot:
                await door_logs.send(content=f"`{member}` was removed from the server.")

    @Cog.listener()
    async def on_member_update(self, pre, pos):
        if pos.id in self.pause_member_update:
            return
        
        # Detect nickname change
        if pos.nick != pre.nick and pos.guild.id == 740662779106689055:
            entry = (await pos.guild.audit_logs().flatten())[0]
            if isinstance(entry.user, Member) and entry.user.id != pos.id:
                return

            general = await self.bot.fetch_channel(741381152543211550)
            if pos.nick != pre.nick and not pos.permissions_in(general).manage_nicknames and not pos.bot:
                
                self.pause_member_update.append(pos.id)
                await pos.edit(nick=pre.nick)
                self.pause_member_update.remove(pos.id)

                with suppress(Forbidden):
                    await pos.send(embed=Embed(
                        color=0xFFBF00,
                        title="Warning",
                        description="I understand you want to change your nickname in Neko Heaven, however nickname changes are now enforced by command.\n"
                                    "If you want to change your nickname, please run `k!nick <new nick>` in <#974366490260279326>.\n"))
    
    @Cog.listener()
    async def on_user_update(self, pre, pos):
        if pos.id in self.bot.pause_member_update:
            return
        
        # Detect avatar change and scan for NSFW
        if str(pos.avatar_url) and str(pos.avatar_url) != str(pre.avatar_url):
            guild = self.bot.get_guild(740662779106689055)
            try: member = await guild.fetch_member(pos.id)
            except NotFound: return

            if 851225537165918259 not in [role.id for role in member.roles]:
                return  # Ignore members who don't even have the first rank to save DeepAI credit.

            if member and not await self.confirm_pfp(member): return

    # Catgirl Heaven server icon changes
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_guild_update(self, pre, post):
        if pre.id == 740662779106689055 and \
            pre.icon_url != post.icon_url: # Neko Heaven server ID
            channel = self.bot.get_channel(742211981720813629)  # #🖼server-icon-history ID
            if post.is_icon_animated():
                with open("Workspace/icon.gif", "wb") as f:
                    f.write(BytesIO(await post.icon_url_as(format='gif').read()).getbuffer())

                server_icon = await channel.send(file=File("Workspace/icon.gif"))
                os.remove("Workspace/icon.gif")
                await server_icon.publish()

            else:
                with open("Workspace/icon.png", "wb") as f:
                    f.write(BytesIO(await post.icon_url_as(format='png').read()).getbuffer())

                server_icon = await channel.send(file=File("Workspace/icon.png"))
                os.remove("Workspace/icon.png")
                await server_icon.publish()

    # Disconnect voice bot if VC already has one
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        channel = after.channel
        
        if not channel:
            return
        
        if member.bot:
            # General rule
            musicbot_already_present = False
            for i in channel.members:
                if i.id == member.id:
                    continue
                else:
                    if i.bot:
                        musicbot_already_present = True
                        break
            
            if musicbot_already_present:
                await sleep(2)
                await member.move_to(None)

    
    # Errors
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: Exception):
        if not isinstance(error, CommandNotFound):
            with suppress(NotFound, Forbidden):
                await ctx.message.add_reaction("❌")
            
        if not isinstance(error, CommandOnCooldown) and ctx.command:
            ctx.command.reset_cooldown(ctx)
            
        if self.bot.config['debug_mode']:
            raise error.original
            
        if not self.bot.config['debug_mode']:
            msg = ctx.message
            em = Embed(title="Error", color=0xff0000)
            if isinstance(error, BotMissingPermissions):
                em.description = f"This bot is missing one or more permissions listed in `{self.bot.command_prefix}help` " \
                                 f"under `Required Permissions` or you are trying to use the command in a DM channel." \

            elif isinstance(error, MissingPermissions):
                em.description = "You are missing a required permission, or you are trying to use the command in a DM channel."

            elif isinstance(error, NotOwner):
                em.description = "That command is not listed in the help menu and is to be used by the owner only."

            elif isinstance(error, MissingRequiredArgument):
                em.description = f"\"{error.param.name}\" is a required argument for command " \
                                 f"\"{ctx.command.name}\" that is missing."

            elif isinstance(error, BadArgument):
                em.description = f"You didn't type something correctly. Details below:\n" \
                                 f"{error}"

            elif isinstance(error, CommandNotFound):
                supposed_command = msg.content.split()[0]
                em.description = f"Command \"{supposed_command}\" doesn't exist."
            
            elif isinstance(error, CommandOnCooldown):
                await msg.author.send(embed=Embed(
                    description=f"That command is on a {round(error.cooldown.per)} second cooldown.\n"
                                f"Retry in {round(error.retry_after)} seconds."))
            
            elif isinstance(error, CheckFailure):
                return

            else:
                try:
                    em.description = f"**{type(error.original).__name__}**: {error.original}\n" \
                                    f"\n" \
                                    f"If you keep getting this error, please join the support server."
                except AttributeError:
                    em.description = f"**{type(error).__name__}**: {error}\n" \
                                    f"\n" \
                                    f"If you keep getting this error, please join the support server."
                
                # Raising the exception causes the progam 
                # to think about the exception in the wrong way, so we must 
                # target the exception indirectly.
                if not self.bot.config["debug_mode"]:
                    try:
                        if hasattr(error, "original"):
                            raise error.original
                        else:
                            raise error
                    except Exception:
                        error = exc_info()

                    await self.bot.errorlog.send(error, event=f"Command: {ctx.command.name}")
                else:
                    try:
                        raise error.original
                    except AttributeError:
                        raise error
                
            try:
                await ctx.send(embed=em)
            except Forbidden:
                with suppress(Forbidden):
                    await ctx.author.send(
                        content="This error was sent likely because I "
                                "was blocked from sending messages there.",
                        embed=em)

def setup(bot):
    bot.add_cog(Events(bot))