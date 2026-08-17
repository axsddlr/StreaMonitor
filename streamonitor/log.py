import logging
import parameters


class Logger(object):
    def __init__(self, name="__name__"):
        self.name = name
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - {}: %(message)s'.format(name))
        self.handler = logging.StreamHandler()
        self.handler.setFormatter(self.formatter)

        self.logger = logging.getLogger(self.name)
        self.loglevel = logging.DEBUG if parameters.DEBUG else logging.INFO
        self.logger.setLevel(self.loglevel)
        self.logger.addHandler(self.handler)

    def get_logger(self):
        logger = logging.getLogger(self.name)
        logger.setLevel(self.loglevel)
        logger.addHandler(self.handler)
        return logger

    def debug(self, msg, *args):
        self.logger.debug(msg, *args)

    def warning(self, msg, *args):
        self.logger.warning(msg, *args)

    def error(self, msg, *args):
        self.logger.error(msg, *args)

    def info(self, msg, *args):
        self.logger.info(msg, *args)
