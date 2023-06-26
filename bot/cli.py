from pathlib import Path

import click

from bot.bot import bot
from bot.configuration import Configuration
from bot.logs import configure_loggers


def entry_point():
    grp_main()


pass_configuration = click.make_pass_decorator(Configuration)


@click.group()
@click.option("--ini-file", type=Path)
@click.pass_context
def grp_main(context: click.Context, ini_file: Path | None):
    configuration = Configuration.parse_obj(dict(_ini_file=ini_file))
    context.obj = configuration
    configure_loggers()


@grp_main.command("run")
@pass_configuration
def cmd_run(configuration: Configuration):
    bot.configure(configuration)
    bot.run()


if __name__ == "__main__":
    entry_point()
