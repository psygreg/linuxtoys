#!/usr/bin/env python3

import sys
import os # Import the 'os' module

if __name__ == "__main__":
    # --- SET SCRIPT_DIR ENVIRONMENT VARIABLE ---
    # Set SCRIPT_DIR relative to linuxtoys.py so all scripts can find libs
    # The libs directory is always at the same location relative to this entry point
    linuxtoys_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ['SCRIPT_DIR'] = linuxtoys_dir

    # UPD_SERVICE runs from a headless systemd unit and must follow the CLI path.
    if os.environ.get('UPD_SERVICE') == '1':
        os.environ['EASY_CLI'] = '1'
    
    # --- VERIFY LIBRARIES EXIST ---
    # Safeguard: ensure the lib directory is present
    libs_dir = os.path.join(linuxtoys_dir, 'libs')
    if not os.path.isdir(libs_dir):
        print("Error: LinuxToys library files not found.")
        print(f"Expected path: {libs_dir}")
        print("The installation may be corrupted or incomplete.")
        sys.exit(1)
    
    # --- SCRIPTS INITIALIZATION ---
    # Initialize git-based scripts synchronization with fallback to bundled scripts
    try:
        from app.scripts_loader import initialize_scripts
        initialize_scripts()
    except ImportError:
        pass  # scripts_loader may not be available in some environments
    
    # --- DEVELOPER MODE BANNER ---
    try:
        from app.dev_mode import print_dev_mode_banner
        print_dev_mode_banner()
    except ImportError:
        pass  # dev_mode not available
    
    # --- UPDATE CHECK ---
    # Only run git-based updater in CLI mode (when EASY_CLI is set)
    # This preserves the git-based update functionality for development/git-cloned versions
    # when used in CLI mode, while GUI mode uses the new GitHub API-based checker
    if os.environ.get('EASY_CLI') == '1':
        # In CLI mode, use the git-based updater for development versions
        dir = os.path.dirname(os.path.realpath(__file__))
        os.system(f'{dir}/helpers/update_self.sh')

    # --- DISPLAY CHECK FOR GUI MODE ---
    # Check for display server before importing GTK to prevent crashes in headless environments
    if os.environ.get('EASY_CLI') != '1':
        if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            print("Error: No display server detected. Please run in a graphical environment.")
            print("For CLI mode, set EASY_CLI=1 and run with appropriate arguments.")
            sys.exit(1)

    from app import main

    # --- LAUNCH GUI ---
    # This part runs after any CLI-mode updates, or immediately for GUI mode
    sys.exit(main.run())
