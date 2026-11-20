"""Audio/video sync regression test for the two-input (separate audio) mux path.

Chaturbate hands back a ``(video_url, audio_url)`` pair: two separate live
HLS renditions. Each input is opened at its own last segment, so their first
timestamps differ by about one segment. ffmpeg without ``-copyts`` normalizes
every input's start to zero independently, which discards that difference and
plays the audio against video from a different point in time -- a constant
offset for the whole recording (the "video and audio is out of sync" bug).

This test builds the same situation deterministically:

* a video-only HLS rendition and an audio-only HLS rendition of one source,
  both carrying markers (white flash / 1 kHz click) at identical source times;
* an audio playlist that starts at segment 2, i.e. the audio joins 4 s into
  the source, the way a live rendition's window sits ahead of the video one;
* the real ``getVideoFfmpeg`` muxes the two, and the markers in the resulting
  file are measured. Both renditions share one timeline, so an in-sync file
  must have the audio click for source t=7.3 s at file time 7.3 s - v0, with
  v0 the video start.

Stdlib only (unittest) plus ffmpeg on PATH.

Run:  python -m unittest discover -s tests -p "test_av_sync.py" -v
"""
import http.server
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

FFMPEG = os.environ.get('STRMNTR_FFMPEG_PATH', 'ffmpeg')

DUR = 14                      # source length
SEG = 2                       # hls segment length
MARKERS = [0.7, 3.1, 7.3, 11.9]   # irregular: an A/V shift cannot alias to zero
AUDIO_START_SEG = 2           # audio rendition joins at source t=4 s
FIRST_AUDIO_MARKER = MARKERS[2]   # only this one and later survive the late join
TOLERANCE = 0.3               # seconds; the bug produces ~4 s

_TMP = tempfile.mkdtemp(prefix='strmntr-avsync-')
_MEDIA = os.path.join(_TMP, 'media')


def _sh(cmd, cwd=None):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)


def _hls(src_args, out_dir, prefix):
    os.makedirs(out_dir, exist_ok=True)
    r = _sh([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y'] + src_args + [
        '-f', 'hls', '-hls_time', str(SEG), '-hls_list_size', '0',
        '-hls_playlist_type', 'vod',
        '-hls_segment_filename', os.path.join(out_dir, prefix + '%03d.ts'),
        os.path.join(out_dir, 'index.m3u8')])
    if r.returncode:
        raise RuntimeError('hls build failed: %s' % r.stderr.decode('utf-8', 'replace'))


def _build_media():
    """Video-only + audio-only HLS of one source, audio joined AUDIO_START_SEG late."""
    video = os.path.join(_MEDIA, 'video')
    audio = os.path.join(_MEDIA, 'audio')
    audio_late = os.path.join(_MEDIA, 'audio_late')

    flash = '+'.join('between(T,%.2f,%.2f)' % (m - 0.01, m + 0.06) for m in MARKERS)
    _hls(['-f', 'lavfi', '-i', 'color=c=black:s=320x240:r=25:d=%d' % DUR,
          '-vf', "geq=lum='if(%s,235,20)':cb=128:cr=128" % flash,
          '-c:v', 'libx264', '-preset', 'ultrafast', '-g', '25', '-pix_fmt', 'yuv420p'],
         video, 'v')

    click = '+'.join('lt(abs(t-%.2f),0.03)' % m for m in MARKERS)
    _hls(['-f', 'lavfi', '-i', "aevalsrc='if(%s,0.9*sin(2*PI*1000*t),0)':s=48000:d=%d"
          % (click, DUR),
          '-c:a', 'aac', '-ar', '48000'],
         audio, 'a')

    # The "late join": the audio playlist starts at segment AUDIO_START_SEG, so
    # its first segment carries source t>=4 s. Same as a live audio rendition
    # whose window is a segment ahead of the video one.
    os.makedirs(audio_late, exist_ok=True)
    with open(os.path.join(audio, 'index.m3u8'), encoding='utf-8') as fh:
        lines = fh.read().splitlines()
    out, dropped = [], 0
    for line in lines:
        if line.startswith('#EXT-X-MEDIA-SEQUENCE:'):
            continue
        m = re.match(r'^a\d+\.ts$', line)
        if m and dropped < AUDIO_START_SEG:
            out.pop()          # drop the #EXTINF that goes with it
            dropped += 1
            continue
        out.append(line)
    out.insert(out.index('#EXTM3U') + 1, '#EXT-X-MEDIA-SEQUENCE:%d' % AUDIO_START_SEG)
    with open(os.path.join(audio_late, 'index.m3u8'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out) + '\n')
    for name in os.listdir(audio):
        if name.endswith('.ts'):
            with open(os.path.join(audio, name), 'rb') as src, \
                    open(os.path.join(audio_late, name), 'wb') as dst:
                dst.write(src.read())


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        kwargs.pop('directory', None)
        super().__init__(*args, directory=_MEDIA, **kwargs)

    def log_message(self, *args):
        pass


_SERVER = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _QuietHandler)
_BASE = 'http://127.0.0.1:%d' % _SERVER.server_address[1]

_build_media()
threading.Thread(target=_SERVER.serve_forever, daemon=True).start()


def tearDownModule():
    _SERVER.shutdown()
    _SERVER.server_close()


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
    def __init__(self):
        self.headers = {'User-Agent': 'streamonitor-avsync-test'}
        self.cookies = None
        self.logger = StubLogger()
        self.lastInfo = {}
        self.video_url_timeout = None
        self.stopDownload = None


def measure(path, cwd):
    """Return (flash_times, click_times) in the recorded file's timeline."""
    stats = 'stats.txt'
    stats_path = os.path.join(cwd, stats)
    if os.path.exists(stats_path):
        os.remove(stats_path)
    _sh([FFMPEG, '-hide_banner', '-nostats', '-y', '-i', path,
         '-vf', 'signalstats,metadata=mode=print:key=lavfi.signalstats.YAVG:file=' + stats,
         '-f', 'null', '-'], cwd=cwd)

    frames, pts = [], None
    with open(stats_path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            m = re.search(r'pts_time:([0-9.]+)', line)
            if m:
                pts = float(m.group(1))
            m = re.search(r'YAVG=([0-9.]+)', line)
            if m and pts is not None:
                frames.append((pts, float(m.group(1))))
    flashes = []
    for t, y in frames:
        if y <= 100:
            continue
        if flashes and t - flashes[-1][-1] <= 0.2:
            flashes[-1].append(t)
        else:
            flashes.append([t])
    flashes = [sum(g) / len(g) for g in flashes]

    r = subprocess.run([FFMPEG, '-hide_banner', '-nostats', '-i', path,
                        '-af', 'silencedetect=n=-35dB:d=0.03', '-f', 'null', '-'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    clicks = [float(x) for x in
              re.findall(r'silence_end: ([0-9.]+)', r.stderr.decode('utf-8', 'replace'))]
    # The last silence_end is the end of file's trailing silence; the caller
    # only anchors on the first click, which is a real marker onset.
    return flashes, clicks


class AVSyncTest(unittest.TestCase):
    def test_separate_audio_rendition_stays_in_sync(self):
        import parameters
        from streamonitor.downloaders.ffmpeg import getVideoFfmpeg

        ext = parameters.CONTAINER
        filename = os.path.join(_TMP, 'sync.%s' % ext)
        stub = StubBot()

        result = {}
        thread = threading.Thread(
            target=lambda: result.update(
                ret=getVideoFfmpeg(stub, (_BASE + '/video/index.m3u8',
                                          _BASE + '/audio_late/index.m3u8'), filename)),
            daemon=True)
        thread.start()
        deadline = time.monotonic() + 180
        while thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.5)
        if thread.is_alive():
            if stub.stopDownload:
                stub.stopDownload()
            thread.join(30)
            self.fail('the two-input recording never finished')

        self.assertTrue(result.get('ret'),
                        'recording failed: %s' % stub.logger.messages)
        self.assertTrue(os.path.exists(filename) and os.path.getsize(filename) > 0,
                        'no output file was written')

        flashes, clicks = measure(filename, _TMP)
        self.assertGreaterEqual(len(flashes), 2,
                                'flash markers not found in the recording: %s' % (flashes,))
        self.assertTrue(clicks, 'click markers not found in the recording')

        # Video content t appears at file time t - v0; the audio content that
        # joined 4 s late must land on the same timeline.
        v0 = flashes[0] - MARKERS[0]
        offset = clicks[0] + v0 - FIRST_AUDIO_MARKER
        self.assertLess(
            abs(offset), TOLERANCE,
            'audio and video are %.2fs out of sync (flashes=%s, clicks=%s, v0=%.2f)'
            % (offset, [round(f, 2) for f in flashes],
               [round(c, 2) for c in clicks], v0))

        # Keeping the input timelines must not leave the file starting at the
        # show's absolute timestamp (hours in on a long-running stream).
        start = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=start_time',
             '-of', 'csv=p=0', filename],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
        start = float(start.decode('utf-8', 'replace').strip() or 0)
        self.assertLess(abs(start), 0.5,
                        'the recording starts at %.2fs instead of 0' % start)


if __name__ == '__main__':
    unittest.main(verbosity=2)
