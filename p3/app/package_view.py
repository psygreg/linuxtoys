import os

from .gtk_common import Gtk, GLib
from gi.repository import Pango
from . import gui_rs


class PackageView(Gtk.Box):
    """Transient details/install view for a user-selected local package."""

    def __init__(self, parent, package_path, metadata):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.parent = parent
        self.package_path = os.path.realpath(package_path)
        self.metadata = dict(metadata or {})
        self.job_id = None
        self._return_source = None

        self.set_name("linuxtoys-package-view")
        self.set_hexpand(True)
        self.set_vexpand(True)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        self.pack_start(scroller, True, True, 0)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        body.set_halign(Gtk.Align.CENTER)
        body.set_valign(Gtk.Align.CENTER)
        body.set_margin_start(40)
        body.set_margin_end(40)
        body.set_margin_top(32)
        body.set_margin_bottom(32)
        scroller.add(body)

        icon = Gtk.Image()
        gui_rs.set_image_source(
            icon,
            self.metadata.get("icon_path", ""),
            self.metadata.get("icon_name", "package-x-generic"),
            96,
        )
        body.pack_start(icon, False, False, 0)

        name = str(self.metadata.get("name") or os.path.basename(self.package_path))
        title = Gtk.Label()
        title.set_markup(f"<span size='xx-large'><b>{GLib.markup_escape_text(name)}</b></span>")
        title.set_justify(Gtk.Justification.CENTER)
        title.set_line_wrap(True)
        body.pack_start(title, False, False, 0)

        description = str(self.metadata.get("description") or "").strip()
        if description:
            label = Gtk.Label(label=description)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_justify(Gtk.Justification.CENTER)
            label.set_max_width_chars(72)
            label.get_style_context().add_class("dim-label")
            body.pack_start(label, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(7)
        grid.set_halign(Gtk.Align.CENTER)
        body.pack_start(grid, False, False, 8)

        rows = (
            ("package_view_version", "Version", self.metadata.get("version")),
            ("package_view_architecture", "Architecture", self.metadata.get("architecture")),
            ("package_view_format", "Format", parent.translations.get(f"package_view_format_{self.metadata.get('kind', 'package')}", self.metadata.get("format_label") or "Package")),
            ("package_view_maintainer", "Maintainer", self.metadata.get("maintainer")),
            ("package_view_file", "File", os.path.basename(self.package_path)),
        )
        row = 0
        for key, fallback, value in rows:
            value = str(value or "").strip()
            if not value:
                continue
            key_label = Gtk.Label(label=parent.translations.get(key, fallback))
            key_label.set_halign(Gtk.Align.END)
            key_label.get_style_context().add_class("dim-label")
            value_label = Gtk.Label(label=value)
            value_label.set_halign(Gtk.Align.START)
            value_label.set_selectable(True)
            value_label.set_ellipsize(Pango.EllipsizeMode.END)
            value_label.set_max_width_chars(48)
            grid.attach(key_label, 0, row, 1, 1)
            grid.attach(value_label, 1, row, 1, 1)
            row += 1

        warning = Gtk.Label(
            label=parent.translations.get(
                "package_view_external_warning",
                "This package comes from an external file. Only install packages from sources you trust.",
            )
        )
        warning.set_line_wrap(True)
        warning.set_justify(Gtk.Justification.CENTER)
        warning.set_max_width_chars(68)
        warning.get_style_context().add_class("dim-label")
        body.pack_start(warning, False, False, 8)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls.set_halign(Gtk.Align.CENTER)
        body.pack_start(controls, False, False, 4)

        self.cancel_button = Gtk.Button(
            label=parent.translations.get("cancel_label", "Cancel")
        )
        self.cancel_button.set_size_request(125, 35)
        self.cancel_button.connect("clicked", lambda *_: parent.close_package_view())
        controls.pack_start(self.cancel_button, False, False, 0)

        self.install_button = Gtk.Button()
        self.install_button.set_size_request(125, 35)
        self.install_button.get_style_context().add_class("suggested-action")
        self.install_button.connect("clicked", self._install)
        controls.pack_start(self.install_button, False, False, 0)

        self.set_install_state("available")
        self.show_all()

    def _install(self, _button):
        if self.job_id is not None:
            return
        self.job_id = self.parent.enqueue_local_package(self.package_path, self.metadata)
        if self.job_id:
            self.set_install_state("queued")

    def _record(self):
        if not self.job_id:
            return None
        for record in self.parent._appstream_runner.snapshot():
            if record.get("id") == self.job_id:
                return record
        return None

    def refresh_install_state(self):
        record = self._record()
        if record is None:
            return
        self.set_install_state(record.get("status") or "available")

    def set_install_state(self, state):
        button = self.install_button
        context = button.get_style_context()
        context.remove_class("suggested-action")

        if state == "queued":
            label = self.parent.translations.get("app_page_queued", "Queued")
            icon = "appointment-soon-symbolic"
            sensitive = False
        elif state == "running":
            label = self.parent.translations.get("update_status_updating", "Installing…")
            icon = "folder-download-symbolic"
            sensitive = False
        elif state == "success":
            label = self.parent.translations.get("package_view_completed", "Completed")
            icon = "emblem-ok-symbolic"
            sensitive = False
            if self._return_source is None:
                self._return_source = GLib.timeout_add(2000, self._return_after_success)
        elif state == "failed":
            label = self.parent.translations.get("skills_install_label", "Install")
            icon = "emblem-system-symbolic"
            sensitive = True
            self.job_id = None
        else:
            label = self.parent.translations.get("skills_install_label", "Install")
            icon = "emblem-system-symbolic"
            sensitive = True
            context.add_class("suggested-action")

        button.set_label(label)
        button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        button.set_sensitive(sensitive)
        self.cancel_button.set_sensitive(state not in ("queued", "running"))

    def _return_after_success(self):
        self._return_source = None
        if self.get_parent() is not None:
            self.parent.close_package_view(crossfade=True)
        return False
