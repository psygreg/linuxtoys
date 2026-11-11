#!/usr/bin/env python3

"""
Version Update Helper Script

This script helps update the version number in:
1. src/ver (single source of truth read by the build tooling)
2. p3/app/updater/__init__.py (updater's __version__)

Both paths are resolved relative to this script, so it can be run from any
working directory. The updater reads __version__ from __init__.py, so
updating that file keeps the application and the version file in sync.

Usage: python3 update_version.py <new_version>
Example: python3 update_version.py 4.4
"""

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VERSION_FILE_PATH = os.path.join(REPO_ROOT, "src", "ver")
UPDATER_INIT_PATH = os.path.join(REPO_ROOT, "p3", "app", "updater", "__init__.py")


def update_version_file(
    new_version: str,
    version_file_path: str = VERSION_FILE_PATH,
) -> bool:
    """
    Update the version in the src/ver file.
    """
    if not os.path.isfile(version_file_path):
        print(f"Error: version file {version_file_path} not found!")
        return False

    try:
        with open(version_file_path, 'w', encoding='utf-8') as f:
            f.write(new_version + '\n')

        print(f"Successfully updated version file {version_file_path}")
        return True

    except Exception as e:
        print(f"Error updating version file: {e}")
        return False


def update_updater_version(
    new_version: str,
    file_path: str = UPDATER_INIT_PATH,
) -> bool:
    """
    Update the version in the updater's __init__.py file.
    """
    if not os.path.isfile(file_path):
        print(f"Warning: File {file_path} not found!")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        pattern = r'__version__\s*=\s*"[^"]*"'
        replacement = f'__version__ = "{new_version}"'

        new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            if f'__version__ = "{new_version}"' in content:
                print("updater/__init__.py already at requested version")
                return True
            print("Warning: __version__ string not found or not changed in updater!")
            return False

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print("Successfully updated version in updater/__init__.py")
        return True

    except Exception as e:
        print(f"Error updating updater version: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 update_version.py <new_version>")
        print("Example: python3 update_version.py 4.4")
        sys.exit(1)

    new_version = sys.argv[1]

    if not re.match(r'^\d+\.\d+(\.\d+)?$', new_version):
        print("Error: Version should be in format X.Y or X.Y.Z (e.g., 4.4 or 4.4.1)")
        sys.exit(1)

    success = True

    if not update_version_file(new_version):
        success = False

    if not update_updater_version(new_version):
        success = False

    if success:
        print(f"Version successfully updated to {new_version}")
        print("Remember to commit this change and create a new release tag!")
    else:
        print("Failed to update version")
        sys.exit(1)
