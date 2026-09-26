"""GTK view listing features that LinuxToys can currently remove."""

import os

from . import get_icon_path, gui_rs, installed_packages, parser
from .gtk_common import Gtk
from .revert_helper import _get_executed_script_names


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
        self._rows = {}
        self._row_states = {}
        self.refresh()

    def refresh(self):
        cache = self.parent_window.script_cache
        if not cache.is_populated:
            # Installed data is not ready yet. Do not retain stale application rows
            # behind the loading indicator.
            for row in self._rows.values():
                self.content.remove(row)
                row.destroy()
            self._rows.clear()
            self._row_states.clear()
            for child in self.content.get_children():
                self.content.remove(child)
                child.destroy()
            spinner = Gtk.Spinner()
            spinner.start()
            spinner.set_halign(Gtk.Align.CENTER)
            spinner.set_margin_top(24)
            self.content.pack_start(spinner, False, False, 0)
            self.show_all()
            return

        # Remove a previous loading/empty-state widget without disturbing retained
        # native application rows.
        for child in list(self.content.get_children()):
            if child not in self._rows.values():
                self.content.remove(child)
                child.destroy()

        cache.refresh_removable_cache()
        installed = [
            info for info in cache.get_all_scripts()
            if cache.is_script_removable(info)
        ]

        snapshot = installed_packages.snapshot()
        flatpak_ids = snapshot.get("flatpak", {}).keys()
        appstream_installed = parser.get_installed_appstream_entries(
            snapshot.get("native", ()),
            flatpak_ids,
            executed_names=_get_executed_script_names(),
            translations=self.parent_window.translations,
        )
        seen = {
            info.get("path") or (info.get("name", ""), info.get("repo", ""))
            for info in installed
        }
        for info in appstream_installed:
            key = info.get("path") or (info.get("name", ""), info.get("repo", ""))
            if key in seen or not cache.is_script_removable(info):
                continue
            seen.add(key)
            installed.append(info)

        installed.sort(key=lambda info: str(info.get("name", "")).casefold())

        keyed = [(self._stable_key(info), info) for info in installed]
        wanted = {key for key, _info in keyed}

        for key in list(self._rows):
            if key in wanted:
                continue
            row = self._rows.pop(key)
            self._row_states.pop(key, None)
            self.content.remove(row)
            row.destroy()

        new_items = []
        for key, info in keyed:
            spec = self._row_spec(info, key)
            signature = self._row_signature(spec)
            row = self._rows.get(key)
            if row is None:
                new_items.append((key, info, spec, signature))
                continue
            if self._row_states.get(key) != signature:
                if not gui_rs.reconcile_list_row(row, spec):
                    raise RuntimeError(f"Failed to reconcile native installed row {key}")
                self._bind_row(row, info)
                self._row_states[key] = signature

        if new_items:
            rows = gui_rs.add_list_rows(
                self.content, [spec for _key, _info, spec, _signature in new_items]
            )
            if len(rows) != len(new_items):
                raise RuntimeError("Native installed row batch returned an incomplete result")
            for row, (key, info, _spec, signature) in zip(rows, new_items):
                self._rows[key] = row
                self._row_states[key] = signature
                self._bind_row(row, info)

        if not keyed:
            label = Gtk.Label(
                label=self.parent_window.translations.get(
                    "installed_features_empty",
                    "No removable features are currently installed.",
                )
            )
            label.get_style_context().add_class("dim-label")
            label.set_margin_top(24)
            self.content.pack_start(label, False, False, 0)
        else:
            for position, (key, _info) in enumerate(keyed):
                self.content.reorder_child(self._rows[key], position)

        self.show_all()

    @staticmethod
    def _stable_key(info):
        path = str(info.get("path") or "").strip()
        if path:
            return f"path:{path}"
        appstream_id = str(info.get("appstream_id") or "").strip()
        source = str(info.get("appstream_source") or "").strip()
        package = info.get("package-name") or ""
        if isinstance(package, (list, tuple, set)):
            package = ",".join(sorted(str(value) for value in package))
        if appstream_id or package:
            return f"appstream:{source}:{appstream_id}:{package}"
        return "entry:{}:{}".format(
            str(info.get("name", "")).casefold(),
            str(info.get("repo", "")).casefold(),
        )

    @staticmethod
    def _row_signature(spec):
        return (
            spec["name"],
            spec["icon_path"],
            spec["icon_name"],
            spec["launch"],
            spec["action_tooltip"],
        )

    def _bind_row(self, row, info):
        launch = gui_rs.card_child(row, "linuxtoys-list-row-launch")
        if launch is not None:
            launch.set_tooltip_text(
                self.parent_window.translations.get("app_page_open", "Open")
            )
            launch.connect("clicked", self._launch, info)
        action = gui_rs.card_child(row, "linuxtoys-list-row-action")
        if action is not None:
            action.connect("clicked", self._remove, info)

    def _row_spec(self, info, key):
        icon_value = str(info.get("icon") or "application-x-executable")
        icon_path = ""
        icon_name = icon_value
        if icon_value.endswith((".png", ".svg")):
            path = icon_value if os.path.isabs(icon_value) else get_icon_path(icon_value)
            if path and os.path.exists(path):
                icon_path = path
                icon_name = "application-x-executable"

        launch = bool(
            info.get("is_appstream_entry")
            and self.parent_window._can_launch_appstream_app(info)
        )
        return {
            "key": key,
            "name": str(info.get("name", "")),
            "secondary": "",
            "secondary_visible": False,
            "icon_path": icon_path,
            "icon_name": icon_name,
            "status_icon": "",
            "spinner": False,
            "launch": launch,
            "action_kind": 2,
            "destructive_action": True,
            "action_tooltip": self.parent_window.translations.get(
                "term_view_remove", "Remove installed components"
            ),
        }

    def _launch(self, _button, info):
        self.parent_window._launch_appstream_app(info)

    def _remove(self, button, info):
        self.parent_window._on_item_remove_clicked(button, dict(info))
