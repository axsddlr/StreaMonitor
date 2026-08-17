from dataclasses import asdict
import os

from litestar import Request, get, post, delete, patch
from litestar.controller import Controller
from litestar.exceptions import NotFoundException, HTTPException

from streamonitor.managers.httpmanager_v2.auth import auth_guard
from streamonitor.managers.httpmanager_v2.serializers import streamer_to_dto, disk_space_dto
from streamonitor.managers.httpmanager_v2.schemas import AddStreamerRequest, SetCookiesRequest
from parameters import COOKIES_DIR


def _manager(request: Request):
    return request.app.state.manager


class StreamersController(Controller):
    path = "/api/v1/streamers"
    guards = [auth_guard]

    @get()
    async def list_streamers(
        self,
        request: Request,
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
    async def add_streamer(self, request: Request, data: AddStreamerRequest) -> dict:
        manager = _manager(request)
        streamer = manager.getStreamer(data.username, data.site)
        res = manager.do_add(streamer, data.username, data.site)
        # Manager.do_add only returns "Added [...]" on success; every other
        # branch (unknown site, invalid username, already exists, missing
        # value(s), internal failure) is an error message starting with
        # something else. Checking for the success prefix directly (instead
        # of blocklisting known error strings) avoids silently treating any
        # future/unrecognized error message as a success.
        success = res.startswith("Added ")
        return {"message": res, "success": success}

    @delete("/{username:str}/{site:str}", status_code=200)
    async def remove_streamer(self, request: Request, username: str, site: str) -> dict:
        manager = _manager(request)
        streamer = manager.getStreamer(username, site)
        res = manager.do_remove(streamer, username, site)
        if res == "Streamer not found":
            raise NotFoundException(detail=res)
        if res == "Failed to remove streamer":
            raise HTTPException(status_code=500, detail=res)
        return {"message": res}

    @patch("/{username:str}/{site:str}/toggle")
    async def toggle_streamer(self, request: Request, username: str, site: str) -> dict:
        manager = _manager(request)
        streamer = manager.getStreamer(username, site)
        if streamer is None:
            raise NotFoundException(detail="Streamer not found")
        if streamer.running:
            res = manager.do_stop(streamer, username, site)
        else:
            res = manager.do_start(streamer, username, site)
        return {"message": res, "running": streamer.running}

    @patch("/{username:str}/{site:str}/cookies")
    async def set_cookies(self, request: Request, username: str, site: str, data: SetCookiesRequest) -> dict:
        manager = _manager(request)
        streamer = manager.getStreamer(username, site)
        if streamer is None:
            raise NotFoundException(detail="Streamer not found")
        if not hasattr(streamer, 'setCookiesPath'):
            raise HTTPException(status_code=400, detail=f"Cookies are not supported for {streamer.site}")

        content = (data.content or '').strip()
        if not content:
            streamer.setCookiesPath(None)
            manager.saveConfig()
            return {"message": f"Cookies cleared for {streamer.username}", "cookies_path": None}

        try:
            os.makedirs(COOKIES_DIR, exist_ok=True)
            path = os.path.abspath(os.path.join(COOKIES_DIR, f"{streamer.siteslug}-{streamer.username}.txt"))
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content + '\n')
            streamer.setCookiesPath(path)
            manager.saveConfig()
            return {"message": f"Cookies set for {streamer.username}", "cookies_path": path}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to set cookies: {e}")

    @patch("/start-all")
    async def start_all(self, request: Request) -> dict:
        manager = _manager(request)
        res = manager.do_start(None, '*', None)
        return {"message": res}

    @patch("/stop-all")
    async def stop_all(self, request: Request) -> dict:
        manager = _manager(request)
        res = manager.do_stop(None, '*', None)
        return {"message": res}
