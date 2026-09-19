"""GTK view for the session-scoped AppStream installation queue."""

import html
from .gtk_common import Gtk
from . import get_icon_path
from .gtk_common import load_scaled_pixbuf


class AppStreamQueueView(Gtk.ScrolledWindow):
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

        for record in self.parent_window._appstream_runner.snapshot():
            self.content.pack_start(self._create_row(record), False, False, 0)
        self.show_all()

    def _create_row(self, record):
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        outer.get_style_context().add_class("queue-item")
        outer.set_margin_top(2)
        outer.set_margin_bottom(2)

        icon_value = record.get("icon") or "application-x-executable"
        image = self._image_for(icon_value, 38)
        outer.pack_start(image, False, False, 12)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name = Gtk.Label()
        name.set_markup(f"<b>{html.escape(record.get('name', ''))}</b>")
        name.set_halign(Gtk.Align.START)
        status = Gtk.Label(label=self._status_text(record["status"]))
        status.set_halign(Gtk.Align.START)
        status.get_style_context().add_class("dim-label")
        text.pack_start(name, False, False, 0)
        text.pack_start(status, False, False, 0)
        outer.pack_start(text, True, True, 0)

        state = record["status"]
        if state == "running":
            indicator = Gtk.Spinner()
            indicator.start()
        else:
            indicator = Gtk.Image.new_from_icon_name(self._status_icon(state), Gtk.IconSize.BUTTON)
        outer.pack_start(indicator, False, False, 4)

        if state == "queued":
            button = Gtk.Button.new_from_icon_name("process-stop-symbolic", Gtk.IconSize.BUTTON)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_tooltip_text(self.parent_window.translations.get("cancel_btn_label", "Cancel"))
            button.connect("clicked", self._cancel, record["id"])
            outer.pack_start(button, False, False, 4)
        elif state == "success":
            button = Gtk.Button.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.get_style_context().add_class("destructive-action")
            button.get_style_context().add_class("queue-remove")
            button.set_tooltip_text(self.parent_window.translations.get("term_view_remove", "Remove installed components"))
            button.connect("clicked", self._remove, record["id"], record["info"])
            outer.pack_start(button, False, False, 4)

        return outer

    def _cancel(self, _button, job_id):
        self.parent_window._appstream_runner.cancel(job_id)

    def _remove(self, _button, record_id, info):
        # Keep the queue identity separate from the AppStream/catalog identity.
        # The terminal removal flow will consume this only after a successful
        # uninstall, so failed/cancelled removals leave the queue entry intact.
        removal_info = dict(info)
        removal_info["_appstream_queue_record_id"] = record_id
        self.parent_window._on_item_remove_clicked(_button, removal_info)

    def _status_text(self, state):
        translations = self.parent_window.translations
        status_keys = {
            "queued": ("queued", "Waiting to install"),
            "running": ("app_page_queued", "Queued"),
            "success": ("app_page_installed", "Installed"),
            "failed": ("skills_error_install", "Installation failed"),
            "cancelled": ("cancelled", "Cancelled"),
        }
        key, fallback = status_keys.get(state, (None, state))
        return translations.get(key, fallback) if key else fallback

    @staticmethod
    def _status_icon(state):
        return {
            "queued": "appointment-soon-symbolic",
            "success": "emblem-ok-symbolic",
            "failed": "dialog-warning-symbolic",
            "cancelled": "process-stop-symbolic",
        }.get(state, "dialog-information-symbolic")

    @staticmethod
    def _image_for(icon_value, size):
        if icon_value.endswith((".png", ".svg")):
            import os
            path = icon_value if os.path.isabs(icon_value) else get_icon_path(icon_value)
            if path and os.path.exists(path):
                pixbuf = load_scaled_pixbuf(path, size, size, True)
                if pixbuf is not None:
                    return Gtk.Image.new_from_pixbuf(pixbuf)
        image = Gtk.Image.new_from_icon_name(icon_value, Gtk.IconSize.DIALOG)
        image.set_pixel_size(size)
        return image
