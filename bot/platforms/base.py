from __future__ import annotations

from typing import Type, Optional, Protocol, Generic, TypeVar, Dict

import pydantic.generics

from bot.media import MediaPlayer, Media
from bot.utils import Data


Field = pydantic.Field


class CommandData(Data):
    pass


class MediaPlayerData(Data):
    pass


SomeData = TypeVar("SomeData", bound=Data)
SomeCommandData = TypeVar("SomeCommandData", bound=CommandData)
SomeMediaPlayerData = TypeVar("SomeMediaPlayerData", bound=MediaPlayerData)


class Context(Generic[SomeData]):
    data: SomeData
    platform: Platform

    def __init__(self, *, platform: Platform, data: Data):
        self.data = data
        self.platform = platform


class CommandContext(Context[SomeCommandData]):
    """
    A `CommandContext` provides the API accessible to commands while processing messages.
    """

    async def send_response(self, message: str):
        """
        Delegates to the platform to send a response back to the end user.
        :param message:
        :return:
        """
        return await self.platform.send_response(message, self.data)

    async def join_audio(self) -> MediaPlayer:
        """
        Instructs the bot to join the current user's audio channel, returning
         a `MediaPlayer` that can be further interacted with
        :return:
        """
        data = await self.platform.get_media_player_data(self.data)
        context = MediaPlayerContext(platform=self.platform, data=data)
        return await context.join_audio()

    async def leave_audio(self):
        """
        Instructs the bot to leave the current audio channel.
        :return:
        """
        data = await self.platform.get_media_player_data(self.data)
        context = MediaPlayerContext(platform=self.platform, data=data)
        return await context.leave_audio()


class MediaPlayerContext(Context[SomeMediaPlayerData]):
    """
    A `MediaPlayerContext` provides the API accessible to media players.

    A `MediaPlayerContext` *must* obtain media players through the wrapped platform
     - as this is how the bot can hook into the media player creation flows to attach
     callbacks and persistence to the media player factory.
    """

    async def join_audio(self) -> MediaPlayer:
        """
        Joins the audio channel of the underlying `MediaPlayerContext`.
        :return:
        """
        await self.platform.join_audio(self.data)
        media_player = await self.platform.get_media_player(self)
        return media_player

    async def leave_audio(self):
        """
        Leaves the audio channel of the underlying `MediaPlayerContext`.
        :return:
        """
        media_player = await self.platform.get_media_player(self)
        await media_player.stop()
        await self.platform.leave_audio(self.data)

    async def play(self, media: Media):
        """
        Plays the provided `Media` in the audio channel of the underlying `MediaPlayerContext`.
        :return:
        """
        await self.platform.play_audio(media, self.data)

    async def stop(self):
        await self.platform.stop_audio(self.data)

    async def is_connected(self) -> bool:
        return await self.platform.is_audio_connected(self.data)

    async def is_playing(self) -> bool:
        return await self.platform.is_audio_playing(self.data)


class OnReady(Protocol):
    async def __call__(self):
        ...


class ProcessMessage(Protocol):
    async def __call__(self, message: str, command_data: CommandData):
        ...


class GetMediaPlayer(Protocol):
    async def __call__(self, context: MediaPlayerContext) -> MediaPlayer:
        ...


async def process_message(_: str, __: CommandData):
    return None


async def get_media_player(context: MediaPlayerContext) -> MediaPlayer:
    return MediaPlayer(context)


class Platform(Generic[SomeCommandData, SomeMediaPlayerData]):
    """
    Interface to connect a chat platform to the bot framework.

    command_data_cls: Data container for command data (used for (de)serialization)
    media_player_data_cls: Data container for media player data (used for (de)serialization)
    name: Key name for the platform
    process_message: Callback when messages are received
    on_ready: Callback when listener is ready (for post-initialization)
    get_media_player: Factory method called to obtain media players (exposes hooks into persistence, etc.)
    """

    command_data_cls: Type[SomeCommandData]
    media_player_data_cls: Type[MediaPlayerData]

    name: str = None
    registry: Dict[str, Type[Platform]] = {}
    process_message: ProcessMessage
    on_ready: Optional[OnReady]
    get_media_player: GetMediaPlayer

    def __init__(self, **kwargs):
        self.get_media_player = get_media_player
        self.on_ready = None
        self.process_message = process_message

    def __init_subclass__(cls):
        """
        When defining a platform:
            class NewPlatform(Platform[CmdData, MPData]):
        will fetch `(CmdData, MPData)` from the `cls` object at `__class_getitem_args__`.

        NOTE: This data is set in `__class_getitem__`
        :return:
        """
        # fetch generic arguments set within `__class_getitem__`
        ((command_data_cls, media_player_data_cls),) = getattr(cls, "__class_getitem_args__")
        if not isinstance(command_data_cls, TypeVar):
            cls.command_data_cls = command_data_cls
        if not isinstance(media_player_data_cls, TypeVar):
            cls.media_player_data_cls = media_player_data_cls

        # ensure name is defined for registry
        assert cls.name is not None, f"{cls.__name__}.name unset"
        exists = cls.registry.get(cls.name)
        assert exists is None, f"{cls.name} already registered: {exists.__name__}"
        cls.registry[cls.name] = cls

    def __class_getitem__(cls, *args):
        """
        When defining a platform:
            class NewPlatform(Platform[CmdData, MPData]):
        will store `(CmdData, MPData)` in the `cls` object at `__class_getitem_args__`.

        NOTE: This data is fetched in `__init_subclass__`.
        :return:
        """
        # set generic arguments within the class for fetching within `__init_subclass__`
        to_return = super().__class_getitem__(*args)
        setattr(cls, "__class_getitem_args__", args)
        return to_return

    async def run_listener(self):
        """
        Starts a listener for the platform capable of receiving messages from users.
        :return:
        """
        raise NotImplementedError()

    async def send_response(self, message: str, data: SomeCommandData):
        """
        Sends a response back to the user after a command has been processed.
        :return:
        """
        raise NotImplementedError()

    async def get_media_player_data(self, data: CommandData) -> MediaPlayerData:
        """
        Gets a `MediaPlayerData` instance from incoming `CommandData`.  A `MediaPlayerContext`
        is constructed from this data - as a result, this method also provides a hook to validate
        whether a user is authorized to manipulate a media player for the current user's state.
        :param data:
        :return:
        """
        raise NotImplementedError()

    async def join_audio(self, data: MediaPlayerData):
        """
        Joins the audio channel specified by the incoming `MediaPlayerData` object.

        Should gracefully handle conditions where the bot is already connected to the desired channel.

        NOTE: Should not require validation
        :param data:
        :return:
        """
        raise NotImplementedError()

    async def leave_audio(self, data: MediaPlayerData):
        """
        Leaves the current audio channel.

        Should gracefully handle conditions where the bot is already disconnected from
         its current channel.

        NOTE: Should not require validation
        :param data:
        :return:
        """
        raise NotImplementedError()

    async def play_audio(self, media: Media, data: MediaPlayerData):
        """
        Plays the provided `Media` in the audio channel specified by the
        incoming `MediaPlayerData` object.

        NOTE: Should not require validation
        :param media:
        :param data:
        :return:
        """
        raise NotImplementedError()

    async def stop_audio(self, data: MediaPlayerData):
        """
        Stops playback in the audio channel specified by the incoming `MediaPlayerData` object.

        Should gracefully handle conditions where audio isn't currently playing.

        NOTE: Should not require validation
        :param data:
        :return:
        """
        raise NotImplementedError()

    async def is_audio_connected(self, data: MediaPlayerData) -> bool:
        """
        Returns True/False whether the bot is currently connected to the audio channel
        specified by the incoming `MediaPlayerData` object.

        NOTE: Should not require validation
        :param data:
        :return:
        """
        raise NotImplementedError()

    async def is_audio_playing(self, data: MediaPlayerData) -> bool:
        """
        Returns True/False whether the bot is currently playing audio in the audio channel
        specified by the incoming `MediaPlayerData` object.

        NOTE: Should not require validation
        :param data:
        :return:
        """
        raise NotImplementedError()
