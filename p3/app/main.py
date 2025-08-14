from email import header
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import sys
import os
import json

from .window import AppWindow
from .compat import get_system_compat_keys, script_is_compatible
from .lang_utils import load_translations, create_translator
from .cli_helper import run_manifest_mode


class Application(Gtk.Application):
    def __init__(self, translations, *args, **kwargs):
        super().__init__(*args, application_id="com.linuxtoys.app", **kwargs)
        self.window = None
        self.translations = translations

    def do_activate(self):
        if not self.window:
            self.window = AppWindow(self, self.translations)
            self.load_css()
        self.window.present()

    def load_css(self):
        try:
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path('app/style.css')
            screen = Gdk.Screen.get_default()
            Gtk.StyleContext.add_provider_for_screen(
                screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"Error loading CSS: {e}")

# Use lang_utils for all translation functionality
translations = load_translations()  # Auto-detect language from lang_utils
_ = create_translator()  # Create translator function from lang_utils

def run():
    # Check for CLI manifest mode
    if os.environ.get('LT_MANIFEST') == '1':
        # Run in CLI mode using manifest.txt
        sys.exit(run_manifest_mode(translations))
    
    # FIX: Set the application icon before running
    # Make sure you have an icon at 'app/icons/app-icon.png'
    icon_path = os.path.abspath("app/icons/app-icon.png")
    if os.path.exists(icon_path):
        Gtk.Window.set_default_icon_from_file(icon_path)
    else:
        print(f"Warning: App icon not found at {icon_path}")

    # Use the already loaded translations from lang_utils
    app = Application(translations)
    app.run(sys.argv)
