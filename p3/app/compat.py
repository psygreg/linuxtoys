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
