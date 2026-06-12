"""Home dashboard: health checkup, volume gauges, and clickable stat cards.

Stat summaries are cached on the app (``_home_cache``) so returning to Home
shows the last values instantly instead of re-running every scan; the slow
workers only re-fire when the cache is stale (or via Refresh). Each stat card
deep-links to its screen on click. The checkup hero runs the read-only
``core.checkup`` suite and renders findings with one-tap action buttons.
"""

from __future__ import annotations

import logging
import time

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ...console import human_size
from ...core import apps as apps_mod
from ...core import checkup, disk, history, junk, services, startup, updates
from ...core.checkup import Finding
from ...windows import winget
from ...windows.admin import is_admin
from ..widgets import Panel, usage_gauge
from .base import BaseView

logger = logging.getLogger("sifty.tui")

_CACHE_TTL = 300.0  # seconds before a cached stat is considered stale

_SEVERITY_DOT = {"ok": "[green]●[/green]", "info": "[yellow]●[/yellow]",
                 "attention": "[red]●[/red]"}


class StatCard(Panel):
    """A stat panel that deep-links to its screen when clicked."""

    def __init__(self, *children, title: str = "", nav_key: str = "", **kwargs) -> None:
        super().__init__(*children, title=title, **kwargs)
        self.add_class("stat-card")
        self._nav_key = nav_key
        if nav_key:
            self.border_subtitle = "open ▸"

    async def on_click(self) -> None:
        if self._nav_key:
            await self.app.show(self._nav_key)


class HomeView(BaseView):
    def compose(self) -> ComposeResult:
        yield Static("Overview", classes="title")
        if is_admin():
            yield Static("[green]●[/green] Administrator — all tasks available.",
                         classes="subtle")
        else:
            yield Static(
                "[yellow]●[/yellow] Standard user — some tasks need elevation.  "
                "[@click=app.elevate][b]Elevate (F2)[/b][/]",
                classes="subtle",
            )
        with Panel(title="Health checkup", id="checkup-panel"):
            yield Static(
                "Scan everything at once: junk, updates, registry orphans, stale "
                "downloads, disk space and startup. Read-only — nothing is changed.",
                classes="subtle",
            )
            with Horizontal(classes="actions"):
                yield Button("Run checkup", id="run-checkup", variant="primary")
                yield Button("Refresh stats", id="refresh-stats")
            yield Vertical(id="checkup-results")
        yield Panel(Static("Reading volumes…", id="vol-body"), title="Volumes")
        with Horizontal(classes="stat-row"):
            yield StatCard(Static("…", id="junk-summary"), title="Junk", nav_key="junk")
            yield StatCard(Static("checking…", id="updates-summary"), title="Updates", nav_key="updates")
        with Horizontal(classes="stat-row"):
            yield StatCard(Static("…", id="apps-summary"), title="Apps", nav_key="apps")
            yield StatCard(Static("…", id="startup-summary"), title="Startup", nav_key="startup")
        with Horizontal(classes="stat-row"):
            yield StatCard(Static("…", id="services-summary"), title="Services", nav_key="services")
            yield StatCard(Static("…", id="history-summary"), title="History", nav_key="reports")

    def on_mount(self) -> None:
        self._render_volumes()  # fast (psutil), no worker needed
        self._set("history-summary", self._history_text())  # fast (sqlite)
        self._load_stats()

    def _load_stats(self, force: bool = False) -> None:
        """Show cached summaries; only re-scan the ones that are stale."""
        loaders = {
            "junk-summary": self.compute_junk,
            "apps-summary": self.compute_apps,
            "startup-summary": self.compute_startup,
            "services-summary": self.compute_services,
            "updates-summary": self.compute_updates,
        }
        cache = self._cache()
        now = time.monotonic()
        for wid, loader in loaders.items():
            cached = cache.get(wid)
            if cached is not None:
                self._set(wid, cached[0])
            stale = force or cached is None or now - cached[1] > _CACHE_TTL
            if stale and self.workers_enabled():
                loader()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "run-checkup":
            event.button.disabled = True
            await self.query_one("#checkup-results", Vertical).remove_children()
            await self.query_one("#checkup-results", Vertical).mount(
                Static("[dim]Running checkup…[/dim]", classes="subtle")
            )
            self.run_checkup_worker()
        elif bid == "refresh-stats":
            self._load_stats(force=True)
        elif bid.startswith("fix-"):
            await self.app.show(bid.removeprefix("fix-"))

    # ----------------------------------------------------------------- checkup
    @work(thread=True, exclusive=True, group="home-checkup")
    def run_checkup_worker(self) -> None:
        try:
            findings = checkup.run_checkup()
        except Exception:
            logger.exception("Home: checkup failed")
            findings = []
        self.app.call_from_thread(self._show_findings, findings)

    async def _show_findings(self, findings: list[Finding]) -> None:
        try:
            self.query_one("#run-checkup", Button).disabled = False
            results = self.query_one("#checkup-results", Vertical)
        except Exception:
            return  # view was navigated away mid-scan
        await results.remove_children()
        if not findings:
            await results.mount(Static("Checkup failed — see `sifty logs`.", classes="subtle"))
            return
        for f in findings:
            dot = _SEVERITY_DOT.get(f.severity, "")
            row = Horizontal(classes="finding-row")
            await results.mount(row)
            await row.mount(Static(f"{dot} [b]{f.label}[/b] — {f.summary}", classes="finding-text"))
            if f.action_label and f.action_key:
                await row.mount(Button(f.action_label, id=f"fix-{f.action_key}", classes="fix"))
        issues = sum(1 for f in findings if f.severity != "ok")
        verdict = (f"[b]{issues}[/b] item(s) worth a look." if issues
                   else "[green]All clear — nothing needs attention.[/green]")
        await results.mount(Static(verdict, classes="status"))

    # ----------------------------------------------------------------- render
    def _cache(self) -> dict:
        cache = getattr(self.app, "_home_cache", None)
        if cache is None:
            cache = {}
            self.app._home_cache = cache
        return cache

    def _set(self, widget_id: str, text, *, remember: bool = False) -> None:
        try:
            self.query_one(f"#{widget_id}", Static).update(text)
        except Exception:
            pass
        if remember:
            self._cache()[widget_id] = (text, time.monotonic())

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
            return "no history yet"
        if not summ["runs"]:
            return "nothing cleaned yet"
        return f"reclaimed [b]{human_size(summ['bytes_freed'])}[/b] over {summ['runs']} runs"

    # ----------------------------------------------------------------- workers
    @work(thread=True, exclusive=True, group="home-junk")
    def compute_junk(self) -> None:
        try:
            total = sum(cat.size for cat in junk.scan())
        except Exception:
            logger.exception("Home: junk total scan failed")
            return
        self.app.call_from_thread(
            self._set, "junk-summary", f"[b]{human_size(total)}[/b] reclaimable", remember=True
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
            value = (f"[b]{len(installed)}[/b] installed\nlargest: {largest.name} "
                     f"({human_size(largest.size_bytes)})")
        else:
            value = "none found"
        self.app.call_from_thread(self._set, "apps-summary", value, remember=True)

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
            f"[b]{len(entries)}[/b] programs · {enabled} enabled", remember=True,
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
            f"[b]{present}[/b] optional · {disabled} disabled", remember=True,
        )

    @work(thread=True, exclusive=True, group="home-updates")
    def compute_updates(self) -> None:
        try:
            if not winget.available():
                value = "winget unavailable"
            else:
                ups = updates.list_upgrades()
                value = f"[b]{len(ups)}[/b] available" if ups else "up to date"
        except Exception:
            logger.exception("Home: updates summary failed")
            return
        self.app.call_from_thread(self._set, "updates-summary", value, remember=True)
