import enum
import logging
import math
from typing import List, Optional

import jinja2
import pydantic

from bot.commands import base
from bot.integrations.down_for_across import Integration as DownForAcross, Puzzle
from bot.platforms import CommandContext
from bot.utils import split


logger = logging.getLogger(__name__)


class State(enum.Enum):
    Search = "search"
    SearchResults = "search_results"
    FetchGameURL = "fetch_game_url"
    Selection = "selection"
    NoResults = "no_results"
    Cancelled = "cancelled"


class CommandData(base.CommandData):
    state: State = State.Search
    search_results: List[Puzzle] = pydantic.Field(default_factory=list)
    query: str = ""
    page_number: int = 1
    game_url: str = ""
    selection: int = -1
    page_size: int = 10

    def set_page_number(self, page_number: int):
        self.page_number = min(page_number, self.total_pages())
        self.page_number = max(1, page_number)

    def next_page(self):
        self.set_page_number(self.page_number + 1)

    def previous_page(self):
        self.set_page_number(self.page_number - 1)

    def select_puzzle(self, index: int):
        if 1 <= index <= len(self.page()):
            self.selection = index
            self.state = State.FetchGameURL

    def start_search(self, query: str):
        self.query = query
        self.state = State.Search

        self.page_number = self.__fields__["page_number"].get_default()
        self.selection = self.__fields__["selection"].get_default()
        self.search_results = self.__fields__["search_results"].get_default()

    def set_search_results(self, search_results: List[Puzzle]):
        self.search_results = search_results
        self.state = State.SearchResults
        if not self.search_results:
            self.state = State.NoResults

    def set_game_url(self, game_url: str):
        self.game_url = game_url
        self.state = State.Selection

    def cancel(self):
        self.state = State.Cancelled

    def page(self) -> List[Puzzle]:
        start = (self.page_number - 1) * self.page_size
        end = start + self.page_size
        return self.search_results[start:end]

    def total_pages(self) -> int:
        return math.ceil(len(self.search_results) / self.page_size)

    def selected_puzzle(self) -> Optional[Puzzle]:
        if self.selection is not None:
            return self.page()[self.selection - 1]
        return None

    def render(self) -> str:
        if self.state == State.Search:
            return search_template.render(data=self)
        elif self.state == State.FetchGameURL:
            return fetch_game_url_template.render(data=self)
        elif self.state == State.SearchResults:
            return search_result_template.render(data=self)
        elif self.state == State.Selection:
            return selection_template.render(data=self)
        elif self.state == State.NoResults:
            return no_results_template.render(data=self)
        elif self.state == State.Cancelled:
            return cancelled_template.render(data=self)

    def should_continue_conversation(self) -> bool:
        return self.state not in [State.Selection, State.NoResults, State.Cancelled]


class Command(base.Command[CommandData]):
    name = "cw"
    help = "search for and play crosswords from downforacross.comm"

    async def process_message(
        self,
        message: str,
        context: CommandContext,
        *,
        down_for_across: DownForAcross = None,
        **kwargs,
    ):
        if self.data.state == State.Search:
            _, query = split(message)
            logger.debug(f"processing search: {query}")

            self.data.start_search(query)
            await context.send_response(self.data.render())

            search_results = await down_for_across.search(query)
            self.data.set_search_results(search_results)

        elif self.data.state == State.SearchResults:
            command, rest = split(message)
            if command == "next":
                logger.debug(f"processing search results: next page")
                self.data.next_page()
            if command == "prev":
                logger.debug(f"processing search results: previous page")
                self.data.previous_page()
            if command == "cancel":
                logger.debug(f"processing search results: cancel")
                self.data.cancel()
            if command == "play":
                index, rest = split(rest)
                logger.debug(f"processing search results: play {index}")

                self.data.select_puzzle(int(index))
                await context.send_response(self.data.render())

                puzzle = self.data.selected_puzzle()
                game_url = await down_for_across.play(puzzle)
                self.data.set_game_url(game_url)
                await context.send_response(self.data.render())

        await context.send_response(self.data.render())
        return self.data.should_continue_conversation()


search_template = jinja2.Template(
    """
Searching for {i}{{data.query}}{i}...
"""
)

search_result_template = jinja2.Template(
    """
Showing results for {i}{{data.query}}{i} ({{data.page_number}} of {{data.total_pages()}})
{% for puzzle in data.page() -%}
{b}{{loop.index}}.{b} {{puzzle.title}} by {{puzzle.author}}
{% endfor %}
{c}{cp}next{c} for next page
{c}{cp}prev{c} for previous page
{c}{cp}play <number>{c} to select a puzzle
{c}{cp}cancel{c} to cancel
"""
)

fetch_game_url_template = jinja2.Template(
    """
Obtaining game URL ({b}{{data.selected_puzzle().title}}{b} by {{data.selected_puzzle().author}})
"""
)

selection_template = jinja2.Template(
    """
{{data.game_url}} ({b}{{data.selected_puzzle().title}}{b} by {{data.selected_puzzle().author}})
"""
)


no_results_template = jinja2.Template(
    """
No results found for {b}{{data.query}}{b}.
"""
)

cancelled_template = jinja2.Template(
    """
Cancelled search.
"""
)
