import errno
import io
import os
import subprocess
import sys
import tempfile
import time

import requests.cookies
from threading import Thread
from parameters import DEBUG, SEGMENT_TIME, CONTAINER, FFMPEG_PATH, FFMPEG_READRATE, STALL_TIMEOUT
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
    # A CDN that accepts the connection and then goes silent leaves ffmpeg
    # blocked in a socket read forever: the retry options above never fire
    # because nothing errors. 15s bounds every socket read so the fail-fast
    # paths actually get a chance to run.
    '-rw_timeout', '15000000',
]

# After this many "403 Forbidden" lines in the stderr log the watchdog
# terminates ffmpeg early. The bot then refreshes the session token instead
# of waiting out the (bounded) HLS retry loop. A single transient 403 is
# tolerated; a dead session produces a flood.
WATCHDOG_403_THRESHOLD = 3

# After a TLS reset on the init-segment keepalive, ffmpeg can re-parse the
# stream with a stale/garbled init and emit "Invalid NAL unit size" forever
# while writing nothing. A handful is normal at a segment edge; a burst means
# the recording is dead and must be restarted.
WATCHDOG_CORRUPT_THRESHOLD = 20


def getVideoFfmpeg(self, url, filename):
    stderr_path = filename + '.stderr.log'
    progress_path = filename + '.progress'
    cmd = [
        FFMPEG_PATH,
        '-user_agent', self.headers['User-Agent'],
        # Log only warnings/errors: at the default level CB's LLHLS playlists
        # produce hundreds of "Skip ('#EXT-X-PART:...')" parse notices and
        # segment-open lines per minute, drowning out the messages we
        # actually diagnose from.
        '-loglevel', 'warning',
        # Machine-readable progress. Unlike the stats line it is written at
        # every log level, so the stall watchdog keeps working while the log
        # stays quiet.
        '-progress', progress_path,
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

    # Sites hand back (video, audio) when the rendition has a separate audio
    # group, and None for the audio half when it does not. A None used to
    # reach the argv (and Popen), raising inside the worker thread and making
    # getVideo() report success for a recording that never started.
    if isinstance(url, tuple) and url[1]:
        video_url, audio_url = url
        cmd.extend(reconnect_opts + HLS_OPTS + ['-thread_queue_size', '1024', '-i', video_url])
        cmd.extend(reconnect_opts + HLS_OPTS + ['-thread_queue_size', '1024', '-i', audio_url])
        cmd.extend(['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-map', '0:v:0', '-map', '1:a:0'] + MOVFLAGS)
    else:
        if isinstance(url, tuple):
            url = url[0]
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
            # ffmpeg finalises the container when asked to quit, which is
            # worth waiting for on a normal stop. A failure path (stall, dead
            # session) has nothing left to write, and ffmpeg can sit in a
            # playlist-reload sleep without ever reading 'q', so those ask for
            # a short grace and get terminated instead of wasting the show.
            self.grace = 30

        def pls_stop(self, grace=None):
            if grace is not None:
                self.grace = grace
            self.stop = True

    stopping = _Stopper()
    error = False

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
            else:
                self.logger.error("Got OSError, errno: " + str(e.errno))
            error = True
            return
        except Exception as e:
            # Anything else (a bad option, a None that slipped into argv) must
            # not look like a completed recording.
            self.logger.error('Failed to start ffmpeg: ' + str(e))
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
                wrapper = io.TextIOWrapper(process.stderr, encoding='utf-8', errors='replace')
                try:
                    for line in wrapper:
                        if _NOISY not in line:
                            # ffmpeg's own output carries no timestamps, so a
                            # silent multi-hour stall is invisible after the
                            # fact; stamp every line as it arrives.
                            stderr_handle.write(time.strftime('%Y-%m-%d %H:%M:%S ') + line)
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
                        wrapper.close()
                    except Exception:
                        pass
                    try:
                        stderr_handle.flush()
                    except Exception:
                        pass
            filter_thread = Thread(target=filter_stderr, daemon=True)
            filter_thread.start()

        def watch_output():
            """Kill ffmpeg when the CDN session dies or output stops.

            The 403/corrupt counters only see errors ffmpeg actually writes.
            A stream that simply goes quiet (socket alive, no new segments)
            writes nothing at all, which is the failure that used to record
            nothing for hours while looking healthy. The -progress file is
            the signal for that case and needs no DEBUG.
            """
            nonlocal error
            forbidden = 0
            corrupt = 0
            position = 0
            last_us = None
            last_progress = time.monotonic()
            progress_readable = False
            progress_disabled = False
            while process.poll() is None and not stopping.stop:
                if DEBUG:
                    try:
                        with open(stderr_path, 'r', errors='replace') as f:
                            f.seek(position)
                            chunk = f.read()
                            position = f.tell()
                            forbidden += chunk.count('403 Forbidden')
                            corrupt += chunk.count('Invalid NAL unit size')
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
                        stopping.pls_stop(grace=5)
                        return
                    if corrupt >= WATCHDOG_CORRUPT_THRESHOLD:
                        self.logger.warning('ffmpeg is emitting corrupt-stream errors (stale init segment?), restarting recording')
                        stopping.pls_stop(grace=5)
                        return
                if not progress_disabled:
                    try:
                        us = None
                        with open(progress_path, 'r', errors='replace') as f:
                            for line in f:
                                if line.startswith('out_time_us='):
                                    try:
                                        us = int(line.split('=', 1)[1])
                                    except ValueError:
                                        pass
                        progress_readable = True
                        if us is not None and us != last_us:
                            last_us = us
                            last_progress = time.monotonic()
                    except OSError:
                        if progress_readable:
                            # Can't measure progress any more: stop judging
                            # rather than risk killing a healthy recording.
                            progress_disabled = True
                            progress_readable = False
                            self.logger.warning('Cannot read ffmpeg progress file, stall detection disabled for this recording')
                if progress_readable and time.monotonic() - last_progress > STALL_TIMEOUT:
                    self.logger.warning(
                        'ffmpeg made no output progress for %ds (stalled stream?), restarting the recording', STALL_TIMEOUT)
                    if hasattr(self, 'lastInfo') and isinstance(self.lastInfo, dict):
                        self.lastInfo.pop('url', None)
                    if hasattr(self, '_current_edge') and hasattr(self, '_exclude_edge'):
                        self._exclude_edge = self._current_edge
                    # Take the bot's error path: keep the log/progress files
                    # as evidence and let it refetch a fresh session token.
                    error = True
                    stopping.pls_stop(grace=5)
                    return
                time.sleep(1)

        Thread(target=watch_output, daemon=True).start()

        try:
            while process.poll() is None:
                if stopping.stop:
                    try:
                        try:
                            process.stdin.write(b'q')
                            process.stdin.flush()
                        except (BrokenPipeError, OSError):
                            pass
                        process.wait(timeout=stopping.grace)
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
            if process.stdin:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            if stderr_handle:
                stderr_handle.close()
            if not error and DEBUG and os.path.exists(stderr_path):
                # Only keep the stderr log for failed runs; a clean recording
                # shouldn't litter the downloads folder with .stderr.log files.
                try:
                    os.remove(stderr_path)
                except OSError:
                    pass
            if not error and os.path.exists(progress_path):
                # Kept on failure: its last out_time_us=/speed= is the only
                # record of where a stalled recording stopped making progress.
                try:
                    os.remove(progress_path)
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
