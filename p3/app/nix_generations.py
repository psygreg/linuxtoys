"""List and manage Home Manager and NixOS system generations.

The GUI dialog and the generated terminal scripts share this module so the
dialog lists exactly the generations the shell helpers act on. Listing is
read-only; activating or deleting a generation is materialized as a terminal
script, keeping privileged NixOS operations inside the normal ``sudo_`` flow.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from . import nix_catalog

HOME_SCOPE = "home-manager"
SYSTEM_SCOPE = "system"
SCOPES = (HOME_SCOPE, SYSTEM_SCOPE)

_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")
_LIST_LINE = re.compile(
    r"^\s*(?P<id>\d+)\s+"
    r"(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})"
    r"(?P<tail>.*)$"
)
_LINK_SUFFIX = "-link"


class GenerationError(ValueError):
    """A Nix generation operation was refused before anything ran."""


def home_profile_path() -> Path:
    """Return the Home Manager profile path, honoring ``XDG_STATE_HOME``."""
    state_home = os.environ.get("XDG_STATE_HOME") or str(
        Path("~/.local/state").expanduser()
    )
    return Path(state_home) / "nix" / "profiles" / "home-manager"


def system_profile_path() -> Path:
    """Return the NixOS system profile path."""
    return Path("/nix/var/nix/profiles/system")


def _profile_path(scope: str) -> Path:
    if scope == HOME_SCOPE:
        return home_profile_path()
    if scope == SYSTEM_SCOPE:
        return system_profile_path()
    raise GenerationError(f"Unknown Nix generation scope: {scope}")


def _nix_env_binary() -> str | None:
    """Locate ``nix-env``: it shares its directory with the Nix binary."""
    found = shutil.which("nix-env")
    if found:
        return found
    try:
        nix = nix_catalog.nix_executable()
    except Exception:
        nix = None
    if nix:
        sibling = Path(nix).with_name("nix-env")
        if sibling.is_file() and os.access(sibling, os.X_OK):
            return str(sibling)
    for candidate in (
        Path("~/.nix-profile/bin/nix-env").expanduser(),
        Path("~/.local/state/nix/profile/bin/nix-env").expanduser(),
        Path("/nix/var/nix/profiles/default/bin/nix-env"),
        Path("/run/current-system/sw/bin/nix-env"),
        Path("/usr/bin/nix-env"),
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _generation_link(profile: Path, generation: int) -> Path:
    return profile.parent / f"{profile.name}-{generation}{_LINK_SUFFIX}"


def _link_ids(profile: Path) -> list[int]:
    """Return every ``<profile>-<n>-link`` generation in the profile directory."""
    directory = profile.parent
    prefix = f"{profile.name}-"
    try:
        entries = list(directory.iterdir())
    except OSError:
        return []
    ids = []
    for entry in entries:
        name = entry.name
        if not (name.startswith(prefix) and name.endswith(_LINK_SUFFIX)):
            continue
        number = name[len(prefix) : -len(_LINK_SUFFIX)]
        if number.isdigit() and int(number) > 0:
            ids.append(int(number))
    return sorted(ids)


def _profile_present(profile: Path) -> bool:
    return os.path.lexists(profile) or bool(_link_ids(profile))


def _link_target(path: Path) -> str:
    """Return a link's target even when the target no longer exists."""
    try:
        target = os.readlink(path)
    except OSError:
        target = ""
    if target:
        if not os.path.isabs(target):
            target = os.path.join(os.path.dirname(path), target)
        return os.path.normpath(target)
    try:
        return os.path.realpath(path)
    except OSError:
        return ""


def _same_target(first: Path, second: Path) -> bool:
    """Compare two profile links after following every symlink in the chain.

    Nix writes the profile symlink relative to its generation link
    (``home-manager -> home-manager-11-link``), so a plain ``readlink``
    comparison would never mark the current generation.
    """
    try:
        first_target = os.path.realpath(first)
        second_target = os.path.realpath(second)
    except OSError:
        return False
    if not first_target or not second_target:
        return False
    return os.path.normpath(first_target) == os.path.normpath(second_target)


def _record(
    profile: Path,
    generation: int,
    date_text: str = "",
    current_marker: bool = False,
) -> dict[str, object]:
    link = _generation_link(profile, generation)
    if not date_text:
        try:
            date_text = datetime.fromtimestamp(link.lstat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except (OSError, OverflowError, ValueError):
            date_text = ""
    return {
        "id": generation,
        "date": date_text,
        "path": _link_target(link),
        "current": current_marker or _same_target(profile, link),
    }


def _parse_generations(output: str, profile: Path) -> list[dict[str, object]]:
    records = []
    seen = set()
    for line in output.splitlines():
        match = _LIST_LINE.match(line)
        if not match:
            continue
        generation = int(match.group("id"))
        if generation <= 0 or generation in seen:
            continue
        seen.add(generation)
        records.append(
            _record(
                profile,
                generation,
                f"{match.group('date')} {match.group('time')}",
                "current" in match.group("tail").casefold(),
            )
        )
    return records


def _list_with_nix_env(profile: Path) -> list[dict[str, object]]:
    nix_env = _nix_env_binary()
    if not nix_env:
        return []
    try:
        result = subprocess.run(
            [nix_env, "--profile", str(profile), "--list-generations"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return _parse_generations(result.stdout, profile)


def _list_from_links(profile: Path) -> list[dict[str, object]]:
    return [_record(profile, generation) for generation in _link_ids(profile)]


def list_scope(scope: str) -> list[dict[str, object]]:
    """Return this scope's generations, newest first.

    ``nix-env`` supplies the timestamps and current marker; the profile links
    are the fallback when ``nix-env`` is unavailable or its output cannot be
    parsed. A scope without a profile (or generation links) is simply empty.
    """
    profile = _profile_path(scope)
    if not _profile_present(profile):
        return []
    records = _list_with_nix_env(profile)
    if not records:
        records = _list_from_links(profile)
    records.sort(key=lambda record: int(record["id"]), reverse=True)
    return records


def available_scopes() -> tuple[str, ...]:
    """Scopes LinuxToys can manage on this host, Home Manager first."""
    try:
        if not nix_catalog.enabled():
            return ()
    except Exception:
        return ()
    scopes = []
    if _profile_present(home_profile_path()):
        scopes.append(HOME_SCOPE)
    try:
        is_nixos = nix_catalog.is_nixos()
    except Exception:
        is_nixos = False
    if is_nixos and _profile_present(system_profile_path()):
        scopes.append(SYSTEM_SCOPE)
    return tuple(scopes)


def scan() -> dict[str, dict[str, object]]:
    """Read every available scope, isolating a failure to its own page."""
    result: dict[str, dict[str, object]] = {}
    for scope in available_scopes():
        try:
            result[scope] = {"generations": list_scope(scope), "error": ""}
        except Exception as error:  # surface the exact read failure
            result[scope] = {"generations": [], "error": str(error)}
    return result


def _generation_number(generation: object) -> int:
    text = str(generation).strip()
    try:
        number = int(text)
    except (TypeError, ValueError) as error:
        raise GenerationError("Invalid Nix generation") from error
    if number <= 0 or str(number) != text:
        raise GenerationError("Invalid Nix generation")
    return number


def _clean_label(value: object, fallback: str) -> str:
    text = _CONTROL.sub(" ", str(value or "")).strip()
    return text or fallback


def _materialize(
    scope: str,
    generation: object,
    action: str,
    name: object = "",
    description: object = "",
) -> dict[str, object]:
    if scope not in SCOPES:
        raise GenerationError("Invalid Nix generation scope")
    number = _generation_number(generation)
    if action not in ("activate", "delete"):
        raise GenerationError("Invalid Nix generation action")
    default_name = (
        f"Activate Nix generation {number}"
        if action == "activate"
        else f"Delete Nix generation {number}"
    )
    default_description = (
        "Activate this Nix generation and rebuild the running configuration from it."
        if action == "activate"
        else "Delete this Nix generation record."
    )
    display_name = _clean_label(name, default_name)
    display_description = _clean_label(description, default_description)
    function = (
        "nix_generation_switch" if action == "activate"
        else "nix_generation_delete"
    )
    script_fd, script_path = tempfile.mkstemp(
        prefix="linuxtoys-nix-generation-", suffix=".sh"
    )
    with os.fdopen(script_fd, "w", encoding="utf-8") as handle:
        handle.write(
            "#!/usr/bin/env bash\n"
            f"# name: {display_name}\n"
            f"# description: {display_description}\n"
            "# icon: nix.svg\n"
            "# architectures: x86_64, aarch64\n"
            "set -eo pipefail\n"
            'source "$SCRIPT_DIR/libs/linuxtoys.bash"\n'
            'source "$SCRIPT_DIR/libs/nixsys.bash"\n'
            f"{function} {shlex.quote(scope)} {number}\n"
        )
    os.chmod(script_path, 0o700)
    info: dict[str, object] = {
        "name": display_name,
        "description": display_description,
        "icon": "nix.svg",
        "path": script_path,
        "version": "",
        "is_script": True,
        "is_subcategory": False,
        "revert": "no",
        "reboot": "no",
        "repo": "",
    }
    if action == "delete":
        info["cleanup_path"] = script_path
    return info


def materialize_switch(
    scope: str,
    generation: object,
    name: object = "",
    description: object = "",
) -> dict[str, object]:
    """Create the terminal script that activates one generation."""
    return _materialize(scope, generation, "activate", name, description)


def materialize_delete(
    scope: str,
    generation: object,
    name: object = "",
    description: object = "",
) -> dict[str, object]:
    """Create the terminal script that deletes one generation record."""
    return _materialize(scope, generation, "delete", name, description)
