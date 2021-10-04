import logging

import jinja2

from bot.commands import base
from bot.platforms import CommandContext


logger = logging.getLogger(__name__)


class CommandData(base.CommandData):
    def render(self) -> str:
        return template.render(data=self)


class Command(base.Command[CommandData]):
    name = "leave"
    help = "instruct the bot to leave the current audio channel"

    async def process_message(self, message: str, context: CommandContext, **kwargs):
        logger.debug(f"processing")

        media_player = await context.join_audio()
        await media_player.clear()
        await context.leave_audio()

        await context.send_response(self.data.render())


template = jinja2.Template(
    """
Bot has left current voice channel
"""
)
