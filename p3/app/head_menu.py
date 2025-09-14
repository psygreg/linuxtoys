from .gtk_common import Gtk, GLib
from . import cli_helper
from . import script_runner
from . import language_selector
from .lang_utils import create_translator
import threading
import os


class WaitDialog(Gtk.Dialog):
	def __init__(self, parent, message="Waiting..."):
		_ = create_translator()
		super().__init__(title=_("waiting_title"), transient_for=parent, modal=True)
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
			message = _("waiting_message")
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
	def __init__(self, script_runner: script_runner.ScriptRunner, parent_window=None, on_language_changed=None):
		super().__init__()
		_ = create_translator()
		self.script_runner = script_runner
		self.parent_window = parent_window
		self.on_language_changed = on_language_changed
		self.results = []
		self._temp_sh = '/tmp/._temp_script.sh'
		self.dlg = None

		# Set the hamburger menu icon (like GNOME)
		hamburger_icon = Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON)
		self.set_image(hamburger_icon)

		pop = Gtk.Popover()

		vbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
		vbox.set_border_width(6)

		self.load_manifest = Gtk.ModelButton(label=_("load_manifest"))
		self.load_manifest.set_image(Gtk.Image.new_from_icon_name("document-open", Gtk.IconSize.MENU))
		self.load_manifest.connect("clicked", self.__on_load_manifest)

		self.language_select = Gtk.ModelButton(label=_("select_language"))
		self.language_select.set_image(Gtk.Image.new_from_icon_name("preferences-desktop-locale", Gtk.IconSize.MENU))
		self.language_select.connect("clicked", self.__on_language_select)

		vbox.pack_start(self.load_manifest, True, True, 0)
		vbox.pack_start(self.language_select, True, True, 0)
		vbox.show_all()

		pop.add(vbox)

		self.set_popover(pop)

	def refresh_menu_translations(self):
		"""Refresh menu items with new translations"""
		_ = create_translator()
		self.load_manifest.set_label(_("load_manifest"))
		self.language_select.set_label(_("select_language"))

	def __on_language_select(self, widget):
		"""Handle language selection menu item click"""
		if self.parent_window:
			from . import lang_utils
			current_translations = lang_utils.load_translations()
			selector = language_selector.LanguageSelector(
				self.parent_window, 
				current_translations, 
				self.on_language_changed
			)
			selector.show_language_selector()

	def __on_load_manifest(self, widget):
		scripts_name = self.__file_choose()

		if scripts_name is None:
			return

		threading.Thread(
			target=self.__wrapper_t,
			args=(scripts_name,)
		).start()

	def __on_language_select(self, widget):
		"""Handle language selection menu item click"""
		if self.parent_window and hasattr(self.parent_window, 'translations'):
			selector = language_selector.LanguageSelector(
				self.parent_window,
				self.parent_window.translations,
				self.on_language_changed
			)
			selector.show_language_selector()

	def __file_choose(self):
		_ = create_translator()
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
		_ = create_translator()
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