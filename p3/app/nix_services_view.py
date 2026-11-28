"""Embedded app-page view for configurable NixOS services.

A catalog attribute that maps to a NixOS service module is installed through
``services.<name>`` instead of ``pkgs.<name>``. The view edits the service's
safe option subset (booleans, enums, strings, numbers and string lists) and
queues the selection in the persistent Nix queue. Option values that were not
touched resolve to the current nixpkgs defaults, so the widgets always show the
service's actual effective state.
"""

from __future__ import annotations

import json
import logging

from . import nix_queue, nix_services
from .gtk_common import GLib, Gtk, resolve_symbolic_icon

logger = logging.getLogger(__name__)


class NixServicesView(Gtk.ScrolledWindow):
    """Service options page that consumes the Stack's width without setting it."""

    def do_get_preferred_width(self):
        return (0, 0)

    def do_get_preferred_width_for_height(self, height):
        return (0, 0)

    def __init__(self, parent, source_info):
        super().__init__()
        self.parent_window = parent
        self.source_info = dict(source_info)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.content.set_margin_start(32)
        self.content.set_margin_end(32)
        self.content.set_margin_top(18)
        self.content.set_margin_bottom(18)
        self.add(self.content)

        self._header = Gtk.Label()
        self._header.set_halign(Gtk.Align.START)
        self._header.set_xalign(0.0)
        self._header.set_line_wrap(True)
        self.content.pack_start(self._header, False, False, 0)

        self._status = Gtk.Label()
        self._status.set_halign(Gtk.Align.START)
        self._status.set_xalign(0.0)
        self._status.set_line_wrap(True)
        self.content.pack_start(self._status, False, False, 0)

        self._options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.content.pack_start(self._options_box, False, False, 0)

        self._empty = Gtk.Label()
        self._empty.set_halign(Gtk.Align.START)
        self._empty.set_xalign(0.0)
        self._empty.set_line_wrap(True)
        self.content.pack_start(self._empty, False, False, 0)

        self._note = Gtk.Label()
        self._note.set_halign(Gtk.Align.START)
        self._note.set_xalign(0.0)
        self._note.set_line_wrap(True)
        self._note.get_style_context().add_class("dim-label")
        self.content.pack_start(self._note, False, False, 0)

        self._save_button = Gtk.Button()
        self._save_label = ""
        self._set_save_button_content(
            self._t("nix_service_save_options", "Save service options")
        )
        self._save_button.set_halign(Gtk.Align.START)
        self._save_button.connect("clicked", self._save)
        self.content.pack_start(self._save_button, False, False, 0)

        self._widgets = {}
        self._option_meta = {}
        self._original_values = {}
        self._dirty = set()
        self._signature = None
        self._populated = False

    def _t(self, key, fallback):
        return self.parent_window.translations.get(key, fallback)

    def _set_save_button_content(self, label):
        child = self._save_button.get_child()
        if child is not None:
            self._save_button.remove(child)
        self._save_label = label
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.pack_start(
            Gtk.Image.new_from_icon_name(
                resolve_symbolic_icon("document-save-symbolic"),
                Gtk.IconSize.BUTTON,
            ),
            False,
            False,
            0,
        )
        box.pack_start(Gtk.Label(label=label), False, False, 0)
        self._save_button.add(box)
        self._save_button.get_style_context().add_class("suggested-action")
        self._save_button.show_all()

    def ensure_populated(self):
        """Populate option state/rows only when the tab is first shown."""
        if self._populated:
            return
        self._populated = True
        self.refresh()

    def refresh(self):
        try:
            state = nix_services.service_state(self.source_info)
        except Exception as error:
            logger.warning("Could not read Nix service state: %s", error)
            state = None
        if state is None:
            self.hide()
            return
        self.show()
        service = state["service"]
        options = state["options"]
        signature = json.dumps(
            {
                "name": state["name"],
                "status": state["status"],
                "options": [
                    [
                        option["path"],
                        option["kind"],
                        option["value"],
                        option.get("choices") or [],
                        bool(option.get("stale")),
                    ]
                    for option in options
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        description = str(service.get("description") or "").strip()
        level = (
            self._t("nix_service_level_user", "User service (Home Manager)")
            if state.get("scope") == "home-manager"
            else self._t("nix_service_level_system", "System service (NixOS)")
        )
        self._header.set_markup(
            f"<b>{GLib.markup_escape_text(service['name'])}</b>\n"
            f"<small>{GLib.markup_escape_text(level)}</small>"
            + (
                f"\n{GLib.markup_escape_text(description)}"
                if description
                else ""
            )
        )
        self._status.set_text(self._status_text(state))
        if signature != self._signature:
            self._signature = signature
            self._rebuild(options)
        has_options = bool(options)
        self._empty.set_text(
            ""
            if has_options
            else self._t(
                "nix_service_no_options",
                "This service has no configurable options.",
            )
        )
        self._empty.set_visible(not has_options)
        self._note.set_text(
            self._t(
                "nix_service_apply_note",
                "Changes take effect after applying the queued Nix operations.",
            )
            if has_options
            else ""
        )
        self._note.set_visible(has_options)
        show_action = state["status"] == "available" or has_options
        if show_action:
            label = (
                self._t("nix_service_install", "Install service")
                if state["status"] == "available" and not has_options
                else self._t(
                    "nix_service_save_options", "Save service options"
                )
            )
            if label != self._save_label:
                self._set_save_button_content(label)
        self._save_button.set_visible(show_action)
        self._save_button.set_sensitive(
            show_action and state["status"] != "removing"
        )
        self.show_all()
        self._empty.set_visible(not has_options)
        self._note.set_visible(has_options)
        self._save_button.set_visible(show_action)

    def _status_text(self, state):
        status = state["status"]
        if status == "installed":
            return self._t("app_page_installed", "Installed")
        if status == "removing":
            return self._t("nix_extension_remove_queued", "Waiting to remove")
        if status == "queued":
            return self._t("queued", "Waiting to install")
        return self._t(
            "nix_service_not_installed",
            "Not installed.",
        )

    def _rebuild(self, options):
        for child in list(self._options_box.get_children()):
            self._options_box.remove(child)
            child.destroy()
        self._widgets = {}
        self._option_meta = {}
        self._original_values = {}
        self._dirty = set()
        for option in options:
            self._option_meta[option["path"]] = option
            self._original_values[option["path"]] = option.get("value")
            self._options_box.pack_start(
                self._option_row(option), False, False, 0
            )
        self._options_box.show_all()

    def _option_row(self, option):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0.0)
        label.set_markup(
            f"<b>{GLib.markup_escape_text(option['path'])}</b>"
        )
        text_box.pack_start(label, False, False, 0)
        description = str(option.get("description") or "").strip()
        if description:
            hint = Gtk.Label()
            hint.set_halign(Gtk.Align.START)
            hint.set_xalign(0.0)
            hint.set_line_wrap(True)
            hint.get_style_context().add_class("dim-label")
            hint.set_markup(GLib.markup_escape_text(description))
            text_box.pack_start(hint, False, False, 0)
        row.pack_start(text_box, True, True, 0)

        kind = option["kind"]
        value = option.get("value")
        if kind == "bool":
            widget = Gtk.Switch()
            widget.set_active(bool(value))
            widget.set_valign(Gtk.Align.CENTER)
        elif kind == "enum":
            widget = Gtk.ComboBoxText()
            choices = [str(choice) for choice in option.get("choices") or ()]
            for choice in choices:
                widget.append(choice, choice)
            current = "" if value is None else str(value)
            if current and current not in choices:
                widget.append(current, current)
            if current:
                widget.set_active_id(current)
            widget.set_valign(Gtk.Align.CENTER)
        else:
            widget = Gtk.Entry()
            widget.set_hexpand(False)
            widget.set_width_chars(28)
            widget.set_text(self._format_value(kind, value))
            widget.set_placeholder_text(
                self._t("nix_service_value_placeholder", "Value")
            )
            widget.set_valign(Gtk.Align.CENTER)
        self._widgets[option["path"]] = (kind, widget)
        if kind == "bool":
            widget.connect(
                "notify::active",
                lambda *_args, path=option["path"]: self._dirty.add(path),
            )
        elif kind == "enum":
            widget.connect(
                "changed",
                lambda *_args, path=option["path"]: self._dirty.add(path),
            )
        else:
            widget.connect(
                "changed",
                lambda *_args, path=option["path"]: self._dirty.add(path),
            )
        row.pack_start(widget, False, False, 0)
        if option.get("stale"):
            stale = Gtk.Label()
            stale.get_style_context().add_class("dim-label")
            stale.set_text(
                self._t(
                    "nix_service_stale_option",
                    "Saved value (no longer declared by nixpkgs)",
                )
            )
            row.pack_start(stale, False, False, 0)
        return row

    @staticmethod
    def _format_value(kind, value):
        if value is None:
            return ""
        if kind == "list":
            return ", ".join(str(item) for item in value)
        return str(value)

    def _keep_value(self, path, value):
        """Keep untouched synthetic values only when they were already saved."""
        option = self._option_meta.get(path) or {}
        if path in self._dirty:
            return True
        if (
            value == self._original_values.get(path)
            and not option.get("saved")
            and option.get("default") is None
        ):
            # The evaluator could not resolve this option's default; an
            # untouched empty/false widget is not a user choice and must not
            # become an override that hides the upstream default.
            return False
        return True

    def _collect_values(self):
        values = {}
        for path, (kind, widget) in self._widgets.items():
            option = self._option_meta.get(path) or {}
            if option.get("stale"):
                # Stale values are preserved by the apply pass; they are not
                # accepted by the current service option schema.
                continue
            if kind == "bool":
                value = bool(widget.get_active())
                if self._keep_value(path, value):
                    values[path] = value
            elif kind == "enum":
                active = widget.get_active_id()
                if active is not None and self._keep_value(path, active):
                    values[path] = active
            else:
                text = widget.get_text()
                if kind == "int":
                    if text.strip():
                        try:
                            value = int(text.strip())
                        except ValueError:
                            raise ValueError(
                                f"'{path}' must be a whole number"
                            ) from None
                        if self._keep_value(path, value):
                            values[path] = value
                elif kind == "float":
                    if text.strip():
                        try:
                            value = float(text.strip())
                        except ValueError:
                            raise ValueError(
                                f"'{path}' must be a number"
                            ) from None
                        if self._keep_value(path, value):
                            values[path] = value
                elif kind == "list":
                    value = [
                        item.strip()
                        for item in text.replace("\n", ",").split(",")
                        if item.strip()
                    ]
                    if self._keep_value(path, value):
                        values[path] = value
                else:
                    if self._keep_value(path, text):
                        values[path] = text
        return values

    def _save(self, _button):
        try:
            values = self._collect_values()
            record_id = nix_queue.set_service_options(
                self.source_info, values
            )
        except (OSError, ValueError) as error:
            from .gtk_dialogs import run_message_dialog

            logger.warning("Could not queue Nix service options: %s", error)
            run_message_dialog(
                self.parent_window,
                title="Nix",
                secondary_text=str(error),
                message_type=Gtk.MessageType.ERROR,
                buttons=[("OK", Gtk.ResponseType.OK)],
                default_response=Gtk.ResponseType.OK,
            )
            return
        if record_id is None:
            self.refresh()
            return
        self.refresh()
        callback = getattr(self.parent_window, "_on_appstream_queue_changed", None)
        if callback is not None:
            callback()
