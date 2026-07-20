#!/usr/bin/env python3
"""
LinuxToys Manifest Helper Module

This module provides manifest file functionality for LinuxToys, allowing IT staff 
and technicians to automate installations using manifest files.
"""

import os
import sys
import subprocess
import shutil
import asyncio
import argparse
import re
from .parser import get_categories, get_all_scripts_recursive
from .compat import get_system_compat_keys, script_is_compatible, is_containerized, script_is_container_compatible
from .reboot_helper import check_ostree_pending_deployments
from .updater.update_helper import UpdateHelper


PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+_.:@-]*$")
MANIFEST_ITEM_MAX_LENGTH = 256
CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x1f\x7f]")
ALLOWED_LIBRARY_FUNCTIONS = frozenset({'pkg_install', 'pkg_flat'})
FLATPAK_ID_RE = re.compile(
    r"^[A-Za-z][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*){2,}(?:/[A-Za-z0-9_.-]+){0,2}$"
)


def _validate_script_dir():
    """Validate the SCRIPT_DIR inherited from the LinuxToys entry point."""
    script_dir = os.environ.get("SCRIPT_DIR")
    if not script_dir:
        raise RuntimeError(
            "SCRIPT_DIR is not set. Run the manifest helper through linuxtoys.py."
        )

    lib_path = os.path.join(script_dir, "libs", "linuxtoys.lib")
    if not os.path.isfile(lib_path):
        raise RuntimeError(f"LinuxToys library not found at: {lib_path}")

    return script_dir


def _run_library_function(function_name, arguments):
    """Invoke an approved linuxtoys.lib function without shell-parsing manifest data."""
    if function_name not in ALLOWED_LIBRARY_FUNCTIONS:
        raise ValueError(f"disallowed library function: {function_name}")

    _validate_script_dir()

    # The function name comes only from the internal allowlist. Manifest values
    # are positional parameters and are never inserted into shell code.
    script_content = f'''set -e
set -o pipefail
: "${{SCRIPT_DIR:?SCRIPT_DIR is not set}}"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
{function_name} "$@"
'''
    interactive = os.environ.get("EASY_CLI") == "1"
    return subprocess.run(
        ['bash', '-c', script_content, 'manifest-helper', *arguments],
        stdin=sys.stdin if interactive else None,
        stdout=sys.stdout if interactive else subprocess.PIPE,
        stderr=sys.stderr if interactive else subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )



def valid_manifest_value(value):
    """Reject values that should never be interpreted as manifest identifiers."""
    return (
        bool(value)
        and len(value) <= MANIFEST_ITEM_MAX_LENGTH
        and value == value.strip()
        and not value.startswith('-')
        and not CONTROL_CHARACTER_RE.search(value)
    )


def valid_package_name(package_name):
    """Reject malformed package names before querying a package manager."""
    return valid_manifest_value(package_name) and bool(PACKAGE_NAME_RE.fullmatch(package_name))


def valid_flatpak_id(flatpak_name):
    """Validate a Flatpak application ID, optionally including branch/architecture."""
    return valid_manifest_value(flatpak_name) and bool(FLATPAK_ID_RE.fullmatch(flatpak_name))


def check_package_exists(package_name):
    """Use LinuxToys distro detection to validate repository availability."""
    if not valid_package_name(package_name):
        return False

    _validate_script_dir()

    checks = r''': "${SCRIPT_DIR:?SCRIPT_DIR is not set}"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
sysdetect
package="$1"
if is_debian || is_ubuntu; then
    apt-cache show -- "$package" >/dev/null 2>&1
elif is_arch || is_cachy; then
    pacman -Si -- "$package" >/dev/null 2>&1 || { command -v paru >/dev/null && paru -Si -- "$package" >/dev/null 2>&1; }
elif is_ostree || is_fedora || is_rhel; then
    dnf -q repoquery --available -- "$package" >/dev/null 2>&1 || dnf -q list --available "$package" >/dev/null 2>&1
elif is_suse; then
    zypper --non-interactive search --match-exact --type package -- "$package" 2>/dev/null | grep -Eq "^i? \\|[[:space:]]*$package[[:space:]]*\\|"
elif is_solus; then
    eopkg list-available 2>/dev/null | awk '{print $1}' | grep -Fxq -- "$package"
else
    exit 2
fi
'''
    try:
        result = subprocess.run(
            ['bash', '-c', checks, 'manifest-helper', package_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=45,
            env=os.environ.copy(),
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


async def check_flatpak_exists_async(flatpak_name):
    """Check for an exact Flatpak application ID in configured remotes."""
    if not valid_flatpak_id(flatpak_name) or not shutil.which('flatpak'):
        return False

    base_id = flatpak_name.split('/', 1)[0]
    try:
        process = await asyncio.create_subprocess_exec(
            'flatpak', 'remote-info', 'flathub', base_id,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(process.communicate(), timeout=30)
        if process.returncode == 0:
            return True

        process = await asyncio.create_subprocess_exec(
            'flatpak', 'search', '--columns=application', base_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=30)
        return process.returncode == 0 and base_id in stdout.decode().splitlines()
    except (asyncio.TimeoutError, OSError):
        return False


async def check_flatpaks_async(flatpak_names):
    return await asyncio.gather(*(check_flatpak_exists_async(name) for name in flatpak_names))


def install_packages(package_names):
    """Install packages in one pkg_install call through linuxtoys.lib."""
    result = _run_library_function('pkg_install', package_names)
    if result.returncode != 0 and result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0


def install_flatpaks(flatpak_names):
    """Install Flatpaks in one pkg_flat call through linuxtoys.lib."""
    result = _run_library_function('pkg_flat', flatpak_names)
    if result.returncode != 0 and result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0


def find_script_by_name(script_name, translations=None):
    """
    Find a script by its name across all categories and root scripts, including nested subcategories.
    Returns the script info dict if found, None otherwise.
    """
    # Check root scripts (those shown as categories)
    categories = get_categories(translations)
    for category in categories:
        if category.get('is_script'):
            # For root scripts, check both the filename and the parsed name
            filename_without_ext = os.path.splitext(os.path.basename(category['path']))[0]
            if (category['name'].lower() == script_name.lower() or 
                filename_without_ext.lower() == script_name.lower()):
                return category

    # Check scripts within categories (including nested subcategories)
    for category in categories:
        if not category.get('is_script'):
            # Use recursive search to find scripts in all subdirectories
            all_scripts = get_all_scripts_recursive(category['path'], translations)
            for script in all_scripts:
                filename_without_ext = os.path.splitext(os.path.basename(script['path']))[0]
                if (script['name'].lower() == script_name.lower() or 
                    filename_without_ext.lower() == script_name.lower()):
                    return script

    return None


async def find_script_by_name_async(script_name, translations=None):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, find_script_by_name, script_name, translations)


def load_manifest(manifest_path='manifest.txt'):
    """
    Load script names from a manifest file.
    Validates that the first line is '# LinuxToys Manifest File' to confirm it's a valid manifest.
    Returns a list of script names, one per line.
    """
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest file '{manifest_path}' not found.")
        return []

    script_names = []
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # Validate manifest format by checking first line
            if not lines:
                print(f"Error: Manifest file '{manifest_path}' is empty.")
                return []
                
            first_line = lines[0].strip()
            if first_line != '# LinuxToys Manifest File':
                print(f"Error: '{manifest_path}' is not a valid LinuxToys manifest file.")
                print(f"Expected first line: '# LinuxToys Manifest File'")
                print(f"Found: '{first_line}'")
                return []
            
            # Process the rest of the lines
            for line_num, line in enumerate(lines[1:], 2):  # Start from line 2
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    if not valid_manifest_value(line):
                        print(f"Error: unsafe or malformed manifest entry on line {line_num}: {line!r}")
                        return []
                    script_names.append(line)
                    
    except Exception as e:
        print(f"Error reading manifest file '{manifest_path}': {e}")
        return []

    return script_names


def run_script(script_info):
    """
    Execute a single script and return its exit code.
    In developer mode, performs dry-run validation instead of execution.
    """
    # Check if we should dry-run instead of execute

    try:
        from .dev_mode import should_dry_run_scripts, dry_run_script
        if should_dry_run_scripts():
            print(f"🧪 DRY-RUN MODE: Validating script instead of executing")
            dry_run_result = dry_run_script(script_info['path'])
            # Return 0 if validation passed, 1 if failed
            return 0 if dry_run_result['syntax_valid'] and dry_run_result['dependencies_valid'] else 1
    except ImportError:
        pass  # dev_mode not available, continue with normal execution
    
    print(f"Running script: {script_info['name']} ({script_info['path']})")
    print("-" * 50)
    
    try:
        # Check if EASY_CLI mode is enabled
        if os.environ.get("EASY_CLI") == "1":
            result = subprocess.run(['bash', script_info['path']],
                                    stdin=sys.stdin,
                                    stdout=sys.stdout,
                                    stderr=sys.stderr,
                                    check=True)

        else:
            # Execute the script with bash, similar to how the GUI does it
            result = subprocess.run(['bash', script_info['path']], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.STDOUT, 
                                universal_newlines=True)
        
        # Print the output
        if result.stdout:
            print(result.stdout)
        
        print(f"\n--- Script finished with exit code: {result.returncode} ---")
        return result.returncode
        
    except Exception as e:
        print(f"Error executing script '{script_info['name']}': {e}")
        return 1


def run_update_check_cli(translations=None):
    """
    CLI function to check for updates.

    Returns:
        bool: True when an update is available, False otherwise.
    """
    print("LinuxToys Update Checker\n")
    
    # Run update check with verbose output and no dialog
    _check = UpdateHelper()
    update_available = _check._update_available()
    if update_available:
        print(f"⚡️ A new version {_check._latest_ver.get('tag_name', '')} of LinuxToys is available.\n")
        print(_check._latest_ver.get('body', 'No changelog available.'), '\n')
        
        # In headless mode (UPD_SERVICE=1), automatically accept the update
        if os.environ.get('UPD_SERVICE') == '1':
            print("Running in headless updater service mode. Automatically applying update...")
            resp = 'y'
        else:
            # In interactive mode, prompt the user
            try:
                resp = input(">>> Do you want to update to the latest version? [y/N]: ").strip().lower()
            except EOFError:
                # If input fails (no terminal), default to 'n' to avoid errors
                print("No terminal available. Update declined.")
                resp = 'n'
        
        if resp == 'y':
            try:
                subprocess.run(['sh', '-c', 'curl -fsSL https://linux.toys/install.sh | bash'], check=True)
            except Exception as e:
                print(f"✗ An error occurred during the update process.\n{str(e)}")
    else:
        print("✓ It's already on the latest available version.")
    return update_available


def check_ostree_deployment_cli(translations=None):
    """
    CLI function to check for pending ostree deployments and handle reboot requirement.
    
    Returns:
        bool: True if user chose to continue despite pending deployments, 
              False if user chose to exit/reboot
    """
    print("Checking for pending system updates...")
    
    if not check_ostree_pending_deployments():
        return True  # No pending deployments, continue normally
    
    # Use translations if available, fallback to English
    title = translations.get('ostree_deployment_title', 'Pending System Updates') if translations else 'Pending System Updates'
    message = translations.get('ostree_deployment_message', 
        'Your system has pending updates that require a reboot to complete. You must reboot your computer to apply these changes before installing additional features.'
    ) if translations else 'Your system has pending updates that require a reboot to complete. You must reboot your computer to apply these changes before installing additional features.'
    
    reboot_now_text = translations.get('reboot_now_btn', 'Reboot Now') if translations else 'Reboot Now'
    reboot_later_text = translations.get('reboot_later_btn', 'Reboot Later') if translations else 'Reboot Later'
    
    print("\n" + "=" * 60)
    print(f"WARNING: {title.upper()}")
    print("=" * 60)
    print(message)
    print()
    print("Options:")
    print(f"  1. {reboot_now_text} (recommended)")
    print(f"  2. Exit LinuxToys and {reboot_later_text.lower()}")
    print("  3. Continue anyway (not recommended)")
    print()
    
    while True:
        try:
            choice = input("Please choose an option [1/2/3]: ").strip()
            
            if choice == '1':
                # Attempt to reboot the system
                print("Initiating system reboot...")
                try:
                    subprocess.run(['systemctl', 'reboot'], check=True)
                    return False  # This line shouldn't be reached if reboot succeeds
                except subprocess.CalledProcessError as e:
                    print(f"Error: Failed to initiate reboot: {e}")
                    print("Please reboot manually using your system's power menu.")
                    return False
                except Exception as e:
                    print(f"Error: An error occurred while trying to reboot: {e}")
                    print("Please reboot manually using your system's power menu.")
                    return False
                    
            elif choice == '2':
                # Exit the application
                print(f"Exiting LinuxToys. Please reboot your system and try again.")
                return False
                
            elif choice == '3':
                # Continue despite warning
                print("Warning: Continuing without rebooting may cause issues.")
                print("Some scripts may not work correctly until you reboot.")
                return True
                
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
                
        except KeyboardInterrupt:
            print("\n\nOperation cancelled. Exiting LinuxToys.")
            return False
        except EOFError:
            print("\n\nInput ended. Exiting LinuxToys.")
            return False



def parse_manifest_arguments(argv=None):
    """Parse manifest-mode CLI arguments."""
    parser = argparse.ArgumentParser(add_help=False, prog='linuxtoys')
    parser.add_argument('manifest_path', nargs='?', default='manifest.txt')
    parser.add_argument('--check-updates', action='store_true')
    parser.add_argument('--yes', '-y', action='store_true')
    parser.add_argument('--help', '-h', action='store_true')
    args, unknown = parser.parse_known_args(argv)
    if args.manifest_path in {'check-updates', 'update-check'}:
        args.check_updates = True
        args.manifest_path = 'manifest.txt'
    if unknown:
        raise ValueError(f"unrecognized argument(s): {' '.join(unknown)}")
    return args


def print_cli_usage():
    """
    Print usage information for CLI mode.
    """
    print("LinuxToys CLI Usage:")
    print("=" * 40)
    print("LT_MANIFEST=1 python3 linuxtoys.py [options]")
    print()
    print("Options:")
    print("  <no arguments>           - Use default 'manifest.txt' in current directory")
    print("  <manifest_path>          - Use specified manifest file")
    print("  check-updates            - Check for LinuxToys updates")
    print("  update-check             - Check for LinuxToys updates")
    print("  --check-updates          - Check for LinuxToys updates")
    print("  --yes, -y                - Skip confirmation")
    print("  --help, -h               - Show this help message")
    print()
    print("Manifest File Format:")
    print("  - First line must be: # LinuxToys Manifest File")
    print("  - List items one per line (scripts, packages, or flatpaks)")
    print("  - Lines starting with # are comments")
    print("  - Empty lines are ignored")
    print()
    print("Examples:")
    print("  LT_MANIFEST=1 python3 linuxtoys.py")
    print("  LT_MANIFEST=1 python3 linuxtoys.py /path/to/my-manifest.txt")
    print("  LT_MANIFEST=1 python3 linuxtoys.py check-updates")


def run_manifest_mode(translations=None):
    """
    Main function for CLI manifest mode.
    Loads the manifest, finds scripts, checks compatibility, and runs them sequentially.
    
    Command-line usage:
    - No arguments: uses default 'manifest.txt' in current directory
    - check-updates/update-check/--check-updates: runs update check
    - --help/-h: shows usage information
    - <manifest_path>: uses specified manifest file path
    """
    try:
        args = parse_manifest_arguments(sys.argv[1:])
    except ValueError as exc:
        print(f"Error: {exc}")
        print_cli_usage()
        return 2

    if args.help:
        print_cli_usage()
        return 0
    if args.check_updates:
        return 1 if run_update_check_cli(translations) else 0

    manifest_path = args.manifest_path

    print("LinuxToys CLI Manifest Mode")
    print("=" * 40)
    
    # Display which manifest file is being used
    if manifest_path != 'manifest.txt':
        print(f"Using manifest file: {manifest_path}")
        print()
    
    # Check for pending ostree deployments on compatible systems
    system_compat_keys = get_system_compat_keys()
    if {'ostree', 'ublue'} & system_compat_keys:
        if not check_ostree_deployment_cli(translations):
            # User chose to exit or reboot
            return 0
    
    # Load script names from manifest
    script_names = load_manifest(manifest_path)
    if not script_names:
        print("No scripts found in manifest or manifest file is empty.")
        return 1

    print(f"Found {len(script_names)} item(s) in manifest:")
    for name in script_names:
        print(f"  - {name}")
    print()

    # Get system compatibility keys for filtering
    compat_keys = get_system_compat_keys()
    print(f"System compatibility keys: {', '.join(compat_keys) if compat_keys else 'None'}")
    print()

    # Find and validate all scripts first, also check for packages/flatpaks
    scripts_to_run = []
    packages_to_install = []
    flatpaks_to_install = []
    invalid_items = []
    
    # Explicit prefixes avoid ambiguity; unprefixed entries retain auto-detection.
    potential_flatpaks = []
    explicit_packages = []
    explicit_scripts = []
    other_items = []
    for raw_name in script_names:
        prefix, separator, value = raw_name.partition(':')
        if separator and prefix.lower() in {'script', 'package', 'pkg', 'flatpak'}:
            name = value.strip()
            if not name:
                print(f"Error: empty manifest entry '{raw_name}'.")
                invalid_items.append(raw_name)
            elif prefix.lower() == 'script':
                explicit_scripts.append(name)
            elif prefix.lower() in {'package', 'pkg'}:
                explicit_packages.append(name)
            else:
                potential_flatpaks.append(name)
        elif valid_flatpak_id(raw_name):
            potential_flatpaks.append(raw_name)
        else:
            other_items.append(raw_name)

    for package_name in explicit_packages:
        if not valid_package_name(package_name):
            print(f"Error: invalid package name '{package_name}'.")
            invalid_items.append(package_name)
        elif check_package_exists(package_name):
            print(f"✓ Found package: {package_name}")
            packages_to_install.append(package_name)
        else:
            print(f"Error: package '{package_name}' was not found in available repositories.")
            invalid_items.append(package_name)

    other_items = explicit_scripts + other_items

    # Check flatpaks asynchronously
    if potential_flatpaks:
        print(f"Checking {len(potential_flatpaks)} potential flatpak(s) asynchronously...")
        flatpak_exists_results = asyncio.run(check_flatpaks_async(potential_flatpaks))
        for name, exists in zip(potential_flatpaks, flatpak_exists_results):
            if not valid_flatpak_id(name):
                print(f"Error: invalid Flatpak ID '{name}'.")
                invalid_items.append(name)
            elif exists:
                print(f"✓ Found flatpak: {name}")
                flatpaks_to_install.append(name)
            else:
                print(f"Error: Flatpak '{name}' was not found in configured remotes.")
                invalid_items.append(name)

    # Check other items (scripts and packages)
    for script_name in other_items:
        # Check if it's a script
        script_info = find_script_by_name(script_name, translations)
        
        if script_info is None:
            # Not a script, validate and check it as a system package.
            if not valid_package_name(script_name):
                print(f"Error: unsafe or malformed manifest item '{script_name}'.")
                invalid_items.append(script_name)
                continue
            if check_package_exists(script_name):
                print(f"✓ Found package: {script_name}")
                packages_to_install.append(script_name)
                continue
            
            # Neither script nor package found
            print(f"Error: '{script_name}' is not a LinuxToys script or an available package.")
            invalid_items.append(script_name)
            continue
            
        # Check compatibility for scripts
        if not script_is_compatible(script_info['path'], compat_keys):
            print(f"Warning: Script '{script_name}' is not compatible with this system. Skipping.")
            continue
            
        # Check container compatibility
        if is_containerized() and not script_is_container_compatible(script_info['path']):
            print(f"Warning: Script '{script_name}' is not compatible with containerized systems. Skipping.")
            continue
            
        scripts_to_run.append(script_info)

    if invalid_items:
        print("\nManifest validation failed. Nothing will be executed or installed.")
        print("Rejected item(s):")
        for item in invalid_items:
            print(f"  - {item}")
        return 2

    total_items = len(scripts_to_run) + len(packages_to_install) + len(flatpaks_to_install)
    
    if total_items == 0:
        print("No compatible scripts, packages, or flatpaks found to run/install.")
        return 1

    print(f"Will execute/install {total_items} item(s):")
    for script in scripts_to_run:
        print(f"  - [SCRIPT] {script['name']}")
    for package in packages_to_install:
        print(f"  - [PACKAGE] {package}")
    for flatpak in flatpaks_to_install:
        print(f"  - [FLATPAK] {flatpak}")
    print()

    # Ask for confirmation unless --yes was supplied.
    if not args.yes:
        try:
            response = input("Continue? [y/N]: ").strip().lower()
            if response not in ['y', 'yes']:
                print("Operation cancelled.")
                return 0
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return 0

    # Execute scripts and install packages/flatpaks sequentially
    failed_items = []
    current_item = 0
    
    # Install packages first in one library call.
    if packages_to_install:
        current_item += len(packages_to_install)
        print(f"\nInstalling {len(packages_to_install)} package(s)...")
        print("=" * 60)
        if install_packages(packages_to_install):
            for package in packages_to_install:
                print(f"✓ Successfully installed package: {package}")
        else:
            for package in packages_to_install:
                failed_items.append(('PACKAGE', package, 1))
            print("✗ Package installation failed")

    # Avoid concurrent Flatpak/sudo operations by using one pkg_flat call.
    if flatpaks_to_install:
        current_item += len(flatpaks_to_install)
        print(f"\nInstalling {len(flatpaks_to_install)} Flatpak(s)...")
        print("=" * 60)
        if install_flatpaks(flatpaks_to_install):
            for flatpak in flatpaks_to_install:
                print(f"✓ Successfully installed flatpak: {flatpak}")
        else:
            for flatpak in flatpaks_to_install:
                failed_items.append(('FLATPAK', flatpak, 1))
            print("✗ Flatpak installation failed")

    # Execute scripts last
    for script_info in scripts_to_run:
        current_item += 1
        print(f"\n[{current_item}/{total_items}] Executing script: {script_info['name']}")
        print("=" * 60)
        
        exit_code = run_script(script_info)
        
        if exit_code != 0:
            failed_items.append(('SCRIPT', script_info['name'], exit_code))
            print(f"Script '{script_info['name']}' failed with exit code {exit_code}")
            
            # Ask if user wants to continue on failure
            try:
                response = input("Continue with remaining items? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Execution stopped.")
                    break
            except KeyboardInterrupt:
                print("\nExecution stopped.")
                break

    # Summary
    print("\n" + "=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)
    successful_count = total_items - len(failed_items)
    print(f"Successfully executed/installed: {successful_count}/{total_items} items")
    
    if failed_items:
        print("Failed items:")
        for item_type, item_name, exit_code in failed_items:
            print(f"  - [{item_type}] {item_name} (exit code: {exit_code})")
        return 1
    else:
        print("All scripts executed and packages/flatpaks installed successfully!")
        return 0
