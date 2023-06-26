from typing import Literal

from discord import ButtonStyle, Interaction, SelectOption
from discord.ui import button, select
from wavelink import Playable

from bot.bot import bot
from bot.utils import (
    ensure_bot_voice_data,
    get_bot_voice_data,
    get_user_voice_channel,
    is_user_in_bot_voice_channel,
)
from bot.view import View as BaseView

empty_select_option = SelectOption(label="", value="")


class View(BaseView):
    """
    Provides a view that allows users to manipulate the bot's current audio queue

    Utilizes a select list to allow users to choose tracks to remove from the queue.
    However, select lists have a maximum size (25 items) - thus the queue display is paged.
    """

    state: Literal["open"] | Literal["closed"]
    page_number: int
    page_size: int
    skip_selected_track: Playable | None

    def __init__(self, interaction: Interaction):
        super().__init__(interaction=interaction)
        self.page_number = 0
        self.page_size = 25
        self.skip_selected_track = None
        self.state = "open"

    def get_queue(self) -> list[Playable]:
        """
        Helper method that fetches the current queue from the bot.
        """
        queue = []
        bot_voice_data = get_bot_voice_data(self.interaction)
        if bot_voice_data:
            bot_voice_client, _ = bot_voice_data
            if bot_voice_client.current:
                queue.append(bot_voice_client.current)
            queue.extend(bot_voice_client.queue)
        return queue

    def get_max_page_number(self) -> int:
        """
        Helper method that determines the last page of queue data.
        """
        return int(len(self.get_queue()) / self.page_size)

    def get_current_page(self) -> list[Playable]:
        """
        Derives the current page from 'page_number' and 'page_size'
        """
        start_index = self.page_number * self.page_size
        end_index = start_index + self.page_size
        return self.get_queue()[start_index:end_index]

    def get_icon(self) -> str:
        """
        Gets a play or pause icon depending on the player state
        """
        bot_voice_client, _ = ensure_bot_voice_data(self.interaction)
        if bot_voice_client.is_paused():
            icon = "⏸"
        else:
            icon = "⏵"
        return icon

    async def update(self, interaction: Interaction | None = None):
        """
        Prepares and dispatches a view update to the discord servers
        """
        complete = False
        show_actions = False

        if self.state == "open":
            # ensure that the page number is within bounds
            self.page_number = min(self.page_number, self.get_max_page_number())

            # clear the existing select list
            self.skip_select._underlying.options.clear()

            # build the queue text and select list
            offset = self.page_number * self.page_size
            lines = []
            for index, item in enumerate(self.get_current_page()):
                queue_position = offset + index
                icon = ""
                if queue_position == 0:
                    icon = self.get_icon()

                lines.append(f"{queue_position + 1}. {icon} {item.title}")
                select_option = SelectOption(
                    label=f"{queue_position + 1}. {item.title}",
                    value=str(queue_position),
                    default=self.skip_selected_track == item,
                )
                self.skip_select.append_option(select_option)
            content = "\n".join(lines)

            # configure UI component enablement
            self.play_pause_button.disabled = any(
                [
                    len(self.get_queue()) == 0,
                    not is_user_in_bot_voice_channel(self.interaction),
                ]
            )
            self.next_page_button.disabled = (
                self.page_number >= self.get_max_page_number()
            )
            self.prev_page_button.disabled = self.page_number <= 0
            self.skip_select.disabled = any(
                [
                    len(self.get_current_page()) == 0,
                    not is_user_in_bot_voice_channel(self.interaction),
                ]
            )
            self.skip_button.disabled = any(
                [
                    len(self.get_current_page()) == 0,
                    self.skip_selected_track is None,
                    not is_user_in_bot_voice_channel(self.interaction),
                ]
            )
            # NOTE: select lists cannot be empty - use an empty option if there are no items in the page
            if not self.get_current_page():
                self.skip_select.append_option(empty_select_option)

            show_actions = True
        elif self.state == "closed":
            content = "The command has been cancelled"
            complete = True
        else:
            raise NotImplementedError(self.state)

        await self.dispatch(
            content=content,
            interaction=interaction,
            show_actions=show_actions,
            complete=complete,
        )

    @button(label="Refresh", row=0, style=ButtonStyle.primary)
    async def refresh_button(self, interaction: Interaction, button):
        await self.update(interaction=interaction)

    @button(label="Play/Pause", row=0, style=ButtonStyle.primary)
    async def play_pause_button(self, interaction: Interaction, button):
        if is_user_in_bot_voice_channel(self.interaction):
            bot_voice_client, _ = ensure_bot_voice_data(interaction)
            if bot_voice_client.is_paused():
                await bot_voice_client.resume()
            else:
                await bot_voice_client.pause()
        await self.update(interaction=interaction)

    @button(label="Skip Selected Song", row=0, style=ButtonStyle.danger)
    async def skip_button(self, interaction: Interaction, button):
        if self.skip_selected_track and is_user_in_bot_voice_channel(self.interaction):
            bot_voice_client, _ = ensure_bot_voice_data(interaction)
            await bot_voice_client.remove(self.skip_selected_track)
            self.skip_selected_track = None
        await self.update(interaction=interaction)

    @select(
        options=[empty_select_option],
        placeholder="Select a song to skip",
        row=1,
    )
    async def skip_select(self, interaction: Interaction, select):
        if interaction.data is None:
            raise Exception(f"selection data not found")

        values: list[str] = interaction.data.get("values", [])
        if not values:
            raise Exception(f"selected values not found")

        queue_position = values[0]
        if not queue_position:
            return

        queue_position = int(queue_position)
        self.skip_selected_track = self.get_queue()[queue_position]
        await self.update(interaction=interaction)

    @button(label="Previous", row=2, style=ButtonStyle.secondary)
    async def prev_page_button(self, interaction: Interaction, button):
        self.page_number = max(self.page_number - 1, 0)
        self.skip_selected_track = None
        await self.update(interaction=interaction)

    @button(label="Next", row=2, style=ButtonStyle.secondary)
    async def next_page_button(self, interaction: Interaction, button):
        max_page_number = int(len(self.get_queue()) / self.page_size)
        self.page_number = min(self.page_number + 1, max_page_number)
        self.skip_selected_track = None
        await self.update(interaction=interaction)

    @button(label="Cancel", row=2, style=ButtonStyle.danger)
    async def close_button(self, interaction: Interaction, button):
        self.state = "closed"
        await self.update(interaction=interaction)


@bot.tree.command(description="interact with the bot's current audio queue")
async def queue(interaction: Interaction):
    await View.create(interaction=interaction)
