import re
import time
import threading
import m3u8
import requests
from urllib.parse import urljoin
from streamonitor.bot import Bot
from streamonitor.enums import Status, Gender
from streamonitor.utils.cookies import load_cookies_from_netscape
from parameters import WANTED_RESOLUTION, WANTED_RESOLUTION_PREFERENCE


class Chaturbate(Bot):
    site = 'Chaturbate'
    siteslug = 'CB'
    bulk_update = True
    video_url_timeout = 20 * 60

    EDGE_MIN_INTERVAL = 1.0
    _edge_lock = threading.Lock()
    _edge_last_call = 0.0

    _GENDER_MAP = {
        'f': Gender.FEMALE,
        'm': Gender.MALE,
        's': Gender.TRANS,
        'c': Gender.BOTH,
    }

    @classmethod
    def validateUsername(cls, username):
        try:
            r = requests.head(f'https://chaturbate.com/{username}/', timeout=10)
            return r.ok
        except Exception:
            return False

    def __init__(self, username, cookies_path=None):
        super().__init__(username)
        self.sleep_on_offline = 30
        self.sleep_on_error = 20
        self._url_fetched_at = 0.0
        self.cookies_path = None
        if cookies_path:
            self.setCookiesPath(cookies_path)

    def setCookiesPath(self, path):
        self.cookies_path = path
        if path:
            jar = load_cookies_from_netscape(path)
            self.cookies = jar
            self.session.cookies.update(jar)
            self.bulk_update = False
            self.record_private = True
        else:
            self.cookies = None
            self.session.cookies.clear()
            self.bulk_update = True
            self.record_private = False
    
    def getWebsiteURL(self):
        return "https://www.chaturbate.com/" + self.username
    
    def getVideoUrl(self):
        if self.bulk_update:
            url_age = time.time() - self._url_fetched_at
            if not self.lastInfo.get('url') or url_age >= self.video_url_timeout:
                self.getStatus()
        url = self.lastInfo.get('url')
        if not url:
            return None

        if 'llhls.m3u8' in url:
            return self._getCmafPlaylist(url)

        if self.lastInfo.get('cmaf_edge'):
            url = url.replace('playlist.m3u8', 'playlist_sfm4s.m3u8')
            url = re.sub('live-.+amlst', 'live-c-fhls/amlst', url)

        return self.getWantedResolutionPlaylist(url)

    def _getCmafPlaylist(self, url):
        # The edge API now hands out a master playlist (llhls.m3u8?token=<JWE>)
        # whose JWE token is single-use. Invalidate the cached URL up front so
        # any retry fetches a fresh token via getStatus() instead of reusing a
        # consumed one — which 403s and, via the old fallback, fed the master
        # URL itself to ffmpeg (which can't use it: no session cookies and the
        # token is spent).
        self.lastInfo.pop('url', None)

        result = self.session.get(url, headers=self.headers)
        if not result.ok:
            self.logger.warning('Master playlist fetch failed: HTTP %d', result.status_code)
            return None

        try:
            master = m3u8.loads(result.text)
        except Exception as e:
            self.logger.warning('Master playlist parse failed: %s', e)
            return None

        audio_uris = {}
        for media in master.media:
            if media.type == 'AUDIO':
                audio_uris[media.group_id] = urljoin(url, media.uri)

        variants = []
        for playlist in master.playlists:
            stream_info = playlist.stream_info
            resolution = stream_info.resolution if type(stream_info.resolution) is tuple else (0, 0)
            audio_group = getattr(stream_info, 'audio', None)
            variants.append({
                'url': urljoin(url, playlist.uri),
                'resolution': resolution,
                'bandwidth': stream_info.bandwidth,
                'audio_url': audio_uris.get(audio_group) if audio_group else None
            })

        if not variants:
            # A valid media playlist without variants is a direct chunklist
            # URL (older API format) that ffmpeg can consume as-is. Only treat
            # it as a failure when the body doesn't look like a playlist at
            # all (e.g. a 403 error page).
            if '#EXTINF' in result.text or '#EXT-X-PART' in result.text:
                return url
            self.logger.warning('Master playlist contains no variants')
            return None

        for variant in variants:
            w, h = variant['resolution']
            if w < h:
                variant['resolution_diff'] = w - WANTED_RESOLUTION
            else:
                variant['resolution_diff'] = h - WANTED_RESOLUTION

        variants.sort(key=lambda a: abs(a['resolution_diff']))

        if WANTED_RESOLUTION_PREFERENCE == 'exact':
            selected = next((v for v in variants if abs(v['resolution_diff']) == 0), variants[0])
        else:
            selected = variants[0]

        self.logger.info(f"Selected {selected['resolution'][0]}x{selected['resolution'][1]} resolution (CMAF)")
        return (selected['url'], selected['audio_url'])
    
    @staticmethod
    def _parseStatus(status):
        if status == "public":
            return Status.PUBLIC
        elif status in ["private", "hidden"]:
            return Status.PRIVATE
        else:
            return Status.OFFLINE

    def getStatus(self):
        headers = {"X-Requested-With": "XMLHttpRequest"}
        data = {"room_slug": self.username, "bandwidth": "high"}

        try:
            with Chaturbate._edge_lock:
                wait = Chaturbate.EDGE_MIN_INTERVAL - (time.time() - Chaturbate._edge_last_call)
                if wait > 0:
                    time.sleep(wait)
                Chaturbate._edge_last_call = time.time()
            r = self.session.post("https://chaturbate.com/get_edge_hls_url_ajax/", headers=headers, data=data, timeout=10)
            if r.status_code == 429:
                status = Status.RATELIMIT
            else:
                self.lastInfo = r.json()
                self._url_fetched_at = time.time()
                status = self._parseStatus(self.lastInfo['room_status'])
                if status == status.PUBLIC and not self.lastInfo['url']:
                    status = status.RESTRICTED
        except Exception as e:
            self.logger.warning(f'getStatus request failed: {e}')
            status = Status.ERROR

        self.ratelimit = status == Status.RATELIMIT
        return status

    @classmethod
    def fromConfig(cls, data):
        instance = super().fromConfig(data)
        cookies_path = data.get('cookies_path')
        if cookies_path:
            instance.setCookiesPath(cookies_path)
        return instance

    def export(self):
        data = super().export()
        if self.cookies_path:
            data['cookies_path'] = self.cookies_path
        return data

    @classmethod
    def getStatusBulk(cls, streamers, session=None):
        for streamer in streamers:
            if not isinstance(streamer, Chaturbate):
                continue

        if session is None:
            session = requests.Session()
            session.headers.update(cls.headers)
        r = session.get("https://chaturbate.com/affiliates/api/onlinerooms/?format=json&wm=DkfRj", timeout=30)

        if not r.ok:
            r.raise_for_status()

        try:
            data = r.json()
        except requests.exceptions.JSONDecodeError:
            print('Failed to parse JSON response')
            return
        data_map = {str(model['username']).lower(): model for model in data}

        for streamer in streamers:
            model_data = data_map.get(streamer.username.lower())
            if not model_data:
                streamer.setStatus(Status.OFFLINE)
                continue
            if model_data.get('gender'):
                streamer.gender = cls._GENDER_MAP.get(model_data.get('gender'))
            if model_data.get('country'):
                streamer.country = model_data.get('country', '').upper()
            status = cls._parseStatus(model_data['current_show'])
            if status == status.PUBLIC:
                if streamer.sc in [status.PUBLIC, Status.RESTRICTED]:
                    continue
                status = streamer.getStatus()
            if status == Status.UNKNOWN:
                print(f'[{streamer.siteslug}] {streamer.username}: Bulk update got unknown status: {status}')
            streamer.setStatus(status)
