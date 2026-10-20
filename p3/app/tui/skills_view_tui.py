from __future__ import annotations

import asyncio
from functools import partial

from rich.markup import escape
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    OptionList,
    TabbedContent,
    TabPane,
)
from textual.widgets.option_list import Option

from .helper import translations
from .skills_core import (
    CommandError,
    MissingSourceError,
    NpxNotFoundError,
    detect_agents,
    format_installs,
    install_skill,
    is_dev_mode,
    list_installed,
    load_popular,
    open_skill_url,
    remove_skill,
    search,
)


def _t(key: str, default: str) -> str:
    """Return the translation of ``key``, or ``default`` if missing.

    Reads the shared ``translations`` dict on every call, so labels
    follow the current language each time a widget is built.
    """
    return translations.get(key, default)


class ActionDialog(ModalScreen["str | None"]):
    """Modal that asks what to do with the selected skill.

    Shows the name, the description (or a generic text) and the AI
    agent disclaimer, with Back, View Details and Install buttons.
    Dismisses with ``"details"`` or ``"install"``, or with None for
    Back and Escape.

    Args:
        skill: Skill dict to act on.
    """

    DEFAULT_CLASSES = "lt-modal"
    BINDINGS = [Binding("escape", "close", "Back")]

    def __init__(self, skill: dict) -> None:
        super().__init__()
        self._skill = skill

    def compose(self) -> ComposeResult:
        desc = self._skill.get("description") or _t(
            "skills_seeker_desc", "Browse, search and install AI agent skills."
        )
        with Vertical():
            yield Label(
                escape(self._skill.get("name", "Unknown")),
                classes="dialog-title",
            )
            yield Label(escape(desc), classes="dialog-text")
            disclaimer = _t("ai_agent_disclaimer", "")
            if disclaimer:
                yield Label(escape(disclaimer), classes="dialog-text")
            with Horizontal():
                yield Button(_t("skills_back_label", "Back"), id="back")
                yield Button(
                    _t("skills_detail_label", "View Details"), id="details"
                )
                yield Button(
                    _t("skills_install_label", "Install"),
                    id="install",
                    variant="success",
                )

    def on_mount(self) -> None:
        self.query_one("#back", Button).focus()  # padrão seguro, como na GUI

    @on(Button.Pressed)
    def _pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(None if event.button.id == "back" else event.button.id)

    def action_close(self) -> None:
        self.dismiss(None)


class AgentChoiceDialog(ModalScreen["str | None"]):
    """Modal that lets the user pick the agent to install a skill for.

    Lists the detected agents with Cancel and Install buttons.
    Dismisses with the chosen agent id, or None if cancelled.

    Args:
        agents: Agent ids from ``detect_agents``. The caller is
            expected to pass at least one.
    """

    DEFAULT_CLASSES = "lt-modal"
    BINDINGS = [Binding("escape", "close", "Cancel")]

    def __init__(self, agents: list[str]) -> None:
        super().__init__()
        self._agents = agents

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(
                _t("skills_choose_agent_title", "Choose Agent"),
                classes="dialog-title",
            )
            yield OptionList(*(Option(a, id=a) for a in self._agents))
            with Horizontal():
                yield Button(_t("skills_back_label", "Cancel"), id="cancel")
                yield Button(
                    _t("skills_install_label", "Install"),
                    id="install",
                    variant="success",
                )

    def on_mount(self) -> None:
        option_list = self.query_one(OptionList)
        option_list.highlighted = 0
        option_list.focus()

    @on(OptionList.OptionSelected)
    def _option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        self.dismiss(event.option.id)

    @on(Button.Pressed)
    def _pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        index = self.query_one(OptionList).highlighted
        if index is None:
            return
        self.dismiss(self.query_one(OptionList).get_option_at_index(index).id)

    def action_close(self) -> None:
        self.dismiss(None)


class ConfirmRemoveDialog(ModalScreen[bool]):
    """Modal that asks to confirm the removal of a skill.

    Equivalent to the GUI's ``MessageDialog``. Cancel is focused by
    default. Dismisses with True only when Remove is pressed; Cancel
    and Escape dismiss with False.

    Args:
        skill_name: Name of the skill, shown in the dialog.
    """

    DEFAULT_CLASSES = "lt-modal"
    BINDINGS = [Binding("escape", "close", "Cancel")]

    def __init__(self, skill_name: str) -> None:
        super().__init__()
        self._skill_name = skill_name

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(
                _t("skills_confirm_remove_title", "Remove Skill?"),
                classes="dialog-title",
            )
            yield Label(escape(self._skill_name))
            yield Label(
                _t(
                    "skills_confirm_remove_msg",
                    "This will remove the skill from all linked agents.",
                ),
                classes="dialog-text",
            )
            with Horizontal():
                yield Button(_t("skills_back_label", "Cancel"), id="cancel")
                yield Button(
                    _t("skills_remove_label", "Remove"),
                    id="remove",
                    variant="error",
                )

    def on_mount(self) -> None:
        self.query_one("#cancel", Button).focus()

    @on(Button.Pressed)
    def _pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "remove")

    def action_close(self) -> None:
        self.dismiss(False)


class SkillCard(ListItem):
    """List item for a skill in the Discover tab.

    Shows the name and the install count (e.g. ``↓ 1.2K``).

    Attributes:
        skill_data: The skill dict. Not called ``name`` to avoid a
            clash with ``Widget.name``.

    Args:
        skill: Skill dict from ``load_popular`` or ``search``.
    """

    def __init__(self, skill: dict) -> None:
        super().__init__()
        self.skill_data = skill  # evita colidir com Widget.name

    def compose(self) -> ComposeResult:
        name = escape(self.skill_data.get("name") or "Unknown")
        installs = format_installs(self.skill_data.get("installs", 0))
        yield Label(f"{name}  [dim]↓ {installs}[/dim]")


class InstalledCard(ListItem):
    """List item for a skill in the Installed tab.

    Shows the name in bold followed by the agents it is linked to.

    Attributes:
        skill_data: The skill dict.

    Args:
        skill: Skill dict from ``list_installed``.
    """

    def __init__(self, skill: dict) -> None:
        super().__init__()
        self.skill_data = skill

    def compose(self) -> ComposeResult:
        name = escape(self.skill_data.get("name") or "Unknown")
        agents = escape(", ".join(self.skill_data.get("agents", [])))
        suffix = f"  [dim]{agents}[/dim]" if agents else ""
        yield Label(f"[b]{name}[/b]{suffix}")


class SkillsSeekerView(Vertical):
    """Main view of the skills feature: browse, search, install, remove.

    Has two tabs. "Discover" lists the popular skills (or the search
    results) from skills.sh. Selecting one opens ``ActionDialog``,
    which leads to its page or to the install flow. "Installed" lists
    the globally installed skills; selecting one asks for confirmation
    and removes it. Network and npx work runs in workers, so the UI
    stays responsive.

    The main screen calls ``do_search`` when the user submits a search
    and ``focus_results`` to move focus into the list.

    Attributes:
        _all_skills: Cache of the popular skills, loaded once.
    """

    DEFAULT_CSS = """
    SkillsSeekerView { height: 1fr; width: 100% }
    SkillsSeekerView TabbedContent { height: 1fr; }
    SkillsSeekerView TabPane { padding: 0 1; }
    SkillsSeekerView ListView { height: 1fr; }
    SkillsSeekerView LoadingIndicator { height: 3; }
    SkillsSeekerView .status { color: $text-muted; height: 1; }
    SkillsSeekerView #reload_installed { dock: right; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._all_skills: list[dict] = []

    def compose(self) -> ComposeResult:
        with TabbedContent(initial="discover"):
            with TabPane(_t("skills_tab_discover", "Discover"), id="discover"):
                yield LoadingIndicator(id="discover_loading")
                yield ListView(id="discover_list")
                yield Label("", id="discover_status", classes="status")
            with TabPane(
                _t("skills_tab_installed", "Installed"), id="installed"
            ):
                yield Button(
                    _t("skills_reload_label", "Reload"), id="reload_installed"
                )
                yield LoadingIndicator(id="installed_loading")
                yield ListView(id="installed_list")
                yield Label("", id="installed_status", classes="status")

    def on_mount(self) -> None:
        self.load_discover()

    def focus_results(self) -> None:
        self.query_one("#discover_list", ListView).focus()

    def _set_busy(self, tab: str, busy: bool) -> None:
        """Switch a tab between the loading indicator and its list.

        Args:
            tab: ``"discover"`` or ``"installed"``.
            busy: True to show the indicator and hide the list.
        """
        self.query_one(f"#{tab}_loading").display = busy
        self.query_one(f"#{tab}_list").display = not busy

    def _set_status(self, tab: str, text: str) -> None:
        """Set the status line text of a tab.

        Args:
            tab: ``"discover"`` or ``"installed"``.
            text: Text to show.
        """
        self.query_one(f"#{tab}_status", Label).update(text)

    async def _fill_list(self, tab: str, items: list[ListItem]) -> None:
        """Replace the contents of a tab's list.

        Clears the list, adds ``items`` in one operation and
        highlights the first one.

        Args:
            tab: ``"discover"`` or ``"installed"``.
            items: New list items. May be empty.
        """
        list_view = self.query_one(f"#{tab}_list", ListView)
        await list_view.clear()
        if items:
            await list_view.extend(items)
            list_view.index = 0

    @on(TabbedContent.TabActivated)
    def _tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Reload the installed skills whenever that tab is opened."""
        if event.pane.id == "installed":
            self.load_installed()

    @on(Button.Pressed, "#reload_installed")
    def _reload_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.load_installed()

    def do_search(self, query: str) -> None:
        """Search the catalog from the Discover tab.

        Public API, called by the main screen when the user submits a
        search. Switches to the Discover tab and loads the results.
        An empty query shows the popular skills.

        Args:
            query: Search text. Surrounding whitespace is ignored.
        """
        self.query_one(TabbedContent).active = "discover"
        self.load_discover(query.strip())

    @work(exclusive=True, group="discover")
    async def load_discover(self, query: str = "") -> None:
        """Load the Discover list: search results or popular skills.

        Worker, exclusive in the ``discover`` group, so a new call
        supersedes the previous one. Shows the loading indicator, runs
        the network call in a thread, fills the list and sets the
        status to the result count or to an empty/offline message. The
        popular skills are fetched once and cached in ``_all_skills``.

        Args:
            query: Search text. Empty to show the popular skills.
        """
        self._set_busy("discover", True)
        if query:
            self._set_status(
                "discover", _t("skills_searching", "Searching...")
            )
            skills = await asyncio.to_thread(search, query)
            empty_msg = _t(
                "skills_no_results", "No skills found for your search."
            )
        else:
            if self._all_skills:
                skills = self._all_skills
            else:
                self._set_status(
                    "discover", _t("skills_loading", "Loading...")
                )
                skills = await asyncio.to_thread(load_popular, 50)
                self._all_skills = skills
            empty_msg = _t(
                "skills_no_internet",
                "Internet connection is required to search and browse skills.",
            )

        await self._fill_list("discover", [SkillCard(s) for s in skills])
        self._set_busy("discover", False)
        self._set_status(
            "discover", f"{len(skills)} skill(s)" if skills else empty_msg
        )

    @on(ListView.Selected, "#discover_list")
    def _discover_selected(self, event: ListView.Selected) -> None:
        event.stop()
        if isinstance(event.item, SkillCard):
            skill = event.item.skill_data
            self.app.push_screen(
                ActionDialog(skill), partial(self._on_action, skill)
            )

    def _on_action(self, skill: dict, action: str | None) -> None:
        if action == "details":
            if not open_skill_url(skill):
                self.notify(
                    _t(
                        "skills_error_no_source",
                        "Could not determine skill URL.",
                    ),
                    severity="error",
                )
        elif action == "install":
            self._start_install(skill)

    def _start_install(self, skill: dict) -> None:
        if not skill.get("source"):
            self.notify(
                _t(
                    "skills_error_no_source",
                    "Could not determine skill source.",
                ),
                severity="error",
            )
            return
        agents = detect_agents()
        if not agents:
            self.notify(
                _t(
                    "skills_no_agents",
                    "No supported AI agents detected on this system.",
                ),
                severity="error",
            )
            return
        self.app.push_screen(
            AgentChoiceDialog(agents), partial(self._on_agent_chosen, skill)
        )

    def _on_agent_chosen(self, skill: dict, agent: str | None) -> None:
        if agent:
            self.run_install(skill, agent)

    @work(group="install")
    async def run_install(self, skill: dict, agent: str) -> None:
        self._set_status("discover", _t("skills_installing", "Installing..."))
        try:
            result = await asyncio.to_thread(install_skill, skill, agent)
        except NpxNotFoundError:
            self._install_failed(
                _t(
                    "skills_error_no_npx",
                    "Node.js (npx) is required to install skills.",
                )
            )
            return
        except MissingSourceError:
            self._install_failed(
                _t(
                    "skills_error_no_source",
                    "Could not determine skill source.",
                )
            )
            return
        except Exception as e:  # noqa: BLE001
            self._install_failed(str(e))
            return

        if result.ok:
            self._set_status(
                "discover",
                _t("skills_installed_ok", "Skill installed successfully!"),
            )
            self.notify(
                _t("skills_installed_ok", "Skill installed successfully!")
            )
        elif result.timed_out:
            self._install_failed(
                _t("skills_error_timeout", "Installation timed out.")
            )
        else:
            self._install_failed(
                result.message
                or _t("skills_error_install", "Installation failed.")
            )

    def _install_failed(self, message: str) -> None:
        self._set_status(
            "discover", _t("skills_error_install", "Installation failed.")
        )
        self.notify(message, severity="error", timeout=10)

    @work(exclusive=True, group="installed")
    async def load_installed(self) -> None:
        self._set_busy("installed", True)
        self._set_status("installed", _t("skills_loading", "Loading..."))
        try:
            skills = await asyncio.to_thread(list_installed)
        except NpxNotFoundError:
            await self._fill_list("installed", [])
            self._set_busy("installed", False)
            self._set_status(
                "installed",
                _t("skills_error_no_npx", "Node.js (npx) is required."),
            )
            return
        except CommandError as e:
            await self._fill_list("installed", [])
            self._set_busy("installed", False)
            self._set_status("installed", str(e))
            return

        await self._fill_list("installed", [InstalledCard(s) for s in skills])
        self._set_busy("installed", False)
        self._set_status(
            "installed",
            f"{len(skills)} skill(s)"
            if skills
            else _t("skills_no_installed", "No skills installed globally."),
        )

    @on(ListView.Selected, "#installed_list")
    def _installed_selected(self, event: ListView.Selected) -> None:
        event.stop()
        if not isinstance(event.item, InstalledCard):
            return
        if is_dev_mode():
            self.notify("Mock mode: removal is disabled.", severity="warning")
            return
        skill = event.item.skill_data
        self.app.push_screen(
            ConfirmRemoveDialog(skill.get("name", "")),
            partial(self._on_remove_confirmed, skill),
        )

    def _on_remove_confirmed(
        self, skill: dict, confirmed: bool | None
    ) -> None:
        if confirmed:
            self.run_remove(skill)

    @work(group="remove")
    async def run_remove(self, skill: dict) -> None:
        self._set_status("installed", _t("skills_removing", "Removing..."))
        try:
            result = await asyncio.to_thread(remove_skill, skill)
        except NpxNotFoundError:
            self.notify(
                _t("skills_error_no_npx", "Node.js (npx) is required."),
                severity="error",
            )
            return
        except Exception as e:  # noqa: BLE001
            self.notify(str(e), severity="error", timeout=10)
            return

        if result.ok:
            self.notify(_t("skills_removed_ok", "Skill removed."))
            self.load_installed()
        else:
            self._set_status(
                "installed", _t("skills_error_remove", "Removal failed.")
            )
            self.notify(
                result.message or _t("skills_error_remove", "Removal failed."),
                severity="error",
                timeout=10,
            )
