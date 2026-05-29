"""Headless smoke tests for the TUI skeleton, via Textual's Pilot harness.

`start_workers=False` keeps the (slow, real-system) junk scan from running so
these stay fast and deterministic.
"""

from __future__ import annotations

from textual.widgets import DataTable, ListView, Static

from sifty.tui.app import SECTIONS, SiftyApp


async def test_app_boots_with_full_sidebar():
    app = SiftyApp(start_workers=False)
    async with app.run_test():
        sidebar = app.query_one("#sidebar", ListView)
        assert len(sidebar.children) == len(SECTIONS)


async def test_home_shows_volumes_table():
    app = SiftyApp(start_workers=False)
    async with app.run_test():
        table = app.query_one("#volumes", DataTable)
        assert table.row_count >= 1  # at least the system drive


async def test_navigation_swaps_to_placeholder():
    app = SiftyApp(start_workers=False)
    async with app.run_test():
        await app.show_placeholder("apps")
        title = app.query_one(".title", Static)
        assert "Apps" in str(title.render())


async def test_junk_total_label_updates():
    app = SiftyApp(start_workers=False)
    async with app.run_test():
        app._set_junk_total(1536)
        label = app.query_one("#junk-total", Static)
        assert "1.5 KB" in str(label.render())
