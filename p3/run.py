#!/usr/bin/env python3

import sys
import os # Import the 'os' module

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

    # --- DISPLAY CHECK FOR GUI MODE ---
    # Check for display server before importing GTK to prevent crashes in headless environments
    if os.environ.get('LT_MANIFEST') != '1':
        if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            print("Error: No display server detected. Please run in a graphical environment.")
            print("For CLI mode, set LT_MANIFEST=1 and run with appropriate arguments.")
            sys.exit(1)

    # --- VTE VERSION CHECK ---
    # Detect VTE version and route to appropriate runtime
    # VTE 0.80+ requires modern runtime, older versions use legacy runtime
    use_legacy = False
    
    if os.environ.get('LT_MANIFEST') != '1':  # Only check VTE for GUI mode
        try:
            from vte_compat import is_vte_compatible, get_vte_version
            
            if not is_vte_compatible():
                version = get_vte_version()
                if version:
                    major, minor, patch = version
                    print(f"Detected VTE {major}.{minor}.{patch} - using legacy runtime for compatibility")
                else:
                    print("VTE version could not be detected - using legacy runtime for compatibility")
                use_legacy = True
            else:
                version = get_vte_version()
                if version:
                    major, minor, patch = version
                    print(f"Detected VTE {major}.{minor}.{patch} - using modern runtime")
        except Exception as e:
            print(f"Warning: VTE detection failed ({e}), defaulting to legacy runtime")
            use_legacy = True

    # --- IMPORT MAIN AFTER CHECKS ---
    if use_legacy:
        from app.legacy import main
    else:
        from app import main

    # --- LAUNCH GUI ---
    # This part runs after any CLI-mode updates, or immediately for GUI mode
    sys.exit(main.run())
