#!/usr/bin/env python3
"""Prepare/check a reviewed local snapshot. Never fetch, publish or promote ISAs.

After reviewing source and refreshing existing route digests, run --write, review
the generated lock/manifest, then --check. --export NEW_DIR and --artifact-dir
OUTPUT_ROOT prepare local review files only. No git/network operations exist.
"""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "p3"))
from app import script_compat as compat  # noqa: E402

MAX_PAYLOAD = 64 * 1024 * 1024
ARTIFACT_FILES = frozenset({"scripts.tar", "validation.json", "SHA256SUMS"})


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate manifest key: {key}")
        result[key] = value
    return result


def _regular_bytes(path: Path, maximum: int) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
        raise ValueError(f"Expected a bounded regular file: {path}")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError(f"File type changed during preparation: {path}")
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError(f"File exceeds preparation limit: {path}")
    return data


def approved_files(tree: Path) -> dict[str, bytes]:
    """Fresh exact-byte snapshot under the existing client authority.

    Export is stricter than runtime mirror validation: no .git, README/LICENSE
    exception, extra/empty directory, symlink or special file enters an artifact.
    """
    if tree.is_symlink() or not tree.is_dir():
        raise ValueError(f"Expected a regular scripts directory: {tree}")
    raw = _regular_bytes(tree / compat.MANIFEST, 1024 * 1024)
    manifest = json.loads(raw, object_pairs_hook=_unique_object)
    if (
        not isinstance(manifest, dict)
        or set(manifest)
        != {"schema", "requires_api", "architecture_policy_sha256", "files"}
        or type(manifest["schema"]) is not int
        or type(manifest["requires_api"]) is not int
        or not isinstance(manifest["files"], dict)
        or not manifest["files"]
        or len(manifest["files"]) > 10000
    ):
        raise ValueError("Malformed script manifest")
    expected_names = {compat.MANIFEST, *manifest["files"]}
    allowed_dirs: set[str] = set()
    for name, sha in manifest["files"].items():
        path = PurePosixPath(name)
        if (
            not name
            or path.is_absolute()
            or path.as_posix() != name
            or ".." in path.parts
            or "\\" in name
            or any(ord(char) < 32 or ord(char) == 127 for char in name)
            or name in {compat.MANIFEST, ".incomplete", *compat.IGNORED_FILES}
            or any(part.casefold() == ".git" for part in path.parts)
            or not isinstance(sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", sha) is None
        ):
            raise ValueError(f"Unsafe or malformed manifest member: {name!r}")
        allowed_dirs.update(
            p.as_posix() for p in path.parents if p != PurePosixPath(".")
        )
    if allowed_dirs & expected_names:
        raise ValueError("Manifest file/directory collision")
    portable_names: dict[str, str] = {}
    for name in expected_names | allowed_dirs:
        other = portable_names.setdefault(name.casefold(), name)
        if other != name:
            raise ValueError(f"Manifest path case collision: {other!r}, {name!r}")
    seen: set[str] = set()

    def scan(directory: Path) -> None:
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                name = path.relative_to(tree).as_posix()
                mode = entry.stat(follow_symlinks=False).st_mode
                if stat.S_ISDIR(mode) and name in allowed_dirs:
                    scan(path)
                elif stat.S_ISREG(mode) and name in expected_names:
                    seen.add(name)
                else:
                    raise ValueError(f"Unexpected file, directory or file type: {path}")

    scan(tree)
    if seen != expected_names:
        raise ValueError(f"Missing manifest member(s): {sorted(expected_names - seen)}")
    # M3A remains the approval/API/architecture-policy authority.
    compat.require_bundle(tree)
    result = {compat.MANIFEST: raw}
    total = len(raw)
    for name, sha in sorted(manifest["files"].items()):
        data = _regular_bytes(tree / name, min(16 * 1024 * 1024, MAX_PAYLOAD - total))
        if compat.digest(data) != sha:
            raise ValueError(f"Content changed during preparation: {name}")
        if name.endswith(".sh"):
            compat.require_api(data.decode("utf-8"))
        result[name] = data
        total += len(data)
    if _regular_bytes(tree / compat.MANIFEST, 1024 * 1024) != raw:
        raise ValueError("Manifest changed during preparation")
    return result


def _mode(name: str) -> int:
    return 0o755 if name.endswith(".sh") else 0o644


def artifact_bytes(files: dict[str, bytes]) -> dict[str, bytes]:
    """Canonical POSIX tar and deterministic report; no clock, host or Git data."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo("scripts/" + name)
            info.size = len(data)
            info.mode = _mode(name)
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(data))
    tar = buffer.getvalue()
    manifest = json.loads(files[compat.MANIFEST])
    report = {
        "schema": 1,
        "status": "validated",
        "publication": False,
        "revision": compat.digest(files[compat.MANIFEST]),
        "script_api": compat.SCRIPT_API,
        "architecture_policy_sha256": manifest["architecture_policy_sha256"],
        "manifest_files": len(files) - 1,
        "archive_files": len(files),
        "payload_bytes": sum(len(data) for data in files.values()),
        "archive": "scripts.tar",
        "archive_sha256": compat.digest(tar),
        "archive_format": "POSIX pax; sorted regular files; uid/gid/mtime=0; .sh=0755, other=0644",
        "checks": [
            "client-approved revision",
            "script API",
            "architecture policy",
            "exact inventory including hidden files",
            "regular files only",
            "fresh raw-byte digests",
            "bounded payload",
        ],
    }
    payload = {
        "scripts.tar": tar,
        "validation.json": (json.dumps(report, indent=2) + "\n").encode(),
    }
    payload["SHA256SUMS"] = "".join(
        f"{compat.digest(data)}  {name}\n" for name, data in sorted(payload.items())
    ).encode()
    return payload


def _outside_source(destination: Path, tree: Path) -> Path:
    if destination.is_symlink():
        raise ValueError("Output destination must not be a symlink")
    destination = destination.resolve()
    if destination.is_relative_to(tree.resolve()):
        raise ValueError("Output destination must be outside the scripts source")
    return destination


def _write_new_directory(destination: Path, files: dict[str, bytes]) -> None:
    """Exclusively reserve a revision; failed exports never report completion."""
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        # A publisher/reviewer must refuse a directory retaining this marker.
        (destination / ".incomplete").touch(exist_ok=False)
        for name, data in sorted(files.items()):
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
            target.chmod(_mode(name))
            if _regular_bytes(target, len(data)) != data:
                raise ValueError(f"Export readback mismatch: {name}")
        (destination / ".incomplete").unlink()
    except BaseException:
        # Exclusively created by us, never an existing revision.
        shutil.rmtree(destination)
        raise


def export_tree(tree: Path, destination: Path) -> None:
    destination = _outside_source(destination, tree)
    files = approved_files(tree)
    _write_new_directory(destination, files)
    compat.require_bundle(destination)


def prepare_artifact(tree: Path, output_root: Path) -> Path:
    output_root = _outside_source(output_root, tree)
    files = approved_files(tree)
    revision = compat.digest(files[compat.MANIFEST])
    payload = artifact_bytes(files)
    output_root.mkdir(parents=True, exist_ok=True)
    destination = output_root / revision
    _write_new_directory(destination, payload)
    return destination


def verify_artifact(tree: Path, destination: Path) -> None:
    """Reconstruct expected bytes from the trusted client, not artifact claims."""
    files = approved_files(tree)
    expected = artifact_bytes(files)
    if (
        destination.is_symlink()
        or not destination.is_dir()
        or destination.name != compat.digest(files[compat.MANIFEST])
        or {p.name for p in destination.iterdir()} != ARTIFACT_FILES
    ):
        raise ValueError("Unexpected, incomplete or differently addressed artifact")
    for name, data in expected.items():
        if _regular_bytes(destination / name, len(data)) != data:
            raise ValueError(f"Artifact integrity failure: {name}")


def expected() -> tuple[bytes, bytes]:
    tree = ROOT / "p3/scripts"
    policy = json.loads(compat.POLICY_PATH.read_bytes())
    for sha, declaration in policy["scripts"].items():
        path = tree / declaration["path"]
        body_bytes = _regular_bytes(path, 16 * 1024 * 1024)
        if compat.digest(body_bytes) != sha:
            raise ValueError(f"Review/refresh architecture route first: {path}")
        if "aarch64" in declaration["architectures"]:
            body = body_bytes.decode("utf-8")
            guard = 'python3 "$SCRIPT_DIR/app/script_compat.py" "${BASH_SOURCE[0]}" || exit 1'
            if "# requires-script-api: 1" not in body or guard not in body:
                raise ValueError(f"Missing early client API guard: {path}")
            if body.index(guard) > body.index('source "$SCRIPT_DIR/libs/'):
                raise ValueError(
                    f"Client API guard must precede library loading: {path}"
                )
    manifest = {
        "schema": 1,
        "requires_api": compat.SCRIPT_API,
        "architecture_policy_sha256": compat.digest(compat.POLICY_PATH.read_bytes()),
        "files": {
            name: compat.digest(_regular_bytes(path, 16 * 1024 * 1024))
            for name, path in sorted(compat.inventory(tree).items())
        },
    }
    raw = (json.dumps(manifest, indent=2) + "\n").encode()
    revision = compat.digest(raw)
    lock = {
        "schema": 1,
        "script_api": compat.SCRIPT_API,
        "preferred_revision": revision,
        "accepted_revisions": [revision],
    }
    return raw, (json.dumps(lock, indent=2) + "\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--export", type=Path, metavar="NEW_DIR")
    output.add_argument("--artifact-dir", type=Path, metavar="OUTPUT_ROOT")
    output.add_argument("--verify-artifact", type=Path, metavar="REVISION_DIR")
    args = parser.parse_args()
    if args.write and (args.export or args.artifact_dir or args.verify_artifact):
        parser.error(
            "Approval writing and artifact preparation must be separate review steps"
        )
    manifest = ROOT / "p3/scripts" / compat.MANIFEST
    # Check untrusted file types/metadata before the legacy approval generator.
    # In particular, never let a declared FIFO reach an ordinary read_bytes().
    if args.check:
        approved_files(manifest.parent)
    raw, lock = expected()
    if args.write:
        manifest.write_bytes(raw)
        compat.LOCK_PATH.write_bytes(lock)
    if manifest.read_bytes() != raw or compat.LOCK_PATH.read_bytes() != lock:
        raise SystemExit(
            "Unreviewed source/lock changes; prepare and review a new revision"
        )
    compat.require_bundle(manifest.parent)
    if args.export:
        export_tree(manifest.parent, args.export)
    elif args.artifact_dir:
        destination = prepare_artifact(manifest.parent, args.artifact_dir)
        print(f"Local review artifact: {destination}")
    elif args.verify_artifact:
        verify_artifact(manifest.parent, args.verify_artifact)
        print("Artifact verified against the installed client approval")
    else:
        approved_files(manifest.parent)
    print(f"Approved revision: {compat.digest(raw)}")
    print(f"Immutable rollout tag: {compat.preferred_tag()}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Script preparation refused: {exc}") from exc
