from pathlib import Path

from litestar import Litestar, Request
from litestar.config.cors import CORSConfig
from litestar.exceptions import HTTPException
from litestar.openapi import OpenAPIConfig
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from litestar.response import Response

from .routes.streamers import StreamersController
from .routes.recordings import RecordingsController, VideoController
from .routes.system import SystemController, AuthController, LegacyController
from .routes.ws import status_feed
from .routes.spa import spa_fallback, spa_root


def _server_error_handler(request: Request, exc: Exception) -> Response:
    # Registering a catch-all Exception handler shadows Litestar's built-in
    # mapping for its own exceptions (NotAuthorizedException -> 401,
    # NotFoundException -> 404, etc.) when they surface from sync guards run
    # through a thread pool. Handle HTTP exceptions here directly so their
    # status codes and headers are preserved.
    if isinstance(exc, HTTPException):
        return Response(
            content={"detail": exc.detail},
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )
    # Otherwise Litestar swallows the traceback and returns a bare 500, making
    # server-side failures impossible to diagnose from logs. Log the full
    # traceback, then return a generic error body.
    logging.getLogger("streamonitor.httpmanager_v2").error(
        "Unhandled exception while handling %s %s\n%s",
        request.method,
        request.url,
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )
    return Response(
        content={"detail": "Internal Server Error"},
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )


def create_app(manager) -> Litestar:
    # The React SPA is served by spa_root/spa_fallback (see routes/spa.py).
    # They use Response instead of Litestar's File so no Content-Disposition
    # header is emitted - otherwise the browser downloads index.html instead
    # of rendering it.
    app = Litestar(
        route_handlers=[
            StreamersController,
            RecordingsController,
            VideoController,
            SystemController,
            AuthController,
            LegacyController,
            status_feed,
            spa_root,
            spa_fallback,
        ],
        exception_handlers={Exception: _server_error_handler},
        cors_config=CORSConfig(allow_origins=["*"]),
        openapi_config=OpenAPIConfig(title="StreaMonitor API", version="2.0.0"),
    )
    app.state.manager = manager
    return app
