import os
import threading

from .compat import (
    get_system_compat_keys, 
    script_is_compatible, 
    script_is_localized,
    is_containerized,
    script_is_container_compatible,
    should_show_optimization_script,
    get_script_file_data,
    clear_script_file_cache,
)
from .lang_utils import detect_system_language
from . import appstream_parser, git_scripts_manager, new_index, official_index, repo_parser


# Select an immediately available scripts tree. GUI synchronization happens later.
SCRIPTS_DIR = git_scripts_manager.get_available_scripts_dir()


def set_scripts_dir(path):
    """Switch the active scripts root used by parsers and repository lists."""
    global SCRIPTS_DIR
    SCRIPTS_DIR = os.path.abspath(path)
    clear_script_file_cache()
    clear_script_tree_cache()
    repo_parser.clear_runtime_caches()
    appstream_parser.clear_runtime_cache()
    return SCRIPTS_DIR

RESERVED_DIRECTORIES = {
    "lists",
}


# Structural index for the active scripts source. Startup previously rediscovered
# the same directory tree through independent os.listdir()/os.walk() calls in
# category, search, repository-map and display-name paths.
_SCRIPT_TREE_LOCK = threading.RLock()
_SCRIPT_TREE_CACHE = None


def clear_script_tree_cache():
    """Drop the scripts-tree index after a source or filesystem change."""
    global _SCRIPT_TREE_CACHE
    with _SCRIPT_TREE_LOCK:
        _SCRIPT_TREE_CACHE = None


def _build_script_tree_index(root_path):
    """Collect directory relationships and shell-script locations in one traversal."""
    root_path = os.path.abspath(root_path)
    directories = {}
    all_scripts = []
    scripts_by_id = {}

    if not os.path.isdir(root_path):
        return {
            "root": root_path,
            "directories": directories,
            "all_scripts": (),
            "scripts_by_id": {},
        }

    def scan_directory(directory_path):
        try:
            entries = list(os.scandir(directory_path))
        except OSError:
            return

        child_dirs = []
        script_names = []
        file_names = []
        ordered_entries = []

        for entry in entries:
            name = entry.name
            try:
                is_dir = entry.is_dir()
                is_file = entry.is_file()
            except OSError:
                continue

            if is_dir:
                if _should_skip_directory(name):
                    continue
                child_dirs.append(name)
                ordered_entries.append(("dir", name))
                continue

            if not is_file:
                continue

            file_names.append(name)
            if name.endswith(".sh"):
                script_names.append(name)
                ordered_entries.append(("script", name))

        directory_path = os.path.abspath(directory_path)
        directories[directory_path] = {
            "dirs": tuple(child_dirs),
            "scripts": tuple(script_names),
            "files": frozenset(file_names),
            # Preserve os.listdir-style interleaving for recursive collection.
            "entries": tuple(ordered_entries),
        }

        # os.walk exposed all files in the current directory before descending.
        # Preserve that ordering for repository/display-name lookups.
        for file_name in script_names:
            script_path = os.path.join(directory_path, file_name)
            all_scripts.append(script_path)
            script_id = os.path.splitext(file_name)[0].casefold()
            scripts_by_id.setdefault(script_id, script_path)

        for child_name in child_dirs:
            scan_directory(os.path.join(directory_path, child_name))

    scan_directory(root_path)

    return {
        "root": root_path,
        "directories": directories,
        "all_scripts": tuple(all_scripts),
        "scripts_by_id": scripts_by_id,
    }

def _get_script_tree_index():
    """Return the structural index for the current SCRIPTS_DIR."""
    global _SCRIPT_TREE_CACHE
    root_path = os.path.abspath(SCRIPTS_DIR)

    with _SCRIPT_TREE_LOCK:
        cached = _SCRIPT_TREE_CACHE
        if cached is not None and cached.get("root") == root_path:
            return cached

        cached = _build_script_tree_index(root_path)
        _SCRIPT_TREE_CACHE = cached
        return cached


def prepare_script_tree_index():
    """Build the managed scripts-tree index once before parallel consumers start."""
    return _get_script_tree_index()


def _indexed_category_paths():
    """Return every indexed category directory relative to SCRIPTS_DIR."""
    index = _get_script_tree_index()
    root = index["root"]
    result = []

    for directory_path in index["directories"]:
        if directory_path == root:
            continue
        relative = os.path.relpath(directory_path, root).replace(os.sep, "/")
        if relative and relative != ".":
            result.append(relative)

    return tuple(result)


def _indexed_directory(directory_path):
    """Return indexed data only for paths inside the managed scripts source."""
    directory_path = os.path.abspath(directory_path)
    root_path = os.path.abspath(SCRIPTS_DIR)

    try:
        if os.path.commonpath((directory_path, root_path)) != root_path:
            return None
    except ValueError:
        return None

    return _get_script_tree_index()["directories"].get(directory_path)


def _script_names_in(directory_path):
    indexed = _indexed_directory(directory_path)
    if indexed is not None:
        return indexed["scripts"]

    # Local Scripts live outside SCRIPTS_DIR and stay intentionally live rather
    # than being frozen into the managed-source index.
    try:
        return tuple(
            name for name in os.listdir(directory_path)
            if name.endswith(".sh")
            and os.path.isfile(os.path.join(directory_path, name))
        )
    except OSError:
        return ()


def _subcategory_names_in(directory_path):
    indexed = _indexed_directory(directory_path)
    if indexed is not None:
        return indexed["dirs"]

    try:
        return tuple(
            name for name in os.listdir(directory_path)
            if not _should_skip_directory(name)
            and os.path.isdir(os.path.join(directory_path, name))
        )
    except OSError:
        return ()


def _directory_entries_in(directory_path):
    """Return visible script/directory entries in original filesystem order."""
    indexed = _indexed_directory(directory_path)
    if indexed is not None:
        return indexed["entries"]

    ordered = []
    try:
        for name in os.listdir(directory_path):
            path = os.path.join(directory_path, name)
            if name.endswith(".sh") and os.path.isfile(path):
                ordered.append(("script", name))
            elif not _should_skip_directory(name) and os.path.isdir(path):
                ordered.append(("dir", name))
    except OSError:
        pass
    return tuple(ordered)


def _directory_has_file(directory_path, file_name):
    indexed = _indexed_directory(directory_path)
    if indexed is not None:
        return file_name in indexed["files"]
    return os.path.isfile(os.path.join(directory_path, file_name))


def _path_exists(file_path):
    """Avoid a separate stat for files already represented by the tree index."""
    directory_path = os.path.dirname(os.path.abspath(file_path))
    indexed = _indexed_directory(directory_path)
    if indexed is not None:
        return os.path.basename(file_path) in indexed["files"]
    return os.path.exists(file_path)


def _get_negated_scripts(directory_path, compat_keys):
    """Return names negated by compatible scripts in one directory."""
    negated_scripts = set()

    for file_name in _script_names_in(directory_path):
        file_path = os.path.join(directory_path, file_name)
        if not script_is_compatible(file_path, compat_keys):
            continue

        negates_value = get_script_file_data(file_path)["headers"].get("negates")
        if not negates_value:
            continue

        negated_scripts.update(
            name.strip()
            for name in negates_value.split(",")
            if name.strip()
        )

    return negated_scripts

def script_requires_reboot(script_path, system_compat_keys):
    """
    Check whether a script requires a reboot for the current system.
    """
    reboot_value = (
        get_script_file_data(script_path)["headers"]
        .get("reboot", "")
        .strip()
        .lower()
    )
    if reboot_value == "yes":
        return True
    if reboot_value == "ostree":
        return bool({"ostree", "ublue"} & system_compat_keys)
    return False


def _parse_metadata_file(file_path, default_values, translations=None):
    """
    A generic parser for metadata files.

    Shell-script headers reuse compat.get_script_file_data(), so the script is
    opened only once even when compatibility/localization checks also need it.
    """
    metadata = default_values.copy()
    metadata["path"] = file_path

    if not _path_exists(file_path):
        return metadata

    try:
        if file_path.endswith(".sh"):
            headers = get_script_file_data(file_path)["headers"]
            for key, raw_value in headers.items():
                value = raw_value
                if translations and key in ("name", "description"):
                    translated_value = translations.get(value, value)
                    if key == "name" and translated_value != value:
                        metadata["_name_is_translated"] = True
                    if key == "description":
                        current_language = detect_system_language()
                        metadata["description_localized"] = (
                            current_language == "en"
                            or (
                                value in translations
                                and isinstance(translated_value, str)
                                and bool(translated_value.strip())
                            )
                        )
                    value = translated_value

                if key in metadata:
                    metadata[key] = value
                elif key in ("negates", "revert"):
                    metadata[key] = value
                elif key == "needed":
                    metadata["needed"] = value.split() or None
        else:
            with open(file_path, "r", encoding="utf-8") as metadata_file:
                for line in metadata_file:
                    line_content = line.strip()
                    parts = line_content.split(":", 1)
                    if len(parts) != 2:
                        continue

                    key = parts[0].strip().lower()
                    value = parts[1].strip()
                    if translations and key in ("name", "description"):
                        translated_value = translations.get(value, value)
                        if key == "name" and translated_value != value:
                            metadata["_name_is_translated"] = True
                        if key == "description":
                            current_language = detect_system_language()
                            metadata["description_localized"] = (
                                current_language == "en"
                                or (
                                    value in translations
                                    and isinstance(translated_value, str)
                                    and bool(translated_value.strip())
                                )
                            )
                        value = translated_value

                    if key in metadata:
                        metadata[key] = value
                    elif key in ("negates", "revert"):
                        metadata[key] = value
                    elif key == "needed":
                        metadata["needed"] = value.split() or None
    except Exception as error:
        print(f"Error reading metadata from {file_path}: {error}")

    if file_path.endswith(".sh"):
        metadata["is_new"] = new_index.is_new_script(file_path)
        metadata["is_official"] = official_index.is_verified_script(file_path)
        metadata["is_verified"] = metadata["is_official"]
    else:
        metadata["is_new"] = False
        metadata["is_official"] = False
        metadata["is_verified"] = False

    return metadata

def get_subcategories_for_category(category_path, translations=None):
    """Return subcategories for a category using the shared structural index."""
    subcategories = []

    for item_name in _subcategory_names_in(category_path):
        item_path = os.path.join(category_path, item_name)
        info_file_path = os.path.join(item_path, 'category-info.txt')
        defaults = {
            'name': item_name,
            'description': 'A subcategory of scripts.',
            'icon': 'folder-open',
            'mode': 'auto'
        }
        subcat_info = _parse_metadata_file(info_file_path, defaults, translations)
        subcat_info['name'] = translations.get(item_name, item_name) if translations else item_name
        subcat_info['path'] = item_path
        subcat_info['is_script'] = False
        subcat_info['is_subcategory'] = True

        # The structural index already knows whether this directory contains a
        # visible child category. Resolve it once and derive display_mode from
        # the metadata we just parsed instead of calling get_category_mode(),
        # which would repeat the child check and re-read category-info.txt for
        # leaf categories.
        has_children = bool(_subcategory_names_in(item_path))
        subcat_info['has_subcategories'] = has_children
        if has_children:
            subcat_info['display_mode'] = 'menu'
        else:
            mode = str(subcat_info.get('mode', 'auto')).strip().lower()
            subcat_info['display_mode'] = 'checklist' if mode == 'checklist' else 'menu'

        subcategories.append(subcat_info)

    return sorted(subcategories, key=lambda cat: cat['name'])

def get_categories(translations=None):
    """Return top-level categories from the shared scripts-tree index."""
    categories = []
    if not os.path.isdir(SCRIPTS_DIR):
        return categories

    compat_keys = get_system_compat_keys()
    current_locale = detect_system_language()
    negated_scripts = _get_negated_scripts(SCRIPTS_DIR, compat_keys)

    for file_name in _script_names_in(SCRIPTS_DIR):
        file_path = os.path.join(SCRIPTS_DIR, file_name)
        script_name_without_ext = os.path.splitext(file_name)[0]
        if script_name_without_ext in negated_scripts:
            continue

        defaults = {
            'name': file_name,
            'description': '',
            'icon': 'application-x-executable',
            'reboot': 'no',
            'repo': '',
            'revert': 'yes',
        }
        header = _parse_metadata_file(file_path, defaults, translations)
        if not script_is_compatible(file_path, compat_keys):
            continue
        if not script_is_localized(file_path, current_locale):
            continue
        if is_containerized() and not script_is_container_compatible(file_path):
            continue
        if not should_show_optimization_script(file_path):
            continue

        category_entry = {
            'name': header.get('name', file_name),
            'path': file_path,
            'icon': header.get('icon', 'application-x-executable'),
            'description': header.get('description', ''),
            'is_script': True,
            'is_new': header.get('is_new', False),
            'is_official': header.get('is_official', False),
            'is_verified': header.get('is_verified', False)
        }
        if header.get("_name_is_translated"):
            category_entry["registry_name"] = script_name_without_ext
        categories.append(category_entry)

    for category_name in _subcategory_names_in(SCRIPTS_DIR):
        category_path = os.path.join(SCRIPTS_DIR, category_name)
        info_file_path = os.path.join(category_path, 'category-info.txt')
        defaults = {
            'name': category_name,
            'description': 'A category of scripts.',
            'icon': 'folder-open',
            'mode': 'auto'
        }
        cat_info = _parse_metadata_file(info_file_path, defaults, translations)
        cat_info['name'] = translations.get(category_name, category_name) if translations else category_name
        cat_info['path'] = category_path
        cat_info['is_script'] = False
        cat_info['has_subcategories'] = has_subcategories(category_path)
        cat_info['display_mode'] = get_category_mode(category_path, translations)
        categories.append(cat_info)

    return sorted(categories, key=lambda cat: cat['name'])

def get_repo_entries(translations=None):
    """Return all valid dynamic repository entries from scripts/repos.json."""
    return repo_parser.load_repo_entries(SCRIPTS_DIR, translations)


def _get_appstream_curated_entries(translations=None):
    """Return every LinuxToys-curated offer that should suppress AppStream duplicates."""
    return [
        *get_repo_entries(translations),
        *get_all_scripts_recursive(SCRIPTS_DIR, translations),
    ]


def get_appstream_entries(translations=None):
    """Return the last published AppStream catalog as repository-like entries."""
    return appstream_parser.load_entries(
        SCRIPTS_DIR,
        curated_entries=_get_appstream_curated_entries(translations),
        category_paths=_indexed_category_paths(),
    )

def get_repository_map():
    """Return internal software names mapped to upstream repositories."""
    repositories = {}

    for entry in get_repo_entries():
        entry_name = str(entry.get("name", "")).strip()
        entry_id = str(
            entry.get("id")
            or entry.get("script")
            or entry_name
        ).strip()
        repo = entry.get("repo")

        if entry_id and isinstance(repo, str) and repo.strip():
            repositories[entry_id.casefold()] = repo.strip()

    for file_path in _get_script_tree_index()["all_scripts"]:
        file_name = os.path.basename(file_path)
        script_id = os.path.splitext(file_name)[0]
        normalized_id = script_id.casefold()
        if normalized_id in repositories:
            continue

        metadata = _parse_metadata_file(file_path, {"repo": ""})
        repo = metadata.get("repo")
        if isinstance(repo, str) and repo.strip():
            repositories[normalized_id] = repo.strip()

    return repositories

def get_repository(name):
    """Return the upstream repository for a script/repository-list entry."""
    if not name:
        return None

    return get_repository_map().get(
        str(name).strip().casefold()
    )

def get_display_name(name, translations=None):
    """Resolve an internal script/repository name to its UI display name."""
    if not name:
        return name

    normalized_name = str(name).strip().casefold()

    for entry in get_repo_entries(translations):
        entry_name = str(entry.get("name", "")).strip()
        entry_id = str(
            entry.get("id")
            or entry.get("script")
            or entry_name
        ).strip()
        if entry_id.casefold() == normalized_name:
            return entry_name or name

    file_path = _get_script_tree_index()["scripts_by_id"].get(normalized_name)
    if file_path:
        script_id = os.path.splitext(os.path.basename(file_path))[0]
        metadata = _parse_metadata_file(
            file_path,
            {"name": script_id},
            translations,
        )
        return metadata.get("name", script_id)

    return name

def get_scripts_for_category(category_path, translations=None, include_appstream=True):
    """Return scripts and subcategories for one category.

    ``include_appstream=False`` is used by the startup bootstrap so the curated
    LinuxToys interface can be published without waiting for the much larger
    AppStream catalog. Normal callers retain the previous behavior.
    """
    items = []

    if category_path.endswith('.local/linuxtoys/scripts'):
        create_script_name = translations.get('create_new_script_name', 'Create New Script') if translations else 'Create New Script'
        create_script_desc = translations.get('create_new_script_desc', 'Create a new local script') if translations else 'Create a new local script'
        items.append({
            'name': create_script_name,
            'description': create_script_desc,
            'icon': 'document-new',
            'path': category_path,
            'is_script': False,
            'is_subcategory': False,
            'is_create_script': True
        })

    # Managed source paths are represented by the index; Local Scripts and other
    # external paths keep the previous live-filesystem behavior.
    if _indexed_directory(category_path) is None and not os.path.isdir(category_path):
        return items

    compat_keys = get_system_compat_keys()
    current_locale = detect_system_language()
    negated_scripts = _get_negated_scripts(category_path, compat_keys)

    items.extend(get_subcategories_for_category(category_path, translations))

    if category_path.endswith('sysadm') or category_path.endswith('sysadm/'):
        local_dir = f'{os.environ["HOME"]}/.local/linuxtoys/scripts'
        local_scripts_name = translations.get('local_scripts_name', 'Local Scripts') if translations else 'Local Scripts'
        local_scripts_desc = translations.get('local_scripts_desc', 'Drop your scripts here') if translations else 'Drop your scripts here'
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

    for file_name in _script_names_in(category_path):
        file_path = os.path.join(category_path, file_name)
        script_name_without_ext = os.path.splitext(file_name)[0]
        if script_name_without_ext in negated_scripts:
            continue
        if not script_is_compatible(file_path, compat_keys):
            continue
        if not script_is_localized(file_path, current_locale):
            continue
        if is_containerized() and not script_is_container_compatible(file_path):
            continue
        if not should_show_optimization_script(file_path):
            continue

        is_local_script = '.local/linuxtoys/scripts' in file_path
        defaults = {
            'name': 'No Name', 'version': 'N/A',
            'description': '',
            'icon': 'application-x-executable',
            'reboot': 'no',
            'repo': '',
            'revert': 'yes',
        }
        script_info = _parse_metadata_file(file_path, defaults, translations)
        if is_local_script and script_info['name'] == 'No Name':
            script_info['name'] = os.path.splitext(file_name)[0]
        if script_info.pop("_name_is_translated", False):
            script_info["registry_name"] = script_name_without_ext
        script_info['is_script'] = True
        script_info['is_subcategory'] = False
        items.append(script_info)

    items.extend(
        repo_parser.get_entries_for_category(
            SCRIPTS_DIR,
            category_path,
            translations,
        )
    )

    if include_appstream:
        items.extend(
            appstream_parser.get_entries_for_category(
                SCRIPTS_DIR,
                category_path,
                curated_entries=_get_appstream_curated_entries(translations),
                category_paths=_indexed_category_paths(),
            )
        )

    return sorted(
        items,
        key=lambda item: (
            not item.get("is_create_script", False),
            not item.get("is_subcategory", False),
            item["name"],
        ),
    )

def get_all_scripts_recursive(directory_path, translations=None):
    """Recursively return compatible scripts, reusing the structural index."""
    scripts = []
    if _indexed_directory(directory_path) is None and not os.path.isdir(directory_path):
        return scripts

    compat_keys = get_system_compat_keys()
    current_locale = detect_system_language()
    negated_scripts = _get_negated_scripts(directory_path, compat_keys)

    for entry_kind, item_name in _directory_entries_in(directory_path):
        item_path = os.path.join(directory_path, item_name)

        if entry_kind == "dir":
            scripts.extend(get_all_scripts_recursive(item_path, translations))
            continue

        script_name_without_ext = os.path.splitext(item_name)[0]
        if script_name_without_ext in negated_scripts:
            continue
        if not script_is_compatible(item_path, compat_keys):
            continue
        if not script_is_localized(item_path, current_locale):
            continue
        if is_containerized() and not script_is_container_compatible(item_path):
            continue
        if not should_show_optimization_script(item_path):
            continue

        defaults = {
            'name': 'No Name', 'version': 'N/A',
            'description': '',
            'icon': 'application-x-executable',
            'reboot': 'no',
            'repo': '',
        }
        script_info = _parse_metadata_file(item_path, defaults, translations)
        if '.local/linuxtoys/scripts' in item_path and script_info['name'] == 'No Name':
            script_info['name'] = os.path.splitext(item_name)[0]
        if script_info.pop("_name_is_translated", False):
            script_info["registry_name"] = script_name_without_ext
        script_info['is_script'] = True
        script_info['is_subcategory'] = False
        scripts.append(script_info)

    return scripts


def has_subcategories(category_path):
    """Return whether a category contains any visible subcategory."""
    return bool(_subcategory_names_in(category_path))

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
        if _directory_has_file(current_build_path, 'category-info.txt'):
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

def _should_skip_directory(name):
    return name.startswith(".") or name in RESERVED_DIRECTORIES
