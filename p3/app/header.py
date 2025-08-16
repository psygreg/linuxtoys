import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango
import os

def create_header(translations, category_info=None):
    """
    Creates and returns the main header widget for the application.
    This widget contains the logo, title, and subtitle.
    
    Args:
        translations: Translation dictionary
        category_info: Dictionary with category information (name, description, icon, etc.)
                      If None, shows default LinuxToys header
    """
    # Main container for the header
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    header_box.set_margin_top(4)
    # header_box.set_margin_bottom(16)
    # header_box.set_margin_start(16)
    # header_box.set_margin_end(16)
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
    title_label.set_markup(f"<big><big><b>{title_text}</b></big></big>")
    title_label.set_xalign(0) # Align left

    # Subtitle with text wrapping
    subtitle_label = Gtk.Label(label=subtitle_text)
    subtitle_label.set_line_wrap(True)
    subtitle_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    subtitle_label.set_xalign(0) # Align left

    # Add text to the vertical box
    text_vbox.pack_start(title_label, False, False, 0)
    text_vbox.pack_start(subtitle_label, False, False, 0)
    
    # Add logo and text box to the main header box
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
            logo = Gtk.Image.new_from_file("app/icons/app-icon.png")
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
        # If only a filename, presume it's in the icons folder
        if not os.path.isabs(icon_value) and '/' not in icon_value:
            icon_path = os.path.join(os.path.dirname(__file__), 'icons', icon_value)
        else:
            icon_path = icon_value
        if os.path.exists(icon_path):
            icon_widget = Gtk.Image.new_from_file(icon_path)
        else:
            icon_widget = Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)
    else:
        icon_widget = Gtk.Image.new_from_icon_name(icon_value, Gtk.IconSize.DIALOG)
    
    icon_widget.set_pixel_size(64)
    return icon_widget
