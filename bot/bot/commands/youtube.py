from typing import Coroutine, Literal

from discord import ButtonStyle, Interaction
from discord.ui import View as BaseView
from discord.ui import button
from wavelink import YouTubeTrack

from bot.bot import bot
from bot.utils import call_command, ensure_bot_voice_data, ensure_instance
from bot.view import View as BaseView


class View(BaseView):
    """
    Provides a view that allows users to query youtube and select a video to add to the bot's audio queue

    Because each row of UI components can contain 5 buttons - youtube search results are paged.
    """

    page_number: int
    page_size: int
    query: str
    selected_track: YouTubeTrack | None
    state: Literal["fetch"] | Literal["results"] | Literal["selection"] | Literal[
        "closed"
    ]
    tracks: list[YouTubeTrack]

    def __init__(self, interaction: Interaction, query: str):
        super().__init__(interaction=interaction)
        self.page_number = 0
        self.page_size = 5
        self.query = query
        self.selected_track = None
        self.state = "fetch"
        self.tracks = []

    @classmethod
    async def create(cls, interaction: Interaction, query: str):
        return await super().create(interaction=interaction, query=query)

    def get_total_pages(self) -> int:
        """
        Returns the last page of the search results
        """
        return int(len(self.tracks) / self.page_size)

    def get_current_page(self) -> list[YouTubeTrack]:
        """
        Derives the current page using `page_number` and `page_size`
        """
        start_index = self.page_number * self.page_size
        end_index = start_index + self.page_size
        return self.tracks[start_index:end_index]

    async def update(self, interaction: Interaction | None = None):
        """
        Prepares a view update and dispatches it to the discord server
        """
        tasks: list[Coroutine] = []
        show_actions = False
        complete = False

        if self.state == "fetch":
            content = f"Fetching results for '{self.query}'"
            tasks.append(self.fetch_tracks())

        elif self.state == "results":
            # prepare the text content
            lines = []
            lines.append(f"Showing results for '{self.query}'.")
            lines.append(f"[ {self.page_number + 1} / {self.get_total_pages() + 1} ]")
            for index, item in enumerate(self.get_current_page()):
                lines.append(f"{index + 1}. {item.title}")
            content = "\n".join(lines)

            # handle UI component enablement
            buttons = [
                self.one_button,
                self.two_button,
                self.three_button,
                self.four_button,
                self.five_button,
            ]
            self.next_button.disabled = self.page_number >= self.get_total_pages()
            self.prev_button.disabled = self.page_number <= 0
            for index, button in enumerate(buttons):
                button.disabled = index >= len(self.get_current_page())

            show_actions = True
        elif self.state == "selection":
            selected_track = ensure_instance(self.selected_track, YouTubeTrack)
            content = f"Added '{selected_track.title} to the bot's current audio queue."
            complete = True
        elif self.state == "closed":
            content = "The command has been cancelled"
            complete = True
        else:
            raise NotImplementedError(self.state)

        await self.dispatch(
            content,
            complete=complete,
            interaction=interaction,
            show_actions=show_actions,
            tasks=tasks,
        )

    async def fetch_tracks(self):
        """
        Performs a youtube search to fetch results for display
        """
        self.tracks = await YouTubeTrack.search(self.query)
        self.state = "results"
        await self.update()

    async def select_track(self, interaction: Interaction, index: int):
        """
        Selects a youtube track and adds it to the audio queue
        """
        from bot.commands.join import join

        selected_track = self.get_current_page()[index]

        # NOTE: this indirectly ensures that the bot and user are in the same channel
        await call_command(join, self.interaction)

        bot_voice_client, _ = ensure_bot_voice_data(interaction)
        await bot_voice_client.enqueue(selected_track)

        self.selected_track = selected_track
        self.state = "selection"

        await self.update(interaction=interaction)

    @button(label="1", row=0, style=ButtonStyle.primary)
    async def one_button(self, interaction: Interaction, button):
        await self.select_track(interaction, 0)

    @button(label="2", row=0, style=ButtonStyle.primary)
    async def two_button(self, interaction: Interaction, button):
        await self.select_track(interaction, 1)

    @button(label="3", row=0, style=ButtonStyle.primary)
    async def three_button(self, interaction: Interaction, button):
        await self.select_track(interaction, 2)

    @button(label="4", row=0, style=ButtonStyle.primary)
    async def four_button(self, interaction: Interaction, button):
        await self.select_track(interaction, 3)

    @button(label="5", row=0, style=ButtonStyle.primary)
    async def five_button(self, interaction: Interaction, button):
        await self.select_track(interaction, 4)

    @button(label="Previous", row=1, style=ButtonStyle.secondary)
    async def prev_button(self, interaction: Interaction, button):
        self.page_number = max(self.page_number - 1, 0)
        await self.update(interaction=interaction)

    @button(label="Next", row=1, style=ButtonStyle.secondary)
    async def next_button(self, interaction: Interaction, button):
        max_page = int(len(self.tracks) / self.page_size)
        self.page_number = min(self.page_number + 1, max_page)
        await self.update(interaction=interaction)

    @button(label="Cancel", row=1, style=ButtonStyle.danger)
    async def close_button(self, interaction: Interaction, button):
        self.state = "closed"
        await self.update(interaction=interaction)


@bot.tree.command(description="adds a youtube video to the bot's current audio queue")
async def youtube(interaction: Interaction, *, query: str):
    await View.create(interaction=interaction, query=query)
