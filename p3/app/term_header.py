from .gtk_common import Gtk, Pango, escape_markup, load_scaled_pixbuf
from . import get_icon_path

class InfosHead(Gtk.Box):
    def __init__(self, translations=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.translations = translations or {}
        vbox_infos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
 
        self.label_name = Gtk.Label()
        self.label_name.set_halign(Gtk.Align.START)
        self.label_desc = Gtk.Label()
        self.label_desc.set_halign(Gtk.Align.START)
        self.label_desc.set_line_wrap(True)
        self.label_desc.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.label_repo = Gtk.Label()
        self.label_repo.set_halign(Gtk.Align.START)
 
        self.hbox_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.hbox_header.set_margin_left(32)
        self.hbox_header.set_margin_top(12)
        self.hbox_header.set_margin_right(32)
        self.hbox_header.set_margin_bottom(5)
 
        self.icon_head = Gtk.Image()
        self.hbox_header.pack_start(self.icon_head, False, False, 0)
 
        vbox_infos.pack_start(self.label_name, False, False, 0)
        vbox_infos.pack_start(self.label_desc, False, False, 0)
        vbox_infos.pack_start(self.label_repo, False, False, 0)
 
        self.hbox_header.pack_start(vbox_infos, True, True, 0)
        self.pack_start(self.hbox_header, False, False, 0)
 
        hbox_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
 
        # Use translatable button label
        execute_label = self.translations.get("term_view_execute", " Execute ")
        self.button_run = Gtk.Button(label=execute_label)
        self.button_run.set_image(
            Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        )
        self.button_run.set_halign(Gtk.Align.START)
        self.button_run.set_size_request(125, 35)
        remove_label = self.translations.get("term_view_remove", " Remove ")
        self.button_remove = Gtk.Button(label=remove_label)
        self.button_remove.set_image(
            Gtk.Image.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
        )
        self.button_remove.set_halign(Gtk.Align.START)
        self.button_remove.set_size_request(125, 35)
        report_label = self.translations.get("report_label", " Report Bug ")
        self.button_copy = Gtk.Button(label=report_label)
        self.button_copy.set_image(
            Gtk.Image.new_from_icon_name("dialog-warning-symbolic", Gtk.IconSize.BUTTON)
        )
        self.button_copy.set_halign(Gtk.Align.START)
        self.button_copy.set_size_request(150, 35)
 
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_fraction(0.0)
 
        hbox_controls.pack_start(self.button_run, False, False, 0)
        hbox_controls.pack_start(self.button_remove, False, False, 0)
        hbox_controls.pack_start(self.button_copy, False, False, 0)
        hbox_controls.pack_start(self.progress_bar, True, True, 0)
 
        vbox_infos.pack_start(hbox_controls, False, False, 10)
 
    def _update_header_labels(self, script_info: dict):
        name = escape_markup(script_info.get("name", ""))
        description = str(script_info.get("description", "") or "")
        repo = str(script_info.get("repo", "") or "")

        self.label_name.set_markup(f"<big><big><b>{name}</b></big></big>")
        self.label_desc.set_text(description)

        if repo:
            repo_markup = escape_markup(repo)
            repo_display = escape_markup(
                repo.replace("https://", "").replace("http://", "").rstrip("/")
            )
            self.label_repo.set_markup(f"<a href='{repo_markup}'>{repo_display}</a>")
            self.label_repo.show()
        else:
            self.label_repo.set_text("")
            self.label_repo.hide()

        icon_value = script_info.get("icon") or "local-script.svg"
        icon_path = get_icon_path(icon_value) or get_icon_path("local-script.svg")
        pixbuf = load_scaled_pixbuf(icon_path, 100, 100) if icon_path else None

        if pixbuf is not None:
            self.icon_head.set_from_pixbuf(pixbuf)
        else:
            self.icon_head.set_from_icon_name(
                "application-x-executable", Gtk.IconSize.DIALOG
            )
            self.icon_head.set_pixel_size(100)
