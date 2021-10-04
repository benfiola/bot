import logging
from typing import List, Type

import jinja2
import pydantic

from bot.commands import base
from bot.platforms import CommandContext


logger = logging.getLogger(__name__)


class CommandInfo(pydantic.BaseModel):
    name: str
    help: str

    @classmethod
    def from_command(cls, command: Type[base.Command]):
        return cls(name=command.name, help=command.help)


class CommandData(base.CommandData):
    commands: List[CommandInfo] = pydantic.Field(default_factory=list)

    def render(self):
        return template.render(data=self)


class Command(base.Command[CommandData]):
    name = "help"
    help = "print help text"

    async def process_message(self, message: str, context: CommandContext, **kwargs):
        logger.debug(f"processing")

        commands = sorted(base.Command.list_commands(), key=lambda c: c.name)
        commands = [CommandInfo.from_command(c) for c in commands]
        self.data.commands = commands

        await context.send_response(self.data.render())


template = jinja2.Template(
    """
{%- for command in data.commands -%}
{c}{cp}{{command.name}}{c} {{command.help}}
{% endfor -%}
"""
)
