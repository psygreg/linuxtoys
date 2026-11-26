"""Persistent queue for Nix package operations.

Nix installs are declarative: selecting a package records an operation here and
nothing is built until the user presses "Apply Nix package operations" on the
queue view. The queue survives restarts so a pending rebuild is never lost.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path

from .atomic_io import atomic_write_json

QUEUE_PATH = Path(
    os.environ.get(
        "LINUXTOYS_NIX_QUEUE",
        str(
            Path(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"))
            / "linuxtoys"
            / "nix"
            / "queue.json"
        ),
    )
)
SCHEMA = 1
_ATTR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_'-]*$")
_LOCK = threading.RLock()
_CHANGE_CALLBACK = None


def set_change_callback(callback):
    """Register a GTK-side refresh callback (invoked from any worker thread)."""
    global _CHANGE_CALLBACK
    _CHANGE_CALLBACK = callback


def _notify():
    callback = _CHANGE_CALLBACK
    if callback is None:
        return
    try:
        callback()
    except Exception:
        pass


def _read():
    try:
        payload = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, UnicodeError):
        return {"schema": SCHEMA, "operations": []}
    if not isinstance(payload, dict):
        return {"schema": SCHEMA, "operations": []}
    operations = payload.get("operations")
    if not isinstance(operations, list):
        operations = []
    clean = []
    for record in operations:
        if not isinstance(record, dict):
            continue
        attr = str(record.get("attr") or "").strip()
        scope = str(record.get("scope") or "").strip()
        action = str(record.get("action") or "").strip()
        if not _ATTR_RE.fullmatch(attr):
            continue
        if scope not in ("home-manager", "system"):
            continue
        if action not in ("install", "remove"):
            continue
        clean.append(
            {
                "id": str(record.get("id") or f"nix:{attr}:{scope}"),
                "attr": attr,
                "name": str(record.get("name") or attr),
                "scope": scope,
                "action": action,
                "version": str(record.get("version") or ""),
                "icon": str(record.get("icon") or "nix.svg"),
                "created": int(record.get("created") or 0),
            }
        )
    return {"schema": SCHEMA, "operations": clean}


def _write(payload):
    atomic_write_json(QUEUE_PATH, payload, separators=(",", ":"), fsync=True)


def snapshot():
    """Return the current operations, reloading shell-side queue changes."""
    with _LOCK:
        return list(_read()["operations"])


def pending():
    return bool(snapshot())


def pending_for(attr, scope=None):
    attr = str(attr or "").strip()
    scope = str(scope or "").strip()
    return [
        record
        for record in snapshot()
        if record["attr"] == attr and (not scope or record["scope"] == scope)
    ]


def add(info, action="install", scope=None):
    """Queue one operation, replacing any opposite pending action."""
    attr = str(info.get("nix_name") or info.get("package-name") or "").strip()
    if not _ATTR_RE.fullmatch(attr):
        raise ValueError("Invalid Nix package name")
    scope = str(scope or info.get("nix_scope") or "home-manager").strip()
    if scope not in ("home-manager", "system"):
        raise ValueError("Invalid Nix install scope")
    action = str(action or "install").strip()
    if action not in ("install", "remove"):
        raise ValueError("Invalid Nix operation")
    name = str(info.get("name") or attr).strip() or attr
    record_id = f"nix:{attr}:{scope}"
    with _LOCK:
        payload = _read()
        operations = [
            record
            for record in payload["operations"]
            if not (record["attr"] == attr and record["scope"] == scope)
        ]
        operations.append(
            {
                "id": record_id,
                "attr": attr,
                "name": name,
                "scope": scope,
                "action": action,
                "version": str(info.get("nix_version") or info.get("appstream_version") or ""),
                "icon": str(info.get("icon") or "nix.svg"),
                "created": int(time.time()),
            }
        )
        _write({"schema": SCHEMA, "operations": operations})
    _notify()
    return record_id


def remove(record_id):
    with _LOCK:
        payload = _read()
        operations = [record for record in payload["operations"] if record["id"] != record_id]
        if len(operations) == len(payload["operations"]):
            return False
        _write({"schema": SCHEMA, "operations": operations})
    _notify()
    return True


def install_state(info):
    """Resolve the app-page state for a Nix source selection."""
    attr = str(info.get("nix_name") or info.get("package-name") or "").strip()
    scope = str(info.get("nix_scope") or "").strip()
    records = pending_for(attr, scope or None)
    if records:
        return "nix_queued"
    from . import nix_catalog

    if nix_catalog.is_installed(info):
        return "installed"
    return "available"
