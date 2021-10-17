from __future__ import annotations

import logging
from typing import Optional, Union

import discord  # noqa

from bot.media import Media
from bot.platforms import base


logger = logging.getLogger(__name__)


class DiscordClient(discord.Client):
    """
    Typed wrapper around base discord client.
    """

    async def fetch_channel(self, channel_id) -> Union[discord.TextChannel, discord.VoiceChannel]:
        return await super().fetch_channel(channel_id)

    async def fetch_guild(self, guild_id) -> discord.Guild:
        return await super().fetch_guild(guild_id)


class DiscordVoiceClient(discord.VoiceClient):
    async def potential_reconnect(self):
        """
        Overrides potential reconnection when bot is forcefully removed from a channel.
        :return:
        """
        await self.disconnect(force=True)
        return False


class CommandData(base.CommandData):
    """
    Data container for discord related state while processing commands.

    response_message_id: Message id for an ongoing conversation between user and bot
    guild_id: Server id for originating message
    channel_id: Text channel id for originating message
    author_id: Author id for originating message
    message_id: Message id for originating message
    voice_channel_id: Voice channel id for author of originating message
    """

    response_message_id: Optional[int] = base.Field(persist=True)
    guild_id: int = base.Field(hash=True)
    channel_id: int = base.Field(hash=True)
    author_id: int = base.Field(hash=True)
    message_id: int
    voice_channel_id: Optional[int] = None


class MediaPlayerData(base.MediaPlayerData):
    """
    Data container for discord related state while running a media player.

    guild_id: Server id for running media player
    channel_id: Voice channel id for running media player
    """

    channel_id: int = base.Field(persist=True, hash=True)
    guild_id: int = base.Field(persist=True, hash=True)


class Platform(base.Platform[CommandData, MediaPlayerData]):
    """
    Platform implementation for discord.
    """

    name = "discord"

    bot_token: str
    command_prefix: str
    discord_client: DiscordClient

    def __init__(self, bot_token: str, command_prefix: str = ";;"):
        self.bot_token = bot_token
        self.command_prefix = command_prefix
        self.discord_client = DiscordClient()
        self.discord_client.on_message = self.receive_message

    async def receive_message(self, message: discord.Message):
        # ignore bot messages
        if message.author == self.discord_client.user:
            logger.debug(f"message received: ignored: bot message ({message.id})")
            return
        # ignore non-commands
        if not message.content.startswith(self.command_prefix):
            logger.debug(f"message received: ignored: not command ({message.id})")
            return

        logger.debug(f"message received: processing ({message.id})")

        # strip command prefix
        content = message.content[len(self.command_prefix) :]

        # assemble command data
        voice_channel_id = None
        if message.author.voice:
            voice_channel_id = message.author.voice.channel.id
        command_data = CommandData(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            author_id=message.author.id,
            voice_channel_id=voice_channel_id,
            message_id=message.id,
        )

        await self.process_message(content, command_data)

    async def run_listener(self):
        logger.debug(f"running listener")

        # attach on_ready listener if defined
        if self.on_ready:
            self.discord_client.on_ready = self.on_ready

        # start login flow
        await self.discord_client.login(self.bot_token)
        await self.discord_client.connect()

    async def send_response(self, content: str, data: CommandData):
        # replace metacharacters
        content = content.replace("{cp}", self.command_prefix)
        content = content.replace("{cb}", "```")
        content = content.replace("{c}", "`")
        content = content.replace("{i}", "*")
        content = content.replace("{b}", "**")

        channel = await self.discord_client.fetch_channel(data.channel_id)
        if not data.response_message_id:
            # if response_message_id unset, create a new message with command response
            logger.debug(f"sending response: create ({data.message_id})")
            message = await channel.send(content=content)
            data.response_message_id = message.id
        else:
            # if response_message_id set, edit existing message with new command response
            logger.debug(f"sending response: edit ({data.message_id})")
            message = await channel.fetch_message(data.response_message_id)
            new_message = await message.reply(content=content)
            data.response_message_id = new_message.id

    async def get_media_player_data(self, data: CommandData) -> MediaPlayerData:
        # ensure user is in a voice channel
        assert data.voice_channel_id, f"user not in voice channel"

        guild = await self.discord_client.fetch_guild(data.guild_id)
        voice_client = guild.voice_client

        # ensure user in same voice channel as bot
        if voice_client:
            assert (
                data.voice_channel_id == voice_client.channel.id
            ), f"bot in different voice channel"

        # assemble media player data
        media_player_data = MediaPlayerData(
            guild_id=data.guild_id, channel_id=data.voice_channel_id
        )
        return media_player_data

    async def join_audio(self, data: MediaPlayerData):
        voice_client = await self._get_voice_client(data)

        if voice_client and voice_client.is_connected():
            if voice_client.channel.id == data.channel_id:
                # if voice client connected to desired channel - do nothing
                return
            # disconnect from existing audio channel
            await voice_client.disconnect()

        # connect to desired channel
        channel = await self.discord_client.fetch_channel(data.channel_id)
        assert isinstance(channel, discord.VoiceChannel)
        await channel.connect(cls=DiscordVoiceClient)

    async def leave_audio(self, data: MediaPlayerData):
        voice_client = await self._get_voice_client(data)

        # handle cases where bot is not connected to a voice channel
        if not voice_client:
            return

        # disconnect from existing channel
        await voice_client.disconnect(force=True)

    async def play_audio(self, media: Media, data: MediaPlayerData):
        voice_client = await self._get_voice_client(data)

        # `before_options` and `options` are necessary to ffmpeg otherwise
        # audio will be cut short during playback.
        source = await discord.FFmpegOpusAudio.from_probe(
            media.url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            options="-vn",
        )

        if voice_client.is_playing():
            # handle case where voice client is currently playing audio
            # (this throws an exception)
            voice_client.stop()
        voice_client.play(source)

    async def stop_audio(self, data: MediaPlayerData):
        voice_client = await self._get_voice_client(data)

        # handle cases where bot is not currently playing audio
        if voice_client is None:
            return
        if not voice_client.is_playing():
            return

        # stop audio playback
        voice_client.stop()

    async def is_audio_connected(self, data: MediaPlayerData) -> bool:
        voice_client = await self._get_voice_client(data)

        if not voice_client:
            return False

        return voice_client.is_connected()

    async def is_audio_playing(self, data: MediaPlayerData) -> bool:
        voice_client = await self._get_voice_client(data)

        if not voice_client:
            return False

        return voice_client.is_playing()

    async def should_stay_connected_to_audio(self, data: MediaPlayerData) -> bool:
        voice_client = await self._get_voice_client(data)

        if not voice_client:
            return False

        channel = voice_client.channel
        if not channel:
            return False

        channel_not_empty = len(channel.members) > 1
        return channel_not_empty

    async def _get_voice_client(self, data: MediaPlayerData) -> Optional[discord.VoiceClient]:
        """
        Convenience method to obtain a voice client.
        :param data:
        :return:
        """
        guild = await self.discord_client.fetch_guild(data.guild_id)
        voice_client = guild.voice_client
        return voice_client
