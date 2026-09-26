import os

from .gtk_common import Gtk, escape_markup, load_scaled_pixbuf
from . import get_icon_path, gui_rs

class InfosHead(Gtk.Box):
    def __init__(self, translations=None, show_terminal_controls=True):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.translations = translations or {}

        execute_label = self.translations.get("term_view_execute", " Execute ")
        remove_label = self.translations.get("term_view_remove", " Remove ")
        report_label = self.translations.get("report_label", " Report Bug ")

        native_widgets = gui_rs.populate_infos_head(
            self,
            execute_label=execute_label,
            remove_label=remove_label,
            report_label=report_label,
            show_terminal_controls=show_terminal_controls,
        )
        if native_widgets is None:
            raise RuntimeError("Native InfosHead construction failed")

        for name, widget in native_widgets.items():
            setattr(self, name, widget)

    def _update_header_labels(self, script_info: dict):
        name = escape_markup(script_info.get("name", ""))
        description = str(script_info.get("description", "") or "")
        repo = str(script_info.get("repo", "") or "")

        self.label_name.set_markup(f"<big><big><b>{name}</b></big></big>")
        self.label_desc.set_text(description)

        if repo:
            repo_markup = escape_markup(repo)
            repo_display = escape_markup(
                repo.replace("https://", "").replace("http://", "").rstrip("/")
            )
            self.label_repo.set_markup(f"<a href='{repo_markup}'>{repo_display}</a>")
            self.label_repo.show()
        else:
            self.label_repo.set_text("")
            self.label_repo.hide()

        icon_value = str(script_info.get("icon") or "local-script.svg")
        icon_size = 100

        # AppStream entries may carry an absolute path to an icon from the
        # distribution AppStream cache.  Do not feed those paths through
        # LinuxToys' bundled-icon resolver: on distributions such as Arch that
        # can discard an otherwise valid AppStream icon.  This mirrors the icon
        # handling used by the application cards.
        if icon_value.endswith((".png", ".svg")):
            if os.path.isabs(icon_value) or "/" in icon_value:
                icon_path = icon_value if os.path.exists(icon_value) else None
            else:
                icon_path = get_icon_path(icon_value)

            pixbuf = (
                load_scaled_pixbuf(icon_path, icon_size, icon_size, True)
                if icon_path
                else None
            )
            if pixbuf is not None:
                self.icon_head.set_from_pixbuf(pixbuf)
            else:
                self.icon_head.set_from_icon_name(
                    "application-x-executable", Gtk.IconSize.DIALOG
                )
                self.icon_head.set_pixel_size(icon_size)
        else:
            # Named icons belong to the active GTK icon theme.
            self.icon_head.set_from_icon_name(icon_value, Gtk.IconSize.DIALOG)
            self.icon_head.set_pixel_size(icon_size)
