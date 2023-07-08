import configparser
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from pydantic import BaseSettings as PydanticBaseSettings
from pydantic.env_settings import SettingsSourceCallable

from bot.utils import ensure_subclass


class BaseSettings(PydanticBaseSettings):
    """
    Provides a settings base class that's configured to utilize the `ini_settings` settings source.
    """

    class Config(PydanticBaseSettings.Config):
        ini_file: ClassVar[None | Path | str] = None
        ini_section: ClassVar[None | str] = None

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> tuple[SettingsSourceCallable, ...]:
            return init_settings, env_settings, ini_settings

    def __init__(
        self,
        _ini_file: Path | str | None = None,
        _ini_section: None | str = None,
        **kwargs,
    ):
        config = ensure_subclass(self.__config__, self.Config)

        if _ini_file:
            config.ini_file = _ini_file
        if _ini_section:
            config.ini_section = _ini_section
        super().__init__(**kwargs)


def ini_settings(settings: PydanticBaseSettings) -> dict:
    """
    A pydantic settings source capable of reading data from ini files
    """
    if not isinstance(settings, BaseSettings):
        return {}
    config = ensure_subclass(settings.__config__, BaseSettings.Config)

    ini_file = config.ini_file
    if not ini_file:
        return {}

    ini_file = Path(ini_file)
    if not ini_file.exists():
        return {}

    parser = configparser.SafeConfigParser()
    parser.read_string(ini_file.read_text())

    ini_section_str = config.ini_section or parser.default_section
    return dict(parser[ini_section_str])


class Configuration(BaseSettings):
    """
    Configuration for the bot.
    """

    class Config(BaseSettings.Config):
        ini_section = "bot"
        env_prefix = "BOT_"

    discord_api_token: str
    discord_server_id: int
    discord_wordle_channel_id: int
    lavalink_url: str

    def get_lavalink_password(self) -> str | None:
        return urlparse(self.lavalink_url).password

    def get_lavalink_uri(self) -> str:
        parts = urlparse(self.lavalink_url)
        return f"{parts.scheme}://{parts.hostname}:{parts.port}"
