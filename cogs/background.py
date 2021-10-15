from asyncio import sleep
from datetime import datetime
from json import load

from discord.activity import Activity
from discord.enums import ActivityType, Status
from discord.ext.commands.cog import Cog
from discord.ext.tasks import loop
from discord_components import Button

from utils.classes import Embed

class BackgroundTasks(Cog):
    """Background loops"""

    def __init__(self, bot):
        self.bot = bot
        self.save_data.start()
        self.status_change.start()
        self.disboard_reminder.start()

        self.library_cycle_index = 0
        self.library_cycle.start()

    @loop(seconds=60)
    async def status_change(self):
        time = datetime.utcnow().strftime("%H:%M")

        if self.bot.inactive >= 5:
            status = Status.idle
        else:
            status = Status.online

        if self.bot.config['debug_mode']:
            activity = Activity(
                type=ActivityType.playing,
                name="in DEBUG MODE")

        else:
            activity = Activity(
                type=ActivityType.watching,
                name=f"{self.bot.command_prefix} | UTC: {time}")

        await self.bot.change_presence(status=status, activity=activity)

    @loop(seconds=297.5)
    async def save_data(self):
        # If the repl is exited while saving, data may be corrupted or reset.
        print("[NHK: ... Saving, do not quit...", end="\r")
        await sleep(2)
        print("[NHK: !!! Saving, do not quit...", end="\r")
        time = datetime.now().strftime("%H:%M, %m/%d/%Y")

        self.bot.database.update(self.bot.user_data)

        self.bot.inactive = self.bot.inactive + 1
        print(f"[NHK: {time}] Running.")
   
    @loop(hours=5)
    async def disboard_reminder(self):
        bot_spam = await self.bot.fetch_channel(740671751293501592)
        await bot_spam.send(embed=Embed(
            color=0x24b7b7,
            title="DISBOARD Reminder",
            description="Hey, did you know you can help expand this server in one message?\n"
                        "Type `!d bump` to increase the visibility of this server on [Disboard.org](https://disboard.org/).\n"
                        "To further expose this server to a larger audience, head to <#754548692010270720> and follow each link!"
        ).set_footer(text="ℹ️ You will have to log in with Discord on the external sites."
        ).set_thumbnail(url="https://cdn.discordapp.com/attachments/742481946030112779/891745342431850576/unknown.png"))

    @loop(seconds=5)
    async def library_cycle(self):
        library = self.bot.get_channel(892851304920125460)
        if not library: 
            try: library = await self.bot.fetch_channel(892851304920125460)
            except NotFound: self.library_cycle.cancel()

        try: message = await library.fetch_message(892947918879862875)
        except NotFound: self.library_cycle.cancel()

        with open("Files/library_cycles.json", "r") as f:
            library_cycle_entries = load(f)["books"]

        visual_index = ["▫️　"]*len(library_cycle_entries)
        visual_index[self.library_cycle_index] = "◼️　"  # Green square

        await message.edit(
            content="> If you want to add relevant books to this cycle, please use the <#740728594766102538> channel.",
            embed=Embed.from_dict(library_cycle_entries[self.library_cycle_index]).set_footer(text=''.join(visual_index))
        )

        if self.library_cycle_index == len(library_cycle_entries)-1:
            self.library_cycle_index = 0
        else:
            self.library_cycle_index += 1

    @status_change.before_loop
    async def sc_wait(self):
        await self.bot.wait_until_ready()
        await sleep(30)

    @save_data.before_loop
    async def sd_wait(self):
        await self.bot.wait_until_ready()
        await sleep(15)

    @disboard_reminder.before_loop
    async def dr_wait(self):
        await self.bot.wait_until_ready()
        await sleep(300)

    @library_cycle.before_loop
    async def lc_wait(self):
        await self.bot.wait_until_ready()
        await sleep(5)

    def cog_unload(self):
        self.status_change.cancel()
        self.save_data.cancel()
        self.disboard_reminder.cancel()
        self.library_cycle.cancel()

def setup(bot):
    bot.add_cog(BackgroundTasks(bot))