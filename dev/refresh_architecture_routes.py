#!/usr/bin/env python3
"""Refresh reviewed script digests and catalog ISA declarations after review.

Review the source changes first. For scripts, this command only refreshes
existing paths, preserving architecture lists — never promote an ISA by hand.
For catalog entries it recomputes the ISA declarations from reviewed evidence:

- a list record may declare ``architectures`` explicitly;
- asset-backed entries (git/bin/tar/url/make and the native package ones)
  stay x86_64-only unless git-db.json proves installable aarch64 assets:
  an asset without explicit architecture evidence, a single-binary asset or
  a tarball asset is presumed x86_64-only.

Only rows whose record still matches an approved declaration digest are
updated; edited records keep failing closed until re-approved.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Release-asset kinds each entry type can actually install from. Mirrors the
# git-release matcher: bundle kinds count for git entries, tarballs only for
# tar entries, and bin entries need their exact declared asset.
_GIT_KINDS = {"appimage", "flatpak", "snap", "pacman", "rpm", "deb", "eopkg"}


def _canonical_record_digest(record: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def _refresh_scripts(root: Path, policy: dict) -> None:
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


def _load_git_db(root: Path) -> dict:
    path = root / "p3/scripts/git-db.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    repositories = data.get("repositories") if isinstance(data, dict) else None
    return repositories if isinstance(repositories, dict) else {}


def _asset_architectures(asset: dict) -> set[str]:
    """Explicit architecture evidence of one cached asset; unlabelled = none."""
    values = asset.get("architectures")
    if not isinstance(values, list):
        return set()
    return {
        value.strip().lower()
        for value in values
        if isinstance(value, str) and value.strip().lower() in ("x86_64", "aarch64")
    }


def _proven_architectures(record: dict, git_db: dict) -> set[str]:
    """ISAs a repository listing is explicitly proven for, beyond x86_64.

    Assets without architecture evidence, single-binary assets and tarball
    assets are presumed x86_64-only; only explicit aarch64 evidence grants the
    ISA, and only through an installable kind for the entry's type.
    """
    proven: set[str] = set()
    entry_type = str(record.get("type") or "git")
    repo = str(record.get("repo") or "")
    record_data = git_db.get(repo)
    if not isinstance(record_data, dict):
        return proven
    assets = record_data.get("assets")
    if not isinstance(assets, list):
        return proven
    if entry_type == "git":
        wanted_kinds = _GIT_KINDS
    elif entry_type == "tar":
        wanted_kinds = {"tar"}
    elif entry_type == "bin":
        wanted_kinds = None  # exact declared asset only
    else:
        return proven
    wanted_asset = str(record.get("package-name") or "").strip()
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if wanted_kinds is None:
            if str(asset.get("name") or "") != wanted_asset:
                continue
        elif asset.get("kind") not in wanted_kinds:
            continue
        if "aarch64" in _asset_architectures(asset):
            proven.add("aarch64")
    return proven


def _record_architectures(record: dict) -> list[str] | None:
    """Explicit per-record declaration, validated against the supported ISAs."""
    values = record.get("architectures")
    if values is None:
        return None
    if (
        isinstance(values, list)
        and values
        and all(
            isinstance(value, str) and value.strip().lower() in ("x86_64", "aarch64")
            for value in values
        )
    ):
        ordered: list[str] = []
        for value in values:
            token = value.strip().lower()
            if token not in ordered:
                ordered.append(token)
        return ordered
    raise SystemExit(
        f"Record {record.get('name')!r} declares invalid architectures: {values!r}"
    )


def _iter_list_records(root: Path):
    """Every repository-list record, in deterministic file order."""
    scripts_dir = root / "p3/scripts"
    paths = []
    repos_json = scripts_dir / "repos.json"
    if repos_json.is_file():
        paths.append(repos_json)
    lists_dir = scripts_dir / "lists"
    if lists_dir.is_dir():
        paths.extend(sorted(lists_dir.rglob("*.json")))
    for path in paths:
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = [data]
        else:
            continue
        for record in records:
            if isinstance(record, dict) and isinstance(record.get("name"), str):
                yield record


def _refresh_catalogs(root: Path, policy: dict) -> None:
    git_db = _load_git_db(root)
    approved: dict[str, list[dict]] = {}
    for record in _iter_list_records(root):
        approved.setdefault(record["name"], []).append(record)

    for name, declaration in policy["catalogs"].items():
        repo = str(declaration.get("repo") or "")
        accepted = declaration.get("declarations")
        if not isinstance(accepted, list):
            continue
        approved_digests = {str(digest) for digest in accepted}
        candidates = [
            record
            for record in approved.get(name, [])
            if str(record.get("repo") or "") == repo
            and _canonical_record_digest(record) in approved_digests
        ]
        if not candidates:
            # Edited or renamed record: the entry stays dead at runtime until
            # it is re-approved; leave the reviewed row untouched.
            continue
        record = candidates[0]
        declared = _record_architectures(record)
        if declared is not None:
            architectures = declared
        else:
            # No declaration: x86_64 by presumption, aarch64 only when the
            # cached release assets explicitly prove an installable ARM build.
            proven = _proven_architectures(record, git_db)
            architectures = ["x86_64"] + sorted(proven - {"x86_64"})
        declaration["architectures"] = architectures


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "p3/app/architecture-routes.json"
    policy = json.loads(path.read_text())
    _refresh_scripts(root, policy)
    _refresh_catalogs(root, policy)
    path.write_text(json.dumps(policy, indent=2) + "\n")


if __name__ == "__main__":
    main()
