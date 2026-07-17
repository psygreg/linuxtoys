import os

from .gtk_common import Gdk, Gtk, GdkPixbuf
from . import get_icon_path, compat, revert_helper

class ItemWidgetFactory:
    def create_flowbox(self):
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(5)
        flowbox.set_activate_on_single_click(False)

        # Selection is enabled dynamically only for Local Scripts.
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)

        flowbox.set_homogeneous(True)
        flowbox.set_margin_left(32)
        flowbox.set_margin_top(8)
        flowbox.set_margin_right(32)
        flowbox.set_margin_bottom(4)
        flowbox.set_column_spacing(16)
        flowbox.set_row_spacing(12)
        return flowbox
    
    def create_item_widget(self, item_info, checklist: bool = False, allow_drag: bool = False,):
        import os

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_size_request(128, 52)  # Fixed width for all items
        box.set_hexpand(False)
        box.set_halign(Gtk.Align.FILL)

        # Show a remove button on the left for scripts that are already installed
        is_removable_script = self._is_script_removable(item_info)
        if is_removable_script:
            box.get_style_context().add_class("installed-card")
            remove_btn = Gtk.Button.new_from_icon_name(
                "edit-delete-symbolic", Gtk.IconSize.MENU
            )
            remove_btn.get_style_context().add_class("installed-card-remove-left")
            remove_btn.set_size_request(24, 24)
            remove_btn.set_margin_left(4)
            remove_btn.set_tooltip_text(
                self.translations.get(
                    "term_view_remove", "Remove installed components"
                )
            )
            remove_btn.set_relief(Gtk.ReliefStyle.NONE)
            remove_btn.set_can_focus(False)
            remove_btn.get_style_context().add_class("destructive-action")
            remove_btn.connect("clicked", self._on_item_remove_clicked, item_info)
            box.pack_start(remove_btn, False, False, 0)
        else:
            left_pad = Gtk.Label()
            left_pad.set_size_request(10, 1)
            box.pack_start(left_pad, False, False, 0)

        display_name = item_info["name"]

        label = Gtk.Label(label=display_name)
        label.set_line_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_halign(Gtk.Align.CENTER)
        label.set_valign(Gtk.Align.CENTER)
        label.set_max_width_chars(28)  # Limit label width
        label.set_width_chars(4)  # Set consistent width
        label.set_hexpand(False)

        # Make categories and subcategories bold, keep scripts regular
        is_main_category = self.current_category_info is None  # We're in the main menu
        is_subcategory = item_info.get("is_subcategory", False)
        is_category_type = item_info.get("type") == "category"
        is_not_script = not item_info.get("is_script", False)

        if checklist:
            check = Gtk.CheckButton()
            check.connect("toggled", self._on_toggled_check)
            check.script_info = item_info
            # Make checkbox non-focusable so it doesn't interfere with keyboard navigation
            check.set_can_focus(False)
            box.pack_start(check, False, False, 0)

        if (
            is_subcategory
            or (is_category_type and is_not_script)
            or (is_main_category and is_not_script)
        ):
            # This is a category or subcategory - make it bold
            # Escape HTML characters to prevent markup issues
            import html

            escaped_name = html.escape(display_name)
            label.set_markup(f"<b>{escaped_name}</b>")
        box.pack_start(label, True, True, 0)

        icon_value = item_info.get("icon", "application-x-executable")
        icon_widget = None
        icon_size = 38  # Target icon size

        # If icon_value looks like a file path or just a filename, use Gtk.Image.new_from_file
        if icon_value.endswith(".png") or icon_value.endswith(".svg"):
            # If only a filename, use the global icon path resolver
            if not os.path.isabs(icon_value) and "/" not in icon_value:
                icon_path = get_icon_path(
                    "local-script.svg"
                    if ".local/linuxtoys/scripts" in item_info.get("path")
                    else icon_value
                )
            else:
                icon_path = icon_value if os.path.exists(icon_value) else None

            if icon_path and os.path.exists(icon_path):
                if icon_path.endswith(".svg") or icon_path.endswith(".png"):
                    # For SVG files, load as pixbuf with specific size
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                            icon_path, icon_size, icon_size, True
                        )
                        icon_widget = Gtk.Image.new_from_pixbuf(pixbuf)
                    except Exception:
                        # Fallback to default icon if SVG loading fails
                        icon_widget = Gtk.Image.new_from_icon_name(
                            "application-x-executable", Gtk.IconSize.DIALOG
                        )
                        icon_widget.set_pixel_size(icon_size)
                else:
                    # For PNG files, use regular loading and set pixel size
                    icon_widget = Gtk.Image.new_from_file(icon_path)
                    icon_widget.set_pixel_size(icon_size)
            else:
                icon_widget = Gtk.Image.new_from_icon_name(
                    "application-x-executable", Gtk.IconSize.DIALOG
                )
                icon_widget.set_pixel_size(icon_size)
        else:
            icon_widget = Gtk.Image.new_from_icon_name(icon_value, Gtk.IconSize.DIALOG)
            icon_widget.set_pixel_size(icon_size)  ## altura dos icones
        icon_widget.set_halign(Gtk.Align.END)
        icon_widget.set_valign(Gtk.Align.CENTER)

        box.pack_start(icon_widget, False, False, 20)

        event_box = Gtk.EventBox()
        event_box.add(box)
        event_box.get_style_context().add_class("script-item")
        if item_info.get("is_new", False):
            event_box.get_style_context().add_class("script-item-new")
        event_box.info = item_info
        # Store reference to checkbox for easy access in keyboard handlers
        if checklist:
            event_box.checkbox = check

        # Enable mouse events for hover effects and right-click
        event_box.set_events(
            event_box.get_events()
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
        )

        # Connect hover events only (click events are connected separately)
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

    def _is_script_removable(self, item_info):
        """Check if a script item is installed and can be removed."""
        # Use the search cache's pre-computed removable state whenever possible
        if self.script_cache.is_populated:
            return self.script_cache.is_script_removable(item_info)

        # Fallback to direct computation if the cache is not ready yet
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
    
    def _on_item_remove_clicked(self, button, item_info):
        """Handle remove button click on a script item."""
        # Check if reboot is required before proceeding
        if self.reboot_required:
            self._show_reboot_warning_dialog()
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
            # Hover effect
            widget.get_style_context().add_class("script-item-hover")

            # Force a redraw
            widget.queue_draw()
        except Exception as e:
            print(f"Error in hover enter: {e}")

        return False

    def on_item_leave(self, widget, event):
        """Handle mouse leaving a script/category item - remove hover effect."""
        try:
            style_context = widget.get_style_context()
            style_context.remove_class("script-item-hover")

            # Force a redraw
            widget.queue_draw()
        except Exception as e:
            print(f"Error in hover leave: {e}")

        return False

    def on_item_button_press(self, widget, event):
        """Handle mouse button presses on items - both left and right clicks."""
        if event.button == 1:  # Left click
            # Determine the appropriate click handler based on item type and context
            info = widget.info

            if (
                ".local/linuxtoys/scripts/" in info.get("path")
                and event.state & Gdk.ModifierType.CONTROL_MASK
            ):
                if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
                    self._edit_local_script(widget.info)
                return False
            # If this is a search result, use script click handler
            if self.search_active:
                self.on_script_clicked(widget, event)
                return True

            # If this is a subcategory or category, use category click handler
            if info.get("is_subcategory", False) or (not info.get("is_script", False)):
                self.on_category_clicked(widget, event)
            else:
                # This is a script, use script click handler
                self.on_script_clicked(widget, event)
            return True

        elif event.button == 3:  # Right click
            self._show_context_menu(widget, event)
            return True

        return False

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