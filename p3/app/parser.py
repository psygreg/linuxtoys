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

def get_subcategories_for_category(category_path, translations=None):
    """
    Returns a list of subcategories for a given category.
    
    Note: Categories that contain subcategories will automatically be set to 'menu' mode,
    regardless of their mode setting in category-info.txt. Only leaf categories 
    (without subdirectories) can use 'checklist' mode.
    """
    subcategories = []
    if not os.path.isdir(category_path):
        return subcategories

    for item_name in os.listdir(category_path):
        item_path = os.path.join(category_path, item_name)
        if os.path.isdir(item_path):
            info_file_path = os.path.join(item_path, 'category-info.txt')
            defaults = {
                'name': item_name,
                'description': 'A subcategory of scripts.',
                'icon': 'folder-open',
                'mode': 'auto'  # subcategories can have their own mode
            }
            subcat_info = _parse_metadata_file(info_file_path, defaults, translations)
            # Use folder name as 'name', but replace with translation if available
            subcat_info['name'] = translations.get(item_name, item_name) if translations else item_name
            subcat_info['path'] = item_path
            subcat_info['is_script'] = False
            subcat_info['is_subcategory'] = True
            # Ensure subcategories also have the proper mode set
            subcat_info['has_subcategories'] = has_subcategories(item_path)
            subcat_info['display_mode'] = get_category_mode(item_path, translations)
            subcategories.append(subcat_info)

    return sorted(subcategories, key=lambda cat: cat['name'])


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
                'description': '',
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
                'mode': 'auto'  # auto, menu, checklist
            }
            cat_info = _parse_metadata_file(info_file_path, defaults, translations)
            # Use folder name as 'name', but replace with translation if available
            cat_info['name'] = translations.get(category_name, category_name) if translations else category_name
            cat_info['path'] = category_path
            cat_info['is_script'] = False
            cat_info['has_subcategories'] = has_subcategories(category_path)
            cat_info['display_mode'] = get_category_mode(category_path, translations)
            categories.append(cat_info)

    return sorted(categories, key=lambda cat: cat['name'])


def get_scripts_for_category(category_path, translations=None):
    """
    Returns a list of scripts and subcategories for a given category.
    """
    items = []
    if not os.path.isdir(category_path):
        return items

    # Get system compatibility and locale
    compat_keys = get_system_compat_keys()
    current_locale = detect_system_language()

    # First, add subcategories
    subcategories = get_subcategories_for_category(category_path, translations)
    items.extend(subcategories)
    
    # Add Local Scripts as a subcategory when viewing sysadm directory
    if category_path.endswith('sysadm') or category_path.endswith('sysadm/'):
        local_dir = f'{os.environ["HOME"]}/.local/linuxtoys/scripts'
        local_scripts_name = translations.get('local_scripts_name', 'Local Scripts')
        local_scripts_desc = translations.get('local_scripts_desc', 'Drop your scripts here')
        
        items.append({
            'name': local_scripts_name,
            'description': local_scripts_desc,
            'icon': 'local-script.svg',
            'mode': 'auto',
            'path': local_dir,
            'is_script': False,
            'is_subcategory': True,
            'has_subcategories': False,
            'display_mode': 'menu'
        })

    # Then, add scripts
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
            
            # Check if this is a local script (in user's local directory)
            is_local_script = '.local/linuxtoys/scripts' in file_path
            
            defaults = {
                'name': 'No Name', 'version': 'N/A',
                'description': '',
                'icon': 'application-x-executable',
                'reboot': 'no',
                'noconfirm': 'no'
            }
            script_info = _parse_metadata_file(file_path, defaults, translations)
            
            # For local scripts, use filename if no name was found in headers
            if is_local_script and script_info['name'] == 'No Name':
                # Remove .sh extension and use filename as display name
                script_info['name'] = os.path.splitext(file_name)[0]
            
            script_info['is_script'] = True
            script_info['is_subcategory'] = False
            items.append(script_info)

    return sorted(items, key=lambda s: (not s.get('is_subcategory', False), s['name']))


def get_all_scripts_recursive(directory_path, translations=None):
    """
    Recursively gets all scripts from a directory and its subdirectories.
    This is useful for bulk operations or searching across nested categories.
    """
    scripts = []
    if not os.path.isdir(directory_path):
        return scripts

    # Get system compatibility and locale
    compat_keys = get_system_compat_keys()
    current_locale = detect_system_language()

    for item_name in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item_name)
        
        if item_name.endswith('.sh') and os.path.isfile(item_path):
            # Filter by compatibility and locale
            if not script_is_compatible(item_path, compat_keys):
                continue
            if not script_is_localized(item_path, current_locale):
                continue
            # Filter by container compatibility
            if is_containerized() and not script_is_container_compatible(item_path):
                continue
            # Filter optimization scripts based on installation state
            if not should_show_optimization_script(item_path):
                continue
            
            defaults = {
                'name': 'No Name', 'version': 'N/A',
                'description': '',
                'icon': 'application-x-executable',
                'reboot': 'no',
                'noconfirm': 'no'
            }
            script_info = _parse_metadata_file(item_path, defaults, translations)
            
            # Check if this is a local script (in user's local directory)
            is_local_script = '.local/linuxtoys/scripts' in item_path
            
            # For local scripts, use filename if no name was found in headers
            if is_local_script and script_info['name'] == 'No Name':
                # Remove .sh extension and use filename as display name
                script_info['name'] = os.path.splitext(item_name)[0]
            
            script_info['is_script'] = True
            script_info['is_subcategory'] = False
            scripts.append(script_info)
            
        elif os.path.isdir(item_path):
            # Recursively get scripts from subdirectories
            scripts.extend(get_all_scripts_recursive(item_path, translations))

    return scripts


def has_subcategories(category_path):
    """
    Check if a category has any subdirectories (subcategories).
    """
    if not os.path.isdir(category_path):
        return False
    
    for item_name in os.listdir(category_path):
        item_path = os.path.join(category_path, item_name)
        if os.path.isdir(item_path):
            return True
    
    return False


def get_category_mode(category_path, translations=None):
    """
    Determine the display mode for a category based on its metadata and content.
    Returns 'menu' for navigation or 'checklist' for bulk operations.
    
    Important: Categories with subcategories MUST use 'menu' mode.
    Only leaf categories (no subdirectories) can use 'checklist' mode.
    """
    # First check if this category has subcategories
    has_subs = has_subcategories(category_path)
    
    # Categories with subcategories MUST be in menu mode
    if has_subs:
        return 'menu'
    
    # For leaf categories (no subcategories), check the metadata preference
    info_file_path = os.path.join(category_path, 'category-info.txt')
    defaults = {
        'mode': 'auto'  # auto, menu, checklist
    }
    cat_info = _parse_metadata_file(info_file_path, defaults, translations)
    
    mode = cat_info.get('mode', 'auto')
    
    if mode == 'checklist':
        # Explicit checklist mode - only allowed for leaf categories
        return 'checklist'

    # menu mode or any other value defaults to menu
    return 'menu'


def get_breadcrumb_path(current_path, translations=None):
    """
    Generate a breadcrumb navigation path for nested categories.
    Returns a list of dictionaries with 'name' and 'path' for each level.
    """
    breadcrumbs = []
    
    # Start from scripts directory
    scripts_path = os.path.abspath(SCRIPTS_DIR)
    current_abs_path = os.path.abspath(current_path)
    
    # If current path is not within scripts directory, return empty
    if not current_abs_path.startswith(scripts_path):
        return breadcrumbs
    
    # Get relative path from scripts directory
    rel_path = os.path.relpath(current_abs_path, scripts_path)
    
    # If we're in the root scripts directory, return empty
    if rel_path == '.':
        return breadcrumbs
    
    # Build breadcrumb path
    path_parts = rel_path.split(os.sep)
    current_build_path = scripts_path
    
    for part in path_parts:
        current_build_path = os.path.join(current_build_path, part)
        
        # Get the display name for this level
        display_name = part
        if translations:
            display_name = translations.get(part, part)
        
        # Try to get name from category-info.txt if it exists
        info_file = os.path.join(current_build_path, 'category-info.txt')
        if os.path.exists(info_file):
            defaults = {'name': part}
            cat_info = _parse_metadata_file(info_file, defaults, translations)
            display_name = cat_info.get('name', display_name)
        
        breadcrumbs.append({
            'name': display_name,
            'path': current_build_path
        })
    
    return breadcrumbs


def is_nested_category(category_path):
    """
    Check if a given path represents a nested category (not a top-level category).
    """
    scripts_path = os.path.abspath(SCRIPTS_DIR)
    category_abs_path = os.path.abspath(category_path)
    
    if not category_abs_path.startswith(scripts_path):
        return False
    
    rel_path = os.path.relpath(category_abs_path, scripts_path)
    return os.sep in rel_path
