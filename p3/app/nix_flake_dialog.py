"""GTK dialog for importing a Nix flake into Home Manager or NixOS."""

from __future__ import annotations

import threading

from . import nix_catalog, nix_flakes
from .gtk_common import GLib, Gtk
from .gtk_dialogs import run_message_dialog


class NixFlakeDialog(Gtk.Dialog):
    """Inspect one flake, select its outputs and queue the configuration merge."""

    def __init__(self, parent_window):
        self.translations = getattr(parent_window, "translations", {})
        super().__init__(
            title=self._t("nix_flake_import_title", "Import Nix flake"),
            transient_for=parent_window,
            modal=True,
        )
        self.set_default_size(780, 680)
        self.parent_window = parent_window
        self.info = None
        self.result_script = None
        self._checkboxes = {}
        self._scope_values = []
        self._read_running = False
        self._destroyed = False
        self.connect("destroy", self._on_destroy)
        self._build()

    def _on_destroy(self, _widget):
        self._destroyed = True

    def _t(self, key, fallback):
        return self.translations.get(key, fallback)

    def _build(self):
        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.set_margin_top(18)
        content.set_margin_bottom(12)

        intro = Gtk.Label(
            label=self._t(
                "nix_flake_import_intro",
                "Import a flake from a URL or a local directory. LinuxToys "
                "will inspect its outputs and merge the selected packages, "
                "modules or overlays into the chosen Nix configuration.",
            ),
            xalign=0,
        )
        intro.set_line_wrap(True)
        content.pack_start(intro, False, False, 0)

        warning = Gtk.Label(
            label=self._t(
                "nix_flake_import_warning",
                "Only import flakes you trust: their modules, packages and "
                "overlays become part of your configuration.",
            ),
            xalign=0,
        )
        warning.set_line_wrap(True)
        warning.get_style_context().add_class("dim-label")
        content.pack_start(warning, False, False, 0)

        ref_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.reference_entry = Gtk.Entry()
        self.reference_entry.set_placeholder_text(
            self._t(
                "nix_flake_reference_placeholder",
                "github:owner/repo, git+https://… or /path/to/flake",
            )
        )
        self.reference_entry.connect("activate", self._on_read_clicked)
        ref_box.pack_start(self.reference_entry, True, True, 0)
        self.read_button = Gtk.Button(
            label=self._t("nix_flake_read", "Read flake")
        )
        self.read_button.connect("clicked", self._on_read_clicked)
        ref_box.pack_start(self.read_button, False, False, 0)
        content.pack_start(ref_box, False, False, 0)

        self.status_label = Gtk.Label(label="", xalign=0)
        self.status_label.set_line_wrap(True)
        self.status_label.get_style_context().add_class("dim-label")
        content.pack_start(self.status_label, False, False, 0)

        scope_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        scope_box.pack_start(
            Gtk.Label(label=self._t("nix_flake_scope", "Install for:")),
            False,
            False,
            0,
        )
        self.scope_combo = Gtk.ComboBoxText()
        self.scope_combo.connect("changed", self._on_scope_changed)
        scope_box.pack_start(self.scope_combo, False, False, 0)
        content.pack_start(scope_box, False, False, 0)

        self.description_label = Gtk.Label(label="", xalign=0)
        self.description_label.set_line_wrap(True)
        self.description_label.get_style_context().add_class("dim-label")
        content.pack_start(self.description_label, False, False, 0)

        self.options_frame = Gtk.Frame(
            label=self._t("nix_flake_outputs", "Flake outputs")
        )
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(260)
        self.options_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8
        )
        self.options_box.set_margin_start(10)
        self.options_box.set_margin_end(10)
        self.options_box.set_margin_top(10)
        self.options_box.set_margin_bottom(10)
        scroller.add(self.options_box)
        self.options_frame.add(scroller)
        content.pack_start(self.options_frame, True, True, 0)

        self.imports_frame = Gtk.Frame(
            label=self._t("nix_flake_existing", "Imported flakes")
        )
        self.imports_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=6
        )
        self.imports_box.set_margin_start(10)
        self.imports_box.set_margin_end(10)
        self.imports_box.set_margin_top(8)
        self.imports_box.set_margin_bottom(8)
        self.imports_frame.add(self.imports_box)
        content.pack_start(self.imports_frame, False, False, 0)

        self.add_button(
            self._t("cancel_btn_label", "Cancel"), Gtk.ResponseType.CANCEL
        )
        action_area = self.get_action_area()
        self.import_button = Gtk.Button(
            label=self._t("nix_flake_import", "Import")
        )
        self.import_button.get_style_context().add_class("suggested-action")
        self.import_button.connect("clicked", self._on_import_clicked)
        action_area.pack_start(self.import_button, False, False, 0)

        self._set_ready(False)
        self.show_all()
        self._refresh_existing_imports()

    def _set_ready(self, ready):
        self.import_button.set_sensitive(bool(ready))

    def _on_read_clicked(self, _widget=None):
        if self._read_running:
            return
        reference = self.reference_entry.get_text().strip()
        if not reference:
            self.status_label.set_text(
                self._t("nix_flake_reference_required", "Enter a flake reference.")
            )
            return
        self._read_running = True
        self.read_button.set_sensitive(False)
        self.import_button.set_sensitive(False)
        self.status_label.set_text(
            self._t("nix_flake_reading", "Inspecting the flake…")
        )

        def worker():
            try:
                info = nix_flakes.inspect(reference)
            except Exception as error:  # surface the exact refusal
                message = str(error)
                if not self._destroyed:
                    GLib.idle_add(self._on_read_failed, message)
            else:
                if not self._destroyed:
                    GLib.idle_add(self._on_read_succeeded, info)

        threading.Thread(
            target=worker,
            daemon=True,
            name="linuxtoys-nix-flake-inspect",
        ).start()

    def _on_read_failed(self, message):
        if self._destroyed:
            return False
        self._read_running = False
        self.read_button.set_sensitive(True)
        self.info = None
        self._checkboxes = {}
        self._clear_box(self.options_box)
        self.description_label.set_text("")
        self.scope_combo.remove_all()
        self._scope_values = []
        self.status_label.set_text(message)
        self._set_ready(False)
        return False

    def _on_read_succeeded(self, info):
        if self._destroyed:
            return False
        self._read_running = False
        self.read_button.set_sensitive(True)
        self.info = info
        description = str(info.get("description") or "").strip()
        self.description_label.set_text(description)
        self.status_label.set_text("")
        self._build_options()
        self._populate_scopes()
        self._refresh_existing_imports()
        self._update_scope_sensitivity()
        self.options_box.show_all()
        self.imports_box.show_all()
        if not self._scope_values:
            self.status_label.set_text(
                self._t(
                    "nix_flake_no_scope",
                    "Neither Home Manager nor a NixOS system configuration is available.",
                )
            )
        elif not any(
            option.get("selectable")
            for option in info.get("options") or ()
        ):
            self.status_label.set_text(
                self._t(
                    "nix_flake_no_outputs",
                    "This flake has no outputs LinuxToys can merge into a Nix configuration.",
                )
            )
        return False

    def _clear_box(self, box):
        for child in box.get_children():
            box.remove(child)

    def _build_options(self):
        self._checkboxes = {}
        self._clear_box(self.options_box)
        if not self.info:
            return
        groups = []
        seen = set()
        for option in self.info.get("options") or ():
            group = str(option.get("group") or "")
            if group and group not in seen:
                seen.add(group)
                groups.append(group)
        for group in groups:
            label = Gtk.Label(xalign=0)
            label.set_markup(f"<b>{GLib.markup_escape_text(group)}</b>")
            self.options_box.pack_start(label, False, False, 0)
            for option in self.info.get("options") or ():
                if str(option.get("group") or "") != group:
                    continue
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                check = Gtk.CheckButton(label=str(option.get("label") or ""))
                check.set_sensitive(bool(option.get("selectable")))
                if not option.get("selectable"):
                    check.set_tooltip_text(
                        self._t(
                            "nix_flake_not_merged",
                            "This output cannot be merged into the configuration.",
                        )
                    )
                else:
                    check.set_active(nix_flakes.default_selected(option))
                self._checkboxes[str(option.get("key"))] = check
                box.pack_start(check, False, False, 0)
                self.options_box.pack_start(box, False, False, 0)

    def _populate_scopes(self):
        self.scope_combo.remove_all()
        self._scope_values = []
        if self.info.get("home_manager"):
            self.scope_combo.append_text(self._t("nix_flake_scope_home", "Home Manager"))
            self._scope_values.append("home-manager")
        if self.info.get("system_scope"):
            self.scope_combo.append_text(self._t("nix_flake_scope_system", "System (NixOS)"))
            self._scope_values.append("system")
        if self._scope_values:
            self.scope_combo.set_active(0)

    def _current_scope(self):
        index = self.scope_combo.get_active()
        if 0 <= index < len(self._scope_values):
            return self._scope_values[index]
        return ""

    def _on_scope_changed(self, _combo):
        self._update_scope_sensitivity()

    def _update_scope_sensitivity(self):
        scope = self._current_scope()
        for option in (self.info or {}).get("options") or ():
            check = self._checkboxes.get(str(option.get("key")))
            if check is None or not option.get("selectable"):
                continue
            option_scope = str(option.get("scope") or "both")
            matches = option_scope in ("both", scope)
            check.set_sensitive(matches)
        self._set_ready(bool(scope) and bool(self._selected_keys()))

    def _selected_keys(self):
        return [
            key
            for key, check in self._checkboxes.items()
            if check.get_active() and check.get_sensitive()
        ]

    def _on_import_clicked(self, _button):
        if not self.info:
            return
        scope = self._current_scope()
        if not scope:
            self.status_label.set_text(
                self._t(
                    "nix_flake_no_scope",
                    "Neither Home Manager nor a NixOS system configuration is available.",
                )
            )
            return
        keys = self._selected_keys()
        if not keys:
            self.status_label.set_text(
                self._t(
                    "nix_flake_select_output",
                    "Select at least one output to import.",
                )
            )
            return
        try:
            nix_flakes.add_import(self.info, scope, keys)
            script = nix_flakes.materialize_apply(scope)
        except Exception as error:
            run_message_dialog(
                self,
                title=self._t("nix_flake_import_title", "Import Nix flake"),
                secondary_text=str(error),
                message_type=Gtk.MessageType.ERROR,
                buttons=[("OK", Gtk.ResponseType.OK)],
                default_response=Gtk.ResponseType.OK,
            )
            return
        self.result_script = script
        self.response(Gtk.ResponseType.OK)

    def _refresh_existing_imports(self):
        self._clear_box(self.imports_box)
        try:
            records = nix_flakes.imports()
        except Exception:
            records = []
        if not records:
            self.imports_frame.hide()
            return
        self.imports_frame.show()
        for record in records:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            label = Gtk.Label(
                label=f"{record.get('description') or record.get('reference')} "
                f"({record.get('scope')})",
                xalign=0,
            )
            label.set_line_wrap(True)
            row.pack_start(label, True, True, 0)
            remove = Gtk.Button(label=self._t("nix_flake_remove", "Remove"))
            remove.connect("clicked", self._on_remove_clicked, record)
            row.pack_start(remove, False, False, 0)
            self.imports_box.pack_start(row, False, False, 0)
            row.show_all()

    def _on_remove_clicked(self, _button, record):
        try:
            script = nix_flakes.materialize_removal(record)
        except Exception as error:
            run_message_dialog(
                self,
                title=self._t("nix_flake_import_title", "Import Nix flake"),
                secondary_text=str(error),
                message_type=Gtk.MessageType.ERROR,
                buttons=[("OK", Gtk.ResponseType.OK)],
                default_response=Gtk.ResponseType.OK,
            )
            return
        self.result_script = script
        self.response(Gtk.ResponseType.OK)


def show_import_dialog(parent_window):
    """Run the dialog and open the generated merge script in the terminal."""
    if not nix_catalog.enabled():
        run_message_dialog(
            parent_window,
            title="Nix",
            secondary_text="Nix is not available on this system.",
            message_type=Gtk.MessageType.WARNING,
            buttons=[("OK", Gtk.ResponseType.OK)],
            default_response=Gtk.ResponseType.OK,
        )
        return
    dialog = NixFlakeDialog(parent_window)
    response = dialog.run()
    script = dialog.result_script
    dialog.destroy()
    if response == Gtk.ResponseType.OK and script is not None:
        parent_window.open_term_view([script], auto_run=True)
