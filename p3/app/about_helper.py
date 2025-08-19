from .gtk_common import Gtk, GdkPixbuf, GLib
import os
import requests
import threading
import json
from . import get_icon_path

class AboutDialog:
    def __init__(self, parent_window, translations):
        self.parent_window = parent_window
        self.translations = translations
        self.contributors = []
        
    def show_about_dialog(self):
        """Creates and shows the About dialog"""
        # Create the dialog
        dialog = Gtk.Dialog(
            title=self.translations.get('about_title', 'About LinuxToys'),
            parent=self.parent_window,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        dialog.set_default_size(512, 310)
        dialog.set_resizable(False)
        
        # Add Close button
        # close_text = self.translations.get('script_runner_close', 'Close')
        # dialog.add_button(close_text, Gtk.ResponseType.CLOSE)
        
        ## Cria uma barra superior para abas
        notebook = Gtk.Notebook()
        notebook.set_size_request(-1, 310)
        content_area = dialog.get_content_area()
        content_area.add(notebook)

        # Get content area
        # content_area.set_spacing(20)
        # content_area.set_margin_left(20)
        # content_area.set_margin_right(20)
        # content_area.set_margin_top(8)
        # content_area.set_margin_bottom(20)

        ## ---------------------------
        ## ABA: SOBRE
        ## ---------------------------
        aba_sobre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        aba_sobre.set_border_width(16)
        
        # App header section
        app_header = self._create_app_header()
        aba_sobre.pack_start(app_header, False, False, 0)
        
        # Separator
        separator1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        aba_sobre.pack_start(separator1, False, False, 0)
        
        # Author section
        author_section = self._create_author_section()
        aba_sobre.pack_start(author_section, False, False, 0)
        
        # Separator
        separator2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        aba_sobre.pack_start(separator2, False, False, 0)
        
        # Contributors section
        contributors_section = self._create_contributors_section()
        aba_sobre.pack_start(contributors_section, False, False, 0)
        
        notebook.append_page(aba_sobre, Gtk.Label(label="Sobre"))


        ## ---------------------------
        ## ABA: LICENÇA
        ## ---------------------------
        aba_licenca = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        aba_licenca.set_border_width(10)

        licenca_text = """
                      GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.

Preamble

The GNU General Public License is a free, copyleft license for
software and other kinds of works.

The licenses for most software and other practical works are designed
to take away your freedom to share and change the works.  By contrast,
the GNU General Public License is intended to guarantee your freedom to
share and change all versions of a program--to make sure it remains free
software for all its users.  We, the Free Software Foundation, use the
GNU General Public License for most of our software; it applies also to
any other work released this way by its authors.  You can apply it to
your programs, too.
        """

        licenca_label = Gtk.Label(label=licenca_text)
        licenca_label.set_justify(Gtk.Justification.LEFT)
        licenca_label.set_line_wrap(True)
        licenca_label.set_selectable(True)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(licenca_label)

        aba_licenca.pack_start(scroll, True, True, 0)
        
        notebook.append_page(aba_licenca, Gtk.Label(label="Licença"))

        
        ## ---------------------------
        # Show all widgets
        dialog.show_all()
        
        # Load contributors in background
        threading.Thread(target=self._load_contributors, daemon=True).start()
        
        # Run dialog
        response = dialog.run()
        dialog.destroy()


    def _create_app_header(self):
        """Creates the app header with icon, name and description"""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_halign(Gtk.Align.CENTER)
        
        # App icon
        try:
            icon_path = get_icon_path("linuxtoys_64x64.png")
            if icon_path:
                app_icon = Gtk.Image.new_from_file(icon_path)
                app_icon.set_pixel_size(64)
            else:
                raise FileNotFoundError("app-icon.png not found")
        except Exception:
            app_icon = Gtk.Image.new_from_icon_name("applications-utilities", Gtk.IconSize.DIALOG)
            app_icon.set_pixel_size(64)
        
        # Text box
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        text_box.set_margin_top(10) ## margem acima do titulo
        
        # App name
        name_label = Gtk.Label()
        name_label.set_markup("<big><big><b>LinuxToys</b></big></big>")
        name_label.set_halign(Gtk.Align.START)
        
        # App description
        description = self.translations.get("subtitle", "A collection of tools for Linux in a user-friendly way.")
        desc_label = Gtk.Label(label=description)
        desc_label.set_line_wrap(True)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_max_width_chars(52)
        
        text_box.pack_start(name_label, False, False, 0)
        text_box.pack_start(desc_label, False, False, 0)
        
        header_box.pack_start(app_icon, False, False, 0)
        header_box.pack_start(text_box, True, True, 0)
        
        return header_box
        
    def _create_author_section(self):
        """Creates the author section with photo and info"""
        author_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        author_box.set_halign(Gtk.Align.CENTER)
        
        # Author photo
        try:
            # Load the author photo in its original resolution (36x36)
            icon_path = get_icon_path("psyicon.png")
            if icon_path:
                author_photo = Gtk.Image.new_from_file(icon_path)
            else:
                raise FileNotFoundError("psyicon.png not found")
        except Exception:
            author_photo = Gtk.Image.new_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)
            author_photo.set_pixel_size(36)
        
        # Author info
        author_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        # Author name
        author_name = Gtk.Label()
        author_name.set_markup("<b>Victor 'psygreg' Gregory</b>")
        author_name.set_halign(Gtk.Align.START)
        
        # Author role
        role_text = self.translations.get('project_lead', 'Project Lead')
        author_role = Gtk.Label()
        author_role.set_markup(f"<small>{role_text}</small>")
        author_role.set_halign(Gtk.Align.START)
        
        author_info_box.pack_start(author_name, False, False, 0)
        author_info_box.pack_start(author_role, False, False, 0)
        
        author_box.pack_start(author_photo, False, False, 0)
        author_box.pack_start(author_info_box, True, True, 0)
        
        return author_box
        
    def _create_contributors_section(self):
        """Creates the contributors section"""
        contributors_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Contributors title
        contributors_title = Gtk.Label()
        contributors_title.set_markup(f"<b>{self.translations.get('contributors', 'Contributors')}</b>")
        contributors_title.set_halign(Gtk.Align.CENTER)
        
        # Contributors grid (will be populated when data loads)
        self.contributors_grid = Gtk.Grid()
        self.contributors_grid.set_column_spacing(48)
        self.contributors_grid.set_row_spacing(8)
        self.contributors_grid.set_halign(Gtk.Align.CENTER)
        
        # Loading label
        self.loading_label = Gtk.Label(label="Loading contributors...")
        self.loading_label.set_halign(Gtk.Align.CENTER)
        
        contributors_box.pack_start(contributors_title, False, False, 0)
        contributors_box.pack_start(self.loading_label, False, False, 0)
        contributors_box.pack_start(self.contributors_grid, True, True, 0)
        
        return contributors_box
        
    def _load_contributors(self):
        """Loads contributors from GitHub API in background thread"""
        try:
            response = requests.get(
                "https://api.github.com/repos/psygreg/linuxtoys/contributors",
                timeout=10
            )
            if response.status_code == 200:
                contributors_data = response.json()
                # Filter out 'psygreg' since he's already mentioned as project lead
                filtered_contributors = [c for c in contributors_data if c['login'].lower() != 'psygreg']
                # Get top 10 contributors (after filtering)
                self.contributors = filtered_contributors[:9]
                # Update UI in main thread
                GLib.idle_add(self._update_contributors_ui)
            else:
                GLib.idle_add(self._show_contributors_error)
        except Exception as e:
            print(f"Error loading contributors: {e}")
            GLib.idle_add(self._show_contributors_error)
            
    def _update_contributors_ui(self):
        """Updates the contributors UI with loaded data"""
        # Hide loading label
        self.loading_label.hide()
        
        # Clear existing grid content
        for child in self.contributors_grid.get_children():
            self.contributors_grid.remove(child)
        
        # Add contributors in two columns
        for i, contributor in enumerate(self.contributors):
            row = i // 3
            col = i % 3
            
            # Create contributor label
            contributor_label = Gtk.Label(label=contributor['login'])
            contributor_label.set_halign(Gtk.Align.START)
            
            self.contributors_grid.attach(contributor_label, col, row, 1, 1)
        
        self.contributors_grid.show_all()
        
    def _show_contributors_error(self):
        """Shows error message when contributors can't be loaded"""
        self.loading_label.set_text("Unable to load contributors")

def show_about_dialog(parent_window, translations):
    """Convenience function to show the about dialog"""
    about_dialog = AboutDialog(parent_window, translations)
    about_dialog.show_about_dialog()
