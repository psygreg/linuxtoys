import os
import random
import re
import webbrowser
import hashlib
import json
import threading
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .gtk_common import Gdk, Gtk, GdkPixbuf, Pango, GLib
from .term_header import InfosHead
from . import get_icon_path, appstream_cache, appstream_extensions, gui_rs, _catalog_rs
from .lang_utils import detect_system_language


class _WidthNeutralTextView(Gtk.TextView):
    """Wrapped app-page text whose content must not establish page width."""

    def do_get_preferred_width(self):
        return (0, 0)

    def do_get_preferred_width_for_height(self, height):
        return (0, 0)


class _WidthNeutralScreenshotFrame(Gtk.Frame):
    """Screenshot frame whose image must follow, not establish, page width."""

    def do_get_preferred_width(self):
        return (0, 0)

    def do_get_preferred_width_for_height(self, height):
        return (0, 0)


class _WidthNeutralStack(Gtk.Stack):
    """Tabbed app-page body that must not establish the window's minimum width."""

    def do_get_preferred_width(self):
        return (0, 0)

    def do_get_preferred_width_for_height(self, height):
        return (0, 0)


class _WidthNeutralStackSwitcher(Gtk.StackSwitcher):
    """Tab selector whose natural width must not establish the app-page/window width."""

    def do_get_preferred_width(self):
        return (0, 0)

    def do_get_preferred_width_for_height(self, height):
        return (0, 0)


class _WidthNeutralFeaturedGrid(Gtk.Grid):
    """Lower Featured rows must not establish the app-page/window width."""

    def do_get_preferred_width(self):
        return (0, 0)

    def do_get_preferred_width_for_height(self, height):
        return (0, 0)


class _WidthNeutralFeaturedFlowBox(Gtk.FlowBox):
    """App-page measuring FlowBox that must not establish window width."""

    def do_get_preferred_width(self):
        return (0, 0)

    def do_get_preferred_width_for_height(self, height):
        return (0, 0)


class AppPageView(Gtk.Box):
    """Repository-entry details page with screenshots and install/support actions."""

    def __init__(self, script_info, parent, translations=None, on_install_callback=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.script_info = script_info
        self.parent = parent
        self.translations = translations or {}
        self.on_install_callback = on_install_callback
        self._selected_install_info = script_info
        self._source_button = None
        self._install_button = None
        self._open_button = None
        self._install_state = "available"
        self._rating_buttons = []
        self._rating_box = None
        self._rating_submitting = False
        self.screenshot_index = 0
        self.screenshot_stack = None
        self.screenshot_counter = None
        self._screenshot_autoplay_source = None
        self._destroyed = False
        self._featured_fill_source = None
        self._featured_fill_signature = None
        self._featured_fill_first_draw = True
        self._featured_fill_box = None
        self._featured_fill_flowbox = None
        self._featured_fill_grid = None
        self._featured_flow_columns = None
        self._featured_flow_width = 0
        self._remote_screenshots_pending = 0
        self._responsive_textviews = []
        self._description_translation_button = None
        self._description_translation_spinner = None
        self._description_original_blocks = None
        self._description_translated_blocks = None
        self._description_view = None
        self._description_showing_translation = False
        self._body_holder = None
        self._body_stack = None
        self._body_switcher = None
        self._extensions_view = None
        self.connect("destroy", self._on_destroy)

        self.header = InfosHead(self.translations, show_terminal_controls=False)
        self.header._update_header_labels(script_info)

        # Keep secondary metadata such as the ODRS rating out of InfosHead's
        # left-side information column. An overlay lets it occupy the free
        # top-right corner without changing the header's existing layout.
        self._header_overlay = Gtk.Overlay()
        self._header_overlay.add(self.header)

        self._build_name_line()
        self._build_developer_line()
        self._build_native_header_actions()
        self.pack_start(self._header_overlay, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.set_margin_left(32)
        content.set_margin_right(32)
        content.set_margin_top(8)
        content.set_margin_bottom(24)
        scroller.add(content)
        self._content_scroller = scroller
        self._content_box = content

        self._last_content_widget = None

        screenshots = script_info.get("screenshots") or []
        if screenshots:
            screenshot_viewer = self._build_screenshot_viewer(screenshots)
            content.pack_start(screenshot_viewer, False, False, 0)
            self._last_content_widget = screenshot_viewer

        long_description = str(script_info.get("long_description", "") or "").strip()
        long_description_blocks = script_info.get("long_description_blocks") or []
        if long_description_blocks and script_info.get("long_description_format") == "appstream":
            description = self._build_translatable_appstream_description(long_description_blocks)
            content.pack_start(description, False, False, 0)
            self._last_content_widget = description
        elif long_description:
            description = self._build_long_description(
                long_description,
                script_info.get("long_description_format") == "markdown",
            )
            content.pack_start(description, False, False, 0)
            self._last_content_widget = description

        self._build_featured_fill()
        self._body_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.pack_start(self._body_holder, True, True, 0)
        self._sync_extensions_tabs()
        self.set_border_width(12)

        # Re-evaluate only after GTK has wrapped/measured the real page contents.
        # Do not schedule Featured from every intermediate GTK allocation.
        # Initial population comes from map; window resizing is handled by the
        # single top-level settled-resize coordinator.
        self.connect("map", self._schedule_featured_fill)

    def _build_featured_fill(self):
        """Create a dormant Featured section used only when the page has spare height."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_no_show_all(True)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(separator, False, False, 0)

        label = Gtk.Label(
            label=self.translations.get("featured_scripts", "Try These")
        )
        label.set_halign(Gtk.Align.START)
        label.set_markup(f"<big><b>{label.get_text()}</b></big>")
        label.get_style_context().add_class("title-2")
        box.pack_start(label, False, False, 0)

        # The first visible row is a FlowBox. GTK can therefore reflow it from
        # the real app-page allocation without the Featured section establishing
        # its own window width. The rows below inherit the resulting column count.
        flowbox = _WidthNeutralFeaturedFlowBox()
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_homogeneous(True)
        flowbox.set_min_children_per_line(1)
        flowbox.set_max_children_per_line(5)
        flowbox.set_column_spacing(16)
        flowbox.set_row_spacing(18)
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_hexpand(True)
        flowbox.connect("size-allocate", self._on_featured_flowbox_allocate)
        box.pack_start(flowbox, False, False, 0)

        grid = _WidthNeutralFeaturedGrid()
        grid.set_valign(Gtk.Align.START)
        grid.set_column_homogeneous(True)
        # Large Featured cards span two rows. Without homogeneous grid rows, GTK
        # is free to satisfy overlapping two-row height requests by distributing
        # height unevenly between individual rows, so the exact same card can look
        # taller or shorter depending on neighboring large-card placements. Keep
        # every lower-grid row at one shared height; a large card then always owns
        # exactly two identical rows plus the row spacing.
        grid.set_row_homogeneous(True)
        grid.set_column_spacing(22)
        grid.set_row_spacing(18)
        box.pack_start(grid, False, False, 0)

        self._featured_fill_box = box
        self._featured_fill_flowbox = flowbox
        self._featured_fill_grid = grid
        self._content_box.pack_start(box, False, False, 0)

    def _on_featured_flowbox_allocate(self, flowbox, allocation):
        """Derive columns directly from this width-neutral FlowBox allocation."""
        available_width = int(allocation.width)
        if available_width <= 1:
            return False

        self._featured_flow_width = available_width
        if getattr(self.parent, "_window_resize_pending", False):
            # Record geometry only. Column arithmetic and rebuilding wait for the
            # single settled-resize pass.
            return False

        # 128px is only the hard minimum size request of an ordinary script
        # widget; it is not a useful layout column width. At normal app-page
        # widths it trivially allows all five columns (~704px total), which is why
        # the previous implementation effectively stayed at five columns.
        #
        # Use a dedicated *layout* minimum instead. Cards remain free to expand
        # homogeneously beyond this width; this value only controls when another
        # column is allowed to appear.
        minimum_card_width = 280

        spacing = int(flowbox.get_column_spacing())
        columns = max(
            1,
            (available_width + spacing)
            // (minimum_card_width + spacing),
        )

        max_columns = 5
        categories_flowbox = getattr(self.parent, "categories_flowbox", None)
        if categories_flowbox is not None:
            configured = int(categories_flowbox.get_max_children_per_line())
            if configured > 0:
                max_columns = configured
        columns = min(max_columns, int(columns))

        # Re-evaluate on *every* meaningful FlowBox allocation. This is what
        # makes shrinking symmetric with growing: a 4-column layout cannot stay
        # latched merely because it was previously locked to four children.
        if columns != self._featured_flow_columns:
            self._featured_flow_columns = columns
            flowbox.set_min_children_per_line(columns)
            flowbox.set_max_children_per_line(columns)
            self._featured_fill_signature = None
            self._schedule_featured_fill()

        return False

    def _schedule_featured_fill(self, *_args):
        if self._destroyed:
            return False

        if getattr(self.parent, "_window_resize_pending", False):
            return False

        if self._featured_fill_source is not None:
            GLib.source_remove(self._featured_fill_source)
        self._featured_fill_source = GLib.timeout_add(
            120, self._refresh_featured_fill
        )
        return False

    def on_window_resize_settled(self, *, size_changed=True):
        """Consume final window geometry once after the global resize debounce."""
        if self._destroyed:
            return False

        # Re-evaluate FlowBox columns from its final allocation. The handler only
        # rebuilds when the calculated column count actually changes.
        flowbox = self._featured_fill_flowbox
        if flowbox is not None:
            allocation = flowbox.get_allocation()
            self._on_featured_flowbox_allocate(flowbox, allocation)

        # Wrapped TextViews need a final height-for-width fit, but not one for
        # every intermediate allocation produced during the drag.
        for view in tuple(self._responsive_textviews):
            try:
                self._fit_markdown_view_height(view)
            except (RuntimeError, AttributeError):
                pass

        # Screenshot presentation stays fixed, but source variant selection follows
        # the final allocation in both grow and shrink directions.
        if self.screenshot_stack is not None:
            for frame in self.screenshot_stack.get_children():
                try:
                    self._on_screenshot_size_allocate(frame, frame.get_allocation())
                except (RuntimeError, AttributeError):
                    pass

        self._featured_fill_signature = None if size_changed else self._featured_fill_signature
        self._schedule_featured_fill()
        return False

    def _clear_featured_fill(self):
        if self._featured_fill_flowbox is not None:
            for child in self._featured_fill_flowbox.get_children():
                child.destroy()
        if self._featured_fill_grid is not None:
            for child in self._featured_fill_grid.get_children():
                child.destroy()

    def _refresh_featured_fill(self):
        """Fill only the viewport space below the page's actual rendered content."""
        self._featured_fill_source = None
        if self._destroyed or self._featured_fill_box is None:
            return False

        # Remote screenshots begin life as tiny spinners. Measuring at that point
        # makes the page look artificially empty and can massively over-populate
        # Featured. Wait until every screenshot has either loaded or failed.
        if self._remote_screenshots_pending > 0:
            self._featured_fill_box.hide()
            self._clear_featured_fill()
            self._featured_fill_signature = None
            return False

        viewport_height = self._content_scroller.get_allocated_height()
        viewport_width = self._content_scroller.get_allocated_width()
        if viewport_height <= 1 or viewport_width <= 1:
            return False

        # Measure from the last real app-page widget directly. Featured is packed
        # after that widget, so its visibility cannot change this bottom edge.
        # Do NOT hide/show Featured merely to measure: doing so causes another GTK
        # size-allocation, which schedules another refresh and briefly destroys the
        # pointer/tooltip state of the cards.
        last_widget = self._last_content_widget
        if last_widget is not None:
            allocation = last_widget.get_allocation()
            used_bottom = allocation.y + allocation.height
        else:
            # An app with neither screenshots nor a long description has no body
            # content below the content box's top margin.
            used_bottom = self._content_box.get_margin_top()

        # Scrolling is determined solely by the normal app-page content. Featured
        # must never be the reason an app page acquires a scrollbar or asks GTK for
        # a larger window.
        bottom_margin = self._content_box.get_margin_bottom()
        base_height = used_bottom + bottom_margin
        if base_height >= viewport_height:
            self._featured_fill_box.hide()
            self._clear_featured_fill()
            self._featured_fill_signature = None
            return False
        if not getattr(self.parent, "all_scripts", None):
            self._clear_featured_fill()
            self._featured_fill_signature = None
            return False

        parent = self.parent
        eligible = parent._eligible_featured_scripts()
        if not eligible:
            self._clear_featured_fill()
            self._featured_fill_signature = None
            return False

        children = self._featured_fill_box.get_children()
        separator = children[0]
        label = children[1]
        card_width, fallback_card_height = parent._get_featured_card_size()

        # App-page Featured has its own ordinary-card geometry. Once the measuring
        # FlowBox has been allocated, use the height GTK actually gave those cards
        # instead of the representative main-menu card height. This keeps a large
        # card exactly two app-page rows tall.
        measured_row_height = 0
        for flow_child in self._featured_fill_flowbox.get_children():
            try:
                child = flow_child.get_child()
                height = int((child or flow_child).get_allocated_height())
            except (AttributeError, RuntimeError, TypeError):
                height = 0
            if height > 1:
                measured_row_height = max(measured_row_height, height)

        card_height = measured_row_height or int(fallback_card_height)
        fixed_height = (
            separator.get_preferred_height()[1]
            + label.get_preferred_height()[1]
            + card_height
            + (self._featured_fill_box.get_spacing() * 3)
        )

        capacity = parent.calculate_featured_capacity(
            viewport_height,
            used_bottom,
            fixed_height=fixed_height,
            row_spacing=self._featured_fill_grid.get_row_spacing(),
            bottom_padding=bottom_margin,
        )
        if capacity is None:
            self._clear_featured_fill()
            self._featured_fill_signature = None
            return False

        # The first row belongs to the FlowBox. Before it has measured the real
        # allocation, give it the maximum candidate count so natural wrapping can
        # discover the actual number that fits. After that, its observed count is
        # authoritative for every lower Grid row.
        max_columns = 5
        categories_flowbox = getattr(parent, "categories_flowbox", None)
        if categories_flowbox is not None:
            configured = int(categories_flowbox.get_max_children_per_line())
            if configured > 0:
                max_columns = configured

        measuring_columns = self._featured_flow_columns is None
        columns = int(self._featured_flow_columns or max_columns)
        columns = max(1, min(max_columns, columns))
        # calculate_featured_capacity() is shared with the main menu and therefore
        # bases its row count on the main-menu representative card. Recalculate only
        # the app-page lower-grid rows from the measured FlowBox row height.
        available_grid_height = int(capacity.get("available_rows_height", 0))
        grid_row_spacing = max(0, int(self._featured_fill_grid.get_row_spacing()))
        if available_grid_height < card_height:
            grid_rows = 0
        else:
            grid_rows = 1 + (
                available_grid_height - card_height
            ) // (card_height + grid_row_spacing)
        grid_rows = max(0, int(grid_rows))
        rows = 1 + grid_rows

        # App-page Featured has two distinct layout regions:
        #   1. the first FlowBox row, which is always ordinary cards and exists
        #      primarily to measure the real number of columns;
        #   2. the lower Grid, which is the only region allowed to contain large
        #      two-row cards.
        #
        # Keep their capacities separate so the measuring row can never be
        # interpreted as space available to a large card.
        first_row_count = columns
        grid_slot_count = grid_rows * columns

        eligible_count = len(eligible)
        large_count = parent._calculate_featured_large_count(
            grid_rows, columns, eligible_count
        )

        # A large card may only consume two rows in the lower Grid. Clamp the
        # shared main-menu heuristic to the physical capacity of that region
        # before converting Grid slots into an item count.
        max_grid_large_count = max(0, grid_rows // 2) * columns
        large_count = min(
            large_count,
            max_grid_large_count,
            max(0, eligible_count - first_row_count),
        )

        # Every two-row large card consumes one additional Grid slot compared
        # with an ordinary card.
        grid_item_count = max(0, grid_slot_count - large_count)
        count = min(
            eligible_count,
            first_row_count + grid_item_count,
        )

        if measuring_columns:
            # During the provisional measuring pass the FlowBox receives the
            # maximum possible ordinary-card row and the lower Grid stays empty.
            count = min(eligible_count, max(count, max_columns))

        current_key = parent._featured_script_key(self.script_info)
        scripts = parent.select_featured_scripts_for_app_page(
            count,
            exclude_keys={current_key},
            category=self.script_info.get("category"),
        )
        if not scripts:
            self._clear_featured_fill()
            self._featured_fill_signature = None
            return False

        large_count = min(large_count, len(scripts))
        count = len(scripts)

        # Geometry is the stable signature. Do not randomize the app-page selection
        # on every size-allocation callback.
        geometry = (rows, columns, large_count, count)
        previous_geometry = (
            self._featured_fill_signature[:4]
            if self._featured_fill_signature
            else None
        )
        if (
            geometry == previous_geometry
            and self._featured_fill_flowbox.get_children()
        ):
            for child in self._featured_fill_box.get_children():
                child.show_all()
            self._featured_fill_box.show()

            # The first populated layout is deliberately rendered at opacity 0 so
            # GTK can account for its real height without flashing the provisional
            # row count. This is the follow-up pass, so reveal the settled layout.
            if not self._featured_fill_first_draw:
                self._featured_fill_box.set_opacity(1.0)
            return False

        self._clear_featured_fill()

        # Keep the FlowBox row visually ordinary so it can be the reliable
        # horizontal measuring authority. Large cards remain in the lower Grid.
        if measuring_columns:
            first_row_scripts = scripts[:max_columns]
            remaining_scripts = []
        else:
            first_row_scripts = scripts[:columns]
            remaining_scripts = scripts[columns:]

        # App-page Featured keeps its unique two-stage layout: the first row is
        # still a FlowBox and remains the sole authority for the real column count.
        # Only the lower-grid assignment is planned in Rust. The app-page candidate
        # selection above (Myket affinity first) is intentionally unchanged.
        large_count = min(
            0 if measuring_columns else large_count,
            len(remaining_scripts),
            max(0, grid_rows // 2) * columns,
        )

        prepared_widgets = []
        # Keep the exact row height established by the app-page measuring FlowBox.
        # Do not replace it with capacity["card_height"], which belongs to the main
        # Featured geometry.
        row_spacing = int(self._featured_fill_grid.get_row_spacing())
        large_height = (2 * card_height) + row_spacing

        def finish_featured_widget(widget, script_info):
            widget.set_tooltip_text(script_info.get("description") or None)
            widget.set_can_focus(True)
            widget.connect("key-press-event", parent._on_featured_card_key_press)
            widget.add_events(
                Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK
            )
            widget.connect("enter-notify-event", parent._on_featured_card_enter)
            widget.connect("leave-notify-event", parent._on_featured_card_leave)
            prepared_widgets.append(widget)
            return widget

        # Preserve the measuring FlowBox behavior exactly: before its first real
        # allocation it receives max_columns ordinary cards and no lower-grid cards.
        first_row_widgets = parent.create_native_item_batch(
            self._featured_fill_flowbox, first_row_scripts
        )
        if first_row_widgets is None:
            raise RuntimeError("App-page Featured first row requires native GTK cards")
        for widget, script_info in zip(first_row_widgets, first_row_scripts):
            finish_featured_widget(widget, script_info)

        previous_large_positions = list(
            getattr(parent, "_featured_large_positions", set())
        )
        candidate_flags = [
            (bool(script.get("description_localized", False)), False)
            for script in remaining_scripts
        ]
        grid_plan = _catalog_rs.featured_layout_plan(
            candidate_flags,
            grid_rows,
            columns,
            large_count,
            previous_large_positions,
            random.getrandbits(64),
        ) if remaining_scripts else []

        large_entries = [
            (remaining_scripts[index], (column, row))
            for index, column, row, is_large in grid_plan
            if is_large
        ]
        normal_entries = [
            (remaining_scripts[index], (column, row))
            for index, column, row, is_large in grid_plan
            if not is_large
        ]
        parent._featured_large_positions = {position for _script, position in large_entries}
        large_count = len(large_entries)

        # Large Featured cards use the same two-row geometry as the main section.
        for script_info, position in large_entries:
            widget = parent.create_native_featured_large_widget(
                self._featured_fill_grid,
                script_info,
                position,
                featured_height=large_height,
            )
            if widget is None:
                raise RuntimeError("App-page large Featured card creation failed")
            finish_featured_widget(widget, script_info)

        if normal_entries:
            normal_grid_widgets = parent.create_native_featured_grid_batch(
                self._featured_fill_grid, normal_entries
            )
            if normal_grid_widgets is None:
                raise RuntimeError("App-page Featured grid requires native GTK cards")
            for widget, (script_info, _position) in zip(
                normal_grid_widgets, normal_entries
            ):
                finish_featured_widget(widget, script_info)

        self._featured_fill_signature = (
            rows,
            columns,
            large_count,
            count,
            tuple(parent._featured_script_key(script) for script in scripts),
        )
        # _featured_fill_box has no-show-all enabled deliberately so the
        # AppPageView's initial page.show_all() cannot expose an unmeasured
        # Featured section. Reveal its descendants normally, then explicitly
        # show the no-show-all root once we know it fits.
        for child in self._featured_fill_box.get_children():
            child.show_all()

        if self._featured_fill_first_draw or self._featured_flow_columns is None:
            # Keep the provisional Featured layout fully allocated but visually
            # transparent. Unlike hide(), opacity does not remove it from GTK's
            # layout, so the next pass sees the same geometry that previously
            # caused the visible draw/redraw. This is a sh*tty solution to the
            # redraw problem but it's the best I could come up with. Any ideas?
            self._featured_fill_box.set_opacity(0.0)
            self._featured_fill_box.show()
            self._featured_fill_first_draw = False

            # Do not rely solely on size-allocate to produce the settling pass.
            # Schedule it explicitly after GTK has had a chance to allocate this
            # transparent first layout.
            self._schedule_featured_fill()
            return False

        self._featured_fill_box.set_opacity(1.0)
        self._featured_fill_box.show()
        parent.animate_item_batch(prepared_widgets)
        return False

    @staticmethod
    def _normalized_language(value):
        value = str(value or "").strip().replace("_", "-")
        return value.split("-", 1)[0].casefold() if value else ""

    def _description_needs_translation(self):
        # Native AppStream metadata does not reliably preserve which locale
        # supplied the already-selected long description. Always offer the
        # best-effort translation action for native entries rather than hiding
        # it based on an uncertain locale. Flatpak entries retain locale
        # provenance, so keep the precise source-vs-target check for them.
        if self.script_info.get("appstream_source") != "flatpak":
            return True

        source = self._normalized_language(self.script_info.get("long_description_locale"))
        target = self._normalized_language(detect_system_language())
        return bool(source and target and source != target)

    def _build_translatable_appstream_description(self, blocks):
        self._description_original_blocks = blocks
        self._description_view = self._build_appstream_description(blocks)

        if not self._description_needs_translation():
            return self._description_view

        # Give the translation control its own compact row.  Gtk.Overlay does not
        # reserve layout space for overlays, so placing the button over the TextView
        # allowed the first wrapped lines to run underneath it.
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        container.set_hexpand(True)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        button_row.set_hexpand(True)

        button = Gtk.Button()
        self._set_translation_button_symbol(button)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.set_halign(Gtk.Align.END)
        button.set_valign(Gtk.Align.CENTER)
        button.set_can_focus(False)
        button.set_tooltip_text(self.translations.get("app_page_translate", "Translate"))
        button.connect("clicked", self._on_translate_description_clicked)
        button_row.pack_end(button, False, False, 0)

        container.pack_start(button_row, False, False, 0)
        container.pack_start(self._description_view, False, False, 0)
        self._description_translation_button = button
        return container

    def _translation_cache_path(self):
        app_id = str(self.script_info.get("appstream_id") or self.script_info.get("id") or "").strip()
        target = self._normalized_language(detect_system_language())
        payload = json.dumps(
            self._description_original_blocks or [], ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        key = hashlib.sha256(f"{app_id}\0{target}\0{digest}".encode("utf-8")).hexdigest()
        cache_dir = appstream_cache.CACHE_DIR / "translations"
        return cache_dir / f"{key}.json"

    def _load_cached_description_translation(self):
        path = self._translation_cache_path()
        try:
            with open(path, "r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, list) else None
        except (OSError, ValueError, TypeError):
            return None

    def _save_cached_description_translation(self, blocks):
        path = self._translation_cache_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".tmp")
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(blocks, handle, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp, path)
        except OSError:
            pass

    @staticmethod
    def _set_translation_button_symbol(button):
        """Use a bold text symbol without depending on a particular icon theme."""
        child = button.get_child()
        if child is not None:
            button.remove(child)
        label = Gtk.Label()
        label.set_markup("<b>文/A</b>")
        button.add(label)
        label.show()

    @staticmethod
    def _google_translate_text(text, target_language):
        """Best-effort translation through Google's public web endpoint.

        Use POST rather than putting the description in the URL. Besides avoiding
        URL-length failures, this behaves better with punctuation and non-ASCII
        AppStream prose. This remains an unofficial endpoint and may be throttled.
        """
        text = str(text or "")
        if not text.strip():
            return text

        data = urlencode({
            "client": "gtx",
            "sl": "auto",
            "tl": target_language,
            "dt": "t",
            "q": text,
        }).encode("utf-8")
        request = Request(
            "https://translate.googleapis.com/translate_a/single",
            data=data,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) LinuxToys/1",
                "Accept": "application/json,text/plain,*/*",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.load(response)
        except HTTPError as exc:
            # Keep the concrete HTTP status in stderr; the UI remains best-effort.
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            raise RuntimeError(
                f"Google Translate HTTP {exc.code}: {detail or exc.reason}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"Google Translate connection failed: {exc.reason}") from exc

        segments = payload[0] if isinstance(payload, list) and payload else []
        translated = "".join(
            str(segment[0]) for segment in segments
            if isinstance(segment, list) and segment and segment[0] is not None
        )
        if not translated:
            raise ValueError("Google Translate returned an empty translation")
        return translated

    def _translate_description_blocks(self, blocks, target_language):
        translated = []
        for block in blocks or ():
            copy_block = {"type": block.get("type")}
            if block.get("type") == "paragraph":
                copy_block["spans"] = self._translate_description_spans(
                    block.get("spans") or (), target_language
                )
            elif block.get("type") in ("unordered_list", "ordered_list"):
                copy_block["items"] = [
                    self._translate_description_spans(item, target_language)
                    for item in block.get("items") or ()
                ]
            else:
                copy_block.update(block)
            translated.append(copy_block)
        return translated

    def _translate_description_spans(self, spans, target_language):
        result = []
        for span in spans or ():
            item = dict(span)
            styles = set(item.get("styles") or ())
            if "code" not in styles:
                item["text"] = self._google_translate_text(item.get("text", ""), target_language)
            result.append(item)
        return result

    def _on_translate_description_clicked(self, _button):
        if self._description_showing_translation:
            self._set_appstream_description_blocks(self._description_original_blocks)
            self._description_showing_translation = False
            self._description_translation_button.set_tooltip_text(
                self.translations.get("app_page_translate", "Translate")
            )
            return

        if self._description_translated_blocks is not None:
            self._show_description_translation(self._description_translated_blocks)
            return

        cached = self._load_cached_description_translation()
        if cached is not None:
            self._description_translated_blocks = cached
            self._show_description_translation(cached)
            return

        button = self._description_translation_button
        button.set_sensitive(False)
        child = button.get_child()
        if child is not None:
            button.remove(child)
        spinner = Gtk.Spinner()
        spinner.start()
        button.add(spinner)
        spinner.show()
        self._description_translation_spinner = spinner
        target = self._normalized_language(detect_system_language())

        def worker():
            try:
                translated = self._translate_description_blocks(
                    self._description_original_blocks, target
                )
                self._save_cached_description_translation(translated)
                GLib.idle_add(self._finish_description_translation, translated, None)
            except Exception as exc:
                print(f"AppStream description translation failed: {exc}", flush=True)
                GLib.idle_add(self._finish_description_translation, None, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_description_translation(self, translated, error):
        if self._destroyed:
            return False
        button = self._description_translation_button
        child = button.get_child() if button is not None else None
        if child is not None:
            button.remove(child)
        self._set_translation_button_symbol(button)
        button.set_sensitive(True)
        self._description_translation_spinner = None

        if translated is not None:
            self._description_translated_blocks = translated
            self._show_description_translation(translated)
        else:
            button.set_tooltip_text(
                self.translations.get("app_page_translate_failed", "Translation failed. Try again.")
            )
        return False

    def _show_description_translation(self, blocks):
        self._set_appstream_description_blocks(blocks)
        self._description_showing_translation = True
        self._description_translation_button.set_tooltip_text(
            self.translations.get("app_page_show_original", "Show original")
        )

    def _set_appstream_description_blocks(self, blocks):
        replacement = self._appstream_description_buffer(blocks)
        self._description_view.set_buffer(replacement)
        self._description_view.set_size_request(-1, 1)
        self._schedule_markdown_view_height_fit(self._description_view)
        self._featured_fill_signature = None
        self._schedule_featured_fill()

    def _appstream_description_buffer(self, blocks):
        """Build the AppStream description buffer in native Rust/GTK."""
        buffer = Gtk.TextBuffer()
        if not gui_rs.populate_appstream_buffer(buffer, blocks):
            raise RuntimeError("Native AppStream description rendering failed")
        return buffer

    def _build_appstream_description(self, blocks):
        """Render preserved AppStream XML semantics directly, without Markdown."""
        view = _WidthNeutralTextView()
        view.get_style_context().add_class("app-page-description")
        view.set_halign(Gtk.Align.FILL)
        view.set_valign(Gtk.Align.START)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_editable(False)
        view.set_cursor_visible(False)
        view.set_can_focus(False)
        view.set_focus_on_click(False)
        view.set_accepts_tab(False)
        view.set_left_margin(0)
        view.set_right_margin(0)
        view.set_pixels_above_lines(0)
        view.set_pixels_below_lines(0)
        view.set_hexpand(True)
        view.set_vexpand(False)
        view.set_size_request(-1, 1)
        view.set_buffer(self._appstream_description_buffer(blocks))
        view._markdown_fit_source = None
        self._responsive_textviews.append(view)
        view.connect("size-allocate", self._schedule_markdown_view_height_fit)
        view.connect("map", self._schedule_markdown_view_height_fit)
        return view

    def _build_long_description(self, text, is_markdown):
        if not is_markdown:
            description = Gtk.Label(label=text)
            description.set_halign(Gtk.Align.FILL)
            description.set_valign(Gtk.Align.START)
            description.set_xalign(0.0)
            description.set_line_wrap(True)
            description.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            description.set_selectable(False)
            description.set_can_focus(False)
            description.set_focus_on_click(False)
            return description

        # App-page Markdown is rendered directly from the source text instead of
        # going through Python-Markdown -> HTML -> TextBuffer. This deliberately
        # preserves source line structure: adjacent list items stay adjacent and
        # explicit blank lines stay blank lines, without HTML "loose list"
        # paragraphs introducing synthetic spacing.
        view = _WidthNeutralTextView()
        view.get_style_context().add_class("app-page-description")
        view.set_halign(Gtk.Align.FILL)
        view.set_valign(Gtk.Align.START)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_editable(False)
        view.set_cursor_visible(False)
        view.set_can_focus(False)
        view.set_focus_on_click(False)
        view.set_accepts_tab(False)
        view.set_left_margin(0)
        view.set_right_margin(0)
        view.set_pixels_above_lines(0)
        view.set_pixels_below_lines(0)
        view.set_hexpand(True)

        view.set_buffer(self._markdown_to_textbuffer(text))

        # Gtk.TextView is scrollable and can otherwise claim spare vertical
        # allocation inside the page's viewport. Keep it height-for-content.
        # Measurement is deferred until GTK has completed wrapping/layout.
        view.set_vexpand(False)
        view.set_size_request(-1, 1)
        view._markdown_fit_source = None
        self._responsive_textviews.append(view)
        view.connect("size-allocate", self._schedule_markdown_view_height_fit)
        view.connect("map", self._schedule_markdown_view_height_fit)
        view.connect("button-release-event", self._on_markdown_link_clicked)
        return view

    def _markdown_to_textbuffer(self, md_text):
        """Render app-page Markdown into a Gtk.TextBuffer in native Rust/GTK."""
        buffer = Gtk.TextBuffer()
        if not gui_rs.populate_markdown_buffer(buffer, md_text):
            raise RuntimeError("Native Markdown rendering failed")
        return buffer

    def _schedule_markdown_view_height_fit(self, view, *_args):
        """Measure Markdown after GTK finishes the current layout pass."""
        if getattr(self.parent, "_window_resize_pending", False):
            return
        if getattr(view, "_markdown_fit_source", None) is None:
            view._markdown_fit_source = GLib.idle_add(
                self._fit_markdown_view_height,
                view,
                priority=GLib.PRIORITY_DEFAULT_IDLE,
            )

    def _fit_markdown_view_height(self, view):
        """Keep a wrapped Markdown TextView only as tall as its rendered text."""
        view._markdown_fit_source = None
        if getattr(self.parent, "_window_resize_pending", False):
            return False

        # If the widget has not received a real width yet, wait for the next
        # allocation. Text wrapping (and therefore height) depends on that width.
        if view.get_allocated_width() <= 1:
            return False

        buffer = view.get_buffer()
        if buffer.get_char_count() == 0:
            desired_height = 1
        else:
            end = buffer.get_end_iter()
            y, line_height = view.get_line_yrange(end)
            desired_height = max(1, y + line_height)

        current_height = view.get_size_request()[1]
        if current_height != desired_height:
            view.set_size_request(-1, desired_height)
            view.queue_resize()

        return False

    def _on_markdown_link_clicked(self, view, event):
        if event.button != 1:
            return False

        x, y = view.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET,
            int(event.x),
            int(event.y),
        )
        iterator = view.get_iter_at_location(x, y)
        if isinstance(iterator, tuple):
            iterator = iterator[-1]

        for tag in iterator.get_tags():
            name = str(tag.get_property("name") or "")
            if not name.startswith("md-link-"):
                continue
            try:
                url = bytes.fromhex(name[len("md-link-"):]).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                continue
            if url:
                try:
                    Gtk.show_uri_on_window(self.parent, url, Gdk.CURRENT_TIME)
                except Exception:
                    webbrowser.open(url)
                return True

        return False

    def _build_name_line(self):
        license_name = str(self.script_info.get("license", "") or "").strip()
        if not license_name:
            return

        name = GLib.markup_escape_text(str(self.script_info.get("name", "") or ""))
        license_markup = GLib.markup_escape_text(license_name)
        self.header.label_name.set_markup(
            f'<big><big><b>{name}</b></big></big>  <span size="small">{license_markup}</span>'
        )


    def _build_native_header_actions(self):
        """Build the repetitive app-page header/action hierarchy in native GTK."""
        is_appstream = bool(self.script_info.get("is_appstream_entry", False))

        aggregate_markup = ""
        show_aggregate = False
        if is_appstream:
            try:
                rating = float(self.script_info.get("review_rating"))
                count = int(self.script_info.get("review_count"))
            except (TypeError, ValueError):
                rating = -1.0
                count = 0
            if count > 0 and 0.0 <= rating <= 100.0:
                aggregate_markup = (
                    f'<span size="large" weight="bold">★ {rating / 20.0:.1f}</span>'
                    f'  <span>({count})</span>'
                )
                show_aggregate = True

        try:
            widgets = gui_rs.populate_app_page_header(
                self._header_overlay,
                self.header.vbox_infos,
                self.header.label_repo,
                aggregate_markup=aggregate_markup,
                install_label=self.translations.get("skills_install_label", " Install "),
                open_label=self.translations.get("app_page_open", " Open "),
                show_aggregate=show_aggregate,
                show_rating=is_appstream,
            )
        except Exception as error:
            raise RuntimeError("Native app-page header construction failed") from error

        if widgets is None:
            raise RuntimeError("Native app-page header construction failed")

        self._install_button = widgets["install_button"]
        self._open_button = widgets["open_button"]
        self._rating_box = widgets["rating_box"]
        self._rating_buttons = widgets["rating_buttons"]
        controls = widgets["controls"]

        self._install_button.connect("clicked", self._on_install_clicked)
        self._open_button.connect("clicked", self._on_open_clicked)

        if self._rating_buttons:
            tooltip = self.translations.get("app_page_rate_stars", "Rate {stars} stars")
            for stars, button in enumerate(self._rating_buttons, start=1):
                button.set_tooltip_text(tooltip.format(stars=stars))
                button.connect("clicked", self._on_rating_clicked, stars)

        # Rust creates the stable shell. Dynamic/source-specific controls remain
        # Python-owned because their presence and behavior are application state.
        source_button = self._build_source_button()
        if source_button is not None:
            controls.pack_start(source_button, False, False, 0)

        purchase_url = self.script_info.get("purchase_url") or ""
        purchase_options = self.script_info.get("purchase_options") or []
        subscription_options = self.script_info.get("subscription_options") or []
        purchase_price = self.script_info.get("purchase_price")
        subscription_price = self.script_info.get("subscription_price")
        donate_url = self.script_info.get("donate_url") or ""
        homepage_url = self.script_info.get("homepage_url") or ""

        if not purchase_options and purchase_url and purchase_price is not None:
            purchase_options = [{
                "name": "",
                "price": purchase_price,
                "currency_symbol": self.script_info.get("purchase_currency_symbol") or "$",
                "url": purchase_url,
            }]
        if not subscription_options and purchase_url and subscription_price is not None:
            subscription_options = [{
                "name": "",
                "months": 1,
                "price": subscription_price,
                "currency_symbol": self.script_info.get("subscription_currency_symbol") or "$",
                "url": purchase_url,
            }]

        if purchase_options:
            controls.pack_start(
                self._build_commerce_button("purchase", purchase_options, purchase_url),
                False, False, 0,
            )
        if subscription_options:
            controls.pack_start(
                self._build_commerce_button("subscription", subscription_options, purchase_url),
                False, False, 0,
            )
        if purchase_url and not purchase_options and not subscription_options:
            controls.pack_start(
                self._build_commerce_button("purchase", [], purchase_url),
                False, False, 0,
            )

        if homepage_url:
            homepage_button = gui_rs.add_app_page_action_button(
                controls, self.translations.get("app_page_homepage", " Website "),
                "web-browser-symbolic",
            )
            if homepage_button is None:
                raise RuntimeError("Native homepage action construction failed")
            homepage_button.connect("clicked", self._open_url, homepage_url)

        if donate_url:
            donate_button = gui_rs.add_app_page_action_button(
                controls, self.translations.get("app_page_donate", " Donate "),
                "emblem-favorite-symbolic",
                suggested=not purchase_url and not purchase_options and not subscription_options,
            )
            if donate_button is None:
                raise RuntimeError("Native donate action construction failed")
            donate_button.connect("clicked", self._open_url, donate_url)

        # Match the old repository/rating row visibility behavior.
        if is_appstream and not str(self.script_info.get("repo", "") or "").strip():
            self.header.label_repo.hide()

        controls.show_all()
        self._open_button.hide()
        self.refresh_install_state()


    def _rating_app_id(self):
        return str(self.script_info.get("appstream_id") or self.script_info.get("id") or "").strip()

    def _refresh_rating_state(self):
        if not self._rating_buttons:
            return
        app_id = self._rating_app_id()
        rated = appstream_cache.has_submitted_odrs_rating(app_id)
        submitted_stars = appstream_cache.get_submitted_odrs_rating(app_id) if rated else None
        enabled = self._install_state == "installed" and not rated and not self._rating_submitting
        for index, button in enumerate(self._rating_buttons, start=1):
            button.set_sensitive(enabled)
            # Once rated, keep the control locked but paint the user's submitted
            # score so the local cache also serves as their rating history.
            if rated and submitted_stars is not None:
                button.set_label("★" if index <= submitted_stars else "☆")
            else:
                button.set_label("☆")
        if self._rating_box is not None:
            # Do not expose the rating control at all unless this exact source is
            # currently installed/removable.  no-show-all keeps later parent
            # show_all() calls from accidentally revealing it while unavailable.
            installed = self._install_state == "installed"
            self._rating_box.set_no_show_all(not installed)
            if installed:
                self._rating_box.show_all()
            else:
                self._rating_box.hide()

            if rated:
                self._rating_box.set_tooltip_text(
                    self.translations.get("app_page_rate_done", "You have already rated this app.")
                )
            else:
                self._rating_box.set_tooltip_text(None)

    def _on_rating_clicked(self, _button, stars):
        if self._install_state != "installed" or self._rating_submitting:
            return
        app_id = self._rating_app_id()
        if not app_id or appstream_cache.has_submitted_odrs_rating(app_id):
            self._refresh_rating_state()
            return

        presets = {
            5: self.translations.get("app_page_rate_5", "Excellent, this app is a must have!!"),
            4: self.translations.get("app_page_rate_4", "Very good app. Give it a try."),
            3: self.translations.get("app_page_rate_3", "Decent pick."),
            2: self.translations.get("app_page_rate_2", "Needs improvements..."),
            1: self.translations.get("app_page_rate_1", "Had issues."),
        }
        summary = presets[int(stars)]
        # The preset review is intentionally not shown here. The user only needs
        # to confirm the score they selected; the localized preset remains the
        # plain-text summary submitted to ODRS below.
        confirm_template = self.translations.get(
            "app_page_rate_confirm_message",
            "This rating cannot be changed or retracted after it is submitted.",
        ).replace("\\n", "\n")
        confirm_warning = confirm_template.split("\n\n", 1)[0].strip()
        star_rating = "★" * int(stars) + "☆" * (5 - int(stars))

        dialog = Gtk.MessageDialog(
            transient_for=self.parent,
            modal=True,
            message_type=Gtk.MessageType.OTHER,
            buttons=Gtk.ButtonsType.NONE,
            text=self.translations.get("app_page_rate_confirm_title", "Submit Rating?"),
        )
        dialog.format_secondary_text(confirm_warning)

        # Keep the explanatory text normally aligned, but present the selected
        # score as its own centered row underneath it.
        star_label = Gtk.Label(label=star_rating)
        star_label.set_halign(Gtk.Align.CENTER)
        star_label.set_xalign(0.5)
        star_label.set_margin_top(12)
        star_label.set_margin_bottom(4)
        star_label.get_style_context().add_class("title-2")
        dialog.get_message_area().pack_start(star_label, False, False, 0)
        star_label.show()

        dialog.add_button(self.translations.get("cancel_btn_label", "Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self.translations.get("app_page_rate_submit", "Submit"), Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return

        self._rating_submitting = True
        self._refresh_rating_state()
        description = self.translations.get("app_page_rate_signature", "Submitted via LinuxToys")
        version = str(self._selected_install_info.get("appstream_version", "") or "unknown")

        def worker():
            success, error = appstream_cache.submit_odrs_rating(
                app_id, stars, summary, description, version
            )
            GLib.idle_add(self._finish_rating_submission, success, error)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_rating_submission(self, success, error):
        self._rating_submitting = False
        self._refresh_rating_state()
        if self._destroyed:
            return False
        if success:
            title = self.translations.get("app_page_rate_success_title", "Rating Submitted")
            message = self.translations.get("app_page_rate_success_message", "Thank you! Your rating was submitted to ODRS.")
            message_type = Gtk.MessageType.INFO
        else:
            title = self.translations.get("app_page_rate_failed_title", "Rating Failed")
            message = self.translations.get("app_page_rate_failed_message", "Could not submit the rating. Please try again later.")
            if error:
                message = f"{message}\n\n{error}"
            message_type = Gtk.MessageType.ERROR
        dialog = Gtk.MessageDialog(
            transient_for=self.parent, modal=True, message_type=message_type,
            buttons=Gtk.ButtonsType.OK, text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
        return False


    def _build_developer_line(self):
        developer = str(self.script_info.get("developer", "") or "").strip()
        if not developer:
            return

        badge_path = ""
        if self.script_info.get("is_official", False):
            badge_path = get_icon_path("ltverified.svg") or ""
        elif self.script_info.get("is_verified", False):
            badge_path = get_icon_path("verified.svg") or ""
        elif self.script_info.get("is_appstream_entry", False):
            distro_badge = str(self.script_info.get("native_distro_badge", "") or "")
            appstream_badge = str(self.script_info.get("appstream_badge", "") or "")
            if distro_badge:
                badge_path = get_icon_path(distro_badge) or ""
            elif appstream_badge:
                badge_path = get_icon_path(appstream_badge) or ""
        elif self.script_info.get("is_repo_entry", False):
            badge_path = get_icon_path("distros/linuxtoys.svg") or ""
        elif (self.script_info.get("is_script", False)
              and not self.script_info.get("is_subcategory", False)
              and ".local/linuxtoys/scripts" not in str(self.script_info.get("path", ""))):
            badge_path = get_icon_path("distros/linuxtoys.svg") or ""

        if badge_path and not os.path.exists(badge_path):
            badge_path = ""
        if not gui_rs.add_app_page_developer_line(self.header.vbox_infos, developer, badge_path):
            raise RuntimeError("Native app-page developer line construction failed")


    def _format_price(self, option):
        symbol = option.get("currency_symbol") or "$"
        return f"{symbol}{option['price']:.2f}"

    def _commerce_button_label(self, kind, options):
        if kind == "purchase":
            plain_key, plain_fallback = "app_page_purchase", " Purchase "
            price_key, price_fallback = "app_page_purchase_price", " Purchase · ${price} "
        else:
            plain_key, plain_fallback = "app_page_subscribe", " Subscribe "
            price_key, price_fallback = "app_page_subscribe_price", " Subscribe · ${price} "

        if not options:
            return self.translations.get(plain_key, plain_fallback)

        lowest = min(options, key=lambda option: option["price"])
        price_text = self._format_price(lowest)
        if len(options) > 1:
            from_template = self.translations.get("app_page_from_price", "from ${price}")
            price_text = from_template.replace("${price}", price_text)

        template = self.translations.get(price_key, price_fallback)
        return template.replace("${price}", "{price}").format(price=price_text)

    def _subscription_option_label(self, option):
        pieces = []
        name = str(option.get("name") or "").strip()
        if name:
            pieces.append(name)

        months = option.get("months")
        if isinstance(months, int) and months > 0:
            if months == 1:
                unit = self.translations.get("app_page_month", "month")
            else:
                unit = self.translations.get("app_page_months", "months")
            pieces.append(f"{months} {unit}")

        pieces.append(self._format_price(option))
        return " · ".join(pieces)

    def _set_action_button_content(self, button, label, icon_name, dropdown=False):
        """Build consistent action-button contents with explicit horizontal padding."""
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        content.set_margin_start(8)
        content.set_margin_end(8)

        content.pack_start(
            Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON),
            False,
            False,
            0,
        )

        text = Gtk.Label(label=str(label).strip())
        content.pack_start(text, False, False, 0)

        if dropdown:
            content.pack_start(
                Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.BUTTON),
                False,
                False,
                0,
            )

        button.add(content)

    def _build_commerce_button(self, kind, options, fallback_url=""):
        label = self._commerce_button_label(kind, options)

        # Tiered purchases and subscriptions with multiple tiers/time frames use
        # a highlighted MenuButton so every choice stays inside the main action.
        if len(options) > 1:
            button = Gtk.MenuButton()
            self._set_action_button_content(
                button, label, "emblem-web-symbolic", dropdown=True
            )
            menu = Gtk.Menu()
            for option in options:
                if kind == "subscription":
                    option_label = self._subscription_option_label(option)
                else:
                    name = str(option.get("name") or "").strip()
                    option_label = " · ".join(
                        part for part in (name, self._format_price(option)) if part
                    )
                item = Gtk.MenuItem(label=option_label)
                item.connect("activate", self._open_url, option["url"])
                menu.append(item)
            menu.show_all()
            button.set_popup(menu)
        else:
            button = Gtk.Button()
            self._set_action_button_content(button, label, "emblem-web-symbolic")
            target_url = options[0]["url"] if options else fallback_url
            button.connect("clicked", self._open_url, target_url)

        button.get_style_context().add_class("suggested-action")
        return button

    def _source_label(self, entry):
        source = str(entry.get("appstream_source", "") or "").strip()
        if source == "flatpak":
            scope = str(entry.get("flatpak_scope", "") or "").strip()
            if scope == "system" and self._has_multiple_flatpak_scopes():
                system = self.translations.get("app_page_source_system", "system")
                return f"Flathub ({system})"
            return "Flathub"
        if source == "native":
            return self.translations.get("app_page_source_native", "Native")
        return source.capitalize() or self.translations.get("app_page_source_native", "Native")

    @staticmethod
    def _source_key(entry):
        source = str(entry.get("appstream_source", "") or "").strip()
        if source != "flatpak":
            return source
        scope = str(entry.get("flatpak_scope", "") or "").strip()
        installation = str(entry.get("flatpak_installation", "") or "").strip()
        return f"flatpak:{scope}:{installation}"

    def _has_multiple_flatpak_scopes(self):
        options = self.script_info.get("source_options") or ()
        scopes = {
            str(option.get("flatpak_scope", "") or "").strip()
            for option in options
            if isinstance(option, dict)
            and str(option.get("appstream_source", "") or "").strip() == "flatpak"
        }
        scopes.discard("")
        return len(scopes) > 1

    def _set_source_button_content(self, button, entry):
        child = button.get_child()
        if child is not None:
            button.remove(child)
        self._set_action_button_content(
            button,
            self._source_label(entry),
            "package-x-generic-symbolic",
            dropdown=True,
        )
        button.show_all()

    def _source_popover_item(self, entry, recommended_source, popover):
        button = Gtk.Button()
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.set_halign(Gtk.Align.FILL)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        source = self._source_key(entry)
        if source == recommended_source:
            badge_path = get_icon_path("distros/linuxtoys.svg")
            if badge_path and os.path.exists(badge_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        badge_path, 16, 16, True
                    )
                    row.pack_start(
                        Gtk.Image.new_from_pixbuf(pixbuf), False, False, 0
                    )
                except Exception:
                    pass

        label = Gtk.Label(label=self._source_label(entry))
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0.0)
        row.pack_start(label, True, True, 0)
        button.add(row)

        def activate(_button):
            popover.popdown()
            self._on_source_selected(_button, entry)

        button.connect("clicked", activate)
        return button

    def _build_source_button(self):
        options = self.script_info.get("source_options") or ()
        if len(options) < 2:
            return None

        recommended_source = str(
            self.script_info.get("recommended_source")
            or self.script_info.get("appstream_source")
            or ""
        )

        button = Gtk.MenuButton()
        self._set_source_button_content(button, self._selected_install_info)

        popover = Gtk.Popover.new(button)
        popover.set_position(Gtk.PositionType.BOTTOM)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_left(4)
        box.set_margin_right(4)

        for option in options:
            if isinstance(option, dict):
                box.pack_start(
                    self._source_popover_item(option, recommended_source, popover),
                    False,
                    False,
                    0,
                )

        popover.add(box)
        box.show_all()
        button.set_popover(popover)

        self._source_button = button
        return button

    def _on_source_selected(self, _item, entry):
        self._selected_install_info = entry
        if self._source_button is not None:
            self._set_source_button_content(self._source_button, entry)

        # A source change may reparent _content_scroller between the bare body and
        # a Details/Extensions Gtk.Stack. Do not let Featured keep geometry measured
        # against the previous body hierarchy while GTK is reallocating the scroller.
        if self._featured_fill_box is not None:
            self._featured_fill_box.hide()
        self._clear_featured_fill()
        self._featured_fill_signature = None

        self._sync_extensions_tabs()
        self.refresh_install_state()

        # Re-measure only after the new body hierarchy has been attached and GTK has
        # had an idle turn to allocate the persistent content scroller in its new
        # parent. _schedule_featured_fill adds the normal settling debounce itself.
        GLib.idle_add(self._schedule_featured_fill)

    def _sync_extensions_tabs(self):
        """Show Details/Extensions only when the selected Flatpak source has addons."""
        if self._body_holder is None:
            return
        extensions = appstream_cache.get_flatpak_extensions(self._selected_install_info)
        # _content_scroller is persistent across source changes. Detach it from
        # whichever temporary body container currently owns it before destroying
        # the old body hierarchy; otherwise the no-extensions layout destroys the
        # scroller itself and the next source selection reuses an invalid widget.
        content_parent = self._content_scroller.get_parent()
        if content_parent is not None:
            content_parent.remove(self._content_scroller)

        for child in list(self._body_holder.get_children()):
            self._body_holder.remove(child)
            child.destroy()

        if not extensions:
            self._body_stack = None
            self._body_switcher = None
            self._extensions_view = None
            self._body_holder.pack_start(self._content_scroller, True, True, 0)
            self._body_holder.show_all()
            return

        stack = _WidthNeutralStack()
        # Keep initialization transition-free. Gtk.Stack only considers visible
        # children when settling its initial visible child, and show_all() below
        # changes child visibility during realization.
        stack.set_transition_type(Gtk.StackTransitionType.NONE)
        stack.set_transition_duration(140)
        stack.add_titled(
            self._content_scroller, "details",
            self.translations.get("app_page_details", "Details"),
        )
        extensions_view = appstream_extensions.AppStreamExtensionsView(
            self.parent, self._selected_install_info, extensions
        )
        stack.add_titled(
            extensions_view, "extensions",
            self.translations.get("app_page_extensions", "Extensions"),
        )
        switcher = _WidthNeutralStackSwitcher()
        switcher.set_stack(stack)
        switcher.set_halign(Gtk.Align.FILL)
        switcher.set_hexpand(True)
        switcher.set_margin_top(2)
        switcher.set_margin_bottom(2)

        # Gtk.StackSwitcher itself can expand while its internal toggle buttons
        # keep their natural widths. Expand those too so Details/Extensions read
        # as two equal-width tabs across the app page rather than centered buttons.
        for child in switcher.get_children():
            child.set_hexpand(True)
            child.set_halign(Gtk.Align.FILL)

        self._body_holder.pack_start(switcher, False, False, 0)
        self._body_holder.pack_start(stack, True, True, 0)
        self._body_stack = stack
        self._body_switcher = switcher
        self._extensions_view = extensions_view

        # Realize/show both stack children first, then choose Details while
        # transitions are disabled. This prevents GTK from settling on the
        # already-visible Extensions child during show_all().
        self._body_holder.show_all()
        stack.set_visible_child(self._content_scroller)

        # User-driven tab changes can animate normally from this point onward.
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

    def set_install_state(self, state):
        """Render the AppStream install action without affecting the rest of the page."""
        button = self._install_button
        if button is None or not self.script_info.get("is_appstream_entry"):
            return

        self._install_state = state
        context = button.get_style_context()
        context.remove_class("destructive-action")

        if state == "installed":
            label = self.translations.get("skills_remove_label", "Remove")
            icon = "edit-delete-symbolic"
            sensitive = True
            context.add_class("destructive-action")
        elif state == "removing":
            label = self.translations.get("skills_removing", "Removing…")
            icon = "folder-download-symbolic"
            sensitive = False
            context.add_class("destructive-action")
        elif state == "queued":
            label = self.translations.get("app_page_queued", "Queued")
            icon = "folder-download-symbolic"
            sensitive = False
        else:
            label = self.translations.get("skills_install_label", "Install")
            icon = "emblem-system-symbolic"
            sensitive = True

        button.set_label(label)
        button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        button.set_sensitive(sensitive)
        if self._source_button is not None:
            self._source_button.set_sensitive(sensitive)

        if self._open_button is not None:
            can_launch = False
            if state == "installed":
                resolver = getattr(self.parent, "_can_launch_appstream_app", None)
                can_launch = bool(
                    resolver is not None
                    and resolver(self._selected_install_info)
                )

            if can_launch:
                self._open_button.set_sensitive(True)
                self._open_button.show()
                child = self._open_button.get_child()
                if child is not None:
                    child.show_all()
            else:
                self._open_button.hide()

        button.show_all()
        self._refresh_rating_state()

    def refresh_install_state(self):
        """Refresh Available/Queued/Installed from the window's session/registry state."""
        if not self.script_info.get("is_appstream_entry"):
            return
        resolver = getattr(self.parent, "_get_appstream_install_state", None)
        state = resolver(self._selected_install_info) if resolver is not None else "available"
        self.set_install_state(state)
        if self._extensions_view is not None:
            self._extensions_view.refresh()

    def _screenshot_variants(self, screenshot):
        """Normalize new AppStream variant groups and legacy string screenshots."""
        if isinstance(screenshot, dict):
            raw = screenshot.get("images") or []
        else:
            raw = [{"url": screenshot, "width": 0, "height": 0}]

        variants = []
        seen = set()
        for item in raw:
            if isinstance(item, dict):
                value = str(item.get("url", "") or "").strip()
                try:
                    width = max(0, int(item.get("width", 0) or 0))
                    height = max(0, int(item.get("height", 0) or 0))
                except (TypeError, ValueError):
                    width = height = 0
            else:
                value = str(item or "").strip()
                width = height = 0
            if not value or value in seen:
                continue
            seen.add(value)
            variants.append({"url": value, "width": width, "height": height})
        variants.sort(key=lambda item: (item["width"], item["height"]))
        return variants

    @staticmethod
    def _choose_screenshot_variant(variants, target_width):
        """Choose the smallest known variant meeting target_width, else the largest."""
        if not variants:
            return None
        sized = [item for item in variants if item.get("width", 0) > 0]
        if not sized:
            return variants[0]
        for item in sized:
            if item["width"] >= target_width:
                return item
        return sized[-1]

    def _screenshot_target_width(self, frame, allocation=None):
        # 1120px is the normal quality floor. Account for the monitor scale factor
        # so a HiDPI window can request a sharper source before it becomes blurry.
        width = allocation.width if allocation is not None else frame.get_allocated_width()
        try:
            scale = max(1, int(frame.get_scale_factor()))
        except Exception:
            scale = 1
        return max(1120, max(0, int(width)) * scale)

    def _on_screenshot_size_allocate(self, frame, allocation):
        # Presentation must follow every allocation, including intermediate drag
        # allocations. Source-variant selection can remain settled-resize-only.
        self._fit_screenshot_to_frame(frame, allocation)

        if getattr(self.parent, "_window_resize_pending", False):
            return
        variants = getattr(frame, "_linuxtoys_screenshot_variants", ())
        if not variants:
            return
        variant = self._choose_screenshot_variant(
            variants, self._screenshot_target_width(frame, allocation)
        )
        if not variant:
            return
        requested_url = getattr(frame, "_linuxtoys_screenshot_requested_url", "")
        # Follow the best AppStream variant in both directions.  A larger
        # allocation may upgrade the source; shrinking may select a smaller one
        # again. Cached variants make subsequent switches inexpensive.
        if variant["url"] != requested_url:
            self._request_screenshot_variant(frame, variant, initial=False)

    @staticmethod
    def _fit_screenshot_to_frame(frame, allocation=None):
        """Scale the displayed screenshot to the frame's current allocation."""
        master = getattr(frame, "_linuxtoys_screenshot_master_pixbuf", None)
        image = getattr(frame, "_linuxtoys_screenshot_image", None)
        if master is None or image is None:
            return

        width = allocation.width if allocation is not None else frame.get_allocated_width()
        # A screenshot can finish loading before its frame receives a useful
        # allocation. Do not collapse it to 1px in that transient state: use the
        # already allocated details viewport as the initial width, then normal
        # size-allocate events take over.
        if int(width) <= 1:
            owner = frame.get_ancestor(Gtk.ScrolledWindow)
            if owner is not None:
                width = owner.get_allocated_width()
        if int(width) <= 1:
            return

        # Leave a tiny allowance for Gtk.Frame borders and never enlarge beyond
        # the normal 760x430 presentation envelope.
        available_width = max(1, int(width) - 4)
        source_width = max(1, master.get_width())
        source_height = max(1, master.get_height())
        scale = min(1.0, 760.0 / source_width, 430.0 / source_height,
                    available_width / source_width)
        target_width = max(1, int(source_width * scale))
        target_height = max(1, int(source_height * scale))

        if getattr(frame, "_linuxtoys_screenshot_display_size", None) == (
            target_width, target_height
        ):
            return

        if target_width == source_width and target_height == source_height:
            displayed = master
        else:
            displayed = master.scale_simple(
                target_width, target_height, GdkPixbuf.InterpType.BILINEAR
            )
        if displayed is not None:
            image.set_from_pixbuf(displayed)
            frame._linuxtoys_screenshot_display_size = (target_width, target_height)

    def _build_screenshot_viewer(self, screenshots):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # The width-neutral stack remains a Python policy widget; Rust owns the
        # repetitive navigation/counter chrome around it.
        self.screenshot_stack = _WidthNeutralStack()
        self.screenshot_stack.set_hexpand(True)
        self.screenshot_stack.set_transition_duration(220)

        valid_count = 0
        for screenshot in screenshots:
            variants = self._screenshot_variants(screenshot)
            if not variants:
                continue

            frame = _WidthNeutralScreenshotFrame()
            frame.set_shadow_type(Gtk.ShadowType.IN)
            frame.set_hexpand(True)
            frame._linuxtoys_screenshot_variants = variants
            frame._linuxtoys_screenshot_master_pixbuf = None
            frame._linuxtoys_screenshot_image = None
            frame._linuxtoys_screenshot_display_size = None
            frame._linuxtoys_screenshot_source_width = 0
            frame._linuxtoys_screenshot_requested_url = ""
            frame._linuxtoys_screenshot_request_id = 0
            frame.connect("size-allocate", self._on_screenshot_size_allocate)

            variant = self._choose_screenshot_variant(variants, 1120)
            if not variant:
                continue
            if not self._request_screenshot_variant(frame, variant, initial=True):
                continue

            self.screenshot_stack.add_named(frame, f"shot_{valid_count}")
            valid_count += 1

        if not valid_count:
            return outer

        self._screenshot_count = valid_count
        self.screenshot_stack.set_visible_child_name("shot_0")
        chrome = gui_rs.populate_screenshot_chrome(
            outer, self.screenshot_stack,
            previous_tooltip=self.translations.get(
                "app_page_previous_screenshot", "Previous screenshot"
            ),
            next_tooltip=self.translations.get(
                "app_page_next_screenshot", "Next screenshot"
            ),
        )
        if chrome is None:
            raise RuntimeError("Native screenshot chrome construction failed")
        previous_button = chrome["previous"]
        next_button = chrome["next"]
        self.screenshot_counter = chrome["counter"]
        previous_button.connect("clicked", self._on_screenshot_nav_clicked, -1)
        next_button.connect("clicked", self._on_screenshot_nav_clicked, 1)
        self._update_screenshot_counter()

        if valid_count == 1:
            previous_button.set_sensitive(False)
            next_button.set_sensitive(False)
        else:
            self._screenshot_autoplay_source = GLib.timeout_add_seconds(
                7, self._auto_cycle_screenshot
            )

        return outer

    def _request_screenshot_variant(self, frame, variant, *, initial=False):
        path = str(variant.get("url", "") or "").strip()
        if not path:
            return False

        frame._linuxtoys_screenshot_requested_url = path
        frame._linuxtoys_screenshot_request_id += 1
        request_id = frame._linuxtoys_screenshot_request_id

        if path.startswith(("https://", "http://")):
            spinner = None
            if initial:
                spinner = Gtk.Spinner()
                spinner.start()
                spinner.set_halign(Gtk.Align.CENTER)
                spinner.set_valign(Gtk.Align.CENTER)
                frame.add(spinner)
                self._remote_screenshots_pending += 1
            self._load_remote_screenshot_async(
                path, frame, spinner, variant, request_id, initial=initial
            )
            return True

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 760, 430, True)
            image = Gtk.Image()
            image.set_halign(Gtk.Align.CENTER)
            image.set_valign(Gtk.Align.CENTER)
            old = frame.get_child()
            if old is not None:
                frame.remove(old)
            frame.add(image)
            frame._linuxtoys_screenshot_master_pixbuf = pixbuf
            frame._linuxtoys_screenshot_image = image
            frame._linuxtoys_screenshot_display_size = None
            self._fit_screenshot_to_frame(frame)
            frame.queue_resize()
            GLib.idle_add(self._fit_screenshot_to_frame, frame)
            frame._linuxtoys_screenshot_source_width = int(variant.get("width", 0) or 0)
            return True
        except Exception:
            return False

    def _load_remote_screenshot_async(self, url, frame, spinner, variant, request_id, *, initial=False):
        """Fetch only the selected AppStream screenshot variant without blocking GTK."""
        cache_dir = Path(os.path.expanduser("~/.cache/linuxtoys/appstream/screenshots"))
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        target = cache_dir / f"{digest}.img"

        def worker():
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
                if not target.is_file():
                    request = Request(url, headers={"User-Agent": "LinuxToys AppStream"})
                    with urlopen(request, timeout=20) as response:
                        data = response.read(12 * 1024 * 1024 + 1)
                    if len(data) > 12 * 1024 * 1024:
                        raise ValueError("screenshot exceeds size limit")
                    tmp = target.with_suffix(".tmp")
                    tmp.write_bytes(data)
                    os.replace(tmp, target)
                if not self._destroyed:
                    GLib.idle_add(
                        self._finish_remote_screenshot, frame, spinner, str(target),
                        variant, request_id, initial
                    )
            except Exception:
                if not self._destroyed:
                    GLib.idle_add(
                        self._fail_remote_screenshot, frame, spinner, request_id, initial
                    )

        threading.Thread(target=worker, daemon=True).start()

    def _remote_screenshot_settled(self, frame):
        """Release the Featured measurement gate once an initial screenshot settles."""
        if getattr(frame, "_linuxtoys_screenshot_settled", False):
            return
        frame._linuxtoys_screenshot_settled = True
        self._remote_screenshots_pending = max(
            0, self._remote_screenshots_pending - 1
        )
        if self._remote_screenshots_pending == 0 and not self._destroyed:
            GLib.timeout_add(80, self._schedule_featured_fill)

    def _finish_remote_screenshot(self, frame, spinner, path, variant, request_id, initial):
        if self._destroyed:
            return False

        # A resize can request a larger variant while an older request is still in
        # flight. Cache the old response, but never let it replace the newer one.
        stale = request_id != getattr(frame, "_linuxtoys_screenshot_request_id", 0)
        if stale and not (initial and spinner is not None and frame.get_child() is spinner):
            if initial:
                self._remote_screenshot_settled(frame)
            return False

        try:
            # Source resolution follows the current allocation, but presentation
            # size must not.  Giving Gtk.Image a maximized-window-sized pixbuf
            # makes that pixbuf part of GTK's preferred-width calculation and can
            # prevent the window from shrinking again.  Keep the same stable
            # presentation size used by local screenshots.
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                path, 760, 430, True
            )
            image = Gtk.Image()
            image.set_halign(Gtk.Align.CENTER)
            image.set_valign(Gtk.Align.CENTER)
            old = frame.get_child()
            if old is not None:
                if isinstance(old, Gtk.Spinner):
                    old.stop()
                frame.remove(old)
            frame.add(image)
            frame._linuxtoys_screenshot_master_pixbuf = pixbuf
            frame._linuxtoys_screenshot_image = image
            frame._linuxtoys_screenshot_display_size = None
            self._fit_screenshot_to_frame(frame)
            frame.queue_resize()
            GLib.idle_add(self._fit_screenshot_to_frame, frame)
            frame._linuxtoys_screenshot_source_width = int(variant.get("width", 0) or 0)
            frame.show_all()
            if initial:
                self._remote_screenshot_settled(frame)
        except Exception:
            return self._fail_remote_screenshot(frame, spinner, request_id, initial)
        return False

    def _fail_remote_screenshot(self, frame, spinner, request_id=None, initial=True):
        if self._destroyed:
            return False
        if request_id is not None and request_id != getattr(frame, "_linuxtoys_screenshot_request_id", 0):
            if initial:
                self._remote_screenshot_settled(frame)
            return False
        try:
            if spinner is not None and frame.get_child() is spinner:
                spinner.stop()
                spinner.hide()
        except Exception:
            pass
        if initial:
            self._remote_screenshot_settled(frame)
        return False

    def _on_screenshot_nav_clicked(self, _button, direction):
        """Stop autoplay permanently once the user navigates the carousel."""
        self._stop_screenshot_autoplay()
        self.cycle_screenshot(direction)

    def _auto_cycle_screenshot(self):
        """Advance the carousel every seven seconds while autoplay is active."""
        if not self.screenshot_stack or getattr(self, "_screenshot_count", 0) < 2:
            self._screenshot_autoplay_source = None
            return False

        self.cycle_screenshot(1)
        return True

    def _on_destroy(self, *_args):
        """Invalidate pending asynchronous work when this app page goes away."""
        self._destroyed = True
        self._stop_screenshot_autoplay()
        if self._featured_fill_source is not None:
            GLib.source_remove(self._featured_fill_source)
            self._featured_fill_source = None

    def _stop_screenshot_autoplay(self, *_args):
        if self._screenshot_autoplay_source is not None:
            GLib.source_remove(self._screenshot_autoplay_source)
            self._screenshot_autoplay_source = None

    def cycle_screenshot(self, direction):
        if not self.screenshot_stack or getattr(self, "_screenshot_count", 0) < 2:
            return

        if direction > 0:
            self.screenshot_stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT
            )
        else:
            self.screenshot_stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_RIGHT
            )

        self.screenshot_index = (
            self.screenshot_index + direction
        ) % self._screenshot_count
        self.screenshot_stack.set_visible_child_name(
            f"shot_{self.screenshot_index}"
        )
        self._update_screenshot_counter()

    def _update_screenshot_counter(self):
        if self.screenshot_counter is not None:
            self.screenshot_counter.set_text(
                f"{self.screenshot_index + 1} / {self._screenshot_count}"
            )

    def _on_open_clicked(self, _button):
        launcher = getattr(self.parent, "_launch_appstream_app", None)
        if launcher is not None:
            launcher(self._selected_install_info)

    def _on_install_clicked(self, _button):
        if self._install_state == "installed":
            remover = getattr(self.parent, "_on_item_remove_clicked", None)
            if remover is not None:
                remover(_button, self._selected_install_info)
            return
        if self.on_install_callback:
            self.on_install_callback(self._selected_install_info)

    def _open_url(self, _button, url):
        try:
            Gtk.show_uri_on_window(self.parent, url, Gdk.CURRENT_TIME)
        except Exception:
            webbrowser.open(url)
