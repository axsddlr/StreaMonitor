from dataclasses import asdict
from typing import Any

from litestar import get, post, delete, patch
from litestar.controller import Controller
from litestar.exceptions import NotFoundException, HTTPException

from streamonitor.managers.httpmanager_v2.auth import auth_guard
from streamonitor.managers.httpmanager_v2.serializers import streamer_to_dto, disk_space_dto
from streamonitor.managers.httpmanager_v2.schemas import AddStreamerRequest


def _manager(request):
    return request.app.state.manager


class StreamersController(Controller):
    path = "/api/v1/streamers"
    guards = [auth_guard]

    @get()
    async def list_streamers(
        self,
        request,
        filter_username: str = "",
        filter_site: str = "",
        filter_status: str = "",
        sort_by: str = "username",
        sort_dir: str = "asc",
    ) -> dict:
        manager = _manager(request)
        streamers = list(manager.streamers)

        # Filter
        if filter_username:
            streamers = [s for s in streamers if filter_username.lower() in s.username.lower()]
        if filter_site:
            streamers = [s for s in streamers if s.site.lower() == filter_site.lower() or s.siteslug.lower() == filter_site.lower()]
        if filter_status:
            if filter_status == "running":
                streamers = [s for s in streamers if s.running]
            elif filter_status == "recording":
                streamers = [s for s in streamers if s.recording]
            elif filter_status == "offline":
                from streamonitor.enums import Status
                streamers = [s for s in streamers if s.sc in (Status.OFFLINE, Status.LONG_OFFLINE)]
            elif filter_status == "online":
                from streamonitor.enums import Status
                streamers = [s for s in streamers if s.sc == Status.PUBLIC]

        # Sort
        reverse = sort_dir == "desc"
        try:
            if sort_by == "video_count":
                streamers.sort(key=lambda s: len(s.video_files), reverse=reverse)
            elif sort_by == "video_total_size":
                streamers.sort(key=lambda s: s.video_files_total_size, reverse=reverse)
            elif sort_by == "status":
                streamers.sort(key=lambda s: s.sc.value, reverse=reverse)
            else:
                streamers.sort(key=lambda s: getattr(s, sort_by, "").lower() if isinstance(getattr(s, sort_by, ""), str) else getattr(s, sort_by, 0), reverse=reverse)
        except Exception:
            streamers.sort(key=lambda s: s.username.lower(), reverse=reverse)

        return {
            "streamers": [asdict(streamer_to_dto(s)) for s in streamers],
            "disk": asdict(disk_space_dto()),
        }

    @post()
    async def add_streamer(self, request, data: AddStreamerRequest) -> dict:
        manager = _manager(request)
        streamer = manager.getStreamer(data.username, data.site)
        res = manager.do_add(streamer, data.username, data.site)
        success = res not in ("Streamer already exists", "Missing value(s)") and not res.startswith("Failed")
        return {"message": res, "success": success}

    @delete("/{username:str}/{site:str}", status_code=200)
    async def remove_streamer(self, request, username: str, site: str) -> dict:
        manager = _manager(request)
        streamer = manager.getStreamer(username, site)
        res = manager.do_remove(streamer, username, site)
        if res == "Streamer not found":
            raise NotFoundException(detail=res)
        if res == "Failed to remove streamer":
            raise HTTPException(status_code=500, detail=res)
        return {"message": res}

    @patch("/{username:str}/{site:str}/toggle")
    async def toggle_streamer(self, request, username: str, site: str) -> dict:
        manager = _manager(request)
        streamer = manager.getStreamer(username, site)
        if streamer is None:
            raise NotFoundException(detail="Streamer not found")
        if streamer.running:
            res = manager.do_stop(streamer, username, site)
        else:
            res = manager.do_start(streamer, username, site)
        return {"message": res, "running": streamer.running}

    @patch("/start-all")
    async def start_all(self, request) -> dict:
        manager = _manager(request)
        res = manager.do_start(None, '*', None)
        return {"message": res}

    @patch("/stop-all")
    async def stop_all(self, request) -> dict:
        manager = _manager(request)
        res = manager.do_stop(None, '*', None)
        return {"message": res}
