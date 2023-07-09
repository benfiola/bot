import datetime
import re

from discord import ClientUser, Message, TextChannel
from discord.ext import tasks
from discord.ext.commands import Cog

from bot.bot import bot
from bot.utils import ensure_instance


def has_reaction(emoji: str, message: Message) -> bool:
    """
    Helper function that returns True if the bot has already reacted to `message` with `emoji`.
    """
    for reaction in message.reactions:
        if reaction.emoji != emoji:
            continue
        if reaction.me:
            return True
    return False


@bot.cog
class Wordle(Cog):
    """
    Cog that polls a specific discord channel for wordle results.

    The current winners for the latest wordle puzzle receive a winner emoji reaction.
    Anyone who bricks the latest wordle puzzle (X/6) receives a brick emoji reaction.
    """

    def __init__(self):
        self.loop.start()

    @tasks.loop(seconds=60.0)
    async def loop(self):
        """
        Loop that performs wordle result polling.
        """
        winner_emoji = "👑"
        brick_emoji = "🧱"
        brick_score = 1000

        regex = re.compile(r"Wordle (\d+) ([\d]+|X)/(\d+)")

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
            number, score, *_ = match.groups()

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
                # remove winner reactions for no-longer-winning scores
                if score != lowest_score and has_reaction(winner_emoji, message):
                    bot_user = ensure_instance(bot.user, ClientUser)
                    await message.remove_reaction(winner_emoji, bot_user)
                # add winner reactions to currently winning scores
                if score == lowest_score and not has_reaction(winner_emoji, message):
                    await message.add_reaction(winner_emoji)
                # add brick emoji for brick scores
                if score == brick_score and not has_reaction(brick_emoji, message):
                    await message.add_reaction(brick_emoji)

    @loop.before_loop
    async def before_loop(self):
        """
        Ensures the bot is ready before polling begins
        """
        await bot.wait_until_ready()
