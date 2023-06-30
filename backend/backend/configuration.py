import configparser
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

from pydantic import BaseSettings as PydanticBaseSettings
from pydantic.env_settings import SettingsSourceCallable


class BaseSettings(PydanticBaseSettings):
    """
    Provides a settings base class that's configured to utilize the `ini_settings` settings source.
    """

    class Config(PydanticBaseSettings.Config):
        ini_file: None | Path | str = None
        ini_section: None | str = None

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            return init_settings, ini_settings

    __config__: Config

    def __init__(
        self,
        _ini_file: Path | str | None = None,
        _ini_section: None | str = None,
        **kwargs,
    ):
        if _ini_file:
            self.__config__.ini_file = _ini_file
        if _ini_section:
            self.__config__.ini_section = _ini_section
        super().__init__(**kwargs)


def ini_settings(settings: PydanticBaseSettings) -> dict:
    """
    A pydantic settings source capable of reading data from ini files
    """
    if not isinstance(settings, BaseSettings):
        return {}

    ini_file = settings.__config__.ini_file
    if not ini_file:
        return {}

    ini_file = Path(ini_file)
    if not ini_file.exists():
        return {}

    parser = configparser.SafeConfigParser()
    parser.read_string(ini_file.read_text())

    ini_section_str = settings.__config__.ini_section or parser.default_section
    return dict(parser[ini_section_str])


class Configuration(BaseSettings):
    """
    Configuration for the backend.
    """

    class Config(BaseSettings.Config):
        ini_section = "bot"
