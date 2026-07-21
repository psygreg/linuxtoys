from . import reboot_helper
from .compat import should_enable_manual_revert, get_revert_capability
from .gtk_common import Gdk, GLib, Gtk, Vte
from .gtk_dialogs import run_message_dialog
from .term_header import InfosHead
from .term_reporting import BugReporting
from .term_runner import TerminalRunner
from .revert_helper import build_uninstall_script_entry, _load_last_execution
 
class TermRunScripts(Gtk.Box, TerminalRunner, BugReporting):
    def __init__(
        self, scripts_infos: list, parent, translations=None, removable_script_info=None, auto_run=False
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.parent = parent
        self.translations = translations or {}
        self.script_queue = scripts_infos.copy()
        self.removable_script_info = removable_script_info
        self.total_scripts = len(scripts_infos)
        self.scripts_executed = 0
        self.auto_run = auto_run
        self.executed_scripts = []  # Track scripts that actually ran for cache updates
        
        # Track revert capability of the removable script (if available)
        self.removable_script_revert_capability = None
        self.removable_script_manual_revert_enabled = False
        self.removable_script_has_registry_entry = False
        self.removable_script_revert_disabled = False
        self._flatpak_installed_detected = False  # Track if flatpak was installed during script execution
        self._self_update = False
        self._cleanup_script_path = None
        self._current_action_is_removal = False
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
        self._current_script_name = None  # Will be set when script runs, or from first script
        if scripts_infos:
            first_script = scripts_infos[0]
            first_script_name = first_script.get('name')
            if first_script_name:
                # Initialize with first script name for bug reporting (even before run)
                self._current_script_name = first_script_name
                operations = _load_last_execution(first_script_name)
                self.current_script_has_registry_entry = bool(operations)
 
        self.terminal = Vte.Terminal()
        self.terminal.connect("child-exited", self.on_child_exit)
        self.terminal.connect("key-press-event", self._on_terminal_key_press)
        self.terminal.set_vexpand(True)
        self.terminal.set_can_focus(True)
 
        self.vbox_main = InfosHead(translations)
 
        self._run_button_handler_id = self.vbox_main.button_run.connect(
            "clicked", self.on_button_run_clicked
        )
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
        
        # If auto_run is enabled, automatically start running the scripts
        if self.auto_run:
            GLib.idle_add(self.on_button_run_clicked, None)
 
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
        response = run_message_dialog(
            self,
            title=self.translations.get(
                "remove_confirm_title",
                "Remove Installed Components?",
            ),
            secondary_text=self.translations.get(
                "remove_confirm_message",
                "LinuxToys will attempt to remove all components installed by "
                "'{script_name}'. Do you want to continue?",
            ).format(script_name=script_name),
            message_type=Gtk.MessageType.WARNING,
            buttons=[
                (
                    self.translations.get("cancel_btn_label", "Cancel"),
                    Gtk.ResponseType.CANCEL,
                ),
                (
                    self.translations.get("yes", "Yes"),
                    Gtk.ResponseType.YES,
                ),
            ],
            default_response=Gtk.ResponseType.CANCEL,
        )
        return response == Gtk.ResponseType.YES
 
    def _show_remove_not_available_dialog(self):
        response = run_message_dialog(
            self,
            title=self.translations.get(
                "remove_not_available_title",
                "Removal Not Available",
            ),
            secondary_text=self.translations.get(
                "remove_not_available_message",
                "No removable components were detected for this script."
            ),
            message_type=Gtk.MessageType.INFO,
            buttons=[
                ("OK", Gtk.ResponseType.OK),
            ],
        )
        return response == Gtk.ResponseType.OK
 
    def _show_internal_revert_confirmation_dialog(self, script_name):
        response = run_message_dialog(
            self,
            title=self.translations.get(
                "internal_revert_confirm_title",
                "Re-run Script for Removal?",
            ),
            secondary_text=self.translations.get(
                "internal_revert_confirm_message",
                "This script has a custom removal method. Running it again will attempt to remove its components. Do you want to continue?"
            ),
            message_type=Gtk.MessageType.WARNING,
            buttons=[
                (
                    self.translations.get("cancel_btn_label", "Cancel"),
                    Gtk.ResponseType.CANCEL,
                ),
                (
                    self.translations.get("yes", "Yes"),
                    Gtk.ResponseType.YES,
                ),
            ],
            default_response=Gtk.ResponseType.CANCEL,
        )
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
        # Ignore repeated clicks or duplicate idle callbacks while a script is active.
        if self.parent._script_running:
            return False

        self.vbox_main.button_run.set_sensitive(False)

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
        return False
 
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
            # Keep all terminal-exit confirmation and cancellation handling in
            # NavCtl.on_back_button_clicked(), which is also used by the header button.
            self.on_done_clicked(None)
            return True
 
        return False
 
    def on_done_clicked(self, button):
        self.parent.set_focus(None)
 
        # Check for reboot requirements after checklist completion
        reboot_helper.check_reboot_requirement_after_checklist(
            self.parent, self.translations, self.parent._close_application
        )

        # Refresh cached removable state for any scripts that were just executed
        # so the remove buttons appear/disappear correctly when returning to the UI
        if hasattr(self.parent, 'script_cache') and self.parent.script_cache.is_populated:
            for script_info in getattr(self, 'executed_scripts', []):
                self.parent.script_cache.update_removable_for_script(script_info)
 
        self.parent.on_back_button_clicked(None)
