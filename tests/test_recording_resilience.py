"""Recording-resilience tests.

Covers the behaviours a recording must have to survive a flaky CDN:
a stalled stream is restarted instead of recording nothing, a silent
server cannot block forever, a ``(video, None)`` audio pair still
records, failed parts are kept for the final merge, and stderr log lines
carry timestamps. Stdlib only (unittest) - the repo has no test suite.

Run:  python -m unittest discover -s tests -p "test_recording_resilience.py" -v
(needs requests, m3u8 and django-environ installed, plus ffmpeg on PATH)
"""
import http.server
import logging
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_TMP = Path(tempfile.mkdtemp(prefix='strmntr-tests-'))
MEDIA = _TMP / 'media'
DOWNLOADS = _TMP / 'downloads'
MEDIA.mkdir()
DOWNLOADS.mkdir()

# parameters.py reads these at import time, and read_env() never overrides
# values already in the environment, so set them before importing the app.
os.environ.update({
    'STRMNTR_DEBUG': '1',
    'STRMNTR_DOWNLOAD_DIR': str(DOWNLOADS),
    'STRMNTR_CONTAINER': 'mp4',
    'STRMNTR_FFMPEG_READRATE': '0',
    'STRMNTR_STALL_TIMEOUT': '5',
})

FFMPEG = os.environ.get('STRMNTR_FFMPEG_PATH', 'ffmpeg')

import parameters  # noqa: E402
from streamonitor.bot import Bot  # noqa: E402
from streamonitor.downloaders.ffmpeg import getVideoFfmpeg  # noqa: E402
from streamonitor.enums import Status  # noqa: E402


def _out(name):
    """Recording path with the configured container extension."""
    return str(DOWNLOADS / ('%s.%s' % (name, parameters.CONTAINER)))


def _build_media():
    """VOD playlist (ends) plus a live playlist that never grows."""
    vod = MEDIA / 'vod'
    vod.mkdir()
    subprocess.run(
        [FFMPEG, '-hide_banner', '-loglevel', 'error', '-y',
         '-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=30', '-t', '6',
         '-c:v', 'libx264', '-preset', 'ultrafast', '-g', '30',
         '-f', 'hls', '-hls_time', '2',
         '-hls_segment_filename', str(vod / 'seg%d.ts'),
         '-hls_list_size', '0', '-hls_playlist_type', 'vod',
         str(vod / 'index.m3u8')],
        check=True)

    # No ENDLIST and a long target duration: ffmpeg consumes the segments
    # then waits for media that never arrives, exactly like a CDN session
    # that stays connected but stopped producing.
    stall = MEDIA / 'stall'
    stall.mkdir()
    for f in vod.iterdir():
        if f.suffix == '.ts':
            shutil.copyfile(f, stall / f.name)
    (stall / 'index.m3u8').write_text(
        '#EXTM3U\n'
        '#EXT-X-VERSION:3\n'
        '#EXT-X-TARGETDURATION:30\n'
        '#EXT-X-MEDIA-SEQUENCE:0\n'
        '#EXTINF:2.000000,\nseg0.ts\n'
        '#EXTINF:2.000000,\nseg1.ts\n'
        '#EXTINF:2.000000,\nseg2.ts\n',
        encoding='utf-8')

    # A playable file the merge test can concatenate.
    subprocess.run(
        [FFMPEG, '-hide_banner', '-loglevel', 'error', '-y',
         '-f', 'lavfi', '-i', 'testsrc2=size=320x240:rate=30', '-t', '1',
         '-c:v', 'libx264', '-preset', 'ultrafast',
         str(MEDIA / ('tiny.%s' % parameters.CONTAINER))],
        check=True)


_build_media()


def tearDownModule():
    _SERVER.shutdown()
    print('\nartifacts left in: %s' % _TMP)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(MEDIA), **kwargs)

    def log_message(self, *args):
        pass


_SERVER = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _QuietHandler)
BASE = 'http://127.0.0.1:%d' % _SERVER.server_address[1]
threading.Thread(target=_SERVER.serve_forever, daemon=True).start()


class StubLogger:
    def __init__(self):
        self.messages = []

    def _add(self, level, msg, *args):
        try:
            text = msg % args if args else str(msg)
        except Exception:
            text = '%s %s' % (msg, args)
        self.messages.append('%s: %s' % (level, text))

    def info(self, msg, *args):
        self._add('info', msg, *args)

    def warning(self, msg, *args):
        self._add('warning', msg, *args)

    def error(self, msg, *args):
        self._add('error', msg, *args)


class StubBot:
    """Minimal stand-in for Bot: getVideoFfmpeg only needs these."""

    def __init__(self):
        self.headers = {'User-Agent': 'streamonitor-tests'}
        self.cookies = None
        self.logger = StubLogger()
        self.lastInfo = {}
        self.video_url_timeout = None
        self.stopDownload = None


def run_recording(stub, url, filename, deadline):
    """Call getVideoFfmpeg, returning None if it never returns in time."""
    result = {}

    def call():
        result['ret'] = getVideoFfmpeg(stub, url, filename)

    thread = threading.Thread(target=call, daemon=True)
    thread.start()
    thread.join(deadline)
    if thread.is_alive():
        for _ in range(50):
            if stub.stopDownload:
                break
            time.sleep(0.1)
        if stub.stopDownload:
            stub.stopDownload()
        thread.join(20)
        return None
    return result.get('ret')


class StallDetectionTest(unittest.TestCase):
    def test_stalled_stream_is_restarted_instead_of_recording_nothing(self):
        filename = _out('stall')
        stub = StubBot()

        start = time.monotonic()
        ret = run_recording(stub, BASE + '/stall/index.m3u8', filename, deadline=60)
        elapsed = time.monotonic() - start

        self.assertIsNotNone(
            ret, 'getVideoFfmpeg never returned: a stalled stream was not detected')
        self.assertFalse(ret, 'a stalled stream must be reported as a failed recording')
        self.assertLess(elapsed, 40, 'the stall took too long to detect')
        self.assertTrue(
            any('stall' in m.lower() for m in stub.logger.messages),
            'expected a stall warning, got: %s' % stub.logger.messages)

    def test_healthy_recording_is_not_killed(self):
        filename = _out('healthy')
        stub = StubBot()

        start = time.monotonic()
        ret = run_recording(stub, BASE + '/vod/index.m3u8', filename, deadline=45)
        elapsed = time.monotonic() - start

        self.assertIsNotNone(ret, 'getVideoFfmpeg never returned for a healthy playlist')
        self.assertTrue(ret, 'a healthy recording must succeed: %s' % stub.logger.messages)
        self.assertTrue(os.path.getsize(filename) > 0, 'no output file was written')
        self.assertLess(elapsed, 40, 'a healthy recording must not wait for the stall timeout')


class HungSocketTest(unittest.TestCase):
    def test_silent_server_does_not_block_forever(self):
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        held = []

        def hold():
            conn, _ = listener.accept()
            held.append(conn)
            time.sleep(120)

        threading.Thread(target=hold, daemon=True).start()

        filename = _out('hung')
        stub = StubBot()
        start = time.monotonic()
        ret = run_recording(stub, 'http://127.0.0.1:%d/live.m3u8' % port, filename, deadline=75)
        elapsed = time.monotonic() - start

        self.assertIsNotNone(
            ret, 'ffmpeg blocked forever on a server that accepted and never replied')
        self.assertFalse(ret)
        self.assertLess(elapsed, 60, 'the hung connection took too long to give up')


class MissingAudioUrlTest(unittest.TestCase):
    def test_recording_with_missing_audio_url_produces_a_file(self):
        filename = _out('noaudio')
        stub = StubBot()

        ret = run_recording(
            stub, (BASE + '/vod/index.m3u8', None), filename, deadline=45)

        self.assertIsNotNone(ret, 'getVideoFfmpeg never returned for a (video, None) pair')
        self.assertTrue(ret, '(video, None) must record: %s' % stub.logger.messages)
        self.assertTrue(
            os.path.exists(filename) and os.path.getsize(filename) > 0,
            'a (video, None) pair produced no recording')


class StderrLogTest(unittest.TestCase):
    def test_failed_run_log_lines_carry_timestamps(self):
        filename = _out('timestamped')
        stub = StubBot()

        ret = run_recording(stub, BASE + '/nope/index.m3u8', filename, deadline=60)

        self.assertFalse(ret)
        log_path = filename + '.stderr.log'
        self.assertTrue(os.path.exists(log_path), 'no stderr log for a failed run')
        with open(log_path, encoding='utf-8', errors='replace') as fh:
            lines = [l for l in fh.read().splitlines() if l.strip()]
        body = [l for l in lines if not l.startswith('[streamonitor] argv:')]
        self.assertTrue(body, 'the stderr log has no ffmpeg output')
        for line in body:
            self.assertRegex(
                line, r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ',
                'stderr line is not timestamped: %r' % line)


class StallingSite(Bot):
    """A site whose stream always stalls, so the bot must restart it."""
    site = 'TestStallSite'
    siteslug = 'TSS'
    sleep_on_offline = 1
    sleep_on_long_offline = 1
    sleep_on_error = 1
    sleep_on_private = 1
    sleep_on_ratelimit = 1
    sleep_on_recording_error = 1

    def __init__(self, username, url):
        self._url = url
        self.url_calls = 0
        super().__init__(username)

    def getWebsiteURL(self):
        return BASE + '/'

    def getStatus(self):
        return Status.PUBLIC

    def getVideoUrl(self):
        self.url_calls += 1
        return self._url


class MergePartsTest(unittest.TestCase):
    def test_merge_skips_empty_parts_instead_of_failing(self):
        bot = StallingSite('mergeuser', BASE + '/vod/index.m3u8')
        folder = bot.outputFolder
        os.makedirs(folder, exist_ok=True)
        ext = parameters.CONTAINER
        good = os.path.join(folder, 'good.' + ext)
        shutil.copyfile(str(MEDIA / ('tiny.' + ext)), good)
        empty = os.path.join(folder, 'empty.' + ext)
        open(empty, 'wb').close()
        missing = os.path.join(folder, 'missing.' + ext)

        # One empty part used to abort the whole concat, leaving every
        # fragment on disk unmerged.
        messages = []
        handler = logging.Handler()
        handler.emit = lambda record: messages.append(record.getMessage())
        bot.logger.addHandler(handler)
        try:
            bot._merge_parts([empty, good, missing], clear_manifest=False)
        finally:
            bot.logger.removeHandler(handler)

        self.assertFalse(os.path.exists(empty), 'the empty part was not cleaned up')
        self.assertTrue(
            os.path.exists(good) and os.path.getsize(good) > 0,
            'the usable part did not survive the merge')
        self.assertFalse(
            any('Merge failed' in m for m in messages),
            'the merge failed instead of skipping the empty part: %s' % messages)


class BotRestartTest(unittest.TestCase):
    def test_failed_recording_keeps_its_part_and_restarts(self):
        bot = StallingSite('partsuser', BASE + '/stall/index.m3u8')
        bot.running = True
        bot.start()
        manifest_text = ''
        kept_part = None
        try:
            # Wait until both facts hold: the failed part was kept in the
            # merge manifest, and the bot started another attempt.
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                manifest = os.path.join(bot.outputFolder, '.parts.txt')
                if os.path.exists(manifest):
                    with open(manifest, encoding='utf-8') as fh:
                        text = fh.read()
                    parts = [l.strip() for l in text.splitlines() if l.strip()]
                    nonempty = [p for p in parts
                                if os.path.exists(p) and os.path.getsize(p) > 0]
                    if nonempty:
                        manifest_text = text
                        kept_part = nonempty[0]
                if manifest_text and bot.url_calls >= 2:
                    break
                time.sleep(0.5)

            self.assertGreaterEqual(
                bot.url_calls, 2,
                'the bot did not restart the recording after the stall')
            self.assertTrue(
                manifest_text,
                'no .parts.txt listing a non-empty kept part was written')
            self.assertTrue(
                os.path.exists(kept_part) and os.path.getsize(kept_part) > 0,
                'the kept part is empty: %s' % kept_part)
        finally:
            bot.stop(None, None)
            bot.quitting = True
            bot.join(60)


if __name__ == '__main__':
    unittest.main(verbosity=2)
