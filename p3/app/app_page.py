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
from . import get_icon_path, appstream_cache
from .lang_utils import detect_system_language


class _WidthNeutralTextView(Gtk.TextView):
    """Wrapped app-page text whose content must not establish page width."""

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
        self._build_rating_line()
        self._build_repository_rating_row()
        self._build_actions()
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
        self.pack_start(scroller, True, True, 0)
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
        card_width, card_height = parent._get_featured_card_size()
        fixed_height = (
            separator.get_preferred_height()[1]
            + label.get_preferred_height()[1]
            + int(card_height)
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
        grid_rows = max(0, int(capacity["rows"]))
        rows = 1 + grid_rows
        slot_count = rows * columns

        # Use exactly the same large-card allowance as main-menu Featured.
        eligible_count = len(eligible)
        large_count = parent._calculate_featured_large_count(
            grid_rows, columns, eligible_count
        )
        count = min(eligible_count, max(0, slot_count - (2 * large_count)))
        large_count = min(large_count, count)
        count = min(eligible_count, max(0, slot_count - (2 * large_count)))
        if measuring_columns:
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

        localized_scripts = [
            script for script in remaining_scripts
            if script.get("description_localized", False)
        ]
        other_scripts = [
            script for script in remaining_scripts
            if not script.get("description_localized", False)
        ]
        random.shuffle(localized_scripts)
        random.shuffle(other_scripts)

        large_count = min(
            0 if measuring_columns else large_count,
            len(remaining_scripts),
            max(0, grid_rows // 3) * columns,
        )
        if len(localized_scripts) >= large_count:
            large_scripts = localized_scripts[:large_count]
            normal_scripts = localized_scripts[large_count:] + other_scripts
        else:
            needed = large_count - len(localized_scripts)
            large_scripts = localized_scripts + other_scripts[:needed]
            normal_scripts = other_scripts[needed:]
        random.shuffle(large_scripts)
        random.shuffle(normal_scripts)

        prepared_widgets = []
        occupied = set()
        card_height = int(capacity.get("card_height", card_height))
        row_spacing = int(capacity.get("row_spacing", 18))
        large_height = (3 * card_height) + (2 * row_spacing)

        def prepare_widget(script_info, *, large=False):
            widget = parent.create_item_widget(
                script_info,
                featured_large=large,
                featured_height=large_height if large else 0,
            )
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

        for script_info in first_row_scripts:
            self._featured_fill_flowbox.add(prepare_widget(script_info, large=False))

        large_positions = parent._choose_featured_large_positions(
            grid_rows, columns, large_count
        )
        large_count = min(large_count, len(large_positions), len(large_scripts))
        random.shuffle(large_positions)

        for script_info, position in zip(large_scripts, large_positions):
            column, row = position
            occupied.update(parent._featured_occupied_cells(position))
            self._featured_fill_grid.attach(
                prepare_widget(script_info, large=True), column, row, 1, 3
            )

        free_cells = [
            (column, row)
            for row in range(grid_rows)
            for column in range(columns)
            if (column, row) not in occupied
        ]
        for script_info, (column, row) in zip(normal_scripts, free_cells):
            self._featured_fill_grid.attach(
                prepare_widget(script_info, large=False), column, row, 1, 1
            )

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
        """Build the AppStream description buffer while preserving its block styling."""
        buffer = Gtk.TextBuffer()
        tag_base = buffer.create_tag("as-base", scale=1.10)
        tag_lead = buffer.create_tag("as-lead", scale=1.20)
        tag_list = buffer.create_tag("as-list", left_margin=18, indent=-12, scale=1.10)
        tag_bold = buffer.create_tag("as-bold", weight=Pango.Weight.BOLD)
        tag_italic = buffer.create_tag("as-italic", style=Pango.Style.ITALIC)
        tag_code = buffer.create_tag("as-code", family="monospace")

        def insert_spans(spans, base_tags=()):
            for span in spans or ():
                text = str(span.get("text", "") or "")
                if not text:
                    continue
                tags = list(base_tags)
                for style in span.get("styles", ()):
                    if style == "bold":
                        tags.append(tag_bold)
                    elif style == "italic":
                        tags.append(tag_italic)
                    elif style == "code":
                        tags.append(tag_code)
                end = buffer.get_end_iter()
                if tags:
                    buffer.insert_with_tags(end, text, *tags)
                else:
                    buffer.insert(end, text)

        first_paragraph = True
        rendered_blocks = 0
        for block in blocks or ():
            block_type = block.get("type")
            if block_type == "paragraph":
                if rendered_blocks:
                    buffer.insert(buffer.get_end_iter(), "\n\n")
                insert_spans(block.get("spans"), (tag_lead,) if first_paragraph else (tag_base,))
                first_paragraph = False
                rendered_blocks += 1
            elif block_type in ("unordered_list", "ordered_list"):
                if rendered_blocks:
                    buffer.insert(buffer.get_end_iter(), "\n\n")
                items = block.get("items") or ()
                for index, item in enumerate(items, 1):
                    if index > 1:
                        buffer.insert(buffer.get_end_iter(), "\n")
                    prefix = f"{index}. " if block_type == "ordered_list" else "• "
                    buffer.insert_with_tags(buffer.get_end_iter(), prefix, tag_list)
                    insert_spans(item, (tag_list,))
                rendered_blocks += 1
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
        """Render app-page Markdown directly into a Gtk.TextBuffer.

        Based on the update-dialog renderer, with app-page-specific restrained
        headings and recursive inline parsing so combinations such as
        ``**text with `code`**`` retain both styles.
        """
        buffer = Gtk.TextBuffer()

        tag_bold = buffer.create_tag("md-bold", weight=Pango.Weight.BOLD)
        tag_italic = buffer.create_tag("md-italic", style=Pango.Style.ITALIC)
        tag_code = buffer.create_tag("md-code", family="monospace")
        tag_code_block = buffer.create_tag(
            "md-code-block",
            family="monospace",
            left_margin=14,
            right_margin=14,
            pixels_above_lines=3,
            pixels_below_lines=3,
        )
        tag_table_header = buffer.create_tag(
            "md-table-header", family="monospace", weight=Pango.Weight.BOLD
        )
        tag_table = buffer.create_tag("md-table", family="monospace")
        tag_strike = buffer.create_tag("md-strike", strikethrough=True)
        tag_heading = buffer.create_tag(
            "md-heading",
            weight=Pango.Weight.BOLD,
            scale=1.08,
        )
        # Give the first prose paragraph a little more visual weight without
        # turning it into a heading. Block elements before it do not consume it.
        tag_base = buffer.create_tag("md-base", scale=1.10)
        tag_lead = buffer.create_tag("md-lead", scale=1.20)
        tag_quote = buffer.create_tag(
            "md-quote",
            style=Pango.Style.ITALIC,
            left_margin=18,
            right_margin=8,
        )
        tag_list = buffer.create_tag("md-list", left_margin=18, indent=-12, scale=1.10)
        tag_rule = buffer.create_tag("md-rule")

        inline_pattern = re.compile(
            r"(`[^`]+`)"
            r"|(\[([^\]]+)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\))"
            r"|(\*\*([^*]+)\*\*)"
            r"|(__([^_]+)__)"
            r"|(~~([^~]+)~~)"
            r"|(\*([^*\n]+)\*)"
            r"|(?<!\w)_([^_\n]+)_(?!\w)"
        )

        def insert(value, *tags):
            if not value:
                return
            end_iter = buffer.get_end_iter()
            if tags:
                buffer.insert_with_tags(end_iter, value, *tags)
            else:
                buffer.insert(end_iter, value)

        link_count = 0

        def insert_inline(value, base_tags=()):
            nonlocal link_count
            pos = 0
            for match in inline_pattern.finditer(value):
                insert(value[pos:match.start()], *base_tags)

                if match.group(1):
                    insert(match.group(1)[1:-1], *base_tags, tag_code)
                elif match.group(2):
                    label = match.group(3)
                    url = match.group(4)
                    link_count += 1
                    tag_link = buffer.create_tag(
                        f"md-link-{link_count}",
                        underline=Pango.Underline.SINGLE,
                    )
                    tag_link._markdown_url = url
                    insert_inline(label, (*base_tags, tag_link))
                elif match.group(5):
                    insert_inline(match.group(6), (*base_tags, tag_bold))
                elif match.group(7):
                    insert_inline(match.group(8), (*base_tags, tag_bold))
                elif match.group(9):
                    insert_inline(match.group(10), (*base_tags, tag_strike))
                elif match.group(11):
                    insert_inline(match.group(12), (*base_tags, tag_italic))
                else:
                    insert_inline(match.group(13), (*base_tags, tag_italic))

                pos = match.end()

            insert(value[pos:], *base_tags)

        def split_table_row(value):
            """Split a simple GFM pipe row while preserving escaped pipes."""
            value = value.strip()
            if value.startswith("|"):
                value = value[1:]
            if value.endswith("|") and not value.endswith(r"\|"):
                value = value[:-1]

            cells = []
            current = []
            escaped = False
            for char in value:
                if escaped:
                    current.append(char)
                    escaped = False
                elif char == "\\":
                    escaped = True
                    current.append(char)
                elif char == "|":
                    cells.append("".join(current).strip())
                    current = []
                else:
                    current.append(char)
            cells.append("".join(current).strip())
            return cells

        def table_separator(value):
            cells = split_table_row(value)
            if not cells:
                return None
            aligns = []
            for cell in cells:
                compact = cell.replace(" ", "")
                if not re.fullmatch(r":?-{3,}:?", compact):
                    return None
                if compact.startswith(":") and compact.endswith(":"):
                    aligns.append("center")
                elif compact.endswith(":"):
                    aligns.append("right")
                else:
                    aligns.append("left")
            return aligns

        def render_table(rows, aligns):
            # TextBuffer cannot host a real Gtk.Grid inline, so render tables as
            # a compact monospace grid. Column widths are derived from source
            # text and capped so pathological cells do not explode page width.
            column_count = max(len(row) for row in rows)
            normalized = [row + [""] * (column_count - len(row)) for row in rows]
            widths = []
            for col in range(column_count):
                widths.append(min(40, max(len(row[col]) for row in normalized)))

            for row_index, row in enumerate(normalized):
                pieces = []
                for col, cell in enumerate(row):
                    width = widths[col]
                    align = aligns[col] if col < len(aligns) else "left"
                    plain = re.sub(r"[`*_~]", "", cell)
                    if len(plain) > width:
                        plain = plain[:max(1, width - 1)] + "…"
                    if align == "right":
                        pieces.append(plain.rjust(width))
                    elif align == "center":
                        pieces.append(plain.center(width))
                    else:
                        pieces.append(plain.ljust(width))
                insert(" | ".join(pieces), tag_table_header if row_index == 0 else tag_table)

                # Keep the header visually separated from the body. Because both
                # header and body use the same monospace metrics, the columns stay
                # aligned even though the header is bold.
                if row_index == 0:
                    insert("\n", tag_table)
                    separators = []
                    for col, width in enumerate(widths):
                        align = aligns[col] if col < len(aligns) else "left"
                        if align == "center" and width >= 2:
                            separators.append(":" + "-" * (width - 2) + ":")
                        elif align == "right" and width >= 1:
                            separators.append("-" * (width - 1) + ":")
                        elif align == "left" and col < len(aligns) and aligns[col] == "left" and width >= 1:
                            separators.append("-" * width)
                        else:
                            separators.append("-" * width)
                    insert("-+-".join(separators), tag_table)

                if row_index < len(normalized) - 1:
                    insert("\n")

        lines = str(md_text or "").splitlines()
        index = 0
        in_fence = False
        fence_char = ""
        fence_len = 0
        code_lines = []
        lead_started = False
        lead_finished = False

        while index < len(lines):
            raw_line = lines[index]
            line = raw_line.rstrip()

            fence = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
            if in_fence:
                closing = re.match(r"^\s{0,3}([`~]{3,})\s*$", line)
                if closing and closing.group(1)[0] == fence_char and len(closing.group(1)) >= fence_len:
                    insert("\n".join(code_lines), tag_code_block)
                    code_lines = []
                    in_fence = False
                    if index < len(lines) - 1:
                        insert("\n")
                else:
                    code_lines.append(raw_line)
                index += 1
                continue

            if fence:
                in_fence = True
                fence_char = fence.group(1)[0]
                fence_len = len(fence.group(1))
                code_lines = []
                index += 1
                continue

            # A GFM table starts with a normal row followed immediately by a
            # delimiter row such as | --- | :---: | ---: |.
            if "|" in line and index + 1 < len(lines):
                aligns = table_separator(lines[index + 1])
                if aligns is not None:
                    rows = [split_table_row(line)]
                    index += 2
                    while index < len(lines) and "|" in lines[index] and lines[index].strip():
                        rows.append(split_table_row(lines[index]))
                        index += 1
                    render_table(rows, aligns)
                    if index < len(lines):
                        insert("\n")
                    continue

            heading = re.match(r"^\s*(#{1,6})\s+(.+?)\s*#*\s*$", line)
            unordered = re.match(r"^(\s*)[-+*]\s+(.+)$", line)
            ordered = re.match(r"^(\s*)(\d+)[.)]\s+(.+)$", line)
            quote = re.match(r"^\s*>\s?(.*)$", line)

            is_rule = bool(re.match(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$", line))
            is_block = bool(heading or unordered or ordered or quote or is_rule)

            # The lead style belongs to the first ordinary prose paragraph. A
            # heading/list/etc. before it is ignored; once prose has started, a
            # blank line or another block closes the lead paragraph.
            if lead_started and not lead_finished and (not line.strip() or is_block):
                lead_finished = True

            if is_rule:
                insert("────────────────────────", tag_rule)
            elif heading:
                insert_inline(heading.group(2), (tag_heading,))
            elif unordered:
                depth = min(len(unordered.group(1).expandtabs(4)) // 2, 4)
                prefix = f"{'    ' * depth}• "
                insert(prefix, tag_list)
                insert_inline(unordered.group(2), (tag_list,))
            elif ordered:
                depth = min(len(ordered.group(1).expandtabs(4)) // 2, 4)
                prefix = f"{'    ' * depth}{ordered.group(2)}. "
                insert(prefix, tag_list)
                insert_inline(ordered.group(3), (tag_list,))
            elif quote:
                insert_inline(quote.group(1), (tag_quote,))
            elif line.strip():
                if not lead_started:
                    lead_started = True
                insert_inline(line, (tag_lead,) if not lead_finished else (tag_base,))
            else:
                insert_inline(line)

            if index < len(lines) - 1:
                insert("\n")
            index += 1

        # Unclosed fences remain useful/readable rather than disappearing.
        if in_fence:
            insert("\n".join(code_lines), tag_code_block)

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
            url = getattr(tag, "_markdown_url", None)
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


    def _build_rating_line(self):
        """Show only the cached ODRS aggregate in the header's top-right corner."""
        if not self.script_info.get("is_appstream_entry", False):
            return

        try:
            rating = float(self.script_info.get("review_rating"))
            count = int(self.script_info.get("review_count"))
        except (TypeError, ValueError):
            return
        if count <= 0 or not (0.0 <= rating <= 100.0):
            return

        aggregate = Gtk.Label()
        aggregate.set_markup(
            f'<span size="large" weight="bold">★ {rating / 20.0:.1f}</span>'
            f'  <span>({count})</span>'
        )
        aggregate.set_halign(Gtk.Align.END)
        aggregate.set_valign(Gtk.Align.START)
        aggregate.set_margin_top(16)
        aggregate.set_margin_right(32)
        aggregate.set_selectable(False)
        aggregate.set_can_focus(False)
        self._header_overlay.add_overlay(aggregate)

    def _build_rating_control(self):
        """Build the compact installed-only rating control for the actions row."""
        if not self.script_info.get("is_appstream_entry", False):
            return None

        rating_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        rating_row.set_halign(Gtk.Align.END)
        rating_row.set_valign(Gtk.Align.CENTER)

        self._rating_buttons = []
        for stars in range(1, 6):
            button = Gtk.Button(label="☆")
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_can_focus(False)
            button.set_size_request(24, 24)
            button.set_tooltip_text(
                self.translations.get("app_page_rate_stars", "Rate {stars} stars").format(stars=stars)
            )

            # GTK themes often give ordinary buttons generous horizontal padding.
            # Keep these five glyph-only buttons tight so the whole control fits on
            # the same row as Website/Repository and the install/source actions.
            css = Gtk.CssProvider()
            css.load_from_data(
                b"button { min-width: 20px; min-height: 20px; padding: 1px 3px; margin: 0; }"
            )
            button.get_style_context().add_provider(
                css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            button.connect("clicked", self._on_rating_clicked, stars)
            rating_row.pack_start(button, False, False, 0)
            self._rating_buttons.append(button)

        self._rating_box = rating_row
        return rating_row

    def _build_repository_rating_row(self):
        """Put the rating control on the same row as InfosHead's repository link."""
        if not self.script_info.get("is_appstream_entry", False):
            return

        repo_label = getattr(self.header, "label_repo", None)
        infos_box = getattr(self.header, "vbox_infos", None)
        if repo_label is None or infos_box is None:
            return

        parent = repo_label.get_parent()
        if parent is not None:
            parent.remove(repo_label)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_hexpand(True)
        row.set_halign(Gtk.Align.FILL)
        row.set_valign(Gtk.Align.CENTER)

        # Preserve InfosHead's existing repository/URL label on the left.
        row.pack_start(repo_label, False, False, 0)

        # Let the empty middle of this metadata row absorb translated prompt width
        # instead of competing with install/source/commerce buttons below.
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        row.pack_start(spacer, True, True, 0)

        rating_control = self._build_rating_control()
        if rating_control is not None:
            row.pack_end(rating_control, False, False, 0)

        # _build_developer_line() inserts itself at index 1, leaving the original
        # repository label at index 3 (name, developer, description, repository).
        infos_box.pack_start(row, False, False, 0)
        infos_box.reorder_child(row, 3)
        row.show_all()
        if not str(self.script_info.get("repo", "") or "").strip():
            repo_label.hide()

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

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_halign(Gtk.Align.START)
        row.set_margin_bottom(5)

        label = Gtk.Label()
        label.set_markup(
            f'<span size="small" weight="bold">{GLib.markup_escape_text(developer)}</span>'
        )
        label.set_halign(Gtk.Align.START)
        label.set_selectable(False)
        label.set_can_focus(False)
        row.pack_start(label, False, False, 0)

        badge_path = ""
        if self.script_info.get("is_verified", False):
            badge_path = get_icon_path("verified.svg")
        elif self.script_info.get("is_appstream_entry", False):
            distro_badge = str(self.script_info.get("native_distro_badge", "") or "")
            appstream_badge = str(self.script_info.get("appstream_badge", "") or "")
            if distro_badge:
                badge_path = get_icon_path(distro_badge)
            elif appstream_badge:
                badge_path = get_icon_path(appstream_badge)
        elif self.script_info.get("is_repo_entry", False):
            badge_path = get_icon_path("distros/linuxtoys.svg")
        elif (
            self.script_info.get("is_script", False)
            and not self.script_info.get("is_subcategory", False)
            and ".local/linuxtoys/scripts"
            not in str(self.script_info.get("path", ""))
        ):
            badge_path = get_icon_path("distros/linuxtoys.svg")

        if badge_path and os.path.exists(badge_path):
            try:
                badge_size = 16
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    badge_path, badge_size, badge_size, True
                )
                badge = Gtk.Image.new_from_pixbuf(pixbuf)
                row.pack_start(badge, False, False, 0)
            except Exception:
                pass

        self.header.vbox_infos.pack_start(row, False, False, 0)

        # InfosHead builds the name first, followed by the description/repository.
        # Reorder the developer row directly below the application name.
        self.header.vbox_infos.reorder_child(row, 1)


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

    def _source_menu_item(self, entry, recommended_source):
        item = Gtk.MenuItem()
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        source = self._source_key(entry)
        if source == recommended_source:
            badge_path = get_icon_path("distros/linuxtoys.svg")
            if badge_path and os.path.exists(badge_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        badge_path, 16, 16, True
                    )
                    row.pack_start(Gtk.Image.new_from_pixbuf(pixbuf), False, False, 0)
                except Exception:
                    pass
        row.pack_start(Gtk.Label(label=self._source_label(entry)), False, False, 0)
        item.add(row)
        item.connect("activate", self._on_source_selected, entry)
        return item

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

        menu = Gtk.Menu()
        for option in options:
            if isinstance(option, dict):
                menu.append(self._source_menu_item(option, recommended_source))
        menu.show_all()
        button.set_popup(menu)
        self._source_button = button
        return button

    def _on_source_selected(self, _item, entry):
        self._selected_install_info = entry
        if self._source_button is not None:
            self._set_source_button_content(self._source_button, entry)
        self.refresh_install_state()

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

    def _build_actions(self):
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        install_label = self.translations.get("skills_install_label", " Install ")
        install_button = Gtk.Button(label=install_label)
        self._install_button = install_button
        install_button.set_image(
            Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        )
        install_button.set_size_request(125, 35)
        install_button.connect("clicked", self._on_install_clicked)
        controls.pack_start(install_button, False, False, 0)

        open_button = Gtk.Button()
        self._open_button = open_button
        self._set_action_button_content(
            open_button,
            self.translations.get("app_page_open", " Open "),
            "media-playback-start-symbolic",
        )
        open_button.set_no_show_all(True)
        open_button.hide()
        open_button.connect("clicked", self._on_open_clicked)
        controls.pack_start(open_button, False, False, 0)

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

        # Backward compatibility for script_info produced by an older parser.
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
                False, False, 0
            )

        if subscription_options:
            controls.pack_start(
                self._build_commerce_button("subscription", subscription_options, purchase_url),
                False, False, 0
            )

        if purchase_url and not purchase_options and not subscription_options:
            controls.pack_start(
                self._build_commerce_button("purchase", [], purchase_url),
                False, False, 0
            )

        if homepage_url:
            homepage_button = Gtk.Button()
            self._set_action_button_content(
                homepage_button,
                self.translations.get("app_page_homepage", " Website "),
                "web-browser-symbolic",
            )
            homepage_button.connect("clicked", self._open_url, homepage_url)
            controls.pack_start(homepage_button, False, False, 0)

        if donate_url:
            donate_button = Gtk.Button()
            self._set_action_button_content(
                donate_button,
                self.translations.get("app_page_donate", " Donate "),
                "emblem-favorite-symbolic",
            )
            if not purchase_url and not purchase_options and not subscription_options:
                donate_button.get_style_context().add_class("suggested-action")
            donate_button.connect("clicked", self._open_url, donate_url)
            controls.pack_start(donate_button, False, False, 0)

        controls.set_hexpand(True)
        self.header.vbox_infos.pack_start(controls, False, False, 10)
        self.refresh_install_state()

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

    def _build_screenshot_viewer(self, screenshots):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        previous_button = Gtk.Button.new_from_icon_name(
            "go-previous-symbolic", Gtk.IconSize.BUTTON
        )
        next_button = Gtk.Button.new_from_icon_name(
            "go-next-symbolic", Gtk.IconSize.BUTTON
        )
        previous_button.set_tooltip_text(
            self.translations.get("app_page_previous_screenshot", "Previous screenshot")
        )
        next_button.set_tooltip_text(
            self.translations.get("app_page_next_screenshot", "Next screenshot")
        )
        previous_button.connect("clicked", self._on_screenshot_nav_clicked, -1)
        next_button.connect("clicked", self._on_screenshot_nav_clicked, 1)

        self.screenshot_stack = Gtk.Stack()
        self.screenshot_stack.set_hexpand(True)
        self.screenshot_stack.set_transition_duration(220)

        valid_count = 0
        for screenshot in screenshots:
            variants = self._screenshot_variants(screenshot)
            if not variants:
                continue

            frame = Gtk.Frame()
            frame.set_shadow_type(Gtk.ShadowType.IN)
            frame._linuxtoys_screenshot_variants = variants
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
        row.pack_start(previous_button, False, False, 0)
        row.pack_start(self.screenshot_stack, True, True, 0)
        row.pack_start(next_button, False, False, 0)
        outer.pack_start(row, False, False, 0)

        self.screenshot_counter = Gtk.Label()
        self.screenshot_counter.set_halign(Gtk.Align.CENTER)
        self._update_screenshot_counter()
        outer.pack_start(self.screenshot_counter, False, False, 0)

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
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            image.set_halign(Gtk.Align.CENTER)
            image.set_valign(Gtk.Align.CENTER)
            old = frame.get_child()
            if old is not None:
                frame.remove(old)
            frame.add(image)
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
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            image.set_halign(Gtk.Align.CENTER)
            image.set_valign(Gtk.Align.CENTER)
            old = frame.get_child()
            if old is not None:
                if isinstance(old, Gtk.Spinner):
                    old.stop()
                frame.remove(old)
            frame.add(image)
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
