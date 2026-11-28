"""GTK dialog for managing Home Manager and NixOS system generations."""

from __future__ import annotations

import threading
from typing import Any

from . import nix_catalog, nix_generations
from .gtk_common import GLib, Gtk
from .gtk_dialogs import run_message_dialog
from .lang_utils import create_translator


class NixGenerationsDialog(Gtk.Dialog):
    """List recorded generations and hand activation/deletion to a terminal."""

    def __init__(self, parent_window: Any) -> None:
        self.translations = getattr(parent_window, "translations", {})
        super().__init__(
            title=self._t("nix_generations_title", "Nix generations"),
            transient_for=parent_window,
            modal=True,
        )
        self.set_default_size(760, 620)
        self.parent_window = parent_window
        self.result_script: dict[str, Any] | None = None
        self._destroyed = False
        self._load_running = False
        self._load_token = 0
        self._pages: dict[str, dict[str, Any]] = {}
        self._scopes: tuple[str, ...] = nix_generations.available_scopes()
        self.connect("destroy", self._on_destroy)
        self._build()

    def _on_destroy(self, _widget: Any) -> None:
        self._destroyed = True

    def _t(self, key: str, fallback: str) -> str:
        return self.translations.get(key, fallback)

    def _scope_name(self, scope: str) -> str:
        if scope == nix_generations.HOME_SCOPE:
            return self._t("nix_generations_home", "Home Manager")
        return self._t("nix_generations_system", "NixOS system")

    def _build(self) -> None:
        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.set_margin_top(18)
        content.set_margin_bottom(12)

        intro = Gtk.Label(
            label=self._t(
                "nix_generations_intro",
                "Manage the recorded Home Manager and NixOS system "
                "generations. Activating an older generation rolls back "
                "to it; deleting removes the generation record.",
            ),
            xalign=0,
        )
        intro.set_line_wrap(True)
        content.pack_start(intro, False, False, 0)

        if self._scopes:
            self.notebook = Gtk.Notebook()
            self.notebook.set_vexpand(True)
            for scope in self._scopes:
                self.notebook.append_page(
                    self._build_page(scope),
                    Gtk.Label(label=self._scope_name(scope)),
                )
            content.pack_start(self.notebook, True, True, 0)
        else:
            empty = Gtk.Label(
                label=self._t("nix_generations_empty", "No generations found."),
                xalign=0,
            )
            empty.set_line_wrap(True)
            empty.get_style_context().add_class("dim-label")
            content.pack_start(empty, False, False, 0)

        action_area = self.get_action_area()
        self.refresh_button = Gtk.Button(
            label=self._t("nix_generations_refresh", "Refresh")
        )
        self.refresh_button.connect("clicked", self._on_refresh_clicked)
        self.refresh_button.set_sensitive(bool(self._scopes))
        action_area.pack_start(self.refresh_button, False, False, 0)
        self.add_button(
            self._t("script_runner_close", "Close"), Gtk.ResponseType.CLOSE
        )

        self.show_all()
        if self._scopes:
            GLib.idle_add(self._refresh)

    def _build_page(self, scope: str) -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        status = Gtk.Label(label="", xalign=0)
        status.set_line_wrap(True)
        # Keep an empty status line from reserving height between the notebook
        # tabs and the generation list; it is shown only when it has a message.
        status.set_no_show_all(True)
        status.get_style_context().add_class("dim-label")
        page.pack_start(status, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        # The theme's list padding leaves a small blank band above the first
        # generation and below the last one; keep this list flush with the
        # notebook page instead.
        listbox.get_style_context().add_class("nix-generations-list")
        scroller.add(listbox)
        page.pack_start(scroller, True, True, 0)

        self._pages[scope] = {"status": status, "list": listbox}
        return page

    def _on_refresh_clicked(self, _button: Any) -> None:
        self._refresh()

    @staticmethod
    def _set_status(page: dict[str, Any], text: str) -> None:
        """Show a status message, or hide the label when there is nothing to say."""
        page["status"].set_text(text)
        if text:
            page["status"].show()
        else:
            page["status"].hide()

    def _refresh(self) -> bool:
        if self._destroyed or self._load_running or not self._scopes:
            return False
        self._load_running = True
        self._load_token += 1
        token = self._load_token
        self.refresh_button.set_sensitive(False)
        for page in self._pages.values():
            self._set_status(
                page,
                self._t("nix_generations_loading", "Loading generations…"),
            )
            self._clear_box(page["list"])

        def worker():
            try:
                data = nix_generations.scan()
            except Exception as error:  # surface the exact read failure
                data = {"__error__": str(error)}
            GLib.idle_add(self._on_loaded, token, data)

        threading.Thread(
            target=worker,
            daemon=True,
            name="linuxtoys-nix-generations",
        ).start()
        return False

    def _clear_box(self, box: Gtk.Box) -> None:
        for child in box.get_children():
            box.remove(child)

    def _on_loaded(self, token: int, data: Any) -> bool:
        if self._destroyed or token != self._load_token:
            return False
        self._load_running = False
        self.refresh_button.set_sensitive(True)
        global_error = str((data or {}).get("__error__") or "")
        for scope, page in self._pages.items():
            if global_error:
                self._set_status(
                    page,
                    self._t(
                        "nix_generations_load_failed",
                        "Could not read Nix generations: {error}",
                    ).format(error=global_error),
                )
                continue
            entry = data.get(scope) or {}
            error = str(entry.get("error") or "")
            if error:
                self._set_status(
                    page,
                    self._t(
                        "nix_generations_load_failed",
                        "Could not read Nix generations: {error}",
                    ).format(error=error),
                )
                continue
            generations = entry.get("generations") or []
            if not generations:
                self._set_status(
                    page,
                    self._t("nix_generations_empty", "No generations found."),
                )
                continue
            self._set_status(page, "")
            for record in generations:
                page["list"].add(self._build_row(scope, record))
            page["list"].show_all()
        return False

    def _build_row(
        self, scope: str, record: dict[str, Any]
    ) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_activatable(False)
        row.set_selectable(False)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(xalign=0)
        label = self._t(
            "nix_generations_generation", "Generation {generation}"
        ).format(generation=int(record.get("id") or 0))
        title.set_markup(f"<b>{GLib.markup_escape_text(label)}</b>")
        info.pack_start(title, False, False, 0)

        meta = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        date_label = Gtk.Label(label=str(record.get("date") or ""), xalign=0)
        date_label.get_style_context().add_class("dim-label")
        meta.pack_start(date_label, False, False, 0)
        is_current = bool(record.get("current"))
        if is_current:
            current_label = Gtk.Label(
                label=self._t("nix_generations_current", "Current")
            )
            current_label.get_style_context().add_class("accent")
            meta.pack_start(current_label, False, False, 0)
        info.pack_start(meta, False, False, 0)
        box.pack_start(info, True, True, 0)

        activate = Gtk.Button(
            label=self._t("nix_generations_activate", "Activate")
        )
        activate.connect("clicked", self._on_action, scope, record, "activate")
        delete = Gtk.Button(label=self._t("nix_generations_delete", "Delete"))
        delete.get_style_context().add_class("destructive-action")
        delete.connect("clicked", self._on_action, scope, record, "delete")
        if is_current:
            tooltip = self._t(
                "nix_generations_current_tooltip",
                "This generation is already current.",
            )
            activate.set_sensitive(False)
            activate.set_tooltip_text(tooltip)
            delete.set_sensitive(False)
            delete.set_tooltip_text(tooltip)
        box.pack_start(activate, False, False, 0)
        box.pack_start(delete, False, False, 0)
        row.add(box)
        return row

    def _on_action(
        self,
        _button: Any,
        scope: str,
        record: dict[str, Any],
        action: str,
    ) -> None:
        generation = int(record.get("id") or 0)
        if generation <= 0:
            return
        scope_name = self._scope_name(scope)
        if action == "activate":
            title = self._t(
                "nix_generations_activate_confirm_title",
                "Activate generation",
            )
            message = self._t(
                "nix_generations_activate_confirm_message",
                "Activate generation {generation} ({scope})? The running "
                "configuration will be replaced.",
            ).format(generation=generation, scope=scope_name)
            action_label = self._t("nix_generations_activate", "Activate")
            buttons = [
                (
                    self._t("cancel_btn_label", "Cancel"),
                    Gtk.ResponseType.CANCEL,
                ),
                (action_label, Gtk.ResponseType.OK),
            ]
        else:
            title = self._t(
                "nix_generations_delete_confirm_title", "Delete generation"
            )
            message = self._t(
                "nix_generations_delete_confirm_message",
                "Delete generation {generation} ({scope})? The generation "
                "record is removed; Nix garbage collection frees the store "
                "paths later.",
            ).format(generation=generation, scope=scope_name)
            action_label = self._t("nix_generations_delete", "Delete")
            buttons = [
                (
                    self._t("cancel_btn_label", "Cancel"),
                    Gtk.ResponseType.CANCEL,
                ),
                (
                    action_label,
                    Gtk.ResponseType.OK,
                    "destructive-action",
                ),
            ]

        response = run_message_dialog(
            self,
            title=title,
            secondary_text=message,
            message_type=Gtk.MessageType.WARNING,
            buttons=buttons,
            default_response=Gtk.ResponseType.CANCEL,
        )
        if response != Gtk.ResponseType.OK:
            return

        try:
            if action == "activate":
                script = nix_generations.materialize_switch(
                    scope,
                    generation,
                    name=self._t(
                        "nix_generations_activate_action",
                        "Activate Nix generation {generation}",
                    ).format(generation=generation),
                    description=self._t(
                        "nix_generations_activate_action_desc",
                        "Activate this Nix generation and rebuild the running "
                        "configuration from it.",
                    ),
                )
            else:
                script = nix_generations.materialize_delete(
                    scope,
                    generation,
                    name=self._t(
                        "nix_generations_delete_action",
                        "Delete Nix generation {generation}",
                    ).format(generation=generation),
                    description=self._t(
                        "nix_generations_delete_action_desc",
                        "Delete this Nix generation record.",
                    ),
                )
        except Exception as error:
            run_message_dialog(
                self,
                title=self._t("nix_generations_title", "Nix generations"),
                secondary_text=str(error),
                message_type=Gtk.MessageType.ERROR,
                buttons=[("OK", Gtk.ResponseType.OK)],
                default_response=Gtk.ResponseType.OK,
            )
            return
        self.result_script = script
        self.response(Gtk.ResponseType.OK)


def show_generations_dialog(parent_window: Any) -> None:
    """Run the dialog and open the chosen generation action in a terminal."""
    _ = create_translator()
    if not nix_catalog.enabled():
        run_message_dialog(
            parent_window,
            title=_("nix_generations_title"),
            secondary_text=_("nix_generations_unavailable"),
            message_type=Gtk.MessageType.WARNING,
            buttons=[(_("script_runner_close"), Gtk.ResponseType.CLOSE)],
            default_response=Gtk.ResponseType.CLOSE,
        )
        return
    dialog = NixGenerationsDialog(parent_window)
    response = dialog.run()
    script = dialog.result_script
    dialog.destroy()
    if response == Gtk.ResponseType.OK and script is not None:
        parent_window.open_term_view([script], auto_run=True)
