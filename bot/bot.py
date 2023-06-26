import logging

from discord import Intents
from discord.ext.commands.bot import Bot as BaseBot
from wavelink import Node, NodePool

from bot.configuration import Configuration

logger = logging.getLogger(__name__)


class Bot(BaseBot):
    _configuration: Configuration | None

    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=";;", intents=intents)
        self._configuration = None

    def configure(self, configuration: Configuration):
        """
        Attaches the provided configuration to the bot.
        """
        self._configuration = configuration

    def get_configuration(self) -> Configuration:
        """
        Gets the configuration attached to the bot.

        Raises an exception if configuration is not attached to the bot.
        """
        if not self._configuration:
            raise RuntimeError(f"bot is not configured")
        return self._configuration

    async def on_ready(self):
        """
        Called after the bot is ready to receive commands.

        Synchronizes registered application commands with the discord servers
        """
        await self.tree.sync()

    async def setup_hook(self):
        """
        Called after launch but before being ready.  Allows initialization + configuration of other dependencies
        """
        configuration = self.get_configuration()
        kwargs: dict = {"password": configuration.get_lavalink_password()}
        node = Node(uri=configuration.get_lavalink_uri(), **kwargs)
        await NodePool.connect(client=self, nodes=[node])

    async def start(self):
        """
        Wrapper around the superclasses' `start` method - but utilizes the attached configuration to start the bot.
        """
        configuration = self.get_configuration()
        return await super().start(configuration.discord_api_token)

    def run(self):
        """
        Wrapper around the superclasses' `run` method - but utilizes the attached configuration to start the bot.
        """
        configuration = self.get_configuration()
        return super().run(configuration.discord_api_token)


bot = Bot()
