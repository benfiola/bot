from __future__ import annotations

import configparser
import inspect
import pathlib
from typing import Dict, List, Generic, TypeVar, Type, Any

import pydantic.generics

from bot.integrations import Integration as BaseIntegration
from bot.platforms import Platform as BasePlatform
from bot.storage import Storage as BaseStorage

SomeObject = TypeVar("SomeObject")


class RegistryItem(Generic[SomeObject], pydantic.generics.GenericModel):
    """
    Simple data container storing the name of an item within a registry,
     and a set of kwargs that can be used to construct the item within
     the registry.
    """

    name: str
    kwargs: Dict[str, Any]

    @classmethod
    def registry(cls) -> Dict[str, Type[SomeObject]]:
        raise NotImplementedError()


class Storage(RegistryItem[BaseStorage]):
    @classmethod
    def registry(cls) -> Dict[str, Type[BaseStorage]]:
        return BaseStorage.registry


class Integration(RegistryItem[BaseIntegration]):
    @classmethod
    def registry(cls) -> Dict[str, Type[BaseIntegration]]:
        return BaseIntegration.registry


class Platform(RegistryItem[BasePlatform]):
    @classmethod
    def registry(cls) -> Dict[str, Type[BasePlatform]]:
        return BasePlatform.registry


class Configuration(pydantic.BaseModel):
    """
    Lightweight parent configuration object storing containers
     for each of the registry-backed components within the system.
    """

    storage: Storage
    platform: Platform
    integrations: List[Integration]


def parse(config_file: pathlib.Path):
    # parse ini
    parser = configparser.ConfigParser()
    parser.read(config_file)

    # set defaults
    storage = None
    integrations = []
    platform = None

    for section in parser.sections():
        data = dict(parser[section])

        # skip if disabled
        enabled = data.pop("enabled", "false")
        enabled = pydantic.parse_obj_as(bool, enabled)
        if not enabled:
            continue

        # determine config model class
        _, group, name = section.split(".")
        if group.lower() == "integration":
            # parse integration
            cls = cls_from_config_cls(Integration, name)
            kwargs = parse_kwargs(cls, data)
            integration = Integration(kwargs=kwargs, name=name)
            integrations.append(integration)
        elif group.lower() == "storage":
            # parse storage
            cls = cls_from_config_cls(Storage, name)
            kwargs = parse_kwargs(cls, data)
            storage = Storage(kwargs=kwargs, name=name)
        elif group.lower() == "platform":
            # parse platform
            cls = cls_from_config_cls(Platform, name)
            kwargs = parse_kwargs(cls, data)
            platform = Platform(kwargs=kwargs, name=name)
        else:
            raise ValueError(f"unrecognized group: {group}")

    # assemble configuration
    configuration = Configuration(storage=storage, platform=platform, integrations=integrations)
    return configuration


def cls_from_config_cls(config_cls: Type[RegistryItem[SomeObject]], name: str) -> Type[SomeObject]:
    """
    Pulls a registry item at `name` from a given `config_cls`
    :param config_cls:
    :param name:
    :return:
    """
    cls = config_cls.registry().get(name)
    if not cls:
        raise ValueError(f"unrecognized {config_cls.__name__}: {name}")
    return cls


def parse_kwargs(cls: Type, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inspects the given `cls` object and uses type annotations in the constructor
     to correctly parse ini config fields into an appropriate type.

    Returns a dict of kwargs to be provided to the `cls` constructor at a later time.
    :param cls:
    :param data:
    :return:
    """
    signature = inspect.signature(cls)
    kwargs = {}
    for parameter_name, parameter in signature.parameters.items():
        if parameter_name not in data:
            continue
        value = data[parameter_name]
        parameter_type = parameter.annotation
        if parameter_type == signature.empty:
            parameter_type = str
        value = pydantic.parse_obj_as(parameter_type, value)
        kwargs[parameter_name] = value
    return kwargs
