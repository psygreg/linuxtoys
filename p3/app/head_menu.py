from .gtk_common import Gtk, GLib
from . import cli_helper
from . import script_runner
import threading


class MenuButton(Gtk.MenuButton):
	def __init__(self, script_runner: script_runner.ScriptRunner):
		super().__init__()
		self.script_runner = script_runner
		self.results = []

		_menu = Gtk.Menu()
		_menu.set_halign(Gtk.Align.END)

		load_manifest = Gtk.MenuItem(label="Load Manifest")
		load_manifest.connect("activate", self.__on_load_manifest)

		_menu.append(load_manifest)
		_menu.show_all()

		self.set_popup(_menu)

	def __on_load_manifest(self, widget):
		scripts_name = self.__file_choose()

		if scripts_name is None:
			return

		thread = threading.Thread(
			target=self.__wrapper_t,
			args=(scripts_name,)
		).start()

	def __file_choose(self):
		scripts_name = []

		dialog = Gtk.FileChooserDialog(
			title="Please choose your Manifest",
			parent=self.get_toplevel(),
			action=Gtk.FileChooserAction.OPEN,
		)

		dialog.add_buttons(
			Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.OK
		)

		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			scripts_name = cli_helper.load_manifest(dialog.get_filename())
		dialog.destroy()

		return scripts_name

	def __wrapper_t(self, scripts_name):
		for script_name in scripts_name:
			script_info = cli_helper.find_script_by_name(script_name)
			script_info is not None and self.results.append(script_info)

		GLib.idle_add(self.__update_results)

	def __update_results(self):
		self.script_runner.run_scripts_sequentially(scripts_list=self.results)
