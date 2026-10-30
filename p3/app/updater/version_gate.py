"""Script-run gate for outdated LinuxToys installations.

LinuxToys refuses to run scripts when the installed release is more than
``GATE_GRACE_RELEASES`` published releases behind the newest published
release (grace means "you may ignore this many"; being more out of date
than that blocks scripts). Every published tag counts, so frequent patch
releases tighten the window quickly.

The gate follows the self-update policy from ``update_helper`` and stays
inactive where the app cannot update itself: developer mode, GregOS
(updates arrive with the system image) and repository-owned installs
(PPA/Copr/git checkout).

Data path: a background thread fetches the published release list
(GitHub first, Gitea fallback, mirroring ``_get_latest_version``) and
stores it in the LinuxToys cache directory. Checks only read the cache:
script-run handlers run on the UI main loop and must never wait on the
network. When no usable data is available, checks fail open and the
refresh thread keeps trying (with backoff), so a broken release service
never bricks script execution.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

from .. import compat

GATE_GRACE_RELEASES = 2
"""Published releases newer than the installed one that still run scripts.

"More than two releases out of date" = blocked beyond this count."""

_CACHE_TTL_SECONDS = 6 * 60 * 60
_RELEASE_PAGE_SIZE = 25
_FETCH_BACKOFF_SECONDS = 60
_REPO_OWNER = "psygreg"
_REPO_NAME = "linuxtoys"

_GITHUB_RELEASES_URL = (
    f"https://api.github.com/repos/{_REPO_OWNER}/{_REPO_NAME}"
    f"/releases?per_page={_RELEASE_PAGE_SIZE}"
)
_GITEA_RELEASES_URL = (
    f"https://git.linux.toys/api/v1/repos/{_REPO_OWNER}/{_REPO_NAME}"
    f"/releases?limit={_RELEASE_PAGE_SIZE}"
)

_LOCK = threading.Lock()
_MEM_CACHE: dict = {}
_FETCHING = False
_LAST_FAILED_AT = 0.0

_current_version_cache: str | None = None
_applicable_cache = None


def parse_release_version(tag) -> tuple | None:
    """Parse a release tag into a comparable integer tuple.

    Handles the repository's plain numeric tags ("7.7.6") plus the optional
    leading "v". Anything unparseable (suffixes, exception tags) returns
    None so callers cannot prove the release is newer and must fail open.
    """
    text = str(tag or "").strip()
    if text[:1] in ("v", "V"):
        text = text[1:]
    parts = []
    for chunk in text.split("."):
        chunk = chunk.strip()
        if not chunk.isdigit():
            break
        parts.append(int(chunk))
        if len(parts) >= 4:
            break
    return tuple(parts) if parts else None


def get_current_version_cached() -> str:
    """Resolve the running LinuxToys version once per process."""
    global _current_version_cache
    if _current_version_cache is None:
        from .update_helper import get_current_version

        _current_version_cache = get_current_version()
    return _current_version_cache


def is_gate_applicable() -> bool:
    """Whether the outdated-version gate is active on this host.

    Mirrors ``UpdateHelper._update_available``: hosts that cannot
    self-update through the app get no gate either, because "update now"
    would point at a channel that does not own the installation. Developer
    mode also opts out entirely.
    """
    global _applicable_cache
    if _applicable_cache is None:
        applicable = False
        try:
            from .. import dev_mode
            from .update_helper import is_from_repository

            applicable = not (
                dev_mode.is_dev_mode_enabled()
                or compat.self_updates_disabled()
                or is_from_repository()
            )
        except Exception:
            # A failed environment probing must not silently hard-block
            # every script on the system.
            applicable = False
        _applicable_cache = applicable
    return _applicable_cache


def _cache_path() -> str:
    try:
        return os.path.join(compat.get_linuxtoys_cache_dir(), "update-state.json")
    except Exception:
        return ""


def _read_cache_state() -> dict | None:
    path = _cache_path()
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as state_file:
            data = json.load(state_file)
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    releases = data.get("releases")
    fetched_at = data.get("fetched_at")
    if not isinstance(releases, list) or not releases:
        return None
    try:
        fetched_at = float(fetched_at)
    except (TypeError, ValueError):
        fetched_at = 0.0
    return {"releases": releases, "fetched_at": fetched_at}


def _write_cache_state(state: dict) -> None:
    path = _cache_path()
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as state_file:
            json.dump(state, state_file)
        os.replace(tmp_path, path)
    except OSError:
        pass


def _load_state() -> tuple[list | None, float]:
    """Return the freshest cached release list: memory first, then disk."""
    with _LOCK:
        if _MEM_CACHE.get("releases"):
            return list(_MEM_CACHE["releases"]), float(
                _MEM_CACHE.get("fetched_at") or 0.0
            )
    disk_state = _read_cache_state()
    if disk_state is not None:
        return disk_state["releases"], disk_state["fetched_at"]
    return None, 0.0


def _fetch_list_from_api(api_url: str, source_name: str) -> list | None:
    """Fetch the release list from one API and normalize it for the cache."""
    try:
        request = urllib.request.Request(api_url)
        request.add_header("User-Agent", "LinuxToys-UpdateChecker/1.0")
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        json.JSONDecodeError,
        UnicodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"Release list fetch from {source_name} failed: {exc}")
        return None

    if not isinstance(data, list):
        return None

    releases = []
    for entry in data:
        if not isinstance(entry, dict) or entry.get("draft"):
            continue
        tag_name = str(entry.get("tag_name") or "").strip().lstrip("v")
        if not tag_name:
            continue
        releases.append(
            {"tag_name": tag_name, "body": str(entry.get("body") or "")[:8000]}
        )
    return releases or None


def _fetch_release_list() -> list | None:
    """Fetch the published release list (newest first), GitHub then Gitea."""
    for api_url, source_name in (
        (_GITHUB_RELEASES_URL, "GitHub"),
        (_GITEA_RELEASES_URL, "Gitea"),
    ):
        releases = _fetch_list_from_api(api_url, source_name)
        if releases:
            return releases
    return None


def refresh(force: bool = False) -> None:
    """Ensure the cached release list is fresh; fetch off-thread if needed.

    Never blocks the caller: the worker runs in a daemon thread, so both
    the GUI startup check and CLI launches can call this freely.
    """
    if not is_gate_applicable():
        return

    # Freshness probes run outside the lock: _load_state() takes it too, and
    # threading.Lock is not re-entrant (a nested acquire would deadlock the
    # caller's thread).
    if not force:
        releases, fetched_at = _load_state()
        if releases is not None and (
            time.time() - fetched_at < _CACHE_TTL_SECONDS
        ):
            return

    global _FETCHING
    with _LOCK:
        if _FETCHING:
            return
        if not force and time.time() - _LAST_FAILED_AT < _FETCH_BACKOFF_SECONDS:
            return
        _FETCHING = True

    threading.Thread(
        target=_refresh_worker, daemon=True, name="linuxtoys-release-list"
    ).start()


def _refresh_worker() -> None:
    global _FETCHING, _LAST_FAILED_AT
    try:
        releases = _fetch_release_list()
        if releases:
            state = {"releases": releases, "fetched_at": time.time()}
            _write_cache_state(state)
            with _LOCK:
                _MEM_CACHE["releases"] = releases
                _MEM_CACHE["fetched_at"] = state["fetched_at"]
        else:
            # Keep any older cache on failure and pace the retries.
            with _LOCK:
                _LAST_FAILED_AT = time.time()
    finally:
        with _LOCK:
            _FETCHING = False


def count_newer_releases(current: str, releases) -> int:
    """Count published releases strictly newer than *current*."""
    current_tuple = parse_release_version(current)
    if not current_tuple:
        return 0
    count = 0
    for entry in releases or ():
        if not isinstance(entry, dict):
            continue
        release_tuple = parse_release_version(entry.get("tag_name"))
        if release_tuple and release_tuple > current_tuple:
            count += 1
    return count


def check() -> dict:
    """Decide whether script runs are refused. Non-blocking; fails open.

    Returns a dict with:
        applicable: the gate is active on this host at all
        fetched: usable release data exists
        blocked: the run must be refused
        current/latest: installed and newest published versions
        behind: published releases newer than the installed one
        latest_body: release notes of the newest published release
        reason: machine-readable failure note when nothing was fetched
    """
    current = get_current_version_cached()
    result = {
        "applicable": False,
        "fetched": False,
        "blocked": False,
        "current": current,
        "latest": "",
        "behind": 0,
        "latest_body": "",
        "reason": "",
    }
    if not is_gate_applicable():
        return result
    result["applicable"] = True

    releases, fetched_at = _load_state()
    if releases is None:
        result["reason"] = "no-release-data"
        # Warm the cache so the next attempt (or the next script run) has
        # data instead of silently failing open forever.
        refresh()
        return result

    if time.time() - fetched_at >= _CACHE_TTL_SECONDS:
        # Stale-but-present data still decides this run (understate rather
        # than stall the UI); refresh for the next attempt.
        refresh()

    latest = releases[0].get("tag_name", "") if releases else ""
    result.update(
        {
            "fetched": True,
            "latest": latest,
            "behind": count_newer_releases(current, releases),
            "latest_body": (
                releases[0].get("body", "") if isinstance(releases[0], dict) else ""
            ),
        }
    )
    result["blocked"] = result["behind"] > GATE_GRACE_RELEASES
    return result


def refusal_message(gate: dict) -> str | None:
    """Plain-text refusal explanation for CLI surfaces; None when allowed."""
    if not gate.get("blocked"):
        return None
    current = gate.get("current") or "unknown"
    latest = gate.get("latest") or "unknown"
    return (
        f"This LinuxToys version ({current}) is {gate.get('behind', 0)} releases "
        f"behind the latest published version ({latest}). Scripts are disabled "
        "until LinuxToys is updated. Run 'linuxtoys update' to install it."
    )

