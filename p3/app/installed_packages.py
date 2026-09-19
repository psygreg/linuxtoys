"""RAM + disk cache of user-installed packages relevant to AppStream management."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import tempfile
import threading
import xml.etree.ElementTree as ET
from pathlib import Path

from .compat import get_system_compat_keys, is_containerized

CACHE_ROOT = Path(os.path.expanduser("~/.cache/linuxtoys"))
_LOCK = threading.RLock()
_STATE = {"manager": None, "native": set(), "flatpak": {}, "loaded": False}


def _manager():
    keys = get_system_compat_keys()
    if "steamos" in keys:
        return None
    if "ostree" in keys or "ublue" in keys:
        return "rpm-ostree"
    if "cachy" in keys or "arch" in keys or "manjaro" in keys:
        return "pacman"
    if "ubuntu" in keys or "debian" in keys or "pika" in keys or "deepin" in keys or "zorin" in keys:
        return "apt"
    if "fedora" in keys or "rhel" in keys:
        return "dnf"
    if "suse" in keys:
        return "zypper"
    return None


def _path(name):
    return CACHE_ROOT / name


def _read_lines(name):
    try:
        return {line.strip() for line in _path(name).read_text(encoding="utf-8").splitlines() if line.strip()}
    except OSError:
        return set()


def _atomic_lines(name, values):
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    target = _path(name)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text("".join(f"{value}\n" for value in sorted(set(values))), encoding="utf-8")
    os.replace(tmp, target)


def load_previous():
    """Load the previous startup snapshot immediately; never invokes a package manager."""
    manager = _manager()
    flatpak = {}
    for value in _read_lines("flatpak"):
        scope, sep, app_id = value.partition("\t")
        if sep and app_id:
            flatpak.setdefault(app_id.casefold(), set()).add(scope)
        else:
            flatpak.setdefault(value.casefold(), set()).add("unknown")
    with _LOCK:
        _STATE["manager"] = manager
        _STATE["native"] = _read_lines(manager) if manager else set()
        _STATE["flatpak"] = flatpak
        _STATE["loaded"] = True
    return snapshot()


def _run(cmd):
    try:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              text=True, check=False, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _collect_flatpak():
    if is_containerized() or not shutil_which("flatpak"):
        return {}
    result = {}
    # Query scopes independently so externally-installed apps can be removed from
    # the same installation that actually owns them.
    for scope, flag in (("user", "--user"), ("system", "--system")):
        output = _run(["flatpak", flag, "list", "--app", "--columns=application"])
        for line in output.splitlines():
            app_id = line.strip()
            if app_id:
                result.setdefault(app_id.casefold(), set()).add(scope)
    return result


def shutil_which(command):
    from shutil import which
    return which(command)


def _collect_native(manager):
    if manager == "pacman":
        return {line.split()[0] for line in _run(["pacman", "-Qe"]).splitlines() if line.strip()}
    if manager == "apt":
        packages = set()
        for line in _run(["apt", "list", "--manual-installed"]).splitlines():
            line = line.strip()
            if not line or line.startswith(("Listing", "WARNING")) or "/" not in line:
                continue
            packages.add(line.split("/", 1)[0])
        return packages
    if manager == "dnf":
        output = _run(["dnf", "repoquery", "--leaves", "--userinstalled", "--qf", "%{name}"])
        return {line.strip() for line in output.splitlines() if line.strip() and not line.startswith("Updating")}
    if manager == "zypper":
        output = _run([
            "zypper", "--xmlout", "--non-interactive", "--disable-repositories",
            "packages", "--userinstalled",
        ])
        if not output.strip():
            return set()
        try:
            root = ET.fromstring(output)
        except ET.ParseError:
            return set()
        return {
            node.get("name", "").strip()
            for node in root.iter("solvable")
            if node.get("name", "").strip()
        }
    if manager == "rpm-ostree":
        packages = set()
        collecting = False
        for raw in _run(["rpm-ostree", "status"]).splitlines():
            stripped = raw.strip()
            if stripped.startswith("LayeredPackages:"):
                collecting = True
                stripped = stripped.split(":", 1)[1].strip()
            elif collecting and raw[:1].isspace() and stripped and ":" not in stripped:
                pass
            elif collecting:
                break
            else:
                continue
            packages.update(stripped.split())
        return packages
    return set()


def refresh():
    """Refresh both snapshots synchronously. Intended for a background thread."""
    manager = _manager()
    native = _collect_native(manager) if manager else set()
    flatpak = _collect_flatpak()
    if manager:
        _atomic_lines(manager, native)
    flatpak_lines = [f"{scope}\t{app_id}" for app_id, scopes in flatpak.items() for scope in scopes]
    _atomic_lines("flatpak", flatpak_lines)
    with _LOCK:
        _STATE.update(manager=manager, native=set(native), flatpak={k: set(v) for k, v in flatpak.items()}, loaded=True)
    return snapshot()


def snapshot():
    with _LOCK:
        return {
            "manager": _STATE["manager"],
            "native": set(_STATE["native"]),
            "flatpak": {key: set(value) for key, value in _STATE["flatpak"].items()},
            "loaded": _STATE["loaded"],
        }


def match(info):
    """Return observed installation metadata for one AppStream entry, or None."""
    source = str(info.get("appstream_source", "") or "").strip()
    with _LOCK:
        if source == "flatpak":
            app_id = str(info.get("package-name") or info.get("appstream_id") or "").strip()
            scopes = _STATE["flatpak"].get(app_id.casefold())
            if not scopes:
                return None
            preferred = str(info.get("flatpak_scope", "") or "").strip()
            scope = preferred if preferred in scopes else ("user" if "user" in scopes else sorted(scopes)[0])
            return {"source": "flatpak", "package": app_id, "scope": scope}
        if source == "native":
            value = info.get("package-name") or ()
            packages = [value] if isinstance(value, str) else list(value)
            installed = [str(pkg) for pkg in packages if str(pkg) in _STATE["native"]]
            if installed:
                return {"source": "native", "packages": installed, "manager": _STATE["manager"]}
    return None


def build_external_removal(info, installed_match, translations=None):
    """Build a temporary standard package-removal script for an observed install."""
    if not installed_match:
        return None
    lines = ["#!/bin/bash", "set -eo pipefail", 'source "$SCRIPT_DIR/libs/linuxtoys.bash"', 'source "$SCRIPT_DIR/libs/helpers.bash"']
    if installed_match["source"] == "flatpak":
        app_id = shlex.quote(installed_match["package"])
        scope = installed_match.get("scope")
        flag = "--user" if scope == "user" else "--system" if scope == "system" else ""
        lines.append(f"flatpak {flag} uninstall -y {app_id}".replace("  ", " "))
    else:
        packages = " ".join(shlex.quote(pkg) for pkg in installed_match.get("packages", ()))
        if not packages:
            return None
        lines += ["sudo_rq", f"pkg_remove {packages}"]
    lines.append('echo "Removal completed."')
    fd, temp_path = tempfile.mkstemp(prefix="linuxtoys-appstream-remove-", suffix=".sh")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    os.chmod(temp_path, 0o700)
    name = info.get("name", "Application")
    label = (translations or {}).get("remove_action_name", "Remove {name}").format(name=name)
    return {"icon": info.get("icon", "application-x-executable"), "name": label,
            "description": "Remove an installed AppStream package.", "repo": info.get("repo", ""),
            "path": temp_path, "is_script": True, "cleanup_path": temp_path}


load_previous()
