"""Persistent queue for Nix package and extension operations.

Nix installs are declarative: selecting a package records an operation here and
nothing is built until the user presses "Apply Nix package operations" on the
queue view. Extension operations (plugins of a host package) use the same
queue and are applied by the generated extension module. The queue survives
restarts so a pending rebuild is never lost.
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
SCHEMA = 2
_VALID_SCOPES = ("home-manager", "system")
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


def _created(record):
    try:
        return int(record.get("created") or 0)
    except (TypeError, ValueError):
        return 0


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
        kind = str(record.get("kind") or "package").strip() or "package"
        scope = str(record.get("scope") or "").strip()
        action = str(record.get("action") or "").strip()
        if scope not in _VALID_SCOPES:
            continue
        if action not in ("install", "remove"):
            continue
        if kind == "extension":
            host = str(record.get("host") or "").strip()
            extension = str(record.get("extension") or "").strip()
            if not _ATTR_RE.fullmatch(host) or not _ATTR_RE.fullmatch(extension):
                continue
            clean.append(
                {
                    "id": str(
                        record.get("id")
                        or f"nix-ext:{host}:{extension}:{scope}"
                    ),
                    "kind": "extension",
                    "host": host,
                    "extension": extension,
                    "name": str(record.get("name") or extension),
                    "scope": scope,
                    "action": action,
                    "version": str(record.get("version") or ""),
                    "icon": str(record.get("icon") or "nix.svg"),
                    "created": _created(record),
                }
            )
            continue
        attr = str(record.get("attr") or "").strip()
        if not _ATTR_RE.fullmatch(attr):
            continue
        clean.append(
            {
                "id": str(record.get("id") or f"nix:{attr}:{scope}"),
                "kind": "package",
                "attr": attr,
                "name": str(record.get("name") or attr),
                "scope": scope,
                "action": action,
                "version": str(record.get("version") or ""),
                "icon": str(record.get("icon") or "nix.svg"),
                "created": _created(record),
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
        if record.get("kind") != "extension"
        and record.get("attr") == attr
        and (not scope or record.get("scope") == scope)
    ]


def pending_extension_for(host, scope=None, action=None):
    """Pending extension operations for one host."""
    host = str(host or "").strip()
    scope = str(scope or "").strip()
    action = str(action or "").strip()
    return [
        record
        for record in snapshot()
        if record.get("kind") == "extension"
        and record.get("host") == host
        and (not scope or record.get("scope") == scope)
        and (not action or record.get("action") == action)
    ]


def add(info, action="install", scope=None):
    """Queue one package operation, replacing any opposite pending action."""
    attr = str(info.get("nix_name") or info.get("package-name") or "").strip()
    if not _ATTR_RE.fullmatch(attr):
        raise ValueError("Invalid Nix package name")
    scope = str(scope or info.get("nix_scope") or "home-manager").strip()
    if scope not in _VALID_SCOPES:
        raise ValueError("Invalid Nix install scope")
    action = str(action or "install").strip()
    if action not in ("install", "remove"):
        raise ValueError("Invalid Nix operation")
    if action == "install":
        try:
            from . import nix_metadata

            if not nix_metadata.package_supported_on_host(info):
                raise ValueError(
                    "This Nix package is not available for this architecture"
                )
        except ImportError:
            pass
        try:
            from . import nix_catalog

            if (
                nix_catalog.cached_path() is not None
                and not nix_catalog.attr_available(attr)
            ):
                raise ValueError(
                    "This Nix package is not available on this architecture"
                )
        except ImportError:
            pass
    name = str(info.get("name") or attr).strip() or attr
    record_id = f"nix:{attr}:{scope}"
    with _LOCK:
        payload = _read()
        operations = [
            record
            for record in payload["operations"]
            if not (
                record.get("kind") != "extension"
                and record.get("attr") == attr
                and record.get("scope") == scope
            )
        ]
        if action == "remove":
            # Removing a host also retires its pending extension operations;
            # the apply pass drops any installed selection as well.
            operations = [
                record
                for record in operations
                if not (
                    record.get("kind") == "extension"
                    and record.get("host") == attr
                    and record.get("scope") == scope
                )
            ]
        operations.append(
            {
                "id": record_id,
                "kind": "package",
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


def add_extension(info, action="install", scope=None):
    """Queue one plugin install/removal for a Nix host package.

    ``info`` is the extension payload produced by ``nix_extensions`` (or the
    app-page row carrying the same fields). Installations are validated against
    the current discovery cache; removals remain possible after a nixpkgs
    update so a stale selection is never undeletable.
    """
    host = str(
        info.get("nix_ext_host")
        or info.get("parent_id")
        or info.get("nix_name")
        or ""
    ).strip()
    extension = str(
        info.get("nix_ext_attr")
        or info.get("extension")
        or ""
    ).strip()
    if not _ATTR_RE.fullmatch(host):
        raise ValueError("Invalid Nix extension host package")
    if not _ATTR_RE.fullmatch(extension):
        raise ValueError("Invalid Nix extension name")
    action = str(action or "install").strip()
    if action not in ("install", "remove"):
        raise ValueError("Invalid Nix extension operation")
    scope = str(
        scope or info.get("nix_ext_scope") or info.get("nix_scope") or ""
    ).strip()
    if scope not in _VALID_SCOPES:
        try:
            from . import nix_catalog

            available = nix_catalog.scopes()
        except Exception:
            available = []
        if "home-manager" in available:
            scope = "home-manager"
        elif "system" in available:
            scope = "system"
        else:
            raise ValueError("No Nix install scope is available")
    if action == "install":
        from . import nix_extensions

        cap = nix_extensions.cached_capabilities().get(host)
        if cap is None or extension not in {
            item["attr"] for item in cap.get("plugins") or ()
        }:
            raise ValueError(
                "This Nix extension is not available in the current nixpkgs revision"
            )
    name = str(info.get("name") or extension).strip() or extension
    record_id = f"nix-ext:{host}:{extension}:{scope}"
    with _LOCK:
        payload = _read()
        operations = [
            record
            for record in payload["operations"]
            if not (
                record.get("kind") == "extension"
                and record.get("host") == host
                and record.get("extension") == extension
                and record.get("scope") == scope
            )
        ]
        if action == "install":
            # Installing an extension implies keeping its host installed, so a
            # pending host removal queued earlier is superseded.
            operations = [
                record
                for record in operations
                if not (
                    record.get("kind") != "extension"
                    and record.get("attr") == host
                    and record.get("scope") == scope
                    and record.get("action") == "remove"
                )
            ]
        operations.append(
            {
                "id": record_id,
                "kind": "extension",
                "host": host,
                "extension": extension,
                "name": name,
                "scope": scope,
                "action": action,
                "version": str(info.get("version") or ""),
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
    # A queued plugin install will wrap (and therefore install) its host on
    # apply, so the app page already counts it as queued.
    if pending_extension_for(attr, scope or None, action="install"):
        return "nix_queued"
    from . import nix_catalog

    if nix_catalog.is_installed(info):
        return "installed"
    return "available"
