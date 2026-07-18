from time import sleep

import requests

from streamonitor.bot import LOADED_SITES
from streamonitor.manager import Manager
from streamonitor.clean_exit import CleanExit
import streamonitor.log as log


class BulkStatusManager(Manager):
    def __init__(self, streamers):
        super().__init__(streamers)
        self.logger = log.Logger("bulk_status_manager")

    def run(self):
        bulk_bots = frozenset([site for site in LOADED_SITES if hasattr(site, 'getStatusBulk') and site.bulk_update])
        bot_sessions = {}
        self._bot_sessions = bot_sessions
        bot_errors = {}

        for bot in bulk_bots:
            bot_sessions[bot] = requests.Session()

        while True:
            bot_bulk = {}
            for streamer in self.streamers:
                bot_class = streamer.__class__
                if bot_class not in bulk_bots:
                    continue
                if not streamer.running:
                    continue
                bot_bulk.setdefault(bot_class, set()).add(streamer)
            for bot_class, streamers in bot_bulk.items():
                try:
                    self.logger.debug('Get ' + str(bot_class.site) + ' bulk status')
                    bot_class.getStatusBulk(streamers, session=bot_sessions[bot_class])
                    bot_errors[bot_class] = 0
                except Exception as e:
                    bot_errors[bot_class] = bot_errors.get(bot_class, 0) + 1
                    backoff = min(60 * bot_errors[bot_class], 600)
                    self.logger.error(f"Error in bulk status check for {bot_class.site}: {e} (backoff: {backoff}s)")
                    sleep(backoff)
                    continue
            sleep(10)

    def do_quit(self, _=None, __=None, ___=None):
        if hasattr(self, '_bot_sessions'):
            for s in self._bot_sessions.values():
                s.close()
        CleanExit(self.streamers)()
