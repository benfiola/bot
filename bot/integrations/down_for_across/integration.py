from __future__ import annotations

import asyncio
import logging
from typing import List

import pydantic
import requests.auth

from bot.integrations.base import Integration as IntegrationBase
from bot.utils import create_browser

logger = logging.getLogger(__name__)


class Integration(IntegrationBase):
    """
    downforacross integration
    """

    name = "down-for-across"

    def __init__(self):
        self.client = Client()

    async def search(self, query: str) -> List[Puzzle]:
        """
        Searches downforacross for puzzles
        :param query:
        :return:
        """
        logger.debug(f"search: {query}")
        return await self.client.puzzle_list(query)

    @staticmethod
    async def play(puzzle: Puzzle):
        """
        Obtains a play URL for a given puzzle.
        :param puzzle:
        :return:
        """
        logger.debug(f"play: {puzzle.id}")
        return await get_game_url(puzzle)


class Puzzle(pydantic.BaseModel):
    id: str
    author: str
    title: str


class Client:
    def __init__(self):
        self.base_url = "https://api.foracross.com/api"
        self.session = requests.Session()

    async def puzzle_list(self, name: str) -> List[Puzzle]:
        """
        Implementation of GET https://api.foracross.com/api/puzzle_list API.
        :param name:
        :return:
        """

        def inner():
            url = f"{self.base_url}/puzzle_list"

            params = dict()
            params["page"] = 0
            params["pageSize"] = 50
            params["filter[nameOrTitleFilter]"] = name
            params[f"filter[sizeFilter][Mini]"] = "true"
            params[f"filter[sizeFilter][Standard]"] = "true"

            return self.session.get(url, params=params)

        response = await asyncio.get_event_loop().run_in_executor(None, inner)
        response.raise_for_status()

        data = response.json()
        puzzles = []
        for item in data["puzzles"]:
            puzzle_id = item["pid"]
            author = item["content"]["info"]["author"]
            title = item["content"]["info"]["title"]
            puzzle = Puzzle(id=puzzle_id, author=author, title=title)
            puzzles.append(puzzle)

        return puzzles


async def get_game_url(puzzle: Puzzle) -> str:
    """
    Uses selenium to open a browser to the given puzzle play link.
    Navigates to the play link, waits for the URL to change to a game URL, and closes the browser.

    This is because downforacross utilizes websockets to initialize a game session
    and there's no API to do so programmatically - thus requiring web automation.
    :param puzzle:
    :return:
    """
    frontend_url = f"https://downforacross.com/beta"
    play_url = f"{frontend_url}/play/{puzzle.id}"
    game_url = f"{frontend_url}/game"

    with create_browser() as browser:

        async def poll_for_game_url():
            while not browser.current_url.startswith(game_url):
                await asyncio.sleep(0.1)

        browser.get(play_url)
        await asyncio.wait_for(poll_for_game_url(), timeout=10)

        return browser.current_url
