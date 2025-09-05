import json
import os
import threading

import requests

from . import get_app_resource_path, get_icon_path
from .gtk_common import GdkPixbuf, GLib, Gtk
from .update_helper import get_current_version


class AboutDialog:
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.contributors = []
        self.app_version = get_current_version()

    def show_about_dialog(self):
        """Creates and shows the About dialog"""
        # Create the dialog
        dialog = Gtk.Dialog(
            title=_("About LinuxToys"),
            parent=self.parent_window,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        dialog.set_default_size(512, 310)
        dialog.set_resizable(False)

        # Creates a top bar for tabs
        notebook = Gtk.Notebook()
        notebook.set_size_request(-1, 310)
        content_area = dialog.get_content_area()
        content_area.add(notebook)

        # ---------------------------
        # TAB: ABOUT
        # ---------------------------
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

        notebook.append_page(aba_sobre, Gtk.Label(label=_("About")))

        # ---------------------------
        # TAB: LICENSE
        # ---------------------------
        aba_licenca = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        aba_licenca.set_border_width(10)
        license_path = get_app_resource_path("../LICENSE")

        # Add the version number to the license header
        license_header_text = f"LinuxToys {self.app_version}"
        licenca_header = Gtk.Label(label=license_header_text)
        licenca_header.set_justify(Gtk.Justification.CENTER)
        aba_licenca.pack_start(licenca_header, False, False, 0)

        # Load license text from file
        licenca_label = Gtk.Label(label=_("License file not found."))
        try:
            with open(license_path, "r", encoding="utf-8") as f:
                license_text = f.read()
                licenca_label = Gtk.Label(label=license_text)
        except Exception as e:
            print(f"Error loading license. {e}")
        licenca_label.set_justify(Gtk.Justification.LEFT)
        licenca_label.set_line_wrap(True)
        licenca_label.set_selectable(True)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(licenca_label)
        aba_licenca.pack_start(scroll, True, True, 0)
        notebook.append_page(aba_licenca, Gtk.Label(label=_("License")))

        # ---------------------------
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
            app_icon = Gtk.Image.new_from_icon_name(
                "applications-utilities", Gtk.IconSize.DIALOG
            )
            app_icon.set_pixel_size(64)

        # Text box
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        text_box.set_margin_top(10)  # top margin

        # App name
        name_label = Gtk.Label()
        name_label.set_markup(f"<big><big><b>LinuxToys</b></big></big>")
        name_label.set_halign(Gtk.Align.START)

        # App version
        version_label = Gtk.Label()
        version_label.set_markup(
            f"<small>{_('version_label')} {self.app_version}</small>"
        )
        version_label.set_halign(Gtk.Align.START)

        # App description
        description = _("subtitle")
        desc_label = Gtk.Label(label=description)
        desc_label.set_line_wrap(True)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_max_width_chars(52)

        text_box.pack_start(name_label, False, False, 0)
        text_box.pack_start(
            version_label, False, False, 0
        )  # Adds the version below the name
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
            author_photo = Gtk.Image.new_from_icon_name(
                "avatar-default", Gtk.IconSize.DIALOG
            )
            author_photo.set_pixel_size(36)

        # Author info
        author_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        # Author name
        author_name = Gtk.Label()
        author_name.set_markup("<b>Victor 'psygreg' Gregory</b>")
        author_name.set_halign(Gtk.Align.START)

        # Author role
        role_text = _("Project Lead")
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
        contributors_title.set_markup(f"<b>{_('Contributors')}</b>")
        contributors_title.set_halign(Gtk.Align.CENTER)

        # Contributors grid (will be populated when data loads)
        self.contributors_grid = Gtk.Grid()
        self.contributors_grid.set_column_spacing(48)
        self.contributors_grid.set_row_spacing(8)
        self.contributors_grid.set_halign(Gtk.Align.CENTER)

        # Loading label
        self.loading_label = Gtk.Label(label=_("Loading contributors..."))
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
                timeout=10,
            )
            if response.status_code == 200:
                contributors_data = response.json()
                # Filter out 'psygreg' since he's already mentioned as project lead
                filtered_contributors = [
                    c for c in contributors_data if c["login"].lower() != "psygreg"
                ]
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
            contributor_label = Gtk.Label(label=contributor["login"])
            contributor_label.set_halign(Gtk.Align.START)

            self.contributors_grid.attach(contributor_label, col, row, 1, 1)

        self.contributors_grid.show_all()

    def _show_contributors_error(self):
        """Shows error message when contributors can't be loaded"""
        self.loading_label.set_text(_("Unable to load contributors"))


def show_about_dialog(parent_window):
    """Convenience function to show the about dialog"""
    about_dialog = AboutDialog(parent_window)
    about_dialog.show_about_dialog()
