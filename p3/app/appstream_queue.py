"""GTK view for the session-scoped AppStream installation queue."""

import os

from . import get_icon_path, gui_rs, nix_catalog, nix_queue
from .gtk_common import GLib, Gtk, resolve_symbolic_icon


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

        self._appstream_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=10
        )
        self.content.pack_start(self._appstream_box, False, False, 0)

        self._nix_section = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8
        )
        self._nix_section.set_margin_top(10)
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self._nix_section.pack_start(separator, False, False, 0)
        self._nix_title = Gtk.Label()
        self._nix_title.set_halign(Gtk.Align.START)
        self._nix_title.set_markup(
            f"<b>{GLib.markup_escape_text(self._translated('nix_queue_section', 'Nix packages'))}</b>"
        )
        self._nix_section.pack_start(self._nix_title, False, False, 0)
        self._nix_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._nix_section.pack_start(self._nix_box, False, False, 0)
        self._nix_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._apply_button = Gtk.Button()
        self._apply_button.set_halign(Gtk.Align.START)
        self._set_apply_button_content()
        self._apply_button.connect("clicked", self._apply_nix_operations)
        self._nix_actions.pack_start(self._apply_button, False, False, 0)
        self._nix_section.pack_start(self._nix_actions, False, False, 0)
        self.content.pack_start(self._nix_section, False, False, 0)
        self._nix_section.set_no_show_all(True)
        self.refresh()

    def _translated(self, key, fallback):
        return self.parent_window.translations.get(key, fallback)

    def _set_apply_button_content(self):
        child = self._apply_button.get_child()
        if child is not None:
            self._apply_button.remove(child)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.pack_start(
            Gtk.Image.new_from_icon_name(
                resolve_symbolic_icon("system-run-symbolic"), Gtk.IconSize.BUTTON
            ),
            False,
            False,
            0,
        )
        box.pack_start(
            Gtk.Label(
                label=self._translated(
                    "nix_apply_operations", "Apply Nix package operations"
                )
            ),
            False,
            False,
            0,
        )
        self._apply_button.add(box)
        self._apply_button.get_style_context().add_class("suggested-action")
        self._apply_button.show_all()

    def refresh(self):
        records = list(self.parent_window._appstream_runner.snapshot())
        specs = [self._row_spec(record) for record in records]
        rows = gui_rs.reconcile_list_rows(self._appstream_box, specs)

        for record in records:
            row = rows[str(record["id"])]
            self._bind_action(row, record)

        self._refresh_nix_section()
        self.show_all()
        if not nix_queue.pending():
            self._nix_section.hide()

    def _refresh_nix_section(self):
        operations = nix_queue.snapshot()
        if not operations:
            self._nix_section.set_no_show_all(True)
            self._nix_section.hide()
            gui_rs.reconcile_list_rows(self._nix_box, [])
            return

        self._nix_section.set_no_show_all(False)
        specs = [self._nix_row_spec(record) for record in operations]
        rows = gui_rs.reconcile_list_rows(self._nix_box, specs)
        for record in operations:
            row = rows.get(str(record["id"]))
            if row is not None:
                self._bind_nix_action(row, record)
        self._apply_button.set_sensitive(True)
        self._nix_section.show_all()

    def _nix_row_spec(self, record):
        scope = record.get("scope", "")
        scope_label = (
            self._translated("app_page_source_nix_system", "Nix (system)")
            if scope == "system"
            else self._translated(
                "app_page_source_nix_home_manager", "Nix (home-manager)"
            )
        )
        action = record.get("action", "install")
        action_label = (
            self._translated("nix_queue_remove", "Remove")
            if action == "remove"
            else self._translated("nix_queue_install", "Install")
        )
        secondary = f"{action_label} · {scope_label}"
        if record.get("kind") == "extension":
            host = str(record.get("host") or "").strip()
            if host:
                secondary = f"{action_label} · {scope_label} · {host}"
        elif record.get("kind") == "service":
            service = str(record.get("service") or record.get("attr") or "").strip()
            if service:
                secondary = f"{action_label} · {scope_label} · {service}"
        icon_path = ""
        icon_name = "nix.svg"
        path = get_icon_path("nix.svg")
        if path and os.path.isfile(path):
            icon_path = path
            icon_name = "application-x-executable"
        return {
            "key": str(record["id"]),
            "name": record.get("name", record.get("attr", "")),
            "secondary": secondary,
            "secondary_visible": True,
            "icon_path": icon_path,
            "icon_name": icon_name,
            "status_icon": resolve_symbolic_icon("appointment-soon-symbolic"),
            "spinner": False,
            "action_kind": 1,
            "destructive_action": False,
            "action_tooltip": self._translated("cancel_btn_label", "Cancel"),
        }

    def _bind_nix_action(self, row, record):
        action = gui_rs.card_child(row, "linuxtoys-list-row-action")
        if action is None:
            return
        action.connect("clicked", self._remove_nix_operation, record["id"])

    def _remove_nix_operation(self, _button, record_id):
        nix_queue.remove(record_id)
        self.refresh()

    def _apply_nix_operations(self, _button):
        info = nix_catalog.materialize_apply()
        self._apply_button.set_sensitive(False)
        self.parent_window.open_term_view([info], auto_run=True)

    def _bind_action(self, row, record):
        action = gui_rs.card_child(row, "linuxtoys-list-row-action")
        if action is None:
            return
        state = record["status"]
        if state == "queued":
            action.connect("clicked", self._cancel, record["id"])
        elif state == "success" and record.get("action") != "skill_install":
            # A skill install writes agent skill files; there is nothing the
            # queue's "remove installed components" flow could take back.
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
        else:
            icon_name = resolve_symbolic_icon(icon_value)

        action_kind = 1 if state == "queued" else 2 if state == "success" else 0
        if state == "success" and record.get("action") == "skill_install":
            action_kind = 0
        tooltip = ""
        if state == "queued":
            tooltip = self.parent_window.translations.get("cancel_btn_label", "Cancel")
        elif state == "success" and record.get("action") != "skill_install":
            tooltip = self.parent_window.translations.get(
                "term_view_remove", "Remove installed components"
            )

        return {
            "key": str(record["id"]),
            "name": record.get("name", ""),
            "secondary": self._status_text(state, record),
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

    def _status_text(self, state, record=None):
        translations = self.parent_window.translations
        if (record or {}).get("action") == "skill_install":
            status_keys = {
                "queued": ("queued", "Waiting to install"),
                "running": ("app_page_queued", "Queued"),
                "success": ("mcp_skill_installed", "Agent skill installed"),
                "failed": ("skills_error_install", "Installation failed"),
                "cancelled": ("cancelled", "Cancelled"),
            }
        else:
            status_keys = {
                "queued": ("queued", "Waiting to install"),
                "running": ("app_page_queued", "Queued"),
                "success": ("app_page_installed", "Installed"),
                "failed": ("skills_error_install", "Installation failed"),
                "cancelled": ("cancelled", "Cancelled"),
            }
        key, fallback = status_keys.get(state, (None, state))
        text = translations.get(key, fallback) if key else fallback
        # A failed background job has no terminal to read afterwards; show the
        # recorded reason on the row itself instead of only "Installation failed".
        reason = str((record or {}).get("failure_reason") or "").strip()
        if state == "failed" and reason:
            text = f"{text} — {reason}"
        return text

    @staticmethod
    def _status_icon(state):
        return resolve_symbolic_icon({
            "queued": "appointment-soon-symbolic",
            "success": "emblem-ok-symbolic",
            "failed": "dialog-warning-symbolic",
            "cancelled": "process-stop-symbolic",
        }.get(state, "dialog-information-symbolic"))
