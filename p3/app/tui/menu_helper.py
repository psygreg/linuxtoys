import asyncio

from app.easy_cli import is_dev_mode_enabled

from .about_helper import AboutWidget
from .dialog_screen import LanguageSelectorDialog
from .helper import (
    invalidate_search_caches,
    translations,
    warm_search_and_category_index,
)
from .manifest_dialog import ManifestDialog
from .registry_screen import RegistryScreen


class MenuSelectionMixin:
    """Mixin that handles main menu selection on the HomeScreen.

    Maps each menu item to its action: toggle the About panel, open
    the registry, resync the scripts, change the language, open the
    manifest dialog or check for updates.

    The host class must provide ``query``, ``query_one``, ``notify``,
    ``run_worker`` and ``app``, the widgets ``#menu-panel``,
    ``#logo_lt``, ``#home-menu`` and ``#terminal-conteiner``, and the
    methods ``_hide_terminal``, ``action_reset_to_home``,
    ``_refresh_fixed_ui_labels``, ``on_manifest_chosen`` and
    ``_trigger_update_check``.

    Attributes:
        _is_about_showing: Whether the About panel is currently
            replacing the main menu.
    """

    _is_about_showing: bool = False

    def on_list_view_selected(self, event) -> None:
        """
        Trata o item de menu selecionado e aciona a ação correspondente.
        """
        if event.item.id == "about":
            self._toggle_about_panel()
            return

        if self._is_about_showing:
            self._toggle_about_panel(force_hide=True)

        item_id = event.item.id
        action_map = {
            "registry": lambda: self.app.push_screen(RegistryScreen()),
            "scripts_resync": self._start_scripts_resync,
            "language": lambda: self.app.push_screen(
                LanguageSelectorDialog(), callback=self.apply_language_change
            ),
            "manifest": lambda: self.app.push_screen(
                ManifestDialog(), callback=self.on_manifest_chosen
            ),
            "update": self._trigger_update_check,
        }

        if item_id in action_map:
            action_map[item_id]()

    def _toggle_about_panel(self, force_hide: bool = False) -> None:
        """Show or hide the About panel in place of the main menu.

        Hides the embedded terminal first if it is visible. When
        shown, hides the logo and the menu, mounts an ``AboutWidget``
        in ``#menu-panel`` and sets the panel title. When hidden,
        removes the widget and brings the logo and menu back.

        Args:
            force_hide: If True, always hide the panel instead of
                toggling it.
        """
        menu_panel = self.query_one("#menu-panel")
        logo = self.query_one("#logo_lt")
        home_menu = self.query_one("#home-menu")
        terminal_container = self.query_one("#terminal-conteiner")

        if terminal_container.display:
            self._hide_terminal()

        should_show = not self._is_about_showing
        if force_hide:
            should_show = False

        self._is_about_showing = should_show
        logo.display = not should_show
        home_menu.display = not should_show

        if should_show:
            about_widget = AboutWidget(id="about-content")
            menu_panel.mount(about_widget)
            menu_panel.border_title = translations.get(
                "about_title", "About LinuxToys"
            )
            about_widget.scroll_visible()
        else:
            about_content = self.query("#about-content")
            if about_content:
                about_content.remove()

    def _start_scripts_resync(self) -> None:
        """Start a background resync of the scripts.

        In developer mode the sync is skipped (with a warning) so
        local script edits are not overwritten. Otherwise it notifies
        the user and runs ``_resync_scripts_worker`` as an exclusive
        thread worker.
        """
        if is_dev_mode_enabled():
            self.notify(
                "Modo de desenvolvedor ativo — sincronização de scripts foi pulada.",
                severity="warning",
            )
            return

        self.notify("Sincronizando scripts...", timeout=3)
        self.run_worker(
            self._resync_scripts_worker,
            thread=True,
            exclusive=True,
            name="scripts_resync",
        )

    def _resync_scripts_worker(self) -> None:
        """Force-update the scripts and report progress to the UI.

        Runs in a worker thread. Calls ``force_update_scripts`` and
        shows each progress key, translated through ``translations``,
        as a notification on the UI thread. When it ends,
        ``_on_scripts_resync_done`` receives the result.
        """
        from app.git_scripts_manager import force_update_scripts

        def progress(key: str) -> None:
            message = translations.get(key, key)
            self.app.call_from_thread(self.notify, message, timeout=3)

        try:
            success = force_update_scripts(progress_callback=progress)
            if success:
                invalidate_search_caches()
                warm_search_and_category_index(translations)
        except Exception:
            success = False
        self.app.call_from_thread(self._on_scripts_resync_done, success)

    def _on_scripts_resync_done(self, success: bool) -> None:
        """Handle the end of the scripts resync.

        Runs on the UI thread. On success, notifies,
        returns to the home screen so the menu shows the updated scripts.

        Args:
            success: Whether the resync worked.
        """
        if success:
            self.notify(
                "Scripts sincronizados com sucesso.", severity="information"
            )
            self.run_worker(self.action_reset_to_home())
        else:
            self.notify(
                "Não foi possível sincronizar os scripts agora.",
                severity="warning",
            )

    async def apply_language_change(
        self, new_language_code: str | None
    ) -> None:
        """Apply a language change to the whole application.

        Loads the new translations and updates the shared
        ``translations`` dict in place, so every module that imports
        it sees the new strings. Then persists the choice, rebuilds
        the search and category caches, resets to the home screen and
        refreshes the fixed UI labels. Used as the callback of
        ``LanguageSelectorDialog``.

        Args:
            new_language_code: Short language code (e.g. ``"pt"``),
                or None if the dialog was dismissed without a choice,
                in which case nothing happens.
        """
        if new_language_code is None:
            return

        from app import lang_utils

        new_translations = lang_utils.load_translations(new_language_code)
        translations.clear()
        translations.update(new_translations)
        lang_utils.save_language(new_language_code)
        invalidate_search_caches()
        await asyncio.to_thread(warm_search_and_category_index, translations)

        await self.action_reset_to_home()
        await self._refresh_fixed_ui_labels()
