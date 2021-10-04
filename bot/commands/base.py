from __future__ import annotations

from typing import Generic, TypeVar, Type, Dict, List, Optional

import pydantic

from bot.platforms import CommandContext


class CommandData(pydantic.BaseModel):
    def render(self):
        raise NotImplementedError()


SomeCommandData = TypeVar("SomeCommandData", bound=CommandData)


class Command(Generic[SomeCommandData]):
    """
    Base command implementation.

    A command represents a single (or ongoing), fixed interaction between the bot and the end user.

    name: the name (and initial root command) this class maps to
    help: a short description of the command

    data: data for the command used for rendering messages and maintaining state across subsequent interactions
    data_cls: data class of which `data` is an instance - used for de(serialization) of data
    registry: a mapping of `name` -> `cls` for all imported commands

    """

    name: str = None
    help: str = None

    data: SomeCommandData
    data_cls: Type[SomeCommandData] = CommandData
    registry: Dict[str, Type[Command]] = {}

    def __init__(self):
        # instantiate data with initial state on creation - persistent storage should replace this.
        self.data = self.data_cls()

    def __init_subclass__(cls):
        """
        When defining a command:
            class NewCommand(Platform[Data]):
        will fetch `(Data)` from the `cls` object at `__class_getitem_args__`.

        NOTE: This data is fetched in `__init_subclass__`.

        Will additionally ensure subclasses define `name` and `help`.
        Will additionally register subclasses within `cls.registry`.

        :return:
        """
        ((data_cls),) = getattr(cls, "__class_getitem_args__")
        if not isinstance(data_cls, TypeVar):
            cls.data_cls = data_cls

        assert cls.name is not None, f"{cls.__name__}.name unset"
        assert cls.help is not None, f"{cls.__name__}.help unset"

        exists = cls.registry.get(cls.name)
        assert exists is None, f"{cls.name} already registered: {exists.__name__}"

        cls.registry[cls.name] = cls

    def __class_getitem__(cls, *args):
        """
        When defining a command:
            class NewCommand(Command[Data]):
        will store `(Data)` in the `cls` object at `__class_getitem_args__`.

        NOTE: This data is fetched in `__init_subclass__`.
        :return:
        """
        setattr(cls, "__class_getitem_args__", args)
        return super().__class_getitem__(*args)

    async def process_message(
        self, message: str, context: CommandContext, **kwargs
    ) -> Optional[bool]:
        """
        Main entry point into a command.

        Processes the `message`, uses the `context` to interact with the bot and end user.

        Optionally, can specify integrations that will be detected and injected by the bot at runtime.

        :param message:
        :param context:
        :param kwargs:
        :return:
        """
        raise NotImplementedError()

    @classmethod
    def get_command(cls, name: str) -> Type[Command]:
        """
        Fetches a command by name from the registry
        :param name:
        :return:
        """
        exists = cls.registry.get(name)
        assert exists is not None, f"command not found: {name}"
        return exists

    @classmethod
    def list_commands(cls) -> List[Type[Command]]:
        """
        Lists all commands registered to this class.
        :return:
        """
        return list(cls.registry.values())
