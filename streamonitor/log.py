import sys

from loguru import logger as _logger

import parameters

_LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} - {level} - {extra[name]}: {message}"
_LOG_LEVEL = "DEBUG" if parameters.DEBUG else "INFO"

# Configure a single stdout sink for the whole app
_logger.remove()
_logger.add(sys.stdout, format=_LOG_FORMAT, level=_LOG_LEVEL, enqueue=True)


def get_logger(name="__name__"):
    """Return a Loguru logger bound with a component name."""
    return _logger.bind(name=name)


class Logger:
    """Compatibility wrapper so existing code can use Logger()."""

    def __init__(self, name="__name__"):
        self.logger = get_logger(name)

    def get_logger(self):
        return self.logger

    def __getattr__(self, item):
        return getattr(self.logger, item)

    def warn(self, msg):
        self.logger.warning(msg)
