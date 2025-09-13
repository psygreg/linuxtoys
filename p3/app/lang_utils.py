"""
Language detection and translation utilities
Similar to linuxtoys.lib _lang_ function but for Python modules
"""

import os
import json
import glob
import configparser


def get_config_dir():
    """
    Get the configuration directory for LinuxToys
    Creates it if it doesn't exist
    """
    config_dir = os.path.expanduser("~/.config/linuxtoys")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_saved_language():
    """
    Get the user's saved language preference
    Returns None if no preference is saved
    """
    config_file = os.path.join(get_config_dir(), "language.conf")
    if os.path.exists(config_file):
        try:
            config = configparser.ConfigParser()
            config.read(config_file)
            return config.get('language', 'code', fallback=None)
        except Exception:
            return None
    return None


def save_language(lang_code):
    """
    Save the user's language preference
    """
    config_dir = get_config_dir()
    config_file = os.path.join(config_dir, "language.conf")
    
    config = configparser.ConfigParser()
    config['language'] = {'code': lang_code}
    
    try:
        with open(config_file, 'w') as f:
            config.write(f)
        return True
    except Exception as e:
        print(f"Error saving language preference: {e}")
        return False


def detect_system_language():
    """
    Detect language using saved preference first, then system language
    Returns language code (e.g., 'pt', 'en', 'es')
    """
    # First check if user has saved a language preference
    saved_lang = get_saved_language()
    if saved_lang:
        # Verify the saved language is still available
        available_langs = []
        lang_dir = os.path.join(os.path.dirname(__file__), '..', 'libs', 'lang')
        
        if os.path.exists(lang_dir):
            for lang_file in glob.glob(os.path.join(lang_dir, '*.json')):
                lang_code = os.path.basename(lang_file).replace('.json', '')
                available_langs.append(lang_code)
        
        if saved_lang in available_langs:
            return saved_lang
    
    # Fall back to system language detection
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


def get_language_names():
    """
    Get mapping of language codes to human-readable names
    Returns dictionary of {code: name} pairs
    """
    return {
        'en': 'English',
        'pt': 'Português',
        'es': 'Español', 
        'de': 'Deutsch',
        'fr': 'Français',
        'it': 'Italiano',
        'ar': 'العربية',
        'ru': 'Русский',
        'zh': '中文',
        'ja': '日本語',
        'hi': 'हिंदी',
        'tr': 'Türkçe',
        'id': 'Bahasa Indonesia',
        'ko': '한국어',
        'vi': 'Tiếng Việt',
        'tl': 'Tagalog',
        'bn': 'বাংলা',
        'ur': 'اردو'
    }


def get_localized_language_names(current_translations):
    """
    Get language names in the currently selected language if available
    Falls back to native language names
    """
    localized_names = {
        'en': current_translations.get('lang_english', 'English'),
        'pt': current_translations.get('lang_portuguese', 'Português'),
        'es': current_translations.get('lang_spanish', 'Español'),
        'de': current_translations.get('lang_german', 'Deutsch'),
        'fr': current_translations.get('lang_french', 'Français'),
        'it': current_translations.get('lang_italian', 'Italiano'),
        'ar': current_translations.get('lang_arabic', 'العربية'),
        'ru': current_translations.get('lang_russian', 'Русский'),
        'zh': current_translations.get('lang_chinese', '中文'),
        'ja': current_translations.get('lang_japanese', '日本語'),
        'hi': current_translations.get('lang_hindi', 'हिंदी'),
        'tr': current_translations.get('lang_turkish', 'Türkçe'),
        'id': current_translations.get('lang_indonesian', 'Bahasa Indonesia'),
        'ko': current_translations.get('lang_korean', '한국어'),
        'vi': current_translations.get('lang_vietnamese', 'Tiếng Việt'),
        'tl': current_translations.get('lang_tagalog', 'Tagalog'),
        'bn': current_translations.get('lang_bengali', 'বাংলা'),
        'ur': current_translations.get('lang_urdu', 'اردو')
    }
    
    # Fall back to native names for any missing translations
    native_names = get_language_names()
    for code in native_names:
        if localized_names.get(code) == current_translations.get(f'lang_{code}', ''):
            localized_names[code] = native_names[code]
    
    return localized_names


def create_translator(lang_code=None):
    """
    Create a translator function similar to the _() function
    Usage: _ = create_translator(); translated = _('key')
    """
    translations = load_translations(lang_code)
    
    def translate(key):
        return translations.get(key, key)
    
    return translate


def escape_for_markup(text):
    """
    Escape text for use in Pango markup contexts.
    Converts & to &amp; for proper XML parsing.
    """
    if text is None:
        return ""
    return text.replace('&', '&amp;')


def create_markup_translator(lang_code=None):
    """
    Create a translator function that escapes text for markup contexts.
    Usage: _ = create_markup_translator(); markup_safe = _('key')
    """
    translations = load_translations(lang_code)
    
    def translate(key):
        text = translations.get(key, key)
        return escape_for_markup(text)
    
    return translate


# Default translator instance for convenience
_ = create_translator()
