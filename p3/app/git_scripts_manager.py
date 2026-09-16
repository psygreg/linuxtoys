#!/usr/bin/env python3
"""
Git Scripts Manager Module

This module handles live updating of scripts via git.
It clones or pulls the scripts repository from GitHub/Git.Linux.Toys
with automatic fallback to bundled scripts on failure.

Features:
- Clone scripts repository on first run
- Pull updates on subsequent runs
- Automatic fallback to bundled scripts if git operations fail
- Network error handling and timeouts
- Logging for debugging
"""

import os
import subprocess
import shutil
import logging
import time
import threading
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
                "git",
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


def _promote_staged_scripts_cache():
    """Atomically-ish swap a validated staging clone into the active cache path.

    Never recursively delete the active cache before promotion. Rename the old tree
    aside first (an atomic metadata operation on the same filesystem), install the
    staging tree at the canonical path, then clean up the retired tree afterwards.
    If promotion fails, restore the previous tree whenever possible.
    """
    if not os.path.isdir(GIT_SCRIPTS_STAGING_DIR):
        raise FileNotFoundError(
            f"Scripts staging directory does not exist: {GIT_SCRIPTS_STAGING_DIR}"
        )

    retired_path = None
    if os.path.exists(GIT_SCRIPTS_CACHE_DIR):
        retired_path = (
            f"{GIT_SCRIPTS_RETIRED_PREFIX}."
            f"{os.getpid()}.{time.time_ns()}"
        )
        os.replace(GIT_SCRIPTS_CACHE_DIR, retired_path)

    try:
        os.replace(GIT_SCRIPTS_STAGING_DIR, GIT_SCRIPTS_CACHE_DIR)
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
    finally:
        if retired_path:
            _cleanup_retired_cache(retired_path)


def _clone_scripts_repo(progress_callback=None):
    """Clone into a staging directory and promote only after a successful clone."""
    if not _ensure_cache_dir():
        logger.error("Cannot create cache directory")
        return False

    if os.path.exists(GIT_SCRIPTS_STAGING_DIR):
        try:
            shutil.rmtree(GIT_SCRIPTS_STAGING_DIR)
        except Exception as e:
            logger.error(f"Failed to clear scripts staging directory: {e}")
            return False

    urls = (
        (GITHUB_REPO_URL, "scripts_init_cloning_github", "GitHub"),
        (GITLINUXTOYS_REPO_URL, "scripts_init_cloning_linux_toys", "git.linux.toys"),
    )

    for repo_url, progress_key, label in urls:
        if progress_callback:
            progress_callback(progress_key)
        logger.info(f"Attempting to clone scripts from {repo_url} (timeout: {GIT_TIMEOUT}s)")
        success, _, error = _run_git_command(
            ["clone", "--depth=1", repo_url, GIT_SCRIPTS_STAGING_DIR]
        )

        if success:
            try:
                # The normal clone path is used only when no valid cached repository
                # exists. Move any broken/incomplete cache aside first, promote the
                # validated staging tree, then clean up the retired tree best-effort.
                _promote_staged_scripts_cache()
            except Exception as e:
                logger.error(f"Failed to promote synchronized scripts cache: {e}")
                return False

            logger.info(f"Successfully cloned scripts from {label}")
            _write_update_timestamp()
            if progress_callback:
                progress_callback("scripts_init_success")
            return True

        logger.warning(f"{label} clone failed: {error}")
        try:
            if os.path.exists(GIT_SCRIPTS_STAGING_DIR):
                shutil.rmtree(GIT_SCRIPTS_STAGING_DIR)
        except OSError:
            pass

    logger.info("Will keep the currently available scripts source")
    if progress_callback:
        progress_callback("scripts_init_failed")
    return False

def _pull_scripts_repo(progress_callback=None, force=False):
    """
    Pull updates from the scripts repository.

    Times out after 10 seconds to prevent hanging on network issues.
    Respects the update interval to avoid rate limiting unless force is True.

    If pull fails (including timeout), will use the cached repository.

    Args:
        progress_callback: Optional function to call with progress messages
        force: Whether to bypass the update interval

    Returns:
        bool: True if pull was successful or skipped due to rate limiting
    """
    if not _git_repo_exists():
        logger.warning("Scripts repository not found in cache, cloning instead")
        if progress_callback:
            progress_callback("scripts_init_not_found")
        return _clone_scripts_repo(progress_callback)

    # Check if we should update based on time interval unless explicitly forced.
    if not force and not _should_update_scripts():
        logger.info("Skipping repository update due to rate limiting (updated < 6 hours ago)")
        return True  # Return True since we have valid cached scripts

    if progress_callback:
        progress_callback("scripts_init_updating")
    logger.info(f"Pulling updates for scripts repository (timeout: {GIT_TIMEOUT}s)")
    success, output, error = _run_git_command(
        ["pull", "--ff-only"],
        cwd=GIT_SCRIPTS_CACHE_DIR
    )

    if success:
        # Restore the managed cache to exactly the checked-out revision.
        reset_success, _, reset_error = _run_git_command(
            ["reset", "--hard", "HEAD"],
            cwd=GIT_SCRIPTS_CACHE_DIR
        )

        if not reset_success:
            logger.warning(
                f"Failed to restore scripts working tree: {reset_error}"
            )
            return False

        logger.info(
            "Successfully pulled scripts updates and restored working tree"
        )
        _write_update_timestamp()
        if progress_callback:
            progress_callback("scripts_init_update_success")
        return True

    logger.warning(f"Failed to pull updates: {error}")

    if force:
        logger.info(
            "Forced scripts update failed to pull; attempting a clean clone"
        )
        return _clone_scripts_repo(progress_callback)

    logger.info("Keeping the cached scripts repository unchanged")
    return False

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
    """Cheap startup check for a previously successful cache; never invokes git."""
    return (
        os.path.isdir(GIT_SCRIPTS_CACHE_DIR)
        and os.path.isdir(os.path.join(GIT_SCRIPTS_CACHE_DIR, ".git"))
        and os.path.isfile(LAST_UPDATE_TIMESTAMP_FILE)
    )


def get_available_scripts_dir():
    """Return an immediately usable scripts tree without network/subprocess work."""
    bundled_scripts_dir = get_bundled_scripts_dir()

    if is_dev_mode_enabled():
        return bundled_scripts_dir

    if _cached_scripts_are_readily_available():
        return GIT_SCRIPTS_CACHE_DIR

    return bundled_scripts_dir


def _synchronize_scripts_unlocked(progress_callback=None, force=False):
    """Synchronize the remote repository and report whether usable data changed.

    This function may block and is intended for a worker thread in GUI mode.
    """
    if is_dev_mode_enabled():
        return {
            "success": False,
            "changed": False,
            "performed": False,
            "path": get_bundled_scripts_dir(),
        }

    # One HEAD lookup both validates the cached repository and captures the
    # revision used for change detection. Avoid separate rev-parse probes.
    old_commit = _get_head_commit()
    had_repo = old_commit is not None

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
    """Synchronize scripts while preventing overlapping in-process promotions."""
    with _SYNC_LOCK:
        return _synchronize_scripts_unlocked(
            progress_callback=progress_callback,
            force=force,
        )


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
        return get_bundled_scripts_dir()

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
