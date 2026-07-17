from .gtk_common import GLib
from . import parser

class FeaturedCtl:
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
                    scripts = parser.get_scripts_for_category(category_path, self.translations)
                    for script in scripts:
                        if script.get("is_script", False) and not script.get("is_create_script", False):
                            all_scripts.append(script)
                except Exception:
                    pass  # Skip categories that fail to load
        except Exception as e:
            print(f"Error collecting all scripts: {e}")
        
        return all_scripts

    def _calculate_random_scripts_count(self):
        """Calculate how many random scripts can fit without scrolling."""
        # Get window height and calculate available space
        window_height = self.get_allocated_height()
        
        # Estimate heights in pixels
        header_height = 80
        categories_height = 250  # Approximate height for categories section
        separator_and_label_height = 60
        footer_height = 100
        
        available_height = window_height - header_height - categories_height - separator_and_label_height - footer_height
        
        # Each item widget is approximately 76px (52px height + 12px row spacing)
        # Items per line is 5, so we calculate rows needed
        items_per_line = 5
        item_height_with_spacing = 76
        
        # Calculate rows that can fit
        available_rows = max(1, available_height // item_height_with_spacing)
        scripts_count = available_rows * items_per_line
        
        # Cap at a reasonable maximum (e.g., 15 scripts)
        return min(max(5, scripts_count), 15)

    def _select_random_scripts(self):
        """Randomly select scripts to display."""
        if not self.all_scripts:
            return []
        
        import random
        
        count = self._calculate_random_scripts_count()
        return random.sample(self.all_scripts, min(count, len(self.all_scripts)))

    def _refresh_random_scripts_display(self):
        """Refresh the random scripts display with new random selection."""
        if not self.all_scripts or self.current_category_info is not None:
            self.random_scripts_refresh_timer = None
            return False
        
        # Clear existing random scripts
        for child in self.random_scripts_flowbox.get_children():
            child.destroy()
        
        # Get new random selection
        random_scripts = self._select_random_scripts()
        
        # Display them
        for script_info in random_scripts:
            widget = self.create_item_widget(script_info)
            description = script_info.get("description", "")
            if description:
                widget.set_tooltip_text(description)
            else:
                widget.set_tooltip_text(None)
            self.random_scripts_flowbox.add(widget)
        
        self.random_scripts_flowbox.show_all()
        
        # Return True to keep the timer running
        return True

    def _deferred_start_random_scripts_refresh_timer(self):
        """Start the random scripts timer (called asynchronously after scripts are loaded)."""
        # Show the featured section if there are scripts
        if self.featured_scripts_container and self.all_scripts:
            self.featured_scripts_container.show_all()
            
            # Initial display
            self._refresh_random_scripts_display()
            
            # Start periodic refresh timer (30 seconds)
            if self.random_scripts_refresh_timer:
                GLib.source_remove(self.random_scripts_refresh_timer)
            
            self.random_scripts_refresh_timer = GLib.timeout_add_seconds(
                15, self._refresh_random_scripts_display
            )
        
        return False  # Remove from idle callbacks

    def _prepare_random_scripts_display(self):
        """Prepare random scripts display on main menu (defers actual population)."""
        # Set flag to indicate we want the timer to start when scripts are ready
        self.should_start_random_timer = True
        
        # If scripts are already loaded, start the timer now
        if self.all_scripts:
            GLib.idle_add(self._deferred_start_random_scripts_refresh_timer)

    def _stop_random_scripts_refresh_timer(self):
        """Stop the random scripts refresh timer."""
        if self.random_scripts_refresh_timer:
            GLib.source_remove(self.random_scripts_refresh_timer)
            self.random_scripts_refresh_timer = None