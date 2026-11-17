#!/usr/bin/env python3
"""Synchronize the script catalog from the upstream mirror repository.

The psygreg/scripts mirror's default branch is the content source: live script
fixes flow to installed clients without a client release. Network failures
retain the previous cache or the bundled snapshot. All execution still passes
through the architecture policy gates.
"""

import os
import subprocess
import shutil
import logging
import time
import threading
import tempfile
import fcntl
from pathlib import Path

from .dev_mode import is_dev_mode_enabled

# Set up logging
logger = logging.getLogger(__name__)

# Git repository URLs (primary and fallback)
GITHUB_REPO_URL = "https://github.com/psygreg/scripts.git"
GITLINUXTOYS_REPO_URL = "https://git.linux.toys/psygreg/scripts.git"

# Cache directory paths
CACHE_DIR = os.path.expanduser("~/.cache/linuxtoys")
GIT_SCRIPTS_CACHE_DIR = os.path.join(CACHE_DIR, "scripts")
LAST_UPDATE_TIMESTAMP_FILE = os.path.join(CACHE_DIR, "last_update.timestamp")
GIT_SCRIPTS_STAGING_DIR = os.path.join(CACHE_DIR, "scripts.updating")
GIT_SCRIPTS_RETIRED_PREFIX = os.path.join(CACHE_DIR, "scripts.retired")

# Prevent overlapping synchronize/force-update operations inside one process.
_SYNC_LOCK = threading.RLock()

# Timeout for git operations (in seconds)
# Set to 10 seconds to prevent hanging on network issues
GIT_TIMEOUT = 10

# Update interval for script repository (6 hours)
UPDATE_INTERVAL = 6 * 60 * 60


def _get_last_update_timestamp():
    """
    Get the timestamp of the last successful git operation.

    Returns:
        float: Unix timestamp of last update, or None if never updated
    """
    try:
        if os.path.exists(LAST_UPDATE_TIMESTAMP_FILE):
            with open(LAST_UPDATE_TIMESTAMP_FILE, 'r') as f:
                return float(f.read().strip())
    except (OSError, ValueError) as e:
        logger.debug(f"Could not read last update timestamp: {e}")
    return None


def _write_update_timestamp():
    """
    Write the current timestamp as the last update time.
    """
    try:
        _ensure_cache_dir()
        with open(LAST_UPDATE_TIMESTAMP_FILE, 'w') as f:
            f.write(str(time.time()))
        logger.debug(f"Updated timestamp file: {LAST_UPDATE_TIMESTAMP_FILE}")
    except OSError as e:
        logger.error(f"Failed to write update timestamp: {e}")


def _should_update_scripts():
    """
    Check if enough time has passed to update scripts.

    Returns:
        bool: True if update interval has elapsed or this is the first run
    """
    last_update = _get_last_update_timestamp()
    if last_update is None:
        return True  # First run, should update

    elapsed = time.time() - last_update
    if elapsed >= UPDATE_INTERVAL:
        logger.debug(f"Update interval elapsed ({elapsed/3600:.1f} hours), allowing update")
        return True  # 6+ hours have passed

    logger.debug(f"Scripts updated {elapsed/3600:.1f} hours ago, skipping update to avoid rate limiting")
    return False


def _run_git_command(args, cwd=None, timeout=GIT_TIMEOUT):
    """
    Run a git command with error handling and timeout protection.

    Args:
        args (list): Arguments to pass to git command
        cwd (str): Working directory for the command
        timeout (int): Command timeout in seconds

    Returns:
        tuple: (success, output, error) - success is bool, output and error are strings
    """
    try:
        result = subprocess.run(
            [
                "git", "-c", "core.hooksPath=/dev/null",
                *args
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )

        success = result.returncode == 0
        return success, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        error_msg = f"Git command timed out after {timeout} seconds"
        logger.warning(error_msg)
        return False, "", error_msg
    except FileNotFoundError:
        return False, "", "Git is not installed"
    except Exception as e:
        return False, "", str(e)


def _ensure_cache_dir():
    """Ensure the cache directory exists."""
    try:
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create cache directory: {e}")
        return False


def _git_repo_exists():
    """Cheap filesystem-only check for a cached git worktree."""
    return (
        os.path.isdir(GIT_SCRIPTS_CACHE_DIR)
        and os.path.isdir(os.path.join(GIT_SCRIPTS_CACHE_DIR, ".git"))
    )


def _get_head_commit(short=False):
    """Return HEAD for the cached repo, or None when the cache is invalid."""
    if not _git_repo_exists():
        return None
    args = ["rev-parse"]
    if short:
        args.append("--short")
    args.append("HEAD")
    success, output, _ = _run_git_command(args, cwd=GIT_SCRIPTS_CACHE_DIR)
    if not success:
        return None
    commit = output.strip()
    return commit or None

def _cleanup_retired_cache(path):
    """Remove a retired scripts tree without making promotion depend on cleanup."""
    if not path or not os.path.exists(path):
        return

    try:
        shutil.rmtree(path)
    except OSError as e:
        # A stale/active reader or another process may transiently keep changing the
        # old tree. It is already outside the active cache path, so this is harmless.
        logger.warning(f"Could not remove retired scripts cache {path}: {e}")


def _looks_like_scripts_tree(path):
    """Cheap structural sanity check for a candidate scripts tree.

    A healthy tree always carries the git release index and at least one
    install script; anything else (empty clone, error page, partial copy) is
    never promoted or executed.
    """
    if not os.path.isdir(path):
        return False
    if not os.path.isfile(os.path.join(path, "git-db.json")):
        return False
    for _directory, _dirs, names in os.walk(path):
        if any(name.endswith(".sh") for name in names):
            return True
    return False


def _promote_staged_scripts_cache(staging_dir=None):
    """Atomically-ish swap a validated staging clone into the active cache path.

    Never recursively delete the active cache before promotion. Rename the old tree
    aside first (an atomic metadata operation on the same filesystem), install the
    staging tree at the canonical path, then clean up the retired tree afterwards.
    If promotion fails, restore the previous tree whenever possible.
    """
    staging_dir = staging_dir or GIT_SCRIPTS_STAGING_DIR
    if not _looks_like_scripts_tree(staging_dir):
        raise FileNotFoundError(
            f"Scripts staging directory does not exist: {staging_dir}"
        )

    retired_path = None
    if os.path.exists(GIT_SCRIPTS_CACHE_DIR):
        retired_path = (
            f"{GIT_SCRIPTS_RETIRED_PREFIX}."
            f"{os.getpid()}.{time.time_ns()}"
        )
        os.replace(GIT_SCRIPTS_CACHE_DIR, retired_path)

    try:
        os.replace(staging_dir, GIT_SCRIPTS_CACHE_DIR)
    except Exception:
        # Roll back only when the canonical destination is still free. If another
        # process already installed a usable cache, do not overwrite it.
        if (
            retired_path
            and os.path.exists(retired_path)
            and not os.path.exists(GIT_SCRIPTS_CACHE_DIR)
        ):
            try:
                os.replace(retired_path, GIT_SCRIPTS_CACHE_DIR)
                retired_path = None
            except OSError as restore_error:
                logger.error(
                    f"Failed to restore previous scripts cache after promotion error: "
                    f"{restore_error}"
                )
        raise
    else:
        if retired_path:
            _cleanup_retired_cache(retired_path)


def _clone_scripts_repo(progress_callback=None):
    """Clone the mirror's default branch into private staging; promote on success."""
    if not _ensure_cache_dir():
        return False
    urls = (
        (GITHUB_REPO_URL, "scripts_init_cloning_github"),
        (GITLINUXTOYS_REPO_URL, "scripts_init_cloning_linux_toys"),
    )
    for repo_url, progress_key in urls:
        if progress_callback:
            progress_callback(progress_key)
        staging = tempfile.mkdtemp(prefix="scripts.updating.", dir=CACHE_DIR)
        try:
            success, _, error = _run_git_command(
                ["clone", "--depth=1", "--single-branch", "--", repo_url, staging]
            )
            if not success:
                logger.warning("Scripts mirror fetch failed: %s", error)
                continue
            if not _looks_like_scripts_tree(staging):
                logger.warning("Rejected synchronized scripts: incomplete tree")
                continue
            _promote_staged_scripts_cache(staging)
            _write_update_timestamp()
            if progress_callback:
                progress_callback("scripts_init_success")
            return True
        except (OSError, ValueError) as exc:
            logger.warning("Rejected synchronized scripts: %s", exc)
        finally:
            if os.path.exists(staging):
                shutil.rmtree(staging)
    if progress_callback:
        progress_callback("scripts_init_failed")
    return False


def _pull_scripts_repo(progress_callback=None, force=False):
    """Update through staging, never pull/reset the active execution tree."""
    if not force and _cached_scripts_are_readily_available() and not _should_update_scripts():
        return True
    return _clone_scripts_repo(progress_callback)


def force_update_scripts(progress_callback=None):
    """Update the script cache immediately, bypassing the update interval."""
    if is_dev_mode_enabled():
        logger.info("Developer mode active - skipping forced script cache update")
        return False

    return synchronize_scripts(progress_callback=progress_callback, force=True)["success"]


def get_bundled_scripts_dir():
    """Return the bundled scripts directory without performing any git operation."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))


def _cached_scripts_are_readily_available():
    """Check cached-tree sanity without invoking git or the network."""
    return _looks_like_scripts_tree(GIT_SCRIPTS_CACHE_DIR) and _git_repo_exists()


def get_available_scripts_dir():
    """Select a usable source; a broken cache falls back to the bundled tree."""
    if not is_dev_mode_enabled() and _cached_scripts_are_readily_available():
        return GIT_SCRIPTS_CACHE_DIR
    return get_bundled_scripts_dir()


def _synchronize_scripts_unlocked(progress_callback=None, force=False):
    """Synchronize the remote repository and report whether usable data changed.

    This function may block and is intended for a worker thread in GUI mode.
    """
    if is_dev_mode_enabled():
        return {
            "success": False,
            "changed": False,
            "performed": False,
            "path": get_available_scripts_dir(),
        }

    # One HEAD lookup both validates the cached repository and captures the
    # revision used for change detection. Avoid separate rev-parse probes.
    had_repo = _cached_scripts_are_readily_available()
    old_commit = _get_head_commit() if had_repo else None

    performed = force or not had_repo or _should_update_scripts()
    if not performed:
        return {
            "success": True,
            "changed": False,
            "performed": False,
            "path": GIT_SCRIPTS_CACHE_DIR,
        }

    if had_repo:
        success = _pull_scripts_repo(progress_callback, force=force)
    else:
        if progress_callback:
            progress_callback("scripts_init_first_run")
        success = _clone_scripts_repo(progress_callback)

    if not success:
        return {
            "success": False,
            "changed": False,
            "performed": True,
            "path": get_available_scripts_dir(),
        }

    new_commit = _get_head_commit()
    if new_commit is None:
        return {
            "success": False,
            "changed": False,
            "performed": True,
            "path": get_available_scripts_dir(),
        }

    return {
        "success": True,
        "changed": (not had_repo) or (old_commit != new_commit),
        "performed": True,
        "path": GIT_SCRIPTS_CACHE_DIR,
    }


def synchronize_scripts(progress_callback=None, force=False):
    """Serialize promotion across threads/processes; readers only see whole trees."""
    with _SYNC_LOCK:
        if not _ensure_cache_dir():
            return {"success": False, "changed": False, "performed": False,
                    "path": get_available_scripts_dir()}
        with open(os.path.join(CACHE_DIR, "scripts.sync.lock"), "a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return {"success": False, "changed": False, "performed": False,
                        "path": get_available_scripts_dir()}
            try:
                return _synchronize_scripts_unlocked(progress_callback, force)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


def will_perform_git_operation():
    """Return whether a synchronization worker would perform clone/pull."""
    if is_dev_mode_enabled():
        return False
    if not _cached_scripts_are_readily_available():
        return True
    return _should_update_scripts()


def get_scripts_dir(progress_callback=None):
    """Synchronize synchronously, retained for CLI/backwards compatibility."""
    if is_dev_mode_enabled():
        return get_available_scripts_dir()

    result = synchronize_scripts(progress_callback=progress_callback)
    if result["success"] and os.path.isdir(result["path"]):
        return result["path"]
    return get_available_scripts_dir()


def is_using_git_scripts():
    """Return whether a readily available cached repository exists."""
    if is_dev_mode_enabled():
        return False
    return _cached_scripts_are_readily_available()


def get_git_scripts_status(active_path=None):
    """Return synchronization status without triggering a synchronization."""
    active_path = active_path or get_available_scripts_dir()
    is_git_synced = (
        not is_dev_mode_enabled()
        and os.path.abspath(active_path) == os.path.abspath(GIT_SCRIPTS_CACHE_DIR)
        and _cached_scripts_are_readily_available()
    )

    status = {
        "synced": is_git_synced,
        "path": active_path,
        "is_git_synced": is_git_synced,
        "last_commit": None,
    }

    if is_git_synced:
        try:
            status["last_commit"] = _get_head_commit(short=True)
        except Exception:
            pass

    return status
