#!/bin/sh
set -e

# config.json and stripchat_mouflon_keys.json are auto-created by the app itself
# at whatever path STRMNTR_CONFIG / STRMNTR_MOUFLON_KEYS point to (see
# streamonitor/config.py and streamonitor/sites/stripchat.py), so no manual
# pre-creation is needed here.
exec python3 Downloader.py
