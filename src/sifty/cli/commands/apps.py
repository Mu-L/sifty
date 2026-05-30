"""`sifty apps` — list installed apps and startup items, uninstall via winget."""

from __future__ import annotations

import typer
from rich.table import Table

from ...console import confirm, console, error, human_size, success, warn
from ...core import apps
from .. import output

app = typer.Typer(help="List, inspect, and remove installed apps and startup items.")


@app.command("list")
def list_cmd(
    sort_by_size: bool = typer.Option(False, "--by-size", help="Sort by disk size (largest first)."),
    limit: int = typer.Option(0, "--limit", "-n", help="Show only the first N apps (0 = all)."),
) -> None:
    """List installed applications."""
    items = apps.installed_apps()
    if sort_by_size:
        items = sorted(items, key=lambda a: a.size_bytes, reverse=True)
    if limit:
        items = items[:limit]

    if output.json_enabled():
        output.emit([
            {"name": a.name, "version": a.version, "publisher": a.publisher,
             "size_bytes": a.size_bytes}
            for a in items
        ])
        return

    table = Table(title=f"Installed apps ({len(items)})")
    table.add_column("Name")
    table.add_column("Version", style="dim")
    table.add_column("Publisher", style="dim")
    table.add_column("Size", justify="right")
    for a in items:
        table.add_row(a.name, a.version, a.publisher, human_size(a.size_bytes) if a.size_bytes else "—")
    console.print(table)


@app.command("startup")
def startup_cmd() -> None:
    """List programs that launch at startup."""
    entries = apps.startup_entries()
    if output.json_enabled():
        output.emit([
            {"name": e.name, "location": e.location, "command": e.command}
            for e in entries
        ])
        return
    table = Table(title=f"Startup programs ({len(entries)})")
    table.add_column("Name")
    table.add_column("Origin", style="dim")
    table.add_column("Command")
    for e in entries:
        table.add_row(e.name, e.location, e.command)
    console.print(table)


@app.command("uninstall")
def uninstall_cmd(
    name: str = typer.Argument(..., help="App name (or winget id) to uninstall."),
    apply: bool = typer.Option(False, "--apply", help="Actually run the uninstaller."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Uninstall an app via winget (preferred) with a dry-run preview."""
    from ...windows import winget

    if not winget.available():
        error("winget is not available on this system.")
        raise typer.Exit(1)

    if not apply:
        console.print(f"[dim]Dry-run:[/dim] would run [cyan]winget uninstall --name \"{name}\"[/cyan]")
        console.print("[dim]Re-run with --apply to uninstall.[/dim]")
        return

    if not confirm(f"Uninstall '{name}'?", assume_yes=yes):
        warn("Cancelled.")
        return

    ok, message = apps.uninstall_app(name)
    if ok:
        success(message)
    else:
        error(message)
        raise typer.Exit(1)
