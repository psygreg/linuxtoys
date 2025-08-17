#!/usr/bin/env python3

import sys
import os # Import the 'os' module
from app import main

if __name__ == "__main__":
    # --- DEVELOPER MODE BANNER ---
    try:
        from app.dev_mode import print_dev_mode_banner
        print_dev_mode_banner()
    except ImportError:
        pass  # dev_mode not available
    
    # --- UPDATE CHECK ---
    # Only run git-based updater in CLI mode (when LT_MANIFEST is set)
    # This preserves the git-based update functionality for development/git-cloned versions
    # when used in CLI mode, while GUI mode uses the new GitHub API-based checker
    if os.environ.get('LT_MANIFEST') == '1':
        # In CLI mode, use the git-based updater for development versions
        os.system('./helpers/update_self.sh')

    # --- LAUNCH GUI ---
    # This part runs after any CLI-mode updates, or immediately for GUI mode
    sys.exit(main.run())
