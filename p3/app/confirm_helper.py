"""
Confirmation dialog helper for LinuxToys
Handles confirmation dialogs before script execution
"""

from .gtk_common import Gtk


def _should_skip_confirmation(script_info):
    """
    Check if a script has noconfirm: yes in its header.
    Returns True if confirmation should be skipped.
    """
    # First try to use parsed metadata if available
    if 'noconfirm' in script_info:
        return script_info['noconfirm'].lower() == 'yes'
    
    # Fallback to file parsing for backward compatibility
    try:
        with open(script_info['path'], 'r', encoding='utf-8') as f:
            for line in f:
                if not line.startswith('#'):
                    break  # Stop reading once we exit the header section
                if line.startswith('# noconfirm:'):
                    value = line[len('# noconfirm:'):].strip().lower()
                    return value == 'yes'
    except Exception:
        pass
    return False


def show_single_script_confirmation(script_info, parent_window):
    """
    Show confirmation dialog for a single script execution.

    Args:
        script_info: Dictionary containing script information (name, description, path)
        parent_window: Parent window for the dialog

    Returns:
        True if user confirms, False if cancelled
    """
    # Check if script has noconfirm flag
    if _should_skip_confirmation(script_info):
        return True
        
    # Get translated strings
    confirm_title = _("Confirm Action")
    confirm_btn = _("Install")
    cancel_btn = _("Cancel")
    script_details_label = _("Script Details")
    
    # Create confirmation dialog
    dialog = Gtk.Dialog(
        title="",  # Empty title, we'll add custom title in content
        transient_for=parent_window,
        flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
    )
    
    # Set dialog properties
    dialog.set_resizable(False)
    dialog.set_default_size(400, 200)
    
    # Create content area with script information
    content_area = dialog.get_content_area()
    
    # Custom title label - bold and bigger
    title_label = Gtk.Label()
    title_label.set_markup(f"<span size='large' weight='bold'>{confirm_title}</span>")
    title_label.set_margin_top(15)
    title_label.set_margin_bottom(15)
    title_label.set_halign(Gtk.Align.CENTER)
    content_area.pack_start(title_label, False, False, 0)
    
    # Script details frame
    frame = Gtk.Frame()
    frame.set_label(script_details_label)
    frame.set_margin_bottom(10)
    frame.set_margin_left(30)
    frame.set_margin_right(30)
    
    details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    details_box.set_margin_left(10)
    details_box.set_margin_right(10)
    details_box.set_margin_top(5)
    details_box.set_margin_bottom(10)
    
    # Script description only (removed name display)
    desc_label = Gtk.Label()
    description = script_info.get('description', 'No description available')
    desc_label.set_markup(f"<b>{description}</b>")
    desc_label.set_halign(Gtk.Align.START)
    desc_label.set_line_wrap(True)
    desc_label.set_max_width_chars(50)
    details_box.pack_start(desc_label, False, False, 0)
    
    frame.add(details_box)
    content_area.pack_start(frame, True, True, 0)
    
    # Add buttons with custom padding
    action_area = dialog.get_action_area()
    action_area.set_margin_bottom(8)
    action_area.set_halign(Gtk.Align.CENTER)
    
    dialog.add_button(cancel_btn, Gtk.ResponseType.CANCEL)
    confirm_button = dialog.add_button(confirm_btn, Gtk.ResponseType.OK)
    confirm_button.get_style_context().add_class("suggested-action")
    dialog.set_default_response(Gtk.ResponseType.OK)
    
    # Show all widgets
    dialog.show_all()
    
    # Run dialog and get response
    response = dialog.run()
    dialog.destroy()
    
    return response == Gtk.ResponseType.OK


def show_checklist_confirmation(selected_scripts, parent_window):
    """
    Show confirmation dialog for checklist script execution.

    Args:
        selected_scripts: List of selected script dictionaries
        parent_window: Parent window for the dialog

    Returns:
        True if user confirms, False if cancelled
    """
    # Filter out scripts with noconfirm flag
    scripts_to_confirm = [script for script in selected_scripts if not _should_skip_confirmation(script)]
    
    # If no scripts need confirmation, proceed
    if not scripts_to_confirm:
        return True
        
    # Get translated strings
    confirm_title = _("Confirm Installation")
    confirm_btn = _("Install")
    cancel_btn = _("Cancel")
    selected_items_label = _("Selected Items")
    
    # Create confirmation dialog
    dialog = Gtk.Dialog(
        title="",  # Empty title, we'll add custom title in content
        transient_for=parent_window,
        flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
    )
    
    # Set dialog properties
    dialog.set_resizable(True)
    dialog.set_default_size(500, 400)
    
    # Create content area with selected scripts
    content_area = dialog.get_content_area()
    
    # Custom title label - bold and bigger
    title_label = Gtk.Label()
    title_label.set_markup(f"<span size='large' weight='bold'>{confirm_title}</span>")
    title_label.set_margin_top(15)
    title_label.set_margin_bottom(15)
    title_label.set_halign(Gtk.Align.CENTER)
    content_area.pack_start(title_label, False, False, 0)
    
    # Selected items frame
    frame = Gtk.Frame()
    frame.set_label(f"{selected_items_label} ({len(scripts_to_confirm)})")
    frame.set_margin_bottom(10)
    frame.set_margin_left(30)
    frame.set_margin_right(30)
    
    # Scrollable area for script list
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.set_min_content_height(200)
    
    scripts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    scripts_box.set_margin_left(10)
    scripts_box.set_margin_right(10)
    scripts_box.set_margin_top(5)
    scripts_box.set_margin_bottom(10)
    scripts_box.set_halign(Gtk.Align.FILL)
    
    # Add each script to the list (description only, no name)
    for script in scripts_to_confirm:
        script_item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        script_item.set_margin_bottom(8)
        script_item.set_halign(Gtk.Align.FILL)
        
        # Script description only
        desc_label = Gtk.Label()
        description = script.get('description', 'No description available')
        desc_label.set_markup(f"• <b>{description}</b>")
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_line_wrap(True)
        desc_label.set_max_width_chars(60)
        script_item.pack_start(desc_label, False, False, 0)
        
        scripts_box.pack_start(script_item, False, False, 0)
    
    scrolled.add(scripts_box)
    frame.add(scrolled)
    content_area.pack_start(frame, True, True, 0)
    
    # Show auto-confirm notice if some scripts were filtered
    if len(scripts_to_confirm) < len(selected_scripts):
        auto_count = len(selected_scripts) - len(scripts_to_confirm)
        notice_label = Gtk.Label()
        notice_text = _(
            "Note: {} script(s) will run automatically without confirmation."
        ).format(auto_count)
        notice_label.set_markup(f"<i>{notice_text}</i>")
        notice_label.set_margin_top(5)
        notice_label.set_margin_left(30)
        notice_label.set_margin_right(30)
        notice_label.get_style_context().add_class("dim-label")
        content_area.pack_start(notice_label, False, False, 0)
    
    # Add buttons with custom padding
    action_area = dialog.get_action_area()
    action_area.set_margin_bottom(8)
    action_area.set_halign(Gtk.Align.CENTER)
    
    dialog.add_button(cancel_btn, Gtk.ResponseType.CANCEL)
    confirm_button = dialog.add_button(confirm_btn, Gtk.ResponseType.OK)
    confirm_button.get_style_context().add_class("suggested-action")
    dialog.set_default_response(Gtk.ResponseType.OK)
    
    # Show all widgets
    dialog.show_all()
    
    # Run dialog and get response
    response = dialog.run()
    dialog.destroy()
    
    return response == Gtk.ResponseType.OK
