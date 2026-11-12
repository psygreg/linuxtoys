import sys
from requests.exceptions import ConnectionError, Timeout

from .gtk_common import Gdk, Gtk, Vte
from .gtk_dialogs import run_message_dialog
from .term_registry import ExecutionRegistry
from .antenna import antenna

class BugReporting:
    def _get_vte_buffer_text(self) -> str:
        """Read the terminal's scrollback buffer directly from VTE.

        The script output is rendered into the VTE widget through a PTY and never
        passes through the Python process's stdout/stderr, so antenna's log_capture
        buffer is empty for real script runs. Reading the widget's own text buffer
        is therefore the reliable source and needs no clipboard round-trip (which is
        prone to returning None/empty under Wayland, without a selection owner, or
        when wait_for_text() times out).
        """
        terminal = getattr(self, "terminal", None)
        if terminal is None:
            return ""

        def usable_text(result):
            # PyGObject versions return either text or (text, attributes). Never
            # stringify malformed output or salvage another tuple field.
            if isinstance(result, tuple):
                result = result[0] if result else None
            return result if isinstance(result, str) and result.strip() else ""

        # Prefer the absolute buffer range so scrollback is included. Confine
        # binding-error handling to each API attempt; normalize results outside
        # those handlers so unrelated processing errors are not swallowed.
        try:
            read_range = getattr(terminal, "get_text_range_format", None)
            if callable(read_range):
                _column, cursor_row = terminal.get_cursor_position()
                result = read_range(
                    Vte.Format.TEXT, 0, 0, cursor_row + terminal.get_row_count(), 0
                )
            else:
                result = None
        except Exception:
            result = None

        text = usable_text(result)
        if text:
            return text

        # Missing, failed, empty or malformed range exports can still have a
        # usable viewport. Avoid deprecated get_text() and its attributes issue.
        try:
            result = terminal.get_text_format(Vte.Format.TEXT)
        except Exception:
            return ""
        return usable_text(result)

    def _get_terminal_text(self) -> str:
        """Extract the terminal output for bug reporting.

        Order of preference:
        1. The VTE text buffer directly (reliable, no clipboard).
        2. A clipboard round-trip (legacy behaviour).
        3. antenna's in-memory log_capture buffer (only has Python-side output).
        """
        text = self._get_vte_buffer_text()
        if text.strip():
            return text

        # Legacy clipboard fallback.
        try:
            if hasattr(self.terminal, "select_all"):
                self.terminal.select_all()

            if hasattr(self.terminal, "copy_clipboard_format"):
                self.terminal.copy_clipboard_format(Vte.Format.TEXT)
            else:
                self.terminal.copy_clipboard()

            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clip_text = clipboard.wait_for_text()

            if hasattr(self.terminal, "unselect_all"):
                self.terminal.unselect_all()

            if isinstance(clip_text, str) and clip_text.strip():
                return clip_text
        except Exception:
            pass

        # Last resort: Python-side captured stdout/stderr.
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
 
    def _show_bug_report_empty_dialog(self):
        """Tell the user there is no terminal output to report, and do not submit."""
        return run_message_dialog(
            self,
            title=self.translations.get(
                "bug_report_empty_title",
                "Nothing to Report",
            ),
            secondary_text=self.translations.get(
                "bug_report_empty_logs",
                "There is no terminal output to send. Run a script first, then try again.",
            ),
            message_type=Gtk.MessageType.WARNING,
            buttons=[("OK", Gtk.ResponseType.OK)],
            default_response=Gtk.ResponseType.OK,
        )

    def _last_terminal_line(self) -> str:
        """The last non-blank line of the terminal output, which says why a run ended."""
        lines = [line.strip() for line in self._get_vte_buffer_text().split("\n")]
        return next((line for line in reversed(lines) if line), "")

    def _show_bug_report_cancelled_dialog(self):
        """Explain a cancelled or skipped run instead of filing a report for it."""
        return run_message_dialog(
            self,
            title=self.translations.get("bug_report_cancelled_title", "Nothing to Report"),
            secondary_text=self.translations.get(
                "bug_report_cancelled_message",
                "The last run was cancelled or skipped, so there is nothing to report.\n\nLast message: {reason}",
            ).format(reason=self._last_terminal_line() or "-"),
            message_type=Gtk.MessageType.INFO,
            buttons=[("OK", Gtk.ResponseType.OK)],
            default_response=Gtk.ResponseType.OK,
        )

    def _show_bug_report_rejected_dialog(self):
        """The server found no text it could file from the terminal output."""
        return run_message_dialog(
            self,
            title=self.translations.get("bug_report_rejected_title", "Nothing to Report"),
            secondary_text=self.translations.get(
                "bug_report_rejected_message",
                "The terminal output had no text that could be sent, so the report was not submitted.",
            ),
            message_type=Gtk.MessageType.WARNING,
            buttons=[("OK", Gtk.ResponseType.OK)],
            default_response=Gtk.ResponseType.OK,
        )

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
        if getattr(self, "_last_exit_code", None) == 100:
            self._show_bug_report_cancelled_dialog()
            return
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

            # Never send an empty report. If there is no real terminal output and no
            # registry fallback, stop here and tell the user, instead of letting the
            # downstream padding in antenna.submit_issue (transmap / registry footer)
            # fabricate a non-empty body from operations metadata.
            if not logs or logs.strip() == "":
                self._show_bug_report_empty_dialog()
                return

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

            # A None result means submission was intentionally blocked/cancelled
            # by Antenna (for example, because this LinuxToys version is outdated).
            # Antenna has already shown the appropriate explanation, so do not
            # follow it with the generic submission-failed dialog.
            if result is None:
                return

            # Show result dialog
            self._show_bug_report_result_dialog(True, result)
        except antenna.EmptyReportError:
            self._show_bug_report_rejected_dialog()
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
        if not auto_reports_enabled or getattr(self, "_last_exit_code", None) == 100:
            return
        
        try:
            # Get terminal logs
            logs = self._get_terminal_text()

            # Do not auto-file a report with no real output.
            if not logs or logs.strip() == "":
                return

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