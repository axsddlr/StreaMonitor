import uvicorn

import streamonitor.log as log
from streamonitor.bot import LOADED_SITES
from streamonitor.manager import Manager
from parameters import WEBSERVER_HOST, WEBSERVER_PORT


class HTTPManager(Manager):
    def __init__(self, streamers):
        super().__init__(streamers)
        self.logger = log.Logger("http_manager")
        self.loaded_site_names = sorted([site.site for site in LOADED_SITES])

    def run(self):
        from .app import create_app

        app = create_app(manager=self)

        # Suppress uvicorn access logs to keep console clean
        uvicorn_log_config = uvicorn.config.LOGGING_CONFIG.copy()
        uvicorn_log_config["loggers"]["uvicorn.access"]["level"] = "WARNING"

        config = uvicorn.Config(
            app,
            host=WEBSERVER_HOST,
            port=WEBSERVER_PORT,
            log_config=uvicorn_log_config,
            # uvloop cannot be imported from a non-main thread ("can't register
            # atexit after shutdown" RuntimeError), and this server runs inside
            # a manager daemon thread, so force the asyncio event loop.
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        # Server.serve() only installs signal handlers when running in the
        # main thread (uvicorn's capture_signals() no-ops otherwise), so this
        # is safe to run from a manager daemon thread.
        server.run()
