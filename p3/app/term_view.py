import os
import sys

from . import dev_mode, get_icon_path, reboot_helper
from .compat import should_enable_manual_revert, get_revert_capability
from .antenna import antenna
from requests.exceptions import ConnectionError, Timeout
from .gtk_common import Gdk, GdkPixbuf, GLib, Gtk, Pango, Vte
from .revert_helper import build_uninstall_script_entry, build_auto_revert_script_entry, _load_last_execution
from .updater.update_dialog import DialogRestart
from .action_registry import parse_registry_file


class InfosHead(Gtk.Box):
    def __init__(self, translations=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.translations = translations or {}
        vbox_infos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        self.label_name = Gtk.Label()
        self.label_name.set_halign(Gtk.Align.START)
        self.label_desc = Gtk.Label()
        self.label_desc.set_halign(Gtk.Align.START)
        self.label_desc.set_line_wrap(True)
        self.label_desc.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.label_repo = Gtk.Label()
        self.label_repo.set_halign(Gtk.Align.START)

        self.hbox_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.hbox_header.set_margin_left(32)
        self.hbox_header.set_margin_top(12)
        self.hbox_header.set_margin_right(32)
        self.hbox_header.set_margin_bottom(5)

        self.icon_head = Gtk.Image()
        self.hbox_header.pack_start(self.icon_head, False, False, 0)

        vbox_infos.pack_start(self.label_name, False, False, 0)
        vbox_infos.pack_start(self.label_desc, False, False, 0)
        vbox_infos.pack_start(self.label_repo, False, False, 0)

        self.hbox_header.pack_start(vbox_infos, True, True, 0)
        self.pack_start(self.hbox_header, False, False, 0)

        hbox_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Use translatable button label
        execute_label = self.translations.get("term_view_execute", " Execute ")
        self.button_run = Gtk.Button(label=execute_label)
        self.button_run.set_image(
            Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        )
        self.button_run.set_halign(Gtk.Align.START)
        self.button_run.set_size_request(125, 35)
        remove_label = self.translations.get("term_view_remove", " Remove ")
        self.button_remove = Gtk.Button(label=remove_label)
        self.button_remove.set_image(
            Gtk.Image.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
        )
        self.button_remove.set_halign(Gtk.Align.START)
        self.button_remove.set_size_request(125, 35)
        report_label = self.translations.get("report_label", " Report Bug ")
        self.button_copy = Gtk.Button(label=report_label)
        self.button_copy.set_image(
            Gtk.Image.new_from_icon_name("dialog-warning-symbolic", Gtk.IconSize.BUTTON)
        )
        self.button_copy.set_halign(Gtk.Align.START)
        self.button_copy.set_size_request(150, 35)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_fraction(0.0)

        hbox_controls.pack_start(self.button_run, False, False, 0)
        hbox_controls.pack_start(self.button_remove, False, False, 0)
        hbox_controls.pack_start(self.button_copy, False, False, 0)
        hbox_controls.pack_start(self.progress_bar, True, True, 0)

        vbox_infos.pack_start(hbox_controls, False, False, 10)

    def _update_header_labels(self, script_info: list):
        _name = GLib.markup_escape_text(script_info.get("name", ""))
        _desc = GLib.markup_escape_text(script_info.get("description", ""))
        _repo = GLib.markup_escape_text(script_info.get("repo", ""))
        self.label_name.set_markup(f"<big><big><b>{_name}</b></big></big>")
        self.label_desc.set_markup(f"{_desc}")
        self.label_repo.set_markup(f"<a href='{_repo}'>{_repo}</a>")

        icon_value = script_info.get("icon")
        if icon_value:
            icon_path = get_icon_path(icon_value)
            if icon_path:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    icon_path, 100, 100, True
                )
                self.icon_head.set_from_pixbuf(pixbuf)
            else:
                default_path = get_icon_path("local-script.svg")
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    default_path, 100, 100, True
                )
                self.icon_head.set_from_pixbuf(pixbuf)
        else:
            default_path = get_icon_path("local-script.svg")
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                default_path, 100, 100, True
            )
            self.icon_head.set_from_pixbuf(pixbuf)


class TermRunScripts(Gtk.Box):
    def __init__(
        self, scripts_infos: list, parent, translations=None, removable_script_info=None
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.parent = parent
        self.translations = translations or {}
        self.script_queue = scripts_infos.copy()
        self.removable_script_info = removable_script_info
        self.total_scripts = len(scripts_infos)
        self.scripts_executed = 0
        
        # Store revert capability of the removable script (if available)
        self.removable_script_revert_capability = None
        self.removable_script_manual_revert_enabled = False
        self.removable_script_has_registry_entry = False
        self.removable_script_revert_disabled = False
        if self.removable_script_info:
            script_path = self.removable_script_info.get('path')
            script_name = self.removable_script_info.get('name')
            if script_path:
                self.removable_script_revert_capability = get_revert_capability(script_path)
                self.removable_script_manual_revert_enabled = should_enable_manual_revert(script_path)
                # If revert capability is explicitly 'no', mark as disabled
                if self.removable_script_revert_capability == "no":
                    self.removable_script_revert_disabled = True
            if script_name:
                # Check if this script has a registry entry (was previously installed)
                operations = _load_last_execution(script_name)
                self.removable_script_has_registry_entry = bool(operations)
        
        # Track if current/first script has a registry entry for bug report visibility
        self.current_script_has_registry_entry = False
        if scripts_infos:
            first_script = scripts_infos[0]
            first_script_name = first_script.get('name')
            if first_script_name:
                operations = _load_last_execution(first_script_name)
                self.current_script_has_registry_entry = bool(operations)

        self.terminal = Vte.Terminal()
        self.terminal.connect("child-exited", self.on_child_exit)
        self.terminal.connect("key-press-event", self._on_terminal_key_press)
        self.terminal.set_vexpand(True)
        self.terminal.set_can_focus(True)

        self.vbox_main = InfosHead(translations)

        self.vbox_main.button_run.connect("clicked", self.on_button_run_clicked)
        self.vbox_main.button_remove.connect("clicked", self.on_button_remove_clicked)
        self.vbox_main.button_copy.connect("clicked", self.on_copy_clicked)
        self.vbox_main.button_remove.set_sensitive(bool(self.removable_script_info))
        self._set_remove_button_visibility()
        self._set_bug_report_button_visibility()
        
        # Use translatable waiting text
        waiting_text = self.translations.get(
            "term_view_waiting", "Waiting {current}/{total}"
        )
        self.vbox_main.progress_bar.set_text(
            waiting_text.format(current=self.scripts_executed, total=self.total_scripts)
        )

        self.vbox_main.pack_start(self.terminal, True, True, 0)

        self.set_border_width(12)
        self.add(self.vbox_main)

        # Connect key press event to handle Escape
        self.connect("key-press-event", self._on_key_press)

        if self.script_queue:
            self.vbox_main._update_header_labels(self.script_queue[0])

    def _set_remove_button_visibility(self):
        # Button shown if ALL conditions are met:
        # 1. There's a removable script
        # 2. Only one script in queue
        # 3. Revert is NOT explicitly disabled (# revert: no)
        # 4. Revert is actually available:
        #    - Revert capability is 'internal' (re-run workflow) - no registry check needed
        #    - OR manual revert is enabled AND there's a registry entry (script was previously installed)
        is_internal_revert = self.removable_script_revert_capability == "internal"
        revert_available = is_internal_revert or (self.removable_script_manual_revert_enabled and self.removable_script_has_registry_entry)
        if self.removable_script_info and self.total_scripts == 1 and revert_available and not self.removable_script_revert_disabled:
            self.vbox_main.button_remove.set_no_show_all(False)
            self.vbox_main.button_remove.show()
        else:
            self.vbox_main.button_remove.set_no_show_all(True)
            self.vbox_main.button_remove.hide()

    def _set_bug_report_button_visibility(self):
        """
        Set bug report button visibility based on:
        1. Auto error reporting is NOT enabled
        2. Script has been run before (exists in registry) OR is being run now
        """
        auto_reports_enabled = getattr(self.parent, 'auto_error_reports_enabled', False)
        
        # Hide button if auto error reports are enabled
        if auto_reports_enabled:
            self.vbox_main.button_copy.set_no_show_all(True)
            self.vbox_main.button_copy.hide()
        # Hide button if script has never been run before (not in registry)
        elif not self.current_script_has_registry_entry:
            self.vbox_main.button_copy.set_no_show_all(True)
            self.vbox_main.button_copy.hide()
        # Show button if both conditions are met
        else:
            self.vbox_main.button_copy.set_no_show_all(False)
            self.vbox_main.button_copy.show()

    def _show_remove_confirmation_dialog(self, script_name):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self.translations.get(
                "remove_confirm_title", "Remove Installed Components?"
            ),
        )
        dialog.format_secondary_text(
            self.translations.get(
                "remove_confirm_message",
                "LinuxToys will attempt to remove all components installed by '{script_name}'. Do you want to continue?",
            ).format(script_name=script_name)
        )
        dialog.add_button(
            self.translations.get("cancel_btn_label", "Cancel"), Gtk.ResponseType.CANCEL
        )
        dialog.add_button(self.translations.get("yes", "Yes"), Gtk.ResponseType.YES)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def _show_remove_not_available_dialog(self):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=self.translations.get(
                "remove_not_available_title", "Removal Not Available"
            ),
        )
        dialog.format_secondary_text(
            self.translations.get(
                "remove_not_available_message",
                "No removable components were detected for this script.",
            )
        )
        dialog.run()
        dialog.destroy()

    def _show_internal_revert_confirmation_dialog(self, script_name):
        """Show confirmation dialog for internal revert (re-run script)."""
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self.translations.get(
                "internal_revert_confirm_title", "Re-run Script for Removal?"
            ),
        )
        dialog.format_secondary_text(
            self.translations.get(
                "internal_revert_confirm_message",
                "This script has a custom removal method. Running it again will attempt to remove its components. Do you want to continue?",
            ).format(script_name=script_name)
        )
        dialog.add_button(
            self.translations.get("cancel_btn_label", "Cancel"), Gtk.ResponseType.CANCEL
        )
        dialog.add_button(self.translations.get("yes", "Yes"), Gtk.ResponseType.YES)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def on_button_remove_clicked(self, widget):
        if not self.removable_script_info or self.parent._script_running:
            return

        script_name = self.removable_script_info.get("name", "Script")
        is_internal_revert = self.removable_script_revert_capability == "internal"
        
        # Show appropriate confirmation dialog
        if is_internal_revert:
            if not self._show_internal_revert_confirmation_dialog(script_name):
                return
            # For internal revert, just re-queue the original script
            self.script_queue = [self.removable_script_info]
        else:
            if not self._show_remove_confirmation_dialog(script_name):
                return
            # For normal revert, build the uninstall script
            remove_script_entry = build_uninstall_script_entry(
                self.removable_script_info, self.translations
            )
            if not remove_script_entry:
                self._show_remove_not_available_dialog()
                return
            self.script_queue = [remove_script_entry]
        
        self.total_scripts = 1
        self.scripts_executed = 0
        self.vbox_main.progress_bar.set_fraction(0.0)
        self.vbox_main._update_header_labels(self.script_queue[0])
        waiting_text = self.translations.get(
            "term_view_waiting", "Waiting {current}/{total}"
        )
        self.vbox_main.progress_bar.set_text(waiting_text.format(current=0, total=1))
        self.vbox_main.button_remove.set_sensitive(False)
        self.on_button_run_clicked(self.vbox_main.button_run)

    def on_button_run_clicked(self, widget):
        # Use translatable running text
        is_removal = bool(self.script_queue and self.script_queue[0].get("cleanup_path"))
        running_text = self.translations.get(
            "term_view_running", "Running {current}/{total}"
        )
        if is_removal:
            running_text = self.translations.get(
                "term_view_removing", "Removing {current}/{total}"
            )
        self.vbox_main.progress_bar.set_text(
            running_text.format(current=self.scripts_executed, total=self.total_scripts)
        )
        running_label = self.translations.get("term_view_running_label", " Running ")
        if is_removal:
            running_label = self.translations.get(
                "term_view_removing_label", " Removing "
            )
        self.vbox_main.button_run.set_label(running_label)
        self.terminal.set_can_focus(True)
        
        # Make bug report button available once run is started (for error reporting during execution)
        auto_reports_enabled = getattr(self.parent, 'auto_error_reports_enabled', False)
        if not auto_reports_enabled and not self.current_script_has_registry_entry:
            self.vbox_main.button_copy.set_no_show_all(False)
            self.vbox_main.button_copy.show()
            self.current_script_has_registry_entry = True  # Mark as available for this session
        
        self._run_next_script()

    def _save_to_registry(self, script_name, transmap_path):
        """Save script execution record to registry."""
        try:
            import datetime
            registry_dir = os.path.expanduser("~/.cache/linuxtoys")
            registry_file = os.path.join(registry_dir, "registry")
            
            # Create directory if it doesn't exist
            os.makedirs(registry_dir, exist_ok=True)
            
            # Read transmap contents
            transmap_contents = ""
            if os.path.exists(transmap_path):
                try:
                    with open(transmap_path, "r") as f:
                        transmap_contents = f.read().strip()
                except (IOError, OSError):
                    pass
            
            # Format entry with timestamp
            timestamp = datetime.datetime.now().isoformat()
            entry = f"[{timestamp}] Script: {script_name}\n"
            if transmap_contents:
                entry += f"Changes:\n"
                for line in transmap_contents.split("\n"):
                    if line.strip():
                        entry += f"  - {line}\n"
            else:
                entry += "Changes: (none)\n"
            entry += "---\n\n"
            
            # Append to registry file
            with open(registry_file, "a") as f:
                f.write(entry)
        except Exception:
            pass  # Silently ignore registry errors

    def _try_auto_revert(self, transmap_path):
        """
        Attempt to build an auto-revert script from transmap operations.
        
        Returns a script_info-like dict if revertible operations exist, None otherwise.
        """
        if not os.path.exists(transmap_path):
            return None
        
        # Get the current script info to pass to the auto-revert builder
        current_script = None
        if hasattr(self, "_current_script_name"):
            current_script = {
                "name": self._current_script_name,
                "icon": "application-x-executable",
                "repo": "",
            }
        
        if not current_script:
            return None
        
        try:
            auto_revert_entry = build_auto_revert_script_entry(
                current_script, transmap_path, self.translations
            )
            return auto_revert_entry
        except Exception:
            return None

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

    def _auto_submit_bug_report_on_error(self):
        """Automatically submit a bug report when a script exits with an error code."""
        # Check if auto error reports are enabled
        auto_reports_enabled = getattr(self.parent, 'auto_error_reports_enabled', False)
        if not auto_reports_enabled:
            return
        
        try:
            # Get terminal logs
            logs = self._get_terminal_text()
            
            # Gather system information
            context_parts = []
            
            # Add script execution info
            if self.script_queue or self.scripts_executed > 0:
                context_parts.append(f"Scripts executed: {self.scripts_executed}/{self.total_scripts}")
            
            # Add system info (OS, GPU)
            system_context = antenna.get_system_context()
            if system_context:
                context_parts.append(system_context)
            
            # Add script execution history
            history_context = antenna.get_history_context()
            if history_context:
                context_parts.append(history_context)
            
            context = " | ".join(context_parts)
            
            # Submit the issue using antenna (silently, without showing confirmation dialog)
            title = self.translations.get(
                "bug_report_title", "Bug Report from LinuxToys"
            )
            result = antenna.submit_issue(title=title, logs=logs, context=context)
            
            # Optionally show result, but don't block the user
            if result:
                # Silent submission - just log it
                pass
        except (ConnectionError, Timeout):
            # Network errors - silently skip, user can report manually
            pass
        except Exception:
            # Any other errors - silently skip
            pass

    def on_child_exit(self, term, status):
        if getattr(self, "_cleanup_script_path", None):
            try:
                if os.path.exists(self._cleanup_script_path):
                    os.remove(self._cleanup_script_path)
            except Exception:
                pass
            self._cleanup_script_path = None

        if self._self_update:
            DialogRestart(parent=self.get_toplevel()).show()

        # Save to registry and wipe transmap file if script executed successfully
        if os.WIFEXITED(status):
            exit_code = os.WEXITSTATUS(status)
            if exit_code == 0:
                transmap_path = "/tmp/linuxtoys/transmap"
                # Get current script name for registry
                script_name = getattr(self, "_current_script_name", "unknown")
                # Save to registry before wiping
                self._save_to_registry(script_name, transmap_path)
                try:
                    if os.path.exists(transmap_path):
                        os.remove(transmap_path)
                except (IOError, OSError):
                    pass  # Silently ignore if transmap cannot be removed

        # Check for error exit codes and handle auto-reversion or bug report
        if self._is_error_exit_code(status) and not self._current_action_is_removal:
            # Only auto-handle for regular scripts, not removal operations
            transmap_path = "/tmp/linuxtoys/transmap"
            auto_reports_enabled = getattr(self.parent, 'auto_error_reports_enabled', False)
            
            # Submit bug report first if enabled (before auto-revert consumes transmap)
            if auto_reports_enabled:
                self._auto_submit_bug_report_on_error()
            
            # Try to auto-revert if there are operations in the transmap
            auto_revert_entry = self._try_auto_revert(transmap_path)
            
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
                self.on_button_run_clicked(self.vbox_main.button_run)
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
            self.vbox_main.button_run.connect("clicked", self.on_done_clicked)
            self.parent._script_running = False
            self.vbox_main.button_run.set_sensitive(True)
            self.terminal.set_can_focus(True)
            self.vbox_main.button_run.grab_focus()
            return

        self.parent._script_running = True
        current_script = self.script_queue.pop(0)
        self.vbox_main._update_header_labels(current_script)

        # Add script to execution history
        script_name = current_script.get("name", "unknown")
        self._current_script_name = script_name  # Store for registry
        antenna.add_script_to_history(script_name)
        
        # Clear transmap file for new script execution
        try:
            transmap_path = "/tmp/linuxtoys/transmap"
            with open(transmap_path, "w") as f:
                pass  # Truncate/clear the file
        except (IOError, OSError):
            pass  # Silently ignore if transmap cannot be cleared

        script_path = current_script.get("path", "true")
        if current_script.get("reboot") == "yes":
            self.parent.reboot_required = True

        self._self_update = current_script.get("self_update", False)
        self._cleanup_script_path = current_script.get("cleanup_path")
        self._current_action_is_removal = bool(self._cleanup_script_path)

        child_env = os.environ.copy()
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

        self.vbox_main.button_run.set_sensitive(False)
        self.vbox_main.button_remove.set_sensitive(False)

    def _get_last_registry_execution(self) -> str:
        """Get the last execution data from registry for the current script.
        
        Returns formatted text of the last execution, or empty string if not found.
        """
        if not hasattr(self, "_current_script_name") or not self._current_script_name:
            return ""
        
        try:
            registry_data = parse_registry_file()
            if self._current_script_name not in registry_data:
                return ""
            
            executions = registry_data[self._current_script_name]
            if not executions:
                return ""
            
            # Get the last execution
            timestamp, operations = executions[-1]
            
            # Format the registry data nicely
            lines = [f"Last execution of '{self._current_script_name}':\n"]
            if timestamp:
                lines.append(f"Timestamp: {timestamp}\n")
            
            if operations:
                lines.append("\nOperations performed:")
                for op in operations:
                    lines.append(f"  • {op}")
            else:
                lines.append("\nOperations: (none)")
            
            return "\n".join(lines)
        except Exception:
            return ""

    def _get_terminal_text(self) -> str:
        """Extract all text from the terminal by copying to clipboard and reading back."""
        try:
            # Select all terminal content
            if hasattr(self.terminal, "select_all"):
                self.terminal.select_all()
            
            # Copy to clipboard
            if hasattr(self.terminal, "copy_clipboard_format"):
                self.terminal.copy_clipboard_format(Vte.Format.TEXT)
            else:
                self.terminal.copy_clipboard()
            
            # Read from clipboard
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            text = clipboard.wait_for_text()
            
            # Unselect
            if hasattr(self.terminal, "unselect_all"):
                self.terminal.unselect_all()
            
            return text if isinstance(text, str) else ""
        except Exception:
            # If clipboard extraction fails, fall back to antenna logs
            try:
                logs = antenna.log_capture.get_logs()
                return logs if isinstance(logs, str) else ""
            except Exception:
                return ""

    def _show_bug_report_confirmation_dialog(self):
        """Show confirmation dialog before sending bug report."""
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=self.translations.get(
                "bug_report_confirm_title", "Send Bug Report?"
            ),
        )
        dialog.format_secondary_text(
            self.translations.get(
                "bug_report_confirm_message",
                "Your terminal output will be sent to the remote server to help us fix issues. Do you want to continue?",
            )
        )
        dialog.add_button(
            self.translations.get("cancel_btn_label", "Cancel"), Gtk.ResponseType.CANCEL
        )
        dialog.add_button(
            self.translations.get("send_btn_label", "Send"), Gtk.ResponseType.YES
        )
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def _show_bug_report_result_dialog(self, success: bool, issue_data: dict = None):
        """Show result dialog after bug report submission."""
        if success and issue_data:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=self.translations.get(
                    "bug_report_success_title", "Bug Report Submitted"
                ),
            )
            issue_url = issue_data.get("issue_url", "")
            issue_number = issue_data.get("issue_number", "")
            dialog.format_secondary_text(
                self.translations.get(
                    "bug_report_success_message",
                    "Thank you! Your bug report has been submitted.\n"
                    "Issue #{issue_number}: {issue_url}",
                ).format(issue_number=issue_number, issue_url=issue_url)
            )
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=self.translations.get(
                    "bug_report_failed_title", "Bug Report Failed"
                ),
            )
            dialog.format_secondary_text(
                self.translations.get(
                    "bug_report_failed_message",
                    "Could not submit the bug report. Please try again later.",
                )
            )
        dialog.run()
        dialog.destroy()

    def _show_bug_report_network_error_dialog(self, title: str, message: str):
        """Show network-specific error dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def _copy_terminal_text(self, copy_all=False):
        """Copy terminal text to clipboard."""
        if copy_all and hasattr(self.terminal, "select_all"):
            self.terminal.select_all()

        if hasattr(self.terminal, "copy_clipboard_format"):
            self.terminal.copy_clipboard_format(Vte.Format.TEXT)
        else:
            self.terminal.copy_clipboard()

        if copy_all and hasattr(self.terminal, "unselect_all"):
            self.terminal.unselect_all()

    def on_copy_clicked(self, button):
        """Handle bug report button click."""
        if not self._show_bug_report_confirmation_dialog():
            return
        
        try:
            # Get terminal logs
            logs = self._get_terminal_text()
            
            # If terminal logs are empty, try to get registry data for this script
            if not logs or logs.strip() == "":
                registry_logs = self._get_last_registry_execution()
                if registry_logs:
                    logs = f"[Using registry data from last execution]\n{registry_logs}"
            
            # Gather system information
            context_parts = []
            
            # Add script execution info
            if self.script_queue or self.scripts_executed > 0:
                context_parts.append(f"Scripts executed: {self.scripts_executed}/{self.total_scripts}")
            
            # Add system info (OS, GPU)
            system_context = antenna.get_system_context()
            if system_context:
                context_parts.append(system_context)
            
            # Add script execution history
            history_context = antenna.get_history_context()
            if history_context:
                context_parts.append(history_context)
            
            context = " | ".join(context_parts)
            
            # Submit the issue using antenna
            title = self.translations.get(
                "bug_report_title", "Bug Report from LinuxToys"
            )
            result = antenna.submit_issue(title=title, logs=logs, context=context)
            
            # Show result dialog
            self._show_bug_report_result_dialog(result is not None, result or {})
        except ConnectionError:
            self._show_bug_report_network_error_dialog(
                self.translations.get(
                    "bug_report_no_connection",
                    "No Internet Connection",
                ),
                self.translations.get(
                    "bug_report_no_connection_message",
                    "Unable to send bug report: No internet connection detected. Please check your network and try again.",
                )
            )
        except Timeout:
            self._show_bug_report_network_error_dialog(
                self.translations.get(
                    "bug_report_timeout",
                    "Connection Timeout",
                ),
                self.translations.get(
                    "bug_report_timeout_message",
                    "Unable to send bug report: Server connection timed out. Please try again later.",
                )
            )
        except Exception as e:
            if "500" in str(e) or "502" in str(e) or "503" in str(e):
                self._show_bug_report_network_error_dialog(
                    self.translations.get(
                        "bug_report_server_error",
                        "Server Error",
                    ),
                    self.translations.get(
                        "bug_report_server_error_message",
                        "Unable to send bug report: The server encountered an error. Please try again later.",
                    )
                )
            else:
                print(f"Error submitting bug report: {e}", file=sys.stderr)
                self._show_bug_report_result_dialog(False)

    def _on_terminal_key_press(self, widget, event):
        state = event.state
        ctrl_shift = (state & Gdk.ModifierType.CONTROL_MASK) and (
            state & Gdk.ModifierType.SHIFT_MASK
        )
        if ctrl_shift and event.keyval == Gdk.KEY_C:
            has_selection = (
                self.terminal.get_has_selection()
                if hasattr(self.terminal, "get_has_selection")
                else False
            )
            self._copy_terminal_text(copy_all=not has_selection)
            return True
        return False

    def _on_key_press(self, widget, event):
        """Handle key press events - specifically Escape to go back."""
        if event.keyval == Gdk.KEY_Escape:
            # Check if a script is currently running
            if self.parent._script_running:
                # Show the warning dialog before cancelling
                if self.parent._show_cancel_script_warning_dialog():
                    # User confirmed to cancel
                    self.on_done_clicked(None)
                # Otherwise, continue running (user chose not to cancel)
                return True
            else:
                # No script running, just go back
                self.on_done_clicked(None)
                return True

        return False

    def on_done_clicked(self, button):
        self.parent.set_focus(None)

        # Check for reboot requirements after checklist completion
        reboot_helper.check_reboot_requirement_after_checklist(
            self.parent, self.translations, self.parent._close_application
        )

        self.parent.on_back_button_clicked(None)
