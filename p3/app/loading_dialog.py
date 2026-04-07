#!/usr/bin/env python3
"""
Loading Dialog for Scripts Initialization

This module provides a GUI loading dialog that displays during scripts
initialization. It only activates in GUI mode (not in CLI mode).
"""

import os
import threading

try:
    from .gtk_common import Gtk, GLib
    GTK_AVAILABLE = True
except ImportError:
    GTK_AVAILABLE = False


class FirstRunLoadingDialog:
    """
    A loading dialog shown during scripts initialization.
    Only appears in GUI mode with a display server available.
    """
    
    def __init__(self, translations=None, parent=None):
        """
        Initialize the loading dialog.
        
        Args:
            translations: Translation dictionary (optional)
            parent: Parent window (optional)
        """
        self.translations = translations or {}
        self.parent = parent
        self.dialog = None
        self.progress_bar = None
        self.status_label = None
        self.pulse_timeout_id = None
    
    def _get_text(self, key, fallback):
        """Get translated text or use fallback."""
        return self.translations.get(key, fallback)
        
    def show(self, title="scripts_init_title", message="scripts_init_fetching"):
        """
        Show the loading dialog.
        
        Args:
            title: Dialog title (translation key or fallback text)
            message: Initial status message (translation key or fallback text)
            
        Returns:
            bool: True if dialog was shown, False if not in GUI mode
        """
        # Only show in GUI mode
        if not self._can_show_gui():
            return False
        
        try:
            # Get translated title and message
            # Fallback to key name if not found in translations
            dialog_title = self._get_text(title, title)
            dialog_message = self._get_text(message, message)
            
            self.dialog = Gtk.Dialog(
                title=dialog_title,
                parent=self.parent,
                flags=Gtk.DialogFlags.MODAL,
                buttons=()  # No buttons while loading
            )
            self.dialog.set_default_size(400, 150)
            self.dialog.set_resizable(False)
            
            # Set window properties
            self.dialog.set_icon_name("dialog-information")
            
            content_area = self.dialog.get_content_area()
            content_area.set_spacing(15)
            content_area.set_margin_start(20)
            content_area.set_margin_end(20)
            content_area.set_margin_top(20)
            content_area.set_margin_bottom(20)
            
            # Status label
            self.status_label = Gtk.Label(
                label=dialog_message,
                xalign=0,
                wrap=True
            )
            content_area.pack_start(self.status_label, False, False, 0)
            
            # Progress bar with pulse animation
            self.progress_bar = Gtk.ProgressBar()
            self.progress_bar.set_show_text(False)
            content_area.pack_start(self.progress_bar, False, False, 0)
            
            # Start pulse animation
            self.pulse_timeout_id = GLib.timeout_add(100, self._pulse_progress)
            
            content_area.show_all()
            
            # Show dialog non-blocking
            self.dialog.show_all()
            return True
            
        except Exception as e:
            print(f"Warning: Could not show loading dialog: {e}")
            return False
    
    def update_message(self, message):
        """
        Update the status message in the dialog.
        
        Args:
            message: New status message (translation key or text)
        """
        if self.status_label and self.dialog:
            try:
                # Get translated message
                translated_message = self._get_text(message, message)
                GLib.idle_add(lambda: self._update_label_safe(translated_message))
            except Exception as e:
                print(f"Warning: Could not update loading dialog message: {e}")
    
    def _update_label_safe(self, message):
        """Safely update label from main thread."""
        if self.status_label:
            self.status_label.set_text(message)
        return False
    
    def _pulse_progress(self):
        """Pulse the progress bar animation."""
        if self.progress_bar and self.dialog:
            try:
                self.progress_bar.pulse()
                return True  # Continue pulsing
            except Exception:
                return False
        return False
    
    def hide(self):
        """Hide and destroy the loading dialog."""
        try:
            if self.pulse_timeout_id is not None:
                GLib.source_remove(self.pulse_timeout_id)
                self.pulse_timeout_id = None
            
            if self.dialog:
                self.dialog.destroy()
                self.dialog = None
        except Exception as e:
            print(f"Warning: Error hiding loading dialog: {e}")
    
    def _can_show_gui(self):
        """
        Check if GUI mode is available.
        
        Returns:
            bool: True if in GUI mode with display available
        """
        # Skip in CLI mode
        if os.environ.get('EASY_CLI') == '1':
            return False
        
        # Check if display is available
        if not GTK_AVAILABLE:
            return False
        
        if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            return False
        
        return True


def show_loading_dialog_for_scripts_init(callback, translations=None):
    """
    Show a loading dialog while executing a callback (typically git sync operations).
    
    This function handles showing the dialog and pumping GTK events while
    the callback executes in a separate thread. The dialog displays during
    all script initialization operations, not just first-run scenarios.
    
    Args:
        callback: Function to call while showing the loading dialog.
                 Should accept a progress_callback function as argument.
        translations: Translation dictionary (optional)
    
    Returns:
        Any: The return value of the callback function
    """
    if not _can_show_gui_dialog():
        # Not in GUI mode, just execute callback without dialog
        return callback(lambda msg: None)
    
    dialog = FirstRunLoadingDialog(translations=translations)
    result = [None]  # Use list to capture result from thread
    exception = [None]  # Capture any exceptions
    
    def run_in_thread():
        try:
            # Create progress callback that updates dialog
            def progress_callback(message):
                if message:
                    dialog.update_message(message)
            
            result[0] = callback(progress_callback)
        except Exception as e:
            exception[0] = e
    
    try:
        # Show the dialog
        if dialog.show():
            # Start callback in background thread
            thread = threading.Thread(target=run_in_thread, daemon=False)
            thread.start()
            
            # Pump GTK events while thread is running
            while thread.is_alive():
                while Gtk.events_pending():
                    Gtk.main_iteration_do(False)
                thread.join(timeout=0.05)
            
            # Hide dialog
            dialog.hide()
        else:
            # Dialog couldn't be shown, just run callback
            result[0] = callback(lambda msg: None)
    except Exception as e:
        dialog.hide()
        exception[0] = e
    
    if exception[0]:
        raise exception[0]
    
    return result[0]


def _can_show_gui_dialog():
    """Check if GUI dialog can be shown."""
    if not GTK_AVAILABLE:
        return False
    if os.environ.get('EASY_CLI') == '1':
        return False
    if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
        return False
    return True
