"""Client-owned, exact-byte script revision approval (no network or GUI imports).

A repository, its manifest and its architecture headers cannot approve themselves.
The installed client pins manifest digests and its architecture policy separately.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys

if not __package__:  # Early shell-script guard, including older clients.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.architecture import ArchitectureError

SCRIPT_API = 1
MANIFEST = ".linuxtoys-scripts.json"
APP_DIR = Path(__file__).resolve().parent
LOCK_PATH = APP_DIR / "script-revisions.json"
POLICY_PATH = APP_DIR / "architecture-routes.json"
# Remote repositories also carry these documentation files. They are never code.
IGNORED_FILES = frozenset({"README.md", "LICENSE"})
_verified: dict[str, tuple[object, dict]] = {}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def client_revisions() -> dict:
    lock = json.loads(LOCK_PATH.read_bytes())
    if (
        not isinstance(lock, dict)
        or lock.get("schema") != 1
        or lock.get("script_api") != SCRIPT_API
        or not isinstance(lock.get("accepted_revisions"), list)
        or lock.get("preferred_revision") not in lock["accepted_revisions"]
        or not all(
            isinstance(x, str)
            and len(x) == 64
            and all(c in "0123456789abcdef" for c in x)
            for x in lock["accepted_revisions"]
        )
    ):
        raise ArchitectureError(
            "Invalid client script revision lock; repair the client"
        )
    return lock


def preferred_tag() -> str:
    return (
        f"linuxtoys-script-api-{SCRIPT_API}-{client_revisions()['preferred_revision']}"
    )


def require_api(text: str) -> None:
    """Reject explicit newer/older/conflicting script capability requirements."""
    requirements = re.findall(r"(?m)^# requires-script-api:\s*(.*)$", text)
    if requirements and any(value.strip() != str(SCRIPT_API) for value in requirements):
        raise ArchitectureError(
            f"Script requires a different client script API (installed: {SCRIPT_API})"
        )


def inventory(root: Path) -> dict[str, Path]:
    """Enumerate regular source files only; reject symlinks and special files."""
    if root.is_symlink() or not root.is_dir():
        raise ArchitectureError(f"Invalid scripts tree: {root}")
    files = {}

    def unreadable(error: OSError) -> None:
        raise error

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=unreadable):
        base = Path(directory)
        if base == root:
            dirs[:] = [name for name in dirs if name != ".git"]
        for name in dirs + names:
            path = base / name
            if path.is_symlink() or not (path.is_dir() or path.is_file()):
                raise ArchitectureError(f"Non-regular scripts member: {path}")
        for name in names:
            path = base / name
            relative = path.relative_to(root).as_posix()
            if relative not in {MANIFEST, *IGNORED_FILES}:
                files[relative] = path
                if len(files) > 10000:
                    raise ArchitectureError(
                        "Scripts inventory exceeds the safety limit"
                    )
    return files


def require_bundle(root: str | Path) -> dict:
    """Validate the complete tree before selection/promotion; cache by file stats.

    Hashes cover raw bytes, including line endings. The fingerprint includes the
    complete inventory and ctime, so partial updates invalidate a cached check.
    """
    root = Path(root).absolute()
    try:
        manifest_path = root / MANIFEST
        if manifest_path.is_symlink() or manifest_path.stat().st_size > 1024 * 1024:
            raise ArchitectureError("Invalid scripts manifest")
        raw = manifest_path.read_bytes()
        revision = digest(raw)
        lock = client_revisions()
        if revision not in lock["accepted_revisions"]:
            raise ArchitectureError(
                f"Unqualified scripts revision {revision}; keep the approved bundle "
                "or install a client that explicitly approves this revision"
            )
        manifest = json.loads(raw)
        if (
            not isinstance(manifest, dict)
            or manifest.get("schema") != 1
            or manifest.get("requires_api") != SCRIPT_API
            or manifest.get("architecture_policy_sha256")
            != digest(POLICY_PATH.read_bytes())
            or not isinstance(manifest.get("files"), dict)
        ):
            raise ArchitectureError(
                "Scripts require a different client API/architecture policy"
            )
        files = inventory(root)
        if set(files) != set(manifest["files"]):
            raise ArchitectureError("Incomplete or unexpected scripts inventory")
        fingerprint = (
            revision,
            tuple(
                (name, (s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns))
                for name, path in sorted(files.items())
                for s in [path.stat()]
            ),
        )
        previous = _verified.get(str(root))
        if previous and previous[0] == fingerprint:
            return previous[1]
        for name, path in files.items():
            if (
                path.stat().st_size > 16 * 1024 * 1024
                or digest(path.read_bytes()) != manifest["files"][name]
            ):
                raise ArchitectureError(f"Scripts integrity failure: {name}")
        # Staging paths are unique: bound retained metadata across repeated syncs.
        if str(root) not in _verified and len(_verified) >= 8:
            oldest = next(iter(_verified), None)
            if oldest is not None:
                _verified.pop(oldest, None)
        _verified[str(root)] = (fingerprint, manifest)
        return manifest
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ArchitectureError(
            f"Scripts compatibility check failed for {root}: {exc}"
        ) from exc


def require_managed_script(path: str | Path) -> None:
    """Gate managed content; local generated scripts still use architecture policy.

    Recognize managed roots even if their manifest was removed. A remote header
    must never downgrade a failed bundle check to local-script permission.
    """
    path = Path(path).absolute()
    from app import git_scripts_manager

    roots = [
        Path(git_scripts_manager.get_bundled_scripts_dir()).absolute(),
        Path(git_scripts_manager.GIT_SCRIPTS_CACHE_DIR).absolute(),
    ]
    roots += [p for p in path.parents if (p / MANIFEST).exists()]
    for root in roots:
        if path.is_relative_to(root):
            manifest = require_bundle(root)
            name = path.relative_to(root).as_posix()
            if name not in manifest["files"] or path.is_symlink():
                raise ArchitectureError(
                    f"Script is not an approved bundle member: {path}"
                )
            if digest(path.read_bytes()) != manifest["files"][name]:
                raise ArchitectureError(
                    f"Script changed after bundle validation: {path}"
                )
            return


def main() -> int:
    from app.architecture import require_script_path

    try:
        if len(sys.argv) != 2:
            raise ArchitectureError("Usage: script_compat.py SCRIPT")
        path = Path(sys.argv[1]).absolute()
        # API-requiring routes may only execute as original approved members.
        root = next((p for p in path.parents if (p / MANIFEST).is_file()), None)
        if root is None:
            raise ArchitectureError(
                "This script requires an approved script bundle and client API 1"
            )
        require_bundle(root)
        require_script_path(path)
        return 0
    except (OSError, ValueError) as exc:
        print(f"LinuxToys: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
