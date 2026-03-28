import os
from dataclasses import asdict
from pathlib import Path

from litestar import get, delete
from litestar.controller import Controller
from litestar.exceptions import NotFoundException, HTTPException
from litestar.response import File

from streamonitor.managers.httpmanager_v2.auth import auth_guard
from streamonitor.managers.httpmanager_v2.serializers import streamer_to_dto
from streamonitor.managers.httpmanager_v2.schemas import RecordingDTO
from streamonitor.utils.human_file_size import human_file_size


def _manager(request):
    return request.app.state.manager


class RecordingsController(Controller):
    path = "/api/v1/streamers"
    guards = [auth_guard]

    @get("/{username:str}/{site:str}/recordings")
    async def list_recordings(
        self,
        request,
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
                abs_path=v.abs_path,
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
    async def delete_recording(self, request, username: str, site: str, filename: str) -> dict:
        manager = _manager(request)
        streamer = manager.getStreamer(username, site)
        if streamer is None:
            raise NotFoundException(detail="Streamer not found")
        streamer.cache_file_list()

        # Find the file among cached video files
        match = next((v for v in streamer.video_files if v.filename == filename), None)
        if match is None:
            raise NotFoundException(detail=f"File not found: {filename}")
        try:
            os.remove(match.abs_path)
            streamer.cache_file_list()
        except Exception as e:
            raise HTTPException(status_code=500, detail=repr(e))
        return {"message": "Deleted"}


class VideoController(Controller):
    path = "/api/v1/video"

    @get("/{username:str}/{site:str}/{filename:path}")
    async def serve_video(self, request, username: str, site: str, filename: str) -> File:
        """Serve video file. Auth via token query param (required for <video> elements)."""
        from streamonitor.managers.httpmanager_v2.auth import (
            auth_guard, validate_token, _check_basic_auth, _check_bearer_token
        )
        from parameters import WEBSERVER_PASSWORD
        from litestar.exceptions import NotAuthorizedException

        if WEBSERVER_PASSWORD:
            authorization = request.headers.get("authorization")
            token_param = request.query_params.get("token", "")
            if (
                not _check_basic_auth(authorization)
                and not _check_bearer_token(authorization)
                and not validate_token(token_param)
            ):
                raise NotAuthorizedException(detail="Unauthorized")

        manager = _manager(request)
        streamer = manager.getStreamer(username, site)
        if streamer is None:
            raise NotFoundException(detail="Streamer not found")
        file_path = os.path.join(os.path.abspath(streamer.outputFolder), filename)
        if not os.path.isfile(file_path):
            raise NotFoundException(detail="File not found")
        return File(path=file_path, filename=filename)
