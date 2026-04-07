"""
Action Registry viewer - displays all script execution records from the registry file.
"""

import os
import shutil
from .gtk_common import Gtk
from .lang_utils import create_translator


def parse_registry_file():
    """
    Parse the registry file and return a dict of scripts and their operations.
    
    Returns:
        dict: {script_name: [(timestamp, [operations]), ...], ...}
         Empty dict if registry file doesn't exist or can't be read.
    """
    registry_file = os.path.expanduser("~/.cache/linuxtoys/registry")
    
    if not os.path.exists(registry_file):
        return {}
    
    try:
        with open(registry_file, "r") as f:
            content = f.read()
    except Exception:
        return {}
    
    # Split by registry entries (format: [timestamp] Script: name\nChanges:\n  - operation)
    entries = content.split("---\n")
    
    scripts_registry = {}
    
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        
        lines = entry.split("\n")
        if not lines:
            continue
        
        # First line should have the timestamp and script name
        first_line = lines[0] if lines else ""
        
        # Parse first line: [timestamp] Script: name
        timestamp = ""
        script_name = ""
        
        if "[" in first_line and "]" in first_line:
            bracket_end = first_line.index("]")
            timestamp = first_line[1:bracket_end]  # Extract timestamp
            rest = first_line[bracket_end+1:].strip()
            if rest.startswith("Script:"):
                script_name = rest.replace("Script:", "").strip()
        
        if not script_name:
            continue
        
        # Parse operations
        operations = []
        for line in lines[1:]:
            line = line.strip()
            if line.startswith("- "):
                # Remove "- " prefix
                op_line = line[2:].strip()
                if op_line and op_line != "Changes:" and op_line != "Changes: (none)":
                    operations.append(op_line)
        
        # Add to registry
        if script_name not in scripts_registry:
            scripts_registry[script_name] = []
        
        scripts_registry[script_name].append((timestamp, operations))
    
    return scripts_registry


def _find_backup_files_for_script(script_name, registry_data):
    """
    Find all backup files (.bak) associated with a script's executions.
    
    Args:
        script_name: name of the script
        registry_data: dict of {script_name: [(timestamp, [operations]), ...]}
    
    Returns:
        list of backup file paths that exist on the system
    """
    backup_files = []
    
    if script_name not in registry_data:
        return backup_files
    
    executions = registry_data[script_name]
    
    for timestamp, operations in executions:
        for op_line in operations:
            parts = op_line.split()
            if not parts:
                continue
            
            op_type = parts[0]
            
            # File-related operations have backup files
            if op_type in ("edited", "created", "removed") and len(parts) > 1:
                file_path = parts[1]
                backup_path = f"{file_path}.bak"
                
                # Check if backup exists and not already in list
                if os.path.exists(backup_path) and backup_path not in backup_files:
                    backup_files.append(backup_path)
    
    return backup_files


def _remove_script_from_registry(script_name):
    """
    Remove all entries for a script from the registry file.
    
    Returns True if successful, False otherwise.
    """
    registry_file = os.path.expanduser("~/.cache/linuxtoys/registry")
    
    if not os.path.exists(registry_file):
        return False
    
    try:
        with open(registry_file, "r") as f:
            content = f.read()
    except Exception:
        return False
    
    # Split by registry entries
    entries = content.split("---\n")
    
    # Filter out entries for the script we want to remove
    filtered_entries = []
    found = False
    
    for entry in entries:
        entry_stripped = entry.strip()
        if not entry_stripped:
            continue
        
        lines = entry_stripped.split("\n")
        first_line = lines[0] if lines else ""
        
        # Check if this entry belongs to the script we're removing
        if f"Script: {script_name}" in first_line:
            found = True
            continue  # Skip this entry
        
        filtered_entries.append(entry_stripped)
    
    if not found:
        return False
    
    # Reconstruct the registry file
    new_content = "---\n".join(filtered_entries)
    
    try:
        with open(registry_file, "w") as f:
            f.write(new_content)
        return True
    except Exception:
        return False


def _remove_backup_files(backup_files):
    """
    Remove backup files from the system.
    
    Args:
        backup_files: list of backup file paths
    
    Returns:
        tuple of (successful_count, failed_paths)
    """
    successful_count = 0
    failed_paths = []
    
    for backup_path in backup_files:
        try:
            if os.path.isdir(backup_path):
                shutil.rmtree(backup_path)
            else:
                os.remove(backup_path)
            successful_count += 1
        except Exception:
            failed_paths.append(backup_path)
    
    return successful_count, failed_paths


class ActionRegistryDialog(Gtk.Dialog):
    """Dialog displaying script execution records from the registry file."""
    
    def __init__(self, parent=None):
        _ = create_translator()
        super().__init__(title=_("action_registry"), transient_for=parent, modal=True)
        
        self.set_default_size(700, 500)
        self.set_border_width(12)
        
        content_area = self.get_content_area()
        content_area.set_vexpand(True)
        content_area.set_hexpand(True)
        
        # Main paned container for split panels
        main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        main_paned.set_vexpand(True)
        main_paned.set_hexpand(True)
        main_paned.set_margin_bottom(15)
        content_area.add(main_paned)
        
        # Left panel - Scripts list
        left_frame = Gtk.Frame(label=_("scripts_label"))
        left_frame.set_shadow_type(Gtk.ShadowType.IN)
        left_frame.set_vexpand(True)
        left_frame.set_hexpand(False)
        
        # Scrolled window for scripts list
        scrolled_left = Gtk.ScrolledWindow()
        scrolled_left.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_left.set_vexpand(True)
        scrolled_left.set_hexpand(False)
        left_frame.add(scrolled_left)
        
        # Scripts list store and treeview
        self.scripts_store = Gtk.ListStore(str)  # script name
        self.scripts_treeview = Gtk.TreeView(model=self.scripts_store)
        self.scripts_treeview.set_headers_visible(False)
        
        # Column for script names
        cell_renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Script", cell_renderer, text=0)
        self.scripts_treeview.append_column(column)
        
        # Selection changed callback
        selection = self.scripts_treeview.get_selection()
        selection.connect("changed", self.__on_script_selected)
        
        scrolled_left.add(self.scripts_treeview)
        main_paned.pack1(left_frame, False, True)
        
        # Right panel - Registry details
        right_frame = Gtk.Frame(label=_("registry_details_label"))
        right_frame.set_shadow_type(Gtk.ShadowType.IN)
        right_frame.set_vexpand(True)
        right_frame.set_hexpand(True)
        
        # Scrolled window for details
        scrolled_right = Gtk.ScrolledWindow()
        scrolled_right.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_right.set_min_content_width(350)
        scrolled_right.set_vexpand(True)
        scrolled_right.set_hexpand(True)
        right_frame.add(scrolled_right)
        
        # Text view for registry details
        self.details_textview = Gtk.TextView()
        self.details_textview.set_editable(False)
        self.details_textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.details_textview.set_monospace(True)
        scrolled_right.add(self.details_textview)
        
        main_paned.pack2(right_frame, True, True)
        
        # Set initial position for the divider (left panel gets ~200px)
        main_paned.set_position(200)
        
        # Load registry data
        self.registry_data = parse_registry_file()
        self.__populate_scripts_list()
        
        # Track currently selected script for cleanup
        self.current_script = None
        
        # Add buttons
        cleanup_button = self.add_button(_("registry_cleanup_label"), Gtk.ResponseType.NONE)
        cleanup_button.set_sensitive(False)
        self.cleanup_button = cleanup_button
        
        self.add_button(_("script_runner_close"), Gtk.ResponseType.CLOSE)
        
        # Connect cleanup button signal
        self.cleanup_button.connect("clicked", self.__on_cleanup_clicked)
        
        self.show_all()
    
    def __populate_scripts_list(self):
        """Populate the scripts list from registry data."""
        self.scripts_store.clear()
        for script_name in sorted(self.registry_data.keys()):
            self.scripts_store.append([script_name])
    
    def __on_script_selected(self, selection):
        """Handle script selection from the list."""
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            self.details_textview.get_buffer().set_text("")
            self.current_script = None
            self.cleanup_button.set_sensitive(False)
            return
        
        script_name = model.get_value(tree_iter, 0)
        self.current_script = script_name
        self.cleanup_button.set_sensitive(True)
        self.__display_script_details(script_name)
    
    def __display_script_details(self, script_name):
        """Display registry details for the selected script."""
        if script_name not in self.registry_data:
            self.details_textview.get_buffer().set_text("")
            return
        
        executions = self.registry_data[script_name]
        
        # Build detailed text
        lines = [f"Script: {script_name}\n"]
        lines.append("=" * 60 + "\n\n")
        
        for idx, (timestamp, operations) in enumerate(executions, 1):
            lines.append(f"Execution #{idx}")
            if timestamp:
                lines.append(f"Timestamp: {timestamp}\n")
            else:
                lines.append("\n")
            
            if operations:
                lines.append("Operations:")
                for op in operations:
                    lines.append(f"  • {op}")
            else:
                lines.append("Operations: (none)")
            
            lines.append("\n" + "-" * 60 + "\n\n")
        
        text_buffer = self.details_textview.get_buffer()
        text_buffer.set_text("".join(lines))
    
    def __on_cleanup_clicked(self, button):
        """Handle cleanup button click."""
        if not self.current_script:
            return
        
        self.__show_cleanup_confirmation()
    
    def __show_cleanup_confirmation(self):
        """Show confirmation dialog for cleanup."""
        if not self.current_script:
            return
        
        _ = create_translator()
        
        # Find backup files that will be removed
        backup_files = _find_backup_files_for_script(self.current_script, self.registry_data)
        
        # Create confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=_("registry_cleanup_title"),
        )
        
        backup_count = len(backup_files)
        secondary_text = (
            f"This will remove the registry entry for '{self.current_script}' and delete "
            f"{backup_count} backup file(s). After removal, you will no longer be able "
            "to undo the operations from this script using the app.\n\n"
            "This action cannot be undone."
        )
        dialog.format_secondary_text(secondary_text)
        
        # Add buttons
        dialog.add_buttons(
            _("cancel_btn_label"), Gtk.ResponseType.CANCEL,
            _("term_view_remove"), Gtk.ResponseType.OK
        )
        
        # Make OK button red/destructive
        ok_button = dialog.get_widget_for_response(Gtk.ResponseType.OK)
        ok_button.get_style_context().add_class("destructive-action")
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK:
            self.__perform_cleanup()
    
    def __perform_cleanup(self):
        """Perform the actual cleanup."""
        if not self.current_script:
            return
        
        _ = create_translator()
        
        # Find backup files
        backup_files = _find_backup_files_for_script(self.current_script, self.registry_data)
        
        # Remove script from registry
        registry_removed = _remove_script_from_registry(self.current_script)
        
        # Remove backup files
        success_count, failed_paths = _remove_backup_files(backup_files)
        
        # Show result dialog
        if registry_removed:
            if failed_paths:
                # Some files couldn't be removed
                message = (
                    f"Registry entry removed. {success_count} backup file(s) deleted, "
                    f"but {len(failed_paths)} could not be removed (may require elevated permissions)."
                )
                dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text=_("registry_cleanup_partial_title"),
                )
                dialog.format_secondary_text(message)
            else:
                # All successful
                message = (
                    f"Registry entry and {len(backup_files)} backup file(s) successfully removed."
                )
                dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text=_("registry_cleanup_success_title"),
                )
                dialog.format_secondary_text(message)
            
            dialog.run()
            dialog.destroy()
            
            # Refresh the list
            self.registry_data = parse_registry_file()
            self.__populate_scripts_list()
            self.current_script = None
            self.cleanup_button.set_sensitive(False)
            self.details_textview.get_buffer().set_text("")
        else:
            # Failed to remove from registry
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_("registry_cleanup_failed"),
            )
            dialog.run()
            dialog.destroy()


def show_action_registry_dialog(parent=None):
    """Show the action registry dialog."""
    dialog = ActionRegistryDialog(parent)
    dialog.run()
    dialog.destroy()
