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
    Check whether Flathub was configured for the first time this session.

    The flag is set by flathub.sh on a fresh Flathub setup, where Flatpak's
    app-export paths and the desktop menu cache have not been picked up by the
    running session yet. Newly installed Flatpak apps need a logout/login (or
    reboot) to appear in the app menu.

    Returns:
        bool: True if the pending flag exists, False otherwise
    """
    return os.path.isfile("/tmp/flatpak_path_pending")


def _clear_flatpak_path_pending():
    """Remove the Flatpak session-refresh flag once the prompt has been shown."""
    try:
        os.remove("/tmp/flatpak_path_pending")
    except OSError:
        pass


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


def _message_dialog(
    parent_window,
    translations,
    *,
    title_key,
    title_default,
    message_key,
    message_default,
    icon_name,
    size,
    max_width_chars,
):
    """Shared chrome for the reboot-helper dialogs.

    Returns ``(dialog, Gtk)``: a transient, non-resizable dialog with the
    standard margins and an icon + wrapped-message row. Buttons and any
    extra content are the caller's concern.
    """
    # Import GTK only when needed for GUI functionality
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    dialog = Gtk.Dialog(
        title=translations.get(title_key, title_default),
        transient_for=parent_window,
        flags=0,
    )
    dialog.set_default_size(*size)
    dialog.set_resizable(False)

    content_area = dialog.get_content_area()
    content_area.set_spacing(10)
    content_area.set_margin_start(20)
    content_area.set_margin_end(20)
    content_area.set_margin_top(20)
    content_area.set_margin_bottom(10)

    # Icon and message row
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
    icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
    icon.set_valign(Gtk.Align.START)
    hbox.pack_start(icon, False, False, 0)

    message_label = Gtk.Label()
    message_label.set_text(translations.get(message_key, message_default))
    message_label.set_line_wrap(True)
    message_label.set_max_width_chars(max_width_chars)
    message_label.set_justify(Gtk.Justification.LEFT)
    message_label.set_valign(Gtk.Align.START)
    hbox.pack_start(message_label, True, True, 0)
    content_area.pack_start(hbox, True, True, 0)

    return dialog, Gtk


def _run_reboot_choice(dialog, Gtk):
    """Show ``dialog``, map its YES/NO buttons to the reboot-choice strings."""
    dialog.show_all()

    response = dialog.run()
    dialog.destroy()

    if response == Gtk.ResponseType.YES:
        return "reboot_now"
    elif response == Gtk.ResponseType.NO:
        return "reboot_later"
    else:
        return "cancelled"


def show_reboot_warning_dialog(
    parent_window, translations, message_key=None, message_default=None
):
    """
    Show a dialog warning that a reboot or session refresh is required.

    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys
        message_key: Optional translation key overriding the default message
        message_default: Optional default text for the overriding message

    Returns:
        str: 'reboot_now', 'reboot_later', or 'cancelled'
    """
    if not message_key:
        message_key = "reboot_required_message"
        message_default = (
            "A script requiring a system reboot has been executed. You must "
            "reboot your computer before installing other features."
        )
    dialog, Gtk = _message_dialog(
        parent_window,
        translations,
        title_key="reboot_required_title",
        title_default="Reboot Required",
        message_key=message_key,
        message_default=message_default or "",
        icon_name="dialog-warning",
        size=(400, 150),
        max_width_chars=50,
    )
    dialog.add_button(
        translations.get("reboot_now_btn", "Reboot Now"), Gtk.ResponseType.YES
    )
    dialog.add_button(
        translations.get("reboot_later_btn", "Reboot Later"), Gtk.ResponseType.NO
    )
    return _run_reboot_choice(dialog, Gtk)


def show_ostree_deployment_warning_dialog(parent_window, translations):
    """
    Shows a dialog warning about pending ostree deployments that require reboot.

    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys

    Returns:
        str: 'reboot_now', 'reboot_later', or 'cancelled'
    """
    dialog, Gtk = _message_dialog(
        parent_window,
        translations,
        title_key="ostree_deployment_title",
        title_default="Pending System Updates",
        message_key="ostree_deployment_message",
        message_default=(
            "Your system has pending updates that require a reboot to "
            "complete. You must reboot your computer to apply these changes "
            "before installing additional features."
        ),
        icon_name="dialog-warning",
        size=(400, 150),
        max_width_chars=50,
    )
    dialog.add_button(
        translations.get("reboot_now_btn", "Reboot Now"), Gtk.ResponseType.YES
    )
    dialog.add_button(
        translations.get("reboot_later_btn", "Reboot Later"), Gtk.ResponseType.NO
    )
    return _run_reboot_choice(dialog, Gtk)


def show_ostree_package_deployment_info_dialog(parent_window, translations):
    """
    Shows an informational dialog explaining how package deployment works on ostree systems.
    This is a non-intrusive info dialog that informs users that newly installed packages
    will only be deployed after a system reboot.

    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys

    Returns:
        bool: True if the user ticked "Don't remind me again", False otherwise
    """
    dialog, Gtk = _message_dialog(
        parent_window,
        translations,
        title_key="ostree_info_title",
        title_default="Package Deployment Information",
        message_key="ostree_info_message",
        message_default=(
            "This system uses ostree for atomic updates. Any newly installed "
            "packages will be deployed and available after your next system "
            "reboot."
        ),
        icon_name="dialog-information",
        size=(420, 170),
        max_width_chars=55,
    )

    # Add OK button to dismiss
    ok_button = dialog.add_button(
        translations.get("ok_btn", "OK"), Gtk.ResponseType.OK
    )
    dialog.set_default_response(Gtk.ResponseType.OK)

    dont_remind = Gtk.CheckButton.new_with_label(
        translations.get("ostree_info_dont_remind", "Don't remind me again")
    )
    dialog.get_content_area().pack_start(dont_remind, False, False, 0)

    dialog.set_focus(ok_button)
    dialog.show_all()

    dialog.run()
    dont_remind_checked = dont_remind.get_active()
    dialog.destroy()

    return dont_remind_checked


def show_flatpak_installed_info_dialog(parent_window, translations):
    """
    Shows an informational dialog informing users that flatpak has been installed
    and flatpak apps will appear in their app menu after a system reboot.

    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys
    """
    dialog, Gtk = _message_dialog(
        parent_window,
        translations,
        title_key="flatpak_installed_title",
        title_default="Flatpak Installed",
        message_key="flatpak_installed_message",
        message_default=(
            "Flatpak has been successfully installed on your system. "
            "Flatpak applications will appear in your app menu after your "
            "next system reboot."
        ),
        icon_name="dialog-information",
        size=(420, 170),
        max_width_chars=55,
    )

    # Add OK button to dismiss
    dialog.add_button(translations.get("ok_btn", "OK"), Gtk.ResponseType.OK)

    dialog.show_all()

    dialog.run()
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


def handle_reboot_requirement(
    parent_window, translations, close_app_callback, flatpak_session=False
):
    """
    Handle the reboot requirement.

    Args:
        flatpak_session: True when the caller knows the requirement is a
            Flatpak session refresh (log out/in) rather than a full reboot.
            When False, the Flatpak session-refresh wording is applied
            automatically if the Flatpak session-refresh flag is set.

    Returns:
        bool: True when script execution should remain blocked.
              False when the user chose to continue without rebooting.
    """
    global _reboot_warning_acknowledged

    if not flatpak_session and check_flatpak_path_pending():
        flatpak_session = True

    if flatpak_session:
        response = show_reboot_warning_dialog(
            parent_window,
            translations,
            message_key="flatpak_session_refresh_message",
            message_default=(
                "Flathub was just set up for the first time on this system. "
                "Log out and back in (or reboot) so newly installed Flatpak "
                "applications appear in your app menu before installing more."
            ),
        )
    else:
        response = show_reboot_warning_dialog(parent_window, translations)

    if response == "reboot_now":
        if not reboot_system(parent_window):
            close_app_callback()

        return True

    if response == "reboot_later":
        _reboot_warning_acknowledged = True
        _acknowledge_warning_this_boot(FLATPAK_ACK_PATH)
        _clear_flatpak_path_pending()
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
        blocked = handle_reboot_requirement(
            parent_window,
            translations,
            close_app_callback,
            flatpak_session=True,
        )
        if not blocked:
            _clear_flatpak_path_pending()
        return blocked

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
