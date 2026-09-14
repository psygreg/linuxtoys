import random

from .gtk_common import Gdk, GLib
from . import parser


class FeaturedCtl:
    FEATURED_REFRESH_MIN_SECONDS = 8
    FEATURED_REFRESH_MAX_SECONDS = 15
    FEATURED_REFRESH_MIN_ITEMS = 10
    FEATURED_REFRESH_MAX_ITEMS = 25
    FEATURED_MAX_ROWS = 10
    FEATURED_RESIZE_DEBOUNCE_MS = 150
    FEATURED_SWAP_ANIMATION_MS = 180

    def _collect_all_scripts(self):
        """Collect direct top-level scripts, preferring already parsed cache data."""
        all_scripts = []
        seen = set()

        def add_scripts(scripts):
            for script in scripts:
                if (
                    not script.get("is_script", False)
                    or script.get("is_create_script", False)
                ):
                    continue
                key = script.get("path") or (
                    script.get("name", ""),
                    script.get("repo", ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                all_scripts.append(script)

        try:
            category_cache = getattr(self, "category_cache", None)
            if category_cache is not None and category_cache.scripts_by_category:
                categories = category_cache.get_categories()
                for category in categories:
                    if category.get("is_script"):
                        continue
                    category_path = category.get("path", "")
                    if category_path:
                        add_scripts(
                            category_cache.get_scripts_for_category(category_path)
                        )
                return all_scripts

            # Compatibility fallback for callers that do not own a CategoryCache.
            categories = parser.get_categories(self.translations)
            for category in categories:
                if category.get("is_script"):
                    continue
                category_path = category.get("path", "")
                if not category_path:
                    continue
                try:
                    add_scripts(
                        parser.get_scripts_for_category(
                            category_path,
                            self.translations,
                        )
                    )
                except Exception:
                    continue

        except Exception as error:
            print(f"Error collecting all scripts: {error}")

        return all_scripts

    @staticmethod
    def _preferred_height(widget):
        """Return a widget's natural preferred height."""
        if widget is None:
            return 0

        try:
            _minimum, natural = widget.get_preferred_height()
            return natural
        except (AttributeError, TypeError):
            return widget.get_allocated_height()

    @staticmethod
    def _preferred_width(widget):
        """Return a widget's natural preferred width."""
        if widget is None:
            return 0

        try:
            _minimum, natural = widget.get_preferred_width()
            return natural
        except (AttributeError, TypeError):
            return widget.get_allocated_width()

    def _get_featured_card_size(self):
        """
        Measure a representative script card.

        Existing category cards are preferred because they are already realized.
        A featured card is created temporarily only when no existing card can be
        measured yet.
        """
        sample = None
        temporary_sample = False

        category_children = self.categories_flowbox.get_children()
        if category_children:
            sample = category_children[0].get_child()

        if sample is None and self.all_scripts:
            sample = self.create_item_widget(self.all_scripts[0])
            temporary_sample = True

        card_width = self._preferred_width(sample)
        card_height = self._preferred_height(sample)

        if temporary_sample:
            sample.destroy()

        # Safe fallbacks for the first allocation cycle.
        return max(1, card_width or 120), max(1, card_height or 64)

    def _calculate_featured_columns(self):
        """Mirror the main menu's *actual* currently allocated column count."""
        category_children = self.categories_flowbox.get_children()
        columns = 0

        # FlowBox does not expose its current effective column count directly.
        # Once allocated, however, every child in the same row has the same Y
        # coordinate. Count the fullest allocated row so this follows GTK's real
        # layout decision instead of trying to reproduce it from preferred widths.
        row_counts = {}
        for child in category_children:
            allocation = child.get_allocation()
            if allocation.width <= 1 or allocation.height <= 1:
                continue
            row_counts[allocation.y] = row_counts.get(allocation.y, 0) + 1

        if row_counts:
            columns = max(row_counts.values())

        # During the first allocation cycle there may not be usable child geometry
        # yet. Be conservative; the size-allocate callback will recalculate this as
        # soon as GTK has laid out the main menu. This avoids ever over-populating
        # the featured section during startup.
        if columns <= 0:
            columns = 1

        main_max_columns = self.categories_flowbox.get_max_children_per_line()
        if main_max_columns > 0:
            columns = min(columns, main_max_columns)

        columns = max(1, int(columns))

        return columns

    def _calculate_random_scripts_count(self):
        """Calculate Featured geometry and the number of actual app cards shown."""
        if (
            not self.all_scripts
            or self.current_category_info is not None
            or self.main_stack.get_visible_child_name() != "categories"
        ):
            self._featured_layout_metrics = None
            return 0

        viewport_height = self.categories_view.get_allocated_height()
        categories_height = self.categories_flowbox.get_allocated_height()

        if viewport_height <= 1 or categories_height <= 1:
            self._featured_layout_metrics = None
            return 0

        container = self.featured_scripts_container
        vertical_margins = (
            container.get_margin_top() + container.get_margin_bottom()
        )

        separator = None
        children = container.get_children()
        if children:
            separator = children[0]

        separator_height = self._preferred_height(separator)
        label_height = self._preferred_height(self.random_scripts_label)
        section_spacing = container.get_spacing() * 2
        fixed_featured_height = (
            vertical_margins
            + separator_height
            + label_height
            + section_spacing
        )
        available_rows_height = (
            viewport_height - categories_height - fixed_featured_height
        )

        _card_width, card_height = self._get_featured_card_size()
        row_spacing = self.random_scripts_flowbox.get_row_spacing()
        if available_rows_height < card_height:
            self._featured_layout_metrics = None
            return 0

        rows = 1 + (
            available_rows_height - card_height
        ) // (card_height + row_spacing)
        rows = min(self.FEATURED_MAX_ROWS, int(rows))
        columns = self._calculate_featured_columns()

        eligible_count = len(self._eligible_featured_scripts())
        if eligible_count <= 0:
            self._featured_layout_metrics = None
            return 0

        # One three-row card at 3-5 rows, two at 6-8, and three at 9+.
        # Once the maximum-height layout is available (9+ rows), scale the large
        # card allowance with width as well: keep the base three, then add one
        # more for every column beyond three (4 columns -> 4 large cards,
        # 5 columns -> 5 large cards, and so on).
        #
        # A large card occupies three normal grid cells, so every one reduces the
        # number of distinct apps that fit by two while preserving exactly the
        # same overall Featured height and column count.
        if rows >= 9:
            max_large_cards = max(3, columns)
        else:
            max_large_cards = min(3, rows // 3)

        large_count = min(max_large_cards, eligible_count)
        slot_count = rows * columns
        item_capacity = max(0, slot_count - (2 * large_count))
        item_count = min(eligible_count, item_capacity)
        large_count = min(large_count, item_count)

        # If a very small eligible pool forced large_count down, reclaim the slots
        # that no longer need to be reserved by a three-row card.
        item_capacity = max(0, slot_count - (2 * large_count))
        item_count = min(eligible_count, item_capacity)

        self._featured_layout_metrics = {
            "rows": rows,
            "columns": columns,
            "card_height": card_height,
            "row_spacing": row_spacing,
            "large_count": large_count,
            "item_count": item_count,
        }
        return item_count

    @staticmethod
    def _featured_script_key(script):
        """Return a stable identity for Featured history/exclusion checks."""
        return script.get("path") or (
            script.get("name", ""),
            script.get("repo", ""),
        )

    def _eligible_featured_scripts(self):
        """Return scripts that may currently appear in Featured."""
        return [
            script
            for script in self.all_scripts
            if not self._is_script_removable(script)
        ]

    @staticmethod
    def _featured_history_limit(count):
        """How many previous Featured sets must remain excluded."""
        if count < 10:
            return 3
        if count < 20:
            return 2
        return 1

    def _select_random_scripts(self, count):
        """Select a fresh Featured set while avoiding recently displayed cards."""
        if not self.all_scripts or count <= 0:
            return []

        eligible = self._eligible_featured_scripts()
        if not eligible:
            return []

        count = min(count, len(eligible))
        history = list(getattr(self, "_featured_history", ()))
        history_limit = self._featured_history_limit(count)
        history = history[-history_limit:]

        # Prefer excluding every retained set. If that would leave too few cards to
        # fill the current layout, forget the oldest set(s) one at a time. This keeps
        # the strongest possible no-repeat window without shrinking Featured.
        while True:
            excluded = set().union(*history) if history else set()
            candidates = [
                script
                for script in eligible
                if self._featured_script_key(script) not in excluded
            ]
            if len(candidates) >= count or not history:
                break
            history.pop(0)

        self._featured_history = history
        return random.sample(candidates, min(count, len(candidates)))

    def _choose_featured_large_positions(self, rows, columns, count):
        """Pick non-overlapping three-row spans, avoiding last positions if possible."""
        if count <= 0 or rows < 3 or columns <= 0:
            self._featured_large_positions = set()
            return []

        previous = set(getattr(self, "_featured_large_positions", set()))
        all_positions = [
            (column, row)
            for column in range(columns)
            for row in range(rows - 2)
        ]

        def find_layout(candidates):
            candidates = list(candidates)
            random.shuffle(candidates)

            def overlaps(position, chosen):
                column, row = position
                for other_column, other_row in chosen:
                    if column != other_column:
                        continue
                    if not (row + 2 < other_row or other_row + 2 < row):
                        return True
                return False

            def search(index, chosen):
                if len(chosen) == count:
                    return list(chosen)
                if len(candidates) - index < count - len(chosen):
                    return None
                for candidate_index in range(index, len(candidates)):
                    candidate = candidates[candidate_index]
                    if overlaps(candidate, chosen):
                        continue
                    result = search(candidate_index + 1, chosen + [candidate])
                    if result is not None:
                        return result
                return None

            return search(0, [])

        # Strong preference: none of the large cards uses the exact same top-left
        # slot as the previous rotation. If current geometry makes that impossible
        # (for example one column with exactly six rows and two large cards), fall
        # back to the best valid non-overlapping layout instead of dropping cards.
        fresh_positions = [pos for pos in all_positions if pos not in previous]
        chosen = find_layout(fresh_positions) or find_layout(all_positions) or []
        self._featured_large_positions = set(chosen)
        return chosen

    @staticmethod
    def _featured_occupied_cells(position):
        column, row = position
        return {(column, row + offset) for offset in range(3)}

    def _clear_random_scripts(self):
        """Remove every currently displayed featured card."""
        for child in self.random_scripts_flowbox.get_children():
            child.destroy()

    def _hide_featured_section(self, discard=False):
        """Hide Featured Scripts without losing its current state by default."""
        if getattr(self, "_featured_swap_timer", None):
            GLib.source_remove(self._featured_swap_timer)
            self._featured_swap_timer = None

        self.random_scripts_revealer.set_reveal_child(False)
        self.featured_scripts_revealer.set_reveal_child(False)

        if discard:
            self._clear_random_scripts()
            self._featured_last_count = 0
            self._featured_last_layout = None
            self._featured_history = []
            self._featured_large_positions = set()

    def _invalidate_featured_scripts(self):
        """Discard Featured state when its backing script data becomes stale."""
        self._stop_random_scripts_refresh_timer()
        self._hide_featured_section(discard=True)

    def _populate_random_scripts(self, scripts, count, layout):
        """Replace hidden Featured cards, including true three-row variants."""
        self._featured_swap_timer = None
        self._featured_swap_required_by_layout = False

        on_categories_view = (
            self.current_category_info is None
            and self.main_stack.get_visible_child_name() == "categories"
        )
        if not self.all_scripts or not on_categories_view or count <= 0:
            return False

        rows = int(layout.get("rows", 0))
        columns = int(layout.get("columns", 0))
        large_count = min(int(layout.get("large_count", 0)), len(scripts))
        card_height = int(layout.get("card_height", 52))
        row_spacing = int(layout.get("row_spacing", 12))
        if rows <= 0 or columns <= 0:
            return False

        self._clear_random_scripts()

        large_positions = self._choose_featured_large_positions(
            rows, columns, large_count
        )
        large_count = min(large_count, len(large_positions))

        # Choose which apps get the richer presentation independently from where
        # those cards land. This keeps both the content and placement randomized.
        shuffled_scripts = list(scripts)
        random.shuffle(shuffled_scripts)
        large_scripts = shuffled_scripts[:large_count]
        normal_scripts = shuffled_scripts[large_count:]
        random.shuffle(large_positions)

        occupied = set()
        large_height = (3 * card_height) + (2 * row_spacing)

        def prepare_widget(script_info, *, large=False):
            widget = self.create_item_widget(
                script_info,
                featured_large=large,
                featured_height=large_height if large else 0,
            )
            description = script_info.get("description", "")
            widget.set_tooltip_text(description or None)
            widget.set_can_focus(True)
            widget.connect("key-press-event", self._on_featured_card_key_press)
            widget.add_events(
                Gdk.EventMask.ENTER_NOTIFY_MASK
                | Gdk.EventMask.LEAVE_NOTIFY_MASK
            )
            widget.connect("enter-notify-event", self._on_featured_card_enter)
            widget.connect("leave-notify-event", self._on_featured_card_leave)
            return widget

        for script_info, position in zip(large_scripts, large_positions):
            column, row = position
            occupied.update(self._featured_occupied_cells(position))
            widget = prepare_widget(script_info, large=True)
            self.random_scripts_flowbox.attach(widget, column, row, 1, 3)

        free_cells = [
            (column, row)
            for row in range(rows)
            for column in range(columns)
            if (column, row) not in occupied
        ]
        for script_info, (column, row) in zip(normal_scripts, free_cells):
            widget = prepare_widget(script_info, large=False)
            self.random_scripts_flowbox.attach(widget, column, row, 1, 1)

        self._featured_last_count = count
        self._featured_last_layout = (
            rows, columns, large_count, count
        )

        displayed_keys = {
            self._featured_script_key(script_info)
            for script_info in scripts
        }
        history_limit = self._featured_history_limit(count)
        history = list(getattr(self, "_featured_history", ()))
        history.append(displayed_keys)
        self._featured_history = history[-history_limit:]

        self.featured_scripts_revealer.show_all()
        self.featured_scripts_revealer.set_reveal_child(True)
        self.random_scripts_revealer.set_reveal_child(True)
        return False

    def _refresh_random_scripts_display(self, force=False):
        """
        Recalculate and refresh the featured section.

        The first set reveals the whole section. Later replacements fade the cards
        out, swap them while hidden, then fade the replacement set in.
        """
        on_categories_view = (
            self.current_category_info is None
            and self.main_stack.get_visible_child_name() == "categories"
        )

        if not self.all_scripts or not on_categories_view:
            # Navigation is not an invalidation event. A queued timer/resize callback
            # can arrive just after the stack changes, so simply stop here and keep
            # the existing cards intact for the next visit to the main menu.
            return False

        count = self._calculate_random_scripts_count()

        if count <= 0:
            # Temporarily hide when no complete row fits, but retain the chosen cards.
            self._hide_featured_section(discard=False)
            return True

        current_children = self.random_scripts_flowbox.get_children()
        layout = dict(getattr(self, "_featured_layout_metrics", {}) or {})
        layout_signature = (
            int(layout.get("rows", 0)),
            int(layout.get("columns", 0)),
            int(layout.get("large_count", 0)),
            count,
        )
        layout_changed = (
            layout_signature != getattr(self, "_featured_last_layout", None)
        )

        if (
            not force
            and not layout_changed
            and current_children
        ):
            self.featured_scripts_revealer.show_all()
            self.featured_scripts_revealer.set_reveal_child(True)
            self.random_scripts_revealer.set_reveal_child(True)
            return True

        scripts = self._select_random_scripts(count)

        if getattr(self, "_featured_swap_timer", None):
            GLib.source_remove(self._featured_swap_timer)
            self._featured_swap_timer = None

        if current_children:
            # Hover is allowed to cancel a cosmetic timed rotation, but a resize
            # that changes the grid geometry must complete. Window maximization can
            # synthesize pointer enter events while GTK reallocates the cards.
            self._featured_swap_required_by_layout = layout_changed
            self.random_scripts_revealer.set_reveal_child(False)
            self._featured_swap_timer = GLib.timeout_add(
                self.FEATURED_SWAP_ANIMATION_MS,
                self._populate_random_scripts,
                scripts,
                count,
                layout,
            )
        else:
            self._featured_swap_required_by_layout = False
            self._populate_random_scripts(scripts, count, layout)

        return True

    def _on_featured_size_allocate(self, _widget, _allocation):
        """
        Debounce resize events and update the featured layout after allocation.

        Returning to the main menu deliberately waits for this signal instead of
        measuring geometry from an idle callback. Gtk.Stack transitions can leave
        the categories view reporting its previous allocation for a short time;
        using that stale size caused a wrong Featured set to flash before the real
        allocation arrived.
        """
        if self.main_stack.get_visible_child_name() != "categories":
            return

        if getattr(self, "_featured_resize_timer", None):
            GLib.source_remove(self._featured_resize_timer)

        self._featured_resize_timer = GLib.timeout_add(
            self.FEATURED_RESIZE_DEBOUNCE_MS,
            self._apply_featured_resize,
        )

    def _apply_featured_resize(self):
        """Apply the resize-triggered featured-section update using settled geometry."""
        self._featured_resize_timer = None

        if not (
            self.should_start_random_timer
            and self.all_scripts
            and self.main_stack.get_visible_child_name() == "categories"
        ):
            return False

        self._refresh_random_scripts_display(force=False)

        # A navigation return is complete only after a fresh allocation has been
        # observed. Start the periodic rotation from this settled state rather than
        # from the stale geometry that may still exist immediately after switching
        # Gtk.Stack children.
        if getattr(self, "_featured_waiting_for_allocation", False):
            self._featured_waiting_for_allocation = False
            self._restart_random_scripts_refresh_timer()

        return False

    def _on_featured_card_key_press(self, widget, event):
        """Keep keyboard activation available after moving Featured to Gtk.Grid."""
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            self._activate_item(widget, event)
            return True
        return False

    def _on_featured_card_enter(self, _widget, _event):
        """Pause Featured rotation while the pointer is over a card."""
        self._featured_hovered = True

        if self.random_scripts_refresh_timer:
            GLib.source_remove(self.random_scripts_refresh_timer)
            self.random_scripts_refresh_timer = None

        # If the periodic timeout fired just before the pointer entered, cancel
        # that cosmetic replacement and keep the cards the user is reading. A
        # resize-driven swap is different: it is required to make the cards match
        # the newly available rows/columns, and maximizing/restoring the window can
        # itself generate enter events during GTK reallocation. Never cancel those.
        if (
            getattr(self, "_featured_swap_timer", None)
            and not getattr(self, "_featured_swap_required_by_layout", False)
        ):
            GLib.source_remove(self._featured_swap_timer)
            self._featured_swap_timer = None
            self._featured_swap_required_by_layout = False
            self.random_scripts_revealer.set_reveal_child(True)

        return False

    def _on_featured_card_leave(self, _widget, _event):
        """Resume Featured rotation with a fresh interval after hover ends."""
        self._featured_hovered = False

        if (
            self.should_start_random_timer
            and self.all_scripts
            and self.current_category_info is None
            and self.main_stack.get_visible_child_name() == "categories"
            and not getattr(self, "_featured_waiting_for_allocation", False)
        ):
            self._restart_random_scripts_refresh_timer()

        return False

    def _get_featured_refresh_seconds(self):
        """Scale Featured rotation from 8s at <=10 cards to 15s at >=25 cards."""
        count = self._calculate_random_scripts_count()

        if count <= self.FEATURED_REFRESH_MIN_ITEMS:
            return self.FEATURED_REFRESH_MIN_SECONDS

        if count >= self.FEATURED_REFRESH_MAX_ITEMS:
            return self.FEATURED_REFRESH_MAX_SECONDS

        item_span = (
            self.FEATURED_REFRESH_MAX_ITEMS
            - self.FEATURED_REFRESH_MIN_ITEMS
        )
        time_span = (
            self.FEATURED_REFRESH_MAX_SECONDS
            - self.FEATURED_REFRESH_MIN_SECONDS
        )
        progress = (
            count - self.FEATURED_REFRESH_MIN_ITEMS
        ) / item_span

        return round(
            self.FEATURED_REFRESH_MIN_SECONDS
            + progress * time_span
        )

    def _periodic_random_scripts_refresh(self):
        """Rotate Featured once, then schedule the next dynamic interval."""
        self.random_scripts_refresh_timer = None
        self._refresh_random_scripts_display(force=True)

        if (
            self.should_start_random_timer
            and self.all_scripts
            and self.current_category_info is None
            and self.main_stack.get_visible_child_name() == "categories"
            and not getattr(self, "_featured_hovered", False)
            and not getattr(self, "_featured_waiting_for_allocation", False)
        ):
            self._restart_random_scripts_refresh_timer()

        # This timeout is intentionally one-shot. Recreating it after every
        # rotation lets the interval follow the current Featured item count.
        return False

    def _restart_random_scripts_refresh_timer(self):
        """Restart Featured rotation using the interval for the current card count."""
        if self.random_scripts_refresh_timer:
            GLib.source_remove(self.random_scripts_refresh_timer)
            self.random_scripts_refresh_timer = None

        # Hover owns the pause. The leave handler will start a completely fresh
        # interval, giving the user the full reading time after moving away.
        if getattr(self, "_featured_hovered", False):
            return

        refresh_seconds = self._get_featured_refresh_seconds()

        self.random_scripts_refresh_timer = GLib.timeout_add_seconds(
            refresh_seconds,
            self._periodic_random_scripts_refresh,
        )

    def _deferred_start_random_scripts_refresh_timer(self):
        """Populate Featured on initial startup once usable geometry exists."""
        if not self.featured_scripts_container or not self.all_scripts:
            return False

        if self.main_stack.get_visible_child_name() != "categories":
            return False

        # This path is for initial startup/data publication only. Navigation back to
        # the main menu is handled by _prepare_random_scripts_display(), which waits
        # for a fresh size-allocate signal before measuring anything.
        if getattr(self, "_featured_waiting_for_allocation", False):
            return False

        if (
            self.categories_view.get_allocated_height() <= 1
            or self.categories_flowbox.get_allocated_height() <= 1
        ):
            GLib.timeout_add(
                self.FEATURED_RESIZE_DEBOUNCE_MS,
                self._deferred_start_random_scripts_refresh_timer,
            )
            return False

        has_existing_cards = bool(self.random_scripts_flowbox.get_children())
        self._refresh_random_scripts_display(force=not has_existing_cards)
        self._restart_random_scripts_refresh_timer()
        return False

    def _prepare_random_scripts_display(self):
        """Resume Featured after navigation using the next real GTK allocation."""
        self.should_start_random_timer = True

        if not self.all_scripts:
            self.featured_scripts_revealer.set_reveal_child(False)
            return

        # Keep the previous cards alive, but do not reveal or recalculate them yet.
        # Gtk.Stack can briefly expose stale allocation values immediately after the
        # visible child changes. The next size-allocate callback is the first safe
        # point at which to calculate rows/columns for the returned main menu.
        self._featured_waiting_for_allocation = True
        self.random_scripts_revealer.set_reveal_child(False)
        self.featured_scripts_revealer.set_reveal_child(False)

        # Ensure GTK schedules a fresh allocation even when the window itself did
        # not change size while the category view was hidden in the stack.
        self.categories_view.queue_resize()
        self.categories_flowbox.queue_resize()

    def _stop_random_scripts_refresh_timer(self):
        """Stop featured-script refresh, resize and animation callbacks."""
        if self.random_scripts_refresh_timer:
            GLib.source_remove(self.random_scripts_refresh_timer)
            self.random_scripts_refresh_timer = None

        if getattr(self, "_featured_resize_timer", None):
            GLib.source_remove(self._featured_resize_timer)
            self._featured_resize_timer = None

        if getattr(self, "_featured_swap_timer", None):
            GLib.source_remove(self._featured_swap_timer)
            self._featured_swap_timer = None
        self._featured_swap_required_by_layout = False
