import os

from .gtk_common import Gdk, GLib, Gtk, load_scaled_pixbuf
from gi.repository import Pango
from . import get_icon_path, compat, revert_helper, official_index, installed_packages
from .gtk_dialogs import run_message_dialog
from . import gui_rs


# Internal IDs whose menu cards should never display a badge.
# Physical script IDs are their filename without the extension; repository and
# AppStream entries use their explicit ``id`` when available.
BADGE_EXCLUDED_IDS = {
    "sysup",
    "pdefaults",
}


class ItemWidgetFactory:
    def create_flowbox(self):
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(10)
        flowbox.set_activate_on_single_click(False)

        flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        flowbox.connect("key-press-event", self._on_flowbox_key_press)

        flowbox.set_homogeneous(True)
        flowbox.set_margin_left(32)
        flowbox.set_margin_top(8)
        flowbox.set_margin_right(32)
        flowbox.set_margin_bottom(4)
        flowbox.set_column_spacing(16)
        flowbox.set_row_spacing(12)
        return flowbox

    def _on_flowbox_key_press(self, flowbox, event):
        """Activate the selected item when Enter is pressed in a FlowBox."""
        if event.keyval not in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            return False

        # Let focused controls inside a card, such as the removal button,
        # handle their own activation instead of running the selected item.
        if self.get_focus() is not flowbox:
            return False

        selected_children = flowbox.get_selected_children()
        if not selected_children:
            return False

        if (
            self.current_category_info
            and self.current_category_info.get("display_mode", "menu") == "checklist"
        ):
            checked_scripts = [
                check.script_info
                for check in self.check_buttons
                if check.get_active()
            ]
            if checked_scripts:
                self.on_install_checklist(None)
                return True

        self._activate_item(selected_children[0].get_child(), event)
        return True

    def _on_item_remove_focus_in(self, button, event, event_box):
        """Keep the selected card aligned with its focused removal button."""
        flowbox_child = event_box.get_parent()
        flowbox = flowbox_child.get_parent()
        if isinstance(flowbox, Gtk.FlowBox):
            flowbox.select_child(flowbox_child)
        return False

    def animate_item_batch(
        self,
        widgets,
        *,
        duration_ms: int = 120,
        stagger_ms: int = 9,
        delay_ms: int = 0,
    ):
        """Fade cards through one shared frame-paced animation scheduler.

        New batches join the same 20 ms GTK timeout instead of creating an
        overlapping timeout for every population batch. This keeps animation
        work bounded even while a large category is still being populated.
        """
        widgets = [widget for widget in widgets if widget is not None]
        if not widgets:
            return

        duration_us = max(1, int(duration_ms)) * 1000
        stagger_us = max(0, int(stagger_ms)) * 1000
        start_us = GLib.get_monotonic_time() + max(0, int(delay_ms)) * 1000

        animations = getattr(self, "_item_fade_animations", None)
        if animations is None:
            animations = []
            self._item_fade_animations = animations

        for index, widget in enumerate(widgets):
            try:
                widget.set_opacity(0.0)
            except (RuntimeError, AttributeError):
                continue
            animations.append(
                [widget, start_us + index * stagger_us, duration_us]
            )

        if not animations or getattr(self, "_item_fade_timer_id", None):
            return

        def tick():
            now_us = GLib.get_monotonic_time()
            active = []

            for widget, widget_start_us, widget_duration_us in animations:
                progress = (now_us - widget_start_us) / widget_duration_us
                progress = max(0.0, min(1.0, progress))
                opacity = 1.0 - (1.0 - progress) ** 3
                try:
                    widget.set_opacity(opacity)
                except (RuntimeError, AttributeError):
                    continue

                if progress < 1.0:
                    active.append([widget, widget_start_us, widget_duration_us])

            animations[:] = active
            if animations:
                return True

            self._item_fade_timer_id = None
            return False

        self._item_fade_timer_id = GLib.timeout_add(20, tick)

    @staticmethod
    def _uses_linuxtoys_verified_badge(item_info):
        """Return whether this entry is first-party verified by LinuxToys."""
        if item_info.get("is_official", False):
            return True

        path = str(item_info.get("path", "") or "").strip()
        if item_info.get("is_script", False) and path and not path.startswith("repo://"):
            return official_index.is_verified_script(path)

        # Compatibility fallback for older cached/repository entries that predate
        # is_official. Repository-list entries use their name as the official-index
        # identity; AppStream's own is_verified flag remains a separate concept.
        values = [item_info.get("id"), item_info.get("script")]
        if item_info.get("is_repo_entry", False):
            values.append(item_info.get("name"))
        for value in values:
            if not value:
                continue
            candidate = os.path.splitext(os.path.basename(str(value).strip()))[0]
            if official_index.is_verified_name(candidate):
                return True
        return False

    def _native_item_spec(self, item_info, checklist=False, force_category=False):
        """Return the native-card descriptor, or None for Python-only cards."""
        is_main_category = self.current_category_info is None
        is_subcategory = item_info.get("is_subcategory", False)
        is_category_type = item_info.get("type") == "category"
        is_not_script = not item_info.get("is_script", False)
        is_category_card = (
            force_category
            or is_subcategory
            or (is_category_type and is_not_script)
            or (is_main_category and is_not_script)
        )
        if not gui_rs.available():
            return None

        is_removable_script = self._is_script_removable(item_info)
        icon_value = str(item_info.get("icon", "application-x-executable") or "")
        icon_path = ""
        icon_name = icon_value

        # Remote icons are first-class sources for the native Rust image loader.
        # Do not classify URL paths ending in .png/.svg/.webp as local filesystem icons.
        is_remote_icon = icon_value.startswith(("https://", "http://", "/v2/"))
        if not is_remote_icon:
            if os.path.isabs(icon_value) and os.path.isfile(icon_value):
                # AppStream and other sources may use any image format supported by
                # GdkPixbuf, including JXL on current Arch/CachyOS catalogs.
                icon_path = icon_value
                icon_name = "application-x-executable"
            elif "/" not in icon_value and icon_value.endswith((".png", ".svg", ".webp")):
                # LinuxToys-bundled relative artwork.
                icon_path = get_icon_path(
                    "local-script.svg"
                    if ".local/linuxtoys/scripts" in (item_info.get("path") or "")
                    else icon_value
                ) or ""
                icon_name = "application-x-executable"

        verified = item_info.get("is_verified", False)
        distro_badge = str(item_info.get("native_distro_badge", "") or "")
        appstream_badge = str(item_info.get("appstream_badge", "") or "")
        badge_path = ""
        internal_id = str(item_info.get("id") or item_info.get("script") or "").strip()
        if not internal_id:
            item_path = str(item_info.get("path", "") or "")
            if item_path and not item_path.startswith("repo://"):
                internal_id = os.path.splitext(os.path.basename(item_path))[0]
        badge_excluded = internal_id.casefold() in {
            value.casefold() for value in BADGE_EXCLUDED_IDS
        }
        if not badge_excluded:
            if self._uses_linuxtoys_verified_badge(item_info):
                badge_path = get_icon_path("ltverified.webp") or ""
            elif verified:
                badge_path = get_icon_path("verified.svg") or ""
            elif item_info.get("is_appstream_entry", False):
                if distro_badge:
                    badge_path = get_icon_path(distro_badge) or ""
                elif appstream_badge:
                    badge_path = get_icon_path(appstream_badge) or ""
            elif item_info.get("is_repo_entry", False):
                badge_path = get_icon_path("distros/linuxtoys.webp") or ""
            elif (
                item_info.get("is_script", False)
                and not item_info.get("is_subcategory", False)
                and ".local/linuxtoys/scripts" not in str(item_info.get("path", ""))
            ):
                badge_path = get_icon_path("distros/linuxtoys.webp") or ""

        return {
            "name": item_info["name"],
            "icon_path": icon_path,
            "icon_name": icon_name,
            "badge_path": badge_path,
            "bold": bool(is_category_card),
            "removable": is_removable_script,
            "checklist": bool(checklist),
            "is_new": bool(item_info.get("is_new", False)),
            "category": bool(is_category_card),
        }

    def _finish_native_item_widget(
        self, event_box, item_info, spec, *, allow_drag=False
    ):
        """Attach Python state/callbacks to a card already constructed by Rust."""
        event_box.info = item_info

        # Match the Python card contract: hover styling belongs to the inset
        # painted surface, not the outer EventBox whose allocation also reserves
        # room for the edge badge.
        card_surface = gui_rs.card_child(event_box, "linuxtoys-native-surface")
        if card_surface is not None:
            event_box.card_surface = card_surface

        if spec.get("checklist"):
            check = gui_rs.card_child(event_box, "linuxtoys-native-check")
            if check is not None:
                check.script_info = item_info
                check.connect("toggled", self._on_toggled_check)
                event_box.checkbox = check

        # Rust keeps this control in the card even while it is hidden, allowing
        # terminal completion to update removable state without rebuilding the card.
        remove_btn = gui_rs.card_child(event_box, "linuxtoys-native-remove")
        if remove_btn is not None:
            remove_btn.set_tooltip_text(
                self.translations.get(
                    "term_view_remove", "Remove installed components"
                )
            )
            remove_btn.connect("clicked", self._on_item_remove_clicked, item_info)
            remove_btn.connect(
                "focus-in-event", self._on_item_remove_focus_in, event_box
            )
            event_box.remove_button = remove_btn

        if allow_drag:
            event_box.drag_source_set(
                Gdk.ModifierType.BUTTON1_MASK,
                [Gtk.TargetEntry.new("text/uri-list", 0, 0)],
                Gdk.DragAction.COPY,
            )
            event_box.connect("drag-data-get", self.on_drag_data_get)
            event_box.connect("drag-end", self.on_drag_end)

        event_box.connect("enter-notify-event", self.on_item_enter)
        event_box.connect("leave-notify-event", self.on_item_leave)
        event_box.connect("button-press-event", self.on_item_button_press)
        return event_box

    def create_native_item_batch(
        self, flowbox, item_infos, *, checklist=False, allow_drag=False
    ):
        """Construct and insert a homogeneous ordinary-card batch in native GTK."""
        item_infos = list(item_infos)
        if not item_infos:
            return []
        specs = [self._native_item_spec(info, checklist=checklist) for info in item_infos]
        if any(spec is None for spec in specs):
            return None
        try:
            widgets = gui_rs.add_item_cards(flowbox, specs)
        except Exception as error:
            print(f"Warning: native GTK batch creation failed, using Python fallback: {error}")
            return None
        finished = [
            self._finish_native_item_widget(
                widget, info, spec, allow_drag=allow_drag
            )
            for widget, info, spec in zip(widgets, item_infos, specs)
        ]
        return finished

    def create_native_featured_grid_batch(self, grid, items_with_positions):
        """Construct ordinary Featured cards directly in their Gtk.Grid cells."""
        items_with_positions = list(items_with_positions)
        if not items_with_positions:
            return []

        infos = [info for info, _position in items_with_positions]
        positions = [position for _info, position in items_with_positions]
        specs = [self._native_item_spec(info) for info in infos]
        if any(spec is None or spec.get("removable") or spec.get("checklist") for spec in specs):
            return None

        try:
            widgets = gui_rs.attach_item_cards_grid(grid, specs, positions)
        except Exception as error:
            print(f"Warning: native Featured grid creation failed, using Python fallback: {error}")
            return None

        return [
            self._finish_native_item_widget(widget, info, spec)
            for widget, info, spec in zip(widgets, infos, specs)
        ]

    def create_native_featured_large_widget(
        self, grid, item_info, position, *, featured_height=0
    ):
        """Construct and attach one two-row Featured card in native GTK."""
        spec = self._native_item_spec(item_info)
        if spec is None or spec.get("removable") or spec.get("checklist"):
            return None
        spec = dict(spec)
        spec["description"] = item_info.get("description", "") or ""
        try:
            widget = gui_rs.attach_featured_large_card(
                grid, spec, position, featured_height
            )
        except Exception as error:
            print(
                "Warning: native Featured large-card creation failed, "
                f"using Python fallback: {error}"
            )
            return None
        if widget is None:
            return None
        return self._finish_native_item_widget(widget, item_info, spec)

    def update_native_featured_widget(self, widget, item_info):
        """Rebind one native ordinary Featured card in place."""
        spec = self._native_item_spec(item_info)
        if spec is None or spec.get("removable") or spec.get("checklist"):
            return False
        try:
            updated = gui_rs.update_item_card(widget, spec)
        except Exception as error:
            print(f"Warning: native Featured card update failed: {error}")
            return False
        if updated:
            widget.info = item_info
            widget.set_tooltip_text(item_info.get("description", "") or None)
        return updated

    def create_item_widget(
        self,
        item_info,
        checklist: bool = False,
        allow_drag: bool = False,
        featured_large: bool = False,
        featured_height: int = 0,
        force_category: bool = False,
    ):
        if featured_large:
            return self._create_featured_large_item_widget(
                item_info, featured_height=featured_height
            )

        # All standard cards are native-only. The Rust GUI owns the complete
        # foreground/card hierarchy; Python only attaches application state,
        # callbacks, and the allocation-dependent category watermark wrapper.
        native_spec = self._native_item_spec(
            item_info,
            checklist=checklist,
            force_category=force_category,
        )
        if native_spec is None:
            raise RuntimeError(
                "Standard cards require the native Rust GUI implementation"
            )

        staging_grid = Gtk.Grid()
        try:
            native_widgets = gui_rs.attach_item_cards_grid(
                staging_grid, [native_spec], [(0, 0)]
            )
            if not native_widgets:
                raise RuntimeError("native constructor returned no widget")

            event_box = native_widgets[0]
            staging_grid.remove(event_box)
            return self._finish_native_item_widget(
                event_box,
                item_info,
                native_spec,
                allow_drag=allow_drag,
            )
        except Exception as error:
            raise RuntimeError(
                f"Native standard-card creation failed: {error}"
            ) from error


    def update_featured_normal_widget(self, widget, item_info):
        """Rebind an existing ordinary Featured card without changing its hierarchy."""
        if self.update_native_featured_widget(widget, item_info):
            return widget

        widget.info = item_info
        widget.set_tooltip_text(item_info.get("description", "") or None)

        label = getattr(widget, "_featured_name_widget", None)
        if isinstance(label, Gtk.Label):
            label.set_text(item_info.get("name", ""))

        icon = getattr(widget, "_featured_icon_widget", None)
        if isinstance(icon, Gtk.Image):
            icon_value = item_info.get("icon", "application-x-executable")
            icon_size = 38
            pixbuf = None
            if icon_value.endswith((".png", ".svg", ".webp")):
                if not os.path.isabs(icon_value) and "/" not in icon_value:
                    icon_path = get_icon_path(
                        "local-script.svg"
                        if ".local/linuxtoys/scripts" in (item_info.get("path") or "")
                        else icon_value
                    )
                else:
                    icon_path = icon_value if os.path.exists(icon_value) else None
                if icon_path and os.path.exists(icon_path):
                    pixbuf = load_scaled_pixbuf(icon_path, icon_size, icon_size, True)

            if pixbuf is not None:
                icon.set_from_pixbuf(pixbuf)
            else:
                themed = (
                    icon_value
                    if not icon_value.endswith((".png", ".svg", ".webp"))
                    else "application-x-executable"
                )
                icon.set_from_icon_name(themed, Gtk.IconSize.DIALOG)
                icon.set_pixel_size(icon_size)

        overlay = getattr(widget, "_featured_card_overlay", None)
        old_badge = getattr(widget, "_featured_badge_widget", None)
        if overlay is not None and old_badge is not None:
            overlay.remove(old_badge)
            widget._featured_badge_widget = None

        internal_id = str(
            item_info.get("id") or item_info.get("script") or ""
        ).strip()
        if not internal_id:
            item_path = str(item_info.get("path", "") or "")
            if item_path and not item_path.startswith("repo://"):
                internal_id = os.path.splitext(os.path.basename(item_path))[0]

        badge_excluded = internal_id.casefold() in {
            value.casefold() for value in BADGE_EXCLUDED_IDS
        }
        badge_path = ""
        if not badge_excluded:
            if self._uses_linuxtoys_verified_badge(item_info):
                badge_path = get_icon_path("ltverified.webp")
            elif item_info.get("is_verified", False):
                badge_path = get_icon_path("verified.svg")
            elif item_info.get("is_appstream_entry", False):
                distro_badge = str(item_info.get("native_distro_badge", "") or "")
                appstream_badge = str(item_info.get("appstream_badge", "") or "")
                if distro_badge:
                    badge_path = get_icon_path(distro_badge)
                elif appstream_badge:
                    badge_path = get_icon_path(appstream_badge)
            elif item_info.get("is_repo_entry", False):
                badge_path = get_icon_path("distros/linuxtoys.webp")
            elif (
                item_info.get("is_script", False)
                and not item_info.get("is_subcategory", False)
                and ".local/linuxtoys/scripts" not in str(item_info.get("path", ""))
            ):
                badge_path = get_icon_path("distros/linuxtoys.webp")

        if overlay is not None and badge_path:
            badge_pixbuf = load_scaled_pixbuf(badge_path, 20, 20, True)
            if badge_pixbuf is not None:
                badge = Gtk.Image.new_from_pixbuf(badge_pixbuf)
                badge.set_halign(Gtk.Align.END)
                badge.set_valign(Gtk.Align.START)
                overlay.add_overlay(badge)
                badge.show()
                widget._featured_badge_widget = badge

        style = widget.card_surface.get_style_context()
        if item_info.get("is_new", False):
            style.add_class("script-item-new")
        else:
            style.remove_class("script-item-new")

        return widget

    def _create_featured_large_item_widget(self, item_info, featured_height: int = 0):
        """Create the large Featured variant entirely in native GTK."""
        staging_grid = Gtk.Grid()
        widget = self.create_native_featured_large_widget(
            staging_grid, item_info, (0, 0), featured_height=featured_height
        )
        if widget is None:
            raise RuntimeError("Large Featured cards require the native Rust GUI implementation")
        staging_grid.remove(widget)
        return widget

    def _is_script_removable(self, item_info):
        """Check if a script item is installed and can be removed."""
        if item_info.get("appstream_source") == "homebrew":
            return installed_packages.match(item_info) is not None
        # Use the search cache's pre-computed removable state whenever possible
        if self.script_cache.is_populated:
            return self.script_cache.is_script_removable(item_info)

        # Fallback to direct computation if the cache is not ready yet
        if item_info.get("is_repo_entry"):
            return bool(
                revert_helper._load_last_execution(
                    item_info.get("name", "")
                )
            )
        if not item_info.get("is_script"):
            return False
        script_path = item_info.get("path", "")
        if not script_path or not os.path.isfile(script_path):
            return False
        script_name = item_info.get("name", "")
        if not script_name:
            return False

        revert_capability = compat.get_revert_capability(script_path)
        if revert_capability == "no":
            return False

        # Internal revert re-runs the script itself for removal
        if revert_capability == "internal":
            return bool(revert_helper._load_last_execution(script_name))

        # Manual revert requires a registry entry and enabled manual revert
        if not compat.should_enable_manual_revert(script_path):
            return False

        return bool(revert_helper._load_last_execution(script_name))

    def _set_item_removable_state(self, event_box, removable):
        """Toggle an existing card's removal affordance without rebuilding it."""
        remove_btn = getattr(event_box, "remove_button", None)
        if remove_btn is None:
            remove_btn = gui_rs.card_child(event_box, "linuxtoys-native-remove")
        if remove_btn is None:
            return False

        removable = bool(removable)
        row = remove_btn.get_parent()
        if row is not None:
            style = row.get_style_context()
            if removable:
                style.add_class("installed-card")
            else:
                style.remove_class("installed-card")

        label = gui_rs.card_child(event_box, "linuxtoys-native-name")
        if isinstance(label, Gtk.Label):
            is_category = bool(
                event_box.info.get("is_subcategory", False)
                or event_box.info.get("type") == "category"
            )
            label.set_margin_start(0 if removable else (0 if is_category else 22))

        if removable:
            remove_btn.set_no_show_all(False)
            remove_btn.show()
        else:
            remove_btn.hide()
            remove_btn.set_no_show_all(True)

        return True

    def _refresh_flowbox_removable_states(self, flowbox):
        """Refresh removal controls on already-built cards in one FlowBox."""
        if flowbox is None:
            return
        for flowbox_child in flowbox.get_children():
            event_box = flowbox_child.get_child()
            item_info = getattr(event_box, "info", None)
            if not item_info:
                continue
            self._set_item_removable_state(
                event_box, self._is_script_removable(item_info)
            )

    def _on_item_remove_clicked(self, button, item_info):
        """Handle remove button click on a script item."""
        # Check if reboot is required before proceeding
        if self.reboot_required:
            if not self._show_reboot_warning_dialog():
                return

        # AppStream removals use the same persistent hidden PTY as installs.
        # Keep every other removal on the existing terminal-view path.
        if item_info.get("is_appstream_entry"):
            script_name = item_info.get("name", "Script")
            response = run_message_dialog(
                self,
                title=self.translations.get(
                    "remove_confirm_title", "Remove Installed Components?"
                ),
                secondary_text=self.translations.get(
                    "remove_confirm_message",
                    "LinuxToys will attempt to remove all components installed by "
                    "'{script_name}'. Do you want to continue?",
                ).format(script_name=script_name),
                message_type=Gtk.MessageType.WARNING,
                buttons=[
                    (self.translations.get("cancel_btn_label", "Cancel"), Gtk.ResponseType.CANCEL),
                    (self.translations.get("yes", "Yes"), Gtk.ResponseType.YES),
                ],
                default_response=Gtk.ResponseType.CANCEL,
            )
            if response != Gtk.ResponseType.YES:
                return

            remove_entry = revert_helper.build_uninstall_script_entry(
                item_info, self.translations
            )
            if not remove_entry:
                run_message_dialog(
                    self,
                    title=self.translations.get(
                        "remove_not_available_title", "Removal Not Available"
                    ),
                    secondary_text=self.translations.get(
                        "remove_not_available_message",
                        "No removable components were detected for this script.",
                    ),
                    message_type=Gtk.MessageType.INFO,
                    buttons=[("OK", Gtk.ResponseType.OK)],
                )
                return

            self._appstream_runner.enqueue_removal(
                item_info,
                remove_entry,
                record_id=item_info.get("_appstream_queue_record_id"),
            )
            return

        # Use a copy without auto_run so the term view waits for the removal flow
        script_copy = dict(item_info)
        script_copy.pop("auto_run", None)

        # Open the term view for the script and trigger the existing removal flow
        run_box = self.open_term_view(
            [script_copy], removable_script_info=item_info, auto_run=False
        )
        if run_box:
            run_box.on_button_remove_clicked(None)

    def on_item_enter(self, widget, event):
        """Handle mouse entering a script/category item - add hover effect."""
        try:
            # Hover effect belongs to the painted card surface; the outer
            # EventBox may include transparent room for an edge badge.
            card_surface = getattr(widget, "card_surface", widget)
            card_surface.get_style_context().add_class("script-item-hover")
            # Force a redraw
            card_surface.queue_draw()
        except Exception as e:
            print(f"Error in hover enter: {e}")

        return False

    def on_item_leave(self, widget, event):
        """Handle mouse leaving a script/category item - remove hover effect."""
        try:
            card_surface = getattr(widget, "card_surface", widget)
            style_context = card_surface.get_style_context()
            style_context.remove_class("script-item-hover")
            # Force a redraw
            card_surface.queue_draw()
        except Exception as e:
            print(f"Error in hover leave: {e}")

        return False

    def on_item_button_press(self, widget, event):
        """Handle mouse button presses on items - both left and right clicks."""
        if event.button == 1:  # Left click
            # Determine the appropriate click handler based on item type and context
            info = widget.info

            if (
                ".local/linuxtoys/scripts/" in (info.get("path") or "")
                and event.state & Gdk.ModifierType.CONTROL_MASK
            ):
                if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
                    self._edit_local_script(widget.info)
                return False
            self._activate_item(widget, event)
            return True

        elif event.button == 3:  # Right click
            self._show_context_menu(widget, event)
            return True

        return False

    def _activate_item(self, widget, event):
        """Route keyboard and pointer activation through the same handlers."""
        info = widget.info

        # Route by the item's own type, not by the global search state. Search
        # remains active while an app page is open, and using it here would make
        # unrelated category cards behave like executable scripts.
        if info.get("is_homebrew_category"):
            self._activate_homebrew_category(widget, event)
        elif info.get("is_aur_category"):
            self._activate_aur_category(info)
        elif info.get("is_script", False):
            self.on_script_clicked(widget, event)
        else:
            self.on_category_clicked(widget, event)

    def _show_context_menu(self, widget, event):
        """Show context menu for right-click on items."""
        info = widget.info

        # Only show context menu for local scripts
        if not self._is_local_script(info):
            return

        # Get all selected local scripts
        selected_children = self.scripts_flowbox.get_selected_children()
        selected_infos = []
        for child in selected_children:
            event_box = child.get_child()
            item_info = event_box.info
            if self._is_local_script(item_info):
                selected_infos.append(item_info)

        # If multiple selected, show limited menu
        if len(selected_infos) > 1:
            menu = Gtk.Menu()

            # Export option
            export_item = Gtk.MenuItem(label=self.translations.get("export", "Export"))
            export_item.connect(
                "activate", lambda item: self._export_local_scripts(selected_infos)
            )
            menu.append(export_item)

            # Delete option
            delete_item = Gtk.MenuItem(
                label=self.translations.get("delete_script", "Delete Script")
            )
            delete_item.connect(
                "activate", lambda item: self._delete_local_scripts(selected_infos)
            )
            menu.append(delete_item)

            menu.show_all()
            menu.popup_at_pointer(event)
        else:
            # Single selection menu
            menu = Gtk.Menu()

            # Export option
            export_item = Gtk.MenuItem(label=self.translations.get("export", "Export"))
            export_item.connect(
                "activate", lambda item: self._export_local_script(info)
            )
            menu.append(export_item)

            # Edit option
            edit_item = Gtk.MenuItem(
                label=self.translations.get("edit_script", "Edit Script")
            )
            edit_item.connect("activate", lambda item: self._edit_local_script(info))
            menu.append(edit_item)

            # Delete option
            delete_item = Gtk.MenuItem(
                label=self.translations.get("delete_script", "Delete Script")
            )
            delete_item.connect(
                "activate", lambda item: self._delete_local_script(info)
            )
            menu.append(delete_item)

            menu.show_all()
            menu.popup_at_pointer(event)
