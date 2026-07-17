import asyncio
import logging
import os
import shutil
import threading

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
)
from .gtk_common import Gdk, GLib, Gtk, GdkPixbuf
from .window_items import ItemWidgetFactory
from .window_search import SearchCtl
from .window_nav import NavCtl
from .featured_scripts import FeaturedCtl
from .local_scripts import LocalScriptsCtl
from .updater.update_dialog import UpdateDialog
from .updater.update_helper import UpdateHelper

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
        self.set_default_size(800, 600)  ##
        # self.set_resizable(False) ## Desabilita o redimensionamento da janela

        # Set window icon for proper GNOME integration
        self._set_window_icon()

        # --- Instance variables for script management ---
        self.reboot_required = False  # Track if a reboot is required
        self.current_category_info = None  # Track current category for header updates
        self.navigation_stack = []  # Stack to track navigation history for proper back button behavior
        self.view_counter = 0  # Counter for unique view names

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

        # Checklist
        self.check_buttons = []

        # Auto error reporting preference
        self.auto_error_reports_enabled = False

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
        
        # Create separator and featured scripts section
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
        self.random_scripts_flowbox.set_homogeneous(True)
        # No margins here since the container already has them
        self.random_scripts_flowbox.set_margin_left(0)
        self.random_scripts_flowbox.set_margin_top(0)
        self.random_scripts_flowbox.set_margin_right(0)
        self.random_scripts_flowbox.set_margin_bottom(0)
        self.random_scripts_flowbox.set_column_spacing(16)
        self.random_scripts_flowbox.set_row_spacing(12)
        
        self.featured_scripts_container.pack_start(self.random_scripts_flowbox, False, False, 0)
        
        categories_container.pack_start(self.featured_scripts_container, False, False, 0)
        
        self.categories_view = Gtk.ScrolledWindow()
        self.categories_view.add(categories_container)
        self.main_stack.add_named(self.categories_view, "categories")

        self.scripts_flowbox = self.create_flowbox()
        self.scripts_view = Gtk.ScrolledWindow()
        self.scripts_view.add(self.scripts_flowbox)
        self.main_stack.add_named(self.scripts_view, "scripts")

        # Create search results view
        self.search_flowbox = self.create_flowbox()
        self.search_view = Gtk.ScrolledWindow()
        self.search_view.add(self.search_flowbox)
        self.main_stack.add_named(self.search_view, "search")

        self.reveal = revealer.RevealerFooter(self)
        main_vbox.pack_start(self.reveal, False, False, 0)

        # --- Load Data and Connect Signals ---
        self.load_categories()

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

        # Local scripts
        self.local_sh_dir = f"{os.environ['HOME']}/.local/linuxtoys/scripts/"

        # Initialize drag-and-drop but don't enable it by default
        self._setup_drag_and_drop()

        self._script_running = False

        # Populate caches asynchronously to avoid blocking the UI
        GLib.idle_add(self._populate_search_cache)
        GLib.idle_add(self._populate_category_cache)
        GLib.idle_add(self._populate_all_scripts)
        GLib.idle_add(self._show_ostree_package_deployment_info_on_startup)
        GLib.idle_add(self._check_updates)
        GLib.idle_add(self._start_file_watcher)
        GLib.idle_add(self._check_deepin_immutability_on_startup)

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

    def _start_file_watcher(self):
        """Start the file watcher (only active in DEV_MODE)."""
        if not dev_mode.is_dev_mode_enabled():
            return False
        file_watcher.start(self)
        return False

    def _on_files_changed(self, changed_files):
        """Handle file change notification from the watcher."""
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

    def _check_updates(self):
        threading.Thread(target=self._show_dialog_and_update, daemon=True).start()

    def _show_dialog_and_update(self):
        self._check = UpdateHelper()
        if self._check._update_available():
            GLib.idle_add(self._open_update_dialog, self._check._latest_ver)

    def _open_update_dialog(self, latest_ver):
        UpdateDialog(latest_ver, self).show()
        return False

    def _on_key_press(self, widget, event):
        keyval = event.keyval

        if self.main_stack.get_visible_child_name() == "running_scripts":
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

            if current_view == "categories":
                flowbox_to_check = self.categories_flowbox
            elif current_view == "search":
                flowbox_to_check = self.search_flowbox
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
                        # Simulate a click on the selected item
                        sim_event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
                        sim_event.button = 1
                        selected_children[0].get_child().emit(
                            "button-press-event", sim_event
                        )
                        return True
            else:
                # Normal menu behavior: activate the selected item
                screens = {
                    "categories": self.categories_flowbox.get_selected_children(),
                    "search": self.search_flowbox.get_selected_children(),
                }

                selected_widget = screens.get(
                    self.main_stack.get_visible_child_name(),
                    self.scripts_flowbox.get_selected_children(),
                )

                sim_event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
                sim_event.button = 1

                if selected_widget:
                    selected_widget[0].get_child().emit("button-press-event", sim_event)
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

    def load_categories(self):
        """Loads categories and connects their click event."""
        # Use cached categories if available, otherwise parse from filesystem
        if self.category_cache.is_populated:
            categories = self.category_cache.get_categories()
        else:
            categories = parser.get_categories(self.translations)

        # Store current category info and temporarily set to None for proper bold formatting
        temp_current_category = self.current_category_info
        self.current_category_info = None

        self.categories_flowbox.foreach(
            lambda widget: self.categories_flowbox.remove(widget)
        )
        for cat in categories:
            widget = self.create_item_widget(cat)
            description = cat.get("description", "")
            if description:
                widget.set_tooltip_text(description)
            else:
                widget.set_tooltip_text(None)
            self.categories_flowbox.add(widget)

        # Restore the current category info
        self.current_category_info = temp_current_category

        self.categories_flowbox.show_all()

    def _load_scripts_into_flowbox(self, flowbox, category_info):
        for child in flowbox.get_children():
            flowbox.remove(child)

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

        for script_info in scripts:
            widget = self.create_item_widget(
                script_info,
                checklist=checklist_mode,
                allow_drag=self._is_local_scripts_category(category_info),
            )

            description = script_info.get("description", "")
            widget.set_tooltip_text(description or None)
            flowbox.add(widget)

        self._configure_local_scripts_interaction(flowbox, category_info)

        if checklist_mode:
            self.reveal.set_reveal_child(len(self.check_buttons) >= 2)

    def load_scripts(self, category_info):
        """Loads scripts for a category and connects their click event. Supports checklist mode."""
        self._load_scripts_into_flowbox(self.scripts_flowbox, category_info)
        self.scripts_flowbox.show_all()

    def on_install_checklist(self, button):
        """Run checked scripts sequentially."""
        # Check if reboot is required before proceeding
        if self.reboot_required:
            self._show_reboot_warning_dialog()
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

                    # If user cancelled, don't proceed
                    if not confirmed:
                        return []

                deps.extend(required_scripts)

            deps.append(info)

        return deps

    def on_script_clicked(self, widget, event):
        """Handles script click by creating the dialog and starting the thread."""
        # Check if reboot is required before proceeding
        if self.reboot_required:
            self._show_reboot_warning_dialog()
            return

        info = widget.info

        # Check if this is the "Create New Script" option
        if info.get("is_create_script"):
            self._handle_create_new_script()
            return

        script_path = info.get("path", "")
        if script_path.endswith("skills-seeker.sh") or info.get("name") == "Skills Seeker":
            self.open_skills_seeker_view()
            return

        deps = asyncio.run(self._process_needed_scripts([info]))

        # Only open terminal if user didn't cancel the needed requirements dialog
        if deps:
            # Show confirmation dialog only if script hasn't been run before
            script_name = info.get('name', '')
            registry_data = action_registry.parse_registry_file()
            is_first_run = script_name not in registry_data
            
            # Show confirmation dialog only on first run
            if is_first_run:
                confirmed = needed_helper.show_run_confirmation_dialog(
                    self, self.translations, deps
                )
            else:
                # Skip dialog on subsequent runs to allow easy bug reports and uninstalls
                confirmed = True
            
            if confirmed:
                removable = info if len(deps) == 1 else None
                # Entering the terminal view always starts the selected scripts immediately.
                self.open_term_view(deps, removable_script_info=removable, auto_run=True)

    def _install_skill_from_seeker(self, source, slug, agent):
        tmp_dir = "/tmp/linuxtoys"
        os.makedirs(tmp_dir, exist_ok=True)
        safe_source = source.replace("/", "_")
        tmp_script = os.path.join(tmp_dir, f"skill_install_{safe_source}_{slug}.sh")
        script_content = f"""#!/bin/bash
# name: Install Skill {slug}
# description: Install skill {source} for agent {agent}
source "$SCRIPT_DIR/libs/linuxtoys.lib"
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
        """Shows a dialog warning that a reboot is required before continuing."""
        reboot_helper.handle_reboot_requirement(
            self, self.translations, self._close_application
        )

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

        # Update search engine translations
        self.search_engine.update_translations(self.translations)
        
        # Refresh category cache with new translations in background
        def refresh_category_cache():
            try:
                self.category_cache.refresh_for_translations(self.translations)
            except Exception as e:
                print(f"Error refreshing category cache: {e}")
        
        # Refresh all scripts cache for random scripts display
        def refresh_all_scripts():
            try:
                self.all_scripts = self._collect_all_scripts()
            except Exception as e:
                print(f"Error refreshing all scripts cache: {e}")
        
        threading.Thread(target=refresh_category_cache, daemon=True).start()
        threading.Thread(target=refresh_all_scripts, daemon=True).start()

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