"""
Prerequisites requirement dialog helper module.
Handles displaying and confirming required scripts before proceeding.
"""
from .gtk_common import Gtk, GdkPixbuf

from . import get_icon_path

def _script_row(script_info, show_repo=False):
    """Build one script row: icon + bold name + dim description.

    With ``show_repo`` a dimmed link to the script's repository is appended
    (run-confirmation only; the prerequisites dialog keeps its plainer row).
    """
    item_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

    # Script icon (if available)
    icon_value = script_info.get("icon")
    if icon_value:
        icon_path = get_icon_path(icon_value)
        if icon_path:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    icon_path, 48, 48, True
                )
                icon = Gtk.Image.new_from_pixbuf(pixbuf)
                icon.set_valign(Gtk.Align.START)
                item_hbox.pack_start(icon, False, False, 0)
            except Exception:
                pass  # Silently skip if icon loading fails

    item_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

    # Script name (bold)
    name_label = Gtk.Label()
    name_label.set_markup(f"<b>{script_info.get('name', 'Unknown')}</b>")
    name_label.set_justify(Gtk.Justification.LEFT)
    name_label.set_halign(Gtk.Align.START)
    item_box.pack_start(name_label, False, False, 0)

    # Script description (if available)
    description = script_info.get("description", "")
    if description:
        desc_label = Gtk.Label()
        desc_label.set_text(description)
        desc_label.set_line_wrap(True)
        desc_label.set_max_width_chars(40)
        desc_label.set_justify(Gtk.Justification.LEFT)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.get_style_context().add_class("dim-label")
        item_box.pack_start(desc_label, False, False, 0)

    if show_repo:
        repo = script_info.get("repo", "")
        if repo:
            repo_label = Gtk.Label()
            # Strip protocol and trailing slash from display text for cleaner appearance
            repo_display = repo.replace('https://', '').replace('http://', '').rstrip('/')
            repo_label.set_markup(f"<a href='{repo}'>{repo_display}</a>")
            repo_label.set_line_wrap(True)
            repo_label.set_max_width_chars(40)
            repo_label.set_justify(Gtk.Justification.LEFT)
            repo_label.set_halign(Gtk.Align.START)
            repo_label.get_style_context().add_class("dim-label")
            item_box.pack_start(repo_label, False, False, 0)

    item_hbox.pack_start(item_box, True, True, 0)
    return item_hbox


def _script_list_scroller(scripts, min_height, show_repo=False):
    """Build the scrolled script list shared by the needed/confirm dialogs."""
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled_window.set_min_content_height(min_height)

    scripts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    scripts_box.set_margin_start(10)
    scripts_box.set_margin_end(10)

    for script_info in scripts:
        scripts_box.pack_start(
            _script_row(script_info, show_repo), False, False, 0
        )

    scrolled_window.add(scripts_box)
    return scrolled_window


def show_needed_requirements_dialog(
    parent_window, translations, script_name, required_scripts
):
    """
    Shows a dialog displaying the required scripts that need to be run first.

    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys
        script_name: Name of the script that has requirements
        required_scripts: List of required script info dicts with 'name' and 'description' keys

    Returns:
        bool: True if user confirmed to proceed, False if user chose to cancel
    """
    dialog = Gtk.Dialog(
        title=translations.get("needed_requirements_title", "Script Requirements"),
        transient_for=parent_window,
        flags=0,
    )
    dialog.set_default_size(500, 300)
    dialog.set_resizable(True)

    dialog.add_button(
        translations.get("cancel_btn_label", "Cancel"), Gtk.ResponseType.CANCEL
    )
    dialog.add_button(translations.get("confirm_title", "Proceed"), Gtk.ResponseType.OK)

    # Set focus to the "Proceed" button (safer default for continuing)
    dialog.set_default_response(Gtk.ResponseType.OK)

    content_area = dialog.get_content_area()
    content_area.set_spacing(15)
    content_area.set_margin_start(20)
    content_area.set_margin_end(20)
    content_area.set_margin_top(20)
    content_area.set_margin_bottom(20)

    # Add info icon and header message
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)

    # Info icon
    icon = Gtk.Image.new_from_icon_name("dialog-information", Gtk.IconSize.DIALOG)
    icon.set_valign(Gtk.Align.START)
    header_box.pack_start(icon, False, False, 0)

    # Header message with script_name substitution
    header_label = Gtk.Label()
    header_text = translations.get(
        "needed_requirements_message",
        '"{script_name}" requires the following features to be installed first:',
    ).format(script_name=script_name)
    header_label.set_text(header_text)
    header_label.set_line_wrap(True)
    header_label.set_max_width_chars(50)
    header_label.set_justify(Gtk.Justification.LEFT)
    header_label.set_valign(Gtk.Align.START)
    header_box.pack_start(header_label, True, True, 0)

    content_area.pack_start(header_box, False, False, 0)

    content_area.pack_start(
        _script_list_scroller(required_scripts, min_height=150), True, True, 0
    )

    # Add footer message
    footer_label = Gtk.Label()
    footer_text = translations.get(
        "needed_requirements_footer",
        "These required features will be installed first, then the main script will proceed.",
    )
    footer_label.set_text(footer_text)
    footer_label.set_line_wrap(True)
    footer_label.set_max_width_chars(50)
    footer_label.set_justify(Gtk.Justification.LEFT)
    footer_label.set_halign(Gtk.Align.START)

    # Make footer text slightly lighter
    footer_context = footer_label.get_style_context()
    footer_context.add_class("dim-label")
    content_area.pack_start(footer_label, False, False, 0)

    dialog.show_all()

    response = dialog.run()
    dialog.destroy()

    return response == Gtk.ResponseType.OK


def show_run_confirmation_dialog(parent_window, translations, scripts_to_run, external_request=False):
    """
    Shows a confirmation dialog for running one or more scripts.
    
    Args:
        parent_window: The parent GTK window for the dialog
        translations: Dictionary containing translation keys
        scripts_to_run: List of script info dicts with 'name' and 'description' keys
    
    Returns:
        bool: True if user confirmed to proceed, False if user chose to cancel
    """
    # Format title with script name if there's a single script
    if len(scripts_to_run) == 1:
        script_name = scripts_to_run[0].get('name', 'Script')
        if external_request:
            title = translations.get(
                "uri_install_title", "Install {script_name}"
            ).format(script_name=script_name)
        else:
            title = translations.get(
                "script_runner_title", "Run {script_name}"
            ).format(script_name=script_name)
    else:
        title = translations.get(
            "uri_install_title_multi", "Install requested features"
        ) if external_request else translations.get("script_runner_title", "Run Scripts")
    
    dialog = Gtk.Dialog(
        title=title,
        transient_for=parent_window,
        flags=0,
    )
    dialog.set_default_size(450, 300)
    dialog.set_resizable(True)

    dialog.add_button(
        translations.get("cancel_btn_label", "Cancel"), Gtk.ResponseType.CANCEL
    )
    dialog.add_button(
        translations.get("uri_install_btn", "Install")
        if external_request
        else translations.get("term_view_execute", "Execute"),
        Gtk.ResponseType.OK,
    )

    # Set focus to the "Execute" button
    dialog.set_default_response(Gtk.ResponseType.OK)

    content_area = dialog.get_content_area()
    content_area.set_spacing(15)
    content_area.set_margin_start(20)
    content_area.set_margin_end(20)
    content_area.set_margin_top(20)
    content_area.set_margin_bottom(20)

    if external_request:
        request_label = Gtk.Label()
        request_label.set_text(
            translations.get(
                "uri_install_request_message",
                "A website requested that LinuxToys install this feature. Review it before continuing.",
            )
        )
        request_label.set_line_wrap(True)
        request_label.set_max_width_chars(50)
        request_label.set_halign(Gtk.Align.START)
        request_label.set_justify(Gtk.Justification.LEFT)
        content_area.pack_start(request_label, False, False, 0)

    content_area.pack_start(_script_list_scroller(
        scripts_to_run, min_height=100, show_repo=True
    ), True, True, 0)

    dialog.show_all()

    response = dialog.run()
    dialog.destroy()

    return response == Gtk.ResponseType.OK
