"""
Checklist functionality helper for LinuxToys
Handles checklist script execution and management
"""

from .gtk_common import Gtk
from . import script_runner
import os


def run_scripts_sequentially(scripts, parent_window, on_dialog_closed_callback):
    """Run scripts sequentially in a single ScriptRunner window."""
    if not scripts:
        return
    
    runner = script_runner.ScriptRunner(parent_window)
    
    def on_completion():
        if on_dialog_closed_callback:
            on_dialog_closed_callback(None, None)
    
    runner.run_scripts_sequentially(scripts, on_completion=on_completion)


def handle_install_checklist(check_buttons, parent_window, on_dialog_closed_callback):
    """Handle checklist installation - extract selected scripts and run them."""
    selected_scripts = [cb.script_info for cb in check_buttons if cb.get_active()]
    if not selected_scripts:
        return
    
    # Import confirm_helper here to avoid circular imports
    from . import confirm_helper
    
    # Show confirmation dialog before executing checklist
    if not confirm_helper.show_checklist_confirmation(selected_scripts, parent_window):
        return  # User cancelled
    
    run_scripts_sequentially(selected_scripts, parent_window, on_dialog_closed_callback)
