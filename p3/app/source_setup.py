"""Prerequisite planning for catalog install sources.

URI installs can target a source before its package manager or repository is
configured. This module decides which catalog setup script (if any) must run
first and reports a source-specific error when the host cannot support it.
It is GUI-agnostic and never runs a script itself.
"""

from __future__ import annotations

import shutil
import subprocess

from . import manifest_helper


_SOURCE_LABELS = {
    "flathub": "Flathub",
    "flatpark": "FlatPark",
    "snap": "Snap Store",
    "homebrew": "Homebrew",
    "aur": "AUR",
    "appimage": "AppImage",
    "nix": "Nix",
    "nix-flake": "Nix flake",
    "native": "Native",
}


def source_label(source):
    return _SOURCE_LABELS.get(str(source or "").strip(), str(source or "").strip())


def _flatpak_supported_host():
    """Mirror LinuxToys' systemd/non-container Flatpak catalog policy."""
    try:
        from .compat import get_system_compat_keys, is_containerized

        return (
            not is_containerized()
            and "systemd" in get_system_compat_keys()
        )
    except Exception:
        return False


def _flatpak_remote_ready(remote, installation=""):
    """Whether one Flatpak remote exists in the requested installation."""
    executable = shutil.which("flatpak")
    if not executable:
        return False
    wanted = str(remote or "flathub").strip()
    installation = str(installation or "").strip()
    if installation and installation != "default":
        commands = [[executable, f"--installation={installation}", "remotes", "--columns=name"]]
    else:
        commands = [
            [executable, "--user", "remotes", "--columns=name"],
            [executable, "--system", "remotes", "--columns=name"],
        ]
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            if wanted in {line.strip() for line in result.stdout.splitlines()}:
                return True
    return False


def _snap_ready():
    return shutil.which("snap") is not None


def _snap_supported_host():
    """Mirror the bash pkg_snap host policy before offering Snap setup."""
    try:
        from .compat import get_system_compat_keys, is_containerized

        if is_containerized():
            return False
        keys = get_system_compat_keys()
        if "systemd" not in keys or "steamos" in keys:
            return False
        if "ostree" in keys and "gregos" not in keys:
            return False
        return True
    except Exception:
        return False


def _homebrew_ready():
    from . import homebrew_catalog

    return homebrew_catalog.enabled()


def _aur_supported():
    from . import aur_cache

    return aur_cache.supported()


def _manjaro_host():
    try:
        from .compat import get_system_compat_keys

        return "manjaro" in get_system_compat_keys()
    except Exception:
        return False


def _aur_client_ready():
    if _manjaro_host():
        return shutil.which("pamac") is not None
    return shutil.which("paru") is not None


def _flatpak_source(entry):
    remote = str(entry.get("flatpak_remote") or "flathub").strip().casefold()
    return "flatpark" if remote == "flatpark" else "flathub"


def source_kind(entry):
    """Return the install-source family a resolved entry will use."""
    if not isinstance(entry, dict):
        return "none"

    source = str(entry.get("appstream_source") or "").strip().casefold()
    if source == "flatpak":
        return _flatpak_source(entry)
    if source in {
        "snap", "homebrew", "aur", "appimage", "native", "nix", "nix-flake",
    }:
        return source

    entry_type = str(entry.get("type") or "").strip().casefold()
    if entry_type == "flathub":
        return _flatpak_source(entry)
    if entry_type == "snap":
        return "snap"
    if entry_type == "native":
        return "native"
    if entry_type == "url":
        try:
            from . import compat, repo_parser

            resolved = repo_parser._resolve_url_package(
                entry, compat.get_system_compat_keys()
            )
        except Exception:
            resolved = None
        kind = resolved[0] if resolved else ""
        if kind == "flatpak":
            # Flatpak bundle files bootstrap the default Flathub remote.
            return "flathub"
        if kind == "snap":
            return "snap"
        if kind == "appimage":
            return "appimage"
        return "native"
    return "none"


def _translated(translations, key, fallback, **values):
    try:
        text = (translations or {}).get(key, fallback)
        return str(text).format(**values)
    except Exception:
        try:
            return fallback.format(**values)
        except Exception:
            return fallback


def _error(translations, key, fallback, **values):
    return _translated(translations, key, fallback, **values)


def setup_plan(entry, translations=None):
    """Return the setup scripts a source needs, or a user-facing refusal.

    The result is a dict with ``source``, ``label``, ``setup_ids`` (catalog
    script ids to run in order), ``error`` (empty when usable) and ``ready``.
    Nix plans are intentionally left to the URI handler because their installer
    and subsystem setup are generated rather than plain catalog scripts.
    """
    source = source_kind(entry)
    plan = {
        "source": source,
        "label": source_label(source),
        "setup_ids": [],
        "error": "",
        "ready": True,
    }
    if source in {"native", "none", "appimage", "nix", "nix-flake"}:
        return plan

    if source in {"flathub", "flatpark"}:
        remote = "flatpark" if source == "flatpark" else "flathub"
        if not _flatpak_supported_host():
            plan["ready"] = False
            plan["error"] = _error(
                translations,
                "uri_flatpak_unavailable",
                "Flatpak is not supported on this system.",
            )
            return plan
        if _flatpak_remote_ready(
            remote, entry.get("flatpak_installation")
        ):
            return plan
        script_id = "flatpark" if remote == "flatpark" else "flathub"
        if manifest_helper.find_script_by_id(script_id, translations) is None:
            plan["ready"] = False
            plan["error"] = _error(
                translations,
                "uri_flatpak_source_unavailable",
                "{source} Flatpak support is not available on this system.",
                source=source_label(remote),
            )
            return plan
        plan["setup_ids"] = [script_id]
        plan["ready"] = False
        return plan

    if source == "snap":
        if not _snap_supported_host():
            plan["ready"] = False
            plan["error"] = _error(
                translations,
                "uri_snap_unavailable",
                "Snap packages are not supported on this system.",
            )
            return plan
        if _snap_ready():
            return plan
        if manifest_helper.find_script_by_id("snap", translations) is None:
            plan["ready"] = False
            plan["error"] = _error(
                translations,
                "uri_snap_unavailable",
                "Snap packages are not supported on this system.",
            )
            return plan
        plan["setup_ids"] = ["snap"]
        plan["ready"] = False
        return plan

    if source == "homebrew":
        if _homebrew_ready():
            return plan
        if manifest_helper.find_script_by_id("brew", translations) is None:
            plan["ready"] = False
            plan["error"] = _error(
                translations,
                "uri_homebrew_unavailable",
                "Homebrew is not available on this system.",
            )
            return plan
        plan["setup_ids"] = ["brew"]
        plan["ready"] = False
        return plan

    if source == "aur":
        if not _aur_supported():
            plan["ready"] = False
            plan["error"] = _error(
                translations,
                "uri_aur_unsupported",
                "AUR packages are only available on Arch-based systems.",
            )
            return plan
        if _aur_client_ready():
            return plan
        if _manjaro_host():
            plan["ready"] = False
            plan["error"] = _error(
                translations,
                "uri_aur_helper_unavailable",
                "No AUR helper is available on this system.",
            )
            return plan
        script_id = "paru"
        if manifest_helper.find_script_by_id(script_id, translations) is None:
            plan["ready"] = False
            plan["error"] = _error(
                translations,
                "uri_aur_helper_unavailable",
                "No AUR helper is available and the catalog helper installer is unavailable.",
            )
            return plan
        plan["setup_ids"] = [script_id]
        plan["ready"] = False
        return plan

    return plan


def setup_scripts(plan, translations=None):
    """Materialize plain catalog setup scripts from a plan."""
    scripts = []
    for script_id in plan.get("setup_ids") or ():
        script = manifest_helper.find_script_by_id(script_id, translations)
        if script is None:
            raise ValueError(
                _error(
                    translations,
                    "uri_source_setup_unavailable",
                    "The required {source} setup is not available on this system.",
                    source=plan.get("label") or "package-source",
                )
            )
        scripts.append(script)
    return scripts
