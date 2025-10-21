#!/usr/bin/env python3

import os
import sys
import tempfile
from .parser import get_categories, get_all_scripts_recursive
from .update_helper import get_current_version
from .cli_helper import run_manifest_mode, run_update_check_cli, find_script_by_name, run_script


def easy_cli_run_script(script_info):
    """
    Run a LinuxToys script in EASY_CLI mode while preventing any xdg-open calls.
    """

    # Disable zenity to avoid GUI prompts during EASY_CLI execution
    os.environ['DISABLE_ZENITY'] = '1'

    script_path = script_info['path']

    # Create a temporary copy of the script excluding any 'xdg-open' lines
    with open(script_path, "r") as f:
        lines = f.readlines()
    filtered_lines = [line for line in lines if "xdg-open" not in line]

    tmp_file = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8")
    tmp_file.writelines(filtered_lines)
    tmp_file.close()
    temp_script_path = tmp_file.name

    try:
        # Execute the script using run_script
        run_script({"name": script_info["name"], "path": temp_script_path})
    except KeyboardInterrupt:
        # Stop execution if the user presses Ctrl+C
        return 130
    except Exception as e:
        print(f"✗ Error while executing the script: {e}")
        return 1
    finally:
        # Remove the temporary script file
        os.remove(temp_script_path)

    return 0


def confirm_action(prompt_message):
    """Ask the user for confirmation to continue after a failure."""
    try:
        response = input(f"{prompt_message} [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Operation cancelled.")
            return False
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user.")
        return False
    return True


def execute_scripts_with_feedback(scripts_found):
    """Execute each script sequentially and provide CLI feedback."""
    total = len(scripts_found)
    
    for index, script_info in enumerate(scripts_found, 1):
        name = script_info.get("name", os.path.basename(script_info["path"]))
        print(f"\n[{index}/{total}] 🚀 Running: {name}")
        print("=" * 60)

        exit_code = easy_cli_run_script(script_info)

        if exit_code == 0:
            print(f"✓ {name} Completed successfully.")
        elif exit_code == 130:
            print("\n⚠️  Execution interrupted by the user.")
            break
        else:
            print(f"✗ {name} Failed with exit code: {exit_code}.")
            # Ask the user if they want to continue with the remaining scripts
            if not confirm_action("Do you want to continue with the remaining scripts?"):
                print("❌ Operation cancelled.")
                break


def scripts_install(args: list, skip_confirmation, translations):
    """Handle script installation in EASY_CLI mode."""

    # Filter out confirmation flags from the install list
    install_list = [arg for arg in args if arg not in ("-y", "--yes")]

    # Check if any script was specified
    if not install_list:
        print("\n✗ No items specified for installation.\n")
        easy_cli_help_message()
        return 0

    print("🧰 EASY CLI INSTALL MODE")
    print("=" * 60)
    print(f"📜 Requested scripts: {', '.join(install_list)}\n")

    scripts_found_list = []
    scripts_missing = []

    # Search scripts by name
    for script_name in install_list:
        script_info = find_script_by_name(script_name, translations)
        if script_info:
            scripts_found_list.append(script_info)
        else:
            scripts_missing.append(script_name)

    # Report missing scripts
    if scripts_missing:
        print("⚠️  Scripts not found:")
        for name in scripts_missing:
            print(f" - {name}")
        print()

    if not scripts_found_list:
        print("✗ No valid scripts found. Aborting.")
        return 0

    # Calculate column widths for display
    max_file_len = max(len(os.path.basename(s["path"])) for s in scripts_found_list)
    max_name_len = max(len(s["name"]) for s in scripts_found_list)

    # Display found scripts
    print(f"✅ {len(scripts_found_list)} Script(s) found and ready for execution:\n")
    for script_info in scripts_found_list:
        print(f" - {script_info['name']:<{max_name_len}} | {os.path.basename(script_info['path']):<{max_file_len}}")
    print()

    # Ask user to confirm execution
    if skip_confirmation or confirm_action("Confirm script execution?"):
        execute_scripts_with_feedback(scripts_found_list)


def print_script_list(translations):
    """Print all available scripts in a formatted list."""
    scripts = get_all_scripts(translations)

    # Calculate column widths for alignment
    max_file_len = max(len(os.path.splitext(os.path.basename(s["path"]))[0]) for s in scripts)
    max_name_len = max(len(s["name"]) for s in scripts)

    print(f"\nScripts found: {len(scripts)}\n")
    print(f"   {'SCRIPT':<{max_file_len}}     {'NAME':<{max_name_len}}")
    print("=" * (max_file_len + max_name_len + 4))

    for script in sorted(scripts, key=lambda s: s["name"].lower()):
        filename = os.path.splitext(os.path.basename(script["path"]))[0]
        print(f" - {filename:<{max_file_len}} --> {script['name']:<{max_name_len}}")


def get_all_scripts(translations=None):
    """Return a sorted list of all scripts including nested categories."""
    scripts = []
    categories = get_categories(translations) or []

    def add_script(name, path):
        if not name or not path:
            return
        scripts.append({"name": name, "path": path})

    for category in categories:
        path = category.get('path')
        name = category.get('name')
        if not path or not name:
            continue

        if category.get('is_script'):
            add_script(name, path)
        else:
            for script in (get_all_scripts_recursive(path, translations) or []):
                add_script(script.get('name'), script.get('path'))

    # Remove duplicates and sort by name
    unique_scripts = { (s["name"], s["path"]) : s for s in scripts }.values()
    return sorted(unique_scripts, key=lambda s: s["name"])


def easy_cli_help_message():
    """Print usage information for EASY CLI mode."""
    print("LinuxToys EASY CLI Usage:")
    print("=" * 60)
    print("Usage:")
    print("  EASY_CLI=1 python3 run.py --install [option] <item1> <item2> ...")
    print()
    print("Functions:")
    print("  -i, --install              Install selected options")
    print()
    print("Install options:")
    print("  -s, --script       Install specified LinuxToys scripts")
    # print("  -p, --package     Install specified LinuxToys packages")
    # print("  -f, --flatpak     Install specified LinuxToys flatpaks")
    print("  -l, --list         List all available scripts")
    print()
    print("Examples:")
    print("  EASY_CLI=1 python3 run.py --install -s script1 script2")
    print("  EASY_CLI=1 python3 run.py --install -p package1 package2")
    print("  EASY_CLI=1 python3 run.py --install -f flatpak1 flatpak2")
    print()
    print("Other options:")
    print("  -h, --help         Show this help message")
    print("  -m, --manifest     Enable manifest mode features")
    print("  -v, --version      Show version information")
    print("  -y, --yes          Skip confirmation prompts (recommended as the last argument)")
    print()


# --- MAIN EASY CLI HANDLER ---
def easy_cli_handler(translations=None):
    """
    Handles the EASY CLI mode for LinuxToys, parsing command-line arguments and executing actions.

    Supports:
    - Installing scripts (--install -s <script1> <script2> ...)
    - Listing available scripts (--install -l)
    - Checking for updates (update, upgrade, --check-updates)
    - Running in manifest mode (--manifest, -m)
    - Displaying version (-v, --version)
    - Displaying help (-h, --help)

    It also supports developer mode (-D, --DEV_MODE) and optional automatic 
    confirmation flags (-y, --yes) to skip prompts.
    """

    # --- Developer Mode ---
    def dev_check(args):
        dev_flags = ("-D", "--DEV_MODE")
        found = False

        for flag in dev_flags:
            while flag in args:
                args.remove(flag)
                found = True

        if found and not os.environ.get("DEV_MODE"):
            os.environ["DEV_MODE"] = "1"
            try:
                from app.dev_mode import print_dev_mode_banner
                print_dev_mode_banner()
            except ImportError:
                pass

    # --- Skip confirmation flags ---
    def skip_confirmation(args):
        if os.environ.get("DEV_MODE") == "1":
            return True

        skip_flags = ("-y", "--yes")
        found = False
        for flag in skip_flags:
            while flag in args:
                args.remove(flag)
                found = True

        return found

    args = sys.argv[1:]

    dev_check(args)

    if not args:
        print("✗ No arguments provided.\n")
        easy_cli_help_message()
        return 0

    if args[0] in ("-i", "--install"):
        if len(args) < 2:
            print("✗ Missing parameter after '-i' | '--install'.\n")
            print("Use:")
            print("  [-s | --script]    for scripts")
            # print("  [-p | --package]  for packages")
            # print("  [-f | --flatpak]  for flatpaks")
            print("  [-l | --list]      list all available scripts")
            return 0

        if args[1] in ("-s", "--script"):
            scripts_install(args[2:], skip_confirmation(args), translations)
            return 0
        
        # TODO : Implement instalation of pakages and flatpaks
        # elif args[1] in ("-p", "--package"): # Para instalação de pacotes
        #     packages_install(args[2:], skip_confirmation(args), translations)
        #     return 0

        # elif args[1] in ("-f", "--flatpak"): # Para instalação de flatpaks
        #     flatpaks_install(args[2:], skip_confirmation(args), translations)
        #     return 0

        elif args[1] in ("-l", "--list"):
            print_script_list(translations)
            return 0
        
        else:
            print("✗ Invalid parameter after '-i' | '--install'.\n")
            easy_cli_help_message()
            return 0

    elif args[0] in ("-h", "--help", "help"):
        easy_cli_help_message()
        return 0
    
    elif args[0] in ("update", "upgrade", "check-updates", "update-check", "--check-updates"):
        return 1 if run_update_check_cli(translations) else 0
    
    elif args[0] in ("--manifest", "-m"):
        return run_manifest_mode(translations)
    
    elif args[0] in ("-v", "--version"):
        print(f"LinuxToys {get_current_version()}")
        return 0
    
    else:
        print(f"\n✗ Unknown action: {args[0]} \n")
        easy_cli_help_message()
        return 0
