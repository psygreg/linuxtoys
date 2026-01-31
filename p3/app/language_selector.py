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
        
        # Set a larger minimum size for the dialog
        dialog.set_default_size(500, 450)
        dialog.set_resizable(True)
        
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
        
        # Add search entry
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text(self.current_translations.get('search_languages_placeholder', 'Search languages'))
        search_entry.set_hexpand(True)
        content_area.pack_start(search_entry, False, False, 0)
        
        # Create scrolled window for the language list
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_size_request(400, 300)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        
        # Create list box for language selection
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        listbox.set_activate_on_single_click(False)
        scrolled_window.add(listbox)
        
        # Get available languages and their localized names
        available_languages = lang_utils.get_available_languages()
        localized_names = lang_utils.get_localized_language_names(self.current_translations)
        current_language = lang_utils.detect_system_language()
        
        # Store language data for later retrieval
        self.language_rows = {}
        selected_row = None
        
        # Set up search filtering function
        def filter_func(row):
            search_text = search_entry.get_text().lower()
            if not search_text:
                return True
            
            # Get the language code for this row
            lang_code = self.language_rows.get(row, '').lower()
            
            # Get the language name from the row
            hbox = row.get_child()
            if hbox and hbox.get_children():
                name_label = hbox.get_children()[0]
                if hasattr(name_label, 'get_text'):
                    language_name = name_label.get_text().lower()
                    # Match either language name or language code
                    return (search_text in language_name or 
                            search_text in lang_code)
            return False
        
        # Connect search entry to update filter
        def on_search_changed(entry):
            listbox.invalidate_filter()
            # Auto-select first visible item when searching
            first_visible = None
            for row in listbox.get_children():
                if row.get_visible():
                    first_visible = row
                    break
            if first_visible:
                listbox.select_row(first_visible)
        
        search_entry.connect('search-changed', on_search_changed)
        
        # Allow Enter key in search to confirm selection
        def on_search_key_press(entry, event):
            # Check if Enter key was pressed
            if event.keyval == 65293:  # Enter key
                dialog.response(Gtk.ResponseType.OK)
                return True
            return False
        
        search_entry.connect('key-press-event', on_search_key_press)
        
        # Populate list box with languages
        for lang_code in available_languages:
            display_name = localized_names.get(lang_code, lang_code)
            
            # Create row with language name
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)
            
            # Language name label
            name_label = Gtk.Label(label=display_name)
            name_label.set_halign(Gtk.Align.START)
            name_label.set_hexpand(True)
            hbox.pack_start(name_label, True, True, 0)
            
            # Language code label (smaller, aligned right)
            if lang_code != display_name:
                code_label = Gtk.Label(label=f"({lang_code})")
                code_label.set_halign(Gtk.Align.END)
                code_label.get_style_context().add_class("dim-label")
                hbox.pack_start(code_label, False, False, 0)
            
            row.add(hbox)
            listbox.add(row)
            
            # Store mapping for retrieval
            self.language_rows[row] = lang_code
            
            # Mark current language as selected
            if lang_code == current_language:
                selected_row = row
        
        # Set the filter function after all rows are populated
        listbox.set_filter_func(filter_func)
        
        # Set current selection
        if selected_row:
            listbox.select_row(selected_row)
        
        # Enable double-click to select
        def on_row_activated(listbox, row):
            dialog.response(Gtk.ResponseType.OK)
        
        listbox.connect('row-activated', on_row_activated)
        
        content_area.pack_start(scrolled_window, True, True, 0)
        
        # Show all widgets
        dialog.show_all()
        
        # Run dialog and get response
        response = dialog.run()
        selected_language = None
        
        if response == Gtk.ResponseType.OK:
            selected_row = listbox.get_selected_row()
            if selected_row:
                selected_language = self.language_rows.get(selected_row)
        
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
