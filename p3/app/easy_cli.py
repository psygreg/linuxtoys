#!/usr/bin/env python3

import os
import sys
import tempfile
import asyncio
from .parser import get_categories, get_all_scripts_recursive
from .updater import __version__
from .manifest_helper import (
    run_manifest_mode, run_update_check_cli, find_script_by_name, 
    run_script, check_package_exists, install_package, 
    check_flatpaks_async, install_flatpaks_async
)
from .dev_mode import is_dev_mode_enabled

def resolve_script_dir():
    """
    Ensure SCRIPT_DIR exists based on the current file's location.
    Searches parent directories until one containing 'libs' is found.
    Sets SCRIPT_DIR to that absolute path.
    Raises FileNotFoundError if no 'libs' directory is found.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))

    while True:
        libs_path = os.path.join(current_dir, "libs")
        if os.path.isdir(libs_path):
            os.environ["SCRIPT_DIR"] = current_dir
            return current_dir

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir

    raise FileNotFoundError(f"'libs' folder not found relative to {__file__}")

def _save_script_to_registry(script_name, transmap_path):
    """Save script execution record to registry."""
    try:
        import datetime
        registry_dir = os.path.expanduser("~/.cache/linuxtoys")
        registry_file = os.path.join(registry_dir, "registry")
        
        # Create directory if it doesn't exist
        os.makedirs(registry_dir, exist_ok=True)
        
        # Read transmap contents
        transmap_contents = ""
        if os.path.exists(transmap_path):
            try:
                with open(transmap_path, "r") as f:
                    transmap_contents = f.read().strip()
            except (IOError, OSError):
                pass
        
        # Format entry with timestamp
        timestamp = datetime.datetime.now().isoformat()
        entry = f"[{timestamp}] Script: {script_name}\n"
        if transmap_contents:
            entry += f"Changes:\n"
            for line in transmap_contents.split("\n"):
                if line.strip():
                    entry += f"  - {line}\n"
        else:
            entry += "Changes: (none)\n"
        entry += "---\n\n"
        
        # Append to registry file
        with open(registry_file, "a") as f:
            f.write(entry)
    except Exception:
        pass  # Silently ignore registry errors

def create_temp_file(script_path):
    """
    Create a temporary script file by filtering out xdg-open calls.
    """

    # Resolve SCRIPT_DIR
    script_dir = resolve_script_dir()

    # Open the original script and set to a list
    with open(script_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    filtered_lines = []
    for line in lines:
        # Ignore lines containing "xdg-open"
        if "xdg-open" in line:
            continue
        # Replace $SCRIPT_DIR
        line = line.replace("$SCRIPT_DIR", script_dir)
        if line.strip().startswith("/libs/"):
            line = line.replace("/libs/", f"{script_dir}/libs/")
        elif " libs/" in line:
            line = line.replace(" libs/", f" {script_dir}/libs/")
        filtered_lines.append(line)

    tmp_file = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8")
    tmp_file.writelines(filtered_lines)
    tmp_file.close()
    temp_file_path = tmp_file.name
    return temp_file_path


def easy_cli_run_script(script_info):
    """
    Run a LinuxToys script in EASY_CLI mode while preventing any xdg-open calls.
    """

    # Check if dev mode is enabled and run the script
    if is_dev_mode_enabled():
        return run_script(script_info)
    
    # Disable zenity to avoid GUI prompts during EASY_CLI execution
    os.environ['DISABLE_ZENITY'] = '1'

    script_path = script_info['path']
    script_name = script_info.get('name', 'unknown')

    # Create a temporary script file
    temp_file_path = create_temp_file(script_path)

    # Clear transmap file for new script execution
    try:
        transmap_path = "/tmp/linuxtoys/transmap"
        with open(transmap_path, "w") as f:
            pass  # Truncate/clear the file
    except (IOError, OSError):
        pass  # Silently ignore if transmap cannot be cleared

    try:
        # Execute the script using run_script
        code = run_script({"name": script_info["name"], "path": temp_file_path})

        # Save to registry and wipe transmap file if script executed successfully
        if code == 0:
            transmap_path = "/tmp/linuxtoys/transmap"
            _save_script_to_registry(script_name, transmap_path)
            try:
                if os.path.exists(transmap_path):
                    os.remove(transmap_path)
            except (IOError, OSError):
                pass  # Silently ignore if transmap cannot be removed

        if code != 0:
            return 1
        
    except KeyboardInterrupt:
        # Stop execution if the user presses Ctrl+C
        return 130
    except Exception as e:
        print(f"✗ Error while executing the script: {e}")
        return 1
    finally:
        # Remove the temporary script file
        os.remove(temp_file_path)

    return code


def confirm_action(prompt_message):
    """Ask the user to confirm an action."""
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

        elif exit_code == 1:
            print(f"✗ {name} Failed with exit code: {exit_code}.")
            
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
        # Heuristic: if it looks like a flatpak, skip script search
        if script_name.count('.') >= 2:
            print(f"⚠️  Skipping script search for '{script_name}' (appears to be a flatpak)")
            scripts_missing.append(f"{script_name} (Flatpak pattern)")
            continue

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

def install_packages_with_feedback(packages_found):
    """Install each package sequentially and provide CLI feedback."""
    
    failed_items = []
    current_item = 0
    total_items = len(packages_found)

    # Ensure SCRIPT_DIR is set correctly
    resolve_script_dir()

    # Install packages first
    for package in packages_found:
        current_item += 1
        print(f"\n[{current_item}/{total_items}] Installing package: {package}")
        print("=" * 60)

        try:
            success = install_package(package)
        except KeyboardInterrupt:
            # Stop execution if the user presses Ctrl+C
            return print("\n⚠️  Execution interrupted by the user.")
        except Exception as e:
            print(f"✗ Error while executing the script: {e}")
            return 1
        
        if not success:
            failed_items.append(('PACKAGE', package, 1))
            print(f"Package '{package}' installation failed")
            
            # Ask if user wants to continue on failure
            if not confirm_action("Do you want to continue with the remaining installations?"):
                print("❌ Operation cancelled.")
                break

def packages_install(args: list, skip_confirmation, translations):
    """Handle package installation in EASY_CLI mode."""

    # Filter out confirmation flags from the install list
    install_to_list = [arg for arg in args if arg not in ("-y", "--yes")]


    if not install_to_list:
        print("\n✗ No items specified for installation.\n")
        easy_cli_help_message()
        return 0
    
    print("🧰 EASY CLI INSTALL MODE")
    print("=" * 60)
    print(f"📜 Requested pakeges: {', '.join(install_to_list)}\n")

    packages_found_list = []
    packages_missing = []

    # Check if Packages exist by name
    for package_name in install_to_list:
        # Heuristic: if it looks like a flatpak, skip package search
        if package_name.count('.') >= 2:
            print(f"⚠️  Skipping package search for '{package_name}' (appears to be a flatpak)")
            packages_missing.append(f"{package_name} (Flatpak pattern)")
            continue

        package_exist = check_package_exists(package_name)
        if package_exist:
            packages_found_list.append(package_name)
        else:
            packages_missing.append(package_name)

    # Report missing packages
    if packages_missing:
        print("⚠️  Packages not found:")
        for name in packages_missing:
            print(f" - {name}")
        print()

    if not packages_found_list:
        print("✗ No valid packages found. Aborting.")
        return 0
    
    # Display found packages
    print(f"✅ {len(packages_found_list)} Package(s) found and ready for installation:\n")
    for package_name in packages_found_list:
        print(f" - {package_name}")
    print()

    # Ask user to confirm execution
    if skip_confirmation or confirm_action("Confirm package installation?"):
        install_packages_with_feedback(packages_found_list)


def install_flatpaks_with_feedback(flatpaks_found):
    """Install flatpaks asynchronously and provide CLI feedback."""
    
    failed_items = []
    total_items = len(flatpaks_found)

    # Ensure SCRIPT_DIR is set correctly
    resolve_script_dir()

    print(f"\nInstalling {total_items} flatpak(s) asynchronously...")
    print("=" * 60)

    try:
        # Run asynchronous installation
        results = asyncio.run(install_flatpaks_async(flatpaks_found))
        
        for flatpak, (success, err_msg) in zip(flatpaks_found, results):
            if success:
                print(f"✓ Successfully installed flatpak: {flatpak}")
            else:
                failed_items.append(('FLATPAK', flatpak, 1))
                print(f"✗ Failed to install flatpak: {flatpak}")
                if err_msg:
                    print(f"Error: {err_msg}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Execution interrupted by the user.")
        return
    except Exception as e:
        print(f"✗ Error during flatpak installation: {e}")
        return 1

    if failed_items:
        print(f"\n⚠️  {len(failed_items)} flatpak installation(s) failed.")


def flatpaks_install(args: list, skip_confirmation, translations):
    """Handle flatpak installation in EASY_CLI mode."""

    # Filter out confirmation flags from the install list
    install_to_list = [arg for arg in args if arg not in ("-y", "--yes")]

    if not install_to_list:
        print("\n✗ No items specified for installation.\n")
        easy_cli_help_message()
        return 0
    
    print("🧰 EASY CLI INSTALL MODE")
    print("=" * 60)
    print(f"📜 Requested flatpaks: {', '.join(install_to_list)}\n")

    flatpaks_found_list = []
    flatpaks_missing = []

    # Check if Flatpaks exist by name asynchronously
    if install_to_list:
        print(f"Checking {len(install_to_list)} flatpak(s) asynchronously...")
        exists_results = asyncio.run(check_flatpaks_async(install_to_list))
        for name, exists in zip(install_to_list, exists_results):
            if exists:
                flatpaks_found_list.append(name)
            else:
                flatpaks_missing.append(name)

    # Report missing flatpaks
    if flatpaks_missing:
        print("⚠️  Flatpaks not found:")
        for name in flatpaks_missing:
            print(f" - {name}")
        print()

    if not flatpaks_found_list:
        print("✗ No valid flatpaks found. Aborting.")
        return 0
    
    # Display found flatpaks
    print(f"✅ {len(flatpaks_found_list)} Flatpak(s) found and ready for installation:\n")
    for flatpak_name in flatpaks_found_list:
        print(f" - {flatpak_name}")
    print()

    # Ask user to confirm execution
    if skip_confirmation or confirm_action("Confirm flatpak installation?"):
        install_flatpaks_with_feedback(flatpaks_found_list)


def smart_install(args: list, skip_confirmation, translations):
    """Handle smart installation - checks for scripts first, then packages."""
    
    # Filter out confirmation flags from the install list
    install_list = [arg for arg in args if arg not in ("-y", "--yes")]

    if not install_list:
        print("\n✗ No items specified for installation.\n")
        easy_cli_help_message()
        return 0
    
    print("🧰 LINUXTOYS CLI SMART INSTALL MODE")
    print("=" * 60)
    print(f"📜 Requested items: {', '.join(install_list)}\n")

    scripts_found_list = []
    packages_to_install = []
    flatpaks_to_install = []
    items_missing = []

    # Identify potential flatpaks
    potential_flatpaks = [item for item in install_list if item.count('.') >= 2]
    other_items = [item for item in install_list if item.count('.') < 2]

    # Check flatpaks asynchronously
    if potential_flatpaks:
        print(f"Checking {len(potential_flatpaks)} potential flatpak(s) asynchronously...")
        exists_results = asyncio.run(check_flatpaks_async(potential_flatpaks))
        for name, exists in zip(potential_flatpaks, exists_results):
            if exists:
                flatpaks_to_install.append(name)
                print(f"✓ Found flatpak: {name}")
            else:
                items_missing.append(name)
                print(f"✗ Flatpak not found: {name}")

    # For other items, decide based on its name pattern
    for item_name in other_items:
        # try to find it as a script first
        script_info = find_script_by_name(item_name, translations)
        if script_info:
            scripts_found_list.append(script_info)
            print(f"✓ Found script: {item_name}")
        else:
            # If not a script, check if it's a package
            package_exist = check_package_exists(item_name)
            if package_exist:
                packages_to_install.append(item_name)
                print(f"✓ Found package: {item_name}")
            else:
                items_missing.append(item_name)
                print(f"✗ Not found: {item_name}")
    
    print()

    # Report missing items
    if items_missing:
        print("⚠️  Items not found:")
        for name in items_missing:
            print(f" - {name}")
        print()

    if not scripts_found_list and not packages_to_install and not flatpaks_to_install:
        print("✗ No valid items found. Aborting.")
        return 0

    # Display summary
    if scripts_found_list:
        max_file_len = max(len(os.path.basename(s["path"])) for s in scripts_found_list)
        max_name_len = max(len(s["name"]) for s in scripts_found_list)
        print(f"📜 {len(scripts_found_list)} Script(s) to execute:\n")
        for script_info in scripts_found_list:
            print(f" - {script_info['name']:<{max_name_len}} | {os.path.basename(script_info['path']):<{max_file_len}}")
        print()

    if packages_to_install:
        print(f"📦 {len(packages_to_install)} Package(s) to install:\n")
        for package_name in packages_to_install:
            print(f" - {package_name}")
        print()

    if flatpaks_to_install:
        print(f"📦 {len(flatpaks_to_install)} Flatpak(s) to install:\n")
        for flatpak_name in flatpaks_to_install:
            print(f" - {flatpak_name}")
        print()

    # Ask user to confirm execution
    if skip_confirmation or confirm_action("Confirm installation?"):
        # Install packages first
        if packages_to_install:
            print("\n" + "=" * 60)
            print("INSTALLING PACKAGES")
            print("=" * 60)
            install_packages_with_feedback(packages_to_install)

        # Install flatpaks second
        if flatpaks_to_install:
            print("\n" + "=" * 60)
            print("INSTALLING FLATPAKS")
            print("=" * 60)
            install_flatpaks_with_feedback(flatpaks_to_install)

        # Execute scripts last
        if scripts_found_list:
            print("\n" + "=" * 60)
            print("EXECUTING SCRIPTS")
            print("=" * 60)
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
    """Return a sorted list of all scripts."""
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
    print("\nLinuxToys CLI Mode Usage:")
    print("=" * 60)
    print("\nUsage:")
    print("  linuxtoys --install [Option] <item1> <item2> ...")
    print("  linuxtoys --install <item1> <item2> ...  (smart mode)")
    # print("  EASY_CLI=1 python3 run.py --install [option] <item1> <item2> ...")
    print()
    print("Functions:")
    print("  -i, --install      Install selected options (scripts, packages)")
    print()
    print("Options:")
    print("  -s, --script       Install specified LinuxToys scripts")
    print("  -p, --package      Install packages from the system package manager")
    print("  -f, --flatpak      Install specified Flatpaks")
    print("  (no option)        Smart mode: checks items by pattern (scripts, packages, flatpaks)")
    print()
    print("Examples:")
    print("  linuxtoys --install --script <script1> <script2>")
    print("  linuxtoys --install --package <package1> <package2>")
    print("  linuxtoys --install --flatpak <flatpak1> <flatpak2>")
    print("  linuxtoys --install <item1> <item2>  (smart mode)")
    # print("  EASY_CLI=1 linuxtoys --install -f <flatpak1> <flatpak2>")
    print()
    print("Other functions:")
    print("  -h, --help         Show this help message")
    print("  -l, --list         List all available scripts")
    print("  -m, --manifest     Enable manifest mode features")
    print("  -v, --version      Show version information")
    print("  -y, --yes          Skip confirmation prompts (recommended as the last argument)")
    print("  update, upgrade    Check for updates and upgrade LinuxToys")
    # print("  -D, --DEV_MODE     Enable developer mode (for scripts debugging)\n    Usage: EASY_CLI=1 python3 run.py -D -i -s <script1>")
    print()


# --- MAIN EASY CLI HANDLER ---
def easy_cli_handler(translations=None):
    """
    Handles the CLI mode for LinuxToys, parsing command-line arguments and executing actions.

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
    
    if args[0][0] == "-" and args[0][1] != "-" and len(args[0]) > 2:
        # Split combined flags (-isy to -i -s -y)
        combined_flags = args[0][1:]
        args = [f"-{flag}" for flag in combined_flags] + args[1:]

    # Check if first argument is incompatible with default --install mode
    incompatible_options = ("-h", "--help", "help", "-l", "--list", "-m", "--manifest",
                           "-v", "--version", "update", "upgrade", "check-updates",
                           "update-check", "--check-updates")
    
    # If first argument is not an incompatible option and not --install, prepend --install
    if args[0] not in ("-i", "--install") and args[0] not in incompatible_options:
        args = ["--install"] + args

    if args[0] in ("-i", "--install"):
        if len(args) < 2:
            print("✗ Missing parameter after '-i' | '--install'.\n")
            print("Use:")
            print("  [-s | --script]    for scripts")
            print("  [-p | --package]  for packages")
            # print("  [-f | --flatpak]  for flatpaks")
            print("  [-l | --list]      list all available scripts")
            print("  [item names]       smart mode (checks scripts first, then packages)")
            return 0

        if args[1] in ("-s", "--script", "--scripts"):
            scripts_install(args[2:], skip_confirmation(args), translations)
            return 0
        
        elif args[1] in ("-p", "--package", "--packages"): # Para instalação de pacotes
            packages_install(args[2:], skip_confirmation(args), translations)
            return 0

        elif args[1] in ("-f", "--flatpak", "--flatpaks"): # Para instalação de flatpaks
            flatpaks_install(args[2:], skip_confirmation(args), translations)
            return 0

        elif args[1] in ("-l", "--list"):
            print_script_list(translations)
            return 0
        
        else:
            # Smart install mode - checks by pattern (scripts, packages, flatpaks)
            smart_install(args[1:], skip_confirmation(args), translations)
            return 0
        
    elif args[0] in ("-l", "--list"):
        print_script_list(translations)
        return 0

    elif args[0] in ("-h", "--help", "help"):
        easy_cli_help_message()
        return 0
    
    elif args[0] in ("update", "upgrade", "check-updates", "update-check", "--check-updates"):
        return 1 if run_update_check_cli(translations) else 0
    
    elif args[0] in ("--manifest", "-m"):
        return run_manifest_mode(translations)
    
    elif args[0] in ("-v", "--version"):
        print(f"LinuxToys {__version__}")
        return 0
    
    else:
        print(f"\n✗ Unknown action: {args[0]} \n")
        easy_cli_help_message()
        return 0
