import errno
import io
import os
import subprocess
import sys
import tempfile
import time

import requests.cookies
from threading import Thread
from parameters import DEBUG, SEGMENT_TIME, CONTAINER, FFMPEG_PATH, FFMPEG_READRATE
from streamonitor.utils.cookies import dump_cookies_to_netscape

MOVFLAGS = ['-movflags', '+frag_keyframe+empty_moov'] if CONTAINER == 'mp4' else []

# HLS demuxer retry bounds. Without these, a dead edge session token (HTTP
# 403 from the CDN) makes the protocol layer reconnect-loop for the whole
# recording instead of failing fast so the bot can fetch a fresh token.
HLS_OPTS = [
    '-max_reload', '20',
    '-seg_max_retry', '20',
    '-m3u8_hold_counters', '20',
    '-live_start_index', '-1',
]

# After this many "403 Forbidden" lines in the stderr log the watchdog
# terminates ffmpeg early. The bot then refreshes the session token instead
# of waiting out the (bounded) HLS retry loop. A single transient 403 is
# tolerated; a dead session produces a flood.
WATCHDOG_403_THRESHOLD = 3


def getVideoFfmpeg(self, url, filename):
    cmd = [
        FFMPEG_PATH,
        '-user_agent', self.headers['User-Agent'],
        # Log only warnings/errors: at the default level CB's LLHLS playlists
        # produce hundreds of "Skip ('#EXT-X-PART:...')" parse notices and
        # segment-open lines per minute, drowning out the messages we
        # actually diagnose from.
        '-loglevel', 'warning',
    ]

    cookie_file = None
    if type(self.cookies) is requests.cookies.RequestsCookieJar and len(self.cookies) > 0:
        cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.cookies.txt', delete=False)
        dump_cookies_to_netscape(self.cookies, cookie_file.name)
        cookie_file.close()
        cmd.extend(['-cookies', cookie_file.name])

    if FFMPEG_READRATE:
        cmd.extend(['-readrate', f'{FFMPEG_READRATE!s}'])

    # Note: no -reconnect_at_eof here. For HLS, the playlist response ending
    # (EOF) is normal, and reconnecting on EOF makes ffmpeg refetch the whole
    # playlist on every poll and, once the session dies, spin in a 403 loop
    # that balloons the stderr log to hundreds of MB. -reconnect 1 +
    # -reconnect_streamed still recover genuine mid-transfer drops.
    reconnect_opts = [
        '-reconnect', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '10',
    ]

    if isinstance(url, tuple):
        video_url, audio_url = url
        cmd.extend(reconnect_opts + HLS_OPTS + ['-thread_queue_size', '1024', '-i', video_url])
        cmd.extend(reconnect_opts + HLS_OPTS + ['-thread_queue_size', '1024', '-i', audio_url])
        cmd.extend(['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-map', '0:v:0', '-map', '1:a:0'] + MOVFLAGS)
    else:
        cmd.extend(reconnect_opts + HLS_OPTS + ['-thread_queue_size', '1024',
            '-i', url,
            '-c:a', 'copy',
            '-c:v', 'copy',
        ] + MOVFLAGS)

    timeout = getattr(self, 'video_url_timeout', None)
    if timeout:
        cmd.extend(['-t', str(timeout)])

    suffix = ''
    if hasattr(self, 'filename_extra_suffix'):
        suffix = self.filename_extra_suffix

    if SEGMENT_TIME is not None:
        username = filename.rsplit('-', maxsplit=2)[0]
        cmd.extend([
            '-f', 'segment',
            '-reset_timestamps', '1',
            '-segment_time', str(SEGMENT_TIME),
            '-strftime', '1',
        ] + MOVFLAGS + [f'{username}-%Y%m%d-%H%M%S{suffix}.{CONTAINER}'])
    else:
        cmd.extend([
            os.path.splitext(filename)[0] + suffix + '.' + CONTAINER
        ])

    class _Stopper:
        def __init__(self):
            self.stop = False

        def pls_stop(self):
            self.stop = True

    stopping = _Stopper()
    error = False
    stderr_path = filename + '.stderr.log'

    def execute():
        nonlocal error
        stderr_handle = None
        process = None
        filter_thread = None
        try:
            stderr_handle = open(stderr_path, 'w', buffering=1) if DEBUG else None
            if stderr_handle:
                # First line of the log records the exact command, so a pasted
                # log proves which options the *running* image actually used.
                stderr_handle.write('[streamonitor] argv: ' + subprocess.list2cmdline(cmd) + '\n')
                stderr_handle.flush()
            # Pipe stderr through a filter thread (below) that drops
            # known-benign noise before it reaches the log file.
            stderr = subprocess.PIPE if DEBUG else subprocess.DEVNULL
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(
                args=cmd, stdin=subprocess.PIPE, stderr=stderr, stdout=subprocess.DEVNULL, startupinfo=startupinfo)
        except OSError as e:
            if e.errno == errno.ENOENT:
                self.logger.error('FFMpeg executable not found!')
                error = True
                return
            else:
                self.logger.error("Got OSError, errno: " + str(e.errno))
                error = True
                return

        if process is None:
            if stderr_handle:
                stderr_handle.close()
            return

        # CB's LLHLS wraps every CMAF chunk in its own moov box, so ffmpeg
        # logs this notice once per segment part. It is harmless and the last
        # thing spamming the log; drop it (the watchdog still sees every
        # warning and error line).
        _NOISY = 'Found duplicated MOOV Atom. Skipped it'
        if stderr_handle and process.stderr:
            def filter_stderr():
                try:
                    for line in io.TextIOWrapper(process.stderr, encoding='utf-8', errors='replace'):
                        if _NOISY not in line:
                            stderr_handle.write(line)
                except Exception:
                    # If writing the log fails (e.g. disk full), keep draining
                    # the pipe so ffmpeg never blocks on stderr output.
                    try:
                        while process.stderr.read(65536):
                            pass
                    except Exception:
                        pass
                finally:
                    try:
                        stderr_handle.flush()
                    except Exception:
                        pass
            filter_thread = Thread(target=filter_stderr, daemon=True)
            filter_thread.start()

        def watch_stderr():
            """Kill ffmpeg early when the CDN starts 403ing (dead session token).

            The HLS retry options above already bound ffmpeg's retries, but a
            dead session still spends minutes retrying before the bot can
            refresh the token. Watching the stderr log for a flood of 403s
            lets us fail fast and hand control back to the bot for a fresh
            token immediately.
            """
            if not DEBUG:
                return
            forbidden = 0
            position = 0
            try:
                while process.poll() is None and not stopping.stop:
                    try:
                        with open(stderr_path, 'r', errors='replace') as f:
                            f.seek(position)
                            chunk = f.read()
                            position = f.tell()
                            forbidden += chunk.count('403 Forbidden')
                    except OSError:
                        pass
                    if forbidden >= WATCHDOG_403_THRESHOLD:
                        self.logger.warning('CDN returned 403 repeatedly (session expired?), stopping ffmpeg to refresh token')
                        # Invalidate the cached edge URL so the next
                        # getVideoUrl() fetches a fresh session token instead
                        # of reusing the dead one (chaturbate only refreshes
                        # on age >= timeout).
                        if hasattr(self, 'lastInfo') and isinstance(self.lastInfo, dict):
                            self.lastInfo.pop('url', None)
                        # If the site supports edge exclusion (chaturbate
                        # does), steer the next getStatus() to a different
                        # edge instead of bouncing back to the failing one.
                        if hasattr(self, '_current_edge') and hasattr(self, '_exclude_edge'):
                            self._exclude_edge = self._current_edge
                        stopping.pls_stop()
                        return
                    time.sleep(1)
            except Exception:
                pass

        if DEBUG:
            Thread(target=watch_stderr, daemon=True).start()

        try:
            while process.poll() is None:
                if stopping.stop:
                    try:
                        try:
                            process.stdin.write(b'q')
                            process.stdin.flush()
                        except (BrokenPipeError, OSError):
                            pass
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                    break
                try:
                    process.wait(1)
                except subprocess.TimeoutExpired:
                    pass

            if process.returncode and process.returncode != 0 and process.returncode != 255:
                self.logger.error('The process exited with an error. Return code: ' + str(process.returncode))
                error = True
        finally:
            if filter_thread is not None:
                filter_thread.join(timeout=5)
            if stderr_handle:
                stderr_handle.close()
            if not error and DEBUG and os.path.exists(stderr_path):
                # Only keep the stderr log for failed runs; a clean recording
                # shouldn't litter the downloads folder with .stderr.log files.
                try:
                    os.remove(stderr_path)
                except OSError:
                    pass

    thread = Thread(target=execute)
    thread.start()
    self.stopDownload = lambda: stopping.pls_stop()
    thread.join()
    self.stopDownload = None
    if cookie_file:
        try:
            os.remove(cookie_file.name)
        except OSError:
            pass
    return not error
