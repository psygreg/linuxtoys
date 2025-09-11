"""
Search functionality for LinuxToys application.
Provides search capabilities across script names, descriptions, and categories.
"""

import os
import re
from . import parser
from .compat import get_system_compat_keys, script_is_compatible, script_is_localized, is_containerized, script_is_container_compatible
from .lang_utils import detect_system_language


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
    
    def __init__(self, translations=None):
        self.translations = translations or {}
        self.system_compat_keys = get_system_compat_keys()
        self.current_locale = detect_system_language()
        
    def update_translations(self, translations):
        """Update translations for the search engine."""
        self.translations = translations
        
    def search(self, query, max_results=50):
        """
        Search for scripts matching the query.
        
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
        
        # Search through scripts only (not categories)
        self._search_all_scripts(query, results)
        
        # Sort results by relevance and limit to max_results
        results.sort()
        return results[:max_results]
    
    def _search_categories(self, query, results):
        """Search through categories."""
        categories = parser.get_categories(self.translations)
        
        for category in categories:
            # Skip script categories (we'll handle them in _search_all_scripts)
            if category.get('is_script', False):
                continue
                
            score = self._calculate_match_score(query, category, 'category')
            if score > 0:
                # Add category type marker for UI handling
                category_copy = category.copy()
                category_copy['type'] = 'category'
                results.append(SearchResult(category_copy, 'category', score))
    
    def _search_all_scripts(self, query, results):
        """Search through all scripts recursively."""
        scripts_dir = parser.SCRIPTS_DIR
        
        # Get all scripts from all directories recursively (includes root and nested scripts)
        all_scripts = parser.get_all_scripts_recursive(scripts_dir, self.translations)
        for script_info in all_scripts:
            score = self._calculate_match_score(query, script_info, 'script')
            if score > 0:
                results.append(SearchResult(script_info, 'script', score))
    
    def _is_script_available(self, script_path):
        """Check if a script should be available based on compatibility filters."""
        if not script_is_compatible(script_path, self.system_compat_keys):
            return False
        if not script_is_localized(script_path, self.current_locale):
            return False
        if is_containerized() and not script_is_container_compatible(script_path):
            return False
        # Note: We skip the optimization script filter here as it's specific to certain contexts
        return True
    
    def _get_script_info(self, script_path):
        """Get script information similar to parser._parse_metadata_file."""
        defaults = {
            'name': os.path.basename(script_path),
            'description': 'No Description.',
            'icon': 'application-x-executable',
            'reboot': 'no',
            'noconfirm': 'no'
        }
        
        script_info = defaults.copy()
        script_info['path'] = script_path
        script_info['is_script'] = True
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.startswith('#'):
                        break
                    line_content = line[2:]  # Remove '# '
                    parts = line_content.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        # Translation support for name/description
                        if self.translations and key in ['name', 'description']:
                            value = self.translations.get(value, value)
                        if key in script_info:
                            script_info[key] = value
        except Exception:
            pass
            
        return script_info
    
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


def create_search_engine(translations=None):
    """Factory function to create a search engine instance."""
    return SearchEngine(translations)
