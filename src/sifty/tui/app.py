"""Sifty TUI — M1 skeleton: header, sidebar navigation, and a Home dashboard.

This is the first milestone of the plan in ``docs/TUI_DESIGN.md``: it proves the
frame (sidebar nav + content swapping) and the worker pattern (computing the junk
total off the UI thread). Later milestones replace the per-section placeholders
with real interactive screens.
"""

from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Static,
)

from ..commands import disk, junk
from ..console import human_size

# (nav key, sidebar label) — order defines the menu.
SECTIONS: list[tuple[str, str]] = [
    ("home", "🏠 Home"),
    ("junk", "🧹 Junk"),
    ("disk", "💾 Disk"),
    ("apps", "📦 Apps"),
    ("updates", "⬆ Updates"),
    ("ai", "🤖 AI"),
]


class SiftyApp(App):
    """The top-level Sifty terminal application."""

    CSS = """
    #sidebar { width: 24; border-right: solid $accent; }
    #content { padding: 1 2; }
    .title { text-style: bold; color: $accent; padding-bottom: 1; }
    #volumes { height: auto; margin-bottom: 1; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    TITLE = "Sifty"
    SUB_TITLE = "Windows maintenance"

    def __init__(self, start_workers: bool = True) -> None:
        super().__init__()
        # Lets tests boot the app without kicking off the (slow) junk scan.
        self._start_workers = start_workers

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ListView(
                *[ListItem(Label(label), id=f"nav-{key}") for key, label in SECTIONS],
                id="sidebar",
            )
            yield VerticalScroll(id="content")
        yield Footer()

    async def on_mount(self) -> None:
        await self.show_home()

    # ----------------------------------------------------------------- nav
    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        key = (event.item.id or "nav-home").removeprefix("nav-")
        if key == "home":
            await self.show_home()
        else:
            await self.show_placeholder(key)

    async def _reset_content(self) -> VerticalScroll:
        content = self.query_one("#content", VerticalScroll)
        await content.remove_children()
        return content

    async def show_placeholder(self, key: str) -> None:
        content = await self._reset_content()
        label = dict(SECTIONS).get(key, key)
        await content.mount(Static(label, classes="title"))
        await content.mount(
            Static("Coming soon — see docs/TUI_DESIGN.md for the planned screen.")
        )

    async def show_home(self) -> None:
        content = await self._reset_content()
        await content.mount(Static("Overview", classes="title"))

        table = DataTable(id="volumes")
        table.add_columns("Drive", "Used", "Free", "Total", "Used %")
        for v in disk.volumes():
            table.add_row(
                v.mountpoint,
                human_size(v.used),
                human_size(v.free),
                human_size(v.total),
                f"{v.percent:.0f}%",
            )
        await content.mount(table)
        await content.mount(Label("Reclaimable junk: …", id="junk-total"))

        if self._start_workers:
            self.compute_junk_total()

    # -------------------------------------------------------------- workers
    @work(thread=True, exclusive=True)
    def compute_junk_total(self) -> None:
        """Total reclaimable junk, computed off the UI thread (proves pattern)."""
        try:
            total = sum(cat.size for cat in junk.scan())
        except Exception:
            return
        self.call_from_thread(self._set_junk_total, total)

    def _set_junk_total(self, total: int) -> None:
        try:
            self.query_one("#junk-total", Label).update(
                f"Reclaimable junk: {human_size(total)}"
            )
        except Exception:
            pass

    # -------------------------------------------------------------- actions
    async def action_refresh(self) -> None:
        await self.show_home()


def run() -> None:
    """Entry point used by the ``sifty tui`` command."""
    SiftyApp().run()
