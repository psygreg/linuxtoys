#!/usr/bin/env python3
"""Refresh reviewed script digests after code review; never promote an ISA.

Review the source changes first. Add new routes/architectures explicitly to the
policy; this command only refreshes existing paths, preserving architecture lists.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "p3/app/architecture-routes.json"
    policy = json.loads(path.read_text())
    scripts = {}
    for declaration in policy["scripts"].values():
        file = root / "p3/scripts" / declaration["path"]
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if (
            digest in scripts
            and scripts[digest]["architectures"] != declaration["architectures"]
        ):
            raise SystemExit(
                "Identical script bodies have conflicting architecture declarations"
            )
        scripts[digest] = declaration
    policy["scripts"] = scripts
    path.write_text(json.dumps(policy, indent=2) + "\n")


if __name__ == "__main__":
    main()
