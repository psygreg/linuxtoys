"""RAM + disk cache of user-installed packages relevant to AppStream management."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from . import homebrew_catalog
from . import registry_utils
from .compat import get_system_compat_keys, is_containerized

CACHE_ROOT = Path(os.path.expanduser("~/.cache/linuxtoys"))
_LOCK = threading.RLock()
_STATE = {"manager": None, "native": set(), "flatpak": {}, "snap": set(), "homebrew": set(), "loaded": False}


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
        _STATE["snap"] = {value.casefold() for value in _read_lines("snap")}
        _STATE["homebrew"] = {v.casefold() for v in _read_lines("homebrew-installed")} if homebrew_catalog.enabled() else set()
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


def _collect_snap():
    if is_containerized() or not shutil_which("snap"):
        return set()
    output = _run(["snap", "list"])
    result = set()
    for line in output.splitlines()[1:]:
        fields = line.split()
        if fields:
            result.add(fields[0].casefold())
    return result


def shutil_which(command):
    from shutil import which
    return which(command)


_ZYPPER_PACKAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+~-]*$")


def _parse_zypper_userinstalled(output):
    """Extract package names from zypper's `packages --userinstalled` listing.

    That command has no machine-readable output: even under --xmlout the
    listing arrives as a plain `S | Repository | Name | Version | Arch` table
    inside the XML stream (unlike `search`, which emits <solvable> elements).
    Rows are therefore recognized structurally: five pipe-separated fields
    whose first one is an installed status marker. That excludes the header
    ("S"), the column separators and the localized zypper messages.
    """
    packages = set()
    for line in output.splitlines():
        fields = [field.strip() for field in line.split("|")]
        if len(fields) != 5:
            continue
        status, _repository, name, version, _arch = fields
        if not status.startswith(("i", "v")):
            continue
        if not _ZYPPER_PACKAGE_NAME.fullmatch(name) or not version:
            continue
        packages.add(name)
    return packages


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
        return _parse_zypper_userinstalled(output)
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
    snap = _collect_snap()
    homebrew = homebrew_catalog.installed_names()
    if manager:
        _atomic_lines(manager, native)
    flatpak_lines = [f"{scope}\t{app_id}" for app_id, scopes in flatpak.items() for scope in scopes]
    _atomic_lines("flatpak", flatpak_lines)
    _atomic_lines("snap", snap)
    _atomic_lines("homebrew-installed", homebrew)
    with _LOCK:
        _STATE.update(
            manager=manager,
            native=set(native),
            flatpak={k: set(v) for k, v in flatpak.items()},
            snap=set(snap),
            homebrew=set(homebrew),
            loaded=True,
        )
    return snapshot()


def snapshot():
    with _LOCK:
        return {
            "manager": _STATE["manager"],
            "native": set(_STATE["native"]),
            "flatpak": {key: set(value) for key, value in _STATE["flatpak"].items()},
            "snap": set(_STATE["snap"]),
            "homebrew": set(_STATE["homebrew"]) if homebrew_catalog.enabled() else set(),
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
        if source == "homebrew":
            package = str(info.get("homebrew_name") or info.get("package-name") or "").strip()
            if homebrew_catalog.enabled() and package.casefold() in _STATE["homebrew"]:
                return {"source": "homebrew", "package": package}
            return None
        if source == "snap":
            snap_name = str(info.get("snap_name") or info.get("package-name") or "").strip()
            if snap_name and snap_name.casefold() in _STATE["snap"]:
                return {"source": "snap", "package": snap_name}
            return None
        if source in ("native", "aur"):
            value = info.get("package-name") or ()
            packages = [value] if isinstance(value, str) else list(value)
            installed = [str(pkg) for pkg in packages if str(pkg) in _STATE["native"]]
            if installed:
                return {"source": "native", "packages": installed, "manager": _STATE["manager"]}
    return None


# --- Provider dependency protection -----------------------------------------
#
# Some features install OTHER software the user may keep around: Homebrew
# (brew.sh), the Flathub remote (flathub.sh), Snapcraft (snap.sh), the Paru AUR
# helper (sys/sysadm/paru.sh) and Gear Lever (AppStream, used for AppImage
# integration on systemd systems). Such a feature is still tracked as installed
# as usual, but its removal is blocked while anything installed through it
# remains.

_PROVIDER_DEPENDENCIES = {
    "brew": "homebrew",
    "homebrew": "homebrew",
    "flathub": "flatpak",
    "snap": "snap",
    "snapcraft": "snap",
    "paru": "aur",
    "it.mijorus.gearlever": "appimage",
    "gear lever": "appimage",
}


def _provider_identity_candidates(script_info):
    """All identity strings a provider feature may be registered under."""
    candidates = (
        script_info.get("registry_name"),
        script_info.get("appstream_id"),
        script_info.get("name"),
        os.path.splitext(os.path.basename(str(script_info.get("path", "") or "")))[0],
    )
    return {
        str(candidate or "").strip().casefold()
        for candidate in candidates
        if str(candidate or "").strip()
    }


def _provider_kind(script_info):
    """Map one script/appstream identity onto its provider dependency kind."""
    for identity in _provider_identity_candidates(script_info or {}):
        if identity in _PROVIDER_DEPENDENCIES:
            return _PROVIDER_DEPENDENCIES[identity]
    return None


def _registry_dependent_counts():
    """Count AUR packages and AppImages known to the Action Registry."""
    counts = {"aur": 0, "appimage": 0}
    for name, executions in registry_utils.parse_registry_file().items():
        if not executions:
            continue
        if name.startswith("AUR: "):
            counts["aur"] += 1
            continue
        # Removal/auto-revert transactions describe uninstalls, not installs.
        if name.startswith(("Remove: ", "Auto-revert: ")):
            continue
        for operation in executions[-1][1]:
            text = str(operation)
            if text.startswith("appimage ") and not text.startswith("appimage rm "):
                counts["appimage"] += 1
    return counts


def _plural(count, singular, plural):
    return f"{count} {singular}" if count == 1 else f"{count} {plural}"


_CALL_SCRIPT_RE = re.compile(r"\bcall_script\s+([A-Za-z0-9_.:-]+)")
_DEPENDENCY_GRAPH_TTL_SECONDS = 30.0
_DEPENDENCY_GRAPH = {"built": None, "callers": {}, "declarers": {}}


def _dependency_graph():
    """Static relations between catalog features (cached briefly).

    callers:    call_script argument -> identity keys of scripts invoking it
    declarers:  declared listing dependency package -> feature identity keys

    A broken catalog must never block removals, so any failure keeps whatever
    partial graph was gathered.
    """
    now = time.monotonic()
    if (
        _DEPENDENCY_GRAPH["built"] is not None
        and now - _DEPENDENCY_GRAPH["built"] < _DEPENDENCY_GRAPH_TTL_SECONDS
    ):
        return _DEPENDENCY_GRAPH

    callers = {}
    declarers = {}
    try:
        from . import parser, repo_parser
        from .compat import get_script_file_data

        paths = list(parser._get_script_tree_index().get("all_scripts") or ())
        for path in paths:
            path = str(path)
            stem = os.path.splitext(os.path.basename(path))[0].casefold()
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            parent_keys = {stem}
            try:
                display = get_script_file_data(path)["headers"].get("name")
            except Exception:
                display = None
            if str(display or "").strip():
                parent_keys.add(str(display).strip().casefold())
            for match in _CALL_SCRIPT_RE.finditer(text):
                child = match.group(1).strip().casefold()
                if child:
                    callers.setdefault(child, set()).update(parent_keys)

        for entry in repo_parser.load_repo_entries(None) or ():
            if not isinstance(entry, dict):
                continue
            feature_keys = _provider_identity_candidates(entry)
            if not feature_keys:
                continue
            for dependency in entry.get("dependencies") or []:
                if not isinstance(dependency, dict):
                    continue
                spec = dependency.get("package-name")
                if isinstance(spec, dict):
                    packages = [
                        str(value).strip()
                        for value in spec.values()
                        if str(value or "").strip()
                    ]
                else:
                    try:
                        packages = repo_parser._normalize_package_names(spec)
                    except Exception:
                        packages = []
                for package in packages:
                    key = str(package or "").strip().casefold()
                    if key:
                        declarers.setdefault(key, set()).update(feature_keys)
    except Exception:
        pass

    _DEPENDENCY_GRAPH.update(built=now, callers=callers, declarers=declarers)
    return _DEPENDENCY_GRAPH


def provider_has_transaction(script_info):
    """Whether a provider feature was ever executed through LinuxToys.

    Some providers legitimately record no reversible operations (Flathub only
    adds a remote), so their transactions may carry no ops at all; such a
    transaction must still count as installed on the removability side.
    """
    if _provider_kind(script_info or {}) is None:
        return False
    registered = {
        str(name or "").strip().casefold()
        for name in registry_utils.parse_registry_file()
    }
    return any(
        identity in registered
        for identity in _provider_identity_candidates(script_info or {})
    )


def dependency_blockers(script_info):
    """Return human-readable reasons blocking removal of a feature.

    The empty list means removal is safe. Blockers are computed from the live
    installed-packages snapshot plus the Action Registry, so they reflect both
    installs made through LinuxToys and observed ones.
    """
    blockers = []

    provider = _provider_kind(script_info or {})
    if provider is not None:
        state = snapshot()
        registry_counts = _registry_dependent_counts()
        counts = {
            "homebrew": len(state.get("homebrew") or ()),
            "flatpak": len(state.get("flatpak") or {}),
            "snap": len(state.get("snap") or ()),
            "aur": registry_counts["aur"],
            "appimage": registry_counts["appimage"],
        }

        total = counts.get(provider, 0)
        if total > 0:
            labels = {
                "homebrew": _plural(total, "installed Homebrew package",
                                    "installed Homebrew packages"),
                "flatpak": _plural(total, "installed Flatpak app",
                                   "installed Flatpak apps"),
                "snap": _plural(total, "installed Snap", "installed Snaps"),
                "aur": _plural(total, "installed AUR package",
                               "installed AUR packages"),
                "appimage": _plural(total, "installed AppImage",
                                    "installed AppImages"),
            }
            blockers.append(labels[provider])

    registry_names = {
        str(name or "").strip().casefold()
        for name in registry_utils.parse_registry_file()
    }
    blockers.extend(_installed_dependent_blockers(script_info, registry_names))
    return blockers


def _installed_dependent_blockers(script_info, registry_names):
    """Blockers for components other installed features rely on.

    - A script called via ``call_script`` by MORE THAN ONE installed feature is
      blocked: with a single parent the parent's own revert also reverts the
      component, so removal stays safe.
    - A package declared as a listing dependency is blocked while any installed
      feature that declares it remains.
    """
    blockers = []
    graph = _dependency_graph()
    identity_keys = _provider_identity_candidates(script_info or {})
    if not identity_keys:
        return blockers

    installed_callers = set()
    installed_declarers = set()
    for child_key in identity_keys:
        for parent_key in graph["callers"].get(child_key, ()):
            if parent_key in registry_names:
                installed_callers.add(parent_key)
        for declarer_key in graph["declarers"].get(child_key, ()):
            if declarer_key in registry_names:
                installed_declarers.add(declarer_key)

    if len(installed_callers) > 1:
        blockers.append(_plural(
            len(installed_callers),
            "installed feature depends on it",
            "installed features depend on it",
        ))
    if installed_declarers:
        blockers.append(_plural(
            len(installed_declarers),
            "installed feature declares it as a dependency",
            "installed features declare it as a dependency",
        ))
    return blockers


def removal_blocked(script_info):
    """Whether dependency protection currently switches removal off."""
    return bool(dependency_blockers(script_info))


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
    elif installed_match["source"] == "homebrew":
        lines += ['source "$SCRIPT_DIR/libs/packages.bash"',
                  f"pkg_brew_remove {shlex.quote(installed_match['package'])}"]
    elif installed_match["source"] == "snap":
        snap_name = shlex.quote(installed_match["package"])
        lines += ["sudo_rq", f"sudo_ snap remove {snap_name}"]
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
    # Stable, untranslated registry identity — the appstream_id is language-
    # independent, unlike the display name (see get_display_name).
    stable_identity = str(info.get("appstream_id") or name).strip()
    return {"icon": info.get("icon", "application-x-executable"), "name": label,
            "registry_name": f"Remove: {stable_identity}",
            "description": "Remove an installed AppStream package.", "repo": info.get("repo", ""),
            "path": temp_path, "is_script": True, "cleanup_path": temp_path}


load_previous()
