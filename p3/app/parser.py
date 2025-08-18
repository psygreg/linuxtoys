import os

from .compat import (
    get_system_compat_keys, 
    script_is_compatible, 
    script_is_localized,
    is_containerized,
    script_is_container_compatible,
    should_show_optimization_script
)
from .lang_utils import detect_system_language

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')

def script_requires_reboot(script_path, system_compat_keys):
    """
    Check if a script requires a reboot for the current system.
    Returns True if script requires reboot and matches system compatibility.
    """
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('# reboot:'):
                    reboot_value = line[len('# reboot:'):].strip().lower()
                    if reboot_value == 'yes':
                        return True
                    elif reboot_value == 'ostree':
                        # Check if system has ostree or ublue compatibility
                        return bool({'ostree', 'ublue'} & system_compat_keys)
                if not line.startswith('#'):
                    break
    except Exception:
        pass
    return False

def _parse_metadata_file(file_path, default_values, translations=None):
    """
    A generic parser for our metadata files (.sh headers or category-info.txt).
    """
    metadata = default_values.copy()
    metadata['path'] = file_path

    if not os.path.exists(file_path):
        return metadata

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if file_path.endswith('.sh') and not line.startswith('#'):
                    break
                prefix = ''
                if file_path.endswith('.sh'):
                    prefix = '# '
                if line.startswith(prefix):
                    line_content = line[len(prefix):]
                    parts = line_content.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        # Translation support for name/description
                        if translations and key in ['name', 'description']:
                            value = translations.get(value, value)
                        if key in metadata:
                            metadata[key] = value
    except Exception as e:
        print(f"Error reading metadata from {file_path}: {e}")

    return metadata

def get_categories(translations=None):
    """
    Returns a list of categories, reading metadata from 'category-info.txt' in each folder.
    """
    categories = []
    if not os.path.isdir(SCRIPTS_DIR):
        return categories

    # Get system compatibility and locale
    compat_keys = get_system_compat_keys()
    current_locale = detect_system_language()

    # Add each root script as its own category using header info
    for file_name in os.listdir(SCRIPTS_DIR):
        file_path = os.path.join(SCRIPTS_DIR, file_name)
        if file_name.endswith('.sh') and os.path.isfile(file_path):
            defaults = {
                'name': file_name,
                'description': 'No Description.',
                'icon': 'application-x-executable',
                'reboot': 'no',
                'noconfirm': 'no'
            }
            header = _parse_metadata_file(file_path, defaults, translations)
            # Filter by compatibility and locale
            if not script_is_compatible(file_path, compat_keys):
                continue
            if not script_is_localized(file_path, current_locale):
                continue
            # Filter by container compatibility
            if is_containerized() and not script_is_container_compatible(file_path):
                continue
            # Filter optimization scripts based on installation state
            if not should_show_optimization_script(file_path):
                continue
            categories.append({
                'name': header.get('name', file_name),
                'path': file_path,
                'icon': header.get('icon', 'application-x-executable'),
                'description': header.get('description', ''),
                'is_script': True
            })

    # Add subfolders as categories
    for category_name in os.listdir(SCRIPTS_DIR):
        category_path = os.path.join(SCRIPTS_DIR, category_name)
        if os.path.isdir(category_path):
            info_file_path = os.path.join(category_path, 'category-info.txt')
            defaults = {
                'name': category_name,
                'description': 'A category of scripts.',
                'icon': 'folder-open',
                'mode': 'menu'  # Default mode is menu
            }
            cat_info = _parse_metadata_file(info_file_path, defaults, translations)
            # Use folder name as 'name', but replace with translation if available
            cat_info['name'] = translations.get(category_name, category_name) if translations else category_name
            cat_info['path'] = category_path
            cat_info['is_script'] = False
            categories.append(cat_info)

    return sorted(categories, key=lambda cat: cat['name'])


def get_scripts_for_category(category_path, translations=None):
    """
    Returns a list of scripts for a given category.
    """
    scripts = []
    if not os.path.isdir(category_path):
        return scripts

    # Get system compatibility and locale
    compat_keys = get_system_compat_keys()
    current_locale = detect_system_language()

    for file_name in os.listdir(category_path):
        if file_name.endswith('.sh'):
            file_path = os.path.join(category_path, file_name)
            
            # Filter by compatibility and locale
            if not script_is_compatible(file_path, compat_keys):
                continue
            if not script_is_localized(file_path, current_locale):
                continue
            # Filter by container compatibility
            if is_containerized() and not script_is_container_compatible(file_path):
                continue
            # Filter optimization scripts based on installation state
            if not should_show_optimization_script(file_path):
                continue
            
            defaults = {
                'name': 'No Name', 'version': 'N/A',
                'description': 'No Description.',
                'icon': 'application-x-executable',
                'reboot': 'no',
                'noconfirm': 'no'
            }
            scripts.append(_parse_metadata_file(file_path, defaults, translations))

    return sorted(scripts, key=lambda s: s['name'])
