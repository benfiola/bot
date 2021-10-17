import logging
from typing import Optional
import urllib.parse

import jinja2

from bot.commands import base
from bot.integrations import youtube as yt
from bot.media import Media
from bot.platforms import CommandContext
from bot.utils import split


logger = logging.getLogger(__name__)


class CommandData(base.CommandData):
    media: Optional[Media] = None

    def render(self) -> str:
        return template.render(data=self)


class Command(base.Command[CommandData]):
    name = "play"
    help = "play media from the provided url"

    async def process_message(
        self, message: str, context: CommandContext, youtube: yt.Integration = None, **kwargs
    ):
        _, url = split(message)
        logger.debug(f"processing: {url}")

        parts = urllib.parse.urlparse(url)
        assert all([parts.hostname, parts.scheme, parts.path]), f"invalid url: {url}"

        media = Media(url=url, title=url)

        yt_video = await youtube.get_from_url(media.url)
        if yt_video:
            media = await youtube.convert(yt_video)

        self.data.media = media

        media_player = await context.join_audio()
        await media_player.enqueue(self.data.media)
        await context.send_response(self.data.render())


template = jinja2.Template(
    """
Added {b}{{data.media.title}}{b} to the media queue.
"""
)
