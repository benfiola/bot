from click import Context, group, make_pass_decorator, option
from pathlib import Path

from backend.configuration import Configuration


pass_configuration = make_pass_decorator(Configuration)


def entry_point():
    grp_map()


@group()
@pass_context
@option("ini-file", type=Path)
def grp_main(ctx: Context, ini_file: Path | None = None):
    configuration = Configuration.parse_obj(dict(_ini_file=ini_file))
    ctx.obj = configuration


@grp_main.command("server")
@pass_configuration
def cmd_server(configuration: Configuration):
    pass


if __name__ == "__main__":
    entry_point()
