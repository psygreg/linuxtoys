from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess

from rich.markup import escape
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Label

from app import compat

from .helper import translations

logger = logging.getLogger(__name__)

_MARKER_NAME = "startup-recommendations-dismissed"


def _t(key: str, default: str) -> str:
    return translations.get(key, default)


def _marker_path() -> str:
    return os.path.join(compat.get_linuxtoys_cache_dir(), _MARKER_NAME)


def is_suppressed() -> bool:
    return os.path.isfile(_marker_path())


def suppress() -> None:
    marker = _marker_path()
    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("1\n")
    except OSError as exc:
        logger.warning(
            "Could not save startup recommendation preference: %s", exc
        )


def command_succeeds(command: list[str]) -> bool:
    """Run a command silently and report whether it exited with 0.

    BLOCKING: waits up to 8 s. Use it only as a probe. Never use it to
    run actions, because those must go to the terminal.

    Args:
        command: Argument list to run. Output is discarded.

    Returns:
        True if the exit code is 0. A missing binary, an OS error or a
        timeout return False.
    """
    try:
        return (
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
                check=False,
            ).returncode
            == 0
        )
    except (OSError, subprocess.SubprocessError):
        return False


def _flathub_ready(flatpak: str) -> bool:
    """Return True if a ``flathub`` remote exists in either scope.

    BLOCKING: runs ``flatpak remotes`` for ``--user`` and ``--system``
    (8 s timeout each). A scope that fails is skipped.

    Args:
        flatpak: Path of the ``flatpak`` executable.
    """
    for scope in ("--user", "--system"):
        try:
            result = subprocess.run(
                [flatpak, scope, "remotes", "--columns=name"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0 and "flathub" in {
            line.strip() for line in result.stdout.splitlines()
        }:
            return True
    return False


def detect() -> list[str]:
    """Return the optional setup scripts that are useful on this host."""
    keys = compat.get_system_compat_keys()
    recommendations: list[str] = []

    if (
        not compat.is_containerized()
        and "solus" not in keys
        and "ostree" not in keys
        and "systemd" in keys
    ):
        flatpak = shutil.which("flatpak")
        if not flatpak or not _flathub_ready(flatpak):
            recommendations.append("flathub")

    if "fedora" in keys:
        if not (
            command_succeeds(["rpm", "-q", "rpmfusion-free-release"])
            and command_succeeds(["rpm", "-q", "rpmfusion-nonfree-release"])
        ):
            recommendations.append("rpmfusion")

    if "arch" in keys:
        if not command_succeeds(["pacman", "-Slq", "multilib"]):
            recommendations.append("multilib")

    if keys.intersection({"steamos", "gnomeos", "dakota", "kde-linux"}):
        from app import homebrew_catalog

        if not homebrew_catalog.enabled():
            recommendations.append("brew")

    return recommendations


def _names(scripts: list[dict]) -> str:
    return "\n".join(f"• {escape(s.get('name', '?'))}" for s in scripts)


class StartupRecommendationsDialog(ModalScreen["tuple[bool, bool]"]):
    """Modal that offers the recommended scripts.

    Dismisses with ``(accepted, dont_remind)``. ``accepted`` is True only
    for Install. "Not now" and Escape give False. ``dont_remind`` is the
    checkbox state and is reported in every case. Focus starts on
    "Not now".

    Args:
        scripts: Script info dicts to list (``name`` key).
    """

    DEFAULT_CLASSES = "lt-modal"
    BINDINGS = [Binding("escape", "close", "Not now")]

    def __init__(self, scripts: list[dict]) -> None:
        super().__init__()
        self._scripts = scripts

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(
                _t(
                    "startup_recommendations_title",
                    "Recommended for your system",
                ),
                classes="dialog-title",
            )
            yield Label(
                _t(
                    "startup_recommendations_msg",
                    "We detected features that may improve your setup:",
                ),
                classes="dialog-text",
            )
            with VerticalScroll():
                yield Label(_names(self._scripts))
            yield Checkbox(
                _t(
                    "startup_recommendations_dont_remind",
                    "Don't remind me again",
                ),
                id="dont_remind",
            )
            with Horizontal():
                yield Button(
                    _t("startup_recommendations_skip", "Not now"), id="skip"
                )
                yield Button(
                    _t("skills_install_label", "Install"),
                    id="accept",
                    variant="success",
                )

    def on_mount(self) -> None:
        self.query_one("#skip", Button).focus()

    def _finish(self, accepted: bool) -> None:
        self.dismiss(
            (accepted, self.query_one("#dont_remind", Checkbox).value)
        )

    @on(Button.Pressed)
    def _pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self._finish(event.button.id == "accept")

    def action_close(self) -> None:
        self._finish(False)


class NeededRequirementsDialog(ModalScreen[bool]):
    """Modal that asks to confirm the dependencies of a script.

    Dismisses with True on Install, and False on Cancel or Escape. Focus
    starts on Install.

    Args:
        script_name: Name of the script that needs them. Shown escaped.
        required: Script info dicts of the dependencies (``name`` key).
    """

    DEFAULT_CLASSES = "lt-modal"
    BINDINGS = [Binding("escape", "close", "Cancel")]

    def __init__(self, script_name: str, required: list[dict]) -> None:
        super().__init__()
        self._script_name = script_name
        self._required = required

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(
                _t("needed_requirements_title", "Required features"),
                classes="dialog-title",
            )
            yield Label(
                _t("needed_requirements_msg", "{name} requires:").format(
                    name=escape(self._script_name)
                ),
                classes="dialog-text",
            )
            with VerticalScroll():
                yield Label(_names(self._required))
            with Horizontal():
                yield Button(_t("skills_back_label", "Cancel"), id="cancel")
                yield Button(
                    _t("skills_install_label", "Install"),
                    id="accept",
                    variant="success",
                )

    def on_mount(self) -> None:
        self.query_one("#accept", Button).focus()

    @on(Button.Pressed)
    def _pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "accept")

    def action_close(self) -> None:
        self.dismiss(False)


class StartupRecommendationsMixin:
    """Mixin that detects, asks and installs startup recommendations.

    For the main app class. Flow: detect, resolve the scripts, ask,
    add the ``needed`` dependencies and run everything through the
    manifest queue.

    The host must provide: ``_is_manifest_run``, ``_ensure_terminal_free()``,
    ``is_skills_seeker_showing``, ``_close_skills_seeker()``,
    ``_manifest_temp_files``, ``_discard_manifest_temp_files()``,
    ``_prepare_queue_script(item)`` and ``_start_manifest_queue(items)``,
    plus the Textual ``app`` and ``notify``.

    Attributes:
        _startup_checked: True once the check has been started. It
            guarantees a single run.
        _is_startup: True once the startup queue has been launched.
    """

    _startup_checked = False
    _is_startup = False

    def check_startup_recommendations(self) -> None:
        """Start the recommendation check, at most once."""
        if self._startup_checked:
            return
        self._startup_checked = True
        self._startup_recommendations_worker()

    @work(exclusive=True, group="startup-recommendations")
    async def _startup_recommendations_worker(self) -> None:
        """Run the whole recommendation flow."""
        try:
            if await asyncio.to_thread(is_suppressed):
                return
            script_ids = await asyncio.to_thread(detect)
            if not script_ids:
                return

            scripts = await self._resolve_scripts(script_ids)
            if not scripts:
                return

            accepted, dont_remind = await self.app.push_screen_wait(
                StartupRecommendationsDialog(scripts)
            )
            if dont_remind:
                await asyncio.to_thread(suppress)
            if not accepted:
                return

            queue = await self._build_startup_queue(scripts)
            if queue:
                await self._launch_startup_queue(queue)
        except Exception:  # noqa: BLE001
            logger.exception("startup recommendations failed")

    async def _resolve_scripts(self, script_ids: list[str]) -> list[dict]:
        """Resolve script names into script info dicts."""
        from app.manifest_helper import find_script_by_name_async

        found = await asyncio.gather(
            *(find_script_by_name_async(s, translations) for s in script_ids)
        )
        scripts = [s for s in found if s]
        if len(scripts) != len(script_ids):
            logger.warning(
                "Could not resolve %d startup recommendation(s)",
                len(script_ids) - len(scripts),
            )
        return scripts

    async def _build_startup_queue(self, scripts: list[dict]) -> list[dict]:
        """Build the run queue, with dependencies before each script.

        Dependencies come from the ``needed`` key and are looked up
        concurrently. Those not already queued are confirmed in
        ``NeededRequirementsDialog``. Items are de-duplicated by name.
        Equivalent to the GUI's ``_process_needed_scripts``. Repository
        entries are materialized later, by ``_execute_script_info``.

        Args:
            scripts: Resolved recommendation scripts.

        Returns:
            The ordered queue, or an empty list if the user declines any
            dependency prompt (nothing runs then).
        """
        from app.manifest_helper import find_script_by_name_async

        queue: list[dict] = []
        queued: set[str] = set()

        def add(item: dict) -> None:
            name = item.get("name", "")
            if name in queued:
                return
            queued.add(name)
            queue.append(item)

        for info in scripts:
            required: list[dict] = []
            if needed := info.get("needed"):
                found = await asyncio.gather(
                    *(
                        find_script_by_name_async(n, translations)
                        for n in needed
                    )
                )
                required = [
                    r for r in found if r and r.get("name", "") not in queued
                ]
                if required:
                    confirmed = await self.app.push_screen_wait(
                        NeededRequirementsDialog(
                            info.get("name", "Script"), required
                        )
                    )
                    if not confirmed:
                        return []

            for item in (*required, info):
                add(item)
        return queue

    async def _launch_startup_queue(self, queue: list[dict]) -> None:
        """Prepare the queue scripts and start the manifest runner."""
        if self._is_manifest_run or not self._ensure_terminal_free():
            return
        if self.is_skills_seeker_showing:
            await self._close_skills_seeker()

        self._manifest_temp_files = []
        try:
            prepared = [self._prepare_queue_script(item) for item in queue]
        except (OSError, ValueError) as exc:
            self._discard_manifest_temp_files()
            self.notify(
                f"Não foi possível preparar a execução: {exc}",
                severity="error",
            )
            return
        self._is_startup = True
        self._start_manifest_queue(prepared)
