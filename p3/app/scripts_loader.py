#!/usr/bin/env python3
"""Scripts source initialization helpers."""

import logging
import os

from .git_scripts_manager import (
    get_available_scripts_dir,
    get_git_scripts_status,
    get_scripts_dir,
)

logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class _GitSyncLogFilter(logging.Filter):
    def filter(self, record):
        return "LT_DEBUG" in os.environ


_git_sync_log_filter = _GitSyncLogFilter()
logger.addFilter(_git_sync_log_filter)
logging.getLogger("app.git_scripts_manager").addFilter(_git_sync_log_filter)


def prepare_scripts():
    """Select the best immediately available source without synchronizing."""
    scripts_dir = get_available_scripts_dir()
    os.environ["CACHE_DIR"] = scripts_dir
    return scripts_dir


def initialize_scripts():
    """Synchronize scripts synchronously (used by CLI/headless modes)."""
    try:
        scripts_dir = get_scripts_dir()
        os.environ["CACHE_DIR"] = scripts_dir
        status = get_git_scripts_status(scripts_dir)
        if status["is_git_synced"]:
            logger.info("✓ Scripts synchronized from git repository")
        else:
            logger.info("⊠ Using bundled scripts (git sync not available)")
        return scripts_dir
    except Exception as e:
        logger.error(f"Error initializing scripts: {e}")
        return prepare_scripts()


def get_active_scripts_dir():
    """Return the currently selected source without network/subprocess work."""
    return get_available_scripts_dir()
