from . import get_icon_path
from .gtk_common import Gtk, GLib
import threading
from .antenna import antenna


class BugReportDialog(Gtk.Dialog):
    """Dialog for collecting bug report information from the user."""
    
    def __init__(self, parent, translations):
        super().__init__(
            title=translations.get("report_label", "Report Bug"),
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK
            )
        )
        self.translations = translations
        self.set_default_size(500, 300)
        
        # Get the OK button and style it
        ok_button = self.get_widget_for_response(Gtk.ResponseType.OK)
        ok_button.get_style_context().add_class("suggested-action")
        
        content_area = self.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_start(10)
        content_area.set_margin_end(10)
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)
        
        # Title label
        title_label = Gtk.Label(
            label="<b>" + translations.get("report_label", "Report Bug") + "</b>",
            use_markup=True,
            xalign=0
        )
        content_area.pack_start(title_label, False, False, 0)
        
        # Description
        desc_label = Gtk.Label(
            label=translations.get(
                "bug_report_desc",
                "Please describe the issue you encountered:"
            ),
            xalign=0,
            wrap=True
        )
        content_area.pack_start(desc_label, False, False, 0)
        
        # Text view with scrolling
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_buffer = self.text_view.get_buffer()
        
        scrolled.add(self.text_view)
        content_area.pack_start(scrolled, True, True, 0)
        
        # System info label
        system_context = antenna.get_system_context()
        info_label = Gtk.Label(
            label=f"<small>{translations.get('system_info', 'System Info')}: {system_context}</small>",
            use_markup=True,
            xalign=0,
            wrap=True
        )
        info_label.set_selectable(True)
        content_area.pack_start(info_label, False, False, 0)
        
        content_area.show_all()
    
    def get_user_comment(self) -> str:
        """Get the user's bug report text."""
        return self.text_buffer.get_text(
            self.text_buffer.get_start_iter(),
            self.text_buffer.get_end_iter(),
            False
        ).strip()


class SupportFooter(Gtk.Box):
    def __init__(self, translations, parent_window=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.set_margin_top(10)
        self.translations = translations or {}
        self.parent_window = parent_window
        self.set_margin_bottom(10)
        self.set_halign(Gtk.Align.CENTER)

        self.urls_labels = [
            ("https://linux.toys/knowledgebase.html", "Wiki", "wiki.svg", True),
            (
                None,
                self.translations.get("report_label", "Report Bug"),
                "report.svg",
                False,
            ),
            (
                "https://linux.toys/credits.html",
                self.translations.get("credits_label", "Credits"),
                "credits.svg",
                True,
            ),
            (
                "https://ko-fi.com/psygreg",
                self.translations.get("support_footer", "Support this project"),
                "sponsor.svg",
                True,
            ),
        ]

        for i, (url, label, icon, is_link) in enumerate(self.urls_labels):
            if is_link:
                button = Gtk.LinkButton(uri=url, label=label)
            else:
                # Bug report button - use regular button with click handler
                button = Gtk.Button(label=label)
                button.connect("clicked", self._on_bug_report_clicked)
            
            if icon_path := get_icon_path(icon):
                icon_img = Gtk.Image.new_from_file(icon_path)
                button.set_image(icon_img)
            self.pack_start(button, False, False, 0)

            if i < len(self.urls_labels) - 1:
                separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                self.pack_start(separator, False, False, 0)
    
    def _on_bug_report_clicked(self, button):
        """Handle bug report button click."""
        # Find the parent window
        parent = self.parent_window
        if not parent:
            parent = self.get_toplevel()
        
        dialog = BugReportDialog(parent, self.translations)
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            comment = dialog.get_user_comment()
            dialog.destroy()
            
            if comment:
                self._submit_bug_report(comment, parent)
            else:
                # Show error if no comment provided
                error_dialog = Gtk.MessageDialog(
                    parent=parent,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=self.translations.get("error_label", "Error"),
                )
                error_dialog.format_secondary_text(
                    self.translations.get(
                        "bug_report_empty",
                        "Please provide a description of the issue."
                    )
                )
                error_dialog.run()
                error_dialog.destroy()
        else:
            dialog.destroy()
    
    def _submit_bug_report(self, comment: str, parent_window):
        """Submit bug report in background thread."""
        def submit():
            try:
                system_context = antenna.get_system_context()
                antenna.submit_issue(
                    title="User Report: Bug from GUI",
                    logs=comment,
                    context=system_context,
                )
                
                # Show success message on main thread
                GLib.idle_add(self._show_success, parent_window)
            except Exception as e:
                # Show error message on main thread
                GLib.idle_add(self._show_error, parent_window, str(e))
        
        # Run submission in background thread
        thread = threading.Thread(target=submit, daemon=True)
        thread.start()
    
    def _show_success(self, parent_window):
        """Show success dialog."""
        dialog = Gtk.MessageDialog(
            parent=parent_window,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=self.translations.get("success_label", "Success"),
        )
        dialog.format_secondary_text(
            self.translations.get(
                "bug_report_submitted",
                "Thank you! Your bug report has been submitted."
            )
        )
        dialog.run()
        dialog.destroy()
    
    def _show_error(self, parent_window, error_msg: str):
        """Show error dialog."""
        dialog = Gtk.MessageDialog(
            parent=parent_window,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=self.translations.get("error_label", "Error"),
        )
        dialog.format_secondary_text(
            self.translations.get(
                "bug_report_failed",
                "Failed to submit bug report: "
            ) + error_msg
        )
        dialog.run()
        dialog.destroy()

class RevealerFooter(Gtk.Revealer):
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.set_transition_duration(300)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.button_box = Gtk.ButtonBox(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=10
        )
        self.button_box.set_layout(Gtk.ButtonBoxStyle.CENTER)
        self.button_box.set_margin_top(5)
        self.button_box.set_margin_bottom(5)

        self.button_next = Gtk.Button(
            label=self.parent.translations.get("next_label", "Next")
        )
        self.button_next.set_image(
            Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.BUTTON)
        )
        self.button_next.set_always_show_image(True)
        self.button_next.set_tooltip_text(
            self.parent.translations.get("next_label", "Next")
        )
        self.button_next.set_size_request(125, 35)
        self.button_next.connect("clicked", self._on_next_clicked)

        self.button_cancel = Gtk.Button(
            label=self.parent.translations.get("cancel_label", "Cancel")
        )
        self.button_cancel.set_image(
            Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.BUTTON)
        )
        self.button_cancel.set_always_show_image(True)
        self.button_cancel.set_tooltip_text(
            self.parent.translations.get("cancel_label", "Cancel")
        )
        self.button_cancel.set_size_request(125, 35)
        self.button_cancel.connect("clicked", self._on_cancel_clicked)

        self.button_box.add(self.button_cancel)
        self.button_box.add(self.button_next)

        self.support = SupportFooter(
            self.parent.translations,
            parent_window=self.parent.get_toplevel()
        )

        container.pack_start(self.support, False, False, 0)
        container.pack_start(self.button_box, False, False, 0)
        self.add(container)

    def _on_next_clicked(self, button):
        self.parent.on_install_checklist(button)

    def _on_cancel_clicked(self, button):
        self.parent.on_cancel_checklist(button)
