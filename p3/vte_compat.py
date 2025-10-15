#!/usr/bin/env python3
"""
VTE Version Compatibility Detection

This module provides utilities to detect the VTE (Virtual Terminal Emulator) version
before importing it, allowing the application to gracefully handle unsupported versions
by falling back to a legacy runtime.

VTE 0.80+ introduced breaking changes that require code adjustments. This module
helps determine whether to use the modern or legacy version of the application.
"""

import subprocess
import sys
import re

def get_vte_version():
    """
    Detect the installed VTE version without importing it.
    
    This function uses pkg-config to query the VTE version, which avoids
    import errors that would occur if we tried to import an incompatible version.
    
    Returns:
        tuple: (major, minor, patch) version numbers, or None if VTE is not found
    
    Example:
        >>> version = get_vte_version()
        >>> if version and version >= (0, 80, 0):
        ...     print("VTE 0.80 or newer")
    """
    try:
        # Try pkg-config first (most reliable method)
        result = subprocess.run(
            ['pkg-config', '--modversion', 'vte-2.91'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version_str = result.stdout.strip()
            # Parse version string like "0.80.0" or "0.78.1"
            match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_str)
            if match:
                return tuple(map(int, match.groups()))
        
        # If pkg-config fails, try alternate method with python-gi
        # This is less reliable but works in some environments
        import gi
        gi.require_version('Gtk', '3.0')
        
        # Try to get VTE version by inspecting available versions
        try:
            # This will fail gracefully if VTE is not available
            repository = gi.Repository.get_default()
            if repository.enumerate_versions('Vte'):
                # Try to load version info
                gi.require_version('Vte', '2.91')
                from gi.repository import Vte
                
                # Try to get version from module attributes
                if hasattr(Vte, 'get_major_version'):
                    major = Vte.get_major_version()
                    minor = Vte.get_minor_version() if hasattr(Vte, 'get_minor_version') else 0
                    micro = Vte.get_micro_version() if hasattr(Vte, 'get_micro_version') else 0
                    return (major, minor, micro)
        except (ValueError, ImportError, AttributeError):
            pass
            
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    return None

def is_vte_compatible():
    """
    Check if the installed VTE version is compatible with the modern runtime.
    
    Returns:
        bool: True if VTE is version 0.80 or newer, False if older or not found
    
    Example:
        >>> if is_vte_compatible():
        ...     from app import main
        ... else:
        ...     from app.legacy import main
    """
    version = get_vte_version()
    
    if version is None:
        # If we can't detect VTE, assume it's not installed or too old
        # Default to legacy runtime for safety
        print("Warning: Could not detect VTE version. Using legacy runtime.", file=sys.stderr)
        return False
    
    # Check if version is 0.80 or newer
    # VTE 0.80 introduced breaking API changes
    major, minor, _ = version
    
    if major > 0:
        return True
    elif major == 0 and minor >= 80:
        return True
    else:
        return False

def print_vte_info():
    """
    Print VTE version information for debugging purposes.
    
    This is useful for troubleshooting compatibility issues.
    """
    version = get_vte_version()
    
    if version:
        major, minor, patch = version
        print(f"VTE version detected: {major}.{minor}.{patch}")
        
        if is_vte_compatible():
            print("VTE runtime: MODERN (0.80+)")
        else:
            print("VTE runtime: LEGACY (pre-0.80)")
    else:
        print("VTE version: NOT DETECTED")
        print("VTE runtime: LEGACY (fallback)")

if __name__ == '__main__':
    # When run directly, print version info
    print_vte_info()
