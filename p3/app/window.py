import asyncio
import json
import logging
import os
import shutil
import subprocess
import threading
import sys

from . import (
    action_registry,
    appstream_cache,
    appstream_parser,
    appstream_queue,
    appstream_runner,
    installed_features,
    installed_packages,
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
    uri_parser,
    git_scripts_manager,
    gtk_dialogs
)
from .gtk_common import Gdk, GLib, Gtk, GdkPixbuf
from gi.repository import Gio
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
        self._default_window_size = (920, 630)
        self._last_normal_window_size = self._default_window_size
        self.set_default_size(*self._default_window_size)
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
        self._appstream_cache_started = False
        self._installed_packages_refresh_started = False
        self._installed_packages_refresh_pending = False
        self._appstream_runner = appstream_runner.AppStreamRunner(self)

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
        # One debounce authority for all expensive application-level responsive
        # work. GTK may continue allocating live while the user drags the window;
        # LinuxToys only recalculates custom layouts after geometry settles.
        self._window_resize_settle_timer = None
        self._window_resize_pending = False
        self._window_resize_settling = False
        self._pending_window_size = self._default_window_size
        self._last_settled_window_size = None
        self._featured_last_count = None
        self._featured_swap_timer = None
        self._featured_hovered = False
        self._featured_last_layout = None
        self._featured_large_positions = set()
        self._featured_history = []
        self._featured_sensed_categories = []
        self._load_featured_sense()
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
        self._appstream_state = "hidden"
        # Only the bootstrap case blocks the main menu. Once both artifacts exist,
        # future AppStream refreshes remain fully background operations.
        self._appstream_pickle_missing_at_startup = (
            not appstream_parser.RUNTIME_CACHE_PATH.is_file()
        )
        self._appstream_initial_build_pending = (
            not appstream_cache.CATALOG_PATH.is_file()
            or self._appstream_pickle_missing_at_startup
        )
        self._categories_loading_hide_source = None
        self._categories_loading_hide_started_us = None
        self._categories_loading_watermarks_flushed = False
        self._categories_loading_fade_source = None
        self._categories_loading_fade_started_us = None
        self._categories_loading_fade_duration_ms = 220
        self._categories_startup_transition_complete = False

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

        # Shared background-status indicator. Automatic updater states have
        # priority; while the updater is idle/up-to-date, AppStream may borrow the
        # same indicator while its catalog is synchronizing.
        self.update_indicator = Gtk.Button()
        self.update_indicator.set_relief(Gtk.ReliefStyle.NONE)
        self.update_indicator.get_style_context().add_class("update-indicator")
        self.update_indicator.connect("clicked", self._on_update_indicator_clicked)
        self.header_bar.pack_end(self.update_indicator)
        self._refresh_status_indicator()

        # Installed features library. pack_end() ordering is right-to-left here,
        # so this sits immediately to the left of the shared LinuxToys state button.
        self.installed_features_button = Gtk.Button.new_from_icon_name(
            "view-list-symbolic", Gtk.IconSize.BUTTON
        )
        self.installed_features_button.set_relief(Gtk.ReliefStyle.NONE)
        self.installed_features_button.set_tooltip_text(
            self.translations.get("installed_features", "Installed Features")
        )
        self.installed_features_button.connect("clicked", self._open_installed_features)
        self.header_bar.pack_end(self.installed_features_button)

        # Session AppStream queue. It becomes part of the header only after the
        # persistent PTY has actually been requested for the first time.
        self.appstream_queue_button = Gtk.Button.new_from_icon_name(
            "folder-download-symbolic", Gtk.IconSize.BUTTON
        )
        self.appstream_queue_button.set_relief(Gtk.ReliefStyle.NONE)
        self.appstream_queue_button.get_style_context().add_class("appstream-queue-indicator")
        self.appstream_queue_button.set_tooltip_text("Application installation queue")
        self.appstream_queue_button.connect("clicked", self._open_appstream_queue)
        self.header_bar.pack_end(self.appstream_queue_button)
        self.appstream_queue_button.hide()

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
        # Featured needs true row-spanning cards, which Gtk.FlowBox cannot provide.
        # Keep the historical attribute name for compatibility with the Featured
        # controller, but back it with a homogeneous Gtk.Grid.
        self.random_scripts_flowbox = Gtk.Grid()
        self.random_scripts_flowbox.set_valign(Gtk.Align.START)
        self.random_scripts_flowbox.set_column_homogeneous(True)
        self.random_scripts_flowbox.set_row_homogeneous(True)
        # No margins here since the container already has them.
        self.random_scripts_flowbox.set_margin_left(0)
        self.random_scripts_flowbox.set_margin_top(0)
        self.random_scripts_flowbox.set_margin_right(0)
        self.random_scripts_flowbox.set_margin_bottom(0)
        # Gtk.FlowBox adds a small amount of visual breathing room around its
        # children through the FlowBoxChild wrapper. Featured uses Gtk.Grid so
        # cards can span rows, therefore compensate for that wrapper here to
        # make the *visible* card-to-card gaps match the main-menu FlowBoxes.
        self.random_scripts_flowbox.set_column_spacing(20)
        self.random_scripts_flowbox.set_row_spacing(18)

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
        # This page is horizontally responsive: category cards reflow and Featured
        # mirrors their effective column count. Never let an old natural width
        # become a horizontal scrollable area after a window resize/state change.
        self.categories_view.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC,
        )
        self.categories_view.add(categories_container)
        # Keep the real menu in the widget/layout tree so category allocations and
        # watermark rendering can complete behind the startup roller, but do not let
        # the unfinished menu flash on screen.
        self.categories_view.set_opacity(0.0)

        # The parser-backed menu is populated asynchronously. Keep the already-open
        # window visually responsive while the first usable category snapshot is
        # prepared instead of presenting an unexplained blank page.
        self.categories_loading_overlay = Gtk.Overlay()
        self.categories_loading_overlay.add(self.categories_view)

        self.categories_loading_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )
        self.categories_loading_box.set_halign(Gtk.Align.CENTER)
        self.categories_loading_box.set_valign(Gtk.Align.CENTER)

        self.categories_loading_spinner = Gtk.Spinner()
        self.categories_loading_spinner.set_size_request(64, 64)
        self.categories_loading_spinner.start()
        self.categories_loading_box.pack_start(
            self.categories_loading_spinner, False, False, 0
        )

        self.categories_loading_label = Gtk.Label()
        loading_text = self.translations.get(
            "appstream_initial_building",
            "Building initial AppStream catalog.\nThis may take a few seconds...",
        )
        self.categories_loading_label.set_markup(
            f'<span weight="bold" size="large">{GLib.markup_escape_text(loading_text)}</span>'
        )
        self.categories_loading_label.set_line_wrap(True)
        self.categories_loading_label.set_justify(Gtk.Justification.CENTER)
        self.categories_loading_label.set_max_width_chars(56)
        # The window calls show_all() later during startup. Without no-show-all,
        # that recursively makes this label visible again even when the pickle
        # already existed and set_visible(False) was used here.
        self.categories_loading_label.set_no_show_all(True)
        self.categories_loading_box.pack_start(
            self.categories_loading_label, False, False, 0
        )

        self.categories_loading_overlay.add_overlay(self.categories_loading_box)
        self.main_stack.add_named(self.categories_loading_overlay, "categories")

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

        # --- Restore and show the Window ---
        self._restore_window_state()
        self.connect("configure-event", self._on_window_configure)
        self.connect("window-state-event", self._on_window_state_changed)
        self.show_all()

        # no-show-all keeps the first-run message out of recursive show_all().
        # Explicitly restore its intended startup state afterwards.
        if self._appstream_pickle_missing_at_startup:
            self.categories_loading_label.show()
        else:
            self.categories_loading_label.hide()

        # show_all() recursively reveals header children, including the queue
        # button that was intentionally hidden when it was created. Re-apply
        # queue visibility from the actual session queue after the initial show.
        self._on_appstream_queue_changed()
        self.show_categories_view()  # Call this after show_all to ensure proper visibility state

        # Connect focus events to enable/disable tooltips
        self.connect("focus-in-event", self._on_focus_in)
        self.connect("focus-out-event", self._on_focus_out)

        self.connect("key-press-event", self._on_key_press)
        self.connect("delete-event", self._on_close_requested)

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
        GLib.idle_add(self._refresh_installed_packages_async)
        GLib.idle_add(self._show_ostree_package_deployment_info_on_startup)
        GLib.idle_add(self._check_updates)
        GLib.idle_add(self._start_file_watcher)
        GLib.idle_add(self._check_deepin_immutability_on_startup)
        GLib.idle_add(self._start_startup_recommendation_check)

    def _startup_recommendations_suppressed(self):
        marker = os.path.join(
            compat.get_linuxtoys_cache_dir(), "startup-recommendations-dismissed"
        )
        return os.path.isfile(marker)

    def _suppress_startup_recommendations(self):
        marker = os.path.join(
            compat.get_linuxtoys_cache_dir(), "startup-recommendations-dismissed"
        )
        try:
            os.makedirs(os.path.dirname(marker), exist_ok=True)
            with open(marker, "w", encoding="utf-8") as handle:
                handle.write("1\n")
        except OSError as exc:
            logger.warning("Could not save startup recommendation preference: %s", exc)

    @staticmethod
    def _command_succeeds(command):
        try:
            return subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
                check=False,
            ).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _detect_startup_recommendations(self):
        """Return optional repository/setup scripts useful on this host."""
        keys = compat.get_system_compat_keys()
        recommendations = []

        # Match flathub.sh: !solus, !ostree, systemd: yes. Recommend it when
        # Flatpak itself is absent or neither user nor system scope has Flathub.
        if (
            not compat.is_containerized()
            and "solus" not in keys
            and "ostree" not in keys
            and "systemd" in keys
        ):
            flatpak = shutil.which("flatpak")
            flathub_ready = False
            if flatpak:
                for scope in ("--user", "--system"):
                    try:
                        result = subprocess.run(
                            [flatpak, scope, "remotes", "--columns=name"],
                            capture_output=True,
                            text=True,
                            timeout=8,
                            check=False,
                        )
                    except (OSError, subprocess.SubprocessError):
                        continue
                    if result.returncode == 0 and "flathub" in {
                        line.strip() for line in result.stdout.splitlines()
                    }:
                        flathub_ready = True
                        break
            if not flatpak or not flathub_ready:
                recommendations.append("flathub")

        # The startup recommendation is intentionally Fedora-only even though the
        # standalone RPM Fusion script also supports other compatibility classes.
        if "fedora" in keys:
            if not (
                self._command_succeeds(["rpm", "-q", "rpmfusion-free-release"])
                and self._command_succeeds(["rpm", "-q", "rpmfusion-nonfree-release"])
            ):
                recommendations.append("rpmfusion")

        if "arch" in keys:
            if not self._command_succeeds(["pacman", "-Slq", "multilib"]):
                recommendations.append("multilib")

        return recommendations

    def _start_startup_recommendation_check(self):
        if self._startup_recommendations_suppressed():
            return False

        def worker():
            recommendations = self._detect_startup_recommendations()
            if recommendations:
                GLib.idle_add(self._show_startup_recommendations, recommendations)

        threading.Thread(
            target=worker,
            daemon=True,
            name="linuxtoys-startup-recommendations",
        ).start()
        return False

    def _show_startup_recommendations(self, recommendations):
        if self._startup_recommendations_suppressed():
            return False

        accepted, dont_remind = gtk_dialogs.run_startup_recommendations_dialog(
            self,
            self.translations,
            recommendations,
        )
        if dont_remind:
            self._suppress_startup_recommendations()

        if not accepted:
            return False

        async def resolve():
            resolved = []
            for script_id in recommendations:
                info = await manifest_helper.find_script_by_name_async(
                    script_id, self.translations
                )
                if info is not None:
                    resolved.append(info)
            return resolved

        script_infos = asyncio.run(resolve())
        if len(script_infos) != len(recommendations):
            missing = len(recommendations) - len(script_infos)
            logger.warning("Could not resolve %d startup recommendation(s)", missing)

        if not script_infos:
            return False

        deps = asyncio.run(self._process_needed_scripts(script_infos))
        if deps:
            # open_term_view already executes a list sequentially, which gives the
            # combined Flathub+RPM Fusion / Flathub+Multilib cases one chain.
            self.open_term_view(deps, auto_run=True)
        return False

    def _set_appstream_state(self, state):
        """Record AppStream state and refresh the shared header indicator."""
        self._appstream_state = state
        return self._refresh_status_indicator()

    def _start_appstream_cache(self):
        """Refresh AppStream metadata after the first usable UI is queued."""
        if self._appstream_cache_started:
            return False
        self._appstream_cache_started = True
        def report_state(state):
            GLib.idle_add(self._set_appstream_state, state)

        def worker():
            initial_build = self._appstream_initial_build_pending
            result = appstream_cache.refresh_cache(status_callback=report_state)
            if not result.get("success"):
                logger.warning(
                    "AppStream catalog refresh failed: %s",
                    result.get("error", "unknown error"),
                )
                if initial_build:
                    # Never strand a first launch behind the roller. LinuxToys can
                    # still operate with curated entries and retry AppStream later.
                    GLib.idle_add(self._finish_initial_appstream_build, False, False)
                return

            changed = bool(result.get("changed"))
            prepared = True

            # A first launch must have the derived pickle before the menu is
            # revealed, even if a catalog happened to appear before this worker ran.
            # For later refreshes, prewarm only when a new catalog was published.
            if initial_build or changed:
                prepared = appstream_parser.prepare_runtime_cache()
                if not prepared:
                    logger.warning(
                        "Could not prewarm AppStream runtime cache; "
                        "the normal parser path will rebuild it."
                    )

            if initial_build:
                GLib.idle_add(
                    self._finish_initial_appstream_build,
                    changed,
                    prepared,
                )
            elif changed:
                GLib.idle_add(self._apply_appstream_catalog)

        threading.Thread(
            target=worker,
            daemon=True,
            name="linuxtoys-appstream-cache",
        ).start()
        return False

    def _finish_initial_appstream_build(self, catalog_changed, prepared):
        """Release first-run startup after AppStream catalog/pickle preparation."""
        self._appstream_initial_build_pending = False
        if hasattr(self, "categories_loading_label"):
            self.categories_loading_label.hide()

        if catalog_changed:
            # Rebuild parser/UI caches against the newly published catalog. The
            # ordinary startup loading gate will then wait for the final category
            # watermarks before revealing the menu.
            return self._apply_appstream_catalog()

        # If the catalog was already current, preparation only needed to create the
        # missing derived pickle. The existing in-memory UI data is already valid.
        # If preparation failed, release startup anyway rather than trapping the UI.
        self._hide_categories_loading_indicator()
        return False

    def _apply_appstream_catalog(self):
        """Publish a newly completed AppStream catalog through normal UI caches."""
        appstream_parser.clear_runtime_cache()
        self._discard_retained_category_views()

        # Replace rather than invalidate in place: an older parser worker can then
        # finish harmlessly while generation guards prevent it from publishing.
        self.script_cache = search_helper.ScriptCache()
        self.category_cache = search_helper.CategoryCache()
        self.search_engine.set_cache(self.script_cache)
        self.all_scripts = []

        self.load_categories()
        if self.current_category_info is not None:
            self.load_scripts(self.current_category_info)

        self._populate_runtime_caches()

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
            self._hide_categories_loading_indicator()
            self.all_scripts = featured
            if (
                self.should_start_random_timer
                and featured
                and self._categories_startup_transition_complete
            ):
                self._deferred_start_random_scripts_refresh_timer()
            return False

        def top_level_ready(categories, scripts_by_category):
            # Runs in the parser worker. Only prepare immutable-ish Python snapshots
            # here; all GTK work is handed back to the main loop.
            if self.category_cache is not category_cache:
                return

            featured = collect_featured(categories, scripts_by_category)
            GLib.idle_add(publish_bootstrap, categories, featured)
            # AppStream is supplemental. Do not let even its freshness check/catalog
            # decode contend with the parser before the first usable UI is queued.
            GLib.idle_add(self._start_appstream_cache)

            # Network/git work is lower startup priority than getting the first
            # usable Featured pool ready, but need not wait for recursive caches.
            schedule_git_sync()

        def publish_full_featured(featured):
            if self.category_cache is not category_cache:
                return False
            self.all_scripts = featured
            if (
                self.should_start_random_timer
                and featured
                and self._categories_startup_transition_complete
            ):
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
                GLib.idle_add(self._refresh_installed_features_view)
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

    def _refresh_status_indicator(self):
        """Render updater/AppStream state through the single header indicator.

        Active updater states always win. The passive up-to-date/disabled states
        yield to an AppStream synchronization or failure; once AppStream reaches
        ready, the normal updater state becomes visible again.
        """
        if not hasattr(self, "update_indicator"):
            return False

        context = self.update_indicator.get_style_context()
        context.remove_class("suggested-action")
        context.remove_class("update-restart-ready")
        self.update_indicator.set_sensitive(False)

        # Updating LinuxToys itself is always the highest-priority information.
        updater_active = self._update_state in (
            "checking",
            "updating",
            "restart-ready",
            "error",
        )

        if updater_active:
            state = self._update_state
            source = "updater"
        elif self._appstream_state in ("building", "failed"):
            state = self._appstream_state
            source = "appstream"
        else:
            state = self._update_state
            source = "updater"

        if source == "appstream":
            if state == "building":
                spinner = Gtk.Spinner()
                spinner.start()
                image = spinner
                tooltip = self.translations.get(
                    "appstream_status_building",
                    "Building application catalog…",
                )
            else:
                image = Gtk.Image.new_from_icon_name(
                    "dialog-warning-symbolic", Gtk.IconSize.BUTTON
                )
                tooltip = self.translations.get(
                    "appstream_status_failed",
                    "Application catalog refresh failed. The previous catalog will be used.",
                )
        else:
            if state == "disabled":
                self.update_indicator.hide()
                return False
            if state == "checking":
                image = Gtk.Image.new_from_icon_name(
                    "view-refresh-symbolic", Gtk.IconSize.BUTTON
                )
                tooltip = self._tr_update(
                    "update_status_checking", "Checking for updates…"
                )
            elif state == "up-to-date":
                image = Gtk.Image.new_from_icon_name(
                    "emblem-ok-symbolic", Gtk.IconSize.BUTTON
                )
                tooltip = self._tr_update(
                    "update_status_up_to_date", "LinuxToys is up to date."
                )
            elif state == "updating":
                spinner = Gtk.Spinner()
                spinner.start()
                image = spinner
                tooltip = self._tr_update(
                    "update_status_updating", "Updating LinuxToys…"
                )
            elif state == "restart-ready":
                image = Gtk.Image.new_from_icon_name(
                    "software-update-available-symbolic", Gtk.IconSize.BUTTON
                )
                tooltip = self._tr_update(
                    "update_status_restart", "Update installed. Restart LinuxToys."
                )
                self.update_indicator.set_sensitive(True)
                context.add_class("suggested-action")
                context.add_class("update-restart-ready")
            else:
                image = Gtk.Image.new_from_icon_name(
                    "dialog-warning-symbolic", Gtk.IconSize.BUTTON
                )
                tooltip = self._tr_update(
                    "update_status_failed", "Automatic update failed."
                )

        self.update_indicator.set_image(image)
        self.update_indicator.set_tooltip_text(tooltip)
        self.update_indicator.show_all()
        return False

    def _set_update_state(self, state):
        """Record updater state and refresh the shared header indicator."""
        self._update_state = state
        return self._refresh_status_indicator()

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

    def _refresh_installed_packages_async(self, force=False):
        """Refresh observed native/Flatpak installations without blocking GTK."""
        if self._installed_packages_refresh_started:
            if force:
                self._installed_packages_refresh_pending = True
            return False
        self._installed_packages_refresh_started = True
        self._installed_packages_refresh_pending = False

        def worker():
            try:
                installed_packages.refresh()
            except Exception as exc:
                logger.warning("Installed package refresh failed: %s", exc)
            finally:
                self._installed_packages_refresh_started = False
                rerun = self._installed_packages_refresh_pending
                self._installed_packages_refresh_pending = False
                GLib.idle_add(self._on_installed_packages_changed)
                if rerun:
                    GLib.idle_add(self._refresh_installed_packages_async, True)

        threading.Thread(
            target=worker, daemon=True, name="linuxtoys-installed-packages"
        ).start()
        return False

    def _refresh_installed_features_view(self):
        view = self.main_stack.get_child_by_name("installed_features")
        if view is not None and hasattr(view, "refresh"):
            view.refresh()
        return False

    def _on_installed_packages_changed(self):
        # Observed AppStream state participates in ScriptCache removability.
        if self.script_cache.is_populated:
            self.script_cache.refresh_removable_cache()

        app_page = self.main_stack.get_child_by_name("app_page")
        if app_page is not None and hasattr(app_page, "refresh_install_state"):
            app_page.refresh_install_state()

        installed_view = self.main_stack.get_child_by_name("installed_features")
        if installed_view is not None and hasattr(installed_view, "refresh"):
            installed_view.refresh()
        return False

    def _appstream_registry_managed(self, info):
        registry_data = action_registry.parse_registry_file()
        candidates = (
            str(info.get("appstream_id", "") or "").strip(),
            str(info.get("name", "") or "").strip(),
            str(info.get("appstream_canonical_name", "") or "").strip(),
        )
        return any(candidate and candidate in registry_data for candidate in candidates)

    def _on_item_remove_clicked(self, button, info):
        """Use observed package state when AppStream was installed outside LinuxToys."""
        if not info.get("is_appstream_entry") or self._appstream_registry_managed(info):
            return ItemWidgetFactory._on_item_remove_clicked(self, button, info)

        observed = installed_packages.match(info)
        if observed is None:
            return ItemWidgetFactory._on_item_remove_clicked(self, button, info)

        remove_info = installed_packages.build_external_removal(
            info, observed, self.translations
        )
        if remove_info is None:
            return
        record_id = info.get("_appstream_queue_record_id")
        self._appstream_runner.enqueue_removal(info, remove_info, record_id=record_id)
        app_page = self.main_stack.get_child_by_name("app_page")
        if app_page is not None and hasattr(app_page, "refresh_install_state"):
            app_page.refresh_install_state()

    @staticmethod
    def _appstream_desktop_app(info):
        """Resolve an installed AppStream entry to a desktop application."""
        if not info or not info.get("is_appstream_entry"):
            return None
        desktop_id = str(info.get("appstream_launchable", "") or "").strip()
        if not desktop_id:
            return None
        try:
            return Gio.DesktopAppInfo.new(desktop_id)
        except (TypeError, AttributeError):
            return None

    def _can_launch_appstream_app(self, info):
        return self._appstream_desktop_app(info) is not None

    def _launch_appstream_app(self, info):
        """Launch an AppStream application's installed desktop entry."""
        app = self._appstream_desktop_app(info)
        if app is None:
            return False
        try:
            app.launch([], None)
            return True
        except GLib.Error as exc:
            logger.warning(
                "Unable to launch AppStream application %s: %s",
                info.get("appstream_id") or info.get("name") or "",
                exc,
            )
            return False

    def _get_appstream_install_state(self, info):
        """Resolve AppStream page state from this session first, then the registry."""
        appstream_id = str(info.get("appstream_id", "") or "").strip()
        if not appstream_id:
            return "available"

        session_state = self._appstream_runner.status_for_appstream_id(appstream_id)
        if session_state is not None:
            return session_state

        registry_data = action_registry.parse_registry_file()
        # appstream_id is the stable identity used by new background installs.
        # Keep display/canonical-name fallbacks for entries installed by older builds.
        registry_candidates = (
            appstream_id,
            str(info.get("name", "") or "").strip(),
            str(info.get("appstream_canonical_name", "") or "").strip(),
        )
        if any(candidate and candidate in registry_data for candidate in registry_candidates):
            return "installed"
        if installed_packages.match(info) is not None:
            return "installed"
        return "available"

    def _on_appstream_queue_changed(self):
        """Refresh the session queue button and the queue view, if visible."""
        records = self._appstream_runner.snapshot()

        # Always refresh the visible AppStream page before handling the empty
        # queue case. A successful removal retires its session record, so the
        # queue can become empty here; returning before this refresh would leave
        # the page stuck in the transient "removing" state. The resolver can
        # now fall through to the registry, where the reverted install
        # transaction has already been removed, and render the Install state.
        app_page = self.main_stack.get_child_by_name("app_page")
        if app_page is not None and hasattr(app_page, "refresh_install_state"):
            app_page.refresh_install_state()

        context = self.appstream_queue_button.get_style_context()
        if not records:
            context.remove_class("suggested-action")
            context.remove_class("appstream-queue-error")
            self.appstream_queue_button.hide()
            queue_view = self.main_stack.get_child_by_name("appstream_queue")
            if queue_view is not None and hasattr(queue_view, "refresh"):
                queue_view.refresh()
            return False

        self.appstream_queue_button.show_all()
        context.remove_class("suggested-action")
        context.remove_class("appstream-queue-error")

        active = any(record["status"] in ("queued", "running") for record in records)
        failed = any(record["status"] == "failed" for record in records)
        if active:
            context.add_class("suggested-action")
            self.appstream_queue_button.set_tooltip_text("Application installations in progress")
        elif failed:
            context.add_class("appstream-queue-error")
            self.appstream_queue_button.set_tooltip_text("One or more application installations failed")
        else:
            self.appstream_queue_button.set_tooltip_text("Application installation queue")

        queue_view = self.main_stack.get_child_by_name("appstream_queue")
        if queue_view is not None and hasattr(queue_view, "refresh"):
            queue_view.refresh()

        return False

    def _open_installed_features(self, _button=None):
        """Open the system-wide list of features LinuxToys can currently remove."""
        if self.main_stack.get_visible_child_name() == "installed_features":
            return

        old = self.main_stack.get_child_by_name("installed_features")
        if old is not None:
            self.main_stack.remove(old)
            old.destroy()

        # Installed Features and Queue are sibling utility views, not navigation
        # levels. Switching between them must preserve the original non-utility
        # origin instead of making one utility view the parent of the other.
        if self.main_stack.get_visible_child_name() == "appstream_queue":
            self._installed_features_prev = getattr(self, "_appstream_queue_prev", None)
        else:
            self._installed_features_prev = {
                "child": self.main_stack.get_visible_child(),
                "header_visible": self.header_widget.get_visible(),
                "title": self.header_bar.props.title,
                "footer_revealed": self.reveal.get_reveal_child(),
                "back_visible": self.back_button.get_visible(),
            }
        view = installed_features.InstalledFeaturesView(self)
        self.main_stack.add_named(view, "installed_features")
        view.show_all()
        self.header_widget.hide()
        self.reveal.set_reveal_child(False)
        self.back_button.show()
        title = self.translations.get("installed_features", "Installed Features")
        self.header_bar.props.title = f"LinuxToys: {title}"
        self.main_stack.set_visible_child_name("installed_features")

    def _open_appstream_queue(self, _button=None):
        """Open the session history/queue attached to the persistent AppStream PTY."""
        if self.main_stack.get_visible_child_name() == "appstream_queue":
            return

        old = self.main_stack.get_child_by_name("appstream_queue")
        if old is not None:
            self.main_stack.remove(old)
            old.destroy()

        # Installed Features and Queue are sibling utility views, not navigation
        # levels. Switching between them must preserve the original non-utility
        # origin instead of making one utility view the parent of the other.
        if self.main_stack.get_visible_child_name() == "installed_features":
            self._appstream_queue_prev = getattr(self, "_installed_features_prev", None)
        else:
            self._appstream_queue_prev = {
                "child": self.main_stack.get_visible_child(),
                "header_visible": self.header_widget.get_visible(),
                "title": self.header_bar.props.title,
                "footer_revealed": self.reveal.get_reveal_child(),
                "back_visible": self.back_button.get_visible(),
            }
        view = appstream_queue.AppStreamQueueView(self)
        self.main_stack.add_named(view, "appstream_queue")
        view.show_all()
        self.header_widget.hide()
        self.reveal.set_reveal_child(False)
        self.back_button.show()
        title = self.translations.get("installation_queue", "Installation Queue")
        self.header_bar.props.title = f"LinuxToys: {title}"
        self.main_stack.set_visible_child_name("appstream_queue")

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

    def _categories_watermarks_ready(self):
        """Return True once every rendered category watermark has a real pixbuf."""
        flowbox = getattr(self, "categories_flowbox", None)
        if flowbox is None or not flowbox.get_children():
            return False

        watermark_surfaces = []
        stack = [flowbox]
        while stack:
            widget = stack.pop()
            if hasattr(widget, "_linuxtoys_apply_pending_watermark"):
                watermark_surfaces.append(widget)
            try:
                stack.extend(widget.get_children())
            except (AttributeError, RuntimeError):
                pass

        # Category cards without a watermark are valid, but if no watermark surface
        # has even been constructed yet GTK has not reached the state we are waiting
        # for.
        if not watermark_surfaces:
            return False

        for surface in watermark_surfaces:
            # The size-allocate callback creates this attribute.  None means its
            # pending final size has already been rendered successfully.
            if not hasattr(surface, "_linuxtoys_pending_watermark_size"):
                return False
            if surface._linuxtoys_pending_watermark_size is not None:
                return False

        return True

    def _finish_categories_loading_when_ready(self):
        """Keep the startup roller visible until category watermarks are painted."""
        if not hasattr(self, "categories_loading_box"):
            self._categories_loading_hide_source = None
            return False

        # This callback runs every 16 ms while startup is waiting. It must remain
        # inspection-only: watermark rendering is comparatively expensive GTK work
        # and should never be repeated from the polling loop.
        if self._categories_watermarks_ready():
            self._categories_loading_hide_source = None
            self._categories_loading_hide_started_us = None
            self._start_categories_loading_fade()
            return False

        # Never strand the application behind the roller if an icon is malformed or
        # a theme/backend never produces the expected allocation callback.
        started = self._categories_loading_hide_started_us
        if started is not None and GLib.get_monotonic_time() - started >= 2_000_000:
            self._categories_loading_hide_source = None
            self._categories_loading_hide_started_us = None
            self.categories_view.set_opacity(1.0)
            self.categories_loading_spinner.stop()
            self.categories_loading_box.hide()
            self._categories_startup_transition_complete = True
            if self.should_start_random_timer and self.all_scripts:
                GLib.idle_add(self._deferred_start_random_scripts_refresh_timer)
            return False

        return True

    def _start_categories_loading_fade(self):
        """Cross-fade the completed main menu in while the startup roller fades out."""
        if self._categories_loading_fade_source is not None:
            return False
        if not hasattr(self, "categories_view"):
            return False

        self._categories_loading_fade_started_us = GLib.get_monotonic_time()
        self.categories_view.set_opacity(0.0)
        self.categories_loading_box.set_opacity(1.0)
        self._categories_loading_fade_source = GLib.timeout_add(
            16,
            self._step_categories_loading_fade,
        )
        return False

    def _step_categories_loading_fade(self):
        """Advance the startup cross-fade without removing either widget from layout."""
        started = self._categories_loading_fade_started_us
        if started is None:
            self._categories_loading_fade_source = None
            return False

        elapsed_ms = (GLib.get_monotonic_time() - started) / 1000.0
        duration = max(1, self._categories_loading_fade_duration_ms)
        progress = min(1.0, elapsed_ms / duration)

        self.categories_view.set_opacity(progress)
        self.categories_loading_box.set_opacity(1.0 - progress)

        if progress < 1.0:
            return True

        self._categories_loading_fade_source = None
        self._categories_loading_fade_started_us = None
        self.categories_view.set_opacity(1.0)
        self.categories_loading_box.set_opacity(1.0)
        self.categories_loading_spinner.stop()
        self.categories_loading_box.hide()

        # Featured creation/animation is intentionally held back during startup so
        # its GTK work cannot contend with the opacity crossfade. Release it only
        # after the final crossfade frame has been committed.
        self._categories_startup_transition_complete = True
        if self.should_start_random_timer and self.all_scripts:
            GLib.idle_add(self._deferred_start_random_scripts_refresh_timer)
        return False

    def _hide_categories_loading_indicator(self):
        """Hide startup loading only after bootstrap data and watermarks are ready."""
        if not hasattr(self, "categories_loading_box"):
            return False
        if self._appstream_initial_build_pending:
            return False
        if not self.categories_loading_box.get_visible():
            return False
        if self._categories_loading_hide_source is not None:
            return False

        self._categories_loading_hide_started_us = GLib.get_monotonic_time()

        # Give any deferred startup watermark allocations one explicit chance to
        # render before polling. After this, the 16 ms readiness callback only
        # observes state; normal allocation/resize machinery owns further renders.
        if not self._categories_loading_watermarks_flushed:
            flush = getattr(self, "_flush_deferred_category_watermarks", None)
            if flush is not None:
                flush()
            self._categories_loading_watermarks_flushed = True

        self._categories_loading_hide_source = GLib.timeout_add(
            16,
            self._finish_categories_loading_when_ready,
        )
        return False

    def _render_categories(self, categories):
        """Render an already parsed category snapshot on the GTK thread."""
        # Store current category info and temporarily set to None for proper bold formatting.
        temp_current_category = self.current_category_info
        self.current_category_info = None

        self.categories_flowbox.foreach(
            lambda widget: self.categories_flowbox.remove(widget)
        )

        # Specials is a virtual top-level category backed by the curated category
        # cache. Keep it first so the LinuxToys-curated catalog is the leading
        # main-menu option. Its visible strings come from the normal translation
        # dictionary, just like the parser-backed categories.
        specials_category = {
            "name": self.translations.get("specials", "Specials"),
            "description": self.translations.get(
                "specials_desc",
                "LinuxToys-curated software and scripts.",
            ),
            "icon": "linuxtoys.svg",
            "path": "specials://root",
            "type": "category",
            "is_script": False,
            "is_subcategory": False,
            "is_linuxtoys_specials": True,
        }
        rendered_categories = [specials_category, *categories]

        for cat in rendered_categories:
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
        self._hide_categories_loading_indicator()

    def _load_scripts_into_flowbox(
        self,
        flowbox,
        category_info,
        defer_initial=False,
        pause_after_initial_ms=0,
        animate_initial=True,
    ):
        """
        Populate category cards lazily.

        Only a small viewport-sized buffer is materialized initially. More cards
        are appended when the user reaches 75% of the currently materialized
        content. The complete category remains lightweight Python data until its
        cards are actually needed.
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
                    pause_after_initial_ms=pause_after_initial_ms,
                    animate_initial=animate_initial,
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

        # Invalidate every deferred/timed population targeting this FlowBox.
        generation = getattr(flowbox, "_linuxtoys_population_generation", 0) + 1
        flowbox._linuxtoys_population_generation = generation
        flowbox._linuxtoys_lazy_state = None

        category_path = category_info["path"]

        # Specials depends on the complete recursive CategoryCache. The main menu
        # is published from the top-level bootstrap before that cache has finished.
        if (
            category_info.get("is_linuxtoys_specials")
            or category_info.get("is_linuxtoys_specials_category")
        ) and not self.category_cache.is_populated:
            expected_cache = self.category_cache

            def populate_specials_when_ready():
                if (
                    getattr(flowbox, "_linuxtoys_population_generation", None)
                    != generation
                ):
                    return False
                if self.category_cache is not expected_cache:
                    self._load_scripts_into_flowbox(
                        flowbox, category_info, defer_initial=False
                    )
                    return False
                if not expected_cache.is_populated:
                    return True
                self._load_scripts_into_flowbox(
                    flowbox, category_info, defer_initial=False
                )
                return False

            GLib.timeout_add(100, populate_specials_when_ready)
            return

        if category_info.get("is_linuxtoys_specials"):
            scripts = self.category_cache.get_linuxtoys_special_categories(
                self.translations
            )
        elif category_info.get("is_linuxtoys_specials_category"):
            scripts = self.category_cache.get_linuxtoys_special_scripts(
                category_info.get("specials_category_path", "")
            )
        elif self.category_cache.is_populated:
            scripts = self.category_cache.get_scripts_for_category(category_path)
            if not scripts:
                scripts = parser.get_scripts_for_category(
                    category_path, self.translations
                )
        else:
            scripts = parser.get_scripts_for_category(
                category_path, self.translations
            )

        scripts = list(scripts)
        checklist_mode = category_info.get("display_mode", "menu") == "checklist"
        allow_drag = self._is_local_scripts_category(category_info)

        frame_batch_size = 2
        frame_interval_ms = 20
        scroll_trigger = 0.75

        def find_scrolled_window():
            widget = flowbox
            while widget is not None:
                if isinstance(widget, Gtk.ScrolledWindow):
                    return widget
                try:
                    widget = widget.get_parent()
                except (AttributeError, RuntimeError):
                    return None
            return None

        def viewport_capacity():
            """
            Estimate one visible viewport of cards from the live allocation.

            Card content has a 128x52 minimum request. Account for FlowBox margins,
            card badge-edge space and row/column spacing. Once GTK has real child
            allocations, prefer those measurements over the fallback constants.
            """
            scrolled = find_scrolled_window()
            if scrolled is not None:
                allocation = scrolled.get_allocation()
                viewport_width = max(1, int(allocation.width))
                viewport_height = max(1, int(allocation.height))
            else:
                allocation = flowbox.get_allocation()
                viewport_width = max(1, int(allocation.width))
                viewport_height = max(1, int(allocation.height))

            card_width = 132
            card_height = 56
            children = flowbox.get_children()
            if children:
                child_allocation = children[0].get_allocation()
                if child_allocation.width > 1:
                    card_width = int(child_allocation.width)
                if child_allocation.height > 1:
                    card_height = int(child_allocation.height)

            horizontal_space = max(1, viewport_width - 64)
            columns = max(
                1,
                min(
                    5,
                    int((horizontal_space + 16) // max(1, card_width + 16)),
                ),
            )
            visible_rows = max(
                1,
                int((viewport_height + 12 + card_height - 1) // (card_height + 12)),
            )
            return max(1, columns * visible_rows)

        state = {
            "scripts": scripts,
            "next_index": 0,
            "target_index": 0,
            "timer_id": None,
            "generation": generation,
            "initial_complete": False,
        }
        flowbox._linuxtoys_lazy_state = state

        def state_is_current():
            return (
                getattr(flowbox, "_linuxtoys_population_generation", None)
                == generation
                and getattr(flowbox, "_linuxtoys_lazy_state", None) is state
            )

        def add_card(script_info):
            widget = self.create_item_widget(
                script_info,
                checklist=checklist_mode,
                allow_drag=allow_drag,
            )
            description = script_info.get("description", "")
            widget.set_tooltip_text(description or None)
            widget.set_opacity(0.0)
            flowbox.add(widget)
            return widget

        def populate_timed_batch():
            if not state_is_current():
                state["timer_id"] = None
                return False

            target = min(state["target_index"], len(scripts))
            if state["next_index"] >= target:
                state["timer_id"] = None
                return False

            batch_widgets = []
            stop = min(target, state["next_index"] + frame_batch_size)
            while state["next_index"] < stop:
                widget = add_card(scripts[state["next_index"]])
                state["next_index"] += 1
                widget.show_all()
                batch_widgets.append(widget)

            self.animate_item_batch(
                batch_widgets,
                duration_ms=110,
                stagger_ms=5,
            )

            if state["next_index"] >= target:
                state["timer_id"] = None
                return False
            return True

        def ensure_population_timer(delay_ms=frame_interval_ms):
            if not state_is_current():
                return
            if state["next_index"] >= state["target_index"]:
                return
            if state["timer_id"] is not None:
                return

            def start_or_continue():
                if not state_is_current():
                    state["timer_id"] = None
                    return False
                return populate_timed_batch()

            state["timer_id"] = GLib.timeout_add(
                max(1, int(delay_ms)),
                start_or_continue,
                priority=GLib.PRIORITY_LOW,
            )

        def request_more(viewports=1):
            if not state_is_current() or state["next_index"] >= len(scripts):
                return

            capacity = viewport_capacity()
            extra = max(1, capacity * max(1, int(viewports)))
            state["target_index"] = min(
                len(scripts),
                max(state["target_index"], state["next_index"] + extra),
            )
            ensure_population_timer()

        def on_scroll_position_changed(adjustment):
            if not state_is_current() or not state["initial_complete"]:
                return
            if state["target_index"] >= len(scripts):
                return

            upper = float(adjustment.get_upper())
            page_size = float(adjustment.get_page_size())
            if upper <= 0.0:
                return

            progress = (float(adjustment.get_value()) + page_size) / upper
            if progress >= scroll_trigger:
                request_more(1)

        def on_flowbox_size_allocate(_widget, _allocation):
            if not state_is_current() or not state["initial_complete"]:
                return

            # A resize can expose substantially more room without producing a
            # scroll event. Keep at least two viewports materialized ahead of an
            # enlarged viewport, but never discard cards when the window shrinks.
            capacity = viewport_capacity()
            desired = min(len(scripts), max(capacity * 2, state["next_index"]))
            if desired > state["target_index"]:
                state["target_index"] = desired
                ensure_population_timer()

        # Connect the scrolling/resize observers once per FlowBox. Their callbacks
        # always consult the FlowBox's current lazy state, so retained category
        # views and later generations do not accumulate active population logic.
        scrolled = find_scrolled_window()
        if scrolled is not None:
            adjustment = scrolled.get_vadjustment()
            if not getattr(flowbox, "_linuxtoys_lazy_scroll_connected", False):
                def lazy_scroll_dispatch(adj, target_flowbox=flowbox):
                    current = getattr(
                        target_flowbox, "_linuxtoys_lazy_scroll_callback", None
                    )
                    if current is not None:
                        current(adj)

                adjustment.connect("value-changed", lazy_scroll_dispatch)
                flowbox._linuxtoys_lazy_scroll_connected = True
            flowbox._linuxtoys_lazy_scroll_callback = on_scroll_position_changed

        if not getattr(flowbox, "_linuxtoys_lazy_resize_connected", False):
            def lazy_resize_dispatch(widget, allocation, target_flowbox=flowbox):
                current = getattr(
                    target_flowbox, "_linuxtoys_lazy_resize_callback", None
                )
                if current is not None:
                    current(widget, allocation)

            flowbox.connect("size-allocate", lazy_resize_dispatch)
            flowbox._linuxtoys_lazy_resize_connected = True
        flowbox._linuxtoys_lazy_resize_callback = on_flowbox_size_allocate

        def populate_initial_batch():
            if not state_is_current():
                return False

            # Put a small seed batch on screen immediately. This deliberately
            # happens before asking GTK for the real viewport/card geometry, so
            # entering a category never presents an empty page while allocations
            # settle. The seed also gives viewport_capacity() a real card
            # allocation to measure on the following main-loop turn.
            seed_count = min(len(scripts), 6)
            seed_widgets = []
            while state["next_index"] < seed_count:
                widget = add_card(scripts[state["next_index"]])
                state["next_index"] += 1
                widget.show_all()
                seed_widgets.append(widget)

            if animate_initial:
                self.animate_item_batch(
                    seed_widgets,
                    duration_ms=90,
                    stagger_ms=5,
                )
            else:
                for widget in seed_widgets:
                    widget.set_opacity(1.0)

            self._configure_local_scripts_interaction(flowbox, category_info)
            if checklist_mode:
                self.reveal.set_reveal_child(len(self.check_buttons) >= 2)

            def finish_initial_sizing():
                if not state_is_current():
                    return False

                capacity = viewport_capacity()
                # Small windows get more scrolling headroom; large windows already
                # expose many cards, so two viewports are enough.
                multiplier = 3 if capacity <= 20 else 2
                state["target_index"] = min(
                    len(scripts),
                    max(state["next_index"], capacity * multiplier),
                )
                state["initial_complete"] = True

                if state["next_index"] < state["target_index"]:
                    pause_ms = max(0, int(pause_after_initial_ms))
                    ensure_population_timer(
                        pause_ms
                        if pause_ms > frame_interval_ms
                        else frame_interval_ms
                    )
                return False

            # Let GTK paint/allocate the seed cards first. The expensive-looking
            # part of entering the category is therefore overlapped with the first
            # visible frame instead of preceding it.
            GLib.idle_add(
                finish_initial_sizing,
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

        script_info = uri_parser.resolve_install_target(target_id, self.translations)
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

        if info.get("is_appstream_entry"):
            # AppStream installs stay on the app page. Queue state owns the button
            # until the background operation succeeds, fails, or is cancelled.
            self._appstream_runner.enqueue(deps)
            app_page = self.main_stack.get_child_by_name("app_page")
            if app_page is not None and hasattr(app_page, "refresh_install_state"):
                app_page.refresh_install_state()
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

    def _on_close_requested(self, _widget, _event):
        """Guard application shutdown while AppStream work is still active."""
        runner = getattr(self, "_appstream_runner", None)
        if runner is not None and runner.has_pending_operations():
            if not self._show_queue_close_warning_dialog():
                return True

        self._close_application()
        return True

    def _show_queue_close_warning_dialog(self):
        """Warn before closing while queued or running operations remain."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self.translations.get(
                "queue_close_title",
                "Operations Are Still Running",
            ),
        )

        dialog.format_secondary_text(
            self.translations.get(
                "queue_close_message",
                "Closing LinuxToys will stop all queued and running operations. "
                "Interrupting an operation while it is in progress may cause "
                "problems with your system. Are you sure you want to close?",
            )
        )

        dialog.add_button(
            self.translations.get(
                "queue_close_continue_btn",
                "Keep LinuxToys Open",
            ),
            Gtk.ResponseType.NO,
        )
        close_button = dialog.add_button(
            self.translations.get(
                "queue_close_close_btn",
                "Close Anyway",
            ),
            Gtk.ResponseType.YES,
        )
        close_button.get_style_context().add_class("destructive-action")
        dialog.set_default_response(Gtk.ResponseType.NO)

        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES


    def _window_state_path(self):
        """Return the per-environment cache path used for window geometry."""
        try:
            cache_dir = compat.get_linuxtoys_cache_dir()
        except (AttributeError, TypeError):
            cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "linuxtoys")
        return os.path.join(cache_dir, "window-state.json")

    def _primary_monitor_workarea(self):
        """Return the primary monitor's usable (non-panel) width and height."""
        display = Gdk.Display.get_default()
        if display is not None and hasattr(display, "get_primary_monitor"):
            monitor = display.get_primary_monitor()
            if monitor is not None:
                area = monitor.get_workarea()
                return area.width, area.height

        screen = Gdk.Screen.get_default()
        if screen is not None:
            monitor_index = screen.get_primary_monitor()
            area = screen.get_monitor_workarea(monitor_index)
            return area.width, area.height
        return None

    def _restore_window_state(self):
        """Restore the last usable size/maximized state for the current display."""
        default_width, default_height = self._default_window_size
        workarea = self._primary_monitor_workarea()

        state = {}
        try:
            with open(self._window_state_path(), "r", encoding="utf-8") as state_file:
                state = json.load(state_file)
            if not isinstance(state, dict):
                state = {}
        except (OSError, ValueError, TypeError):
            state = {}

        if state.get("maximized") is True:
            self.maximize()
            return

        try:
            width = int(state.get("width", default_width))
            height = int(state.get("height", default_height))
        except (TypeError, ValueError):
            width, height = default_width, default_height

        # Reject nonsensical/corrupt geometry as well as geometry that no longer
        # fits the current monitor. In either case, retry with the app default.
        saved_size_valid = width > 0 and height > 0
        if workarea is not None:
            saved_size_valid = (
                saved_size_valid
                and width <= workarea[0]
                and height <= workarea[1]
            )

        if not saved_size_valid:
            width, height = default_width, default_height

        if workarea is not None and (width > workarea[0] or height > workarea[1]):
            self.maximize()
            return

        self._last_normal_window_size = (width, height)
        self.set_default_size(width, height)

    def _on_window_state_changed(self, _widget, event):
        """Keep Featured out of width negotiation while leaving maximized state."""
        changed = bool(event.changed_mask & Gdk.WindowState.MAXIMIZED)
        maximized = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
        if not changed or maximized:
            return False

        if (
            hasattr(self, "main_stack")
            and self.main_stack.get_visible_child_name() == "categories"
            and getattr(self, "random_scripts_flowbox", None) is not None
        ):
            # Do not destroy/reselect cards here. Hiding the fixed-column grid is
            # enough to stop its maximized natural width influencing the restored
            # top-level size, while preserving Featured state and history.
            self.random_scripts_flowbox.hide()
            self.categories_view.queue_resize()
            self.categories_flowbox.queue_resize()

            if getattr(self, "_featured_unmaximize_timer", None):
                GLib.source_remove(self._featured_unmaximize_timer)

            self._featured_unmaximize_timer = GLib.timeout_add(
                self.FEATURED_RESIZE_DEBOUNCE_MS,
                self._finish_featured_unmaximize,
            )

        return False

    def _finish_featured_unmaximize(self):
        """Re-enable Featured after the restored window geometry has settled."""
        self._featured_unmaximize_timer = None

        if self.main_stack.get_visible_child_name() != "categories":
            self.random_scripts_flowbox.show()
            return False

        # At this point the category FlowBox has the restored viewport width, so the
        # existing Featured geometry calculation can safely mirror its real columns.
        self._featured_last_layout = None
        self._featured_layout_metrics = None
        self._refresh_random_scripts_display(force=False)
        self.random_scripts_flowbox.show()
        self.categories_view.queue_resize()
        return False

    def _request_window_resize_settle(self, *_args):
        """Restart the single debounce used by responsive LinuxToys UI work."""
        if getattr(self, "_window_resize_settling", False):
            return False

        width, height = self.get_size()
        if width > 0 and height > 0:
            self._pending_window_size = (int(width), int(height))

        self._window_resize_pending = True
        if self._window_resize_settle_timer is not None:
            GLib.source_remove(self._window_resize_settle_timer)

        self._window_resize_settle_timer = GLib.timeout_add(
            self.FEATURED_RESIZE_DEBOUNCE_MS,
            self._apply_window_resize_settled,
        )
        return False

    def _apply_window_resize_settled(self):
        """Run expensive responsive calculations once after resizing goes quiet."""
        self._window_resize_settle_timer = None
        self._window_resize_pending = False
        self._window_resize_settling = True

        try:
            size = tuple(getattr(self, "_pending_window_size", self.get_size()))
            size_changed = size != self._last_settled_window_size
            self._last_settled_window_size = size

            # Allocation-sized category watermarks are intentionally not regenerated
            # while an interactive resize is in progress. Render them once at the
            # final settled allocation instead.
            flush_watermarks = getattr(self, "_flush_deferred_category_watermarks", None)
            if flush_watermarks is not None:
                flush_watermarks()

            # Main-menu Featured already compares its final rows/columns against
            # the previous layout, so this is cheap when no breakpoint changed.
            if (
                self.should_start_random_timer
                and self.all_scripts
                and self._categories_startup_transition_complete
                and self.main_stack.get_visible_child_name() == "categories"
            ):
                self._apply_featured_resize()

            # App pages own several width-dependent operations (description height,
            # screenshot source choice and Featured geometry). Let the page consume
            # the same final window geometry in one pass.
            if self.main_stack.get_visible_child_name() == "app_page":
                page = self.main_stack.get_child_by_name("app_page")
                if page is not None and hasattr(page, "on_window_resize_settled"):
                    page.on_window_resize_settled(size_changed=size_changed)
        finally:
            self._window_resize_settling = False

        return False

    def _on_window_configure(self, _widget, _event):
        """Remember normal size and debounce expensive responsive recalculation."""
        self._request_window_resize_settle()

        gdk_window = self.get_window()
        if gdk_window is None:
            return False
        if gdk_window.get_state() & Gdk.WindowState.MAXIMIZED:
            return False

        width, height = self.get_size()
        if width > 0 and height > 0:
            self._last_normal_window_size = (width, height)
        return False

    def _save_window_state(self):
        """Persist the last normal size plus the current maximized state."""
        maximized = False
        gdk_window = self.get_window()
        if gdk_window is not None:
            maximized = bool(gdk_window.get_state() & Gdk.WindowState.MAXIMIZED)

        width, height = self._last_normal_window_size
        state = {
            "width": int(width),
            "height": int(height),
            "maximized": maximized,
        }

        state_path = self._window_state_path()
        try:
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            temporary_path = f"{state_path}.tmp"
            with open(temporary_path, "w", encoding="utf-8") as state_file:
                json.dump(state, state_file)
            os.replace(temporary_path, state_path)
        except OSError as exc:
            logger.warning("Could not save window state: %s", exc)

    def _close_application(self):
        """Closes the application gracefully and performs cleanup."""
        if getattr(self, "_featured_unmaximize_timer", None):
            GLib.source_remove(self._featured_unmaximize_timer)
            self._featured_unmaximize_timer = None
        # Persist UI state once per session, at shutdown.
        self._save_window_state()
        self._save_featured_sense()

        # Stop the persistent AppStream PTY before deleting its temporary state.
        if getattr(self, "_appstream_runner", None) is not None:
            self._appstream_runner.shutdown()

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
        current_view = self.main_stack.get_visible_child_name()
        app_page_info = None
        if current_view == "app_page":
            current_page = self.main_stack.get_child_by_name("app_page")
            if current_page is not None:
                app_page_info = current_page.script_info

        # Hidden retained category views contain already-rendered translated
        # labels/tooltips. Drop them so Back never resurrects the old locale.
        self._discard_retained_category_views()

        # App pages and utility views own their visible header state. Rebuilding the
        # normal category header while one is visible can expose that header and
        # corrupt the view we are trying to preserve across a language change.
        if current_view not in ("app_page", "appstream_queue", "installed_features"):
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

        # Refresh the shared updater/AppStream indicator tooltip in the new language.
        self._refresh_status_indicator()

        # Always reload categories with new translations (so they're ready when user navigates back)
        self.load_categories()

        # Refresh footer translations
        self.reveal.update_translations(self.translations)

        # Queue and Installed Features are persistent utility views whose rows are
        # rendered directly from self.translations. Refresh them in place and keep
        # their utility-view header state instead of falling through to category
        # navigation refresh logic from the view they were opened from.
        if current_view == "appstream_queue":
            queue_view = self.main_stack.get_child_by_name("appstream_queue")
            if queue_view is not None and hasattr(queue_view, "refresh"):
                queue_view.refresh()
            self.header_widget.hide()
            self.reveal.set_reveal_child(False)
            self.back_button.show()
            title = self.translations.get("installation_queue", "Installation Queue")
            self.header_bar.props.title = f"LinuxToys: {title}"
            return

        if current_view == "installed_features":
            installed_view = self.main_stack.get_child_by_name("installed_features")
            if installed_view is not None and hasattr(installed_view, "refresh"):
                installed_view.refresh()
            self.header_widget.hide()
            self.reveal.set_reveal_child(False)
            self.back_button.show()
            title = self.translations.get("installed_features", "Installed Features")
            self.header_bar.props.title = f"LinuxToys: {title}"
            return

        # App pages are snapshots of translated repository metadata, so recreate
        # the active page from freshly parsed metadata while preserving the exact
        # view it should return to on Back.
        if current_view == "app_page":
            fresh_info = None
            if app_page_info:
                script_name = app_page_info.get("name")
                if script_name:
                    fresh_info = manifest_helper.find_script_by_name(
                        script_name, self.translations
                    )

            self.refresh_app_page_with_fade(fresh_info or app_page_info)
            return

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

    def _refresh_removable_scripts(
        self, pause_after_initial_ms=0, animate_initial=True
    ):
        """
        Refresh removable-script state and rebuild the currently visible cards.

        The removal button is created inside create_item_widget(), so refreshing
        only the boolean cache is insufficient: the displayed widgets must also
        be recreated.

        ``pause_after_initial_ms`` is used by terminal Back navigation: the first
        screenful is rebuilt synchronously while the terminal is still visible,
        then later progressive batches are held until the stack transition ends.
        """
        if self.script_cache.is_populated:
            self.script_cache.refresh_removable_cache()

        # Refresh the current category/subcategory view.
        if self.current_category_info is not None:
            self._load_scripts_into_flowbox(
                self.scripts_flowbox,
                self.current_category_info,
                pause_after_initial_ms=pause_after_initial_ms,
                animate_initial=animate_initial,
            )
            self.scripts_flowbox.show_all()
        else:
            # Root-level scripts can also be removable.
            self.load_categories()
