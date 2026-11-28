"""Embedded app-page view for optional Flatpak and Nix extensions.

Flatpak addon components and Nix plugin sets share the same row UI. The two
sources differ in where the selection lives and how an action is executed:

* Flatpak extensions are queued in the AppStream runner and their installed
  state comes from ``flatpak list``.
* Nix extensions are queued in the persistent Nix queue; applying that queue
  rewrites the generated extension module and rebuilds the profile.
"""

import logging
import os

from . import appstream_cache, get_icon_path, gui_rs, nix_extensions, nix_queue
from .gtk_common import Gtk, resolve_symbolic_icon

logger = logging.getLogger(__name__)


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
        self._populated = False

    def ensure_populated(self):
        """Populate extension state/rows only when the tab is first shown."""
        if self._populated:
            return
        self._populated = True
        self.refresh()

    def refresh(self):
        installed = self._installed_keys()
        jobs = self._jobs()

        keyed = []
        specs = []
        for info in self.extensions:
            key = self._key(info)
            if not key:
                continue
            state = "installed" if key in installed else "available"
            record = jobs.get(key)
            if self._nix_entry(info):
                if record is not None:
                    state = "queued"
            elif record and record.get("status") in ("queued", "running"):
                state = (
                    "removing"
                    if record.get("action") == "extension_remove"
                    else record["status"]
                )
            keyed.append((key, info, state, record))
            spec = self._row_spec(key, info, state, record)
            spec["embedded"] = True
            specs.append(spec)

        rows = gui_rs.reconcile_list_rows(self.content, specs)
        for key, info, state, record in keyed:
            self._bind(rows[key], info, state, record)
        self.show_all()

    @staticmethod
    def _nix_entry(info):
        return str(info.get("extension_kind") or "") == "nix"

    @classmethod
    def _key(cls, info):
        if cls._nix_entry(info):
            return str(info.get("nix_ext_attr") or info.get("id") or "").strip()
        return str(info.get("flatpak_ref") or "").strip()

    def _installed_keys(self):
        if str(self.source_info.get("appstream_source") or "") == "nix":
            try:
                return nix_extensions.installed_extensions(self.source_info)
            except Exception as error:
                logger.warning("Could not read Nix extension state: %s", error)
                return set()
        return appstream_cache.installed_flatpak_extension_refs(self.source_info)

    def _jobs(self):
        jobs = {}
        if str(self.source_info.get("appstream_source") or "") == "nix":
            host = str(self.source_info.get("nix_name") or "").strip()
            scope = str(self.source_info.get("nix_scope") or "").strip()
            try:
                records = nix_queue.snapshot()
            except Exception:
                records = []
            for record in records:
                if record.get("kind") != "extension":
                    continue
                if str(record.get("host") or "") != host:
                    continue
                if scope and str(record.get("scope") or "") != scope:
                    continue
                jobs.setdefault(str(record.get("extension") or ""), record)
            return jobs

        records = self.parent_window._appstream_runner.snapshot()
        for record in records:
            ref = str(record.get("info", {}).get("flatpak_ref") or "").strip()
            if ref:
                jobs.setdefault(ref, record)
        return jobs

    def _row_spec(self, key, info, state, record=None):
        icon_value = str(info.get("icon") or "application-x-addon-symbolic")
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

        tr = self.parent_window.translations
        if state == "available":
            secondary = str(info.get("summary") or "")
            status_icon, spinner, action_kind, destructive = "", False, 3, False
            tooltip = tr.get("skills_install_label", "Install")
        elif state == "installed":
            secondary = tr.get("app_page_installed", "Installed")
            status_icon, spinner, action_kind, destructive = resolve_symbolic_icon("emblem-ok-symbolic"), False, 2, True
            tooltip = tr.get("term_view_remove", "Remove installed components")
        elif state == "queued":
            removing = bool(record and record.get("action") == "remove")
            secondary = (
                tr.get("nix_extension_remove_queued", "Waiting to remove")
                if removing
                else tr.get("queued", "Waiting to install")
            )
            status_icon, spinner, action_kind, destructive = resolve_symbolic_icon("appointment-soon-symbolic"), False, 1, False
            tooltip = tr.get("cancel_btn_label", "Cancel")
        elif state == "removing":
            secondary = tr.get("skills_removing", "Removing…")
            status_icon, spinner, action_kind, destructive = "", True, 0, False
            tooltip = ""
        else:  # running
            secondary = tr.get("skills_installing", "Installing…")
            status_icon, spinner, action_kind, destructive = "", True, 0, False
            tooltip = ""
        return {"key": key, "name": str(info.get("name") or info.get("id") or key),
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

    def _after_queue_change(self):
        self.refresh()
        callback = getattr(self.parent_window, "_on_appstream_queue_changed", None)
        if callback is not None:
            callback()

    def _queue_nix(self, info, action):
        payload = dict(info)
        payload["nix_scope"] = (
            payload.get("nix_ext_scope")
            or self.source_info.get("nix_scope")
            or ""
        )
        try:
            nix_queue.add_extension(payload, action=action)
        except (OSError, ValueError) as error:
            from .gtk_dialogs import run_message_dialog

            logger.warning("Could not queue Nix extension operation: %s", error)
            run_message_dialog(
                self.parent_window,
                title="Nix",
                secondary_text=str(error),
                message_type=Gtk.MessageType.ERROR,
                buttons=[("OK", Gtk.ResponseType.OK)],
                default_response=Gtk.ResponseType.OK,
            )
            return False
        self._after_queue_change()
        return True

    def _install(self, _button, info):
        if self._nix_entry(info):
            self._queue_nix(info, "install")
            return
        payload = dict(info)
        payload["is_flatpak_extension"] = True
        self.parent_window._appstream_runner.enqueue_extension(payload)

    def _remove(self, _button, info, record):
        if self._nix_entry(info):
            self._queue_nix(info, "remove")
            return
        record_id = record.get("id") if record and record.get("status") == "success" else None
        self.parent_window._appstream_runner.enqueue_extension_removal(dict(info), record_id=record_id)

    def _cancel(self, _button, job_id):
        if any(
            record.get("id") == job_id and record.get("kind") == "extension"
            for record in nix_queue.snapshot()
        ):
            nix_queue.remove(job_id)
            self._after_queue_change()
            return
        self.parent_window._appstream_runner.cancel(job_id)
