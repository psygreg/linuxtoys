import asyncio
import logging
import os
import shutil
import threading
import sys

from . import (
    action_registry,
    compat,
    deepin_immutable_helper,
    dev_mode,
    file_watcher,
    get_icon_path,
    head_menu,
    header,
    manifest_helper,
    needed_helper,
    parser,
    reboot_helper,
    revealer,
    search_helper,
    skills_view,
    repo_parser,
    git_scripts_manager
)
from .gtk_common import Gdk, GLib, Gtk, GdkPixbuf
from .window_items import ItemWidgetFactory
from .window_search import SearchCtl
from .window_nav import NavCtl
from .featured_scripts import FeaturedCtl
from .local_scripts import LocalScriptsCtl
from .updater.update_dialog import UpdateDialog
from .updater.update_helper import UpdateHelper, run_background_update
from .lang_utils import get_automatic_updates, create_translator

logger = logging.getLogger(__name__)


class AppWindow(
    SearchCtl,
    NavCtl,
    FeaturedCtl,
    LocalScriptsCtl,
    ItemWidgetFactory,
    Gtk.ApplicationWindow,
):
    def __init__(self, application, translations, *args, **kwargs):
        super().__init__(application=application, *args, **kwargs)
        self.translations = translations

        self.set_title("LinuxToys")
        self.set_default_size(920, 800)  ##
        # self.set_resizable(False) ## Desabilita o redimensionamento da janela

        # Set window icon for proper GNOME integration
        self._set_window_icon()

        # --- Instance variables for script management ---
        self.reboot_required = False  # Track if a reboot is required
        self.current_category_info = None  # Track current category for header updates
        self.navigation_stack = []  # Stack to track navigation history for proper back button behavior
        # Fully-built parent category views retained while navigating deeper.
        # NavCtl consumes these on Back instead of reconstructing FlowBoxes.
        self._category_view_cache = {}
        self.view_counter = 0  # Counter for unique view names
        self._scripts_sync_started = False

        # Initialize search functionality with cache
        self.script_cache = search_helper.ScriptCache()
        self.search_engine = search_helper.create_search_engine(
            self.translations, self.script_cache
        )
        self.search_active = False
        self.search_results = []
        
        # Initialize category cache for faster navigation
        self.category_cache = search_helper.CategoryCache()

        # Random scripts display
        self.all_scripts = []  # Cache of all available scripts from all categories
        self.random_scripts_flowbox = None  # Flowbox for random scripts
        self.random_scripts_refresh_timer = None  # Timer for periodic refresh
        self.random_scripts_label = None  # Label for "Featured" section
        self.featured_scripts_container = None  # Container for the featured section
        self.should_start_random_timer = False  # Flag to start timer when scripts are ready
        self._featured_resize_timer = None
        self._featured_last_count = None
        self._featured_swap_timer = None
        self._featured_hovered = False
        self.featured_scripts_revealer = None
        self.random_scripts_revealer = None

        # Checklist
        self.check_buttons = []

        # Auto error reporting preference
        self.auto_error_reports_enabled = False

        # Automatic self-update state. Missing preferences intentionally default on.
        self.automatic_updates_enabled = get_automatic_updates()
        self._background_update_started = False
        self._update_state = "checking" if self.automatic_updates_enabled else "disabled"

        # --- UI Structure ---
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_vbox)

        self.header_widget = header.create_header(self.translations)
        main_vbox.pack_start(self.header_widget, False, False, 8)

        # HeaderBar setup with Hyprland/Wayland compatibility
        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_show_close_button(True)

        # Try to detect if we're running on Wayland/Hyprland and adjust accordingly
        try:
            # Check if we should use server-side decorations for better compatibility
            display = Gdk.Display.get_default()
            if display:
                backend_type = type(display).__name__
                if "Wayland" in backend_type:
                    # On Wayland (including Hyprland), prefer server-side decorations
                    # This can help avoid hanging issues with client-side decorations
                    self.set_decorated(True)  # Enable window manager decorations
                    # Still set the headerbar but with less aggressive CSD
                    self.header_bar.set_decoration_layout(
                        "menu:minimize,maximize,close"
                    )
        except Exception as e:
            print(f"Warning: Could not detect display backend: {e}")

        self.set_titlebar(self.header_bar)

        self.back_button = Gtk.Button.new_from_icon_name(
            "go-previous-symbolic", Gtk.IconSize.BUTTON
        )
        self.header_bar.pack_start(self.back_button)

        # Create search UI components
        self._create_search_ui()

        # Store reference to the menu button for later updates
        self.menu_button = head_menu.MenuButton(
            parent_window=self, on_language_changed=self.on_language_changed
        )
        self.header_bar.pack_end(self.menu_button)

        # Automatic update status indicator, shown only while automatic updates
        # are enabled (or while an installed update is waiting for restart).
        self.update_indicator = Gtk.Button()
        self.update_indicator.set_relief(Gtk.ReliefStyle.NONE)
        self.update_indicator.get_style_context().add_class("update-indicator")
        self.update_indicator.connect("clicked", self._on_update_indicator_clicked)
        self.header_bar.pack_end(self.update_indicator)
        self._set_update_state(self._update_state)

        self.main_stack = Gtk.Stack()
        self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.main_stack.set_transition_duration(
            200
        )  # Set a reasonable transition duration
        main_vbox.pack_start(self.main_stack, True, True, 0)

        # Create categories view with random scripts section
        categories_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        self.categories_flowbox = self.create_flowbox()
        categories_container.pack_start(self.categories_flowbox, False, False, 0)
        
        # Create separator and featured scripts section. The outer revealer animates
        # the section's first appearance; the inner revealer cross-fades card swaps.
        self.featured_scripts_revealer = Gtk.Revealer()
        self.featured_scripts_revealer.set_transition_type(
            Gtk.RevealerTransitionType.SLIDE_DOWN
        )
        self.featured_scripts_revealer.set_transition_duration(220)
        self.featured_scripts_revealer.set_reveal_child(False)

        self.featured_scripts_container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=12
        )
        self.featured_scripts_container.set_margin_left(32)
        self.featured_scripts_container.set_margin_top(24)
        self.featured_scripts_container.set_margin_right(32)
        self.featured_scripts_container.set_margin_bottom(24)
        
        # Add separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.featured_scripts_container.pack_start(separator, False, False, 0)
        
        # Add label for featured scripts
        self.random_scripts_label = Gtk.Label(
            label=self.translations.get("featured_scripts", "Try These")
        )
        self.random_scripts_label.set_halign(Gtk.Align.START)
        self.random_scripts_label.set_markup(f"<big><b>{self.random_scripts_label.get_text()}</b></big>")
        label_style = self.random_scripts_label.get_style_context()
        label_style.add_class("title-2")  # Add CSS class for styling
        self.featured_scripts_container.pack_start(self.random_scripts_label, False, False, 0)
        
        # Create flowbox for random scripts (without extra margins since container has them)
        self.random_scripts_flowbox = Gtk.FlowBox()
        self.random_scripts_flowbox.set_valign(Gtk.Align.START)
        self.random_scripts_flowbox.set_max_children_per_line(5)
        self.random_scripts_flowbox.set_activate_on_single_click(False)
        self.random_scripts_flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.random_scripts_flowbox.connect(
            "key-press-event", self._on_flowbox_key_press
        )
        self.random_scripts_flowbox.set_homogeneous(True)
        # No margins here since the container already has them
        self.random_scripts_flowbox.set_margin_left(0)
        self.random_scripts_flowbox.set_margin_top(0)
        self.random_scripts_flowbox.set_margin_right(0)
        self.random_scripts_flowbox.set_margin_bottom(0)
        self.random_scripts_flowbox.set_column_spacing(16)
        self.random_scripts_flowbox.set_row_spacing(12)
        
        self.random_scripts_revealer = Gtk.Revealer()
        self.random_scripts_revealer.set_transition_type(
            Gtk.RevealerTransitionType.CROSSFADE
        )
        self.random_scripts_revealer.set_transition_duration(180)
        self.random_scripts_revealer.set_reveal_child(False)
        self.random_scripts_revealer.add(self.random_scripts_flowbox)
        self.featured_scripts_container.pack_start(
            self.random_scripts_revealer, False, False, 0
        )

        self.featured_scripts_revealer.add(self.featured_scripts_container)
        categories_container.pack_start(
            self.featured_scripts_revealer, False, False, 0
        )
        
        self.categories_view = Gtk.ScrolledWindow()
        self.categories_view.add(categories_container)
        self.main_stack.add_named(self.categories_view, "categories")

        self.scripts_flowbox = self.create_flowbox()
        self.scripts_view = Gtk.ScrolledWindow()
        self.scripts_view.add(self.scripts_flowbox)
        self.main_stack.add_named(self.scripts_view, "scripts")

        # Create search results view
        self.search_flowbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.search_view = Gtk.ScrolledWindow()
        self.search_view.add(self.search_flowbox)
        self.main_stack.add_named(self.search_view, "search")

        self.reveal = revealer.RevealerFooter(self)
        main_vbox.pack_start(self.reveal, False, False, 0)

        # --- Load Data and Connect Signals ---
        # Categories are published by the progressive parser worker below. Avoid
        # a synchronous parser.get_categories() pass on the GTK startup thread.
        self.back_button.connect("clicked", self.on_back_button_clicked)

        # --- Check for pending ostree deployments ---
        self._check_ostree_deployments_on_startup()

        # --- Show the Window ---
        self.show_all()
        self.show_categories_view()  # Call this after show_all to ensure proper visibility state

        # Connect focus events to enable/disable tooltips
        self.connect("focus-in-event", self._on_focus_in)
        self.connect("focus-out-event", self._on_focus_out)

        self.connect("key-press-event", self._on_key_press)

        self.categories_view.connect(
            "size-allocate",
            self._on_featured_size_allocate,
        )

        # Local scripts
        self.local_sh_dir = f"{os.environ['HOME']}/.local/linuxtoys/scripts/"

        # Initialize drag-and-drop but don't enable it by default
        self._setup_drag_and_drop()

        self._script_running = False

        # Build all parser-backed caches in one background pass.  Running three
        # independent walkers here used to make them contend for the GIL and disk
        # cache while parsing the same files repeatedly.
        # Prioritize parser-backed startup data. Git synchronization begins as
        # soon as top-level scripts (and therefore Featured Scripts) are ready.
        GLib.idle_add(self._populate_runtime_caches)
        GLib.idle_add(self._show_ostree_package_deployment_info_on_startup)
        GLib.idle_add(self._check_updates)
        GLib.idle_add(self._start_file_watcher)
        GLib.idle_add(self._check_deepin_immutability_on_startup)

    def _populate_runtime_caches(self):
        """Build parser caches while progressively publishing startup-ready data."""

        category_cache = self.category_cache
        script_cache = self.script_cache
        translations = self.translations
        git_sync_scheduled = False

        def schedule_git_sync():
            nonlocal git_sync_scheduled
            if git_sync_scheduled:
                return
            git_sync_scheduled = True
            GLib.idle_add(self._start_scripts_synchronization)

        def collect_featured(categories, scripts_by_category):
            featured = []
            seen = set()
            for category in categories:
                if category.get("is_script"):
                    continue
                category_path = category.get("path", "")
                if not category_path:
                    continue
                for item in scripts_by_category.get(os.path.abspath(category_path), ()):
                    if not item.get("is_script") or item.get("is_create_script"):
                        continue
                    key = item.get("path") or (
                        item.get("name", ""),
                        item.get("repo", ""),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    featured.append(item)
            return featured

        def publish_bootstrap(categories, featured):
            # GTK-side publication. Cache identity is our generation guard for
            # script synchronization and language changes that replace the caches.
            if self.category_cache is not category_cache:
                return False

            self._render_categories(categories)
            self.all_scripts = featured
            if self.should_start_random_timer and featured:
                self._deferred_start_random_scripts_refresh_timer()
            return False

        def top_level_ready(categories, scripts_by_category):
            # Runs in the parser worker. Only prepare immutable-ish Python snapshots
            # here; all GTK work is handed back to the main loop.
            if self.category_cache is not category_cache:
                return

            featured = collect_featured(categories, scripts_by_category)
            GLib.idle_add(publish_bootstrap, categories, featured)

            # Network/git work is lower startup priority than getting the first
            # usable Featured pool ready, but need not wait for recursive caches.
            schedule_git_sync()

        def publish_full_featured(featured):
            if self.category_cache is not category_cache:
                return False
            self.all_scripts = featured
            if self.should_start_random_timer and featured:
                self._deferred_start_random_scripts_refresh_timer()
            return False

        def populate_in_background():
            try:
                category_cache.populate(
                    translations,
                    top_level_ready=top_level_ready,
                    top_level_ready_min_scripts=10,
                )

                # A scripts sync/language change may have swapped cache objects while
                # this worker was parsing the previous source. Never publish stale data.
                if self.category_cache is not category_cache:
                    return

                full_featured = collect_featured(
                    category_cache.get_categories(),
                    category_cache.scripts_by_category,
                )
                GLib.idle_add(publish_full_featured, full_featured)

                script_cache.populate_from_category_cache(category_cache)
            except Exception as e:
                print(f"Error populating runtime caches: {e}")
            finally:
                # Do not suppress synchronization merely because one parser entry
                # was malformed. _scripts_sync_started keeps this idempotent.
                schedule_git_sync()

        threading.Thread(target=populate_in_background, daemon=True).start()
        return False

    def _populate_search_cache(self):
        """Populate the search cache in a background thread to avoid blocking the UI."""

        def populate_in_background():
            try:
                self.script_cache.populate(self.translations)
            except Exception as e:
                print(f"Error populating search cache: {e}")

        threading.Thread(target=populate_in_background, daemon=True).start()
        return False  # Remove from idle callbacks

    def _populate_category_cache(self):
        """Populate the category cache in a background thread to avoid blocking the UI."""

        def populate_in_background():
            try:
                self.category_cache.populate(self.translations)
            except Exception as e:
                print(f"Error populating category cache: {e}")

        threading.Thread(target=populate_in_background, daemon=True).start()
        return False  # Remove from idle callbacks

    def _populate_all_scripts(self):
        """Populate the all_scripts cache in a background thread for random scripts display."""

        def populate_in_background():
            try:
                self.all_scripts = self._collect_all_scripts()
                # Start the timer if we're on the main menu and scripts were collected
                if self.should_start_random_timer and self.all_scripts:
                    GLib.idle_add(self._deferred_start_random_scripts_refresh_timer)
            except Exception as e:
                print(f"Error populating all scripts cache: {e}")

        threading.Thread(target=populate_in_background, daemon=True).start()
        return False  # Remove from idle callbacks

    def _start_scripts_synchronization(self):
        """Synchronize remote scripts after the GTK window has started."""
        if self._scripts_sync_started or dev_mode.is_dev_mode_enabled():
            return False

        self._scripts_sync_started = True

        def synchronize_in_background():
            try:
                result = git_scripts_manager.synchronize_scripts()
            except Exception as e:
                logger.warning("Background scripts synchronization failed: %s", e)
                return

            new_root = result.get("path")
            if not result.get("success") or not new_root or not os.path.isdir(new_root):
                return

            old_root = os.path.abspath(parser.SCRIPTS_DIR)
            new_root = os.path.abspath(new_root)
            source_changed = old_root != new_root

            if source_changed or result.get("changed"):
                GLib.idle_add(
                    self._apply_synchronized_scripts,
                    old_root,
                    new_root,
                )

        threading.Thread(target=synchronize_in_background, daemon=True).start()
        return False

    @staticmethod
    def _rebase_scripts_path(path, old_root, new_root):
        """Move a scripts-tree path to the same relative location in a new root."""
        if not path:
            return path

        try:
            absolute_path = os.path.abspath(path)
            if os.path.commonpath((absolute_path, old_root)) != old_root:
                return path
            relative = os.path.relpath(absolute_path, old_root)
            return os.path.normpath(os.path.join(new_root, relative))
        except (OSError, ValueError):
            return path

    def _rebase_category_info(self, category_info, old_root, new_root):
        if not category_info:
            return category_info
        updated = dict(category_info)
        updated["path"] = self._rebase_scripts_path(
            updated.get("path", ""), old_root, new_root
        )
        return updated

    def _apply_synchronized_scripts(self, old_root, new_root):
        """Switch parser/cache/UI state to a successfully synchronized scripts tree."""
        if self._script_running or self.main_stack.get_visible_child_name() == "app_page":
            # Keep already-open execution/app-page objects tied to the source they
            # were created from. Apply the new tree as soon as that view is idle.
            GLib.timeout_add(500, self._apply_synchronized_scripts, old_root, new_root)
            return False

        source_changed = old_root != new_root

        if source_changed:
            self.current_category_info = self._rebase_category_info(
                self.current_category_info, old_root, new_root
            )
            self.navigation_stack = [
                self._rebase_category_info(item, old_root, new_root)
                for item in self.navigation_stack
            ]

        # Retained GTK views reflect the old parser/cache state. Never carry
        # them across a synchronized scripts-tree update.
        self._discard_retained_category_views()

        parser.set_scripts_dir(new_root)
        os.environ["CACHE_DIR"] = new_root

        # Replace cache instances instead of invalidating them in place. Any initial
        # startup-population thread can then finish harmlessly on the old objects.
        self.script_cache = search_helper.ScriptCache()
        self.category_cache = search_helper.CategoryCache()
        self.search_engine.set_cache(self.script_cache)
        self.all_scripts = []

        # Immediately rebuild the visible view directly from the new filesystem.
        self.load_categories()
        if self.current_category_info is not None:
            fresh_info = self._get_fresh_category_info_with_translations()
            if fresh_info:
                self.current_category_info = fresh_info
            self.load_scripts(self.current_category_info)
            self._update_header(self.current_category_info)

        # Repopulate all acceleration caches from the new source in one pass.
        self._populate_runtime_caches()

        # If a search is visible, rerun the query once the new search cache is ready.
        if self.main_stack.get_visible_child_name() == "search":
            query = self.search_entry.get_text()

            def refresh_search_when_ready():
                if not self.script_cache.is_populated:
                    return True
                if query and self.search_entry.get_text() == query:
                    self.search_entry.emit("changed")
                return False

            GLib.timeout_add(100, refresh_search_when_ready)

        return False

    def _start_file_watcher(self):
        """Start the file watcher (only active in DEV_MODE)."""
        if not dev_mode.is_dev_mode_enabled():
            return False
        file_watcher.start(self)
        return False

    def _on_files_changed(self, changed_files):
        """Handle file change notification from the watcher."""
        # DEV_MODE may add/remove/rename scripts or categories in-place. Drop the
        # structural parser index before rebuilding UI/search caches so those
        # changes are visible immediately.
        parser.clear_script_tree_cache()
        self._discard_retained_category_views()
        self.script_cache.invalidate()
        self.category_cache.invalidate()
        self.all_scripts = []
        self.load_categories()
        if self.current_category_info is not None:
            self.load_scripts(self.current_category_info)

        py_changed = any(f.endswith('.py') for f in changed_files)
        if py_changed:
            import os, sys
            python = sys.executable
            os.execv(python, [python] + sys.argv)

    def _tr_update(self, key, fallback):
        """Translate an update UI string while translation catalogs catch up."""
        value = create_translator()(key)
        return fallback if value == key else value

    def _set_update_state(self, state):
        """Update the header indicator. Must only be called on the GTK thread."""
        self._update_state = state
        if not hasattr(self, "update_indicator"):
            return False

        context = self.update_indicator.get_style_context()
        context.remove_class("suggested-action")
        context.remove_class("update-restart-ready")
        self.update_indicator.set_sensitive(False)

        if state == "disabled":
            self.update_indicator.hide()
            return False

        self.update_indicator.show()
        if state == "checking":
            image = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
            tooltip = self._tr_update("update_status_checking", "Checking for updates…")
        elif state == "up-to-date":
            image = Gtk.Image.new_from_icon_name("emblem-ok-symbolic", Gtk.IconSize.BUTTON)
            tooltip = self._tr_update("update_status_up_to_date", "LinuxToys is up to date.")
        elif state == "updating":
            spinner = Gtk.Spinner()
            spinner.start()
            image = spinner
            tooltip = self._tr_update("update_status_updating", "Updating LinuxToys…")
        elif state == "restart-ready":
            image = Gtk.Image.new_from_icon_name("software-update-available-symbolic", Gtk.IconSize.BUTTON)
            tooltip = self._tr_update("update_status_restart", "Update installed. Restart LinuxToys.")
            self.update_indicator.set_sensitive(True)
            context.add_class("suggested-action")
            context.add_class("update-restart-ready")
        else:
            image = Gtk.Image.new_from_icon_name("dialog-warning-symbolic", Gtk.IconSize.BUTTON)
            tooltip = self._tr_update("update_status_failed", "Automatic update failed.")

        self.update_indicator.set_image(image)
        self.update_indicator.set_tooltip_text(tooltip)
        self.update_indicator.show_all()
        return False

    def set_automatic_updates_enabled(self, enabled):
        self.automatic_updates_enabled = bool(enabled)
        if not enabled:
            # Do not discard a completed update's restart affordance.
            if self._update_state != "restart-ready":
                self._set_update_state("disabled")
            return

        if self._update_state in ("disabled", "error"):
            self._set_update_state("checking")
            self._check_updates()

    def _on_update_indicator_clicked(self, _button):
        if self._update_state != "restart-ready":
            return
        os.execv(sys.executable, [sys.executable, *sys.argv])

    def _check_updates(self):
        if self.automatic_updates_enabled:
            self._set_update_state("checking")
        threading.Thread(target=self._show_dialog_and_update, daemon=True).start()
        return False

    def _show_dialog_and_update(self):
        self._check = UpdateHelper()
        available = self._check._update_available()

        if not available:
            if self.automatic_updates_enabled:
                GLib.idle_add(self._set_update_state, "up-to-date")
            return

        if not self.automatic_updates_enabled:
            GLib.idle_add(self._open_update_dialog, self._check._latest_ver)
            return

        if self._background_update_started:
            return
        self._background_update_started = True
        GLib.idle_add(self._set_update_state, "updating")
        success, error = run_background_update()
        if success:
            GLib.idle_add(self._set_update_state, "restart-ready")
        else:
            self._background_update_started = False
            if error:
                logger.warning("Automatic LinuxToys update failed: %s", error)
            GLib.idle_add(self._set_update_state, "error")

    def _open_update_dialog(self, latest_ver):
        UpdateDialog(latest_ver, self).show()
        return False

    def _is_menu_flowbox_focused(self):
        """Return whether keyboard focus is on a menu FlowBox, not a child button."""
        focused_widget = self.get_focus()
        if isinstance(focused_widget, Gtk.Button):
            return False

        while focused_widget is not None:
            if isinstance(focused_widget, Gtk.FlowBox):
                return True
            focused_widget = focused_widget.get_parent()
        return False

    def _on_key_press(self, widget, event):
        keyval = event.keyval

        current_view = self.main_stack.get_visible_child_name()
        if current_view == "app_page":
            page = self.main_stack.get_child_by_name("app_page")
            if keyval == Gdk.KEY_Escape:
                self.on_back_button_clicked(None)
                return True
            if page is not None and keyval in (Gdk.KEY_Left, Gdk.KEY_Right):
                page.cycle_screenshot(-1 if keyval == Gdk.KEY_Left else 1)
                return True
            return False

        if current_view == "running_scripts":
            return False

        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if not self._is_menu_flowbox_focused():
                return False

        if keyval == Gdk.KEY_Delete:
            selected_children = [
                child.get_child().info
                for child in self.scripts_flowbox.get_selected_children()
            ]
            self._delete_local_scripts(selected_children)

        elif (event.state & Gdk.ModifierType.CONTROL_MASK) and keyval == Gdk.KEY_a:
            if self._is_local_scripts_category(self.current_category_info):
                for child in self.scripts_flowbox.get_children():
                    self.scripts_flowbox.select_child(child)
                return True

            return False

        elif keyval == Gdk.KEY_space:
            # In checklist mode, Space toggles the checkbox of the currently selected item
            if (
                self.current_category_info
                and self.current_category_info.get("display_mode", "menu")
                == "checklist"
            ):
                selected_children = self.scripts_flowbox.get_selected_children()
                if selected_children:
                    # Get the first selected child
                    child = selected_children[0]
                    event_box = child.get_child()
                    # Use the stored checkbox reference
                    if hasattr(event_box, "checkbox"):
                        event_box.checkbox.set_active(
                            not event_box.checkbox.get_active()
                        )
                        return True
                return False

        elif keyval == Gdk.KEY_Escape:
            # Determine which flowbox has selections based on current view
            current_view = self.main_stack.get_visible_child_name()
            flowbox_to_check = None

            if current_view == "search":
                if self._clear_search_result_selections():
                    return True
            elif current_view == "categories":
                flowbox_to_check = self.categories_flowbox
            else:  # scripts view
                flowbox_to_check = self.scripts_flowbox

            # First, deselect any selected items
            if flowbox_to_check and flowbox_to_check.get_selected_children():
                flowbox_to_check.unselect_all()
                return True

            # If nothing is selected, go back to the previous menu
            # (but not if we're already at the main categories view)
            if current_view != "categories" or self.search_active:
                self.on_back_button_clicked(None)
                return True

            return False

        elif keyval == Gdk.KEY_Return:
            # In checklist mode, special handling
            if (
                self.current_category_info
                and self.current_category_info.get("display_mode", "menu")
                == "checklist"
            ):
                # Get all checked items
                checked_scripts = [
                    cb.script_info for cb in self.check_buttons if cb.get_active()
                ]

                if checked_scripts:
                    # Run all checked scripts
                    self.on_install_checklist(None)
                    return True
                else:
                    # If nothing is checked, run only the currently selected item
                    selected_children = self.scripts_flowbox.get_selected_children()
                    if selected_children:
                        self._activate_item(selected_children[0].get_child(), event)
                        return True
            else:
                # Normal menu behavior: activate the selected item
                if self.main_stack.get_visible_child_name() == "search":
                    selected_widget = self._get_selected_search_result_children()
                elif self.main_stack.get_visible_child_name() == "categories":
                    selected_widget = self.categories_flowbox.get_selected_children()
                else:
                    selected_widget = self.scripts_flowbox.get_selected_children()

                if selected_widget:
                    self._activate_item(selected_widget[0].get_child(), event)
                return True

        # Quick search: if typing letters without modifiers, focus search entry and type there
        current_focus = self.get_focus()
        if (
            current_focus != self.search_entry
            and (65 <= keyval <= 90 or 97 <= keyval <= 122)
            and not (
                event.state
                & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.META_MASK)
            )
        ):
            self.search_entry.grab_focus()
            current_text = self.search_entry.get_text()
            char = chr(keyval)
            self.search_entry.set_text(current_text + char)
            self.search_entry.set_position(-1)  # Move cursor to end
            return True

        return False

    def _check_ostree_deployments_on_startup(self):
        """
        Check for pending ostree deployments on application startup.
        If found on compatible systems, show warning dialog.
        """
        # Get system compatibility keys
        system_compat_keys = compat.get_system_compat_keys()

        # Only check on ostree-based systems
        if {"ostree", "ublue"} & system_compat_keys:
            if reboot_helper.check_ostree_pending_deployments():
                # Use GLib.idle_add to ensure the dialog shows after the window is fully initialized
                GLib.idle_add(self._show_ostree_deployment_warning)

    def _show_ostree_deployment_warning(self):
        """
        Show the ostree deployment warning dialog.
        Called via GLib.idle_add to ensure proper timing.
        """
        reboot_helper.handle_ostree_deployment_requirement(
            self, self.translations, self._close_application
        )
        return False  # Remove from idle callbacks

    def _show_ostree_package_deployment_info_on_startup(self):
        """
        Show informational dialog about package deployment on ostree systems.
        This dialog is shown asynchronously on startup for ostree/ublue systems
        to inform users that packages are deployed on reboot.
        """
        if dev_mode.is_dev_mode_enabled():
            return False
    
        # Get system compatibility keys
        system_compat_keys = compat.get_system_compat_keys()

        # Only show on ostree-based systems
        if {"ostree", "ublue"} & system_compat_keys:
            # Use GLib.idle_add to ensure the dialog shows after the window is fully initialized
            GLib.idle_add(self._show_ostree_package_deployment_info)
        return False  # Remove from idle callbacks

    def _show_ostree_package_deployment_info(self):
        """
        Display the ostree package deployment info dialog.
        Called via GLib.idle_add to ensure proper timing.
        Non-blocking informational dialog.
        """
        reboot_helper.show_ostree_package_deployment_info_dialog(
            self, self.translations
        )
        return False  # Remove from idle callbacks

    def _check_deepin_immutability_on_startup(self):
        """
        Check if Deepin immutability permission needs to be requested on first run.
        This is called asynchronously during startup via GLib.idle_add.
        """
        if dev_mode.is_dev_mode_enabled():
            return False
    
        try:
            reboot_required = deepin_immutable_helper.check_and_handle_deepin_immutability(
                self, self.translations
            )
            if reboot_required:
                logger.info("Deepin immutability was enabled, marking reboot as required")
                self.reboot_required = True
        except Exception as e:
            logger.error(f"Error checking Deepin immutability: {e}")
        return False  # Remove from idle callbacks

    def _set_window_icon(self):
        """
        Set the window icon for proper GNOME desktop integration.
        This ensures the icon appears correctly in the taskbar and window manager.
        Uses async loading to prevent blocking on Hyprland.
        """

        def load_icon_async():
            """Load icon in background thread to prevent blocking."""
            try:
                # Try multiple icon locations in order of preference
                icon_paths = [
                    # System-wide installation paths
                    "/usr/share/icons/hicolor/scalable/apps/linuxtoys.svg",
                    "/usr/share/pixmaps/linuxtoys.svg",
                    # Development/local paths
                    get_icon_path("linuxtoys.svg"),
                    # Fallback to the icon in the source directory
                    os.path.join(
                        os.path.dirname(__file__), "..", "..", "src", "linuxtoys.svg"
                    ),
                    # Relative path from the script location
                    os.path.join(
                        os.path.dirname(__file__),
                        "..",
                        "..",
                        "..",
                        "src",
                        "linuxtoys.svg",
                    ),
                ]

                icon_set = False
                for icon_path in icon_paths:
                    if icon_path and os.path.exists(icon_path):
                        try:
                            # Set window icon from file using GLib.idle_add for thread safety
                            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
                            GLib.idle_add(lambda: self.set_icon(pixbuf))
                            icon_set = True
                            break
                        except Exception:
                            # Continue to next path if this one fails
                            continue

                # If no file-based icon worked, try setting icon name for theme integration
                if not icon_set:
                    GLib.idle_add(lambda: self.set_icon_name("linuxtoys"))

            except Exception:
                # Fallback: set a generic icon if all else fails
                try:
                    GLib.idle_add(
                        lambda: self.set_icon_name("application-x-executable")
                    )
                except Exception:
                    pass  # If even this fails, just continue without an icon

        # Load icon asynchronously to prevent blocking on window manager issues
        import threading

        threading.Thread(target=load_icon_async, daemon=True).start()

    def _set_window_icon_from_file(self, icon_path):
        """Set window icon from file with fallback to theme icon on error."""
        def _apply():
            try:
                if not hasattr(self, 'get_window') or not self.get_window():
                    return
                if icon_path and os.path.exists(icon_path):
                    self.set_icon_from_file(icon_path)
                else:
                    self.set_icon_name("application-x-executable")
            except Exception:
                try:
                    self.set_icon_name("application-x-executable")
                except Exception:
                    pass
        GLib.idle_add(_apply)

    def _set_tooltips_enabled(self, enabled):
        # Categories
        for flowbox_child in self.categories_flowbox.get_children():
            widget = flowbox_child.get_child()
            widget.set_has_tooltip(enabled)
            if enabled:
                description = getattr(widget, "info", {}).get("description", "")
                if description:
                    widget.set_tooltip_text(description)
                else:
                    widget.set_tooltip_text(None)
            else:
                widget.set_tooltip_text(None)
        # Scripts
        for flowbox_child in self.scripts_flowbox.get_children():
            widget = flowbox_child.get_child()
            widget.set_has_tooltip(enabled)
            if enabled:
                description = getattr(widget, "info", {}).get("description", "")
                if description:
                    widget.set_tooltip_text(description)
                else:
                    widget.set_tooltip_text(None)
            else:
                widget.set_tooltip_text(None)

    def _on_focus_in(self, *args):
        self._set_tooltips_enabled(True)

    def _on_focus_out(self, *args):
        self._set_tooltips_enabled(False)

    def _on_toggled_check(self, button):
        if button.get_active():
            if button not in self.check_buttons:
                self.check_buttons.append(button)
        else:
            if button in self.check_buttons:
                self.check_buttons.remove(button)

        self.reveal.button_box.show_all()
        self.reveal.support.hide()
        self.reveal.set_reveal_child(len(self.check_buttons) >= 2)

    def _render_categories(self, categories):
        """Render an already parsed category snapshot on the GTK thread."""
        # Store current category info and temporarily set to None for proper bold formatting.
        temp_current_category = self.current_category_info
        self.current_category_info = None

        self.categories_flowbox.foreach(
            lambda widget: self.categories_flowbox.remove(widget)
        )
        for cat in categories:
            widget = self.create_item_widget(cat)
            description = cat.get("description", "")
            widget.set_tooltip_text(description or None)
            self.categories_flowbox.add(widget)

        self.current_category_info = temp_current_category
        self.categories_flowbox.show_all()

    def load_categories(self):
        """Load categories synchronously for explicit refresh/fallback paths."""
        # A progressive population may already have parsed the root category list
        # even though the recursive cache is not complete yet. Reuse it when present.
        categories = self.category_cache.get_categories()
        if not categories:
            categories = parser.get_categories(self.translations)
        self._render_categories(categories)

    def _load_scripts_into_flowbox(self, flowbox, category_info, defer_initial=False):
        """
        Populate a category without blocking navigation on every card.

        Navigation may defer the entire lookup/construction pass until after the
        Gtk.Stack slide completes. This is important for cache misses and nested
        categories too: even parser work should not compete with the transition.
        """
        if defer_initial:
            scheduled_generation = (
                getattr(flowbox, "_linuxtoys_population_generation", 0) + 1
            )
            flowbox._linuxtoys_population_generation = scheduled_generation
            transition_delay = max(1, int(self.main_stack.get_transition_duration()))

            def populate_after_transition():
                if (
                    getattr(flowbox, "_linuxtoys_population_generation", None)
                    != scheduled_generation
                ):
                    return False
                self._load_scripts_into_flowbox(
                    flowbox,
                    category_info,
                    defer_initial=False,
                )
                return False

            GLib.timeout_add(
                transition_delay,
                populate_after_transition,
                priority=GLib.PRIORITY_LOW,
            )
            return
        for child in flowbox.get_children():
            flowbox.remove(child)

        # Invalidate an older deferred population targeting this same FlowBox.
        generation = getattr(flowbox, "_linuxtoys_population_generation", 0) + 1
        flowbox._linuxtoys_population_generation = generation

        category_path = category_info["path"]

        if self.category_cache.is_populated:
            scripts = self.category_cache.get_scripts_for_category(category_path)
            if not scripts:
                scripts = parser.get_scripts_for_category(
                    category_path, self.translations
                )
        else:
            scripts = parser.get_scripts_for_category(
                category_path, self.translations
            )

        checklist_mode = category_info.get("display_mode", "menu") == "checklist"
        allow_drag = self._is_local_scripts_category(category_info)

        # Around three rows at the normal five-column layout. This bounds the
        # click-to-first-frame work independently of category size.
        initial_batch_size = 10
        # Keep FlowBox mutation frame-sized after the first screenful. Two cards
        # per frame avoids the ten-widget layout bursts that made large categories
        # visibly hitch while still filling them at roughly 120 cards/second.
        frame_batch_size = 2

        def add_card(script_info):
            widget = self.create_item_widget(
                script_info,
                checklist=checklist_mode,
                allow_drag=allow_drag,
            )
            description = script_info.get("description", "")
            widget.set_tooltip_text(description or None)
            # Opacity must be zero before the widget becomes visible; otherwise
            # GTK may paint one fully-opaque frame before the fade scheduler runs.
            widget.set_opacity(0.0)
            flowbox.add(widget)
            return widget

        initial_count = min(len(scripts), initial_batch_size)
        remaining = iter(scripts[initial_count:])
        frame_interval_ms = 16

        def populate_timed_batch():
            if (
                getattr(flowbox, "_linuxtoys_population_generation", None)
                != generation
            ):
                return False

            added = 0
            batch_widgets = []
            exhausted = False
            while added < frame_batch_size:
                try:
                    script_info = next(remaining)
                except StopIteration:
                    exhausted = True
                    break

                widget = add_card(script_info)
                widget.show_all()
                batch_widgets.append(widget)
                added += 1

            self.animate_item_batch(
                batch_widgets,
                duration_ms=110,
                stagger_ms=5,
            )
            return not exhausted

        def populate_initial_batch():
            if (
                getattr(flowbox, "_linuxtoys_population_generation", None)
                != generation
            ):
                return False

            initial_widgets = []
            for script_info in scripts[:initial_count]:
                widget = add_card(script_info)
                widget.show_all()
                initial_widgets.append(widget)

            self.animate_item_batch(
                initial_widgets,
                duration_ms=120,
                stagger_ms=8,
            )

            self._configure_local_scripts_interaction(flowbox, category_info)
            if checklist_mode:
                self.reveal.set_reveal_child(len(self.check_buttons) >= 2)

            if initial_count < len(scripts):
                GLib.timeout_add(
                    frame_interval_ms,
                    populate_timed_batch,
                    priority=GLib.PRIORITY_LOW,
                )
            return False

        populate_initial_batch()

    def load_scripts(self, category_info):
        """Loads scripts for a category and connects their click event. Supports checklist mode."""
        self._load_scripts_into_flowbox(self.scripts_flowbox, category_info)
        self.scripts_flowbox.show_all()

    def on_install_checklist(self, button):
        """Run checked scripts sequentially."""
        # Check if reboot is required before proceeding
        if self.reboot_required:
            if not self._show_reboot_warning_dialog():
                return

        selected_scripts = [
            sh.script_info for sh in self.check_buttons if sh.get_active()
        ]
        if not selected_scripts:
            return

        for cb in self.check_buttons[:]:
            cb.set_active(False)

        deps = asyncio.run(self._process_needed_scripts(selected_scripts))

        self.open_term_view(deps, auto_run=True)

    def on_cancel_checklist(self, button):
        """Uncheck all boxes, remove checklist buttons from footer, and return to previous view."""
        for cb in self.check_buttons[:]:
            cb.set_active(False)

        # Use back button logic to go to the appropriate previous view
        self.on_back_button_clicked(None)

    async def _process_needed_scripts(self, script_infos):
        deps = []
        for info in script_infos:
            required_scripts = []

            if has_depends := info.get("needed"):
                tasks = [
                    manifest_helper.find_script_by_name_async(_d, self.translations)
                    for _d in has_depends
                ]
                res = await asyncio.gather(*tasks)
                required_scripts = [r for r in res if r]

                # Show dialog asking for confirmation to install required features
                if required_scripts:
                    script_name = info.get("name", "Script")
                    confirmed = needed_helper.show_needed_requirements_dialog(
                        self, self.translations, script_name, required_scripts
                    )

                    if not confirmed:
                        return []

            for required in required_scripts:
                if required.get("is_repo_entry"):
                    required = repo_parser.materialize_repo_script(required)
                deps.append(required)

            if info.get("is_repo_entry"):
                info = repo_parser.materialize_repo_script(info)

            deps.append(info)

        return deps

    def show_external_install_error(self, message):
        """Show a safe user-facing error for an external URI request."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=self.translations.get(
                "uri_install_error_title", "Unable to open LinuxToys link"
            ),
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def handle_external_install_request(self, target_id):
        """Resolve a browser-requested installation by stable ID.

        Repository entries that expose an app page follow the same individual-
        activation flow as an in-app click. Entries without an app page retain
        the explicit external-request confirmation before execution.
        """
        if self.reboot_required and not self._show_reboot_warning_dialog():
            return

        script_info = manifest_helper.find_script_by_id(target_id, self.translations)
        if script_info is None:
            self.show_external_install_error(
                self.translations.get(
                    "uri_install_not_found",
                    "The requested feature was not found or is not compatible with this system.",
                )
            )
            return

        # URI activation represents an individual app activation, so repository
        # entries with app-page metadata must show that page first. The page's
        # Install button then continues through the normal app-page install flow.
        if script_info.get("is_repo_entry") and script_info.get("has_app_page"):
            self.open_app_page(script_info)
            return

        deps = asyncio.run(self._process_needed_scripts([script_info]))
        if not deps:
            return

        # External requests without an app page always require explicit in-app
        # confirmation, even when the feature was previously executed.
        if not needed_helper.show_run_confirmation_dialog(
            self, self.translations, deps, external_request=True
        ):
            return

        removable = script_info if len(deps) == 1 else None
        self.open_term_view(
            deps,
            removable_script_info=removable,
            auto_run=True,
        )

    def _run_single_script_install(self, info, close_app_page=False):
        """Run the normal single-entry confirmation and terminal-view flow."""
        deps = asyncio.run(self._process_needed_scripts([info]))
        if not deps:
            return

        script_name = info.get("name", "")
        registry_data = action_registry.parse_registry_file()
        is_first_run = script_name not in registry_data

        if is_first_run:
            confirmed = needed_helper.show_run_confirmation_dialog(
                self, self.translations, deps
            )
        else:
            # Preserve the existing easy re-run/report/uninstall behavior.
            confirmed = True

        if not confirmed:
            return

        if close_app_page:
            self.close_app_page_for_install()

        removable = info if len(deps) == 1 else None
        self.open_term_view(deps, removable_script_info=removable, auto_run=True)

    def _install_from_app_page(self, info):
        """Install an entry after the user chooses Install on its app page."""
        if self.reboot_required and not self._show_reboot_warning_dialog():
            return
        self._run_single_script_install(info, close_app_page=True)

    def on_script_clicked(self, widget, event):
        """Handle an individual script/app activation."""
        if self.reboot_required:
            if not self._show_reboot_warning_dialog():
                return

        info = widget.info

        if info.get("is_create_script"):
            self._handle_create_new_script()
            return

        script_path = info.get("path", "")
        if script_path.endswith("skills-seeker.sh") or info.get("name") == "Skills Seeker":
            self.open_skills_seeker_view()
            return

        # App pages apply only to individual activation. Checklist batch execution
        # continues to use on_install_checklist() and therefore bypasses this branch.
        if info.get("is_repo_entry") and info.get("has_app_page"):
            self.open_app_page(info)
            return

        self._run_single_script_install(info)

    def _install_skill_from_seeker(self, source, slug, agent):
        tmp_dir = "/tmp/linuxtoys"
        os.makedirs(tmp_dir, exist_ok=True)
        safe_source = source.replace("/", "_")
        tmp_script = os.path.join(tmp_dir, f"skill_install_{safe_source}_{slug}.sh")
        script_content = f"""#!/bin/bash
# name: Install Skill {slug}
# description: Install skill {source} for agent {agent}
source "$SCRIPT_DIR/libs/linuxtoys.bash"
_lang_
pkg_npm npm
npx skills add "{source}" -a "{agent}" -g -y --skill "{slug}"
"""
        with open(tmp_script, "w") as f:
            f.write(script_content)
        os.chmod(tmp_script, 0o755)

        script_info = {
            "name": f"Install {slug}",
            "path": tmp_script,
            "icon": "emblem-system-symbolic",
            "description": f"Install skill {source}/{slug} for {agent}",
        }
        self.open_term_view([script_info], removable_script_info=script_info, auto_run=True)

    def _show_reboot_warning_dialog(self):
        """Shows a dialog warning that a reboot is required before continuing.

        Returns:
            bool: True if the action may proceed (user chose to continue
                  without rebooting), False if it should remain blocked.
        """
        proceed = not reboot_helper.handle_reboot_requirement(
            self, self.translations, self._close_application
        )
        if proceed:
            # User opted to continue without rebooting; no longer block this session
            self.reboot_required = False
        return proceed

    def _show_cancel_script_warning_dialog(self):
        """
        Shows a confirmation dialog warning that cancelling will stop the running script.

        Returns:
            bool: True if user confirmed to cancel, False if user chose to continue
        """
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self.translations.get("cancel_script_title", "Cancel Running Script?"),
        )

        dialog.format_secondary_text(
            self.translations.get(
                "cancel_script_message",
                "A script is currently running. If you go back now, the running task will be cancelled. Are you sure you want to cancel?",
            )
        )

        # Add buttons
        dialog.add_button(
            self.translations.get("cancel_script_continue_btn", "Continue Running"),
            Gtk.ResponseType.NO,
        )
        dialog.add_button(
            self.translations.get("cancel_script_cancel_btn", "Cancel Script"),
            Gtk.ResponseType.YES,
        )

        # Set focus to the "Continue Running" button (safer default)
        dialog.set_default_response(Gtk.ResponseType.NO)

        response = dialog.run()
        dialog.destroy()

        # Return True if user clicked "Cancel Script" (YES), False otherwise
        return response == Gtk.ResponseType.YES

    def _close_application(self):
        """Closes the application gracefully and performs cleanup."""
        # Clean up temporary directory
        tmp_linuxtoys_path = "/tmp/linuxtoys"
        try:
            if os.path.exists(tmp_linuxtoys_path):
                shutil.rmtree(tmp_linuxtoys_path)
                print(f"Cleaned up temporary directory: {tmp_linuxtoys_path}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary directory {tmp_linuxtoys_path}: {e}")
        
        self.get_application().quit()

    def on_language_changed(self, new_language_code):
        """Handle language change by reloading translations and updating UI"""
        from . import lang_utils

        # Load new translations
        self.translations = lang_utils.load_translations(new_language_code)

        # Swap in fresh parser-backed caches and rebuild them together.  Avoid
        # SearchEngine.update_translations() here because it starts its own full
        # filesystem scan, duplicating the category/featured refresh.
        self.search_engine.translations = self.translations
        self.script_cache = search_helper.ScriptCache()
        self.category_cache = search_helper.CategoryCache()
        self.search_engine.set_cache(self.script_cache)
        self.all_scripts = []
        self._populate_runtime_caches()

        # Update search entry placeholder text
        self.search_entry.set_placeholder_text(
            self.translations.get("search_placeholder", "Search features")
        )
        
        # Update random scripts label
        if self.random_scripts_label:
            featured_label = self.translations.get("featured_scripts", "Try These")
            self.random_scripts_label.set_markup(f"<big><b>{featured_label}</b></big>")

        # Refresh the UI with new translations
        self._refresh_ui_with_new_translations()

    def _refresh_ui_with_new_translations(self):
        """Refresh all UI elements with new translations"""
        # Hidden retained category views contain already-rendered translated
        # labels/tooltips. Drop them so Back never resurrects the old locale.
        self._discard_retained_category_views()

        # Update header
        self._update_header(self.current_category_info)

        # Update title bar
        if self.current_category_info:
            category_name = self.current_category_info.get("name", "Unknown")
            self.header_bar.props.title = f"LinuxToys: {category_name}"
        else:
            self.header_bar.props.title = "LinuxToys"

        # Refresh the dropdown menu with new translations
        if hasattr(self, "menu_button"):
            self.menu_button.refresh_menu_translations()

        # Always reload categories with new translations (so they're ready when user navigates back)
        self.load_categories()

        # Refresh footer translations
        self.reveal.update_translations(self.translations)

        # If the Skills Seeker is active, recreate it with the new translations
        if self.main_stack.get_visible_child_name() == "skills_seeker":
            existing = self.main_stack.get_child_by_name("skills_seeker")
            if existing is not None:
                new_view = skills_view.SkillsSeekerView(
                    self.translations,
                    on_install_callback=self._install_skill_from_seeker,
                )
                self.main_stack.remove(existing)
                self.main_stack.add_named(new_view, "skills_seeker")
                self.scripts_view = new_view
                self.scripts_flowbox = new_view.get_flowbox()
                self.header_bar.props.title = self.translations.get(
                    "skills_seeker_desc", "Skills"
                )
                icon_path = get_icon_path("skill.svg")
                self._set_window_icon_from_file(icon_path)
                self.search_entry.set_placeholder_text(
                    self.translations.get("skills_search_placeholder", "Search skills...")
                )
                self._search_entry_prev_placeholder = self.translations.get(
                    "search_placeholder", "Search features"
                )
                new_view.show_all()
                self.header_widget.hide()
                self.main_stack.set_visible_child_name("skills_seeker")
            return

        # If we're currently viewing categories, we're done since load_categories() already updated the view
        if self.main_stack.get_visible_child_name() == "categories":
            return

        # If we're in a category/subcategory view, reload it with new translations
        if self.current_category_info:
            # Update navigation stack with fresh translations
            self._refresh_navigation_stack_translations()

            # Get fresh category info with new translations
            updated_category_info = self._get_fresh_category_info_with_translations()
            if updated_category_info:
                self.current_category_info = updated_category_info
                # Update header with fresh category info
                self._update_header(self.current_category_info)
                # Update title bar with fresh category name
                category_name = self.current_category_info.get("name", "Unknown")
                self.header_bar.props.title = f"LinuxToys: {category_name}"

            # Reload the scripts view with new translations
            self.load_scripts(self.current_category_info)

        # Update footer if in checklist mode
        if (
            self.current_category_info
            and self.current_category_info.get("display_mode", "menu") == "checklist"
        ):
            self.reveal.set_reveal_child(len(self.check_buttons) >= 2)

    def _get_fresh_category_info_with_translations(self):
        """Get fresh category info with updated translations"""
        if not self.current_category_info:
            return None

        current_path = self.current_category_info.get("path", "")
        if not current_path:
            return None

        from . import parser

        # Check if this is the Local Scripts directory
        if ".local/linuxtoys/scripts" in current_path:
            # Recreate Local Scripts category info with new translations
            local_scripts_name = self.translations.get(
                "local_scripts_name", "Local Scripts"
            )
            local_scripts_desc = self.translations.get(
                "local_scripts_desc", "Drop your scripts here"
            )

            return {
                "name": local_scripts_name,
                "description": local_scripts_desc,
                "icon": "local-script.svg",
                "mode": "auto",
                "path": current_path,
                "is_script": False,
                "is_subcategory": True,
                "has_subcategories": False,
                "display_mode": "menu",
            }

        # Check if this is a main category
        if current_path.startswith(parser.SCRIPTS_DIR):
            # Get all categories with new translations
            categories = parser.get_categories(self.translations)

            # Find matching category by path
            for category in categories:
                if category.get("path") == current_path:
                    return category

            # If not found in main categories, check subcategories
            # Get the parent directory to find subcategories
            import os

            parent_path = os.path.dirname(current_path)
            if parent_path and parent_path != current_path:
                subcategories = parser.get_subcategories_for_category(
                    parent_path, self.translations
                )
                for subcategory in subcategories:
                    if subcategory.get("path") == current_path:
                        return subcategory

        # If no match found, return the current info (fallback)
        return self.current_category_info

    def _refresh_navigation_stack_translations(self):
        """Refresh all category info in the navigation stack with new translations"""
        if not self.navigation_stack:
            return

        # Update each category in the navigation stack with fresh translations
        for i, category_info in enumerate(self.navigation_stack):
            current_path = category_info.get("path", "")
            if not current_path:
                continue

            from . import parser

            # Check if this is the Local Scripts directory
            if ".local/linuxtoys/scripts" in current_path:
                # Update Local Scripts category info with new translations
                local_scripts_name = self.translations.get(
                    "local_scripts_name", "Local Scripts"
                )
                local_scripts_desc = self.translations.get(
                    "local_scripts_desc", "Drop your scripts here"
                )

                self.navigation_stack[i] = {
                    "name": local_scripts_name,
                    "description": local_scripts_desc,
                    "icon": "local-script.svg",
                    "mode": "auto",
                    "path": current_path,
                    "is_script": False,
                    "is_subcategory": True,
                    "has_subcategories": False,
                    "display_mode": "menu",
                }
                continue

            # Check if this is a main category
            if current_path.startswith(parser.SCRIPTS_DIR):
                # Get all categories with new translations
                categories = parser.get_categories(self.translations)

                # Find matching category by path
                for category in categories:
                    if category.get("path") == current_path:
                        self.navigation_stack[i] = category
                        break
                else:
                    # If not found in main categories, check subcategories
                    import os

                    parent_path = os.path.dirname(current_path)
                    if parent_path and parent_path != current_path:
                        subcategories = parser.get_subcategories_for_category(
                            parent_path, self.translations
                        )
                        for subcategory in subcategories:
                            if subcategory.get("path") == current_path:
                                self.navigation_stack[i] = subcategory
                                break

    def _refresh_removable_scripts(self):
        """
        Refresh removable-script state and rebuild the currently visible cards.

        The removal button is created inside create_item_widget(), so refreshing
        only the boolean cache is insufficient: the displayed widgets must also
        be recreated.
        """
        if self.script_cache.is_populated:
            self.script_cache.refresh_removable_cache()

        # Refresh the current category/subcategory view.
        if self.current_category_info is not None:
            self._load_scripts_into_flowbox(
                self.scripts_flowbox,
                self.current_category_info,
            )
            self.scripts_flowbox.show_all()
        else:
            # Root-level scripts can also be removable.
            self.load_categories()