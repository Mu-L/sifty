"""Sifty command-line entry point (thin: wires command groups, calls core)."""

from __future__ import annotations

import sys

import typer

from .. import __version__
from ..console import console, error, warn
from ..infra.logging import get_logger, log_file, setup_logging
from ..windows.admin import is_admin, relaunch_as_admin
from . import output
from .commands import ai_group, apps, disk, junk, organize, updates

app = typer.Typer(
    name="sifty",
    help="Sifty — AI-assisted Windows maintenance: junk, disk, apps, updates, files.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(junk.app, name="junk")
app.add_typer(disk.app, name="disk")
app.add_typer(apps.app, name="apps")
app.add_typer(updates.app, name="update")
app.add_typer(organize.app, name="organize")
app.add_typer(ai_group.app, name="ai")


@app.callback()
def main(
    admin: bool = typer.Option(
        False, "--admin", "--elevate",
        help="Relaunch elevated (UAC) so admin-only tasks can run.",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Also write debug logs to stderr.",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON (read-only commands).",
    ),
) -> None:
    """Sifty — AI-assisted Windows maintenance."""
    setup_logging(verbose)
    output.set_json(json_output)
    get_logger("sifty.cli").debug("invoked: %s", " ".join(sys.argv[1:]))
    if admin and not is_admin():
        if relaunch_as_admin():
            raise typer.Exit()  # elevated process takes over in a new window
        warn("Elevation was declined; continuing without administrator rights.")


@app.command("tui")
def tui_cmd() -> None:
    """Launch the interactive full-screen TUI."""
    from ..tui.app import run  # lazy import: keeps CLI startup fast

    run()


@app.command("version")
def version_cmd() -> None:
    """Show the Sifty version."""
    console.print(f"Sifty {__version__}")


@app.command("doctor")
def doctor_cmd() -> None:
    """Report environment readiness (admin rights, winget, Ollama)."""
    from ..ai.client import OllamaClient
    from ..windows import winget

    admin = is_admin()
    has_winget = winget.available()
    client = OllamaClient.from_config()
    ollama = client.is_available()
    if output.json_enabled():
        output.emit({
            "administrator": admin,
            "winget": has_winget,
            "ollama_model": client.model,
            "ollama_reachable": ollama,
            "log_file": str(log_file()),
        })
        return
    console.print(f"Administrator: {'[green]yes[/green]' if admin else '[yellow]no[/yellow] (some junk/uninstall actions need it)'}")
    console.print(f"winget: {'[green]available[/green]' if has_winget else '[red]missing[/red]'}")
    console.print(f"Ollama ({client.model}): {'[green]reachable[/green]' if ollama else '[yellow]not running[/yellow]'}")
    console.print(f"Log file: [dim]{log_file()}[/dim]")


@app.command("logs")
def logs_cmd(
    tail: int = typer.Option(40, "--tail", "-n", help="Show the last N lines."),
    path_only: bool = typer.Option(False, "--path", help="Print the log file path only."),
) -> None:
    """Show the diagnostics log (location and recent lines)."""
    path = log_file()
    if path_only:
        console.print(str(path))
        return
    if not path.exists():
        console.print("No log file yet — nothing has been logged.")
        return
    console.print(f"[dim]{path}[/dim]\n")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-tail:]:
        console.print(line, markup=False, highlight=False)


def entrypoint() -> None:
    """Console-script entry point: set up logging and capture fatal crashes."""
    setup_logging()
    try:
        app()
    except SystemExit:
        raise  # normal Typer/Click exit
    except KeyboardInterrupt:
        raise
    except Exception:
        get_logger("sifty.cli").exception("Fatal error")
        error(f"Sifty hit an unexpected error. Details written to {log_file()}")
        raise SystemExit(1)


if __name__ == "__main__":
    entrypoint()
