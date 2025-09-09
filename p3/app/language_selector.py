"""
Language selector dialog for LinuxToys
"""

from .gtk_common import Gtk
from . import lang_utils


class LanguageSelector:
    def __init__(self, parent_window, current_translations, on_language_changed=None):
        self.parent_window = parent_window
        self.current_translations = current_translations
        self.on_language_changed = on_language_changed
        
    def show_language_selector(self):
        """
        Show language selection dialog
        Returns the selected language code or None if cancelled
        """
        dialog = Gtk.Dialog(
            title=self.current_translations.get('select_language_title', 'Select Language'),
            parent=self.parent_window,
            modal=True
        )
        
        # Add buttons
        dialog.add_button(self.current_translations.get('cancel_btn_label', 'Cancel'), Gtk.ResponseType.CANCEL)
        dialog.add_button(self.current_translations.get('select_button', 'Select'), Gtk.ResponseType.OK)
        
        # Create content area
        content_area = dialog.get_content_area()
        content_area.set_spacing(12)
        content_area.set_margin_start(20)
        content_area.set_margin_end(20)
        content_area.set_margin_top(20)
        content_area.set_margin_bottom(20)
        
        # Add label
        label = Gtk.Label(label=self.current_translations.get('select_language_message', 'Please select your preferred language:'))
        label.set_halign(Gtk.Align.START)
        content_area.pack_start(label, False, False, 0)
        
        # Create combo box for language selection
        combo = Gtk.ComboBoxText()
        combo.set_hexpand(True)
        
        # Get available languages and their localized names
        available_languages = lang_utils.get_available_languages()
        localized_names = lang_utils.get_localized_language_names(self.current_translations)
        current_language = lang_utils.detect_system_language()
        
        # Populate combo box
        active_index = 0
        for i, lang_code in enumerate(available_languages):
            display_name = localized_names.get(lang_code, lang_code)
            combo.append(lang_code, display_name)
            if lang_code == current_language:
                active_index = i
        
        # Set current selection
        combo.set_active(active_index)
        
        content_area.pack_start(combo, False, False, 0)
        
        # Show all widgets
        dialog.show_all()
        
        # Run dialog and get response
        response = dialog.run()
        selected_language = None
        
        if response == Gtk.ResponseType.OK:
            selected_language = combo.get_active_id()
        
        dialog.destroy()
        
        # If a new language was selected and it's different from current
        if selected_language and selected_language != current_language:
            # Save the language preference
            lang_utils.save_language(selected_language)
            
            # Call the callback if provided
            if self.on_language_changed:
                self.on_language_changed(selected_language)
        
        return selected_language


def create_language_menu_item(translations):
    """
    Create a menu item for language selection
    Returns a Gtk.MenuItem
    """
    menu_item = Gtk.MenuItem(label=translations.get('select_language', 'Select Language'))
    return menu_item
