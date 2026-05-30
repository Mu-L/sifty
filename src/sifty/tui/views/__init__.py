"""Content views, one per sidebar section."""

from __future__ import annotations

from .ai import AIView
from .apps import AppsView
from .cleanup import CleanupView
from .disk import DiskView
from .home import HomeView
from .junk import JunkView
from .reports import ReportsView
from .startup import StartupView
from .updates import UpdatesView

# Maps a sidebar nav key to its view class.
VIEWS = {
    "home": HomeView,
    "junk": JunkView,
    "disk": DiskView,
    "cleanup": CleanupView,
    "apps": AppsView,
    "startup": StartupView,
    "updates": UpdatesView,
    "reports": ReportsView,
    "ai": AIView,
}

__all__ = [
    "VIEWS",
    "HomeView",
    "JunkView",
    "DiskView",
    "CleanupView",
    "AppsView",
    "StartupView",
    "UpdatesView",
    "ReportsView",
    "AIView",
]
