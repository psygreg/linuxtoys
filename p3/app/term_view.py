from .gtk_common import Gtk, GLib, Gdk, Vte, Pango, GdkPixbuf
from . import get_icon_path
from . import dev_mode
import os, sys
from .updater.update_dialog import DialogRestart


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
		execute_label = self.translations.get('term_view_execute', ' Execute ')
		self.button_run = Gtk.Button(label=execute_label)
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
	def __init__(self, scripts_infos: list, parent, translations=None):
		super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		self.parent = parent
		self.translations = translations or {}
		self.script_queue = scripts_infos.copy()
		self.total_scripts = len(scripts_infos)
		self.scripts_executed = 0

		self.terminal = Vte.Terminal()
		self.terminal.connect("child-exited", self.on_child_exit)
		self.terminal.set_vexpand(True)

		self.vbox_main = InfosHead(translations)

		self.vbox_main.button_run.connect("clicked", self.on_button_run_clicked)
		# Use translatable waiting text
		waiting_text = self.translations.get('term_view_waiting', 'Waiting {current}/{total}')
		self.vbox_main.progress_bar.set_text(waiting_text.format(current=self.scripts_executed, total=self.total_scripts))

		self.vbox_main.pack_start(self.terminal, True, True, 0)

		self.set_border_width(12)
		self.add(self.vbox_main)

		if self.script_queue:
			self.vbox_main._update_header_labels(self.script_queue[0])

	def on_button_run_clicked(self, widget):
		# Use translatable running text
		running_text = self.translations.get('term_view_running', 'Running {current}/{total}')
		self.vbox_main.progress_bar.set_text(running_text.format(current=self.scripts_executed, total=self.total_scripts))
		running_label = self.translations.get('term_view_running_label', ' Running ')
		self.vbox_main.button_run.set_label(running_label)
		self._run_next_script()

	def on_child_exit(self, term, status):
		if self._self_update:
			DialogRestart(parent=self.get_toplevel()).show()

		self.scripts_executed += 1
		progress = self.scripts_executed / self.total_scripts
		self.vbox_main.progress_bar.set_fraction(progress)
		# Use translatable running text
		running_text = self.translations.get('term_view_running', 'Running {current}/{total}')
		self.vbox_main.progress_bar.set_text(running_text.format(current=self.scripts_executed, total=self.total_scripts))
		self._run_next_script()

	def _run_next_script(self):
		if not self.script_queue:
			# Use translatable done text
			done_label = self.translations.get('term_view_done', ' Done ')
			done_text = self.translations.get('term_view_done_text', 'Done')
			self.vbox_main.button_run.set_label(done_label)
			self.vbox_main.button_run.set_image(Gtk.Image.new_from_icon_name("emblem-ok-symbolic", Gtk.IconSize.BUTTON))
			self.vbox_main.progress_bar.set_text(done_text)
			self.vbox_main.button_run.connect("clicked", self.on_done_clicked)
			self.parent._script_running = False
			self.vbox_main.button_run.set_sensitive(True)
			return

		self.parent._script_running = True
		current_script = self.script_queue.pop(0)
		self.vbox_main._update_header_labels(current_script)

		script_path = current_script.get('path', 'true')
		if current_script.get('reboot') == "yes":
			self.parent.reboot_required = True

		self._self_update = current_script.get('self_update', False)

		script_dir = str(os.path.join(os.path.dirname(os.path.dirname(__file__))))

		shell_exec = ["/bin/bash", f"{script_path}"]
		if dev_mode.is_dev_mode_enabled():
			lib_path = os.path.dirname(__file__)
			shell_exec = [sys.executable, '-c', f'import sys; sys.path.append("{lib_path}"); import dev_mode; dev_mode.dry_run_script("{script_path}")']

		self.terminal.spawn_async(
			Vte.PtyFlags.DEFAULT,
			None,
			shell_exec,
			[f'SCRIPT_DIR={script_dir}'],
			GLib.SpawnFlags.DEFAULT,
			None, None, -1, None, None
		)

		self.vbox_main.button_run.set_sensitive(False)

	def on_done_clicked(self, button):
		self.parent.set_focus(None)
		self.parent.on_back_button_clicked(None)