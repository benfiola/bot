import datetime
import logging
import re

from discord import ClientUser, Message, Reaction, TextChannel
from discord.ext import tasks
from discord.ext.commands import Cog

from bot.bot import bot
from bot.utils import ensure_instance

logger = logging.getLogger(__name__)


def has_reaction(emoji: str, message: Message) -> bool:
    """
    Helper function that returns True when the bot has reacted to a specific message.
    """
    for reaction in message.reactions:
        if reaction.emoji != emoji:
            continue
        if reaction.me:
            return True
    return False


async def add_reaction(emoji: str, message: Message):
    """
    Helper function that reacts to a message using the bot user.

    If the reaction already exists, is a no-op.
    """
    if not has_reaction(emoji, message):
        await message.add_reaction(emoji)


async def remove_reaction(emoji: str, message: Message, user: ClientUser):
    """
    Helper function that removes an existing bot reaction from a message

    If no reaction exists, is a no-op.
    """
    if has_reaction(emoji, message):
        await message.remove_reaction(emoji, user)


@bot.cog
class Wordle(Cog):
    """
    Cog that polls a specific discord channel for wordle results.

    The current winners for the latest wordle puzzle receive a winner emoji reaction.
    Anyone who bricks the latest wordle puzzle (X/6) receives a brick emoji reaction.
    Any wordle boards with all green squares receives a green emoji reaction.
    Any wordle boards with all yellow squares receives a yellow emoji reaction.
    """

    def __init__(self):
        # treat all exceptions as retryable
        # TODO: determine more specific exception classes
        self.loop.add_exception_type(Exception)
        self.loop.start()

    @tasks.loop(seconds=60.0)
    async def loop(self):
        """
        Loop that performs wordle result polling.
        """
        try:
            winner_emoji = "👑"
            brick_emoji = "🧱"
            green_emoji = "🟩"
            yellow_emoji = "🟨"
            brick_score = 1000

            regex = re.compile(r"Wordle (\d+) ([\d]+|X)/\d+")

            channel_id = bot.get_configuration().discord_wordle_channel_id
            channel = ensure_instance(bot.get_channel(channel_id), TextChannel)
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            one_day_ago = now - datetime.timedelta(days=1)
            two_days_ago = now - datetime.timedelta(days=2)

            # collect wordle results
            results: dict[int, dict[int, list[Message]]] = {}
            recent_results = False
            async for message in channel.history(after=two_days_ago):
                match = regex.search(message.content)
                if not match:
                    continue
                if message.created_at >= one_day_ago:
                    recent_results = True
                number, score = match.groups()

                # transform brick score ('X') into a numeric value for consistent parsing
                score = f"{brick_score}" if score == "X" else score

                number, score = map(int, (number, score))
                results.setdefault(number, {}).setdefault(score, []).append(message)

            # if no wordle results have been posted in the last day, don't do anything
            if not recent_results:
                return

            # determine the latest wordle match and the current winning score
            latest_wordle_match = max(results.keys())
            lowest_score = min(results[latest_wordle_match])

            # manipulate message reactions
            for score, score_messages in results[latest_wordle_match].items():
                for message in score_messages:
                    is_brick = score == brick_score
                    is_winner = score == lowest_score
                    has_green = green_emoji in message.content
                    has_yellow = yellow_emoji in message.content
                    bot_user = ensure_instance(bot.user, ClientUser)

                    # remove winner reaction for no-longer-winning scores
                    if not is_winner:
                        await remove_reaction(winner_emoji, message, bot_user)

                    # add winner reaction to currently winning scores
                    if is_winner:
                        await add_reaction(winner_emoji, message)

                    # add brick reaction for brick scores
                    if is_brick:
                        await add_reaction(brick_emoji, message)

                    # add green reaction if wordle board is all green
                    if has_green and not has_yellow:
                        await add_reaction(green_emoji, message)

                    # add yellow reaction if wordle board is all yellow
                    if has_yellow and not has_green:
                        await add_reaction(yellow_emoji, message)

        except Exception as e:
            # NOTE: retryable exceptions (see __init__) are not logged - log them explicitly for informational purposes
            logger.exception(f"wordle task raised exception", exc_info=e)
            raise e

    @loop.before_loop
    async def before_loop(self):
        """
        Ensures the bot is ready before polling begins
        """
        await bot.wait_until_ready()
