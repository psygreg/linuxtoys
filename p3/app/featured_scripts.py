import random

from .gtk_common import GLib
from . import parser


class FeaturedCtl:
    FEATURED_REFRESH_SECONDS = 15
    FEATURED_MAX_ROWS = 10
    FEATURED_MAX_COLUMNS = 15
    FEATURED_RESIZE_DEBOUNCE_MS = 150

    def _collect_all_scripts(self):
        """Collect all scripts from all categories into a flat list."""
        all_scripts = []

        try:
            categories = parser.get_categories(self.translations)

            for category in categories:
                category_path = category.get("path", "")
                if not category_path:
                    continue

                try:
                    scripts = parser.get_scripts_for_category(
                        category_path,
                        self.translations,
                    )

                    for script in scripts:
                        if (
                            script.get("is_script", False)
                            and not script.get("is_create_script", False)
                        ):
                            all_scripts.append(script)
                except Exception:
                    # A broken category should not prevent featured scripts
                    # from being collected from the remaining categories.
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
        """Calculate how many cards fit horizontally, up to the FlowBox limit."""
        flowbox_width = self.random_scripts_flowbox.get_allocated_width()

        if flowbox_width <= 1:
            viewport_width = self.categories_view.get_allocated_width()
            horizontal_margins = (
                self.featured_scripts_container.get_margin_left()
                + self.featured_scripts_container.get_margin_right()
            )
            flowbox_width = max(0, viewport_width - horizontal_margins)

        card_width, _card_height = self._get_featured_card_size()
        column_spacing = self.random_scripts_flowbox.get_column_spacing()

        # n cards require:
        # n * card_width + (n - 1) * spacing
        columns = (flowbox_width + column_spacing) // (
            card_width + column_spacing
        )

        return max(
            1,
            min(self.FEATURED_MAX_COLUMNS, int(columns)),
        )

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
            len(self.all_scripts),
        )

    def _select_random_scripts(self, count):
        """Randomly select exactly the requested number of scripts."""
        if not self.all_scripts or count <= 0:
            return []

        return random.sample(
            self.all_scripts,
            min(count, len(self.all_scripts)),
        )

    def _clear_random_scripts(self):
        """Remove every currently displayed featured card."""
        for child in self.random_scripts_flowbox.get_children():
            child.destroy()

    def _refresh_random_scripts_display(self, force=False):
        """
        Recalculate and refresh the featured section.

        Returns True while the periodic timer should continue running.
        """
        on_categories_view = (
            self.current_category_info is None
            and self.main_stack.get_visible_child_name() == "categories"
        )

        if not self.all_scripts or not on_categories_view:
            self._clear_random_scripts()
            self.featured_scripts_container.hide()
            self._featured_last_count = 0
            return False

        count = self._calculate_random_scripts_count()

        if count <= 0:
            self._clear_random_scripts()
            self.featured_scripts_container.hide()
            self._featured_last_count = 0
            return True

        # A resize that does not change the number of fitting cards should not
        # randomly replace all cards. The periodic timer can still refresh them.
        if (
            not force
            and count == getattr(self, "_featured_last_count", None)
            and self.random_scripts_flowbox.get_children()
        ):
            self.featured_scripts_container.show_all()
            return True

        self._clear_random_scripts()

        for script_info in self._select_random_scripts(count):
            widget = self.create_item_widget(script_info)
            description = script_info.get("description", "")
            widget.set_tooltip_text(description or None)
            self.random_scripts_flowbox.add(widget)

        self._featured_last_count = count
        self.featured_scripts_container.show_all()

        return True

    def _on_featured_size_allocate(self, _widget, _allocation):
        """
        Debounce resize events and update the featured layout after allocation.
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
        """Apply the resize-triggered featured-section update."""
        self._featured_resize_timer = None

        if (
            self.should_start_random_timer
            and self.all_scripts
            and self.main_stack.get_visible_child_name() == "categories"
        ):
            self._refresh_random_scripts_display(force=False)

        return False

    def _periodic_random_scripts_refresh(self):
        """Periodic callback that deliberately selects a new random set."""
        return self._refresh_random_scripts_display(force=True)

    def _deferred_start_random_scripts_refresh_timer(self):
        """Start or restart the featured scripts timer."""
        if not self.featured_scripts_container or not self.all_scripts:
            return False

        if self.main_stack.get_visible_child_name() != "categories":
            return False

        # Wait until GTK has allocated the category viewport before measuring it.
        if (
            self.categories_view.get_allocated_height() <= 1
            or self.categories_flowbox.get_allocated_height() <= 1
        ):
            GLib.timeout_add(
                self.FEATURED_RESIZE_DEBOUNCE_MS,
                self._deferred_start_random_scripts_refresh_timer,
            )
            return False

        self._refresh_random_scripts_display(force=True)

        if self.random_scripts_refresh_timer:
            GLib.source_remove(self.random_scripts_refresh_timer)

        self.random_scripts_refresh_timer = GLib.timeout_add_seconds(
            self.FEATURED_REFRESH_SECONDS,
            self._periodic_random_scripts_refresh,
        )

        return False

    def _prepare_random_scripts_display(self):
        """Prepare featured scripts when returning to the main menu."""
        self.should_start_random_timer = True

        if self.all_scripts:
            GLib.idle_add(
                self._deferred_start_random_scripts_refresh_timer
            )
        else:
            self.featured_scripts_container.hide()

    def _stop_random_scripts_refresh_timer(self):
        """Stop featured-script refresh and resize callbacks."""
        if self.random_scripts_refresh_timer:
            GLib.source_remove(self.random_scripts_refresh_timer)
            self.random_scripts_refresh_timer = None

        if getattr(self, "_featured_resize_timer", None):
            GLib.source_remove(self._featured_resize_timer)
            self._featured_resize_timer = None