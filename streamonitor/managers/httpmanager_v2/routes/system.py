from dataclasses import asdict

from litestar import Request, get
from litestar.controller import Controller

from streamonitor.bot import Bot, LOADED_SITES
from streamonitor.enums import Status
from streamonitor.managers.httpmanager_v2.auth import auth_guard
from streamonitor.managers.httpmanager_v2.serializers import disk_space_dto
from streamonitor.managers.httpmanager_v2.auth import generate_token
from parameters import WEBSERVER_PASSWORD


def _manager(request: Request):
    return request.app.state.manager


class SystemController(Controller):
    path = "/api/v1/system"
    guards = [auth_guard]

    @get("/disk-space")
    async def get_disk_space(self) -> dict:
        return asdict(disk_space_dto())

    @get("/settings")
    async def get_settings(self, request: Request) -> dict:
        sites = {site.siteslug: site.site for site in LOADED_SITES}
        statuses = {status.value: Bot.status_messages[status] for status in Status}
        return {
            "sites": dict(sorted(sites.items(), key=lambda x: x[1])),
            "statuses": statuses,
        }

    @get("/command")
    async def exec_command(self, request: Request, command: str = "") -> dict:
        manager = _manager(request)
        result = manager.execCmd(command)
        return {"result": result}


class AuthController(Controller):
    path = "/api/v1/auth"

    @get("/login")
    async def login(self, request: Request) -> dict:
        """Validate credentials (basic auth) and return a bearer token."""
        import base64
        import secrets as _secrets
        from litestar.exceptions import NotAuthorizedException

        if not WEBSERVER_PASSWORD:
            token = generate_token()
            return {"token": token}

        authorization = request.headers.get("authorization", "")
        if authorization.startswith("Basic "):
            try:
                decoded = base64.b64decode(authorization[6:]).decode("utf-8")
                username, _, password = decoded.partition(":")
                if username == "admin" and _secrets.compare_digest(password, WEBSERVER_PASSWORD):
                    token = generate_token()
                    return {"token": token}
            except Exception:
                pass

        # No WWW-Authenticate header (see auth.auth_guard): it would make the
        # browser pop a native basic-auth dialog that loops against our custom
        # login page.
        raise NotAuthorizedException(detail="Invalid credentials")


# Legacy compat routes
class LegacyController(Controller):
    path = "/api"
    guards = [auth_guard]

    @get("/basesettings")
    async def base_settings(self, request: Request) -> dict:
        sites = {site.siteslug: site.site for site in LOADED_SITES}
        statuses = {status.value: Bot.status_messages[status] for status in Status}
        return {"sites": sites, "status": statuses}

    @get("/data")
    async def data(self, request: Request) -> dict:
        manager = _manager(request)
        from streamonitor.utils.human_file_size import human_file_size
        from streamonitor.managers.outofspace_detector import OOSDetector
        json_streamers = [
            {
                "site": s.siteslug,
                "running": s.running,
                "recording": s.recording,
                "sc": s.sc.value,
                "status": s.status(),
                "url": s.url,
                "username": s.username,
            }
            for s in manager.streamers
        ]
        usage = OOSDetector.space_usage()
        return {
            "streamers": json_streamers,
            "freeSpace": {
                "percentage": str(round(OOSDetector.free_space(), 3)),
                "absolute": human_file_size(usage.free),
            },
        }

    @get("/command")
    async def command(self, request: Request, command: str = "") -> str:
        manager = _manager(request)
        return manager.execCmd(command) or ""
