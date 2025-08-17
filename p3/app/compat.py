def is_containerized():
    """
    Detect if the system is running inside a container.
    
    This function checks multiple indicators to determine if the system
    is running in a containerized environment such as Docker, Podman, LXC, etc.
    
    Detection methods:
    1. Environment variables (container, CONTAINER_ID, DOCKER_CONTAINER, PODMAN_CONTAINER)
    2. Container-specific files (/.dockerenv, /run/.containerenv)
    3. cgroup analysis for container indicators
    4. systemd-detect-virt utility (if available)
    
    Returns:
        bool: True if containerized, False otherwise.
    """
    import os
    
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

    return keys

def get_current_locale():
    """
    Get the current system locale (language code).
    Returns the detected language code (e.g., 'en', 'pt').
    """
    import os
    # Get language from LANG environment variable (first 2 characters)
    lang = os.environ.get('LANG', 'en_US')[:2]
    return lang

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
    
    Scripts are considered incompatible with containers if:
    1. They use flatpak_in_lib function (automatic exclusion)
    2. They have a '# nocontainer' header (with optional system keys)
    
    The nocontainer header supports several formats:
    - '# nocontainer' - hide in all containers
    - '# nocontainer:' - hide in all containers (empty value)
    - '# nocontainer: debian, ubuntu' - hide only in debian/ubuntu containers
    - '# nocontainer: fedora' - hide only in fedora containers
    
    Priority rules:
    - If nocontainer header is present, it takes precedence over flatpak_in_lib
    - If nocontainer specifies keys that don't match current system, script is shown
      even if it contains flatpak_in_lib
    - If no nocontainer header, flatpak_in_lib causes automatic exclusion
    
    Args:
        script_path (str): Path to the script file
        
    Returns:
        bool: False if script should be hidden in containers, True otherwise
    """
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            has_flatpak_in_lib = 'flatpak_in_lib' in content
            nocontainer_keys = None
            
            # Check for nocontainer header
            for line in content.split('\n'):
                if line.startswith('# nocontainer'):
                    if ':' in line:
                        # nocontainer with specific keys
                        nocontainer_line = line[line.index(':') + 1:].strip()
                        if nocontainer_line:
                            nocontainer_keys = set([k.strip() for k in nocontainer_line.split(',')])
                        else:
                            # Empty after colon means hide in all containers
                            nocontainer_keys = set()
                    else:
                        # Plain nocontainer means hide in all containers
                        nocontainer_keys = set()
                    break
                if not line.startswith('#'):
                    break
            
            # If nocontainer header is present, it takes precedence
            if nocontainer_keys is not None:
                if len(nocontainer_keys) == 0:
                    # Hide in all containers
                    return False
                else:
                    # Hide only in containers that match the specified keys
                    current_compat_keys = get_system_compat_keys()
                    return not bool(current_compat_keys & nocontainer_keys)
            
            # If no nocontainer header, fall back to flatpak_in_lib check
            if has_flatpak_in_lib:
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
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('# compat:'):
                    compat_line = line[len('# compat:'):].strip()
                    script_keys = set([k.strip() for k in compat_line.split(',')])
                    return bool(compat_keys & script_keys)
                if not line.startswith('#'):
                    break
    except Exception:
        pass
    return True  # If no compat header, show by default

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
