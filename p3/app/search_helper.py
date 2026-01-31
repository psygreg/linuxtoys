"""
Search functionality for LinuxToys application.
Provides search capabilities across script names, descriptions, and categories.
Uses caching for improved performance during runtime.
"""

import os
import re
from . import parser
from .compat import (
    get_system_compat_keys, 
    script_is_compatible, 
    script_is_localized, 
    is_containerized, 
    script_is_container_compatible,
    should_show_optimization_script
)
from .lang_utils import detect_system_language


class ScriptCache:
    """
    Caches available scripts based on system compatibility.
    Built on app startup to provide fast searches without traversing directories.
    
    The cache stores:
    - All compatible scripts filtered by system compat keys
    - Locale-specific scripts
    - Container compatibility
    - Optimization script visibility state
    """
    
    def __init__(self):
        self.scripts = []  # List of cached script info dicts
        self.is_populated = False
        self.system_compat_keys = get_system_compat_keys()
        self.current_locale = detect_system_language()
        self.is_containerized = is_containerized()
    
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
        scripts_dir = parser.SCRIPTS_DIR
        
        # Get all scripts from main directory recursively
        self._collect_scripts_from_directory(scripts_dir, translations)
        
        # Also get local scripts directory
        local_scripts_dir = f'{os.environ.get("HOME", "")}/.local/linuxtoys/scripts'
        if os.path.isdir(local_scripts_dir):
            self._collect_scripts_from_directory(local_scripts_dir, translations)
        
        self.is_populated = True
    
    def _collect_scripts_from_directory(self, directory_path, translations=None):
        """Recursively collect scripts from a directory."""
        if not os.path.isdir(directory_path):
            return
        
        # Get the set of scripts that should be hidden due to negation
        negated_scripts = parser._get_negated_scripts(directory_path, self.system_compat_keys)
        
        for item_name in os.listdir(directory_path):
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
                    'noconfirm': 'no',
                    'repo': ''
                }
                script_info = parser._parse_metadata_file(item_path, defaults, translations)
                
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
    
    def invalidate(self):
        """Invalidate the cache, forcing repopulation on next use."""
        self.is_populated = False
        self.scripts = []
    
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
        # Sort by score (descending), then by name
        if self.match_score != other.match_score:
            return self.match_score > other.match_score
        return self.item_info.get('name', '').lower() < other.item_info.get('name', '').lower()


class SearchEngine:
    """Main search engine for LinuxToys."""
    
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
        
        Args:
            query: Search string
            max_results: Maximum number of results to return
            
        Returns:
            List of SearchResult objects, sorted by relevance
        """
        if not query or len(query.strip()) < 2:
            return []
            
        query = query.strip().lower()
        results = []
        
        # Search through cached scripts (much faster than directory traversal)
        self._search_cached_scripts(query, results)
        
        # Sort results by relevance and limit to max_results
        results.sort()
        return results[:max_results]
    
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

    def _calculate_match_score(self, query, item_info, item_type):
        """
        Calculate relevance score for a search match.
        Higher score = more relevant.
        """
        name = item_info.get('name', '').lower()
        description = item_info.get('description', '').lower()
        score = 0
        
        # Exact name match gets highest score
        if query == name:
            score += 100
        # Name starts with query
        elif name.startswith(query):
            score += 80
        # Query appears in name
        elif query in name:
            score += 60
        
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
