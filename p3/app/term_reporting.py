import sys
from requests.exceptions import ConnectionError, Timeout

from .gtk_common import Gdk, Gtk, Vte
from .gtk_dialogs import run_message_dialog
from .term_registry import ExecutionRegistry
from .antenna import antenna

class BugReporting:
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
        response = run_message_dialog(
            self,
            title=self.translations.get(
                "bug_report_confirm_title",
                "Send Bug Report?",
            ),
            secondary_text=self.translations.get(
                "bug_report_confirm_message",
                "Your terminal output will be sent to the remote server to help us fix issues. Do you want to continue?"
            ),
            message_type=Gtk.MessageType.QUESTION,
            buttons=[
                (
                    self.translations.get("cancel_btn_label", "Cancel"),
                    Gtk.ResponseType.CANCEL,
                ),
                (
                    self.translations.get("send_btn_label", "Send"),
                    Gtk.ResponseType.YES,
                ),
            ],
            default_response=Gtk.ResponseType.CANCEL,
        )
        return response == Gtk.ResponseType.YES
 
    def _show_bug_report_result_dialog(self, success: bool, issue_data: dict = None):
        if success and issue_data:
            issue_url = issue_data.get("issue_url", "")
            issue_number = issue_data.get("issue_number", "")
            response = run_message_dialog(
                self,
                title=self.translations.get(
                    "bug_report_success_title",
                    "Bug Report Submitted",
                ),
                secondary_text=self.translations.get(
                    "bug_report_success_message",
                    "Thank you! Your bug report has been submitted.\n"
                    "Issue #{issue_number}: {issue_url}",
                ).format(issue_number=issue_number, issue_url=issue_url),
                message_type=Gtk.MessageType.INFO,
                buttons=[("OK", Gtk.ResponseType.OK)],
                default_response=Gtk.ResponseType.OK,
            )
            return response == Gtk.ResponseType.OK
        else:
            response = run_message_dialog(
                self,
                title=self.translations.get(
                    "bug_report_failed_title",
                    "Bug Report Failed",
                ),
                secondary_text=self.translations.get(
                    "bug_report_failed_message",
                    "Could not submit the bug report. Please try again later."
                ),
                message_type=Gtk.MessageType.ERROR,
                buttons=[("OK", Gtk.ResponseType.OK)],
                default_response=Gtk.ResponseType.OK,
            )
            return response == Gtk.ResponseType.OK
 
    def _show_bug_report_network_error_dialog(self, title: str, message: str):
        response = run_message_dialog(
            self,
            title=(title),
            secondary_text=(message),
            message_type=Gtk.MessageType.ERROR,
            buttons=[
                ("OK", Gtk.ResponseType.OK),
            ],
        )
        return response == Gtk.ResponseType.OK
 
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
                script_name = getattr(
                    self,
                    "_current_script_name",
                    None,
                )
                if not script_name and self.script_queue:
                    script_name = self.script_queue[0].get("name")

                registry_logs = ExecutionRegistry._get_last_registry_execution(script_name)
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