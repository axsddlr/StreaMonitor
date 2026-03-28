#!/bin/sh
set -e

# Ensure required files exist so the app can start without manual setup
[ -f /app/config.json ]                    || echo '[]' > /app/config.json
[ -f /app/stripchat_mouflon_keys.json ]    || echo '{}' > /app/stripchat_mouflon_keys.json

exec python3 Downloader.py
