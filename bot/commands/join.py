import logging

import jinja2

from bot.commands import base
from bot.platforms import CommandContext


logger = logging.getLogger(__name__)


class CommandData(base.CommandData):
    def render(self) -> str:
        return template.render(data=self)


class Command(base.Command[CommandData]):
    name = "join"
    help = "instruct the bot to join the current audio channel"

    async def process_message(self, message: str, context: CommandContext, **kwargs):
        logger.debug(f"processing")

        media_player = await context.join_audio()
        await media_player.play()

        await context.send_response(self.data.render())


template = jinja2.Template(
    """
Bot has joined current audio channel
"""
)
