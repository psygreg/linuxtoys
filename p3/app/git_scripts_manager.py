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
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

# Git repository URLs (primary and fallback)
GITHUB_REPO_URL = "https://github.com/psygreg/scripts.git"
GITLINUXTOYS_REPO_URL = "https://git.linux.toys/psygreg/scripts.git"

# Cache directory paths
CACHE_DIR = os.path.expanduser("~/.cache/linuxtoys")
GIT_SCRIPTS_CACHE_DIR = os.path.join(CACHE_DIR, "scripts")
LAST_UPDATE_TIMESTAMP_FILE = os.path.join(CACHE_DIR, "last_update.timestamp")

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
    """Check if the git repository already exists in cache."""
    if not os.path.isdir(GIT_SCRIPTS_CACHE_DIR):
        return False
    
    # Check if it's a valid git repository
    git_dir = os.path.join(GIT_SCRIPTS_CACHE_DIR, ".git")
    return os.path.isdir(git_dir)


def _clone_scripts_repo(progress_callback=None):
    """
    Attempt to clone the scripts repository.
    Tries GitHub first, then falls back to git.linux.toys.
    Times out after 10 seconds per attempt to avoid hanging on network issues.
    
    Args:
        progress_callback: Optional function to call with progress messages
        
    Returns:
        bool: True if clone was successful
    """
    if not _ensure_cache_dir():
        logger.error("Cannot create cache directory")
        return False
    
    # If directory exists but we want to clone fresh, remove it
    if os.path.exists(GIT_SCRIPTS_CACHE_DIR):
        try:
            if progress_callback:
                progress_callback("scripts_init_preparing")
            shutil.rmtree(GIT_SCRIPTS_CACHE_DIR)
        except Exception as e:
            logger.error(f"Failed to remove existing scripts directory: {e}")
            return False
    
    # Try cloning from GitHub first
    if progress_callback:
        progress_callback("scripts_init_cloning_github")
    logger.info(f"Attempting to clone scripts from {GITHUB_REPO_URL} (timeout: {GIT_TIMEOUT}s)")
    success, output, error = _run_git_command(
        ["clone", "--depth=1", GITHUB_REPO_URL, GIT_SCRIPTS_CACHE_DIR]
    )
    
    if success:
        logger.info("Successfully cloned scripts from GitHub")
        _write_update_timestamp()
        if progress_callback:
            progress_callback("scripts_init_success")
        return True
    
    logger.warning(f"GitHub clone failed: {error}")
    
    # Try fallback URL
    if progress_callback:
        progress_callback("scripts_init_cloning_linux_toys")
    logger.info(f"Attempting to clone scripts from {GITLINUXTOYS_REPO_URL} (timeout: {GIT_TIMEOUT}s)")
    success, output, error = _run_git_command(
        ["clone", "--depth=1", GITLINUXTOYS_REPO_URL, GIT_SCRIPTS_CACHE_DIR]
    )
    
    if success:
        logger.info("Successfully cloned scripts from git.linux.toys")
        _write_update_timestamp()
        if progress_callback:
            progress_callback("scripts_init_success")
        return True
    
    logger.error(f"git.linux.toys clone failed: {error}")
    logger.info("Will fall back to bundled scripts")
    if progress_callback:
        progress_callback("scripts_init_failed")
    return False


def _pull_scripts_repo(progress_callback=None):
    """
    Pull updates from the scripts repository.
    
    Times out after 10 seconds to prevent hanging on network issues.
    Respects the update interval to avoid rate limiting - will only pull if
    the last update was more than 6 hours ago or this is the first run.
    
    If pull fails (including timeout), will use the cached repository.
    
    Args:
        progress_callback: Optional function to call with progress messages
    
    Returns:
        bool: True if pull was successful or skipped due to rate limiting
    """
    if not _git_repo_exists():
        logger.warning("Scripts repository not found in cache, cloning instead")
        if progress_callback:
            progress_callback("scripts_init_not_found")
        return _clone_scripts_repo(progress_callback)
    
    # Check if we should update based on time interval
    if not _should_update_scripts():
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
        logger.info("Successfully pulled scripts updates")
        _write_update_timestamp()
        if progress_callback:
            progress_callback("scripts_init_update_success")
        return True
    
    logger.warning(f"Failed to pull updates: {error}")
    logger.info("Falling back to cached scripts repository")
    # Return True here since we already have the repo, even if pull failed
    # This ensures we use cached scripts rather than failing completely
    return True


def will_perform_git_operation():
    """
    Check if a git operation (clone or pull) will actually be performed.
    
    This is useful to determine if a loading dialog should be shown before
    calling get_scripts_dir().
    
    Returns:
        bool: True if a git operation will be performed, False if scripts will be used from cache
    """
    # If repo doesn't exist, we'll try to clone
    if not _git_repo_exists():
        return True
    
    # If repo exists and update interval has passed, we'll try to pull
    if _should_update_scripts():
        return True
    
    # Otherwise, we'll just use cached scripts without any git operations
    return False


def get_scripts_dir(progress_callback=None):
    """
    Get the scripts directory, attempting git sync with fallback to bundled scripts.
    
    This is the main entry point for the scripts manager.
    It will:
    1. Try to sync scripts from git (clone if needed, pull if exists)
    2. Return the git-synced directory if successful
    3. Fall back to bundled scripts if git operations fail or git is unavailable
    
    Args:
        progress_callback: Optional function to call with progress messages
    
    Returns:
        str: Absolute path to the scripts directory (either git-synced or bundled)
    """
    # First, try to sync from git
    if _git_repo_exists():
        # Repository exists, try to pull updates
        if _pull_scripts_repo(progress_callback) and os.path.isdir(GIT_SCRIPTS_CACHE_DIR):
            logger.info(f"Using git-synced scripts from {GIT_SCRIPTS_CACHE_DIR}")
            return GIT_SCRIPTS_CACHE_DIR
    else:
        # Repository doesn't exist, try to clone it (first run scenario)
        if progress_callback:
            progress_callback("scripts_init_first_run")
        if _clone_scripts_repo(progress_callback):
            logger.info(f"Using git-synced scripts from {GIT_SCRIPTS_CACHE_DIR}")
            return GIT_SCRIPTS_CACHE_DIR
    
    # If git sync failed or was unavailable, fall back to bundled scripts
    bundled_scripts_dir = os.path.join(
        os.path.dirname(__file__), '..', 'scripts'
    )
    logger.info(f"Falling back to bundled scripts from {bundled_scripts_dir}")
    return bundled_scripts_dir


def is_using_git_scripts():
    """
    Check if the app is currently using git-synced scripts.
    
    Returns:
        bool: True if using git-synced scripts, False if using bundled scripts
    """
    return os.path.exists(GIT_SCRIPTS_CACHE_DIR) and _git_repo_exists()


def get_git_scripts_status():
    """
    Get status information about git scripts synchronization.
    
    Returns:
        dict: Status dictionary with keys:
            - synced: bool - Whether git sync was successful
            - path: str - Path to scripts directory being used
            - is_git_synced: bool - Whether using git-synced scripts
            - last_commit: str - Last commit hash (if available)
    """
    is_git_synced = is_using_git_scripts()
    
    status = {
        "synced": is_git_synced,
        "path": get_scripts_dir(),
        "is_git_synced": is_git_synced,
        "last_commit": None
    }
    
    if is_git_synced:
        try:
            success, commit_hash, _ = _run_git_command(
                ["rev-parse", "--short", "HEAD"],
                cwd=GIT_SCRIPTS_CACHE_DIR
            )
            if success:
                status["last_commit"] = commit_hash.strip()
        except Exception:
            pass
    
    return status
