"""Windows Task Scheduler primitives (wraps schtasks.exe).

Sifty tasks live under a ``\\Sifty\\`` task-folder so they're easy to find and
remove. User tasks don't need Administrator rights.
"""

from __future__ import annotations

import subprocess

TASK_FOLDER = "Sifty"


def _task_path(name: str) -> str:
    return f"\\{TASK_FOLDER}\\{name}"


def available() -> bool:
    try:
        subprocess.run(["schtasks", "/?"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def create(name: str, command: str, sc: str = "WEEKLY", day: str = "SUN", time: str = "03:00") -> tuple[bool, str]:
    """Register/replace a scheduled task. Returns (ok, message)."""
    args = ["schtasks", "/Create", "/F", "/TN", _task_path(name), "/TR", command,
            "/SC", sc, "/ST", time]
    if sc.upper() == "WEEKLY":
        args += ["/D", day]
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    detail = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, detail


def delete(name: str) -> bool:
    result = subprocess.run(
        ["schtasks", "/Delete", "/F", "/TN", _task_path(name)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.returncode == 0


def query() -> list[str]:
    """Return Sifty task names currently registered with Task Scheduler."""
    result = subprocess.run(
        ["schtasks", "/Query", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    names: list[str] = []
    prefix = f"\\{TASK_FOLDER}\\"
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        task_name = line.split('","')[0].strip().strip('"')
        if task_name.startswith(prefix):
            names.append(task_name[len(prefix):])
    return names
