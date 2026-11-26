"""Import Nix flakes into the user's Home Manager or NixOS configuration.

A flake is inspected with ``nix flake metadata`` and one ``nix eval`` query so
that packages, Home Manager modules, NixOS modules and overlays are all
discovered without guessing at its output structure. The selected outputs are
merged into the user's configuration through a generated
``linuxtoys-flakes.nix`` (or ``linuxtoys-system-flakes.nix``) module that the
LinuxToys-managed module imports.

Imported flakes are referenced by their locked URL through
``builtins.getFlake``. A locked flake reference keeps the user's configuration
working under pure flake evaluation without rewriting their ``flake.nix``
inputs; the generated module is imported into that configuration instead.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from . import nix_catalog
from .atomic_io import atomic_write_json, atomic_write_text

DATA_DIR = (
    Path(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"))
    / "linuxtoys"
    / "nix-flakes"
)
WRAPPER_DIR = DATA_DIR / "wrappers"
# Imported-flake configuration is durable user data, not a rebuildable cache:
# clearing the cache must never drop already applied imports.
STATE_DIR = DATA_DIR
STATE_PATH = STATE_DIR / "flakes.json"
SCHEMA = 1
METADATA_TIMEOUT = 180
LOCK_TIMEOUT = 300
EVAL_TIMEOUT = 240
MAX_REFERENCE_LENGTH = 512
LOCK = threading.RLock()

_REFERENCE_PREFIXES = (
    "github:",
    "gitlab:",
    "sourcehut:",
    "git+https:",
    "git+ssh:",
    "git+file:",
    "https://",
    "path:",
)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_MODULE_ATTRS = {
    "home_module": {"homeManagerModules", "homeModules"},
    "nixos_module": {"nixosModules", "nixosModule"},
    "overlay": {"overlays", "overlay"},
}
_MODULE_ATTR_DEFAULTS = {
    "home_module": "homeManagerModules",
    "nixos_module": "nixosModules",
    "overlay": "overlays",
}


class FlakeError(ValueError):
    """A flake reference or one of its outputs cannot be used."""


def _nix_executable():
    executable = nix_catalog.nix_executable()
    if not executable:
        raise FlakeError("Nix is not installed")
    return executable


def _run_nix(arguments, timeout):
    executable = _nix_executable()
    command = [
        executable,
        "--extra-experimental-features",
        "nix-command flakes",
        *arguments,
    ]
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C"},
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise FlakeError(f"The flake operation timed out after {timeout}s") from error
    except OSError as error:
        raise FlakeError(f"Could not run Nix: {error}") from error
    if result.returncode != 0:
        detail = [
            line.strip()
            for line in (result.stderr or "").splitlines()
            if line.strip()
        ]
        errors = [line for line in detail if line.startswith("error:")]
        raise FlakeError(
            errors[0]
            if errors
            else (
                detail[-1]
                if detail
                else f"nix exited with status {result.returncode}"
            )
        )
    return result.stdout


def validate_reference(reference):
    """Validate and normalize a user-entered flake reference."""
    value = str(reference or "").strip()
    if not value:
        raise FlakeError("A flake reference is required")
    if len(value) > MAX_REFERENCE_LENGTH:
        raise FlakeError("The flake reference is too long")
    if _CONTROL.search(value) or value.startswith("-") or value.startswith("--"):
        raise FlakeError("The flake reference contains unsafe characters")
    if "://" in value and not value.startswith(
        ("https://", "git+https://", "git+ssh://", "git+file://")
    ):
        raise FlakeError("Only HTTPS, Git and path flake references are supported")
    if value.startswith(_REFERENCE_PREFIXES):
        return value
    if value.startswith("/"):
        path = Path(value).expanduser()
        if path.is_dir():
            return "path:" + os.fspath(path)
        raise FlakeError(f"Flake directory does not exist: {value}")
    if value.startswith("~/"):
        path = Path(value).expanduser()
        if path.is_dir():
            return "path:" + os.fspath(path)
        raise FlakeError(f"Flake directory does not exist: {value}")
    if "/" in value and not value.startswith(("http:", "https:")):
        path = Path(value).expanduser()
        if path.is_dir():
            return "path:" + os.path.abspath(os.fspath(path))
    raise FlakeError(
        "Enter a flake URL (github:owner/repo, git+https://…) or a local directory"
    )


def _locked_url(metadata):
    """Return a reproducible flake URL from ``nix flake metadata`` output."""
    if not isinstance(metadata, dict):
        raise FlakeError("Nix returned unreadable flake metadata")
    locked = metadata.get("locked")
    url = metadata.get("url")
    candidate = ""
    if isinstance(url, str) and url.strip():
        candidate = url.strip()
        if candidate.startswith("path:") and "narHash=" not in candidate:
            # A bare path is not pure-evaluation safe; rebuild it from the
            # locked node below instead of returning it as-is.
            if not isinstance(locked, dict) or not locked.get("narHash"):
                raise FlakeError("Nix did not return a locked flake reference")
            candidate = ""
    if candidate:
        return candidate
    if not isinstance(locked, dict):
        raise FlakeError("Nix did not return a locked flake reference")
    locked_type = str(locked.get("type") or "").strip()
    if locked_type in {"github", "gitlab", "sourcehut"}:
        owner = str(locked.get("owner") or "").strip()
        repo = str(locked.get("repo") or "").strip()
        rev = str(locked.get("rev") or "").strip()
        if owner and repo and rev:
            return f"{locked_type}:{owner}/{repo}/{rev}"
    if locked_type == "path":
        path = str(locked.get("path") or "").strip()
        if path:
            from urllib.parse import quote

            query = []
            if locked.get("lastModified") is not None:
                query.append(f"lastModified={int(locked['lastModified'])}")
            nar_hash = str(locked.get("narHash") or "").strip()
            if nar_hash:
                query.append("narHash=" + quote(nar_hash, safe=""))
            suffix = "?" + "&".join(query) if query else ""
            return f"path:{path}{suffix}"
    resolved = metadata.get("resolvedUrl")
    if isinstance(resolved, str) and resolved.strip():
        return resolved.strip()
    raise FlakeError("Nix did not return a reproducible flake reference")


def _metadata(reference):
    output = _run_nix(
        [
            "flake",
            "metadata",
            "--json",
            "--no-write-lock-file",
            reference,
        ],
        METADATA_TIMEOUT,
    )
    try:
        metadata = json.loads(output)
    except (TypeError, ValueError) as error:
        raise FlakeError("Nix returned unreadable flake metadata") from error
    if not isinstance(metadata, dict):
        raise FlakeError("Nix returned unreadable flake metadata")
    return metadata


def _wrapper_content(target_url):
    return (
        "{\n"
        '  description = "LinuxToys flake import wrapper";\n'
        f"  inputs.target.url = {json.dumps(target_url, ensure_ascii=False)};\n"
        "  outputs = { self, target, ... }: target;\n"
        "}\n"
    )


def _wrapper_directory(target_url, content):
    digest = hashlib.sha256(
        (target_url + "\0" + content).encode("utf-8", "surrogatepass")
    ).hexdigest()[:24]
    return WRAPPER_DIR / digest


def _wrapper(reference):
    """Return a locked wrapper URL for a flake.

    The wrapper pins the target flake and all of its inputs in its own
    ``flake.lock``. This makes ``builtins.getFlake`` usable from the
    generated module under pure flake evaluation, including for local path
    flakes that do not ship a lock file. The wrapped output is simply the
    target flake's output set.

    The wrapper directory is keyed by the locked target URL and the wrapper
    text, so a template change never invalidates already imported wrappers.
    An existing lock is never refreshed: the target URL is itself pinned
    (revision, content hash), and rewriting the lock would change the
    wrapper's content hash while old generated modules still reference it.
    """
    metadata = _metadata(reference)
    target_url = _locked_url(metadata)
    content = _wrapper_content(target_url)
    directory = _wrapper_directory(target_url, content)
    directory.mkdir(parents=True, exist_ok=True)
    flake_path = directory / "flake.nix"
    try:
        current = flake_path.read_text(encoding="utf-8")
    except OSError:
        current = None
    if current != content:
        atomic_write_text(flake_path, content, mode=0o644, fsync=True)
    lock_path = directory / "flake.lock"
    if not lock_path.is_file() or current != content:
        _run_nix(
            ["flake", "lock", f"path:{os.fspath(directory)}"],
            LOCK_TIMEOUT,
        )
    wrapper_metadata = _metadata(f"path:{os.fspath(directory)}")
    wrapper_url = _locked_url(wrapper_metadata)
    return {
        "directory": os.fspath(directory),
        "original_url": target_url,
        "url": wrapper_url,
        "description": str(metadata.get("description") or "").strip(),
    }


_INSPECT_EXPRESSION = r"""
let
  url = @@URL@@;
  system = @@SYSTEM@@;
  flake = builtins.getFlake url;
  names = value:
    if builtins.isAttrs value then builtins.attrNames value else [];
  moduleInfo = value:
    if value == null then { names = []; direct = false; isList = false; }
    else if builtins.isAttrs value then { names = builtins.attrNames value; direct = false; isList = false; }
    else { names = [ "default" ]; direct = true; isList = builtins.isList value; };
  homeModules = flake.homeManagerModules or flake.homeModules or null;
  homeModulesAttr =
    if flake ? homeManagerModules then "homeManagerModules"
    else if flake ? homeModules then "homeModules"
    else "";
  nixosModules = flake.nixosModules or flake.nixosModule or null;
  nixosModulesAttr =
    if flake ? nixosModules then "nixosModules"
    else if flake ? nixosModule then "nixosModule"
    else "";
  overlays = flake.overlays or flake.overlay or null;
  overlaysAttr =
    if flake ? overlays then "overlays"
    else if flake ? overlay then "overlay"
    else "";
in {
  description = flake.description or "";
  packages = names (flake.packages.${system} or null);
  legacyPackages = names (flake.legacyPackages.${system} or null);
  defaultPackage =
    if (flake.defaultPackage.${system} or null) != null then [ "default" ] else [];
  apps = names (flake.apps.${system} or null);
  homeManagerModules = moduleInfo homeModules // { attr = homeModulesAttr; };
  nixosModules = moduleInfo nixosModules // { attr = nixosModulesAttr; };
  overlays = moduleInfo overlays // { attr = overlaysAttr; };
  homeConfigurations = names (flake.homeConfigurations or null);
  nixosConfigurations = names (flake.nixosConfigurations or null);
}
"""


def _eval_outputs(url, system):
    expression = (
        _INSPECT_EXPRESSION.replace(
            "@@URL@@", json.dumps(url, ensure_ascii=False)
        ).replace("@@SYSTEM@@", json.dumps(system, ensure_ascii=False))
    )
    output = _run_nix(
        [
            "eval",
            "--json",
            "--no-write-lock-file",
            "--expr",
            expression,
        ],
        EVAL_TIMEOUT,
    )
    try:
        data = json.loads(output)
    except (TypeError, ValueError) as error:
        raise FlakeError("Nix returned unreadable flake outputs") from error
    if not isinstance(data, dict):
        raise FlakeError("Nix returned unreadable flake outputs")
    return data


def _clean_names(values):
    result = []
    for value in values if isinstance(values, list) else ():
        name = str(value or "").strip()
        if name and name not in result:
            result.append(name)
    return result


def _option(key, group, label, scope, *, selectable=True, **extra):
    option = {
        "key": key,
        "group": group,
        "label": label,
        "scope": scope,
        "selectable": bool(selectable),
    }
    option.update(extra)
    return option


def default_selected(option):
    """Whether a discovered output is selected when the picker opens."""
    kind = str(option.get("kind") or "")
    if kind in ("home_module", "nixos_module", "default_package"):
        return True
    if (
        kind == "package"
        and option.get("source") == "packages"
        and option.get("name") == "default"
    ):
        return True
    return False


def _build_options(outputs, system):
    options = []
    for name in _clean_names(outputs.get("packages")):
        key = f"package:packages:{name}"
        options.append(
            _option(
                key,
                "Packages",
                name,
                "both",
                kind="package",
                source="packages",
                name=name,
            )
        )
    for name in _clean_names(outputs.get("legacyPackages")):
        key = f"package:legacyPackages:{name}"
        options.append(
            _option(
                key,
                "Legacy packages",
                name,
                "both",
                kind="package",
                source="legacyPackages",
                name=name,
            )
        )
    for name in _clean_names(outputs.get("defaultPackage")):
        key = "package:defaultPackage:default"
        options.append(
            _option(
                key,
                "Default package",
                name,
                "both",
                kind="default_package",
                source="defaultPackage",
                name="default",
            )
        )
    home = outputs.get("homeManagerModules")
    if isinstance(home, dict):
        attr = str(home.get("attr") or "").strip()
        direct = bool(home.get("direct"))
        for name in _clean_names(home.get("names")):
            key = f"home-module:{name}"
            options.append(
                _option(
                    key,
                    "Home Manager modules",
                    name,
                    "home-manager",
                    kind="home_module",
                    attr=attr or "homeManagerModules",
                    name=name,
                    direct=direct,
                    is_list=bool(home.get("isList")),
                )
            )
    nixos = outputs.get("nixosModules")
    if isinstance(nixos, dict):
        attr = str(nixos.get("attr") or "").strip()
        direct = bool(nixos.get("direct"))
        for name in _clean_names(nixos.get("names")):
            key = f"nixos-module:{name}"
            options.append(
                _option(
                    key,
                    "NixOS modules",
                    name,
                    "system",
                    kind="nixos_module",
                    attr=attr or "nixosModules",
                    name=name,
                    direct=direct,
                    is_list=bool(nixos.get("isList")),
                )
            )
    overlays = outputs.get("overlays")
    if isinstance(overlays, dict):
        attr = str(overlays.get("attr") or "").strip()
        direct = bool(overlays.get("direct"))
        for name in _clean_names(overlays.get("names")):
            key = f"overlay:{name}"
            options.append(
                _option(
                    key,
                    "Overlays",
                    name,
                    "both",
                    kind="overlay",
                    attr=attr or "overlays",
                    name=name,
                    direct=direct,
                    is_list=bool(overlays.get("isList")),
                )
            )
    for name in _clean_names(outputs.get("apps")):
        options.append(
            _option(
                f"app:{name}",
                "Apps (not merged)",
                name,
                "both",
                selectable=False,
                kind="app",
                name=name,
            )
        )
    for name in _clean_names(outputs.get("homeConfigurations")):
        options.append(
            _option(
                f"home-configuration:{name}",
                "Configurations (not merged)",
                name,
                "both",
                selectable=False,
                kind="home_configuration",
                name=name,
            )
        )
    for name in _clean_names(outputs.get("nixosConfigurations")):
        options.append(
            _option(
                f"system-configuration:{name}",
                "Configurations (not merged)",
                name,
                "both",
                selectable=False,
                kind="nixos_configuration",
                name=name,
            )
        )
    return options


def inspect(reference):
    """Inspect a flake and return its importable outputs for this host."""
    system = nix_catalog.linux_arch()
    if not system:
        raise FlakeError("Nix flakes are only available on x86_64 and aarch64 hosts")
    normalized = validate_reference(reference)
    wrapper = _wrapper(normalized)
    outputs = _eval_outputs(wrapper["url"], system)
    description = str(
        wrapper.get("description") or outputs.get("description") or ""
    ).strip()
    options = _build_options(outputs, system)
    return {
        "reference": normalized,
        "url": wrapper["url"],
        "original_url": wrapper["original_url"],
        "wrapper": wrapper["directory"],
        "description": description,
        "system": system,
        "options": options,
        "home_manager": nix_catalog.home_manager_available(),
        "system_scope": nix_catalog.is_nixos(),
        "apps": _clean_names(outputs.get("apps")),
        "home_configurations": _clean_names(outputs.get("homeConfigurations")),
        "nixos_configurations": _clean_names(outputs.get("nixosConfigurations")),
    }


def _load_state():
    try:
        text = STATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"schema": SCHEMA, "flakes": []}
    except OSError as error:
        raise FlakeError(
            f"Could not read the imported flake state: {error}"
        ) from error
    try:
        payload = json.loads(text)
    except (ValueError, TypeError, UnicodeError) as error:
        raise FlakeError(
            "The imported flake state is unreadable; move "
            f"{STATE_PATH} aside to reset it."
        ) from error
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise FlakeError(
            "The imported flake state has an unsupported format; move "
            f"{STATE_PATH} aside to reset it."
        )
    flakes = []
    for record in payload.get("flakes") or ():
        if not isinstance(record, dict):
            continue
        url = str(record.get("url") or "").strip()
        scope = str(record.get("scope") or "").strip()
        if not url or scope not in ("home-manager", "system"):
            continue
        options = [
            option
            for option in record.get("options") or ()
            if isinstance(option, dict)
            and str(option.get("key") or "").strip()
            and bool(option.get("selectable", True))
        ]
        if not options:
            continue
        original_url = str(record.get("original_url") or "").strip()
        stable = original_url or url
        flakes.append(
            {
                "id": f"{scope}:{stable}",
                "url": url,
                "original_url": original_url,
                "wrapper": str(record.get("wrapper") or ""),
                "reference": str(record.get("reference") or url),
                "description": str(record.get("description") or ""),
                "scope": scope,
                "system": str(record.get("system") or ""),
                "options": options,
                "imported": int(record.get("imported") or 0),
            }
        )
    return {"schema": SCHEMA, "flakes": flakes}


def state_available():
    """Whether the durable imported-flake state file currently exists."""
    try:
        return STATE_PATH.is_file()
    except OSError:
        return False


def _save_state(payload):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        STATE_PATH,
        payload,
        mode=0o600,
        separators=(",", ":"),
        ensure_ascii=False,
        fsync=True,
    )


def imports(scope=None):
    records = _load_state()["flakes"]
    if scope:
        records = [record for record in records if record["scope"] == scope]
    return sorted(
        records,
        key=lambda record: (
            record["description"] or record["reference"],
            record["id"],
        ),
    )


def add_import(info, scope, selected_keys):
    """Store selected flake outputs and return the record."""
    if scope not in ("home-manager", "system"):
        raise FlakeError("Invalid flake install scope")
    allowed = {
        option["key"]: option
        for option in info.get("options") or ()
        if isinstance(option, dict)
        and option.get("selectable")
        and (
            (
                scope == "system"
                and option.get("scope") in ("both", "system")
            )
            or (
                scope == "home-manager"
                and option.get("scope") in ("both", "home-manager")
            )
        )
    }
    selected = [allowed[key] for key in selected_keys if key in allowed]
    if not selected:
        raise FlakeError("Select at least one importable flake output")
    url = str(info.get("url") or "").strip()
    if not url:
        raise FlakeError("The flake has no locked URL")
    original_url = str(info.get("original_url") or "").strip()
    stable = original_url or url
    record = {
        "id": f"{scope}:{stable}",
        "url": url,
        "original_url": original_url,
        "wrapper": str(info.get("wrapper") or ""),
        "reference": str(info.get("reference") or url),
        "description": str(info.get("description") or ""),
        "scope": scope,
        "system": str(info.get("system") or nix_catalog.linux_arch()),
        "options": selected,
        "imported": int(time.time()),
    }
    with LOCK:
        payload = _load_state()
        payload["flakes"] = [
            existing
            for existing in payload["flakes"]
            if existing["scope"] != scope
            or (
                existing["id"] != record["id"]
                and existing["reference"] != record["reference"]
                and not (
                    original_url
                    and existing.get("original_url") == original_url
                )
            )
        ]
        payload["flakes"].append(record)
        _save_state(payload)
    return record


_WRAPPER_NAME = re.compile(r"^[0-9a-f]{24}$")


def cleanup_wrappers():
    """Delete wrapper trees no longer referenced by an imported flake.

    Only direct children with our digest-style names are considered, and a
    wrapper is kept when any durable state record still references it. This
    is called after a successful rebuild, never while the old generated
    module may still need the wrapper.
    """
    try:
        records = imports()
    except FlakeError:
        raise
    referenced = {
        str(Path(str(record.get("wrapper") or "").strip()).resolve())
        for record in records
        if str(record.get("wrapper") or "").strip()
    }
    try:
        root = WRAPPER_DIR.resolve()
    except OSError:
        return 0
    removed = 0
    try:
        children = list(WRAPPER_DIR.iterdir())
    except OSError:
        return 0
    for child in children:
        if not _WRAPPER_NAME.fullmatch(child.name):
            continue
        if child.is_symlink() or not child.is_dir():
            continue
        try:
            target = child.resolve()
            target.relative_to(root)
        except (OSError, ValueError):
            continue
        if str(target) in referenced:
            continue
        shutil.rmtree(target, ignore_errors=True)
        removed += 1
    return removed


def remove_imports(record_ids):
    """Remove imported flakes by id and return the affected scopes.

    Missing ids are tolerated: a failed rebuild leaves the generated module
    and registry transaction in place while the state record is already
    gone, and the same removal must be retryable. The id starts with the
    scope (``home-manager:...`` or ``system:...``), so the affected scope is
    recoverable even then.
    """
    wanted = {
        str(record_id or "").strip()
        for record_id in record_ids or ()
        if str(record_id or "").strip()
    }
    if not wanted:
        raise FlakeError("No imported flake id was provided")
    scopes = set()
    removed = 0
    with LOCK:
        payload = _load_state()
        kept = []
        for record in payload["flakes"]:
            if record["id"] in wanted:
                scopes.add(record["scope"])
                wanted.discard(record["id"])
                removed += 1
            else:
                kept.append(record)
        if removed:
            payload["flakes"] = kept
            _save_state(payload)
    for record_id in wanted:
        scope = record_id.split(":", 1)[0]
        if scope in ("home-manager", "system"):
            scopes.add(scope)
    if not scopes:
        raise FlakeError("No imported flake matched the requested id")
    return sorted(scopes)


def remove_import(record_id):
    record_id = str(record_id or "").strip()
    if not record_id:
        return False
    if not any(record["id"] == record_id for record in imports()):
        return False
    remove_imports([record_id])
    return True


def record_ids_for_reference(reference, scope=None):
    """Return the state ids matching a reference, original URL or wrapper URL."""
    value = str(reference or "").strip()
    if not value:
        return []
    return [
        record["id"]
        for record in imports(scope)
        if value in (
            record.get("reference"),
            record.get("original_url"),
            record.get("url"),
        )
    ]


def _nix_string(value):
    return json.dumps(str(value), ensure_ascii=False)


def _lookup(expression, name):
    return f"(builtins.getAttr {_nix_string(name)} {expression})"


def _package_expression(variable, option):
    source = option.get("source")
    name = option.get("name")
    if source == "defaultPackage":
        return f"{variable}.defaultPackage.${{system}}"
    attr = "packages" if source == "packages" else "legacyPackages"
    return _lookup(f"{variable}.{attr}.${{system}}", name)


def _module_expression(variable, option):
    kind = str(option.get("kind") or "")
    attr = str(option.get("attr") or "")
    allowed = _MODULE_ATTRS.get(kind) or {"homeManagerModules", "nixosModules"}
    if attr not in allowed:
        attr = _MODULE_ATTR_DEFAULTS.get(kind, "homeManagerModules")
    if option.get("direct"):
        return f"{variable}.{attr}"
    return _lookup(f"{variable}.{attr}", option.get("name"))


def _overlay_expression(variable, option):
    attr = str(option.get("attr") or "")
    if attr not in _MODULE_ATTRS["overlay"]:
        attr = _MODULE_ATTR_DEFAULTS["overlay"]
    if option.get("direct"):
        return f"{variable}.{attr}"
    return _lookup(f"{variable}.{attr}", option.get("name"))


def _append_sequence(lines, name, expressions, sequences):
    """Append a list-valued assignment, concatenating whole-list outputs."""
    if not expressions and not sequences:
        return
    suffix = "".join(f" ++ {expression}" for expression in sequences)
    if expressions:
        lines.append(f"  {name} = [")
        lines.extend(f"    {expression}" for expression in expressions)
        lines.append(f"  ]{suffix};")
    elif len(sequences) == 1:
        lines.append(f"  {name} = {sequences[0]};")
    else:
        lines.append(f"  {name} = []{suffix};")


def render_module(scope):
    """Render the Nix module that merges the imported flakes for one scope."""
    if scope not in ("home-manager", "system"):
        raise FlakeError("Invalid flake install scope")
    records = imports(scope)
    variables = []
    module_imports = []
    module_sequences = []
    packages = []
    overlays = []
    overlay_sequences = []
    for index, record in enumerate(records):
        variable = f"flake_{index}"
        variables.append((variable, record["url"]))
        for option in record.get("options") or ():
            kind = option.get("kind")
            if kind in ("package", "default_package"):
                packages.append(_package_expression(variable, option))
            elif kind == "home_module" and scope == "home-manager":
                target = (
                    module_sequences
                    if option.get("is_list")
                    else module_imports
                )
                target.append(_module_expression(variable, option))
            elif kind == "nixos_module" and scope == "system":
                target = (
                    module_sequences
                    if option.get("is_list")
                    else module_imports
                )
                target.append(_module_expression(variable, option))
            elif kind == "overlay":
                target = (
                    overlay_sequences
                    if option.get("is_list")
                    else overlays
                )
                target.append(_overlay_expression(variable, option))

    lines = [
        "{ pkgs, ... }:",
        "",
        "# Generated by LinuxToys from imported Nix flakes.",
    ]
    if variables:
        lines.append("let")
        lines.append("  system = pkgs.stdenv.hostPlatform.system;")
        for variable, url in variables:
            lines.append(f"  {variable} = builtins.getFlake {_nix_string(url)};")
        lines.append("in")
    lines.append("{")
    _append_sequence(lines, "imports", module_imports, module_sequences)
    if packages:
        target = (
            "environment.systemPackages"
            if scope == "system"
            else "home.packages"
        )
        lines.append(f"  {target} = [")
        lines.extend(f"    {expression}" for expression in packages)
        lines.append("  ];")
    _append_sequence(lines, "nixpkgs.overlays", overlays, overlay_sequences)
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _account():
    import getpass

    return (
        getpass.getuser(),
        os.path.expanduser("~"),
        socket.gethostname() or "nixos",
    )


def render_home_flake(system, username, home):
    return f"""{{ description = "Home Manager configuration managed by LinuxToys";
  inputs = {{
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    home-manager = {{
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    }};
  }};
  outputs = {{ self, nixpkgs, home-manager, ... }}:
    let
      system = {json.dumps(system)};
      username = {json.dumps(username)};
      homeDirectory = {json.dumps(home)};
    in {{
      homeConfigurations.${{username}} = home-manager.lib.homeManagerConfiguration {{
        pkgs = import nixpkgs {{ inherit system; config.allowUnfree = true; }};
        modules = [ ./home.nix ];
      }};
    }};
}}
"""


def render_system_flake(system, hostname):
    return f"""{{ description = "NixOS configuration managed by LinuxToys";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = {{ self, nixpkgs, ... }}:
    {{
      nixosConfigurations.{json.dumps(hostname)} = nixpkgs.lib.nixosSystem {{
        system = {json.dumps(system)};
        modules = [ ./configuration.nix ];
      }};
    }};
}}
"""


def materialize_removal(record):
    """Create a terminal script that removes one imported flake and rebuilds.

    State is mutated only when the script actually runs, so cancelling the
    terminal leaves the import and its registry transaction untouched.
    """
    if not isinstance(record, dict):
        raise FlakeError("No imported flake was selected")
    record_id = str(record.get("id") or "").strip()
    scope = str(record.get("scope") or "").strip()
    if not record_id or scope not in ("home-manager", "system"):
        raise FlakeError("Invalid imported flake record")
    from urllib.parse import quote

    encoded = quote(record_id, safe="")
    label = str(
        record.get("description")
        or record.get("reference")
        or record.get("original_url")
        or "Nix flake"
    ).strip()
    # The label lands in a shell comment; never let flake metadata inject a
    # newline that would turn the rest into executable lines.
    label = _CONTROL.sub(" ", label).strip() or "Nix flake"
    name = f"Remove Nix flake: {label}"
    script_fd, script_path = tempfile.mkstemp(
        prefix="linuxtoys-flake-remove-", suffix=".sh"
    )
    with os.fdopen(script_fd, "w", encoding="utf-8") as handle:
        handle.write(
            "#!/usr/bin/env bash\n"
            f"# name: {name}\n"
            "# description: Remove this imported flake and rebuild the Nix configuration.\n"
            "# icon: nix.svg\n"
            "# architectures: x86_64, aarch64\n"
            "set -eo pipefail\n"
            'source "$SCRIPT_DIR/libs/linuxtoys.bash"\n'
            'source "$SCRIPT_DIR/libs/nixsys.bash"\n'
            f"nix_remove_flakes {shlex.quote(encoded)}\n"
        )
    os.chmod(script_path, 0o700)
    return {
        "name": name,
        "description": "Remove this imported flake and rebuild the Nix configuration.",
        "icon": "nix.svg",
        "path": script_path,
        "version": "",
        "is_script": True,
        "is_subcategory": False,
        "revert": "no",
        "reboot": "no",
        "repo": "",
        "cleanup_path": script_path,
    }


def materialize_apply(scope):
    """Create a terminal script that publishes and rebuilds the flake module."""
    if scope not in ("home-manager", "system"):
        raise FlakeError("Invalid flake install scope")
    if scope == "home-manager" and not nix_catalog.home_manager_available():
        raise FlakeError("Home Manager is not available")
    if scope == "system" and not nix_catalog.is_nixos():
        raise FlakeError("The system scope is only available on NixOS")
    system = nix_catalog.linux_arch()
    if not system:
        raise FlakeError(
            "Nix flakes are only available on x86_64 and aarch64 hosts"
        )
    username, home, hostname = _account()
    module_text = render_module(scope)
    flake_text = (
        render_system_flake(system, hostname)
        if scope == "system"
        else render_home_flake(system, username, home)
    )
    module_fd, module_path = tempfile.mkstemp(
        prefix="linuxtoys-flake-module-", suffix=".nix"
    )
    with os.fdopen(module_fd, "w", encoding="utf-8") as handle:
        handle.write(module_text)
    flake_fd, flake_path = tempfile.mkstemp(
        prefix="linuxtoys-flake-", suffix=".nix"
    )
    with os.fdopen(flake_fd, "w", encoding="utf-8") as handle:
        handle.write(flake_text)
    script_fd, script_path = tempfile.mkstemp(
        prefix="linuxtoys-flake-import-", suffix=".sh"
    )
    with os.fdopen(script_fd, "w", encoding="utf-8") as handle:
        handle.write(
            "#!/usr/bin/env bash\n"
            "# name: Import Nix flake\n"
            "# description: Merge the imported flake outputs into the Nix configuration.\n"
            "# icon: nix.svg\n"
            "# architectures: x86_64, aarch64\n"
            "set -eo pipefail\n"
            'source "$SCRIPT_DIR/libs/linuxtoys.bash"\n'
            'source "$SCRIPT_DIR/libs/nixsys.bash"\n'
            f"module_source={shlex.quote(module_path)}\n"
            f"flake_source={shlex.quote(flake_path)}\n"
            "trap 'rm -f -- \"$module_source\" \"$flake_source\"' EXIT\n"
            "nix_import_flake_module "
            f"{shlex.quote(scope)} \"$module_source\" \"$flake_source\"\n"
        )
    os.chmod(script_path, 0o700)
    return {
        "name": "Import Nix flake",
        "description": "Merge the imported flake outputs into the Nix configuration.",
        "icon": "nix.svg",
        "path": script_path,
        "version": "",
        "is_script": True,
        "is_subcategory": False,
        "revert": "no",
        "reboot": "no",
        "repo": "",
    }
