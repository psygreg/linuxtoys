from .gtk_common import Gtk, Pango, GdkPixbuf
import os
from . import get_icon_path
from .lang_utils import escape_for_markup

def create_header(translations, category_info=None):
    """
    Creates and returns the main header widget for the application.
    This widget contains the logo, title, and subtitle.
    
    Args:
        translations: Translation dictionary
        category_info: Dictionary with category information (name, description, icon, etc.)
                      If None, shows default LinuxToys header (clickable for About dialog)
    """
    # Main container for the header
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    header_box.set_margin_top(4)
    # header_box.set_margin_bottom(16)
    header_box.set_margin_start(90)  # Add 40px left padding
    header_box.set_margin_end(90)    # Add 40px right padding
    header_box.set_halign(Gtk.Align.CENTER)

    # Logo/Icon
    logo = _create_icon_widget(category_info)

    # Vertical box for Title and Subtitle
    text_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    
    # Title and subtitle based on category or default
    if category_info:
        title_text = category_info.get('name', 'LinuxToys')
        subtitle_text = category_info.get('description', translations.get("subtitle", ""))
    else:
        title_text = "LinuxToys"
        subtitle_text = translations.get("subtitle", "")

    # Title using Pango Markup for styling (bold and larger text)
    title_label = Gtk.Label()
    title_label.set_margin_top(10) ## margem acima do titulo
    title_label.set_markup(f"<big><big><b>{escape_for_markup(title_text)}</b></big></big>")
    title_label.set_xalign(0) # Align left

    # Subtitle with text wrapping
    subtitle_label = Gtk.Label(label=subtitle_text)
    subtitle_label.set_line_wrap(True)
    subtitle_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    subtitle_label.set_xalign(0) # Align left

    # Add text to the vertical box
    text_vbox.pack_start(title_label, False, False, 0)
    text_vbox.pack_start(subtitle_label, False, False, 0)
    
    # If this is the main menu (no category_info), hide the header entirely
    if not category_info:
        # Hide the entire header by setting visibility to false
        header_box.set_visible(False)
        
        # Also hide the logo and text boxes individually for cleaner layout
        logo.set_visible(False)
        text_vbox.set_visible(False)
    else:
        # Non-clickable version for category pages - show full header
        logo.set_margin_end(10)  # 10px padding between icon and text
        header_box.pack_start(logo, False, False, 0)
        header_box.pack_start(text_vbox, True, True, 0)

    return header_box

def _create_icon_widget(category_info):
    """
    Creates an icon widget based on category info, similar to menu buttons.
    Falls back to default app icon if no category info provided.
    """
    if not category_info:
        # Default LinuxToys icon
        try:
            icon_path = get_icon_path("linuxtoys.svg")
            if icon_path:
                # For SVG files, load as pixbuf with specific size
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        icon_path, 72, 72, True
                    )
                    logo = Gtk.Image.new_from_pixbuf(pixbuf)
                except Exception:
                    # Fallback if SVG loading fails
                    logo = Gtk.Image.new_from_icon_name("applications-utilities", Gtk.IconSize.DIALOG)
                    logo.set_pixel_size(64)
            else:
                raise FileNotFoundError("linuxtoys.svg not found")
        except Exception:
            # Fallback to a system icon if the logo is not found
            logo = Gtk.Image.new_from_icon_name("applications-utilities", Gtk.IconSize.DIALOG)
            logo.set_pixel_size(64)
        return logo

    # Get icon from category info
    icon_value = category_info.get('icon', 'application-x-executable')
    icon_widget = None
    
    # If icon_value looks like a file path or just a filename, use Gtk.Image.new_from_file
    if icon_value.endswith('.png') or icon_value.endswith('.svg'):
        # If only a filename, use the global icon path resolver
        if not os.path.isabs(icon_value) and '/' not in icon_value:
            icon_path = get_icon_path(icon_value)
        else:
            icon_path = icon_value if os.path.exists(icon_value) else None
            
        if icon_path and os.path.exists(icon_path):
            try:
                # Load image files as pixbuf with proper scaling, especially for SVG
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    icon_path, 64, 64, True
                )
                icon_widget = Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                # Fallback if loading fails
                icon_widget = Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)
                icon_widget.set_pixel_size(64)
        else:
            icon_widget = Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)
            icon_widget.set_pixel_size(64)
    else:
        icon_widget = Gtk.Image.new_from_icon_name(icon_value, Gtk.IconSize.DIALOG)
        icon_widget.set_pixel_size(64)
    
    return icon_widget
