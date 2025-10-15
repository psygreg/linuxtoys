"""
Developer mode utilities for LinuxToys.

This module provides functionality to override compatibility checks and simulate
different system environments for development and testing purposes.

Environment Variables:
- DEV_MODE=1: Enable developer mode (shows all scripts regardless of compatibility)
- COMPAT=<key>: Simulate a specific system (e.g., COMPAT=fedora, COMPAT=arch)
- CONTAINER=1: Simulate container environment (applies container checks)
- OPTIMIZER=1: Simulate optimized system (show removal scripts only)
- OPTIMIZER=0: Simulate unoptimized system (show installation scripts only)

Features:
- Compatibility override and system simulation
- Container environment simulation and override
- Optimizer state simulation and override
- Dry-run script validation (checks parsing and library sourcing)

Usage:
    DEV_MODE=1 python3 run.py                                 # Show all scripts, ignore all checks
    DEV_MODE=1 COMPAT=fedora python3 run.py                   # Simulate Fedora system
    DEV_MODE=1 CONTAINER=1 python3 run.py                     # Simulate container environment
    DEV_MODE=1 OPTIMIZER=1 python3 run.py                     # Simulate optimized system
    DEV_MODE=1 OPTIMIZER=0 python3 run.py                     # Simulate unoptimized system
    DEV_MODE=1 COMPAT=arch CONTAINER=1 OPTIMIZER=1 python3 run.py # Full simulation
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


def get_dev_optimizer_override():
    """
    Get the optimizer state override from OPTIMIZER environment variable.
    
    Returns:
        str or None: The optimizer simulation setting ('1' to simulate optimized, 
                     '0' to simulate unoptimized), or None if not set
    """
    return os.environ.get('OPTIMIZER')


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


def should_override_optimizer_checks():
    """
    Check if optimizer state checks should be overridden.
    
    In developer mode:
    - Without OPTIMIZER set: override optimizer checks (show both install and remove scripts)
    - With OPTIMIZER=1 or OPTIMIZER=0: apply optimizer simulation logic
    
    Returns:
        bool: True if optimizer checks should be overridden (ignored)
    """
    if not is_dev_mode_enabled():
        return False
    
    # If OPTIMIZER is set, don't override - simulate optimizer behavior
    optimizer_override = get_dev_optimizer_override()
    if optimizer_override in ['0', '1']:
        return False
    
    # Default in dev mode: override (ignore) optimizer checks
    return True


def should_simulate_optimizations_installed():
    """
    Check if optimized system should be simulated.
    
    Returns:
        bool: True if DEV_MODE=1 and OPTIMIZER=1 (simulate optimized system)
    """
    return is_dev_mode_enabled() and get_dev_optimizer_override() == '1'


def should_simulate_optimizations_not_installed():
    """
    Check if unoptimized system should be simulated.
    
    Returns:
        bool: True if DEV_MODE=1 and OPTIMIZER=0 (simulate unoptimized system)
    """
    return is_dev_mode_enabled() and get_dev_optimizer_override() == '0'


def get_effective_compat_keys():
    """
    Get the effective compatibility keys for the current session.
    
    In developer mode:
    - If COMPAT is set: return simulated keys plus GPU/desktop keys
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
        # Include simulated OS keys plus GPU and desktop keys
        from .compat import get_gpu_compat_keys, get_desktop_compat_keys
        keys = get_simulated_compat_keys()
        keys.update(get_gpu_compat_keys())
        keys.update(get_desktop_compat_keys())
        return keys
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
    optimizer_override = get_dev_optimizer_override()
    
    if compat_override:
        status_parts.append(f"simulating {compat_override}, keys: {sorted(get_effective_compat_keys())}")
    else:
        status_parts.append("showing all scripts")
    
    if container_override == '1':
        status_parts.append("simulating container environment")
    else:
        status_parts.append("ignoring container checks")
    
    if optimizer_override == '1':
        status_parts.append("simulating optimized system")
    elif optimizer_override == '0':
        status_parts.append("simulating unoptimized system")
    else:
        status_parts.append("ignoring optimizer state")
    
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
    
    # Dynamically find the p3 root by looking for the 'libs' directory
    # Support scripts at different nesting levels (scripts/, scripts/category/, scripts/category/subcategory/)
    current_dir = script_dir
    p3_root = None
    max_levels = 5  # Safety limit to prevent infinite loops
    
    for _ in range(max_levels):
        potential_libs_dir = os.path.join(current_dir, 'libs')
        if os.path.exists(potential_libs_dir) and os.path.isdir(potential_libs_dir):
            # Check if this looks like the actual libs directory by looking for known files
            lib_files = [f for f in os.listdir(potential_libs_dir) if f.endswith('.lib')]
            if lib_files:
                p3_root = current_dir
                break
        current_dir = os.path.dirname(current_dir)
    
    if p3_root is None:
        # Fallback to the old method if we can't find the libs directory
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


def validate_script_sudo_usage(script_path):
    """
    Validate that scripts properly call sudo_rq before using sudo commands.
    
    Analyzes both direct sudo usage in main script flow and function calls to ensure
    that functions containing sudo are only called after sudo_rq is established.
    
    Args:
        script_path (str): Path to the script file
        
    Returns:
        dict: Validation results with sudo usage analysis
    """
    validation = {
        'status': 'valid',
        'sudo_commands_found': [],
        'sudo_rq_found': False,
        'sudo_rq_line': None,
        'first_sudo_line': None,
        'proper_usage': True,
        'functions_with_sudo': [],
        'function_calls_before_sudo_rq': [],
        'function_calls_after_sudo_rq': [],
        'errors': []
    }
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        sudo_rq_line_num = None
        first_sudo_line_num = None
        sudo_commands = []
        functions_with_sudo = []
        function_calls_before_sudo_rq = []
        function_calls_after_sudo_rq = []
        
        # First pass: identify functions and their sudo usage
        function_definitions = {}  # function_name -> has_sudo
        in_function = False
        function_name = None
        brace_count = 0
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('#'):
                continue
                
            line_without_quotes = re.sub(r'["\'].*?["\']', '', stripped_line)
            
            # Detect function definitions
            func_match = re.match(r'(?:function\s+)?(\w+)\s*\(\)\s*\{?', line_without_quotes)
            if func_match and not in_function:
                in_function = True
                function_name = func_match.group(1)
                function_definitions[function_name] = False  # Initialize as no sudo
                brace_count = line_without_quotes.count('{') - line_without_quotes.count('}')
                continue
            
            if in_function:
                brace_count += line_without_quotes.count('{') - line_without_quotes.count('}')
                
                # Check for sudo usage inside function
                sudo_pattern = r'(?:^|[;&|]\s*)\s*sudo\s+\w+'
                if re.search(sudo_pattern, line_without_quotes) and not re.search(r'\bsudo_rq\b', line_without_quotes):
                    function_definitions[function_name] = True
                    functions_with_sudo.append({
                        'function': function_name,
                        'line': line_num,
                        'command': stripped_line
                    })
                
                if brace_count <= 0:
                    in_function = False
                    function_name = None
                continue
        
        # Second pass: analyze main script flow
        in_function = False
        brace_count = 0
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('#'):
                continue
                
            line_without_quotes = re.sub(r'["\'].*?["\']', '', stripped_line)
            
            # Skip function definitions (we already processed them)
            func_match = re.match(r'(?:function\s+)?(\w+)\s*\(\)\s*\{?', line_without_quotes)
            if func_match and not in_function:
                in_function = True
                brace_count = line_without_quotes.count('{') - line_without_quotes.count('}')
                continue
            
            if in_function:
                brace_count += line_without_quotes.count('{') - line_without_quotes.count('}')
                if brace_count <= 0:
                    in_function = False
                continue
            
            # Only analyze main script flow (outside functions)
            
            # Check for sudo_rq function call
            if re.search(r'\bsudo_rq\b', line_without_quotes):
                # Make sure it's not just in a comment - check if it's an actual command
                # Remove comments for this check
                line_without_comments = re.sub(r'#.*$', '', line_without_quotes)
                if re.search(r'\bsudo_rq\b', line_without_comments.strip()):
                    if sudo_rq_line_num is None:
                        sudo_rq_line_num = line_num
                        validation['sudo_rq_found'] = True
                        validation['sudo_rq_line'] = line_num
            
            # Check for direct sudo commands in main script
            sudo_pattern = r'(?:^|[;&|]\s*)\s*sudo\s+\w+'
            if re.search(sudo_pattern, line_without_quotes) and not re.search(r'\bsudo_rq\b', line_without_quotes):
                if first_sudo_line_num is None:
                    first_sudo_line_num = line_num
                    validation['first_sudo_line'] = line_num
                
                sudo_commands.append({
                    'line': line_num,
                    'command': stripped_line
                })
            
            # Check for function calls in main script
            for func_name in function_definitions:
                if re.search(rf'\b{func_name}\b', line_without_quotes):
                    # Check if this is actually a function call (not part of a larger word)
                    func_call_pattern = rf'\b{func_name}\s*(?:\(\s*\)|\s|$|;|&|\|)'
                    if re.search(func_call_pattern, line_without_quotes):
                        call_info = {
                            'function': func_name,
                            'line': line_num,
                            'has_sudo': function_definitions[func_name],
                            'command': stripped_line
                        }
                        
                        if sudo_rq_line_num is None or line_num < sudo_rq_line_num:
                            function_calls_before_sudo_rq.append(call_info)
                        else:
                            function_calls_after_sudo_rq.append(call_info)
        
        validation['sudo_commands_found'] = sudo_commands
        validation['functions_with_sudo'] = functions_with_sudo
        validation['function_calls_before_sudo_rq'] = function_calls_before_sudo_rq
        validation['function_calls_after_sudo_rq'] = function_calls_after_sudo_rq
        
        # Validate execution flow
        errors = []
        
        # Check direct sudo usage in main flow
        if sudo_commands:
            if not validation['sudo_rq_found']:
                errors.append("Script uses sudo commands in main flow but never calls sudo_rq")
            elif sudo_rq_line_num > first_sudo_line_num:
                errors.append(f"sudo_rq (line {sudo_rq_line_num}) called after first sudo usage in main flow (line {first_sudo_line_num})")
        
        # Check function calls with sudo before sudo_rq
        functions_with_sudo_called_early = []
        for call_info in function_calls_before_sudo_rq:
            if call_info['has_sudo']:
                functions_with_sudo_called_early.append(call_info)
        
        if functions_with_sudo_called_early:
            if not validation['sudo_rq_found']:
                func_names = [call['function'] for call in functions_with_sudo_called_early]
                errors.append(f"Functions with sudo called but sudo_rq never called: {', '.join(set(func_names))}")
            else:
                for call_info in functions_with_sudo_called_early:
                    errors.append(f"Function '{call_info['function']}' with sudo called at line {call_info['line']} before sudo_rq (line {sudo_rq_line_num})")
        
        if errors:
            validation['status'] = 'invalid'
            validation['proper_usage'] = False
            validation['errors'] = errors
        
    except Exception as e:
        validation['status'] = 'error'
        validation['errors'] = [f"Failed to validate sudo usage: {str(e)}"]
    
    return validation


def validate_script_header(script_path):
    """
    Validate that the script contains the required header metadata.

    Args:
        script_path (str): Path to the script file

    Returns:
        dict: Validation results with missing fields and status
    """
    required_fields = ["name", "version", "description", "icon", "compat"]
    found_fields = {}
    missing_fields = []

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Only check first 15 lines (header area)
        for line in lines[:15]:
            if line.startswith("#"):
                for field in required_fields:
                    if line.lower().startswith(f"# {field}:"):
                        found_fields[field] = line.strip().split(":", 1)[1].strip()

        for field in required_fields:
            if field not in found_fields:
                missing_fields.append(field)

        status = "valid" if not missing_fields else "invalid"

        return {
            "status": status,
            "found": found_fields,
            "missing": missing_fields,
        }

    except Exception as e:
        return {
            "status": "error",
            "found": {},
            "missing": required_fields,
            "error": str(e),
        }


def dry_run_script(script_path):
    """
    Perform a dry-run of a script, checking syntax, header and dependencies without execution.

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
        'sudo_valid': False,
        'validation': {},
        'sudo_validation': {},
        'syntax_errors': [],
        'warnings': []
    }

    # --- 1. Check bash syntax ---
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_file:
            with open(script_path, 'r', encoding='utf-8') as original:
                temp_file.write(original.read())
            temp_file.flush()

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

    # --- 2. Validate header metadata ---
    header_validation = validate_script_header(script_path)
    if header_validation["status"] == "valid":
        print("✅ Header: Valid")
    elif header_validation["status"] == "invalid":
        print("⚠️  Header: Missing fields -> " + ", ".join(header_validation["missing"]))
        result["warnings"].append(
            f"Script header missing fields: {', '.join(header_validation['missing'])}"
        )
    else:
        print(f"❌ Header validation failed: {header_validation['error']}")

    # --- 3. Validate sudo usage ---
    sudo_validation = validate_script_sudo_usage(script_path)
    result['sudo_validation'] = sudo_validation

    if sudo_validation['status'] == 'valid':
        result['sudo_valid'] = True
        if sudo_validation['sudo_commands_found']:
            print("✅ Sudo: Valid (sudo_rq called before sudo usage)")
        else:
            print("✅ Sudo: Valid (no sudo commands found)")
    elif sudo_validation['status'] == 'invalid':
        print("❌ Sudo: Invalid")
        for error in sudo_validation['errors']:
            print(f"   {error}")
    else:
        print("⚠️  Sudo: Validation errors occurred")
        for error in sudo_validation['errors']:
            print(f"   {error}")

    # Show sudo usage details if commands were found
    if sudo_validation['sudo_commands_found']:
        print(f"🔒 Sudo commands: {len(sudo_validation['sudo_commands_found'])} found in main flow")
        if sudo_validation['sudo_rq_found']:
            print(f"   sudo_rq call: line {sudo_validation['sudo_rq_line']}")
        print(f"   First sudo: line {sudo_validation['first_sudo_line']}")
    
    # Show function call analysis
    if sudo_validation['functions_with_sudo']:
        print(f"ℹ️  Functions with sudo: {len(sudo_validation['functions_with_sudo'])} found")
        func_summary = {}
        for func_info in sudo_validation['functions_with_sudo']:
            func_name = func_info['function']
            if func_name not in func_summary:
                func_summary[func_name] = 0
            func_summary[func_name] += 1
        for func_name, count in func_summary.items():
            print(f"   {func_name}(): {count} sudo command(s)")
    
    # Show function call timing analysis
    calls_before = sudo_validation['function_calls_before_sudo_rq']
    calls_after = sudo_validation['function_calls_after_sudo_rq']
    
    if calls_before or calls_after:
        print("📞 Function calls analysis:")
        
        if calls_before:
            print(f"   Before sudo_rq: {len(calls_before)} calls")
            sudo_calls_before = [call for call in calls_before if call['has_sudo']]
            if sudo_calls_before:
                print(f"      ⚠️  {len(sudo_calls_before)} with sudo: {', '.join([call['function'] for call in sudo_calls_before])}")
            else:
                print("      ✅ None with sudo")
        
        if calls_after:
            print(f"   After sudo_rq: {len(calls_after)} calls")
            sudo_calls_after = [call for call in calls_after if call['has_sudo']]
            if sudo_calls_after:
                print(f"      ✅ {len(sudo_calls_after)} with sudo: {', '.join([call['function'] for call in sudo_calls_after])}")
    elif sudo_validation['functions_with_sudo']:
        print("📞 No function calls detected in main flow")

    # --- 4. Validate dependencies ---
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
    overall_status = "✅ PASS" if result['syntax_valid'] and result['dependencies_valid'] and result['sudo_valid'] else "❌ FAIL"
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
        optimizer_override = get_dev_optimizer_override()
        
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
        
        if optimizer_override == '1':
            print("⚡ Optimizer simulation: OPTIMIZED (showing removal scripts)")
            print("   System appears to have optimizations installed")
        elif optimizer_override == '0':
            print("⚡ Optimizer simulation: UNOPTIMIZED (showing installation scripts)")
            print("   System appears to have no optimizations")
        else:
            print("⚡ Optimizer simulation: DISABLED (showing all optimization scripts)")
            print("   Use OPTIMIZER=1 for optimized, OPTIMIZER=0 for unoptimized")
        
        print("🧪 Script execution: DRY-RUN mode (validation only)")
        print("   Scripts will be validated but not executed")
        print("=" * 60)
        print()
