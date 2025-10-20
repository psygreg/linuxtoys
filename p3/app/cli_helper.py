#!/usr/bin/env python3
"""
LinuxToys CLI Helper Module

This module provides command-line interface functionality for LinuxToys, allowing IT staff 
and technicians to automate installations using manifest files.

Key Features:
- Automatic detection and installation of system packages
- Automatic detection and installation of flatpaks
- Execution of LinuxToys scripts
- Custom manifest file support with validation
- Cross-platform package manager support (apt, dnf, pacman, zypper, rpm-ostree)

CLI Usage:
    LT_MANIFEST=1 python3 run.py [options]

Options:
    <no arguments>          - Use default 'manifest.txt' in current directory
    <manifest_path>         - Use specified manifest file
    check-updates           - Check for LinuxToys updates
    --help, -h              - Show usage information

Manifest File Format:
    - First line must be: # LinuxToys Manifest File
    - List items one per line (scripts, packages, or flatpaks)
    - Lines starting with # are comments
    - Empty lines are ignored
    - Priority: Scripts > Packages > Flatpaks

Example Manifest:
    # LinuxToys Manifest File
    # Install system packages
    vim
    htop
    # Install flatpaks
    org.mozilla.firefox
    # Run LinuxToys scripts
    script-name
"""

import os
import sys
import subprocess
import shutil
from .parser import get_categories, get_all_scripts_recursive
from .compat import get_system_compat_keys, script_is_compatible, is_containerized, script_is_container_compatible
from .update_helper import run_update_check
from .reboot_helper import check_ostree_pending_deployments


def get_os_info():
    """
    Parse /etc/os-release to get distribution information.
    Returns a dict with ID, ID_LIKE, and other OS information.
    """
    os_info = {}
    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os_info[key] = value
    except FileNotFoundError:
        # Fallback for systems without /etc/os-release
        pass
    return os_info


def check_package_exists(package_name):
    """
    Check if a package exists in the system's package repositories.
    Returns True if package exists, False otherwise.
    """
    os_info = get_os_info()
    id_val = os_info.get('ID', '')
    id_like = os_info.get('ID_LIKE', '')
    
    try:
        # Check for rpm-ostree systems first
        if shutil.which('rpm-ostree'):
            # Use dnf to search since rpm-ostree uses DNF repos
            result = subprocess.run(['dnf', 'search', '--quiet', package_name], 
                                  capture_output=True, text=True, timeout=30)
            return result.returncode == 0 and package_name in result.stdout
            
        # Debian/Ubuntu systems
        elif (('debian' in id_like or 'ubuntu' in id_like or 
               id_val in ['debian', 'ubuntu']) and 
              shutil.which('apt-cache')):
            result = subprocess.run(['apt-cache', 'search', '--names-only', f'^{package_name}$'], 
                                  capture_output=True, text=True, timeout=30)
            return result.returncode == 0 and result.stdout.strip() != ""
            
        # Arch-based systems
        elif ((id_val in ['arch', 'cachyos'] or 
               'arch' in id_like or 'archlinux' in id_like) and 
              shutil.which('pacman')):
            result = subprocess.run(['pacman', '-Ss', f'^{package_name}$'], 
                                  capture_output=True, text=True, timeout=30)
            return result.returncode == 0 and result.stdout.strip() != ""
            
        # Fedora/RHEL systems
        elif (('rhel' in id_like or 'fedora' in id_like or 
               'fedora' in id_val) and 
              shutil.which('dnf')):
            result = subprocess.run(['dnf', 'search', '--quiet', package_name], 
                                  capture_output=True, text=True, timeout=30)
            return result.returncode == 0 and package_name in result.stdout
            
        # openSUSE systems
        elif (('suse' in id_like or 'suse' in id_val) and shutil.which('zypper')):
            result = subprocess.run(['zypper', 'search', '--exact-match', package_name], 
                                  capture_output=True, text=True, timeout=30)
            return result.returncode == 0 and result.stdout.strip() != ""
            
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
        pass
        
    return False


def check_flatpak_exists(flatpak_name):
    """
    Check if a flatpak exists in available repositories.
    Returns True if flatpak exists, False otherwise.
    """
    if not shutil.which('flatpak'):
        return False
        
    try:
        # Search for exact match in flatpak remotes
        result = subprocess.run(['flatpak', 'search', '--columns=application', flatpak_name], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            # Check if flatpak_name exactly matches any of the application IDs
            for line in result.stdout.strip().split('\n'):
                if line.strip() == flatpak_name:
                    return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
        pass
        
    return False


def install_package(package_name):
    """
    Install a package using the system's package manager.
    Returns True if successful, False otherwise.
    """
    try:
        # Create a temporary script to install the package using linuxtoys.lib functions
        lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs', 'linuxtoys.lib')
        
        script_content = f'''#!/bin/bash
source "{lib_path}"
_packages=("{package_name}")
_install_
'''
        
        # Execute the installation script
        result = subprocess.run(['bash', '-c', script_content], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Successfully installed package: {package_name}")
            return True
        else:
            print(f"✗ Failed to install package: {package_name}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error installing package {package_name}: {e}")
        return False


def install_flatpak(flatpak_name):
    """
    Install a flatpak using the linuxtoys.lib _flatpak_ function.
    Returns True if successful, False otherwise.
    """
    try:
        # Create a temporary script to install the flatpak using linuxtoys.lib functions
        lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs', 'linuxtoys.lib')
        
        script_content = f'''#!/bin/bash
source "{lib_path}"
_flatpaks=("{flatpak_name}")
_flatpak_
'''
        
        # Execute the installation script
        result = subprocess.run(['bash', '-c', script_content], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Successfully installed flatpak: {flatpak_name}")
            return True
        else:
            print(f"✗ Failed to install flatpak: {flatpak_name}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error installing flatpak {flatpak_name}: {e}")
        return False


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

    # Disable zenity for CLI execution
    # This prevents GUI dialogs from appearing during script execution
    # We handle user prompts via CLI instead
    os.environ['DISABLE_ZENITY'] = '1'

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
    """
    print("LinuxToys Update Checker")
    print("=" * 40)
    
    # Run update check with verbose output and no dialog
    return run_update_check(show_dialog=False, verbose=True, translations=translations)


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



def ask_continue_on_failure():
    """ Pergunta ao usuário se deseja continuar após falha """
    try:
        response = input("Continue com os itens restantes? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("Execução interrompida.")
            return False
    except KeyboardInterrupt:
        print("\nExecução interrompida.")
        return False
    return True

def execute_scripts_with_feedback(scripts_found):
    total = len(scripts_found)
    
    for index, script_info in enumerate(scripts_found, 1):
        name = script_info.get("name", os.path.basename(script_info["path"]))
        print(f"\n[{index}/{total}] 🚀 Executando: {name}")
        print("=" * 60)

        exit_code = run_script(script_info)

        if exit_code == 0:
            print(f"✓ {name} concluído com sucesso.")
        else:
            print(f"✗ {name} falhou com código {exit_code}.")
            
            # Pergunta se o usuário quer continuar com os itens restantes
            if not ask_continue_on_failure():
                break


def scripts_install(args:list, translations):

    # if "-y" in args or "--yes" in args:
    #     increase_privileges()

    # Filtra a lista de scripts removendo os flags de confirmação
    install_list = [arg for arg in args if arg not in ("-y", "--yes")]

    # Verifica se algum script foi especificado
    if not install_list:
        print("✗ Nenhum item especificado para instalação.\n")
        print("Use: ")
        print("   EASY_CLI=1 python3 run.py --install [option] <item1> <item2> ...")
        return 0  # Interrompe o fluxo normal do programa

    print("🧰 EASY CLI INSTALL MODE")
    print("=" * 60)
    print(f"📜 Scripts solicitados: {', '.join(install_list)}\n")

    scripts_found_list = []
    scripts_missing = []

    # Busca scripts com find_script_by_name()
    for script_name in install_list:
        script_info = find_script_by_name(script_name, translations)

        if script_info:
            scripts_found_list.append(script_info)
        else:
            scripts_missing.append(script_name)

    # Relatório de scripts não encontrados
    if scripts_missing:
        print("⚠️ Scripts não encontrados:")
        for name in scripts_missing:
            print(f" - {name}")
        print()

    if not scripts_found_list:
        print("✗ Nenhum script válido encontrado. Abortando.")
        return True

    # Relatório dos scripts encontrados
    print(f"✅ {len(scripts_found_list)} script(s) encontrados e prontos para execução:\n")
    for script_info in scripts_found_list:
        print(f" - {script_info['name']} | {os.path.basename (script_info['path'])}")
    print()

    execute_scripts_with_feedback(scripts_found_list)

    
def easy_cli_help_mansage():
    """
    Print usage information for EASY CLI mode.

    To use it with the source code, run the following command:
    #### EASY_CLI=1 SCRIPT_DIR=[path/to/lunuxtoys/p3] python3 run.py --install [option] <item1> <item2> ...

    """
    print("LinuxToys EASY CLI Usage:")
    print("=" * 60)
    print("Usage:")
    print("  EASY_CLI=1 python3 run.py --install [option] <item1> <item2> ...")
    print()
    print("Install options:")
    print("  -s, --script       Install specified LinuxToys scripts")
    print("  -p, --package      Install specified system packages")
    print("  -f, --flatpak      Install specified Flatpak packages")
    print()
    print("Examples:")
    print("  EASY_CLI=1 python3 run.py --install -s script1 script2")
    print("  EASY_CLI=1 python3 run.py --install -p package1 package2")
    print("  EASY_CLI=1 python3 run.py --install -f flatpak1 flatpak2")
    print()
    print("Other options:")
    print("  -h, --help         Show this help message")
    print("  -m, --manifest     Enable manifest mode features")
    print()

    
        
def easy_cli_handler(translations=None):

    """
    Main function for EASY CLI mode.
    """

    args = sys.argv[1:]


    if not args:
        print("✗ Nenhum argumento fornecido.\n")
        easy_cli_help_mansage()
        return 0
    
    if args[0] in ("-i", "--install"):
        if args[1] in ("-s", "--script"): # Para instalação de scripts
            scripts_install(args[2:], translations)
            return 0

        # TODO : Implementar instalação de pacotes e flatpaks
        # elif args[1] in ("-p", "--package"): # Para instalação de pacotes
        #     packages_install(args[2:], translations)
        #     return 0

        # elif args[1] in ("-f", "--flatpak"): # Para instalação de flatpaks
        #     flatpaks_install(args[2:], translations)
        #     return 0

        else:
            print("✗ Parâmetro inválido após '--install'. \n ")
            print("Use:")
            print("  [-s | --script] for scripts")
            print("  [-p | --package] for pacotes")
            print("  [-f | --flatpak] for flatpaks")
            return 0
        

    elif args[0] in ("-h", "--help", "help"):
        easy_cli_help_mansage()
        return 0
    
    elif args[0] in ("check-updates", "update-check", "--check-updates"):
        return 1 if run_update_check_cli(translations) else 0
    
    elif args[0] in ("--manifest", "-m"):
        # Run in CLI mode using manifest.txt
        return run_manifest_mode(translations)

    else:
        print(f"\n✗ Ação desconhecida: {args[0]} \n")
        easy_cli_help_mansage()
        return 0
    


def print_cli_usage():
    """
    Print usage information for CLI mode.
    """
    print("LinuxToys CLI Usage:")
    print("=" * 40)
    print("LT_MANIFEST=1 python3 run.py [options]")
    print()
    print("Options:")
    print("  <no arguments>           - Use default 'manifest.txt' in current directory")
    print("  <manifest_path>          - Use specified manifest file")
    print("  check-updates            - Check for LinuxToys updates")
    print("  update-check             - Check for LinuxToys updates")
    print("  --check-updates          - Check for LinuxToys updates")
    print("  --help, -h               - Show this help message")
    print()
    print("Manifest File Format:")
    print("  - First line must be: # LinuxToys Manifest File")
    print("  - List items one per line (scripts, packages, or flatpaks)")
    print("  - Lines starting with # are comments")
    print("  - Empty lines are ignored")
    print()
    print("Examples:")
    print("  LT_MANIFEST=1 python3 run.py")
    print("  LT_MANIFEST=1 python3 run.py /path/to/my-manifest.txt")
    print("  LT_MANIFEST=1 python3 run.py check-updates")


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
    # Parse command-line arguments
    manifest_path = 'manifest.txt'  # Default manifest path
    
    # If LT_MANIFEST != "1", it means the script is running in EASY_CLI mode.
    if os.environ.get("LT_MANIFEST") != "1":
        if len(sys.argv) > 2:
            arg = sys.argv[2]
            
            # Check for help request
            if arg in ['--help', '-h', 'help']:
                print_cli_usage()
                return 0
            
            # Check if user wants to run update check
            elif arg in ['check-updates', 'update-check', '--check-updates']:
                return 1 if run_update_check_cli(translations) else 0
            
            # Otherwise, treat the argument as a manifest file path
            else:
                manifest_path = arg
    
    else:
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            
            # Check for help request
            if arg in ['--help', '-h', 'help']:
                print_cli_usage()
                return 0
            
            # Check if user wants to run update check
            elif arg in ['check-updates', 'update-check', '--check-updates']:
                return 1 if run_update_check_cli(translations) else 0
            
            # Otherwise, treat the argument as a manifest file path
            else:
                manifest_path = arg
    
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

    print(f"Found {len(script_names)} script(s) in manifest:")
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
    
    for script_name in script_names:
        script_info = find_script_by_name(script_name, translations)
        
        if script_info is None:
            # Script not found, check if it's a package or flatpak
            print(f"Script '{script_name}' not found, checking if it's a package or flatpak...")
            
            # First check if it's a package (preferred over flatpak)
            if check_package_exists(script_name):
                print(f"✓ Found package: {script_name}")
                packages_to_install.append(script_name)
                continue
            
            # If not a package, check if it's a flatpak
            elif check_flatpak_exists(script_name):
                print(f"✓ Found flatpak: {script_name}")
                flatpaks_to_install.append(script_name)
                continue
            
            # Neither script, package, nor flatpak found
            print(f"Warning: '{script_name}' not found as script, package, or flatpak. Skipping.")
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

    # Ask for confirmation
    try:
        response = input("Continue? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("Operation cancelled.")
            return 0
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 0

    # Execute scripts and install packages/flatpaks sequentially
    failed_items = []
    current_item = 0
    
    # Install packages first
    for package in packages_to_install:
        current_item += 1
        print(f"\n[{current_item}/{total_items}] Installing package: {package}")
        print("=" * 60)
        
        success = install_package(package)
        
        if not success:
            failed_items.append(('PACKAGE', package, 1))
            print(f"Package '{package}' installation failed")
            
            # Ask if user wants to continue on failure
            try:
                response = input("Continue with remaining items? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Execution stopped.")
                    break
            except KeyboardInterrupt:
                print("\nExecution stopped.")
                break
    
    # Install flatpaks second
    for flatpak in flatpaks_to_install:
        current_item += 1
        print(f"\n[{current_item}/{total_items}] Installing flatpak: {flatpak}")
        print("=" * 60)
        
        success = install_flatpak(flatpak)
        
        if not success:
            failed_items.append(('FLATPAK', flatpak, 1))
            print(f"Flatpak '{flatpak}' installation failed")
            
            # Ask if user wants to continue on failure
            try:
                response = input("Continue with remaining items? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Execution stopped.")
                    break
            except KeyboardInterrupt:
                print("\nExecution stopped.")
                break
    
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
