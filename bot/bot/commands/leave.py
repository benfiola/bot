from discord import Interaction

from bot.bot import bot
from bot.error import BotCommandError
from bot.utils import get_bot_voice_data, get_user_voice_channel


@bot.tree.command(description="asks the bot to leave its voice channel")
async def leave(interaction: Interaction):
    bot_voice_data = get_bot_voice_data(interaction)
    if not bot_voice_data:
        raise BotCommandError(f"The bot isn't currently in a voice channel")
    bot_voice_client, bot_voice_channel = bot_voice_data

    user_voice_channel = get_user_voice_channel(interaction)
    if not user_voice_channel or user_voice_channel.id != bot_voice_channel.id:
        if len(bot_voice_channel.members) > 1:
            raise BotCommandError(
                "The bot is currently in another active voice channel"
            )

    await bot_voice_client.leave()
    await interaction.response.send_message(f"The bot has left its voice channel")
