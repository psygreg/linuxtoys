from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Link,
    ListView,
    Static,
)

from app.action_registry import (
    _find_backup_files_for_script,
    _remove_backup_files,
    _remove_script_from_registry,
)
from app.manifest_helper import export_registered_manifest
from app.registry_utils import parse_registry_file, search_registry_entries

from .dialog_screen import ConfirmCleanupDialog
from .helper import translations
from .my_widgets import FocusableLabel, RegistryListItem


class RegistryScreen(Screen):
    BINDINGS = [
        Binding(
            "escape", "close_registry", translations.get("script_runner_close")
        ),
        Binding("e", "export_registry", translations.get("export", "Export")),
        Binding(
            "c",
            "cleanup_registry",
            translations.get("registry_cleanup_label", "Cleanup"),
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.registry_data = parse_registry_file()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="left-column"):
                yield Input(
                    placeholder=translations.get("search", "Search"),
                    id="search-registry",
                )
                with Vertical(id="left-panel"):
                    script_name = sorted(self.registry_data.keys())
                    yield ListView(
                        *[RegistryListItem(name) for name in script_name],
                        id="registry-list",
                    )
            with Vertical(id="right-panel"):
                yield Static(
                    "Selecione um script à esquerda para ver os detalhes"
                    if self.registry_data
                    else "Nenhum script foi executado ainda.",
                    id="registry-details",
                )
        with Horizontal(classes="home-links"):
            yield Link("Wiki", url="https://linux.toys/documentation.html")
            yield Static("│", classes="link-sep")
            yield FocusableLabel(
                f"[u]{translations.get('report_label', 'Report Bug')}[/u]",
                id="report-bug",
                classes="report-bug",
            )
            yield Static("│", classes="link-sep")
            yield Link(
                f"{translations.get('devportal_label', 'Credits')}",
                url="https://dev.linux.toys",
            )
            yield Static("│", classes="link-sep")
            yield Link(
                f"{translations.get('support_footer', 'Support this project')}",
                url="https://ko-fi.com/psygreg",
            )
        yield Footer(show_command_palette=False)

    def on_mount(self) -> None:
        self.query_one("#left-panel").border_title = translations.get(
            "scripts_label"
        )
        self.query_one("#right-panel").border_title = translations.get(
            "registry_details_label"
        )

        list_view = self.query_one("#registry-list", ListView)
        list_view.focus()
        if self.registry_data:
            list_view.index = 0
            first_item = list_view.query(RegistryListItem).first()
            self._display_script_details(first_item.script_name)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        item = event.item
        if isinstance(item, RegistryListItem):
            self._display_script_details(item.script_name)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-registry":
            return
        await self._filter_history(event.value)

    async def _filter_history(self, query: str) -> None:
        """Rebuild the list with the scripts that match ``query``.

        Selects the first match and shows its details, or a "not
        found" message when nothing matches.

        Args:
            query: Text typed in the search box.
        """
        filtered_data = search_registry_entries(self.registry_data, query)
        filtered_names = sorted(filtered_data.keys())
        list_view = self.query_one("#registry-list", ListView)
        await list_view.clear()
        await list_view.extend(RegistryListItem(n) for n in filtered_names)
        # for name in filtered_names:
        #     await list_view.append(RegistryListItem(name))
        details = self.query_one("#registry-details", Static)
        if filtered_names:
            list_view.index = 0
            self._display_script_details(filtered_names[0])
        else:
            details.update("No script found.")  # criar tradução

    def _display_script_details(self, script_name: str) -> None:
        """Render the executions of a script in the details panel.

        For each execution it shows the timestamp (when available) and
        the list of operations, or a "none" line when there are none.

        Args:
            script_name: Registry key of the script to display.
        """
        executions = self.registry_data.get(script_name, [])
        lines = [f"Script: {script_name}\n", "=" * 60 + "\n\n"]

        for idx, (timestamp, operations) in enumerate(executions, 1):
            lines.append(f"Timestamp: {idx}\n")
            if timestamp:
                lines.append(f"Timestamp: {timestamp}\n")
            lines.append("\n")
            if operations:
                lines.append("Operações:\n")
                for op in operations:
                    lines.append(f"  • {op}\n")
            else:
                lines.append("Operações: (nenhuma)\n")
            lines.append("\n" + "-" * 60 + "\n\n")

        self.query_one("#registry-details", Static).update("".join(lines))

    def action_close_registry(self) -> None:
        self.app.pop_screen()

    def action_cleanup_registry(self) -> None:
        list_view = self.query_one("#registry-list", ListView)
        self.selected_item = list_view.highlighted_child
        if not isinstance(self.selected_item, RegistryListItem):
            return

        script_display = self.selected_item.script_name

        backup_files = _find_backup_files_for_script(
            script_display, self.registry_data
        )
        backup_count = len(backup_files)

        async def handle_dialog_result(confirmed: bool | None) -> None:
            if confirmed:
                await self._execute_cleanup()
            else:
                pass

        self.app.push_screen(
            ConfirmCleanupDialog(script_display, backup_count),
            callback=handle_dialog_result,
        )

    async def _execute_cleanup(self) -> None:
        """Remove the highlighted script from the registry and its backups."""
        list_view = self.query_one("#registry-list", ListView)
        self.selected_item = list_view.highlighted_child
        if not isinstance(self.selected_item, RegistryListItem):
            return

        script_display = self.selected_item.script_name
        # Find backup files
        backup_files = _find_backup_files_for_script(
            script_display, self.registry_data
        )

        # Remove script from registry
        registry_removed = _remove_script_from_registry(script_display)

        # Remove backup files
        success_count, failed_paths = _remove_backup_files(backup_files)
        if registry_removed:
            if failed_paths:
                self.notify(
                    f"Registry entry removed. {success_count} backup file(s) deleted, "
                    f"but {len(failed_paths)} could not be removed (may require elevated permissions)."
                )
            else:
                self.notify(
                    f"Registry entry and {len(backup_files)} backup file(s) successfully removed."
                )
            await self._refresh_page()
        else:
            self.notify(
                translations.get("registry_cleanup_failed", "Cleanup Failed")
            )

    async def _refresh_page(self):
        """Reload the registry from disk and rebuild the list.

        Selects the first script and shows its details, or the
        "nothing executed yet" message if the registry is empty.
        """
        self.registry_data = parse_registry_file()
        script_names = sorted(self.registry_data.keys())
        list_view = self.query_one("#registry-list", ListView)
        await list_view.remove_children()
        await list_view.mount(
            *[RegistryListItem(name) for name in script_names]
        )
        details_widget = self.query_one("#registry-details", Static)
        if script_names:
            list_view.index = 0
            self._display_script_details(script_names[0])
        else:
            details_widget.update("Nenhum script foi executado ainda.")

    def action_export_registry(self) -> None:
        try:
            manifest_path, entry_count = export_registered_manifest(
                registry_data=self.registry_data,
                translations=translations,
            )
            self.notify(
                translations.get(
                    "registry_export_success_message",
                    "Exported {count} registered operation(s) to:\n{path}",
                ).format(count=entry_count, path=manifest_path)
            )
        except OSError as exc:
            self.notify(
                translations.get(
                    "registry_export_error_title", "Manifest export failed"
                )
            )


class RegistryOpenerMixin:
    def action_open_history(self) -> None:
        self.app.push_screen(RegistryScreen())
