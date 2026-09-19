"""GTK view listing features that LinuxToys can currently remove."""

import html
import os

from . import get_icon_path
from .gtk_common import Gtk, load_scaled_pixbuf


class InstalledFeaturesView(Gtk.ScrolledWindow):
    def __init__(self, parent):
        super().__init__()
        self.parent_window = parent
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.content.set_margin_start(32)
        self.content.set_margin_end(32)
        self.content.set_margin_top(18)
        self.content.set_margin_bottom(18)
        self.add(self.content)
        self.refresh()

    def refresh(self):
        for child in self.content.get_children():
            self.content.remove(child)
            child.destroy()

        cache = self.parent_window.script_cache
        if not cache.is_populated:
            spinner = Gtk.Spinner()
            spinner.start()
            spinner.set_halign(Gtk.Align.CENTER)
            spinner.set_margin_top(24)
            self.content.pack_start(spinner, False, False, 0)
            self.show_all()
            return

        # Re-read both the Registry and the observed AppStream package snapshot.
        cache.refresh_removable_cache()
        installed = [
            info for info in cache.get_all_scripts()
            if cache.is_script_removable(info)
        ]
        installed.sort(key=lambda info: str(info.get("name", "")).casefold())

        if not installed:
            label = Gtk.Label(
                label=self.parent_window.translations.get(
                    "installed_features_empty", "No removable features are currently installed."
                )
            )
            label.get_style_context().add_class("dim-label")
            label.set_margin_top(24)
            self.content.pack_start(label, False, False, 0)
        else:
            for info in installed:
                self.content.pack_start(self._create_row(info), False, False, 0)

        self.show_all()

    def _create_row(self, info):
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        outer.get_style_context().add_class("queue-item")
        outer.set_margin_top(2)
        outer.set_margin_bottom(2)

        image = self._image_for(info.get("icon") or "application-x-executable", 38)
        outer.pack_start(image, False, False, 12)

        name = Gtk.Label()
        name.set_markup(f"<b>{html.escape(str(info.get('name', '')))}</b>")
        name.set_halign(Gtk.Align.START)
        outer.pack_start(name, True, True, 0)

        button = Gtk.Button.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.get_style_context().add_class("destructive-action")
        button.get_style_context().add_class("queue-remove")
        button.set_tooltip_text(
            self.parent_window.translations.get(
                "term_view_remove", "Remove installed components"
            )
        )
        button.connect("clicked", self._remove, info)
        outer.pack_start(button, False, False, 4)
        return outer

    def _remove(self, button, info):
        self.parent_window._on_item_remove_clicked(button, dict(info))

    @staticmethod
    def _image_for(icon_value, size):
        icon_value = str(icon_value or "application-x-executable")
        if icon_value.endswith((".png", ".svg")):
            path = icon_value if os.path.isabs(icon_value) else get_icon_path(icon_value)
            if path and os.path.exists(path):
                pixbuf = load_scaled_pixbuf(path, size, size, True)
                if pixbuf is not None:
                    return Gtk.Image.new_from_pixbuf(pixbuf)
        image = Gtk.Image.new_from_icon_name(icon_value, Gtk.IconSize.DIALOG)
        image.set_pixel_size(size)
        return image
