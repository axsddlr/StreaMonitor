import errno
import os
import subprocess
import sys

import requests.cookies
from threading import Thread
from parameters import DEBUG, SEGMENT_TIME, CONTAINER, FFMPEG_PATH, FFMPEG_READRATE


def getVideoFfmpeg(self, url, filename):
    cmd = [
        FFMPEG_PATH,
        '-user_agent', self.headers['User-Agent']
    ]

    if type(self.cookies) is requests.cookies.RequestsCookieJar:
        cookies_text = ''
        for cookie in self.cookies:
            cookies_text += cookie.name + "=" + cookie.value + "; path=" + cookie.path + '; domain=' + cookie.domain + '\n'
        if len(cookies_text) > 10:
            cookies_text = cookies_text[:-1]
        cmd.extend([
            '-cookies', cookies_text
        ])

    if FFMPEG_READRATE:
        cmd.extend(['-readrate', f'{FFMPEG_READRATE!s}'])

    reconnect_opts = [
        '-reconnect', '1',
        '-reconnect_streamed', '1',
        '-reconnect_at_eof', '1',
        '-reconnect_delay_max', '10',
    ]

    if isinstance(url, tuple):
        video_url, audio_url = url
        cmd.extend(reconnect_opts + ['-i', video_url])
        cmd.extend(reconnect_opts + ['-i', audio_url])
        cmd.extend(['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-map', '0:v:0', '-map', '1:a:0', '-movflags', '+frag_keyframe+empty_moov'])
    else:
        cmd.extend(reconnect_opts + [
            '-max_reload', '20',
            '-seg_max_retry', '20',
            '-m3u8_hold_counters', '20',
            '-live_start_index', '-1',
            '-i', url,
            '-c:a', 'copy',
            '-c:v', 'copy',
            '-movflags', '+frag_keyframe+empty_moov',
        ])

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
            '-movflags', '+frag_keyframe+empty_moov',
            f'{username}-%Y%m%d-%H%M%S{suffix}.{CONTAINER}'
        ])
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

    def execute():
        nonlocal error
        stderr_handle = None
        process = None
        try:
            stderr_handle = open(filename + '.stderr.log', 'w') if DEBUG else None
            stderr = stderr_handle if stderr_handle else subprocess.DEVNULL
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

        try:
            while process.poll() is None:
                if stopping.stop:
                    try:
                        process.communicate(b'q', timeout=30)
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
            if stderr_handle:
                stderr_handle.close()

    thread = Thread(target=execute)
    thread.start()
    self.stopDownload = lambda: stopping.pls_stop()
    thread.join()
    self.stopDownload = None
    return not error
