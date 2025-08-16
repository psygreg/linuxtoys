import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import subprocess
import threading
from . import parser
from . import compat


class ScriptRunner:
    """Handles execution of scripts in a dialog window with real-time output."""
    
    def __init__(self, parent_window, translations=None):
        self.parent_window = parent_window
        self.translations = translations or {}
        self.running_process = None
        self.dialog = None
        self.close_button = None
        
    def run_script(self, script_info, on_completion=None, on_reboot_required=None):
        """
        Run a script and display output in a dialog.
        
        Args:
            script_info: Dictionary containing script information (name, path, etc.)
            on_completion: Callback function called when script completes
            on_reboot_required: Callback function called if script requires reboot
        """
        self.on_completion = on_completion
        self.on_reboot_required = on_reboot_required
        
        # Create the dialog
        if isinstance(script_info, dict):
            script_name = script_info.get('name', 'Unknown Script')
        else:
            # If script_info is just a path string, extract filename
            import os
            script_name = os.path.basename(script_info) if script_info else 'Unknown Script'
        
        dialog_title = self.translations.get('script_runner_title', 'Running "{script_name}"').format(script_name=script_name)
        self.dialog = Gtk.Dialog(
            title=dialog_title, 
            transient_for=self.parent_window, 
            flags=0
        )
        
        # Add close button
        close_text = self.translations.get('script_runner_close', 'Close')
        self.close_button = self.dialog.add_button(close_text, Gtk.ResponseType.CLOSE)
        
        # Configure dialog
        self.dialog.set_default_size(600, 400)
        self.dialog.set_deletable(False)
        self.close_button.set_sensitive(False)
        
        # Create scrolled text view for output
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        
        textview = Gtk.TextView()
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        textview.set_monospace(True)
        
        scrolled_window.add(textview)
        
        # Add padding around the content area
        content_box = self.dialog.get_content_area()
        content_box.set_margin_left(12)
        content_box.set_margin_right(12)
        content_box.set_margin_top(12)
        
        content_box.add(scrolled_window)
        
        # Add padding to the action area (button area)
        action_area = self.dialog.get_action_area()
        action_area.set_margin_right(4)
        action_area.set_margin_bottom(6)
        action_area.set_margin_top(8)
        
        self.dialog.show_all()
        
        # Get text buffer for output
        text_buffer = textview.get_buffer()
        
        # Connect dialog response to cleanup
        self.dialog.connect("response", self._on_dialog_closed)
        
        # Start script execution thread
        thread = threading.Thread(
            target=self._execute_script_thread, 
            args=(script_info, text_buffer)
        )
        thread.start()
        
        return self.dialog
    
    def run_script_with_callback(self, script_info, callback):
        """
        Run a script and call callback when done.
        Legacy method for compatibility with existing checklist code.
        """
        def completion_handler():
            if callback:
                callback()
        
        return self.run_script(script_info, on_completion=completion_handler)
    
    def _execute_script_thread(self, script_info, text_buffer):
        """Runs in background, executes script, and sends output to GUI thread."""
        try:
            # Extract script path - handle both dict and direct path
            script_path = script_info.get('path') if isinstance(script_info, dict) else script_info
            
            self.running_process = subprocess.Popen(
                ['bash', script_path], 
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, 
                bufsize=1, 
                universal_newlines=True
            )
            
            # Stream output to dialog
            for line in self.running_process.stdout:
                GLib.idle_add(self._append_text_to_buffer, text_buffer, line)
            
            # Wait for process to complete
            self.running_process.wait()
            return_code_text = self.translations.get('script_runner_finished', 'Script finished with exit code: {exit_code}').format(exit_code=self.running_process.returncode)
            return_code_msg = f"\n--- {return_code_text} ---"
            GLib.idle_add(self._append_text_to_buffer, text_buffer, return_code_msg)
            
            # Check if script requires reboot after successful execution
            if self.running_process.returncode == 0:
                system_compat_keys = compat.get_system_compat_keys()
                if parser.script_requires_reboot(script_path, system_compat_keys):
                    if self.on_reboot_required:
                        GLib.idle_add(self.on_reboot_required)
                        
        except Exception as e:
            error_msg = f"\n--- An unexpected error occurred: {e} ---"
            GLib.idle_add(self._append_text_to_buffer, text_buffer, error_msg)
            
        finally:
            # Enable close button and trigger completion callback
            GLib.idle_add(self.close_button.set_sensitive, True)
            if self.on_completion:
                GLib.idle_add(self.on_completion)
    
    def _append_text_to_buffer(self, buffer, text):
        """Safely updates the Gtk.TextView from another thread."""
        buffer.insert(buffer.get_end_iter(), text)
        return False
    
    def _on_dialog_closed(self, dialog, response_id):
        """Cleans up after the script execution dialog is closed."""
        if self.running_process and self.running_process.poll() is None:
            self.running_process.terminate()
        
        self.running_process = None
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
            self.close_button = None
    
    def is_running(self):
        """Check if a script is currently running."""
        return self.running_process is not None and self.running_process.poll() is None
    
    def terminate(self):
        """Terminate the running script if any."""
        if self.running_process and self.running_process.poll() is None:
            self.running_process.terminate()
            self.running_process = None
