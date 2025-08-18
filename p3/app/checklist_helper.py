"""
Checklist functionality helper for LinuxToys
Handles checklist script execution and management
"""

from .gtk_common import Gtk

import tempfile
import os
from . import script_runner


def run_scripts_sequentially(scripts, parent_window, on_dialog_closed_callback):
    """Run all scripts in a single shell session via a temporary script using ScriptRunner."""
    if not scripts:
        return

    # Create a temporary shell script that runs all selected scripts
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as temp_script:
        temp_script.write('#!/bin/bash\n')
        # Add common initialization for checklist scripts
        temp_script.write('. /etc/os-release\n')
        temp_script.write('SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"\n')
        temp_script.write('source "$SCRIPT_DIR/../../libs/linuxtoys.lib"\n')
        temp_script.write('# language\n')
        temp_script.write('_lang_\n')
        temp_script.write('source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"\n')
        temp_script.write('source "$SCRIPT_DIR/../../libs/helpers.lib"\n')
        temp_script.write('\n')
        
        # Check if any script uses flatpak_in_lib and add it once at the beginning
        needs_flatpak = False
        for script in scripts:
            try:
                with open(script["path"], 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'flatpak_in_lib' in content:
                        needs_flatpak = True
                        break
            except Exception:
                pass
        
        if needs_flatpak:
            temp_script.write('# Initialize flatpak once for all scripts\n')
            temp_script.write('flatpak_in_lib\n')
            temp_script.write('\n')

        needs_sudo = False
        for script in scripts:
            try:
                with open(script["path"], 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'sudo_rq' in content:
                        needs_sudo = True
                        break
            except Exception:
                pass
        if needs_sudo:
            temp_script.write('# Initialize sudo once for all scripts\n')
            temp_script.write('sudo_rq\n')
            temp_script.write('\n')

        # Add selected scripts (with flatpak_in_lib calls removed)
        for script in scripts:
            if needs_flatpak:
                # Create a modified version that comments out flatpak_in_lib calls
                temp_script.write(f'# Running {script["name"]}\n')
                temp_script.write(f'sed "s/^flatpak_in_lib/#flatpak_in_lib # (already executed)/" "{script["path"]}" | bash\n')
            if needs_sudo:
                # Create a modified version that comments out sudo_rq calls
                temp_script.write(f'# Running {script["name"]}\n')
                temp_script.write(f'sed "s/^sudo_rq/#sudo_rq # (already executed)/" "{script["path"]}" | bash\n')
            else:
                temp_script.write(f'"{script["path"]}"\n')
        temp_script_path = temp_script.name
    os.chmod(temp_script_path, 0o700)

    # Create a script info object for the ScriptRunner
    script_names = [script['name'] for script in scripts]
    if len(script_names) == 1:
        title = script_names[0]
    else:
        title = f"Checklist ({len(script_names)} scripts)"
    
    checklist_script_info = {
        'name': title,
        'path': temp_script_path,
        'description': f"Running {len(scripts)} selected scripts"
    }
    
    # Create a ScriptRunner instance for the checklist execution
    runner = script_runner.ScriptRunner(parent_window)
    
    # Define completion callback that cleans up and calls the original callback
    def completion_handler():
        # Clean up temp script
        try:
            os.remove(temp_script_path)
        except Exception:
            pass
        # Call the original callback
        if on_dialog_closed_callback:
            on_dialog_closed_callback(None, None)
    
    # Use ScriptRunner to execute the checklist
    dialog = runner.run_script(
        checklist_script_info,
        on_completion=completion_handler
    )
    
    # Update dialog title to be more specific for checklists
    if dialog:
        dialog.set_title("Running checklist scripts")
    
    return dialog


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
