"""
Language detection and translation utilities using Gettext.
"""

import gettext
import os
import builtins
import locale

APP_NAME = "linuxtoys"
LOCALE_DIR = os.path.join(os.path.dirname(__file__), '..', 'locale')

def setup_gettext():
    """
    Set up the gettext translation system.
    This installs the _() function in the builtins, making it globally available.
    """
    try:
        # Set up the translation domain
        gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
        gettext.textdomain(APP_NAME)
        
        # Install the translator function into the builtins
        builtins._ = gettext.gettext
    except Exception as e:
        print(f"Could not set up gettext: {e}")
        # Fallback to a no-op function if gettext fails
        builtins._ = lambda s: s

def detect_system_language() -> str:
    """
    Detects the system's language code (e.g., 'en', 'pt_BR').
    Falls back to environment variables or a default value.
    """
    try:
        # Get the primary language code from the default locale
        lang_code, _ = locale.getdefaultlocale()
        if lang_code:
            return lang_code
    except (ValueError, TypeError):
        # Fallback if locale is not set correctly
        pass

    # Fallback to environment variables
    lang = os.getenv("LANG") or os.getenv("LANGUAGE")
    if lang:
        return lang.split(".")[0].split(":")[0]

    return "en_US"  # Default fallback
