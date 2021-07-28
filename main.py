# PUBLIC NOTICE: Forking this bot will cause you immediate failures.

# IMPORTS
from os.path import exists
from json import load
from sys import exc_info
from copy import deepcopy

from discord import __version__, Activity, ActivityType, Intents
from discord.enums import Status
from discord.permissions import Permissions
from discord.utils import oauth_url

from utils.classes import Bot
from utils.errorlog import ErrorLog
from utils.FirebaseDB import FirebaseDB

# NOTES

CONFIG_DEFAULTS = {
    "debug_mode": False,        
    # Print exceptions to stdout.

    "error_log_channel": 734499801697091654,
    # The channel that errors are sent to. 

    "event_ongoing": False
    # Whether event-related commands and actions should run.
}

DATA_DEFAULTS = {
    "UserData": {
        "UID": {  # User Settings
            "Settings": {
                "auto_emb": "bool",
            },
            "EventData": {
                "points": 0,
            },
            "Gallery": {
                "channelID": []
            },  # {str(channelID):[imageURL]}
            "Leveling": {
                "personal_modifier": 1.00,
                "Cumulative EXP": 0,
                "Spending EXP": 0,
                "inventory": []
            }
        }
    },
    "GlobalEventData": {
        "participants": ["UID"]
    },
    "Tokens": {
        "BOT_TOKEN":"xxx",
        "DBL_TOKEN":"xxx",
        "DeepAI_key":"xxx"
    },
    "config": {}
}

INIT_EXTENSIONS = [
    "admin",
    "background",
    "commands",
    "events",
    "help",
    "repl",
    # "web"
]

if exists("Files/ServiceAccountKey.json"):
    with open("Files/ServiceAccountKey.json", "r") as f:
        key = load(f)
else:  # If it doesn't exists assume running on replit
    try:
        from replit import db
        key = dict(db["SAK"])
    except Exception:
        raise FileNotFoundError("Could not find ServiceAccountKey.json.")

db = FirebaseDB(
    "https://kyaru-database-default-rtdb.firebaseio.com/", 
    fp_accountkey_json=key)

user_data = db.copy()
# Check the database
for key in DATA_DEFAULTS:
    if key not in user_data:
        user_data[key] = DATA_DEFAULTS[key]
        print(f"[MISSING VALUE] Data key '{key}' missing. "
              f"Inserted default '{DATA_DEFAULTS[key]}'")
found_data = deepcopy(user_data)  # Duplicate to avoid RuntimeError exception
for key in found_data:
    if key not in user_data:
        user_data.pop(key)  # Remove redundant data
        print(f"[REDUNDANCY] Invalid data \'{key}\' found. "
              f"Removed key from file.")
del found_data  # Remove variable from namespace
config_data = user_data["config"]
# Check the bot config
for key in CONFIG_DEFAULTS:
    if key not in config_data:
        config_data[key] = CONFIG_DEFAULTS[key]
        print(f"[MISSING VALUE] Config '{key}' missing. "
              f"Inserted default '{CONFIG_DEFAULTS[key]}'")
found_data = deepcopy(config_data)  # Duplicate to avoid RuntimeError exception
for key in found_data:
    if key not in CONFIG_DEFAULTS:
        config_data.pop(key)  # Remove redundant data
        print(f"[REDUNDANCY] Invalid config \'{key}\' found. "
              f"Removed key from file.")
del found_data  # Remove variable from namespace

db.update(user_data)

print("[BOT INIT] Configurations loaded.")


intents = Intents.default()
intents.members = True
intents.presences = True

bot = Bot(
    description="I help keep Neko Heaven organized.",
    owner_ids=[331551368789622784],  # Ilexis
    status=Status.idle,
    activity=Activity(type=ActivityType.watching, name="myself struggle."),
    command_prefix="k!",
    config=config_data,
    intents=intents,

    database=db,
    user_data=user_data,
    defaults=DATA_DEFAULTS,
    auth=db["Tokens"]
)

# If a custom help command is created:
bot.remove_command("help")

print(f"[BOT INIT] Running in: {bot.cwd}\n"
      f"[BOT INIT] Discord API version: {__version__}")

@bot.event
async def on_ready():
    app_info = await bot.application_info()
    bot.owner = bot.get_user(app_info.owner.id)

    permissions = Permissions()
    permissions.update(
        administrator=True
    )

    # Add the ErrorLog object if the channel is specified
    if bot.user_data["config"]["error_log_channel"]:
        bot.errorlog = ErrorLog(bot, bot.user_data["config"]["error_log_channel"])

    print("\n"
          "#-------------------------------#\n"
          "| Loading initial cogs...\n"
          "#-------------------------------#")

    for cog in INIT_EXTENSIONS:
        try:
            bot.load_extension(f"cogs.{cog}")
            print(f"| Loaded initial cog {cog}")
        except ExtensionAlreadyLoaded:
            continue
        
        except Exception as e:
            if hasattr(error, "original"):
                print(f"| Failed to load extension {cog}\n|   {type(e.original).__name__}: {e.original}")
            else:
                print(f"| Failed to load extension {cog}\n|   {type(e).__name__}: {e}")
            
            error = exc_info()
            if error:
                await bot.errorlog.send(error, event="Load Initial Cog")

    print(f"#-------------------------------#\n"
          f"| Successfully logged in.\n"
          f"#-------------------------------#\n"
          f"| User:      {bot.user}\n"
          f"| User ID:   {bot.user.id}\n"
          f"| Owner:     {bot.owner}\n"
          f"| Guilds:    {len(bot.guilds)}\n"
          f"| OAuth URL: {oauth_url(app_info.id, permissions)}\n"
          f"#------------------------------#\n")

if __name__ == "__main__":
    bot.run()