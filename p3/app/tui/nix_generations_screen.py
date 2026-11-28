"""Textual dialog for managing Home Manager and NixOS generations."""

from __future__ import annotations

import threading

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static

from app import nix_generations

from .helper import make_widget_id, translations


class NixGenerationsScreen(ModalScreen[dict | None]):
    """List recorded generations and return the chosen action to the host."""

    CSS = """
    NixGenerationsScreen {
        align: center middle;
    }
    #nix-generations-dialog {
        width: 92%;
        height: 88%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }
    #nix-generations-intro {
        height: auto;
        margin-top: 1;
    }
    #nix-generations-scope {
        margin-top: 1;
    }
    #nix-generations-status {
        height: auto;
        margin-top: 1;
    }
    #nix-generations-list {
        height: 1fr;
        margin-top: 1;
        border: round $primary;
    }
    #nix-generations-list Static {
        height: auto;
    }
    .nix-generation-row {
        height: auto;
    }
    .nix-generation-row Static {
        width: 1fr;
        height: auto;
    }
    .nix-generation-row Button {
        width: auto;
        height: 1;
        min-width: 10;
        margin-left: 1;
    }
    #nix-generations-actions {
        height: auto;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding(
            "escape",
            "cancel",
            translations.get("script_runner_close", "Close"),
        )
    ]

    def __init__(self) -> None:
        super().__init__()
        self._data: dict[str, dict] = {}
        self._action_widgets: dict[str, tuple[str, str, int]] = {}
        self._load_running = False
        self._load_token = 0
        self._render_token = 0
        self._dismissed = False

    def compose(self) -> ComposeResult:
        with Vertical(id="nix-generations-dialog"):
            yield Label(
                translations.get("nix_generations_title", "Nix generations")
            )
            yield Static(
                translations.get(
                    "nix_generations_intro",
                    "Manage the recorded Home Manager and NixOS system "
                    "generations. Activating an older generation rolls back "
                    "to it; deleting removes the generation record.",
                ),
                id="nix-generations-intro",
                markup=False,
            )
            yield Select(
                [],
                id="nix-generations-scope",
                allow_blank=True,
            )
            yield Static("", id="nix-generations-status", markup=False)
            with VerticalScroll(id="nix-generations-list"):
                yield Static("")
            with Horizontal(id="nix-generations-actions"):
                yield Button(
                    translations.get("nix_generations_refresh", "Refresh"),
                    id="nix-generations-refresh",
                )
                yield Button(
                    translations.get("script_runner_close", "Close"),
                    id="nix-generations-close",
                    variant="primary",
                )

    def on_mount(self) -> None:
        self.query_one("#nix-generations-status", Static).display = False
        self.run_worker(
            self._refresh(), group="nix-generations-load", exclusive=True
        )

    def _status(self, text: str) -> None:
        try:
            widget = self.query_one("#nix-generations-status", Static)
        except Exception:
            return
        widget.update(text)
        widget.display = bool(text)

    def _scope_name(self, scope: str) -> str:
        if scope == nix_generations.HOME_SCOPE:
            return translations.get("nix_generations_home", "Home Manager")
        return translations.get("nix_generations_system", "NixOS system")

    async def _refresh(self) -> None:
        if self._load_running or self._dismissed:
            return
        self._load_running = True
        self._load_token += 1
        token = self._load_token
        # Invalidate a render that may still be mounting rows.
        self._render_token += 1
        self.query_one("#nix-generations-refresh", Button).disabled = True
        self._status(
            translations.get("nix_generations_loading", "Loading generations…")
        )
        await self._clear_list()
        if self._dismissed or token != self._load_token:
            self._load_running = False
            return

        def worker():
            try:
                data = nix_generations.scan()
            except Exception as error:  # surface the exact read failure
                data = {"__error__": str(error)}
            self._notify_thread(self._loaded, token, data)

        threading.Thread(
            target=worker,
            daemon=True,
            name="linuxtoys-tui-nix-generations",
        ).start()

    def _notify_thread(self, callback, *args) -> None:
        if self._dismissed:
            return
        try:
            self.app.call_from_thread(callback, *args)
        except Exception:
            # The app or this modal screen may already be gone.
            pass

    def _loaded(self, token: int, data: dict) -> None:
        if self._dismissed or token != self._load_token:
            return
        self._load_running = False
        self.query_one("#nix-generations-refresh", Button).disabled = False
        self._data = data or {}
        scopes = [
            scope
            for scope in (
                nix_generations.HOME_SCOPE,
                nix_generations.SYSTEM_SCOPE,
            )
            if scope in self._data
        ]
        select = self.query_one("#nix-generations-scope", Select)
        previous = select.value if isinstance(select.value, str) else ""
        values = [(self._scope_name(scope), scope) for scope in scopes]
        select.set_options(values)
        select.disabled = not values
        if values:
            select.value = previous if previous in scopes else scopes[0]
            self.run_worker(
                self._render_scope(),
                group="nix-generations-render",
            )
            return
        global_error = str(self._data.get("__error__") or "")
        if global_error:
            self._status(
                translations.get(
                    "nix_generations_load_failed",
                    "Could not read Nix generations: {error}",
                ).format(error=global_error)
            )
        else:
            self._status(
                translations.get(
                    "nix_generations_empty", "No generations found."
                )
            )

    async def _clear_list(self) -> None:
        try:
            container = self.query_one(
                "#nix-generations-list", VerticalScroll
            )
        except Exception:
            return
        try:
            await container.remove_children()
        except Exception:
            # The screen may have been dismissed while the removal ran.
            pass

    def _current_scope(self) -> str:
        try:
            select = self.query_one("#nix-generations-scope", Select)
        except Exception:
            return ""
        value = select.value
        return value if isinstance(value, str) else ""

    async def _render_scope(self) -> None:
        self._render_token += 1
        token = self._render_token
        await self._clear_list()
        if (
            self._dismissed
            or token != self._render_token
        ):
            return
        self._action_widgets = {}
        scope = self._current_scope()
        if not scope:
            self._status(
                translations.get(
                    "nix_generations_empty", "No generations found."
                )
            )
            return
        entry = self._data.get(scope) or {}
        error = str(entry.get("error") or "")
        if error:
            self._status(
                translations.get(
                    "nix_generations_load_failed",
                    "Could not read Nix generations: {error}",
                ).format(error=error)
            )
            return
        generations = entry.get("generations") or []
        if not generations:
            self._status(
                translations.get(
                    "nix_generations_empty", "No generations found."
                )
            )
            return

        self._status("")
        container = self.query_one("#nix-generations-list", VerticalScroll)
        for record in generations:
            if self._dismissed or token != self._render_token:
                return
            generation = int(record.get("id") or 0)
            if generation <= 0:
                continue
            current = bool(record.get("current"))
            date_text = str(record.get("date") or "")
            if current:
                date_text = (
                    date_text
                    + "  ("
                    + translations.get("nix_generations_current", "Current")
                    + ")"
                )
            label = translations.get(
                "nix_generations_generation", "Generation {generation}"
            ).format(generation=generation)
            text = f"{label}  {date_text}".rstrip()

            row = Horizontal(classes="nix-generation-row")
            activate_id = make_widget_id(
                f"nix-gen-activate-{scope}-{generation}"
            )
            delete_id = make_widget_id(f"nix-gen-delete-{scope}-{generation}")
            self._action_widgets[activate_id] = (
                "activate",
                scope,
                generation,
            )
            self._action_widgets[delete_id] = ("delete", scope, generation)
            container.mount(row)
            row.mount(
                Static(text, markup=False),
                Button(
                    translations.get("nix_generations_activate", "Activate"),
                    id=activate_id,
                    variant="success",
                    disabled=current,
                ),
                Button(
                    translations.get("nix_generations_delete", "Delete"),
                    id=delete_id,
                    variant="error",
                    disabled=current,
                ),
            )

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "nix-generations-scope":
            await self._render_scope()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button_id = event.button.id or ""
        if button_id == "nix-generations-refresh":
            await self._refresh()
            return
        if button_id == "nix-generations-close":
            self.action_cancel()
            return
        action = self._action_widgets.get(button_id)
        if action is None:
            return
        action_name, scope, generation = action
        self._dismissed = True
        self.dismiss(
            {
                "action": action_name,
                "scope": scope,
                "generation": generation,
            }
        )

    def action_cancel(self) -> None:
        self._dismissed = True
        self.dismiss(None)

    def on_unmount(self) -> None:
        self._dismissed = True
