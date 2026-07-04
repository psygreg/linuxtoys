import gi

gi.require_version("Gtk", "3.0")

import logging
import os

from gi.repository import Gtk

from .compat import get_system_compat_keys

logger = logging.getLogger(__name__)


def _is_deepin_system():
    """Check if the current system has 'deepin' compatibility key."""
    compat_keys = get_system_compat_keys()
    return "deepin" in compat_keys


def _has_permission_been_requested():
    """Check if the deepin immutability permission has already been requested."""
    state_file = os.path.expanduser("~/.cache/linuxtoys/deepin_immutable_permission")
    return os.path.exists(state_file)


def _mark_permission_requested():
    """Mark that the deepin immutability permission has been requested."""
    state_dir = os.path.expanduser("~/.cache/linuxtoys")
    os.makedirs(state_dir, exist_ok=True)
    state_file = os.path.join(state_dir, "deepin_immutable_permission")
    try:
        with open(state_file, "w") as f:
            f.write("requested\n")
        logger.debug(f"Marked deepin immutability permission as requested: {state_file}")
    except Exception as e:
        logger.error(f"Failed to mark permission as requested: {e}")


def show_deepin_immutability_dialog(parent, translations=None):
    """
    Show the Deepin immutability permission dialog.
    Returns True if user granted permission, False if denied.
    """
    if translations is None:
        translations = {}
    
    title = translations.get("deepin_immutable_title", "LinuxToys")
    message = translations.get("deepin_immutable_message", 
        "LinuxToys requires permission to disable system immutability "
        "so it can perform system optimization and configuration tasks.\n\n"
        "Would you like to enable writable mode on this Deepin system?")
    enable_btn = translations.get("deepin_immutable_script_name", "Enable Writable Mode")
    deny_btn = translations.get("cancel_btn_label", "Cancel")
    
    dialog = Gtk.MessageDialog(
        parent=parent,
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.NONE,
        text=title,
    )
    dialog.format_secondary_text(message)
    dialog.set_modal(True)

    # Add buttons
    allow_button = dialog.add_button(enable_btn, Gtk.ResponseType.OK)
    allow_button.get_style_context().add_class("suggested-action")
    deny_button = dialog.add_button(deny_btn, Gtk.ResponseType.CANCEL)

    response = dialog.run()
    dialog.destroy()

    return response == Gtk.ResponseType.OK


def show_error_dialog(parent, error_message, translations=None):
    """Show an error dialog with the given message."""
    if translations is None:
        translations = {}
    
    error_title = translations.get("error_label", "Error")
    error_msg = translations.get("deepin_immutable_error_message", 
        "An error occurred while enabling writable mode:\n{error_message}")
    error_msg = error_msg.replace("{error_message}", error_message)
    
    dialog = Gtk.MessageDialog(
        parent=parent,
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=error_title,
    )
    dialog.format_secondary_text(error_msg)
    dialog.set_modal(True)
    dialog.run()
    dialog.destroy()


def _run_deepin_immutable_enable(parent_window, translations=None):
    """
    Run the deepin-immutable-writable enable command through term_view
    following the update dialog pattern.
    """
    if translations is None:
        translations = {}
    
    script_name = translations.get("deepin_immutable_script_name", "Enable Deepin Writable Mode")
    script_desc = translations.get("deepin_immutable_script_description", "Disable system immutability on Deepin.")
    error_create = translations.get("deepin_immutable_failed_to_create", "Failed to create script: {error}")
    
    try:
        # Create temporary script
        with open("/tmp/.deepin_immutable_enable", "w") as f:
            script_content = """#!/bin/bash
source "$SCRIPT_DIR/libs/linuxtoys.lib"
sudo_rq
sudo deepin-immutable-writable enable
"""
            f.write(script_content)

        logger.info("Created temporary deepin immutable script")

        # Open term_view with the script
        parent_window.open_term_view(
            [
                {
                    "icon": "linuxtoys.svg",
                    "name": script_name,
                    "description": script_desc,
                    "repo": "",
                    "path": "/tmp/.deepin_immutable_enable",
                    "deepin_immutable": True,
                    "is_script": True,
                    "auto_run": True,
                }
            ]
        )

        # Return True to indicate reboot is required
        return True

    except Exception as e:
        logger.error(f"Error creating deepin immutable script: {e}")
        error_msg = error_create.replace("{error}", str(e))
        show_error_dialog(parent_window, error_msg, translations)
        return False


def check_and_handle_deepin_immutability(parent_window, translations=None):
    """
    Main entry point: Check if Deepin immutability permission needs to be requested
    and handle the dialog flow.

    Args:
        parent_window: The main app window (GTK parent for dialogs)
        translations: Dictionary of translations (optional)

    Returns:
        True if reboot is required, False otherwise
    """
    if translations is None:
        translations = {}
    
    # Check if system is Deepin
    if not _is_deepin_system():
        logger.debug("Not a Deepin system, skipping immutability check")
        return False

    # Check if permission was already requested
    if _has_permission_been_requested():
        logger.debug("Deepin immutability permission already requested previously")
        return False

    logger.info("First run on Deepin system, requesting immutability permission")

    # Mark that permission has been requested (regardless of outcome)
    _mark_permission_requested()

    # Show the permission dialog
    user_granted = show_deepin_immutability_dialog(parent_window, translations)

    if not user_granted:
        logger.info("User denied deepin immutability permission request")
        return False

    logger.info("User granted deepin immutability permission, opening terminal to execute command")

    # Run the script through term_view
    return _run_deepin_immutable_enable(parent_window, translations)
