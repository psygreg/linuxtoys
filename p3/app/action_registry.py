"""
Action Registry viewer - displays all script execution records from the registry file.
"""

import os
from .gtk_common import Gtk, GLib
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
        main_paned.set_margin_bottom(20)
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
        
        # Set initial position for the divider (left panel gets ~280px)
        main_paned.set_position(280)
        
        # Load registry data
        self.registry_data = parse_registry_file()
        self.__populate_scripts_list()
        
        # Add close button
        self.add_button(_("script_runner_close"), Gtk.ResponseType.CLOSE)
        
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
            return
        
        script_name = model.get_value(tree_iter, 0)
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


def show_action_registry_dialog(parent=None):
    """Show the action registry dialog."""
    dialog = ActionRegistryDialog(parent)
    dialog.run()
    dialog.destroy()
