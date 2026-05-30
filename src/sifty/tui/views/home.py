"""Home dashboard: volume gauges + at-a-glance stat widgets per area."""

from __future__ import annotations

import logging

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Grid
from textual.widgets import Button, Static

from ...console import human_size
from ...core import apps as apps_mod
from ...core import disk, history, junk, services, startup, updates
from ...windows import winget
from ...windows.admin import is_admin
from ..widgets import Panel, usage_gauge
from .base import BaseView

logger = logging.getLogger("sifty.tui")


class HomeView(BaseView):
    def compose(self) -> ComposeResult:
        yield Static("Overview", classes="title")
        yield Panel(Static("Reading volumes…", id="vol-body"), title="Volumes")
        with Grid(id="home-stats"):
            yield Panel(Static("…", id="junk-total"), title="Junk")
            yield Panel(Static("Checking…", id="updates-summary"), title="Updates")
            yield Panel(Static("…", id="apps-summary"), title="Apps")
            yield Panel(Static("…", id="startup-summary"), title="Startup")
            yield Panel(Static("…", id="services-summary"), title="Services")
            yield Panel(Static("…", id="history-summary"), title="History")
        if not is_admin():
            with Panel(title="Administrator"):
                yield Static(
                    "[yellow]●[/yellow] Running as a standard user. Some tasks "
                    "(Windows Temp, Update cache, some uninstalls) need elevation.",
                    classes="subtle",
                )
                yield Button("Restart as administrator", id="elevate", variant="primary")
        else:
            yield Panel(
                Static("[green]●[/green] Running as administrator — all tasks available."),
                title="Administrator",
            )

    def on_mount(self) -> None:
        self._render_volumes()  # fast (psutil), no worker needed
        self._set("history-summary", self._history_text())  # fast (sqlite)
        if self.workers_enabled():
            self.compute_junk_total()
            self.compute_apps()
            self.compute_startup()
            self.compute_services()
            self.compute_updates()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "elevate":
            self.app.action_elevate()

    # ----------------------------------------------------------------- helpers
    def _set(self, widget_id: str, text) -> None:
        try:
            self.query_one(f"#{widget_id}", Static).update(text)
        except Exception:
            pass

    def _render_volumes(self) -> None:
        text = Text()
        for i, v in enumerate(disk.volumes()):
            if i:
                text.append("\n\n")
            text.append(
                f"{v.mountpoint}   {human_size(v.used)} / {human_size(v.total)}"
                f"   ({human_size(v.free)} free)\n",
                style="bold",
            )
            text.append(usage_gauge(v.percent))
        self._set("vol-body", text)

    def _history_text(self) -> str:
        try:
            summ = history.summary()
        except Exception:
            return "No history yet."
        if not summ["runs"]:
            return "Nothing cleaned yet."
        return f"Reclaimed [b]{human_size(summ['bytes_freed'])}[/b] over {summ['runs']} runs"

    # ----------------------------------------------------------------- workers
    @work(thread=True, exclusive=True, group="home-junk")
    def compute_junk_total(self) -> None:
        try:
            total = sum(cat.size for cat in junk.scan())
        except Exception:
            logger.exception("Home: junk total scan failed")
            return
        self.app.call_from_thread(
            self._set, "junk-total",
            f"[b]{human_size(total)}[/b] reclaimable [dim](open Junk to clean)[/dim]",
        )

    @work(thread=True, exclusive=True, group="home-apps")
    def compute_apps(self) -> None:
        try:
            installed = apps_mod.installed_apps()
        except Exception:
            logger.exception("Home: apps summary failed")
            return
        if installed:
            largest = max(installed, key=lambda a: a.size_bytes)
            text = (f"[b]{len(installed)}[/b] installed · largest: "
                    f"{largest.name} ({human_size(largest.size_bytes)})")
        else:
            text = "No apps found."
        self.app.call_from_thread(self._set, "apps-summary", text)

    @work(thread=True, exclusive=True, group="home-startup")
    def compute_startup(self) -> None:
        try:
            entries = startup.list_entries()
        except Exception:
            logger.exception("Home: startup summary failed")
            return
        enabled = sum(1 for e in entries if e.enabled)
        self.app.call_from_thread(
            self._set, "startup-summary",
            f"[b]{len(entries)}[/b] programs · {enabled} enabled",
        )

    @work(thread=True, exclusive=True, group="home-services")
    def compute_services(self) -> None:
        try:
            items = services.list_services()
        except Exception:
            logger.exception("Home: services summary failed")
            return
        present = sum(1 for s in items if s.present)
        disabled = sum(1 for s in items if s.start_type == "disabled")
        self.app.call_from_thread(
            self._set, "services-summary",
            f"[b]{present}[/b] optional · {disabled} disabled",
        )

    @work(thread=True, exclusive=True, group="home-updates")
    def compute_updates(self) -> None:
        try:
            if not winget.available():
                text = "winget unavailable"
            else:
                ups = updates.list_upgrades()
                text = f"[b]{len(ups)}[/b] updates available" if ups else "Up to date"
        except Exception:
            logger.exception("Home: updates summary failed")
            return
        self.app.call_from_thread(self._set, "updates-summary", text)
