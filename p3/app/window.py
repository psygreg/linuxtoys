import asyncio
import json
import logging
import os
import shutil
import subprocess
import threading
import sys
import time

from . import (
    action_registry,
    appstream_cache,
    homebrew_catalog,
    appstream_parser,
    aur_cache,
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
    gtk_dialogs,
    gui_rs,
    package_view
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
        self._default_window_size = self._calculate_default_window_size()
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
        self._package_view_prev = None

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
        # Hidden Back targets get a second, longer debounce. Resize never waits for
        # this speculative work; Back keeps its existing retained/rebuild fallback
        # until a freshly prewarmed replacement is completely ready.
        self._navigation_prewarm_timer = None
        self._navigation_prewarm_generation = 0
        self._navigation_prewarm_extra_delay_ms = 180
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
        self._categories_loading_watermarks_flushed = False
        self._categories_loading_watermark_queue = []
        self._categories_loading_watermark_source = None
        self._categories_loading_fade_source = None
        self._categories_loading_fade_started_us = None
        self._categories_loading_fade_duration_ms = 220
        # Startup has three independent readiness stages. Do not expose the real
        # menu or let Featured measure it until the complete category snapshot has
        # been published, GTK has allocated that snapshot, and its allocation-sized
        # watermarks have been rendered.
        self._categories_startup_render_complete = False
        self._categories_startup_allocation_complete = False
        self._categories_startup_waiting_for_allocation = False
        self._categories_startup_expected_children = 0
        self._categories_startup_transition_complete = False

        # Language changes are presented as a content crossfade. Native Rust
        # rendering remains authoritative for allocation-dependent decorations.
        self._language_transition_active = False
        self._language_transition_phase = None
        self._language_transition_source = None
        self._language_transition_started_us = None
        self._language_transition_duration_ms = 120
        self._language_transition_target = None
        self._language_categories_render_pending = False
        self._language_categories_waiting_for_allocation = False
        self._language_categories_expected_children = 0
        self._language_categories_allocation_complete = False
        self._language_featured_refresh_started = False
        self._language_featured_allocation_complete = False
        self._language_featured_allocate_handler = None
        self._language_search_loading_active = False
        self._language_search_transition_owned = False
        self._language_search_loading_fade_source = None
        self._language_search_loading_fade_started_us = None
        self._language_search_loading_fade_duration_ms = 180

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

        # Create categories view with random scripts section. Keep the complete
        # menu anchored to the top of the viewport: its natural content height is
        # also the geometry basis used by Featured capacity calculations.
        categories_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        categories_container.set_valign(Gtk.Align.START)
        categories_container.set_halign(Gtk.Align.FILL)
        categories_container.set_hexpand(True)
        categories_container.set_vexpand(False)

        self.categories_flowbox = self.create_flowbox()
        self.categories_flowbox.connect(
            "size-allocate",
            self._on_categories_startup_size_allocate,
        )
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
        # Opacity only changes painting; disable input and hover handling while
        # the invisible menu remains allocated behind the startup overlay.
        self.categories_view.set_sensitive(False)

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

        # Create search results view. Keep it inside an Overlay so a language
        # refresh can show the same centered roller pattern used by startup while
        # the replacement translated search/cache generation is prepared.
        self.search_flowbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.search_view = Gtk.ScrolledWindow()
        self.search_view.add(self.search_flowbox)

        self.search_loading_overlay = Gtk.Overlay()
        self.search_loading_overlay.add(self.search_view)

        self.search_language_loading_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )
        self.search_language_loading_box.set_halign(Gtk.Align.CENTER)
        self.search_language_loading_box.set_valign(Gtk.Align.CENTER)
        self.search_language_loading_box.set_no_show_all(True)

        self.search_language_loading_spinner = Gtk.Spinner()
        self.search_language_loading_spinner.set_size_request(64, 64)
        self.search_language_loading_box.pack_start(
            self.search_language_loading_spinner, False, False, 0
        )
        self.search_loading_overlay.add_overlay(self.search_language_loading_box)

        self.main_stack.add_named(self.search_loading_overlay, "search")

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
        self._setup_package_drag_and_drop()

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
        self._homebrew_source_fingerprint = homebrew_catalog.availability_fingerprint()
        self._homebrew_refresh_running = False
        self._homebrew_refresh_pending = False
        self._homebrew_watch_id = GLib.timeout_add_seconds(3, self._check_homebrew_source)
        self.connect("destroy", self._stop_homebrew_watch)
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

        if keys.intersection({"steamos", "gnomeos", "dakota", "kde-linux"}) and not homebrew_catalog.enabled():
            recommendations.append("brew")

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

    def _schedule_appstream_cache_after_startup(self):
        """Start the AppStream freshness worker after the startup transition.

        A genuine first build still starts immediately because the initial loading
        gate depends on it.  Warm starts already have a complete published catalog
        and Rust runtime cache, so source fingerprinting/refresh discovery can wait
        until the first usable UI has finished its cross-fade.
        """
        if self._appstream_cache_started:
            return False
        if self._appstream_initial_build_pending:
            return self._start_appstream_cache()
        if not self._categories_startup_transition_complete:
            return True
        return self._start_appstream_cache()

    def _activate_homebrew_category(self, widget, event):
        if not homebrew_catalog.enabled():
            self._check_homebrew_source()
            return
        source = appstream_cache.get_state().get("sources", {}).get("homebrew", {})
        if (source.get("complete") and homebrew_catalog.binary_snapshot_available()
                and source.get("fingerprint") == homebrew_catalog.fingerprint()):
            # Browse the already-published runtime generation immediately.
            # Refresh/validation stays off GTK and does not gate navigation.
            self._open_aur_category_view(self._homebrew_category_info(), loading=False)
            return
        category_info = self._homebrew_category_info()
        self._open_aur_category_view(category_info, loading=True)
        page = self.scripts_view
        flowbox = self.scripts_flowbox
        self._refresh_homebrew_catalog()

        def finish_loading():
            if self.main_stack.get_visible_child() is not page:
                return False
            if self._homebrew_refresh_running or self._homebrew_refresh_pending:
                return True
            page._linuxtoys_aur_spinner.stop()
            page._linuxtoys_aur_spinner.hide()
            page._linuxtoys_category_content.set_sensitive(True)
            state = appstream_cache.get_state().get("sources", {}).get("homebrew", {})
            if (state.get("complete") and homebrew_catalog.enabled()
                    and self._homebrew_refresh_result.get("success")):
                self._load_scripts_into_flowbox(flowbox, category_info, defer_initial=True)
            else:
                gtk_dialogs.run_message_dialog(
                    self, title="Homebrew",
                    secondary_text=self.translations.get(
                        "homebrew_catalog_unavailable", "Homebrew metadata is unavailable. Try again later."),
                    message_type=Gtk.MessageType.ERROR,
                    buttons=[("OK", Gtk.ResponseType.OK)],
                    default_response=Gtk.ResponseType.OK,
                )
            return False

        GLib.timeout_add(100, finish_loading)

    def _homebrew_category_info(self):
        return {
            "name": "Homebrew",
            "description": self.translations.get("homebrew_category_desc", "Packages from Homebrew."),
            "icon": "brew.png", "path": "homebrew://catalog", "type": "category",
            "is_script": False, "is_subcategory": False, "is_homebrew_category": True,
        }

    def _stop_homebrew_watch(self, _window):
        if self._homebrew_watch_id is not None:
            GLib.source_remove(self._homebrew_watch_id)
            self._homebrew_watch_id = None

    def _check_homebrew_source(self):
        """Observe installer/remover signals and externally changed Brew presence."""
        if not self._categories_startup_transition_complete:
            return True
        fingerprint = homebrew_catalog.availability_fingerprint()
        if fingerprint == self._homebrew_source_fingerprint:
            return True
        self._homebrew_source_fingerprint = fingerprint
        self._homebrew_refresh_pending = True
        self._discard_retained_category_views()
        self.load_categories()
        if not homebrew_catalog.enabled() and (self.current_category_info or {}).get("is_homebrew_category"):
            self.show_categories_view()
        if homebrew_catalog.enabled():
            self._refresh_homebrew_catalog()
        else:
            self._homebrew_refresh_pending = False
            self._apply_appstream_catalog()
        return True

    def _refresh_homebrew_catalog(self):
        if self._homebrew_refresh_running or not homebrew_catalog.enabled():
            return
        self._homebrew_refresh_pending = False
        self._homebrew_refresh_running = True

        def worker():
            try:
                result = appstream_cache.refresh_homebrew_cache()
                if result.get("success"):
                    if result.get("changed"):
                        appstream_parser.prepare_runtime_cache()
                    # Warm the binary runtime/category index off GTK, even when
                    # the published source is unchanged. No entries are decoded.
                    appstream_parser.get_homebrew_entries()
            except Exception as error:
                result = {"success": False, "error": str(error)}
            GLib.idle_add(finish, result)

        def finish(result):
            self._homebrew_refresh_result = result
            self._homebrew_refresh_running = False
            current = homebrew_catalog.availability_fingerprint()
            if not homebrew_catalog.enabled():
                self._homebrew_refresh_pending = False
            elif current != self._homebrew_source_fingerprint:
                self._homebrew_refresh_pending = True
            self._homebrew_source_fingerprint = current
            if result.get("success") and result.get("changed"):
                self._apply_appstream_catalog()
                self._refresh_installed_packages_async(force=True)
            if self._homebrew_refresh_pending:
                self._refresh_homebrew_catalog()
            return False

        threading.Thread(target=worker, daemon=True, name="linuxtoys-homebrew-source").start()

    def _start_homebrew_after_startup(self):
        """Keep optional-source work outside the initial GTK transition."""
        if not self._categories_startup_transition_complete:
            return True
        self._refresh_homebrew_catalog()
        return False

    def _start_appstream_cache(self, *, force=False):
        """Refresh AppStream metadata on its background worker."""
        if self._appstream_cache_started:
            return False
        self._appstream_cache_started = True
        self._start_aur_refresh_if_enabled()

        def report_state(state):
            GLib.idle_add(self._set_appstream_state, state)

        def worker():
            initial_build = self._appstream_initial_build_pending
            result = appstream_cache.refresh_cache(
                force=force,
                status_callback=report_state,
                starter=initial_build,
            )
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

            # A first launch must have the derived runtime cache before the menu is
            # revealed. For later refreshes, prewarm only after a changed catalog.
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
                    bool(result.get("starter")),
                )
            elif changed:
                GLib.idle_add(self._apply_appstream_catalog)
            if not initial_build and homebrew_catalog.enabled():
                GLib.timeout_add(250, self._start_homebrew_after_startup)

        threading.Thread(
            target=worker,
            daemon=True,
            name="linuxtoys-appstream-cache",
        ).start()
        return False

    def _start_appstream_enrichment_after_startup(self):
        """Keep the starter snapshot until one complete enrichment is ready."""
        if not self._categories_startup_transition_complete:
            return True
        self._appstream_cache_started = False
        self._start_appstream_cache(force=True)
        return False

    def _finish_initial_appstream_build(self, catalog_changed, prepared, starter=False):
        """Release first-run startup after AppStream catalog/pickle preparation."""
        self._appstream_initial_build_pending = False
        if homebrew_catalog.enabled():
            GLib.timeout_add(250, self._start_homebrew_after_startup)
        if starter:
            # Wait for the starter's parser/GTK handoff before allowing the full
            # generation to replace its on-disk/runtime caches.
            GLib.timeout_add(250, self._start_appstream_enrichment_after_startup)
        if hasattr(self, "categories_loading_label"):
            self.categories_loading_label.hide()

        if catalog_changed:
            # This is still the bootstrap generation: no completed GTK snapshot is
            # visible yet. Rebuild against the newly published catalog, then let the
            # replacement parser generation render categories and release the roller.
            return self._apply_appstream_catalog(initial_build=True)

        # If the catalog was already current, preparation only needed to create the
        # missing derived pickle. The existing in-memory UI data is already valid.
        # If preparation failed, release startup anyway rather than trapping the UI.
        self._hide_categories_loading_indicator()
        return False

    def _apply_appstream_catalog(self, *, initial_build=False):
        """Stage a newly completed AppStream catalog without blocking GTK.

        The refresh worker has already prewarmed the Rust-derived runtime cache.
        During a normal refresh, keep the currently rendered widgets alive while
        fresh parser caches are populated in the background. During the initial
        build there is no published GTK snapshot yet, so the replacement generation
        must perform the normal bootstrap publication and release the startup roller.
        """
        self._discard_retained_category_views()

        # Do not clear appstream_parser's runtime cache here. prepare_runtime_cache()
        # just built the new generation off-thread, so invalidating it at the handoff
        # defeats the prewarm and forces the parser path to reacquire it.
        #
        # Replace the parser cache objects so an older worker can still finish
        # harmlessly; generation guards in _populate_runtime_caches() prevent stale
        # workers from publishing into this generation. The old GTK snapshot remains
        # visible until the new category snapshot is ready.
        self.script_cache = search_helper.ScriptCache()
        self.category_cache = search_helper.CategoryCache()
        self.search_engine.set_cache(self.script_cache)

        # Keep the currently published Featured/category GTK snapshot alive while
        # the replacement parser generation is built. Clearing all_scripts here
        # turns a background catalog handoff into visible Featured churn and can
        # make resize/timer callbacks rebuild against an empty intermediate state.
        #
        # Never synchronously call load_categories()/load_scripts() here. The new
        # CategoryCache is intentionally empty at this point, and load_categories()
        # would therefore invoke parser.get_categories() on the GTK main thread.
        self._populate_runtime_caches(catalog_refresh=not initial_build)
        return False

    def _populate_runtime_caches(self, *, catalog_refresh=False):
        """Build parser caches while progressively publishing startup-ready data.

        catalog_refresh=True means a complete GTK snapshot is already on screen.
        In that case only swap the backing parser/search/Featured data; do not
        rebuild the top-level category widgets as an intermediate publication.
        """

        category_cache = self.category_cache
        script_cache = self.script_cache
        translations = self.translations
        search_engine = self.search_engine
        language_search_query = (
            str(getattr(self, "_language_transition_search_query", "") or "").strip()
            if getattr(self, "_language_transition_active", False)
            and self.main_stack.get_visible_child_name() == "search"
            else ""
        )
        git_sync_scheduled = False

        def schedule_git_sync():
            nonlocal git_sync_scheduled
            if git_sync_scheduled:
                return
            git_sync_scheduled = True
            GLib.idle_add(self._start_scripts_synchronization)

        def collect_featured(categories, scripts_by_category, *, include_appstream=False):
            featured = []
            seen = set()

            def add_items(items):
                for item in items or ():
                    if (not item.get("is_script") or item.get("is_create_script")
                            or item.get("appstream_source") == "homebrew"):
                        continue
                    key = item.get("path") or (
                        item.get("name", ""),
                        item.get("repo", ""),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    featured.append(item)

            for category in categories:
                if category.get("is_script"):
                    continue
                category_path = category.get("path", "")
                if not category_path:
                    continue
                add_items(
                    scripts_by_category.get(os.path.abspath(category_path), ())
                )

            # CategoryCache intentionally keeps AppStream entries Rust-owned and
            # lazily materialized. For the completed Featured pool, ask Rust only
            # for review-eligible AppStream candidates instead of materializing
            # every category. Keep the bootstrap structural-only so warm startup
            # does not wait for the AppStream runtime catalog.
            if include_appstream:
                try:
                    add_items(parser.get_appstream_featured_descriptors(translations))
                except Exception as error:
                    print(f"Error loading AppStream Featured candidates: {error}")

            return featured

        def publish_bootstrap(categories, featured):
            # GTK-side publication. Cache identity is our generation guard for
            # script synchronization and language changes that replace the caches.
            if self.category_cache is not category_cache:
                return False

            if not catalog_refresh:
                self._render_categories(categories)
                self._hide_categories_loading_indicator()
                self.all_scripts = featured
                self._invalidate_featured_eligibility_cache()
                if (
                    self.should_start_random_timer
                    and featured
                    and self._categories_startup_transition_complete
                ):
                    self._deferred_start_random_scripts_refresh_timer()
            # During a background AppStream refresh the top-level category UI and
            # existing Featured cards remain valid while the complete replacement
            # pool is assembled below. Rebuilding the FlowBox here was the main
            # post-refresh GTK burst: remove every category widget, recreate it,
            # renegotiate layout and regenerate watermarks despite the structural
            # category tree being unchanged.
            return False

        def top_level_ready(categories, scripts_by_category):
            # Runs in the parser worker. Only prepare immutable-ish Python snapshots
            # here; all GTK work is handed back to the main loop.
            if self.category_cache is not category_cache:
                return

            featured = collect_featured(categories, scripts_by_category)
            GLib.idle_add(publish_bootstrap, categories, featured)
            # AppStream is supplemental on warm starts. Keep source fingerprinting
            # and refresh discovery completely outside the startup transition; the
            # last atomically published catalog remains usable in the meantime. A
            # genuine first build is the exception because the loading gate depends
            # on producing the initial catalog/runtime cache.
            if self._appstream_initial_build_pending:
                GLib.idle_add(self._start_appstream_cache)
            else:
                GLib.timeout_add(50, self._schedule_appstream_cache_after_startup)

            # Network/git work is lower startup priority than getting the first
            # usable Featured pool ready, but need not wait for recursive caches.
            schedule_git_sync()

        def publish_full_featured(featured):
            if self.category_cache is not category_cache:
                return False
            self.all_scripts = featured
            self._invalidate_featured_eligibility_cache()
            if (
                self.should_start_random_timer
                and featured
                and self._categories_startup_transition_complete
            ):
                self._deferred_start_random_scripts_refresh_timer()
            return False

        def publish_completed_runtime(prepared_search_query="", prepared_search_results=None):
            """Refresh only the currently visible secondary view after cache swap."""
            if self.category_cache is not category_cache or self.script_cache is not script_cache:
                return False

            visible = self.main_stack.get_visible_child_name()
            if visible == "scripts" and self.current_category_info is not None:
                self.load_scripts(self.current_category_info)
            elif visible == "search":
                query = self.search_entry.get_text().strip()
                if query:
                    if (
                        getattr(self, "_language_transition_active", False)
                        and prepared_search_query
                        and query == prepared_search_query
                        and prepared_search_results is not None
                    ):
                        # The expensive Rust/Python search pass was completed on the
                        # parser worker. GTK only publishes the resulting snapshot;
                        # card creation remains progressively scheduled by
                        # _display_search_results(), so the roller keeps animating.
                        self.search_results = prepared_search_results
                        self._display_search_results()
                        self._language_search_refresh_pending = False
                        self._language_visible_allocation_complete = True
                    elif getattr(self, "_language_transition_active", False):
                        # The query changed while the language cache was rebuilding.
                        # Keep the existing safe fallback for that exceptional case.
                        self._perform_search(query)
                        self._language_search_refresh_pending = False
                        self._language_visible_allocation_complete = True
                    else:
                        self.search_entry.emit("changed")
                elif getattr(self, "_language_transition_active", False):
                    self._language_search_refresh_pending = False
                    self._language_visible_allocation_complete = True
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
                    include_appstream=True,
                )
                GLib.idle_add(publish_full_featured, full_featured)

                script_cache.populate_from_category_cache(category_cache)

                prepared_search_results = None
                if language_search_query:
                    # SearchEngine.search() is data/backend work (including the Rust
                    # generic/AppStream indexes) and does not create GTK widgets.
                    # Keep it off the main loop so Gtk.Spinner continues to animate.
                    prepared_search_results = search_engine.search(language_search_query)

                GLib.idle_add(
                    publish_completed_runtime,
                    language_search_query,
                    prepared_search_results,
                )
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
                self._invalidate_featured_eligibility_cache()
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
            "reboot-ready",
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
            elif state == "reboot-ready":
                image = Gtk.Image.new_from_icon_name(
                    "system-reboot-symbolic", Gtk.IconSize.BUTTON
                )
                tooltip = self.translations.get(
                    "ostree_deployment_title", "Pending System Updates"
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
            if self._update_state not in ("restart-ready", "reboot-ready"):
                self._set_update_state("disabled")
            return

        if self._update_state in ("disabled", "error"):
            self._set_update_state("checking")
            self._check_updates()

    def _on_update_indicator_clicked(self, _button):
        if self._update_state == "reboot-ready":
            self._show_ostree_deployment_warning()
            return
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
                self._prune_registry_removals()
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

    def _prune_registry_removals(self):
        """Prune removal/auto-revert registry entries older than a week.

        Runs inside the installed-packages worker thread: removal transactions
        are only useful shortly after they happen, while installation entries
        must stay tracked for possible future removals. Legacy entries written
        with an already-localized pattern are matched through the current
        translation templates.
        """
        try:
            from .term_registry import ExecutionRegistry

            removed = ExecutionRegistry.prune_expired_removal_entries(
                max_age_days=7,
                extra_prefixes=ExecutionRegistry.localized_removal_prefixes(self.translations),
            )
            if removed:
                logger.info("Pruned %d expired removal registry entries", removed)
        except Exception as exc:
            logger.warning("Registry prune failed: %s", exc)

    def _refresh_installed_features_view(self):
        # Hidden Installed Features views can be expensive to rebuild and GTK will
        # still perform their widget work even though the user cannot see it.
        # A catalog publication only needs an immediate refresh when this view is
        # actually visible; opening it later constructs/refreshes current data.
        if self.main_stack.get_visible_child_name() != "installed_features":
            return False
        view = self.main_stack.get_child_by_name("installed_features")
        if view is not None and hasattr(view, "refresh"):
            view.refresh()
        return False

    def _on_installed_packages_changed(self):
        self._check_homebrew_source()
        # Observed AppStream state participates in ScriptCache and Featured eligibility.
        if self.script_cache.is_populated:
            self.script_cache.refresh_removable_cache()
        self._invalidate_featured_eligibility_cache()

        # The installed-package snapshot is now current, so update the removal
        # controls on already-built category cards without rebuilding the FlowBox.
        self._refresh_removable_scripts(refresh_cache=False)

        app_page = self.main_stack.get_child_by_name("app_page")
        if app_page is not None and hasattr(app_page, "refresh_install_state"):
            app_page.refresh_install_state()

        local_package_view = self.main_stack.get_child_by_name("package_view")
        if local_package_view is not None and hasattr(local_package_view, "refresh_install_state"):
            local_package_view.refresh_install_state()

        installed_view = self.main_stack.get_child_by_name("installed_features")
        if installed_view is not None and hasattr(installed_view, "refresh"):
            installed_view.refresh()
        return False

    def _appstream_registry_managed(self, info):
        registry_data = action_registry.parse_registry_file()
        candidates = (
            str(info.get("registry_name", "") or "").strip(),
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
        if session_state is not None and (
            info.get("appstream_source") != "homebrew" or session_state in ("queued", "removing")
        ):
            return session_state

        if info.get("appstream_source") == "homebrew":
            return "installed" if installed_packages.match(info) is not None else "available"
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

    @staticmethod
    def _local_package_extension(path):
        name = os.path.basename(os.fspath(path)).lower()
        if name.endswith(".pkg.tar.zst") or name.endswith(".pkg.tar.xz") or name.endswith(".pkg.tar.gz") or name.endswith(".pkg.tar.lz4"):
            return "arch"
        for suffix, kind in (
            (".deb", "deb"), (".rpm", "rpm"), (".pacman", "arch"),
            (".eopkg", "eopkg"), (".flatpakref", "flatpakref"),
            (".flatpak", "flatpak"), (".snap", "snap"), (".appimage", "appimage"),
        ):
            if name.endswith(suffix):
                return kind
        return None

    def _local_package_supported_on_host(self, kind):
        if kind == "snap":
            return not {"steamos", "dakota", "gnomeos", "kde-linux"}.intersection(compat.get_system_compat_keys())
        if kind in ("flatpak", "flatpakref"):
            return "systemd" in compat.get_system_compat_keys()
        if kind == "appimage":
            return True
        keys = compat.get_system_compat_keys()
        if kind == "deb":
            return bool(keys & {"debian", "ubuntu"})
        if kind == "rpm":
            return bool(keys & {"fedora", "rhel", "suse", "ostree"})
        if kind == "arch":
            return bool(keys & {"arch", "cachy", "manjaro"})
        if kind == "eopkg":
            return "solus" in keys
        return False

    def _create_package_loading_view(self):
        """Create the same centered roller geometry used by startup loading."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_hexpand(True)
        box.set_vexpand(True)

        spinner = Gtk.Spinner()
        spinner.set_size_request(64, 64)
        spinner.start()
        box.pack_start(spinner, False, False, 0)
        # Keep a strong reference so the spinner can be stopped explicitly when
        # inspection finishes or the user navigates away.
        box._package_loading_spinner = spinner
        return box

    def handle_package_open_request(self, package_path):
        """Open a local package without blocking GTK while its metadata is inspected."""
        package_path = os.path.realpath(os.fspath(package_path))
        kind = self._local_package_extension(package_path)
        if not kind or not os.path.isfile(package_path) or not self._local_package_supported_on_host(kind):
            return False

        current_name = self.main_stack.get_visible_child_name()
        if current_name not in ("package_view", "package_loading"):
            self._package_view_prev = {
                "child": self.main_stack.get_visible_child(),
                "header_visible": self.header_widget.get_visible(),
                "title": self.header_bar.props.title,
                "footer_revealed": self.reveal.get_reveal_child(),
                "back_visible": self.back_button.get_visible(),
            }

        # Supersede any older inspection. Workers are intentionally not killed;
        # their result is simply discarded if a newer request/back navigation wins.
        request_id = getattr(self, "_package_inspection_request_id", 0) + 1
        self._package_inspection_request_id = request_id

        for child_name in ("package_view", "package_loading"):
            old = self.main_stack.get_child_by_name(child_name)
            if old is not None:
                spinner = getattr(old, "_package_loading_spinner", None)
                if spinner is not None:
                    spinner.stop()
                gui_rs.stack_remove_child(self.main_stack, old, destroy=True)

        loading = self._create_package_loading_view()
        gui_rs.stack_attach_child(self.main_stack, loading, "package_loading", make_visible=False)
        self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.main_stack.set_visible_child(loading)

        # Match Terminal View: Package View owns this navigation flow, so prevent
        # header-menu actions from mutating global UI/application state until the
        # package/loading view has been closed.
        self._set_header_actions_sensitive(False)

        self.header_widget.hide()
        self.reveal.set_reveal_child(False)
        self.back_button.show()
        title = self.translations.get("package_view_title", "Install package")
        self.header_bar.props.title = f"LinuxToys: {title}"
        self.present()

        def worker():
            try:
                metadata = gui_rs.inspect_local_package(package_path) or {}
            except Exception as exc:
                logger.warning("Could not inspect local package %s: %s", package_path, exc)
                metadata = {}
            metadata.setdefault("kind", kind)
            metadata.setdefault("name", os.path.basename(package_path))
            GLib.idle_add(
                self._finish_package_inspection,
                request_id,
                package_path,
                metadata,
            )

        threading.Thread(
            target=worker,
            daemon=True,
            name="linuxtoys-package-inspection",
        ).start()
        return True

    def _finish_package_inspection(self, request_id, package_path, metadata):
        """Publish worker metadata and cross-fade the roller into Package View."""
        if request_id != getattr(self, "_package_inspection_request_id", 0):
            return False

        loading = self.main_stack.get_child_by_name("package_loading")
        if loading is None or self.main_stack.get_visible_child_name() != "package_loading":
            return False

        spinner = getattr(loading, "_package_loading_spinner", None)
        if spinner is not None:
            spinner.stop()

        old_package = self.main_stack.get_child_by_name("package_view")
        if old_package is not None:
            gui_rs.stack_remove_child(self.main_stack, old_package, destroy=True)

        view = package_view.PackageView(self, package_path, metadata)
        gui_rs.stack_attach_child(self.main_stack, view, "package_view", make_visible=False)
        self.main_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.main_stack.set_visible_child(view)
        gui_rs.stack_remove_child_after_transition(
            self.main_stack, loading, destroy=True
        )
        return False

    def enqueue_local_package(self, package_path, metadata):
        return self._appstream_runner.enqueue_local_package(package_path, metadata)

    def close_package_view(self, crossfade=False):
        visible_name = self.main_stack.get_visible_child_name()
        child = self.main_stack.get_child_by_name(visible_name) if visible_name in ("package_view", "package_loading") else None
        prev = self._package_view_prev
        if child is None:
            return False

        # Package View uses the same header-menu lock as Terminal View. Restore it
        # before returning to the exact view that opened the package.
        self._set_header_actions_sensitive(True)

        # Invalidate an in-flight inspector before restoring the previous view.
        self._package_inspection_request_id = getattr(self, "_package_inspection_request_id", 0) + 1
        spinner = getattr(child, "_package_loading_spinner", None)
        if spinner is not None:
            spinner.stop()

        if prev and prev.get("child") is not None and prev["child"].get_parent() is self.main_stack:
            transition = Gtk.StackTransitionType.CROSSFADE if crossfade else Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
            self.main_stack.set_transition_type(transition)
            self.main_stack.set_visible_child(prev["child"])
            self.header_bar.props.title = prev.get("title") or "LinuxToys"
            if prev.get("header_visible"):
                self.header_widget.show()
            else:
                self.header_widget.hide()
            self.reveal.set_reveal_child(bool(prev.get("footer_revealed")))
            if prev.get("back_visible"):
                self.back_button.show()
            else:
                self.back_button.hide()
        else:
            self.show_categories_view()

        self._package_view_prev = None
        gui_rs.stack_remove_child_after_transition(self.main_stack, child, destroy=True)
        return False

    def _setup_package_drag_and_drop(self):
        target = Gtk.TargetEntry.new("text/uri-list", 0, 0)
        self.main_stack.drag_dest_set(Gtk.DestDefaults.ALL, [target], Gdk.DragAction.COPY)
        self.main_stack.connect("drag-data-received", self._on_package_drag_data_received)

    def _on_package_drag_data_received(self, widget, context, x, y, selection, info, event_time):
        uris = selection.get_uris() or []
        accepted = False
        for uri in uris:
            file = Gio.File.new_for_uri(uri)
            path = file.get_path()
            if path and self.handle_package_open_request(path):
                accepted = True
                break
        Gtk.drag_finish(context, accepted, False, event_time)

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
            system_compat_keys = compat.get_system_compat_keys()
            if {"ostree", "ublue"} & system_compat_keys:
                GLib.idle_add(self._set_update_state, "reboot-ready")
                GLib.idle_add(self._show_ostree_deployment_warning)
            else:
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

    def _on_categories_startup_size_allocate(self, _widget, allocation):
        """Commit category geometry barriers after a real final FlowBox allocation."""
        if allocation.width <= 1 or allocation.height <= 1:
            return

        child_count = len(self.categories_flowbox.get_children())

        # Startup and language refresh intentionally share the same allocation
        # signal.  Publishing the last card or calling queue_resize() is not a
        # geometry barrier: GTK may still report the previous allocation until
        # this callback runs.
        if (
            getattr(self, "_language_transition_active", False)
            and getattr(self, "_language_categories_waiting_for_allocation", False)
            and (
                self._language_categories_expected_children <= 0
                or child_count == self._language_categories_expected_children
            )
        ):
            self._language_categories_waiting_for_allocation = False
            self._language_categories_allocation_complete = True
            self._language_categories_render_pending = False

        if self._categories_startup_transition_complete:
            return
        if not self._categories_startup_render_complete:
            return
        if not self._categories_startup_waiting_for_allocation:
            return
        if (
            self._categories_startup_expected_children > 0
            and child_count != self._categories_startup_expected_children
        ):
            return

        self._categories_startup_waiting_for_allocation = False
        self._categories_startup_allocation_complete = True

        # Every category surface now exists and has an allocation, so the native
        # watermark pass can no longer finish before later cards are registered.
        self._categories_loading_watermarks_flushed = False
        self._start_startup_watermark_flush()

    def _maybe_start_categories_loading_fade(self):
        """Reveal the main menu only when its complete startup snapshot is paint-ready."""
        if self._categories_startup_transition_complete:
            return False
        if self._appstream_initial_build_pending:
            return False
        if not (
            self._categories_startup_render_complete
            and self._categories_startup_allocation_complete
            and self._categories_loading_watermarks_flushed
        ):
            return False
        if not self.categories_loading_box.get_visible():
            return False
        if self._categories_loading_fade_source is not None:
            return False

        self._start_categories_loading_fade()
        return False

    def _start_categories_loading_fade(self):
        """Cross-fade the fully rendered main menu in while the startup roller fades out."""
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
        self.categories_view.set_sensitive(True)
        if self.should_start_random_timer and self.all_scripts:
            GLib.idle_add(self._deferred_start_random_scripts_refresh_timer)
        return False

    def _start_startup_watermark_flush(self):
        """Render native startup watermarks cooperatively with the GTK main loop."""
        if self._categories_loading_watermark_source is not None:
            return False

        flowbox = getattr(self, "categories_flowbox", None)
        if flowbox is None:
            self._categories_loading_watermarks_flushed = True
            return False

        self._categories_loading_watermark_source = GLib.idle_add(
            self._flush_one_startup_watermark
        )
        return False

    def _flush_one_startup_watermark(self):
        """Render one startup watermark without mistaking unallocated cards for done."""
        flowbox = getattr(self, "categories_flowbox", None)
        if flowbox is None:
            self._categories_loading_watermark_source = None
            self._categories_loading_watermarks_flushed = True
            self._maybe_start_categories_loading_fade()
            return False

        rendered = gui_rs.flush_category_watermarks(flowbox, 1)
        pending = gui_rs.has_pending_render_work(flowbox)

        if pending:
            if rendered:
                # More paint-ready work exists. Yield through the existing idle
                # source so GTK can interleave normal drawing/allocation work.
                return True

            # A registered category surface still needs rendering, but none was
            # paint-ready in this pass. This can happen when the FlowBox's final
            # size-allocate arrives before all nested native surfaces receive
            # theirs. Do not declare startup complete; retry on the next frame.
            self._categories_loading_watermark_source = GLib.timeout_add(
                16, self._flush_one_startup_watermark
            )
            return False

        self._categories_loading_watermark_source = None
        self._categories_loading_watermarks_flushed = True
        self._maybe_start_categories_loading_fade()
        return False

    def _hide_categories_loading_indicator(self):
        """Release startup only after the complete category snapshot is paint-ready."""
        if not hasattr(self, "categories_loading_box"):
            return False
        return self._maybe_start_categories_loading_fade()

    @staticmethod
    def _find_named_descendant(root, widget_name):
        """Find a named GTK descendant without rebuilding or rebinding its card."""
        if root is None:
            return None
        try:
            if root.get_name() == widget_name:
                return root
        except (AttributeError, TypeError):
            pass
        if isinstance(root, Gtk.Container):
            for child in root.get_children():
                found = AppWindow._find_named_descendant(child, widget_name)
                if found is not None:
                    return found
        return None

    def _refresh_root_category_translations_in_place(self):
        """Refresh root-menu language strings without invalidating its card widgets.

        Root category identity/artwork is language-independent. A locale switch must
        therefore never route the persistent root FlowBox through _render_categories().
        Match existing cards by their stable path and update only translated metadata.
        """
        categories = parser.get_categories(self.translations)
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
        translated_by_path = {
            category.get("path"): category
            for category in (specials_category, *categories)
            if category.get("path")
        }

        for child in self.categories_flowbox.get_children():
            widget = child.get_child() if isinstance(child, Gtk.FlowBoxChild) else child
            info = getattr(widget, "info", None)
            if widget is None or not isinstance(info, dict):
                continue

            category = translated_by_path.get(info.get("path"))
            if category is None:
                # A language switch is not a structural category refresh. Leave an
                # unmatched existing card intact rather than destroying the root UI.
                continue

            label = self._find_named_descendant(widget, "linuxtoys-native-name")
            if isinstance(label, Gtk.Label):
                escaped = GLib.markup_escape_text(str(category.get("name", "") or ""))
                label.set_markup(f"<b>{escaped}</b>")

            widget.info = category
            description = category.get("description", "")
            widget.set_tooltip_text(description or None)

        # Only the visible root menu needs a geometry barrier for translated text.
        # No card/watermark state is reset here.
        if self.main_stack.get_visible_child_name() == "categories":
            children = self.categories_flowbox.get_children()
            self._language_categories_expected_children = len(children)
            self._language_categories_waiting_for_allocation = True
            self._language_categories_allocation_complete = False
            self.categories_flowbox.queue_resize()
            self.categories_view.queue_resize()


    def _render_categories(self, categories):
        """Render a parsed category snapshot cooperatively on the GTK thread."""
        # Cancel any older publication that may still be draining. Incrementing the
        # generation makes its idle callback harmless without needing to remove a
        # source that may currently be dispatching.
        generation = getattr(self, "_category_render_generation", 0) + 1
        self._category_render_generation = generation
        if (
            getattr(self, "_language_transition_active", False)
            and self.main_stack.get_visible_child_name() == "categories"
        ):
            self._language_categories_render_pending = True

        startup_render = not self._categories_startup_transition_complete
        if startup_render:
            self._categories_startup_render_complete = False
            self._categories_startup_allocation_complete = False
            self._categories_startup_waiting_for_allocation = False
            self._categories_startup_expected_children = 0
            self._categories_loading_watermarks_flushed = False

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
        category_snapshot = [specials_category, *categories]
        if homebrew_catalog.enabled():
            category_snapshot.append(self._homebrew_category_info())

        # A language change only changes translated card metadata; the root category
        # structure and artwork normally remain identical. Rebind those native cards
        # in place so their Rust CategoryWatermarkState (and already-rendered pixbuf)
        # survives. The existing size-allocate tracking will then invalidate a
        # watermark only if translated text/scaling actually changes the card size.
        if getattr(self, "_language_transition_active", False):
            children = self.categories_flowbox.get_children()
            existing = []
            for child in children:
                widget = child.get_child() if isinstance(child, Gtk.FlowBoxChild) else child
                info = getattr(widget, "info", None)
                if widget is None or not isinstance(info, dict):
                    existing = []
                    break
                existing.append((widget, info))

            same_structure = (
                len(existing) == len(category_snapshot)
                and all(
                    old_info.get("path") == new_info.get("path")
                    for (_, old_info), new_info in zip(existing, category_snapshot)
                )
            )
            if same_structure:
                # A locale switch does not change category identity, artwork, or
                # native card structure. Update only the language-driven fields.
                # In particular, do not call gui_rs.update_item_card(): that generic
                # rebind unnecessarily touches the complete native card spec.
                rebound = True
                translated_cards = []
                for (widget, _old_info), cat in zip(existing, category_snapshot):
                    label = self._find_named_descendant(
                        widget, "linuxtoys-native-name"
                    )
                    if not isinstance(label, Gtk.Label):
                        rebound = False
                        break
                    translated_cards.append((widget, label, cat))

                # Validate every card before changing any of them. If the expected
                # native hierarchy is missing, retain the existing full-rebuild
                # fallback below.
                if rebound:
                    for widget, label, cat in translated_cards:
                        label.set_text(str(cat.get("name", "") or ""))
                        widget.info = cat
                        description = cat.get("description", "")
                        widget.set_tooltip_text(description or None)

                    if self.main_stack.get_visible_child_name() == "categories":
                        self._language_categories_render_pending = True
                        self._language_categories_expected_children = len(children)
                        self._language_categories_waiting_for_allocation = True
                        self._language_categories_allocation_complete = False
                        # Only translated text changed. Let GTK settle any genuine
                        # geometry change; the native watermark state stays intact.
                        self.categories_flowbox.queue_resize()
                        self.categories_view.queue_resize()
                    return

        self.categories_flowbox.foreach(
            lambda widget: self.categories_flowbox.remove(widget)
        )

        pending = iter(category_snapshot)

        # Four cards keeps each GTK burst short while normally filling enough of
        # the first viewport to begin the startup transition immediately.
        batch_size = 4
        first_batch = True

        def append_batch():
            nonlocal first_batch

            if self._category_render_generation != generation:
                return False

            added = 0
            while added < batch_size:
                try:
                    cat = next(pending)
                except StopIteration:
                    if getattr(self, "_language_transition_active", False):
                        self._language_categories_expected_children = len(
                            self.categories_flowbox.get_children()
                        )
                        self._language_categories_waiting_for_allocation = True
                        self._language_categories_allocation_complete = False
                    if startup_render:
                        self._categories_startup_expected_children = len(
                            self.categories_flowbox.get_children()
                        )
                        self._categories_startup_render_complete = True
                        self._categories_startup_waiting_for_allocation = True
                        # Force one allocation of the final, complete FlowBox. The
                        # size-allocate callback is the startup geometry barrier.
                        self.categories_flowbox.queue_resize()
                        self.categories_view.queue_resize()
                    elif getattr(self, "_language_transition_active", False):
                        self.categories_flowbox.queue_resize()
                    return False

                # Root-menu cards have an explicit structural role. Do not infer
                # it from mutable navigation state while this cooperative render
                # yields back to the GTK main loop between batches.
                widget = self.create_item_widget(cat, force_category=True)
                description = cat.get("description", "")
                widget.set_tooltip_text(description or None)
                self.categories_flowbox.add(widget)
                widget.show_all()
                added += 1

            if first_batch:
                first_batch = False

            return True

        # Publish the first small batch now so the parser-ready callback immediately
        # produces useful UI, then yield between all remaining batches.
        if append_batch():
            GLib.idle_add(append_batch)

    def load_categories(self):
        """Load categories synchronously for explicit refresh/fallback paths."""
        # A progressive population may already have parsed the root category list
        # even though the recursive cache is not complete yet. Reuse it when present.
        categories = self.category_cache.get_categories()
        if not categories:
            categories = parser.get_categories(self.translations)
        self._render_categories(categories)

    def _category_items_for_display(self, category_info):
        """Return the exact item list used by normal category browsing."""
        category_path = category_info["path"]
        if category_info.get("is_homebrew_category"):
            return appstream_parser.get_homebrew_entries()
        if category_info.get("is_aur_category"):
            # Keep AUR as a lazy Rust-backed sequence. Converting this to list()
            # materializes tens of thousands of Python dictionaries at once.
            return aur_cache.browse_entries()
        if category_info.get("is_linuxtoys_specials"):
            return list(
                self.category_cache.get_linuxtoys_special_categories(self.translations)
            )
        if category_info.get("is_linuxtoys_specials_category"):
            return list(
                self.category_cache.get_linuxtoys_special_scripts(
                    category_info.get("specials_category_path", "")
                )
            )
        if self.category_cache.is_populated:
            scripts = self.category_cache.get_scripts_for_category(category_path)
            if scripts:
                return list(scripts)
        return list(
            parser.get_scripts_for_category(category_path, self.translations)
        )

    def _partition_category_items(self, category_info, items=None):
        """Split one category into Available and Installed without changing order."""
        available = []
        installed = []
        if items is None:
            items = self._category_items_for_display(category_info)
        for item in items:
            if item.get("is_script") and self._is_script_removable(item):
                installed.append(item)
            else:
                # Subcategories, create-script entries and every other structural
                # card stay exactly where normal category browsing puts them.
                available.append(item)
        return available, installed

    def _category_has_installed_items(self, category_info):
        """Return whether this category needs the Available/Installed tab UI."""
        if not category_info or category_info.get("display_mode", "menu") == "checklist":
            return False
        # AUR is a huge lazy Rust-backed collection. Probing the generic
        # Available/Installed split would enumerate the complete repository and
        # defeat paged browsing. Individual AUR cards still refresh their normal
        # installed/removable state after transactions.
        if category_info.get("is_aur_category") or category_info.get("is_homebrew_category"):
            return False
        if (
            category_info.get("is_linuxtoys_specials")
            and not self.category_cache.is_populated
        ):
            return False
        _available, installed = self._partition_category_items(category_info)
        return bool(installed)

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

        scripts = self._category_items_for_display(category_info)
        category_tab = getattr(flowbox, "_linuxtoys_category_tab", None)
        if category_info.get("is_homebrew_category") and category_tab == "installed":
            scripts = []
        elif category_tab in ("available", "installed") and not category_info.get("is_homebrew_category"):
            available, installed = self._partition_category_items(
                category_info, scripts
            )
            scripts = available if category_tab == "available" else installed
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

        def flush_new_category_watermarks():
            """Flush newly allocated native category cards after this population pass."""
            if not state_is_current():
                return False
            gui_rs.flush_category_watermarks(flowbox)
            return False

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

        def add_card_batch(batch_infos):
            """Create/insert ordinary cards in one Rust call when possible."""
            batch_infos = list(batch_infos)
            widgets = self.create_native_item_batch(
                flowbox,
                batch_infos,
                checklist=checklist_mode,
                allow_drag=allow_drag,
            )
            if widgets is None:
                fallback = [add_card(info) for info in batch_infos]
                return fallback

            for widget, info in zip(widgets, batch_infos):
                description = info.get("description", "")
                widget.set_tooltip_text(description or None)
                widget.set_opacity(0.0)
            return widgets

        def populate_timed_batch():
            if not state_is_current():
                state["timer_id"] = None
                return False

            target = min(state["target_index"], len(scripts))
            if state["next_index"] >= target:
                state["timer_id"] = None
                return False

            stop = min(target, state["next_index"] + frame_batch_size)
            batch_infos = scripts[state["next_index"]:stop]
            batch_widgets = add_card_batch(batch_infos)
            state["next_index"] = stop
            for widget in batch_widgets:
                widget.show_all()

            GLib.idle_add(
                flush_new_category_watermarks,
                priority=GLib.PRIORITY_LOW,
            )

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
            seed_infos = scripts[state["next_index"]:seed_count]
            seed_widgets = add_card_batch(seed_infos)
            state["next_index"] = seed_count
            for widget in seed_widgets:
                widget.show_all()

            GLib.idle_add(
                flush_new_category_watermarks,
                priority=GLib.PRIORITY_LOW,
            )

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

    def _activate_aur_category(self, category_info):
        """Gate AUR behind explicit consent, then open it like a normal category."""
        if not aur_cache.enabled():
            response = gtk_dialogs.run_message_dialog(
                self,
                title=self.translations.get("aur_warning_title", "Enable the AUR?"),
                secondary_text=self.translations.get(
                    "aur_warning_message",
                    "The Arch User Repository contains user-produced build scripts "
                    "that are not reviewed or supported by Arch Linux. Installing "
                    "AUR packages can execute package build instructions on your "
                    "system. Review packages and PKGBUILDs before installing them.",
                ),
                message_type=Gtk.MessageType.WARNING,
                buttons=[
                    (
                        self.translations.get("aur_warning_return", "Return"),
                        Gtk.ResponseType.CANCEL,
                    ),
                    (
                        self.translations.get("aur_warning_enable", "Enable AUR"),
                        Gtk.ResponseType.YES,
                    ),
                ],
                default_response=Gtk.ResponseType.CANCEL,
            )
            if response != Gtk.ResponseType.YES:
                return
            aur_cache.enable()

        # Navigate immediately after consent so the pending download/build has
        # a visible destination instead of leaving the category button inert.
        self._open_aur_category_view(category_info, loading=True)
        page = self.scripts_view
        flowbox = self.scripts_flowbox

        def finish_loading(error_message=None):
            page._linuxtoys_aur_spinner.stop()
            page._linuxtoys_aur_spinner.hide()
            page._linuxtoys_category_content.set_sensitive(True)
            # Back navigation or another category selection must never be undone
            # by a late worker completion.
            if self.main_stack.get_visible_child() is not page:
                return False
            if error_message is not None:
                gtk_dialogs.run_message_dialog(
                    self,
                    title=self.translations.get("aur_refresh_failed_title", "AUR metadata unavailable"),
                    secondary_text=error_message,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=[("OK", Gtk.ResponseType.OK)],
                    default_response=Gtk.ResponseType.OK,
                )
            else:
                self._load_scripts_into_flowbox(flowbox, category_info, defer_initial=True)
            return False

        def worker():
            try:
                # The refresh publishes catalog.bin atomically. Do not materialize
                # the AUR here: category browsing is paged directly from Rust.
                aur_cache.refresh_if_stale()
                # Prewarm the lazy catalog off GTK too: loading/filtering the
                # binary and querying pacman's repositories can be expensive.
                aur_cache.browse_entries()
            except Exception as error:
                logger.warning("AUR catalog refresh failed: %s", error)
                GLib.idle_add(finish_loading, str(error))
                return

            GLib.idle_add(finish_loading)

        threading.Thread(
            target=worker,
            daemon=True,
            name="linuxtoys-aur-enable",
        ).start()

    def _open_aur_category_view(self, category_info, *, loading=False):
        """Open AUR through the same retained/deferred category-view machinery."""
        self._retain_current_category_view()

        self.view_counter += 1
        new_view_name = f"scripts_{self.view_counter}"
        new_flowbox = self.create_flowbox()

        # AUR uses a single lazy/paged FlowBox rather than the normal
        # Available/Installed category browser, but it should still use the same
        # in-stack category-header layout as every other category page.
        content_name = f"{new_view_name}__content"
        content_view = gui_rs.stack_add_scrolled_flowbox(
            self.main_stack, new_flowbox, content_name
        )
        self.main_stack.remove(content_view)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        category_header = header.create_header(self.translations, category_info)
        page.pack_start(category_header, False, False, 8)
        if loading:
            overlay = Gtk.Overlay()
            overlay.add(content_view)
            spinner = Gtk.Spinner()
            spinner.set_size_request(64, 64)
            spinner.set_halign(Gtk.Align.CENTER)
            spinner.set_valign(Gtk.Align.CENTER)
            spinner.set_no_show_all(True)
            overlay.add_overlay(spinner)
            page.pack_start(overlay, True, True, 0)
            page._linuxtoys_aur_spinner = spinner
            content_view.set_sensitive(False)
        else:
            page.pack_start(content_view, True, True, 0)

        page._linuxtoys_category_header = category_header
        page._linuxtoys_category_content = content_view
        page._linuxtoys_category_info = category_info

        gui_rs.stack_attach_child(
            self.main_stack, page, new_view_name, make_visible=False
        )
        page.show_all()

        self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.scripts_flowbox = new_flowbox
        self.scripts_view = page
        self.show_scripts_view(category_info)

        if loading:
            spinner.show()
            spinner.start()
            return False

        # Match normal category navigation: let the slide start with an attached
        # empty destination, then lazily materialize the first viewport.
        self._load_scripts_into_flowbox(
            new_flowbox,
            category_info,
            defer_initial=True,
        )
        return False

    def _show_aur_operation_failure(self, name, output):
        """Show captured PTY output for a failed AUR install/removal."""
        gtk_dialogs.run_message_dialog(
            self,
            title=self.translations.get(
                "aur_operation_failed_title", "AUR operation failed"
            ),
            secondary_text=self.translations.get(
                "aur_operation_failed_message",
                "The operation for '{name}' failed. Terminal output:\n\n{output}",
            ).format(name=name, output=(output or "").strip()),
            message_type=Gtk.MessageType.ERROR,
            buttons=[("OK", Gtk.ResponseType.OK)],
            default_response=Gtk.ResponseType.OK,
        )
        return False

    def _start_aur_refresh_if_enabled(self):
        """Refresh an already-enabled AUR catalog in the background when stale."""
        if not aur_cache.enabled():
            return False

        def worker():
            try:
                aur_cache.refresh_if_stale()

            except Exception as error:
                logger.warning("Background AUR catalog refresh failed: %s", error)

        threading.Thread(
            target=worker,
            daemon=True,
            name="linuxtoys-aur-cache",
        ).start()
        return False

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
        if info.get("appstream_source") == "homebrew":
            # Brew is already required for exposing the source; formula dependencies
            # are handled by Brew, and overlay dependencies by the queued runner.
            if not homebrew_catalog.enabled():
                self._check_homebrew_source()
                return
            deps = [info]
        else:
            deps = asyncio.run(self._process_needed_scripts([info]))
        if not deps:
            return

        if info.get("is_appstream_entry"):
            # AUR entries deliberately do not expose an app page, but they still
            # use the serialized AppStream queue/runner. Reuse the normal script
            # confirmation UI before handing the resolved transaction to it.
            if info.get("is_aur_entry"):
                if not needed_helper.show_run_confirmation_dialog(
                    self, self.translations, deps
                ):
                    return

            # AppStream/AUR installs are owned by the background queue until the
            # operation succeeds, fails, or is cancelled.
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

    def _calculate_default_window_size(self):
        """Choose an initial size in GTK logical pixels, keeping desktop margins."""
        workarea = self._primary_monitor_workarea()
        if workarea is None or min(workarea) <= 0:
            return (920, 630)
        available_width, available_height = workarea
        width = min(1440, max(920, round(available_width * 0.72)))
        height = min(960, max(630, round(available_height * 0.78)))
        # Smaller displays must take precedence over the preferred minimum.
        return (
            max(1, min(width, int(available_width * 0.90))),
            max(1, min(height, int(available_height * 0.90))),
        )

    def _primary_monitor_workarea(self):
        """Return the primary monitor's usable (non-panel) width and height."""
        display = Gdk.Display.get_default()
        if display is not None and hasattr(display, "get_primary_monitor"):
            monitor = display.get_primary_monitor()
            if monitor is None and display.get_n_monitors() > 0:
                monitor = display.get_monitor(0)
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

    def _start_categories_unmaximize_reflow(self):
        """Reflow the root menu after a maximized allocation becomes stale."""
        if getattr(self, "random_scripts_flowbox", None) is None:
            return

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

    def _on_window_state_changed(self, _widget, event):
        """Keep stale maximized root-menu geometry out of restored sizing."""
        changed = bool(event.changed_mask & Gdk.WindowState.MAXIMIZED)
        maximized = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
        if not changed or maximized:
            return False

        if not hasattr(self, "main_stack"):
            return False

        if self.main_stack.get_visible_child_name() == "categories":
            self._categories_geometry_stale = False
            self._start_categories_unmaximize_reflow()
        else:
            # The root menu is hidden, so it will not receive the restored
            # allocation now. Reflow it when navigation exposes it again.
            self._categories_geometry_stale = True

        return False

    def _finish_featured_unmaximize(self):
        """Re-enable Featured after the restored window geometry has settled."""
        self._featured_unmaximize_timer = None

        if self.main_stack.get_visible_child_name() != "categories":
            self.random_scripts_flowbox.show()
            return False

        # At this point the category FlowBox has the restored viewport width, so the
        # existing Featured geometry calculation can safely mirror its real columns.
        self._categories_geometry_stale = False
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

        # Restart the speculative navigation prewarm on every configure event. It
        # intentionally fires after the normal resize settle work, so interactive
        # resizing never competes with hidden-page reconstruction.
        self._navigation_prewarm_generation += 1
        if self._navigation_prewarm_timer is not None:
            GLib.source_remove(self._navigation_prewarm_timer)
        prewarm_generation = self._navigation_prewarm_generation
        self._navigation_prewarm_timer = GLib.timeout_add(
            self.FEATURED_RESIZE_DEBOUNCE_MS
            + self._navigation_prewarm_extra_delay_ms,
            self._run_navigation_resize_prewarm,
            prewarm_generation,
            priority=GLib.PRIORITY_LOW,
        )
        return False

    def _run_navigation_resize_prewarm(self, generation):
        """Prewarm hidden Back targets after the final resize geometry settles."""
        if generation != self._navigation_prewarm_generation:
            return False
        self._navigation_prewarm_timer = None

        # A new configure may have landed between this timer and the normal settle
        # callback. Never build against geometry that is still moving.
        if self._window_resize_pending or self._window_resize_settling:
            return False

        # Reallocate the persistent hidden root menu to the settled Stack geometry.
        # Unlike category history it is a singleton, so rebuilding it would disturb
        # Featured/history state. Preallocation is enough to avoid doing its first
        # new-size layout on the Back click.
        if (
            hasattr(self, "categories_loading_overlay")
            and self.main_stack.get_visible_child_name() != "categories"
        ):
            allocation = self.main_stack.get_allocation()
            if allocation.width > 1 and allocation.height > 1:
                self.categories_loading_overlay.size_allocate(allocation)
            self.categories_flowbox.queue_resize()
            self.categories_view.queue_resize()
            gui_rs.flush_category_watermarks(self.categories_loading_overlay)

            # If unmaximize marked the hidden root stale, consume that work now
            # rather than waiting for root navigation.
            if getattr(self, "_categories_geometry_stale", False):
                self._categories_geometry_stale = False
                self._featured_last_layout = None
                self._featured_layout_metrics = None
                self._refresh_random_scripts_display(force=False)

        self._prewarm_retained_navigation_views(generation)
        return False

    def _flush_visible_category_watermarks(self):
        """Apply deferred native category watermarks in the visible view."""
        if not hasattr(self, "main_stack"):
            return
        root = self.main_stack.get_visible_child()
        if root is not None:
            gui_rs.flush_category_watermarks(root)

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
            startup_watermarks_active = (
                getattr(self, "_categories_loading_watermark_source", None) is not None
            )
            if not startup_watermarks_active:
                self._flush_visible_category_watermarks()

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
        if getattr(self, "_navigation_prewarm_timer", None):
            GLib.source_remove(self._navigation_prewarm_timer)
            self._navigation_prewarm_timer = None
        self._navigation_prewarm_generation += 1
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

    def _on_language_visible_size_allocate(self, widget, allocation):
        """Commit a translated non-category view only after a fresh allocation."""
        if not getattr(self, "_language_transition_active", False):
            return
        if allocation.width <= 1 or allocation.height <= 1:
            return
        handler_id = getattr(self, "_language_visible_allocate_handler", None)
        if handler_id is not None:
            try:
                widget.disconnect(handler_id)
            except (RuntimeError, TypeError):
                pass
            self._language_visible_allocate_handler = None
        self._language_visible_allocation_complete = True

    def _arm_language_visible_allocation_barrier(self, widget):
        """Require an allocation produced by the translated rebuild, not an old one."""
        old_handler = getattr(self, "_language_visible_allocate_handler", None)
        old_widget = getattr(self, "_language_visible_allocate_widget", None)
        if old_handler is not None and old_widget is not None:
            try:
                old_widget.disconnect(old_handler)
            except (RuntimeError, TypeError):
                pass
        self._language_visible_allocation_complete = False
        self._language_visible_allocate_widget = widget
        self._language_visible_allocate_handler = widget.connect(
            "size-allocate", self._on_language_visible_size_allocate
        )
        widget.queue_resize()

    def _on_language_featured_size_allocate(self, grid, allocation):
        """Commit the hidden language Featured rebuild after its real allocation."""
        if not getattr(self, "_language_transition_active", False):
            return
        if allocation.width <= 1 or allocation.height <= 1 or not grid.get_children():
            return
        handler_id = getattr(self, "_language_featured_allocate_handler", None)
        if handler_id is not None:
            grid.disconnect(handler_id)
            self._language_featured_allocate_handler = None
        self._language_featured_allocation_complete = True

    def _show_language_search_loading(self):
        """Replace the old Search snapshot with a centered roller while translating."""
        if not hasattr(self, "search_language_loading_box"):
            return
        if self._language_search_loading_fade_source is not None:
            GLib.source_remove(self._language_search_loading_fade_source)
            self._language_search_loading_fade_source = None
        self._language_search_loading_active = True
        self.search_view.set_opacity(0.0)
        self.search_language_loading_box.set_opacity(1.0)

        # The loading box is deliberately no-show-all so the application's startup
        # show_all() cannot expose it. Its children therefore also need to be shown
        # explicitly when this transient overlay is activated.
        self.search_language_loading_spinner.show()
        self.search_language_loading_box.show()
        self.search_language_loading_spinner.start()

    def _start_language_search_loading_fade(self):
        """Cross-fade the completed translated Search view in over its roller."""
        if not self._language_search_loading_active:
            return False
        if self._language_search_loading_fade_source is not None:
            return False
        self._language_search_loading_fade_started_us = GLib.get_monotonic_time()
        self.search_view.set_opacity(0.0)
        self.search_language_loading_box.set_opacity(1.0)
        self._language_search_loading_fade_source = GLib.timeout_add(
            16, self._step_language_search_loading_fade
        )
        return False

    def _step_language_search_loading_fade(self):
        started = self._language_search_loading_fade_started_us
        if started is None:
            self._language_search_loading_fade_source = None
            return False

        elapsed_ms = (GLib.get_monotonic_time() - started) / 1000.0
        duration = max(1, self._language_search_loading_fade_duration_ms)
        progress = min(1.0, elapsed_ms / duration)
        self.search_view.set_opacity(progress)
        self.search_language_loading_box.set_opacity(1.0 - progress)

        if progress < 1.0:
            return True

        self._language_search_loading_fade_source = None
        self._language_search_loading_fade_started_us = None
        self._language_search_loading_active = False
        self.search_view.set_opacity(1.0)
        self.search_language_loading_box.set_opacity(1.0)
        self.search_language_loading_spinner.stop()
        self.search_language_loading_box.hide()
        return False

    def on_language_changed(self, new_language_code):
        """Cross-fade a complete language refresh instead of exposing rebuild work."""
        if getattr(self, "_language_transition_active", False):
            self._language_transition_target = new_language_code
            return

        self._language_transition_active = True
        self._language_transition_target = new_language_code
        self._language_transition_search_query = (
            self.search_entry.get_text().strip()
            if self.main_stack.get_visible_child_name() == "search"
            else ""
        )
        self._language_search_transition_owned = (
            self.main_stack.get_visible_child_name() == "search"
        )
        if self._language_search_transition_owned:
            self._show_language_search_loading()
        self._language_transition_phase = "out"
        self._language_transition_started_us = GLib.get_monotonic_time()
        self._language_transition_duration_ms = 120
        self._language_categories_render_pending = False
        self._language_categories_waiting_for_allocation = False
        self._language_categories_expected_children = 0
        self._language_categories_allocation_complete = False
        self._language_featured_refresh_started = False
        self._language_featured_allocation_complete = False
        self._language_search_refresh_pending = False
        self._language_visible_allocation_complete = False
        self._language_visible_allocate_handler = None
        self._language_visible_allocate_widget = None
        handler_id = getattr(self, "_language_featured_allocate_handler", None)
        if handler_id is not None:
            self.random_scripts_flowbox.disconnect(handler_id)
            self._language_featured_allocate_handler = None

        if self._language_transition_source is not None:
            GLib.source_remove(self._language_transition_source)
        self._language_transition_source = GLib.timeout_add(
            16, self._step_language_transition
        )

    def _commit_language_search_refresh(self, query):
        """Rerun a preserved search after the language transaction is fully committed."""
        query = str(query or "").strip()
        if not query:
            return False
        if self.main_stack.get_visible_child_name() != "search":
            return False
        if self.search_entry.get_text().strip() != query:
            return False

        # This is deliberately after _language_transition_active becomes False.
        # Intermediate cache publication may prepare the hidden search view, but
        # the final visible result must be produced by the committed language state.
        self._perform_search(query)
        return False

    def _step_language_transition(self):
        """Drive the fade-out/fade-in phases around a hidden translated rebuild."""
        phase = self._language_transition_phase
        started = self._language_transition_started_us
        if phase not in ("out", "in") or started is None:
            self._language_transition_source = None
            return False

        elapsed_ms = (GLib.get_monotonic_time() - started) / 1000.0
        duration = max(1, self._language_transition_duration_ms)
        progress = min(1.0, elapsed_ms / duration)
        search_transition_owned = (
            self.main_stack.get_visible_child_name() == "search"
            and self._language_search_transition_owned
        )
        if not search_transition_owned:
            self.main_stack.set_opacity(1.0 - progress if phase == "out" else progress)

        if progress < 1.0:
            return True

        self._language_transition_source = None
        if phase == "out":
            if not search_transition_owned:
                self.main_stack.set_opacity(0.0)
            self._language_transition_phase = "waiting"
            self._apply_language_change_hidden(self._language_transition_target)
            GLib.idle_add(self._wait_for_language_render_ready)
        else:
            self.main_stack.set_opacity(1.0)
            self._language_transition_phase = None
            self._language_transition_started_us = None
            self._language_transition_active = False
            self._language_transition_target = None
            self._language_featured_refresh_started = False

            final_search_query = getattr(
                self, "_language_transition_search_query", ""
            )
            self._language_transition_search_query = ""
            if (
                final_search_query
                and self.main_stack.get_visible_child_name() == "search"
                and not self._language_search_transition_owned
            ):
                GLib.idle_add(
                    self._commit_language_search_refresh,
                    final_search_query,
                )

            self._language_search_transition_owned = False

            if (
                self.main_stack.get_visible_child_name() == "categories"
                and self.should_start_random_timer
                and self.all_scripts
                and self.random_scripts_flowbox.get_children()
            ):
                self._restart_random_scripts_refresh_timer()
        return False

    def _apply_language_change_hidden(self, new_language_code):
        """Apply translations while main-stack content is fully transparent."""
        from . import lang_utils

        self.translations = lang_utils.load_translations(new_language_code)
        self.search_engine.translations = self.translations
        self.script_cache = search_helper.ScriptCache()
        self.category_cache = search_helper.CategoryCache()
        self.search_engine.set_cache(self.script_cache)
        self.all_scripts = []

        self.search_entry.set_placeholder_text(
            self.translations.get("search_placeholder", "Search features")
        )
        if self.random_scripts_label:
            featured_label = self.translations.get("featured_scripts", "Try These")
            self.random_scripts_label.set_markup(f"<big><b>{featured_label}</b></big>")

        # The entire stack is already transparent. Reset Featured without
        # collapsing its revealers, otherwise the SLIDE_DOWN animation changes the
        # menu requisition while translated category geometry is being measured.
        self._prepare_featured_language_rebuild()

        # Establish every visible-view readiness flag before the replacement cache
        # worker is allowed to publish.  Search in particular sets
        # _language_search_refresh_pending here; starting the worker first allowed
        # publish_completed_runtime() to clear the flag and arm its allocation
        # barrier, only for this refresh to set the flag back to True afterward.
        # That left the language transaction permanently stuck in the waiting phase.
        self._refresh_ui_with_new_translations()
        # The root FlowBox has already been translated in place above. Rebuild only
        # the backing parser/search/Featured data; top_level_ready must not call
        # _render_categories() for a mere locale change.
        self._populate_runtime_caches(catalog_refresh=True)

    def _wait_for_language_render_ready(self):
        """Reveal only after structural and native allocation-dependent work is done."""
        if not getattr(self, "_language_transition_active", False):
            return False

        visible_name = self.main_stack.get_visible_child_name()
        root = self.main_stack.get_visible_child()
        if root is None:
            return True

        allocation = root.get_allocation()
        if allocation.width <= 1 or allocation.height <= 1:
            root.queue_resize()
            return True

        # Category geometry is only a language-transition barrier when Categories
        # is actually the visible Stack page. Hidden Gtk.Stack children are not
        # guaranteed to receive a fresh allocation, so allowing their cooperative
        # rebuild to block Search/utility/app-page transitions can deadlock forever.
        if visible_name == "categories" and self._language_categories_render_pending:
            return True

        if visible_name == "search" and self._language_search_refresh_pending:
            return True

        if (
            visible_name == "search"
            and self._language_search_loading_active
            and self._language_search_loading_fade_source is None
        ):
            self._start_language_search_loading_fade()

        if visible_name == "categories":
            # The translated category snapshot must have received a *new* real
            # allocation before Featured is allowed to measure it.  Positive old
            # allocations are deliberately insufficient here.
            if not self._language_categories_allocation_complete:
                allocation = self.categories_flowbox.get_allocation()
                self.categories_flowbox.queue_resize()
                self.categories_view.queue_resize()
                return True
            if not self.all_scripts:
                return True
            if not self._language_featured_refresh_started:
                self._language_featured_refresh_started = True
                self._language_featured_allocation_complete = False
                self._language_featured_allocate_handler = (
                    self.random_scripts_flowbox.connect(
                        "size-allocate", self._on_language_featured_size_allocate
                    )
                )
                # Language refresh owns Featured while hidden.  Bypass the normal
                # startup/resize entry points so only one calculation can consume
                # this settled category geometry.
                self._refresh_random_scripts_display(force=True)

                # A zero-capacity Featured layout is a valid completed state. The
                # Featured controller intentionally leaves the grid empty when no
                # complete row fits; do not wait for children/allocation that cannot
                # exist in that case.
                if (
                    not self.random_scripts_flowbox.get_children()
                    and self._calculate_random_scripts_count() <= 0
                ):
                    handler_id = getattr(
                        self, "_language_featured_allocate_handler", None
                    )
                    if handler_id is not None:
                        self.random_scripts_flowbox.disconnect(handler_id)
                        self._language_featured_allocate_handler = None
                    self._language_featured_allocation_complete = True
                    return True

                self.random_scripts_flowbox.queue_resize()
                self.featured_scripts_container.queue_resize()
                return True
            featured_children = self.random_scripts_flowbox.get_children()
            if (
                not self._language_featured_allocation_complete
                or (
                    not featured_children
                    and self._calculate_random_scripts_count() > 0
                )
            ):
                return True

        if visible_name != "categories":
            if not self._language_visible_allocation_complete:
                root.queue_resize()
                return True

            # App pages have additional deferred layout work: wrapped text height,
            # screenshots, extension/body layout, and their adaptive Featured fill.
            if visible_name == "app_page" and hasattr(root, "language_render_ready"):
                if not root.language_render_ready():
                    root.queue_resize()
                    return True

        # Rust owns readiness for allocation-dependent native decoration. Flush a
        # small batch per main-loop turn and do not reveal zero/stale allocations.
        gui_rs.flush_category_watermarks(root, 2)
        if gui_rs.has_pending_render_work(root):
            root.queue_resize()
            return True

        self._language_transition_phase = "in"
        self._language_transition_started_us = GLib.get_monotonic_time()
        self._language_transition_duration_ms = 180
        self._language_transition_source = GLib.timeout_add(
            16, self._step_language_transition
        )
        return False

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
        if current_view not in (
            "app_page",
            "appstream_queue",
            "installed_features",
            "search",
        ):
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

        # Root category widgets are persistent UI. A language change updates only
        # their translated strings; it is not a structural category publication.
        self._refresh_root_category_translations_in_place()

        # Refresh footer translations
        self.reveal.update_translations(self.translations)

        # Queue and Installed Features are persistent utility views whose rows are
        # rendered directly from self.translations. Refresh them in place and keep
        # their utility-view header state instead of falling through to category
        # navigation refresh logic from the view they were opened from.
        if current_view == "appstream_queue":
            # Recreate instead of reconciling the visible instance in place.  This
            # gives the language transaction a clean widget generation and avoids
            # retaining old translated labels/callback bindings between refreshes.
            old_view = self.main_stack.get_child_by_name("appstream_queue")
            if old_view is not None:
                self.main_stack.remove(old_view)
                old_view.destroy()
            queue_view = appstream_queue.AppStreamQueueView(self)
            self.main_stack.add_named(queue_view, "appstream_queue")
            queue_view.show_all()
            self.main_stack.set_visible_child(queue_view)
            self._arm_language_visible_allocation_barrier(queue_view)
            self.header_widget.hide()
            self.reveal.set_reveal_child(False)
            self.back_button.show()
            title = self.translations.get("installation_queue", "Installation Queue")
            self.header_bar.props.title = f"LinuxToys: {title}"
            return

        if current_view == "installed_features":
            old_view = self.main_stack.get_child_by_name("installed_features")
            if old_view is not None:
                self.main_stack.remove(old_view)
                old_view.destroy()
            installed_view = installed_features.InstalledFeaturesView(self)
            self.main_stack.add_named(installed_view, "installed_features")
            installed_view.show_all()
            self.main_stack.set_visible_child(installed_view)
            self._arm_language_visible_allocation_barrier(installed_view)
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

            # The outer language transaction already owns the cross-fade.  Do not
            # start the app-page-specific Stack crossfade inside it; replace the page
            # while the whole stack is transparent and wait for the new page itself.
            self.open_app_page(fresh_info or app_page_info, preserve_previous=True)
            page = self.main_stack.get_child_by_name("app_page")
            if page is not None:
                self._arm_language_visible_allocation_barrier(page)
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

        # Search results are snapshots of the old translated search/category caches.
        # Keep the search surface active while hidden, then let the runtime-cache
        # completion callback rerun the exact query against the new language.
        if current_view == "search":
            if self.current_category_info:
                self._refresh_navigation_stack_translations()
                updated_category_info = self._get_fresh_category_info_with_translations()
                if updated_category_info:
                    self.current_category_info = updated_category_info
                self._search_origin_needs_language_refresh = True

            self._language_search_refresh_pending = bool(
                self.search_entry.get_text().strip()
            )
            self.main_stack.set_visible_child_name("search")
            self._update_search_header()
            self.back_button.show()
            self.reveal.set_reveal_child(False)
            self._disable_drag_and_drop()
            if not self._language_search_refresh_pending:
                self._language_visible_allocation_complete = True
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

            # Reload the scripts view with new translations. Category views are
            # retained native GtkScrolledWindow/FlowBox surfaces rather than rebuilt
            # here, so unlike app pages they may keep exactly the same allocation.
            # Arm the language barrier before rebinding their children, then accept
            # the already-valid allocation if GTK has no geometry change to emit.
            category_view = self.main_stack.get_visible_child()
            if category_view is not None:
                self._arm_language_visible_allocation_barrier(category_view)

            self.load_scripts(self.current_category_info)

            if (
                category_view is not None
                and not self._language_visible_allocation_complete
            ):
                allocation = category_view.get_allocation()
                if allocation.width > 1 and allocation.height > 1:
                    handler_id = getattr(
                        self, "_language_visible_allocate_handler", None
                    )
                    if handler_id is not None:
                        try:
                            category_view.disconnect(handler_id)
                        except (RuntimeError, TypeError):
                            pass
                        self._language_visible_allocate_handler = None
                    self._language_visible_allocate_widget = None
                    self._language_visible_allocation_complete = True

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

        # Synthetic/special categories do not live below parser.SCRIPTS_DIR, so
        # rebuild their translated metadata explicitly instead of falling back to
        # the stale current_category_info snapshot.
        if (
            self.current_category_info.get("is_linuxtoys_specials")
            or current_path == "specials://root"
        ):
            refreshed = dict(self.current_category_info)
            refreshed.update(
                {
                    "name": self.translations.get("specials", "Specials"),
                    "description": self.translations.get(
                        "specials_desc",
                        "LinuxToys-curated software and scripts.",
                    ),
                    "path": "specials://root",
                    "is_linuxtoys_specials": True,
                }
            )
            return refreshed

        if self.current_category_info.get("is_homebrew_category"):
            return self._homebrew_category_info() if homebrew_catalog.enabled() else None

        if (
            self.current_category_info.get("is_aur_category")
            or current_path == "aur://catalog"
        ):
            refreshed = dict(self.current_category_info)
            refreshed.update(
                {
                    "name": self.translations.get("aur_category", "AUR"),
                    "description": self.translations.get(
                        "aur_category_desc",
                        self.current_category_info.get(
                            "description",
                            "Browse packages from the Arch User Repository.",
                        ),
                    ),
                    "path": "aur://catalog",
                    "is_aur_category": True,
                }
            )
            return refreshed

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

    def _refresh_removable_scripts(self, refresh_cache=True):
        """Refresh removable state and update existing cards in place."""
        if refresh_cache and self.script_cache.is_populated:
            self.script_cache.refresh_removable_cache()
        self._invalidate_featured_eligibility_cache()

        # Card hierarchies now always contain a hidden removal control. Updating
        # state therefore requires no parser work, card reconstruction, or FlowBox
        # repopulation.
        flowbox = (
            self.scripts_flowbox
            if self.current_category_info is not None
            else self.categories_flowbox
        )

        view = getattr(self, "scripts_view", None)
        available_flowbox = getattr(view, "_linuxtoys_available_flowbox", None)
        installed_flowbox = getattr(view, "_linuxtoys_installed_flowbox", None)
        if self.current_category_info is not None and installed_flowbox is not None:
            # Only rebuild the two lazy lists when an actually displayed card has
            # crossed the Available/Installed boundary. Ordinary terminal returns
            # remain the same zero-rebuild path as before.
            membership_changed = False
            for fb, expected_installed in (
                (available_flowbox, False),
                (installed_flowbox, True),
            ):
                for child in fb.get_children():
                    card = child.get_child()
                    info = getattr(card, "info", None)
                    if not info or not info.get("is_script"):
                        continue
                    if bool(self._is_script_removable(info)) != expected_installed:
                        membership_changed = True
                        break
                if membership_changed:
                    break

            if membership_changed:
                self._load_scripts_into_flowbox(
                    available_flowbox, self.current_category_info, animate_initial=False
                )
                self._load_scripts_into_flowbox(
                    installed_flowbox, self.current_category_info, animate_initial=False
                )
            else:
                self._refresh_flowbox_removable_states(available_flowbox)
                self._refresh_flowbox_removable_states(installed_flowbox)

            # The tab bar itself is conditional. The wrapper always exists so a
            # just-installed app can expose Installed without replacing the whole
            # category view, while removing the last installed app hides it again.
            switcher = getattr(view, "_linuxtoys_category_switcher", None)
            tabs = getattr(view, "_linuxtoys_category_tabs", None)
            has_installed = self._category_has_installed_items(
                self.current_category_info
            )
            if switcher is not None:
                if has_installed:
                    switcher.set_no_show_all(False)
                    switcher.show_all()
                else:
                    switcher.hide()
                    switcher.set_no_show_all(True)
                    if tabs is not None:
                        tabs.set_visible_child_name("available")
            return

        self._refresh_flowbox_removable_states(flowbox)
