import configparser
import functools
import inspect
import logging
import pathlib
import traceback
from typing import Dict, List

from bot.commands import Command
from bot.config import Configuration
from bot.integrations import Integration
from bot.media import MediaPlayer
from bot.platforms import Platform, CommandContext, CommandData, MediaPlayerContext
from bot.storage import Storage
from bot.utils import split


logger = logging.getLogger(__name__)


class Bot:
    """
    Main bot object.

    Intended to glue together the various systems of the app.
    """

    integrations: Dict[str, Integration]
    platform: Platform
    storage: Storage
    media_players: Dict[str, MediaPlayer]

    def __init__(self, platform: Platform, storage: Storage, integrations: List[Integration]):
        self.platform = platform
        self.storage = storage
        self.integrations = {i.name: i for i in integrations}
        self.media_players = {}

        self.platform.on_ready = self.platform_on_ready
        self.platform.process_message = self.process_message
        self.platform.get_media_player = self.load_media_player

    async def get_command(self, message: str, context: CommandContext):
        """
        Gets a command from storage given the provided context.

        If not found, creates a new command from the given context.
        :param message:
        :param context:
        :return:
        """
        command = await self.storage.load_conversation(context)
        if not command:
            logger.debug(f"getting command: new ({context.data.hash()})")
            command_name, _ = split(message)
            command = Command.get_command(command_name)()
        else:
            logger.debug(f"getting command: in storage ({context.data.hash()})")
        return command

    async def media_player_save(self, media_player: MediaPlayer):
        """
        Saves the provided media player.  Assigned to `media_player.save`
         for all media players that pass through `Bot.load_media_player`.
        :param media_player:
        :return:
        """
        logger.debug(f"saving media player: ({media_player.context.data.hash()})")
        if not media_player.data.queue:
            await self.storage.delete_media_player(media_player)
        else:
            await self.storage.save_media_player(media_player)

    async def load_media_player(self, context: MediaPlayerContext) -> MediaPlayer:
        """
        Given a context, will create and cache media players.  For all media players,
         will load data from storage and will register callbacks.
        :param context:
        :return:
        """
        logger.debug(f"loading media player: ({context.data.hash()})")
        media_player = self.media_players.setdefault(context.data.hash(), MediaPlayer(context))
        media_player.save = self.media_player_save
        await self.storage.load_media_player(media_player)
        return media_player

    async def process_message(self, message: str, command_data: CommandData):
        """
        Assigned to `Platform.process_message` - is intended to be called by the platform when
        a message is received.

        Encapsulates the message processing routine of the bot framework.
        :param message:
        :param command_data:
        :return:
        """
        logger.debug(f"processing message: {command_data.hash()}")
        context = CommandContext(platform=self.platform, data=command_data)

        try:
            # obtain command
            command = await self.get_command(message, context)

            # create command callback with injected integrations
            process_message = self.inject_integrations(command.process_message)

            # call command callback
            continue_conversation = await process_message(message, context)

            # persist (or delete) depending on whether conversation is continuing
            if not continue_conversation:
                await self.storage.delete_conversation(context)
            else:
                await self.storage.save_conversation(context, command)
        except Exception as e:
            # log command processing errors as final message in conversation
            message = f"{{cb}}{traceback.format_exc()}{{cb}}"
            await context.send_response(message)
            await self.storage.delete_conversation(context)
            logger.exception(e)

    async def platform_on_ready(self):
        """
        Registered to `Platform.on_ready` and performs post-initialization steps
         that require the platform to be online.

        :return:
        """
        logger.debug(f"platform ready")

        logger.debug(f"loading media players")
        await self.storage.load_all_media_players(self.platform)
        for media_player in self.media_players.values():
            await media_player.start()

    def inject_integrations(self, func: callable) -> callable:
        """
        Inspects a command's callable, determines required integrations and injects them.

        Returns a callable with all integrations injected.
        :param func:
        :return:
        """
        signature = inspect.signature(func)
        bound = signature.bind_partial()

        for parameter_name, parameter in signature.parameters.items():
            parameter_typehint = parameter.annotation

            if parameter_typehint == signature.empty:
                # no typehint provided - ignore
                continue

            if not issubclass(parameter_typehint, Integration):
                # not an integration subclass - ignore
                continue

            # obtain integration from registry
            integration_name = parameter_typehint.name
            integration = self.integrations.get(integration_name)
            assert integration is not None, f"cannot inject integration: {integration_name}"

            # add integration as additional parameter to be injected
            bound.arguments[parameter_name] = integration

        partial = functools.partial(func, **bound.kwargs)

        return partial

    async def start(self):
        """
        Starts the bot.
        :return:
        """
        logger.debug(f"starting bot")
        await self.storage.initialize()
        await self.platform.run_listener()

    @classmethod
    async def create_from_configuration(cls, configuration: Configuration):
        """
        Convenience method to create a `Bot` from provided configuration.
        :param configuration:
        :return:
        """
        # instantiate storage
        storage_cfg = configuration.storage
        storage = Storage.registry[storage_cfg.name](**storage_cfg.kwargs)

        # instantiate platform
        platform_cfg = configuration.platform
        platform = Platform.registry[platform_cfg.name](**platform_cfg.kwargs)

        integrations = []
        for integration_cfg in configuration.integrations:
            # instantiate integration
            integration = Integration.registry[integration_cfg.name](**integration_cfg.kwargs)
            integrations.append(integration)

        # assemble bot
        bot = cls(storage=storage, platform=platform, integrations=integrations)
        return bot
