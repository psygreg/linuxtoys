import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import subprocess
import threading
from . import parser
from . import header
from . import footer
from . import checklist_helper
from . import confirm_helper
from . import compat
from . import reboot_helper

class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, application, translations, *args, **kwargs):
        super().__init__(application=application, *args, **kwargs)
        self.translations = translations

        self.set_default_size(640, 520)
        self.set_title("LinuxToys")

        # --- Instance variables for script management ---
        self.script_is_running = False
        self.running_process = None
        self.reboot_required = False  # Track if a reboot is required

        # --- UI Structure ---
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_vbox)

        self.header_widget = header.create_header(self.translations)
        main_vbox.pack_start(self.header_widget, False, False, 10)

        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_show_close_button(True)
        self.set_titlebar(self.header_bar)

        self.back_button = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.header_bar.pack_start(self.back_button)

        self.main_stack = Gtk.Stack()
        self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        main_vbox.pack_start(self.main_stack, True, True, 0)

        self.categories_flowbox = self.create_flowbox()
        self.categories_view = Gtk.ScrolledWindow()
        self.categories_view.add(self.categories_flowbox)
        self.main_stack.add_named(self.categories_view, "categories")
        
        self.scripts_flowbox = self.create_flowbox()
        self.scripts_view = Gtk.ScrolledWindow()
        self.scripts_view.add(self.scripts_flowbox)
        self.main_stack.add_named(self.scripts_view, "scripts")

        self.footer_widget = footer.create_footer()
        main_vbox.pack_start(self.footer_widget, False, False, 0)

        # --- Load Data and Connect Signals ---
        self.load_categories()
        
        self.back_button.connect("clicked", self.on_back_button_clicked)

        # --- Check for pending ostree deployments ---
        self._check_ostree_deployments_on_startup()

        # --- Show the Window ---
        self.show_categories_view()
        self.show_all()

        # Connect focus events to enable/disable tooltips
        self.connect('focus-in-event', self._on_focus_in)
        self.connect('focus-out-event', self._on_focus_out)

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
                from gi.repository import GLib
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

    def create_flowbox(self):
        """Uses SelectionMode.NONE to disable selection highlight."""
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(2)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_homogeneous(True)  # Make all children the same size
        return flowbox

    def create_item_widget(self, item_info):
        import os
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_size_request(140, 60)  # Fixed width for all items
        box.set_hexpand(False)
        box.set_halign(Gtk.Align.FILL)

        left_pad = Gtk.Label()
        left_pad.set_size_request(10, 1)
        box.pack_start(left_pad, False, False, 0)

        icon_value = item_info.get('icon', 'application-x-executable')
        icon_widget = None
        # If icon_value looks like a file path or just a filename, use Gtk.Image.new_from_file
        if icon_value.endswith('.png') or icon_value.endswith('.svg'):
            # If only a filename, presume it's in the icons folder
            if not os.path.isabs(icon_value) and '/' not in icon_value:
                icon_path = os.path.join(os.path.dirname(__file__), 'icons', icon_value)
            else:
                icon_path = icon_value
            if os.path.exists(icon_path):
                icon_widget = Gtk.Image.new_from_file(icon_path)
            else:
                icon_widget = Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)
        else:
            icon_widget = Gtk.Image.new_from_icon_name(icon_value, Gtk.IconSize.DIALOG)
        icon_widget.set_pixel_size(40)
        icon_widget.set_halign(Gtk.Align.START)
        icon_widget.set_valign(Gtk.Align.CENTER)
        box.pack_start(icon_widget, False, False, 0)

        label = Gtk.Label(label=item_info['name'])
        label.set_line_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_halign(Gtk.Align.CENTER)
        label.set_valign(Gtk.Align.CENTER)
        label.set_max_width_chars(12)  # Limit label width
        label.set_width_chars(10)      # Set consistent width
        label.set_hexpand(False)
        box.pack_start(label, True, True, 0)

        event_box = Gtk.EventBox()
        event_box.add(box)
        event_box.get_style_context().add_class("script-item")
        event_box.info = item_info
        return event_box

    def load_categories(self):
        """Loads categories and connects their click event."""
        categories = parser.get_categories(self.translations)
        
        self.categories_flowbox.foreach(lambda widget: self.categories_flowbox.remove(widget))
        for cat in categories:
            widget = self.create_item_widget(cat)
            widget.set_tooltip_text(cat.get('description', ''))
            widget.connect("button-press-event", self.on_category_clicked)
            self.categories_flowbox.add(widget)
        self.categories_flowbox.show_all()
            
    def load_scripts(self, category_info):
        """Loads scripts for a category and connects their click event. Supports checklist mode."""
        for child in self.scripts_flowbox.get_children():
            self.scripts_flowbox.remove(child)

        scripts = parser.get_scripts_for_category(category_info['path'], self.translations)
        
        checklist_mode = category_info.get('mode', 'menu') == 'checklist'
        self.check_buttons = []

        if checklist_mode:
            flowbox = Gtk.FlowBox()
            flowbox.set_valign(Gtk.Align.START)
            flowbox.set_max_children_per_line(2)  # Two columns like standard menus
            flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
            flowbox.set_homogeneous(True)  # Make all children the same size
            flowbox.set_row_spacing(8)     # Reduce vertical spacing between rows
            flowbox.set_column_spacing(10) # Add some horizontal spacing between columns
            flowbox.set_margin_start(40)   # Symmetric margins for consistent layout
            flowbox.set_margin_end(40)
            self.check_buttons = []

            for script_info in scripts:
                check = Gtk.CheckButton(label=script_info['name'])
                check.script_info = script_info
                check.set_tooltip_text(script_info['description'])
                check.set_size_request(140, 20)  # Reduce height for tighter spacing
                flowbox.add(check)
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
            vbox.pack_start(flowbox, True, True, 0)

            self.scripts_flowbox.add(vbox)
            self.scripts_flowbox.show_all()
        else:
            for script_info in scripts:
                widget = self.create_item_widget(script_info)
                widget.set_tooltip_text(script_info['description'])
                widget.connect("button-press-event", self.on_script_clicked)
                self.scripts_flowbox.add(widget)
            self.scripts_flowbox.show_all()

    def on_install_checklist(self, button):
        """Run checked scripts sequentially."""
        # Check if reboot is required before proceeding
        if self.reboot_required:
            self._show_reboot_warning_dialog()
            return
            
        checklist_helper.handle_install_checklist(
            self.check_buttons, 
            self, 
            self._on_dialog_closed,
            self.translations
        )

    def run_script_with_callback(self, script_info, callback):
        """Run a script and call callback when done."""
        dialog = Gtk.Dialog(title=f"Running \"{script_info['name']}\"", transient_for=self, flags=0)
        close_button = dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        dialog.set_default_size(600, 400)
        dialog.set_deletable(False)
        close_button.set_sensitive(False)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        textview = Gtk.TextView()
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        textview.set_monospace(True)
        scrolled_window.add(textview)
        box = dialog.get_content_area()
        box.add(scrolled_window)
        dialog.show_all()
        text_buffer = textview.get_buffer()
        def thread_func():
            try:
                self.running_process = subprocess.Popen(
                    ['bash', script_info['path']], stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True
                )
                for line in self.running_process.stdout:
                    GLib.idle_add(self._append_text_to_buffer, text_buffer, line)
                self.running_process.wait()
                return_code_msg = f"\n--- Script finished with exit code: {self.running_process.returncode} ---"
                GLib.idle_add(self._append_text_to_buffer, text_buffer, return_code_msg)
                
                # Check if script requires reboot after successful execution
                if self.running_process.returncode == 0:
                    system_compat_keys = compat.get_system_compat_keys()
                    if parser.script_requires_reboot(script_info['path'], system_compat_keys):
                        self.reboot_required = True
                        
            except Exception as e:
                error_msg = f"\n--- An unexpected error occurred: {e} ---"
                GLib.idle_add(self._append_text_to_buffer, text_buffer, error_msg)
            finally:
                GLib.idle_add(close_button.set_sensitive, True)
                dialog.connect("response", lambda *args: (self._on_dialog_closed(dialog, None), callback()))
        thread = threading.Thread(target=thread_func)
        thread.start()

    def on_cancel_checklist(self, button):
        """Uncheck all boxes, remove checklist buttons from footer, and return to main menu."""
        for cb in self.check_buttons:
            cb.set_active(False)
        # Remove checklist buttons from footer
        for child in self.footer_widget.checklist_button_box.get_children():
            self.footer_widget.checklist_button_box.remove(child)
        self.show_categories_view()

    def on_category_clicked(self, widget, event):
        """Handles category click or root script click."""
        # Check if reboot is required before proceeding
        if self.reboot_required:
            self._show_reboot_warning_dialog()
            return
            
        info = widget.info
        # If this is a root script (shown as a category), execute it directly
        if info.get('is_script'):
            if not self.script_is_running:
                # Show confirmation dialog before executing root script
                if not confirm_helper.show_single_script_confirmation(info, self, self.translations):
                    return  # User cancelled
                    
                self.script_is_running = True
                dialog = Gtk.Dialog(title=f"Running \"{info['name']}\"", transient_for=self, flags=0)
                close_button = dialog.add_button("Close", Gtk.ResponseType.CLOSE)
                dialog.set_default_size(600, 400)
                dialog.set_deletable(False)
                close_button.set_sensitive(False)
                scrolled_window = Gtk.ScrolledWindow()
                scrolled_window.set_hexpand(True)
                scrolled_window.set_vexpand(True)
                textview = Gtk.TextView()
                textview.set_editable(False)
                textview.set_cursor_visible(False)
                textview.set_monospace(True)
                scrolled_window.add(textview)
                box = dialog.get_content_area()
                box.add(scrolled_window)
                dialog.show_all()
                text_buffer = textview.get_buffer()
                thread = threading.Thread(target=self._execute_script_thread, args=(info['path'], text_buffer, dialog, close_button))
                thread.start()
        else:
            self.load_scripts(info)
            self.show_scripts_view(info['name'])

    def on_script_clicked(self, widget, event):
        """Handles script click by creating the dialog and starting the thread."""
        if self.script_is_running:
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
        
        dialog = Gtk.Dialog(title=f"Running \"{info['name']}\"", transient_for=self, flags=0)
        # FIX 1: Get a direct reference to the button here in the main thread.
        close_button = dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        
        dialog.set_default_size(600, 400)
        dialog.set_deletable(False)
        close_button.set_sensitive(False) # Disable the button using the direct reference

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)

        textview = Gtk.TextView()
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        textview.set_monospace(True)
        
        scrolled_window.add(textview)
        box = dialog.get_content_area()
        box.add(scrolled_window)
        dialog.show_all()

        text_buffer = textview.get_buffer()
        # FIX 2: Pass the direct button reference to the thread.
        thread = threading.Thread(target=self._execute_script_thread, args=(info['path'], text_buffer, dialog, close_button))
        thread.start()

    # FIX 3: The thread function now accepts the 'close_button' argument.
    def _execute_script_thread(self, script_path, text_buffer, dialog, close_button):
        """Runs in background, executes script, and sends output to GUI thread."""
        try:
            self.running_process = subprocess.Popen(
                ['bash', script_path], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True
            )
            for line in self.running_process.stdout:
                GLib.idle_add(self._append_text_to_buffer, text_buffer, line)
            
            self.running_process.wait()
            return_code_msg = f"\n--- Script finished with exit code: {self.running_process.returncode} ---"
            GLib.idle_add(self._append_text_to_buffer, text_buffer, return_code_msg)

            # Check if script requires reboot after successful execution
            if self.running_process.returncode == 0:
                system_compat_keys = compat.get_system_compat_keys()
                if parser.script_requires_reboot(script_path, system_compat_keys):
                    self.reboot_required = True

        except Exception as e:
            error_msg = f"\n--- An unexpected error occurred: {e} ---"
            GLib.idle_add(self._append_text_to_buffer, text_buffer, error_msg)

        finally:
            # Now we use the direct reference, which is thread-safe.
            GLib.idle_add(close_button.set_sensitive, True)
            dialog.connect("response", self._on_dialog_closed)

    def _append_text_to_buffer(self, buffer, text):
        """Safely updates the Gtk.TextView from another thread."""
        buffer.insert(buffer.get_end_iter(), text)
        return False

    def _on_dialog_closed(self, dialog, response_id):
        """Cleans up after the script execution dialog is closed."""
        if self.running_process and self.running_process.poll() is None:
            self.running_process.terminate()
        
        self.running_process = None
        self.script_is_running = False
        dialog.destroy()

    def _show_reboot_warning_dialog(self):
        """Shows a dialog warning that a reboot is required before continuing."""
        reboot_helper.handle_reboot_requirement(
            self, 
            self.translations, 
            self._close_application
        )
    
    def _close_application(self):
        """Closes the application gracefully."""
        if self.running_process and self.running_process.poll() is None:
            self.running_process.terminate()
        self.get_application().quit()

    def on_back_button_clicked(self, widget):
        """Handles the back button click."""
        self.show_categories_view()
        
    def show_categories_view(self):
        """Switches to the main categories view."""
        self.main_stack.set_visible_child_name("categories")
        self.back_button.hide()
        self.header_bar.props.title = "LinuxToys"
        self.header_widget.show()
        self.footer_widget.show()
        self.footer_widget.show_menu_footer()

    def show_scripts_view(self, category_name):
        """Switches to the view showing scripts in a category."""
        self.main_stack.set_visible_child_name("scripts")
        self.back_button.show()
        self.header_bar.props.title = f"LinuxToys: {category_name}"
        self.header_widget.hide()
        # Show footer only if checklist mode
        # Find the category info by name
        categories = parser.get_categories(self.translations)
        category_info = next((cat for cat in categories if cat['name'] == category_name), None)
        if category_info and category_info.get('mode', 'menu') == 'checklist':
            self.footer_widget.show()
            self.footer_widget.show_checklist_footer()
        else:
            self.footer_widget.hide()
