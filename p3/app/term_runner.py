import sys
import os

from . import dev_mode, reboot_helper
from .gtk_common import GLib, Gtk, Vte, get_toplevel_window
from .term_registry import ExecutionRegistry
from .updater.update_dialog import DialogRestart
from .antenna import antenna

class TerminalRunner:
    def _run_next_script(self):
        if not self.script_queue:
            # Use translatable done text
            done_label = self.translations.get("term_view_done", " Done ")
            done_text = self.translations.get("term_view_done_text", "Done")
            self.vbox_main.button_run.set_label(done_label)
            self.vbox_main.button_run.set_image(
                Gtk.Image.new_from_icon_name("emblem-ok-symbolic", Gtk.IconSize.BUTTON)
            )
            self.vbox_main.progress_bar.set_text(done_text)
            handler_id = getattr(self, "_run_button_handler_id", None)
            if handler_id is not None:
                try:
                    self.vbox_main.button_run.disconnect(handler_id)
                except (TypeError, ValueError):
                    pass
            self._run_button_handler_id = self.vbox_main.button_run.connect(
                "clicked", self.on_done_clicked
            )
            self.parent._script_running = False
            self.vbox_main.button_run.set_sensitive(True)
            self.terminal.set_can_focus(True)
            self.vbox_main.button_run.grab_focus()
            
            # Check if flatpak was installed during script execution and show info if needed
            if getattr(self, "_flatpak_installed_detected", False):
                reboot_helper.show_flatpak_installed_info_dialog(
                    self.parent, self.translations
                )
                # Reset the flag after showing the dialog
                self._flatpak_installed_detected = False
            
            return
 
        self.parent._script_running = True
        current_script = self.script_queue.pop(0)
        self.vbox_main._update_header_labels(current_script)
 
        # Add script to execution history
        script_name = current_script.get("name", "unknown")
        self._current_script_name = script_name  # Store for registry
        self.executed_scripts.append(current_script)
        antenna.add_script_to_history(script_name)
        
        # Clear transmap file for new script execution
        try:
            transmap_path = "/tmp/linuxtoys/transmap"
            open(transmap_path, "w").close()  # Truncate/clear the file
        except (IOError, OSError):
            pass  # Silently ignore if transmap cannot be cleared
 
        script_path = current_script.get("path", "true")
        if current_script.get("reboot") == "yes":
            self.parent.reboot_required = True
 
        self._self_update = current_script.get("self_update", False)
        self._cleanup_script_path = current_script.get("cleanup_path")
        self._current_action_is_removal = bool(self._cleanup_script_path)
 
        child_env = os.environ.copy()
        # Export CHECKLIST_RUN when running multiple scripts in sequence
        if self.total_scripts > 1:
            child_env['CHECKLIST_RUN'] = '1'
        # SCRIPT_DIR is set by linuxtoys.py at startup relative to the entry point
        # This ensures all scripts can find their libs at the same location
        child_env_list = [f"{key}={value}" for key, value in child_env.items()]
 
        shell_exec = ["/bin/bash", f"{script_path}"]
        if dev_mode.is_dev_mode_enabled():
            lib_path = os.path.dirname(__file__)
            shell_exec = [
                sys.executable,
                "-c",
                f'import sys; sys.path.append("{lib_path}"); import dev_mode; dev_mode.dry_run_script("{script_path}")',
            ]
 
        self.terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            None,
            shell_exec,
            child_env_list,
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            None,
        )
 
        # Shift focus to terminal to capture user keyboard input
        # This prevents accidental cancellation when search bar or other widgets have focus
        self.terminal.grab_focus()
 
        self.vbox_main.button_run.set_sensitive(False)
        self.vbox_main.button_remove.set_sensitive(False)

    def on_child_exit(self, term, status):
        if getattr(self, "_cleanup_script_path", None):
            try:
                if os.path.exists(self._cleanup_script_path):
                    os.remove(self._cleanup_script_path)
            except Exception:
                pass
            self._cleanup_script_path = None
 
        if self._self_update:
            toplevel = get_toplevel_window(self)
            if toplevel is not None:
                DialogRestart(parent=toplevel).show()
 
        # Handle transmap file based on exit status
        transmap_path = "/tmp/linuxtoys/transmap"
        
        if os.WIFEXITED(status):
            exit_code = os.WEXITSTATUS(status)
            
            if exit_code == 0:
                # Success - save to registry and wipe transmap
                script_name = getattr(self, "_current_script_name", "unknown")
                ExecutionRegistry._save_to_registry(script_name, transmap_path)
                
                # Check if flatpak was installed during this script before transmap is deleted
                if not getattr(self, "_flatpak_installed_detected", False):
                    if os.path.exists(transmap_path):
                        try:
                            with open(transmap_path, "r") as f:
                                content = f.read()
                                if "pkg flatpak" in content or "pkg file flatpak" in content:
                                    self._flatpak_installed_detected = True
                        except Exception:
                            pass
                
                # Clean up any temp directories created by prep_tmp_noram before removing transmap
                ExecutionRegistry._cleanup_tmp_noram_dirs(transmap_path)
                
                try:
                    if os.path.exists(transmap_path):
                        os.remove(transmap_path)
                except (IOError, OSError):
                    pass  # Silently ignore if transmap cannot be removed
            
            elif exit_code == 100:
                # User cancelled - clean up and wipe transmap but don't save to registry
                ExecutionRegistry._cleanup_tmp_noram_dirs(transmap_path)
                
                try:
                    if os.path.exists(transmap_path):
                        os.remove(transmap_path)
                except (IOError, OSError):
                    pass  # Silently ignore if transmap cannot be removed
        
        else:
            # Signal termination (e.g., Ctrl+C) - clean up and wipe transmap
            ExecutionRegistry._cleanup_tmp_noram_dirs(transmap_path)
            
            try:
                if os.path.exists(transmap_path):
                    os.remove(transmap_path)
            except (IOError, OSError):
                pass  # Silently ignore if transmap cannot be removed
 
        # Check for error exit codes and handle auto-reversion or bug report
        if self._is_error_exit_code(status) and not self._current_action_is_removal:
            # Only auto-handle for regular scripts, not removal operations
            # Save the error to registry before attempting auto-revert
            script_name = getattr(self, "_current_script_name", "unknown")
            ExecutionRegistry._save_to_registry(script_name, transmap_path)
            
            auto_reports_enabled = getattr(self.parent, 'auto_error_reports_enabled', False)
            
            # Submit bug report first if enabled (before auto-revert consumes transmap)
            if auto_reports_enabled:
                self._auto_submit_bug_report_on_error()
            
            # Try to auto-revert if there are operations in the transmap
            auto_revert_entry = ExecutionRegistry._try_auto_revert(
                transmap_path,
                script_name,
                self.translations,
            )
            
            if auto_revert_entry:
                # Auto-revert was successful, execute the reversion script
                self.script_queue = [auto_revert_entry]
                self.total_scripts = 1
                self.scripts_executed = 0
                self.vbox_main.progress_bar.set_fraction(0.0)
                self.vbox_main._update_header_labels(auto_revert_entry)
                waiting_text = self.translations.get(
                    "term_view_waiting", "Waiting {current}/{total}"
                )
                self.vbox_main.progress_bar.set_text(waiting_text.format(current=0, total=1))
                self.vbox_main.button_remove.set_sensitive(False)
                self._run_next_script()
                return  # Skip further processing
            else:
                # No auto-revert possible, wipe transmap only if auto-reporting was enabled
                if auto_reports_enabled:
                    try:
                        if os.path.exists(transmap_path):
                            os.remove(transmap_path)
                    except (IOError, OSError):
                        pass
                # If auto-reporting is disabled, preserve transmap for user to potentially report manually
 
        self.scripts_executed += 1
        progress = self.scripts_executed / self.total_scripts
        self.vbox_main.progress_bar.set_fraction(progress)
        # Use translatable running/removing text
        running_text = self.translations.get(
            "term_view_running", "Running {current}/{total}"
        )
        if getattr(self, "_current_action_is_removal", False):
            running_text = self.translations.get(
                "term_view_removing", "Removing {current}/{total}"
            )
        self.vbox_main.progress_bar.set_text(
            running_text.format(current=self.scripts_executed, total=self.total_scripts)
        )
        self._run_next_script()

    def _is_error_exit_code(self, status):
        """Check if the exit status indicates an error (not success, not cancelled, not normal signal)."""
        # Extract the actual exit code from status
        if os.WIFEXITED(status):
            exit_code = os.WEXITSTATUS(status)
            # 0 = success, 100 = user cancelled
            return exit_code not in (0, 100)
        # If terminated by signal (e.g., keyboard interrupt), it's not an error to report
        # Signals are expected user interactions (Ctrl+C = SIGINT)
        return False