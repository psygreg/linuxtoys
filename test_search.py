#!/usr/bin/env python3

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from search_helper import create_search_engine

def test_search():
    """Test the search functionality for 'Create New Script' option."""
    
    # Create mock translations
    translations = {
        'create_new_script_name': 'Create New Script',
        'create_new_script_desc': 'Create a new local script'
    }
    
    # Create search engine
    search_engine = create_search_engine(translations)
    
    # Test searches that should find the "Create New Script" option
    test_queries = [
        'create',
        'new',
        'script',
        'create new',
        'new script',
        'create script',
        'Create New Script'
    ]
    
    print("Testing search functionality for 'Create New Script' option:")
    print("=" * 60)
    
    for query in test_queries:
        results = search_engine.search(query)
        create_script_results = [r for r in results if r.item_info.get('is_create_script')]
        
        print(f"Query: '{query}'")
        print(f"  Total results: {len(results)}")
        print(f"  'Create New Script' found: {len(create_script_results) > 0}")
        if create_script_results:
            result = create_script_results[0]
            print(f"  Score: {result.match_score}")
            print(f"  Name: {result.item_info['name']}")
            print(f"  Description: {result.item_info['description']}")
        print()

if __name__ == "__main__":
    test_search()