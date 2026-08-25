#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys


def get_installed_version():
    """Return the installed LinuxToys package version, when available."""
    version_commands = (
        ("dpkg-query", ["dpkg-query", "-W", "-f=${Version}", "linuxtoys"]),
        ("rpm", ["rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", "linuxtoys"]),
        ("pacman", ["pacman", "-Q", "linuxtoys"]),
    )

    for command_name, command in version_commands:
        if not shutil.which(command_name):
            continue
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError:
            continue
        output = result.stdout.strip()
        if result.returncode == 0 and output:
            if command_name == "pacman":
                _, separator, output = output.partition(" ")
                if not separator:
                    continue
            return output.split("-", maxsplit=1)[0]

    return None


def print_version():
    """Print the package version, falling back to the bundled version."""
    version = get_installed_version()
    if version is None:
        from app.updater import __version__
        version = __version__
    print(f"{version}")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ("-v", "--version"):
        print_version()
        sys.exit(0)

    # --- SET SCRIPT_DIR AND CACHE_DIR ENVIRONMENT VARIABLES ---
    # Set SCRIPT_DIR relative to linuxtoys.py so all scripts can find libs
    # The libs directory is always at the same location relative to this entry point
    linuxtoys_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ['SCRIPT_DIR'] = linuxtoys_dir
    
    # Set CACHE_DIR to bundled scripts as default fallback
    # This will be overridden by initialize_scripts() if git sync is available
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
        from app.scripts_loader import initialize_scripts

        # CLI synchronization must remain completely non-GUI.
        if cli_mode:
            initialize_scripts()

        else:
            from app import git_scripts_manager

            # Only show the dialog if clone/pull will actually occur.
            if git_scripts_manager.will_perform_git_operation():
                import threading

                from app.gtk_common import GLib
                from app.gtk_dialogs import WaitDialog
                from app.lang_utils import create_translator

                _ = create_translator()

                dialog = WaitDialog(None, _("scripts_init_updating"))
                dialog.start()

                # The normal application GTK loop has not started yet, so run
                # a temporary loop while the repository sync occurs.
                loop = GLib.MainLoop()
                sync_error = []

                def initialize_scripts_thread():
                    try:
                        initialize_scripts()
                    except Exception as exc:
                        sync_error.append(exc)
                    finally:
                        GLib.idle_add(loop.quit)

                threading.Thread(
                    target=initialize_scripts_thread,
                    daemon=True,
                ).start()

                loop.run()
                dialog.stop()

                if sync_error:
                    raise sync_error[0]

            else:
                # Timestamp is still valid. initialize_scripts() is still
                # required so CACHE_DIR is configured correctly, but it will
                # use the cached repository without doing network I/O.
                initialize_scripts()

    except ImportError:
        pass

    from app import main

    # --- LAUNCH GUI ---
    # This part runs after any CLI-mode updates, or immediately for GUI mode
    sys.exit(main.run())
