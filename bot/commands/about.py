import logging
import pathlib

import jinja2

import bot
from bot.commands import base
from bot.platforms import CommandContext


logger = logging.getLogger(__name__)


class CommandData(base.CommandData):
    version: str = None

    def render(self) -> str:
        return template.render(data=self)


class Command(base.Command[CommandData]):
    name = "about"
    help = "information about this bot"

    async def process_message(self, message: str, context: CommandContext, **kwargs):
        logger.debug(f"processing")

        self.data.version = pathlib.Path(bot.__file__).parent.joinpath("version.txt").read_text()

        await context.send_response(self.data.render())


template = jinja2.Template(
    """
bot@{c}{{data.version}}{c} 

github: https://github.com/benfiola/bot.git
made with ♥ by ben
"""
)
