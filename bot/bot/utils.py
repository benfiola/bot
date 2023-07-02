from typing import Any, Awaitable, Callable, Type, TypeVar, cast, TYPE_CHECKING

from discord import Interaction, VoiceState
from discord.app_commands import Command
from discord.channel import VocalGuildChannel
from wavelink.player import VoiceChannel

if TYPE_CHECKING:
    from bot.player import Player

Instance = TypeVar("Instance")


def ensure_instance(obj: Any, v: Type[Instance]) -> Instance:
    """
    Convenience method that asserts a provided object is an instance of the provided type.

    This is because:
    * `assert` statements can be removed from optimized python code
    * typing.TypeGuard requires a `bool` function, and thus, an if statement - negating any benefit of a helper method
    """
    if not isinstance(obj, v):
        raise RuntimeError(f"not an {v.__qualname__} instance")
    return obj


def get_user_voice_channel(interaction: Interaction) -> VocalGuildChannel | None:
    """
    Convenience method to obtain a user voice channel from an interaction.
    """
    # NOTE: interaction.user.voice raises typing errors in the IDE - use 'getattr' as a workaround
    voice_state = cast(None | VoiceState, getattr(interaction.user, "voice", None))
    if not voice_state:
        return None
    return voice_state.channel


def ensure_user_voice_channel(interaction: Interaction) -> VocalGuildChannel:
    """
    Convenience method that ensures a user voice channel exists in an interaction and returns it
    """
    user_voice_channel = get_user_voice_channel(interaction)
    if not user_voice_channel:
        raise RuntimeError(f"user voice channel is None")
    return user_voice_channel


def get_bot_voice_data(interaction: Interaction) -> tuple["Player", VoiceChannel] | None:
    """
    Convenience method to obtain a bot voice client and voice channel from an interaction
    """
    from bot.player import Player
    
    # TODO: is it safe to assume there will always be a guild?
    if interaction.guild is None:
        return
    voice_client = interaction.guild.voice_client
    if not voice_client:
        return None
    # NOTE: voice clients *should* be of `Player` type (look at `join` command)
    voice_client = ensure_instance(voice_client, Player)
    if not voice_client.channel:
        return None
    return voice_client, voice_client.channel


def ensure_bot_voice_data(interaction: Interaction) -> tuple["Player", VoiceChannel]:
    """
    Convenience method that ensures a bot voice client and channel exists in an interaction and returns it
    """
    bot_voice_data = get_bot_voice_data(interaction)
    if not bot_voice_data:
        raise RuntimeError(f"bot voice data is None")
    return bot_voice_data


def is_user_in_bot_voice_channel(interaction: Interaction) -> bool:
    """
    Convenience method that returns True if a user and bot are in the same voice channel
    """
    try:
        user_channel = ensure_user_voice_channel(interaction)
        _, bot_channel = ensure_bot_voice_data(interaction)
        return user_channel.id == bot_channel.id
    except RuntimeError:
        return False


async def call_command(
    command: Any, interaction: Interaction, params: dict | None = None
):
    """
    Helper method to call a command (often, from another command).

    NOTE: This is primarily because `command.callback` is raising typing issues within the IDE.
    """
    params = params or {}
    command = ensure_instance(command, Command)
    func = cast(Callable[[Interaction], Awaitable[None]], command.callback)
    await func(interaction, **params)
