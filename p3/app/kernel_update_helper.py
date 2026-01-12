#!/usr/bin/env python3

import os
import re
import subprocess
import urllib.request
import urllib.error
import json
import gi
gi.require_version("Gtk", "3.0")
gi.require_version('GLib', '2.0')
from gi.repository import Gtk, GLib


def get_current_kernel():
    """
    Get the currently running kernel version.
    Returns a tuple (kernel_name, kernel_version) or (None, None) if not a supported kernel.
    """
    try:
        result = subprocess.run(['uname', '-r'], capture_output=True, text=True, timeout=5)
        kernel_string = result.stdout.strip()
        
        # Check if it's a psycachy kernel
        if 'psycachy-lts' in kernel_string.lower():
            # Extract version number (e.g., "6.6.63-psycachy-lts" -> "6.6.63")
            version_match = re.match(r'^(\d+\.\d+\.\d+)', kernel_string)
            if version_match:
                return ('psycachy-lts', version_match.group(1))
        elif 'psycachy-edge' in kernel_string.lower():
            version_match = re.match(r'^(\d+\.\d+\.\d+)', kernel_string)
            if version_match:
                return ('psycachy-edge', version_match.group(1))
        elif 'psycachy' in kernel_string.lower():
            version_match = re.match(r'^(\d+\.\d+\.\d+)', kernel_string)
            if version_match:
                return ('psycachy', version_match.group(1))
        
        return (None, None)
    except Exception as e:
        print(f"Error getting current kernel: {e}")
        return (None, None)


def get_latest_psycachy_releases():
    """
    Fetch the latest psycachy kernel releases from GitHub.
    Returns dict with 'std', 'lts', and 'ubuntu' keys containing version if successful, None otherwise.
    """
    try:
        api_url = "https://api.github.com/repos/psygreg/linux-psycachy/releases"
        request = urllib.request.Request(api_url)
        request.add_header('User-Agent', 'LinuxToys-KernelUpdateChecker/1.0')
        
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                releases = json.loads(response.read().decode('utf-8'))
                
                # Find latest STD, LTS, and Ubuntu releases
                std_tag = None
                lts_tag = None
                ubuntu_tag = None
                
                for release in releases:
                    tag = release.get('tag_name', '')
                    if tag.startswith('STD-') and std_tag is None:
                        std_tag = tag
                    elif tag.startswith('LTS-') and lts_tag is None:
                        lts_tag = tag
                    elif tag.startswith('Ubuntu-') and ubuntu_tag is None:
                        ubuntu_tag = tag
                    
                    # Break if we found all three
                    if std_tag and lts_tag and ubuntu_tag:
                        break
                
                return {
                    'std': std_tag.replace('STD-', '') if std_tag else None,
                    'lts': lts_tag.replace('LTS-', '') if lts_tag else None,
                    'ubuntu': ubuntu_tag.replace('Ubuntu-', '') if ubuntu_tag else None
                }
    except Exception as e:
        print(f"Error fetching psycachy releases: {e}")
        return None


def compare_versions(current, latest):
    """
    Compare two version strings.
    Returns: 
    - 1 if latest > current (update available)
    - 0 if latest == current (up to date)
    - -1 if latest < current (current is newer)
    """
    def version_tuple(v):
        # Convert version string to tuple of integers for comparison
        # e.g., "6.6.63" -> (6, 6, 63)
        parts = v.split('.')
        return tuple(int(part) for part in parts)
    
    try:
        current_tuple = version_tuple(current)
        latest_tuple = version_tuple(latest)
        
        if latest_tuple > current_tuple:
            return 1
        elif latest_tuple == current_tuple:
            return 0
        else:
            return -1
    except (ValueError, TypeError):
        # If version parsing fails, assume no update needed
        return 0


def check_for_kernel_updates(verbose=False):
    """
    Check if a kernel update is available for the current supported kernel.
    Returns tuple (is_update_available, kernel_type, current_version, latest_version)
    """
    kernel_type, current_version = get_current_kernel()
    
    if kernel_type is None:
        if verbose:
            print("Not running a supported kernel")
        return (False, None, None, None)
    
    if verbose:
        print(f"Running {kernel_type} kernel version: {current_version}")
        print("Checking for updates...")
    
    releases = get_latest_psycachy_releases()
    
    if releases is None:
        if verbose:
            print("Could not check for kernel updates (network error or API unavailable)")
        return (False, kernel_type, current_version, None)
    
    # Get the appropriate latest version based on kernel type
    if kernel_type == 'psycachy-lts':
        latest_version = releases.get('lts')
    elif kernel_type == 'psycachy-edge':
        latest_version = releases.get('std')
    else:  # psycachy
        latest_version = releases.get('ubuntu')
    
    if latest_version is None:
        if verbose:
            print(f"Could not find latest version for {kernel_type}")
        return (False, kernel_type, current_version, None)
    
    if verbose:
        print(f"Latest {kernel_type} version: {latest_version}")
    
    comparison = compare_versions(current_version, latest_version)
    
    if comparison == 1:
        if verbose:
            print("Kernel update available!")
        return (True, kernel_type, current_version, latest_version)
    elif comparison == 0:
        if verbose:
            print("Kernel is up to date.")
        return (False, kernel_type, current_version, latest_version)
    else:
        if verbose:
            print("Current kernel version is newer than the latest release.")
        return (False, kernel_type, current_version, latest_version)


def show_kernel_update_dialog(kernel_type, current_version, latest_version, translations=None):
    """
    Show kernel update dialog using GTK.
    Returns True if user wants to update, False otherwise.
    """
    # Only show GTK dialog in GUI mode
    if os.environ.get('LT_MANIFEST') != '1':
        try:
            return _show_gtk_kernel_update_dialog(kernel_type, current_version, latest_version, translations)
        except ImportError:
            print("GTK not available for kernel update dialog")
            return False
    
    # In CLI mode, don't show dialog
    return False


def _show_gtk_kernel_update_dialog(kernel_type, current_version, latest_version, translations=None):
    """
    Internal function to show GTK kernel update dialog.
    """
    try:
        # Get kernel type display name
        kernel_display_map = {
            'psycachy-lts': 'Psycachy LTS',
            'psycachy-edge': 'Psycachy Edge',
            'psycachy': 'Psycachy',
        }
        kernel_display = kernel_display_map.get(kernel_type, 'Kernel')
        
        dialog = Gtk.Dialog(
            title=translations.get('kernel_update_available_title', 'Kernel Update Available') if translations else 'Kernel Update Available',
            flags=Gtk.DialogFlags.MODAL
        )
        dialog.set_default_size(400, 250)
        dialog.set_resizable(False)

        install_btn = dialog.add_button(
            translations.get('kernel_update_install_btn', 'Install Update') if translations else 'Install Update',
            Gtk.ResponseType.YES
        )
        dialog.add_button(
            translations.get('kernel_update_ignore_btn', 'Ignore') if translations else 'Ignore',
            Gtk.ResponseType.NO
        )
        install_btn.get_style_context().add_class("suggested-action")

        content_area = dialog.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_start(15)
        content_area.set_margin_end(15)
        content_area.set_margin_top(15)
        content_area.set_margin_bottom(15)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # Main message
        message_label = Gtk.Label()
        message_label.set_use_markup(True)
        message_text = translations.get('kernel_update_available_message', 
            f'A new version of {kernel_display} kernel is available.') if translations else f'A new version of {kernel_display} kernel is available.'
        message_label.set_markup(f"<b>{message_text}</b>")
        message_label.set_line_wrap(True)
        message_label.set_halign(Gtk.Align.START)
        vbox.pack_start(message_label, False, False, 0)

        # Current and latest version labels
        current_label = Gtk.Label(
            label=f"{translations.get('kernel_update_current_version', 'Current version:') if translations else 'Current version:'} {current_version}"
        )
        current_label.set_halign(Gtk.Align.START)
        vbox.pack_start(current_label, False, False, 0)

        latest_label = Gtk.Label(
            label=f"{translations.get('kernel_update_latest_version', 'Latest version:') if translations else 'Latest version:'} {latest_version}"
        )
        latest_label.set_halign(Gtk.Align.START)
        latest_label.get_style_context().add_class("dim-label")
        vbox.pack_start(latest_label, False, False, 0)

        # Info message
        info_label = Gtk.Label()
        info_label.set_use_markup(True)
        info_text = translations.get('kernel_update_reboot_required', 
            'A system reboot will be required after installation.') if translations else 'A system reboot will be required after installation.'
        info_label.set_markup(f"<i>{info_text}</i>")
        info_label.set_line_wrap(True)
        info_label.set_halign(Gtk.Align.START)
        info_label.get_style_context().add_class("dim-label")
        vbox.pack_start(info_label, False, False, 5)

        content_area.pack_start(vbox, True, True, 0)

        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    except Exception as e:
        print(f"Error showing GTK kernel update dialog: {e}")
        return False


def run_psycachy_installer(kernel_type):
    """
    Run the psycachy.sh script with the appropriate option.
    """
    try:
        # Determine script path relative to this module
        script_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts', 'extra')
        script_path = os.path.join(script_dir, 'psycachy.sh')
        
        # Set SCRIPT_DIR environment variable for the script
        env = os.environ.copy()
        env['SCRIPT_DIR'] = os.path.dirname(os.path.dirname(__file__))
        
        # Determine which flag to use based on kernel type
        flag_map = {
            'psycachy-lts': '-l',
            'psycachy-edge': '-s',
            'psycachy': '-u',
        }
        flag = flag_map.get(kernel_type, '-u')
        
        # Run the script with the appropriate flag
        subprocess.Popen(
            ['bash', script_path, flag],
            stdin=subprocess.PIPE,
            env=env
        )
        
    except Exception as e:
        print(f"Error running psycachy installer: {e}")
        # Show error dialog
        try:
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Installation Error"
            )
            dialog.format_secondary_text(f"Could not run kernel installer: {e}")
            dialog.run()
            dialog.destroy()
        except Exception:
            pass


def run_kernel_update_check(show_dialog=True, verbose=False, translations=None):
    """
    Main kernel update check function.
    Returns True if update is available, False otherwise.
    """
    # First check if we're on a compatible system
    try:
        from .compat import get_system_compat_keys
        compat_keys = get_system_compat_keys()
        
        # Only run on debian/ubuntu systems
        if not ('debian' in compat_keys or 'ubuntu' in compat_keys):
            if verbose:
                print("Kernel update check skipped: not a Debian/Ubuntu system")
            return False
    except Exception as e:
        if verbose:
            print(f"Could not check system compatibility: {e}")
        return False
    
    # Check for kernel updates
    is_update_available, kernel_type, current_version, latest_version = check_for_kernel_updates(verbose)
    
    if is_update_available and show_dialog and kernel_type and current_version and latest_version:
        # Check if we have a display server before trying to show GTK dialog
        if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
            def show_dialog_and_update():
                if show_kernel_update_dialog(kernel_type, current_version, latest_version, translations):
                    run_psycachy_installer(kernel_type)
            GLib.idle_add(show_dialog_and_update)
        else:
            # No display, print to console instead
            if verbose:
                print(f"Kernel update available: {kernel_type} {latest_version}")
                print("Run in GUI mode to install update.")
    
    return is_update_available


if __name__ == "__main__":
    import sys
    
    # Command line interface
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    no_dialog = '--no-dialog' in sys.argv
    
    if run_kernel_update_check(show_dialog=not no_dialog, verbose=verbose, translations=None):
        sys.exit(1)  # Update available
    else:
        sys.exit(0)  # Up to date or check failed
