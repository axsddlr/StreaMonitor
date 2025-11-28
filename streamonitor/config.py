import json
import sys

from streamonitor.bot import Bot
from streamonitor.log import Logger

logger = Logger('[CONFIG]').get_logger()
config_loc = "config.json"


def load_config():
    try:
        with open(config_loc, "r+") as f:
            return json.load(f)
    except FileNotFoundError:
        with open(config_loc, "w+") as f:
            json.dump([], f, indent=4)
            return []
    except Exception as e:
        print(e)
        sys.exit(1)


def save_config(config):
    try:
        with open(config_loc, "w+") as f:
            json.dump(config, f, indent=4)

        return True
    except Exception as e:
        print(e)
        sys.exit(1)


def loadStreamers():
    """Load and start all configured streamers.

    Creates bot instances first, then starts them all in parallel for faster startup.
    Each bot thread will handle its own initialization and timing.
    """
    streamers = []

    # First pass: Create all bot instances
    for streamer in load_config():
        username = streamer["username"]
        site = streamer["site"]

        bot_class = Bot.str2site(site)
        if not bot_class:
            logger.warning(f'Unknown site: {site} (user: {username})')
            continue

        try:
            streamer_bot = bot_class.fromConfig(streamer)
            streamers.append(streamer_bot)
        except Exception as e:
            logger.error(f'Failed to initialize {username} on {site}: {e}')
            logger.warning(f'Skipping {username} on {site}')
            continue

    # Second pass: Start all threads in parallel
    logger.info(f'Starting {len(streamers)} streamer(s)...')
    for streamer_bot in streamers:
        try:
            streamer_bot.start()
        except Exception as e:
            logger.error(f'Failed to start thread for {streamer_bot.username}: {e}')

    return streamers
