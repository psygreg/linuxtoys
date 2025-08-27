import sys
import os

# Only import GTK-related modules if not in CLI mode
if os.environ.get('LT_MANIFEST') != '1':
    from .gtk_common import Gtk, Gdk
    from .window import AppWindow

from .lang_utils import load_translations, create_translator
from .cli_helper import run_manifest_mode
from .update_helper import run_update_check
from . import get_app_resource_path, get_icon_path


# Only define GUI classes if not in CLI mode
if os.environ.get('LT_MANIFEST') != '1':
    class Application(Gtk.Application):
        def __init__(self, translations, *args, **kwargs):
            super().__init__(*args, application_id="com.linuxtoys.app", **kwargs)
            self.window = None
            self.translations = translations
            
            # Set application properties for better desktop integration
            self.set_application_id("com.linuxtoys.app")

        def do_activate(self):
            if not self.window:
                self.window = AppWindow(self, self.translations)
                self.load_css()
            self.window.present()

        def load_css(self):
            try:
                css_provider = Gtk.CssProvider()
                # Use the app resource path resolver
                css_path = get_app_resource_path('style.css')
                css_provider.load_from_path(css_path)
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
    
    # In GUI mode, use the new GitHub API-based update checker
    # This works for both git-cloned and packaged versions
    try:
        run_update_check(show_dialog=True, verbose=False, translations=translations)
    except Exception as e:
        print(f"Update check failed: {e}")
    
    # FIX: Set the application icon before running
    # Use the icon path resolver
    icon_path = get_icon_path("linuxtoys.svg")
    if icon_path:
        Gtk.Window.set_default_icon_from_file(icon_path)
    else:
        print(f"Warning: App icon not found (linuxtoys.svg)")

    # Use the already loaded translations from lang_utils
    app = Application(translations)
    app.run(sys.argv)
