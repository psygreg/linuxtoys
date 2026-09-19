"""
Search functionality for LinuxToys application.
Provides search capabilities across script names, descriptions, and categories.
Uses caching for improved performance during runtime.

Works transparently with both git-synced and bundled scripts:
- Scripts are sourced from parser.SCRIPTS_DIR which may be git-synced or bundled
- Automatically filters hidden directories (e.g., .git) from git-synced repos
- Includes local scripts from ~/.local/linuxtoys/scripts
"""

import os
import re
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from . import parser, popularity, installed_packages
from .compat import (
    get_system_compat_keys,
    script_is_compatible,
    script_is_localized,
    is_containerized,
    script_is_container_compatible,
    should_show_optimization_script,
    get_revert_capability,
    should_enable_manual_revert,
)
from .lang_utils import detect_system_language
from .revert_helper import _get_executed_script_names
from .official_index import is_verified_script, is_verified_name


def _iter_completed_futures(future_map):
    """Yield futures as they finish without importing another public iterator."""
    pending = set(future_map)
    while pending:
        done, pending = wait(pending, return_when=FIRST_COMPLETED)
        yield from done


class ScriptCache:
    """
    Caches available scripts based on system compatibility.
    Built on app startup to provide fast searches without traversing directories.

    The cache stores:
    - All compatible scripts filtered by system compat keys
    - Locale-specific scripts
    - Container compatibility
    - Optimization script visibility state
    - Removable state (whether the script can currently be uninstalled)
    """

    def __init__(self):
        self.scripts = []  # List of cached script info dicts
        self.is_populated = False
        self.system_compat_keys = get_system_compat_keys()
        self.current_locale = detect_system_language()
        self.is_containerized = is_containerized()
        self._removable_cache = {}  # script_path -> bool

    def populate(self, translations=None):
        """
        Populate the cache with all available scripts for the current system.
        This should be called once on app startup.

        Args:
            translations: Dictionary of translations for script names/descriptions
        """
        if self.is_populated:
            return  # Already populated

        self.scripts = []
        self._removable_cache = {}
        scripts_dir = parser.SCRIPTS_DIR

        # Get all scripts from main directory recursively
        self._collect_scripts_from_directory(scripts_dir, translations)

        for repo_item in parser.get_repo_entries(translations):
            self.scripts.append(repo_item)

        for appstream_item in parser.get_appstream_entries(translations):
            self.scripts.append(appstream_item)

        # Also get local scripts directory
        local_scripts_dir = f'{os.environ.get("HOME", "")}/.local/linuxtoys/scripts'
        if os.path.isdir(local_scripts_dir):
            self._collect_scripts_from_directory(local_scripts_dir, translations)

        # Pre-compute removable state for all cached scripts in one pass
        self._populate_removable_cache()

        self.is_populated = True

    def populate_from_category_cache(self, category_cache):
        """Build the search cache from already parsed category data.

        This avoids a second recursive filesystem walk during startup. Repository
        entries and normal scripts are deduplicated by their stable path/virtual path.
        """
        if self.is_populated:
            return

        self.scripts = []
        self._removable_cache = {}
        seen = set()

        def add_item(item):
            if not item.get("is_script"):
                return
            key = item.get("path") or (
                "repo-name", item.get("name", "").casefold()
            )
            if key in seen:
                return
            seen.add(key)
            self.scripts.append(item)

        for category in category_cache.get_categories():
            add_item(category)

        for scripts in category_cache.scripts_by_category.values():
            for item in scripts:
                add_item(item)

        self._populate_removable_cache()
        self.is_populated = True

    def _collect_scripts_from_directory(self, directory_path, translations=None):
        """Recursively collect scripts from a directory."""
        if not os.path.isdir(directory_path):
            return

        # Get the set of scripts that should be hidden due to negation
        negated_scripts = parser._get_negated_scripts(directory_path, self.system_compat_keys)

        for item_name in os.listdir(directory_path):
            # Skip hidden directories and files (e.g., .git, .gitignore)
            # Important for git-synced scripts which include .git directory
            if item_name.startswith('.'):
                continue

            item_path = os.path.join(directory_path, item_name)

            if item_name.endswith('.sh') and os.path.isfile(item_path):
                # Check if this script is negated by another compatible script
                script_name_without_ext = os.path.splitext(item_name)[0]
                if script_name_without_ext in negated_scripts:
                    continue

                # Filter by compatibility and locale
                if not script_is_compatible(item_path, self.system_compat_keys):
                    continue
                if not script_is_localized(item_path, self.current_locale):
                    continue
                # Filter by container compatibility
                if self.is_containerized and not script_is_container_compatible(item_path):
                    continue
                # Filter optimization scripts based on installation state
                if not should_show_optimization_script(item_path):
                    continue

                # Parse script metadata
                defaults = {
                    'name': 'No Name',
                    'version': 'N/A',
                    'description': '',
                    'icon': 'application-x-executable',
                    'reboot': 'no',
                    'repo': '',
                }
                script_info = parser._parse_metadata_file(item_path, defaults, translations)

                # Store the full path for later category extraction
                script_info['path'] = item_path

                # For local scripts, use filename if no name was found
                is_local_script = '.local/linuxtoys/scripts' in item_path
                if is_local_script and script_info['name'] == 'No Name':
                    script_info['name'] = os.path.splitext(item_name)[0]

                script_info['is_script'] = True
                script_info['is_subcategory'] = False
                self.scripts.append(script_info)

            elif os.path.isdir(item_path):
                # Recursively collect from subdirectories
                self._collect_scripts_from_directory(item_path, translations)

    def get_all_scripts(self):
        """Get all cached scripts."""
        return self.scripts.copy()

    def _populate_removable_cache(self):
        """
        Pre-compute the removable state for every cached script.

        This avoids repeatedly opening the registry file and re-reading each
        script's revert header while browsing categories or search results.
        """
        executed_names = _get_executed_script_names()

        for script_info in self.scripts:
            script_path = script_info.get("path", "")
            script_name = script_info.get("name", "")

            # AppStream entries can be installed outside LinuxToys. Their observed
            # package state is therefore part of removability, not just Registry state.
            if script_info.get("is_appstream_entry"):
                self._removable_cache[script_path] = (
                    script_name in executed_names
                    or installed_packages.match(script_info) is not None
                )
                continue

            if script_info.get("is_repo_entry"):
                self._removable_cache[script_path] = (
                    script_name in executed_names
                )
                continue

            if not script_path or not os.path.isfile(script_path):
                self._removable_cache[script_path] = False
                continue

            script_name = script_info.get('name', '')
            if not script_name:
                self._removable_cache[script_path] = False
                continue

            revert_capability = get_revert_capability(script_path, self.system_compat_keys)
            if revert_capability == 'no':
                self._removable_cache[script_path] = False
                continue

            if revert_capability == 'internal':
                self._removable_cache[script_path] = script_name in executed_names
                continue

            if not should_enable_manual_revert(script_path, self.system_compat_keys):
                self._removable_cache[script_path] = False
                continue

            self._removable_cache[script_path] = script_name in executed_names

    def refresh_removable_cache(self):
        """
        Refresh only the removable state of cached scripts.

        This re-reads the action registry without rebuilding script metadata,
        compatibility information, translations, or categories.
        """
        self._removable_cache.clear()
        self._populate_removable_cache()

    def is_script_removable(self, script_info):
        script_path = script_info.get("path", "")

        if script_path in self._removable_cache:
            return self._removable_cache[script_path]

        if script_info.get("is_appstream_entry"):
            executed_names = _get_executed_script_names()
            return (
                script_info.get("name") in executed_names
                or installed_packages.match(script_info) is not None
            )

        if script_info.get("is_repo_entry"):
            executed_names = _get_executed_script_names()
            return self._repo_entry_is_removable(
                script_info,
                executed_names,
            )

        # Normal physical-script fallback
        if (
            not script_info.get("is_script")
            or not script_path
            or not os.path.isfile(script_path)
        ):
            return False

        script_name = script_info.get("name", "")
        if not script_name:
            return False

        revert_capability = get_revert_capability(
            script_path,
            self.system_compat_keys,
        )

        if revert_capability == "no":
            return False

        executed_names = _get_executed_script_names()

        if revert_capability == "internal":
            return script_name in executed_names

        if not should_enable_manual_revert(
            script_path,
            self.system_compat_keys,
        ):
            return False

        return script_name in executed_names

    def _repo_entry_is_removable(self, script_info, executed_names):
        return (
            script_info.get("is_repo_entry", False)
            and script_info.get("name") in executed_names
        )

    def update_removable_for_script(self, script_info):
        """
        Recompute the removable state for a single script.
        """
        script_path = script_info.get("path", "")
        if not script_path:
            return

        # Remove the previous value so is_script_removable() performs
        # a direct registry-based computation instead of returning stale data.
        self._removable_cache.pop(script_path, None)
        self._removable_cache[script_path] = self.is_script_removable(script_info)

    def invalidate(self):
        """Invalidate the cache, forcing repopulation on next use."""
        self.is_populated = False
        self.scripts = []
        self._removable_cache = {}

    def refresh_for_translations(self, translations):
        """
        Invalidate and repopulate the cache with new translations.
        Call this when language settings change.

        Args:
            translations: Updated dictionary of translations
        """
        self.invalidate()
        self.populate(translations)


class CategoryCache:
    """
    Caches all categories and their scripts for fast navigation.
    Built on app startup to provide fast category/script loading without traversing directories.

    The cache stores:
    - All top-level categories with their metadata
    - All scripts for each category
    - Subcategory information
    - All filtered by system compatibility
    """

    def __init__(self):
        self.categories = []  # List of cached category info dicts
        self.scripts_by_category = {}  # Dict mapping category path -> list of scripts
        self.is_populated = False
        self.system_compat_keys = get_system_compat_keys()
        self.current_locale = detect_system_language()
        self.is_containerized = is_containerized()

    def populate(
        self,
        translations=None,
        top_level_ready=None,
        top_level_ready_min_scripts=0,
        max_workers=4,
    ):
        """Populate category data with bounded parallel filesystem parsing.

        The scripts-tree structure is built once before workers start. Top-level
        categories are then parsed concurrently, followed by dynamically discovered
        nested categories using the same bounded executor. Only this coordinator
        thread mutates ``scripts_by_category`` so readers never race worker writes.

        ``top_level_ready`` retains the progressive startup contract: it receives a
        stable snapshot as soon as enough top-level normal scripts are available, or
        once all top-level work finishes for small trees.
        """
        if self.is_populated:
            return

        self.categories = []
        self.scripts_by_category = {}

        # Build shared structural state before the pool starts. Without this, several
        # workers could all arrive at the tree-cache initialization lock together and
        # gain no useful parallelism during their first category lookup.
        parser.prepare_script_tree_index()
        self.categories = parser.get_categories(translations)

        # Warm repository-list parsing once before category workers fan out. Every
        # category consults this shared dataset; doing the first load here avoids
        # several workers redundantly scanning scripts/lists on the same cold miss.
        parser.get_repo_entries(translations)

        top_level_paths = []
        seen_top_level = set()
        for category in self.categories:
            if category.get('is_script'):
                continue
            category_path = category.get('path', '')
            if not category_path:
                continue
            category_path = os.path.abspath(category_path)
            if category_path in seen_top_level or not os.path.isdir(category_path):
                continue
            seen_top_level.add(category_path)
            top_level_paths.append(category_path)

        minimum_scripts = max(0, int(top_level_ready_min_scripts or 0))
        worker_count = max(1, min(int(max_workers or 1), len(top_level_paths) or 1))
        top_level_published = False
        top_level_script_count = 0
        completed_top_level = set()
        nested_paths = []

        def publish_top_level(force=False):
            nonlocal top_level_published
            if top_level_published or top_level_ready is None:
                return
            if not force and minimum_scripts > 0 and top_level_script_count < minimum_scripts:
                return

            categories_snapshot = self.categories.copy()
            scripts_snapshot = {
                path: items.copy()
                for path, items in self.scripts_by_category.items()
            }
            top_level_published = True
            top_level_ready(categories_snapshot, scripts_snapshot)

        def parse_category(category_path):
            # Keep AppStream off the startup-critical category walk. The normal
            # LinuxToys tree is enough to render the interface immediately; the
            # larger AppStream dataset is merged after the structural walk.
            scripts = parser.get_scripts_for_category(
                category_path, translations, include_appstream=False
            )
            popularity.sort_for_browse(scripts)
            return category_path, scripts

        # Phase 1: top-level categories. Completion order is intentionally allowed to
        # differ from source order for latency, while consumers still iterate the
        # original category list and therefore retain stable display ordering.
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="linuxtoys-category",
        ) as executor:
            futures = {
                executor.submit(parse_category, path): path
                for path in top_level_paths
            }

            for future in _iter_completed_futures(futures):
                category_path = futures[future]
                try:
                    _, scripts = future.result()
                except Exception as error:
                    print(f"Error parsing category {category_path}: {error}")
                    scripts = []

                self.scripts_by_category[category_path] = scripts
                completed_top_level.add(category_path)

                for item in scripts:
                    if item.get('is_subcategory'):
                        subcategory_path = item.get('path', '')
                        if subcategory_path:
                            nested_paths.append(os.path.abspath(subcategory_path))
                    elif item.get('is_script') and not item.get('is_create_script'):
                        top_level_script_count += 1

                if minimum_scripts > 0:
                    publish_top_level()

            publish_top_level(force=True)

            # Phase 2: nested categories. Use a dynamic queue because parsing one
            # category reveals its children. The coordinator alone owns ``visited``
            # and cache mutation; workers only return plain parsed data.
            visited = set(completed_top_level)
            pending = {}

            def submit_nested(path):
                path = os.path.abspath(path)
                if path in visited or path in pending.values() or not os.path.isdir(path):
                    return
                visited.add(path)
                pending[executor.submit(parse_category, path)] = path

            for path in nested_paths:
                submit_nested(path)

            while pending:
                done, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
                for future in done:
                    category_path = pending.pop(future)
                    try:
                        _, scripts = future.result()
                    except Exception as error:
                        print(f"Error parsing category {category_path}: {error}")
                        scripts = []

                    self.scripts_by_category[category_path] = scripts
                    for item in scripts:
                        if item.get('is_subcategory'):
                            subcategory_path = item.get('path', '')
                            if subcategory_path:
                                submit_nested(subcategory_path)

        # Phase 3: enrich the already-published structural cache with AppStream.
        # Load/transform the catalog once, then distribute its entries by category
        # instead of making every category independently enter the AppStream parser.
        appstream_entries = parser.get_appstream_entries(translations)
        appstream_by_category = {}
        for item in appstream_entries:
            category = str(item.get("category", "")).strip()
            if not category:
                continue
            category_path = os.path.abspath(os.path.join(parser.SCRIPTS_DIR, category))
            appstream_by_category.setdefault(category_path, []).append(item)

        for category_path, appstream_items in appstream_by_category.items():
            existing = self.scripts_by_category.get(category_path)
            if existing is None:
                continue
            existing.extend(appstream_items)
            popularity.sort_for_browse(existing)

        self.is_populated = True

    def get_categories(self):
        """Get all cached categories."""
        return self.categories.copy()

    def get_scripts_for_category(self, category_path):
        """Get scripts for a specific category from cache.

        If the path is not in the cache, returns an empty list.
        The caller should have a fallback to parser.get_scripts_for_category().
        """
        return self.scripts_by_category.get(category_path, []).copy()

    def invalidate(self):
        """Invalidate the cache, forcing repopulation on next use."""
        self.is_populated = False
        self.categories = []
        self.scripts_by_category = {}

    def refresh_for_translations(self, translations):
        """
        Invalidate and repopulate the cache with new translations.
        Call this when language settings change.

        Args:
            translations: Updated dictionary of translations
        """
        self.invalidate()
        self.populate(translations)


class SearchResult:
    """Represents a single search result."""

    def __init__(self, item_info, match_type, match_score):
        self.item_info = item_info
        self.match_type = match_type  # 'name', 'description', 'category'
        self.match_score = match_score  # Higher score = better match

    def __lt__(self, other):
        # Relevance remains authoritative. Flathub popularity is only a tie-breaker
        # when both equally relevant results have real cached Flathub scores.
        if self.match_score != other.match_score:
            return self.match_score > other.match_score

        own_popularity = popularity.flathub_search_tiebreak(self.item_info)
        other_popularity = popularity.flathub_search_tiebreak(other.item_info)
        if (
            own_popularity is not None
            and other_popularity is not None
            and own_popularity != other_popularity
        ):
            return own_popularity > other_popularity

        return self.item_info.get('name', '').lower() < other.item_info.get('name', '').lower()


class SearchEngine:
    """Main search engine for LinuxToys."""

    SEARCH_ALIASES = {
        "r": ("positron", "rstudio"),
    }

    def __init__(self, translations=None, script_cache=None):
        self.translations = translations or {}
        self.system_compat_keys = get_system_compat_keys()
        self.current_locale = detect_system_language()
        self.script_cache = script_cache or ScriptCache()

    def update_translations(self, translations):
        """
        Update translations for the search engine and invalidate cache.
        The cache will be repopulated with new translations in background.

        Args:
            translations: Dictionary of translations
        """
        self.translations = translations

        # Invalidate cache and repopulate with new translations in a background thread
        def refresh_cache():
            try:
                self.script_cache.refresh_for_translations(translations)
            except Exception as e:
                print(f"Error refreshing search cache for translations: {e}")

        import threading
        threading.Thread(target=refresh_cache, daemon=True).start()

    def set_cache(self, script_cache):
        """Set the script cache to use."""
        self.script_cache = script_cache

    def search(self, query, max_results=50):
        """
        Search for scripts matching the query using the cache.
        Returns results grouped by category for improved UX.

        Args:
            query: Search string
            max_results: Maximum number of results to return (per category)

        Returns:
            List of category groups: [
                {
                    'category_name': 'Category Name',
                    'category_path': '/path/to/category',
                    'best_match_score': 95,  # Highest score in this category
                    'scripts': [SearchResult, ...]  # Sorted by relevance
                },
                ...
            ]
            Sorted by best_match_score (descending)
        """
        if not query or len(query.strip()) < 2:
            return []

        query = query.strip().lower()
        results = []

        # "linuxtoys" is a special discovery filter: show everything curated by
        # LinuxToys, plus AppStream entries explicitly selected as KNOWN_POPULAR.
        if query == "linuxtoys":
            self._search_linuxtoys_entries(results)
        else:
            # Search through cached scripts (much faster than directory traversal)
            self._search_cached_scripts(query, results)

        # Group results by category
        grouped = self._group_results_by_category(results, max_results)

        return grouped

    def _group_results_by_category(self, results, max_results_per_category):
        """
        Group search results by category and sort appropriately.
        Scripts without a proper category are kept as 'Uncategorized' without a header.

        Args:
            results: List of SearchResult objects
            max_results_per_category: Max results to include per category

        Returns:
            List of category group dicts sorted by best match score
        """
        # Group results by category
        category_groups = {}

        for result in results:
            item_info = result.item_info

            # Resolve every managed category through the parser's breadcrumb
            # metadata.  Explicit category values are relative paths such as
            # ``sys/sysadm`` rather than translation keys, so translating the whole
            # string directly produces labels like "Sys/Sysadm".
            category_key = str(item_info.get("category", "") or "").strip().strip("/")
            if category_key:
                category_path = os.path.abspath(os.path.join(parser.SCRIPTS_DIR, category_key))
                # Normal category navigation uses the directory leaf as the
                # translation key (see parser.get_categories() /
                # get_subcategories_for_category()).  Do the same here rather than
                # get_breadcrumb_path(), whose category-info fallback can replace a
                # translated leaf with the raw directory name.
                leaf = category_key.rsplit("/", 1)[-1]
                category_name = self.translations.get(
                    leaf,
                    leaf.replace("_", " ").title(),
                )
            else:
                # Traditional scripts do not carry category metadata. Resolve their
                # containing directory through the same parser path so both sources
                # use identical category naming rules.
                path = str(item_info.get("path", "") or "")
                if path and "/" in path:
                    category_path = os.path.abspath(path.rsplit("/", 1)[0])
                    try:
                        relative_category = os.path.relpath(category_path, parser.SCRIPTS_DIR)
                    except ValueError:
                        relative_category = "."

                    if relative_category not in ("", ".") and not relative_category.startswith(".."):
                        leaf = relative_category.replace(os.sep, "/").rsplit("/", 1)[-1]
                        category_name = self.translations.get(
                            leaf,
                            leaf.replace("_", " ").title(),
                        )
                    else:
                        category_name = self.translations.get(
                            "uncategorized",
                            "Uncategorized",
                        )
                        category_path = "uncategorized"
                else:
                    category_name = self.translations.get(
                        "uncategorized",
                        "Uncategorized",
                    )
                    category_path = "uncategorized"

            # The same logical category can be reached through different internal
            # paths (for example a curated entry and a filesystem script). Group by
            # the resolved UI name so search never renders duplicate category headers.
            group_key = category_name.strip().casefold()

            if group_key not in category_groups:
                category_groups[group_key] = {
                    "category_name": category_name,
                    "category_path": category_path,
                    "best_match_score": 0,
                    "scripts": [],
                    "show_header": (
                        category_name
                        != self.translations.get(
                            "uncategorized",
                            "Uncategorized",
                        )
                    ),
                }

            if result.match_score > category_groups[group_key]["best_match_score"]:
                category_groups[group_key]["best_match_score"] = result.match_score

            category_groups[group_key]["scripts"].append(result)

        # Sort scripts within each category by relevance
        for group in category_groups.values():
            group['scripts'].sort()
            group['scripts'] = group['scripts'][:max_results_per_category]

        # Convert to list and sort by best match score (descending)
        grouped_list = list(category_groups.values())
        grouped_list.sort(key=lambda g: g['best_match_score'], reverse=True)

        return grouped_list

    def _extract_category_name(self, script_path):
        """
        Extract a human-readable category name from the script path.
        Handles nested categories properly.

        Examples:
        - '/scripts/utils/some_script.sh' -> 'Utils' (or translated)
        - '/scripts/drivers/nvidia/nvidia_installer.sh' -> 'Nvidia' (or 'Drivers - Nvidia' if no leaf translation)
        - '/scripts/pdefaults.sh' -> 'Other' (root-level, no category)

        Uses translations when available (using folder names as keys).
        Falls back to title-cased path components with hierarchy separators.

        Args:
            script_path: Full path to the script

        Returns:
            Category name or 'Other' if not determinable or root-level script
        """
        if not script_path:
            return 'Other'

        # Split the path and find the category parts
        parts = script_path.split('/')

        # Look for script directory indicators
        if 'scripts' in parts:
            idx = parts.index('scripts')

            # Extract all directory parts after 'scripts' (excluding the .sh file)
            category_parts = []
            for i in range(idx + 1, len(parts)):
                part = parts[i]
                if part.endswith('.sh'):
                    # Found the script file, stop collecting category parts
                    break
                category_parts.append(part)

            if not category_parts:
                # Root-level script with no category directory
                return 'Other'

            # Construct full nested category path for grouping key
            full_category_path = '/'.join(category_parts)

            # Try to get translated name for the full nested path first
            translated_name = self.translations.get(full_category_path)
            if translated_name:
                return translated_name

            # Try to get translated name for the leaf (last) category
            leaf_category = category_parts[-1]
            translated_name = self.translations.get(leaf_category)
            if translated_name:
                return translated_name

            # Fallback: build display name with hierarchy separators
            # For nested categories, show as "Parent - Leaf" or "Parent > Leaf"
            display_parts = [p.replace('_', ' ').title() for p in category_parts]
            display_name = ' - '.join(display_parts)
            return display_name

        return 'Other'

    def _search_linuxtoys_entries(self, results):
        """Return LinuxToys-curated entries and developer-selected popular apps."""
        if not self.script_cache.is_populated:
            return

        for script_info in self.script_cache.get_all_scripts():
            if (
                popularity.is_linuxtoys_curated(script_info)
                or popularity.is_known_popular(script_info)
            ):
                results.append(SearchResult(script_info, "script", 100))

    def _search_cached_scripts(self, query, results):
        """Search through cached scripts."""
        if not self.script_cache.is_populated:
            return  # Cache not ready

        for script_info in self.script_cache.get_all_scripts():
            score = self._calculate_match_score(query, script_info, 'script')
            if score > 0:
                results.append(SearchResult(script_info, 'script', score))

        # Add "Create New Script" option as a searchable item
        self._search_create_new_script_option(query, results)

    def _search_categories(self, query, results):
        """Search through categories."""
        categories = parser.get_categories(self.translations)

        for category in categories:
            # Skip script categories (we'll handle them in cached scripts)
            if category.get('is_script', False):
                continue

            score = self._calculate_match_score(query, category, 'category')
            if score > 0:
                # Add category type marker for UI handling
                category_copy = category.copy()
                category_copy['type'] = 'category'
                results.append(SearchResult(category_copy, 'category', score))

    def _search_create_new_script_option(self, query, results):
        """Search for the 'Create New Script' option."""
        # Always include the create script option since the directory can be created on demand
        # We don't need to check if the directory exists as it will be created when needed

        local_scripts_dir = f'{os.environ.get("HOME", "")}/.local/linuxtoys/scripts'
        create_script_name = self.translations.get('create_new_script_name', 'Create New Script')
        create_script_desc = self.translations.get('create_new_script_desc', 'Create a new local script')

        create_script_item = {
            'name': create_script_name,
            'description': create_script_desc,
            'icon': 'document-new',
            'path': local_scripts_dir,
            'is_script': False,
            'is_subcategory': False,
            'is_create_script': True
        }

        # Calculate match score for the create script option
        score = self._calculate_match_score(query, create_script_item, 'create_script')
        if score > 0:
            results.append(SearchResult(create_script_item, 'create_script', score))

    @staticmethod
    def _searchable_package_names(item_info):
        """Return package/application IDs that should participate in search."""
        names = []
        seen = set()

        def add(value):
            if isinstance(value, str):
                value = value.strip().lower()
                if value and value not in seen:
                    seen.add(value)
                    names.append(value)
            elif isinstance(value, (list, tuple, set)):
                for item in value:
                    add(item)
            elif isinstance(value, dict):
                for item in value.values():
                    add(item)

        # The selected AppStream source.
        add(item_info.get("package-name"))

        # Source selection can preserve a discarded native/Flathub alternative.
        # Search both so e.g. native "0ad" still finds "0 A.D." even when the
        # displayed/default entry is the Flathub application ID, and vice versa.
        for option in item_info.get("source_options") or ():
            if isinstance(option, dict):
                add(option.get("package-name"))

        return names

    def _calculate_match_score(self, query, item_info, item_type):
        """
        Calculate relevance score for a search match.
        Higher score = more relevant.
        """
        name = item_info.get('name', '').lower()
        description = item_info.get('description', '').lower()
        score = 0

        # Check for 'new' keyword match (English or translated)
        translated_new = self.translations.get('new_spec_key', 'new').lower()
        if (query == 'new' or query == translated_new) and item_info.get('is_new', False):
            score += 90  # High score for exact 'new' keyword match

        # Check for 'official' keyword match (English or translated)
        translated_official = self.translations.get(
            'official_spec_key',
            'official'
        ).lower()

        if query == 'official' or query == translated_official:
            if item_info.get('is_repo_entry'):
                is_official = is_verified_name(item_info.get('name', ''))
            else:
                is_official = is_verified_script(item_info.get('path', ''))

            if is_official:
                score += 90

        # Exact name match gets highest score
        if query == name:
            score += 100
        # Name starts with query
        elif name.startswith(query):
            score += 80
        # Query appears in name
        elif query in name:
            score += 60

        # Internal search aliases
        aliases = self.SEARCH_ALIASES.get(name, ())
        if any(query in alias for alias in aliases):
            score += 60

        # AppStream/native package names are useful aliases too. Keep them below
        # display-name matches, but above descriptions. Source alternatives are
        # included so both the native package and Flathub application ID remain
        # searchable after duplicate-source collapsing.
        package_names = self._searchable_package_names(item_info)
        if query in package_names:
            score += 90
        elif any(package.startswith(query) for package in package_names):
            score += 70
        elif any(query in package for package in package_names):
            score += 50

        # Description matches (lower priority than name)
        if query in description:
            score += 30

        # Boost scores for certain item types
        if item_type == 'category':
            score += 10  # Categories slightly boosted for navigation
        elif item_type == 'create_script':
            score += 15  # Create script option gets a good boost for utility

        # Boost for shorter names (more specific matches)
        if score > 0 and len(name) < 20:
            score += 5

        # Additional scoring for word boundary matches
        if score > 0:
            # Check if query matches word boundaries (more relevant)
            word_pattern = r'\b' + re.escape(query) + r'\b'
            if re.search(word_pattern, name):
                score += 20
            elif re.search(word_pattern, description):
                score += 10

        return score


def create_search_engine(translations=None, script_cache=None):
    """
    Factory function to create a search engine instance.

    Args:
        translations: Dictionary of translations
        script_cache: Optional ScriptCache instance (creates one if not provided)

    Returns:
        SearchEngine instance configured with the cache
    """
    if script_cache is None:
        script_cache = ScriptCache()
    return SearchEngine(translations, script_cache)
