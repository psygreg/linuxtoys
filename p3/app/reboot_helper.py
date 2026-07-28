"""
Reboot requirement dialog helper module.
Handles reboot warning dialogs and system reboot functionality.
"""

import os
import subprocess


# Reboot warnings acknowledged for the current application session.
# These deliberately remain in memory only, so a new app session will warn again
# if the underlying reboot requirement still exists.
_reboot_warning_acknowledged = False
_ostree_warning_acknowledged = False
REBOOT_STATE_DIR = os.path.expanduser("~/.cache/linuxtoys/reboot-state")
FLATPAK_ACK_PATH = os.path.join(REBOOT_STATE_DIR, "flatpak-warning-ack")
OSTREE_ACK_PATH = os.path.join(REBOOT_STATE_DIR, "ostree-warning-ack")


def _get_boot_id():
    """Return the ID of the currently running system boot."""
    try:
        with open("/proc/sys/kernel/random/boot_id", "r", encoding="utf-8") as file:
            return file.read().strip()
    except (OSError, ValueError):
        return None


def _warning_acknowledged_this_boot(path):
    """Check whether a warning was acknowledged during the current boot."""
    boot_id = _get_boot_id()

    if not boot_id:
        return False

    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip() == boot_id
    except OSError:
        return False


def _acknowledge_warning_this_boot(path):
    """Persist a warning acknowledgement until the next system boot."""
    boot_id = _get_boot_id()

    if not boot_id:
        return

    try:
        os.makedirs(REBOOT_STATE_DIR, exist_ok=True)

        with open(path, "w", encoding="utf-8") as file:
            file.write(boot_id)
    except OSError:
        # The in-memory acknowledgement still works for this app session.
        pass

def check_flatpak_path_pending():
    """
    Check if flatpak installation has set the path pending flag.
    This indicates that the system PATH needs to be updated, requiring a reboot.

    Returns:
        bool: True if the flatpak path pending flag exists, False otherwise
    """
    return os.path.isfile("/tmp/flatpak_path_pending")


def check_ostree_pending_deployments():
    """
    Check if there are pending rpm-ostree deployments.

    Returns:
        bool: True if there are pending deployments requiring reboot, False otherwise
    """
    try:
        # Run rpm-ostree status and capture output
        result = subprocess.run(
            ["rpm-ostree", "status"], capture_output=True, text=True, check=True
        )

        # Look for deployment entries and check if the first one is not booted
        lines = result.stdout.strip().split("\n")
        deployment_found = False
        first_deployment_booted = False

        for line in lines:
            line = line.strip()
            if line.startswith("●"):  # Currently booted deployment
                if not deployment_found:  # This is the first deployment
                    first_deployment_booted = True
                deployment_found = True
            elif line.startswith("○"):  # Available deployment (not booted)
                if (
                    not deployment_found
                ):  # This is the first deployment and it's not booted
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


def show_reboot_warning_dialog(parent_window, translations):
    """
    Shows a dialog warning that a reboot is required before continuing.

    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys

    Returns:
        str: 'reboot_now', 'reboot_later', or 'cancelled'
    """
    # Import GTK only when needed for GUI functionality
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    dialog = Gtk.Dialog(
        title=translations.get("reboot_required_title", "Reboot Required"),
        transient_for=parent_window,
        flags=0,
    )
    dialog.set_default_size(400, 150)
    dialog.set_resizable(False)

    # Add custom buttons
    reboot_now_btn = dialog.add_button(
        translations.get("reboot_now_btn", "Reboot Now"), Gtk.ResponseType.YES
    )
    reboot_later_btn = dialog.add_button(
        translations.get("reboot_later_btn", "Reboot Later"), Gtk.ResponseType.NO
    )

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
        translations.get(
            "reboot_required_message",
            "A script requiring a system reboot has been executed. You must reboot your computer before installing other features.",
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
        return "reboot_now"
    elif response == Gtk.ResponseType.NO:
        return "reboot_later"
    else:
        return "cancelled"


def show_ostree_deployment_warning_dialog(parent_window, translations):
    """
    Shows a dialog warning about pending ostree deployments that require reboot.

    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys

    Returns:
        str: 'reboot_now', 'reboot_later', or 'cancelled'
    """
    # Import GTK only when needed for GUI functionality
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    dialog = Gtk.Dialog(
        title=translations.get("ostree_deployment_title", "Pending System Updates"),
        transient_for=parent_window,
        flags=0,
    )
    dialog.set_default_size(400, 150)
    dialog.set_resizable(False)

    # Add custom buttons
    reboot_now_btn = dialog.add_button(
        translations.get("reboot_now_btn", "Reboot Now"), Gtk.ResponseType.YES
    )
    reboot_later_btn = dialog.add_button(
        translations.get("reboot_later_btn", "Reboot Later"), Gtk.ResponseType.NO
    )

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
        translations.get(
            "ostree_deployment_message",
            "Your system has pending updates that require a reboot to complete. You must reboot your computer to apply these changes before installing additional features.",
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
        return "reboot_now"
    elif response == Gtk.ResponseType.NO:
        return "reboot_later"
    else:
        return "cancelled"


def show_ostree_package_deployment_info_dialog(parent_window, translations):
    """
    Shows an informational dialog explaining how package deployment works on ostree systems.
    This is a non-intrusive info dialog that informs users that newly installed packages
    will only be deployed after a system reboot.

    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys
    """
    # Import GTK only when needed for GUI functionality
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    dialog = Gtk.Dialog(
        title=translations.get("ostree_info_title", "Package Deployment Information"),
        transient_for=parent_window,
        flags=0,
    )
    dialog.set_default_size(420, 170)
    dialog.set_resizable(False)

    # Add OK button to dismiss
    dialog.add_button(
        translations.get("ok_btn", "OK"), Gtk.ResponseType.OK
    )

    # Create message content
    content_area = dialog.get_content_area()
    content_area.set_spacing(10)
    content_area.set_margin_start(20)
    content_area.set_margin_end(20)
    content_area.set_margin_top(20)
    content_area.set_margin_bottom(10)

    # Add info icon and message
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)

    # Info icon
    icon = Gtk.Image.new_from_icon_name("dialog-information", Gtk.IconSize.DIALOG)
    icon.set_valign(Gtk.Align.START)
    hbox.pack_start(icon, False, False, 0)

    # Message text
    message_label = Gtk.Label()
    message_label.set_text(
        translations.get(
            "ostree_info_message",
            "This system uses ostree for atomic updates. Any newly installed packages will be deployed and available after your next system reboot.",
        )
    )
    message_label.set_line_wrap(True)
    message_label.set_max_width_chars(55)
    message_label.set_justify(Gtk.Justification.LEFT)
    message_label.set_valign(Gtk.Align.START)
    hbox.pack_start(message_label, True, True, 0)

    content_area.pack_start(hbox, True, True, 0)
    dialog.show_all()

    response = dialog.run()
    dialog.destroy()


def show_flatpak_installed_info_dialog(parent_window, translations):
    """
    Shows an informational dialog informing users that flatpak has been installed
    and flatpak apps will appear in their app menu after a system reboot.

    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys
    """
    # Import GTK only when needed for GUI functionality
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    dialog = Gtk.Dialog(
        title=translations.get("flatpak_installed_title", "Flatpak Installed"),
        transient_for=parent_window,
        flags=0,
    )
    dialog.set_default_size(420, 170)
    dialog.set_resizable(False)

    # Add OK button to dismiss
    dialog.add_button(
        translations.get("ok_btn", "OK"), Gtk.ResponseType.OK
    )

    # Create message content
    content_area = dialog.get_content_area()
    content_area.set_spacing(10)
    content_area.set_margin_start(20)
    content_area.set_margin_end(20)
    content_area.set_margin_top(20)
    content_area.set_margin_bottom(10)

    # Add info icon and message
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)

    # Info icon
    icon = Gtk.Image.new_from_icon_name("dialog-information", Gtk.IconSize.DIALOG)
    icon.set_valign(Gtk.Align.START)
    hbox.pack_start(icon, False, False, 0)

    # Message text
    message_label = Gtk.Label()
    message_label.set_text(
        translations.get(
            "flatpak_installed_message",
            "Flatpak has been successfully installed on your system. Flatpak applications will appear in your app menu after your next system reboot.",
        )
    )
    message_label.set_line_wrap(True)
    message_label.set_max_width_chars(55)
    message_label.set_justify(Gtk.Justification.LEFT)
    message_label.set_valign(Gtk.Align.START)
    hbox.pack_start(message_label, True, True, 0)

    content_area.pack_start(hbox, True, True, 0)
    dialog.show_all()

    response = dialog.run()
    dialog.destroy()


def reboot_system(parent_window):
    """
    Initiates system reboot using systemctl.

    Args:
        parent_window: The parent GTK window for error dialogs

    Returns:
        bool: True if reboot was initiated successfully, False otherwise
    """
    try:
        subprocess.run(["systemctl", "reboot"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        # If systemctl fails, show error dialog
        _show_reboot_error_dialog(
            parent_window,
            "Reboot Failed",
            f"Failed to initiate system reboot: {e}\n"
            "Please reboot manually using your system's power menu.",
        )
        return False
    except Exception as e:
        # Handle other exceptions
        _show_reboot_error_dialog(
            parent_window,
            "Reboot Failed",
            f"An error occurred while trying to reboot: {e}\n"
            "Please reboot manually using your system's power menu.",
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

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    error_dialog = Gtk.MessageDialog(
        transient_for=parent_window,
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=title,
    )
    error_dialog.format_secondary_text(message)
    error_dialog.run()
    error_dialog.destroy()


def handle_reboot_requirement(parent_window, translations, close_app_callback):
    """
    Handle the reboot requirement.

    Returns:
        bool: True when script execution should remain blocked.
              False when the user chose to continue without rebooting.
    """
    global _reboot_warning_acknowledged

    response = show_reboot_warning_dialog(parent_window, translations)

    if response == "reboot_now":
        if not reboot_system(parent_window):
            close_app_callback()

        return True

    if response == "reboot_later":
        _reboot_warning_acknowledged = True
        _acknowledge_warning_this_boot(FLATPAK_ACK_PATH)
        return False

    # Closing or cancelling the dialog should not bypass the requirement.
    return True


def handle_ostree_deployment_requirement(
    parent_window, translations, close_app_callback
):
    """
    Handle the pending OSTree deployment requirement.

    Returns:
        bool: True when script execution should remain blocked.
              False when the user chose to continue without rebooting.
    """
    global _ostree_warning_acknowledged

    response = show_ostree_deployment_warning_dialog(
        parent_window,
        translations,
    )

    if response == "reboot_now":
        if not reboot_system(parent_window):
            close_app_callback()

        return True

    if response == "reboot_later":
        _ostree_warning_acknowledged = True
        _acknowledge_warning_this_boot(OSTREE_ACK_PATH)
        return False

    return True


def show_flatpak_installed_info_if_needed(parent_window, translations, transmap_path=None):
    """
    Checks if flatpak was installed during script execution and shows info dialog if needed.
    
    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys
        transmap_path: Optional path to the transmap file (for testing). If None, uses default.
    
    Returns:
        bool: True if flatpak was detected and info shown, False otherwise
    """
    if transmap_path is None:
        transmap_path = os.path.expanduser("~/.cache/linuxtoys/transmap")
    
    if not os.path.exists(transmap_path):
        return False
    
    try:
        with open(transmap_path, "r") as f:
            content = f.read()
            # Check if flatpak was installed (look for "pkg flatpak" or "pkg file flatpak")
            if "pkg flatpak" in content or "pkg file flatpak" in content:
                show_flatpak_installed_info_dialog(parent_window, translations)
                return True
    except Exception:
        pass
    
    return False


def check_reboot_requirement_after_checklist(
    parent_window, translations, close_app_callback
):
    """
    Check reboot requirements after a completed checklist.

    Returns:
        bool: True when further script execution should be blocked.
              False when execution may continue.
    """
    flatpak_acknowledged = (
        _reboot_warning_acknowledged
        or _warning_acknowledged_this_boot(FLATPAK_ACK_PATH)
    )

    if not flatpak_acknowledged and check_flatpak_path_pending():
        return handle_reboot_requirement(
            parent_window,
            translations,
            close_app_callback,
        )

    ostree_acknowledged = (
        _ostree_warning_acknowledged
        or _warning_acknowledged_this_boot(OSTREE_ACK_PATH)
    )

    if not ostree_acknowledged and check_ostree_pending_deployments():
        return handle_ostree_deployment_requirement(
            parent_window,
            translations,
            close_app_callback,
        )

    return False
