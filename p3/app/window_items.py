import os

from .gtk_common import Gdk, GdkPixbuf, GLib, Gtk, load_scaled_pixbuf
from gi.repository import Pango
from . import get_icon_path, compat, revert_helper, official_index
from . import _catalog_rs
from .gtk_dialogs import run_message_dialog
from . import gui_rs


# Internal IDs whose menu cards should never display a badge.
# Physical script IDs are their filename without the extension; repository and
# AppStream entries use their explicit ``id`` when available.
BADGE_EXCLUDED_IDS = {
    "sysup",
    "pdefaults",
}


class _LayoutNeutralImage(Gtk.Image):
    """Gtk.Image whose pixbuf never contributes to parent size negotiation."""

    def do_get_preferred_width(self):
        return (0, 0)

    def do_get_preferred_height(self):
        return (0, 0)

    def do_get_preferred_width_for_height(self, height):
        return (0, 0)

    def do_get_preferred_height_for_width(self, width):
        return (0, 0)

class ItemWidgetFactory:
    def _category_watermark_pixbuf(self, icon_path, width, height):
        """Render a supersampled, allocation-sized category watermark."""
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            return None

        cache = getattr(self, "_category_watermark_cache", None)
        if cache is None:
            cache = {}
            self._category_watermark_cache = cache

        key = (icon_path, width, height)
        cached = cache.get(key)
        if cached is not None:
            return cached

        # 2x supersampling is enough for this low-opacity decorative layer while
        # cutting the intermediate canvas from 16x to 4x the final pixel count.
        # The SVG is still rasterized above display resolution and downsampled once.
        supersample = 2
        canvas_width = width * supersample
        canvas_height = height * supersample

        # Preserve the deliberately oversized/cropped presentation used by the
        # pre-rendered watermark: roughly 1.7 card-heights, hanging off the left
        # edge and vertically centred.
        icon_size = max(1, int(round(height * 1.70)))
        icon_size_ss = icon_size * supersample
        icon_x = int(round(-height * 0.42))
        icon_y = int(round((height - icon_size) / 2.0))

        try:
            source = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                icon_path, icon_size_ss, icon_size_ss, True
            )
        except GLib.Error:
            return None

        # GTK remains responsible for SVG rasterization. Rust owns the deterministic
        # crop/composite/downsample/rounded-alpha transform in one coarse call, without
        # allocating the old supersampled transparent canvas.
        try:
            pixels = _catalog_rs.render_category_watermark(
                bytes(source.get_pixels()),
                source.get_width(),
                source.get_height(),
                source.get_rowstride(),
                source.get_n_channels(),
                source.get_has_alpha(),
                width,
                height,
                icon_x,
                icon_y,
                supersample,
                0.46,
                10.0,
            )
        except (ValueError, TypeError, RuntimeError):
            return None

        if not pixels:
            return None

        data = GLib.Bytes.new(pixels)
        result = GdkPixbuf.Pixbuf.new_from_bytes(
            data,
            GdkPixbuf.Colorspace.RGB,
            True,
            8,
            width,
            height,
            width * 4,
        )

        # Allocation sizes are highly repetitive. Keep the cache bounded in case
        # a compositor repeatedly reports one-pixel intermediate resize values.
        if len(cache) >= 96:
            cache.clear()
        cache[key] = result
        return result

    def _flush_deferred_category_watermarks(self):
        """Render allocation-sized category watermarks once after resize settles."""
        root = getattr(self, "categories_flowbox", None)
        if root is None:
            return

        stack = [root]
        while stack:
            widget = stack.pop()
            apply_pending = getattr(widget, "_linuxtoys_apply_pending_watermark", None)
            if apply_pending is not None:
                try:
                    apply_pending(widget)
                except (RuntimeError, AttributeError):
                    pass
            try:
                stack.extend(widget.get_children())
            except (AttributeError, RuntimeError):
                pass

    def create_flowbox(self):
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(5)
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

    def _native_item_spec(self, item_info, checklist=False):
        """Return the native-card descriptor, or None for Python-only cards."""
        is_main_category = self.current_category_info is None
        is_subcategory = item_info.get("is_subcategory", False)
        is_category_type = item_info.get("type") == "category"
        is_not_script = not item_info.get("is_script", False)
        is_category_card = (
            is_subcategory
            or (is_category_type and is_not_script)
            or (is_main_category and is_not_script)
        )
        if is_category_card or not gui_rs.available():
            return None

        is_removable_script = self._is_script_removable(item_info)
        icon_value = str(item_info.get("icon", "application-x-executable") or "")
        icon_path = ""
        icon_name = icon_value
        if icon_value.endswith((".png", ".svg")):
            if not os.path.isabs(icon_value) and "/" not in icon_value:
                icon_path = get_icon_path(
                    "local-script.svg"
                    if ".local/linuxtoys/scripts" in (item_info.get("path") or "")
                    else icon_value
                ) or ""
            elif os.path.exists(icon_value):
                icon_path = icon_value
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
                badge_path = get_icon_path("ltverified.svg") or ""
            elif verified:
                badge_path = get_icon_path("verified.svg") or ""
            elif item_info.get("is_appstream_entry", False):
                if distro_badge:
                    badge_path = get_icon_path(distro_badge) or ""
                elif appstream_badge:
                    badge_path = get_icon_path(appstream_badge) or ""
            elif item_info.get("is_repo_entry", False):
                badge_path = get_icon_path("distros/linuxtoys.svg") or ""
            elif (
                item_info.get("is_script", False)
                and not item_info.get("is_subcategory", False)
                and ".local/linuxtoys/scripts" not in str(item_info.get("path", ""))
            ):
                badge_path = get_icon_path("distros/linuxtoys.svg") or ""

        return {
            "name": item_info["name"],
            "icon_path": icon_path,
            "icon_name": icon_name,
            "badge_path": badge_path,
            "bold": False,
            "removable": is_removable_script,
            "checklist": bool(checklist),
            "is_new": bool(item_info.get("is_new", False)),
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

        if spec.get("removable"):
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
        return [
            self._finish_native_item_widget(
                widget, info, spec, allow_drag=allow_drag
            )
            for widget, info, spec in zip(widgets, item_infos, specs)
        ]

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
    ):
        import os

        if featured_large:
            return self._create_featured_large_item_widget(
                item_info, featured_height=featured_height
            )

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
            remove_btn.set_tooltip_text(
                self.translations.get(
                    "term_view_remove", "Remove installed components"
                )
            )
            remove_btn.set_relief(Gtk.ReliefStyle.NONE)
            remove_btn.set_can_focus(True)
            remove_btn.get_style_context().add_class("destructive-action")
            remove_btn.connect("clicked", self._on_item_remove_clicked, item_info)
            box.pack_start(remove_btn, False, False, 0)
        display_name = item_info["name"]

        label = Gtk.Label(label=display_name)
        if not is_removable_script and not checklist:
            # Preserve the old spacer + box-spacing offset without allocating
            # a throwaway Gtk.Label for normal non-checklist cards. In checklist
            # mode the offset belongs on the checkbox, which is the first visible
            # child after the omitted spacer.
            label.set_margin_start(22)
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
            if not is_removable_script:
                # The original layout had a 10 px spacer widget before the checkbox
                # plus the Gtk.Box's 12 px spacing. Preserve that geometry without
                # allocating a dummy widget for every normal checklist card.
                check.set_margin_start(22)
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
        icon_path = None
        icon_size = 38  # Target icon size

        # If icon_value looks like a file path or just a filename, use Gtk.Image.new_from_file
        if icon_value.endswith(".png") or icon_value.endswith(".svg"):
            # If only a filename, use the global icon path resolver
            if not os.path.isabs(icon_value) and "/" not in icon_value:
                icon_path = get_icon_path(
                    "local-script.svg"
                    if ".local/linuxtoys/scripts" in (item_info.get("path") or "")
                    else icon_value
                )
            else:
                icon_path = icon_value if os.path.exists(icon_value) else None

            if icon_path and os.path.exists(icon_path):
                if icon_path.endswith(".svg") or icon_path.endswith(".png"):
                    # For SVG files, load as pixbuf with specific size
                    pixbuf = load_scaled_pixbuf(
                        icon_path, icon_size, icon_size, True
                    )
                    if pixbuf is not None:
                        icon_widget = Gtk.Image.new_from_pixbuf(pixbuf)
                    else:
                        # Fallback to default icon if file loading fails.
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

        verified = item_info.get("is_verified", False)
        distro_badge = str(item_info.get("native_distro_badge", "") or "")
        appstream_badge = str(item_info.get("appstream_badge", "") or "")
        badge_path = ""
        badge_tooltip = ""

        # Resolve the same stable/internal identity LinuxToys uses elsewhere:
        # explicit repository/AppStream ID first, then the physical script's
        # filename stem. Local scripts are already excluded from LinuxToys badges.
        internal_id = str(
            item_info.get("id")
            or item_info.get("script")
            or ""
        ).strip()
        if not internal_id:
            item_path = str(item_info.get("path", "") or "")
            if item_path and not item_path.startswith("repo://"):
                internal_id = os.path.splitext(os.path.basename(item_path))[0]
        badge_excluded = internal_id.casefold() in {
            value.casefold() for value in BADGE_EXCLUDED_IDS
        }

        if badge_excluded:
            pass
        elif self._uses_linuxtoys_verified_badge(item_info):
            badge_path = get_icon_path("ltverified.svg")
        elif verified:
            badge_path = get_icon_path("verified.svg")
        elif item_info.get("is_appstream_entry", False):
            if distro_badge:
                badge_path = get_icon_path(distro_badge)
            elif appstream_badge:
                badge_path = get_icon_path(appstream_badge)
        elif item_info.get("is_repo_entry", False):
            badge_path = get_icon_path("distros/linuxtoys.svg")
        elif (
            item_info.get("is_script", False)
            and not item_info.get("is_subcategory", False)
            and ".local/linuxtoys/scripts" not in str(item_info.get("path", ""))
        ):
            badge_path = get_icon_path("distros/linuxtoys.svg")

        # Keep the application icon independent from the source/support badge.
        # The badge is attached to the card itself below, so it never obscures
        # unusually large or edge-filling application artwork.
        box.pack_start(icon_widget, False, False, 20)

        event_box = Gtk.EventBox()

        # Keep the painted card surface separate from the outer event widget.
        # Every card reserves the same small amount of transparent space at the
        # top/right. This keeps badged and unbadged cards geometrically identical
        # while letting a 20 px badge straddle the painted card edge without
        # negative margins or invalid GTK size allocations.
        # Category cards use a transparent, card-height GdkPixbuf as a purely
        # decorative background layer. The enlarged SVG is composited into that
        # pixbuf with negative source coordinates, so cropping happens in pixel
        # space rather than GTK allocation space. No Cairo/Pycairo bridge is needed.
        is_category_card = (
            is_subcategory
            or (is_category_type and is_not_script)
            or (is_main_category and is_not_script)
        )
        category_watermark = None
        category_watermark_update = None
        if (
            is_category_card
            and icon_value.endswith(".svg")
            and icon_path
            and os.path.exists(icon_path)
        ):
            # Gtk.Image normally reports its pixbuf as its natural size. Because the
            # pixbuf itself is generated from the current allocation, allowing that
            # request into Gtk.Grid creates an allocation -> pixbuf -> preferred-size
            # feedback loop. The layout-neutral image paints into the allocation it
            # receives but contributes zero to GTK's size negotiation.
            category_watermark = _LayoutNeutralImage()
            category_watermark.set_halign(Gtk.Align.FILL)
            category_watermark.set_valign(Gtk.Align.FILL)

            def category_watermark_update(surface, allocation, image=category_watermark, path=icon_path):
                size = (int(allocation.width), int(allocation.height))
                if size[0] <= 0 or size[1] <= 0:
                    return
                if getattr(image, "_linuxtoys_watermark_size", None) == size:
                    return

                # During interactive resize, record only the final requested size.
                # The 4x render/downsample/rounded-corner work is deferred to the
                # window-level settled-resize pass.
                surface._linuxtoys_pending_watermark_size = size
                if (
                    getattr(self, "_window_resize_pending", False)
                    or not getattr(self, "_categories_startup_transition_complete", True)
                ):
                    # During startup the opaque roller owns the screen. Defer the
                    # expensive 4x watermark composition until window.py drains the
                    # pending cards cooperatively, one per GTK idle dispatch.
                    return

                pixbuf = self._category_watermark_pixbuf(path, *size)
                if pixbuf is not None:
                    image.set_from_pixbuf(pixbuf)
                    image._linuxtoys_watermark_size = size
                    surface._linuxtoys_pending_watermark_size = None

            def apply_pending_watermark(surface, image=category_watermark, path=icon_path):
                size = getattr(surface, "_linuxtoys_pending_watermark_size", None)
                if not size or getattr(image, "_linuxtoys_watermark_size", None) == size:
                    return
                pixbuf = self._category_watermark_pixbuf(path, *size)
                if pixbuf is not None:
                    image.set_from_pixbuf(pixbuf)
                    image._linuxtoys_watermark_size = size
                    surface._linuxtoys_pending_watermark_size = None

        if category_watermark is not None:
            # The normal card_surface Gtk.Box expands `box` across the full FlowBox
            # cell. In the watermark variant both widgets share a Gtk.Grid cell, so
            # the foreground box must explicitly expand as well; otherwise it keeps
            # its 128 px minimum width at the left edge, pulling the centered title
            # and trailing icon left with it.
            box.set_hexpand(True)
            box.set_halign(Gtk.Align.FILL)

            # Stack both children in the same Gtk.Grid cell. The watermark remains
            # behind the normal foreground layout and does not participate in its
            # title/icon positioning.
            card_surface = Gtk.Grid()
            card_surface.attach(category_watermark, 0, 0, 1, 1)
            card_surface.attach(box, 0, 0, 1, 1)
            card_surface._linuxtoys_apply_pending_watermark = apply_pending_watermark
            card_surface.connect("size-allocate", category_watermark_update)
        else:
            card_surface = Gtk.Box()
            card_surface.pack_start(box, True, True, 0)

        card_surface.get_style_context().add_class("script-item")
        event_box.card_surface = card_surface
        # Ordinary Featured cards can be rebound in-place between timed rotations.
        # These references do not alter the widget hierarchy.
        event_box._featured_name_widget = label
        event_box._featured_icon_widget = icon_widget
        event_box._featured_card_overlay = None
        event_box._featured_badge_widget = None

        if item_info.get("is_new", False):
            card_surface.get_style_context().add_class("script-item-new")

        badge_edge_space = 4
        card_surface.set_margin_top(badge_edge_space)
        # Reserve the same horizontal breathing room on both sides. The badge
        # still uses the overlay's full allocation and can straddle the painted
        # card's right edge, while the visible card surface stays geometrically
        # centered inside its FlowBox/Grid cell.
        card_surface.set_margin_start(badge_edge_space)
        card_surface.set_margin_end(badge_edge_space)

        card_overlay = Gtk.Overlay()
        card_overlay.add(card_surface)
        event_box._featured_card_overlay = card_overlay

        if badge_path:
            badge_size = 20
            badge_pixbuf = load_scaled_pixbuf(
                badge_path,
                badge_size,
                badge_size,
                True,
            )
            if badge_pixbuf is not None:
                badge = Gtk.Image.new_from_pixbuf(badge_pixbuf)
                badge.set_halign(Gtk.Align.END)
                badge.set_valign(Gtk.Align.START)
                card_overlay.add_overlay(badge)
                event_box._featured_badge_widget = badge

        event_box.add(card_overlay)

        event_box.info = item_info
        # Store reference to checkbox for easy access in keyboard handlers
        if checklist:
            event_box.checkbox = check

        if is_removable_script:
            remove_btn.connect(
                "focus-in-event", self._on_item_remove_focus_in, event_box
            )

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

        # Gtk.EventBox does not reliably expose :hover state to GTK3 CSS, so
        # keep the lightweight explicit class toggle used by the original UI.
        # This restores the standard card hover effect without affecting the
        # removal button's own hover styling.
        event_box.connect("enter-notify-event", self.on_item_enter)
        event_box.connect("leave-notify-event", self.on_item_leave)
        event_box.connect("button-press-event", self.on_item_button_press)

        return event_box


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
            if icon_value.endswith((".png", ".svg")):
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
                    if not icon_value.endswith((".png", ".svg"))
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
                badge_path = get_icon_path("ltverified.svg")
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
                badge_path = get_icon_path("distros/linuxtoys.svg")
            elif (
                item_info.get("is_script", False)
                and not item_info.get("is_subcategory", False)
                and ".local/linuxtoys/scripts" not in str(item_info.get("path", ""))
            ):
                badge_path = get_icon_path("distros/linuxtoys.svg")

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
        """Create the three-row Featured variant without changing normal cards."""
        import html

        # Start from the regular card so icon resolution, card badges, activation,
        # hover behavior and script metadata remain exactly the same everywhere.
        event_box = self.create_item_widget(item_info)
        card_surface = event_box.card_surface
        base_box = card_surface.get_children()[0]

        # The large card has its own more spacious presentation. Keep all padding
        # inside the existing card boundary so its outer size still matches exactly
        # three normal Featured rows.
        base_box.set_margin_top(16)
        base_box.set_margin_bottom(16)
        base_box.set_margin_start(16)
        base_box.set_margin_end(16)

        # Preserve the regular card's horizontal name/icon row, but normalize the
        # normal-card spacer/padding before moving the widgets. Large AppStream
        # cards use the free right side for the same ODRS aggregate shown on the
        # app page; all other large cards keep their historical centered header.
        is_appstream = bool(item_info.get("is_appstream_entry", False))
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        top_row.set_hexpand(True)
        top_row.set_halign(Gtk.Align.FILL if is_appstream else Gtk.Align.CENTER)

        icon_widget = None
        name_widget = None
        other_widgets = []
        for child in tuple(base_box.get_children()):
            base_box.remove(child)

            if isinstance(child, Gtk.Label):
                child.set_margin_start(0)
                child.set_margin_end(0)
                child.set_hexpand(False)
                child.set_markup(
                    f"<span size=\"x-large\"><b>{html.escape(item_info.get('name', ''))}</b></span>"
                )
                name_widget = child
            elif isinstance(child, Gtk.Image):
                icon_widget = child
            else:
                other_widgets.append(child)

        # Large Featured cards deliberately reverse the regular card's title/icon
        # order: icon first, then title. AppStream cards keep that identity group
        # on the left while their ODRS aggregate occupies the opposite edge.
        if icon_widget is not None:
            # Give the outer edge of the large-card identity group a little more
            # breathing room without changing the spacing between icon and title.
            icon_widget.set_margin_start(4)
            top_row.pack_start(icon_widget, False, False, 0)
        if name_widget is not None:
            top_row.pack_start(name_widget, False, False, 0)
        for child in other_widgets:
            top_row.pack_start(child, False, False, 0)

        if is_appstream:
            try:
                rating = float(item_info.get("review_rating"))
                review_count = int(item_info.get("review_count"))
            except (TypeError, ValueError):
                rating = -1.0
                review_count = 0

            if review_count > 0 and 0.0 <= rating <= 100.0:
                aggregate = Gtk.Label()
                aggregate.set_markup(
                    f'<span size="large" weight="bold">★ {rating / 20.0:.1f}</span>'
                    f'  <span>({review_count})</span>'
                )
                aggregate.set_halign(Gtk.Align.END)
                aggregate.set_valign(Gtk.Align.CENTER)
                # Match the icon's extra inset on the opposite outer edge.
                aggregate.set_margin_end(4)
                aggregate.set_selectable(False)
                aggregate.set_can_focus(False)
                # pack_end leaves any spare header width between the app identity
                # on the left and the ODRS aggregate on the right.
                top_row.pack_end(aggregate, False, False, 0)

        # Increase the application icon from the regular 38 px presentation to
        # 48 px. File-backed icons need their pixbuf reloaded at the new size;
        # themed icons only need a larger pixel-size request.
        large_icon_size = 48
        icon_value = item_info.get("icon", "application-x-executable")

        if isinstance(icon_widget, Gtk.Image):
            if icon_value.endswith(".png") or icon_value.endswith(".svg"):
                if not os.path.isabs(icon_value) and "/" not in icon_value:
                    icon_path = get_icon_path(
                        "local-script.svg"
                        if ".local/linuxtoys/scripts" in (item_info.get("path") or "")
                        else icon_value
                    )
                else:
                    icon_path = icon_value if os.path.exists(icon_value) else None

                if icon_path and os.path.exists(icon_path):
                    pixbuf = load_scaled_pixbuf(
                        icon_path, large_icon_size, large_icon_size, True
                    )
                    if pixbuf is not None:
                        icon_widget.set_from_pixbuf(pixbuf)
                    else:
                        icon_widget.set_from_icon_name(
                            "application-x-executable", Gtk.IconSize.DIALOG
                        )
                        icon_widget.set_pixel_size(large_icon_size)
            else:
                icon_widget.set_from_icon_name(icon_value, Gtk.IconSize.DIALOG)
                icon_widget.set_pixel_size(large_icon_size)

        base_box.set_orientation(Gtk.Orientation.VERTICAL)
        base_box.set_spacing(10)
        base_box.pack_start(top_row, False, False, 0)

        description = Gtk.Label(label=item_info.get("description", ""))
        description.set_markup(
            f"<span size=\"large\">{html.escape(item_info.get('description', ''))}</span>"
        )
        description.set_line_wrap(True)
        description.set_ellipsize(Pango.EllipsizeMode.END)
        description.set_lines(4)
        description.set_justify(Gtk.Justification.CENTER)
        description.set_halign(Gtk.Align.FILL)
        description.set_valign(Gtk.Align.CENTER)
        description.set_hexpand(True)
        description.set_vexpand(True)
        description.get_style_context().add_class("dim-label")
        base_box.pack_start(description, True, True, 0)

        # Widget margins contribute to preferred size, so subtract the vertical
        # 14+14 px internal padding from the requested content height. The EventBox
        # therefore continues to fit the exact three-row span calculated by Featured.
        outer_height = int(featured_height) if featured_height > 0 else 180
        content_height = max(1, outer_height - 28)
        base_box.set_size_request(108, content_height)
        event_box.set_size_request(128, outer_height)

        base_box.show_all()
        return event_box

    def _is_script_removable(self, item_info):
        """Check if a script item is installed and can be removed."""
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
        if info.get("is_script", False):
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
