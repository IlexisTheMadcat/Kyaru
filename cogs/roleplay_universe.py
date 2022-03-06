import re
from copy import deepcopy
from asyncio import sleep, TimeoutError

from discord.ext.commands.cog import Cog
from discord.ext.commands.core import (
    has_permissions, 
    bot_has_permissions, 
    command
)
from discord_components import Button

from utils.classes import Embed


newline = "\n"


class RoleplayUniverse(Cog):
    def __init__(self, bot):
        self.bot = bot

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

        if channel.id == 925217778183602227:
            if str(user.id) in message.content:
                if str(payload.emoji) == "❌":
                    await message.delete()
                    return

    @Cog.listener()
    async def on_message(self, msg):
        if msg.channel.id == 925218470063386625:  # ▶submit-character
            if msg.author.id == self.bot.user.id:
                await sleep(5)
                await msg.delete()
                return

            match = re.search(
                pattern=r"\A"
                        r"Name\n"
                        r"> (.+)\n"
                        r"\n"
                        r"Age\n"
                        r"> ([0-9,]+)\n"
                        r"\n"
                        r"Likes\n"
                        r"> (.+)\n"
                        r"\n"
                        r"Dislikes\n"
                        r"> (.+)\n"
                        r"\n"
                        r"Bio\n"
                        r"> ([\S\s]+)"
                        r"\Z",
                string=msg.content
            )

            await msg.delete()
            if not match or not msg.attachments:
                await msg.channel.send(
                    f"{msg.author.mention}", 
                    embed=Embed(
                        title="Invalid Submission",
                        description="You have to copy the text above and replace the examples with your own text.\n"
                                    "You must also attach an image."
                    )
                )
                await msg.author.send(
                    embed=Embed(
                        title="Invalid Submission",
                        description=f"Please copy everything in the code block and try to fix it.\n"
                                    f"```\n"
                                    f"{msg.content.strip('`')}\n"
                                    f"```"
                        ).set_footer(text="Do not include ``` in your response!")
                    )
                return

            # Copy attachment
            dcfileobj = await msg.attachments[0].to_file()
            buffer_target = await self.bot.fetch_channel(789198608175202394)
            buffer_msg = await buffer_target.send(file=dcfileobj)

            emb = Embed(
                    title=match.group(1),
                    description= 
                        f"Age: {match.group(2)}\n"
                        f"Likes: {match.group(3)}\n"
                        f"Dislikes: {match.group(4)}\n"
                        f"Biography: {match.group(5)}\n"
                        f"\n"
                        f"Submission by {msg.author.mention}"
                ).set_image(url=buffer_msg.attachments[0])

            approve_characters = await self.bot.fetch_channel(925236492085907456)
            control = await approve_characters.send(
                embed=emb,
                components=[
                    [Button(emoji="✅", style=1, id="approve", label="Approve"),
                    Button(emoji="❌", style=2, id="reject", label="Reject")]
                ]
            )

            while True:
                try:
                    interaction = await self.bot.wait_for("button_click", timeout=3600,
                        check=lambda i: 925256191335096330 in [role.id for role in i.user.roles] and i.message.id==control.id)
                except TimeoutError:
                    try:
                        emb.set_footer(text="❌ Timed out")
                        await control.edit(embed=emb)
                    except Exception:
                        pass

                    return
                else:
                    try: await interaction.respond(type=6)
                    except Exception: continue

                    async def approve():
                        characters = await self.bot.fetch_channel(925217778183602227)
                        await characters.send(
                            content=msg.author.mention,
                            embed=Embed(
                                title=match.group(1),
                                description= 
                                    f"🐾 Likes 🐾\n"
                                    f"▫️ {(newline+'▫️ ').join(match.group(3).split(', '))}\n"
                                    f"\n"
                                    f"🐾 Dislikes 🐾\n"
                                    f"▫️ {(newline+'▫️ ').join(match.group(4).split(', '))}\n"
                                    f"\n"
                                    f"🐾 Biography 🐾\n"
                                    f"{match.group(5)}"
                            ).set_image(url=buffer_msg.attachments[0]).set_footer(text=f"Age: {match.group(2)}\n")
                        )

                        await msg.author.add_roles(msg.guild.get_role(925412934195241021))

                    if interaction.component.id == "approve":
                        emb.set_footer(text=f"✅ Approved: {interaction.user} ({interaction.user.id})")
                        await control.edit(embed=emb, components=[])
                        await approve()
                        return
            
                    elif interaction.component.id == "reject":
                    
                        emb.set_footer(text=f"❌ Rejected: {interaction.user} ({interaction.user.id})\n📄 Reason: [TBD]")
                        await control.edit(embed=emb, components=[])   
                    
                        inq = await approve_characters.send(embed=Embed(
                            description="Please type your reason within 2 minutes.\n"
                                        "Send `skip` or `s` to leave blank.\n"
                                        "Send `nvm` or `n` to cancel and approve."))

                        try:
                            m = await self.bot.wait_for("message", timeout=120,
                                check=lambda m: 925256191335096330 in [role.id for role in m.author.roles] and \
                                    m.author.id==interaction.user.id and m.channel.id==control.channel.id)
                        except TimeoutError:
                            await inq.delete()
                            reason = "None provided"
                        else:
                            await m.delete()
                            await inq.delete()

                            if m.content in ["nvm", "Nvm", "NVM", "n", "N"]:
                                emb.set_footer(text=f"✅ Approved: {interaction.user} ({interaction.user.id})")
                                await control.edit(embed=emb, components=[])
                                await approve()
                                return

                            elif m.content in ["skip", "Skip", "SKIP", "s", "S"]:
                                reason = "None provided"

                            else:
                                reason = m.content

                        await msg.author.send(
                            embed=Embed(
                                title="Submission Rejected",
                                description=f"Please copy everything in the code block and try to fix it.\n"
                                            f"```\n"
                                            f"{msg.content.strip('`')}\n"
                                            f"```"
                                ).set_footer(text=f"Reason for rejection: {reason}")
                            )

                        emb.set_footer(text=f"❌ Rejected: {interaction.user} ({interaction.user.id})\n📄 Reason: {reason}")
                        await control.edit(embed=emb, components=[])


def setup(bot):
    bot.add_cog(RoleplayUniverse(bot))