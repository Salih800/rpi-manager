import logging
from pathlib import Path

from constants.folders import LOG_FOLDER


class CustomFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def set_logger(log_name="rpi-default"):
    Path(LOG_FOLDER).mkdir(parents=True, exist_ok=True)
    log_filename = LOG_FOLDER + log_name + '.log'
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = '%(asctime)s - %(levelname)s - %(message)s'

    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(logging.Formatter(fmt))

    # stream_handler = logging.StreamHandler()
    # stream_handler.setLevel(logging.INFO)
    # stream_handler.setFormatter(CustomFormatter(fmt))
    #
    # logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger


def get_logger(name, log_level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    return logger
