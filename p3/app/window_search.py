from .gtk_common import Gdk, Gtk, GLib
from .window_items import ItemWidgetFactory
from .lang_utils import escape_for_markup

class SearchCtl:
    def _create_search_ui(self):
        """Create the search UI components for the header bar."""
        # Create search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(
            self.translations.get("search_placeholder", "Search features")
        )
        self.search_entry.set_size_request(250, -1)  # Set minimum width
        self._search_timer_id = None
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_search_activate)
        self.search_entry.connect("key-press-event", self._on_search_key_press)

        # Pack the search entry directly to the left side of the header (after back button)
        self.header_bar.pack_start(self.search_entry)

    def _on_search_changed(self, search_entry):
        """Handle search text changes."""
        query = search_entry.get_text().strip()

        if self.main_stack.get_visible_child_name() == "skills_seeker":
            if hasattr(self, "scripts_view") and hasattr(self.scripts_view, "do_search"):
                if self._search_timer_id:
                    GLib.source_remove(self._search_timer_id)
                    self._search_timer_id = None
                if not query:
                    self.scripts_view.do_search(query)
                    if self.search_active:
                        self._clear_search_results()
                    return
                self._search_timer_id = GLib.timeout_add(
                    300, self._do_delayed_skills_search, search_entry
                )
                return
            
        # Normal searches can change on every keystroke. Rebuilding grouped GTK
        # results immediately for each character repeatedly cancels/restarts the
        # progressive population animation and makes typing feel like a monolithic
        # redraw. Debounce the regular search path just like Skills Seeker.
        if self._search_timer_id:
            GLib.source_remove(self._search_timer_id)
            self._search_timer_id = None

        if len(query) >= 2:
            self._search_timer_id = GLib.timeout_add(
                140, self._do_delayed_search, search_entry
            )
        elif len(query) == 0 and self.search_active:
            # If search is completely emptied, return to normal mode and remove focus
            self._clear_search_results()
            # Deselect the search entry (remove focus) using GLib.idle_add for deferred execution

            def remove_focus():
                # Try to focus on the current visible child or the main container
                current_child = self.main_stack.get_visible_child()
                if current_child:
                    current_child.grab_focus()
                else:
                    # Fallback: try to focus on the main window itself
                    self.grab_focus()
                return False  # Don't repeat this idle callback

            GLib.idle_add(remove_focus)
            # Also reset the header if we were in search mode
            if self.current_category_info:
                self._update_header(self.current_category_info)
                category_name = self.current_category_info.get("name", "Unknown")
                self.header_bar.props.title = f"LinuxToys: {category_name}"
            else:
                self._update_header()  # Reset to default header
                self.header_bar.props.title = "LinuxToys"

    def _do_delayed_skills_search(self, search_entry):
        self._search_timer_id = None
        query = search_entry.get_text().strip()
        if hasattr(self, "scripts_view") and hasattr(self.scripts_view, "do_search"):
            self.scripts_view.do_search(query)
        return False

    def _do_delayed_search(self, search_entry):
        """Run a normal search once typing has briefly settled."""
        self._search_timer_id = None
        query = search_entry.get_text().strip()
        if len(query) >= 2:
            self._perform_search(query)
        return False

    def _on_search_activate(self, search_entry):
        query = search_entry.get_text().strip()
        if self._try_smart_search_navigation(query):
            return

    # Search results are grouped by category, so find the first
    # actual SearchResult object from the first non-empty group.
        for category_group in self.search_results:
            scripts = category_group.get("scripts", [])
            if scripts:
                self._activate_search_result(scripts[0])
                return

    def _on_search_key_press(self, widget, event):
        """Handle key presses in search entry."""
        if event.keyval == Gdk.KEY_Escape:
            # Clear search on Escape
            widget.set_text("")
            # Deselect the search entry (remove focus) using GLib.idle_add for deferred execution

            def remove_focus():
                # Try to focus on the current visible child or the main container
                current_child = self.main_stack.get_visible_child()
                if current_child:
                    current_child.grab_focus()
                else:
                    # Fallback: try to focus on the main window itself
                    self.grab_focus()
                return False  # Don't repeat this idle callback

            GLib.idle_add(remove_focus)
            if self.search_active:
                self._clear_search_results()
                # Reset header appropriately
                if self.current_category_info:
                    self._update_header(self.current_category_info)
                    category_name = self.current_category_info.get("name", "Unknown")
                    self.header_bar.props.title = f"LinuxToys: {category_name}"
                else:
                    self._update_header()  # Reset to default header
                    self.header_bar.props.title = "LinuxToys"
            return True
        return False

    def _calculate_search_results_columns(self, num_scripts):
        """
        Calculate the optimal number of columns for search results based on available width and script count.
        
        Args:
            num_scripts: Number of scripts to display
            
        Returns:
            int: Number of columns (1-5)
        """
        # Get available width from the search view scrolled window
        if not self.search_view:
            return 2
        
        available_width = self.search_view.get_allocated_width()
        if available_width <= 1:  # Not yet allocated
            return 2
        
        # Item width is 128px + column spacing is 16px = 144px per column
        # Also account for flowbox margins (32px left + 32px right)
        item_with_spacing_width = 128 + 16
        flowbox_margins = 32 + 32
        usable_width = available_width - flowbox_margins
        
        # Calculate how many columns can fit
        columns_by_width = max(1, usable_width // item_with_spacing_width)
        
        # Calculate how many columns we actually need based on scripts
        # Aim for roughly square layouts: don't waste rows
        columns_by_count = min(num_scripts, 5)  # Cap at 5 columns max
        
        # Use the minimum of available width and needed columns, but at least 1
        result = min(columns_by_width, columns_by_count)
        
        # Cap at 5 columns maximum and ensure at least 1
        return max(1, min(5, result))

    def _smart_search_categories(self):
        """Yield every parser-backed category currently available to the UI."""
        seen = set()

        for category in self.category_cache.get_categories():
            path = category.get("path", "")
            if path and path not in seen:
                seen.add(path)
                yield category

        for items in self.category_cache.scripts_by_category.values():
            for item in items:
                if not item.get("is_subcategory"):
                    continue
                path = item.get("path", "")
                if path and path not in seen:
                    seen.add(path)
                    yield item

    def _try_smart_search_navigation(self, query):
        """Open an exact localized category or special utility search target."""
        normalized = query.strip().casefold()
        if not normalized:
            return False

        queue_alias = self.translations.get("search_queue_alias", "queue").strip().casefold()
        installed_alias = self.translations.get(
            "search_installed_alias", "installed"
        ).strip().casefold()

        if normalized == queue_alias:
            self.search_entry.set_text("")
            self._open_appstream_queue()
            return True

        if normalized == installed_alias:
            self.search_entry.set_text("")
            self._open_installed_features()
            return True

        if not self.category_cache.is_populated:
            return False

        for category in self._smart_search_categories():
            pretty_name = str(category.get("name", "") or "").strip()
            if pretty_name and normalized == pretty_name.casefold():
                # Smart category navigation is absolute rather than relative to the
                # current browse/search history. Start at root, then reuse the normal
                # category-click path so view creation and deferred card loading stay
                # identical to a mouse click.
                self.search_entry.set_text("")
                self.show_categories_view()

                class _CategoryTarget:
                    pass

                target = _CategoryTarget()
                target.info = category
                self.on_category_clicked(target, None)
                return True

        return False

    def _perform_search(self, query):
        """Perform smart navigation or display the regular search results."""
        if self._try_smart_search_navigation(query):
            return
        self.search_results = self.search_engine.search(query)
        self._display_search_results()

    def _get_selected_search_result_children(self):
        """Return selected children from the nested search-result FlowBoxes."""
        return [
            child
            for flowbox in self._search_result_flowboxes
            for child in flowbox.get_selected_children()
        ]

    def _clear_search_result_selections(self):
        """Clear selected search results and report whether anything changed."""
        selected_children = self._get_selected_search_result_children()
        for flowbox in self._search_result_flowboxes:
            flowbox.unselect_all()
        return bool(selected_children)

    def _on_search_result_selection_changed(self, selected_flowbox):
        """Ensure only the active category group keeps a visible selection."""
        if not selected_flowbox.get_selected_children():
            return

        for flowbox in self._search_result_flowboxes:
            if flowbox is not selected_flowbox:
                flowbox.unselect_all()

    def _display_search_results(self):
        """Display search results incrementally, grouped by category."""
        self.search_active = True
        self._search_result_flowboxes = []

        # Each query invalidates population work from the previous result set.
        generation = getattr(self, "_search_population_generation", 0) + 1
        self._search_population_generation = generation

        # Clear existing search results completely.
        for child in self.search_flowbox.get_children():
            self.search_flowbox.remove(child)

        # Only the first entry into the search page has a Gtk.Stack transition.
        # Starting the population timer during that transition hides most or all
        # of the gradient because cards are created behind the sliding page.
        entering_search = self.main_stack.get_visible_child_name() != "search"
        self.main_stack.set_visible_child_name("search")
        self.back_button.show()
        self.reveal.set_reveal_child(False)
        self._disable_drag_and_drop()
        self._update_search_header()

        def begin_population():
            # The query may have changed while waiting for the stack transition.
            if getattr(self, "_search_population_generation", None) != generation:
                return False

            results_container = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=0,
            )
            results_container.set_margin_left(0)
            results_container.set_margin_right(0)
            results_container.set_margin_top(8)
            results_container.set_margin_bottom(4)

            # Search result sets are commonly <= 10 items. Keeping the old initial
            # batch of 10 therefore bypassed progressive rendering for most queries.
            # Start with one frame-sized batch so even small searches visibly flow in.
            initial_batch_size = 2
            frame_batch_size = 2
            initial_widgets = []

            # Flatten the grouped search result model into one ordered population
            # stream. Category UI is created only when the first result belonging to
            # that group reaches the stream.
            population_queue = []
            for category_group in self.search_results:
                for search_result in category_group.get("scripts", []):
                    population_queue.append((category_group, search_result))

            group_flowboxes = {}

            def ensure_group(category_group):
                group_key = id(category_group)
                existing = group_flowboxes.get(group_key)
                if existing is not None:
                    return existing

                category_name = category_group.get("category_name", "Other")
                scripts = category_group.get("scripts", [])
                show_header = category_group.get("show_header", True)

                if show_header:
                    category_header = self._create_search_category_header(category_name)
                    results_container.pack_start(category_header, False, False, 0)
                    category_header.show()

                category_flowbox = Gtk.FlowBox()
                category_flowbox.set_valign(Gtk.Align.START)
                columns = self._calculate_search_results_columns(len(scripts))
                category_flowbox.set_max_children_per_line(columns)
                category_flowbox.set_activate_on_single_click(False)
                category_flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
                category_flowbox.connect("key-press-event", self._on_flowbox_key_press)
                category_flowbox.connect(
                    "selected-children-changed",
                    self._on_search_result_selection_changed,
                )
                category_flowbox.set_homogeneous(True)
                category_flowbox.set_margin_left(32)
                category_flowbox.set_margin_right(32)
                category_flowbox.set_margin_top(8)
                category_flowbox.set_margin_bottom(4)
                category_flowbox.set_column_spacing(16)
                category_flowbox.set_row_spacing(12)

                self._search_result_flowboxes.append(category_flowbox)
                results_container.pack_start(category_flowbox, False, False, 0)
                category_flowbox.show()
                group_flowboxes[group_key] = category_flowbox
                return category_flowbox

            def add_result_card(category_group, search_result, *, show_now=False):
                flowbox = ensure_group(category_group)
                item_info = search_result.item_info
                widget = self.create_item_widget(item_info)
                widget.set_tooltip_text(item_info.get("description", "") or None)

                # Hide before insertion/showing so no fully-opaque frame can leak
                # through before the shared fade scheduler handles the card.
                widget.set_opacity(0.0)
                flowbox.add(widget)
                if show_now:
                    widget.show_all()
                return widget

            initial_count = min(initial_batch_size, len(population_queue))
            for category_group, search_result in population_queue[:initial_count]:
                initial_widgets.append(
                    add_result_card(category_group, search_result)
                )

            self.search_flowbox.add(results_container)
            self.search_flowbox.show_all()
            self.animate_item_batch(
                initial_widgets,
                duration_ms=120,
                stagger_ms=8,
                delay_ms=16,
            )

            if initial_count >= len(population_queue):
                return False

            next_index = initial_count
            frame_interval_ms = 16

            def populate_search_batch():
                nonlocal next_index

                if getattr(self, "_search_population_generation", None) != generation:
                    return False

                end_index = min(
                    next_index + frame_batch_size,
                    len(population_queue),
                )
                batch_widgets = []
                for category_group, search_result in population_queue[
                    next_index:end_index
                ]:
                    batch_widgets.append(
                        add_result_card(
                            category_group,
                            search_result,
                            show_now=True,
                        )
                    )

                next_index = end_index
                self.animate_item_batch(
                    batch_widgets,
                    duration_ms=110,
                    stagger_ms=5,
                )
                return next_index < len(population_queue)

            GLib.timeout_add(
                frame_interval_ms,
                populate_search_batch,
                priority=GLib.PRIORITY_LOW,
            )
            return False

        if entering_search:
            transition_delay = max(
                1,
                int(self.main_stack.get_transition_duration()),
            )
            GLib.timeout_add(
                transition_delay,
                begin_population,
                priority=GLib.PRIORITY_LOW,
            )
        else:
            # Already on the search page: there is no stack transition to wait for.
            # Build the first tiny batch now, then continue frame-paced.
            begin_population()

    def _create_search_category_header(self, category_name):
        """
        Create a category header widget for search results.
        Styled consistently with the featured scripts section headers.
        
        Args:
            category_name: Name of the category
            
        Returns:
            A Gtk.Label widget styled as a category header
        """
        header = Gtk.Label()
        # Escape category name to handle & and other special characters in markup
        escaped_name = escape_for_markup(category_name)
        header.set_markup(f"<big><b>{escaped_name}</b></big>")
        header.set_halign(Gtk.Align.START)
        header.set_margin_top(12)
        header.set_margin_bottom(6)
        header.set_margin_start(32)  # Container handles horizontal margins
        header.set_margin_end(0)
        
        # Apply consistent styling with the rest of the app
        label_style = header.get_style_context()
        label_style.add_class("title-2")  # Use same CSS class as featured scripts
        
        return header

    def _activate_search_result(self, search_result):
        """Activate a specific search result (simulate click)."""
        # This would be called when Enter is pressed or result is directly activated
        item_info = search_result.item_info

        # Check if this is the "Create New Script" option
        if item_info.get("is_create_script"):
            self._handle_create_new_script()
            return

        # Handle regular scripts
        if self.reboot_required:
            if not self._show_reboot_warning_dialog():
                return

        # Use VTE-based term_view for execution
        self.open_term_view([item_info], removable_script_info=item_info, auto_run=True)

    def _clear_search_results(self):
        """Clear search results and return to previous view."""
        # Cancel any low-priority card population still targeting the previous
        # result set before its FlowBoxes are detached.
        self._search_population_generation = (
            getattr(self, "_search_population_generation", 0) + 1
        )
        self.search_active = False
        self.search_results = []

        # Return to appropriate view
        if self.current_category_info:
            self.main_stack.set_visible_child(self.scripts_view)
            # Ensure back button is visible for category views
            self.back_button.show()

            if self.current_category_info.get("display_mode", "menu") == "checklist":
                self.reveal.set_reveal_child(len(self.check_buttons) >= 2)

            # Restore drag-and-drop state based on current category
            if self._is_local_scripts_category(self.current_category_info):
                self._enable_drag_and_drop()
            else:
                self._disable_drag_and_drop()
        else:
            self.main_stack.set_visible_child_name("categories")
            # Hide back button for main categories view
            self.back_button.hide()
            # Disable drag-and-drop for main categories
            self._disable_drag_and_drop()
            # Restore footer state for main menu
            self.reveal.set_reveal_child(True)
            self.reveal.button_box.hide()
            self.reveal.support.show_all()

    def _update_search_header(self):
        """Update header for search results view."""
        search_query = self.search_entry.get_text().strip()
        results_count = len(self.search_results)

        # Create search results info for header
        search_info = {
            "name": f'{self.translations.get("search_results", "Search Results")}: "{search_query}"',
            "description": f"{results_count} {self.translations.get('results_found', 'results found')}",
            "icon": "system-search-symbolic",
        }

        self._update_header(search_info)
        self.header_bar.props.title = (
            f"LinuxToys: {self.translations.get('search', 'Search')}"
        )
        self.back_button.show()