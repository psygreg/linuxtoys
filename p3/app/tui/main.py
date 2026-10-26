"""Entry point of the LinuxToys TUI.

``LinuxToys`` is the Textual app. It shows ``SplashScreen`` while the
search and category index is built in a background thread, then switches
to ``HomeScreen``, which holds almost all the interface and is composed of
the mixins from the other modules.

Run it as a module, because the imports are relative.

Constants:
    HOMEBREW_WATCH_INTERVAL: Seconds between checks for a change in
        Homebrew availability.
    HOMEBREW_STARTUP_DELAY: Seconds after startup before the first
        Homebrew catalog refresh.
    HOMEBREW_PAGE_SIZE: Items mounted per page in lazy lists. It is used
        by every lazy list (Homebrew, AppImage and AUR), not only by
        Homebrew.
    RENDER_CHUNK_SIZE: Items mounted per batch while rendering.
    SCROLL_LOAD_MARGIN: Distance from the end of the list, in rows,
        that triggers loading the next page.
"""

import asyncio
from functools import partial

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Link,
    ListItem,
    ListView,
    LoadingIndicator,
    Static,
)

from app import homebrew_catalog
from app.lang_utils import detect_system_language
from app.registry_utils import parse_registry_file

from .about_helper import load_ansi_art
from .app_page_translate import (
    load_cached_translation,
    save_cached_translation,
    translate_description_blocks,
)
from .dialog_screen import ReportBugDialog
from .helper import (
    appimage_category_info,
    get_categories,
    get_specials_root_item,
    homebrew_category_info,
    is_appimage_path,
    is_registered_entry,
    is_search_ready,
    make_widget_id,
    search_scripts_fast,
    translations,
    warm_search_and_category_index,
)
from .menu_helper import MenuSelectionMixin
from .my_widgets import (
    FocusableLabel,
    InfoButton,
    Terminal,
)
from .registry_screen import RegistryOpenerMixin
from .runner_helper import (
    AppstreamRunnerMixin,
    ManifestRunnerMixin,
    ScriptRunnerMixin,
    UpdateRunnerMixin,
)
from .startup_recommendation import StartupRecommendationsMixin
from .tui_app_page import AppPageWidget, hide_app_page, show_app_page

HOMEBREW_WATCH_INTERVAL = 3.0
HOMEBREW_STARTUP_DELAY = 15.0
HOMEBREW_PAGE_SIZE = 60
RENDER_CHUNK_SIZE = 100
SCROLL_LOAD_MARGIN = 5


class HomeScreen(
    MenuSelectionMixin,
    ScriptRunnerMixin,
    AppstreamRunnerMixin,
    UpdateRunnerMixin,
    ManifestRunnerMixin,
    RegistryOpenerMixin,
    StartupRecommendationsMixin,
    Screen,
):
    """main screen for linuxtoys TUI"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._nav_stack: list[tuple[str, str]] = []
        self._render_lock = asyncio.Lock()
        self._render_generation = 0
        self._homebrew_refresh_running = False
        self._homebrew_awaiting_refresh = False
        self._homebrew_source_fingerprint = None
        self._lazy_items = None
        self._lazy_loaded = 0
        self._registry_data = None
        self._skills_search_timer = None
        self._homebrew_search_timer = None
        self._appimage_search_timer = None
        self._skills_prev_display: dict[str, bool] = {}
        self._skills_prev_placeholder = ""
        self._skills_prev_panel_title = ""

    CSS_PATH = "style.tcss"
    _search_timer: asyncio.TimerHandle | None = None
    _SKILLS_HIDDEN = ("#logo_lt", "#home-menu", "#terminal-conteiner")

    BINDINGS = [
        Binding("q", "app.quit", "Sair"),
        Binding("tab", "app.focus_next", "Navegar"),
        Binding("shift+tab", "app.focus_previous", "Anterior"),
        Binding("h", "reset_to_home", "Home"),
        Binding("escape", "go_back", "Voltar"),
        Binding("f1", "noop", "🔴 Uninstall   🟡 New", key_display=" "),
    ]

    def action_noop(self) -> None:
        """Empty action for purely informational captions in the footer."""

    def compose(self) -> ComposeResult:
        linuxtoys_art = load_ansi_art("linuxtoystui.ansi")
        yield Header(id="lt-header")

        with Horizontal(id="body-home"):
            # left panel widgets
            with Vertical(id="left-column-home"):
                yield Input(
                    placeholder=translations.get(
                        "search_placeholder", "Search features"
                    ),
                    id="search-input",
                )
                with VerticalScroll(id="left-panel-home"):
                    registry_data = parse_registry_file()
                    for item in self._home_items():
                        yield self._make_info_button(item, registry_data)
            # right panel widgets
            with VerticalScroll(id="menu-panel"):
                yield Static(linuxtoys_art, id="logo_lt")
                yield ListView(
                    ListItem(
                        Label(
                            translations.get("load_manifest", "Load manifest")
                        ),
                        id="manifest",
                    ),
                    ListItem(
                        Label(
                            translations.get(
                                "select_language", "Select language"
                            )
                        ),
                        id="language",
                    ),
                    ListItem(
                        Label(f"{translations.get('about', 'About')}"),
                        id="about",
                    ),
                    ListItem(
                        Label(f"{translations.get('action_registry')}"),
                        id="registry",
                    ),
                    ListItem(Label("Update LinuxToys"), id="update"),
                    ListItem(
                        Label(
                            translations.get(
                                "scripts_resync", "Scripts resync"
                            )
                        ),
                        id="scripts_resync",
                    ),
                    id="home-menu",
                )
                with Vertical(id="terminal-conteiner"):
                    yield Terminal(id="terminal")

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

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#terminal-conteiner").display = False
        self.query_one("#left-panel-home").border_title = "LinuxToys"
        self.query_one("#menu-panel").border_title = "Menu"
        self._homebrew_source_fingerprint = (
            homebrew_catalog.availability_fingerprint()
        )
        self.set_interval(HOMEBREW_WATCH_INTERVAL, self._check_homebrew_source)
        self.set_timer(HOMEBREW_STARTUP_DELAY, self._request_homebrew_refresh)
        self.watch(
            self.query_one("#left-panel-home", VerticalScroll),
            "scroll_y",
            self._on_items_scroll,
        )

        left_panel = self.query_one("#left-panel-home", VerticalScroll)
        first_button = left_panel.query(InfoButton).first()
        if first_button is not None:
            first_button.focus()

        self.call_after_refresh(self.check_startup_recommendations)

    @property
    def _is_app_page_showing(self) -> bool:
        return bool(self.query(AppPageWidget))

    @property
    def is_skills_seeker_showing(self) -> bool:
        return bool(self.query("SkillsSeekerView"))

    async def _open_skills_seeker(self) -> None:
        from .skills_view_tui import SkillsSeekerView

        if self.is_skills_seeker_showing:
            return

        panel = self.query_one("#menu-panel")
        self._skills_prev_panel_title = panel.border_title
        panel.border_title = "Skills Seeker"

        self._skills_prev_display = {
            sel: self.query_one(sel).display for sel in self._SKILLS_HIDDEN
        }
        for sel in self._SKILLS_HIDDEN:
            self.query_one(sel).display = False

        search = self.query_one("#search-input", Input)
        self._skills_prev_placeholder = search.placeholder
        search.placeholder = translations.get(
            "skills_search_placeholder", "Search skills"
        )
        with search.prevent(Input.Changed):
            search.value = ""

        await self.query_one("#menu-panel").mount(SkillsSeekerView())

    async def _close_skills_seeker(self) -> None:
        if self._skills_search_timer:
            self._skills_search_timer.stop()
            self._skills_search_timer = None
        await self.query("SkillsSeekerView").remove()
        self.query_one(
            "#menu-panel"
        ).border_title = self._skills_prev_panel_title

        for sel, was_displayed in self._skills_prev_display.items():
            self.query_one(sel).display = was_displayed

        search = self.query_one("#search-input", Input)
        search.placeholder = self._skills_prev_placeholder
        with search.prevent(Input.Changed):
            search.value = ""

    def _make_info_button(self, item: dict, registry_data) -> InfoButton:
        return InfoButton(
            item["name"],
            item["description"],
            item["path"],
            item["is_script"],
            is_new=item.get("is_new", False),
            is_installed=is_registered_entry(item, registry_data),
            is_repo_entry=item.get("is_repo_entry", False),
            is_appstream_entry=item.get("is_appstream_entry", False),
            has_app_page=item.get("has_app_page", False),
            info=item,
            id=make_widget_id(item["path"]),
        )

    async def _render_items(self, items, *, lazy: bool = False) -> None:
        """Replace the items panel with new items.

        Only the latest request renders. A call that was superseded while
        waiting for the lock returns at once, and one in progress stops at
        its next chunk. The loading state is cleared and the registry is
        read again. Items are mounted in batches of ``RENDER_CHUNK_SIZE``.

        Args:
            items: Item dicts to show.
            lazy: True to mount only the first ``HOMEBREW_PAGE_SIZE``
                items and load the rest on scroll.
        """
        self._render_generation += 1
        generation = self._render_generation

        async with self._render_lock:
            if generation != self._render_generation:
                return

            self._set_items_loading(False)
            self._lazy_items = items if lazy else None
            self._lazy_loaded = 0
            left_panel = self.query_one("#left-panel-home", VerticalScroll)
            await left_panel.remove_children()
            self._registry_data = parse_registry_file()

            total = len(items)
            first = min(total, HOMEBREW_PAGE_SIZE) if lazy else total
            await self._mount_range(items, 0, first, generation)

    async def _mount_range(
        self, items, start: int, stop: int, generation: int
    ) -> None:
        """Mount ``items[start:stop]`` in batches.

        Must run with ``_render_lock`` held. Stops as soon as
        ``generation`` is no longer current, and updates ``_lazy_loaded``
        after each batch.
        """
        left_panel = self.query_one("#left-panel-home", VerticalScroll)
        for lo in range(start, stop, RENDER_CHUNK_SIZE):
            if generation != self._render_generation:
                return
            hi = min(lo + RENDER_CHUNK_SIZE, stop)
            buttons = [
                self._make_info_button(item, self._registry_data)
                for item in items[lo:hi]
            ]
            await left_panel.mount_all(buttons)
            self._lazy_loaded = hi

    def _on_items_scroll(self, scroll_y: float) -> None:
        """Load the next page when the list is scrolled near its end.

        Only lazy lists are paged. The load runs in an exclusive worker
        of the ``items-page`` group, and an error in it does not close
        the app.
        """
        if self._lazy_items is None or self._lazy_loaded >= len(
            self._lazy_items
        ):
            return
        panel = self.query_one("#left-panel-home", VerticalScroll)
        if scroll_y >= panel.max_scroll_y - SCROLL_LOAD_MARGIN:
            self.run_worker(
                self._load_next_page(),
                exclusive=True,
                group="items-page",
                exit_on_error=False,
            )

    async def _load_next_page(self) -> None:
        generation = self._render_generation
        async with self._render_lock:
            items = self._lazy_items
            if items is None or generation != self._render_generation:
                return
            start = self._lazy_loaded
            stop = min(len(items), start + HOMEBREW_PAGE_SIZE)
            if start >= stop:
                return
            await self._mount_range(items, start, stop, generation)

    def _set_items_loading(self, loading: bool) -> None:
        self.query_one("#left-panel-home", VerticalScroll).loading = loading

    async def _show_items_message(self, text: str) -> None:
        """Empty the items panel and show a persistent message."""
        await self._render_items([])
        await self.query_one("#left-panel-home", VerticalScroll).mount(
            Static(text)
        )

    @on(FocusableLabel.Pressed, "#report-bug")
    def handle_report_bug(self) -> None:
        self.app.push_screen(ReportBugDialog())

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button
        if not isinstance(button, InfoButton):
            return
        if self._is_about_showing:
            self._toggle_about_panel(force_hide=True)
            logo = self.query_one("#logo_lt")
            menu = self.query_one("#home-menu")
            menu_panel = self.query_one("#menu-panel")
            logo.display = True
            menu.display = True
            menu_panel.border_title = "Menu"
            self._is_about_showing = False

        if self.is_skills_seeker_showing:
            await self.action_go_back()

        script_path = button.path
        script_name = str(button.label)
        if (
            script_path.endswith("skills-seeker.sh")
            or script_name == "Skills Seeker"
        ):
            self.query_one("#logo_lt").display = False
            self.query_one("#home-menu").display = False
            await self._open_skills_seeker()
            return

        if button.info.get("is_aur_entry") or (
            button.is_repo_entry and button.has_app_page
        ):
            info = button.info
            if info is None:
                self.notify(
                    f"app_page: sem info | label={button.label!r}",
                    severity="warning",
                )
                return
            await show_app_page(
                self,
                info,
                translations=translations,
                featured=None,
                installed=button.is_installed,
            )
            return

        if button.is_script and self._is_app_page_showing:
            await hide_app_page(self)
        await self.handle_desc_button(button)

    async def on_app_page_widget_back_requested(
        self, message: AppPageWidget.BackRequested
    ) -> None:
        """Go back when the app page asks to leave (same as Escape)."""
        await self.action_go_back()

    def on_app_page_widget_url_requested(
        self, message: AppPageWidget.UrlRequested
    ) -> None:
        """Open the requested URL in the default browser."""
        self.app.open_url(message.url)

    def on_app_page_widget_translate_requested(
        self, message: AppPageWidget.TranslateRequested
    ) -> None:
        """Translate the page description in a thread worker.

        The worker is exclusive in the ``translate`` group. The target
        language comes from ``detect_system_language``, and
        ``message.target_language`` is not used.
        """
        page = self.query_one(AppPageWidget)
        self.run_worker(
            partial(self._translate_description, page, message.blocks),
            thread=True,
            exclusive=True,
            group="translate",
        )

    def _translate_description(self, page: AppPageWidget, blocks) -> None:
        """Translate a description and deliver it to the page.
        BLOCKING: thread worker (network).
        """
        target = (
            detect_system_language().split("-")[0].split("_")[0].casefold()
        )
        try:
            translated = load_cached_translation(
                page.script_info, blocks, target
            )
            if translated is None:
                translated = translate_description_blocks(blocks, target)
                save_cached_translation(
                    page.script_info, blocks, target, translated
                )
        except Exception:
            translated = None

        def deliver() -> None:
            if page.is_attached:
                page.set_translated_blocks(translated)

        self.app.call_from_thread(deliver)

    @on(AppPageWidget.InstallRequested)
    async def _on_app_page_install_requested(
        self, message: AppPageWidget.InstallRequested
    ) -> None:
        """Start the install requested by the app page."""
        if type(message) is not AppPageWidget.InstallRequested:
            return
        entry = message.script_info
        if str(entry.get("path", "")).startswith("aur://"):
            await self.run_appstream_aur_install(entry)
        else:
            self.run_appstream_install(message.script_info)

    @on(AppPageWidget.UninstallRequested)
    def _on_app_page_uninstall_requested(
        self, message: AppPageWidget.UninstallRequested
    ) -> None:
        """Start the removal requested by the app page."""
        self.run_appstream_uninstall(message.script_info)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-input":
            return

        query = event.value.strip()

        if self.is_skills_seeker_showing:
            self._schedule_skills_search(query)
            return

        if self._homebrew_view_active():
            if not self._homebrew_awaiting_refresh:
                self._schedule_homebrew_search(query)
            return

        if self._appimage_view_active():
            self._schedule_appimage_search(query)
            return

        if self._search_timer:
            self._search_timer.cancel()
        if not query:
            await self.action_reset_to_home()
            return

        loop = asyncio.get_running_loop()
        self._search_timer = loop.call_later(
            0.2,
            lambda: self.run_worker(
                lambda: self._execute_search_worker(query),
                thread=True,
                exclusive=True,
                name="search_filter",
            ),
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input" and self.is_skills_seeker_showing:
            for view in self.query("SkillsSeekerView"):
                view.focus_results()

    def _schedule_skills_search(self, query: str) -> None:
        """Run a skills search after 0.4 s without new input.
        The delay is longer than the other searches because each skills
        search is a network call.
        """
        if self._skills_search_timer:
            self._skills_search_timer.stop()
        self._skills_search_timer = self.set_timer(
            0.4, partial(self._run_skills_search, query)
        )

    def _run_skills_search(self, query: str) -> None:
        for view in self.query("SkillsSeekerView"):
            view.do_search(query)

    @on(AppPageWidget.ExtensionInstallRequested)
    def _on_app_page_extension_install_requested(
        self, message: AppPageWidget.ExtensionInstallRequested
    ) -> None:
        """Install the extension requested by the app page."""
        self.run_appstream_extension(message.info, remove=False)

    @on(AppPageWidget.ExtensionRemoveRequested)
    def _on_app_page_extension_remove_requested(
        self, message: AppPageWidget.ExtensionRemoveRequested
    ) -> None:
        """Remove the extension requested by the app page.

        ``message.record_id`` is not used.
        """
        self.run_appstream_extension(message.info, remove=True)

    def _execute_search_worker(self, query: str) -> None:
        # If cache is still warming on first keystroke, this ensures it finishes
        if not is_search_ready():
            warm_search_and_category_index(translations)

        items = search_scripts_fast(query)
        # Safely post back to main UI thread
        self.app.call_from_thread(self._render_search_results, items, query)

    async def _render_search_results(
        self, items: list[dict], query: str
    ) -> None:
        # Guard against out-of-order race conditions when typing quickly
        if self.query_one("#search-input", Input).value.strip() != query:
            return
        await self._render_items(items)

    def _home_items(self) -> list[dict]:
        """Top-level items: Specials button first, then the cached categories."""
        category_snapshot = [
            get_specials_root_item(translations),
            *get_categories(translations),
        ]
        if homebrew_catalog.enabled():
            category_snapshot.append(homebrew_category_info())
        category_snapshot.append(appimage_category_info())
        return category_snapshot

    async def action_go_back(self) -> None:
        if self._is_app_page_showing:
            await hide_app_page(self)
            return

        if self.is_skills_seeker_showing:
            await self._close_skills_seeker()
            self.query_one("#logo_lt").display = True
            self.query_one("#home-menu").display = True
            return

        if self._is_about_showing:
            self._toggle_about_panel(force_hide=True)
            logo = self.query_one("#logo_lt")
            menu = self.query_one("#home-menu")
            menu_panel = self.query_one("#menu-panel")
            logo.display = True
            menu.display = True
            menu_panel.border_title = "Menu"
            self._is_about_showing = False

        if not self._nav_stack:
            return
        self._nav_stack.pop()
        if self._nav_stack:
            current_path, _ = self._nav_stack[-1]
            if is_appimage_path(current_path):
                self._update_breadcrumb()
                await self._render_items([])
                self._set_items_loading(True)
                self._load_appimage_items()
                return
            await self._render_items(self._items_for_path(current_path))
        else:
            await self.action_reset_to_home()
            return
        self._update_breadcrumb()

    async def action_reset_to_home(self) -> None:
        if self.is_skills_seeker_showing:
            await self.action_go_back()
        self.query_one("#search-input", Input).value = ""
        self._nav_stack.clear()
        await self._render_items(self._home_items())
        self._update_breadcrumb()

    async def _refresh_fixed_ui_labels(self) -> None:
        """Rebuild the translated fixed texts.

        Redraws the search placeholder, the home menu and the link bar
        with the current translations, so a language change applies
        without restarting. Texts fixed at import time, such as the key
        bindings, are not refreshed.
        """
        self.query_one("#search-input", Input).placeholder = translations.get(
            "search_placeholder", "Search features"
        )
        menu = self.query_one("#home-menu", ListView)
        await menu.remove_children()
        await menu.mount(
            ListItem(
                Label(f"{translations.get('load_manifest', 'Load manifest')}"),
                id="manifest",
            )
        )
        await menu.mount(
            ListItem(
                Label(
                    f"{translations.get('select_language', 'Select language')}"
                ),
                id="language",
            )
        )
        await menu.mount(
            ListItem(
                Label(f"{translations.get('about', 'About')}"),
                id="about",
            )
        )
        await menu.mount(
            ListItem(
                Label(f"{translations.get('action_registry')}"),
                id="registry",
            )
        )
        await menu.mount(ListItem(Label("Update LinuxToys"), id="update"))
        await menu.mount(
            ListItem(
                Label(
                    f"{translations.get('scripts_resync', 'Scripts resync')}"
                ),
                id="scripts_resync",
            )
        )

        links_container = self.query_one(".home-links", Horizontal)
        await links_container.remove_children()
        await links_container.mount(
            Link("Wiki", url="https://linux.toys/documentation.html")
        )
        await links_container.mount(Static("│", classes="link-sep"))
        await links_container.mount(
            FocusableLabel(
                f"[u]{translations.get('report_label', 'Report Bug')}[/u]",
                id="report-bug",
                classes="report-bug",
            )
        )
        await links_container.mount(Static("│", classes="link-sep"))
        await links_container.mount(
            Link(
                f"{translations.get('devportal_label', 'Credits')}",
                url="https://dev.linux.toys",
            )
        )
        await links_container.mount(Static("│", classes="link-sep"))
        await links_container.mount(
            Link(
                f"{translations.get('support_footer', 'Support this project')}",
                url="https://ko-fi.com/psygreg",
            )
        )


class SplashScreen(Screen):
    """Minimal screen shown while the search cache is built.

    Shows a loading indicator and the translated "loading" text.
    """

    DEFAULT_CSS = """
    SplashScreen { align: center middle; }
    SplashScreen > Vertical { width: auto; height: auto; align: center middle; }
    SplashScreen LoadingIndicator { width: 24; height: 3; }
    SplashScreen Label { width: 100%; content-align: center middle; color: $text-muted; }
    """

    def compose(self):
        with Vertical():
            yield LoadingIndicator()
            yield Label(translations.get("loading", "Loading..."))


class LinuxToys(App):
    """Textual app of the LinuxToys TUI.

    Shows ``SplashScreen``, builds the search and category index in a
    background thread and then switches to ``HomeScreen``.
    """

    CSS_PATH = "style.tcss"
    TITLE = "LinuxToys"

    def on_mount(self) -> None:
        self.push_screen(SplashScreen())
        self._boot()

    @work(thread=True, exclusive=True, group="boot")
    def _boot(self) -> None:
        """Build the search and category index.

        BLOCKING: thread worker. A failure is logged and does not stop
        the app: without the cache, search is slower. It always goes on
        to ``_show_home``.
        """
        try:
            warm_search_and_category_index(translations)
        except Exception as e:  # noqa: BLE001
            self.log.error(f"warm index failed: {e}")
        self.call_from_thread(self._show_home)

    def _show_home(self) -> None:
        self.switch_screen(HomeScreen())


def main() -> int:
    """Run the TUI and return the process exit code."""
    LinuxToys().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
