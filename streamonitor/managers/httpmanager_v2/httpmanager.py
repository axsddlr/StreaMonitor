import logging

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

        uvicorn.run(
            app,
            host=WEBSERVER_HOST,
            port=WEBSERVER_PORT,
            log_config=uvicorn_log_config,
            # Required when running inside a non-main thread
            install_signal_handlers=False,
        )
