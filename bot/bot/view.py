import asyncio
import datetime
from typing import Coroutine, Type, TypeVar

from discord import Interaction
from discord.ui import View as BaseView

SomeView = TypeVar("SomeView", bound="View")


class View(BaseView):
    """
    Subclass of discord.ui.View that provides additional convenience methods and attributes to be used with bot commands.

    Notably:
    * Provides an async construction interface via `View.create`
    * Provides a update -> dispatch lifecycle via `View.update -> View.dispatch`.
    * Clears views on timeout - ignoring those with `View.complete` set to True
    * Only allows command user to interact with view.
    """

    complete: bool
    interaction: Interaction

    def __init__(
        self, interaction: Interaction, timeout: None | datetime.timedelta = None
    ):
        timeout = timeout or datetime.timedelta(minutes=3)
        super().__init__(timeout=timeout.total_seconds())
        self.complete = False
        self.interaction = interaction

    async def interaction_check(self, interaction: Interaction):
        """
        Prevents any user besides the command invoiker to interact with the view
        """
        return interaction.user.id == self.interaction.user.id

    async def on_timeout(self):
        """
        Cleans up any views that have timed out due to inactivity.

        (Timeout speficied via `timeout` in constructor)
        """
        if not self.complete:
            content = f"Command timed out due to inactivity"
            await self.dispatch(content=content, show_actions=False, complete=True)

    @classmethod
    async def create(
        cls: Type[SomeView], interaction: Interaction, **kwargs
    ) -> SomeView:
        """
        Exposes a interface to instantiate a view and issue an initial update.
        """
        view = cls(interaction=interaction, **kwargs)
        await view.update()
        return view

    async def update(self, interaction: Interaction | None = None):
        """
        Exposes an interface to update a view on state change due to interaction + async activity

        - MUST call `View.dispatch` after performing an update.
        - MUST provide 'interaction' argument if triggered by UI action

        """
        raise NotImplementedError()

    async def dispatch(
        self,
        content: str,
        complete: bool | None = None,
        interaction: Interaction | None = None,
        show_actions: bool | None = None,
        tasks: list[Coroutine] | None = None,
    ):
        """
        Issues an update to the discord server.

        'content' defines the text body of the view
        'complete' marks the view as being complete, which removes all actions, and disables interactivity
        'interaction' allows these updates to be reflected as responses to a UI interaction (otherwise, the interaction that triggered the view is used)
        'show_actions' shows or hides UI buttons/selects but keeps the view interactive
        'tasks' represent side-effects that need to be triggered after this update is performed
        """
        complete = complete if complete is not None else False
        show_actions = show_actions if show_actions is not None else False
        tasks = tasks or []

        # NOTE: completing a view disables interactivity - showing actions wouldn't make sense
        if complete and show_actions:
            raise ValueError(f"show_actions and complete both cannot be True")

        view = self if show_actions else None

        if not self.interaction.response.is_done():
            # NOTE: self.interaction.response.send_message requires view to be missing from kwargs when None
            kwargs = {}
            if view is not None:
                kwargs["view"] = view
            await self.interaction.response.send_message(content=content, **kwargs)
        elif interaction:
            await interaction.response.edit_message(content=content, view=view)
        else:
            await self.interaction.edit_original_response(content=content, view=view)

        if complete:
            self.complete = True
            self.stop()

        await asyncio.gather(*tasks)
