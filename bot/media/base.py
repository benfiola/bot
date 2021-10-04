from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, List, Optional, Protocol

from bot.utils import Data, Field

if TYPE_CHECKING:
    from bot.platforms import MediaPlayerContext


logger = logging.getLogger(__name__)


class Media(Data):
    url: str
    title: str
    duration: Optional[datetime.timedelta]


class MediaPlayerData(Data):
    queue: List[Media] = Field(default_factory=list, persist=True)
    elapsed: datetime.timedelta = Field(
        default_factory=lambda: datetime.timedelta(seconds=0), persist=True
    )


class Save(Protocol):
    async def __call__(self, media_player: MediaPlayer):
        ...


async def save(_: MediaPlayer):
    """
    Default `save` callback for `MediaPlayer`.
    :param _:
    :return:
    """
    pass


class MediaPlayer:
    """
    Provides an interface on top of a `MediaPlayerContext` to enable easier
    manipulation of a bot media queue + play/stop activity.

    save: A callback that the `Bot` can attach to - enabling persistence for the media player.
    """

    data: MediaPlayerData
    poll_task: Optional[asyncio.Task]
    context: MediaPlayerContext
    save: Save

    def __init__(self, context: MediaPlayerContext):
        self.context = context
        self.data = MediaPlayerData()
        self.poll_task = None
        self.save = save

    async def start(self):
        """
        Called when initializing a media player (generally during bot startup).

        Typically, accessing the media player is done through a command such that:

        `CommandContext.join_audio` joins the audio and returns a media player, on which one can call `play`.
        :return:
        """
        await self.context.join_audio()
        await self.play()

    async def play(self):
        """
        Plays the song at the top of the queue.
        :return:
        """
        if await self.context.is_playing():
            # if already playing - do nothing
            logger.debug(f"play: already playing media ({self.context.data.hash()})")
            return
        if not self.data.queue:
            # if queue empty - do nothing
            logger.debug(f"play: empty queue ({self.context.data.hash()})")
            return

        media = self.data.queue[0]
        logger.debug(f"play: {media} ({self.context.data.hash()})")

        # start playing media and poll for finish
        await self.context.play(self.data.queue[0])
        self.poll_task = asyncio.create_task(self.poll())

        await self.save(self)

    async def poll(self):
        """
        Task scheduled while playing music: polls for song complete/bot disconnection
        to advance the queue/stop the player.
        :return:
        """
        is_playing = is_connected = True

        # poll until disconnect/song finish
        while all([is_playing, is_connected]):
            is_playing = await self.context.is_playing()
            is_connected = await self.context.is_connected()
            await asyncio.sleep(1)
            self.data.elapsed += datetime.timedelta(seconds=1)

        # clear poll task
        self.poll_task = None

        if not is_connected:
            # if disconnected - stop the media player
            logger.debug(f"poll: disconnected ({self.context.data.hash()})")
            await self.stop()
        elif not is_playing:
            # if song stopped - go to the next song
            logger.debug(f"poll: song finished ({self.context.data.hash()})")
            await self.next()

    async def next(self):
        """
        Skips the currently playing song.
        :return:
        """
        # stop currently playing song (if any)
        await self.stop()

        if not self.data.queue:
            # if queue is empty - do nothing
            logger.debug(f"next: empty queue ({self.context.data.hash()})")
            return

        # go to next song in queue
        logger.debug(f"next: pop media ({self.context.data.hash()})")
        self.data.queue.pop(0)

        # continue playing
        logger.debug(f"next: playing next media ({self.context.data.hash()})")
        await self.play()

        await self.save(self)

    async def stop(self):
        """
        Stops the currently playing song.
        :return:
        """
        if not await self.context.is_playing():
            logger.debug(f"stop: not playing ({self.context.data.hash()})")
            return

        media = self.data.queue[0]
        logger.debug(f"stop: {media} ({self.context.data.hash()})")

        # reset playing state
        if self.poll_task is not None:
            self.poll_task.cancel()
            self.poll_task = None
        self.data.elapsed = datetime.timedelta(seconds=0)
        await self.context.stop()

        await self.save(self)

    async def enqueue(self, media: Media):
        """
        Adds a `Media` object to the end of the queue.
        :param media:
        :return:
        """
        logger.debug(f"enqueue: {media} ({self.context.data.hash()})")

        self.data.queue.append(media)
        if len(self.data.queue) == 1:
            # if item is first item on queue, auto-play
            await self.play()

        await self.save(self)

    async def pop(self, index: int) -> Media:
        """
        Removes a `Media` object from the queue by index.
        :param index:
        :return:
        """
        logger.debug(f"pop: {index} ({self.context.data.hash()})")

        to_return = self.data.queue[index]

        if index == 0:
            # if item is front of queue - skip to the next song
            await self.next()
        else:
            # otherwise remove item directly the queue
            self.data.queue.pop(index)
        await self.save(self)

        return to_return

    async def clear(self):
        """
        Stops the currently playing media and removes all items from the queue.

        :return:
        """
        await self.stop()
        self.data.queue = []

        await self.save(self)
