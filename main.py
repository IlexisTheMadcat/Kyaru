# IMPORTS
from os.path import exists
from json import dump, load
from sys import exc_info
from copy import deepcopy

from discord import __version__, Activity, ActivityType, Intents
from discord.enums import Status
from discord.permissions import Permissions
from discord.utils import oauth_url
from discord.ext.commands import ExtensionAlreadyLoaded

from utils.classes import Bot
from utils.errorlog import ErrorLog
from utils.FirebaseDB import FirebaseDB

# NOTES
DATA_DEFAULTS = {
    "UserData": {
        "UID": {  # User Settings
            "Settings": {
                "auto_emb": False,
                # Whether a message is automatically reposted as an embed when a message link is sent.

                "lp_levelup": False,
                # Whether the bot should minimize the levelup message to reactions.

                "NotificationsDue": {
                    "LevelupMinimizeTip": False
                }  # dict of str:bool
                # A notification sent to users when they use a command for the first time.
                # These are set to true after being executed. Resets by command.
            },
            "Gallery": {
                "channelID": []
            },  # {str(channelID):[imageURL]}
            "Leveling": {
                "personal_modifier": 1.00,
                "inventory": [0],
                "Cumulative EXP": 0,
                "Spending EXP": 0,
                "Event EXP": 0
            },

            "has_boosted": False,

            "EventData": {
                "has_claimed": False    
            }
        }
    },
    "GlobalEventData": {
        "participants": ["UID"],
        "lottery_items": [
            ("Placeholder name", "Placeholder code and instructions")
        ]
        # Add lottery items with eval: 
        # bot.config["lottery_items"].append( ("<reward name>", "||`<code>`||\n<instructions>") )
    },
    "Tokens": {
        "BOT_TOKEN":"xxx",
        "DBL_TOKEN":"xxx",
        "DeepAI_key":"xxx"
    },

    "config": {
        "debug_mode": False,        
        # Print exceptions to stdout.

        "error_log_channel": 734499801697091654,
        # The channel that errors are sent to. 

        "event_ongoing": False
        # Whether event-related commands and actions should run.
    }
}

INIT_EXTENSIONS = [
    "admin",
    "background",
    "commands",
    "events",
    "help",
    "leveling",
    "repl",
    # "web"
]

# 0 = use JSON
# 1 = use Firebase
DATA_CLOUD = 1

if DATA_CLOUD:
    if exists("Files/ServiceAccountKey.json"):
        key = load(open("Files/ServiceAccountKey.json", "r"))
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

else:
    with open("Files/user_data.json", "r") as f:
        db = None
        user_data = load(f)

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
for key in DATA_DEFAULTS['config']:
    if key not in config_data:
        config_data[key] = DATA_DEFAULTS['config'][key]
        print(f"[MISSING VALUE] Config '{key}' missing. "
              f"Inserted default '{DATA_DEFAULTS['config'][key]}'")
found_data = deepcopy(config_data)  # Duplicate to avoid RuntimeError exception
for key in found_data:
    if key not in DATA_DEFAULTS['config']:
        config_data.pop(key)  # Remove redundant data
        print(f"[REDUNDANCY] Invalid config \'{key}\' found. "
              f"Removed key from file.")
del found_data  # Remove variable from namespace

if DATA_CLOUD:
    db.update(user_data)
else:
    with open("Files/user_data.json", "w") as f:
        dump(user_data, f)

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
    auth=user_data["Tokens"],
    use_firebase=DATA_CLOUD
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
            if hasattr(e, "original"):
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