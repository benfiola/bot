import wavelink
from discord import Interaction

from bot.bot import bot
from bot.error import BotCommandError
from bot.utils import call_command, ensure_bot_voice_data


@bot.tree.command(description="add an audio url to the bot's current audio queue")
async def url(interaction: Interaction, url: str):
    from bot.commands.join import join

    # ensure the bot has joined the user's channel before attempting to add a song to the queue
    await call_command(join, interaction)
    bot_voice_client, _ = ensure_bot_voice_data(interaction)

    try:
        track = (await wavelink.GenericTrack.search(url))[0]
    except Exception:
        raise BotCommandError(f"Invalid audio url")

    track.title = url
    await bot_voice_client.enqueue(track)
    await interaction.response.send_message(
        f"Added '{url}' to the bot's current audio queue"
    )
