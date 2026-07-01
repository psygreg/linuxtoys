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
    Tries the requested file, then falls back to .png if .svg fails to render.
    
    Args:
        icon_name: Name of the icon file (e.g., 'app-icon.png')
    
    Returns:
        str: Absolute path to the icon, or None if not found or not renderable
    """
    def _validate(path):
        try:
            from .gtk_common import GdkPixbuf
            GdkPixbuf.Pixbuf.new_from_file(path)
            return True
        except Exception:
            return False

    icon_path = get_app_resource_path('icons', icon_name)
    if os.path.exists(icon_path) and _validate(icon_path):
        return icon_path

    base_name = os.path.splitext(icon_name)[0]
    for ext in ('.png', '.svg'):
        alt_name = base_name + ext
        alt_path = get_app_resource_path('icons', alt_name)
        if os.path.exists(alt_path) and _validate(alt_path):
            return alt_path

    return None

# Make these functions available at package level
__all__ = ['get_app_resource_path', 'get_icon_path']

try:
    from . import skills_fetcher
except ImportError:
    skills_fetcher = None