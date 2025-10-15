import os

# Global path resolver for the legacy app
# Legacy runtime is in app/legacy/, so we need to go up to app/ for local resources
# and up to p3/ for shared resources (scripts, libs)

def get_app_resource_path(*path_parts):
    """
    Get the absolute path to an app resource (icons, etc.)
    Resources like icons are stored in app/, not app/legacy/
    
    Args:
        *path_parts: Path components relative to the app directory
    
    Returns:
        str: Absolute path to the resource
    """
    # Go up one level from app/legacy/ to app/
    legacy_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(legacy_dir)
    return os.path.join(app_dir, *path_parts)

def get_shared_resource_path(*path_parts):
    """
    Get the absolute path to a shared resource (scripts, libs, etc.)
    Shared resources are in p3/scripts and p3/libs, not in app/
    
    Args:
        *path_parts: Path components relative to the p3 directory
    
    Returns:
        str: Absolute path to the resource
    """
    # Go up two levels from app/legacy/ to p3/
    legacy_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(legacy_dir)
    p3_dir = os.path.dirname(app_dir)
    return os.path.join(p3_dir, *path_parts)

def get_icon_path(icon_name):
    """
    Get the absolute path to an icon file.
    
    Args:
        icon_name: Name of the icon file (e.g., 'app-icon.png')
    
    Returns:
        str: Absolute path to the icon, or None if not found
    """
    icon_path = get_app_resource_path('icons', icon_name)
    if os.path.exists(icon_path):
        return icon_path
    return None

# Make these functions available at package level
__all__ = ['get_app_resource_path', 'get_shared_resource_path', 'get_icon_path']