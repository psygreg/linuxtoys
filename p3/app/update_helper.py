#!/usr/bin/env python3

import json
import urllib.request
import urllib.error
import re
import os
import sys

def get_current_version():
    """
    Get the current version from the version file or fallback to hardcoded version.
    """
    # Try to read from version file first
    version_file_paths = [
        '../src/ver',  # Relative to p3/app/
        'src/ver',     # Relative to p3/
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src', 'ver')  # Absolute path
    ]
    
    for version_file in version_file_paths:
        try:
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    version = f.read().strip()
                    if version:
                        return version
        except Exception:
            continue
    
    # Fallback to hardcoded version
    return "5.0.7"

# Current version of the application
CURRENT_VERSION = get_current_version()

def get_latest_github_release(repo_owner="psygreg", repo_name="linuxtoys"):
    """
    Fetch the latest release tag from GitHub API.
    Returns the tag name (version) if successful, None otherwise.
    """
    try:
        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        
        # Create request with User-Agent header (GitHub API requires it)
        request = urllib.request.Request(api_url)
        request.add_header('User-Agent', 'LinuxToys-UpdateChecker/1.0')
        
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('tag_name', '').lstrip('v')  # Remove 'v' prefix if present
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, Exception) as e:
        print(f"Error fetching latest release: {e}")
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
        # e.g., "4.3.1" -> (4, 3, 1), "4.3" -> (4, 3, 0)
        parts = v.split('.')
        return tuple(int(part) for part in parts) + (0,) * (3 - len(parts))
    
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

def check_for_updates(verbose=False):
    """
    Check if an update is available by comparing current version with latest GitHub release.
    Returns:
    - True if update is available
    - False if up to date or check failed
    """
    if verbose:
        print(f"Current version: {CURRENT_VERSION}")
        print("Checking for updates...")
    
    latest_version = get_latest_github_release()
    
    if latest_version is None:
        if verbose:
            print("Could not check for updates (network error or API unavailable)")
        return False
    
    if verbose:
        print(f"Latest version: {latest_version}")
    
    comparison = compare_versions(CURRENT_VERSION, latest_version)
    
    if comparison == 1:
        if verbose:
            print("Update available!")
        return True
    elif comparison == 0:
        if verbose:
            print("Application is up to date.")
        return False
    else:
        if verbose:
            print("Current version is newer than the latest release.")
        return False

def show_update_dialog(latest_version, translations=None):
    """
    Show update dialog using GTK.
    Returns True if user wants to update, False otherwise.
    """
    # Only show GTK dialog in GUI mode
    if os.environ.get('LT_MANIFEST') != '1':
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk
            
            return _show_gtk_update_dialog(latest_version, translations)
        except ImportError:
            print("GTK not available for update dialog")
            return False
    
    # In CLI mode, don't show dialog
    return False


def _show_gtk_update_dialog(latest_version, translations=None):
    """
    Show update dialog using GTK with translation support.
    Returns True if user wants to update, False otherwise.
    """
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        
        # Create dialog
        dialog = Gtk.Dialog(
            title=translations.get('update_available_title', 'Update Available') if translations else 'Update Available',
            flags=Gtk.DialogFlags.MODAL
        )
        dialog.set_default_size(450, 200)
        dialog.set_resizable(False)
        
        # Add custom buttons
        download_btn = dialog.add_button(
            translations.get('update_download_btn', 'Download Update') if translations else 'Download Update',
            Gtk.ResponseType.YES
        )
        ignore_btn = dialog.add_button(
            translations.get('update_ignore_btn', 'Ignore') if translations else 'Ignore',
            Gtk.ResponseType.NO
        )
        
        # Style the download button as suggested/primary action
        download_btn.get_style_context().add_class("suggested-action")
        
        # Create message content
        content_area = dialog.get_content_area()
        content_area.set_spacing(15)
        content_area.set_margin_start(20)
        content_area.set_margin_end(20)
        content_area.set_margin_top(20)
        content_area.set_margin_bottom(15)
        
        # Add update icon and message
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        
        # Update icon
        icon = Gtk.Image.new_from_icon_name("software-update-available", Gtk.IconSize.DIALOG)
        icon.set_valign(Gtk.Align.START)
        hbox.pack_start(icon, False, False, 0)
        
        # Message area
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Main message
        message_label = Gtk.Label()
        message_text = translations.get('update_available_message', 'A new version of LinuxToys is available.') if translations else 'A new version of LinuxToys is available.'
        message_label.set_text(message_text)
        message_label.set_line_wrap(True)
        message_label.set_max_width_chars(40)
        message_label.set_justify(Gtk.Justification.LEFT)
        message_label.set_halign(Gtk.Align.START)
        vbox.pack_start(message_label, False, False, 0)
        
        # Version info
        version_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        current_label = Gtk.Label()
        current_text = f"{translations.get('update_current_version', 'Current version:') if translations else 'Current version:'} {CURRENT_VERSION}"
        current_label.set_text(current_text)
        current_label.set_halign(Gtk.Align.START)
        version_info_box.pack_start(current_label, False, False, 0)
        
        latest_label = Gtk.Label()
        latest_text = f"{translations.get('update_latest_version', 'Latest version:') if translations else 'Latest version:'} {latest_version}"
        latest_label.set_text(latest_text)
        latest_label.set_halign(Gtk.Align.START)
        latest_label.get_style_context().add_class("dim-label")
        version_info_box.pack_start(latest_label, False, False, 0)
        
        vbox.pack_start(version_info_box, False, False, 0)
        hbox.pack_start(vbox, True, True, 0)
        
        content_area.pack_start(hbox, True, True, 0)
        dialog.show_all()
        
        response = dialog.run()
        dialog.destroy()
        
        return response == Gtk.ResponseType.YES
        
    except Exception as e:
        print(f"Error showing GTK update dialog: {e}")
        return False


def open_releases_page(repo_owner="psygreg", repo_name="linuxtoys"):
    """
    Open the GitHub releases page in the default browser.
    """
    try:
        import subprocess
        releases_url = f"https://github.com/{repo_owner}/{repo_name}/releases"
        subprocess.run(['xdg-open', releases_url])
    except Exception as e:
        print(f"Error opening releases page: {e}")

def run_update_check(show_dialog=True, verbose=False, translations=None):
    """
    Main update check function.
    """
    if check_for_updates(verbose):
        latest_version = get_latest_github_release()
        
        if show_dialog and latest_version:
            if show_update_dialog(latest_version, translations):
                open_releases_page()
        
        return True
    
    return False

if __name__ == "__main__":
    # Command line interface
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    no_dialog = '--no-dialog' in sys.argv
    
    if run_update_check(show_dialog=not no_dialog, verbose=verbose, translations=None):
        sys.exit(1)  # Update available
    else:
        sys.exit(0)  # Up to date or check failed
