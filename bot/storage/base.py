from __future__ import annotations

from typing import Optional, List, Dict, Type

from bot.commands import Command
from bot.media import MediaPlayer
from bot.platforms import CommandContext, Platform


class Storage:
    """
    Abstract storage interface intended to provide persistence to the bot.

    Because commands have state that can span several user <-> bot interactions,
    the sum of these interactions are called `conversations`.
    """

    name: str = None
    registry: Dict[str, Type[Storage]] = {}

    def __init__(self, **kwargs):
        pass

    def __init_subclass__(cls, **kwargs):
        assert cls.name is not None, f"{cls.__name__}.name unset"
        exists = cls.registry.get(cls.name)
        assert exists is None, f"{cls.name} already registered: {exists.__name__}"
        cls.registry[cls.name] = cls

    async def initialize(self):
        """
        Hook for initialization on bot startup.
        :return:
        """
        pass

    async def load_conversation(self, command: CommandContext) -> Optional[Command]:
        """
        Given a command context, load an existing conversation from the database.

        Returns a `Command` if a conversation found.
        :param command:
        :return:
        """
        raise NotImplementedError()

    async def save_conversation(self, context: CommandContext, command: Command):
        """
        Given a command + context, save the state as a conversation within the database.

        :param context:
        :param command:
        :return:
        """
        raise NotImplementedError()

    async def delete_conversation(self, context: CommandContext):
        """
        Given a context, delete a conversation within the database.

        :param context:
        :return:
        """
        raise NotImplementedError()

    async def load_all_media_players(self, platform: Platform) -> List[MediaPlayer]:
        """
        Given a platform, loads all attached media players from the database.

        This is done (usually) as a bot initialization step.  It is expected that
        media players are created using `Platform.get_media_player(context)` - as
        this will properly initialize media players with callbacks attached.

        :param platform:
        :return:
        """
        raise NotImplementedError()

    async def load_media_player(self, media_player: MediaPlayer):
        """
        Given a media player, loads state from storage.

        :param media_player:
        :return:
        """
        raise NotImplementedError()

    async def save_media_player(self, media_player: MediaPlayer):
        """
        Given a media player, saves state into storage.

        :param media_player:
        :return:
        """
        raise NotImplementedError()

    async def delete_media_player(self, media_player: MediaPlayer):
        """
        Given a media player, deletes state from storage

        :param media_player:
        :return:
        """
        raise NotImplementedError()
