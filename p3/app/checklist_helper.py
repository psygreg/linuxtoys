"""
Checklist functionality helper for LinuxToys
Handles checklist script execution and management
"""

from .gtk_common import Gtk

from . import script_runner


def run_scripts_sequentially(scripts, parent_window, on_dialog_closed_callback):
    """Run scripts one after another in the same ScriptRunner window."""
    if not scripts:
        return

    # Create a custom ScriptRunner that can handle multiple scripts
    class ChecklistScriptRunner(script_runner.ScriptRunner):
        def __init__(self, parent_window, script_list, translations=None):
            super().__init__(parent_window, translations)
            self.script_list = script_list
            self.current_script_index = 0
            
        def run_checklist(self, on_completion=None):
            """Run all scripts in the checklist sequentially."""
            self.on_completion = on_completion
            
            # Create dialog with checklist title
            script_names = [script['name'] for script in self.script_list]
            if len(script_names) == 1:
                title = script_names[0]
            else:
                title = f"Checklist ({len(script_names)} scripts)"
            
            dialog_title = self.translations.get('script_runner_title', 'Running "{script_name}"').format(script_name=title)
            self.dialog = script_runner.Gtk.Dialog(
                title=dialog_title, 
                transient_for=self.parent_window, 
                flags=0
            )
            
            # Add close button
            close_text = self.translations.get('script_runner_close', 'Close')
            self.close_button = self.dialog.add_button(close_text, script_runner.Gtk.ResponseType.CLOSE)
            
            # Configure dialog
            self.dialog.set_default_size(600, 400)
            self.dialog.set_deletable(False)
            self.close_button.set_sensitive(False)
            
            # Create scrolled text view for output
            scrolled_window = script_runner.Gtk.ScrolledWindow()
            scrolled_window.set_hexpand(True)
            scrolled_window.set_vexpand(True)
            
            textview = script_runner.Gtk.TextView()
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
            
            # Start running the first script
            self._run_next_script()
            
            return self.dialog
            
        def _run_next_script(self):
            """Run the next script in the list."""
            if self.current_script_index >= len(self.script_list):
                # All scripts completed
                script_runner.GLib.idle_add(self.close_button.set_sensitive, True)
                if self.on_completion:
                    script_runner.GLib.idle_add(self.on_completion)
                return
            
            current_script = self.script_list[self.current_script_index]
            
            # Add separator between scripts (except for the first one)
            if self.current_script_index > 0:
                separator = f"\n{'='*60}\n"
                script_runner.GLib.idle_add(self._append_text_to_buffer, self.text_buffer, separator)
            
            # Add script header
            script_header = f"Running script {self.current_script_index + 1}/{len(self.script_list)}: {current_script['name']}\n"
            script_runner.GLib.idle_add(self._append_text_to_buffer, self.text_buffer, script_header)
            script_runner.GLib.idle_add(self._append_text_to_buffer, self.text_buffer, "-" * len(script_header) + "\n")
            
            # Start script execution thread
            import threading
            thread = threading.Thread(
                target=self._execute_current_script_thread, 
                args=(current_script,)
            )
            thread.start()
            
        def _execute_current_script_thread(self, script_info):
            """Execute the current script and move to the next one when done."""
            try:
                # Extract script path
                script_path = script_info.get('path') if isinstance(script_info, dict) else script_info
                
                # Check if we should dry-run instead of execute
                try:
                    from .dev_mode import should_dry_run_scripts, dry_run_script
                    if should_dry_run_scripts():
                        script_runner.GLib.idle_add(self._append_text_to_buffer, self.text_buffer, 
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
                        script_runner.GLib.idle_add(self._append_text_to_buffer, self.text_buffer, dry_run_output)
                        
                        # Simulate process completion
                        exit_code = 0 if dry_run_result['syntax_valid'] and dry_run_result['dependencies_valid'] else 1
                        return_code_msg = f"\n--- Script finished with exit code: {exit_code} ---\n"
                        script_runner.GLib.idle_add(self._append_text_to_buffer, self.text_buffer, return_code_msg)
                        
                        # Move to next script
                        self.current_script_index += 1
                        script_runner.GLib.idle_add(self._run_next_script)
                        return
                except ImportError:
                    pass  # dev_mode not available, continue with normal execution
                
                # Normal script execution
                import subprocess
                self.running_process = subprocess.Popen(
                    ['bash', script_path], 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, 
                    bufsize=1, 
                    universal_newlines=True
                )
                
                # Stream output to dialog
                for line in self.running_process.stdout:
                    script_runner.GLib.idle_add(self._append_text_to_buffer, self.text_buffer, line)
                
                # Wait for process to complete
                self.running_process.wait()
                return_code_text = self.translations.get('script_runner_finished', 'Script finished with exit code: {exit_code}').format(exit_code=self.running_process.returncode)
                return_code_msg = f"\n--- {return_code_text} ---\n"
                script_runner.GLib.idle_add(self._append_text_to_buffer, self.text_buffer, return_code_msg)
                
            except Exception as e:
                error_msg = f"\n--- An unexpected error occurred: {e} ---\n"
                script_runner.GLib.idle_add(self._append_text_to_buffer, self.text_buffer, error_msg)
            
            # Move to next script
            self.current_script_index += 1
            script_runner.GLib.idle_add(self._run_next_script)
    
    # Create and run the checklist
    runner = ChecklistScriptRunner(parent_window, scripts)
    return runner.run_checklist(on_completion=on_dialog_closed_callback)


def handle_install_checklist(check_buttons, parent_window, on_dialog_closed_callback, translations=None):
    """Handle checklist installation - extract selected scripts and run them."""
    selected_scripts = [cb.script_info for cb in check_buttons if cb.get_active()]
    if not selected_scripts:
        return
    
    # Import confirm_helper here to avoid circular imports
    from . import confirm_helper
    
    # Show confirmation dialog before executing checklist
    if not confirm_helper.show_checklist_confirmation(selected_scripts, parent_window, translations or {}):
        return  # User cancelled
    
    run_scripts_sequentially(selected_scripts, parent_window, on_dialog_closed_callback)
