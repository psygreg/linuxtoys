from .gtk_common import Gtk, GLib
from .window_items import ItemWidgetFactory
from .window_search import SearchCtl
from .featured_scripts import FeaturedCtl
from .local_scripts import LocalScriptsCtl
from . import term_view, skills_view, get_icon_path, header

class NavCtl:
    def on_category_clicked(self, widget, event):
        """Handles category click, subcategory click, or root script click."""
        # Check if reboot is required before proceeding
        if self.reboot_required:
            self._show_reboot_warning_dialog()
            return

        info = widget.info

        # Check if this is the "Create New Script" option
        if info.get("is_create_script"):
            self._handle_create_new_script()
            return

        # If this is a root script (shown as a category), execute it directly
        if info.get("is_script"):
            # Use VTE-based term_view for execution
            self.open_term_view([info], removable_script_info=info, auto_run=True)
        else:
            # This is a category or subcategory - navigate to show its contents
            # Create a new view for the subcategory to enable proper animation
            self.view_counter += 1
            new_view_name = f"scripts_{self.view_counter}"

            # Create new flowbox and scrolled window for this level
            new_flowbox = self.create_flowbox()
            new_scrolled_view = Gtk.ScrolledWindow()
            new_scrolled_view.add(new_flowbox)

            # Load content into the new view
            self._load_scripts_into_flowbox(new_flowbox, info)

            # Add the new view to the stack
            self.main_stack.add_named(new_scrolled_view, new_view_name)
            new_scrolled_view.show_all()

            # Set transition for forward navigation
            self.main_stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
            )

            # Update the scripts references
            self.scripts_flowbox = new_flowbox
            self.scripts_view = new_scrolled_view

            # Show the new view with animation
            self.show_scripts_view(info)

    def open_term_view(self, infos, removable_script_info=None, auto_run=True):
        # Check if any script has auto_run flag set in its info dict
        if not auto_run and infos:
            auto_run = any(script.get("auto_run", False) for script in infos)
        
        run_box = term_view.TermRunScripts(
            infos, self, self.translations, removable_script_info=removable_script_info, auto_run=auto_run
        )

        self.header_widget.hide()
        self.reveal.set_reveal_child(False)
        self.check_buttons.clear()
        self.back_button.show()

        child = self.main_stack.get_child_by_name("running_scripts")
        if child is not None:
            self.main_stack.remove(child)
            child.destroy()

        self.main_stack.add_named(run_box, "running_scripts")

        run_box.show_all()

        if self.current_category_info and not self.search_active:
            self.navigation_stack.append(self.current_category_info)

        self.main_stack.set_visible_child_name("running_scripts")
        return run_box

    def open_skills_seeker_view(self):
        self.search_entry.set_text("")
        self._search_entry_prev_placeholder = self.search_entry.get_placeholder_text()
        self.search_entry.set_placeholder_text(
            self.translations.get("skills_search_placeholder", "Search skills...")
        )
        self._clear_search_results()
        self.header_widget.hide()
        self.reveal.set_reveal_child(False)
        self.check_buttons.clear()
        self.back_button.show()

        prev = {
            "scripts_view": self.scripts_view,
            "scripts_flowbox": self.scripts_flowbox,
            "category_info": self.current_category_info,
        }
        self._skills_prev = prev

        skills_view_widget = skills_view.SkillsSeekerView(
            self.translations, on_install_callback=self._install_skill_from_seeker
        )

        child = self.main_stack.get_child_by_name("skills_seeker")
        if child is not None:
            self.main_stack.remove(child)
        self.main_stack.add_named(skills_view_widget, "skills_seeker")

        if self.current_category_info and not self.search_active:
            self.navigation_stack.append(self.current_category_info)

        self.scripts_view = skills_view_widget
        self.scripts_flowbox = skills_view_widget.get_flowbox()

        self.header_bar.props.title = self.translations.get(
            "notranslate", "LinuxToys: Skills Seeker"
        )

        icon_path = get_icon_path("skill.svg")
        self._set_window_icon_from_file(icon_path)

        skills_view_widget.show_all()
        self.header_widget.hide()
        self.main_stack.set_visible_child_name("skills_seeker")

    def on_back_button_clicked(self, widget):
        """Handles the back button click."""

        # Handle leaving the terminal before normal search navigation.
        if self.main_stack.get_visible_child_name() == "running_scripts":
            returning_to_search = self.search_active
            search_query = self.search_entry.get_text().strip()

            child = self.main_stack.get_child_by_name("running_scripts")
            if child is not None:
                self.main_stack.remove(child)
                child.destroy()

            # Installation/removal may have changed the action registry.
            self._refresh_removable_scripts()

            # When launched from search, rerun the same search so its cards
            # are recreated using the refreshed removable-state cache.
            if returning_to_search and search_query:
                self.search_results = self.search_engine.search(search_query)
                self._display_search_results()
                return

            if self.navigation_stack:
                previous_category = self.navigation_stack.pop()
                self.current_category_info = previous_category
                self.header_widget.show()
                self._update_header(previous_category)

                self.header_bar.props.title = (
                    f"LinuxToys: {previous_category.get('name', 'LinuxToys')}"
                )

                if self._is_local_scripts_category(previous_category):
                    self._enable_drag_and_drop()
                else:
                    self._disable_drag_and_drop()

                self._load_scripts_into_flowbox(
                    self.scripts_flowbox,
                    previous_category,
                )
                self.scripts_flowbox.show_all()

                if previous_category.get("display_mode", "menu") == "checklist":
                    self.reveal.set_reveal_child(len(self.check_buttons) >= 2)
                else:
                    self.reveal.set_reveal_child(False)

                self.main_stack.set_visible_child(self.scripts_view)
            else:
                self.load_categories()
                self.show_categories_view()

            return

        # This now applies only when Back is pressed directly from search results.
        if self.search_active:
            self.search_entry.set_text("")
            self._clear_search_results()
            return

        # Check if we're in skills seeker view
        if self.main_stack.get_visible_child_name() == "skills_seeker":
            if self._search_timer_id:
                GLib.source_remove(self._search_timer_id)
                self._search_timer_id = None
            prev = getattr(self, "_skills_prev", None)
            if prev:
                self.scripts_view = prev["scripts_view"]
                self.scripts_flowbox = prev["scripts_flowbox"]
                self.current_category_info = prev["category_info"]

            prev_placeholder = getattr(self, "_search_entry_prev_placeholder", None)
            if prev_placeholder:
                self.search_entry.set_placeholder_text(prev_placeholder)
                self._search_entry_prev_placeholder = None

            child = self.main_stack.get_child_by_name("skills_seeker")
            if child is not None:
                self.main_stack.remove(child)

            self.header_widget.show()
            self._update_header(self.current_category_info)
            if self.current_category_info:
                self.header_bar.props.title = (
                    f"LinuxToys: {self.current_category_info.get('name', 'LinuxToys')}"
                )
                self.main_stack.set_visible_child(self.scripts_view)
                self.back_button.show()
                if self._is_local_scripts_category(self.current_category_info):
                    self._enable_drag_and_drop()
                else:
                    self._disable_drag_and_drop()
                if self.current_category_info.get("display_mode", "menu") == "checklist":
                    self.reveal.set_reveal_child(len(self.check_buttons) >= 2)
                else:
                    self.reveal.set_reveal_child(False)
            else:
                self.show_categories_view()

            if self.navigation_stack:
                self.navigation_stack.pop()
            return

        # Check if a script is currently running
        if self._script_running:
            # Show warning dialog before cancelling the running script
            if not self._show_cancel_script_warning_dialog():
                return  # User cancelled the operation

        self.check_buttons.clear()

        if self.navigation_stack:
            # Store current view for cleanup
            current_view = self.scripts_view

            # Go back to the previous category/subcategory
            previous_category = self.navigation_stack.pop()
            self.current_category_info = previous_category

            # Create a new view for the previous category
            self.view_counter += 1
            new_view_name = f"scripts_{self.view_counter}"

            new_flowbox = self.create_flowbox()
            new_scrolled_view = Gtk.ScrolledWindow()
            new_scrolled_view.add(new_flowbox)

            # Load content into the new view
            self._load_scripts_into_flowbox(new_flowbox, previous_category)

            # Add the new view to the stack
            self.main_stack.add_named(new_scrolled_view, new_view_name)
            new_scrolled_view.show_all()

            # Set transition direction for going back
            self.main_stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
            )

            # Update references
            self.scripts_flowbox = new_flowbox
            self.scripts_view = new_scrolled_view

            # Switch to the new view
            self.main_stack.set_visible_child(new_scrolled_view)

            # Update UI
            category_name = previous_category.get("name", "Unknown")
            self.header_bar.props.title = f"LinuxToys: {category_name}"
            self._update_header(previous_category)

            # Update drag-and-drop state based on the category we're navigating to
            if self._is_local_scripts_category(previous_category):
                self._enable_drag_and_drop()
            else:
                self._disable_drag_and_drop()

            # Show footer only if checklist mode
            if previous_category.get("display_mode", "menu") == "checklist":
                self.reveal.set_reveal_child(len(self.check_buttons) >= 2)
            else:
                self.reveal.set_reveal_child(False)

            # Clean up the old view after transition
            def cleanup_old_view():
                try:
                    self.main_stack.remove(current_view)
                except Exception:
                    pass  # View may already be removed
                # Restore normal transition direction
                self.main_stack.set_transition_type(
                    Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
                )
                return False

            GLib.timeout_add(300, cleanup_old_view)

        else:
            # No more items in stack, go to main categories view
            current_view = self.scripts_view
            self.main_stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
            )
            self.show_categories_view()

            # Clean up the scripts view after transition
            def cleanup_scripts_view():
                try:
                    self.main_stack.remove(current_view)
                except Exception:
                    pass
                # Restore normal transition direction
                self.main_stack.set_transition_type(
                    Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
                )
                return False

            GLib.timeout_add(300, cleanup_scripts_view)

    def show_categories_view(self):
        """Switches to the main categories view."""
        self.current_category_info = None
        self.navigation_stack.clear()  # Clear navigation history
        self.main_stack.set_visible_child_name("categories")
        self.back_button.hide()
        self.header_bar.props.title = "LinuxToys"
        self._update_header()  # Reset to default header
        self.reveal.set_reveal_child(True)
        self.reveal.button_box.hide()
        self.reveal.support.show_all()

        # Disable drag-and-drop when viewing main categories
        self._disable_drag_and_drop()
        
        # Prepare random scripts display (deferred loading)
        self._prepare_random_scripts_display()

    def show_scripts_view(self, category_info):
        """Switches to the view showing scripts in a category."""
        # Stop random scripts timer when leaving main menu
        self.should_start_random_timer = False
        self._stop_random_scripts_refresh_timer()
        
        # If we have current category info, push it to navigation stack
        if self.current_category_info:
            self.navigation_stack.append(self.current_category_info)

        self.current_category_info = category_info

        # Switch to the current scripts view (which may be a new one created for subcategories)
        current_child = self.main_stack.get_visible_child()
        if current_child != self.scripts_view:
            self.main_stack.set_visible_child(self.scripts_view)

        self.back_button.show()

        # Get the category name for the title
        category_name = (
            category_info.get("name", "Unknown") if category_info else "Unknown"
        )
        self.header_bar.props.title = f"LinuxToys: {category_name}"

        # Update header with category information
        if category_info:
            self._update_header(category_info)

        # Enable drag-and-drop only for Local Scripts category
        if self._is_local_scripts_category(category_info):
            self._enable_drag_and_drop()
        else:
            self._disable_drag_and_drop()

        # Show footer only if checklist mode
        if category_info and category_info.get("display_mode", "menu") == "checklist":
            self.reveal.set_reveal_child(len(self.check_buttons) >= 2)
        else:
            self.reveal.set_reveal_child(False)
    
    def _update_header(self, category_info=None):
        """Updates the header with new category information."""
        # Remove the old header
        main_vbox = self.get_child()
        main_vbox.remove(self.header_widget)

        # Create new header with category info
        self.header_widget = header.create_header(self.translations, category_info)
        main_vbox.pack_start(self.header_widget, False, False, 8)
        main_vbox.reorder_child(self.header_widget, 0)  # Move to top

        # Show the new header
        self.header_widget.show_all()