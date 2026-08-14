import os.path
import environ


env = environ.Env()
if os.path.exists('.env'):
    environ.Env.read_env('.env')


DOWNLOADS_DIR = env.str("STRMNTR_DOWNLOAD_DIR", "downloads")
CONFIG_PATH = env.str("STRMNTR_CONFIG", "config.json")
MOUFLON_KEYS_PATH = env.str("STRMNTR_MOUFLON_KEYS", "stripchat_mouflon_keys.json")
MIN_FREE_DISK_PERCENT = env.float("STRMNTR_MIN_FREE_SPACE", 5.0)  # in %
MIN_FREE_DISK_GB = env.float("STRMNTR_MIN_FREE_SPACE_GB", 0)  # in GB, 0 = disabled
DEBUG = env.bool("STRMNTR_DEBUG", False)

# The camsoda bot ignores this setting in favor of a chrome useragent generated with the fake-useragent library
HTTP_USER_AGENT = env.str("STRMNTR_USER_AGENT", "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0")

# Specify the full path to the ffmpeg binary. By default, ffmpeg found on PATH is used.
FFMPEG_PATH = env.str("STRMNTR_FFMPEG_PATH", 'ffmpeg')

# You can enter a number to select a specific height.
# Use a huge number here and closest match to get the highest resolution variant
# Eg: 240, 360, 480, 720, 1080, 1440, 99999
WANTED_RESOLUTION = env.int("STRMNTR_RESOLUTION", 1080)

# Specify match type when specified height
# Possible values: exact, exact_or_least_higher, exact_or_highest_lower, closest
# Beware of the exact policy. Nothing gets downloaded if the wanted resolution is not available
WANTED_RESOLUTION_PREFERENCE = env.str("STRMNTR_RESOLUTION_PREF", 'closest')

# Specify output container here
# Suggested values are 'mkv' or 'mp4'
CONTAINER = env.str("STRMNTR_CONTAINER", 'mkv')

# Add auto-generated VR format suffix to files
VR_FORMAT_SUFFIX = env.bool("STRMNTR_VR_FORMAT_SUFFIX", True)

# Set ffmpeg readrate to whatever works for you.
# Usually this should be either 0, 1 or 1.3 depending on the network
# Setting it to 0 can result in very fragmented recordings.
# 1 can result in skipped segments
# 1.3 should be the sweet spot but use what works
FFMPEG_READRATE = env.int("STRMNTR_FFMPEG_READRATE", 1.3)

# Specify the segment time in seconds
# If None, the video will be downloaded as a single file
# Example:
# 5 minutes
# SEGMENT_TIME = 300
# 1 hour
# SEGMENT_TIME = 3600
# Also see the ffmpeg documentation for the segment_time option
# You can specify time in hh:mm:ss format
# Example:
# 1 hour
# SEGMENT_TIME = '1:00:00'
SEGMENT_TIME = env.str("STRMNTR_SEGMENT_TIME", None)

# HTTP Manager configuration

# Bind address for the web server
# 0.0.0.0 for remote access from all host
WEBSERVER_HOST = env.str("STRMNTR_HOST", "127.0.0.1")
WEBSERVER_PORT = env.int("STRMNTR_PORT", 5000)

# Password for the web server
# If empty no auth required, else username admin and choosen password
WEBSERVER_PASSWORD = env.str("STRMNTR_PASSWORD", "admin")
