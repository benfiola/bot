import asyncio
import functools
import pathlib

import click

from bot.logging_ import configure as configure_loggers
from bot.config import parse as config_parse
from bot.main import Bot


def sync(func):
    """
    Wraps a coroutine in a call to `asyncio.run` as a synchronous method.
    :param func:
    :return:
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapped


def entry_point():
    configure_loggers()
    main()


@click.group()
def main():
    pass


@main.group()
def storage():
    pass


@main.command()
@click.argument("config_file", type=click.Path(exists=True))
@sync
async def run(config_file: click.Path):
    # resolve the configuration file
    config_file = pathlib.Path(str(config_file)).resolve()

    # parse the configuration file
    config = config_parse(config_file)

    # create the bot
    bot = await Bot.create_from_configuration(config)

    # start the bot
    await bot.start()
