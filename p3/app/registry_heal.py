"""Find registry transactions for repository apps that LinuxToys no longer offers.

A repository-list app that is dropped from LinuxToys leaves its registry
transaction behind. The system updater walks git-release transactions and runs
``call_script`` on each one, and ``call_script`` aborts the whole update on a
name nothing offers. The window uses this module to find those transactions so
they can be reverted in the background.

Absence is only trusted when it is proven: every repository listing must parse
(the shared loaders skip unreadable files silently), the AppStream catalog must
be ready (a missing catalog proves nothing), and neither the scripts tree nor
AppStream may offer the app. Any doubt leaves the transaction alone.
"""

import json
import logging
import os
import subprocess
import sys

from . import appstream_cache, registry_utils, repo_parser
from .library_loader import _resolution_scripts_trees

logger = logging.getLogger(__name__)

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROBE_TIMEOUT_SECONDS = 300
_NOT_OFFERED_EXIT = 3
_REMOVAL_TRANSACTION_PREFIXES = ("Remove: ", "Auto-revert: ")


def declared_repo_app_ids(script_dir):
    """Return every repository app id the listings declare, or None if unprovable."""
    trees = _resolution_scripts_trees(script_dir)
    if not trees:
        return None

    declared = set()
    for tree in trees:
        paths = repo_parser._get_repo_list_paths(tree)
        lists_dir = os.path.join(os.path.realpath(tree), "lists") + os.sep
        if not any(os.path.realpath(path).startswith(lists_dir) for path in paths):
            return None
        for path in paths:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, ValueError):
                return None
            if isinstance(data, dict):
                data = [data]
            if not isinstance(data, list):
                return None
            for item in data:
                if (
                    isinstance(item, dict)
                    and "appstream-name" not in item
                    and isinstance(item.get("name"), str)
                ):
                    declared.add(repo_parser._repo_app_id(item["name"]))
    return declared


def _physical_script_present(app_id, scripts_dir):
    """Mirror call_script's `find "$CACHE_DIR" -maxdepth 3 -name "<APP_ID>.sh"`."""
    filename = f"{app_id}.sh"
    for root, dirs, files in os.walk(scripts_dir):
        relative = os.path.relpath(root, scripts_dir)
        depth = 0 if relative == "." else relative.count(os.sep) + 1
        if depth >= 3:
            dirs[:] = []
            continue
        if filename in files:
            return True
    return False


def _appstream_offered(app_id, script_dir):
    """Ask call_script's AppStream resolver in a child process: True, False or None.

    The probe runs out of process so it cannot replace the runtime catalog cache
    the window uses for browsing. Only a clean "not offered" answer counts as
    absence; a failed or timed-out probe is unknown.
    """
    env = dict(os.environ)
    env["SCRIPT_DIR"] = script_dir
    command = [
        sys.executable,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "library_loader.py"),
        "--probe-appstream",
        app_id,
    ]
    try:
        result = subprocess.run(
            command,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("AppStream probe for %s could not run: %s", app_id, exc)
        return None
    if result.returncode == 0:
        return True
    if result.returncode == _NOT_OFFERED_EXIT:
        return False
    logger.warning(
        "AppStream probe for %s was inconclusive (exit %s): %s",
        app_id,
        result.returncode,
        (result.stderr or "").strip()[-300:],
    )
    return None


def find_discontinued_transactions(script_dir=None, registry_data=None):
    """Return registry transactions whose repository app LinuxToys no longer offers.

    Each item is ``{"name": <registry name>, "app_id": <repository app id>}``.
    The result is empty whenever absence cannot be proven.
    """
    script_dir = script_dir or _APP_ROOT
    if registry_data is None:
        registry_data = registry_utils.parse_registry_file()

    transactions = registry_utils.get_repo_release_transactions(registry_data)
    if not transactions:
        return []

    state = appstream_cache.get_state()
    if appstream_cache.cache_needs_refresh() or int(state.get("count") or 0) <= 0:
        return []

    declared = declared_repo_app_ids(script_dir)
    if declared is None:
        return []

    scripts_dir = _resolution_scripts_trees(script_dir)[0]
    discontinued = []
    for name in sorted(transactions):
        app_id = transactions[name]
        if name.startswith(_REMOVAL_TRANSACTION_PREFIXES) or app_id in declared:
            continue
        if _physical_script_present(app_id, scripts_dir):
            continue
        if _appstream_offered(app_id, script_dir) is not False:
            continue
        discontinued.append({"name": name, "app_id": app_id})
    return discontinued
