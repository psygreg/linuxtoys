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

        # Make the featured FlowBox use exactly the same number of columns. Using
        # both min and max prevents shorter featured labels from creating an extra
        # column that the main menu itself does not currently have.
        self.random_scripts_flowbox.set_min_children_per_line(columns)
        self.random_scripts_flowbox.set_max_children_per_line(columns)
        return columns

    def _calculate_random_scripts_count(self):
        """
        Calculate how many featured scripts fit in the unused viewport space.

        Zero means the complete featured section cannot fit and must stay hidden.
        Only complete rows are displayed.
        """
        if (
            not self.all_scripts
            or self.current_category_info is not None
            or self.main_stack.get_visible_child_name() != "categories"
        ):
            return 0

        viewport_height = self.categories_view.get_allocated_height()
        categories_height = self.categories_flowbox.get_allocated_height()

        if viewport_height <= 1 or categories_height <= 1:
            # GTK has not completed its first meaningful allocation yet.
            return 0

        container = self.featured_scripts_container

        vertical_margins = (
            container.get_margin_top()
            + container.get_margin_bottom()
        )

        separator = None
        children = container.get_children()
        if children:
            separator = children[0]

        separator_height = self._preferred_height(separator)
        label_height = self._preferred_height(self.random_scripts_label)

        # The featured container contains separator, label and FlowBox:
        # therefore there are two spacing gaps.
        section_spacing = container.get_spacing() * 2

        fixed_featured_height = (
            vertical_margins
            + separator_height
            + label_height
            + section_spacing
        )

        available_rows_height = (
            viewport_height
            - categories_height
            - fixed_featured_height
        )

        _card_width, card_height = self._get_featured_card_size()
        row_spacing = self.random_scripts_flowbox.get_row_spacing()

        if available_rows_height < card_height:
            return 0

        # The first row needs only card_height. Each additional row also needs
        # one row-spacing gap.
        rows = 1 + (
            available_rows_height - card_height
        ) // (card_height + row_spacing)

        rows = min(self.FEATURED_MAX_ROWS, int(rows))
        columns = self._calculate_featured_columns()

        return min(
            rows * columns,
            len(self._eligible_featured_scripts()),
        )

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
            self._featured_history = []

    def _invalidate_featured_scripts(self):
        """Discard Featured state when its backing script data becomes stale."""
        self._stop_random_scripts_refresh_timer()
        self._hide_featured_section(discard=True)

    def _populate_random_scripts(self, scripts, count):
        """Replace hidden featured cards, then animate the new set in."""
        self._featured_swap_timer = None

        on_categories_view = (
            self.current_category_info is None
            and self.main_stack.get_visible_child_name() == "categories"
        )
        if not self.all_scripts or not on_categories_view or count <= 0:
            # A delayed swap may fire after navigation. Do not destroy the cards;
            # the main-menu state must survive while its stack page is hidden.
            return False

        self._clear_random_scripts()

        for script_info in scripts:
            widget = self.create_item_widget(script_info)
            description = script_info.get("description", "")
            widget.set_tooltip_text(description or None)

            # Keep a Featured card stable while the user is hovering it, so its
            # tooltip/short description cannot disappear during the periodic swap.
            widget.add_events(
                Gdk.EventMask.ENTER_NOTIFY_MASK
                | Gdk.EventMask.LEAVE_NOTIFY_MASK
            )
            widget.connect("enter-notify-event", self._on_featured_card_enter)
            widget.connect("leave-notify-event", self._on_featured_card_leave)

            self.random_scripts_flowbox.add(widget)

        self._featured_last_count = count

        displayed_keys = {
            self._featured_script_key(script_info)
            for script_info in scripts
        }
        history_limit = self._featured_history_limit(count)
        history = list(getattr(self, "_featured_history", ()))
        history.append(displayed_keys)
        self._featured_history = history[-history_limit:]

        # Realize the new cards while the revealer is still closed, then animate in.
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

        if (
            not force
            and count == getattr(self, "_featured_last_count", None)
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
            self.random_scripts_revealer.set_reveal_child(False)
            self._featured_swap_timer = GLib.timeout_add(
                self.FEATURED_SWAP_ANIMATION_MS,
                self._populate_random_scripts,
                scripts,
                count,
            )
        else:
            self._populate_random_scripts(scripts, count)

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

    def _on_featured_card_enter(self, _widget, _event):
        """Pause Featured rotation while the pointer is over a card."""
        self._featured_hovered = True

        if self.random_scripts_refresh_timer:
            GLib.source_remove(self.random_scripts_refresh_timer)
            self.random_scripts_refresh_timer = None

        # If the timeout fired just before the pointer entered, cancel the pending
        # post-fade replacement and keep the cards the user is currently reading.
        if getattr(self, "_featured_swap_timer", None):
            GLib.source_remove(self._featured_swap_timer)
            self._featured_swap_timer = None
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
