import asyncio
import os
import shlex
import shutil
import tempfile
import threading
from collections.abc import Mapping
from contextlib import ExitStack
from functools import partial
from typing import Any

from textual.css.query import NoMatches
from textual.widgets import Input

from app import aur_cache, homebrew_catalog, installed_packages
from app.compat import get_revert_capability, get_system_compat_keys
from app.easy_cli import (
    _cleanup_tmp_noram_dirs,
    _save_script_to_registry,
    _try_execute_auto_revert,
    create_temp_file,
    is_dev_mode_enabled,
    resolve_script_dir,
)
from app.library_loader import script_command, script_environment
from app.manifest_helper import find_script_by_name_async
from app.parser import get_breadcrumb_path, script_requires_reboot
from app.registry_utils import parse_registry_file
from app.repo_parser import materialize_repo_script
from app.revert_helper import build_uninstall_script_entry
from app.updater.update_helper import UpdateHelper

from .appstream_executor import (
    AUR_SECURITY_BLOCKED,
    AUR_SECURITY_OK,
    build_aur_install_script,
    build_flatpak_extension_command,
    build_install_script,
    build_snap_revert_command,
    check_aur_package_security,
)
from .dialog_screen import (
    AurConsentDialog,
    AurHelperDialog,
    AurSecurityDialog,
    CancelledDialog,
    ConfirmScriptScreen,
    ErrorDialog,
    RebootDialog,
    RebootSystemDialog,
    RemoveScriptScreen,
    SuccessDialog,
    SudoPasswordScreen,
    UpdateAvailableDialog,
    UpdateCompleteDialog,
)
from .helper import (
    SPECIALS_ROOT,
    ScriptResult,
    _classify_exit_code,
    appimage_relative,
    get_appimage_items,
    get_homebrew_items,
    get_scripts_for_category_cached,
    get_specials_items,
    is_appimage_path,
    is_homebrew_catalog_valid,
    is_homebrew_path,
    is_registered_entry,
    is_removable,
    is_specials_path,
    refresh_homebrew_catalog,
    refresh_removable_state,
    search_appimage_items,
    search_homebrew_items,
    translations,
)
from .manifest_dialog import ManifestPlanDialog, ManifestReportDialog
from .my_widgets import (
    InfoButton,
    PasswordPromptDetected,
    ScriptFinished,
    Terminal,
)
from .tui_app_page import AppPageWidget, hide_app_page, show_app_page

TRANSMAP_PATH = "/tmp/linuxtoys/transmap"


class ScriptRunnerMixin:
    """Run LinuxToys scripts and own the state shared by every run.

    Mixin for the main app class. Besides installing and removing
    scripts, it holds the run state used by the other runner mixins, the
    terminal helpers and ``on_script_finished``, which handles the end of
    every run. It also browses the dynamic categories (Specials,
    Homebrew, AppImage and AUR) and keeps the breadcrumb.

    Install flow: ``handle_desc_button`` -> ``_handle_script_button`` ->
    confirmation dialog -> ``run_script`` -> ``_execute_script_info`` ->
    terminal -> ``on_script_finished`` -> result dialog ->
    ``_finish_script_run``. Removal goes through ``run_uninstall``."""

    _running_button: InfoButton | None = None
    _running_script_info: dict | None = None
    _running_temp_path: str | None = None
    _running_dev_mode: bool = False
    _running_is_uninstall: bool = False
    _running_appimage_stack: ExitStack | None = None
    _preparing_run: bool = False
    _aur_category_path: str | None = None
    _reboot_system: bool = False

    async def handle_desc_button(self, button: InfoButton) -> None:
        """Call a function based on is script or not."""
        if (
            button.is_repo_entry
            and button.has_app_page
            and button.is_appstream_entry
        ):
            pass
        elif button.is_script:
            if self._reboot_system:
                self.app.push_screen(RebootSystemDialog())
                return
            await self._handle_script_button(button)
        else:
            await self._navigate_to_category(button)

    @staticmethod
    def _read_removal_state(button: InfoButton) -> tuple[dict, bool]:
        """Read the registry and check if the script is removable."""
        registry_data = parse_registry_file()
        is_script = button.is_script
        removable = is_removable(
            str(button.label),
            button.path,
            button.is_repo_entry,
            button.is_appstream_entry,
            is_script=is_script,
            info=button.info,
        )
        return registry_data, removable

    async def _handle_script_button(self, button: InfoButton) -> None:
        """Ask for the right confirmation for a script.

        A script that was never run, or that cannot be removed, asks to
        run it (``ConfirmScriptScreen``). A registered, removable script
        asks to remove it: items that other software depends on are
        blocked with a notification, and a script with an internal
        removal (``_revert_capability``) asks to run it again, because
        the script removes itself. File reads run in threads.

        Args:
            button: Button of the script.
        """
        script_name = str(button.label)
        registry_data, removable = await asyncio.to_thread(
            self._read_removal_state, button
        )
        is_first_run = not is_registered_entry(
            button.info or {"name": script_name}, registry_data
        )

        if is_first_run or not removable:
            self.app.push_screen(
                ConfirmScriptScreen(script_name, button.description),
                callback=lambda confirmed: self._on_confirm_install(
                    button, confirmed
                ),
            )
            return
        script_info = button.info or await find_script_by_name_async(
            script_name, translations
        )
        if script_info is None:
            self.notify(
                f"✗ Script '{script_name}' not found.", severity="warning"
            )
            return

        blockers = await asyncio.to_thread(
            installed_packages.dependency_blockers, script_info
        )
        if blockers:
            self._notify_removal_blocked(script_name, blockers)
            return
        capability = await asyncio.to_thread(
            self._revert_capability, script_info
        )
        is_internal = capability == "internal"
        if is_internal:
            screen = RemoveScriptScreen(
                script_name,
                translations.get(
                    "internal_revert_confirm_message",
                    "This script has a custom removal method. Running it "
                    "again will attempt to remove its components. Do you "
                    "want to continue?",
                ),
                title=translations.get(
                    "internal_revert_confirm_title",
                    "Re-run Script for Removal?",
                ),
                confirm_label=translations.get("yes", "Yes"),
            )
        else:
            screen = RemoveScriptScreen(script_name, button.description)

        self.app.push_screen(
            screen,
            callback=lambda confirmed: self._on_confirm_uninstall(
                button, script_info, confirmed, is_internal
            ),
        )

    def _notify_removal_blocked(
        self, script_name: str, blockers: list[str]
    ) -> None:
        """Warn that installed software still depends on an item."""
        message = translations.get(
            "dependency_block_message",
            "Installed software still depends on '{name}'. "
            "Remove it first:\n\n{blockers}",
        ).format(
            name=script_name,
            blockers="\n".join(f"• {item}" for item in blockers),
        )
        self.notify(
            message,
            title=translations.get(
                "dependency_block_title", "Removal Blocked"
            ),
            severity="warning",
            timeout=10,
        )

    def _on_confirm_install(self, button: InfoButton, confirmed: bool) -> None:
        if confirmed:
            self.run_script(button)

    def _on_confirm_uninstall(
        self,
        button: InfoButton,
        script_info: dict,
        confirmed: bool,
        is_internal: bool = False,
    ) -> None:
        if not confirmed:
            return
        if is_internal:
            self.run_script(button)
            return
        self.run_uninstall(button, script_info)

    async def _navigate_to_category(self, button: InfoButton) -> None:
        """Open a category.

        The AUR category asks for consent first, and Homebrew and
        AppImage use their own loaders. Any other category is pushed on
        the navigation stack, rendered and shown in the breadcrumb.
        """
        if button.info.get("is_aur_category"):
            await self._activate_aur_category(button)
            return

        if is_homebrew_path(button.path):
            await self._open_homebrew_category(button)
            return

        if is_appimage_path(button.path):
            await self._open_appimage_category(button)
            return

        self._nav_stack.append((button.path, str(button.label)))
        await self._render_items(self._items_for_path(button.path))
        self._update_breadcrumb()

    def _items_for_path(self, path: str) -> list[dict]:
        """Return the items of a category path."""
        if is_specials_path(path):
            return get_specials_items(path)
        if is_homebrew_path(path):
            return get_homebrew_items()
        return get_scripts_for_category_cached(path)

    def _homebrew_view_active(self) -> bool:
        return bool(self._nav_stack) and is_homebrew_path(
            self._nav_stack[-1][0]
        )

    async def _open_homebrew_category(self, button: InfoButton) -> None:
        if not homebrew_catalog.enabled():
            self.notify(
                translations.get(
                    "homebrew_unavailable", "Homebrew is not available."
                ),
                severity="warning",
            )
            await self._sync_homebrew_availability()
            return

        self._nav_stack.append((button.path, str(button.label)))
        self._update_breadcrumb()
        await self._render_items([])
        if self._homebrew_view_active():
            self._set_items_loading(True)

        if is_homebrew_catalog_valid():
            self._homebrew_awaiting_refresh = False
            self._load_homebrew_items()
        else:
            self._homebrew_awaiting_refresh = True
            self._request_homebrew_refresh()

    def _load_homebrew_items(self) -> None:
        self.run_worker(
            self._load_homebrew_items_async(),
            exclusive=True,
            group="homebrew-items",
        )

    async def _load_homebrew_items_async(self) -> None:
        unavailable = translations.get(
            "homebrew_catalog_unavailable",
            "Homebrew metadata is unavailable. Try again later.",
        )
        try:
            items = await asyncio.to_thread(get_homebrew_items)
        except Exception:  # noqa: BLE001
            if self._homebrew_view_active():
                await self._show_items_message(unavailable)
            return
        if not self._homebrew_view_active():
            return
        if not items:
            await self._show_items_message(
                translations.get(
                    "homebrew_no_items", "No Homebrew packages found."
                )
            )
            return
        await self._render_items(items, lazy=True)

    def _request_homebrew_refresh(self) -> None:
        if self._homebrew_refresh_running or not homebrew_catalog.enabled():
            return
        self._homebrew_refresh_running = True
        started = homebrew_catalog.availability_fingerprint()
        app = self.app

        def worker() -> None:
            result = refresh_homebrew_catalog()
            try:
                app.call_from_thread(
                    self._finish_homebrew_refresh, result, started
                )
            except Exception:
                pass

        threading.Thread(
            target=worker, daemon=True, name="linuxtoys-homebrew-source"
        ).start()

    async def _finish_homebrew_refresh(self, result: dict, started) -> None:
        """Roda no event loop. Revalida o estado: ele pode ter mudado."""
        self._homebrew_refresh_running = False

        if not homebrew_catalog.enabled():
            await self._sync_homebrew_availability()
            return
        if homebrew_catalog.availability_fingerprint() != started:
            self._request_homebrew_refresh()
            return
        await self._resolve_homebrew_view(result)

    async def _resolve_homebrew_view(self, result: dict) -> None:
        awaiting = self._homebrew_awaiting_refresh
        self._homebrew_awaiting_refresh = False
        if not self._homebrew_view_active():
            return

        from app import appstream_cache

        source = (
            appstream_cache.get_state().get("sources", {}).get("homebrew", {})
        )
        ok = bool(result.get("success") and source.get("complete"))
        unavailable = translations.get(
            "homebrew_catalog_unavailable",
            "Homebrew metadata is unavailable. Try again later.",
        )

        if awaiting:
            if ok:
                self._load_homebrew_items()
            else:
                await self._show_items_message(unavailable)
                self.notify(
                    unavailable, title="Homebrew", severity="error", timeout=8
                )
        elif ok and result.get("changed"):
            self._load_homebrew_items()
            self.notify(
                "Homebrew catalog updated.", title="Homebrew", timeout=3
            )
        elif not ok:
            self.notify(
                unavailable, title="Homebrew", severity="warning", timeout=6
            )

    async def _check_homebrew_source(self) -> None:
        fingerprint = homebrew_catalog.availability_fingerprint()
        if fingerprint == self._homebrew_source_fingerprint:
            return
        self._homebrew_source_fingerprint = fingerprint
        await self._sync_homebrew_availability()
        self._request_homebrew_refresh()

    async def _sync_homebrew_availability(self) -> None:
        """Reconcile the UI with ``homebrew_catalog.enabled()``.

        If the Homebrew view is open and Homebrew is gone, warns and goes
        back to the home. On the home itself, redraws it so the Homebrew
        entry follows the availability.
        """
        if self._homebrew_view_active() and not homebrew_catalog.enabled():
            self._homebrew_awaiting_refresh = False
            self.notify(
                translations.get(
                    "homebrew_removed", "Homebrew is no longer available."
                ),
                severity="warning",
            )
            await self.action_reset_to_home()
        elif not self._nav_stack:
            await self.action_reset_to_home()

    def run_script(self, button: InfoButton) -> None:
        """Run the script of a button in the terminal.

        Does nothing if the terminal is busy. The button is kept in
        ``_running_button``.

        Args:
            button: Button whose ``info`` is run.
        """
        if not self._ensure_terminal_free():
            return

        self._running_button = button
        self._execute_script_info(button.info)

    def _execute_script_info(self, script_info: dict) -> None:
        """Run a script in the embedded terminal.

        Repository entries are materialized first. On failure an error
        is shown, the button is cleared and, during a manifest run, the
        failure is reported to ``_manifest_start_failed``. In dev mode
        the original script runs directly. Otherwise a copy made by
        ``create_temp_file`` runs, and the transmap file is emptied.

        Side effects: sets ``DISABLE_ZENITY=1`` in the process
        environment and shows the terminal. The environment has the
        common variables, the app identity variables and, in a manifest
        run, the manifest variables. It does not check whether the
        terminal accepted the command.

        Args:
            script_info: Script info dict.
        """
        if not self._ensure_terminal_free():
            return
        if script_info.get("is_repo_entry"):
            try:
                script_info = materialize_repo_script(script_info)
            except (ValueError, NotImplementedError, OSError) as exc:
                self.notify(
                    "✗ Could not prepare repository entry "
                    f"'{script_info.get('name', 'unknown')}': {exc}",
                    severity="error",
                )
                self._running_button = None
                if self._is_manifest_run:
                    self._manifest_start_failed(
                        script_info.get("name", "unknown"), 1
                    )
                return
        dev_mode = is_dev_mode_enabled()

        if dev_mode:
            temp_path = script_info["path"]
        else:
            resolve_script_dir()
            temp_path = create_temp_file(script_info["path"])
            try:
                with open(TRANSMAP_PATH, "w"):
                    pass
            except (IOError, OSError):
                pass

        self._running_script_info = script_info
        self._running_temp_path = temp_path
        self._running_dev_mode = dev_mode
        self._running_is_uninstall = False
        self._running_is_appstream = False
        # Disable zenity to avoid GUI prompts during EASY_CLI execution
        os.environ["DISABLE_ZENITY"] = "1"

        env = self._script_env(script_info.get("name", "unknown"))
        env.update(self._app_identity_env(script_info))
        if self._is_manifest_run and not script_info.get("is_batch"):
            env.update(self._manifest_script_env(script_info))

        self._show_terminal()
        terminal = self.query_one("#terminal", Terminal)
        terminal.run_script(
            temp_path,
            env=env,
        )

    @staticmethod
    def _app_identity_env(script_info: dict) -> dict[str, str]:
        """Return the app identity variables (``LINUXTOYS_APP_*``).

        Same as the GUI. ``script_environment`` returns a full
        environment, so it starts from a minimal base and drops
        ``SCRIPT_DIR``, because the script preamble already exports it.
        Only the variables it adds are injected into the terminal.

        Args:
            script_info: Script info dict.

        Returns:
            The extra variables.
        """
        base_env = {"SCRIPT_DIR": os.environ.get("SCRIPT_DIR", "")}
        env = script_environment(script_info, base_env=base_env)
        env.pop("SCRIPT_DIR", None)
        return env

    @staticmethod
    def _script_env(script_name: str, **extra: str) -> dict[str, str]:
        """Return the environment shared by every kind of run.

        Contains ``LINUXTOYS_SCRIPT_NAME``, ``DISABLE_ZENITY=1`` and,
        when ``SCRIPT_DIR`` is set, ``CACHE_DIR`` (``<SCRIPT_DIR>/scripts``).
        """
        env = {
            "LINUXTOYS_SCRIPT_NAME": script_name or "unknown",
            "DISABLE_ZENITY": "1",
        }
        script_dir = os.environ.get("SCRIPT_DIR")
        if script_dir:
            env["CACHE_DIR"] = os.path.join(script_dir, "scripts")
        env.update(extra)
        return env

    def _ensure_terminal_free(self) -> bool:
        """Return True if the terminal is free.

        If a run is in progress, it warns the user and returns False, so
        the state of the running script is never overwritten.
        """
        if self.query_one("#terminal", Terminal).is_busy:
            self.notify(
                "An execution is already underway.", severity="warning"
            )
            return False
        return True

    def _notify_removal_not_available(self) -> None:
        self.notify(
            translations.get(
                "remove_not_available_message",
                "No removable components were detected for this script.",
            ),
            title=translations.get(
                "remove_not_available_title", "Removal Not Available"
            ),
            severity="warning",
        )

    @staticmethod
    def _revert_capability(script_info: dict):
        """Return the revert capability of a script.

        BLOCKING: file access, so run it in a thread.

        Only existing LinuxToys script files are inspected. Non-scripts,
        repository entries, AppStream entries and missing paths return
        ``"yes"`` without reading anything. For the others, the answer
        comes from ``get_revert_capability``. ``"internal"`` means the
        script has its own removal method.
        """
        path = script_info.get("path", "")
        if (
            not script_info.get("is_script")
            or script_info.get("is_repo_entry")
            or script_info.get("is_appstream_entry")
            or not path
            or not os.path.isfile(path)
        ):
            return "yes"
        return get_revert_capability(path, get_system_compat_keys())

    def run_uninstall(self, button: InfoButton, script_info: dict) -> None:
        """Start the removal of a script without blocking the UI."""
        terminal = self.query_one("#terminal", Terminal)
        if self._preparing_run or terminal.is_busy:
            self.notify(
                "An execution is already underway.", severity="warning"
            )
            return
        self._preparing_run = True
        self.run_worker(
            self._prepare_uninstall(button, script_info),
            group="uninstall-prepare",
        )

    async def _prepare_uninstall(
        self, button: InfoButton, script_info: dict
    ) -> None:
        cleanup_path: str | None = None
        started = False
        try:
            uninstall_entry = await asyncio.to_thread(
                build_uninstall_script_entry, script_info, translations
            )
            if not uninstall_entry:
                self._notify_removal_not_available()
                return
            cleanup_path = uninstall_entry.get("cleanup_path")

            try:
                command = await asyncio.to_thread(
                    lambda: script_command(
                        uninstall_entry["path"], resolve_script_dir()
                    )
                )
            except Exception as exc:  # noqa: BLE001
                self.notify(
                    f"✗ Could not prepare removal of '{button.label}': {exc}",
                    severity="error",
                )
                return

            started = self._start_uninstall(
                button, script_info, uninstall_entry, command
            )
        finally:
            if cleanup_path and not started:
                self._cleanup_temp_file(cleanup_path, False)
            self._preparing_run = False

    def _start_uninstall(
        self,
        button: InfoButton,
        script_info: dict,
        uninstall_entry: dict,
        command: list[str],
    ) -> bool:
        """Set the run state and start the removal in the terminal.

        If the terminal does not accept the command, the run is closed
        and the user is warned. The cleanup of the temporary script is
        left to ``_prepare_uninstall``.
        """
        if not self._ensure_terminal_free():
            return False
        self._running_button = button
        self._running_script_info = script_info
        self._running_temp_path = uninstall_entry.get("cleanup_path")
        self._running_dev_mode = False
        self._running_is_uninstall = True
        self._running_is_appstream = False
        self._running_appstream_action = None

        self._show_terminal()
        terminal = self.query_one("#terminal", Terminal)
        started = terminal.run_script(
            command,
            env=self._script_env(str(button.label)),
        )
        if not started:
            self._finish_script_run()
            self.notify(
                "An execution is already underway.", severity="warning"
            )
        return started

    def _show_terminal(self) -> None:
        logo = self.query_one("#logo_lt")
        menu = self.query_one("#home-menu")
        terminal_container = self.query_one("#terminal-conteiner")
        terminal = self.query_one("#terminal", Terminal)

        logo.display = False
        menu.display = False
        terminal_container.display = True
        terminal.focus()

    def _hide_terminal(self) -> None:
        logo = self.query_one("#logo_lt")
        menu = self.query_one("#home-menu")
        terminal_container = self.query_one("#terminal-conteiner")

        terminal_container.display = False
        logo.display = True
        menu.display = True

    async def on_script_finished(self, message: ScriptFinished) -> None:
        """Handle the end of any run in the terminal.

        An update run goes to ``_finish_update_run`` and a manifest run to
        ``_on_manifest_item_finished``. Otherwise the exit code is
        classified:

        - Success: outside dev mode, a script install is saved to the
          registry from the transmap. The temporary file is deleted, and
          ``RebootDialog`` or ``SuccessDialog`` is shown.
        - Cancelled: the transmap is discarded and ``CancelledDialog``
          is shown.
        - Terminal closed: warns that a new session was started.
        - Error: an AppStream install is still saved to the registry. A
          regular install tries an automatic revert and notifies the
          result. Extensions need nothing. Then ``ErrorDialog`` offers a
          bug report.

        AppStream runs also redraw the app page. Dialogs call
        ``_finish_script_run`` when closed.

        Args:
            message: The ``ScriptFinished`` message with ``exit_code``.
        """
        if self._running_is_update:
            self._running_is_update = False
            self._finish_update_run(message.exit_code)
            return

        if self._is_manifest_run:
            self._on_manifest_item_finished(message)
            return
        script_info = self._running_script_info or {}
        is_extension = self._is_extension_entry(script_info)
        script_name = script_info.get("name", "Script")
        registry_name = script_info.get("registry_name", script_name)

        # verify if is reboot
        script_path = script_info.get("path", "")
        system_compat_keys = get_system_compat_keys()
        reboot = not is_extension and script_requires_reboot(
            script_path, system_compat_keys
        )

        temp_path = self._running_temp_path
        dev_mode = self._running_dev_mode
        is_uninstall = self._running_is_uninstall
        is_appstream = self._running_is_appstream
        exit_code = message.exit_code
        result = _classify_exit_code(exit_code)

        action_done = "removed" if is_uninstall else "installed"
        action_verb = "remove" if is_uninstall else "install"

        if result is ScriptResult.SUCCESS:
            if not dev_mode and not is_uninstall and not is_extension:
                _save_script_to_registry(registry_name, TRANSMAP_PATH)
                _cleanup_tmp_noram_dirs(TRANSMAP_PATH)
                self._remove_transmap()
            self._cleanup_temp_file(temp_path, dev_mode)

            if is_appstream:
                await self._refresh_app_page_after_run(
                    script_info, is_uninstall, succeeded=True
                )
            if reboot:
                self.app.push_screen(
                    RebootDialog(), callback=self._finish_script_run
                )
                self._reboot_system = True
            else:
                self.app.push_screen(
                    SuccessDialog(script_name, action=action_done),
                    callback=self._finish_script_run,
                )

        elif result is ScriptResult.CANCELLED:
            if not dev_mode and not is_uninstall:
                self._remove_transmap()
            self._cleanup_temp_file(temp_path, dev_mode)
            if is_appstream:
                await self._refresh_app_page_after_run(
                    script_info, is_uninstall, succeeded=False
                )
            self.app.push_screen(
                CancelledDialog(script_name), callback=self._finish_script_run
            )

        elif result is ScriptResult.TERMINAL_CLOSED:
            self.notify(
                "The terminal closed unexpectedly; a new session was started "
                "automatically.",
                severity="warning",
            )
            self._cleanup_temp_file(temp_path, dev_mode)
            if is_appstream:
                await self._refresh_app_page_after_run(
                    script_info, is_uninstall, succeeded=False
                )
            self._finish_script_run()

        else:  # ScriptResult.ERROR
            if is_extension:
                pass
            elif is_appstream and not is_uninstall:
                _save_script_to_registry(registry_name, TRANSMAP_PATH)
                self._remove_transmap()
            elif not dev_mode and not is_uninstall:
                revert_info = {
                    "name": script_name,
                    "icon": "application-x-executable",
                    "repo": "",
                }
                reverted = _try_execute_auto_revert(revert_info, TRANSMAP_PATH)
                if reverted:
                    self.notify(
                        f"'{script_name}' failed, but automatic reversion  "
                        "completed successfully.",
                        severity="warning",
                    )
                else:
                    self.notify(
                        f"✗ '{script_name}' failed (exit code {exit_code}) "
                        "and the automatic reversion also failed.",
                        severity="error",
                    )
                self._remove_transmap()

            if is_appstream:
                await self._refresh_app_page_after_run(
                    script_info, is_uninstall, succeeded=False
                )

            terminal = self.query_one("#terminal", Terminal)
            terminal_text = terminal.get_full_text()
            self._cleanup_temp_file(temp_path, dev_mode)
            self.app.push_screen(
                ErrorDialog(script_name, exit_code, action=action_verb),
                callback=lambda wants_report: self._on_error_dialog_closed(
                    wants_report, script_name, exit_code, terminal_text
                ),
            )

    def _remove_transmap(self) -> None:
        try:
            if os.path.exists(TRANSMAP_PATH):
                os.remove(TRANSMAP_PATH)
        except (IOError, OSError):
            pass

    def _cleanup_temp_file(
        self, temp_path: str | None, dev_mode: bool
    ) -> None:
        if dev_mode or not temp_path:
            return
        try:
            os.remove(temp_path)
        except OSError:
            pass

    def _finish_script_run(self, _result=None) -> None:
        if not self._running_is_appstream:
            self._hide_terminal()
        self._running_button = None
        self._running_script_info = None
        self._running_temp_path = None
        self._running_is_uninstall = False
        self._running_is_appstream = False
        self._running_appstream_action = None
        stack, self._running_appimage_stack = (
            self._running_appimage_stack,
            None,
        )
        if stack is not None:
            stack.close()
        self.run_worker(
            self._refresh_removable_state(),
            group="removable-refresh",
            exclusive=True,
        )

    async def _refresh_removable_state(self) -> None:
        """Atualiza o cache e redesenha a categoria aberta."""
        await asyncio.to_thread(installed_packages.refresh)
        await asyncio.to_thread(refresh_removable_state)

        if not self._nav_stack:
            return
        if self._aur_view_active():
            self._set_items_loading(True)
            self.run_worker(
                self._load_aur_items(), exclusive=True, group="aur-items"
            )

        if self._homebrew_view_active():
            self._set_items_loading(True)

            if is_homebrew_catalog_valid():
                self._homebrew_awaiting_refresh = False
                self._load_homebrew_items()
        current_path, _ = self._nav_stack[-1]
        await self._render_items(self._items_for_path(current_path))

    def _on_error_dialog_closed(
        self,
        wants_report: bool,
        script_name: str,
        exit_code: int,
        terminal_text: str,
    ) -> None:
        self._finish_script_run()
        if wants_report:
            self.run_worker(
                lambda: self._submit_bug_report(
                    script_name, exit_code, terminal_text
                ),
                thread=True,
                exclusive=False,
            )

    def _submit_bug_report(
        self, script_name: str, exit_code: int, terminal_text: str
    ) -> None:
        from requests.exceptions import ConnectionError, Timeout

        from app.antenna import antenna

        try:
            context_parts = [f"Script: {script_name} | exit code: {exit_code}"]
            system_context = antenna.get_system_context()
            if system_context:
                context_parts.append(system_context)
            history_context = antenna.get_history_context()
            if history_context:
                context_parts.append(history_context)
            context = " | ".join(context_parts)

            result = antenna.submit_issue(
                title="Bug Report from LinuxToys (TUI)",
                logs=terminal_text,
                context=context,
            )
            if result:
                issue_number = result.get("issue_number", "")
                self.app.call_from_thread(
                    self.notify,
                    f"Bug successfully reported (issue #{issue_number}).",
                    severity="information",
                )
            else:
                self.app.call_from_thread(
                    self.notify,
                    "It was not possible to send the bug report.",
                    severity="error",
                )
        except ConnectionError:
            self.app.call_from_thread(
                self.notify,
                "Without an internet connection, it was not possible to report the bug.",
                severity="error",
            )
        except Timeout:
            self.app.call_from_thread(
                self.notify,
                "Timed out while trying to report the bug.",
                severity="error",
            )
        except Exception as exc:
            self.app.call_from_thread(
                self.notify,
                f"Error while reporting the bug: {exc}",
                severity="error",
            )

    def on_password_prompt_detected(
        self, message: PasswordPromptDetected
    ) -> None:
        """O terminal detectou algo parecido com um prompt de senha —
        mostra o diálogo em vez de deixar o usuário digitar no terminal cru."""
        script_name = (
            str(self._running_button.label)
            if self._running_button
            else "script"
        )
        self.app.push_screen(
            SudoPasswordScreen(script_name),
            callback=self._on_password_submitted,
        )

    def _on_password_submitted(self, password: str | None) -> None:
        terminal = self.query_one("#terminal", Terminal)
        if password is None:
            terminal.cancel_password_prompt()
            terminal.send_interrupt()
        else:
            terminal.send_password(password)
        terminal.focus()

    def _update_breadcrumb(self) -> None:
        panel = self.query_one("#left-panel-home")
        base = "LinuxToys"
        if not self._nav_stack:
            panel.border_title = base
            return

        current_path, current_name = self._nav_stack[-1]
        if is_specials_path(current_path):
            specials_label = translations.get("specials", "Specials")
            if current_path == SPECIALS_ROOT:
                panel.border_title = specials_label
            else:
                panel.border_title = f"{specials_label} > {current_name}"
            return

        if is_homebrew_path(current_path):
            panel.border_title = current_name or "Homebrew"
            return

        if is_appimage_path(current_path):
            panel.border_title = " › ".join(
                [
                    translations.get("appimage_category", "AppImages"),
                    *[
                        translations.get(p, p)
                        for p in appimage_relative(current_path).split("/")
                        if p
                    ],
                ]
            )
            return

        crumbs = get_breadcrumb_path(current_path, translations)
        names = " › ".join(
            translations.get(c["name"], c["name"]) for c in crumbs
        )
        panel.border_title = names if names else base

    def _current_app_page(self) -> AppPageWidget | None:
        try:
            return self.query_one(AppPageWidget)
        except NoMatches:
            return None

    @staticmethod
    def _is_extension_entry(entry: Mapping[str, Any] | None) -> bool:
        """Return True for a Flatpak extension.
        Extensions have a ``parent_id`` (set by ``appstream_cache``).
        """
        return bool((entry or {}).get("parent_id"))

    def _reset_app_page_buttons(self) -> None:
        """Re-enable the app page controls after an error or a cancel.

        Extension runs refresh the extension list. For other runs, the
        control that matches the running AppStream action is reset:
        Remove for ``uninstall``, Revert for ``revert`` and Install for
        everything else. Does nothing without an app page.
        """
        page = self._current_app_page()
        if page is None:
            return
        if self._is_extension_entry(self._running_script_info):
            page.refresh_extensions()
            return
        action = self._running_appstream_action
        if action == "uninstall":
            page.reset_remove_button()
        elif action == "revert":
            page.reset_revert_button()
        else:
            page.reset_install_button()

    async def _refresh_app_page_after_run(
        self,
        script_info: dict,
        is_uninstall: bool,
        *,
        succeeded: bool,
    ) -> None:
        page = self._current_app_page()
        if page is None:
            return
        if self._is_extension_entry(script_info):
            self.query_one("#terminal-conteiner").display = False
            page.refresh_extensions()
            return
        if not succeeded:
            self._reset_app_page_buttons()
            return
        await show_app_page(
            self,
            page.script_info,
            translations=translations,
            featured=None,
            installed=not is_uninstall,
        )

    def _schedule_homebrew_search(self, query: str) -> None:
        """Run a Homebrew search after 0.2 s without new input."""
        if self._homebrew_search_timer:
            self._homebrew_search_timer.stop()
        self._homebrew_search_timer = self.set_timer(
            0.2, partial(self._run_homebrew_search, query)
        )

    def _run_homebrew_search(self, query: str) -> None:
        if not self._homebrew_view_active():
            return
        self.run_worker(
            self._homebrew_search_async(query),
            exclusive=True,
            group="homebrew-items",
        )

    async def _homebrew_search_async(self, query: str) -> None:
        if not query:
            await self._load_homebrew_items_async()
            return

        try:
            results = await asyncio.to_thread(search_homebrew_items, query)
        except Exception:  # noqa: BLE001
            if self._homebrew_view_active():
                await self._show_items_message(
                    translations.get(
                        "homebrew_catalog_unavailable",
                        "Homebrew metadata is unavailable. Try again later.",
                    )
                )
            return

        current = self.query_one("#search-input", Input).value.strip()
        if not self._homebrew_view_active() or current != query:
            return

        if not results:
            await self._show_items_message(
                translations.get(
                    "homebrew_no_results", "No Homebrew packages found."
                )
            )
            return
        await self._render_items(results, lazy=True)

    def _appimage_view_active(self) -> bool:
        return bool(self._nav_stack) and is_appimage_path(
            self._nav_stack[-1][0]
        )

    async def _open_appimage_category(self, button: InfoButton) -> None:
        self._nav_stack.append((button.path, str(button.label)))
        self._update_breadcrumb()
        await self._render_items([])
        if self._appimage_view_active():
            self._set_items_loading(True)
        self._load_appimage_items()

    def _load_appimage_items(self) -> None:
        self.run_worker(
            self._load_appimage_items_async(),
            exclusive=True,
            group="appimage-items",
        )

    async def _load_appimage_items_async(self) -> None:
        if not self._appimage_view_active():
            return
        path = self._nav_stack[-1][0]
        try:
            items = await asyncio.to_thread(get_appimage_items, path)
        except Exception:  # noqa: BLE001
            if self._appimage_view_active():
                await self._show_items_message(
                    translations.get(
                        "appimage_unavailable",
                        "AppImage catalog is unavailable.",
                    )
                )
            return
        if not self._appimage_view_active() or self._nav_stack[-1][0] != path:
            return  # navegou durante a carga
        if not items:
            await self._show_items_message(
                translations.get("appimage_no_items", "No AppImages found.")
            )
            return
        await self._render_items(items, lazy=True)

    def _schedule_appimage_search(self, query: str) -> None:
        if self._appimage_search_timer:
            self._appimage_search_timer.stop()
        self._appimage_search_timer = self.set_timer(
            0.2, partial(self._run_appimage_search, query)
        )

    def _run_appimage_search(self, query: str) -> None:
        if not self._appimage_view_active():
            return
        self.run_worker(
            self._appimage_search_async(query),
            exclusive=True,
            group="appimage-items",
        )

    async def _appimage_search_async(self, query: str) -> None:
        if not query:
            await self._load_appimage_items_async()
            return
        try:
            results = await asyncio.to_thread(search_appimage_items, query)
        except Exception:  # noqa: BLE001
            logger.exception("AppImage search failed")
            return
        current = self.query_one("#search-input", Input).value.strip()
        if not self._appimage_view_active() or current != query:
            return
        if not results:
            await self._show_items_message(
                translations.get("appimage_no_results", "No AppImages found.")
            )
            return
        await self._render_items(results, lazy=True)

    async def _activate_aur_category(self, button: InfoButton) -> None:
        """Pede consentimento (uma vez) e abre o AUR como uma categoria."""
        if aur_cache.enabled():
            await self._open_aur_category(button)
            return
        self.app.push_screen(
            AurConsentDialog(),
            callback=lambda accepted: self._on_aur_consent(button, accepted),
        )

    def _on_aur_consent(self, button: InfoButton, accepted: bool) -> None:
        if not accepted:
            return
        if not aur_cache.enable():
            self.notify(
                "The AUR is not supported on this system.",
                severity="warning",
            )
            return
        self.run_worker(self._open_aur_category(button))

    def _aur_view_active(self) -> bool:
        return (
            bool(self._nav_stack)
            and self._nav_stack[-1][0] == self._aur_category_path
        )

    async def _open_aur_category(self, button: InfoButton) -> None:
        self._aur_category_path = button.path
        self._nav_stack.append((button.path, str(button.label)))
        self._update_breadcrumb()
        await self._render_items([])
        if self._aur_view_active():
            self._set_items_loading(True)
        self.run_worker(
            self._load_aur_items(), exclusive=True, group="aur-items"
        )

    @staticmethod
    def _fetch_aur_items():
        """Refresh the AUR metadata if stale and return the entries.

        BLOCKING: network, pacman and the catalog, so run it in a
        thread.

        Returns:
            The entries to browse.
        """
        aur_cache.refresh_if_stale()
        return aur_cache.browse_entries()

    async def _load_aur_items(self) -> None:
        """Load the AUR entries and render them.

        Reads in a thread. An error shows its detail as a message, and an
        empty result shows the "unavailable" message. A late result is
        ignored if the user already left the category, as in the GUI.
        """
        unavailable = translations.get(
            "aur_refresh_failed_title", "AUR metadata unavailable"
        )
        try:
            items = await asyncio.to_thread(self._fetch_aur_items)
        except Exception as exc:  # noqa: BLE001 - erros do catálogo em Rust
            if self._aur_view_active():
                await self._show_items_message(f"{unavailable}\n\n{exc}")
            return
        if not self._aur_view_active():
            return
        if not items:
            await self._show_items_message(unavailable)
            return
        await self._render_items(items, lazy=True)


class AppstreamRunnerMixin:
    """Install, remove and revert AppStream items in the embedded terminal.

    Mixin for the main app class. Each ``run_appstream_*`` method
    prepares a temporary script (or an argv list), fills the ``_running_*``
    state and starts it in the terminal with ``pause_on_exit=False``. The
    host handles the end of the run (``_finish_script_run``), reading that
    state and using ``_running_appstream_action`` to tell the cases apart."""

    _running_is_appstream: bool = False
    _running_appstream_action: str | None = None
    _running_appimage_stack: ExitStack | None

    _running_button: InfoButton | None
    _running_script_info: dict | None
    _running_temp_path: str | None
    _running_dev_mode: bool
    _running_is_uninstall: bool

    @staticmethod
    def _is_plain_script_entry(entry: Mapping[str, Any]) -> bool:
        return not entry.get("is_appstream_entry")

    async def _run_plain_script_from_page(self, entry: dict) -> None:
        """Run a non-AppStream entry that has an app page."""
        button = InfoButton(
            entry["name"],
            entry.get("description", ""),
            entry["path"],
            entry.get("is_script", True),
            is_repo_entry=entry.get("is_repo_entry", False),
            is_appstream_entry=False,
            has_app_page=True,
            info=entry,
        )
        if self._is_app_page_showing:
            await hide_app_page(self)
        await self.handle_desc_button(button)

    def _reset_appstream_remove_button(self) -> None:
        page = self._current_app_page()
        if page is not None:
            page.reset_remove_button()

    @staticmethod
    def _prepare_install_command(entry: dict) -> tuple[Any, str]:
        script_dir = resolve_script_dir()
        if entry.get("appstream_source") == "homebrew":
            raw_path = homebrew_catalog.materialize_install(entry)["path"]
            return script_command(raw_path, script_dir), raw_path

        raw_path = build_install_script(entry)
        script_path = create_temp_file(raw_path)
        try:
            os.remove(raw_path)
        except OSError:
            pass
        return script_path, script_path

    def run_appstream_install(self, script_info: Mapping[str, Any]) -> None:
        entry = dict(script_info)
        name = entry.get("name", "")

        if self._is_plain_script_entry(entry):
            self.run_worker(self._run_plain_script_from_page(entry))
            return

        if self._preparing_run or not self._ensure_terminal_free():
            self._reset_install_button()
            return

        if entry.get("appstream_source") == "appimage":
            self._preparing_run = True
            self.run_worker(
                self._run_appimage_install(entry), group="appimage-install"
            )
            return

        try:
            os.makedirs(
                os.path.dirname(TRANSMAP_PATH), mode=0o700, exist_ok=True
            )
            with open(TRANSMAP_PATH, "w"):
                pass
            command, temp_path = self._prepare_install_command(entry)
        except (OSError, ValueError) as exc:
            self.notify(
                f"✗ Could not prepare install of '{name}': {exc}",
                severity="error",
            )
            self._reset_install_button()
            return
        self._running_button = None
        self._running_script_info = entry
        self._running_temp_path = temp_path
        self._running_dev_mode = False
        self._running_is_uninstall = False
        self._running_is_appstream = True
        self._running_appstream_action = "install"

        terminal = self.query_one("#terminal", Terminal)
        terminal.run_script(
            command,
            env=self._script_env(
                name,
                TRANSMAP_PATH=TRANSMAP_PATH,
            ),
            pause_on_exit=False,
        )

    def _reset_install_button(self) -> None:
        page = self._current_app_page()
        if page is not None:
            page.reset_install_button()

    def run_appstream_snap_revert(
        self, script_info: Mapping[str, Any]
    ) -> None:
        entry = dict(script_info)
        name = entry.get("name", "")
        try:
            argv = build_snap_revert_command(entry)
        except ValueError:
            self.notify(
                f"✗ '{entry.get('name', '')}' has no snap package to revert.",
                severity="warning",
            )
            return

        directory = "/tmp/linuxtoys/appstream-overrides"
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, raw_path = tempfile.mkstemp(
            prefix="snap-revert-", suffix=".sh", dir=directory, text=True
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("#!/usr/bin/env bash\n")
            handle.write(" ".join(shlex.quote(part) for part in argv))
            handle.write("\n")
        os.chmod(raw_path, 0o700)

        resolve_script_dir()
        script_path = create_temp_file(raw_path)
        try:
            os.remove(raw_path)
        except OSError:
            pass

        try:
            with open(TRANSMAP_PATH, "w"):
                pass
        except (IOError, OSError):
            pass

        self._running_button = None
        self._running_script_info = entry
        self._running_temp_path = script_path
        self._running_dev_mode = False
        self._running_is_uninstall = False
        self._running_is_appstream = True
        self._running_appstream_action = "revert"

        terminal = self.query_one("#terminal", Terminal)
        terminal.run_script(
            script_path,
            env=self._script_env(name, TRANSMAP_PATH=TRANSMAP_PATH),
            pause_on_exit=False,
        )

    def run_appstream_uninstall(self, script_info: Mapping[str, Any]) -> None:
        entry = dict(script_info)
        if self._is_plain_script_entry(entry):
            self.run_worker(self._run_plain_script_from_page(entry))
            return

        if self._preparing_run or not self._ensure_terminal_free():
            self._reset_appstream_remove_button()
            return
        self._preparing_run = True
        self.run_worker(
            self._prepare_appstream_uninstall(dict(script_info)),
            group="uninstall-prepare",
        )

    @staticmethod
    def _resolve_appstream_removal(
        entry: dict,
    ) -> tuple[dict | None, list[str]]:
        """Decide how to remove an AppStream item.

        BLOCKING: runs in a thread.

        Order: items that other packages depend on are blocked. An item
        that is not in the LinuxToys registry but is found on the system
        gets an external removal. Any other item gets the standard
        uninstall entry."""
        blockers = installed_packages.dependency_blockers(entry)
        if blockers:
            return None, blockers

        if not is_registered_entry(entry, parse_registry_file()):
            observed = installed_packages.match(entry)
            if observed is not None:
                return (
                    installed_packages.build_external_removal(
                        entry, observed, translations
                    ),
                    [],
                )
        return build_uninstall_script_entry(entry, translations), []

    async def _prepare_appstream_uninstall(self, entry: dict) -> None:
        """Prepare and start the removal of an item."""
        name = entry.get("name", "")
        cleanup_path: str | None = None
        started = False
        try:
            remove_info, blockers = await asyncio.to_thread(
                self._resolve_appstream_removal, entry
            )
            if blockers:
                self._notify_removal_blocked(name, blockers)
                return
            if not remove_info:
                self._notify_removal_not_available()
                return
            cleanup_path = remove_info.get("cleanup_path")

            try:
                command = await asyncio.to_thread(
                    lambda: script_command(
                        remove_info["path"], resolve_script_dir()
                    )
                )
            except Exception as exc:  # noqa: BLE001
                self.notify(
                    f"✗ Could not prepare removal of '{name}': {exc}",
                    severity="error",
                )
                return

            started = self._start_appstream_uninstall(
                entry, cleanup_path, command
            )
        finally:
            if cleanup_path and not started:
                self._cleanup_temp_file(cleanup_path, False)
            if not started:
                self._reset_appstream_remove_button()
            self._preparing_run = False

    def _start_appstream_uninstall(
        self, entry: dict, cleanup_path: str | None, command: list[str]
    ) -> bool:
        if not self._ensure_terminal_free():
            return False
        self._running_button = None
        self._running_script_info = entry
        self._running_temp_path = cleanup_path
        self._running_dev_mode = False
        self._running_is_uninstall = True
        self._running_is_appstream = True
        self._running_appstream_action = "uninstall"

        terminal = self.query_one("#terminal", Terminal)
        started = terminal.run_script(
            command,
            env=self._script_env(entry.get("name", "unknown")),
            pause_on_exit=False,
        )
        if not started:
            self._finish_script_run()
        return started

    async def run_appstream_aur_install(
        self, script_info: Mapping[str, Any]
    ) -> None:
        entry = dict(script_info)
        name = entry.get("name", "")
        package = str(entry.get("package-name") or "").strip()

        if not package:
            self.notify(
                f"✗ '{name}' has no AUR package name.", severity="error"
            )
            page = self._current_app_page()
            if page is not None:
                page.reset_install_button()
            return

        status, detail = await asyncio.to_thread(
            check_aur_package_security, package
        )

        if status != AUR_SECURITY_OK:
            page = self._current_app_page()
            if page is not None:
                page.reset_install_button()
            self.app.push_screen(
                AurSecurityDialog(
                    name,
                    blocked=(status == AUR_SECURITY_BLOCKED),
                    detail=detail,
                )
            )
            return

        if self._aur_helper_missing():
            self._reset_install_button()
            self.app.push_screen(
                AurHelperDialog(), callback=self._on_aur_helper_answer
            )
            return

        raw_path = build_aur_install_script(package)
        resolve_script_dir()
        script_path = create_temp_file(raw_path)
        try:
            os.remove(raw_path)
        except OSError:
            pass

        try:
            with open(TRANSMAP_PATH, "w"):
                pass
        except (IOError, OSError):
            pass
        if not self._ensure_terminal_free():
            page = self._current_app_page()
            if page is not None:
                page.reset_install_button()
            return
        self._running_button = None
        self._running_script_info = entry
        self._running_temp_path = script_path
        self._running_dev_mode = False
        self._running_is_uninstall = False
        self._running_is_appstream = True
        self._running_appstream_action = "install"

        terminal = self.query_one("#terminal", Terminal)
        terminal.run_script(
            script_path,
            env=self._script_env(name, TRANSMAP_PATH=TRANSMAP_PATH),
            pause_on_exit=False,
        )

    def _refresh_extensions_page(self) -> None:
        """Refresh the extension list of the current app page, if any."""
        page = self._current_app_page()
        if page is not None:
            page.refresh_extensions()

    def run_appstream_extension(
        self, info: Mapping[str, Any], *, remove: bool
    ) -> None:
        entry = dict(info)
        name = str(entry.get("name") or entry.get("flatpak_ref") or "")
        try:
            argv = build_flatpak_extension_command(entry, remove)
        except ValueError as exc:
            self.notify(f"✗ {exc}", severity="warning")
            self._refresh_extensions_page()
            return
        if not self._ensure_terminal_free():
            self._refresh_extensions_page()
            return

        self._running_button = None
        self._running_script_info = entry
        self._running_temp_path = None
        self._running_dev_mode = False
        self._running_is_uninstall = remove
        self._running_is_appstream = True
        self._running_appstream_action = (
            "extension_remove" if remove else "extension_install"
        )

        terminal = self.query_one("#terminal", Terminal)
        started = terminal.run_script(
            argv, env=self._script_env(name), pause_on_exit=False
        )
        if not started:
            self._finish_script_run()
            self._refresh_extensions_page()

    async def _run_appimage_install(self, entry: dict) -> None:
        """Download an AppImage and start its installation."""
        from app import appimage_catalog

        stack = ExitStack()
        started = False
        try:
            path, release = await asyncio.to_thread(
                lambda: stack.enter_context(
                    appimage_catalog.download_for_install(entry)
                )
            )
            started = self._start_appimage_install(entry, path, release, stack)
        except (OSError, ValueError, RuntimeError) as exc:
            self.notify(
                f"✗ AppImage installation failed: {exc}", severity="error"
            )
        finally:
            if not started:
                stack.close()
                self._reset_install_button()
            self._preparing_run = False

    def _start_appimage_install(
        self, entry: dict, path: str, release: Any, stack: ExitStack
    ) -> bool:
        if not self._ensure_terminal_free():
            return False
        directory = os.path.dirname(TRANSMAP_PATH)
        os.makedirs(directory, mode=0o700, exist_ok=True)
        with open(TRANSMAP_PATH, "w"):
            pass

        fd, script_path = tempfile.mkstemp(
            prefix="local-package-", suffix=".sh", dir=directory, text=True
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("#!/usr/bin/env bash\n")
                handle.write(f"pkg_appimage {shlex.quote(path)}\n")
            os.chmod(script_path, 0o700)
            command = script_command(script_path, resolve_script_dir())
        except (OSError, ValueError):
            self._cleanup_temp_file(script_path, False)
            raise

        self._running_button = None
        self._running_script_info = {**entry, "appimage_release": release}
        self._running_temp_path = script_path
        self._running_dev_mode = False
        self._running_is_uninstall = False
        self._running_is_appstream = True
        self._running_appstream_action = "install"
        self._running_appimage_stack = stack

        terminal = self.query_one("#terminal", Terminal)
        started = terminal.run_script(
            command,
            env=self._script_env(
                entry.get("name", ""), TRANSMAP_PATH=TRANSMAP_PATH
            ),
            pause_on_exit=False,
        )
        if not started:
            self._cleanup_temp_file(script_path, False)
            self._finish_script_run()
        return bool(started)

    @staticmethod
    def _aur_helper_missing() -> bool:
        """Return True if installing an AUR package needs paru and it is missing."""
        if "manjaro" in get_system_compat_keys():
            return False
        return shutil.which("paru") is None

    def _on_aur_helper_answer(self, accepted: bool) -> None:
        """Install paru if the user accepted ``AurHelperDialog``."""
        if accepted:
            self.run_worker(self._install_aur_helper())

    async def _install_aur_helper(self) -> None:
        """Run the ``Paru`` script through the common script flow."""
        info = await find_script_by_name_async("Paru", translations)
        if info is None:
            self.notify("✗ Script 'Paru' not found.", severity="warning")
            return
        button = InfoButton(
            info["name"],
            info.get("description", ""),
            info["path"],
            True,
            info=info,
        )
        if self._is_app_page_showing:
            await hide_app_page(self)
        self.run_script(button)


class ManifestRunnerMixin:
    """Run a manifest: resolve it, confirm the plan and execute the items.

    Mixin for the main app class. Flow:

    1. ``on_manifest_chosen`` receives the file picked in
       ``ManifestDialog``.
    2. ``_classify_manifest`` (worker thread) loads and resolves it into
       a ``ManifestPlan``, and ``_on_manifest_resolved`` routes the plan.
    3. A missing prerequisite (Flatpak/Flathub or Homebrew) is offered
       for setup in the terminal, and then the manifest is resolved
       again.
    4. ``_review_manifest_plan`` asks for confirmation. A dry run
       validates the items, and a real run builds a queue and executes it
       one item at a time through the host's ``_execute_script_info``.
    5. Each ``ScriptFinished`` reaches ``_on_manifest_item_finished`` and
       ``_advance_manifest`` decides what happens next. The run ends with
       ``ManifestReportDialog``.

    ``StartupRecommendationsMixin`` reuses ``_prepare_queue_script``,
    ``_start_manifest_queue`` and ``_discard_manifest_temp_files``.

    The host must provide ``notify``, ``run_worker``, ``app``,
    ``_execute_script_info``, ``_show_terminal``, ``_hide_terminal``,
    ``_cleanup_temp_file``, ``_remove_transmap``, ``_running_button``,
    ``_running_script_info``, ``_running_temp_path``,
    ``_running_dev_mode`` and ``_is_startup``.

    Attributes:
        _manifest_queue: Items waiting to run, in order.
        _manifest_results: Result dicts of the items already run.
        _manifest_temp_files: Generated scripts to delete when the run
            ends.
        _manifest_bootstrap: State of a prerequisite setup in progress
            (``path``, ``kind`` and ``attempted``), or None.
        _is_manifest_run: True while a run or a prerequisite setup is
            active. The host uses it to route ``ScriptFinished`` to
            ``_on_manifest_item_finished``.
        _MANIFEST_BOOTSTRAP_LABELS: Display name of each prerequisite
            kind.
    """

    _manifest_queue: list[dict] = []
    _manifest_results: list[dict] = []
    _manifest_temp_files: list[str] = []
    _manifest_bootstrap: dict | None = None
    _is_manifest_run: bool = False

    _MANIFEST_BOOTSTRAP_LABELS = {
        "flatpak": "Flatpak/Flathub",
        "homebrew": "Homebrew",
    }

    def on_manifest_chosen(self, manifest_path: str | None) -> None:
        if manifest_path is None:
            return
        # resolve_script_dir()
        if self._is_manifest_run:
            self.notify(
                "A manifest execution is already in progress.",
                severity="warning",
            )
            return
        self.notify("loading manifest...", timeout=3)
        self._start_manifest_classify(manifest_path)

    def _start_manifest_classify(
        self,
        manifest_path: str,
        attempted: tuple[str, ...] = (),
        refresh_appstream: bool = False,
    ) -> None:
        """Resolve the manifest in an exclusive thread worker."""
        self.run_worker(
            lambda: self._classify_manifest(
                manifest_path, attempted, refresh_appstream
            ),
            thread=True,
            exclusive=True,
            name="manifest_classify",
        )

    def _classify_manifest(
        self,
        manifest_path: str,
        attempted: tuple[str, ...] = (),
        refresh_appstream: bool = False,
    ) -> None:
        """Load and resolve the manifest off the UI thread."""
        from app.manifest_helper import load_manifest

        from .manifest_resolver import (
            refresh_appstream_after_flathub,
            resolve_manifest,
        )

        resolve_script_dir()

        if refresh_appstream:
            # Flathub was just enabled: make its AppStream entries visible.
            try:
                refresh_appstream_after_flathub()
            except Exception as exc:  # mirrors the CLI bootstrap helper
                self.app.call_from_thread(
                    self.notify,
                    f"Failed to update AppStream: {exc}",
                    severity="error",
                )
                return

        try:
            names = load_manifest(manifest_path)
        except (OSError, ValueError):  # ValueError covers UnicodeDecodeError
            self.app.call_from_thread(
                self.notify,
                "Unable to read the manifest.",
                severity="error",
            )
            return

        if not names:
            self.app.call_from_thread(
                self.notify, "Empty or invalid manifest.", severity="warning"
            )
            return

        try:
            plan = resolve_manifest(names, translations)
        except Exception as exc:  # worker boundary: never let it kill the TUI
            self.app.call_from_thread(
                self.notify,
                f"Error validating the manifest: {exc}",
                severity="error",
            )
            return
        self.app.call_from_thread(
            self._on_manifest_resolved, plan, manifest_path, attempted
        )

    def _on_manifest_resolved(
        self, plan, manifest_path: str, attempted: tuple[str, ...]
    ) -> None:
        """Route the resolved plan, on the main thread."""
        if plan.bootstrap is None:
            self._review_manifest_plan(plan)
            return

        label = self._MANIFEST_BOOTSTRAP_LABELS[plan.bootstrap]
        if plan.bootstrap in attempted:
            self.notify(
                f"{label} continua indisponível após a configuração.",
                severity="error",
            )
        elif self._dry_run_enabled():
            self.notify(
                f"Pré-requisito ausente: {label}. "
                "O modo dev não instala pré-requisitos.",
                severity="warning",
            )
        else:
            self._offer_manifest_bootstrap(plan, manifest_path, attempted)

    @staticmethod
    def _dry_run_enabled() -> bool:
        from app.dev_mode import should_dry_run_scripts

        return should_dry_run_scripts()

    def _offer_manifest_bootstrap(
        self, plan, manifest_path: str, attempted: tuple[str, ...]
    ) -> None:
        """Ask whether to set up the missing prerequisite."""
        label = self._MANIFEST_BOOTSTRAP_LABELS[plan.bootstrap]
        self.app.push_screen(
            ManifestPlanDialog(
                f"Este manifesto requer {label}",
                [
                    f"{label} não está configurado neste sistema.",
                    "",
                    "Configurar agora e continuar a validação do manifesto?",
                ],
                confirm_label="Configurar",
            ),
            partial(
                self._on_manifest_bootstrap_answer,
                plan,
                manifest_path,
                attempted,
            ),
        )

    def _on_manifest_bootstrap_answer(
        self,
        plan,
        manifest_path: str,
        attempted: tuple[str, ...],
        confirmed: bool | None,
    ) -> None:
        if not confirmed:
            self.notify("Operation cancelled.", timeout=3)
            return

        # Both run in the terminal: they may need sudo.
        self._manifest_temp_files = []
        if plan.bootstrap == "homebrew":
            item = plan.bootstrap_script
        else:
            try:
                item = self._batch_item("Flatpak/Flathub", ["pkg_flat"])
            except OSError as exc:
                self.notify(
                    f"It was not possible to prepare the script: {exc}",
                    severity="error",
                )
                return

        self._manifest_bootstrap = {
            "path": manifest_path,
            "kind": plan.bootstrap,
            "attempted": (*attempted, plan.bootstrap),
        }
        self._is_manifest_run = True  # routes ScriptFinished to our handler
        self._running_button = None
        self._execute_script_info(item)

    def _after_manifest_bootstrap(self, result, exit_code: int | None) -> None:
        state = self._manifest_bootstrap
        self._manifest_bootstrap = None
        self._is_manifest_run = False
        self._running_script_info = None
        self._running_temp_path = None
        self._hide_terminal()
        self._discard_manifest_temp_files()

        label = self._MANIFEST_BOOTSTRAP_LABELS[state["kind"]]
        if result is ScriptResult.SUCCESS:
            self.notify("Validating manifest...", timeout=3)
            self._start_manifest_classify(
                state["path"],
                state["attempted"],
                refresh_appstream=state["kind"] == "flatpak",
            )
        elif result is ScriptResult.CANCELLED:
            self.notify(
                f"{label} configuration cancelled.", severity="warning"
            )
        elif result is ScriptResult.ERROR:
            self.notify(
                f"failed to configure {label} (code {exit_code}).",
                severity="error",
            )

    def _review_manifest_plan(self, plan) -> None:
        """Mirror the CLI: any rejected item aborts, otherwise ask to go on."""
        if not plan.is_valid:
            self.app.push_screen(
                ManifestPlanDialog(
                    "invalid manifest. Nothing will be installed.",
                    [f"✗ {error}" for error in plan.errors],
                    cancel_label="Close",
                )
            )
            return

        if plan.total == 0:
            if plan.warnings:
                self.app.push_screen(
                    ManifestPlanDialog(
                        "No items to execute",
                        [f"- {warning}" for warning in plan.warnings],
                        cancel_label="Close",
                    )
                )
            else:
                self.notify(
                    "No compatible item found in the manifest.",
                    severity="warning",
                )
            return

        dry_run = self._dry_run_enabled()
        lines = self._manifest_plan_lines(plan)
        if dry_run:
            heading = f"DRY-RUN: validar {plan.total} item(ns)?"
            lines = [
                "Nada será instalado: scripts são validados; pacotes, "
                "snaps e flatpaks apenas simulados.",
                "",
                *lines,
            ]
            confirm_label = "Validar"
        else:
            heading = f"Instalar {plan.total} item(ns)?"
            confirm_label = "Continuar"

        self.app.push_screen(
            ManifestPlanDialog(heading, lines, confirm_label=confirm_label),
            partial(self._on_manifest_plan_answer, plan, dry_run),
        )

    @staticmethod
    def _manifest_plan_lines(plan) -> list[str]:
        # Same order in which the queue is executed.
        lines = [f"[PACOTE] {name}" for name in plan.packages]
        lines += [f"[SNAP] {name}" for name in plan.snaps]
        lines += [f"[FLATPAK] {name}" for name in plan.flatpaks]
        lines += [f"[SCRIPT] {script['name']}" for script in plan.scripts]
        if plan.warnings:
            lines += ["", "Ignorados:"]
            lines += [f"  - {warning}" for warning in plan.warnings]
        return lines

    def _on_manifest_plan_answer(
        self, plan, dry_run: bool, confirmed: bool | None
    ) -> None:
        if not confirmed:
            self.notify("Operação cancelada.", timeout=3)
            return
        if dry_run:
            self._start_manifest_dry_run(plan)
            return
        try:
            queue = self._build_manifest_queue(plan)
        except (OSError, ValueError) as exc:
            self._discard_manifest_temp_files()
            self.notify(
                f"Não foi possível preparar a execução: {exc}",
                severity="error",
            )
            return
        self._start_manifest_queue(queue)

    def _build_manifest_queue(self, plan) -> list[dict]:
        """Packages, snaps and flatpaks first (one item each), then scripts.

        One item per kind keeps exit codes meaningful: a single combined
        script would only report the status of its last command.
        """
        self._manifest_temp_files = []
        queue: list[dict] = []

        if plan.packages:
            values = self._shell_words(plan.packages)
            queue.append(
                self._batch_item(
                    f"Packages ({len(plan.packages)})",
                    ["askpass", f"pkg_install {values}"],
                )
            )
        if plan.snaps:
            values = self._shell_words(plan.snaps)
            queue.append(
                self._batch_item(
                    f"Snaps ({len(plan.snaps)})", [f"pkg_snap {values}"]
                )
            )
        if plan.flatpaks:
            values = self._shell_words(plan.flatpaks)
            queue.append(
                self._batch_item(
                    f"Flatpaks ({len(plan.flatpaks)})", [f"pkg_flat {values}"]
                )
            )

        queue.extend(self._prepare_queue_script(s) for s in plan.scripts)
        return queue

    def _prepare_queue_script(self, script: dict) -> dict:
        """Homebrew entries have a virtual path: materialize like run_script."""
        if script.get("appstream_source") != "homebrew":
            return script
        from app import homebrew_catalog

        materialized = homebrew_catalog.materialize_install(script)
        self._manifest_temp_files = [
            *self._manifest_temp_files,
            materialized["path"],
        ]
        return materialized

    @staticmethod
    def _shell_words(names: list[str]) -> str:
        """Join names into one shell-quoted, space-separated string."""
        return " ".join(shlex.quote(name) for name in names)

    def _batch_item(self, name: str, lines: list[str]) -> dict:
        return {
            "name": name,
            "path": self._write_batch_script(lines),
            "is_script": True,
            "is_batch": True,
        }

    def _write_batch_script(self, lines: list[str]) -> str:
        """Write a temporary bash script with the given library calls.

        ``create_temp_file`` prepends the preamble that sets SCRIPT_DIR and
        loads the core library, so nothing is sourced here.
        """
        content = "\n".join(["#!/bin/bash", "set -eo pipefail", *lines, ""])
        fd, path = tempfile.mkstemp(prefix="linuxtoys-manifest-", suffix=".sh")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(path, 0o700)
        # Rebinding (not appending) avoids mutating the shared class attribute.
        self._manifest_temp_files = [*self._manifest_temp_files, path]
        return path

    def _discard_manifest_temp_files(self) -> None:
        """Remove generated batch/Homebrew scripts.

        ``_running_temp_path`` is the copy made by ``create_temp_file``; the
        scripts written above must be removed separately.
        """
        dev_mode = getattr(self, "_running_dev_mode", False)
        for temp_path in self._manifest_temp_files:
            self._cleanup_temp_file(temp_path, dev_mode)
        self._manifest_temp_files = []

    def _manifest_script_env(self, script_info: dict) -> dict[str, str]:
        """Extra variables the CLI exports through ``script_environment``."""
        from app.manifest_helper import script_environment

        env = script_environment(
            script_info, {"SCRIPT_DIR": resolve_script_dir()}
        )
        # The terminal receives one `export` line: keep every value on it.
        return {
            key: str(value).replace("\r", " ").replace("\n", " ")
            for key, value in env.items()
        }

    def _manifest_start_failed(
        self, script_name: str, exit_code: int = 1
    ) -> None:
        """An item could not even start (e.g. repo entry preparation)."""
        if self._manifest_bootstrap is not None:
            self._after_manifest_bootstrap(ScriptResult.ERROR, exit_code)
        else:
            self._advance_manifest(script_name, exit_code)

    def _on_manifest_item_finished(self, message) -> None:
        script_info = self._running_script_info or {}
        script_name = script_info.get("name", "unknown")
        exit_code = message.exit_code
        result = _classify_exit_code(exit_code)
        temp_path = self._running_temp_path
        dev_mode = self._running_dev_mode
        is_batch = bool(script_info.get("is_batch"))

        if not dev_mode:
            # Synthetic batch items are not LinuxToys scripts: no registry.
            if result is ScriptResult.SUCCESS and not is_batch:
                _save_script_to_registry(script_name, TRANSMAP_PATH)
                _cleanup_tmp_noram_dirs(TRANSMAP_PATH)
            self._remove_transmap()
        self._cleanup_temp_file(temp_path, dev_mode)

        if result is ScriptResult.TERMINAL_CLOSED:
            self.notify(
                "The terminal closed unexpectedly; a new session was started "
                "automatically.",
                severity="warning",
            )

        if self._manifest_bootstrap is not None:
            self._after_manifest_bootstrap(result, exit_code)
            return
        self._advance_manifest(script_name, exit_code, is_batch)

    @staticmethod
    def _manifest_status(result) -> str:
        if result is ScriptResult.SUCCESS:
            return "success"
        if result is ScriptResult.CANCELLED:
            return "cancelled"
        if result is ScriptResult.TERMINAL_CLOSED:
            return "closed"
        return "error"

    def _advance_manifest(
        self, script_name: str, exit_code: int | None, is_batch: bool = False
    ) -> None:
        """Record a result, then decide how the queue goes on.

        Like the CLI: only a failed *script* asks whether to continue, while
        failed package/snap/flatpak batches just move on. Cancellation and a
        closed terminal stop the whole run.
        """
        result = _classify_exit_code(exit_code)
        self._manifest_results.append(
            {
                "name": script_name,
                "exit_code": exit_code,
                "success": result is ScriptResult.SUCCESS,
                "status": self._manifest_status(result),
            }
        )

        if result in (ScriptResult.CANCELLED, ScriptResult.TERMINAL_CLOSED):
            self._stop_manifest_run()
            return
        if (
            result is ScriptResult.ERROR
            and not is_batch
            and self._manifest_queue
        ):
            self._ask_continue_after_failure(script_name, exit_code)
            return
        self._run_next_manifest_item()

    def _ask_continue_after_failure(
        self, script_name: str, exit_code: int
    ) -> None:
        remaining = [item["name"] for item in self._manifest_queue]
        self.app.push_screen(
            ManifestPlanDialog(
                f"'{script_name}' falhou (código de saída {exit_code}).",
                ["Continuar com os itens restantes?", "", *remaining],
                confirm_label="Continuar",
                cancel_label="Parar",
            ),
            self._on_manifest_continue_answer,
        )

    def _on_manifest_continue_answer(self, proceed: bool | None) -> None:
        if proceed:
            self._run_next_manifest_item()
            return
        self._stop_manifest_run()

    def _stop_manifest_run(self) -> None:
        not_run = [item["name"] for item in self._manifest_queue]
        self._manifest_queue = []
        self._finish_manifest_run(not_run)

    def _finish_manifest_run(self, not_run: list[str] | None = None) -> None:
        self._hide_terminal()
        results = self._manifest_results
        self._discard_manifest_temp_files()

        self._is_manifest_run = False
        self._manifest_queue = []
        self._manifest_results = []
        self._running_script_info = None
        self._running_temp_path = None
        if self._is_startup:
            self.app.push_screen(SuccessDialog("Script", action="install"))
            self._is_startup = False
        else:
            self.app.push_screen(
                ManifestReportDialog(results, not_run=not_run)
            )

    def _start_manifest_dry_run(self, plan) -> None:
        self.notify("Evaluating items (dry-run)...", timeout=3)
        self.run_worker(
            lambda: self._dry_run_manifest(plan),
            thread=True,
            exclusive=True,
            name="manifest_dry_run",
        )

    def _dry_run_manifest(self, plan) -> None:
        """Same order as a real run; only scripts are actually validated."""
        from app.dev_mode import dry_run_script

        resolve_script_dir()

        results = []
        for label, names in (
            ("Pacotes", plan.packages),
            ("Snaps", plan.snaps),
            ("Flatpaks", plan.flatpaks),
        ):
            if names:
                results.append(
                    {
                        "name": f"{label} ({len(names)})",
                        "exit_code": 0,
                        "success": True,
                        "status": "simulated",
                    }
                )
        for script in plan.scripts:
            results.append(self._dry_run_script_item(script, dry_run_script))
        self.app.call_from_thread(self._finish_manifest_dry_run, results)

    @staticmethod
    def _dry_run_script_item(script: dict, dry_run_script) -> dict:
        """Mirror the CLI: pass when syntax and dependencies are valid."""
        cleanup_path = None
        try:
            target = script
            if script.get("is_repo_entry"):
                target = materialize_repo_script(script)
            elif script.get("appstream_source") == "homebrew":
                from app import homebrew_catalog

                target = homebrew_catalog.materialize_install(script)
                cleanup_path = target["path"]
            outcome = dry_run_script(target["path"])
            ok = bool(
                outcome["syntax_valid"] and outcome["dependencies_valid"]
            )
        except Exception:  # worker boundary: a broken script is a failed item
            ok = False
        finally:
            if cleanup_path:
                try:
                    os.unlink(cleanup_path)
                except OSError:
                    pass
        return {
            "name": script.get("name", "unknown"),
            "exit_code": 0 if ok else 1,
            "success": ok,
            "status": "success" if ok else "error",
        }

    def _finish_manifest_dry_run(self, results: list[dict]) -> None:
        """Show the dry-run report, on the main thread."""
        self.app.push_screen(ManifestReportDialog(results, dry_run=True))

    def _start_manifest_queue(self, items: list[dict]) -> None:
        self._manifest_queue = items
        self._manifest_results = []
        self._is_manifest_run = True
        self._run_next_manifest_item()

    def _run_next_manifest_item(self) -> None:
        if not self._manifest_queue:
            self._finish_manifest_run()
            return
        self._running_button = None
        script_info = self._manifest_queue.pop(0)
        self._execute_script_info(script_info)


class UpdateRunnerMixin:
    """Check for LinuxToys updates and run the installer in the terminal.

    Mixin for the main app class. Flow: ``_trigger_update_check`` starts
    a worker thread, ``_check_for_update`` asks ``UpdateHelper`` for the
    latest release, ``_on_update_checked`` opens ``UpdateAvailableDialog``
    and ``_on_update_decision`` runs the official installer in the
    embedded terminal. When that run ends, the host is expected to call
    ``_finish_update_run``, which restarts the app on success.

    The host must provide ``notify``, ``run_worker``, ``app``,
    ``_show_terminal``, ``_hide_terminal`` and a ``Terminal`` widget with
    id ``#terminal``.

    Attributes:
        _running_is_update: True while the terminal is running the update
            script, so the host can tell it apart from a normal script.
    """

    _running_is_update: bool = False

    def _trigger_update_check(self) -> None:
        """Start the update check in a worker thread."""
        self.notify("LinuxToys Update Checker...")
        self.run_worker(self._check_for_update, thread=True, exclusive=True)

    def _check_for_update(self) -> None:
        """Query the latest release and report back to the main thread."""
        helper = UpdateHelper()
        available = helper._update_available()
        self.app.call_from_thread(self._on_update_checked, helper, available)

    def _on_update_checked(
        self, helper: UpdateHelper, available: bool
    ) -> None:
        """Handle the result of the update check, on the main thread."""
        if not available:
            self.notify("✓ It's already on the latest available version")
            return
        tag = helper._latest_ver.get("tag_name", "")
        body = helper._latest_ver.get("body", "Sem changelog disponível.")
        self.app.push_screen(
            UpdateAvailableDialog(tag, body), callback=self._on_update_decision
        )

    def _on_update_decision(self, wants_update: bool | None) -> None:
        """Run the installer if the user accepted the update."""
        if not wants_update:
            return

        self._running_is_update = True
        self._show_terminal()
        terminal = self.query_one("#terminal", Terminal)
        terminal.run_script(
            ["bash", "-c", "curl -fsSL https://linux.toys/install.sh | bash"]
        )

    def _finish_update_run(self, exit_code: int | None) -> None:
        """Handle the end of the update script."""
        if exit_code == 0:
            self.app.push_screen(
                UpdateCompleteDialog(), callback=self._restart_app
            )
        else:
            self._hide_terminal()
            self.notify("The update failed or was canceled.", severity="error")

    def _restart_app(self, _result: None = None) -> None:
        """Restart the application in place, loading the updated code."""
        import sys

        self.app.exit()
        os.execv(sys.executable, [sys.executable] + sys.argv)
