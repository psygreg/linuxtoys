"""U1 imports/caches/reporting/CLI with fake HTTP, GI, native and execution APIs.

Only these fixtures' in-memory HTTP stub can receive a report payload. Every
socket and external process attempt fails the test. No real report is submitted.
"""
from __future__ import annotations

import ast
from contextlib import ExitStack
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "p3/app"
PACKAGE = "_u1_fixture_app"


def module(name, **values):
    result = ModuleType(name)
    result.__dict__.update(values)
    return result


class OfflineFixtures(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.temp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.stack.enter_context(patch("socket.socket", side_effect=AssertionError("network forbidden")))
        self.stack.enter_context(patch("subprocess.Popen", side_effect=AssertionError("process forbidden")))
        self.stack.enter_context(patch.dict("os.environ", {"HOME": self.temp}))
        package = module(PACKAGE, __path__=[str(APP)])
        self.modules = {PACKAGE: package}
        self.stack.enter_context(patch.dict(sys.modules, self.modules))
        self.stack.enter_context(patch("sys.stdout", new_callable=io.StringIO))
        self.stack.enter_context(patch("sys.stderr", new_callable=io.StringIO))

    def stub(self, relative, **values):
        name = PACKAGE + "." + relative
        result = module(name, **values)
        sys.modules[name] = result
        return result

    def load(self, relative):
        name = PACKAGE + "." + relative
        spec = importlib.util.spec_from_file_location(name, APP / (relative.replace(".", "/") + ".py"))
        result = importlib.util.module_from_spec(spec)
        sys.modules[name] = result
        spec.loader.exec_module(result)
        return result


class CacheWriterTests(OfflineFixtures):
    def setUp(self):
        super().setUp()
        self.stub("_catalog_rs")
        self.cache = self.load("homebrew_catalog")
        self.cache.CACHE_DIR = Path(self.temp) / "cache"
        self.cache.FORMULA_PATH = self.cache.CACHE_DIR / "formula.json"
        self.cache.CACHE_DIR.mkdir()
        self.stack.enter_context(patch.object(self.cache, "enabled", return_value=True))
        self.stack.enter_context(patch.object(self.cache, "cached_path", side_effect=lambda: self.cache.FORMULA_PATH if self.cache.FORMULA_PATH.exists() else None))
        self.stack.enter_context(patch.object(self.cache, "needs_refresh", return_value=True))
        self.http = self.stack.enter_context(patch.object(self.cache, "urlopen"))
        self.sync = self.stack.enter_context(patch(PACKAGE + ".atomic_io.os.fsync"))

    def response(self, data):
        self.http.return_value.__enter__.return_value.read.return_value = data

    def test_formula_keeps_raw_bytes_private_mode_and_fsync(self):
        data = b'[ {"name": "caf\\u00e9"} ]\n'
        self.response(data)
        self.assertEqual(self.cache.load_or_refresh(force=True), self.cache.FORMULA_PATH)
        self.assertEqual(self.cache.FORMULA_PATH.read_bytes(), data)
        self.assertEqual(self.cache.FORMULA_PATH.stat().st_mode & 0o777, 0o600)
        self.sync.assert_called_once()

    def test_formula_failures_keep_previous_data_and_fallback(self):
        for failure in ("replace", "fsync", "invalid", "http"):
            with self.subTest(failure=failure), ExitStack() as stack:
                path = self.cache.FORMULA_PATH
                path.write_bytes(b"old")
                self.response(b'[{"name":"new"}]')
                self.http.side_effect = None
                if failure == "invalid":
                    self.response(b"not json")
                elif failure == "http":
                    self.http.side_effect = OSError("offline")
                else:
                    stack.enter_context(patch(PACKAGE + ".atomic_io.os." + failure, side_effect=OSError("failed")))
                self.assertEqual(self.cache.load_or_refresh(force=True), path)
                self.assertEqual(path.read_bytes(), b"old")
                self.assertEqual(list(self.cache.CACHE_DIR.iterdir()), [path])

    def test_disabled_source_never_fetches_or_writes(self):
        with patch.object(self.cache, "enabled", return_value=False):
            self.assertIsNone(self.cache.load_or_refresh(force=True))
            self.cache.refresh_popularity(force=True)
        self.http.assert_not_called()
        self.sync.assert_not_called()
        self.assertEqual(list(self.cache.CACHE_DIR.iterdir()), [])


class ReportingTests(OfflineFixtures):
    def setUp(self):
        super().setUp()
        class HTTPError(Exception):
            def __init__(self, response=None):
                self.response = response
        self.HTTPError = HTTPError
        exceptions = module("requests.exceptions", HTTPError=HTTPError, ConnectionError=type("ConnectionError", (Exception,), {}), Timeout=type("Timeout", (Exception,), {}))
        self.http = module("requests", exceptions=exceptions, post=Mock(side_effect=AssertionError("unmocked HTTP")), get=Mock(side_effect=AssertionError("unmocked HTTP")))
        self.stack.enter_context(patch.dict(sys.modules, {"requests": self.http, "requests.exceptions": exceptions}))
        self.stub("antenna", __path__=[str(APP / "antenna")])
        self.stub("updater", __path__=[str(APP / "updater")])
        self.version = self.stub("updater.update_helper", get_current_version=Mock(return_value="fixture"), is_current_version=Mock(return_value=(True, "fixture")))
        self.stub("lang_utils", _=lambda value: value)
        gtk = SimpleNamespace(ResponseType=SimpleNamespace(YES=1, CANCEL=0, OK=2), MessageType=SimpleNamespace(INFO=1, WARNING=2, ERROR=3, QUESTION=4))
        self.stub("gtk_common", Gtk=gtk, Gdk=SimpleNamespace(), Vte=SimpleNamespace(Format=SimpleNamespace(TEXT="text")))
        self.dialog = Mock()
        self.stub("gtk_dialogs", run_message_dialog=self.dialog)
        self.registry = Mock(return_value="")
        self.stub("term_registry", ExecutionRegistry=SimpleNamespace(_get_last_registry_execution=self.registry))
        self.background = Mock(return_value="background logs")
        self.stub("appstream_logs", appstream_log_context=self.background)
        self.antenna = self.load("antenna.antenna")
        sys.modules[PACKAGE + ".antenna"].antenna = self.antenna
        self.reporting = self.load("term_reporting")
        for name, result in (("_initialize_antenna", None), ("_get_token", "fake-token"), ("_get_transmap_content", ""), ("_get_last_registry_entries", ""), ("_get_repo_owner_mention", "")):
            self.stack.enter_context(patch.object(self.antenna, name, return_value=result))
        self.antenna.log_capture = SimpleNamespace(get_logs=Mock(return_value=""))
        self.response = SimpleNamespace(status_code=200, raise_for_status=Mock(), json=Mock(return_value={"issue_number": 1, "issue_url": "fixture://issue"}))
        self.http.post.side_effect = None
        self.http.post.return_value = self.response
        self.subject = self.reporting.BugReporting()
        self.subject.translations = {}
        self.subject.script_queue = []
        self.subject.scripts_executed = self.subject.total_scripts = 0
        self.subject.parent = SimpleNamespace(auto_error_reports_enabled=False)
        for name in ("confirmation", "result", "empty", "cancelled", "rejected", "network_error"):
            setattr(self.subject, "_show_bug_report_" + name + "_dialog", Mock(return_value=True))

    def test_history_cache_keeps_json_modes_and_silent_failure(self):
        self.antenna._CACHE_DIR = Path(self.temp) / "antenna"
        self.antenna._HISTORY_FILE = self.antenna._CACHE_DIR / "history.json"
        history = [{"name": "café", "timestamp": 42}]
        self.antenna._save_history(history)
        path = self.antenna._HISTORY_FILE
        self.assertEqual(path.read_bytes(), json.dumps({"history": history}).encode())
        self.assertEqual(self.antenna._load_history(), history)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        with patch(PACKAGE + ".atomic_io.os.replace", side_effect=OSError("failed")):
            self.assertIsNone(self.antenna._save_history([]))
        self.assertEqual(self.antenna._load_history(), history)
        self.assertEqual(list(path.parent.iterdir()), [path])
        self.http.post.assert_not_called()
        self.antenna._get_token.assert_not_called()

    def test_background_import_is_parent_package_and_terminal_ends_payload(self):
        self.antenna.submit_issue("fixture", logs="terminal failure")
        self.background.assert_called_once()
        self.assertEqual(self.http.post.call_args.kwargs["json"]["logs"], "background logs\n\nterminal failure")

    def test_empty_and_control_only_logs_do_not_request_token_or_post(self):
        self.background.return_value = ""
        for logs in ("", " \n\t", "\x00\x07"):
            with self.subTest(logs=logs):
                self.assertIsNone(self.antenna.submit_issue("fixture", logs=logs))
        self.http.post.assert_not_called()
        self.antenna._get_token.assert_not_called()

    def test_422_logs_becomes_empty_report_but_other_http_errors_survive(self):
        for status, detail, expected in (
            (422, [{"loc": ["body", "logs"]}], self.antenna.EmptyReportError),
            (422, [{"loc": ["body", "title"]}], self.HTTPError),
            (500, [{"loc": ["body", "logs"]}], self.HTTPError),
        ):
            with self.subTest(status=status, detail=detail):
                self.response.status_code = status
                self.response.json.return_value = {"detail": detail}
                error = self.HTTPError(self.response)
                self.response.raise_for_status.side_effect = error
                with self.assertRaises(expected):
                    self.antenna.submit_issue("fixture", logs="failure")
        for payload in (None, [], {"detail": None}, {"detail": "logs"}, {"detail": [{"loc": None}]}, {"detail": [{"loc": "logs"}]}):
            self.response.json.return_value = payload
            self.assertFalse(self.antenna._rejected_for_logs(self.response))
        self.response.json.side_effect = ValueError("invalid json")
        self.assertFalse(self.antenna._rejected_for_logs(self.response))

    def test_outdated_version_cancels_before_report_initialization_or_http(self):
        self.version.is_current_version.return_value = (False, "newer")
        self.assertIsNone(self.antenna.submit_issue("fixture", logs="failure"))
        self.dialog.assert_called_once()
        self.antenna._initialize_antenna.assert_not_called()
        self.http.post.assert_not_called()
        self.antenna._get_token.assert_not_called()

    def test_vte_range_precedes_viewport_includes_scrollback_and_accepts_tuples(self):
        for result in ("old scrollback\nlast failure", ("old scrollback\nlast failure", [])):
            terminal = SimpleNamespace(get_cursor_position=Mock(return_value=(4, 500)), get_row_count=Mock(return_value=2), get_text_range_format=Mock(return_value=result), get_text_format=Mock(return_value="viewport"))
            self.subject.terminal = terminal
            self.assertEqual(self.subject._get_vte_buffer_text(), "old scrollback\nlast failure")
            terminal.get_text_range_format.assert_called_once_with("text", 0, 0, 502, 0)
            terminal.get_text_format.assert_not_called()
        terminal.get_row_count.return_value = 0
        self.subject._get_vte_buffer_text()
        self.assertEqual(terminal.get_text_range_format.call_args.args, ("text", 0, 0, 500, 0))

    def test_vte_viewport_fallback_string_tuple_missing_empty_and_failure(self):
        for value in ("viewport", ("viewport", []), (), (None, []), None, 123):
            self.subject.terminal = SimpleNamespace(get_text_format=Mock(return_value=value))
            self.assertEqual(self.subject._get_vte_buffer_text(), "viewport" if value in ("viewport", ("viewport", [])) else "")
        for terminal in (None, SimpleNamespace(), SimpleNamespace(get_text_range_format=Mock(side_effect=RuntimeError("VTE")), get_cursor_position=Mock(return_value=(0, 1)), get_row_count=Mock(return_value=1))):
            self.subject.terminal = terminal
            self.assertEqual(self.subject._get_vte_buffer_text(), "")
        self.antenna.log_capture.get_logs.return_value = "captured"
        self.assertEqual(self.subject._get_terminal_text(), "captured")

    def test_vte_missing_range_method_uses_valid_fallback(self):
        for result in ("viewport\n", ("viewport\n", []), ("viewport\n",)):
            for attributes in ({}, {"get_text_range_format": None}, {"get_text_range_format": 42}):
                with self.subTest(result=result, attributes=attributes):
                    fallback = Mock(return_value=result)
                    self.subject.terminal = SimpleNamespace(get_text_format=fallback, **attributes)
                    self.assertEqual(self.subject._get_vte_buffer_text(), "viewport\n")
                    fallback.assert_called_once_with("text")

    def test_vte_raised_range_exception_uses_valid_fallback(self):
        terminal = SimpleNamespace(
            get_cursor_position=Mock(return_value=(0, 20)),
            get_row_count=Mock(return_value=2),
            get_text_range_format=Mock(side_effect=RuntimeError("binding failed")),
            get_text_format=Mock(return_value=("fallback failure details", [])),
        )
        self.subject.terminal = terminal
        self.assertEqual(self.subject._get_vte_buffer_text(), "fallback failure details")
        terminal.get_text_format.assert_called_once_with("text")

    def test_vte_malformed_or_empty_range_uses_fallback_without_partial_text(self):
        for result in (None, (), (None, "partial"), 42, [], {"text": "partial"},
                       b"partial", (b"partial", []), "", " \n", ("\t", [])):
            with self.subTest(result=result):
                terminal = SimpleNamespace(
                    get_cursor_position=Mock(return_value=(0, 20)),
                    get_row_count=Mock(return_value=2),
                    get_text_range_format=Mock(return_value=result),
                    get_text_format=Mock(return_value="complete fallback"),
                )
                self.subject.terminal = terminal
                self.assertEqual(self.subject._get_vte_buffer_text(), "complete fallback")
                terminal.get_text_format.assert_called_once_with("text")

    def test_vte_valid_single_item_range_tuple_keeps_range_and_skips_fallback(self):
        terminal = SimpleNamespace(
            get_cursor_position=Mock(return_value=(0, 20)),
            get_row_count=Mock(return_value=2),
            get_text_range_format=Mock(return_value=("full scrollback\n",)),
            get_text_format=Mock(side_effect=AssertionError("fallback must not run")),
        )
        self.subject.terminal = terminal
        self.assertEqual(self.subject._get_vte_buffer_text(), "full scrollback\n")
        terminal.get_text_format.assert_not_called()

    def test_vte_fallback_failure_or_unusable_result_returns_empty(self):
        for result in (None, (), (None, []), "", " \n", 42, b"partial"):
            with self.subTest(result=result):
                self.subject.terminal = SimpleNamespace(get_text_format=Mock(return_value=result))
                self.assertEqual(self.subject._get_vte_buffer_text(), "")
        terminal = SimpleNamespace(
            get_cursor_position=Mock(return_value=(0, 20)),
            get_row_count=Mock(return_value=2),
            get_text_range_format=Mock(side_effect=RuntimeError("range failed")),
            get_text_format=Mock(side_effect=RuntimeError("fallback failed")),
        )
        self.subject.terminal = terminal
        self.assertEqual(self.subject._get_vte_buffer_text(), "")
        terminal.get_text_format.assert_called_once_with("text")

    def test_vte_binding_fallback_does_not_swallow_interrupts(self):
        for error in (KeyboardInterrupt, SystemExit):
            for use_range in (True, False):
                with self.subTest(error=error, use_range=use_range):
                    terminal = SimpleNamespace(get_text_format=Mock(side_effect=error))
                    if use_range:
                        terminal.get_cursor_position = Mock(return_value=(0, 20))
                        terminal.get_row_count = Mock(return_value=2)
                        terminal.get_text_range_format = Mock(side_effect=error)
                    self.subject.terminal = terminal
                    with self.assertRaises(error):
                        self.subject._get_vte_buffer_text()
                    if use_range:
                        terminal.get_text_format.assert_not_called()

    def test_vte_result_processing_errors_are_not_masked_as_binding_failures(self):
        class BrokenText(str):
            def strip(self):
                raise LookupError("unrelated result processing error")

        for range_result in (BrokenText("range"), None):
            with self.subTest(range_result=range_result):
                self.subject.terminal = SimpleNamespace(
                    get_cursor_position=Mock(return_value=(0, 20)),
                    get_row_count=Mock(return_value=2),
                    get_text_range_format=Mock(return_value=range_result),
                    get_text_format=Mock(return_value=BrokenText("viewport")),
                )
                with self.assertRaisesRegex(LookupError, "unrelated result processing"):
                    self.subject._get_vte_buffer_text()
                if range_result is not None:
                    self.subject.terminal.get_text_format.assert_not_called()

    def test_child_exit_records_cancellation_and_clears_it_for_later_runs(self):
        for name in ("dev_mode", "package_guard", "reboot_helper", "repo_parser"):
            self.stub(name)
        self.stub("library_loader", script_command=Mock(), script_environment=Mock())
        gtk = sys.modules[PACKAGE + ".gtk_common"]
        gtk.GLib = SimpleNamespace()
        gtk.resolve_symbolic_icon = Mock()
        runner = self.load("term_runner")
        self.subject._clear_runner_lock = Mock()
        self.subject._on_child_exit_body = Mock()
        for status, expected in ((100 << 8, 100), (1 << 8, 1), (0, 0), (9, None)):
            runner.TerminalRunner.on_child_exit(self.subject, None, status)
            self.assertEqual(self.subject._last_exit_code, expected)
            self.subject._on_child_exit_body.assert_called_with(None, status)
            if expected == 100:
                self.subject.on_copy_clicked(None)
                self.subject._show_bug_report_cancelled_dialog.assert_called_once()
        self.assertEqual(self.subject._clear_runner_lock.call_count, 4)
        self.http.post.assert_not_called()

    def test_manual_cancellation_denied_consent_empty_and_auto_disabled_never_submit(self):
        with patch.object(self.antenna, "submit_issue") as submit:
            self.subject._last_exit_code = 100
            self.subject.on_copy_clicked(None)
            self.subject._show_bug_report_cancelled_dialog.assert_called_once()
            self.subject._show_bug_report_confirmation_dialog.assert_not_called()
            self.subject.parent.auto_error_reports_enabled = True
            self.subject._auto_submit_bug_report_on_error()
            self.subject._last_exit_code = 1
            self.subject._show_bug_report_confirmation_dialog.return_value = False
            self.subject.on_copy_clicked(None)
            self.subject._show_bug_report_confirmation_dialog.return_value = True
            with patch.object(self.subject, "_get_terminal_text", return_value=""):
                self.subject.on_copy_clicked(None)
                self.subject._show_bug_report_empty_dialog.assert_called_once()
                self.subject._auto_submit_bug_report_on_error()
            self.subject.parent.auto_error_reports_enabled = False
            self.subject._auto_submit_bug_report_on_error()
            submit.assert_not_called()
        self.http.post.assert_not_called()

    def test_manual_empty_rejection_or_backend_cancellation_has_no_failure_dialog(self):
        self.subject._get_terminal_text = Mock(return_value="failure")
        with patch.object(self.antenna, "get_system_context", return_value=""), patch.object(self.antenna, "get_history_context", return_value=""), patch.object(self.antenna, "submit_issue", return_value=None) as submit:
            self.subject.on_copy_clicked(None)
            self.subject._show_bug_report_result_dialog.assert_not_called()
            submit.side_effect = self.antenna.EmptyReportError()
            self.subject.on_copy_clicked(None)
            self.subject._show_bug_report_rejected_dialog.assert_called_once()
            self.subject._show_bug_report_result_dialog.assert_not_called()
        self.http.post.assert_not_called()


class CliCancellationTests(OfflineFixtures):
    def setUp(self):
        super().setUp()
        # Import the entire CLI with its external application dependencies stubbed.
        source = ast.parse((APP / "easy_cli.py").read_text())
        for node in source.body:
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                if node.module:
                    self.stub(node.module, **{alias.name: Mock() for alias in node.names})
                else:
                    for alias in node.names:
                        self.stub(alias.name)
        self.cli = self.load("easy_cli")

    def test_confirm_eof_and_interrupt_cancel_yes_no_preserved(self):
        for failure in (EOFError, KeyboardInterrupt):
            with patch("builtins.input", side_effect=failure):
                self.assertFalse(self.cli.confirm_action("Continue?"))
        for answer, expected in (("y", True), (" YES ", True), ("", False), ("no", False)):
            with patch("builtins.input", return_value=answer):
                self.assertIs(self.cli.confirm_action("Continue?"), expected)

    def test_existing_batch_failure_decisions_and_eof_are_preserved(self):
        scripts = [{"name": name, "path": name + ".sh"} for name in ("first", "second")]
        for code, answer, expected_runs, expected_prompts in ((1, "n", 2, 0), (2, "n", 1, 1), (2, "y", 2, 1), (100, "n", 1, 1), (130, "y", 1, 0)):
            with self.subTest(code=code), patch.object(self.cli, "easy_cli_run_script", side_effect=[code, 0]) as run, patch("builtins.input", return_value=answer) as prompt:
                self.cli.execute_scripts_with_feedback(scripts)
                self.assertEqual(run.call_count, expected_runs)
                self.assertEqual(prompt.call_count, expected_prompts)
        with patch.object(self.cli, "easy_cli_run_script", return_value=2) as run, patch("builtins.input", side_effect=EOFError):
            self.cli.execute_scripts_with_feedback(scripts)
            run.assert_called_once_with(scripts[0])


if __name__ == "__main__":
    unittest.main()
