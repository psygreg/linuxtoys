"""Action Registry integration for LinuxToys-managed Nix packages and flakes.

Nix installs are declarative and applied by ``nixsys.bash`` rather than by a
materialized script, so they cannot rely on the usual transmap/terminal
registry writer. This module is the single place that turns the applied
module state into stable registry transactions and back.

Package operation format:

    nix install <attr> <scope>

Flake operation format:

    nix flake install <scope> <encoded-state-id>

The scope is ``home-manager`` or ``system``. A package or flake present in
both scopes keeps both operations in one transaction. Package identities are
``Nix: <attr>``; flake identities are ``Nix flake: <reference>``. Removals
and manifest filtering match those names without parsing display labels.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from urllib.parse import quote, unquote

if __package__:
    from .registry_utils import parse_registry_file, remove_script_entries
    from .term_registry import ExecutionRegistry
else:  # Executed as ``python3 app/nix_registry.py`` from the Bash libraries.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from registry_utils import parse_registry_file, remove_script_entries
    from term_registry import ExecutionRegistry

PREFIX = "Nix: "
FLAKE_PREFIX = "Nix flake: "
_OPERATION = "nix install "
_FLAKE_OPERATION = "nix flake install "
_VALID_SCOPES = ("home-manager", "system")
_ATTR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_'-]*$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]+")


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


# ---------------------------------------------------------------------------
# Imported flakes
# ---------------------------------------------------------------------------

def flake_registry_name(reference):
    """Stable Action Registry identity for one imported flake."""
    value = _CONTROL_RE.sub(" ", str(reference or "")).strip()
    return FLAKE_PREFIX + value


def encode_flake_id(record_id):
    """URL-encode a state record id for a whitespace-delimited operation."""
    return quote(str(record_id or ""), safe="")


def decode_flake_id(value):
    return unquote(str(value or ""))


def parse_flake_operation(operation):
    """Return ``(scope, record_id)`` for a flake install operation, else None."""
    text = str(operation or "").strip()
    if not text.startswith(_FLAKE_OPERATION):
        return None
    parts = text.split()
    if (
        len(parts) != 5
        or parts[0] != "nix"
        or parts[1] != "flake"
        or parts[2] != "install"
    ):
        return None
    scope, encoded = parts[3], parts[4]
    if scope not in _VALID_SCOPES:
        return None
    record_id = decode_flake_id(encoded)
    if not record_id:
        return None
    return scope, record_id


def _is_flake_entry(name, executions=None):
    if str(name or "").startswith(FLAKE_PREFIX):
        return True
    if executions is None:
        executions = parse_registry_file().get(name, ())
    return any(
        parse_flake_operation(operation) is not None
        for _timestamp, operations in executions or ()
        for operation in operations
    )


def is_flake_registry_entry(name, executions=None):
    """Whether one registry identity is (or records) an imported flake."""
    return _is_flake_entry(name, executions)


def _write_flake_entry(name, operations):
    """Replace the registry transaction for one imported flake."""
    clean = sorted(
        {
            str(operation).strip()
            for operation in operations or ()
            if parse_flake_operation(operation) is not None
        }
    )
    if not clean:
        return False
    fd, path = tempfile.mkstemp(prefix="linuxtoys-nix-flake-registry-", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(clean) + "\n")
        ExecutionRegistry._save_to_registry(str(name), path)
        return True
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _flake_operations_by_name(registry_data):
    entries = {}
    for name, executions in (registry_data or {}).items():
        operations = []
        for _timestamp, transaction_operations in executions or ():
            for operation in transaction_operations or ():
                parsed = parse_flake_operation(operation)
                if parsed is not None:
                    operations.append(str(operation).strip())
        if operations:
            entries[str(name)] = sorted(set(operations))
    return entries


def _remove_flake_operations(record_ids, registry_data=None):
    """Remove operations for the given state ids from flake transactions."""
    wanted = {str(record_id or "").strip() for record_id in record_ids or ()}
    wanted.discard("")
    if not wanted:
        return 0
    if registry_data is None:
        registry_data = parse_registry_file()
    changed = 0
    for name, operations in _flake_operations_by_name(registry_data).items():
        kept = []
        for operation in operations:
            parsed = parse_flake_operation(operation)
            if parsed is not None and parsed[1] in wanted:
                continue
            kept.append(operation)
        if kept == operations:
            continue
        changed += 1
        if kept:
            _write_flake_entry(name, kept)
        else:
            remove_script_entries(name)
    return changed


def _flake_state():
    try:
        if __package__:
            from . import nix_flakes
        else:
            import nix_flakes
        return nix_flakes
    except Exception:
        return None


def _flake_records():
    module = _flake_state()
    if module is None:
        return []
    try:
        return list(module.imports())
    except Exception:
        return []


def sync_flakes(records=None, prune=False, removed_ids=None):
    """Make registry flake transactions match the imported flake state.

    ``records`` is an optional list of ``nix_flakes`` state records. When
    omitted the durable state is read. ``removed_ids`` first drops operations
    for records that were just removed; ``prune`` then removes transactions
    whose record ids no longer exist in the state. Pruning is skipped when
    the state is empty, so a temporarily unreadable/lost state file cannot
    silently erase every actionable registry entry.
    """
    if records is None:
        module = _flake_state()
        if module is None:
            raise RuntimeError("The imported flake state is unavailable")
        # Deliberately propagate an unreadable/corrupt state file: pruning
        # must never interpret "could not read" as "nothing is imported".
        records = list(module.imports())
    if removed_ids:
        _remove_flake_operations(removed_ids)

    desired = {}
    desired_ids = set()
    for record in records or ():
        if not isinstance(record, dict):
            continue
        scope = str(record.get("scope") or "").strip()
        record_id = str(record.get("id") or "").strip()
        if scope not in _VALID_SCOPES or not record_id:
            continue
        reference = str(
            record.get("reference")
            or record.get("original_url")
            or record.get("url")
            or ""
        ).strip()
        name = flake_registry_name(reference or record_id)
        operation = (
            f"nix flake install {scope} {encode_flake_id(record_id)}"
        )
        desired.setdefault(name, set()).add(operation)
        desired_ids.add(record_id)

    registry_data = parse_registry_file()
    existing = _flake_operations_by_name(registry_data)

    for name, operations in desired.items():
        if existing.get(name) != sorted(operations):
            _write_flake_entry(name, operations)

    state_exists = False
    module = _flake_state()
    if module is not None:
        try:
            state_exists = bool(module.state_available())
        except Exception:
            state_exists = False

    desired_name_by_id = {}
    for name, operations in desired.items():
        for operation in operations:
            parsed = parse_flake_operation(operation)
            if parsed is not None:
                desired_name_by_id[parsed[1]] = name

    if prune and (desired or state_exists):
        for name, operations in existing.items():
            if name in desired:
                continue
            existing_ids = {
                parsed[1]
                for operation in operations
                if (parsed := parse_flake_operation(operation)) is not None
            }
            if not existing_ids:
                continue
            # Drop transactions whose records vanished, and duplicate
            # transactions left behind when a re-import changed the
            # reference spelling for the same state record ids.
            if not (existing_ids & desired_ids) or any(
                desired_name_by_id.get(record_id) not in (None, name)
                for record_id in existing_ids
            ):
                remove_script_entries(name)

    return len(desired)


def sync_from_flakes():
    """Add/update flake transactions for the current durable import state."""
    try:
        return sync_flakes()
    except Exception:
        return 0


def installed_flakes(registry_data=None):
    """Return imported flakes recorded in the Action Registry.

    Registry entries remain listable even if their state record vanished, so
    a stale-but-rebuildable module can still be removed through the standard
    flow. State records enrich them with the flake description and selected
    output labels.
    """
    if registry_data is None:
        registry_data = parse_registry_file()
    records = {
        str(record.get("id") or "").strip(): record
        for record in _flake_records()
    }
    result = []
    for name, operations in _flake_operations_by_name(registry_data).items():
        reference = name
        if reference.startswith(FLAKE_PREFIX):
            reference = reference[len(FLAKE_PREFIX):].strip()
        ids = []
        scopes = set()
        for operation in operations:
            parsed = parse_flake_operation(operation)
            if parsed is None:
                continue
            scope, record_id = parsed
            scopes.add(scope)
            if record_id not in ids:
                ids.append(record_id)
        if not ids:
            continue
        matched = [
            records[record_id]
            for record_id in ids
            if record_id in records
        ]
        description = next(
            (
                str(record.get("description") or "").strip()
                for record in matched
                if str(record.get("description") or "").strip()
            ),
            "",
        )
        labels = []
        for record in matched:
            for option in record.get("options") or ():
                label = str(option.get("label") or "").strip()
                if label and label not in labels:
                    labels.append(label)
        result.append(
            {
                "name": description or reference or "Nix flake",
                "appstream_source": "nix-flake",
                "appstream_id": f"nix-flake:{reference}",
                "nix_flake_reference": reference,
                "nix_flake_ids": sorted(ids),
                "nix_flake_scopes": sorted(scopes),
                "nix_flake_outputs": labels,
                "registry_name": name,
                "icon": "nix.svg",
                "repo": "flake",
                "description": "",
                "path": "",
                "is_script": True,
                "is_appstream_entry": False,
            }
        )
    result.sort(key=lambda item: str(item.get("name", "")).casefold())
    return result


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
