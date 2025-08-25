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
    return "5.1.4"

# Current version of the application
CURRENT_VERSION = get_current_version()

def get_latest_github_release(repo_owner="psygreg", repo_name="linuxtoys"):
    """
    Fetch the latest release info from GitHub API.
    Returns dict with tag_name and body if successful, None otherwise.
    """
    try:
        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        request = urllib.request.Request(api_url)
        """
        User-Agent:
        https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api?apiVersion=2022-11-28#user-agent
        """
        request.add_header('User-Agent', 'LinuxToys-UpdateChecker/1.0')
        
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return {
                    "tag_name": data.get('tag_name', '').lstrip('v'),
                    "body": data.get('body', '')
                }
    except Exception as e:
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
    
    release_info = get_latest_github_release()
    
    if release_info is None:
        if verbose:
            print("Could not check for updates (network error or API unavailable)")
        return False

    # Extract tag_name (string) for dict return
    latest_version = release_info.get("tag_name", "")

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


def markdown_to_pango(md_text):
    
    #Convert simplified Markdown to Pango Markup.
    
    import re

    # **texto**
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', md_text)

    # *texto*
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*(?<!\*)', r'<i>\1</i>', text)

    # [texto](url) -> texto (url)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<u>\1</u> (<span foreground="blue">\2</span>)', text)

    # - item -> • item
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)

    return text


def _show_gtk_update_dialog(latest_version, changelog=None, translations=None):
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, Pango

        dialog = Gtk.Dialog(
            title=translations.get('update_available_title', 'Update Available') if translations else 'Update Available',
            flags=Gtk.DialogFlags.MODAL
        )
        dialog.set_default_size(400, 300)
        dialog.set_resizable(True)

        # Botões
        download_btn = dialog.add_button(
            translations.get('update_download_btn', 'Download Update') if translations else 'Download Update',
            Gtk.ResponseType.YES
        )
        ignore_btn = dialog.add_button(
            translations.get('update_ignore_btn', 'Ignore') if translations else 'Ignore',
            Gtk.ResponseType.NO
        )
        download_btn.get_style_context().add_class("suggested-action")

        content_area = dialog.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_start(15)
        content_area.set_margin_end(15)
        content_area.set_margin_top(15)
        content_area.set_margin_bottom(15)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # MSG
        message_label = Gtk.Label()
        message_label.set_text(
            translations.get('update_available_message', 'A new version of LinuxToys is available.') if translations else 'A new version of LinuxToys is available.'
        )
        message_label.set_line_wrap(True)
        message_label.set_halign(Gtk.Align.START)
        vbox.pack_start(message_label, False, False, 0)

        # Version
        current_label = Gtk.Label(label=f"{translations.get('update_current_version', 'Current version:') if translations else 'Current version:'} {CURRENT_VERSION}")
        current_label.set_halign(Gtk.Align.START)
        vbox.pack_start(current_label, False, False, 0)

        latest_label = Gtk.Label(label=f"{translations.get('update_latest_version', 'Latest version:') if translations else 'Latest version:'} {latest_version}")
        latest_label.set_halign(Gtk.Align.START)
        latest_label.get_style_context().add_class("dim-label")
        vbox.pack_start(latest_label, False, False, 0)

        # Changelog with Markdown
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        changelog_label = Gtk.Label()
        changelog_label.set_use_markup(True)
        changelog_label.set_line_wrap(True)
        changelog_label.set_justify(Gtk.Justification.LEFT)
        changelog_label.set_xalign(0.0)
        changelog_label.set_selectable(True)
        changelog_label.set_max_width_chars(70)

        if changelog:
            changelog_label.set_markup(markdown_to_pango(changelog.strip()))
        else:
            changelog_label.set_text(translations.get('whatsnew_no_changelog', 'Nenhum changelog disponível.'))

        scrolled.add(changelog_label)
        vbox.pack_start(scrolled, True, True, 0)

        content_area.pack_start(vbox, True, True, 0)

        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    except Exception as e:
        print(f"Error showing GTK update dialog: {e}")
        return False


def show_whatsnew_dialog(version, changelog, translations=None):
    """
    Show 'What's New' dialog for the new version.
    """
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, Pango

        dialog = Gtk.Dialog(
            title=f"{translations.get('whatsnew_title', 'O que há de novo')} – {version}" if translations else f"O que há de novo – {version}",
            flags=Gtk.DialogFlags.MODAL
        )
        dialog.set_default_size(-1, -1)
        dialog.set_resizable(True)

        content_area = dialog.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_start(15)
        content_area.set_margin_end(15)
        content_area.set_margin_top(15)
        content_area.set_margin_bottom(15)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        label = Gtk.Label()
        label.set_text(changelog.strip() if changelog else translations.get('whatsnew_no_changelog', 'Nenhum changelog disponível.') if translations else "Nenhum changelog disponível.")
        label.set_line_wrap(True)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_xalign(0.0)
        label.set_yalign(0.0)
        label.set_max_width_chars(50)
        label.set_selectable(True)
        label.set_ellipsize(Pango.EllipsizeMode.NONE)
        label.set_margin_bottom(10)

        scrolled.add(label)
        content_area.pack_start(scrolled, True, True, 0)

        dialog.add_button(translations.get('whatsnew_ok', 'OK') if translations else "OK", Gtk.ResponseType.CLOSE)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    except Exception as e:
        print(f"Error showing What's New dialog: {e}")


# repo_owner="test_your", repo_name="linuxtoys"):
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
        release_info = get_latest_github_release()
        if not release_info:
            return False
        
        latest_version = release_info["tag_name"]
        changelog = release_info["body"]

        if show_dialog and latest_version:
            if _show_gtk_update_dialog(latest_version, changelog, translations):
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
