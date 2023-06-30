from discord import Interaction

from bot.bot import bot
from bot.error import BotCommandError
from bot.player import Player
from bot.utils import get_bot_voice_data, get_user_voice_channel


@bot.tree.command(description="asks the bot to join your voice channel")
async def join(interaction: Interaction):
    user_voice_channel = get_user_voice_channel(interaction)
    if not user_voice_channel:
        raise BotCommandError(f"You're not currently in a voice channel")

    bot_voice_data = get_bot_voice_data(interaction)
    if bot_voice_data:
        bot_voice_client, bot_voice_channel = bot_voice_data
        # NOTE: because other commands invoke this command to ensure a bot has joined the user's channel, this if statement cannot throw an exception
        # (as it captures the case where the bot *already is* in the user's channel)
        if bot_voice_channel.id == user_voice_channel.id:
            return
        if len(bot_voice_channel.members) > 1:
            raise BotCommandError(f"The bot is currently in another active channel")
        await bot_voice_client.leave()

    await user_voice_channel.connect(cls=Player)
    if not interaction.response.is_done():
        await interaction.response.send_message(
            f"The bot has joined your voice channel"
        )
