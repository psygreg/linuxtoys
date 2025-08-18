"""
Developer mode utilities for LinuxToys.

This module provides functionality to override compatibility checks and simulate
different system environments for development and testing purposes.

Environment Variables:
- DEV_MODE=1: Enable developer mode (shows all scripts regardless of compatibility)
- COMPAT=<key>: Simulate a specific system (e.g., COMPAT=fedora, COMPAT=arch)
- CONTAINER=1: Simulate container environment (applies container checks)

Features:
- Compatibility override and system simulation
- Container environment simulation and override
- Dry-run script validation (checks parsing and library sourcing)

Usage:
    DEV_MODE=1 python3 run.py                        # Show all scripts, ignore container checks
    DEV_MODE=1 COMPAT=fedora python3 run.py          # Simulate Fedora system, ignore containers
    DEV_MODE=1 CONTAINER=1 python3 run.py            # Show all scripts, simulate container
    DEV_MODE=1 COMPAT=arch CONTAINER=1 python3 run.py # Simulate Arch in container
"""

import os
import re
import subprocess
import tempfile
import glob


def is_dev_mode_enabled():
    """
    Check if developer mode is enabled via DEV_MODE environment variable.
    
    Returns:
        bool: True if DEV_MODE=1, False otherwise
    """
    return os.environ.get('DEV_MODE') == '1'


def get_dev_compat_override():
    """
    Get the compatibility override from COMPAT environment variable.
    
    Returns:
        str or None: The compatibility key to simulate, or None if not set
    """
    return os.environ.get('COMPAT')


def get_dev_container_override():
    """
    Get the container override from CONTAINER environment variable.
    
    Returns:
        str or None: The container simulation setting ('1' to simulate container), 
                     or None if not set
    """
    return os.environ.get('CONTAINER')


def get_simulated_compat_keys():
    """
    Get compatibility keys for the simulated system.
    
    Returns:
        set: Set of compatibility keys for the simulated system,
             or empty set if no simulation is active
    """
    compat_override = get_dev_compat_override()
    if not compat_override:
        return set()
    
    # Map single keys to their full compatibility sets
    compat_map = {
        'debian': {'debian'},
        'ubuntu': {'ubuntu', 'debian'},  # Ubuntu is debian-like
        'arch': {'arch'},
        'archlinux': {'arch'},
        'cachy': {'cachy'},
        'cachyos': {'cachy'},
        'fedora': {'fedora'},
        'rhel': {'fedora'},  # RHEL is fedora-like
        'suse': {'suse'},
        'opensuse': {'suse'},
        'ostree': {'ostree'},
        'ublue': {'ublue'}
    }
    
    key = compat_override.lower()
    return compat_map.get(key, {key})


def should_override_compatibility():
    """
    Check if compatibility checks should be overridden.
    
    Returns:
        bool: True if DEV_MODE is enabled (with or without COMPAT override)
    """
    return is_dev_mode_enabled()


def should_override_container_checks():
    """
    Check if container checks should be overridden.
    
    In developer mode:
    - Without CONTAINER=1: container checks are ignored (always return True for compatibility)
    - With CONTAINER=1: container checks are simulated (follow normal container logic)
    
    Returns:
        bool: True if container checks should be overridden (ignored)
    """
    if not is_dev_mode_enabled():
        return False
    
    # If CONTAINER=1 is set, don't override - simulate container behavior
    container_override = get_dev_container_override()
    if container_override == '1':
        return False
    
    # Default in dev mode: override (ignore) container checks
    return True


def should_simulate_container():
    """
    Check if container environment should be simulated.
    
    Returns:
        bool: True if DEV_MODE=1 and CONTAINER=1 (simulate container environment)
    """
    return is_dev_mode_enabled() and get_dev_container_override() == '1'


def get_effective_compat_keys():
    """
    Get the effective compatibility keys for the current session.
    
    In developer mode:
    - If COMPAT is set: return simulated keys
    - If COMPAT is not set: return all possible keys (show everything)
    
    In normal mode:
    - Return actual system compatibility keys
    
    Returns:
        set: Set of compatibility keys to use for filtering
    """
    if not is_dev_mode_enabled():
        # Normal mode - use actual system keys
        from .compat import get_system_compat_keys
        return get_system_compat_keys()
    
    compat_override = get_dev_compat_override()
    if compat_override:
        # Developer mode with specific system simulation
        return get_simulated_compat_keys()
    else:
        # Developer mode without simulation - show all scripts
        # Return a superset of all possible compatibility keys
        return {
            'debian', 'ubuntu', 'arch', 'cachy', 'fedora', 
            'rhel', 'suse', 'opensuse', 'ostree', 'ublue'
        }


def get_dev_mode_status():
    """
    Get a human-readable status of the current developer mode configuration.
    
    Returns:
        str: Status message describing the current dev mode state
    """
    if not is_dev_mode_enabled():
        return "Developer mode: OFF"
    
    status_parts = ["Developer mode: ON"]
    
    compat_override = get_dev_compat_override()
    container_override = get_dev_container_override()
    
    if compat_override:
        simulated_keys = get_simulated_compat_keys()
        status_parts.append(f"simulating {compat_override}, keys: {sorted(simulated_keys)}")
    else:
        status_parts.append("showing all scripts")
    
    if container_override == '1':
        status_parts.append("simulating container environment")
    else:
        status_parts.append("ignoring container checks")
    
    return f"{status_parts[0]} ({', '.join(status_parts[1:])})"


def get_script_dependencies(script_path):
    """
    Analyze a script to find its dependencies (sourced files and function calls).
    
    Args:
        script_path (str): Path to the script file
        
    Returns:
        dict: Dictionary with 'sources', 'function_calls', and 'variables' lists
    """
    dependencies = {
        'sources': [],
        'function_calls': [],
        'variables': [],
        'errors': []
    }
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find source statements - process line by line to get better context
        lines = content.split('\n')
        sources_found = set()
        
        for line in lines:
            line = line.strip()
            # Skip comments and empty lines
            if line.startswith('#') or not line:
                continue
                
            # Match source statements
            source_match = re.match(r'(?:source|\.)\s+"?([^";\s]+)"?(?:\s|;|$)', line)
            if source_match:
                source_file = source_match.group(1)
                # Skip if it's clearly not a file (contains shell syntax)
                if not any(char in source_file for char in ['(', ')', '[', ']', '&&', '||']):
                    sources_found.add(source_file)
        
        dependencies['sources'] = list(sources_found)
        
        # Find function calls (common LinuxToys functions)
        known_functions = [
            'flatpak_in_lib', 'snap_in_lib', 'dnf_in_lib', 'apt_in_lib',
            'yay_in_lib', 'pacman_in_lib', 'zypper_in_lib', 'rpm_in_lib',
            'ask_for_reboot', 'confirm_action', 'check_internet'
        ]
        
        for func in known_functions:
            if re.search(rf'\b{func}\b', content):
                dependencies['function_calls'].append(func)
        
        # Find variable references to common LinuxToys variables
        known_variables = [
            'LINUXTOYS_LIB', 'HELPERS_LIB', 'OPTIMIZERS_LIB'
        ]
        
        for var in known_variables:
            if re.search(rf'\${var}\b', content):
                dependencies['variables'].append(var)
        
    except Exception as e:
        dependencies['errors'].append(f"Failed to parse script: {str(e)}")
    
    return dependencies


def validate_script_libraries(script_path):
    """
    Validate that all libraries and functions used by a script are available.
    
    Args:
        script_path (str): Path to the script file
        
    Returns:
        dict: Validation results with status and details
    """
    script_dir = os.path.dirname(os.path.abspath(script_path))
    p3_root = os.path.join(script_dir, '..', '..')
    libs_dir = os.path.join(p3_root, 'libs')
    
    validation = {
        'status': 'valid',
        'dependencies': {},
        'missing_sources': [],
        'missing_functions': [],
        'available_libs': [],
        'resolved_sources': [],
        'errors': []
    }
    
    try:
        # Get script dependencies
        dependencies = get_script_dependencies(script_path)
        validation['dependencies'] = dependencies
        
        # Check for available library files
        lib_files = []
        if os.path.exists(libs_dir):
            for file in os.listdir(libs_dir):
                if file.endswith('.lib'):
                    lib_files.append(file)
                    validation['available_libs'].append(os.path.join(libs_dir, file))
        
        # Validate sourced files
        for source_file in dependencies['sources']:
            source_path = source_file
            resolved = False
            
            # Handle variable substitutions
            if '$SCRIPT_DIR' in source_file and ('${' in source_file or '$' in source_file):
                # Handle combined $SCRIPT_DIR with other variables
                if 'lang/' in source_file and ('${langfile}' in source_file or '$langfile' in source_file):
                    # Check if lang directory exists and has files
                    resolved_base = source_file.replace('$SCRIPT_DIR', script_dir)
                    lang_pattern = resolved_base.replace('${langfile}', '*').replace('$langfile', '*')
                    lang_dir = os.path.dirname(lang_pattern)
                    
                    if os.path.exists(lang_dir):
                        lang_files = glob.glob(lang_pattern)
                        if lang_files:
                            # Found matching language files
                            validation['resolved_sources'].append(f"{source_file} -> found {len(lang_files)} language files")
                            resolved = True
                        else:
                            validation['resolved_sources'].append(f"{source_file} (no matching language files)")
                            resolved = True
                    else:
                        validation['resolved_sources'].append(f"{source_file} (lang directory not found)")
                        resolved = True
                else:
                    # Try to resolve $SCRIPT_DIR first, then handle other variables
                    resolved_path = source_file.replace('$SCRIPT_DIR', script_dir)
                    if os.path.exists(resolved_path):
                        validation['resolved_sources'].append(f"{source_file} -> {resolved_path}")
                        resolved = True
                    else:
                        validation['resolved_sources'].append(f"{source_file} (complex variable substitution)")
                        resolved = True
            elif '$SCRIPT_DIR' in source_file:
                # Replace $SCRIPT_DIR with actual script directory
                resolved_path = source_file.replace('$SCRIPT_DIR', script_dir)
                if os.path.exists(resolved_path):
                    validation['resolved_sources'].append(f"{source_file} -> {resolved_path}")
                    resolved = True
                else:
                    # Try with normalized path
                    normalized_path = os.path.normpath(resolved_path)
                    if os.path.exists(normalized_path):
                        validation['resolved_sources'].append(f"{source_file} -> {normalized_path}")
                        resolved = True
            
            # Handle other common variables
            elif '${' in source_file or '$' in source_file:
                # Try to resolve some common patterns
                if 'lang/' in source_file and ('${langfile}' in source_file or '$langfile' in source_file):
                    # Check if lang directory exists and has files
                    resolved_base = source_file.replace('$SCRIPT_DIR', script_dir) if '$SCRIPT_DIR' in source_file else source_file
                    lang_pattern = resolved_base.replace('${langfile}', '*').replace('$langfile', '*')
                    lang_dir = os.path.dirname(lang_pattern)
                    
                    if os.path.exists(lang_dir):
                        lang_files = glob.glob(lang_pattern)
                        if lang_files:
                            # Found matching language files
                            validation['resolved_sources'].append(f"{source_file} -> found {len(lang_files)} language files")
                            resolved = True
                        else:
                            validation['resolved_sources'].append(f"{source_file} (no matching language files)")
                            resolved = True
                    else:
                        validation['resolved_sources'].append(f"{source_file} (lang directory not found)")
                        resolved = True
                else:
                    # Skip validation for other complex variable substitutions
                    validation['resolved_sources'].append(f"{source_file} (variable substitution - skipped)")
                    resolved = True
            
            # Handle absolute paths
            elif os.path.isabs(source_file):
                if os.path.exists(source_file):
                    validation['resolved_sources'].append(source_file)
                    resolved = True
            
            # Handle relative paths
            else:
                # Try relative to script directory
                relative_to_script = os.path.join(script_dir, source_file)
                if os.path.exists(relative_to_script):
                    validation['resolved_sources'].append(f"{source_file} -> {relative_to_script}")
                    resolved = True
                else:
                    # Try relative to libs directory
                    relative_to_libs = os.path.join(libs_dir, source_file)
                    if os.path.exists(relative_to_libs):
                        validation['resolved_sources'].append(f"{source_file} -> {relative_to_libs}")
                        resolved = True
                    else:
                        # Try with .lib extension
                        with_lib_ext = os.path.join(libs_dir, f"{source_file}.lib")
                        if os.path.exists(with_lib_ext):
                            validation['resolved_sources'].append(f"{source_file} -> {with_lib_ext}")
                            resolved = True
            
            if not resolved:
                validation['missing_sources'].append(source_file)
                validation['status'] = 'invalid'
        
        # Check if functions are defined in available libraries
        all_lib_functions = set()
        for lib_file in validation['available_libs']:
            try:
                with open(lib_file, 'r', encoding='utf-8') as f:
                    lib_content = f.read()
                    # Find function definitions
                    func_matches = re.findall(r'^(\w+)\s*\(\)\s*{', lib_content, re.MULTILINE)
                    all_lib_functions.update(func_matches)
            except Exception as e:
                validation['errors'].append(f"Error reading library {lib_file}: {str(e)}")
        
        # Check if called functions are available
        for func_call in dependencies['function_calls']:
            if func_call not in all_lib_functions:
                validation['missing_functions'].append(func_call)
                # Don't mark as invalid for missing functions, just warn
        
        if dependencies['errors']:
            validation['errors'].extend(dependencies['errors'])
            validation['status'] = 'error'
            
    except Exception as e:
        validation['errors'].append(f"Validation failed: {str(e)}")
        validation['status'] = 'error'
    
    return validation


def dry_run_script(script_path):
    """
    Perform a dry-run of a script, checking syntax and dependencies without execution.
    
    Args:
        script_path (str): Path to the script file
        
    Returns:
        dict: Dry-run results with validation status and details
    """
    print(f"🧪 DRY-RUN: {os.path.basename(script_path)}")
    print("=" * 50)
    
    result = {
        'script': script_path,
        'syntax_valid': False,
        'dependencies_valid': False,
        'validation': {},
        'syntax_errors': [],
        'warnings': []
    }
    
    # Check bash syntax
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_file:
            with open(script_path, 'r', encoding='utf-8') as original:
                temp_file.write(original.read())
            temp_file.flush()
            
            # Use bash -n to check syntax without execution
            syntax_check = subprocess.run(
                ['bash', '-n', temp_file.name],
                capture_output=True, text=True
            )
            
            if syntax_check.returncode == 0:
                result['syntax_valid'] = True
                print("✅ Syntax: Valid")
            else:
                result['syntax_errors'] = syntax_check.stderr.split('\n')
                print("❌ Syntax: Invalid")
                for error in result['syntax_errors']:
                    if error.strip():
                        print(f"   {error}")
        
        os.unlink(temp_file.name)
        
    except Exception as e:
        result['syntax_errors'].append(f"Syntax check failed: {str(e)}")
        print(f"❌ Syntax check failed: {str(e)}")
    
    # Validate dependencies
    validation = validate_script_libraries(script_path)
    result['validation'] = validation
    
    if validation['status'] == 'valid':
        result['dependencies_valid'] = True
        print("✅ Dependencies: Valid")
    elif validation['status'] == 'invalid':
        print("❌ Dependencies: Invalid")
    else:
        print("⚠️  Dependencies: Errors occurred")
    
    # Show dependency details
    deps = validation['dependencies']
    if deps['sources']:
        print(f"📁 Sources: {len(deps['sources'])} found")
        if validation['resolved_sources']:
            for resolved in validation['resolved_sources']:
                print(f"   ✅ {resolved}")
    if deps['function_calls']:
        print(f"🔧 Functions: {', '.join(deps['function_calls'])}")
    if deps['variables']:
        print(f"📝 Variables: {', '.join(deps['variables'])}")
    
    # Show missing dependencies
    if validation['missing_sources']:
        print(f"❌ Missing sources: {', '.join(validation['missing_sources'])}")
    if validation['missing_functions']:
        print(f"⚠️  Undefined functions: {', '.join(validation['missing_functions'])}")
        result['warnings'].extend([f"Function '{f}' not found in libraries" for f in validation['missing_functions']])
    
    # Show errors
    if validation['errors']:
        print("❌ Errors:")
        for error in validation['errors']:
            print(f"   {error}")
    
    # Overall status
    overall_status = "✅ PASS" if result['syntax_valid'] and result['dependencies_valid'] else "❌ FAIL"
    print(f"\n🎯 Overall: {overall_status}")
    print("=" * 50)
    print()
    
    return result


def should_dry_run_scripts():
    """
    Check if scripts should be dry-run instead of executed.
    
    Returns:
        bool: True if in developer mode (scripts should be validated, not executed)
    """
    return is_dev_mode_enabled()


def print_dev_mode_banner():
    """
    Print a banner indicating developer mode status.
    Should be called at application startup when developer mode is active.
    """
    if is_dev_mode_enabled():
        print("=" * 60)
        print("🔧 DEVELOPER MODE ACTIVE")
        print(get_dev_mode_status())
        
        compat_override = get_dev_compat_override()
        container_override = get_dev_container_override()
        
        if compat_override:
            print(f"📋 Simulating system: {compat_override}")
            print("   Scripts will be filtered as if running on this system")
        else:
            print("📋 Showing ALL scripts regardless of compatibility")
            print("   Use COMPAT=<system> to simulate a specific distribution")
        
        if container_override == '1':
            print("📦 Container simulation: ENABLED")
            print("   Container checks will be applied normally")
        else:
            print("📦 Container simulation: DISABLED (ignoring container checks)")
            print("   Use CONTAINER=1 to simulate container environment")
        
        print("🧪 Script execution: DRY-RUN mode (validation only)")
        print("   Scripts will be validated but not executed")
        print("=" * 60)
        print()
