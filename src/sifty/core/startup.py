"""Startup manager (engine): list and reversibly enable/disable startup items.

Disabling is reversible: Run-key values move to a Sifty-owned backup key, and
Startup-folder shortcuts move to a Sifty backup folder. Enabling moves them back.
HKLM Run entries require Administrator rights (the registry call raises without).
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from ..infra.config import app_data_dir
from ..windows import registry
from .models import StartupEntry

logger = logging.getLogger("sifty.core")

__all__ = ["list_entries", "disable", "enable", "set_enabled"]

_RUN_HIVES = [("HKCU", "hkcu-run"), ("HKLM", "hklm-run")]


def _startup_folder() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _disabled_folder() -> Path:
    path = app_data_dir() / "disabled_startup"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _backup_subkey(hive: str) -> str:
    return f"{registry.BACKUP_SUBKEY}\\{hive}"


def list_entries() -> list[StartupEntry]:
    """All startup entries: enabled (live) and disabled (in Sifty's backup)."""
    entries: list[StartupEntry] = []

    for hive, kind in _RUN_HIVES:
        for name, command in registry.list_run_values(hive, registry.RUN_SUBKEY):
            entries.append(StartupEntry(name, command, f"{hive} Run", enabled=True, kind=kind))
        for name, command in registry.list_run_values(hive, _backup_subkey(hive)):
            entries.append(StartupEntry(name, command, f"{hive} Run (disabled)", enabled=False, kind=kind))

    folder = _startup_folder()
    if folder and folder.exists():
        for item in folder.iterdir():
            if item.is_file():
                entries.append(StartupEntry(item.stem, str(item), "Startup folder", enabled=True, kind="folder"))
    for item in _disabled_folder().iterdir():
        if item.is_file():
            entries.append(StartupEntry(item.stem, str(item), "Startup folder (disabled)", enabled=False, kind="folder"))

    return entries


def _hive_for(kind: str) -> str:
    return "HKLM" if kind.startswith("hklm") else "HKCU"


def disable(entry: StartupEntry) -> bool:
    """Move an enabled entry to the backup location. Returns success."""
    try:
        if entry.kind.endswith("-run"):
            hive = _hive_for(entry.kind)
            registry.write_run_value(hive, _backup_subkey(hive), entry.name, entry.command)
            registry.delete_run_value(hive, registry.RUN_SUBKEY, entry.name)
            return True
        if entry.kind == "folder":
            src = Path(entry.command)
            shutil.move(str(src), str(_disabled_folder() / src.name))
            return True
    except OSError:
        logger.exception("Failed to disable startup entry %s", entry.name)
    return False


def enable(entry: StartupEntry) -> bool:
    """Move a disabled entry back to its live location. Returns success."""
    try:
        if entry.kind.endswith("-run"):
            hive = _hive_for(entry.kind)
            registry.write_run_value(hive, registry.RUN_SUBKEY, entry.name, entry.command)
            registry.delete_run_value(hive, _backup_subkey(hive), entry.name)
            return True
        if entry.kind == "folder":
            src = Path(entry.command)
            folder = _startup_folder()
            if folder is None:
                return False
            shutil.move(str(src), str(folder / src.name))
            return True
    except OSError:
        logger.exception("Failed to enable startup entry %s", entry.name)
    return False


def set_enabled(name: str, enabled: bool) -> bool:
    """Toggle the first entry matching ``name`` to the desired state (by name)."""
    for entry in list_entries():
        if entry.name == name and entry.enabled != enabled:
            return enable(entry) if enabled else disable(entry)
    return False
