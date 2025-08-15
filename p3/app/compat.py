def get_system_compat_keys():
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

def script_is_compatible(script_path, compat_keys):
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
