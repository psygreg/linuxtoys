"""Action Registry integration for LinuxToys-managed Nix packages.

Nix installs are declarative and applied by ``nixsys.bash`` rather than by a
materialized script, so they cannot rely on the usual transmap/terminal
registry writer. This module is the single place that turns the applied
module state into stable ``Nix: <attr>`` registry transactions and back.

Registry operation format:

    nix install <attr> <scope>

The scope is ``home-manager`` or ``system``. A package present in both scopes
keeps both operations in one transaction; the registry name stays
``Nix: <attr>`` so removal and manifest export can match it without parsing
display names.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile

if __package__:
    from .registry_utils import parse_registry_file, remove_script_entries
    from .term_registry import ExecutionRegistry
else:  # Executed as ``python3 app/nix_registry.py`` from the Bash libraries.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from registry_utils import parse_registry_file, remove_script_entries
    from term_registry import ExecutionRegistry

PREFIX = "Nix: "
_OPERATION = "nix install "
_VALID_SCOPES = ("home-manager", "system")
_ATTR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_'-]*$")


def registry_name(attr):
    """Return the stable Action Registry identity for one Nix attribute."""
    return PREFIX + str(attr or "").strip()


def _entry_names(registry_data):
    return {
        name
        for name in registry_data
        if str(name).startswith(PREFIX)
    }


def parse_operation(operation):
    """Return ``(attr, scope)`` for a Nix install operation, else None."""
    text = str(operation or "").strip()
    if not text.startswith(_OPERATION):
        return None
    parts = text.split()
    if len(parts) != 4 or parts[0] != "nix" or parts[1] != "install":
        return None
    attr, scope = parts[2], parts[3]
    if not _ATTR_RE.fullmatch(attr) or scope not in _VALID_SCOPES:
        return None
    return attr, scope


def _is_nix_entry(name, executions):
    if str(name).startswith(PREFIX):
        return True
    return any(
        parse_operation(operation) is not None
        for _timestamp, operations in executions or ()
        for operation in operations
    )


def installed_packages(registry_data=None):
    """Return installed Nix packages recorded in the Action Registry.

    Each item is a script-info-like dict suitable for the Installed Features
    list and removal flow. When an attribute records both scopes, the item
    follows the preferred home-manager scope and keeps ``nix_scopes``.
    """
    if registry_data is None:
        registry_data = parse_registry_file()

    packages = {}
    for name, executions in registry_data.items():
        scopes = {}
        for _timestamp, operations in executions or ():
            for operation in operations:
                parsed = parse_operation(operation)
                if parsed is not None:
                    attr, scope = parsed
                    scopes.setdefault(attr, set()).add(scope)
        for attr, attr_scopes in scopes.items():
            if attr in packages:
                packages[attr]["nix_scopes"] = sorted(
                    set(packages[attr]["nix_scopes"]) | attr_scopes
                )
                continue
            packages[attr] = {
                "nix_name": attr,
                "nix_scopes": sorted(attr_scopes),
            }

    result = []
    for attr, data in packages.items():
        scopes = sorted(data["nix_scopes"])
        scope = "home-manager" if "home-manager" in scopes else scopes[0]
        name = attr
        icon = "nix.svg"
        logo = ""
        try:
            if __package__:
                from . import nix_metadata
            else:
                import nix_metadata
            record = nix_metadata.index_record(attr) or {}
            name = str(record.get("name") or "").strip() or attr
            logo = str(record.get("logo") or "").strip()
        except Exception:
            pass
        result.append(
            {
                "name": name,
                "appstream_source": "nix",
                "appstream_id": f"nix:{attr}",
                "nix_name": attr,
                "nix_scope": scope,
                "nix_scopes": scopes,
                "icon": icon,
                "nix_api_logo": logo,
                "repo": "nixpkgs",
                "description": "",
                "path": "",
                "is_script": True,
                "is_appstream_entry": True,
                "registry_name": registry_name(attr),
            }
        )
    result.sort(key=lambda item: str(item.get("name", "")).casefold())
    return result


def is_nix_registry_entry(name, executions=None):
    """Whether one registry identity is (or records) a Nix package."""
    if str(name or "").startswith(PREFIX):
        return True
    if executions is None:
        executions = parse_registry_file().get(name, ())
    return _is_nix_entry(name, executions)


def _write_entry(attr, scopes):
    """Replace the registry transaction for one Nix attribute."""
    lines = [
        f"nix install {attr} {scope}"
        for scope in sorted(set(scopes) & set(_VALID_SCOPES))
    ]
    if not lines:
        return False
    fd, path = tempfile.mkstemp(prefix="linuxtoys-nix-registry-", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        ExecutionRegistry._save_to_registry(registry_name(attr), path)
        return True
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def sync(records):
    """Make registry Nix entries exactly match the applied module state.

    ``records`` is an iterable of ``(attr, scope)`` pairs. Entries for
    attributes that are no longer present are removed; present attributes are
    rewritten with their current scopes.
    """
    wanted = {}
    for attr, scope in records:
        attr = str(attr or "").strip()
        scope = str(scope or "").strip()
        if not _ATTR_RE.fullmatch(attr) or scope not in _VALID_SCOPES:
            continue
        wanted.setdefault(attr, set()).add(scope)

    registry_data = parse_registry_file()
    existing = _entry_names(registry_data)

    for attr, scopes in wanted.items():
        name = registry_name(attr)
        current_scopes = set()
        for _timestamp, operations in registry_data.get(name, ()):
            for operation in operations:
                parsed = parse_operation(operation)
                if parsed is not None and parsed[0] == attr:
                    current_scopes.add(parsed[1])
        if current_scopes != set(scopes):
            _write_entry(attr, scopes)
        existing.discard(name)

    for name in existing:
        remove_script_entries(name)

    return len(wanted)


def sync_file(path):
    """Apply a tab-separated ``attr<TAB>scope`` state file."""
    records = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                records.append((parts[0].strip(), parts[1].strip()))
    return sync(records)


def sync_from_modules():
    """Reconcile registry entries with the current LinuxToys Nix modules.

    Packages installed before registry integration (or after a failed sync)
    become removable without waiting for the next queue apply.
    """
    try:
        if __package__:
            from . import nix_catalog
        else:
            import nix_catalog
    except Exception:
        return 0
    try:
        if not nix_catalog.enabled():
            return 0
        state = nix_catalog.installed_packages()
    except Exception:
        return 0
    records = [
        (attr, scope)
        for scope in ("home-manager", "system")
        for attr in state.get(scope) or ()
    ]
    try:
        return sync(records)
    except Exception:
        return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "sync":
        try:
            count = sync_file(sys.argv[2])
        except (OSError, ValueError, TypeError):
            sys.exit(1)
        print(f"Registered {count} Nix package(s).")
        sys.exit(0)
    if len(sys.argv) == 2 and sys.argv[1] == "list":
        import json

        print(
            json.dumps(
                installed_packages(),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        sys.exit(0)
    sys.exit(2)
