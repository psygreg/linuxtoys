import os

# Global path resolver for the app
def get_app_resource_path(*path_parts):
    """
    Get the absolute path to an app resource (icons, etc.)
    
    Args:
        *path_parts: Path components relative to the app directory
    
    Returns:
        str: Absolute path to the resource
    """
    app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, *path_parts)

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
__all__ = ['get_app_resource_path', 'get_icon_path']