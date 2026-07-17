"""
Shared GTK initialization and reusable GUI helpers.
"""

from __future__ import annotations
import os
from typing import Optional
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Vte", "2.91")

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango, Vte

DEFAULT_ICON_NAME = "application-x-executable"
DEFAULT_FLOWBOX_COLUMNS = 5
DEFAULT_ICON_SIZE = 38

def get_toplevel_window(widget: Gtk.Widget) -> Optional[Gtk.Window]:
    """Return the widget's top-level GTK window when available."""
    toplevel = widget.get_toplevel()

    if isinstance(toplevel, Gtk.Window):
        return toplevel

    return None

def create_flowbox(
    *,
    max_children_per_line: int = DEFAULT_FLOWBOX_COLUMNS,
    selection_mode: Gtk.SelectionMode = Gtk.SelectionMode.NONE,
    homogeneous: bool = True,
    margin_left: int = 32,
    margin_top: int = 8,
    margin_right: int = 32,
    margin_bottom: int = 4,
    column_spacing: int = 16,
    row_spacing: int = 12,
) -> Gtk.FlowBox:
    """Create a consistently configured application flowbox."""
    flowbox = Gtk.FlowBox()
    flowbox.set_valign(Gtk.Align.START)
    flowbox.set_max_children_per_line(max_children_per_line)
    flowbox.set_activate_on_single_click(False)
    flowbox.set_selection_mode(selection_mode)
    flowbox.set_homogeneous(homogeneous)

    flowbox.set_margin_left(margin_left)
    flowbox.set_margin_top(margin_top)
    flowbox.set_margin_right(margin_right)
    flowbox.set_margin_bottom(margin_bottom)

    flowbox.set_column_spacing(column_spacing)
    flowbox.set_row_spacing(row_spacing)

    return flowbox

def load_scaled_pixbuf(
    path: str,
    width: int,
    height: int,
    preserve_aspect_ratio: bool = True,
) -> Optional[GdkPixbuf.Pixbuf]:
    """Load an image at a requested size, returning None on failure."""
    if not path or not os.path.isfile(path):
        return None

    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(
            path,
            width,
            height,
            preserve_aspect_ratio,
        )
    except GLib.Error:
        return None

def create_icon_image(
    icon_name: str = DEFAULT_ICON_NAME,
    *,
    pixel_size: int = DEFAULT_ICON_SIZE,
) -> Gtk.Image:
    """Create a theme icon using the application's standard sizing."""
    image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
    image.set_pixel_size(pixel_size)
    return image

def clear_container(container: Gtk.Container) -> None:
    """Remove all children from a GTK container."""
    for child in list(container.get_children()):
        container.remove(child)

def escape_markup(value: object) -> str:
    """Safely convert a value for use in Pango markup."""
    return GLib.markup_escape_text(str(value or ""))

__all__ = [
    "Gdk",
    "GdkPixbuf",
    "GLib",
    "Gtk",
    "Pango",
    "Vte",
    "DEFAULT_ICON_NAME",
    "DEFAULT_FLOWBOX_COLUMNS",
    "DEFAULT_ICON_SIZE",
    "clear_container",
    "create_flowbox",
    "create_icon_image",
    "escape_markup",
    "get_toplevel_window",
    "load_scaled_pixbuf",
]