from .gtk_common import Gtk, GLib

import subprocess, os
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
        self.local_env = os.environ.copy()
        # Legacy runtime is in app/legacy/, so we need to go up two levels to reach p3/
        self.local_env["SCRIPT_DIR"] = str(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        
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
    
    def run_scripts_sequentially(self, scripts_list, on_completion=None, on_reboot_required=None):
        """
        Run multiple scripts sequentially in a single dialog window.
        
        Args:
            scripts_list: List of script dictionaries/paths to run sequentially
            on_completion: Callback function called when all scripts complete
            on_reboot_required: Callback function called if any script requires reboot
        """
        if not scripts_list:
            if on_completion:
                on_completion()
            return None
        
        self.on_completion = on_completion
        self.on_reboot_required = on_reboot_required
        self.scripts_queue = scripts_list.copy()
        self.current_script_index = 0
        self.total_scripts = len(scripts_list)
        
        # Set flag to indicate this is a checklist execution
        self.local_env['LINUXTOYS_CHECKLIST'] = '1'
        
        # Create the dialog with updated title for multiple scripts
        dialog_title = self.translations.get('script_runner_checklist_title', 'Running Checklist ({current}/{total})')
        dialog_title = dialog_title.format(current=1, total=self.total_scripts)
        
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
        self.text_buffer = textview.get_buffer()
        
        # Connect dialog response to cleanup
        self.dialog.connect("response", self._on_dialog_closed)
        
        # Start the sequential execution
        self._run_next_script_in_sequence()
        
        return self.dialog
    
    def _run_next_script_in_sequence(self):
        """Execute the next script in the sequence."""
        if self.current_script_index >= len(self.scripts_queue):
            # All scripts completed
            GLib.idle_add(self._append_text_to_buffer, self.text_buffer, 
                         f"\n{'='*50}\n✅ All scripts completed successfully!\n{'='*50}\n")
            GLib.idle_add(self._enable_close_button)
            if self.on_completion:
                self.on_completion()
            return
        
        current_script = self.scripts_queue[self.current_script_index]
        script_info = current_script if isinstance(current_script, dict) else {'path': current_script}
        
        # Get script name for display
        if isinstance(script_info, dict):
            script_name = script_info.get('name', 'Unknown Script')
        else:
            import os
            script_name = os.path.basename(script_info) if script_info else 'Unknown Script'
        
        # Update dialog title
        dialog_title = self.translations.get('script_runner_checklist_title', 'Running Checklist ({current}/{total})')
        dialog_title = dialog_title.format(current=self.current_script_index + 1, total=self.total_scripts)
        GLib.idle_add(lambda: self.dialog.set_title(dialog_title))
        
        # Add separator and script header
        separator = f"\n{'='*50}\n"
        header = f"📦 Script {self.current_script_index + 1}/{self.total_scripts}: {script_name}\n"
        separator += header + "="*50 + "\n"
        GLib.idle_add(self._append_text_to_buffer, self.text_buffer, separator)
        
        # Start script execution in a thread
        thread = threading.Thread(
            target=self._execute_script_in_sequence, 
            args=(script_info,)
        )
        thread.start()
    
    def _execute_script_in_sequence(self, script_info):
        """Execute a single script in the sequence and move to the next."""
        try:
            # Extract script path
            script_path = script_info.get('path') if isinstance(script_info, dict) else script_info
            
            # Check if we should dry-run instead of execute
            try:
                from .dev_mode import should_dry_run_scripts, dry_run_script
                if should_dry_run_scripts():
                    GLib.idle_add(self._append_text_to_buffer, self.text_buffer, 
                                "🧪 DEVELOPER MODE: Dry-run validation instead of execution\n\n")
                    
                    # Capture dry-run output
                    import io
                    import sys
                    from contextlib import redirect_stdout
                    
                    output_buffer = io.StringIO()
                    with redirect_stdout(output_buffer):
                        dry_run_result = dry_run_script(script_path)
                    
                    # Send dry-run output to GUI
                    dry_run_output = output_buffer.getvalue()
                    GLib.idle_add(self._append_text_to_buffer, self.text_buffer, dry_run_output)
                    
                    # Simulate successful completion for dry run
                    exit_code = 0 if dry_run_result['syntax_valid'] and dry_run_result['dependencies_valid'] else 1
                    
                else:
                    # Normal execution
                    self.running_process = subprocess.Popen(
                        ['bash', script_path],
                        env=self.local_env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    # Read output line by line and send to GUI
                    for line in iter(self.running_process.stdout.readline, ''):
                        if line:
                            GLib.idle_add(self._append_text_to_buffer, self.text_buffer, line)
                    
                    # Wait for process to complete
                    exit_code = self.running_process.wait()
                    
            except ImportError:
                # dev_mode not available, continue with normal execution
                self.running_process = subprocess.Popen(
                    ['bash', script_path],
                    env=self.local_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                # Read output line by line and send to GUI
                for line in iter(self.running_process.stdout.readline, ''):
                    if line:
                        GLib.idle_add(self._append_text_to_buffer, self.text_buffer, line)
                
                # Wait for process to complete
                exit_code = self.running_process.wait()
            
            # Show completion status
            if exit_code == 0:
                GLib.idle_add(self._append_text_to_buffer, self.text_buffer, 
                             f"\n✅ Script completed successfully (exit code: {exit_code})\n")
            else:
                GLib.idle_add(self._append_text_to_buffer, self.text_buffer, 
                             f"\n❌ Script failed (exit code: {exit_code})\n")
            
            # Check if reboot is required for this script
            if parser.script_requires_reboot(script_path, compat.get_system_compat_keys()):
                if self.on_reboot_required:
                    GLib.idle_add(lambda: self.on_reboot_required())
            
        except Exception as e:
            error_msg = f"\n❌ Error executing script: {str(e)}\n"
            GLib.idle_add(self._append_text_to_buffer, self.text_buffer, error_msg)
        
        finally:
            # Move to next script
            self.current_script_index += 1
            GLib.idle_add(self._run_next_script_in_sequence)
    
    def _enable_close_button(self):
        """Enable the close button when execution is complete."""
        if self.close_button:
            self.close_button.set_sensitive(True)
    
    def _execute_script_thread(self, script_info, text_buffer):
        """Runs in background, executes script, and sends output to GUI thread."""
        try:
            # Extract script path - handle both dict and direct path
            script_path = script_info.get('path') if isinstance(script_info, dict) else script_info
            
            # Check if we should dry-run instead of execute
            try:
                from .dev_mode import should_dry_run_scripts, dry_run_script
                if should_dry_run_scripts():
                    GLib.idle_add(self._append_text_to_buffer, text_buffer, 
                                "🧪 DEVELOPER MODE: Dry-run validation instead of execution\n\n")
                    
                    # Capture dry-run output
                    import io
                    import sys
                    from contextlib import redirect_stdout
                    
                    output_buffer = io.StringIO()
                    with redirect_stdout(output_buffer):
                        dry_run_result = dry_run_script(script_path)
                    
                    # Send dry-run output to GUI
                    dry_run_output = output_buffer.getvalue()
                    GLib.idle_add(self._append_text_to_buffer, text_buffer, dry_run_output)
                    
                    # Create a more complete mock process object
                    class MockProcess:
                        def __init__(self, return_code):
                            self.returncode = return_code
                            self.stdout = None
                            self.stderr = None
                            self.stdin = None
                            self._terminated = True
                        
                        def poll(self):
                            # Return the exit code if process is "finished"
                            return self.returncode
                        
                        def wait(self, timeout=None):
                            # Process is already "finished"
                            return self.returncode
                        
                        def terminate(self):
                            # Already terminated, nothing to do
                            pass
                        
                        def kill(self):
                            # Already terminated, nothing to do
                            pass
                        
                        def communicate(self, input=None, timeout=None):
                            # Return empty output since process is finished
                            return ('', '')
                        
                        def __repr__(self):
                            return f"MockProcess(returncode={self.returncode})"
                    
                    # Simulate process completion
                    exit_code = 0 if dry_run_result['syntax_valid'] and dry_run_result['dependencies_valid'] else 1
                    self.running_process = MockProcess(exit_code)
                    return
            except ImportError:
                pass  # dev_mode not available, continue with normal execution
            
            self.running_process = subprocess.Popen(
                ['bash', script_path], 
                env=self.local_env,
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
