"""GTK view for the session-scoped AppStream installation queue."""

import os

from . import get_icon_path, gui_rs
from .gtk_common import Gtk


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
        records = list(self.parent_window._appstream_runner.snapshot())
        specs = [self._row_spec(record) for record in records]
        rows = gui_rs.reconcile_list_rows(self.content, specs)

        for record in records:
            row = rows[str(record["id"])]
            self._bind_action(row, record)

        self.show_all()

    def _bind_action(self, row, record):
        action = gui_rs.card_child(row, "linuxtoys-list-row-action")
        if action is None:
            return
        state = record["status"]
        if state == "queued":
            action.connect("clicked", self._cancel, record["id"])
        elif state == "success":
            action.connect("clicked", self._remove, record["id"], record["info"])

    def _row_spec(self, record):
        state = record["status"]
        icon_value = str(record.get("icon") or "application-x-executable")
        icon_path = ""
        icon_name = icon_value
        if os.path.isabs(icon_value) and os.path.isfile(icon_value):
            # AppStream may use any image format supported by GdkPixbuf,
            # including JXL on current Arch/CachyOS catalogs.
            icon_path = icon_value
            icon_name = "application-x-executable"
        elif "/" not in icon_value and icon_value.lower().endswith((".png", ".svg", ".webp")):
            path = get_icon_path(icon_value)
            if path and os.path.isfile(path):
                icon_path = path
                icon_name = "application-x-executable"

        action_kind = 1 if state == "queued" else 2 if state == "success" else 0
        tooltip = ""
        if state == "queued":
            tooltip = self.parent_window.translations.get("cancel_btn_label", "Cancel")
        elif state == "success":
            tooltip = self.parent_window.translations.get(
                "term_view_remove", "Remove installed components"
            )

        return {
            "key": str(record["id"]),
            "name": record.get("name", ""),
            "secondary": self._status_text(state),
            "secondary_visible": True,
            "icon_path": icon_path,
            "icon_name": icon_name,
            "status_icon": self._status_icon(state) if state != "running" else "",
            "spinner": state == "running",
            "action_kind": action_kind,
            "destructive_action": state == "success",
            "action_tooltip": tooltip,
        }

    def _cancel(self, _button, job_id):
        self.parent_window._appstream_runner.cancel(job_id)

    def _remove(self, _button, record_id, info):
        if info.get("is_flatpak_extension"):
            self.parent_window._appstream_runner.enqueue_extension_removal(
                dict(info), record_id=record_id
            )
            return
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
