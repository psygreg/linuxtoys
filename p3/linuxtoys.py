#!/usr/bin/env python3

import os
import subprocess
import sys


def configure_launch_flags():
    """Apply global flags before initializing the application."""
    launch_flags = {
        "--devmode": "DEV_MODE",
        "--debug": "LT_DEBUG",
    }
    remaining_args = [sys.argv[0]]

    for argument in sys.argv[1:]:
        environment_variable = launch_flags.get(argument)
        if environment_variable:
            os.environ[environment_variable] = "1"
        else:
            remaining_args.append(argument)

    sys.argv = remaining_args

if __name__ == "__main__":
    configure_launch_flags()

    # Commands that are intrinsically headless should enter the CLI path even
    # when LinuxToys was launched directly rather than through a CLI wrapper.
    if len(sys.argv) == 2 and sys.argv[1] in ("export-manifest", "--export-manifest"):
        os.environ["EASY_CLI"] = "1"

    if len(sys.argv) == 2 and sys.argv[1] in ("-v", "--version", "-h", "--help", "help"):
        from app.easy_cli import easy_cli_help_message, print_version

        if sys.argv[1] in ("-v", "--version"):
            print_version()
        else:
            easy_cli_help_message()
        sys.exit(0)

    if len(sys.argv) == 2 and sys.argv[1].startswith("-"):
        from app.easy_cli import CLI_OPTIONS, easy_cli_help_message

        if sys.argv[1] not in CLI_OPTIONS:
            print(f"Unknown option: {sys.argv[1]}\n")
            easy_cli_help_message()
            sys.exit(2)

    # --- SET SCRIPT_DIR AND CACHE_DIR ENVIRONMENT VARIABLES ---
    # Set SCRIPT_DIR relative to linuxtoys.py so all scripts can find libs
    # The libs directory is always at the same location relative to this entry point
    linuxtoys_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ['SCRIPT_DIR'] = linuxtoys_dir
    
    # Set CACHE_DIR to bundled scripts as default fallback
    # GUI startup replaces this immediately with the last cache when available
    os.environ['CACHE_DIR'] = os.path.join(linuxtoys_dir, 'scripts')

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
     
    # --- DEVELOPER MODE BANNER ---
    try:
        from app.dev_mode import print_dev_mode_banner
        print_dev_mode_banner()
    except ImportError:
        pass  # dev_mode not available
    
    # --- UPDATE CHECK ---
    # Check for updates only in CLI mode (EASY_CLI=1) and display feedback in the terminal.
    if os.environ.get('EASY_CLI') == '1':
        from app.manifest_helper import run_update_check_cli
        run_update_check_cli()
        # If running as UPD_SERVICE, run system update after app update completes
        if os.environ.get('UPD_SERVICE') == '1':
            print("\n" + "=" * 60)
            print("Now running system update...")
            print("=" * 60 + "\n")
            try:
                script_path = os.path.join(os.environ.get('SCRIPT_DIR', linuxtoys_dir), 'scripts', 'sysup.sh')
                subprocess.run(['bash', script_path], check=False)
            except Exception as e:
                print(f"Error running system update: {e}")
            sys.exit(0)
        
    cli_mode = os.environ.get('EASY_CLI') == '1'
    # --- DISPLAY CHECK FOR GUI MODE ---
    if not cli_mode:
        if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            print("Error: No display server detected. Please run in a graphical environment.")
            print("For CLI mode, set EASY_CLI=1 and run with appropriate arguments.")
            sys.exit(1)

    # --- SCRIPTS INITIALIZATION ---
    try:
        from app.scripts_loader import initialize_scripts, prepare_scripts

        if cli_mode:
            # CLI/headless mode keeps synchronous synchronization semantics.
            initialize_scripts()
        else:
            # GUI startup must never wait for network or git. AppWindow starts
            # repository synchronization after the GTK application is running.
            prepare_scripts()

    except ImportError:
        pass

    from app import main

    # --- LAUNCH GUI ---
    # This part runs after any CLI-mode updates, or immediately for GUI mode
    sys.exit(main.run())
