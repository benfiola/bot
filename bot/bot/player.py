import asyncio
import datetime
from typing import cast

from discord import VoiceChannel
from wavelink import Playable
from wavelink import Player as BasePlayer

from bot.utils import ensure_instance


class Player(BasePlayer):
    """
    Subclass of a `wavelink.Player` that provides some default configuration and helper methods
    utilized by bot commands.
    """
    inactivity_interval: datetime.timedelta
    inactivity_timeout: datetime.timedelta
    last_active: datetime.datetime
    monitor_inactivity_task: asyncio.Task | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOTE: if autoplay is not True, queue functionality is disabled
        self.autoplay = True

        self.inactivity_interval = datetime.timedelta(seconds=30)
        self.inactivity_timeout = datetime.timedelta(minutes=2)
        self.last_active = datetime.datetime.now(tz=datetime.timezone.utc)
        self.monitor_inactivity_task = None

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

    async def connect(self, *args, **kwargs):
        """
        Called when the wavelink player is connecting to a channel to stream audio - this method provides a 
        reasonable entrypoint into scheduling side-effects and background tasks.
        """
        await super().connect(*args, **kwargs)
        self.monitor_inactivity_task = asyncio.create_task(self.monitor_inactivity())

    async def monitor_inactivity(self):
        """
        While connected to a voice channel, will monitor for inactivity.

        If the player has been inactive for a fixed period of time (`inactivity_timeout`) - disconnect the player
         from the current voice channel
        """
        self.last_active = datetime.datetime.now(tz=datetime.timezone.utc)

        while True:
            now = datetime.datetime.now(tz=datetime.timezone.utc)

            # inactivity threshold has been reached - trigger a disconnection
            if (now - self.last_active) >= self.inactivity_timeout:
                await self.disconnect()
                break
                
            # check voice channel is non-empty
            is_channel_non_empty = False
            if self.channel:
                try:
                    channel = await self.client.fetch_channel(self.channel.id)
                    channel = ensure_instance(channel, VoiceChannel)
                    if len(channel.members) > 1:
                        is_channel_non_empty = True
                except Exception:
                    pass
            
            # check bot is streaming audio
            is_streaming_audio = self.is_playing() and not self.is_paused()
            
            # update last_active time if bot appears to still be active
            if is_channel_non_empty and is_streaming_audio:
                self.last_active = now
            
            await asyncio.sleep(int(self.inactivity_interval.total_seconds()))


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

    async def disconnect(self, *args, **kwargs):
        """
        Called when the player is disconnecting from a channel - this method provides
        a resonable entrypoint into cleaning up side-effects and background tasks
        """
        if self.monitor_inactivity_task:
            try:
                self.monitor_inactivity_task.cancel()
                await self.monitor_inactivity_task
            except asyncio.CancelledError:
                pass
            self.monitor_inactivity_task = None
        
        await super().disconnect(*args, **kwargs)
    
    async def leave(self):
        """
        A helper method that disconnects the player from its current channel *and* clears its queue.
        """
        await self.disconnect(force=True)
        # NOTE: the _destroy method clears the queue for the current client
        await self._destroy()
