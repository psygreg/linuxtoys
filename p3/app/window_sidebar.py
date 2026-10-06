"""Retractable category sidebar for the main window.

Categories and subcategories are rendered natively by gui-rs in a cascading
layout (icons left of the name, subcategories indented under their parent).
Subcategories are collapsed by default; each category that has them exposes a
disclosure toggle that expands its descendants in place. The sidebar is hidden
by default; the preference is stored alongside the window geometry so future
launches restore it. It collapses automatically on views that are not category
browsing (app pages, terminal, installed features, queue, package views) and
restores itself afterwards.
"""

import os

from .gtk_common import GLib, Gtk
from . import get_icon_path, gui_rs, homebrew_catalog, parser

SIDEBAR_EXCLUDED_VIEWS = frozenset({
    "app_page",
    "running_scripts",
    "installed_features",
    "appstream_queue",
    "package_view",
    "package_loading",
})
SIDEBAR_WIDTH = 260
SIDEBAR_MIN_CONTENT_WIDTH = 400
SIDEBAR_MIN_WINDOW_WIDTH = SIDEBAR_WIDTH + SIDEBAR_MIN_CONTENT_WIDTH
SIDEBAR_TRANSITION_MS = 180
SIDEBAR_MAX_DEPTH = 3


class SidebarCtl:
    # ---- data ------------------------------------------------------------

    @staticmethod
    def _sidebar_entry_key(info):
        """Stable identity shared by sidebar rows and active navigation state."""
        path = str(info.get("path", "") or "")
        if path and "://" not in path:
            return os.path.abspath(path)
        if info.get("is_homebrew_category"):
            return "synthetic:homebrew"
        if info.get("is_aur_category"):
            return "synthetic:aur"
        return f"synthetic:{info.get('id') or info.get('name', '')}"

    def _sidebar_current_key(self):
        info = getattr(self, "current_category_info", None)
        return self._sidebar_entry_key(info) if info else None

    def _sidebar_required_expanded_keys(self):
        """Ancestor branches that must stay open to expose the current category."""
        return {
            self._sidebar_entry_key(info)
            for info in (getattr(self, "navigation_stack", ()) or ())
            if info
        }

    def _sync_sidebar_expanded_path(self):
        """Keep active ancestors open and apply deferred collapses after leaving."""
        required = self._sidebar_required_expanded_keys()
        for key in tuple(self._sidebar_deferred_collapses):
            if key not in required:
                self._sidebar_expanded_keys.discard(key)
                self._sidebar_deferred_collapses.discard(key)
        self._sidebar_expanded_keys.update(required)

    def _sync_sidebar_selection(self):
        """Apply the current-category style without rebuilding category content."""
        current_key = self._sidebar_current_key()
        for child in self._sidebar_box.get_children():
            name = child.get_name() or ""
            prefix = "linuxtoys-sidebar-row-"
            if not name.startswith(prefix):
                continue
            key = name[len(prefix):]
            action = self._sidebar_row_action(child, key)
            if action is None:
                continue
            context = action.get_style_context()
            if key == current_key:
                context.add_class("linuxtoys-sidebar-row-current")
            else:
                context.remove_class("linuxtoys-sidebar-row-current")

    def _sidebar_entries(self):
        """Ordered sidebar entries mirroring the main menu's categories.

        Subcategory rows stay hidden until each ancestor is expanded through
        its disclosure toggle; collapsed categories still advertise children.
        """
        entries = []
        used_keys = set()

        # Root shortcut is useful only while browsing inside the category tree.
        # It is deliberately synthetic so it never participates in cascade
        # expansion or category selection state.
        if getattr(self, "current_category_info", None) is not None:
            entries.append({
                "info": {
                    "id": "sidebar-main-menu",
                    "name": self.translations.get("main_menu", "Main Menu"),
                    "icon": "linuxtoys.svg",
                    "is_sidebar_main_menu": True,
                },
                "depth": 0,
                "key": "synthetic:sidebar-main-menu",
                "has_children": False,
                "expanded": False,
                "ancestors": (),
            })
            used_keys.add("synthetic:sidebar-main-menu")

        categories = (
            self.category_cache.get_categories()
            or parser.get_categories(self.translations)
        )
        for category in categories:
            # Root-level scripts (e.g. the system update entry) are not
            # categories and must not appear in the sidebar.
            if category.get("is_script") or category.get("is_create_script"):
                continue
            if category.get("is_homebrew_category"):
                continue  # appended separately while Homebrew is applicable
            self._append_sidebar_entry(category, 0, entries, used_keys, ())

        # Synthetic categories, only while they are applicable.
        if homebrew_catalog.enabled():
            self._append_sidebar_entry(
                self._homebrew_category_info(), 0, entries, used_keys, ()
            )
        return entries

    def _sidebar_subcategories(self, category, depth):
        """File-backed subcategories eligible for rows; [] past the depth cap."""
        if depth >= SIDEBAR_MAX_DEPTH:
            return []
        path = str(category.get("path", "") or "")
        if not path or "://" in path:
            return []  # synthetic categories have no file-backed children
        try:
            subcategories = parser.get_subcategories_for_category(
                path, self.translations
            )
        except Exception:
            subcategories = []
        return [
            subcategory
            for subcategory in subcategories or []
            if not subcategory.get("is_script")
            and not subcategory.get("is_create_script")
        ]

    def _append_sidebar_entry(self, info, depth, entries, used_keys, ancestors):
        """Append one row plus its descendants, preserving the real tree path."""
        children = self._sidebar_subcategories(info, depth)
        base_key = self._sidebar_entry_key(info)
        key = base_key
        suffix = 0
        while key in used_keys:  # pathological duplicates stay buildable
            suffix += 1
            key = f"{base_key}~{suffix}"
        used_keys.add(key)
        expanded = bool(children) and key in self._sidebar_expanded_keys
        entries.append({
            "info": info,
            "depth": depth,
            "key": key,
            "has_children": bool(children),
            "expanded": expanded,
            "ancestors": tuple(ancestors),
        })
        if expanded:
            child_ancestors = (*ancestors, info)
            for subcategory in children:
                self._append_sidebar_entry(
                    subcategory,
                    depth + 1,
                    entries,
                    used_keys,
                    child_ancestors,
                )

    # ---- build -----------------------------------------------------------

    def _build_sidebar(self):
        """Create the sidebar container and its native rows."""
        self._sidebar_expanded_keys = set()
        self._sidebar_deferred_collapses = set()
        self._sidebar_revealer = Gtk.Revealer()
        self._sidebar_revealer.set_transition_type(
            Gtk.RevealerTransitionType.SLIDE_RIGHT
        )
        self._sidebar_revealer.set_transition_duration(SIDEBAR_TRANSITION_MS)
        self._sidebar_revealer.set_reveal_child(False)
        # Overlay child: pinned to the left edge at its natural (drawer) width.
        self._sidebar_revealer.set_halign(Gtk.Align.START)
        self._sidebar_revealer.set_valign(Gtk.Align.FILL)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        # As an overlay child the drawer's width comes from this request and
        # never reserves layout space in the window body.
        scroller.set_size_request(SIDEBAR_WIDTH, -1)
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.get_style_context().add_class("linuxtoys-sidebar")

        self._sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._sidebar_box.set_margin_top(0)
        self._sidebar_box.set_margin_bottom(8)
        scroller.add(self._sidebar_box)
        self._sidebar_revealer.add(scroller)
        self._refresh_sidebar_rows()

    def _refresh_sidebar_rows(self):
        """Rebuild the native rows from the current catalog snapshot."""
        self._sync_sidebar_expanded_path()
        for child in self._sidebar_box.get_children():
            self._sidebar_box.remove(child)

        specs = []
        wiring = []
        # Cache each rendered row's top-level branch. Sidebar navigation can
        # then prune unrelated cascades without reparsing the category tree.
        self._sidebar_root_by_key = {}
        for entry in self._sidebar_entries():
            info = entry["info"]
            ancestors = entry.get("ancestors", ())
            root_info = ancestors[0] if ancestors else info
            self._sidebar_root_by_key[entry["key"]] = self._sidebar_entry_key(root_info)

            icon_value = str(info.get("icon", "") or "").strip()
            if icon_value.startswith("/") and os.path.isfile(icon_value):
                icon_path, icon_name = icon_value, ""
            else:
                icon_path = get_icon_path(icon_value) or "" if icon_value else ""
                icon_name = "" if icon_path else (icon_value or "folder")

            specs.append({
                "key": entry["key"],
                "label": str(info.get("name", "") or ""),
                "icon_path": icon_path,
                "icon_name": icon_name,
                "depth": entry["depth"],
                "has_children": entry["has_children"],
                "expanded": entry["expanded"],
            })
            wiring.append((
                entry["key"],
                info,
                entry["has_children"],
                entry["expanded"],
                entry["ancestors"],
            ))

        rows = gui_rs.build_sidebar(self._sidebar_box, specs)
        for key, info, has_children, expanded, ancestors in wiring:
            row = rows.get(key)
            if row is None:
                continue
            action = self._sidebar_row_action(row, key)
            if action is not None:
                action.connect(
                    "clicked", self._on_sidebar_row_clicked, info, ancestors
                )
            if not has_children:
                continue
            toggle = self._sidebar_row_toggle(row, key)
            if toggle is not None:
                toggle.set_tooltip_text(
                    self.translations.get(
                        "sidebar_collapse" if expanded else "sidebar_expand",
                        "Collapse" if expanded else "Expand",
                    )
                )
                toggle.connect("clicked", self._on_sidebar_expand_toggled, key)
        self._sync_sidebar_selection()

    @staticmethod
    def _sidebar_row_named_child(row, wanted):
        for child in row.get_children():
            if child.get_name() == wanted:
                return child
        return None

    @classmethod
    def _sidebar_row_action(cls, row, key):
        return cls._sidebar_row_named_child(
            row, f"linuxtoys-sidebar-action-{key}"
        )

    @classmethod
    def _sidebar_row_toggle(cls, row, key):
        return cls._sidebar_row_named_child(
            row, f"linuxtoys-sidebar-toggle-{key}"
        )

    # ---- navigation ------------------------------------------------------

    def _on_sidebar_row_clicked(self, _button, info, ancestors):
        if info.get("is_sidebar_main_menu"):
            if getattr(self, "search_active", False):
                self._clear_search_results()
            self.show_categories_view()
            return

        # Clicking the already-visible category is a selection operation, not
        # navigation: do not rebuild its page or duplicate navigation history.
        if self._sidebar_entry_key(info) == self._sidebar_current_key():
            return
        if getattr(self, "search_active", False):
            self._clear_search_results()

        # Record the destination branch using the row metadata cached during
        # the last sidebar build. Avoid calling _sidebar_entries() here: that
        # reparses subcategory files synchronously on every sidebar click and
        # made sidebar navigation noticeably slower than card navigation.
        destination_root = ancestors[0] if ancestors else info
        destination_root_key = self._sidebar_entry_key(destination_root)
        self._sidebar_pending_root_key = destination_root_key

        # The actual ancestor chain is consumed by show_scripts_view() when the
        # destination page becomes current.
        self._sidebar_navigation_path = [dict(item) for item in ancestors]
        try:
            self._activate_category_info(info)
        finally:
            # Reboot-gate cancellation or another early return must not leak a
            # stale path into the next non-sidebar navigation.
            self._sidebar_navigation_path = None

    def _on_sidebar_expand_toggled(self, _button, key):
        """Show or hide one category's subcategory rows."""
        required = self._sidebar_required_expanded_keys()
        if key in required and key in self._sidebar_expanded_keys:
            # Keep the active path visible, but remember a collapse request
            # until navigation leaves this branch.
            if key in self._sidebar_deferred_collapses:
                self._sidebar_deferred_collapses.discard(key)
            else:
                self._sidebar_deferred_collapses.add(key)
        elif key in self._sidebar_expanded_keys:
            self._sidebar_expanded_keys.discard(key)
            self._sidebar_deferred_collapses.discard(key)
        else:
            self._sidebar_expanded_keys.add(key)
            self._sidebar_deferred_collapses.discard(key)
        self._refresh_sidebar_rows()

    # ---- visibility state ------------------------------------------------

    def _main_stack_view_excluded(self):
        name = self.main_stack.get_visible_child_name() or ""
        return (
            name in SIDEBAR_EXCLUDED_VIEWS or name.startswith("app_page_refresh_")
        )

    def _sidebar_window_width(self):
        """Current window width; overridable for tests."""
        return self.get_allocated_width()

    def _set_sidebar_content_offset(self, reserved):
        """Reserve drawer width without making the sidebar a layout sibling."""
        offset = SIDEBAR_WIDTH if reserved else 0
        if self.main_stack.get_margin_start() == offset:
            return
        self.main_stack.set_margin_start(offset)
        self.main_stack.queue_resize()

    def _cancel_sidebar_release(self):
        source = getattr(self, "_sidebar_release_timer", None)
        if source is not None:
            GLib.source_remove(source)
            self._sidebar_release_timer = None

    def _finish_sidebar_hide(self):
        self._sidebar_release_timer = None
        # A quick reopen may happen before the close animation finishes. Never
        # release its reserved space underneath an open/reopening drawer.
        if not self._sidebar_revealer.get_reveal_child():
            self._set_sidebar_content_offset(False)
        return False

    def _set_sidebar_open(self, open_):
        """Change drawer visibility with one content reflow per operation."""
        self._cancel_sidebar_release()
        if open_:
            # Shrink the content once, then animate the overlay into the space.
            self._set_sidebar_content_offset(True)
            self._sidebar_revealer.set_reveal_child(True)
            return

        # Keep the content reserved while the drawer slides away. Expanding it
        # only after the transition avoids walking responsive layouts through
        # intermediate widths during the animation.
        self._sidebar_revealer.set_reveal_child(False)
        self._sidebar_release_timer = GLib.timeout_add(
            SIDEBAR_TRANSITION_MS, self._finish_sidebar_hide
        )

    def _apply_sidebar_state(self):
        """Apply preference + view context + width guard to the sidebar."""
        width = self._sidebar_window_width()
        width_ok = width == 0 or width >= SIDEBAR_MIN_WINDOW_WIDTH
        excluded = self._main_stack_view_excluded()
        open_allowed = width_ok and not excluded and self._sidebar_preferred

        # set_active() re-enters the toggle handler; flag the sync so the
        # programmatic state write never overwrites the stored preference.
        self._sidebar_updating = True
        try:
            self._set_sidebar_open(open_allowed)
            self.sidebar_toggle_button.set_active(open_allowed)
            # Width-driven hide only. Deliberately NOT view-driven: flipping
            # header-bar children during stack transitions interfered with
            # slide allocations in the previous column layout.
            self.sidebar_toggle_button.set_visible(width_ok)
        finally:
            self._sidebar_updating = False

    def _on_sidebar_toggle_clicked(self, button):
        if getattr(self, "_sidebar_updating", False):
            return  # programmatic sync from _apply_sidebar_state, not a user action
        self._sidebar_preferred = bool(button.get_active())
        self._save_window_state()
        self._apply_sidebar_state()

    def _on_main_stack_view_changed(self, *_args):
        self._apply_sidebar_state()
        # current_category_info is updated by navigation before the destination
        # becomes visible. Besides expansion changes, crossing the root/category
        # boundary changes the row set itself because Main Menu is contextual.
        before = set(self._sidebar_expanded_keys)
        self._sync_sidebar_expanded_path()

        # A sidebar jump may cross top-level branches. Apply that cleanup only
        # after navigation_stack has changed, so deferred collapses retain their
        # original semantics and the old active path cannot be re-opened.
        pending_root = getattr(self, "_sidebar_pending_root_key", None)
        if pending_root is not None:
            self._sidebar_pending_root_key = None
            required = self._sidebar_required_expanded_keys()
            keep = required | {
                key
                for key in self._sidebar_expanded_keys
                if self._sidebar_root_by_key.get(key) == pending_root
            }
            self._sidebar_expanded_keys.intersection_update(keep)
            self._sidebar_deferred_collapses.intersection_update(keep)

        wants_main_menu = getattr(self, "current_category_info", None) is not None
        has_main_menu = any(
            child.get_name() == "linuxtoys-sidebar-row-synthetic:sidebar-main-menu"
            for child in self._sidebar_box.get_children()
        )

        if before != self._sidebar_expanded_keys or wants_main_menu != has_main_menu:
            self._refresh_sidebar_rows()
        else:
            self._sync_sidebar_selection()

    def _on_window_size_for_sidebar(self, _window, allocation):
        width_ok = allocation.width >= SIDEBAR_MIN_WINDOW_WIDTH
        if width_ok != getattr(self, "_sidebar_width_ok_last", None):
            self._sidebar_width_ok_last = width_ok
            self._apply_sidebar_state()
        return False