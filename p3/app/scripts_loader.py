#!/usr/bin/env python3
"""
Scripts Loader Module

This module is called during app initialization to handle script repository
synchronization via git with automatic fallback to bundled scripts.

It should be imported as early as possible in the app startup process.
"""

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the git scripts manager
from .git_scripts_manager import get_scripts_dir, is_using_git_scripts, get_git_scripts_status


def initialize_scripts():
    """
    Initialize scripts repository synchronization.
    
    This function should be called at app startup.
    It will:
    1. Synchronize scripts from git (with automatic fallback)
    2. Set up the scripts directory
    3. Show a loading dialog in GUI mode if this is a first run (clone operation)
    4. Log the status
    
    Returns:
        str: Path to the scripts directory being used
    """
    try:
        # Check if this is a first run (no git scripts cache exists)
        from .git_scripts_manager import GIT_SCRIPTS_CACHE_DIR, _git_repo_exists
        is_first_run = not _git_repo_exists()
        
        # For first run in GUI mode, show loading dialog
        scripts_dir = None
        if is_first_run and _should_show_loading_dialog():
            try:
                from .loading_dialog import show_loading_dialog_for_scripts_init
                
                def init_with_progress(progress_callback):
                    return get_scripts_dir(progress_callback)
                
                scripts_dir = show_loading_dialog_for_scripts_init(init_with_progress)
            except Exception as e:
                logger.debug(f"Could not show loading dialog: {e}")
                scripts_dir = get_scripts_dir()
        else:
            # Not first run, or CLI mode - proceed normally
            scripts_dir = get_scripts_dir()
        
        status = get_git_scripts_status()
        
        if status["is_git_synced"]:
            logger.info("✓ Scripts synchronized from git repository")
            if status["last_commit"]:
                logger.debug(f"  Latest commit: {status['last_commit']}")
        else:
            logger.info("⊠ Using bundled scripts (git sync not available)")
        
        logger.debug(f"  Scripts directory: {scripts_dir}")
        
        return scripts_dir
        
    except Exception as e:
        logger.error(f"Error initializing scripts: {e}")
        # Still return a scripts directory for fallback
        return os.path.join(
            os.path.dirname(__file__), '..', 'scripts'
        )


def _should_show_loading_dialog():
    """
    Check if we should show the loading dialog.
    Only show in GUI mode with display available.
    
    Returns:
        bool: True if loading dialog should be shown
    """
    # Don't show in CLI mode
    if os.environ.get('EASY_CLI') == '1':
        return False
    
    # Check for display server
    if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
        return False
    
    return True


def get_active_scripts_dir():
    """
    Get the currently active scripts directory.
    
    This can be called after initialization to determine which scripts
    directory is being used (git-synced or bundled).
    
    Returns:
        str: Path to the active scripts directory
    """
    from .git_scripts_manager import get_scripts_dir
    return get_scripts_dir()

