"""GTK view listing features that LinuxToys can currently remove."""

import os

from . import get_icon_path, gui_rs, installed_packages, parser, registry_utils
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
        self.refresh()

    def refresh(self):
        cache = self.parent_window.script_cache
        if not cache.is_populated:
            gui_rs.reconcile_list_rows(self.content, state="loading")
            self.show_all()
            return

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

        # External packages installed through the package view have no catalog
        # entry backing them. Their registry transactions record a package-file
        # or AppImage install, so surface them here to stay removable.
        known_registry_names = {
            str(item.get("registry_name") or item.get("name") or "").strip()
            for item in cache.get_all_scripts()
        }
        known_registry_names.discard("")
        for registry_name in registry_utils.get_local_package_entries():
            if registry_name in known_registry_names:
                continue
            info = {
                "name": registry_name,
                "description": "",
                "icon": "package-x-generic",
                "repo": "",
                "path": "",
                "is_script": True,
                "is_local_package": True,
                "registry_name": registry_name,
            }
            key = self._stable_key(info)
            if key in seen:
                continue
            seen.add(key)
            installed.append(info)

        installed.sort(key=lambda info: str(info.get("name", "")).casefold())
        keyed = [(self._stable_key(info), info) for info in installed]

        if not keyed:
            gui_rs.reconcile_list_rows(
                self.content,
                state="empty",
                empty_text=self.parent_window.translations.get(
                    "installed_features_empty",
                    "No removable features are currently installed.",
                ),
            )
            self.show_all()
            return

        specs = [self._row_spec(info, key) for key, info in keyed]
        rows = gui_rs.reconcile_list_rows(self.content, specs)
        for key, info in keyed:
            self._bind_row(rows[key], info)

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

    def _bind_row(self, row, info):
        launch = gui_rs.card_child(row, "linuxtoys-list-row-launch")
        if launch is not None:
            launch.set_tooltip_text(
                self.parent_window.translations.get("app_page_open", "Open")
            )
            launch.connect("clicked", self._launch, info)
        action = gui_rs.card_child(row, "linuxtoys-list-row-action")
        if action is not None:
            # Dependency protection overlay: the row stays listed as installed,
            # but removal is switched off while dependents exist.
            blockers = installed_packages.dependency_blockers(info)
            action.set_sensitive(not blockers)
            if blockers:
                action.set_tooltip_text(
                    self.parent_window.translations.get(
                        "dependency_block_button_tooltip",
                        "Removal blocked: installed software still depends "
                        "on this feature",
                    )
                )
            action.connect("clicked", self._remove, info)

    def _row_spec(self, info, key):
        icon_value = str(info.get("icon") or "application-x-executable")
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
