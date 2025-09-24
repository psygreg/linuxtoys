#!/usr/bin/env python3

import json
import urllib.request
import urllib.error
import re
import os
import sys
import gi
gi.require_version("Gtk", "3.0")
gi.require_version('GLib', '2.0')
from gi.repository import Gtk, Pango, Gdk, GLib
import webbrowser


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
    return "5.4.10"

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

# ---- Markdown to Gtk.TextBuffer ----
def markdown_to_textbuffer(md_text):
    """
    Convert simplified Markdown to Gtk.TextBuffer with tags.
    Supports:
    - **bold**
    - _italic_
    - - lists
    - [link](url) -> clickable
    """
    buffer = Gtk.TextBuffer()

    # Create tags
    tag_bold = buffer.create_tag("bold", weight=Pango.Weight.BOLD)
    tag_italic = buffer.create_tag("italic", style=Pango.Style.ITALIC)

    def insert_with_tag(text, tag=None):
        end_iter = buffer.get_end_iter()
        buffer.insert_with_tags(end_iter, text, tag) if tag else buffer.insert(end_iter, text)

    # Split by lines
    for line in md_text.splitlines():
        # Convert lists
        line = re.sub(r'^\s*[-*]\s+', '• ', line)

        pos = 0
        while pos < len(line):
            # Search for bold, italic, link
            m_bold = re.search(r'\*\*(.+?)\*\*', line[pos:])
            m_italic = re.search(r'_(.+?)_', line[pos:])
            m_link = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line[pos:])
            matches = [m for m in [m_bold, m_italic, m_link] if m]

            if not matches:
                insert_with_tag(line[pos:])
                break

            m_first = min(matches, key=lambda x: x.start())
            start, end = m_first.span()
            insert_with_tag(line[pos:pos+start])

            if m_first == m_bold:
                insert_with_tag(m_first.group(1), tag_bold)
            elif m_first == m_italic:
                insert_with_tag(m_first.group(1), tag_italic)
            elif m_first == m_link:
                link_tag = buffer.create_tag(None, foreground="blue", underline=Pango.Underline.SINGLE)
                link_tag.set_data("url", m_first.group(2))
                insert_with_tag(m_first.group(1), link_tag)

            pos += end

        insert_with_tag("\n")

    return buffer

# ---- GTK Update Dialog ----
def _show_gtk_update_dialog(latest_version, changelog=None, translations=None):
    try:
        dialog = Gtk.Dialog(
            title=translations.get('update_available_title', 'Update Available') if translations else 'Update Available',
            flags=Gtk.DialogFlags.MODAL
        )
        dialog.set_default_size(400, 300)
        dialog.set_resizable(True)

        download_btn = dialog.add_button(
            translations.get('update_download_btn', 'Install Update') if translations else 'Install Update',
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

        # Main message
        message_label = Gtk.Label()
        message_label.set_use_markup(True)
        message_label.set_markup(
            f"<b>{translations.get('update_available_message', 'A new version of LinuxToys is available.') if translations else 'A new version of LinuxToys is available.'}</b>"
        )
        message_label.set_line_wrap(True)
        message_label.set_halign(Gtk.Align.START)
        vbox.pack_start(message_label, False, False, 0)

        # Current and latest version labels
        current_label = Gtk.Label(label=f"{translations.get('update_current_version', 'Current version:') if translations else 'Current version:'} {CURRENT_VERSION}")
        current_label.set_halign(Gtk.Align.START)
        vbox.pack_start(current_label, False, False, 0)

        latest_label = Gtk.Label(label=f"{translations.get('update_latest_version', 'Latest version:') if translations else 'Latest version:'} {latest_version}")
        latest_label.set_halign(Gtk.Align.START)
        latest_label.get_style_context().add_class("dim-label")
        vbox.pack_start(latest_label, False, False, 0)

        # Changelog with TextView
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        textview = Gtk.TextView()
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)

        # Connect event handler for clickable links
        def on_event_after(widget, event):
            if event.type == Gdk.EventType.BUTTON_RELEASE and event.button == 1:
                x, y = widget.window_to_buffer_coords(Gtk.TextWindowType.TEXT, event.x, event.y)
                iter_at_click, trailing = widget.get_iter_at_location(x, y)
                tags = iter_at_click.get_tags()
                for tag in tags:
                    url = tag.get_data("url")
                    if url:
                        webbrowser.open(url)
                        return True
            return False

        textview.connect("button-release-event", on_event_after)

        if changelog:
            buffer = markdown_to_textbuffer(changelog.strip())
            if buffer:
                textview.set_buffer(buffer)
            else:
                buffer = Gtk.TextBuffer()
                buffer.set_text(translations.get('whatsnew_no_changelog', 'No changelog available.'))
                textview.set_buffer(buffer)
        else:
            buffer = Gtk.TextBuffer()
            buffer.set_text(translations.get('whatsnew_no_changelog', 'No changelog available.'))
            textview.set_buffer(buffer)

        scrolled.add(textview)
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

def run_install_script():
    """
    Run the installation script to update the app immediately.
    """
    try:
        import subprocess
        command = 'yes | sh -c "$(curl -fsSL https://linux.toys/install.sh)"'
        subprocess.run(['sh', '-c', command], check=True)
        print("Update completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during update: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

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
            # Check if we have a display server before trying to show GTK dialog
            if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
                def show_dialog_and_update():
                    if _show_gtk_update_dialog(latest_version, changelog, translations):
                        run_install_script()
                GLib.idle_add(show_dialog_and_update)
            else:
                # No display, print to console instead
                print(f"Update available: {latest_version}")
                print("Run in GUI mode to see update dialog.")

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
