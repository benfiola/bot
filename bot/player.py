from typing import cast

from wavelink import Playable
from wavelink import Player as BasePlayer


class Player(BasePlayer):
    """
    Subclass of a `wavelink.Player` that provides some default configuration and helper methods
    utilized by bot commands.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOTE: if autoplay is not True, queue functionality is disabled
        self.autoplay = True

    async def enqueue(self, track: Playable, position: int | None = None):
        """
        A helper function that enqueues a song at an optional location.

        Will restart queue autoplay if the queue stopped playing due to running out of songs.
        """
        is_empty = self.queue.is_empty

        if position is None:
            await self.queue.put_wait(track)
        else:
            self.queue.put_at_index(position, track)

        # NOTE: only autoplay if the queue appears to have stopped from running out of songs.
        if is_empty and not self.is_playing():
            await self.play(cast(Playable, self.queue.get()), populate=False)

    async def remove(self, track: Playable):
        """
        A helper function that removes the provided track from the queue.
        """
        if self.current == track:
            if self.queue.is_empty:
                await self.stop()
                # NOTE: this state doesn't appear to get cleaned up when 'stop' is called - thus, do so here
                self._current = None
            else:
                was_paused = self.is_paused()
                await self.play(cast(Playable, self.queue.get()), populate=False)
                if was_paused:
                    await self.pause()
        else:
            try:
                position = self.queue.find_position(track)
            except ValueError:
                return
            del self.queue[position]

    async def leave(self):
        """
        A helper method that disconnects the player from its current channel *and* clears its queue.
        """
        await self.disconnect(force=True)
        # NOTE: the _destroy method clears the queue for the current client
        await self._destroy()
