import m3u8
import os
import subprocess
from threading import Thread
from ffmpy import FFmpeg, FFRuntimeError
from time import sleep
from parameters import DEBUG, CONTAINER, SEGMENT_TIME, FFMPEG_PATH

_http_lib = None
if not _http_lib:
    try:
        import pycurl_requests as requests
        _http_lib = 'pycurl'
    except ImportError:
        pass
if not _http_lib:
    try:
        import requests
        _http_lib = 'requests'
    except ImportError:
        pass
if not _http_lib:
    raise ImportError("Please install requests or pycurl package to proceed")


def getVideoNativeHLS(self, url, filename, m3u_processor=None):
    self.stopDownloadFlag = False
    error = False
    error_reason = None
    tmpfilename = filename[:-len('.' + CONTAINER)] + '.tmp.ts'
    session = requests.Session()

    def execute():
        nonlocal error, error_reason
        downloaded_list = []
        with open(tmpfilename, 'wb') as outfile:
            did_download = False
            while not self.stopDownloadFlag:
                r = session.get(url, headers=self.headers, cookies=self.cookies)
                if r.status_code != 200:
                    error = True
                    error_reason = f'playlist request failed with status {r.status_code}'
                    return
                content = r.content.decode("utf-8")
                if m3u_processor:
                    content = m3u_processor(content)
                chunklist = m3u8.loads(content)
                if len(chunklist.segments) == 0:
                    error = True
                    error_reason = 'no segments in playlist'
                    return
                for chunk in chunklist.segment_map + chunklist.segments:
                    if chunk.uri in downloaded_list:
                        continue
                    did_download = True
                    downloaded_list.append(chunk.uri)
                    chunk_uri = chunk.uri
                    self.debug('Downloading ' + chunk_uri)
                    if not chunk_uri.startswith("https://"):
                        chunk_uri = '/'.join(url.split('.m3u8')[0].split('/')[:-1]) + '/' + chunk_uri
                    m = session.get(chunk_uri, headers=self.headers, cookies=self.cookies)
                    if m.status_code != 200:
                        error = True
                        error_reason = f'segment request failed with status {m.status_code}'
                        return
                    outfile.write(m.content)
                    if self.stopDownloadFlag:
                        return
                if not did_download:
                    sleep(10)

    def terminate():
        self.stopDownloadFlag = True

    process = Thread(target=execute)
    process.start()
    self.stopDownload = terminate
    process.join()
    self.stopDownload = None

    if error:
        self.logger.error(f'Native HLS download failed: {error_reason or "unknown error"}')
        return False

    if not os.path.exists(tmpfilename):
        self.logger.error('Native HLS download failed: temp file missing')
        return False

    if os.path.getsize(tmpfilename) == 0:
        os.remove(tmpfilename)
        self.logger.error('Native HLS download failed: temp file empty')
        return False

    # Post-processing
    try:
        stdout = open(filename + '.postprocess_stdout.log', 'w+') if DEBUG else subprocess.DEVNULL
        stderr = open(filename + '.postprocess_stderr.log', 'w+') if DEBUG else subprocess.DEVNULL
        output_str = '-c:a copy -c:v copy'
        if SEGMENT_TIME is not None:
            output_str += f' -f segment -reset_timestamps 1 -segment_time {str(SEGMENT_TIME)}'
            filename = filename[:-len('.' + CONTAINER)] + '_%03d.' + CONTAINER
        ff = FFmpeg(executable=FFMPEG_PATH, inputs={tmpfilename: None}, outputs={filename: output_str})
        ff.run(stdout=stdout, stderr=stderr)
        os.remove(tmpfilename)
    except FFRuntimeError as e:
        if e.exit_code and e.exit_code != 255:
            self.logger.error(f'FFmpeg failed on native HLS post-process: exit code {e.exit_code}')
            return False
    except Exception as e:
        self.logger.error(f'Unexpected error in native HLS post-process: {e}')
        return False

    return True
