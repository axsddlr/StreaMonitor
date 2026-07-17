import json
import os
import sys
import tempfile
import time

from streamonitor.bot import Bot
from streamonitor.log import Logger
from parameters import CONFIG_PATH

logger = Logger('[CONFIG]').get_logger()
config_loc = CONFIG_PATH


def load_config():
    try:
        with open(config_loc, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        with open(config_loc, "w") as f:
            json.dump([], f, indent=4)
            return []
    except Exception as e:
        print(e)
        sys.exit(1)


def save_config(config):
    dirname = os.path.dirname(config_loc)
    try:
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json", prefix="config_", dir=dirname or "."
        )
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=4)
        os.replace(tmp_path, config_loc)
        return True
    except Exception as e:
        print(e)
        sys.exit(1)


def loadStreamers():
    streamers = []
    for streamer in load_config():
        username = streamer["username"]
        site = streamer["site"]

        bot_class = Bot.str2site(site)
        if not bot_class:
            logger.warning(f'Unknown site: {site} (user: {username})')
            continue

        streamer_bot = bot_class.fromConfig(streamer)
        streamers.append(streamer_bot)
        streamer_bot.start()
        time.sleep(0.1)
    return streamers
