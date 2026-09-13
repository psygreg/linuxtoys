#!/usr/bin/env python3
"""Build p3/scripts/git-db.json from git-type LinuxToys repository entries."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
P3_DIR = ROOT / "p3"
SCRIPTS_DIR = P3_DIR / "scripts"
DB_PATH = SCRIPTS_DIR / "git-db.json"

if str(P3_DIR) not in sys.path:
    sys.path.insert(0, str(P3_DIR))

try:
    from app import repo_parser
except ImportError as error:
    raise SystemExit(f"Unable to import p3/app/repo_parser.py: {error}") from error

ARCH_ALIASES = repo_parser._GIT_ARCH_ALIASES
ARCH_LABELS = sorted(
    (label for aliases in ARCH_ALIASES.values() for label in aliases),
    key=len,
    reverse=True,
)
ARCH_RE = re.compile(
    r"(?<![a-z0-9])(" + "|".join(map(re.escape, ARCH_LABELS)) + r")(?![a-z0-9])"
)


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Index latest-release packages for LinuxToys git repository entries."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="refresh every git-type repository instead of only missing database entries",
    )
    return parser.parse_args()


def _is_git_entry(entry):
    if not isinstance(entry, dict):
        return False
    value = entry.get("type", "git")
    if isinstance(value, str):
        return value.strip().lower() == "git"
    if isinstance(value, dict):
        return any(
            isinstance(item, str) and item.strip().lower() == "git"
            for item in value.values()
        )
    return False


def _tracked_repositories():
    tracked = {}
    for path in repo_parser._get_repo_list_paths(str(SCRIPTS_DIR)):
        for entry in repo_parser._load_json_entries(path):
            if not _is_git_entry(entry):
                continue
            repo = repo_parser._normalize_git_repo_url(entry.get("repo"))
            if not repo:
                # Keep unsupported git URLs visible in the database as failures.
                raw = entry.get("repo")
                if isinstance(raw, str) and raw.strip():
                    repo = raw.strip()
                else:
                    continue
            tracked.setdefault(repo, set()).add(str(entry.get("name", "")).strip())
    return {repo: sorted(name for name in names if name) for repo, names in sorted(tracked.items())}


def _repository_api(repository):
    canonical = repo_parser._normalize_git_repo_url(repository)
    if not canonical:
        raise ValueError("repository is not a supported GitHub, Codeberg, or GitLab project URL")

    parsed = urlsplit(canonical)
    host = (parsed.hostname or "").lower()
    parts = parsed.path.strip("/").split("/")

    if host in ("github.com", "codeberg.org"):
        owner, repo = parts
        base = "https://api.github.com" if host == "github.com" else "https://codeberg.org/api/v1"
        return host, f"{base}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/releases/latest"

    project = quote("/".join(parts), safe="")
    return host, f"https://gitlab.com/api/v4/projects/{project}/releases/permalink/latest"


def _request_json(url, host):
    headers = {
        "Accept": "application/json",
        "User-Agent": "LinuxToys-git-db-builder",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if host == "github.com" and token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"

    request = Request(url, headers=headers)
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def _normalize_release(host, release):
    if not isinstance(release, dict):
        raise ValueError("release API returned invalid data")

    if host != "gitlab.com":
        assets = release.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError("release API returned no asset list")
        if release.get("draft") or release.get("prerelease"):
            raise ValueError("latest release is not a stable published release")
        return [
            {"name": item.get("name", ""), "url": item.get("browser_download_url", "")}
            for item in assets
            if isinstance(item, dict)
        ]

    links = release.get("assets", {}).get("links", []) if isinstance(release.get("assets"), dict) else []
    if not isinstance(links, list):
        raise ValueError("release API returned no asset list")
    return [
        {"name": item.get("name", ""), "url": item.get("direct_asset_url") or item.get("url", "")}
        for item in links
        if isinstance(item, dict)
    ]


def _asset_kind(name):
    lower = name.lower()
    if re.search(r"(?:^|[._-])(?:debug|debuginfo|debugsource|devel|source|src)(?:[._-]|$)", lower):
        return "other"
    if lower.endswith(".appimage"):
        return "appimage"
    if lower.endswith(".flatpak"):
        return "flatpak"
    if lower.endswith((".pacman", ".pkg.tar.zst")):
        return "pacman"
    if lower.endswith(".rpm"):
        return "rpm"
    if lower.endswith(".deb"):
        return "deb"
    if lower.endswith(".eopkg"):
        return "eopkg"
    if lower.endswith((".tar.gz", ".tar.xz")):
        return "tar"
    return "other"


def _asset_architectures(name):
    lower = name.lower()
    detected = set(ARCH_RE.findall(lower))
    canonical = []
    for arch, aliases in ARCH_ALIASES.items():
        if detected.intersection(aliases):
            canonical.append(arch)
    return canonical


def _build_record(repository, names):
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    record = {"names": names, "checked_at": checked_at, "assets": []}

    try:
        host, api = _repository_api(repository)
        release = _request_json(api, host)
        assets = _normalize_release(host, release)

        normalized_assets = []
        for asset in assets:
            name = asset.get("name", "")
            url = asset.get("url", "")
            if not isinstance(name, str) or not name or not isinstance(url, str) or not url:
                continue
            if urlsplit(url).scheme != "https":
                continue
            normalized_assets.append({
                "name": name,
                "kind": _asset_kind(name),
                "architectures": _asset_architectures(name),
            })
        record["assets"] = sorted(normalized_assets, key=lambda item: item["name"].casefold())
    except (ValueError, HTTPError, URLError, OSError, json.JSONDecodeError) as error:
        record["error"] = str(error)

    return record


def _load_database():
    try:
        data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    repositories = data.get("repositories")
    if not isinstance(repositories, dict):
        repositories = {}
    return {"version": 1, "repositories": repositories}


def main():
    args = _parse_args()
    tracked = _tracked_repositories()
    database = _load_database()
    repositories = database["repositories"]

    targets = tracked if args.all else {repo: names for repo, names in tracked.items() if repo not in repositories}
    mode = "all" if args.all else "diff"
    print(f"git-db: mode={mode}, tracked={len(tracked)}, checking={len(targets)}")

    for repository, names in targets.items():
        print(f"  {repository}")
        repositories[repository] = _build_record(repository, names)
        error = repositories[repository].get("error")
        if error:
            print(f"    error: {error}", file=sys.stderr)

    # Names are list metadata, not API data. Keep them current even in diff mode
    # without spending an API request on repositories already present in the DB.
    for repository, names in tracked.items():
        record = repositories.get(repository)
        if isinstance(record, dict):
            record["names"] = names

    database["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(database, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"git-db: wrote {DB_PATH}")


if __name__ == "__main__":
    main()
