"""Modal dialogs of the TUI.

Each dialog is a ``ModalScreen`` that reports its outcome through
``dismiss()``. Confirmations return a bool, information dialogs return
None, and ``SudoPasswordScreen`` and ``LanguageSelectorDialog`` return a
value or None. Texts come from the translations mapping, with English
defaults. Most dialogs bind Escape to ``cancel``, labeled with the
``script_runner_close`` translation. Those bindings are evaluated at
import time, so they do not follow a later language change.

Groups:

- Script run: ``ConfirmScriptScreen``, ``RemoveScriptScreen``,
  ``SudoPasswordScreen``, ``SuccessDialog``, ``ErrorDialog``,
  ``CancelledDialog`` and ``RebootDialog``.
- Registry: ``ConfirmCleanupDialog``.
- AUR: ``AurConsentDialog``, ``AurHelperDialog`` and
  ``AurSecurityDialog``.
- App: ``ReportBugDialog``, ``LanguageSelectorDialog``,
  ``UpdateAvailableDialog`` and ``UpdateCompleteDialog``.
"""

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Input,
    Label,
    ListView,
    Select,
    Static,
    TextArea,
)

from app.antenna import antenna
from app.lang_utils import (
    get_available_languages,
    get_localized_language_names,
)
from app.official_index import get_bug_report_entries

from .helper import translations
from .my_widgets import LanguageListItem


class ConfirmScriptScreen(ModalScreen[bool]):
    """Ask for confirmation before running a script.

    Shows the script description and two buttons, Cancel and Execute.
    Focus starts on Execute. Dismisses with True on Execute, and False
    on Cancel or Escape.

    Args:
        name: Script name, used in the title.
        description: Text shown in the scrollable body.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def __init__(self, name: str, description: str) -> None:
        super().__init__()
        self.script_name = name
        self.description = description

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(
                f"{translations.get('term_view_execute', 'Execute')} '{self.script_name}'?",
                id="confirm-title",
            )
            with VerticalScroll(id="confirm-description"):
                yield Static(self.description)
            with Horizontal(id="confirm-buttons"):
                yield Button(
                    translations.get("cancel_btn_label", "Cancel"),
                    id="cancel-btn",
                    variant="error",
                )
                yield Button(
                    translations.get("term_view_execute", "Execute"),
                    id="execute-btn",
                    variant="success",
                )

    def on_mount(self) -> None:
        self.query_one("#execute-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "execute-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)


class ConfirmCleanupDialog(ModalScreen[bool]):
    """Ask for confirmation before removing a registry entry.

    The message states that the entry and its backup files will be
    deleted, and that the script's operations can no longer be undone
    from the app afterwards. Dismisses with True on Remove, and False on
    Cancel. It has no Escape binding.

    Args:
        script_name: Script whose registry entry will be removed.
        backup_count: Number of backup files that will be deleted.
        name: Screen name, forwarded to ``ModalScreen``.
        id: Screen id, forwarded to ``ModalScreen``.
        classes: CSS classes, forwarded to ``ModalScreen``.
    """

    def __init__(
        self,
        script_name: str,
        backup_count: int = 0,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.script_name = script_name
        self.backup_count = backup_count

    def compose(self) -> ComposeResult:
        secondary_text = (
            f"This will remove the registry entry for '{self.script_name}' and delete "
            f"{self.backup_count} backup file(s). After removal, you will no longer be able "
            "to undo the operations from this script using the app.\n\n"
            "This action cannot be undone."
        )

        with Vertical(id="confirm-dialog"):
            yield Static(
                translations.get("registry_cleanup_title", "Cleanup registry"),
                id="dialog-title",
            )
            yield Static(secondary_text, id="dialog-message")

            with Horizontal(id="dialog-buttons"):
                yield Button(
                    translations.get("cancel_btn_label", "Cancel"),
                    variant="default",
                    id="cancel-btn",
                )
                yield Button(
                    translations.get("term_view_remove", "Remove"),
                    variant="error",
                    id="remove-btn",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "remove-btn":
            self.dismiss(True)
        else:
            self.dismiss(False)


class RemoveScriptScreen(ModalScreen[bool]):
    """Ask for confirmation before removing a script.

    Shows the description and two buttons, Cancel and a confirm button
    (Remove by default). Focus starts on the confirm button. Dismisses
    with True on confirm, and False on Cancel or Escape.

    Args:
        name: Script name, used in the default title.
        description: Text shown in the scrollable body.
        title: Heading that replaces the default ``Remove '<name>'?``.
        confirm_label: Label that replaces the default Remove label.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def __init__(
        self,
        name: str,
        description: str,
        *,
        title: str | None = None,
        confirm_label: str | None = None,
    ) -> None:
        super().__init__()
        self.script_name = name
        self.description = description
        self._dialog_title = title
        self._confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        heading = (
            self._dialog_title
            or f"{translations.get('term_view_remove', 'Remove')} "
            f"'{self.script_name}'?"
        )
        confirm_label = self._confirm_label or translations.get(
            "term_view_remove", "Remove"
        )
        with Vertical(id="confirm-dialog"):
            yield Static(heading, id="confirm-title")
            with VerticalScroll(id="confirm-description"):
                yield Static(self.description)
            with Horizontal(id="confirm-buttons"):
                yield Button(
                    translations.get("cancel_btn_label", "Cancel"),
                    id="cancel-btn",
                    variant="error",
                )
                yield Button(
                    confirm_label, id="execute-btn", variant="success"
                )

    def on_mount(self) -> None:
        self.query_one("#confirm-description").border_title = "Description"
        self.query_one("#execute-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "execute-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)


class SuccessDialog(ModalScreen[None]):
    """Tell the user that a script finished with exit code 0.

    Dismisses with None on Done or Escape.

    Args:
        script_name: Name of the script.
        action: Past-tense verb for the message, e.g. ``"installed"``.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def __init__(self, script_name: str, action: str = "installed") -> None:
        super().__init__()
        self.script_name = script_name
        self.action = action

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(
                f"'{self.script_name}' was successfully {self.action}."
            )
            with Horizontal(id="confirm-buttons"):
                yield Button(
                    translations.get("term_view_done", "Done"),
                    id="execute-btn",
                    variant="success",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "execute-btn":
            self.dismiss()

    def action_cancel(self) -> None:
        self.dismiss()


class RebootDialog(ModalScreen[bool]):
    """Tell the user that a system reboot is required.

    Shown after a script that requires a reboot, because other features
    must not be installed before it. Dismisses with None (not the
    declared bool) on Done or Escape.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(
                translations.get(
                    "reboot_required_message",
                    "A script requiring a system reboot has been executed. You must reboot your computer before installing other features.",
                )
            )
            with Horizontal(id="confirm-buttons"):
                yield Button(
                    translations.get("term_view_done", "Done"),
                    id="execute-btn",
                    variant="success",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "execute-btn":
            self.dismiss()

    def action_cancel(self) -> None:
        self.dismiss()


class ErrorDialog(ModalScreen[bool]):
    """Report a script that failed with a real error exit code.

    Not used for cancellations or Ctrl+C. Dismisses with True if the
    user pressed Report bug, and False on Done or Escape.

    Args:
        script_name: Name of the script.
        exit_code: Exit code shown in the message, or None if the
            script did not return one.
        action: Verb in the infinitive for the message, e.g.
            ``"install"``.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def __init__(
        self, script_name: str, exit_code: int | None, action: str = "install"
    ) -> None:
        super().__init__()
        self.script_name = script_name
        self.exit_code = exit_code
        self.action = action

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(
                f"Failed to {self.action} the '{self.script_name}' "
                f"(exit code: {self.exit_code})."
            )
            with Horizontal(id="confirm-buttons"):
                yield Button(
                    translations.get("term_view_done", "Done"),
                    id="execute-btn",
                    variant="success",
                )
                yield Button(
                    translations.get("report_label", "Report bug"),
                    id="report-bug",
                    variant="warning",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "report-bug")

    def action_cancel(self) -> None:
        self.dismiss(False)


class SudoPasswordScreen(ModalScreen[str | None]):
    """Collect the sudo password inside the TUI.

    The password is read here and never from ``/dev/tty``, so the dialog
    does not compete with Textual for the terminal input. Enter submits.
    Dismisses with the password, or None if the user cancels or submits
    an empty password.

    Args:
        script_name: Script that needs sudo, shown in the title.
        error_message: Optional message shown above the field, e.g.
            after a wrong password.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def __init__(
        self, script_name: str, error_message: str | None = None
    ) -> None:
        super().__init__()
        self.script_name = script_name
        self.error_message = error_message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(
                f"'{self.script_name}' needs sudo privileges",
                id="confirm-title",
            )
            if self.error_message:
                yield Static(self.error_message, id="sudo-error")
            yield Input(
                password=True,
                id="sudo-password-input",
            )
            with Horizontal(id="confirm-buttons"):
                yield Button(
                    translations.get("cancel_btn_label", "Cancel"),
                    id="cancel-btn",
                    variant="error",
                )
                yield Button(
                    translations.get("confirm_title", "Confirm"),
                    id="confirm-btn",
                    variant="success",
                )

    def on_mount(self) -> None:
        self.query_one("#sudo-password-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "confirm-btn":
            self._submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._submit()

    def _submit(self) -> None:
        password = self.query_one("#sudo-password-input", Input).value
        self.dismiss(password or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class CancelledDialog(ModalScreen[None]):
    """Tell the user that a run was cancelled.

    Exit code 100 is the LinuxToys convention for cancellation. It is
    injected by the TUI when the password prompt is cancelled, or
    produced by the script itself. Dismisses with None.

    Args:
        script_name: Name of the cancelled script.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def __init__(self, script_name: str) -> None:
        super().__init__()
        self.script_name = script_name

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(f"'{self.script_name}' execution cancelled.")
            with Horizontal(id="confirm-buttons"):
                yield Button(
                    translations.get("ok_btn_label", "OK"),
                    id="execute-btn",
                    variant="primary",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "execute-btn":
            self.dismiss()

    def action_cancel(self) -> None:
        self.dismiss()


class ReportBugDialog(ModalScreen[bool]):
    """Form to report a bug.

    Shows an application selector (LinuxToys first, then the entries
    from ``get_bug_report_entries``), a description field and the system
    information. OK submits the report in a thread worker. Dismisses
    with None on Cancel, Escape or after a successful submission
    (the declared bool is never used).
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def compose(self) -> ComposeResult:
        system_context = antenna.get_system_context()

        raw_entries = get_bug_report_entries(translations=translations)
        options = [("LinuxToys", "LinuxToys")] + [
            (display_name, name) for name, display_name in raw_entries
        ]

        with Vertical(id="dialog-container"):
            with Horizontal(classes="form-row"):
                yield Static(
                    translations.get(
                        "bug_report_app", "Application (optional):"
                    ),
                    classes="label-inline",
                )
                yield Select(
                    options,
                    value="LinuxToys",
                    id="select-app",
                    allow_blank=False,
                )
            yield Static(
                translations.get(
                    "bug_report_desc",
                    "Please describe the issue you encountered:",
                ),
                classes="field-label",
            )
            yield TextArea(id="bug-description")
            yield Static(
                f"{translations.get('system_info', 'System Info')}: {system_context}",
                id="system-info-text",
            )
            with Horizontal(id="buttons-aligh-right"):
                yield Button(
                    translations.get("cancel_btn_label", "Cancel"),
                    id="cancel-btn-bug",
                    variant="error",
                )
                yield Button(
                    translations.get("ok_btn_label", "OK"),
                    id="execute-btn-bug",
                    variant="primary",
                )
        yield Footer()

    @on(Button.Pressed, "#cancel-btn-bug")
    def handle_cancel(self) -> None:
        self.dismiss()

    # Handle the OK / Send button
    @on(Button.Pressed, "#execute-btn-bug")
    def handle_execute(self) -> None:
        # Read the values directly from the widgets
        comment = self.query_one("#bug-description", TextArea).text.strip()
        selected_app = self.query_one("#select-app", Select).value

        # Simple validation to avoid sending an empty report
        if not comment:
            self.notify(
                translations.get(
                    "bug_report_empty",
                    "Please provide a description of the issue.",
                ),
                severity="warning",
            )
            return

        # Disable the button to avoid repeated clicks while sending
        self.query_one("#execute-btn-bug", Button).disabled = True

        self._submit_bug_report(comment, selected_app)

    @work(thread=True)
    def _submit_bug_report(self, comment: str, selected_app=None) -> None:
        """Envia o relatório de bug em uma thread de segundo plano."""
        try:
            system_context = antenna.get_system_context()
            antenna.submit_issue(
                title="User Report: Bug from TUI",
                logs=comment,
                context=system_context,
                is_footer_triggered=True,
                related_app=selected_app,
                infer_related_app=False,
            )

            self.app.call_from_thread(
                self.notify,
                translations.get(
                    "bug_report_submitted",
                    "Thank you! Your bug report has been submitted.",
                ),
                title="Sucesso",
                severity="information",
            )

            self.app.call_from_thread(self.dismiss)

        except Exception as e:
            self.app.call_from_thread(
                self.notify,
                f"{translations.get('bug_report_failed', 'Failed to submit bug report: ')} {e}",
                title="Erro",
                severity="error",
            )
            self.app.call_from_thread(
                setattr,
                self.query_one("#execute-btn-bug", Button),
                "disabled",
                False,
            )


class LanguageSelectorDialog(ModalScreen[str | None]):
    """Pick the interface language from a searchable list.

    Lists the available languages with their localized names. The
    search box filters by language code or by name, ignoring case.
    Dismisses with the selected language code, or None on Cancel or
    Escape. Select does nothing if no item is highlighted.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def compose(self) -> ComposeResult:
        display_name = get_localized_language_names(translations)
        codes = get_available_languages()
        with Vertical(id="lang-dialog-container"):
            yield Static(
                translations.get("select_language_message", "Select Language"),
                classes="lang-label",
            )
            yield Input(
                placeholder=translations.get(
                    "search_languages_placeholder", "Search languages"
                ),
                id="search-language",
            )
            yield ListView(
                *[
                    LanguageListItem(code, display_name.get(code, code))
                    for code in codes
                ],
                id="language-list",
            )
            with Horizontal(id="buttons-aligh-right"):
                yield Button(
                    translations.get("cancel_btn_label", "Cancel"),
                    id="cancel-btn-bug",
                    variant="error",
                )
                yield Button(
                    translations.get("select_button", "Select"),
                    id="execute-btn-bug",
                    variant="primary",
                )
        yield Footer()

    @on(Button.Pressed, "#cancel-btn-bug")
    def handle_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#execute-btn-bug")
    def handle_select(self) -> None:
        selected = self.query_one("#language-list", ListView).highlighted_child
        if isinstance(selected, LanguageListItem):
            self.dismiss(selected.code)

    @on(Input.Changed, "#search-language")
    def handle_search_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-language":
            return

        query = event.value.strip().casefold()
        list_view = self.query_one("#language-list", ListView)

        for item in list_view.query(LanguageListItem):
            code_match = query in item.code.casefold()
            name_match = query in item.display_name.casefold()

            item.display = code_match or name_match

    def action_cancel(self) -> None:
        self.dismiss(None)


class UpdateAvailableDialog(ModalScreen[bool]):
    """Offer a new LinuxToys version.

    Shows the version and the changelog. Dismisses with True on Install
    Update, and False on Ignore.

    Args:
        tag: Version tag of the update, shown in the message.
        changelog: Release notes shown in the scrollable body.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def __init__(self, tag: str, changelog: str) -> None:
        super().__init__()
        self.tag = tag
        self.changelog = changelog

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            tempalte_test = translations.get(
                "update_available_message",
                "A new version ${version} of LinuxToys is available.",
            )
            yield Label(tempalte_test.replace("${version}", self.tag))
            with VerticalScroll(id="changelog"):
                yield Static(self.changelog)
            with Horizontal(id="confirm-buttons"):
                yield Button("Ignore", id="no", variant="error")
                yield Button("Install Update", id="yes", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class UpdateCompleteDialog(ModalScreen[None]):
    """Tell the user that the update is installed.

    Offers a single button, which dismisses with None. The caller is
    responsible for restarting the application.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label("Atualização concluída!")
            yield Label(
                translations.get(
                    "update_status_restart",
                    "Update installed. You can restart the application.",
                )
            )
            yield Button(
                translations.get("reboot_now_btn", "Reboot now"),
                id="restart",
                variant="success",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "restart":
            self.dismiss()


class AurSecurityDialog(ModalScreen[None]):
    """Explain why an AUR install was stopped by the security check.

    Shown before any installation starts. Dismisses with None.

    Args:
        script_name: Name of the script.
        blocked: True if the sources look unsafe, False if they could
            not be verified.
        detail: Findings or reason, as returned by
            ``check_aur_package_security``.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def __init__(self, script_name: str, blocked: bool, detail: str) -> None:
        super().__init__()
        self.script_name = script_name
        self.blocked = blocked
        self.detail = detail

    def compose(self) -> ComposeResult:
        if self.blocked:
            title = (
                f"'{self.script_name}' was not installed: potential security "
                "risk found in the AUR package sources."
            )
        else:
            title = (
                f"'{self.script_name}' was not installed: its AUR sources "
                "could not be verified."
            )
        with Vertical(id="confirm-dialog"):
            yield Label(title)
            with VerticalScroll(id="aur-security-detail"):
                yield Static(self.detail)
            with Horizontal(id="confirm-buttons"):
                yield Button(
                    translations.get("ok_btn_label", "OK"),
                    id="execute-btn",
                    variant="primary",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "execute-btn":
            self.dismiss()

    def action_cancel(self) -> None:
        self.dismiss()


class AurConsentDialog(ModalScreen[bool]):
    """Warn about the risks of the AUR before enabling it.

    Focus starts on Return, the safe choice. Dismisses with True on
    Enable AUR, and False on Return or Escape.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(
                translations.get("aur_warning_title", "Enable the AUR?"),
                id="confirm-title",
            )
            with VerticalScroll(id="confirm-description"):
                yield Static(
                    translations.get(
                        "aur_warning_message",
                        "The Arch User Repository contains user-produced "
                        "build scripts that are not reviewed or supported by "
                        "Arch Linux. Installing AUR packages can execute "
                        "package build instructions on your system. Review "
                        "packages and PKGBUILDs before installing them.",
                    )
                )
            with Horizontal(id="confirm-buttons"):
                yield Button(
                    translations.get("aur_warning_return", "Return"),
                    id="cancel-btn",
                )
                yield Button(
                    translations.get("aur_warning_enable", "Enable AUR"),
                    id="enable-btn",
                    variant="warning",
                )

    def on_mount(self) -> None:
        self.query_one("#cancel-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "enable-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)


class AurHelperDialog(ModalScreen[bool]):
    """Ask whether to install paru, the AUR helper, now.

    Focus starts on No. Dismisses with True on Yes, and False on No or
    Escape.
    """

    BINDINGS = [
        Binding("escape", "cancel", translations.get("script_runner_close"))
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(
                translations.get(
                    "aur_helper_required",
                    "This installation requires having paru, an AUR helper, "
                    "available. Do you wish to install it now?",
                )
            )
            with Horizontal(id="confirm-buttons"):
                yield Button(translations.get("no", "No"), id="cancel-btn")
                yield Button(
                    translations.get("yes", "Yes"),
                    id="yes-btn",
                    variant="success",
                )

    def on_mount(self) -> None:
        self.query_one("#cancel-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "yes-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)
