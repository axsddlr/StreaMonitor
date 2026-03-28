from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.openapi import OpenAPIConfig

from .routes.streamers import StreamersController
from .routes.recordings import RecordingsController, VideoController
from .routes.system import SystemController, AuthController, LegacyController
from .routes.ws import status_feed
from .routes.spa import spa_fallback, spa_root


def create_app(manager) -> Litestar:
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
        cors_config=CORSConfig(allow_origins=["*"]),
        openapi_config=OpenAPIConfig(title="StreaMonitor API", version="2.0.0"),
    )
    app.state.manager = manager
    return app
