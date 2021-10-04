import logging
from logging import getLogger

import bot


def configure():
    root_logger = getLogger(bot.__name__)
    formatter = logging.Formatter("[%(asctime)s][%(name)s]: %(msg)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
