import logging

import jinja2
import pydantic

from bot.commands import base
from bot.media import Media
from bot.platforms import CommandContext
from bot.utils import split


logger = logging.getLogger(__name__)


class CommandData(pydantic.BaseModel):
    media: Media = None
    index: int = None

    def render(self) -> str:
        return template.render(data=self)


class Command(base.Command[CommandData]):
    name = "skip"
    help = "remove items from the media queue"

    async def process_message(self, message: str, context: CommandContext, **kwargs):
        _, index = split(message)
        logger.debug(f"processing: {index}")
        if index == "":
            index = "1"
        index = int(index)

        media_player = await context.join_audio()
        media = await media_player.pop(int(index) - 1)

        self.data.index = index
        self.data.media = media
        await context.send_response(self.data.render())


template = jinja2.Template(
    """
Removed {b}{{data.index}}.  {{data.media.title}}{b} from the queue.
"""
)
