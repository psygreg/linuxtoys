"""Embedded app-page view for optional Flatpak extensions."""

import os

from . import appstream_cache, get_icon_path, gui_rs
from .gtk_common import Gtk


class AppStreamExtensionsView(Gtk.ScrolledWindow):
    """Extension page that consumes the Stack's width without establishing it."""

    def do_get_preferred_width(self):
        return (0, 0)

    def do_get_preferred_width_for_height(self, height):
        return (0, 0)

    def __init__(self, parent, source_info, extensions):
        super().__init__()
        self.parent_window = parent
        self.source_info = dict(source_info)
        self.extensions = [dict(item) for item in extensions]
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.content.set_margin_start(32)
        self.content.set_margin_end(32)
        self.content.set_margin_top(18)
        self.content.set_margin_bottom(18)
        self.add(self.content)
        self.refresh()

    def set_source(self, source_info, extensions):
        self.source_info = dict(source_info)
        self.extensions = [dict(item) for item in extensions]
        self.refresh()

    def refresh(self):
        installed = appstream_cache.installed_flatpak_extension_refs(self.source_info)
        records = self.parent_window._appstream_runner.snapshot()
        jobs = {}
        for record in records:
            ref = str(record.get("info", {}).get("flatpak_ref") or "").strip()
            if ref:
                jobs.setdefault(ref, record)

        keyed = []
        specs = []
        for info in self.extensions:
            ref = str(info.get("flatpak_ref") or "").strip()
            if not ref:
                continue
            state = "installed" if ref in installed else "available"
            record = jobs.get(ref)
            if record and record.get("status") in ("queued", "running"):
                state = (
                    "removing"
                    if record.get("action") == "extension_remove"
                    else record["status"]
                )
            keyed.append((ref, info, state, record))
            spec = self._row_spec(ref, info, state)
            spec["embedded"] = True
            specs.append(spec)

        rows = gui_rs.reconcile_list_rows(self.content, specs)
        for ref, info, state, record in keyed:
            self._bind(rows[ref], info, state, record)
        self.show_all()

    def _row_spec(self, ref, info, state):
        icon_value = str(info.get("icon") or "application-x-addon-symbolic")
        icon_path = ""
        icon_name = icon_value
        if icon_value.endswith((".png", ".svg")):
            path = icon_value if os.path.isabs(icon_value) else get_icon_path(icon_value)
            if path and os.path.exists(path):
                icon_path = path
                icon_name = "application-x-addon-symbolic"

        tr = self.parent_window.translations
        if state == "available":
            secondary = str(info.get("summary") or "")
            status_icon, spinner, action_kind, destructive = "", False, 3, False
            tooltip = tr.get("skills_install_label", "Install")
        elif state == "installed":
            secondary = tr.get("app_page_installed", "Installed")
            status_icon, spinner, action_kind, destructive = "emblem-ok-symbolic", False, 2, True
            tooltip = tr.get("term_view_remove", "Remove installed components")
        elif state == "queued":
            secondary = tr.get("queued", "Waiting to install")
            status_icon, spinner, action_kind, destructive = "appointment-soon-symbolic", False, 1, False
            tooltip = tr.get("cancel_btn_label", "Cancel")
        elif state == "removing":
            secondary = tr.get("skills_removing", "Removing…")
            status_icon, spinner, action_kind, destructive = "", True, 0, False
            tooltip = ""
        else:  # running
            secondary = tr.get("skills_installing", "Installing…")
            status_icon, spinner, action_kind, destructive = "", True, 0, False
            tooltip = ""
        return {"key": ref, "name": str(info.get("name") or info.get("id") or ref),
                "secondary": secondary, "secondary_visible": bool(secondary),
                "icon_path": icon_path, "icon_name": icon_name, "status_icon": status_icon,
                "spinner": spinner, "launch": False, "action_kind": action_kind,
                "destructive_action": destructive, "action_tooltip": tooltip}

    def _bind(self, row, info, state, record):
        action = gui_rs.card_child(row, "linuxtoys-list-row-action")
        if action is None:
            return
        if state == "available":
            action.connect("clicked", self._install, info)
        elif state == "installed":
            action.connect("clicked", self._remove, info, record)
        elif state == "queued" and record is not None:
            action.connect("clicked", self._cancel, record["id"])

    def _install(self, _button, info):
        payload = dict(info)
        payload["is_flatpak_extension"] = True
        self.parent_window._appstream_runner.enqueue_extension(payload)

    def _remove(self, _button, info, record):
        record_id = record.get("id") if record and record.get("status") == "success" else None
        self.parent_window._appstream_runner.enqueue_extension_removal(dict(info), record_id=record_id)

    def _cancel(self, _button, job_id):
        self.parent_window._appstream_runner.cancel(job_id)
