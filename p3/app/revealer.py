from .gtk_common import Gtk
from . import get_icon_path


class SupportFooter(Gtk.Box):
    def __init__(self, translations):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.set_margin_top(10)
        self.translations = translations or {}
        self.set_margin_bottom(10)
        self.set_halign(Gtk.Align.CENTER)

        self.urls_labels = [
            ("https://linux.toys/knowledgebase.html", "Wiki", "wiki.svg"),
            ("https://github.com/psygreg/linuxtoys/issues/new?template=bug_report.md", self.translations.get('report_label', 'Report Bug'), "report.svg"),
            ("https://linux.toys/credits.html", self.translations.get('credits_label', 'Credits'), "credits.svg"),
            ("https://ko-fi.com/psygreg", self.translations.get('support_footer', 'Support this project'), "sponsor.svg")
        ]

        for i, (url, label, icon) in enumerate(self.urls_labels):
            link_button = Gtk.LinkButton(uri=url, label=label)
            if icon_path := get_icon_path(icon):
                icon_img = Gtk.Image.new_from_file(icon_path)
                link_button.set_image(icon_img)
            self.pack_start(link_button, False, False, 0)

            if i < len(self.urls_labels) - 1:
                separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                self.pack_start(separator, False, False, 0)


class RevealerFooter(Gtk.Revealer):
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.set_transition_duration(300)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.button_box = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.button_box.set_layout(Gtk.ButtonBoxStyle.CENTER)
        self.button_box.set_margin_top(5)
        self.button_box.set_margin_bottom(5)

        self.button_next = Gtk.Button(label=self.parent.translations.get("next", "Next"))
        self.button_next.set_image(Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.BUTTON))
        self.button_next.set_always_show_image(True)
        self.button_next.set_tooltip_text(self.parent.translations.get("next", "Next"))
        self.button_next.set_size_request(125, 35)
        self.button_next.connect("clicked", self._on_next_clicked)

        self.button_cancel = Gtk.Button(label=self.parent.translations.get("cancel", "Cancel"))
        self.button_cancel.set_image(Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.BUTTON))
        self.button_cancel.set_always_show_image(True)
        self.button_cancel.set_tooltip_text(self.parent.translations.get("cancel", "Cancel"))
        self.button_cancel.set_size_request(125, 35)
        self.button_cancel.connect("clicked", self._on_cancel_clicked)

        self.button_box.add(self.button_cancel)
        self.button_box.add(self.button_next)

        self.support = SupportFooter(self.parent.translations)

        container.pack_start(self.support, False, False, 0)
        container.pack_start(self.button_box, False, False, 0)
        self.add(container)

    def _on_next_clicked(self, button):
        self.parent.on_install_checklist(button)

    def _on_cancel_clicked(self, button):
        self.parent.on_cancel_checklist(button)