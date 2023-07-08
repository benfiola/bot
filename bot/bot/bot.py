import logging
from typing import Type

from discord import Intents
from discord.ext.commands import Cog, Context
from discord.ext.commands.bot import Bot as BaseBot
from wavelink import Node, NodePool

from bot.configuration import Configuration

logger = logging.getLogger(__name__)


class Bot(BaseBot):
    _configuration: Configuration | None
    _cog_classes: list[Type[Cog]]

    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=";;", intents=intents)
        self._configuration = None
        self._cog_classes = []

    def cog(self, cog_class: Type[Cog]):
        """
        Registers a cog with the bot using the provided `name`
        """
        self._cog_classes.append(cog_class)

    async def guild_check(self, ctx: Context):
        """
        Ensures the bot only listens to events originating from the configured guild
        """
        if not ctx.guild:
            return False
        return ctx.guild.id == self.get_configuration().discord_server_id

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
        # initialize cogs
        configuration = self.get_configuration()
        guild = self.get_guild(configuration.discord_server_id)
        if not guild:
            raise RuntimeError(f"guild not found: {configuration.discord_server_id}")
        for cog_class in self._cog_classes:
            cog = cog_class()
            await self.add_cog(cog, guild=guild)

        # sync commands with server
        await self.tree.sync()

    async def setup_hook(self):
        """
        Called after launch but before being ready.  Allows initialization + configuration of other dependencies
        """
        # initialize wavelink
        configuration = self.get_configuration()
        kwargs: dict = {"password": configuration.get_lavalink_password()}
        node = Node(uri=configuration.get_lavalink_uri(), **kwargs)
        await NodePool.connect(client=self, nodes=[node])

    async def start(self, *args, **kwargs):
        """
        Wrapper around the superclasses' `start` method - but utilizes the attached configuration to start the bot.
        """
        configuration = self.get_configuration()
        return await super().start(configuration.discord_api_token, **kwargs)

    def run(self, *args, **kwargs):
        """
        Wrapper around the superclasses' `run` method - but utilizes the attached configuration to start the bot.
        """
        configuration = self.get_configuration()
        return super().run(configuration.discord_api_token, **kwargs)


bot = Bot()
