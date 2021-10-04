import logging

from typing import List

import jinja2
import pydantic

from bot.commands import base
from bot.media import Media
from bot.platforms import CommandContext


logger = logging.getLogger(__name__)


class CommandData(base.CommandData):
    queue: List[Media] = pydantic.Field(default_factory=list)

    def render(self):
        if self.queue:
            return queue_list_template.render(data=self)
        else:
            return empty_template.render(data=self)


class Command(base.Command[CommandData]):
    name = "list"
    help = "list queued media items"

    async def process_message(self, message: str, context: CommandContext, **kwargs):
        logger.debug(f"processing")
        media_player = await context.join_audio()
        self.data.queue = list(media_player.data.queue)
        await context.send_response(self.data.render())


queue_list_template = jinja2.Template(
    """
{% for media in data.queue -%}
{{loop.index}}.  {c}{{media.title}}{c}
{% endfor %}
"""
)


empty_template = jinja2.Template(
    """
Queue is empty.
"""
)
