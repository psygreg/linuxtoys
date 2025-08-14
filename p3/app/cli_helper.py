import os
import sys
import subprocess
from .parser import get_categories, get_scripts_for_category
from .compat import get_system_compat_keys, script_is_compatible


def find_script_by_name(script_name, translations=None):
    """
    Find a script by its name across all categories and root scripts.
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

    # Check scripts within categories
    for category in categories:
        if not category.get('is_script'):
            scripts = get_scripts_for_category(category['path'], translations)
            for script in scripts:
                filename_without_ext = os.path.splitext(os.path.basename(script['path']))[0]
                if (script['name'].lower() == script_name.lower() or 
                    filename_without_ext.lower() == script_name.lower()):
                    return script

    return None


def load_manifest(manifest_path='manifest.txt'):
    """
    Load script names from a manifest file.
    Returns a list of script names, one per line.
    """
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest file '{manifest_path}' not found.")
        return []

    script_names = []
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
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
    """
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


def run_manifest_mode(translations=None):
    """
    Main function for CLI manifest mode.
    Loads the manifest, finds scripts, checks compatibility, and runs them sequentially.
    """
    print("LinuxToys CLI Manifest Mode")
    print("=" * 40)
    
    # Load script names from manifest
    script_names = load_manifest()
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

    # Find and validate all scripts first
    scripts_to_run = []
    for script_name in script_names:
        script_info = find_script_by_name(script_name, translations)
        
        if script_info is None:
            print(f"Warning: Script '{script_name}' not found. Skipping.")
            continue
            
        # Check compatibility
        if not script_is_compatible(script_info['path'], compat_keys):
            print(f"Warning: Script '{script_name}' is not compatible with this system. Skipping.")
            continue
            
        scripts_to_run.append(script_info)

    if not scripts_to_run:
        print("No compatible scripts found to run.")
        return 1

    print(f"Will execute {len(scripts_to_run)} compatible script(s):")
    for script in scripts_to_run:
        print(f"  - {script['name']}")
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

    # Execute scripts sequentially
    failed_scripts = []
    for i, script_info in enumerate(scripts_to_run, 1):
        print(f"\n[{i}/{len(scripts_to_run)}] Executing: {script_info['name']}")
        print("=" * 60)
        
        exit_code = run_script(script_info)
        
        if exit_code != 0:
            failed_scripts.append((script_info['name'], exit_code))
            print(f"Script '{script_info['name']}' failed with exit code {exit_code}")
            
            # Ask if user wants to continue on failure
            try:
                response = input("Continue with remaining scripts? [y/N]: ").strip().lower()
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
    successful_count = len(scripts_to_run) - len(failed_scripts)
    print(f"Successfully executed: {successful_count}/{len(scripts_to_run)} scripts")
    
    if failed_scripts:
        print(f"Failed scripts:")
        for script_name, exit_code in failed_scripts:
            print(f"  - {script_name} (exit code: {exit_code})")
        return 1
    else:
        print("All scripts executed successfully!")
        return 0
