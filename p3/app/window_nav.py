from .gtk_common import Gtk, GLib
from .window_items import ItemWidgetFactory
from .window_search import SearchCtl
from .featured_scripts import FeaturedCtl
from .local_scripts import LocalScriptsCtl
from . import app_page, term_view, skills_view, get_icon_path, header

class NavCtl:
    @staticmethod
    def _category_view_key(category_info):
        """Return a stable key for a parser-backed category view."""
        if not category_info:
            return None
        path = category_info.get("path")
        if not path:
            return None
        import os
        return os.path.abspath(path)

    def _retain_current_category_view(self):
        """Keep the current category view alive for zero-rebuild Back navigation."""
        key = self._category_view_key(self.current_category_info)
        if not key or not getattr(self, "scripts_view", None):
            return

        cache = getattr(self, "_category_view_cache", None)
        if cache is None:
            cache = {}
            self._category_view_cache = cache

        cache[key] = {
            "view": self.scripts_view,
            "flowbox": self.scripts_flowbox,
        }

    def _pop_retained_category_view(self, category_info):
        """Take a retained parent view out of the cache as it becomes current again."""
        key = self._category_view_key(category_info)
        if not key:
            return None
        cache = getattr(self, "_category_view_cache", None)
        if not cache:
            return None
        return cache.pop(key, None)

    def _discard_retained_category_views(self):
        """Remove hidden retained views after parser/UI data becomes stale."""
        cache = getattr(self, "_category_view_cache", None)
        if not cache:
            self._category_view_cache = {}
            return

        current_view = getattr(self, "scripts_view", None)
        for retained in tuple(cache.values()):
            view = retained.get("view")
            if view is None or view is current_view:
                continue
            try:
                if view.get_parent() is self.main_stack:
                    self.main_stack.remove(view)
            except (AttributeError, TypeError):
                pass
        cache.clear()

    def _forget_retained_view(self, view):
        """Drop any cache entry that still points at a view being destroyed."""
        cache = getattr(self, "_category_view_cache", None)
        if not cache or view is None:
            return
        for key, retained in tuple(cache.items()):
            if retained.get("view") is view:
                cache.pop(key, None)

    def on_category_clicked(self, widget, event):
        """Handles category click, subcategory click, or root script click."""
        # Check if reboot is required before proceeding
        if self.reboot_required:
            if not self._show_reboot_warning_dialog():
                return

        info = widget.info

        # Check if this is the "Create New Script" option
        if info.get("is_create_script"):
            self._handle_create_new_script()
            return

        # If this is a root script (shown as a category), execute it directly
        if info.get("is_script"):
            if info.get("is_repo_entry") and info.get("has_app_page"):
                self.open_app_page(info)
            else:
                # Preserve the existing root-script execution behavior.
                self.open_term_view([info], removable_script_info=info, auto_run=True)
        else:
            # This is a category or subcategory - navigate to show its contents.
            # Keep the fully-built parent view alive so Back can return to it
            # immediately without reparsing or rebuilding its cards.
            self._retain_current_category_view()

            # Create a new view for the subcategory to enable proper animation
            self.view_counter += 1
            new_view_name = f"scripts_{self.view_counter}"

            # Create new flowbox and scrolled window for this level
            new_flowbox = self.create_flowbox()
            new_scrolled_view = Gtk.ScrolledWindow()
            new_scrolled_view.add(new_flowbox)

            # Attach and show the empty destination first so Gtk.Stack can begin
            # its slide immediately. Card construction is intentionally deferred
            # until the transition finishes; otherwise the first 10-card layout
            # pass can stall the animation on larger categories.
            self.main_stack.add_named(new_scrolled_view, new_view_name)
            new_scrolled_view.show_all()

            self.main_stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
            )

            self.scripts_flowbox = new_flowbox
            self.scripts_view = new_scrolled_view
            self.show_scripts_view(info)

            self._load_scripts_into_flowbox(
                new_flowbox,
                info,
                defer_initial=True,
            )

    def open_app_page(self, info, preserve_previous=False):
        """Open a repository entry's optional details page without altering checklist state."""
        old_page = self.main_stack.get_child_by_name("app_page")
        if old_page is not None:
            self.main_stack.remove(old_page)
            old_page.destroy()

        if not preserve_previous:
            self._app_page_prev = {
                "child": self.main_stack.get_visible_child(),
                "header_visible": self.header_widget.get_visible(),
                "title": self.header_bar.props.title,
                "footer_revealed": self.reveal.get_reveal_child(),
                "back_visible": self.back_button.get_visible(),
            }

        page = app_page.AppPageView(
            info,
            self,
            self.translations,
            on_install_callback=self._install_from_app_page,
        )
        self.main_stack.add_named(page, "app_page")
        page.show_all()

        self.header_widget.hide()
        self.reveal.set_reveal_child(False)
        self.back_button.show()
        self.header_bar.props.title = f"LinuxToys: {info.get('name', 'App')}"
        self.main_stack.set_visible_child_name("app_page")

    def refresh_app_page_with_fade(self, info):
        """Replace the visible app page with a translated copy using a cross-fade."""
        old_page = self.main_stack.get_child_by_name("app_page")
        if old_page is None:
            self.open_app_page(info, preserve_previous=True)
            return

        page = app_page.AppPageView(
            info,
            self,
            self.translations,
            on_install_callback=self._install_from_app_page,
        )

        # Keep both pages alive for the transition. Removing the old page first
        # makes Gtk.Stack animate from the underlying category instead.
        refresh_name = f"app_page_refresh_{self.view_counter}"
        self.view_counter += 1
        self.main_stack.add_named(page, refresh_name)
        page.show_all()

        old_transition = self.main_stack.get_transition_type()
        old_duration = self.main_stack.get_transition_duration()
        fade_duration = 180
        self.main_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.main_stack.set_transition_duration(fade_duration)
        self.main_stack.set_visible_child(page)

        self.header_widget.hide()
        self.reveal.set_reveal_child(False)
        self.back_button.show()
        self.header_bar.props.title = f"LinuxToys: {info.get('name', 'App')}"

        def finish_refresh():
            try:
                if old_page.get_parent() is self.main_stack:
                    self.main_stack.remove(old_page)
                old_page.destroy()
            except (AttributeError, TypeError):
                pass

            # Restore the canonical child name so normal app-page Back/install
            # handling continues to find the page exactly as before.
            try:
                self.main_stack.child_set_property(page, "name", "app_page")
            except (AttributeError, TypeError):
                pass

            self.main_stack.set_transition_type(old_transition)
            self.main_stack.set_transition_duration(old_duration)
            return False

        GLib.timeout_add(fade_duration + 20, finish_refresh)

    def close_app_page_for_install(self):
        """Remove the app page immediately before entering the terminal flow."""
        # The app page already remembers the exact GTK child it was opened from.
        # Preserve that state for the terminal so Back can return to the same
        # already-built menu/category instead of reconstructing it.
        self._term_prev_override = getattr(self, "_app_page_prev", None)

        child = self.main_stack.get_child_by_name("app_page")
        if child is not None:
            self.main_stack.remove(child)
            child.destroy()
        self._app_page_prev = None

    def open_term_view(self, infos, removable_script_info=None, auto_run=True):
        # Check if any script has auto_run flag set in its info dict
        if not auto_run and infos:
            auto_run = any(script.get("auto_run", False) for script in infos)
        
        run_box = term_view.TermRunScripts(
            infos, self, self.translations, removable_script_info=removable_script_info, auto_run=auto_run
        )

        # Header-menu actions can mutate global UI/application state in ways that
        # are unsafe or confusing while the terminal workflow owns navigation.
        self.menu_button.set_sensitive(False)

        # Defensive restore for any non-standard path that destroys the terminal
        # widget without going through on_back_button_clicked().
        run_box.connect(
            "destroy",
            lambda *_args: self.menu_button.set_sensitive(True),
        )

        # Keep the exact previous view alive, just like app-page/category
        # navigation does. App-page installs provide an override pointing to the
        # page's own parent because the app page itself is destroyed before the
        # terminal is opened.
        prev = getattr(self, "_term_prev_override", None)
        self._term_prev_override = None
        if prev is None:
            prev = {
                "child": self.main_stack.get_visible_child(),
                "header_visible": self.header_widget.get_visible(),
                "title": self.header_bar.props.title,
                "footer_revealed": self.reveal.get_reveal_child(),
            }
        else:
            prev = dict(prev)

        prev.update(
            {
                "scripts_view": self.scripts_view,
                "scripts_flowbox": self.scripts_flowbox,
                "category_info": self.current_category_info,
            }
        )
        prev.setdefault("back_visible", self.back_button.get_visible())
        self._term_prev = prev

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

        # Header utility views preserve the exact view they were opened from.
        utility_name = self.main_stack.get_visible_child_name()
        if utility_name in ("installed_features", "appstream_queue"):
            attr = (
                "_installed_features_prev"
                if utility_name == "installed_features"
                else "_appstream_queue_prev"
            )
            prev = getattr(self, attr, None)
            child = self.main_stack.get_child_by_name(utility_name)
            if prev and prev.get("child") is not None:
                self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
                self.main_stack.set_visible_child(prev["child"])
                self.header_bar.props.title = prev.get("title") or "LinuxToys"
                if prev.get("header_visible"):
                    self.header_widget.show()
                else:
                    self.header_widget.hide()
                self.reveal.set_reveal_child(bool(prev.get("footer_revealed")))
                if prev.get("back_visible"):
                    self.back_button.show()
                else:
                    self.back_button.hide()
            else:
                self.show_categories_view()

            setattr(self, attr, None)
            if child is not None:
                def cleanup_utility_view():
                    try:
                        if child.get_parent() is self.main_stack:
                            self.main_stack.remove(child)
                    except (AttributeError, TypeError):
                        pass
                    try:
                        child.destroy()
                    except (AttributeError, TypeError):
                        pass
                    return False
                GLib.timeout_add(max(1, int(self.main_stack.get_transition_duration())), cleanup_utility_view)
            return

        if self.main_stack.get_visible_child_name() == "app_page":
            child = self.main_stack.get_child_by_name("app_page")

            if child is not None:
                self.main_stack.remove(child)
                child.destroy()

            # App pages are leaf views. Regardless of whether this page was opened
            # from a category card, search result, URI, or another app page's
            # Featured section, Back always returns to the app's owning category.
            #
            # The category view is already kept alive in scripts_view while an app
            # page is open, so prefer it when it matches the page's category. This
            # avoids treating another app page as navigation history.
            if self.current_category_info and self.scripts_view is not None:
                self.main_stack.set_transition_type(
                    Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
                )
                self.main_stack.set_visible_child(self.scripts_view)
                self.header_widget.show()
                self._update_header(self.current_category_info)

                category_name = self.current_category_info.get("name", "Unknown")
                self.header_bar.props.title = f"LinuxToys: {category_name}"
                self.back_button.show()

                if self._is_local_scripts_category(self.current_category_info):
                    self._enable_drag_and_drop()
                else:
                    self._disable_drag_and_drop()

                if (
                    self.current_category_info.get("display_mode", "menu")
                    == "checklist"
                ):
                    self.reveal.set_reveal_child(len(self.check_buttons) >= 2)
                else:
                    self.reveal.set_reveal_child(False)
            else:
                # Root-level app pages have no owning category view to restore.
                self.show_categories_view()

            self._app_page_prev = None
            return

        # Handle leaving the terminal before normal search navigation.
        if self.main_stack.get_visible_child_name() == "running_scripts":
            # Package transactions explicitly lock navigation because interrupting a
            # native package manager can leave the system package database inconsistent.
            if getattr(self, "_runner_navigation_locked", False):
                return

            child = self.main_stack.get_child_by_name("running_scripts")

            # This branch returns before the generic running-script check below,
            # so cancellation must be confirmed here before destroying the VTE view.
            if self._script_running:
                if not self._show_cancel_script_warning_dialog():
                    return

                # Send Ctrl+C to the foreground process before removing the terminal.
                # Destroying the VTE alone is not a reliable cancellation mechanism.
                if child is not None and hasattr(child, "terminal"):
                    try:
                        child.terminal.feed_child(b"\x03")
                    except (TypeError, AttributeError):
                        pass

                self._script_running = False

            returning_to_search = self.search_active
            search_query = self.search_entry.get_text().strip()
            prev = getattr(self, "_term_prev", None)

            transition_delay = max(
                1, int(self.main_stack.get_transition_duration())
            )

            # Installation/removal may have changed the action registry. Rebuild
            # only the first screenful while the terminal is still visible. The
            # remaining progressive batches are deliberately held until after the
            # reverse Gtk.Stack transition, so FlowBox layout cannot steal frames
            # from the slide. The initial cards are also made fully opaque at once
            # because their fade would otherwise overlap the stack animation.
            self._refresh_removable_scripts(
                pause_after_initial_ms=transition_delay + 16,
                animate_initial=False,
            )

            def cleanup_terminal_view():
                # Keep the source child alive for the whole reverse transition,
                # matching normal category Back navigation.
                if child is not None:
                    try:
                        if child.get_parent() is self.main_stack:
                            self.main_stack.remove(child)
                    except (AttributeError, TypeError):
                        pass
                    try:
                        child.destroy()
                    except (AttributeError, TypeError):
                        pass
                return False

            # Search results are generated views whose removable buttons also need
            # refreshing, so preserve their existing dedicated refresh path. Keep
            # the terminal child attached until that transition has completed too.
            if returning_to_search and search_query:
                self.search_results = self.search_engine.search(search_query)
                self._display_search_results()
                GLib.timeout_add(transition_delay, cleanup_terminal_view)
                self._term_prev = None
                return

            if prev and prev.get("child") is not None:
                self.scripts_view = prev.get("scripts_view", self.scripts_view)
                self.scripts_flowbox = prev.get("scripts_flowbox", self.scripts_flowbox)
                self.current_category_info = prev.get("category_info")

                self.main_stack.set_transition_type(
                    Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
                )
                self.main_stack.set_visible_child(prev["child"])
                self.header_bar.props.title = prev.get("title") or "LinuxToys"
                if hasattr(prev["child"], "refresh"):
                    prev["child"].refresh()

                if prev.get("header_visible"):
                    self.header_widget.show()
                else:
                    self.header_widget.hide()
                self.reveal.set_reveal_child(bool(prev.get("footer_revealed")))

                if prev.get("back_visible"):
                    self.back_button.show()
                else:
                    self.back_button.hide()

                if self.current_category_info and self._is_local_scripts_category(
                    self.current_category_info
                ):
                    self._enable_drag_and_drop()
                else:
                    self._disable_drag_and_drop()

                # Installation/removal may have changed which scripts are eligible
                # for Featured. Returning to the root must therefore recalculate the
                # set immediately instead of waiting for the next periodic rotation.
                if self.current_category_info is None:
                    self._prepare_random_scripts_display()

                GLib.timeout_add(transition_delay, cleanup_terminal_view)
                self._term_prev = None
                return

            # Defensive fallback for older/invalid state. This should only be
            # reached if the original child disappeared while the terminal was open.
            self._term_prev = None
            if self.current_category_info:
                self.header_widget.show()
                self._update_header(self.current_category_info)
                self.main_stack.set_visible_child(self.scripts_view)
                self.back_button.show()
            else:
                self.show_categories_view()
            GLib.timeout_add(transition_delay, cleanup_terminal_view)
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
            current_view = self.scripts_view

            # Go back to the previous category/subcategory. Prefer its retained,
            # already-built GTK view; reconstruct only when the cache was
            # deliberately invalidated (language/source/data refresh) or absent.
            previous_category = self.navigation_stack.pop()
            self.current_category_info = previous_category
            retained = self._pop_retained_category_view(previous_category)

            self.main_stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
            )

            if retained is not None:
                previous_view = retained["view"]
                previous_flowbox = retained["flowbox"]
                self.scripts_view = previous_view
                self.scripts_flowbox = previous_flowbox
                self.main_stack.set_visible_child(previous_view)
            else:
                # Safe fallback for invalidated/missing retained views. Keep the
                # transition-first behavior so reconstruction cannot stall it.
                self.view_counter += 1
                new_view_name = f"scripts_{self.view_counter}"

                new_flowbox = self.create_flowbox()
                new_scrolled_view = Gtk.ScrolledWindow()
                new_scrolled_view.add(new_flowbox)
                self.main_stack.add_named(new_scrolled_view, new_view_name)
                new_scrolled_view.show_all()

                self.scripts_flowbox = new_flowbox
                self.scripts_view = new_scrolled_view
                self.main_stack.set_visible_child(new_scrolled_view)

                self._load_scripts_into_flowbox(
                    new_flowbox,
                    previous_category,
                    defer_initial=True,
                )

            category_name = previous_category.get("name", "Unknown")
            self.header_bar.props.title = f"LinuxToys: {category_name}"
            self._update_header(previous_category)

            if self._is_local_scripts_category(previous_category):
                self._enable_drag_and_drop()
            else:
                self._disable_drag_and_drop()

            if previous_category.get("display_mode", "menu") == "checklist":
                self.reveal.set_reveal_child(len(self.check_buttons) >= 2)
            else:
                self.reveal.set_reveal_child(False)

            # The child we are leaving is no longer part of history. Remove it
            # after the animation; parent views deeper in history remain cached.
            def cleanup_old_view():
                self._forget_retained_view(current_view)
                try:
                    self.main_stack.remove(current_view)
                except Exception:
                    pass
                return False

            GLib.timeout_add(300, cleanup_old_view)

        else:
            # No more items in stack, go to main categories view.
            current_view = self.scripts_view
            self.main_stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
            )
            self.show_categories_view()

            def cleanup_scripts_view():
                self._forget_retained_view(current_view)
                try:
                    self.main_stack.remove(current_view)
                except Exception:
                    pass
                return False

            GLib.timeout_add(300, cleanup_scripts_view)

    def show_categories_view(self):
        """Switches to the main categories view."""
        # Any retained category views are only useful while their history is
        # reachable. Returning to the root discards that history and its widgets.
        self._discard_retained_category_views()
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
        # Specials is a virtual curated browser, not part of the user's normal
        # category-browsing history used to bias main-menu Featured suggestions.
        if not (
            category_info.get("is_linuxtoys_specials")
            or category_info.get("is_linuxtoys_specials_category")
        ):
            self._record_featured_category(category_info)

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