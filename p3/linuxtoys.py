#!/usr/bin/env python3

import os
import subprocess
import sys
from urllib.parse import unquote, urlparse

# Vendored TUI dependencies (textual, pyte and their runtime stack) ship
# in-tree so every platform runs the same pinned version, including
# distributions without textual 8.x packaging and the AppImage. The vendor
# directory is inserted ahead of site-packages on purpose: it must win over
# any older copy a distribution happens to have installed.
_VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(_VENDOR_DIR):
    sys.path.insert(0, _VENDOR_DIR)


GUI_PACKAGE_SUFFIXES = (
    ".deb",
    ".rpm",
    ".pacman",
    ".eopkg",
    ".flatpak",
    ".flatpakref",
    ".snap",
    ".appimage",
    ".pkg.tar.zst",
    ".pkg.tar.xz",
    ".pkg.tar.gz",
    ".pkg.tar.lz4",
)

GUI_FLAGS = ("-g", "--gui")

# MCP_AGENT_SERVER_FLAG: `linuxtoys --mcp` runs the headless MCP server for AI
# agents (also the systemd user service ExecStart). It never registers the GUI
# application identity, so the app keeps launching normally through every other
# method while the server is running.
MCP_FLAGS = ("--mcp",)

# Set when the resolved target interface is the TUI (bare launch in a
# terminal or an explicit ``--tui``), so launch-time network work can be
# deferred to the TUI's own background workers.
tui_requested = False

def is_gui_external_request(argument):
    """Return True for external requests that must be handled by the GUI."""
    if not isinstance(argument, str) or not argument:
        return False

    if argument.casefold().startswith("linuxtoys://"):
        return True

    try:
        parsed = urlparse(argument)
        if parsed.scheme.casefold() == "file":
            path = unquote(parsed.path)
        elif not parsed.scheme:
            path = argument
        else:
            return False
    except (TypeError, ValueError):
        return False

    path = os.path.expanduser(path)
    return os.path.isfile(path) and path.casefold().endswith(GUI_PACKAGE_SUFFIXES)

def configure_launch_flags():
    """Apply global flags before initializing the application.

    Returns True when the GUI was explicitly requested.
    """
    launch_flags = {
        "--devmode": "DEV_MODE",
        "--debug": "LT_DEBUG",
    }
    gui_requested = False
    remaining_args = [sys.argv[0]]

    for argument in sys.argv[1:]:
        if argument in GUI_FLAGS:
            gui_requested = True
            continue

        if argument in MCP_FLAGS:
            os.environ["LINUXTOYS_MCP"] = "1"
            continue

        environment_variable = launch_flags.get(argument)
        if environment_variable:
            os.environ[environment_variable] = "1"
        else:
            remaining_args.append(argument)

    sys.argv = remaining_args
    return gui_requested


def is_interactive_terminal():
    """Return True when both stdin and stdout are attached to a terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def resolve_default_interface(gui_requested):
    """Choose the interface when the user did not pick a CLI action.

    - ``--gui`` forces the GUI and only accepts external requests
      (URI or package file) as extra arguments.
    - A bare ``linuxtoys`` opens the TUI when running in a terminal.
      Without a terminal (desktop launchers) it falls back to the GUI.
    - Explicit ``EASY_CLI``/``UPD_SERVICE`` environments are respected.
    """
    global tui_requested
    arguments = sys.argv[1:]

    if gui_requested:
        if any(argument.startswith("-") for argument in arguments):
            print("Error: --gui cannot be combined with CLI options.")
            sys.exit(2)
        os.environ.pop("EASY_CLI", None)
        return

    if arguments:
        return

    if os.environ.get("EASY_CLI") == "1" or os.environ.get("UPD_SERVICE") == "1":
        return

    if is_interactive_terminal():
        sys.argv.append("--tui")
        tui_requested = True


if __name__ == "__main__":
    gui_requested = configure_launch_flags()
    resolve_default_interface(gui_requested=gui_requested)

    # LinuxToys install URIs and supported local package files are graphical
    # activation requests, never EASY_CLI install targets.
    if len(sys.argv) == 2 and is_gui_external_request(sys.argv[1]):
        os.environ.pop("EASY_CLI", None)

    # Commands that are intrinsically headless should enter the CLI path even
    # when LinuxToys was launched directly rather than through a CLI wrapper.
    if len(sys.argv) == 2 and sys.argv[1] in ("export-manifest", "--export-manifest"):
        os.environ["EASY_CLI"] = "1"

    if len(sys.argv) == 2 and sys.argv[1] in ("-t", "--tui"):
        os.environ["EASY_CLI"] = "1"
        tui_requested = True

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

    # --- MCP SERVER MODE ---
    # The headless MCP agent server must bypass the GUI display check, the CLI
    # update check and the EASY_CLI interface entirely: it is a separate
    # service process that never registers the GUI application identity.
    # An explicit --gui request always wins over the server.
    if os.environ.get('LINUXTOYS_MCP') == '1' and not gui_requested:
        os.environ.pop('EASY_CLI', None)
        from app.mcp_server import run_service
        sys.exit(run_service())

    # --- UPDATE CHECK ---
    # Check for updates only in CLI mode (EASY_CLI=1) and display feedback in the terminal.
    # TUI launches skip it: the TUI owns update checks through its own menu, and
    # its startup must not block on the network before the first screen appears.
    if os.environ.get('EASY_CLI') == '1' and not tui_requested:
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
            print("Run 'linuxtoys' in a terminal to use the TUI, or set EASY_CLI=1 for CLI mode.")
            sys.exit(1)

    # --- SCRIPTS INITIALIZATION ---
    try:
        from app.scripts_loader import initialize_scripts, prepare_scripts

        if cli_mode and not tui_requested:
            # CLI/headless mode keeps synchronous synchronization semantics.
            initialize_scripts()
        else:
            # GUI and TUI startup must never wait for network or git. Each
            # interface starts repository synchronization from its own
            # background worker once it is running.
            prepare_scripts()

    except ImportError:
        pass

    from app import main

    # --- LAUNCH GUI ---
    # This part runs after any CLI-mode updates, or immediately for GUI mode
    sys.exit(main.run())
