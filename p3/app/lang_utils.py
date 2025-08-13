"""
Language detection and translation utilities
Similar to linuxtoys.lib _lang_ function but for Python modules
"""

import os
import json
import glob


def detect_system_language():
    """
    Detect system language using LANG environment variable
    Returns language code (e.g., 'pt', 'en', 'es')
    """
    # Get language from LANG environment variable (first 2 characters)
    lang = os.environ.get('LANG', 'en_US')[:2]
    
    # Check available translation files
    available_langs = []
    lang_dir = os.path.join(os.path.dirname(__file__), '..', 'libs', 'lang')
    
    if os.path.exists(lang_dir):
        for lang_file in glob.glob(os.path.join(lang_dir, '*.json')):
            lang_code = os.path.basename(lang_file).replace('.json', '')
            available_langs.append(lang_code)
    
    # If detected language is available, use it; otherwise fall back to English
    if lang in available_langs:
        return lang
    else:
        return 'en'


def load_translations(lang_code=None):
    """
    Load translations for specified language code, or auto-detect if None
    Returns dictionary of translations
    """
    if lang_code is None:
        lang_code = detect_system_language()
    
    lang_dir = os.path.join(os.path.dirname(__file__), '..', 'libs', 'lang')
    
    try:
        lang_file = os.path.join(lang_dir, f'{lang_code}.json')
        with open(lang_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fall back to English if specified language file doesn't exist
        try:
            en_file = os.path.join(lang_dir, 'en.json')
            with open(en_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # If no translation files exist, return empty dict
            print(f"Warning: No translation files found in {lang_dir}")
            return {}


def get_available_languages():
    """
    Get list of available language codes based on existing .json files
    Returns list of language codes
    """
    available_langs = []
    lang_dir = os.path.join(os.path.dirname(__file__), '..', 'libs', 'lang')
    
    if os.path.exists(lang_dir):
        for lang_file in glob.glob(os.path.join(lang_dir, '*.json')):
            lang_code = os.path.basename(lang_file).replace('.json', '')
            available_langs.append(lang_code)
    
    return sorted(available_langs)


def create_translator(lang_code=None):
    """
    Create a translator function similar to the _() function
    Usage: _ = create_translator(); translated = _('key')
    """
    translations = load_translations(lang_code)
    
    def translate(key):
        return translations.get(key, key)
    
    return translate


# Default translator instance for convenience
_ = create_translator()
