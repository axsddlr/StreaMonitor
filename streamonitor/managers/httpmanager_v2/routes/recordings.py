import os
from dataclasses import asdict

from litestar import Request, get, delete
from litestar.controller import Controller
from litestar.exceptions import NotFoundException, HTTPException
from litestar.response import File

from streamonitor.managers.httpmanager_v2.auth import auth_guard
from streamonitor.managers.httpmanager_v2.serializers import streamer_to_dto
from streamonitor.managers.httpmanager_v2.schemas import RecordingDTO
from streamonitor.utils.human_file_size import human_file_size


def _manager(request: Request):
    return request.app.state.manager


class RecordingsController(Controller):
    path = "/api/v1/streamers"
    guards = [auth_guard]

    @get("/{username:str}/{site:str}/recordings")
    async def list_recordings(
        self,
        request: Request,
        username: str,
        site: str,
        sort_by_size: bool = False,
    ) -> dict:
        manager = _manager(request)
        streamer = manager.getStreamer(username, site)
        if streamer is None:
            raise NotFoundException(detail="Streamer not found")
        streamer.cache_file_list()

        videos = list(streamer.video_files)
        if sort_by_size:
            videos.sort(key=lambda v: v.filesize, reverse=True)
        else:
            videos.sort(key=lambda v: v.filename)

        recordings = [
            RecordingDTO(
                filename=v.filename,
                filesize=v.filesize,
                filesize_human=human_file_size(v.filesize),
            )
            for v in videos
        ]
        return {
            "streamer": asdict(streamer_to_dto(streamer)),
            "recordings": [asdict(r) for r in recordings],
            "total_size": streamer.video_files_total_size,
            "total_size_human": human_file_size(streamer.video_files_total_size),
        }

    @delete("/{username:str}/{site:str}/recordings/{filename:path}", status_code=200)
    async def delete_recording(self, request: Request, username: str, site: str, filename: str) -> dict:
        manager = _manager(request)
        streamer = manager.getStreamer(username, site)
        if streamer is None:
            raise NotFoundException(detail="Streamer not found")
        streamer.cache_file_list()

        # Litestar's {filename:path} converter yields a leading slash; strip
        # it so it matches the basename that VideoData stores.
        filename = filename.lstrip("/")

        # Find the file among cached video files
        match = next((v for v in streamer.video_files if v.filename == filename), None)
        if match is None:
            raise NotFoundException(detail=f"File not found: {filename}")
        try:
            os.remove(match.abs_path)
            streamer.cache_file_list()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"message": "Deleted"}


class VideoController(Controller):
    path = "/api/v1/video"
    guards = [auth_guard]

    @get("/{username:str}/{site:str}/{filename:path}")
    async def serve_video(self, request: Request, username: str, site: str, filename: str) -> File:
        """Serve video file. auth_guard supports token-in-query-param auth,
        required since <video> elements can't send custom Authorization headers."""
        manager = _manager(request)
        streamer = manager.getStreamer(username, site)
        if streamer is None:
            raise NotFoundException(detail="Streamer not found")

        # Litestar's {filename:path} converter yields a leading slash; strip
        # it so it matches the basename that VideoData stores.
        filename = filename.lstrip("/")

        # Only serve files that are known recordings of this streamer (matched by
        # exact filename against the cached video list) instead of joining the raw,
        # user-supplied path onto disk — this prevents directory traversal
        # (e.g. filename="../../../etc/passwd") from escaping outputFolder.
        streamer.cache_file_list()
        match = next((v for v in streamer.video_files if v.filename == filename), None)
        if match is None or not os.path.isfile(match.abs_path):
            raise NotFoundException(detail="File not found")
        # content_disposition_type="inline": File would otherwise default to
        # attachment, which is the same class of bug as the SPA routes and can
        # make the <video> element misbehave / prompt a download.
        return File(
            path=match.abs_path,
            filename=match.filename,
            content_disposition_type="inline",
        )
