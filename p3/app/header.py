import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango

def create_header(translations):
    """
    Creates and returns the main header widget for the application.
    This widget contains the logo, title, and subtitle.
    """
    # Main container for the header
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
    header_box.set_margin_top(15)
    header_box.set_margin_bottom(15)
    header_box.set_margin_start(15)
    header_box.set_margin_end(15)
    header_box.set_halign(Gtk.Align.CENTER)

    # Logo
    try:
        logo = Gtk.Image.new_from_file("app/icons/app-icon.png")
    except Exception:
        # Fallback to a system icon if the logo is not found
        logo = Gtk.Image.new_from_icon_name("applications-utilities", Gtk.IconSize.DIALOG)
        logo.set_pixel_size(64)

    # Vertical box for Title and Subtitle
    text_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    
    # Title using Pango Markup for styling (bold and larger text)
    title_label = Gtk.Label()
    title_label.set_markup("<big><b>LinuxToys</b></big>")
    title_label.set_xalign(0) # Align left

    # Subtitle with text wrapping
    subtitle_label = Gtk.Label(
        label=translations.get("subtitle")
    )
    subtitle_label.set_line_wrap(True)
    subtitle_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    subtitle_label.set_xalign(0) # Align left

    # Add text to the vertical box
    text_vbox.pack_start(title_label, False, False, 0)
    text_vbox.pack_start(subtitle_label, False, False, 0)
    
    # Add logo and text box to the main header box
    header_box.pack_start(logo, False, False, 0)
    header_box.pack_start(text_vbox, True, True, 0)

    return header_box
