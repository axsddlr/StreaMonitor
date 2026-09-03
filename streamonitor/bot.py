from __future__ import unicode_literals
import os
import re
import subprocess
import traceback
from enum import Enum
from urllib.parse import urljoin

import m3u8
from time import sleep
from datetime import datetime
from threading import Thread, Lock

import requests
import requests.cookies

from streamonitor.enums import Status, COUNTRIES, Gender, GENDER_DATA
import streamonitor.log as log
from parameters import DOWNLOADS_DIR, DEBUG, WANTED_RESOLUTION, WANTED_RESOLUTION_PREFERENCE, CONTAINER, HTTP_USER_AGENT, FFMPEG_PATH
from streamonitor.downloaders.ffmpeg import getVideoFfmpeg
from streamonitor.models import VideoData

LOADED_SITES = set()


class Bot(Thread):
    site = None
    siteslug = None
    aliases = []
    ratelimit = False
    bulk_update = False
    record_private = False

    sleep_on_private = 5
    sleep_on_offline = 5
    sleep_on_long_offline = 300
    sleep_on_error = 20
    sleep_on_ratelimit = 180
    long_offline_timeout = 600
    video_url_timeout = None

    headers = {
        "User-Agent": HTTP_USER_AGENT
    }

    status_messages = {
        Status.UNKNOWN: "Unknown error",
        Status.PUBLIC: "Channel online",
        Status.OFFLINE: "No stream",
        Status.LONG_OFFLINE: "No stream for a while",
        Status.PRIVATE: "Private show",
        Status.RATELIMIT: "Rate limited",
        Status.NOTEXIST: "Nonexistent user",
        Status.NOTRUNNING: "Not running",
        Status.ERROR: "Error on downloading",
        Status.RESTRICTED: "Model is restricted, maybe geo-block"
    }

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.site:
            global LOADED_SITES
            LOADED_SITES.add(cls)

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.logger = self.getLogger()

        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.cookies = None
        self.cookieUpdater = None
        self.cookie_update_interval = 0

        self.lastInfo = {}  # This dict will hold information about stream after getStatus is called. One can use this in getVideoUrl
        self.running = False
        self.quitting = False
        self.sc: Status = Status.NOTRUNNING  # Status code
        self.previous_status = None
        self.getVideo = getVideoFfmpeg
        self.stopDownload = None
        self._cookie_thread = None
        self.recording = False
        self._video_files_lock = Lock()
        self.video_files = []
        self.video_files_total_size = 0
        self.record_parts = []
        self.cache_file_list()

        self.gender = None
        self.country = None
        self.url = self.getWebsiteURL()

    def setUsername(self, username):
        self.username = username
        self.logger = self.getLogger()
        self.cache_file_list()
        self.url = self.getWebsiteURL()

    def getLogger(self):
        if hasattr(self, 'logger') and self.logger and self.logger.handlers:
            self.logger.removeHandler(self.logger.handlers[0])
        return log.Logger("[" + self.siteslug + "] " + self.username).get_logger()

    def restart(self):
        self.running = True

    def stop(self, a, b, thread_too=False):
        if self.running:
            self.log("Stopping...")
            if self.stopDownload:
                self.stopDownload()
            self.running = False
        if thread_too:
            self.quitting = True
        if self._cookie_thread and self._cookie_thread.is_alive():
            self._cookie_thread.join(timeout=5)

    def getStatus(self):
        return Status.UNKNOWN

    def log(self, message):
        self.logger.info(message)

    def debug(self, message, filename=None):
        if DEBUG:
            self.logger.debug(message)
            if not filename:
                filename = os.path.join(self.outputFolder, 'debug.log')
            with open(filename, 'a+') as debugfile:
                debugfile.write(message + '\n')

    def status(self):
        message = self.status_messages.get(self.sc) or self.status_messages.get(Status.UNKNOWN)
        if self.sc == Status.NOTEXIST:
            self.running = False
        return message

    def getWebsiteURL(self):
        return "javascript:void(0)"

    @property
    def country_data(self):
        return COUNTRIES.get(self.country, {'flag': '', 'name': 'Unknown'})

    @property
    def gender_data(self):
        return GENDER_DATA.get(self.gender, GENDER_DATA.get(Gender.UNKNOWN))

    def cache_file_list(self):
        """Scan directory and cache video file list with thread safety."""
        videos_folder = self.outputFolder
        _videos = []
        _total_size = 0
        if os.path.isdir(videos_folder):
            try:
                for file in os.scandir(videos_folder):
                    if file.is_dir():
                        continue
                    if not os.path.splitext(file.name)[1][1:] in ['mp4', 'mkv', 'webm', 'mov', 'avi', 'wmv', 'ts']:
                        continue
                    video = VideoData(file, self.username)
                    _total_size += video.filesize
                    _videos.append(video)
            except Exception as e:
                self.logger.warning(e)

        # Update shared state with lock to prevent race conditions
        with self._video_files_lock:
            self.video_files = _videos
            self.video_files_total_size = _total_size

    def get_video_files_safe(self):
        """Thread-safe method to get video files list and total size.

        Returns:
            tuple: (video_files copy, total_size)
        """
        with self._video_files_lock:
            return list(self.video_files), self.video_files_total_size

    def _sleep(self, time):
        while time > 0:
            sleep(1)
            time -= 1
            if self.quitting or not self.running:
                return

    def run(self):
        self._recover_interrupted_recording()
        while not self.quitting:
            while not self.running and not self.quitting:
                sleep(1)
            if self.quitting:
                break

            offline_time = self.long_offline_timeout + 1  # Don't start polling when streamer was offline at start
            while self.running:
                try:
                    self.recording = False
                    if not self.bulk_update or self.sc == Status.NOTRUNNING:
                        try:
                            self.sc = self.getStatus()
                        except Exception as e:
                            self.logger.exception(e)
                            self.sc = Status.ERROR
                    # Check if the status has changed and log the update if it's different from the previous status
                    if self.sc != self.previous_status:
                        self.log(self.status())
                        self.previous_status = self.sc
                    if self.sc == Status.ERROR:
                        self._sleep(self.sleep_on_error)
                    if self.sc == Status.OFFLINE:
                        offline_time += self.sleep_on_offline
                        if offline_time > self.long_offline_timeout:
                            self.sc = Status.LONG_OFFLINE
                    elif self.sc == Status.PUBLIC or (self.sc == Status.PRIVATE and self.record_private):
                        offline_time = 0
                        if self.sc == Status.PUBLIC or (self.sc == Status.PRIVATE and self.record_private):
                            if self.cookie_update_interval > 0 and self.cookieUpdater is not None:
                                def update_cookie():
                                    while self.sc == Status.PUBLIC and not self.quitting and self.running:
                                        self._sleep(self.cookie_update_interval)
                                        ret2 = self.cookieUpdater()
                                        if ret2:
                                            self.debug('Updated cookies')
                                        else:
                                            self.logger.warning('Failed to update cookies')
                                cookie_update_process = Thread(target=update_cookie, daemon=True)
                                self._cookie_thread = cookie_update_process
                                cookie_update_process.start()

                            try:
                                video_url = self.getVideoUrl()
                            except Exception as e:
                                self.logger.exception(e)
                                self.logger.error('Failed to get video url')
                                video_url = None
                            if video_url is None:
                                self.sc = Status.ERROR
                                self.logger.error(self.status())
                                self._sleep(self.sleep_on_error)
                                continue
                            self.log('Started downloading show')
                            self.recording = True
                            file = self.genOutFilename()
                            if self.video_url_timeout:
                                self.record_parts.append(file)
                                self._write_parts_manifest()
                            try:
                                ret = self.getVideo(self, video_url, file)
                            except Exception as e:
                                self.logger.exception(e)
                                ret = False
                            if not ret:
                                self.log('Recording ended with error')
                                if self.video_url_timeout and self.record_parts and self.record_parts[-1] == file:
                                    self.record_parts.pop()
                                    self._write_parts_manifest()
                                    # Remove the partial file from the failed
                                    # part: it's not in the merge list and a
                                    # dead-session error can leave a huge,
                                    # unplayable fragment behind.
                                    try:
                                        os.remove(file)
                                    except OSError:
                                        pass
                                self.sc = Status.ERROR
                                self.log(self.status())
                                self._sleep(self.sleep_on_error)
                                continue
                            self.recording = False
                            self.log('Recording ended')
                            try:
                                self.cache_file_list()
                            except Exception as e:
                                self.logger.exception(e)
                except Exception as e:
                    self.logger.exception(e)
                    try:
                        self.cache_file_list()
                    except Exception as e:
                        self.logger.exception(e)
                    self.log(self.status())
                    self.recording = False
                    self._sleep(self.sleep_on_error)
                    continue

                if self.sc in (Status.OFFLINE, Status.LONG_OFFLINE, Status.PRIVATE):
                    self._merge_record_parts()

                if self.quitting:
                    break
                elif self.bulk_update:
                    self._sleep(1)
                elif self.ratelimit:
                    self._sleep(self.sleep_on_ratelimit)
                elif offline_time > self.long_offline_timeout:
                    self._sleep(self.sleep_on_long_offline)
                elif self.sc == Status.PRIVATE:
                    self._sleep(self.sleep_on_private)
                else:
                    self._sleep(self.sleep_on_offline)

            self.sc = Status.NOTRUNNING
            self._merge_record_parts()
            self.log("Stopped")

    def setStatus(self, sc):
        if self.sc == Status.LONG_OFFLINE and sc == Status.OFFLINE:
            return
        self.sc = sc

    def getPlaylistVariants(self, url=None, m3u_data=None):
        sources = []

        if isinstance(m3u_data, m3u8.M3U8):
            variant_m3u8 = m3u_data
        elif isinstance(m3u_data, str):
            variant_m3u8 = m3u8.loads(m3u_data)
        elif not m3u_data or url:
            result = self.session.get(url, headers=self.headers, cookies=self.cookies, timeout=30)
            m3u8_doc = result.content.decode("utf-8")
            variant_m3u8 = m3u8.loads(m3u8_doc)
        else:
            return sources

        for playlist in variant_m3u8.playlists:
            stream_info = playlist.stream_info
            resolution = stream_info.resolution if type(stream_info.resolution) is tuple else (0, 0)
            sources.append({
                'url': playlist.uri,
                'resolution': resolution,
                'frame_rate': stream_info.frame_rate,
                'bandwidth': stream_info.bandwidth
            })

        if not variant_m3u8.is_variant and len(sources) >= 1:
            self.logger.warn("Not variant playlist, can't select resolution")
            return None
        return sources  # [(url, (width, height)),...]

    def getWantedResolutionPlaylist(self, url):
        try:
            sources = self.getPlaylistVariants(url)
            if sources is None:
                return None

            if len(sources) == 0:
                self.logger.error("No available sources")
                return None

            for source in sources:
                width, height = source['resolution']
                if width < height:
                    source['resolution_diff'] = width - WANTED_RESOLUTION
                else:
                    source['resolution_diff'] = height - WANTED_RESOLUTION

            sources.sort(key=lambda a: abs(a['resolution_diff']))
            selected_source = None

            if WANTED_RESOLUTION_PREFERENCE == 'exact':
                if sources[0]['resolution_diff'] == 0:
                    selected_source = sources[0]
            elif WANTED_RESOLUTION_PREFERENCE == 'closest' or len(sources) == 1:
                selected_source = sources[0]
            elif WANTED_RESOLUTION_PREFERENCE == 'exact_or_least_higher':
                for source in sources:
                    if source['resolution_diff'] >= 0:
                        selected_source = source
                        break
            elif WANTED_RESOLUTION_PREFERENCE == 'exact_or_highest_lower':
                for source in sources:
                    if source['resolution_diff'] <= 0:
                        selected_source = source
                        break
            else:
                self.logger.error('Invalid value for WANTED_RESOLUTION_PREFERENCE')
                return None

            if selected_source is None:
                self.logger.error("Couldn't select a resolution")
                return None

            if selected_source['resolution'][1] != 0:
                frame_rate = ''
                if selected_source['frame_rate'] is not None and selected_source['frame_rate'] != 0:
                    frame_rate = f" {selected_source['frame_rate']}fps"
                self.logger.info(f"Selected {selected_source['resolution'][0]}x{selected_source['resolution'][1]}{frame_rate} resolution")
            selected_source_url = selected_source['url']
            return urljoin(url, selected_source_url)
        except Exception as e:
            self.logger.error("Can't get playlist, got some error: " + str(e))
            traceback.print_tb(e.__traceback__)
            return None

    def getVideoUrl(self):
        pass

    def progressInfo(self, p):
        if p.get('status') == 'downloading':
            try:
                downloaded = float(p.get('downloaded_bytes', 0))
                total = float(p.get('total_bytes', 1))
                pct = round(downloaded / total * 100, 1) if total > 0 else 0.0
                self.log(f"Downloading {pct}%")
            except (ValueError, TypeError, ZeroDivisionError):
                self.log("Downloading (unknown size)")
        if p.get('status') == 'finished':
            self.log("Show ended. File:" + p.get('filename', 'unknown'))

    @property
    def outputFolder(self):
        return str(os.path.join(DOWNLOADS_DIR, self.username + ' [' + self.siteslug + ']'))

    def genOutFilename(self, create_dir=True):
        folder = self.outputFolder
        if create_dir:
            os.makedirs(folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(folder, f'{self.username}-{timestamp}.{CONTAINER}')
        return filename

    @property
    def _parts_manifest(self):
        return os.path.join(self.outputFolder, '.parts.txt')

    def _write_parts_manifest(self):
        try:
            os.makedirs(self.outputFolder, exist_ok=True)
            with open(self._parts_manifest, 'w', encoding='utf-8') as f:
                for p in self.record_parts:
                    f.write(p + '\n')
        except Exception:
            pass

    def _clear_parts_manifest(self):
        try:
            os.remove(self._parts_manifest)
        except OSError:
            pass

    def _recover_interrupted_recording(self):
        # Always recover. Parts recorded by the old 20-minute Chaturbate
        # rotation carry a .parts.txt manifest; merge them automatically at
        # startup (e.g. right after updating the image) instead of asking
        # the user to concatenate files by hand. If the manifest is missing
        # (the old code cleared it even on merge failure), fall back to a
        # filename-based scan for consecutive split parts.
        try:
            if os.path.exists(self._parts_manifest):
                with open(self._parts_manifest, 'r', encoding='utf-8') as f:
                    parts = [line.strip() for line in f if line.strip()]
                if parts:
                    self.log(f'Recovering {len(parts)} recording parts from an interrupted session')
                    self._merge_parts(parts, clear_manifest=True)
                else:
                    self._clear_parts_manifest()
            else:
                self._merge_orphaned_parts()
        except Exception as e:
            self.logger.warning(f'Failed to recover interrupted recording: {e}')

    def _merge_record_parts(self):
        parts = self.record_parts
        self.record_parts = []
        if len(parts) <= 1:
            self._clear_parts_manifest()
            return
        self._merge_parts(parts, clear_manifest=True)

    def _merge_parts(self, parts, clear_manifest):
        final = parts[0]
        tmp = final + '.tmp'
        listfile = final + '.concat.txt'
        movflags = ['-movflags', '+frag_keyframe+empty_moov'] if CONTAINER == 'mp4' else []
        try:
            with open(listfile, 'w', encoding='utf-8') as f:
                for p in parts:
                    f.write("file '" + p.replace("'", "'\\''") + "'\n")
            self.log(f'Merging {len(parts)} recording parts into a single file')
            proc = subprocess.run(
                [FFMPEG_PATH, '-y', '-hide_banner', '-loglevel', 'error',
                 '-f', 'concat', '-safe', '0', '-i', listfile,
                 '-c', 'copy'] + movflags + [tmp],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if proc.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
                os.replace(tmp, final)
                for p in parts[1:]:
                    try:
                        os.remove(p)
                    except OSError:
                        pass
                self.log('Recording saved to ' + final)
                if clear_manifest:
                    self._clear_parts_manifest()
            else:
                # Keep the individual parts on failure so a broken merge can
                # never destroy the originals; the manifest (if any) stays
                # too, so the next startup retries automatically.
                detail = ''
                if proc.stderr:
                    detail = proc.stderr.decode('utf-8', errors='replace').strip()
                    if detail:
                        detail = ': ' + detail[-400:]
                self.logger.warning('Merge failed (ffmpeg exit %d), keeping individual parts%s',
                                    proc.returncode, detail)
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except OSError:
                    pass
        except Exception as e:
            self.logger.warning(f'Failed to merge recording parts: {e}')
        finally:
            try:
                os.remove(listfile)
            except OSError:
                pass

    def _merge_orphaned_parts(self):
        """Merge leftover 20-minute rotation parts that have no manifest.

        The old rotation image cleared .parts.txt even when a merge failed,
        which can leave consecutive split files behind. Detect them by
        filename timestamp: rotation restarts are a few seconds apart, while
        a real offline gap lasts at least one status cycle.
        """
        try:
            folder = self.outputFolder
            if not os.path.isdir(folder):
                return
            pattern = re.compile(
                re.escape(self.username) + r'-(\d{8})-(\d{6})\.' + re.escape(CONTAINER) + r'$')
            found = []
            for name in os.listdir(folder):
                m = pattern.match(name)
                if not m:
                    continue
                try:
                    ts = datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H%M%S')
                except ValueError:
                    continue
                found.append((ts, os.path.join(folder, name)))
            found.sort()
            run = []
            for ts, path in found:
                if run and (ts - run[-1][0]).total_seconds() <= 10:
                    run.append((ts, path))
                else:
                    if len(run) >= 2:
                        self._merge_parts([p for _, p in run], clear_manifest=False)
                    run = [(ts, path)]
            if len(run) >= 2:
                self._merge_parts([p for _, p in run], clear_manifest=False)
        except Exception as e:
            self.logger.warning(f'Orphaned part scan failed: {e}')

    @classmethod
    def fromConfig(cls, data):
        instance = cls(username=data['username'])
        instance.running = data.get('running', True)
        instance.country = data.get('country')
        raw_gender = data.get('gender')
        instance.gender = Gender(raw_gender) if raw_gender is not None else None
        return instance

    def export(self):
        return {
            "site": self.site,
            "username": self.username,
            "running": self.running,
            "country": self.country,
            "gender": self.gender.value if isinstance(self.gender, Enum) else self.gender,
        }

    @staticmethod
    def str2site(site: str):
        site = site.lower()
        for sitecls in LOADED_SITES:
            if site == sitecls.site.lower() or \
                    site == sitecls.siteslug.lower() or \
                    site in sitecls.aliases:
                return sitecls
        return None

    @staticmethod
    def createInstance(username: str, site: str = None):
        if site:
            site_cls = Bot.str2site(site)
            if site_cls:
                return site_cls(username)
            else:
                raise Exception('No such site')
        return None

    @classmethod
    def validateUsername(cls, username):
        return True


class RoomIdBot(Bot):
    def __init__(self, username, room_id=None):
        self.room_id = None
        super().__init__(username)

        if room_id and username:
            self.room_id = room_id

        if self.room_id is None and username.isnumeric():  # Username might be the room ID
            username_real = self.getUsernameFromRoomId(username)
            if username_real is not None:  # Username might not be the room ID even though it is numeric
                self.logger.debug(f'Found username: {username_real}')
                self.room_id = username
                self.setUsername(username_real)

        if self.room_id is None:  # We need to get the room ID
            self.room_id = self.getRoomIdFromUsername(username)
            if self.room_id:
                self.logger.debug(f'Found room ID: {self.room_id}')

        if self.room_id is None:  # Still no room ID, streamer probably does not exist
            self.logger.warning(f'Room ID not found')
            self.sc = Status.NOTEXIST

        self.logger = self.getLogger()
        self.url = self.getWebsiteURL()

    @classmethod
    def fromConfig(cls, data):
        instance = cls(username=data['username'], room_id=data.get('room_id'))
        instance.running = data.get('running', True)
        instance.country = data.get('country')
        raw_gender = data.get('gender')
        instance.gender = Gender(raw_gender) if raw_gender is not None else None
        return instance

    def export(self):
        data = super().export()
        data['room_id'] = self.room_id
        return data

    def getRoomIdFromUsername(self, username):
        return None

    def getUsernameFromRoomId(self, room_id):
        return None
