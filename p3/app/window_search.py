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
            
        if len(query) >= 2:
            self._perform_search(query)
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

    def _on_search_activate(self, search_entry):
        """Handle search entry activation (Enter key)."""
        # If there are search results, activate the first one
        if self.search_results:
            first_result = self.search_results[0]
            self._activate_search_result(first_result)

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

    def _perform_search(self, query):
        """Perform the actual search and display results."""
        self.search_results = self.search_engine.search(query)
        self._display_search_results()

    def _display_search_results(self):
        """Display search results in the search view, grouped by category."""
        self.search_active = True

        # Clear existing search results completely
        for child in self.search_flowbox.get_children():
            self.search_flowbox.remove(child)

        # Force switch to search view first to ensure we're in the right context
        self.main_stack.set_visible_child_name("search")

        # Ensure the back button is visible when in search mode
        self.back_button.show()

        self.reveal.set_reveal_child(False)

        # Disable drag-and-drop in search mode
        self._disable_drag_and_drop()

        # Create a container to hold all category groups
        results_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        results_container.set_margin_left(0)
        results_container.set_margin_right(0)
        results_container.set_margin_top(8)
        results_container.set_margin_bottom(4)

        # Add search results grouped by category
        for category_group in self.search_results:
            category_name = category_group.get('category_name', 'Other')
            scripts = category_group.get('scripts', [])
            show_header = category_group.get('show_header', True)
            
            if not scripts:
                continue
            
            # Add category header only if show_header is True
            if show_header:
                category_header = self._create_search_category_header(category_name)
                results_container.pack_start(category_header, False, False, 0)
            
            # Create a flowbox for this category's scripts
            category_flowbox = Gtk.FlowBox()
            category_flowbox.set_valign(Gtk.Align.START)
            # Dynamically calculate columns based on available width and script count
            columns = self._calculate_search_results_columns(len(scripts))
            category_flowbox.set_max_children_per_line(columns)
            category_flowbox.set_activate_on_single_click(False)
            category_flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
            category_flowbox.set_homogeneous(True)
            category_flowbox.set_margin_left(0)
            category_flowbox.set_margin_right(0)
            category_flowbox.set_margin_top(0)
            category_flowbox.set_margin_bottom(0)
            category_flowbox.set_column_spacing(16)
            category_flowbox.set_row_spacing(12)
            
            # Add scripts for this category
            for search_result in scripts:
                item_info = search_result.item_info
                widget = self.create_item_widget(item_info)
                description = item_info.get("description", "")
                if description:
                    widget.set_tooltip_text(description)
                else:
                    widget.set_tooltip_text(None)
                category_flowbox.add(widget)
            
            results_container.pack_start(category_flowbox, False, False, 0)

        # Add the container to the search flowbox
        self.search_flowbox.add(results_container)

        # Ensure all widgets are shown
        self.search_flowbox.show_all()

        # Update header for search view
        self._update_search_header()
    
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
            self._show_reboot_warning_dialog()
            return

        # Use VTE-based term_view for execution
        self.open_term_view([item_info], removable_script_info=item_info, auto_run=True)

    def _clear_search_results(self):
        """Clear search results and return to previous view."""
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