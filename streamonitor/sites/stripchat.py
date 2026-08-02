import itertools
import json
import os.path
import random
import re
import requests
import base64
import hashlib

from streamonitor.bot import RoomIdBot
from streamonitor.downloaders.hls import getVideoNativeHLS
from streamonitor.enums import Status, Gender, COUNTRIES
from parameters import MOUFLON_KEYS_PATH


class StripChat(RoomIdBot):
    site = 'StripChat'
    siteslug = 'SC'

    bulk_update = True
    _static_data = None
    _mouflon_cache_filename = MOUFLON_KEYS_PATH
    _mouflon_keys: dict = None
    _cached_keys: dict[str, bytes] = None
    _PRIVATE_STATUSES = frozenset(["private", "groupShow", "p2p", "virtualPrivate", "p2pVoice"])
    _OFFLINE_STATUSES = frozenset(["off", "idle"])

    _GENDER_MAP = {
        'female': Gender.FEMALE,
        'male': Gender.MALE,
        'maleFemale': Gender.BOTH
    }

    _KEYS_GITHUB_URL = 'https://raw.githubusercontent.com/kesamom/stripchat_mouflon/main/stripchat_mouflon_keys.json'
    _KEYS_DISCOVERY_MAX_ATTEMPTS = 3
    _MMP_PLAYER_ORIGIN = 'https://img.doppiocdn.com/player/mmp'
    _MMP_CHUNK_PATTERN = re.compile(r'(?:mmp\.doppiocdn\.com|img\.doppiocdn\.com)/player/(?:mmp|doppio)/(v[\d.]+)/(chunk-[a-f0-9]+\.js)', re.IGNORECASE)
    _STALE_KEY_MARKER_PATTERN = re.compile(r'[A-Za-z0-9_+-]{16,24}\s*:\s*"[A-Za-z0-9_+-]{16,24}"', re.ASCII)

    if os.path.isfile(_mouflon_cache_filename):
        try:
            with open(_mouflon_cache_filename) as f:
                if not isinstance(_mouflon_keys, dict):
                    _mouflon_keys = {}
                _mouflon_keys.update(json.load(f))
                print('Loaded StripChat mouflon key cache')
        except Exception as e:
            print('Error loading mouflon key cache:', e)

    def __init__(self, username, room_id=None):
        if StripChat._static_data is None:
            StripChat._static_data = {}
            try:
                self.getInitialData()
            except Exception as e:
                print('Error initializing StripChat static data:', e)

        StripChat._load_keys()

        super().__init__(username, room_id)
        self._id = None
        self.vr = False
        self.getVideo = lambda _, url, filename: getVideoNativeHLS(self, url, filename, StripChat.m3u_decoder)

    @classmethod
    def _load_keys(cls):
        if cls._mouflon_keys is not None:
            return
        cls._mouflon_keys = {}
        if os.path.isfile(cls._mouflon_cache_filename):
            try:
                with open(cls._mouflon_cache_filename) as f:
                    cls._mouflon_keys.update(json.load(f))
            except Exception:
                pass

    @classmethod
    def _save_keys(cls):
        try:
            with open(cls._mouflon_cache_filename, 'w') as f:
                json.dump(cls._mouflon_keys, f, indent=2)
        except Exception as e:
            print('Error saving mouflon key cache:', e)

    @classmethod
    def _ensure_keys(cls):
        if cls._mouflon_keys is None:
            cls._mouflon_keys = {}

    @classmethod
    def refreshKeysFromGitHub(cls):
        cls._ensure_keys()
        try:
            r = requests.get(cls._KEYS_GITHUB_URL, headers=cls.headers, timeout=15)
            if r.status_code == 200:
                new_keys = r.json()
                new_count = sum(1 for k in new_keys if k not in cls._mouflon_keys)
                cls._mouflon_keys.update(new_keys)
                cls._save_keys()
                if new_count:
                    print(f'Refreshed {new_count} new StripChat mouflon keys from GitHub')
                return True
        except Exception as e:
            print('Failed to refresh StripChat keys from GitHub:', e)
        return False

    @classmethod
    def _discoverPlayerBundleUrl(cls):
        session = requests.Session()
        try:
            r = session.get('https://stripchat.com/', headers=cls.headers, timeout=15)
            if r.status_code == 200:
                match = cls._MMP_CHUNK_PATTERN.search(r.text)
                if match:
                    return match.group(0)
                viewcam_scripts = re.findall(r'viewcam\.([a-f0-9]+)\.js', r.text)
                if viewcam_scripts:
                    for vc_hash in viewcam_scripts[:1]:
                        vc_url = f'https://assets.chapturist.com/assets/viewcam.{vc_hash}.js'
                        vc_r = session.get(vc_url, headers=cls.headers, timeout=15)
                        if vc_r.status_code == 200:
                            match = cls._MMP_CHUNK_PATTERN.search(vc_r.text)
                            if match:
                                return match.group(0)
        except Exception as e:
            print('Failed to discover MMP player bundle URL:', e)
        return None

    @classmethod
    def _extractKeysFromBundle(cls, bundle_url):
        if not bundle_url:
            return {}
        if not bundle_url.startswith('http'):
            bundle_url = 'https:' + bundle_url
        keys = {}
        try:
            r = requests.get(bundle_url, headers=cls.headers, timeout=15)
            if r.status_code != 200:
                print(f'Failed to fetch player bundle: HTTP {r.status_code}')
                return {}
            content = r.text
            matches = cls._STALE_KEY_MARKER_PATTERN.findall(content)
            candidate_strings = set()
            for m in matches:
                if ':' in m:
                    parts = m.split(':', 1)
                    key_part = parts[0].strip().strip('"').strip("'")
                    val_part = parts[1].strip().strip('"').strip("'")
                    if 16 <= len(key_part) <= 24 and 16 <= len(val_part) <= 24:
                        candidate_strings.add((key_part, val_part))
            for k, v in candidate_strings:
                if k in cls._mouflon_keys or v in cls._mouflon_keys.values():
                    continue
            key_candidates = {}
            for k, v in candidate_strings:
                occurrences = content.count(f'"{k}"')
                if occurrences >= 2 and k != v:
                    key_candidates[k] = v
            if key_candidates:
                print(f'Extracted {len(key_candidates)} candidate key pairs from MMP player bundle')
                has_known_pattern = any(
                    len(k) >= 16 and len(v) >= 16 and k != v
                    for k, v in key_candidates.items()
                )
                if has_known_pattern:
                    return key_candidates
        except Exception as e:
            print('Failed to extract keys from player bundle:', e)
        return keys

    @classmethod
    def refreshKeysFromPlayerBundle(cls):
        cls._ensure_keys()
        bundle_url = cls._discoverPlayerBundleUrl()
        if not bundle_url:
            return False
        extracted = cls._extractKeysFromBundle(bundle_url)
        if extracted:
            new_count = sum(1 for k in extracted if k not in cls._mouflon_keys)
            cls._mouflon_keys.update(extracted)
            cls._save_keys()
            if new_count:
                print(f'Added {new_count} new keys from MMP player bundle')
            return True
        return False

    @classmethod
    def getInitialData(cls):
        session = requests.Session()
        r = session.get('https://stripchat.com/api/front/v3/config/static', headers=cls.headers, timeout=15)
        if r.status_code != 200:
            raise Exception("Failed to fetch static data from StripChat")
        StripChat._static_data = r.json().get('static')

        cls.refreshKeysFromGitHub()

    @classmethod
    def m3u_decoder(cls, content):
        _mouflon_filename = 'media.mp4'

        def _decode(encrypted_b64: str, key: str) -> str:
            if cls._cached_keys is None:
                cls._cached_keys = {}
            hash_bytes = cls._cached_keys[key] if key in cls._cached_keys \
                else cls._cached_keys.setdefault(key, hashlib.sha256(key.encode("utf-8")).digest())
            encrypted_data = base64.b64decode(encrypted_b64 + "==")
            return bytes(a ^ b for (a, b) in zip(encrypted_data, itertools.cycle(hash_bytes))).decode("utf-8")

        psch, pkey, pdkey = StripChat._getMouflonFromM3U(content)

        if psch == 'v1':
            _mouflon_file_attr = "#EXT-X-MOUFLON:FILE:"
        elif psch == 'v2':
            _mouflon_file_attr = "#EXT-X-MOUFLON:URI:"
        else:
            return None

        decoded = ''
        lines = content.splitlines()
        last_decoded_file = None
        for line in lines:
            if line.startswith(_mouflon_file_attr):
                if psch == 'v1':
                    last_decoded_file = _decode(line[len(_mouflon_file_attr):], pdkey)
                elif psch == 'v2':
                    uri = line[len(_mouflon_file_attr):]
                    encoded_part = uri.split('_')[-2]
                    decoded_part = _decode(encoded_part[::-1], pdkey)
                    last_decoded_file = uri.replace(encoded_part, decoded_part).split('/', maxsplit=4)[4]
            elif line.endswith(_mouflon_filename) and last_decoded_file:
                decoded += (line.replace(_mouflon_filename, last_decoded_file)) + '\n'
                last_decoded_file = None
            else:
                decoded += line + '\n'
        return decoded

    @classmethod
    def getMouflonDecKey(cls, pkey):
        cls._ensure_keys()
        if pkey in cls._mouflon_keys:
            return cls._mouflon_keys[pkey]
        return None

    @staticmethod
    def _getMouflonFromM3U(m3u8_doc):
        _start = 0
        _needle = '#EXT-X-MOUFLON:'
        while _needle in (_doc := m3u8_doc[_start:]):
            _mouflon_start = _doc.find(_needle)
            if _mouflon_start > 0:
                _mouflon = _doc[_mouflon_start:m3u8_doc.find('\n', _mouflon_start)].strip().split(':')
                psch = _mouflon[2]
                pkey = _mouflon[3]
                pdkey = StripChat.getMouflonDecKey(pkey)
                if pdkey:
                    return psch, pkey, pdkey
            _start += _mouflon_start + len(_needle)
        return None, None, None

    def getWebsiteURL(self):
        return "https://stripchat.com/" + self.username

    def getVideoUrl(self):
        return self.getWantedResolutionPlaylist(None)

    def getPlaylistVariants(self, url):
        url = "https://edge-hls.{host}/hls/{id}{vr}/master/{id}{vr}{auto}.m3u8".format(
                host='doppiocdn.' + random.choice(['com', 'net', 'org', 'media']),
                id=self.room_id,
                vr='_vr' if self.vr else '',
                auto='_auto' if not self.vr else ''
            )
        result = self.session.get(url, headers=self.headers, cookies=self.cookies, timeout=30)
        m3u8_doc = result.content.decode("utf-8")
        psch, pkey, pdkey = StripChat._getMouflonFromM3U(m3u8_doc)
        if pdkey is None:
            self.log(f'Failed to get mouflon decryption key for pkey={pkey}')
            return []
        variants = super().getPlaylistVariants(m3u_data=m3u8_doc)
        return [variant | {'url': f'{variant["url"]}{"&" if "?" in variant["url"] else "?"}psch={psch}&pkey={pkey}'}
                for variant in variants]

    @staticmethod
    def uniq(length=16):
        chars = ''.join(chr(i) for i in range(ord('a'), ord('z')+1))
        chars += ''.join(chr(i) for i in range(ord('0'), ord('9')+1))
        return ''.join(random.choice(chars) for _ in range(length))

    def _getStatusData(self, username):
        r = self.session.get(
            f'https://stripchat.com/api/front/v2/models/username/{username}/cam?uniq={StripChat.uniq()}',
            headers=self.headers,
            timeout=15
        )

        try:
            data = r.json()
        except requests.exceptions.JSONDecodeError:
            self.log('Failed to parse JSON response')
            return None
        return data

    def _update_lastInfo(self, data):
        if data is None:
            return None
        if 'cam' not in data:
            if 'error' in data:
                error = data['error']
                if error == 'Not Found':
                    return Status.NOTEXIST
                self.logger.warn(f'Status returned error: {error}')
            return Status.UNKNOWN

        self.lastInfo = {'model': data['user']['user']}
        if isinstance(data['cam'], dict):
            self.lastInfo |= data['cam']
        return None

    def getRoomIdFromUsername(self, username):
        if username == self.username and self.room_id is not None:
            return self.room_id

        data = self._getStatusData(username)
        if username == self.username:
            self._update_lastInfo(data)

        if 'user' not in data:
            return None
        if 'user' not in data['user']:
            return None
        if 'id' not in data['user']['user']:
            return None

        return str(data['user']['user']['id'])

    def getStatus(self):
        data = self._getStatusData(self.username)
        if data is None:
            return Status.UNKNOWN

        error = self._update_lastInfo(data)
        if error:
            return error

        if 'user' in data and 'user' in data['user']:
            model_data = data['user']['user']
            if model_data.get('gender'):
                self.gender = StripChat._GENDER_MAP.get(model_data.get('gender'))

            if model_data.get('country'):
                self.country = model_data.get('country', '').upper()
            elif model_data.get('languages'):
                for lang in model_data['languages']:
                    if lang.upper() in COUNTRIES:
                        self.country = lang.upper()
                        break

        status = self.lastInfo['model'].get('status')
        if status == "public" and self.lastInfo["isCamAvailable"] and self.lastInfo["isCamActive"]:
            return Status.PUBLIC
        if status in self._PRIVATE_STATUSES:
            return Status.PRIVATE
        if status in self._OFFLINE_STATUSES:
            return Status.OFFLINE
        if self.lastInfo['model'].get('isDeleted') is True:
            return Status.NOTEXIST
        if data['user'].get('isGeoBanned') is True:
            return Status.RESTRICTED
        self.logger.warn(f'Got unknown status: {status}')
        return Status.UNKNOWN

    @classmethod
    def getStatusBulk(cls, streamers, session=None):
        model_ids = {}
        for streamer in streamers:
            if not isinstance(streamer, StripChat):
                continue
            if streamer.room_id:
                model_ids[streamer.room_id] = streamer

        if session is None:
            session = requests.Session()
            session.headers.update(cls.headers)

        base_url = 'https://stripchat.com/api/front/models/list?'
        batch_num = 100
        data_map = {}
        model_id_list = list(model_ids)
        for _batch_ids in [model_id_list[i:i+batch_num] for i in range(0, len(model_id_list), batch_num)]:
            r = session.get(base_url + '&'.join(f'modelIds[]={model_id}' for model_id in _batch_ids), timeout=30)

            if not r.ok:
                r.raise_for_status()

            try:
                data = r.json()
            except requests.exceptions.JSONDecodeError:
                print('Failed to parse JSON response')
                return
            data_map |= {str(model['id']): model for model in data.get('models', [])}

        for model_id, streamer in model_ids.items():
            model_data = data_map.get(model_id)
            if not model_data:
                streamer.setStatus(Status.UNKNOWN)
                continue
            if model_data.get('gender'):
                streamer.gender = cls._GENDER_MAP.get(model_data.get('gender'))
            if model_data.get('country'):
                streamer.country = model_data.get('country', '').upper()
            status = model_data.get('status')
            if status == "public" and model_data.get("isOnline"):
                streamer.setStatus(Status.PUBLIC)
            elif status in cls._PRIVATE_STATUSES:
                streamer.setStatus(Status.PRIVATE)
            elif status in cls._OFFLINE_STATUSES:
                streamer.setStatus(Status.OFFLINE)
            else:
                print(f'[{streamer.siteslug}] {streamer.username}: Bulk update got unknown status: {status}')
                streamer.setStatus(Status.UNKNOWN)
