"""Persist the user's Textual theme between runs.

The theme name is stored as JSON in the LinuxToys cache directory, the
same place used by the startup recommendation marker. Every function
here is best-effort: a missing or corrupt file simply means "no saved
theme", and a write failure is logged and never raised.
"""

from __future__ import annotations

import json
import logging
import os

from app import compat

logger = logging.getLogger(__name__)

_FILE_NAME = "tui-theme.json"


def _theme_path() -> str:
    return os.path.join(compat.get_linuxtoys_cache_dir(), _FILE_NAME)


def load_theme() -> str | None:
    """Return the saved theme name, or None if there is none.

    Returns:
        The theme name. None if the file is missing, unreadable,
        corrupt or does not hold a string.
    """
    try:
        with open(_theme_path(), "r", encoding="utf-8") as handle:
            value = json.load(handle).get("theme")
    except (OSError, ValueError, AttributeError):
        return None
    return value if isinstance(value, str) and value else None


def save_theme(name: str) -> None:
    """Save the theme name, on a best-effort basis.

    Writes to a temporary file and moves it into place with
    ``os.replace``, so a reader never sees a partial file. An I/O error
    is logged as a warning and not raised.

    Args:
        name: Name of the Textual theme.
    """
    path = _theme_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump({"theme": name}, handle)
        os.replace(tmp, path)
    except OSError as exc:
        logger.warning("Could not save the TUI theme: %s", exc)
