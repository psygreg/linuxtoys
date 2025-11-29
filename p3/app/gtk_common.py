"""
Common GTK imports and initialization for LinuxToys GUI components.
This module centralizes GTK imports to reduce code duplication.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, Pango, Vte

# Export commonly used components
__all__ = ['Gtk', 'Gdk', 'GLib', 'GdkPixbuf', 'Pango', 'gi', 'Vte']
