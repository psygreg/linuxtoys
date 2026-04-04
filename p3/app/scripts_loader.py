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
    3. Log the status
    
    Returns:
        str: Path to the scripts directory being used
    """
    try:
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
