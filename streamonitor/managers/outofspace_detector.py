import os.path
import shutil
from time import sleep
import streamonitor.log as log
from threading import Thread
from parameters import DOWNLOADS_DIR, MIN_FREE_DISK_PERCENT, MIN_FREE_DISK_GB


class OOSDetector(Thread):
    under_threshold_message = 'Free space is under threshold. Exiting.'

    def __init__(self, streamers):
        super().__init__()
        self.streamers = streamers
        self.daemon = True
        self.logger = log.Logger("out_of_space_detector")
        self._paused = False
        self._paused_usernames = set()

    @staticmethod
    def free_space():
        usage = OOSDetector.space_usage()
        free_percent = usage.free / usage.total * 100
        return free_percent

    @staticmethod
    def free_space_gb():
        usage = OOSDetector.space_usage()
        return usage.free / (1024 ** 3)

    @staticmethod
    def space_usage():
        if os.path.exists(DOWNLOADS_DIR):
            usage = shutil.disk_usage(DOWNLOADS_DIR)
        else:
            usage = shutil.disk_usage('.')
        return usage

    @staticmethod
    def disk_space_good():
        if MIN_FREE_DISK_GB > 0:
            # Explicit GB threshold is authoritative; percent floor only
            # applies when no GB threshold is configured (GB=0/disabled).
            return OOSDetector.free_space_gb() > MIN_FREE_DISK_GB
        return OOSDetector.free_space() > MIN_FREE_DISK_PERCENT

    @property
    def paused(self):
        return self._paused

    def run(self):
        while True:
            if not self.disk_space_good():
                if not self._paused:
                    self._pause_all()
                    self._paused = True
                else:
                    self._stop_any_running()
            else:
                if self._paused:
                    self._resume_all()
                    self._paused = False
            sleep(5)

    def _pause_all(self):
        free_gb = self.free_space_gb()
        free_pct = self.free_space()
        self.logger.warning('Free space under threshold (%.1f GB / %.1f%%). Pausing all downloads.',
                            free_gb, free_pct)
        self._paused_usernames = set()
        for streamer in self.streamers:
            if streamer.running:
                self._paused_usernames.add(streamer.username)
                streamer.stop(None, None)

    def _stop_any_running(self):
        for streamer in self.streamers:
            if streamer.running:
                streamer.stop(None, None)

    def _resume_all(self):
        count = 0
        for streamer in self.streamers:
            if streamer.username in self._paused_usernames:
                streamer.restart()
                count += 1
        self._paused_usernames = set()
        self.logger.info('Free space recovered. Resumed %d download(s).', count)
