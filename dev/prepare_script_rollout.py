#!/usr/bin/env python3
"""Prepare/check a reviewed local snapshot. Never fetch, publish or promote ISAs.

After reviewing source and refreshing existing route digests, run --write, review
the generated lock/manifest, then --check. --export NEW_DIR creates rollout files
only; it deliberately performs no git/network operations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "p3"))
from app import script_compat as compat  # noqa: E402


def expected() -> tuple[bytes, bytes]:
    tree = ROOT / "p3/scripts"
    policy = json.loads(compat.POLICY_PATH.read_bytes())
    for sha, declaration in policy["scripts"].items():
        path = tree / declaration["path"]
        if compat.digest(path.read_bytes()) != sha:
            raise ValueError(f"Review/refresh architecture route first: {path}")
        if "aarch64" in declaration["architectures"]:
            body = path.read_text()
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
            name: compat.digest(path.read_bytes())
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
    parser.add_argument("--export", type=Path, metavar="NEW_DIR")
    args = parser.parse_args()
    raw, lock = expected()
    manifest = ROOT / "p3/scripts" / compat.MANIFEST
    if args.write:
        manifest.write_bytes(raw)
        compat.LOCK_PATH.write_bytes(lock)
    if manifest.read_bytes() != raw or compat.LOCK_PATH.read_bytes() != lock:
        raise SystemExit(
            "Unreviewed source/lock changes; prepare and review a new revision"
        )
    compat.require_bundle(manifest.parent)
    if args.export:
        if args.export.exists():
            raise SystemExit("Export destination must not exist")
        if args.export.resolve().is_relative_to(manifest.parent.resolve()):
            raise SystemExit("Export destination must be outside the scripts source")
        shutil.copytree(manifest.parent, args.export)
        compat.require_bundle(args.export)
    print(f"Approved revision: {compat.digest(raw)}")
    print(f"Immutable rollout tag: {compat.preferred_tag()}")


if __name__ == "__main__":
    main()
