"""Textual dialog for importing a Nix flake."""

from __future__ import annotations

import threading

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

from app import nix_flakes

from .helper import translations


class NixFlakeScreen(ModalScreen[dict | None]):
    """Inspect a flake, choose its scope/outputs and return the selection."""

    CSS = """
    NixFlakeScreen {
        align: center middle;
    }
    #nix-flake-dialog {
        width: 92%;
        height: 92%;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }
    #nix-flake-options {
        height: 1fr;
        margin-top: 1;
        border: round $primary;
    }
    #nix-flake-actions {
        height: auto;
    }
    #nix-flake-imports {
        height: auto;
        max-height: 8;
        margin-top: 1;
        border: round $primary;
    }
    .nix-flake-import-row {
        height: auto;
    }
    .nix-flake-import-row Static {
        width: 1fr;
        height: auto;
    }
    .nix-flake-import-row Button {
        width: auto;
        height: 1;
        min-width: 10;
    }
    #nix-flake-status, #nix-flake-description, #nix-flake-warning {
        margin-top: 1;
        height: auto;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close", "Close"))
    ]

    def __init__(self) -> None:
        super().__init__()
        self.info = None
        self._option_widgets = {}
        self._remove_widgets = {}
        self._inspect_running = False
        self._dismissed = False

    def compose(self) -> ComposeResult:
        with Vertical(id="nix-flake-dialog"):
            yield Label(
                translations.get(
                    "nix_flake_import_title", "Import Nix flake"
                )
            )
            yield Static(
                translations.get(
                    "nix_flake_import_warning",
                    "Only import flakes you trust: their modules, packages "
                    "and overlays become part of your configuration.",
                ),
                id="nix-flake-warning",
                markup=False,
            )
            yield Input(
                placeholder=translations.get(
                    "nix_flake_reference_placeholder",
                    "github:owner/repo, git+https://… or /path/to/flake",
                ),
                id="nix-flake-reference",
            )
            with Horizontal(id="nix-flake-actions"):
                yield Button(
                    translations.get("nix_flake_read", "Read flake"),
                    id="nix-flake-read",
                )
                yield Button(
                    translations.get("nix_flake_import", "Import"),
                    id="nix-flake-import",
                    variant="success",
                    disabled=True,
                )
            yield Select(
                [],
                prompt=translations.get("nix_flake_scope", "Install for"),
                id="nix-flake-scope",
                allow_blank=True,
            )
            yield Static("", id="nix-flake-status", markup=False)
            yield Static("", id="nix-flake-description", markup=False)
            with VerticalScroll(id="nix-flake-options"):
                yield Static("")
            yield Label(
                translations.get("nix_flake_existing", "Imported flakes"),
                id="nix-flake-imports-label",
            )
            with VerticalScroll(id="nix-flake-imports"):
                yield Static("")

    def on_mount(self) -> None:
        self.query_one("#nix-flake-import", Button).disabled = True
        self._refresh_imports()

    def _status(self, text: str) -> None:
        try:
            self.query_one("#nix-flake-status", Static).update(text)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button_id = event.button.id or ""
        if button_id == "nix-flake-read":
            self._inspect()
        elif button_id == "nix-flake-import":
            self._submit()
        elif button_id.startswith("nix-flake-remove-"):
            record = self._remove_widgets.get(button_id)
            if record is not None:
                self._dismissed = True
                self.dismiss(
                    {"action": "remove", "record": record}
                )

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "nix-flake-scope":
            self._sync_scope()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id and event.checkbox.id.startswith("nix-flake-option-"):
            self._update_import_button()

    def _inspect(self) -> None:
        if self._inspect_running:
            return
        reference = self.query_one("#nix-flake-reference", Input).value.strip()
        if not reference:
            self._status(
                translations.get(
                    "nix_flake_reference_required", "Enter a flake reference."
                )
            )
            return
        self._inspect_running = True
        self.query_one("#nix-flake-read", Button).disabled = True
        self.query_one("#nix-flake-import", Button).disabled = True
        self._status(
            translations.get("nix_flake_reading", "Inspecting the flake…")
        )

        def worker():
            try:
                info = nix_flakes.inspect(reference)
            except Exception as error:
                self._notify_thread(self._failed, str(error))
            else:
                self._notify_thread(self._loaded, info)

        threading.Thread(
            target=worker, daemon=True, name="linuxtoys-tui-flake-inspect"
        ).start()

    def _notify_thread(self, callback, value) -> None:
        if self._dismissed:
            return
        try:
            self.app.call_from_thread(callback, value)
        except Exception:
            # The app or this modal screen may already be gone.
            pass

    def _failed(self, message: str) -> None:
        if self._dismissed:
            return
        self._inspect_running = False
        self.query_one("#nix-flake-read", Button).disabled = False
        self.info = None
        self._option_widgets = {}
        self._clear_options()
        self.query_one("#nix-flake-description", Static).update("")
        self.query_one("#nix-flake-scope", Select).set_options([])
        self._status(message)

    def _loaded(self, info: dict) -> None:
        if self._dismissed:
            return
        self._inspect_running = False
        self.query_one("#nix-flake-read", Button).disabled = False
        self.info = info
        self._status("")
        self.query_one("#nix-flake-description", Static).update(
            str(info.get("description") or "")
        )
        scope = self.query_one("#nix-flake-scope", Select)
        values = []
        if info.get("home_manager"):
            values.append(
                (
                    translations.get("nix_flake_scope_home", "Home Manager"),
                    "home-manager",
                )
            )
        if info.get("system_scope"):
            values.append(
                (
                    translations.get("nix_flake_scope_system", "System (NixOS)"),
                    "system",
                )
            )
        scope.set_options(values)
        if values:
            scope.value = values[0][1]
        self._build_options()
        self._sync_scope()
        self._refresh_imports()
        if not values:
            self._status(
                translations.get(
                    "nix_flake_no_scope",
                    "Neither Home Manager nor a NixOS system configuration is available.",
                )
            )
        elif not any(
            option.get("selectable")
            for option in info.get("options") or ()
        ):
            self._status(
                translations.get(
                    "nix_flake_no_outputs",
                    "This flake has no outputs LinuxToys can merge into a Nix configuration.",
                )
            )

    def _build_options(self) -> None:
        container = self.query_one("#nix-flake-options", VerticalScroll)
        self._clear_options()
        self._option_widgets = {}
        groups = []
        for option in (self.info or {}).get("options") or ():
            group = str(option.get("group") or "")
            if group and group not in groups:
                groups.append(group)
        for group in groups:
            container.mount(Label(group, markup=False))
            for option in (self.info or {}).get("options") or ():
                if str(option.get("group") or "") != group:
                    continue
                key = str(option.get("key") or "")
                widget = Checkbox(
                    str(option.get("label") or ""),
                    value=nix_flakes.default_selected(option),
                    disabled=not bool(option.get("selectable")),
                    id=f"nix-flake-option-{len(self._option_widgets)}",
                )
                self._option_widgets[key] = widget
                container.mount(widget)

    def _clear_options(self) -> None:
        container = self.query_one("#nix-flake-options", VerticalScroll)
        for child in list(container.children):
            child.remove()

    def _refresh_imports(self) -> None:
        container = self.query_one("#nix-flake-imports", VerticalScroll)
        try:
            records = nix_flakes.imports()
        except Exception:
            records = []
        for child in list(container.children):
            child.remove()
        container.mount(
            Static(
                translations.get("nix_flake_none_imported", "None yet."),
                markup=False,
            )
            if not records
            else Static("")
        )
        self._remove_widgets = {}
        for index, record in enumerate(records):
            button_id = f"nix-flake-remove-{index}"
            self._remove_widgets[button_id] = record
            row = Horizontal(classes="nix-flake-import-row")
            container.mount(row)
            description = (
                record.get("description") or record.get("reference") or ""
            )
            row.mount(
                Static(
                    f"{description} ({record.get('scope')})",
                    markup=False,
                )
            )
            row.mount(
                Button(
                    translations.get("nix_flake_remove", "Remove"),
                    id=button_id,
                    variant="error",
                )
            )

    def _scope(self) -> str:
        value = self.query_one("#nix-flake-scope", Select).value
        return value if isinstance(value, str) else ""

    def _selected_keys(self) -> list[str]:
        scope = self._scope()
        selected = []
        for option in (self.info or {}).get("options") or ():
            key = str(option.get("key") or "")
            widget = self._option_widgets.get(key)
            if widget is None or not widget.value or widget.disabled:
                continue
            option_scope = str(option.get("scope") or "both")
            if option_scope in ("both", scope):
                selected.append(key)
        return selected

    def _sync_scope(self) -> None:
        scope = self._scope()
        for option in (self.info or {}).get("options") or ():
            key = str(option.get("key") or "")
            widget = self._option_widgets.get(key)
            if widget is None or not option.get("selectable"):
                continue
            option_scope = str(option.get("scope") or "both")
            widget.disabled = option_scope not in ("both", scope)
        self._update_import_button()

    def _update_import_button(self) -> None:
        self.query_one("#nix-flake-import", Button).disabled = not (
            self._scope() and self._selected_keys()
        )

    def _submit(self) -> None:
        if not self.info:
            return
        scope = self._scope()
        keys = self._selected_keys()
        if not scope or not keys:
            self._status(
                translations.get(
                    "nix_flake_select_output",
                    "Select at least one output to import.",
                )
            )
            return
        self._dismissed = True
        self.dismiss(
            {
                "action": "import",
                "info": self.info,
                "scope": scope,
                "keys": keys,
            }
        )

    def action_cancel(self) -> None:
        self._dismissed = True
        self.dismiss(None)

    def on_unmount(self) -> None:
        self._dismissed = True
