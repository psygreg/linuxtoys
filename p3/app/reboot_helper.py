"""
Reboot requirement dialog helper module.
Handles reboot warning dialogs and system reboot functionality.
"""

import os
import subprocess


def check_ostree_pending_deployments():
    """
    Check if there are pending rpm-ostree deployments.
    
    Returns:
        bool: True if there are pending deployments requiring reboot, False otherwise
    """
    try:
        # Run rpm-ostree status and capture output
        result = subprocess.run(['rpm-ostree', 'status'], 
                              capture_output=True, text=True, check=True)
        
        # Look for deployment entries and check if the first one is not booted
        lines = result.stdout.strip().split('\n')
        deployment_found = False
        first_deployment_booted = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('●'):  # Currently booted deployment
                if not deployment_found:  # This is the first deployment
                    first_deployment_booted = True
                deployment_found = True
            elif line.startswith('○'):  # Available deployment (not booted)
                if not deployment_found:  # This is the first deployment and it's not booted
                    return True
                deployment_found = True
        
        # If we found deployments but the first one isn't booted, reboot is needed
        return deployment_found and not first_deployment_booted
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        # rpm-ostree command failed or not found
        return False
    except Exception:
        # Any other error
        return False


def show_reboot_warning_dialog(parent_window):
    """
    Shows a dialog warning that a reboot is required before continuing.

    Args:
        parent_window: The parent GTK window for the dialog

    Returns:
        str: 'reboot_now', 'reboot_later', or 'cancelled'
    """
    # Import GTK only when needed for GUI functionality
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    
    dialog = Gtk.Dialog(
        title=_("Reboot Required"), transient_for=parent_window, flags=0
    )
    dialog.set_default_size(400, 150)
    dialog.set_resizable(False)
    
    # Add custom buttons
    reboot_now_btn = dialog.add_button(_("Reboot Now"), Gtk.ResponseType.YES)
    reboot_later_btn = dialog.add_button(_("Reboot Later"), Gtk.ResponseType.NO)
    
    # Create message content
    content_area = dialog.get_content_area()
    content_area.set_spacing(10)
    content_area.set_margin_start(20)
    content_area.set_margin_end(20)
    content_area.set_margin_top(20)
    content_area.set_margin_bottom(10)
    
    # Add warning icon and message
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
    
    # Warning icon
    icon = Gtk.Image.new_from_icon_name("dialog-warning", Gtk.IconSize.DIALOG)
    icon.set_valign(Gtk.Align.START)
    hbox.pack_start(icon, False, False, 0)
    
    # Message text
    message_label = Gtk.Label()
    message_label.set_text(
        _(
            "A script requiring a system reboot has been executed. You must reboot your computer before installing other features."
        )
    )
    message_label.set_line_wrap(True)
    message_label.set_max_width_chars(50)
    message_label.set_justify(Gtk.Justification.LEFT)
    message_label.set_valign(Gtk.Align.START)
    hbox.pack_start(message_label, True, True, 0)
    
    content_area.pack_start(hbox, True, True, 0)
    dialog.show_all()
    
    response = dialog.run()
    dialog.destroy()
    
    if response == Gtk.ResponseType.YES:
        return 'reboot_now'
    elif response == Gtk.ResponseType.NO:
        return 'reboot_later'
    else:
        return 'cancelled'


def show_ostree_deployment_warning_dialog(parent_window):
    """
    Shows a dialog warning about pending ostree deployments that require reboot.

    Args:
        parent_window: The parent GTK window for the dialog

    Returns:
        str: 'reboot_now', 'reboot_later', or 'cancelled'
    """
    # Import GTK only when needed for GUI functionality
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    
    dialog = Gtk.Dialog(
        title=_("Pending System Updates"), transient_for=parent_window, flags=0
    )
    dialog.set_default_size(400, 150)
    dialog.set_resizable(False)
    
    # Add custom buttons
    reboot_now_btn = dialog.add_button(_("Reboot Now"), Gtk.ResponseType.YES)
    reboot_later_btn = dialog.add_button(_("Reboot Later"), Gtk.ResponseType.NO)
    
    # Create message content
    content_area = dialog.get_content_area()
    content_area.set_spacing(10)
    content_area.set_margin_start(20)
    content_area.set_margin_end(20)
    content_area.set_margin_top(20)
    content_area.set_margin_bottom(10)
    
    # Add warning icon and message
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
    
    # Warning icon
    icon = Gtk.Image.new_from_icon_name("dialog-warning", Gtk.IconSize.DIALOG)
    icon.set_valign(Gtk.Align.START)
    hbox.pack_start(icon, False, False, 0)
    
    # Message text
    message_label = Gtk.Label()
    message_label.set_text(
        _(
            "Your system has pending updates that require a reboot to complete. Please reboot your computer to apply these updates before continuing."
        )
    )
    message_label.set_line_wrap(True)
    message_label.set_max_width_chars(50)
    message_label.set_justify(Gtk.Justification.LEFT)
    message_label.set_valign(Gtk.Align.START)
    hbox.pack_start(message_label, True, True, 0)
    
    content_area.pack_start(hbox, True, True, 0)
    dialog.show_all()
    
    response = dialog.run()
    dialog.destroy()
    
    if response == Gtk.ResponseType.YES:
        return 'reboot_now'
    elif response == Gtk.ResponseType.NO:
        return 'reboot_later'
    else:
        return 'cancelled'


def reboot_system(parent_window):
    """
    Initiates system reboot using systemctl.
    
    Args:
        parent_window: The parent GTK window for error dialogs
        
    Returns:
        bool: True if reboot was initiated successfully, False otherwise
    """
    try:
        subprocess.run(['systemctl', 'reboot'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        # If systemctl fails, show error dialog
        _show_reboot_error_dialog(
            parent_window,
            _("Reboot Failed"),
            f"{_('Failed to initiate system reboot:')} {e}\n"
            f"{_("Please reboot manually using your system's power menu.")}",
        )
        return False
    except Exception as e:
        # Handle other exceptions
        _show_reboot_error_dialog(
            parent_window,
            _("Reboot Failed"),
            f"{_('An error occurred while trying to reboot:')} {e}\n"
            f"{_("Please reboot manually using your system's power menu.")}",
        )
        return False


def _show_reboot_error_dialog(parent_window, title, message):
    """
    Shows an error dialog for reboot failures.
    
    Args:
        parent_window: The parent GTK window for the dialog
        title: Title for the error dialog
        message: Error message to display
    """
    # Import GTK only when needed for GUI functionality
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    
    error_dialog = Gtk.MessageDialog(
        transient_for=parent_window,
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=title
    )
    error_dialog.format_secondary_text(message)
    error_dialog.run()
    error_dialog.destroy()


def handle_reboot_requirement(parent_window, close_app_callback):
    """
    Handles the complete reboot requirement flow.
    Shows dialog, handles user choice, and executes appropriate action.

    Args:
        parent_window: The parent GTK window for dialogs
        close_app_callback: Function to call if the application should be closed
    """
    response = show_reboot_warning_dialog(parent_window)

    if response == "reboot_now":
        # Attempt to reboot the system
        if not reboot_system(parent_window):
            # If reboot failed, close the application as fallback
            close_app_callback()
    elif response == "reboot_later":
        # User chose to reboot later, close the application
        close_app_callback()
    # If cancelled, do nothing and return to the application


def handle_ostree_deployment_requirement(parent_window, close_app_callback):
    """
    Handles the complete ostree deployment requirement flow.
    Shows dialog, handles user choice, and executes appropriate action.

    Args:
        parent_window: The parent GTK window for dialogs
        close_app_callback: Function to call if the application should be closed
    """
    response = show_ostree_deployment_warning_dialog(parent_window)
    
    if response == 'reboot_now':
        # Attempt to reboot the system
        if not reboot_system(parent_window):
            # If reboot failed, close the application as fallback
            close_app_callback()
    elif response == 'reboot_later':
        # User chose to reboot later, close the application
        close_app_callback()
    # If cancelled, do nothing and return to the application
