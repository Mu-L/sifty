"""Registry primitives for startup Run keys (read + reversible write)."""

from __future__ import annotations

try:  # Windows-only; tests mock these functions.
    import winreg
except ImportError:  # pragma: no cover - non-Windows
    winreg = None  # type: ignore[assignment]

RUN_SUBKEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
# Sifty's own backup location for disabled Run entries (reversible disable).
BACKUP_SUBKEY = r"SOFTWARE\Sifty\DisabledStartup"


def _hive(name: str):
    return winreg.HKEY_LOCAL_MACHINE if name == "HKLM" else winreg.HKEY_CURRENT_USER


def list_subkeys(hive_name: str, subkey: str) -> list[str]:
    """Return names of all direct subkeys under ``hive/subkey`` (empty if absent)."""
    if winreg is None:  # pragma: no cover - non-Windows
        return []
    try:
        key = winreg.OpenKey(_hive(hive_name), subkey)
    except OSError:
        return []
    out: list[str] = []
    with key:
        count = winreg.QueryInfoKey(key)[0]  # index 0 = subkey count
        for i in range(count):
            try:
                out.append(winreg.EnumKey(key, i))
            except OSError:
                continue
    return out


def read_key_values(hive_name: str, subkey: str) -> dict[str, str]:
    """Return all string values in ``hive/subkey`` as {name: value} (empty if absent)."""
    if winreg is None:  # pragma: no cover - non-Windows
        return {}
    try:
        key = winreg.OpenKey(_hive(hive_name), subkey)
    except OSError:
        return {}
    out: dict[str, str] = {}
    with key:
        count = winreg.QueryInfoKey(key)[1]  # index 1 = value count
        for i in range(count):
            try:
                name, value, _ = winreg.EnumValue(key, i)
                out[name] = str(value)
            except OSError:
                continue
    return out


def list_run_values(hive_name: str, subkey: str = RUN_SUBKEY) -> list[tuple[str, str]]:
    """Return (name, command) pairs from a Run key (empty if absent)."""
    if winreg is None:  # pragma: no cover - non-Windows
        return []
    try:
        key = winreg.OpenKey(_hive(hive_name), subkey)
    except OSError:
        return []
    out: list[tuple[str, str]] = []
    with key:
        count = winreg.QueryInfoKey(key)[1]
        for i in range(count):
            try:
                name, value, _ = winreg.EnumValue(key, i)
                out.append((name, str(value)))
            except OSError:
                continue
    return out


def write_run_value(hive_name: str, subkey: str, name: str, value: str) -> None:
    """Set a Run value, creating the key if needed (raises on permission error)."""
    key = winreg.CreateKey(_hive(hive_name), subkey)
    with key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def delete_run_value(hive_name: str, subkey: str, name: str) -> None:
    """Delete a Run value (raises on permission error / missing value)."""
    with winreg.OpenKey(_hive(hive_name), subkey, 0, winreg.KEY_SET_VALUE) as key:
        winreg.DeleteValue(key, name)
