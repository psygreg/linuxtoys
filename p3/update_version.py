#!/usr/bin/env python3

"""
Version Update Helper Script

This script helps update the version number in both the src/ver file and as a fallback in update_helper.py.
Usage: python update_version.py <new_version>
Example: python update_version.py 4.4
"""

import sys
import re
import os

def update_version_file(new_version, version_file_path="../src/ver"):
    """
    Update the version in the src/ver file.
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(version_file_path), exist_ok=True)
        
        # Write the new version
        with open(version_file_path, 'w', encoding='utf-8') as f:
            f.write(new_version + '\n')
        
        print(f"Successfully updated version file {version_file_path}")
        return True
        
    except Exception as e:
        print(f"Error updating version file: {e}")
        return False

def update_fallback_version_in_code(new_version, file_path="app/update_helper.py"):
    """
    Update the fallback version in the update_helper.py file.
    """
    if not os.path.exists(file_path):
        print(f"Warning: File {file_path} not found!")
        return False
    
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update the fallback version using regex
        pattern = r'return\s+"[^"]*"\s*#\s*Fallback'
        replacement = f'return "{new_version}"  # Fallback'
        
        # Try the more specific pattern first
        new_content = re.sub(pattern, replacement, content)
        
        # If that didn't work, try the general fallback pattern
        if new_content == content:
            pattern = r'#\s*Fallback to hardcoded version\s*\n\s*return\s+"[^"]*"'
            replacement = f'# Fallback to hardcoded version\n    return "{new_version}"'
            new_content = re.sub(pattern, replacement, content)
        
        if new_content == content:
            print("Warning: Fallback version string not found or not changed in code!")
            return False
        
        # Write the updated content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Successfully updated fallback version in code")
        return True
        
    except Exception as e:
        print(f"Error updating fallback version in code: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <new_version>")
        print("Example: python update_version.py 4.4")
        sys.exit(1)
    
    new_version = sys.argv[1]
    
    # Basic version validation
    if not re.match(r'^\d+\.\d+(\.\d+)?$', new_version):
        print("Error: Version should be in format X.Y or X.Y.Z (e.g., 4.4 or 4.4.1)")
        sys.exit(1)
    
    success = True
    
    # Update version file (primary)
    if not update_version_file(new_version):
        success = False
    
    # Update fallback version in code (secondary)
    if not update_fallback_version_in_code(new_version):
        print("Warning: Could not update fallback version in code (this is okay if version file exists)")
    
    if success:
        print(f"Version successfully updated to {new_version}")
        print("Remember to commit this change and create a new release tag!")
    else:
        print("Failed to update version")
        sys.exit(1)
