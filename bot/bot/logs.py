import logging

import bot


def configure_loggers():
    """
    Attaches a default configuration to the root logger for the package.
    """
    logger = logging.getLogger(bot.__name__)
    formatter = logging.Formatter("[%(asctime)s][%(name)s]: %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    discord_logger = logging.getLogger("discord")
    discord_logger.addHandler(handler)
    discord_logger.setLevel(logging.DEBUG)
