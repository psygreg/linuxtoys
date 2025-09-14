from .gtk_common import Gtk, GLib, Gdk
from gi.repository import GdkPixbuf
import os, shutil

from . import parser
from . import header
from . import footer
from . import checklist_helper
from . import confirm_helper
from . import compat
from . import head_menu
from . import reboot_helper
from . import script_runner
from . import search_helper
from . import get_icon_path

class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, application, translations, *args, **kwargs):
        super().__init__(application=application, *args, **kwargs)
        self.translations = translations

        self.set_title("LinuxToys")
        self.set_default_size(780, 560) ## 
        # self.set_resizable(False) ## Desabilita o redimensionamento da janela

        # Set window icon for proper GNOME integration
        self._set_window_icon()

        # --- Instance variables for script management ---
        self.script_is_running = False
        self.reboot_required = False  # Track if a reboot is required
        self.current_category_info = None  # Track current category for header updates
        self.navigation_stack = []  # Stack to track navigation history for proper back button behavior
        self.view_counter = 0  # Counter for unique view names
        
        # Initialize search functionality
        self.search_engine = search_helper.create_search_engine(self.translations)
        self.search_active = False
        self.search_results = []
        
        # Initialize script runner
        self.script_runner = script_runner.ScriptRunner(self, self.translations)

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
                if 'Wayland' in backend_type:
                    # On Wayland (including Hyprland), prefer server-side decorations
                    # This can help avoid hanging issues with client-side decorations
                    self.set_decorated(True)  # Enable window manager decorations
                    # Still set the headerbar but with less aggressive CSD
                    self.header_bar.set_decoration_layout("menu:minimize,maximize,close")
        except Exception as e:
            print(f"Warning: Could not detect display backend: {e}")
        
        self.set_titlebar(self.header_bar)

        self.back_button = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.header_bar.pack_start(self.back_button)

        # Create search UI components
        self._create_search_ui()

        # Store reference to the menu button for later updates
        self.menu_button = head_menu.MenuButton(
            self.script_runner, 
            parent_window=self,
            on_language_changed=self.on_language_changed
        )
        self.header_bar.pack_end(self.menu_button)

        self.main_stack = Gtk.Stack()
        self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.main_stack.set_transition_duration(200)  # Set a reasonable transition duration
        main_vbox.pack_start(self.main_stack, True, True, 0)

        self.categories_flowbox = self.create_flowbox()
        self.categories_view = Gtk.ScrolledWindow()
        self.categories_view.add(self.categories_flowbox)
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

        self.footer_widget = footer.create_footer()
        main_vbox.pack_start(self.footer_widget, False, False, 0)

        # --- Load Data and Connect Signals ---
        self.load_categories()
        
        self.back_button.connect("clicked", self.on_back_button_clicked)

        # --- Check for pending ostree deployments ---
        self._check_ostree_deployments_on_startup()

        # --- Show the Window ---
        self.show_all()
        self.show_categories_view()  # Call this after show_all to ensure proper visibility state

        # Connect focus events to enable/disable tooltips
        self.connect('focus-in-event', self._on_focus_in)
        self.connect('focus-out-event', self._on_focus_out)

        # Local scripts
        self.local_sh_dir = f'{os.environ['HOME']}/.local/linuxtoys/scripts/'

        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.connect("drag-data-received", self._on_drag_data_received)
        self.drag_dest_add_uri_targets()

    def _on_drag_data_received(self, widget, context, x, y, data, info, time):
        sh_paths = [ os.path.normpath(uri[7:]) for uri in data.get_uris() if uri.startswith('file://') and uri.endswith('.sh') ]
        os.makedirs(os.path.dirname(self.local_sh_dir), exist_ok=True)
        [ shutil.copy2(sh_path, f"{self.local_sh_dir}{os.path.basename(sh_path)}") for sh_path in sh_paths ]

        self.load_scripts({
            'name': 'Local Scripts',
            'description': 'Drop your scripts here',
            'icon': 'local-script.svg',
            'mode': 'auto',
            'path': self.local_sh_dir,
            'is_script': False,
            'has_subcategories': False,
            'display_mode': 'menu'
        })

    def _check_ostree_deployments_on_startup(self):
        """
        Check for pending ostree deployments on application startup.
        If found on compatible systems, show warning dialog.
        """
        # Get system compatibility keys
        system_compat_keys = compat.get_system_compat_keys()
        
        # Only check on ostree-based systems
        if {'ostree', 'ublue'} & system_compat_keys:
            if reboot_helper.check_ostree_pending_deployments():
                # Use GLib.idle_add to ensure the dialog shows after the window is fully initialized
                GLib.idle_add(self._show_ostree_deployment_warning)

    def _show_ostree_deployment_warning(self):
        """
        Show the ostree deployment warning dialog.
        Called via GLib.idle_add to ensure proper timing.
        """
        reboot_helper.handle_ostree_deployment_requirement(
            self, 
            self.translations, 
            self._close_application
        )
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
                    os.path.join(os.path.dirname(__file__), "..", "..", "src", "linuxtoys.svg"),
                    # Relative path from the script location
                    os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "linuxtoys.svg")
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
                    GLib.idle_add(lambda: self.set_icon_name("application-x-executable"))
                except Exception:
                    pass  # If even this fails, just continue without an icon
        
        # Load icon asynchronously to prevent blocking on window manager issues
        import threading
        threading.Thread(target=load_icon_async, daemon=True).start()

    def _set_tooltips_enabled(self, enabled):
        # Categories
        for flowbox_child in self.categories_flowbox.get_children():
            widget = flowbox_child.get_child()
            widget.set_has_tooltip(enabled)
            if enabled:
                widget.set_tooltip_text(getattr(widget, 'info', {}).get('description', ''))
            else:
                widget.set_tooltip_text(None)
        # Scripts
        for flowbox_child in self.scripts_flowbox.get_children():
            widget = flowbox_child.get_child()
            widget.set_has_tooltip(enabled)
            if enabled:
                widget.set_tooltip_text(getattr(widget, 'info', {}).get('description', ''))
            else:
                widget.set_tooltip_text(None)

    def _on_focus_in(self, *args):
        self._set_tooltips_enabled(True)

    def _on_focus_out(self, *args):
        self._set_tooltips_enabled(False)

    def _create_search_ui(self):
        """Create the search UI components for the header bar."""
        # Create search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(self.translations.get("search_placeholder", "Search features"))
        self.search_entry.set_size_request(250, -1)  # Set minimum width
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_search_activate)
        self.search_entry.connect("key-press-event", self._on_search_key_press)
        
        # Pack the search entry directly to the left side of the header (after back button)
        self.header_bar.pack_start(self.search_entry)

    def create_flowbox(self):
        """Uses SelectionMode.NONE to disable selection highlight."""
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(5)  ## items per line
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_homogeneous(True)  # Make all children the same size
        ## Adiciona margem de 32 px em todos os lados
        flowbox.set_margin_left(32) 
        flowbox.set_margin_top(8) 
        flowbox.set_margin_right(32) 
        flowbox.set_margin_bottom(32)
        ## Define espaçamento horizontal e vertical entre os itens (em pixels)
        flowbox.set_column_spacing(16)  ## espaço entre itens lado a lado
        flowbox.set_row_spacing(12)     ## espaço entre linhas
        return flowbox

    def create_item_widget(self, item_info):
        import os
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_size_request(128, 52)  # Fixed width for all items
        box.set_hexpand(False)
        box.set_halign(Gtk.Align.FILL)

        left_pad = Gtk.Label()
        left_pad.set_size_request(10, 1)
        box.pack_start(left_pad, False, False, 0)

        label = Gtk.Label(label=item_info['name'])
        label.set_line_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_halign(Gtk.Align.CENTER)
        label.set_valign(Gtk.Align.CENTER)
        label.set_max_width_chars(28)  # Limit label width
        label.set_width_chars(4)      # Set consistent width
        label.set_hexpand(False)
        
        # Make categories and subcategories bold, keep scripts regular
        is_main_category = self.current_category_info is None  # We're in the main menu
        is_subcategory = item_info.get('is_subcategory', False)
        is_category_type = item_info.get('type') == 'category'
        is_not_script = not item_info.get('is_script', False)
        
        if is_subcategory or (is_category_type and is_not_script) or (is_main_category and is_not_script):
            # This is a category or subcategory - make it bold
            # Escape HTML characters to prevent markup issues
            import html
            escaped_name = html.escape(item_info['name'])
            label.set_markup(f"<b>{escaped_name}</b>")
        box.pack_start(label, True, True, 0)

        icon_value = item_info.get('icon', 'application-x-executable')
        icon_widget = None
        icon_size = 38  # Target icon size
        
        # If icon_value looks like a file path or just a filename, use Gtk.Image.new_from_file
        if icon_value.endswith('.png') or icon_value.endswith('.svg'):
            # If only a filename, use the global icon path resolver
            if not os.path.isabs(icon_value) and '/' not in icon_value:
                icon_path = get_icon_path("local-script.svg" if ".local/linuxtoys/scripts" in item_info.get('path') else icon_value)
            else:
                icon_path = icon_value if os.path.exists(icon_value) else None
                
            if icon_path and os.path.exists(icon_path):
                if icon_path.endswith('.svg') or icon_path.endswith('.png'):
                    # For SVG files, load as pixbuf with specific size
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                            icon_path, icon_size, icon_size, True
                        )
                        icon_widget = Gtk.Image.new_from_pixbuf(pixbuf)
                    except Exception:
                        # Fallback to default icon if SVG loading fails
                        icon_widget = Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)
                        icon_widget.set_pixel_size(icon_size)
                else:
                    # For PNG files, use regular loading and set pixel size
                    icon_widget = Gtk.Image.new_from_file(icon_path)
                    icon_widget.set_pixel_size(icon_size)
            else:
                icon_widget = Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)
                icon_widget.set_pixel_size(icon_size)
        else:
            icon_widget = Gtk.Image.new_from_icon_name(icon_value, Gtk.IconSize.DIALOG)
            icon_widget.set_pixel_size(icon_size) ## altura dos icones
        icon_widget.set_halign(Gtk.Align.END)
        icon_widget.set_valign(Gtk.Align.CENTER)

        box.pack_start(icon_widget, False, False, 20)

        event_box = Gtk.EventBox()
        event_box.add(box)
        event_box.get_style_context().add_class("script-item")
        event_box.info = item_info
        
        # Enable mouse events for hover effects
        event_box.set_events(event_box.get_events() | 
                           Gdk.EventMask.ENTER_NOTIFY_MASK | 
                           Gdk.EventMask.LEAVE_NOTIFY_MASK |
                           Gdk.EventMask.BUTTON_PRESS_MASK |
                           Gdk.EventMask.BUTTON_RELEASE_MASK)
        
        # Connect hover events only (click events are connected separately)
        event_box.connect("enter-notify-event", self.on_item_enter)
        event_box.connect("leave-notify-event", self.on_item_leave)
        
        return event_box

    def load_categories(self):
        """Loads categories and connects their click event."""
        categories = parser.get_categories(self.translations)

        local_dir = f'{os.environ['HOME']}/.local/linuxtoys/scripts'
        categories.append({
            'name': 'Local Scripts',
            'description': 'Drop your scripts here',
            'icon': 'local-script.svg',
            'mode': 'auto',
            'path': local_dir,
            'is_script': False,
            'has_subcategories': False,
            'display_mode': 'menu'
        })
        
        self.categories_flowbox.foreach(lambda widget: self.categories_flowbox.remove(widget))
        for cat in categories:
            widget = self.create_item_widget(cat)
            widget.set_tooltip_text(cat.get('description', ''))
            widget.connect("button-press-event", self.on_category_clicked)
            self.categories_flowbox.add(widget)
        self.categories_flowbox.show_all()
            
            
    def _load_scripts_into_flowbox(self, flowbox, category_info):
        """Helper method to load scripts into a specific flowbox."""
        # Clear the flowbox first
        for child in flowbox.get_children():
            flowbox.remove(child)

        scripts = parser.get_scripts_for_category(category_info['path'], self.translations)
        
        checklist_mode = category_info.get('display_mode', 'menu') == 'checklist'
        self.check_buttons = []

        if checklist_mode:
            inner_flowbox = Gtk.FlowBox()
            inner_flowbox.set_valign(Gtk.Align.START)
            inner_flowbox.set_max_children_per_line(5)  # Five columns max like standard menus
            inner_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
            inner_flowbox.set_homogeneous(True)  # Make all children the same size
            inner_flowbox.set_row_spacing(8)     # Reduce vertical spacing between rows
            inner_flowbox.set_column_spacing(10) # Add some horizontal spacing between columns
            inner_flowbox.set_margin_start(40)   # Symmetric margins for consistent layout
            inner_flowbox.set_margin_end(40)
            self.check_buttons = []

            for script_info in scripts:
                if script_info.get('is_subcategory', False):
                    # This should not happen in checklist mode, but handle it gracefully
                    # by treating subcategories as navigable items
                    print(f"Warning: Subcategory '{script_info['name']}' found in checklist mode category")
                    widget = self.create_item_widget(script_info)
                    widget.set_tooltip_text(script_info['description'])
                    widget.connect("button-press-event", self.on_category_clicked)
                    inner_flowbox.add(widget)
                else:
                    # Scripts can be checked in checklist mode
                    check = Gtk.CheckButton(label=script_info['name'])
                    check.script_info = script_info
                    check.set_tooltip_text(script_info['description'])
                    check.set_size_request(128, 16)  # Reduce height for tighter spacing
                    inner_flowbox.add(check)
                    self.check_buttons.append(check)

            # Clear previous checklist buttons from footer
            for child in self.footer_widget.checklist_button_box.get_children():
                self.footer_widget.checklist_button_box.remove(child)

            install_btn = Gtk.Button(label=self.translations.get('install_btn_label', 'Install'))
            cancel_btn = Gtk.Button(label=self.translations.get('cancel_btn_label', 'Cancel'))
            install_btn.connect("clicked", self.on_install_checklist)
            cancel_btn.connect("clicked", self.on_cancel_checklist)
            self.footer_widget.checklist_button_box.pack_start(install_btn, False, False, 0)
            self.footer_widget.checklist_button_box.pack_start(cancel_btn, False, False, 0)
            self.footer_widget.checklist_button_box.show_all()

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            vbox.set_margin_start(32)  # Add left padding
            vbox.set_margin_end(32)    # Add right padding
            vbox.set_margin_top(20)    # Add top padding for better spacing
            vbox.pack_start(inner_flowbox, True, True, 0)

            flowbox.add(vbox)
        else:
            for script_info in scripts:
                widget = self.create_item_widget(script_info)
                widget.set_tooltip_text(script_info['description'])
                
                # Connect different click handlers based on whether it's a subcategory or script
                if script_info.get('is_subcategory', False):
                    # This is a subcategory, use category click handler for navigation
                    widget.connect("button-press-event", self.on_category_clicked)
                else:
                    # This is a script, use script click handler for execution
                    widget.connect("button-press-event", self.on_script_clicked)
                    
                flowbox.add(widget)

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
            
        def on_checklist_dialog_closed(dialog, response_id):
            """Handle checklist dialog closure."""
            if dialog:
                dialog.destroy()
                
        checklist_helper.handle_install_checklist(
            self.check_buttons, 
            self, 
            on_checklist_dialog_closed,
            self.translations
        )

    def run_script_with_callback(self, script_info, callback):
        """Run a script and call callback when done."""
        def completion_handler():
            if callback:
                callback()
        
        def reboot_handler():
            self.reboot_required = True
        
        return self.script_runner.run_script(
            script_info, 
            on_completion=completion_handler,
            on_reboot_required=reboot_handler
        )

    def on_cancel_checklist(self, button):
        """Uncheck all boxes, remove checklist buttons from footer, and return to previous view."""
        for cb in self.check_buttons:
            cb.set_active(False)
        # Remove checklist buttons from footer
        for child in self.footer_widget.checklist_button_box.get_children():
            self.footer_widget.checklist_button_box.remove(child)
        
        # Use back button logic to go to the appropriate previous view
        self.on_back_button_clicked(None)

    def on_category_clicked(self, widget, event):
        """Handles category click, subcategory click, or root script click."""
        # Check if reboot is required before proceeding
        if self.reboot_required:
            self._show_reboot_warning_dialog()
            return
            
        info = widget.info
        # If this is a root script (shown as a category), execute it directly
        if info.get('is_script'):
            if not self.script_runner.is_running():
                # Show confirmation dialog before executing root script
                if not confirm_helper.show_single_script_confirmation(info, self, self.translations):
                    return  # User cancelled
                    
                self.script_is_running = True
                
                def completion_handler():
                    self.script_is_running = False
                
                def reboot_handler():
                    self.reboot_required = True
                
                self.script_runner.run_script(
                    info, 
                    on_completion=completion_handler,
                    on_reboot_required=reboot_handler
                )
        else:
            # This is a category or subcategory - navigate to show its contents  
            # Create a new view for the subcategory to enable proper animation
            self.view_counter += 1
            new_view_name = f"scripts_{self.view_counter}"
            
            # Create new flowbox and scrolled window for this level
            new_flowbox = self.create_flowbox()
            new_scrolled_view = Gtk.ScrolledWindow()
            new_scrolled_view.add(new_flowbox)
            
            # Load content into the new view
            self._load_scripts_into_flowbox(new_flowbox, info)
            
            # Add the new view to the stack
            self.main_stack.add_named(new_scrolled_view, new_view_name)
            new_scrolled_view.show_all()
            
            # Set transition for forward navigation
            self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            
            # Update the scripts references
            self.scripts_flowbox = new_flowbox
            self.scripts_view = new_scrolled_view
            
            # Show the new view with animation
            self.show_scripts_view(info)

    def on_script_clicked(self, widget, event):
        """Handles script click by creating the dialog and starting the thread."""
        if self.script_runner.is_running():
            return

        # Check if reboot is required before proceeding
        if self.reboot_required:
            self._show_reboot_warning_dialog()
            return

        info = widget.info
        
        # Show confirmation dialog before executing script
        if not confirm_helper.show_single_script_confirmation(info, self, self.translations):
            return  # User cancelled
        
        self.script_is_running = True
        
        def completion_handler():
            self.script_is_running = False
        
        def reboot_handler():
            self.reboot_required = True
        
        self.script_runner.run_script(
            info, 
            on_completion=completion_handler,
            on_reboot_required=reboot_handler
        )



    def _show_reboot_warning_dialog(self):
        """Shows a dialog warning that a reboot is required before continuing."""
        reboot_helper.handle_reboot_requirement(
            self, 
            self.translations, 
            self._close_application
        )
    
    def _close_application(self):
        """Closes the application gracefully."""
        self.script_runner.terminate()
        self.get_application().quit()

    def on_language_changed(self, new_language_code):
        """Handle language change by reloading translations and updating UI"""
        from . import lang_utils
        
        # Load new translations
        self.translations = lang_utils.load_translations(new_language_code)
        
        # Update the script runner's translations
        self.script_runner.translations = self.translations
        
        # Update search engine translations
        self.search_engine.update_translations(self.translations)
        
        # Update search entry placeholder text
        self.search_entry.set_placeholder_text(self.translations.get("search_placeholder", "Search features"))
        
        # Refresh the UI with new translations
        self._refresh_ui_with_new_translations()
    
    def _refresh_ui_with_new_translations(self):
        """Refresh all UI elements with new translations"""
        # Update header
        self._update_header(self.current_category_info)
        
        # Update title bar
        if self.current_category_info:
            category_name = self.current_category_info.get('name', 'Unknown')
            self.header_bar.props.title = f"LinuxToys: {category_name}"
        else:
            self.header_bar.props.title = "LinuxToys"
        
        # Refresh the dropdown menu with new translations
        if hasattr(self, 'menu_button'):
            self.menu_button.refresh_menu_translations()
        
        # Refresh the footer with new translations
        if hasattr(self.footer_widget, 'refresh_translations'):
            self.footer_widget.refresh_translations(self.translations)
        
        # Reload categories with new translations
        if self.main_stack.get_visible_child_name() == "categories":
            self.load_categories()
        else:
            # Reload current category/subcategory content
            if self.current_category_info:
                self.load_scripts(self.current_category_info)
        
        # Update footer if in checklist mode
        if (self.current_category_info and 
            self.current_category_info.get('display_mode', 'menu') == 'checklist'):
            # Clear and recreate checklist buttons with new translations
            for child in self.footer_widget.checklist_button_box.get_children():
                self.footer_widget.checklist_button_box.remove(child)
            
            install_btn = Gtk.Button(label=self.translations.get('install_btn_label', 'Install'))
            cancel_btn = Gtk.Button(label=self.translations.get('cancel_btn_label', 'Cancel'))
            install_btn.connect("clicked", self.on_install_checklist)
            cancel_btn.connect("clicked", self.on_cancel_checklist)
            self.footer_widget.checklist_button_box.pack_start(install_btn, False, False, 0)
            self.footer_widget.checklist_button_box.pack_start(cancel_btn, False, False, 0)
            self.footer_widget.checklist_button_box.show_all()

    def _update_header(self, category_info=None):
        """Updates the header with new category information."""
        # Remove the old header
        main_vbox = self.get_child()
        main_vbox.remove(self.header_widget)
        
        # Create new header with category info
        self.header_widget = header.create_header(self.translations, category_info)
        main_vbox.pack_start(self.header_widget, False, False, 8)
        main_vbox.reorder_child(self.header_widget, 0)  # Move to top
        
        # Show the new header
        self.header_widget.show_all()

    def on_item_enter(self, widget, event):
        """Handle mouse entering a script/category item - add hover effect."""
        try:
            # Hover effect
            widget.get_style_context().add_class("script-item-hover")
            
            # Force a redraw
            widget.queue_draw()
        except Exception as e:
            print(f"Error in hover enter: {e}")
        
        return False

    def on_item_leave(self, widget, event):
        """Handle mouse leaving a script/category item - remove hover effect."""
        try:
            style_context = widget.get_style_context()
            style_context.remove_class("script-item-hover")
            
            # Force a redraw
            widget.queue_draw()
        except Exception as e:
            print(f"Error in hover leave: {e}")
        
        return False

    def _on_search_changed(self, search_entry):
        """Handle search text changes."""
        query = search_entry.get_text().strip()
        
        if len(query) >= 2:
            self._perform_search(query)
        elif len(query) == 0 and self.search_active:
            # If search is completely emptied, return to normal mode and remove focus
            self._clear_search_results()
            # Deselect the search entry (remove focus) using GLib.idle_add for deferred execution
            from gi.repository import GLib
            def remove_focus():
                # Try to focus on the current visible child or the main container
                current_child = self.main_stack.get_visible_child()
                if current_child:
                    current_child.grab_focus()
                else:
                    # Fallback: try to focus on the main window itself
                    self.grab_focus()
                return False  # Don't repeat this idle callback
            GLib.idle_add(remove_focus)
            # Also reset the header if we were in search mode
            if self.current_category_info:
                self._update_header(self.current_category_info)
                category_name = self.current_category_info.get('name', 'Unknown')
                self.header_bar.props.title = f"LinuxToys: {category_name}"
            else:
                self._update_header()  # Reset to default header
                self.header_bar.props.title = "LinuxToys"

    def _on_search_activate(self, search_entry):
        """Handle search entry activation (Enter key)."""
        # If there are search results, activate the first one
        if self.search_results:
            first_result = self.search_results[0]
            self._activate_search_result(first_result)

    def _on_search_key_press(self, widget, event):
        """Handle key presses in search entry."""
        if event.keyval == Gdk.KEY_Escape:
            # Clear search on Escape
            widget.set_text("")
            # Deselect the search entry (remove focus) using GLib.idle_add for deferred execution
            from gi.repository import GLib
            def remove_focus():
                # Try to focus on the current visible child or the main container
                current_child = self.main_stack.get_visible_child()
                if current_child:
                    current_child.grab_focus()
                else:
                    # Fallback: try to focus on the main window itself
                    self.grab_focus()
                return False  # Don't repeat this idle callback
            GLib.idle_add(remove_focus)
            if self.search_active:
                self._clear_search_results()
                # Reset header appropriately
                if self.current_category_info:
                    self._update_header(self.current_category_info)
                    category_name = self.current_category_info.get('name', 'Unknown')
                    self.header_bar.props.title = f"LinuxToys: {category_name}"
                else:
                    self._update_header()  # Reset to default header
                    self.header_bar.props.title = "LinuxToys"
            return True
        return False

    def _perform_search(self, query):
        """Perform the actual search and display results."""
        self.search_results = self.search_engine.search(query)
        self._display_search_results()

    def _display_search_results(self):
        """Display search results in the search view."""
        self.search_active = True
        
        # Clear existing search results completely
        for child in self.search_flowbox.get_children():
            self.search_flowbox.remove(child)
        
        # Force switch to search view first to ensure we're in the right context
        self.main_stack.set_visible_child_name("search")
        
        # Ensure the back button is visible when in search mode
        self.back_button.show()
        
        # Add search results (all are scripts now)
        for search_result in self.search_results:
            item_info = search_result.item_info
            widget = self.create_item_widget(item_info)
            widget.set_tooltip_text(item_info.get('description', ''))
            
            # All search results are scripts, so connect script click handler
            widget.connect("button-press-event", self.on_script_clicked)
            
            self.search_flowbox.add(widget)
        
        # Ensure all widgets are shown
        self.search_flowbox.show_all()
        
        # Update header for search view
        self._update_search_header()

    def _activate_search_result(self, search_result):
        """Activate a specific search result (simulate click)."""
        # This would be called when Enter is pressed or result is directly activated
        item_info = search_result.item_info
        
        # All search results are scripts now
        if not self.script_runner.is_running():
            if self.reboot_required:
                self._show_reboot_warning_dialog()
                return
            
            # Show confirmation dialog before executing script
            if confirm_helper.show_single_script_confirmation(item_info, self, self.translations):
                self.script_is_running = True
                
                def completion_handler():
                    self.script_is_running = False
                
                def reboot_handler():
                    self.reboot_required = True
                
                self.script_runner.run_script(
                    item_info, 
                    on_completion=completion_handler,
                    on_reboot_required=reboot_handler
                )

    def _clear_search_results(self):
        """Clear search results and return to previous view."""
        self.search_active = False
        self.search_results = []
        
        # Return to appropriate view
        if self.current_category_info:
            self.main_stack.set_visible_child(self.scripts_view)
            # Ensure back button is visible for category views
            self.back_button.show()
        else:
            self.main_stack.set_visible_child_name("categories")
            # Hide back button for main categories view
            self.back_button.hide()

    def _update_search_header(self):
        """Update header for search results view."""
        search_query = self.search_entry.get_text().strip()
        results_count = len(self.search_results)
        
        # Create search results info for header
        search_info = {
            'name': f"{self.translations.get('search_results', 'Search Results')}: \"{search_query}\"",
            'description': f"{results_count} {self.translations.get('results_found', 'results found')}",
            'icon': 'system-search-symbolic'
        }
        
        self._update_header(search_info)
        self.header_bar.props.title = f"LinuxToys: {self.translations.get('search', 'Search')}"
        self.back_button.show()

    def on_back_button_clicked(self, widget):
        """Handles the back button click."""
        # Check if we're in search view
        if self.search_active:
            # Clear the search bar when returning from search mode
            self.search_entry.set_text("")
            self._clear_search_results()
            return
            
        if self.navigation_stack:
            # Store current view for cleanup
            current_view = self.scripts_view
            
            # Go back to the previous category/subcategory
            previous_category = self.navigation_stack.pop()
            self.current_category_info = previous_category
            
            # Create a new view for the previous category
            self.view_counter += 1
            new_view_name = f"scripts_{self.view_counter}"
            
            new_flowbox = self.create_flowbox()
            new_scrolled_view = Gtk.ScrolledWindow()
            new_scrolled_view.add(new_flowbox)
            
            # Load content into the new view
            self._load_scripts_into_flowbox(new_flowbox, previous_category)
            
            # Add the new view to the stack
            self.main_stack.add_named(new_scrolled_view, new_view_name)
            new_scrolled_view.show_all()
            
            # Set transition direction for going back
            self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            
            # Update references
            self.scripts_flowbox = new_flowbox
            self.scripts_view = new_scrolled_view
            
            # Switch to the new view
            self.main_stack.set_visible_child(new_scrolled_view)
            
            # Update UI
            category_name = previous_category.get('name', 'Unknown')
            self.header_bar.props.title = f"LinuxToys: {category_name}"
            self._update_header(previous_category)
            
            # Show footer only if checklist mode
            if previous_category.get('display_mode', 'menu') == 'checklist':
                self.footer_widget.show()
                self.footer_widget.show_checklist_footer()
                self.footer_widget.set_margin_bottom(0)
            else:
                self.footer_widget.hide()
            
            # Clean up the old view after transition
            def cleanup_old_view():
                try:
                    self.main_stack.remove(current_view)
                except Exception:
                    pass  # View may already be removed
                # Restore normal transition direction
                self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
                return False
            
            GLib.timeout_add(300, cleanup_old_view)
            
        else:
            # No more items in stack, go to main categories view
            current_view = self.scripts_view
            self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            self.show_categories_view()
            
            # Clean up the scripts view after transition
            def cleanup_scripts_view():
                try:
                    self.main_stack.remove(current_view)
                except Exception:
                    pass
                # Restore normal transition direction  
                self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
                return False
            
            GLib.timeout_add(300, cleanup_scripts_view)
        
    def show_categories_view(self):
        """Switches to the main categories view."""
        self.current_category_info = None
        self.navigation_stack.clear()  # Clear navigation history
        self.main_stack.set_visible_child_name("categories")
        self.back_button.hide()
        self.header_bar.props.title = "LinuxToys"
        self._update_header()  # Reset to default header
        self.header_widget.show()
        self.footer_widget.show()
        self.footer_widget.show_menu_footer()
        # Ensure footer has proper spacing
        self.footer_widget.set_margin_bottom(0)

    def show_scripts_view(self, category_info):
        """Switches to the view showing scripts in a category."""
        # If we have current category info, push it to navigation stack
        if self.current_category_info:
            self.navigation_stack.append(self.current_category_info)
        
        self.current_category_info = category_info
        
        # Switch to the current scripts view (which may be a new one created for subcategories)
        current_child = self.main_stack.get_visible_child()
        if current_child != self.scripts_view:
            self.main_stack.set_visible_child(self.scripts_view)
        
        self.back_button.show()
        
        # Get the category name for the title
        category_name = category_info.get('name', 'Unknown') if category_info else 'Unknown'
        self.header_bar.props.title = f"LinuxToys: {category_name}"
        
        # Update header with category information
        if category_info:
            self._update_header(category_info)
        
        # Show footer only if checklist mode
        if category_info and category_info.get('display_mode', 'menu') == 'checklist':
            self.footer_widget.show()
            self.footer_widget.show_checklist_footer()
            # Ensure footer has proper spacing for checklist mode
            self.footer_widget.set_margin_bottom(0)
        else:
            self.footer_widget.hide()
