"""On-disk transcripts for background AppStream jobs.

The AppStream runner installs through a hidden PTY: unlike the terminal
viewer, nothing it prints survives in a widget or in the process stdout that
bug reports collect. Every job therefore writes its own transcript here, and
this module reads those transcripts back for the failure UI and for reports.
"""

from __future__ import annotations

import os
import re

from .compat import get_linuxtoys_cache_dir

LOG_DIRNAME = "appstream-logs"
LOG_KEEP = 20


def appstream_log_path(name):
    """Filesystem path of one job's transcript, or "" when unavailable."""
    directory = os.path.join(get_linuxtoys_cache_dir(), LOG_DIRNAME)
    try:
        os.makedirs(directory, mode=0o700, exist_ok=True)
    except OSError:
        return ""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name or "job")).strip(".-")[:60]
    return os.path.join(directory, f"{safe or 'job'}.log")


def appstream_log_directory():
    """Directory holding job transcripts (it may not exist yet)."""
    return os.path.join(get_linuxtoys_cache_dir(), LOG_DIRNAME)


def append_appstream_log(name, text):
    """Append one job transcript and prune old ones. Never raises."""
    path = appstream_log_path(name)
    if not path:
        return
    try:
        from datetime import datetime, timezone

        stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}]\n{text.rstrip()}\n\n")
        logs = sorted(
            (
                entry
                for entry in os.scandir(os.path.dirname(path))
                if entry.is_file() and entry.name.endswith(".log")
            ),
            key=lambda entry: entry.stat().st_mtime,
            reverse=True,
        )
        for entry in logs[LOG_KEEP:]:
            try:
                os.remove(entry.path)
            except OSError:
                pass
    except OSError:
        pass


def appstream_log_context(limit: int = 120) -> str:
    """The most recent job transcripts, formatted for a bug report body."""
    directory = appstream_log_directory()
    try:
        entries = sorted(
            (
                entry
                for entry in os.scandir(directory)
                if entry.is_file() and entry.name.endswith(".log")
            ),
            key=lambda entry: entry.stat().st_mtime,
            reverse=True,
        )[:3]
    except OSError:
        return ""
    blocks = []
    for entry in entries:
        try:
            with open(entry.path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read().strip()
        except OSError:
            continue
        if not text:
            continue
        lines = text.splitlines()
        if len(lines) > limit:
            lines = ["... (truncated) ..."] + lines[-limit:]
        blocks.append(f"=== APPSTREAM JOB LOG: {entry.name} ===\n" + "\n".join(lines))
    return "\n\n".join(blocks)


def latest_appstream_log_tail(name, limit: int = 40) -> str:
    """The tail of one app's transcript, for a failure dialog."""
    directory = appstream_log_directory()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name or "job")).strip(".-")[:60]
    path = os.path.join(directory, f"{safe or 'job'}.log")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return ""
    if len(lines) > limit:
        lines = ["... (truncated) ..."] + lines[-limit:]
    return "\n".join(lines).strip()
