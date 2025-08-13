"""
Checklist functionality helper for LinuxToys
Handles checklist script execution and management
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import subprocess
import threading
import tempfile
import os


def run_scripts_sequentially(scripts, parent_window, on_dialog_closed_callback):
    """Run all scripts in a single shell session via a temporary script."""
    if not scripts:
        return

    # Create a temporary shell script that runs all selected scripts
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as temp_script:
        temp_script.write('#!/bin/bash\n')
        # Add common initialization for checklist scripts
        temp_script.write('. /etc/os-release\n')
        temp_script.write('SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n')
        temp_script.write('source "$SCRIPT_DIR/../libs/linuxtoys.lib"\n')
        temp_script.write('# language\n')
        temp_script.write('_lang_\n')
        temp_script.write('source "$SCRIPT_DIR/../libs/lang/${langfile}.lib"\n')
        temp_script.write('source "$SCRIPT_DIR/../libs/helpers.lib"\n')
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

    # Create execution dialog
    dialog = Gtk.Dialog(title=f"Running checklist scripts", transient_for=parent_window, flags=0)
    close_button = dialog.add_button("Close", Gtk.ResponseType.CLOSE)
    dialog.set_default_size(600, 400)
    dialog.set_deletable(False)
    close_button.set_sensitive(False)
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_hexpand(True)
    scrolled_window.set_vexpand(True)
    textview = Gtk.TextView()
    textview.set_editable(False)
    textview.set_cursor_visible(False)
    textview.set_monospace(True)
    scrolled_window.add(textview)
    box = dialog.get_content_area()
    box.add(scrolled_window)
    dialog.show_all()
    text_buffer = textview.get_buffer()

    def thread_func():
        try:
            running_process = subprocess.Popen(
                ['bash', temp_script_path], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True
            )
            for line in running_process.stdout:
                GLib.idle_add(_append_text_to_buffer, text_buffer, line)
            running_process.wait()
            return_code_msg = f"\n--- Checklist finished with exit code: {running_process.returncode} ---"
            GLib.idle_add(_append_text_to_buffer, text_buffer, return_code_msg)
        except Exception as e:
            error_msg = f"\n--- An unexpected error occurred: {e} ---"
            GLib.idle_add(_append_text_to_buffer, text_buffer, error_msg)
        finally:
            # Clean up temp script
            try:
                os.remove(temp_script_path)
            except Exception:
                pass
            GLib.idle_add(close_button.set_sensitive, True)
            dialog.connect("response", lambda *args: on_dialog_closed_callback(dialog, None))
    
    thread = threading.Thread(target=thread_func)
    thread.start()


def handle_install_checklist(check_buttons, parent_window, on_dialog_closed_callback):
    """Handle checklist installation - extract selected scripts and run them."""
    selected_scripts = [cb.script_info for cb in check_buttons if cb.get_active()]
    if not selected_scripts:
        return
    run_scripts_sequentially(selected_scripts, parent_window, on_dialog_closed_callback)


def _append_text_to_buffer(buffer, text):
    """Safely updates the Gtk.TextView from another thread."""
    buffer.insert(buffer.get_end_iter(), text)
    return False
