#!/usr/bin/env python3
"""
Simple test script to verify subcategory functionality.
"""

import os
import sys

# Add the p3 directory to the path so we can import the app module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'p3'))

from app.parser import (
    get_categories, 
    get_scripts_for_category, 
    get_subcategories_for_category,
    has_subcategories,
    get_category_mode,
    get_breadcrumb_path,
    is_nested_category,
    get_all_scripts_recursive
)

def test_basic_functionality():
    """Test basic parser functionality."""
    print("=== Testing Basic Functionality ===")
    
    categories = get_categories()
    print(f"Found {len(categories)} categories:")
    
    for cat in categories:
        print(f"  - {cat['name']} ({'script' if cat['is_script'] else 'category'})")
        if not cat['is_script']:
            print(f"    Path: {cat['path']}")
            print(f"    Has subcategories: {cat.get('has_subcategories', False)}")
            print(f"    Display mode: {cat.get('display_mode', 'unknown')}")
    print()

def test_subcategory_detection():
    """Test subcategory detection."""
    print("=== Testing Subcategory Detection ===")
    
    scripts_dir = os.path.join(os.path.dirname(__file__), 'p3', 'scripts')
    
    # Test each category for subcategories
    for item in os.listdir(scripts_dir):
        item_path = os.path.join(scripts_dir, item)
        if os.path.isdir(item_path):
            has_subs = has_subcategories(item_path)
            mode = get_category_mode(item_path)
            print(f"Category '{item}': has_subcategories={has_subs}, mode={mode}")
            
            if has_subs:
                subcats = get_subcategories_for_category(item_path)
                print(f"  Subcategories: {[sub['name'] for sub in subcats]}")
    print()

def test_scripts_and_subcategories():
    """Test getting scripts and subcategories for a category."""
    print("=== Testing Scripts and Subcategories Listing ===")
    
    scripts_dir = os.path.join(os.path.dirname(__file__), 'p3', 'scripts')
    devs_path = os.path.join(scripts_dir, 'devs')
    
    if os.path.exists(devs_path):
        items = get_scripts_for_category(devs_path)
        print(f"Items in 'devs' category ({len(items)} total):")
        
        for item in items:
            item_type = "subcategory" if item.get('is_subcategory') else "script"
            print(f"  - {item['name']} ({item_type})")
    print()

def test_breadcrumb_navigation():
    """Test breadcrumb path generation."""
    print("=== Testing Breadcrumb Navigation ===")
    
    scripts_dir = os.path.join(os.path.dirname(__file__), 'p3', 'scripts')
    test_paths = [
        os.path.join(scripts_dir, 'devs'),
        os.path.join(scripts_dir, 'devs', 'frontend'),
        os.path.join(scripts_dir, 'devs', 'backend'),
        os.path.join(scripts_dir, 'office'),
        scripts_dir  # Root should return empty breadcrumbs
    ]
    
    for path in test_paths:
        if os.path.exists(path):
            breadcrumbs = get_breadcrumb_path(path)
            is_nested = is_nested_category(path)
            rel_path = os.path.relpath(path, scripts_dir) if path != scripts_dir else 'scripts/'
            print(f"Path: {rel_path}")
            print(f"  Is nested: {is_nested}")
            print(f"  Breadcrumbs: {' > '.join([b['name'] for b in breadcrumbs]) if breadcrumbs else 'None'}")
    print()

def test_nested_category_content():
    """Test content listing for nested categories."""
    print("=== Testing Nested Category Content ===")
    
    scripts_dir = os.path.join(os.path.dirname(__file__), 'p3', 'scripts')
    frontend_path = os.path.join(scripts_dir, 'devs', 'frontend')
    backend_path = os.path.join(scripts_dir, 'devs', 'backend')
    
    for path, name in [(frontend_path, 'frontend'), (backend_path, 'backend')]:
        if os.path.exists(path):
            items = get_scripts_for_category(path)
            print(f"Items in 'devs/{name}' subcategory ({len(items)} total):")
            
            for item in items:
                item_type = "subcategory" if item.get('is_subcategory') else "script"
                print(f"  - {item['name']} ({item_type})")
            print()

def test_recursive_script_listing():
    """Test recursive script listing."""
    print("=== Testing Recursive Script Listing ===")
    
    scripts_dir = os.path.join(os.path.dirname(__file__), 'p3', 'scripts')
    devs_path = os.path.join(scripts_dir, 'devs')
    
    if os.path.exists(devs_path):
        all_scripts = get_all_scripts_recursive(devs_path)
        print(f"All scripts in 'devs' category (recursive): {len(all_scripts)} total")
        
        for script in all_scripts[:10]:  # Show first 10 to avoid clutter
            print(f"  - {script['name']} (from {os.path.dirname(script['path'])})")
        if len(all_scripts) > 10:
            print(f"  ... and {len(all_scripts) - 10} more")
    print()

if __name__ == "__main__":
    print("Testing subcategory functionality...\n")
    
    test_basic_functionality()
    test_subcategory_detection()
    test_scripts_and_subcategories()
    test_breadcrumb_navigation()
    test_nested_category_content()
    test_recursive_script_listing()
    
    print("Testing completed!")
