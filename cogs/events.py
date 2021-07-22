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

from PIL import Image
from discord import File, Member, Message, utils
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

from utils.classes import Embed

newline = "\n"


class Events(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.just_joined = list()
        self.bot.pause_member_update = list()

    # Message events
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_message(self, msg: Message):
        # Cooldown
        if msg.author.id in self.bot.global_cooldown: return
        else: self.bot.global_cooldown.update({msg.author.id:"placeholder"})
        
        # Don't respond to bots.
        if msg.author.bot:
            return

        # Check if the message is a command. 
        # Terminates the event if so, so the command can run.
        verify_command = await self.bot.get_context(msg)
        if verify_command.valid:
            self.bot.inactive = 0
            return

        # Upload images only in these channels
        if msg.guild and msg.channel.id in \
            [866172671544524830, 865857091246751775]:
            if not msg.attachments:
                find_url = re.findall(r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))""", msg.content)
                if find_url:
                    if len(find_url) > 1:
                        await msg.delete()
                        await msg.channel.send(content=msg.author.mention, embed=Embed(
                            title="One Image URL",
                            description="While you can attach as many images you want here, please only send a link to one at a time.",
                        ), delete_after=5)

                    elif len(find_url) == 1:
                        if not find_url[0].endswith(("jpg", "jpeg", "png", "gif")):
                            print(find_url)
                            await msg.delete()
                            await msg.channel.send(content=msg.author.mention, embed=Embed(
                                title="Extension Not Allowed",
                                description="URLs must end in the following: [jpg, jpeg, png, gif]",
                            ), delete_after=5)
                else:
                    await msg.delete()
                    await msg.channel.send(content=msg.author.mention, embed=Embed(
                        title="Images only",
                        description="You can only upload images in this channel.\n"
                                    "You can comment on images by sending its **message** URL in <#742571100009136148>"
                        ), delete_after=5)

        # Upscale media uploads in these categories
        if msg.guild and msg.channel.category and msg.channel.category.id in \
            [740663474568560671, 740663386500628570, 815382953370189865]:
            if not msg.attachments:
                await msg.channel.send(content=msg.author.mention, embed=Embed(
                    title="Images only",
                    description="You can only upload images in this channel.\n"
                                "You can comment on images by sending its **message** URL in <#742571100009136148>"
                    ), delete_after=5)

            if len(msg.attachments) > 1:
                await msg.delete()
                await msg.channel.send(
                    content=msg.author.mention,
                    embed=Embed(
                        title="Media", 
                        description="Please send one attachment at a time.",
                        color=0x32d17f),
                    delete_after=5)
            
            else:
                await msg.channel.set_permissions(msg.author, send_messages=False)
                has_upscaled = False

                conf = await msg.channel.send(
                    embed=Embed(
                        title="Upscaling For Quality",
                        description=f"{self.bot.get_emoji(813237675553062954)} {msg.author.mention} Please wait..."))
                
                attach = msg.attachments[0]

                try:
                    dcfileobj = await attach.to_file()
                    attach_data = await attach.read()
                except HTTPException or NotFound:
                    await msg.author.send("**バカ** Baka! Don't delete the file before I can download it!")
                    if msg.channel.id != 777189629505699850:
                        await msg.channel.edit(overwrites=msg.channel.category.overwrites)

                    await conf.delete()
                    return
                
                img = Image.open(BytesIO(attach_data))
                try:
                    img.seek(1)
                except EOFError:
                    is_animated = False
                else:
                    img.seek(0)
                    is_animated = True

                # Check image size due to Discord upload limitations.
                # Upscale will not be used in this case as the file will most likely be larger.
                async def file_too_large_prompt():
                    with suppress(NotFound):
                        await msg.delete()

                    await conf.edit(content=msg.author.mention, embed=Embed(
                        color=0xff0000,
                        description=f"Please upload your image in [this channel](https://discord.com/channels/740662779106689055/789190968267636768), "
                                    f"it is too large for me to send!\n"
                                    f"{self.bot.get_emoji(813237675553062954)} Waiting... (120s)"))
                    
                    buffer_target = self.bot.get_channel(789190968267636768)
                    await buffer_target.set_permissions(msg.author, read_messages=True)

                    try:
                        m = await self.bot.wait_for("message", timeout=60, check=lambda m: m.author.id == msg.author.id and m.channel.id == 789190968267636768)
                    except TimeoutError:
                        await conf.delete()
                        await buffer_target.edit(overwrites=msg.channel.category.overwrites)
                        
                        if msg.channel.id != 777189629505699850:
                            await msg.channel.edit(overwrites=msg.channel.category.overwrites)
                        
                        return

                    else:
                        if not m.attachments:
                            await buffer_target.send("Attach a file next time! Try uploading in the main channel again.", delete_after=5)
                            await sleep(2)
                            await conf.delete()
                            await buffer_target.edit(overwrites=msg.channel.category.overwrites)
                            
                            if msg.channel.id != 777189629505699850:
                                await msg.channel.edit(overwrites=msg.channel.category.overwrites)
                            
                            return
                        
                        await buffer_target.send("Thanks!", delete_after=2)
                        await sleep(2)
                        await buffer_target.edit(overwrites=msg.channel.category.overwrites)

                        emb = Embed(
                            color=0x32d17f, 
                            description=f"Uploaded by {msg.author.mention}"
                                        f"{newline+'[' if msg.content else ''}{msg.content}{']' if msg.content else ''}")

                        emb.set_image(url=m.attachments[0].url)
                        emb.set_footer(text=f"UID: {msg.author.id}")
                                
                        await conf.edit(content="", embed=emb)
                        await conf.add_reaction("⬆")

                        if msg.channel.id != 777189629505699850:
                            await msg.channel.edit(overwrites=msg.channel.category.overwrites)

                if attach.size >= 8000000:
                    await file_too_large_prompt()
                    return
                
                if is_animated:
                    attachment_file = dcfileobj
                
                else:
                    # Loop until image is optimal size
                    width, height = img.size
                    last_width, last_height = 0, 0
                    if not ((width > height and height < 1000) or \
                        (height > width and width < 1000) or \
                        (height == width and width < 1000)):
                        
                        attachment_file = dcfileobj
                    
                    else:
                        has_upscaled = True
                        while True:
                            r = post(
                                    "https://api.deepai.org/api/waifu2x",
                                    files={'image': attach_data},
                                    headers={'api-key': self.bot.auth["DeepAI_key"]})
                            
                            try:
                                result = udownload(r.json()["output_url"])
                            except KeyError:
                                with suppress(NotFound):
                                    await msg.delete()

                                buffer_target = self.bot.get_channel(789198608175202394)
                                buffer_msg = await buffer_target.send(file=dcfileobj)
                                await conf.edit(content="", embed=Embed(color=0x32d17f,
                                    description=f"Uploaded by {msg.author.mention}; Could not be upscaled or failed."
                                                f"{newline+'[' if msg.content else ''}{msg.content}{']' if msg.content else ''}").set_image(url=buffer_msg.attachments[0].url))
                                await conf.add_reaction("⬆")
                                await msg.channel.edit(overwrites=msg.channel.category.overwrites)
                                return

                            img = Image.open(result[0])
                            width, height = img.size

                            if ((width > height and height < 1000) or \
                                (height > width and width < 1000) or \
                                (height == width and width < 1000)) and \
                                (width != last_width and height != last_height):
                                last_width, last_height = width, height
                                await sleep(1)
                                continue
                            else:
                                break

                        attachment_file = File(result[0], filename=f"{msg.id}.png")
                
                buffer_target = self.bot.get_channel(789198608175202394) # #upload-buffer
                try:
                    buffer_msg = await buffer_target.send(file=attachment_file)
                except HTTPException as e:
                    if e.code == 40005:
                        await file_too_large_prompt()
                        return
                    else:
                        with suppress(NotFound):
                            await msg.delete()

                        raise e

                with suppress(NotFound):
                    await msg.delete()

                emb = Embed(
                    color=0x32d17f, 
                    description=f"Uploaded by {msg.author.mention}{'; Upscaled with Waifu2x.' if has_upscaled else ''}"
                                f"{newline+'[' if msg.content else ''}{msg.content}{']' if msg.content else ''}")
                
                emb.set_image(url=buffer_msg.attachments[0].url)
                emb.set_footer(text=f"UID: {msg.author.id}")
            
                await conf.edit(content="", embed=emb)
                await conf.add_reaction("⬆")
                
                if msg.channel.id != 777189629505699850:
                    await msg.channel.edit(overwrites=msg.channel.category.overwrites)

                return
        
        # Search for message links and reformat.
        new_content = deepcopy(msg.content)
        link_findings = re.findall("https://(?:discord|discordapp).com/channels/[0-9]{18}/[0-9]{18}/[0-9]{18}", new_content)
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
                    conf = await msg.channel.send(f"{self.bot.get_emoji(813237675553062954)} Loading...")                    
            
            elif pass_conf:
                conf = await msg.channel.send(f"{self.bot.get_emoji(813237675553062954)} Loading...")
                
            link_jumps = list()

            em: Embed = Embed(
                color=msg.author.color
            ).set_author(
                name=msg.author.display_name,
                icon_url=msg.author.avatar_url)

            if link_findings:
                for e, link in enumerate(link_findings, 1):
                    link_parts = link.split("/")
                    channel = self.bot.get_channel(int(link_parts[5]))
                    if not channel:
                        link_jumps.append(f"@Unknown | :question: [{'{'}Jump to message{'}'}]({link})")
                        continue
                    
                    try:
                        message = await channel.fetch_message(int(link_parts[6]))
                    except NotFound:
                        continue
                    
                    new_content = new_content.replace(link, "[]")

                    link_jumps.append(f"{message.author.mention} | {':warning:' if channel.is_nsfw() else ':white_check_mark:'} [{'{'}#{channel.name}{'}'}]({link})")
                    user = self.bot.get_user(message.author.id)

                link_jumps = list(set(link_jumps))
                    
            # Clean and modify results
            link_jumps.reverse()
            new_content = new_content.strip("\n")
            new_content = new_content.strip(" ")
            backup = deepcopy(new_content)
            new_content = new_content.strip("[]")

            if new_content:
                em.description = f"{backup}\n{newline.join(link_jumps)}"
            else:
                em.description = "\n".join(link_jumps)

            attachment_files = []
            for attach in msg.attachments:
                try:
                    dcfileobj = await attach.to_file()
                    attachment_files.append(dcfileobj)
                except Exception:
                    continue   

            if link_jumps:
                try:
                    await msg.channel.send(
                        files=attachment_files,
                        embed=em)
                except Exception as ee:
                    print(type(ee).name+":", ee)
                    await msg.add_reaction("❌")
                    await sleep(5)
                    await msg.remove_reaction("❌", msg.guild.me)
                else:
                    with suppress(NotFound):
                        await msg.delete()
                
                await conf.delete()

        # Automate image-help purging
        if not msg.author.bot and \
            msg.channel.id == 740725402506494072:

            if self.bot.thread_active:
                return
            
            if not msg.attachments:
                with suppress(NotFound):
                    await msg.delete()

                await msg.channel.send(
                    content=msg.author.mention,
                    embed=Embed(
                        color=0xff0000,
                        description="Please attach the image you are asking about.\n"
                                    "A mod or perhaps a veteran member will assist you."),
                delete_after=5)
                return
            
            self.bot.thread_active = msg.author.id
            await msg.channel.send(
                content=msg.author.mention,
                embed=Embed(
                    title="Thread created.",
                    description="If your question about this image has been answered, please send `k-close` in chat to clear.\n"
                                "Otherwise, inactivity (180s) will purge this channel automatically."))
            
            messages_sent = 1
            while True:
                try:
                    help_resp = await self.bot.wait_for("message", timeout=180, 
                        check=lambda m: m.channel.id == 740725402506494072)
                except TimeoutError:
                    while messages_sent > 0:
                        await msg.channel.purge()
                        messages_sent -= 100
                    
                    self.bot.thread_active = None
                    return
                
                else:
                    if help_resp.content == "k-close" and (msg.author.id == help_resp.author.id or help_resp.author.permissions_in(msg.channel).manage_messages):
                        while messages_sent > 0:
                            await help_resp.channel.purge()
                            messages_sent -= 100

                        self.bot.thread_active = None
                        return
                    
                    messages_sent += 1
                    continue

        # Allow sniped users to protect their message from Dank Memer
        if (msg.content.lower().startswith("pls snipe") or \
            msg.content.lower().startswith("pls sniper") or \
            msg.content.lower().startswith("pls editsnipe")) and \
            msg.guild and msg.guild.me.permissions_in(msg.channel).manage_messages:

            while True:
                try:
                    snipe = await self.bot.wait_for("message", timeout=5, check=lambda m:m.author.id==270904126974590976 and (not m.content or m.content.startswith("**Handy Dandy Tip**")) and m.embeds)
                except TimeoutError:
                    pass
                else:
                    try:
                        extraction = snipe.embeds[0].author.icon_url
                    except IndexError:
                        continue
                    
                    user_id = extraction.split("/")[4]
                    if not self.bot.get_user(int(user_id)):
                        continue

                    user_id1 = msg.author.id
                    user_id2 = int(user_id)

                    await snipe.add_reaction("❌")
                    try:
                        reaction, user = await self.bot.wait_for("reaction_add", timeout=10,
                            check=lambda r,u:str(r.emoji)=="❌" and \
                                u.id in [user_id1, user_id2] or \
                                (u.permissions_in(msg.channel).manage_messages and \
                                u!=self.bot.user))
                        
                    except TimeoutError:
                        await snipe.remove_reaction("❌", self.bot.user)
                    else:
                        # await snipe.delete() # vv
                        await self.bot.http.delete_message(
                            snipe.channel.id,
                            snipe.id)
                            
                        await sleep(0.3)
                        
                        # await msg.delete() # vv
                        await self.bot.http.delete_message(
                            msg.channel.id,
                            msg.message.id)
    
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

        if message.channel.category and \
            message.channel.category.id in \
            [740663386500628570, 740663474568560671]:

            if str(payload.emoji) == "⬆" and \
                message.embeds[0].footer.text and \
                str(user.id) in message.embeds[0].footer.text:

                member = await message.guild.fetch_member(user.id)
                await message.remove_reaction(payload.emoji, member)
                await message.channel.send(
                    content=user.mention,
                    embed=Embed(
                        title="No Self-Upvoting", 
                        description="I've already done that for you.",
                        color=0x32d17f),
                    delete_after=5)

            if str(payload.emoji) == "❌":
                if (user.id == message.author.id or \
                    str(user.id) in message.embeds[0].description):

                    await message.delete()

                else:
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
                        description=f"{self.bot.get_emoji(813237675553062954)} Moderator, please mention the channel\n"
                                    f"you want this post to be moved into.\n"
                                    f"\n"
                                    f"{copied_embed.description}",
                        color=0x32d17f
                    ).set_image(url=copied_embed.image.url
                    ).set_footer(text=copied_embed.footer.text+" (Type `-cancel` to cancel)"))
                    
                
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
                                description=f":x: Timed out.",
                                color=0x32d17f
                            ).set_footer(text=Embed.Empty))
                
                        break

                    else:
                        if msg.content == "-cancel":
                            await message.remove_reaction(payload.emoji, member)
                            await msg.delete()
                            await edit.delete()

                            break

                        channel_mention_search = re.search(r"<#[0-9]{18}>", msg.content)
                        if not channel_mention_search:
                            await bot_spam.send(
                                content=user.mention,
                                embed=Embed(
                                    description=f":x: No channel mentioned. Please try again.",
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
                                        description=f":x: Invalid channel mentioned. Please try again.",
                                        color=0x32d17f
                                    ), delete_after=5)

                            continue

                        if new_channel.category and \
                            not new_channel.category.id in [740663386500628570, 740663474568560671]:
                            await bot_spam.send(
                                content=user.mention,
                                embed=Embed(
                                    description=f":x: No Neko Heaven media channel mentioned. Please try again.",
                                    color=0x32d17f
                                ), delete_after=5)

                            continue

                        if new_channel.id == channel.id: 
                            await bot_spam.send(
                                content=user.mention,
                                embed=Embed(
                                    description=f":x: The source and destination are the same. Please try again.",
                                    color=0x32d17f
                                ), delete_after=5)

                            continue
                        
                        await message.delete()
                        post = await new_channel.send(embed=copied_embed)
                        await post.add_reaction("⬆️")

                        await edit.edit(
                            content=member.mention,
                            embed=Embed(
                                title="Moved Post", 
                                description=f":white_check_mark: Moderator, please mention the channel you want this post to be moved into.",
                                color=0x32d17f
                            ).set_footer(text="I asked here because I would react differently if you responded in that channel."))
                        await bot_spam.send(embed=Embed(description=f"Done. Moved post from {channel.mention} to {new_channel.mention}."))

                        break
                
            return

    # Neko Heaven welcome message
    @Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == 740662779106689055 and not member.bot:
            guild = self.bot.get_guild(740662779106689055)

            if not member:
                return

            user = await self.bot.fetch_user(member.id)
            r = post(
                "https://api.deepai.org/api/nsfw-detector",
                data={'image': str(user.avatar_url)},
                headers={'api-key': self.bot.auth["DeepAI_key"]})
            
            if 'output' in r.json() and r.json()['output']['nsfw_score'] > 0.5:
                muted_role = utils.get(member.guild.roles, id=741431440490627234)
                await member.add_roles(muted_role)
        
                emb = Embed(
                    title=f"{member} ({member.id})",
                    description="Approve suspicious profile picture:"
                ).set_image(url=user.avatar_url)

                pfps = self.bot.get_channel(862146341538627604)
                control = await pfps.send(embed=emb)
                await control.add_reaction("✅")
                await control.add_reaction("❌")

                try:
                    r, u = await self.bot.wait_for("reaction_add", timeout=60*15, 
                        check=lambda r,u: u.permissions_in(pfps).kick_members and \
                        r.message.id==control.id and not \
                        u.bot and \
                        str(r.emoji) in ["✅", "❌"])
                except TimeoutError:
                    emb.title = f"{member} ({member.id}) **(Timed out)**"
                    emb.set_footer(text="User was kicked automatically.")
                    await control.edit(embed=emb)

                    with suppress(Forbidden):
                        await member.send(embed=Embed(
                            color=0xFFBF00,
                            title="Warning",
                            description="I've used a computer algorithm to determine that your profile picture is considered NSFW and against Discord's Terms of Service.\n"
                                        "\n"
                                        "❌No mod was available to declare the safety of your profile picture. I cannot accept the risk of letting you stay for now.\n"
                                        "\n"
                                        "Due to this, you've been automatically soft-banned from Neko Heaven following server rules. If you believe this was in error, "
                                        "please join the appeal server [here](https://discord.gg/3RYGFrbsuJ) to discuss the situation.\n"
                                        "\n"
                                        "The below image is what was scanned for infringement."
                            ).set_image(url=str(user.avatar_url)
                            ).set_footer(text="This test was done by a computer and may not be accurate."))
        
                else:
                    if str(r.emoji) == "✅":
                        emb.title = f"{member} ({member.id}) **(Approved)**"
                        emb.set_footer(text=f"Approved by {u} ({u.id})")
                        await control.edit(embed=emb)

                        await member.remove_roles(muted_role)
            
                    elif str(r.emoji) == "❌":
                        emb.title = f"{member} ({member.id}) **(Rejected)**"
                        emb.set_footer(text=f"Rejected by {u} ({u.id})")
                        await control.edit(embed=emb)
                        inq = await pfps.send("[30s] Short reason?")

                        try:
                            m = await self.bot.wait_for("message", timeout=30,
                                check=lambda m: m.author.permissions_in(pfps).manage_nicknames and \
                                m.author.id==u.id and \
                                m.channel.id==control.channel.id)
                        except TimeoutError:
                            reason = "❌The moderator did not provide a reason."
                        else:
                            reason = f"The moderator provided this reason confirming my suspicion: **`{m.content}`**"
                            await m.delete()
                
                        await inq.delete()

                        with suppress(Forbidden):
                            await member.send(embed=Embed(
                                color=0xFFBF00,
                                title="Warning",
                                description=f"I've used a computer algorithm to determine that your profile picture is considered NSFW and against Discord's Terms of Service.\n"
                                            f"\n"
                                            f"{reason}\n"
                                            f"\n"
                                            "Due to this, you've been soft-banned from Neko Heaven following server rules. If you believe this was in error, "
                                            f"please join the appeal server [here](https://discord.gg/3RYGFrbsuJ) to discuss the situation.\n"
                                            f"\n"
                                            f"The below image is what was scanned for infringement."
                                ).set_image(url=str(user.avatar_url)
                                ).set_footer(text="This test was done by a computer and may not be accurate."))

                        self.just_joined.append(member.id)
                        await guild.ban(member)
                        await guild.unban(member)
                        return

            img = Image.open(BytesIO(await member.avatar_url_as(format='png').read())).convert("RGBA")
            
            image_choices = {
                '1':(106, 293),
                '2':(1103, 254),
                '3':(447, 386),
                '4':(1342, 451),
                '5':(353, 365)
            }

            selection = str(randint(1,5))

            background = Image.open(f"Workspace/Files/user_joined_modal{'_gif' if member.is_avatar_animated() else ''}_{selection}.png", 'r')
            img = img.resize((500,500))
            background.paste(img, image_choices[selection], mask=img)
            background.save(f"Workspace/user_joined_{member.id}.png", format="png")

            image_server = self.bot.get_channel(789198608175202394)
            image_container = await image_server.send(file=File(f"Workspace/user_joined_{member.id}.png"))
            os.remove(f"Workspace/user_joined_{member.id}.png")
            image_url = image_container.attachments[0].url

            channel = self.bot.get_channel(741381152543211550)  # #🐾general ID
            emb = Embed(
                title=f"{member.name} just joined the server!",
            ).set_image(url=image_url)
            emb.set_footer(
                text=f"UID: {member.id}{'; Animated avatars are not supported, sowwy!' if member.is_avatar_animated() else ''}")
            start_the_timer = await channel.send(content=f"Welcome {member.mention}! Have fun and stay safe!", embed=emb)

            self.just_joined.append(member.id)
            try:
                member = await self.bot.wait_for("member_remove", timeout=600, 
                    check=lambda left_member: left_member.id == member.id)

            except TimeoutError:
                self.just_joined.remove(member.id)
            else:
                history = await start_the_timer.channel.history(limit=5).flatten()
                if start_the_timer.id == history[0].id:
                    await start_the_timer.delete()
                else:
                    await channel.send(f"Looks like `{member}` left so soon. {self.bot.get_emoji(740980255581405206)}")

                return

        elif member.guild.id == 740662779106689055 and member.bot:
            channel = self.bot.get_channel(741381152543211550)
            emb = Embed(
                title=f"{member} has been added to the server.",
            ).set_image(url=member.avatar_url)
            emb.set_footer(text=f"UID: {member.id}")
            
            start_the_timer = await channel.send(content=f"Welcome, {member.mention} [BOT]. We hope you can do something nice.", embed=emb)

            self.just_joined.append(member.id)
            try:
                member = await self.bot.wait_for("member_remove", timeout=180, check=lambda member2: member2.id == member.id)
            except TimeoutError:
                self.just_joined.remove(member.id)
            else:
                await start_the_timer.delete()

    @Cog.listener()
    async def on_member_remove(self, member):
        if member.id in self.just_joined and member.guild.id == 740662779106689055:
            self.just_joined.remove(member.id)
            return
        
        if not member.bot and member.guild.id == 740662779106689055:
            channel = self.bot.get_channel(741381152543211550)
            await channel.send(content=f"`{member}` left the server. {self.bot.get_emoji(741726607516893297)}")
            
        elif member.bot and member.guild.id == 740662779106689055:
            channel = self.bot.get_channel(741381152543211550)
            await channel.send(content=f"`{member}` was removed from the server.")

    @Cog.listener()
    async def on_member_update(self, pre, pos):
        if pos.id in self.bot.pause_member_update:
            return
        
        # Detect nickname change
        if pos.nick != pre.nick and pos.guild.id == 740662779106689055:
            entry = (await pos.guild.audit_logs().flatten())[0]
            if isinstance(entry.user, Member) and entry.user.id != pos.id:
                return

            general = await self.bot.fetch_channel(741381152543211550)
            if pos.nick != pre.nick and not pos.permissions_in(general).manage_nicknames and not pos.bot:
                
                self.bot.pause_member_update.append(pos.id)
                await pos.edit(nick=pre.nick)
                self.bot.pause_member_update.remove(pos.id)

                await pos.send(embed=Embed(
                    color=0xFFBF00,
                    title="Warning",
                    description="I understand you want to change your nickname in Neko Heaven, however nickname changes are now enforced by command.\n"
                                "If you want to change your nickname, please run `k!nick <new nick>` in <#740671751293501592>.\n"))
    
    @Cog.listener()
    async def on_user_update(self, pre, pos):
        if pos.id in self.bot.pause_member_update:
            return
        
        # Detect avatar change and scan for NSFW
        if str(pos.avatar_url) and str(pos.avatar_url) != str(pre.avatar_url):
            guild = self.bot.get_guild(740662779106689055)
            member = guild.get_member(pos.id)

            if not member:
                return

            user = await self.bot.fetch_user(member.id)
            r = post(
                "https://api.deepai.org/api/nsfw-detector",
                data={'image': str(user.avatar_url)},
                headers={'api-key': self.bot.auth["DeepAI_key"]})
            
            if 'output' in r.json() and r.json()['output']['nsfw_score'] > 0.5:
                muted_role = utils.get(member.guild.roles, id=741431440490627234)
                await member.add_roles(muted_role)
        
                emb = Embed(
                    title=f"{member} ({member.id})",
                    description="Approve suspicious profile picture:"
                ).set_image(url=user.avatar_url)

                pfps = self.bot.get_channel(862146341538627604)
                control = await pfps.send(embed=emb)
                await control.add_reaction("✅")
                await control.add_reaction("❌")

                try:
                    r, u = await self.bot.wait_for("reaction_add", timeout=60*15, 
                        check=lambda r,u: u.permissions_in(pfps).kick_members and \
                        r.message.id==control.id and not \
                        u.bot and \
                        str(r.emoji) in ["✅", "❌"])
                except TimeoutError:
                    emb.title = f"{member} ({member.id}) **(Timed out)**"
                    emb.set_footer(text="User was kicked automatically.")
                    await control.edit(embed=emb)

                    await member.send(embed=Embed(
                        color=0xFFBF00,
                        title="Warning",
                        description="I've used a computer algorithm to determine that your profile picture is considered NSFW and against Discord's Terms of Service.\n"
                                    "\n"
                                    "❌No mod was available to declare the safety of your profile picture. I cannot accept the risk of letting you stay for now.\n"
                                    "\n"
                                    "Due to this, you've been automatically soft-banned from Neko Heaven following server rules. If you believe this was in error, "
                                    "please join the appeal server [here](https://discord.gg/3RYGFrbsuJ) to discuss the situation.\n"
                                    "\n"
                                    "The below image is what was scanned for infringement."
                        ).set_image(url=str(user.avatar_url)
                        ).set_footer(text="This test was done by a computer and may not be accurate."))
        
                else:
                    if str(r.emoji) == "✅":
                        emb.title = f"{member} ({member.id}) **(Approved)**"
                        emb.set_footer(text=f"Approved by {u} ({u.id})")
                        await control.edit(embed=emb)

                        await member.remove_roles(muted_role)
                        return
            
                    elif str(r.emoji) == "❌":
                        emb.title = f"{member} ({member.id}) **(Rejected)**"
                        emb.set_footer(text=f"Rejected by {u} ({u.id})")
                        await control.edit(embed=emb)
                        inq = await pfps.send("[30s] Short reason?")

                        try:
                            m = await self.bot.wait_for("message", timeout=30,
                                check=lambda m: m.author.permissions_in(pfps).manage_nicknames and \
                                m.author.id==u.id and \
                                m.channel.id==control.channel.id)
                        except TimeoutError:
                            reason = "❌The moderator did not provide a reason."
                        else:
                            reason = f"The moderator provided this reason confirming my suspicion: **`{m.content}`**"
                            await m.delete()
                
                        await inq.delete()
                        await member.send(embed=Embed(
                            color=0xFFBF00,
                            title="Warning",
                            description=f"I've used a computer algorithm to determine that your profile picture is considered NSFW and against Discord's Terms of Service.\n"
                                        f"\n"
                                        f"{reason}\n"
                                        f"\n"
                                        "Due to this, you've been soft-banned from Neko Heaven following server rules. If you believe this was in error, "
                                        f"please join the appeal server [here](https://discord.gg/3RYGFrbsuJ) to discuss the situation.\n"
                                        f"\n"
                                        f"The below image is what was scanned for infringement."
                            ).set_image(url=str(user.avatar_url)
                            ).set_footer(text="This test was done by a computer and may not be accurate."))

                        self.just_joined.append(member.id)
                        await guild.ban(member)
                        await guild.unban(member)
                        return

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