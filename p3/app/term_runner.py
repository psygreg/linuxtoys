import sys
import os
import subprocess

from . import dev_mode, reboot_helper
from .gtk_common import GLib, Gtk, Vte
from .term_registry import ExecutionRegistry
from .antenna import antenna
from .library_loader import script_command, script_environment

class TerminalRunner:
    @staticmethod
    def _has_flatpak_apps():
        """Return whether at least one Flatpak application is currently installed."""
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False

        return result.returncode == 0 and bool(result.stdout.strip())

    def _run_next_script(self):
        if self.script_queue and not hasattr(self, "_flatpak_apps_present_before_run"):
            self._flatpak_apps_present_before_run = self._has_flatpak_apps()

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
            self._clear_runner_lock()
            self.vbox_main.button_run.set_sensitive(True)
            self.terminal.set_can_focus(True)
            self.vbox_main.button_run.grab_focus()
            
            # Show the Flatpak session-path notice when Flatpak itself was installed
            # during this run, or when this run installed the system's first Flatpak app.
            flatpak_was_installed = getattr(self, "_flatpak_installed_detected", False)
            had_flatpak_apps = getattr(self, "_flatpak_apps_present_before_run", True)
            first_flatpak_app_installed = (
                not had_flatpak_apps and self._has_flatpak_apps()
            )

            if flatpak_was_installed or first_flatpak_app_installed:
                reboot_helper.show_flatpak_installed_info_dialog(
                    self.parent, self.translations
                )

            self._flatpak_installed_detected = False
            if hasattr(self, "_flatpak_apps_present_before_run"):
                del self._flatpak_apps_present_before_run

            return
 
        self.parent._script_running = True
        current_script = self.script_queue.pop(0)
        self.vbox_main._update_header_labels(current_script)
 
        # Add script to execution history
        script_name = current_script.get("name", "unknown")
        registry_name = current_script.get("registry_name", script_name)
        self._current_script_name = registry_name  # Stable identity used by the registry
        self._current_script_display_name = script_name
        self.executed_scripts.append(current_script)
        antenna.add_script_to_history(script_name)
        
        # Clear transmap file for new script execution
        try:
            self._transmap_path = self._select_transmap_path()
        except RuntimeError as error:
            print(f"Failed to initialize transaction map: {error}", file=sys.stderr)
            self._transmap_path = ""
 
        script_path = current_script.get("path", "true")
        if current_script.get("reboot") == "yes":
            self.parent.reboot_required = True
 
        self._self_update = current_script.get("self_update", False)
        self._cleanup_script_path = current_script.get("cleanup_path")
        self._current_action_is_removal = bool(self._cleanup_script_path)
 
        child_env = script_environment(current_script, os.environ.copy())
        self._prepare_runner_state()
        if self._runner_state_path:
            child_env["LINUXTOYS_RUNNER_STATE"] = self._runner_state_path
        else:
            child_env.pop("LINUXTOYS_RUNNER_STATE", None)
        if self._transmap_path:
            child_env["TRANSMAP_PATH"] = self._transmap_path
        else:
            child_env.pop("TRANSMAP_PATH", None)
        # Export CHECKLIST_RUN when running multiple scripts in sequence
        if self.total_scripts > 1:
            child_env['CHECKLIST_RUN'] = '1'
        # SCRIPT_DIR is set by linuxtoys.py at startup relative to the entry point
        # This ensures all scripts can find their libs at the same location
        child_env_list = [f"{key}={value}" for key, value in child_env.items()]
 
        if dev_mode.is_dev_mode_enabled():
            lib_path = os.path.dirname(__file__)
            shell_exec = [
                sys.executable,
                "-c",
                f'import sys; sys.path.append("{lib_path}"); import dev_mode; dev_mode.dry_run_script("{script_path}")',
            ]
 
        else:
            shell_exec = script_command(script_path, child_env["SCRIPT_DIR"])

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
        # A dying child must never leave navigation locked, including fatal/exit 100 paths.
        self._clear_runner_lock()

        if getattr(self, "_cleanup_script_path", None):
            try:
                if os.path.exists(self._cleanup_script_path):
                    os.remove(self._cleanup_script_path)
            except Exception:
                pass
            self._cleanup_script_path = None
 
        # Handle transmap file based on exit status
        transmap_path = getattr(self, "_transmap_path", "")
        
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
                
                self._remove_transmap(transmap_path)
            
            elif exit_code == 100:
                # User cancelled - clean up and wipe transmap but don't save to registry
                ExecutionRegistry._cleanup_tmp_noram_dirs(transmap_path)
                
                self._remove_transmap(transmap_path)
        
        else:
            # Signal termination (e.g., Ctrl+C) - clean up and wipe transmap
            ExecutionRegistry._cleanup_tmp_noram_dirs(transmap_path)
            
            self._remove_transmap(transmap_path)
 
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
                getattr(self, "_current_script_display_name", script_name),
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
                    self._remove_transmap(transmap_path)
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

    def _prepare_runner_state(self):
        """Create/reset the shell-to-runner state channel and start watching it."""
        if not getattr(self, "_runner_state_path", ""):
            try:
                directory = "/tmp/linuxtoys"
                os.makedirs(directory, mode=0o700, exist_ok=True)
                self._runner_state_path = os.path.join(
                    directory, f"runner-state-{os.getpid()}-{id(self)}"
                )
            except OSError:
                self._runner_state_path = ""

        if not self._runner_state_path:
            return

        try:
            with open(self._runner_state_path, "w", encoding="utf-8"):
                pass
            os.chmod(self._runner_state_path, 0o600)
        except OSError:
            self._runner_state_path = ""
            return

        self._set_runner_locked(False)
        if not getattr(self, "_runner_state_watch_id", None):
            self._runner_state_watch_id = GLib.timeout_add(
                100, self._poll_runner_state
            )

    def _poll_runner_state(self):
        path = getattr(self, "_runner_state_path", "")
        if not path:
            self._runner_state_watch_id = None
            return False

        try:
            with open(path, "r", encoding="utf-8") as state_file:
                locked = bool(state_file.read().strip())
        except OSError:
            locked = False

        self._set_runner_locked(locked)
        return True

    def _set_runner_locked(self, locked):
        locked = bool(locked)
        self._runner_navigation_locked = locked
        self.parent._runner_navigation_locked = locked

        # A package transaction is intentionally non-interruptible from the UI.
        # Keep terminal output visible, but prevent keyboard input (including
        # Ctrl+C) from reaching the foreground process while the lock is active.
        terminal = getattr(self, "terminal", None)
        if terminal is not None:
            terminal.set_input_enabled(not locked)

        back_button = getattr(self.parent, "back_button", None)
        if back_button is not None:
            back_button.set_sensitive(not locked)

    def _clear_runner_lock(self):
        self._set_runner_locked(False)
        path = getattr(self, "_runner_state_path", "")
        if path:
            try:
                with open(path, "w", encoding="utf-8"):
                    pass
            except OSError:
                pass

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
    
    @staticmethod
    def _select_transmap_path() -> str:
        """Select and prepare a writable transaction-map location."""
        candidates = (
            "/tmp/linuxtoys",
            os.path.expanduser("~/.cache/linuxtoys/tmp"),
        )

        for directory in candidates:
            try:
                os.makedirs(directory, mode=0o700, exist_ok=True)

                if not os.path.isdir(directory):
                    continue

                transmap_path = os.path.join(directory, "transmap")

                # Opening it verifies that the directory and file are writable.
                with open(transmap_path, "w", encoding="utf-8"):
                    pass

                try:
                    os.chmod(transmap_path, 0o600)
                except OSError:
                    pass

                return transmap_path
            except OSError:
                continue

        raise RuntimeError("Could not create a writable transaction map")

    @staticmethod
    def _remove_transmap(transmap_path: str) -> None:
        if not transmap_path:
            return

        try:
            os.remove(transmap_path)
        except FileNotFoundError:
            pass
        except OSError:
            pass
