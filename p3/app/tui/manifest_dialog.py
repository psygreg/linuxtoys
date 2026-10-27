"""Modal screens for running a manifest in the TUI.

``ManifestDialog`` picks a manifest file, ``ManifestPlanDialog`` shows
the resolved plan and asks for confirmation, and ``ManifestReportDialog``
summarizes the result of a run.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Button, DirectoryTree, Footer, Input, Static

from .helper import translations


class FilteredDirectoryTree(DirectoryTree):
    """Directory tree that shows only manifest candidates.

    Lists directories and ``.txt`` files, hides dotfiles and common
    noise directories (``node_modules``, ``__pycache__``, ``.venv``,
    ``venv``, ``.git``), and filters by ``search_query``.

    Attributes:
        search_query: Text to filter by. Empty shows everything allowed.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.search_query: str = ""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        _IGNORED_DIRS = {
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            ".git",
        }
        paths = [
            p
            for p in paths
            if not p.name.startswith(".")
            and p.name not in _IGNORED_DIRS
            and (p.is_dir() or p.name.lower().endswith(".txt"))
        ]
        query = self.search_query.strip().lower()
        if not query:
            return [
                p
                for p in paths
                if p.is_file() or self._dir_contains_match(p, "")
            ]
        return [p for p in paths if self._matches(p, query)]

    def _matches(self, path: Path, query: str) -> bool:
        if query in path.name.lower():
            return True
        return path.is_dir() and self._dir_contains_match(path, query)

    def _dir_contains_match(
        self, directory: Path, query: str, max_depth: int = 3
    ) -> bool:
        """Checa recursivamente (com limite de profundidade, por
        segurança/performance) se algo dentro de `directory` bate com
        a busca."""
        if max_depth <= 0:
            return False
        try:
            entries = directory.iterdir()
        except (PermissionError, OSError):
            return False
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if query in entry.name.lower():
                return True
            if entry.is_dir() and self._dir_contains_match(
                entry, query, max_depth - 1
            ):
                return True
        return False


class ManifestDialog(ModalScreen[str | None]):
    """Modal file picker for a manifest (``.txt``) file.

    Shows the home directory in a filterable tree with a search box,
    debounced by 0.3 s. The Select button is enabled only while a
    ``.txt`` file is selected. Dismisses with the file path, or None on
    cancel or Escape.

    Attributes:
        selected_path: Path of the last selected ``.txt`` file. It only
            exists after a file has been chosen.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="manifest-container"):
            with Horizontal(id="manifest-header"):
                yield Button(
                    translations.get("cancel_btn_label", "Cancelar"),
                    id="cancel-btn-manifest",
                    variant="error",
                )
                yield Static(
                    translations.get(
                        "choose_manifest_title",
                        "Por favor, escolha seu Manifest",
                    ),
                    id="manifest-title",
                )
                yield Input(
                    placeholder=translations.get("search", "Search"),
                    id="manifest-search",
                )
                yield Button(
                    translations.get("select_button", "Selecionar"),
                    id="execute-btn-manifest",
                    variant="primary",
                    disabled=True,
                )

            yield FilteredDirectoryTree(
                Path("~").expanduser(), id="manifest-tree"
            )
        yield Footer()

    def on_mount(self):
        self._search_timer: Timer | None = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "cancel-btn-manifest":
            self.dismiss(None)
        elif event.button.id == "execute-btn-manifest":
            self.dismiss(getattr(self, "selected_path", None))

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "manifest-search":
            return
        query = event.value
        if self._search_timer is not None:
            self._search_timer.stop()
        self._search_timer = self.set_timer(
            0.3, lambda: self._apply_search(query)
        )

    def _apply_search(self, query: str) -> None:
        tree = self.query_one("#manifest-tree", FilteredDirectoryTree)
        tree.search_query = query
        tree.reload()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        if event.path.is_file() and event.path.suffix.lower() == ".txt":
            self.selected_path = str(event.path)
            self.query_one("#execute-btn-manifest", Button).disabled = False
        else:
            self.query_one("#execute-btn-manifest", Button).disabled = True

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self.query_one("#execute-btn-manifest", Button).disabled = True


class ManifestReportDialog(ModalScreen[None]):
    """Modal that summarizes the result of a manifest run.

    Shows the ``ok/total`` count and, when they exist, three sections:
    failed items with the reason, simulated items (dry-run) and items
    that did not run. Dismisses with None when OK is pressed.

    Args:
        results: Result dicts with ``name``, ``success``, ``status``
            (optional: ``"cancelled"``, ``"closed"`` or
            ``"simulated"``) and ``exit_code``.
        dry_run: True if the run was only a validation.
        not_run: Names of items that never started.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def __init__(
        self,
        results: list[dict],
        *,
        dry_run: bool = False,
        not_run: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.results = results
        self.dry_run = dry_run
        self.not_run = not_run or []

    @staticmethod
    def _describe(item: dict, dry_run: bool) -> str:
        status = item.get("status")
        if status == "cancelled":
            return "cancelado"
        if status == "closed":
            return "terminal encerrado"
        if dry_run:
            return "validação falhou"
        return f"código de saída: {item['exit_code']}"

    def compose(self) -> ComposeResult:
        total = len(self.results)
        ok = sum(1 for item in self.results if item["success"])
        failures = [item for item in self.results if not item["success"]]
        simulated = [
            item for item in self.results if item.get("status") == "simulated"
        ]

        sections: list[tuple[str, list[str]]] = []
        if failures:
            sections.append(
                (
                    "Itens com erro:",
                    [
                        f"• {item['name']} — "
                        f"{self._describe(item, self.dry_run)}"
                        for item in failures
                    ],
                )
            )
        if simulated:
            sections.append(
                (
                    "Simulados (não executados):",
                    [f"• {item['name']}" for item in simulated],
                )
            )
        if self.not_run:
            sections.append(
                ("Não executados:", [f"• {name}" for name in self.not_run])
            )

        with Vertical(id="confirm-dialog"):
            if self.dry_run:
                yield Static(
                    f"Dry-run concluído: {ok}/{total} itens sem problemas."
                )
            else:
                yield Static(
                    f"Manifesto concluído: {ok}/{total} "
                    "instalados com sucesso."
                )
            if sections:
                with VerticalScroll(id="manifest-failures"):
                    for title, lines in sections:
                        yield Static(title, classes="field-label")
                        for line in lines:
                            # Text() avoids Rich markup parsing of item names.
                            yield Static(Text(line))
            with Horizontal(id="confirm-buttons"):
                yield Button("OK", id="execute-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "execute-btn":
            self.dismiss()


class ManifestPlanDialog(ModalScreen[bool]):
    """Show a heading and a list of lines.

    Dismisses with ``True`` when the confirm button is pressed and ``False``
    otherwise (cancel button or Escape). Without ``confirm_label`` it acts as
    a plain information dialog. Focus starts on the cancel button, matching
    the ``[y/N]`` default of the CLI.
    """

    _MAX_BODY_ROWS = 10
    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def __init__(
        self,
        heading: str,
        lines: list[str],
        *,
        confirm_label: str | None = None,
        cancel_label: str = "Cancelar",
    ) -> None:
        super().__init__()
        self._heading = heading
        self._lines = lines
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(Text(self._heading), classes="field-label")
            with VerticalScroll(id="manifest-failures"):
                # Text() avoids Rich markup parsing of "[SCRIPT]" and friends.
                yield Static(Text("\n".join(self._lines)))
            with Horizontal(id="confirm-buttons"):
                if self._confirm_label:
                    yield Button(
                        self._confirm_label,
                        id="execute-btn",
                        variant="primary",
                    )
                yield Button(self._cancel_label, id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#confirm-dialog").styles.height = "auto"
        self.query_one("#confirm-buttons").styles.height = "auto"
        body = self.query_one("#manifest-failures")
        body.styles.height = "auto"
        body.styles.max_height = self._MAX_BODY_ROWS
        self.query_one("#cancel-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "execute-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)
