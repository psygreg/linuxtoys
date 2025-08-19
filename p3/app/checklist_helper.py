"""
Checklist functionality helper for LinuxToys
Handles checklist script execution and management
"""

from .gtk_common import Gtk
from . import script_runner


def run_scripts_sequentially(scripts, parent_window, on_dialog_closed_callback):
    """Run scripts one after another using individual ScriptRunner instances."""
    if not scripts:
        return
    
    def run_next_script(index=0):
        """Recursively run scripts one by one."""
        if index >= len(scripts):
            # All scripts completed
            if on_dialog_closed_callback:
                on_dialog_closed_callback(None, None)
            return
        
        current_script = scripts[index]
        script_path = current_script.get('path') if isinstance(current_script, dict) else current_script
        
        # Create ScriptRunner for this script
        runner = script_runner.ScriptRunner(parent_window)
        
        # Define callback for when this script completes
        def on_script_complete():
            # Run the next script
            run_next_script(index + 1)
        
        # Run the current script
        runner.run_script(script_path, on_completion=on_script_complete)
    
    # Start running the first script
    run_next_script(0)


def handle_install_checklist(check_buttons, parent_window, on_dialog_closed_callback, translations=None):
    """Handle checklist installation - extract selected scripts and run them."""
    selected_scripts = [cb.script_info for cb in check_buttons if cb.get_active()]
    if not selected_scripts:
        return
    
    # Import confirm_helper here to avoid circular imports
    from . import confirm_helper
    
    # Show confirmation dialog before executing checklist
    if not confirm_helper.show_checklist_confirmation(selected_scripts, parent_window, translations or {}):
        return  # User cancelled
    
    run_scripts_sequentially(selected_scripts, parent_window, on_dialog_closed_callback)
