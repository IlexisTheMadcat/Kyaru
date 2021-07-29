from discord import AppInfo, Permissions
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.core import bot_has_permissions, command
from discord.utils import oauth_url

from utils.classes import Embed

class MiscCommands(Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------------------------------------------------------
    @command()
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def invite(self, ctx: Context):
        return await ctx.send(embed=Embed(
            color=0xff0000, 
            description="I'd love to join your server, but I simply have no reason to be there.\n"
                        "If you want to use my commands, please use them in this server."))
        
        # Command disabled for this bot.
        """Sends an OAuth bot invite URL"""

        app_info: AppInfo = await self.bot.application_info()
        permissions = Permissions()
        permissions.update(
            administrator=True
        )

        emb = Embed(
            description=f'[Click Here]({oauth_url(app_info.id, permissions)}) '
                        f'to invite this bot to your server.\n'
        ).set_author(
            name=f"Invite {self.bot.user.name}",
            icon_url=self.bot.user.avatar_url
        ).set_footer(
            text="Provided by MechHub Bot Factory")
        
        await ctx.send(embed=emb)

    @command(name="help", aliases=["h"])
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def bhelp(self, ctx):
        emb = Embed(
            title="<:info:818664266390700074> Help",
            description=f"""
**{self.bot.description}**
**Support server: [MechHub/DJ4wdsRYy2](https://discord.gg/DJ4wdsRYy2)**

__`rank/level [user]`__
Return this user's rank in Neko Heaven. Leave blank to return your own.

__`leadarboard/lead`__
Return the top 10 ranked users in Neko Heaven.

__`toggle_lowprofile_levelup/lp_levelup`__
To

__`avatar [user]`__
Return this user's avatar. Leave blank to return your own.

__`toggle_auto_embed/auto_emb`__
Toggle auto-embedding your message.
ー If your message contains message links, you will be given the option to simplify it.
ー Turning this on will automatically simplify it for you.

__`waifu2x/upscale`__
*Use a popular AI-powered API to increase any image's resolution.
ー Highly encouraged that you search google for higher resolutions and true detail by the artist.
ー You may attach a file or append an IMAGE URL to the end of your message.
ー **"This image was redrawn by a computer, results may vary from image to image."**

__`detect_nsfw/nsfw`__
Detects the NSFW rating of the image you link or upload.
ー Kyaru runs this command internally for all users who join Neko Heaven to scan their profile picture for NSFW content.
ー NSFW is usually a score between 0-100%, with 60%> being considered as such.
ー **"This test was done by a computer and may not be accurate."**

__`welcome <user> [image_number (1-5)]`__
Have the bot send a welcome message with the details of the specified user.
ー This currently cannot be made an automatic process in other servers.
""" 
        ).add_field(
            inline=False,
            name="Misc Commands",
            value="""
__`help`__
*Shows this message.*

__`privacy/pcpl/terms/tos/legal`__
*Shows the Privacy Policy and Terms of Service for Mechhub Bot Factory.*

❌__`invite`__ (Disabled for this bot)
*Sends this bot's invite url with all permissions listed under Required Permissions.*
"""
        ).add_field(
            inline=False,
            name="Required Permissions",
            value="""
\- Administrator
"""
        ).set_author(
                name=self.bot.user.name,
                icon_url=self.bot.user.avatar_url
        ).set_footer(
            text="Provided by MechHub Bot Factory")
        
        await ctx.send(embed=emb)
    
    @command(name="privacy", aliases=["pcpl", "terms", "tos", "legal"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def legal(self, ctx):
        # Fetch document from one location
        channel = await self.bot.fetch_channel(815473015394926602)
        message = await channel.fetch_message(815473545307881522)
        await ctx.send(embed=Embed(
            title="<:info:818664266390700074> Legal Notice",
            description=message.content
        ).set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar_url
        ).set_footer(
            text="Provided by MechHub Bot Factory"
        ))

def setup(bot):
    bot.add_cog(MiscCommands(bot))
