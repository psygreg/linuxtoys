"""Persistent queue for Nix package, service and extension operations.

Nix installs are declarative: selecting a package records an operation here and
nothing is built until the user presses "Apply Nix package operations" on the
queue view. Service operations (NixOS services with configurable options) and
extension operations (plugins of a host package) use the same queue. The queue
survives restarts so a pending rebuild is never lost.
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
        if kind == "service":
            service = str(
                record.get("service") or record.get("attr") or ""
            ).strip()
            if not _ATTR_RE.fullmatch(service):
                continue
            raw_options = record.get("options")
            options = {}
            if isinstance(raw_options, dict):
                for path, value in raw_options.items():
                    path = str(path or "").strip()
                    if not path or len(path) > 256:
                        continue
                    if not all(part for part in path.split(".")):
                        continue
                    if isinstance(value, (bool, int, float, str)):
                        options[path] = value
                    elif isinstance(value, list) and all(
                        isinstance(item, str) for item in value
                    ):
                        options[path] = value
            clean.append(
                {
                    "id": str(
                        record.get("id")
                        or f"nix-service:{service}:{scope}"
                    ),
                    "kind": "service",
                    "service": service,
                    "attr": service,
                    "name": str(record.get("name") or service),
                    "scope": scope,
                    "action": action,
                    "options": options,
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
        if record.get("kind") == "package"
        and record.get("attr") == attr
        and (not scope or record.get("scope") == scope)
    ]


def pending_service_for(service, scope=None, action=None):
    """Pending service operations for one service attribute."""
    service = str(service or "").strip()
    scope = str(scope or "").strip()
    action = str(action or "").strip()
    return [
        record
        for record in snapshot()
        if record.get("kind") == "service"
        and str(record.get("service") or record.get("attr") or "") == service
        and (not scope or record.get("scope") == scope)
        and (not action or record.get("action") == action)
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


def _service_capability(info, scope=None):
    """Resolve a service capability, refreshing discovery once if needed."""
    try:
        from . import nix_services
    except Exception:
        return None
    if not nix_services.enabled():
        return None
    requested = str(scope or "").strip()
    name = str(
        (info or {}).get("nix_name")
        or (info or {}).get("package-name")
        or ""
    ).strip()
    service = (
        nix_services.service_for_name(name, requested)
        if requested
        else nix_services.service_for(info)
    )
    if service is not None:
        return service
    if not nix_services.cache_valid():
        try:
            nix_services.load_or_refresh()
        except Exception:
            return None
        service = (
            nix_services.service_for_name(name, requested)
            if requested
            else nix_services.service_for(info)
        )
    return service


def _service_scopes(info):
    """Levels where this attribute is installed, queued or (as a fallback) available."""
    try:
        from . import nix_services
    except Exception:
        return []
    name = str(
        (info or {}).get("nix_name")
        or (info or {}).get("package-name")
        or ""
    ).strip()
    if not name:
        return []
    scopes = []
    for scope in nix_services.installed_service_scopes(name):
        if scope not in scopes:
            scopes.append(scope)
    for record in snapshot():
        if record.get("kind") != "service":
            continue
        if str(record.get("service") or record.get("attr") or "") != name:
            continue
        scope = str(record.get("scope") or "").strip()
        if scope and scope not in scopes:
            scopes.append(scope)
    if scopes:
        return scopes
    for capability in nix_services.service_capabilities(name).values():
        scope = str(capability.get("scope") or "").strip()
        if scope and scope not in scopes:
            scopes.append(scope)
    return scopes


def add(info, action="install", scope=None):
    """Queue one package/service operation, replacing any opposite action."""
    attr = str(info.get("nix_name") or info.get("package-name") or "").strip()
    if not _ATTR_RE.fullmatch(attr):
        raise ValueError("Invalid Nix package name")
    action = str(action or "install").strip()
    if action not in ("install", "remove"):
        raise ValueError("Invalid Nix operation")
    requested = str(scope or info.get("nix_scope") or "").strip()
    if action == "remove":
        service_scopes = _service_scopes(info)
        if requested:
            service_scopes = (
                [requested] if requested in service_scopes else []
            )
        if service_scopes:
            record_id = None
            for service_scope in service_scopes:
                record_id = add_service(
                    info, action="remove", scope=service_scope
                )
            return record_id
    service = _service_capability(info, requested or None)
    if service is not None:
        return add_service(
            info, action=action, scope=service.get("scope") or requested
        )
    try:
        from . import nix_services

        if nix_services.service_unavailable_on_host(attr):
            raise ValueError(
                "This package is only available as a Nix service whose level "
                "is not available on this host"
            )
    except ValueError:
        raise
    except Exception:
        pass
    # A catalog attribute backed by a service module must never be installed
    # as a bare package: the package alone has no daemon/udev units.
    return _add_package(info, action=action, scope=scope)


def _add_package(info, action="install", scope=None):
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
                record.get("kind") == "package"
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


def add_service(info, action="install", scope=None, options=None):
    """Queue one Nix service install/removal with its option overrides.

    The level comes from the resolved capability: Home Manager services are
    user-level and work anywhere Home Manager is available; NixOS services are
    system-level. ``options`` maps option paths to values; values equal to the
    current defaults are not stored, so modules keep tracking upstream defaults
    for untouched options.
    """
    name = str(
        info.get("nix_name")
        or info.get("service")
        or info.get("package-name")
        or ""
    ).strip()
    if not _ATTR_RE.fullmatch(name):
        raise ValueError("Invalid Nix service name")
    action = str(action or "install").strip()
    if action not in ("install", "remove"):
        raise ValueError("Invalid Nix service operation")

    try:
        from . import nix_services

        if not nix_services.enabled():
            raise ValueError(
                "Nix services require Home Manager or a NixOS system configuration"
            )
        requested = str(scope or info.get("nix_scope") or "").strip()
        service = nix_services.service_for_name(name, requested)
        if service is None and action == "install":
            service = _service_capability(info, requested or None)
        service_scope = str((service or {}).get("scope") or requested).strip()
        if not service_scope:
            installed = nix_services.installed_service_scopes(name)
            service_scope = installed[0] if installed else "home-manager"
        if service_scope not in nix_services.scopes():
            raise ValueError(
                f"The {service_scope} service level is not available on this host"
            )
        if (
            service is None
            and action == "install"
            and not nix_services.is_installed(info)
        ):
            raise ValueError(
                "This service is not available in the current service revision"
            )
        overrides = (
            nix_services.overrides_from_values(service or {}, options or {})
            if service is not None
            else {}
        )
    except ValueError:
        raise
    except Exception:
        service = None
        service_scope = str(scope or "home-manager").strip()
        overrides = {}

    display = str(info.get("name") or name).strip() or name
    record_id = f"nix-service:{name}:{service_scope}"
    with _LOCK:
        payload = _read()
        operations = [
            record
            for record in payload["operations"]
            if not (
                record.get("kind") == "service"
                and str(record.get("service") or record.get("attr") or "") == name
                and record.get("scope") == service_scope
            )
            and not (
                record.get("kind") == "package"
                and record.get("attr") == name
                and record.get("scope") == service_scope
            )
        ]
        if action == "install" and options is None:
            # A plain Install action must not clear options the user already
            # saved on a pending service record or on an installed service.
            previous = [
                record
                for record in payload["operations"]
                if record.get("kind") == "service"
                and str(record.get("service") or record.get("attr") or "") == name
                and record.get("scope") == service_scope
                and record.get("action") == "install"
            ]
            if previous:
                overrides = dict(previous[-1].get("options") or {})
            else:
                try:
                    installed_state = nix_services.read_state(
                        nix_services.module_path(service_scope)
                    )
                    overrides = dict(
                        installed_state.get(name, {}).get("options") or {}
                    )
                except Exception:
                    pass
        operations.append(
            {
                "id": record_id,
                "kind": "service",
                "service": name,
                "attr": name,
                "name": display,
                "scope": service_scope,
                "action": action,
                "options": dict(sorted(overrides.items())) if action == "install" else {},
                "version": str(
                    info.get("nix_version") or info.get("appstream_version") or ""
                ),
                "icon": str(info.get("icon") or "nix.svg"),
                "created": int(time.time()),
            }
        )
        _write({"schema": SCHEMA, "operations": operations})
    _notify()
    return record_id


def set_service_options(info, values, scope=None):
    """Queue a service option update, skipping a no-op when already installed."""
    name = str(
        info.get("nix_name")
        or info.get("service")
        or info.get("package-name")
        or ""
    ).strip()
    if not _ATTR_RE.fullmatch(name):
        raise ValueError("Invalid Nix service name")
    try:
        from . import nix_services
    except Exception as error:
        raise ValueError(f"Nix service metadata is unavailable: {error}") from error
    service = _service_capability(info, scope)
    if service is None:
        raise ValueError(
            "This service is not available in the current service revision"
        )
    service_scope = str(service.get("scope") or scope or "home-manager")
    overrides = nix_services.overrides_from_values(service, values or {})
    if (
        not pending_service_for(name, service_scope)
        and name in nix_services.installed_services(service_scope)
    ):
        installed = nix_services.read_state(
            nix_services.module_path(service_scope)
        )
        current = installed.get(name, {}).get("options", {})
        if dict(sorted(current.items())) == dict(sorted(overrides.items())):
            return None
    return add_service(
        info, action="install", scope=service_scope, options=values
    )


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
    # A service can live in either level; the page reflects whichever level
    # actually owns the pending/installed selection.
    if pending_service_for(attr):
        return "nix_queued"
    try:
        from . import nix_services

        if nix_services.is_installed(info):
            return "installed"
    except Exception:
        pass
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
