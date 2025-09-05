import os
import threading

from . import cli_helper, script_runner
from .gtk_common import GLib, Gtk


class WaitDialog(Gtk.Dialog):
	def __init__(self, parent, message="Waiting..."):
		super().__init__(title=_("Waiting..."), transient_for=parent, modal=True)
		self.set_default_size(128, 48)
		self.set_resizable(False)

		box = self.get_content_area()
		h = Gtk.Box(spacing=12)
		h.set_border_width(12)
		box.add(h)

		self.spinner = Gtk.Spinner()
		self.spinner.set_size_request(32, 32)
		h.pack_start(self.spinner, False, False, 0)

		# Use translated message if default, otherwise use provided message
		if message == "Waiting...":
			message = _("Waiting...")
		label = Gtk.Label(label=message)
		label.set_xalign(0)
		h.pack_start(label, True, True, 0)

		self.show_all()

	def start(self):
		self.spinner.start()
		self.show_all()

	def stop(self):
		self.destroy()


class MenuButton(Gtk.MenuButton):
	def __init__(self, script_runner: script_runner.ScriptRunner):
		super().__init__()
		self.script_runner = script_runner
		self.results = []
		self._temp_sh = '/tmp/._temp_script.sh'
		self.dlg = None

		pop = Gtk.Popover()

		vbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
		vbox.set_border_width(6)

		load_manifest = Gtk.ModelButton(label=_("load_manifest"))
		load_manifest.set_image(Gtk.Image.new_from_icon_name("document-open", Gtk.IconSize.MENU))
		load_manifest.connect("clicked", self.__on_load_manifest)

		vbox.pack_start(load_manifest, True, True, 0)
		vbox.show_all()

		pop.add(vbox)

		self.set_popover(pop)

	def __on_load_manifest(self, widget):
		scripts_name = self.__file_choose()

		if scripts_name is None:
			return

		threading.Thread(
			target=self.__wrapper_t,
			args=(scripts_name,)
		).start()

	def __file_choose(self):
		scripts_name = []

		dialog = Gtk.FileChooserDialog(
			title=_("choose_manifest_title"),
			parent=self.get_toplevel(),
			action=Gtk.FileChooserAction.OPEN,
		)

		dialog.add_buttons(
			Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, _("select_button"), Gtk.ResponseType.OK
		)

		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			self.dlg = WaitDialog(self.get_toplevel(), _("loading_manifest_message"))
			self.dlg.start()
			scripts_name = cli_helper.load_manifest(dialog.get_filename())
		dialog.destroy()

		return scripts_name

	def __wrapper_t(self, scripts_name):
		packages_to_install = []
		flatpaks_to_install = []

		for script_name in scripts_name:
			script_info = cli_helper.find_script_by_name(script_name)
			if script_info is None:
				if cli_helper.check_package_exists(script_name):
					packages_to_install.append(script_name)
					continue

				elif cli_helper.check_flatpak_exists(script_name):
					flatpaks_to_install.append(script_name)
					continue
			else:
				self.results.append(script_info)

		if packages_to_install or flatpaks_to_install:
			self.results.append({'name': _("packages_flatpaks"),'path': self._temp_sh, 'is_script': True})
			self.__temp_script(packages_to_install, flatpaks_to_install)

		GLib.idle_add(self.__update_results)

	def __update_results(self):
		self.dlg is not None and self.dlg.stop()

		def completion_handler():
			if os.path.exists(self._temp_sh):
				os.remove(self._temp_sh)

		self.script_runner.run_scripts_sequentially(scripts_list=self.results, on_completion=completion_handler)

	def __temp_script(self, packages, flatpaks):
		lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs', 'linuxtoys.lib')

		script_content = f'''#!/bin/bash
source "{lib_path}"

_packages=("{' '.join(packages)}")
[ "${{#_packages[@]}}" -eq 0 ] || {{ sudo_rq; _install_; }}

_flatpaks=("{' '.join(flatpaks)}")
_flatpak_
'''
		with open(self._temp_sh, 'w+') as f:
			f.write(script_content)
