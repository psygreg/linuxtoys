"""
Official application selector for LinuxToys bug reports.
"""

from .gtk_common import Gtk
from . import official_index


class OfficialAppSelector:
    def __init__(
        self,
        parent_window,
        translations,
        current_app=None,
    ):
        self.parent_window = parent_window
        self.translations = translations
        self.current_app = current_app
        self.app_rows = {}

    def show(self):
        dialog = Gtk.Dialog(
            title=self.translations.get(
                "select_official_app_title",
                "Select Application",
            ),
            parent=self.parent_window,
            modal=True,
        )

        dialog.set_default_size(500, 450)
        dialog.set_resizable(True)

        dialog.add_button(
            self.translations.get("cancel_btn_label", "Cancel"),
            Gtk.ResponseType.CANCEL,
        )
        dialog.add_button(
            self.translations.get("select_button", "Select"),
            Gtk.ResponseType.OK,
        )

        content_area = dialog.get_content_area()
        content_area.set_spacing(12)
        content_area.set_margin_start(20)
        content_area.set_margin_end(20)
        content_area.set_margin_top(20)
        content_area.set_margin_bottom(20)

        label = Gtk.Label(
            label=self.translations.get(
                "select_official_app_message",
                "Select the application this report is about:",
            )
        )
        label.set_halign(Gtk.Align.START)
        content_area.pack_start(label, False, False, 0)

        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text(
            self.translations.get(
                "search",
                "Search applications",
            )
        )
        search_entry.set_hexpand(True)
        content_area.pack_start(search_entry, False, False, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )
        scrolled_window.set_size_request(400, 300)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        listbox.set_activate_on_single_click(False)
        scrolled_window.add(listbox)

        selected_row = None

        def add_row(app_name, display_name):
            nonlocal selected_row

            row = Gtk.ListBoxRow()

            hbox = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=12,
            )
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)

            name_label = Gtk.Label(label=display_name)
            name_label.set_halign(Gtk.Align.START)
            name_label.set_hexpand(True)
            hbox.pack_start(name_label, True, True, 0)

            if app_name and app_name != display_name:
                id_label = Gtk.Label(label=f"({app_name})")
                id_label.set_halign(Gtk.Align.END)
                id_label.get_style_context().add_class("dim-label")
                hbox.pack_start(id_label, False, False, 0)

            row.add(hbox)
            listbox.add(row)

            self.app_rows[row] = app_name

            if app_name == self.current_app:
                selected_row = row

        # Explicit "not about an application" option.
        add_row(
            None,
            self.translations.get(
                "bug_report_general",
                "LinuxToys",
            ),
        )

        for app_name, display_name in official_index.get_verified_entries(
            self.translations
        ):
            add_row(app_name, display_name)

        def filter_func(row):
            search_text = search_entry.get_text().strip().casefold()
            if not search_text:
                return True

            app_name = self.app_rows.get(row)

            hbox = row.get_child()
            if not hbox:
                return False

            children = hbox.get_children()
            if not children:
                return False

            display_name = children[0].get_text().casefold()

            return (
                search_text in display_name
                or (
                    app_name is not None
                    and search_text in app_name.casefold()
                )
            )

        listbox.set_filter_func(filter_func)

        def on_search_changed(entry):
            listbox.invalidate_filter()

            for row in listbox.get_children():
                if row.get_visible():
                    listbox.select_row(row)
                    break

        search_entry.connect("search-changed", on_search_changed)

        def on_search_key_press(entry, event):
            if event.keyval == 65293:
                dialog.response(Gtk.ResponseType.OK)
                return True
            return False

        search_entry.connect(
            "key-press-event",
            on_search_key_press,
        )

        def on_row_activated(listbox, row):
            dialog.response(Gtk.ResponseType.OK)

        listbox.connect("row-activated", on_row_activated)

        if selected_row:
            listbox.select_row(selected_row)

        content_area.pack_start(
            scrolled_window,
            True,
            True,
            0,
        )

        dialog.show_all()

        response = dialog.run()
        selected_app = self.current_app

        if response == Gtk.ResponseType.OK:
            row = listbox.get_selected_row()
            if row:
                selected_app = self.app_rows.get(row)

        dialog.destroy()
        return selected_app