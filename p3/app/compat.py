def is_containerized():
    """
    Detect if the system is running inside a container.
    
    This function checks multiple indicators to determine if the system
    is running in a containerized environment such as Docker, Podman, LXC, etc.
    
    In developer mode:
    - If CONTAINER=1 is set, simulate being in a container (return True)
    - If CONTAINER is not set, use actual container detection
    
    Detection methods:
    1. Environment variables (container, CONTAINER_ID, DOCKER_CONTAINER, PODMAN_CONTAINER)
    2. Container-specific files (/.dockerenv, /run/.containerenv)
    3. cgroup analysis for container indicators
    4. systemd-detect-virt utility (if available)
    
    Returns:
        bool: True if containerized, False otherwise.
    """
    import os
    
    # Check for developer mode container simulation
    try:
        from .dev_mode import should_simulate_container
        if should_simulate_container():
            return True  # Simulate being in a container when CONTAINER=1
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass
    
    # Check for container environment variables
    container_env_vars = [
        'container',
        'CONTAINER_ID',
        'DOCKER_CONTAINER',
        'PODMAN_CONTAINER'
    ]
    
    for var in container_env_vars:
        if os.environ.get(var):
            return True
    
    # Check for container-specific files
    container_files = [
        '/.dockerenv',
        '/run/.containerenv'
    ]
    
    for file_path in container_files:
        if os.path.exists(file_path):
            return True
    
    # Check cgroup for container indicators
    try:
        with open('/proc/1/cgroup', 'r') as f:
            cgroup_content = f.read()
            container_indicators = ['docker', 'lxc', 'containerd', 'podman']
            for indicator in container_indicators:
                if indicator in cgroup_content:
                    return True
    except Exception:
        pass
    
    # Check for systemd-detect-virt (if available)
    try:
        result = os.system('command -v systemd-detect-virt >/dev/null 2>&1')
        if result == 0:
            # Run systemd-detect-virt --container
            exit_code = os.system('systemd-detect-virt --container >/dev/null 2>&1')
            if exit_code == 0:  # Returns 0 if in container
                return True
    except Exception:
        pass
    
    return False

def get_system_compat_keys():
    """
    Get the system compatibility keys.
    
    In developer mode, this can be overridden to simulate different systems
    or show all scripts regardless of compatibility.
    
    Returns:
        set: Set of compatibility keys for the current system
    """
    # Check if developer mode override is active
    try:
        from .dev_mode import is_dev_mode_enabled, get_effective_compat_keys
        if is_dev_mode_enabled():
            return get_effective_compat_keys()
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass
    
    keys = set()
    os_release = {}
    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    os_release[k] = v.strip('"')
    except Exception:
        pass

    id_val = os_release.get('ID', '').lower()
    id_like = os_release.get('ID_LIKE', '').lower()

    if id_val in ['debian']:
        keys.add('debian')
    if id_val in ['ubuntu'] or 'ubuntu' in id_like or 'debian' in id_like:
        keys.add('ubuntu')
    if id_val in ['cachyos']:
        keys.add('cachy')
    if (id_val in ['arch', 'archlinux'] or 'arch' in id_like or 'archlinux' in id_like) and id_val != 'cachyos':
        keys.add('arch')
    if id_val in ['rhel', 'fedora'] or 'rhel' in id_like or 'fedora' in id_like:
        keys.add('fedora')
    if id_val in ['suse', 'opensuse'] or 'suse' in id_like or 'opensuse' in id_like:
        keys.add('suse')

    # Check for rpm-ostree immutable distros
    import os
    if os.system('command -v rpm-ostree >/dev/null 2>&1') == 0:
        if id_val in ['bazzite'] or id_val in ['bluefin'] or id_val in ['aurora']:
            keys = {'ublue'}
        else:
            keys = {'ostree'}  # Override all other keys

    # Add GPU compatibility keys
    gpu_keys = get_gpu_compat_keys()
    keys.update(gpu_keys)

    return keys

def get_gpu_compat_keys():
    """
    Get the GPU compatibility keys based on detected GPUs.
    
    Returns:
        set: Set of GPU compatibility keys ('gpu', 'gpu-amd', 'gpu-intel', 'gpu-nvidia')
    """
    keys = set()
    try:
        import subprocess
        result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=10)
        lspci_output = result.stdout.lower()
        
        has_amd = 'radeon' in lspci_output or 'rx' in lspci_output
        has_intel = False
        has_nvidia = 'nvidia' in lspci_output
        
        # Check Intel GPU by ensuring 'intel' and ('vga' or '3d') are in the same line
        for line in lspci_output.split('\n'):
            if 'intel' in line and ('vga' in line or '3d' in line):
                has_intel = True
                break
        
        if has_amd or has_intel or has_nvidia:
            keys.add('gpu')
        if has_amd:
            keys.add('gpu-amd')
        if has_intel:
            keys.add('gpu-intel')
        if has_nvidia:
            keys.add('gpu-nvidia')
    except Exception:
        pass
    return keys

def are_optimizations_installed():
    """
    Check if system optimizations have been applied.
    
    This function checks for the presence of the autopatch state file
    which indicates that LinuxToys optimizations have been installed.
    
    In developer mode:
    - If OPTIMIZER=1 is set, simulate optimizations being installed (return True)
    - If OPTIMIZER=0 is set, simulate optimizations not being installed (return False)
    - If OPTIMIZER is not set, use actual file detection
    
    Returns:
        bool: True if optimizations are installed, False otherwise
    """
    import os
    
    # Check for developer mode optimizer simulation
    try:
        from .dev_mode import should_simulate_optimizations_installed, should_simulate_optimizations_not_installed
        if should_simulate_optimizations_installed():
            return True   # Simulate optimizations installed
        if should_simulate_optimizations_not_installed():
            return False  # Simulate optimizations not installed
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass
    
    autopatch_state_file = os.path.expanduser("~/.local/.autopatch.state")
    return os.path.exists(autopatch_state_file)


def should_show_optimization_script(script_path):
    """
    Determine if an optimization-related script should be shown based on current state.
    
    This function implements the toggle logic for optimization scripts:
    - If optimizations are NOT installed: show installation scripts (pdefaults.sh, etc.)
    - If optimizations ARE installed: show removal scripts (unoptimize.sh, etc.)
    
    In developer mode:
    - Without OPTIMIZER set: override optimization checks (show both install and remove scripts)
    - With OPTIMIZER=1 or OPTIMIZER=0: apply optimization simulation logic
    
    Args:
        script_path (str): Path to the script file
        
    Returns:
        bool: True if the script should be shown, False if it should be hidden
    """
    import os
    
    # Check for developer mode optimizer override
    try:
        from .dev_mode import should_override_optimizer_checks
        if should_override_optimizer_checks():
            return True  # Override: always show all optimization scripts
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass
    
    script_name = os.path.basename(script_path)
    optimizations_installed = are_optimizations_installed()
    
    # Installation scripts - show only when optimizations are NOT installed
    installation_scripts = [
        'pdefaults.sh', 
        'pdefaults-ostree.sh'
    ]
    
    # Removal scripts - show only when optimizations ARE installed  
    removal_scripts = [
        'unoptimize.sh',
        'unoptimize-ostree.sh'
    ]
    
    if script_name in installation_scripts:
        return not optimizations_installed  # Show if NOT installed
    elif script_name in removal_scripts:
        return optimizations_installed      # Show if installed
    else:
        return True  # Show all other scripts normally

def script_uses_flatpak_in_lib(script_path):
    """
    Check if a script uses the flatpak_in_lib function.
    
    Args:
        script_path (str): Path to the script file
        
    Returns:
        bool: True if the script contains a call to flatpak_in_lib
    """
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return 'flatpak_in_lib' in content
    except Exception:
        pass
    return False

def script_is_container_compatible(script_path):
    """
    Check if a script should be shown in containerized environments.
    
    In developer mode:
    - If CONTAINER is not set (default): override container checks (always return True)
    - If CONTAINER=1: apply normal container compatibility logic
    
    Scripts are considered incompatible with containers if:
    1. They use flatpak_in_lib function (automatic exclusion)
    2. They have a '# nocontainer' header (with optional system keys)
    
    The nocontainer header supports several formats:
    - '# nocontainer' - hide in all containers
    - '# nocontainer:' - hide in all containers (empty value)
    - '# nocontainer: debian, ubuntu' - hide only in debian/ubuntu containers
    - '# nocontainer: fedora' - hide only in fedora containers
    - '# nocontainer: invert' - show ONLY in containers (hide on host)
    - '# nocontainer: invert, debian' - show only in debian containers
    
    Priority rules:
    - If nocontainer header is present, it takes precedence over flatpak_in_lib
    - If nocontainer specifies keys that don't match current system, script is shown
      even if it contains flatpak_in_lib
    - If no nocontainer header, flatpak_in_lib causes automatic exclusion
    - 'invert' keyword reverses the container logic
    
    Args:
        script_path (str): Path to the script file
        
    Returns:
        bool: False if script should be hidden in containers, True otherwise
    """
    # Check for developer mode container override
    try:
        from .dev_mode import should_override_container_checks
        if should_override_container_checks():
            return True  # Override: always show scripts regardless of container compatibility
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            has_flatpak_in_lib = 'flatpak_in_lib' in content
            nocontainer_keys = None
            has_invert = False
            
            # Check for nocontainer header
            for line in content.split('\n'):
                if line.startswith('# nocontainer'):
                    if ':' in line:
                        # nocontainer with specific keys
                        nocontainer_line = line[line.index(':') + 1:].strip()
                        if nocontainer_line:
                            keys = [k.strip() for k in nocontainer_line.split(',')]
                            has_invert = 'invert' in keys
                            # Remove 'invert' from the keys list to process other keys normally
                            nocontainer_keys = set([k for k in keys if k != 'invert'])
                        else:
                            # Empty after colon means hide in all containers
                            nocontainer_keys = set()
                    else:
                        # Plain nocontainer means hide in all containers
                        nocontainer_keys = set()
                    break
                if not line.startswith('#'):
                    break
            
            # Check if we're actually in a container
            is_in_container = is_containerized()
            
            # If nocontainer header is present, it takes precedence
            if nocontainer_keys is not None:
                if has_invert:
                    # Invert logic: show only in containers
                    if not is_in_container:
                        return False  # Hide on host when invert is specified
                    
                    # If we're in a container and have other keys, check compatibility
                    if len(nocontainer_keys) > 0:
                        current_compat_keys = get_system_compat_keys()
                        return bool(current_compat_keys & nocontainer_keys)
                    else:
                        # Only 'invert' specified, show in any container
                        return True
                else:
                    # Normal logic: hide in containers
                    if not is_in_container:
                        return True  # Always show on host when no invert
                    
                    if len(nocontainer_keys) == 0:
                        # Hide in all containers
                        return False
                    else:
                        # Hide only in containers that match the specified keys
                        current_compat_keys = get_system_compat_keys()
                        return not bool(current_compat_keys & nocontainer_keys)
            
            # If no nocontainer header, fall back to flatpak_in_lib check
            if has_flatpak_in_lib and is_in_container:
                return False
                
    except Exception:
        pass
    return True  # If no restrictions, allow by default

def script_is_compatible(script_path, compat_keys):
    """
    Check if a script is compatible with the given compatibility keys.
    
    In developer mode without COMPAT override, all scripts are considered compatible.
    
    Args:
        script_path (str): Path to the script file
        compat_keys (set): Set of compatibility keys for the current system
        
    Returns:
        bool: True if script is compatible, False otherwise
    """
    # Check if developer mode override is active
    try:
        from .dev_mode import is_dev_mode_enabled, get_dev_compat_override
        if is_dev_mode_enabled() and not get_dev_compat_override():
            # Developer mode without specific system simulation - show all scripts
            return True
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass
    
    os_compatible = True
    gpu_compatible = 'gpu' in compat_keys  # Default for unset GPU header
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('# compat:'):
                    compat_line = line[len('# compat:'):].strip()
                    script_keys = set([k.strip() for k in compat_line.split(',')])
                    os_compatible = bool(compat_keys & script_keys)
                elif line.startswith('# gpu:'):
                    gpu_value = line[len('# gpu:'):].strip()
                    gpu_values = [v.strip() for v in gpu_value.split(',') if v.strip()]
                    gpu_script_keys = set()
                    for v in gpu_values:
                        if v == 'AMD':
                            gpu_script_keys.add('gpu-amd')
                        elif v == 'Intel':
                            gpu_script_keys.add('gpu-intel')
                        elif v == 'Nvidia':
                            gpu_script_keys.add('gpu-nvidia')
                        else:
                            # Unknown value, treat as general GPU
                            gpu_script_keys.add('gpu')
                    if gpu_script_keys:
                        gpu_compatible = bool(compat_keys & gpu_script_keys)
                    else:
                        # Empty header, treat as general GPU
                        gpu_compatible = 'gpu' in compat_keys
                if not line.startswith('#'):
                    break
    except Exception:
        pass
    
    return os_compatible and gpu_compatible

def script_is_localized(script_path, current_locale):
    """
    Check if a script should be shown for the current locale.
    Returns True if:
    - No 'localize' header is present (show by default)
    - 'localize' header contains the current locale
    """
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('# localize:'):
                    localize_line = line[len('# localize:'):].strip()
                    localize_keys = set([k.strip().lower() for k in localize_line.split(',')])
                    return current_locale.lower() in localize_keys
                if not line.startswith('#'):
                    break
    except Exception:
        pass
    return True  # If no localize header, show by default
