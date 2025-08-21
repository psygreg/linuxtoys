import gi
gi.require_version('WebKit2', '4.1')

from .gtk_common import Gtk
from gi.repository import WebKit2
import webbrowser

def create_webview_window(uri):
    # Creates a new window to display a webview
    window = Gtk.Window()
    window.set_default_size(800, 600)
    window.set_title("")

    # Creates a webview widget and loads the specified URI
    webview = WebKit2.WebView()
    webview.load_uri(uri)

    # Adds the webview to the window and shows all widgets
    window.add(webview)
    window.show_all()

def create_footer():
    # Creates the main horizontal box for the footer
    footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
    footer_box.set_margin_top(10)
    footer_box.set_margin_bottom(10)
    footer_box.set_halign(Gtk.Align.CENTER)

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
    support_label = translation.get('support_footer', 'Apoie este projeto')

    # GitHub button that opens in a webview
    website_button = Gtk.Button(label="Check us out on GitHub")
    website_button.connect("clicked", lambda _: create_webview_window("https://github.com/psygreg/linuxtoys"))

    # Vertical separator between buttons
    separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)

    # Donation button that opens in the default web browser
    donation_button = Gtk.Button(label=support_label)
    donation_button.connect("clicked", lambda _: webbrowser.open("https://ko-fi.com/psygreg"))

    # Adds buttons and separator to the footer box
    footer_box.pack_start(website_button, False, False, 0)
    footer_box.pack_start(separator, False, False, 10)
    footer_box.pack_start(donation_button, False, False, 0)

    # Horizontal separator at the top of the main footer box
    final_separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

    # Main vertical box to organize the footer
    main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    main_vbox.pack_start(final_separator, False, False, 0)
    main_vbox.menu_footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    main_vbox.menu_footer_box.set_halign(Gtk.Align.CENTER)
    main_vbox.menu_footer_box.set_margin_top(10)
    main_vbox.menu_footer_box.set_margin_bottom(0)

    # Wiki button that opens in a webview
    menu_website_button = Gtk.Button(label="Wiki")
    menu_website_button.connect("clicked", lambda _: create_webview_window("https://github.com/psygreg/linuxtoys/wiki"))
    
    # Changelog button that opens in a webview
    changelog_button = Gtk.Button(label="Changelog")
    changelog_button.connect("clicked", lambda _: create_webview_window("https://github.com/psygreg/linuxtoys/releases"))
    
    # Report bug button that opens in the default web browser
    report_label = translation.get('report_label', 'Report Bug')
    menu_bug_button = Gtk.Button(label=report_label)
    menu_bug_button.connect("clicked", lambda _: webbrowser.open("https://github.com/psygreg/linuxtoys/issues/new?template=bug_report.md"))
    
    # Credits button that opens in a webview
    credits_label = translation.get('credits_label', 'Credits')
    menu_credits_button = Gtk.Button(label=credits_label)
    menu_credits_button.connect("clicked", lambda _: create_webview_window("https://github.com/psygreg/linuxtoys/wiki/Credits"))
    
    # Donation button for the menu that opens in the default web browser
    menu_donation_button = Gtk.Button(label=support_label)
    menu_donation_button.connect("clicked", lambda _: webbrowser.open("https://ko-fi.com/psygreg"))

    # List of buttons for easier addition to the footer
    buttons = [
        menu_website_button,
        changelog_button,
        menu_bug_button,
        menu_credits_button,
        menu_donation_button
    ]

    # Adds buttons and separators to the footer
    for i, button in enumerate(buttons):
        main_vbox.menu_footer_box.pack_start(button, False, False, 0)
        if i < len(buttons) - 1:
            separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            main_vbox.menu_footer_box.pack_start(separator, False, False, 10)

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
    main_vbox.show_menu_footer = show_menu_footer
    main_vbox.show_checklist_footer = show_checklist_footer

    # Displays the menu footer by default
    main_vbox.show_menu_footer()

    return main_vbox