"""Nixpkgs catalog, setup discovery and queued operation materialization.

The Nix subsystem is deliberately self-managed: LinuxToys never installs
packages through ``nix-env``. It maintains a declarative ``linuxtoys.nix``
module for home-manager and for NixOS system packages, then rebuilds the
affected profile when the user applies queued operations.

This module owns discovery, the package snapshot cache and the generated
helper scripts. The heavy normalization/filtering lives in Rust
(``_catalog_rs.NixCatalog``), mirroring the other catalogs.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from . import _catalog_rs

_CACHE_ROOT = Path(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
)
CACHE_DIR = _CACHE_ROOT / "linuxtoys" / "nix-catalog"
RAW_PATH = CACHE_DIR / "packages.json"
MAX_AGE = 14 * 24 * 60 * 60
MAX_BYTES = 128 * 1024 * 1024
SEARCH_TIMEOUT = 15 * 60

_HM_CONFIG_OVERRIDE = os.environ.get("HOME_MANAGER_CONFIG")
HOME_CONFIG_DIR = (
    Path(_HM_CONFIG_OVERRIDE).expanduser().parent
    if _HM_CONFIG_OVERRIDE
    else Path(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")) / "home-manager"
)
HOME_MODULE_PATH = Path(
    os.environ.get(
        "LINUXTOYS_NIX_HM_MODULE",
        str(HOME_CONFIG_DIR / "linuxtoys.nix"),
    )
)
SYSTEM_MODULE_PATH = Path(
    os.environ.get("LINUXTOYS_NIX_SYSTEM_MODULE", "/etc/nixos/linuxtoys.nix")
)
_ATTR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_'-]*$")
_MODULE_PACKAGE_RE = re.compile(
    r"^\s*pkgs\.([A-Za-z_][A-Za-z0-9_'-]*)\s*(?:#.*)?$", re.MULTILINE
)
_LOCK = threading.RLock()
_VALIDATED_SNAPSHOT = None
logger = logging.getLogger(__name__)


def nix_executable():
    """Discover the Nix client without relying on a desktop session PATH."""
    candidates = [
        shutil.which("nix"),
        os.environ.get("NIX_BIN"),
        "/nix/var/nix/profiles/default/bin/nix",
        "/usr/bin/nix",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return os.path.abspath(candidate)
    return None


def enabled():
    # Presence is authoritative, exactly like Homebrew.
    return nix_executable() is not None


def home_manager_available():
    if shutil.which("home-manager"):
        return True
    for candidate in (
        Path(os.path.expanduser("~/.nix-profile/bin/home-manager")),
        Path(os.path.expanduser("~/.local/state/nix/profile/bin/home-manager")),
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return True
    return False


def is_nixos():
    return (
        os.path.exists("/etc/NIXOS")
        or os.path.exists("/etc/nixos/configuration.nix")
        or shutil.which("nixos-rebuild") is not None
    )


def linux_arch():
    machine = platform.machine().lower()
    if machine in ("aarch64", "arm64"):
        return "aarch64-linux"
    return "x86_64-linux"


def scopes():
    """Available install scopes, user-level first."""
    if not enabled():
        return []
    result = []
    if home_manager_available():
        result.append("home-manager")
    if is_nixos():
        result.append("system")
    return result


def availability_fingerprint():
    return (nix_executable(), home_manager_available(), is_nixos())


def _path_state(path):
    try:
        stat = path.stat()
        return (stat.st_size, stat.st_mtime_ns)
    except OSError:
        return None


def fingerprint():
    return json.dumps(
        {
            "executable": nix_executable(),
            "arch": linux_arch(),
            "raw": _path_state(RAW_PATH),
            "binary": _path_state(RAW_PATH.with_suffix(".bin")),
            "scopes": scopes(),
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def valid_snapshot():
    """Validate the cached nixpkgs snapshot on a worker."""
    global _VALIDATED_SNAPSHOT
    try:
        stat = RAW_PATH.stat()
        token = (os.fspath(RAW_PATH), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if _VALIDATED_SNAPSHOT == token:
            return True
        if not 0 < stat.st_size <= MAX_BYTES:
            return False
        if _catalog_rs.nix_snapshot_valid(os.fspath(RAW_PATH), MAX_BYTES):
            _VALIDATED_SNAPSHOT = token
            return True
        return False
    except (OSError, ValueError, UnicodeError):
        return False


def cached_path():
    """Return valid local metadata; never download. Call on a worker."""
    return RAW_PATH if enabled() and valid_snapshot() else None


def binary_snapshot_available():
    """Cheap UI readiness check; the Rust loader rebuilds stale binaries."""
    if not enabled():
        return False
    try:
        source = RAW_PATH.stat()
        binary = RAW_PATH.with_suffix(".bin").stat()
        return source.st_size > 0 and binary.st_size > 0 and binary.st_mtime_ns >= source.st_mtime_ns
    except OSError:
        return False


def needs_refresh():
    if not enabled():
        return False
    if not valid_snapshot():
        return True
    try:
        return time.time() - RAW_PATH.stat().st_mtime >= MAX_AGE
    except OSError:
        return True


def _nix_search_command(executable):
    return [
        executable,
        "--extra-experimental-features",
        "nix-command flakes",
        "search",
        "nixpkgs",
        "^",
        "--json",
    ]


def load_or_refresh(force=False):
    """Fetch the nixpkgs package list only while Nix is present.

    The previous valid snapshot is retained when a refresh fails, so a transient
    network/registry problem never empties the Nix category.
    """
    if not enabled():
        return None
    with _LOCK:
        try:
            fresh = not needs_refresh()
        except OSError:
            fresh = False
        if force or not fresh:
            temporary = None
            try:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(
                    dir=CACHE_DIR, prefix="packages-", suffix=".json"
                )
                executable = nix_executable()
                if not executable:
                    return None
                environment = {
                    **os.environ,
                    "NIX_CONFIG": (
                        (os.environ.get("NIX_CONFIG", "") + "\n")
                        if os.environ.get("NIX_CONFIG")
                        else ""
                    )
                    + "extra-experimental-features = nix-command flakes\n",
                    "LC_ALL": "C",
                }
                with os.fdopen(fd, "wb") as handle:
                    result = subprocess.run(
                        _nix_search_command(executable),
                        stdout=handle,
                        stderr=subprocess.PIPE,
                        timeout=SEARCH_TIMEOUT,
                        check=False,
                        env=environment,
                    )
                if result.returncode:
                    detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
                    raise RuntimeError(
                        detail[-1] if detail else "nix search failed"
                    )
                size = os.path.getsize(temporary)
                if not 0 < size <= MAX_BYTES:
                    raise ValueError("Nix package metadata is empty or too large")
                if not _catalog_rs.nix_snapshot_valid(temporary, MAX_BYTES):
                    raise ValueError("Invalid Nix package metadata")
                if not enabled():
                    return None
                os.replace(temporary, RAW_PATH)
                temporary = None
                _VALIDATED_SNAPSHOT = None
                # Force the Rust binary cache to be rebuilt from the new source.
                try:
                    RAW_PATH.with_suffix(".bin").unlink()
                except OSError:
                    pass
                # Warm the compact Rust cache on this worker so opening the
                # category never pays the normalization cost on the GTK thread.
                try:
                    _catalog_rs.NixCatalog(os.fspath(RAW_PATH), scopes())
                except Exception:
                    pass
            except Exception as error:
                logger.warning(
                    "Nix package list refresh failed; retaining cached data: %s", error
                )
            finally:
                if temporary:
                    try:
                        os.unlink(temporary)
                    except OSError:
                        pass
        path = cached_path()
        if path is not None and not binary_snapshot_available():
            # The raw snapshot may already be fresh while the compact Rust cache
            # is missing (first run after an upgrade, for example).
            try:
                _catalog_rs.NixCatalog(os.fspath(path), scopes())
            except Exception:
                pass
        return path


def _flakes_enabled():
    executable = nix_executable()
    if not executable:
        return False
    for args in (["config", "show", "experimental-features"], ["show-config"]):
        try:
            result = subprocess.run(
                [executable, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode:
            continue
        if args[0] == "show-config":
            for line in result.stdout.splitlines():
                key, separator, value = line.partition("=")
                if separator and key.strip() == "experimental-features":
                    return "flakes" in value.split()
            continue
        values = result.stdout.replace(",", " ").split()
        return "flakes" in values
    return False


def _unfree_enabled():
    if os.environ.get("NIXPKGS_ALLOW_UNFREE") in ("1", "true", "yes"):
        return True
    marker = _CACHE_ROOT / "linuxtoys" / "nix" / "allow-unfree"
    try:
        if marker.read_text(encoding="utf-8").strip() == "1":
            return True
    except OSError:
        pass
    candidates = [
        HOME_MODULE_PATH,
        SYSTEM_MODULE_PATH,
        Path(os.path.expanduser("~/.config/nixpkgs/config.nix")),
        HOME_CONFIG_DIR / "home.nix",
        HOME_CONFIG_DIR / "flake.nix",
        Path("/etc/nixos/configuration.nix"),
    ]
    if _HM_CONFIG_OVERRIDE:
        candidates.append(Path(_HM_CONFIG_OVERRIDE).expanduser())
    pattern = re.compile(r"allowUnfree\s*=\s*true")
    for candidate in candidates:
        try:
            if pattern.search(candidate.read_text(encoding="utf-8", errors="replace")):
                return True
        except OSError:
            continue
    return False


def setup_status():
    """Return the first-click readiness report used by the setup dialog."""
    flakes = _flakes_enabled()
    unfree = _unfree_enabled()
    home_manager = home_manager_available()
    system = is_nixos()
    return {
        "nix": enabled(),
        "flakes": flakes,
        "unfree": unfree,
        "home_manager": home_manager,
        "system": system,
        "backend": home_manager or system,
        "ready": bool(enabled() and flakes and (home_manager or system)),
    }


def setup_missing(status=None):
    status = status or setup_status()
    missing = []
    if not status["flakes"]:
        missing.append("flakes")
    if not status["unfree"]:
        missing.append("unfree")
    if not status["home_manager"] and not status["system"]:
        missing.append("home-manager")
    return missing


def module_path(scope):
    return SYSTEM_MODULE_PATH if scope == "system" else HOME_MODULE_PATH


def _module_packages(path):
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return set(_MODULE_PACKAGE_RE.findall(content))


def installed_names(scope=None):
    """Observe the packages LinuxToys itself manages through its Nix modules."""
    paths = [module_path(scope)] if scope else [HOME_MODULE_PATH, SYSTEM_MODULE_PATH]
    names = set()
    for path in paths:
        names.update(_module_packages(path))
    return names


def is_installed(info):
    attr = str(
        info.get("nix_name") or info.get("package-name") or ""
    ).strip()
    if not attr:
        return False
    scope = str(info.get("nix_scope") or "").strip()
    return attr in installed_names(scope or None)


def validate_attr(attr):
    value = str(attr or "").strip()
    if not _ATTR_RE.fullmatch(value):
        raise ValueError("Invalid Nix package name")
    return value


def _materialize_script(function, name, description):
    fd, path = tempfile.mkstemp(prefix="linuxtoys-nix-", suffix=".sh")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(
            "#!/usr/bin/env bash\n"
            f"# name: {name}\n"
            f"# description: {description}\n"
            "# icon: nix.svg\n"
            "# architectures: x86_64, aarch64\n"
            "set -eo pipefail\n"
            'source "$SCRIPT_DIR/libs/linuxtoys.bash"\n'
            'source "$SCRIPT_DIR/libs/nixsys.bash"\n'
            f"{function}\n"
        )
    os.chmod(path, 0o700)
    return {
        "name": name,
        "description": description,
        "icon": "nix.svg",
        "path": path,
        "version": "",
        "is_script": True,
        "is_subcategory": False,
        "revert": "no",
        "reboot": "no",
        "repo": "",
    }


def materialize_setup():
    """Script that checks/offers flakes, unfree and home-manager setup."""
    return _materialize_script(
        "nix_setup",
        "Nix package management setup",
        "Check and configure flakes, unfree packages and home-manager.",
    )


def materialize_apply():
    """Script that applies every queued Nix install/removal."""
    return _materialize_script(
        "nix_apply_operations",
        "Apply Nix package operations",
        "Rebuild home-manager and/or the NixOS system profile.",
    )
