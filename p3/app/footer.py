import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

def create_footer():
    """
    Creates and returns the main footer widget with clickable links.
    """
    # Main container for the footer
    footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
    footer_box.set_margin_top(10)
    footer_box.set_margin_bottom(10)
    footer_box.set_halign(Gtk.Align.CENTER) # Center the whole footer

    # Get translation for 'Support this Project'
    # Get translation from main window
    translation = None
    try:
        # Find the main window and get its translations attribute
        for win in Gtk.Window.list_toplevels():
            if hasattr(win, 'translations'):
                translation = win.translations
                break
    except Exception:
        pass
    if translation is None:
        translation = {}
    support_label = translation.get('support_footer', 'Support this Project')

    # Website Link
    website_button = Gtk.LinkButton(
        uri="https://github.com/psygreg/linuxtoys", 
        label="Check us out on GitHub"
    )

    # Separator
    separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)

    # Donation Link (translated)
    donation_button = Gtk.LinkButton(
        uri="https://ko-fi.com/psygreg", 
        label=support_label
    )

    # Add buttons to the footer box
    footer_box.pack_start(website_button, False, False, 0)
    footer_box.pack_start(separator, False, False, 10)
    footer_box.pack_start(donation_button, False, False, 0)

    # Add a final separator for visual balance
    final_separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

    # Create a vertical box to hold the links and the top separator
    main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    main_vbox.pack_start(final_separator, False, False, 0)
    # Main menu footer section (use new widget instances)
    main_vbox.menu_footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
    main_vbox.menu_footer_box.set_halign(Gtk.Align.CENTER)
    main_vbox.menu_footer_box.set_margin_top(10)
    main_vbox.menu_footer_box.set_margin_bottom(0)
    menu_website_button = Gtk.LinkButton(
        uri="https://github.com/psygreg/linuxtoys/wiki", 
        label="Wiki"
    )
    menu_separator1 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
    
    # Bug reporting button
    report_label = translation.get('report_label', 'Report Bug')
    menu_bug_button = Gtk.LinkButton(
        uri="https://github.com/psygreg/linuxtoys/issues", 
        label=report_label
    )
    menu_separator2 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
    
    menu_donation_button = Gtk.LinkButton(
        uri="https://ko-fi.com/psygreg", 
        label=support_label
    )
    main_vbox.menu_footer_box.pack_start(menu_website_button, False, False, 0)
    main_vbox.menu_footer_box.pack_start(menu_separator1, False, False, 10)
    main_vbox.menu_footer_box.pack_start(menu_bug_button, False, False, 0)
    main_vbox.menu_footer_box.pack_start(menu_separator2, False, False, 10)
    main_vbox.menu_footer_box.pack_start(menu_donation_button, False, False, 0)
    main_vbox.pack_start(main_vbox.menu_footer_box, False, False, 0)

    # Checklist footer section
    main_vbox.checklist_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    main_vbox.checklist_button_box.set_halign(Gtk.Align.CENTER)
    main_vbox.checklist_button_box.set_margin_top(8)
    main_vbox.checklist_button_box.set_margin_bottom(12)
    main_vbox.pack_end(main_vbox.checklist_button_box, False, False, 0)

    # Methods to show/hide sections
    def show_menu_footer():
        main_vbox.menu_footer_box.set_margin_bottom(8)
        main_vbox.checklist_button_box.set_margin_bottom(0)
        main_vbox.checklist_button_box.hide()
        main_vbox.menu_footer_box.show()
    def show_checklist_footer():
        main_vbox.menu_footer_box.set_margin_bottom(0)
        main_vbox.checklist_button_box.set_margin_bottom(12)
        main_vbox.menu_footer_box.hide()
        main_vbox.checklist_button_box.show()
    main_vbox.show_menu_footer = show_menu_footer
    main_vbox.show_checklist_footer = show_checklist_footer

    # Default to menu footer
    main_vbox.show_menu_footer()

    return main_vbox
