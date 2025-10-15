from .gtk_common import Gtk
import webbrowser

def create_footer():
    # Main container for the footer
    footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
    footer_box.set_margin_top(10)
    footer_box.set_margin_bottom(10)
    footer_box.set_halign(Gtk.Align.CENTER) # Center the whole footer

    # Attempts to load application translations
    translation = None
    try:
        for win in Gtk.Window.list_toplevels():
            if hasattr(win, 'translations'):
                translation = win.translations
                break
    except Exception:
        pass
    if translation is None:
        translation = {}
    support_label = translation.get('support_footer', 'Support this project')

    # Website LinkButton (opens in default browser)
    website_button = Gtk.LinkButton(
        uri="https://github.com/psygreg/linuxtoys", 
        label="Check us out on GitHub"
    )

    # Vertical separator between buttons
    separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)

    # Donation LinkButton (opens in default browser)
    donation_button = Gtk.LinkButton(
        uri="https://ko-fi.com/psygreg", 
        label=support_label
    )

    # Adds buttons and separator to the footer box, allowing them to expand
    footer_box.pack_start(website_button, True, True, 0)
    footer_box.pack_start(separator, False, False, 10)
    footer_box.pack_start(donation_button, True, True, 0)

    # Horizontal separator at the top of the main footer box
    final_separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

    # Main vertical box to organize the footer
    main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    main_vbox.pack_start(final_separator, False, False, 0)
    main_vbox.menu_footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
    main_vbox.menu_footer_box.set_halign(Gtk.Align.CENTER)
    main_vbox.menu_footer_box.set_margin_top(10)
    main_vbox.menu_footer_box.set_margin_bottom(0)

    # Wiki LinkButton
    menu_website_button = Gtk.LinkButton(
        uri="https://linux.toys/knowledgebase.html", 
        label="Wiki"
    )
    
    # Report bug LinkButton
    report_label = translation.get('report_label', 'Report Bug')
    menu_bug_button = Gtk.LinkButton(
        uri="https://github.com/psygreg/linuxtoys/issues/new?template=bug_report.md",
        label=report_label
    )
    
    # Credits LinkButton
    credits_label = translation.get('credits_label', 'Credits')
    menu_credits_button = Gtk.LinkButton(
        uri="https://linux.toys/credits.html",
        label=credits_label
    )
    
    # Donation LinkButton for the menu
    menu_donation_button = Gtk.LinkButton(
        uri="https://ko-fi.com/psygreg", 
        label=support_label
    )

    # Adds buttons to the footer, allowing them to expand and fill space
    main_vbox.menu_footer_box.pack_start(menu_website_button, True, True, 0)
    main_vbox.menu_footer_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 10)
    main_vbox.menu_footer_box.pack_start(menu_bug_button, True, True, 0)
    main_vbox.menu_footer_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 10)
    main_vbox.menu_footer_box.pack_start(menu_credits_button, True, True, 0)
    main_vbox.menu_footer_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 10)
    main_vbox.menu_footer_box.pack_start(menu_donation_button, True, True, 0)

    # Adds the menu footer box to the main vertical box
    main_vbox.pack_start(main_vbox.menu_footer_box, False, False, 0)

    # Checklist button box for a different footer layout
    main_vbox.checklist_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    main_vbox.checklist_button_box.set_halign(Gtk.Align.CENTER)
    main_vbox.checklist_button_box.set_margin_top(8)
    main_vbox.checklist_button_box.set_margin_bottom(12)
    main_vbox.pack_end(main_vbox.checklist_button_box, False, False, 0)

    # Functions to show/hide the different footers
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
    
    def refresh_translations(new_translations):
        """Refresh footer with new translations"""
        # Update support label text
        support_label = new_translations.get('support_footer', 'Support this project')
        donation_button.set_label(support_label)
        menu_donation_button.set_label(support_label)
        
        # Update report bug label
        report_label = new_translations.get('report_label', 'Report Bug')
        menu_bug_button.set_label(report_label)
        
        # Update credits label
        credits_label = new_translations.get('credits_label', 'Credits')
        menu_credits_button.set_label(credits_label)
    
    main_vbox.show_menu_footer = show_menu_footer
    main_vbox.show_checklist_footer = show_checklist_footer
    main_vbox.refresh_translations = refresh_translations

    # Displays the menu footer by default
    main_vbox.show_menu_footer()

    return main_vbox