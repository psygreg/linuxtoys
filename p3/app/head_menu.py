from .gtk_common import Gtk, GLib
from . import cli_helper
from . import script_runner
from . import language_selector
from .lang_utils import create_translator
import threading
import os, re


class InputDialog(Gtk.MessageDialog):
	def __init__(self, parent):
		super().__init__(parent=parent, flags=0, buttons=Gtk.ButtonsType.OK_CANCEL)
		self.set_title("Input")
		self.set_decorated(False)

		content_area = self.get_content_area()

		main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
		content_area.add(main_box)

		title_label = Gtk.Label(label="<span size='x-large'><b>Enter your script name</b></span>")
		title_label.set_use_markup(True)
		title_label.set_margin_bottom(5)
		main_box.pack_start(title_label, False, False, 0)

		icon_label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
		image = Gtk.Image.new_from_icon_name("text-x-script", Gtk.IconSize.MENU)
		label = Gtk.Label(label="Type your script name")
		icon_label_box.pack_start(image, False, False, 0)
		icon_label_box.pack_start(label, False, False, 0)
		main_box.pack_start(icon_label_box, False, False, 0)

		entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
		entry_label = Gtk.Label(label="Name:")
		self.entry_name = Gtk.Entry()
		self.entry_name.set_placeholder_text("Type your script name here...")

		entry_box.pack_start(entry_label, False, False, 0)
		entry_box.pack_start(self.entry_name, False, False, 0)

		main_box.set_margin_start(35)
		main_box.set_margin_bottom(15)
		main_box.set_margin_end(35)

		main_box.pack_start(entry_box, False, False, 0)

		self.show_all()

	def get_input(self):
		return self.entry_name.get_text()


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
		self.local_sh_dir = f'{os.environ['HOME']}/.local/linuxtoys/scripts/'

		# Set the hamburger menu icon (like GNOME)
		hamburger_icon = Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON)
		self.set_image(hamburger_icon)

		pop = Gtk.Popover()

		vbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
		vbox.set_border_width(6)

		self.load_manifest = Gtk.ModelButton(label=_("load_manifest"))
		self.load_manifest.set_image(Gtk.Image.new_from_icon_name("document-open", Gtk.IconSize.MENU))
		self.load_manifest.connect("clicked", self.__on_load_manifest)

		self.create_script = Gtk.ModelButton(label="Create Local Script")
		self.create_script.set_image(Gtk.Image.new_from_icon_name("text-x-script", Gtk.IconSize.MENU))
		self.create_script.connect("clicked", self.__on_create_local_sh_manifest)

		self.language_select = Gtk.ModelButton(label=_("select_language"))
		self.language_select.set_image(Gtk.Image.new_from_icon_name("preferences-desktop-locale", Gtk.IconSize.MENU))
		self.language_select.connect("clicked", self.__on_language_select)

		vbox.pack_start(self.load_manifest, True, True, 0)
		vbox.pack_start(self.create_script, True, True, 0)
		vbox.pack_start(self.language_select, True, True, 0)
		vbox.show_all()

		pop.add(vbox)

		self.set_popover(pop)

	def __on_create_local_sh_manifest(self, widget):
		dialog = InputDialog(parent=self.get_toplevel())

		if dialog.run() == Gtk.ResponseType.OK:
			sh_name = dialog.get_input()
			sh_filename = re.sub(r'[^a-z0-9-_]', '', sh_name.lower())
			sh_filename and self.__create_and_open_local_sh(filename=sh_filename, name=sh_name)

		dialog.destroy()

	def __create_and_open_local_sh(self, filename=None, name=None):
		os.makedirs(os.path.dirname(self.local_sh_dir), exist_ok=True)
		_template_local_script = f"""#!/bin/bash
# name: {name.capitalize()}
# version: 1.0
# description: Local Script
# icon: local-scripts.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${{langfile}}.lib"

# Check the docs in https://linuxtoys.luminhost.xyz/handbook.html for more...
		"""

		with open(f"{self.local_sh_dir}{filename}.sh", "w+") as f:
			f.write(_template_local_script)

		os.system(f'xdg-open {self.local_sh_dir}{filename}.sh')

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