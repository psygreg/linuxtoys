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
        self._rows = {}
        self._row_states = {}
        self.refresh()

    def refresh(self):
        records = list(self.parent_window._appstream_runner.snapshot())
        wanted = {str(record["id"]): record for record in records}

        # Remove jobs that disappeared from the runner snapshot.
        for key in list(self._rows):
            if key in wanted:
                continue
            row = self._rows.pop(key)
            self._row_states.pop(key, None)
            self.content.remove(row)
            row.destroy()

        # Reconcile existing rows and collect genuinely new jobs for one native batch.
        new_records = []
        for record in records:
            key = str(record["id"])
            spec = self._row_spec(record)
            row = self._rows.get(key)
            if row is None:
                new_records.append((record, spec))
                continue

            state_signature = (
                record.get("status"),
                spec["secondary"],
                spec["status_icon"],
                spec["spinner"],
                spec["action_kind"],
                spec["destructive_action"],
                spec["action_tooltip"],
            )
            if self._row_states.get(key) != state_signature:
                if not gui_rs.reconcile_list_row(row, spec):
                    raise RuntimeError(f"Failed to reconcile native queue row {key}")
                self._bind_action(row, record)
                self._row_states[key] = state_signature

        if new_records:
            rows = gui_rs.add_list_rows(
                self.content, [spec for _record, spec in new_records]
            )
            if len(rows) != len(new_records):
                raise RuntimeError("Native queue row batch returned an incomplete result")
            for row, (record, spec) in zip(rows, new_records):
                key = str(record["id"])
                self._rows[key] = row
                self._row_states[key] = (
                    record.get("status"),
                    spec["secondary"],
                    spec["status_icon"],
                    spec["spinner"],
                    spec["action_kind"],
                    spec["destructive_action"],
                    spec["action_tooltip"],
                )
                self._bind_action(row, record)

        # Runner snapshots are ordered. Preserve that order without rebuilding rows.
        for position, record in enumerate(records):
            row = self._rows.get(str(record["id"]))
            if row is not None:
                self.content.reorder_child(row, position)

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
        if icon_value.endswith((".png", ".svg")):
            path = icon_value if os.path.isabs(icon_value) else get_icon_path(icon_value)
            if path and os.path.exists(path):
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
