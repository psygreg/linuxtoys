"""Resolve native Flatpak refs and installed-app runtime extensions read-only."""

from __future__ import annotations

import configparser
import re
import subprocess

from .architecture import ArchitectureError, host, normalize


def _query(*args: str) -> str:
    try:
        return subprocess.run(
            ["flatpak", *args], check=True, capture_output=True, text=True, timeout=30
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise ArchitectureError(
            "Flatpak ref is unavailable; configure the remote and install the native target app first"
        ) from error


def validate_ref(ref: str) -> str:
    """Check a fully resolved ref, rejecting foreign/unknown ISA and ambiguity."""
    parts = ref.split("/")
    if len(parts) == 4 and parts[0] in {"app", "runtime"}:
        parts = parts[1:]
    if len(parts) != 3 or not all(re.fullmatch(r"[A-Za-z0-9._+-]+", p) for p in parts):
        raise ArchitectureError(f"Invalid/unresolved Flatpak ref: {ref!r}")
    if normalize(parts[1]) != host():
        raise ArchitectureError(f"Foreign Flatpak architecture in {ref}")
    return "/".join(parts)


def resolve_refs(requests: list[str], remote: str, scope: str) -> list[str]:
    """Resolve the entire batch without bootstrapping remotes or installing apps."""
    native = host().value
    refs = []
    for request in requests:
        # Ref architecture, if supplied, must already agree with the host.
        parts = request.split("/")
        if len(parts) == 3 and parts[1] and normalize(parts[1]) != host():
            raise ArchitectureError(f"Foreign Flatpak request: {request}")
        ref = _query(
            "remote-info", scope, f"--arch={native}", "--show-ref", remote, request
        )
        refs.append(validate_ref(ref))
    return refs


def extension_plan(app_id: str, extension: str) -> tuple[str, str, list[str]]:
    """Resolve extensions from installed app/runtime metadata, never fixed branches.

    GNOME/KDE runtime branches are not Freedesktop extension branches. Read the
    runtime's Extension section (including version/versions) instead of guessing.
    """
    validate_name = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2,}")
    if not validate_name.fullmatch(app_id) or not validate_name.fullmatch(extension):
        raise ArchitectureError("Expected an application ID and extension ID")
    scope = ""
    runtime = ""
    for candidate in ("--user", "--system"):
        try:
            runtime = validate_ref(_query("info", candidate, "--show-runtime", app_id))
        except ArchitectureError:
            continue
        scope = candidate
        break
    if not scope:
        raise ArchitectureError(f"Install native {app_id} before adding {extension}")
    metadata = configparser.ConfigParser(interpolation=None, strict=True)
    try:
        metadata.read_string(_query("info", scope, "--show-metadata", runtime))
    except configparser.Error as error:
        raise ArchitectureError("Invalid installed runtime metadata") from error
    sections = [
        section
        for section in metadata.sections()
        if section.startswith("Extension ")
        and (extension == section[10:] or extension.startswith(section[10:] + "."))
    ]
    if not sections:
        raise ArchitectureError(
            f"Runtime {runtime} does not declare extension {extension}"
        )
    section = metadata[max(sections, key=len)]
    versions = section.get("versions") or section.get("version")
    if not versions:
        raise ArchitectureError(f"Runtime does not declare a branch for {extension}")
    branches = sorted(
        set(value.strip() for value in versions.split(";") if value.strip())
    )
    requests = [f"{extension}/{host().value}/{branch}" for branch in branches]
    remote = _query("info", scope, "--show-origin", runtime)
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", remote):
        raise ArchitectureError("Installed runtime has no unambiguous origin remote")
    return scope, remote, resolve_refs(requests, remote, scope)


def extension_refs(app_id: str, extension: str) -> list[str]:
    """Return exact refs for callers that do not install/record transactions."""
    return extension_plan(app_id, extension)[2]
