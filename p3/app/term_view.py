from .gtk_common import Gtk, GLib, Gdk, Vte, Pango, GdkPixbuf
from . import get_icon_path
import os


class InfosHead(Gtk.Box):
	def __init__(self):
		super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
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

		self.button_run = Gtk.Button(label=" Execute ")
		self.button_run.set_image(Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON))
		self.button_run.set_halign(Gtk.Align.START)
		self.button_run.set_size_request(125, 35)

		self.progress_bar = Gtk.ProgressBar()
		self.progress_bar.set_show_text(True)
		self.progress_bar.set_fraction(0.0)

		hbox_controls.pack_start(self.button_run, False, False, 0)
		hbox_controls.pack_start(self.progress_bar, True, True, 0)

		vbox_infos.pack_start(hbox_controls, False, False, 10)

	def _update_header_labels(self, script_info: list):
		_name = GLib.markup_escape_text(script_info.get('name', ''))
		_desc = GLib.markup_escape_text(script_info.get('description', ''))
		_repo = GLib.markup_escape_text(script_info.get('repo', ''))
		self.label_name.set_markup(f"<big><big><b>{_name}</b></big></big>")
		self.label_desc.set_markup(f"{_desc}")
		self.label_repo.set_markup(f"<a href='{_repo}'>{_repo}</a>")

		icon_value = script_info.get('icon')
		if icon_value:
			icon_path = get_icon_path(icon_value)
			if icon_path:
				pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 100, 100, True)
				self.icon_head.set_from_pixbuf(pixbuf)
			else:
				default_path = get_icon_path("local-script.svg")
				pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(default_path, 100, 100, True)
				self.icon_head.set_from_pixbuf(pixbuf)
		else:
			default_path = get_icon_path("local-script.svg")
			pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(default_path, 100, 100, True)
			self.icon_head.set_from_pixbuf(pixbuf)


class TermRunScripts(Gtk.Box):
	def __init__(self, scripts_infos: list, parent):
		super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		self.parent = parent
		self.script_queue = scripts_infos.copy()
		self.total_scripts = len(scripts_infos)
		self.scripts_executed = 0

		self.terminal = Vte.Terminal()
		self.terminal.connect("child-exited", self.on_child_exit)
		self.terminal.set_size(80, 24)

		self.vbox_main = InfosHead()

		self.vbox_main.button_run.connect("clicked", self.on_button_run_clicked)
		self.vbox_main.progress_bar.set_text(f"Waiting {self.scripts_executed}/{self.total_scripts}")

		self.vbox_main.pack_start(self.terminal, True, True, 0)

		self.set_border_width(12)
		self.add(self.vbox_main)

		if self.script_queue:
			self.vbox_main._update_header_labels(self.script_queue[0])

	def on_button_run_clicked(self, widget):
		self.vbox_main.progress_bar.set_text(f"Running {self.scripts_executed}/{self.total_scripts}")
		self.vbox_main.button_run.set_label(" Running ")
		self._run_next_script()

	def on_child_exit(self, term, status):
		self.scripts_executed += 1
		progress = self.scripts_executed / self.total_scripts
		self.vbox_main.progress_bar.set_fraction(progress)
		self.vbox_main.progress_bar.set_text(f"Running {self.scripts_executed}/{self.total_scripts}")
		self._run_next_script()

	def _run_next_script(self):
		if not self.script_queue:
			self.vbox_main.button_run.set_label(" Done ")
			self.vbox_main.button_run.set_image(Gtk.Image.new_from_icon_name("emblem-ok-symbolic", Gtk.IconSize.BUTTON))
			self.vbox_main.progress_bar.set_text("Done")
			self.vbox_main.button_run.connect("clicked", self.on_done_clicked)

			self.vbox_main.button_run.set_sensitive(True)
			return

		current_script = self.script_queue.pop(0)
		self.vbox_main._update_header_labels(current_script)

		script_path = current_script.get('path', 'true')
		script_dir = str(os.path.join(os.path.dirname(os.path.dirname(__file__))))

		self.terminal.spawn_async(
			Vte.PtyFlags.DEFAULT,
			None,
			["/bin/bash", "-c", f"{script_path}"],
			[f'SCRIPT_DIR={script_dir}'],
			GLib.SpawnFlags.DO_NOT_REAP_CHILD,
			None, None, -1, None, None
		)

		self.vbox_main.button_run.set_sensitive(False)

	def on_done_clicked(self, button):
		self.parent.set_focus(None)
		self.parent.on_back_button_clicked(None)