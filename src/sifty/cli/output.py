"""Output mode for CLI commands: human (Rich) or machine-readable (--json).

Read-only commands check :func:`json_enabled` and call :func:`emit` instead of
rendering a Rich table, so Sifty can be driven from scripts and scheduled tasks.
"""

from __future__ import annotations

import json
from typing import Any

_json_mode = False


def set_json(enabled: bool) -> None:
    global _json_mode
    _json_mode = enabled


def json_enabled() -> bool:
    return _json_mode


def emit(payload: Any) -> None:
    """Print a payload as a single line of JSON to stdout (Path → str)."""
    print(json.dumps(payload, default=str, ensure_ascii=False))
