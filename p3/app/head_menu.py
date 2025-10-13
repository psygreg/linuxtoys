from .gtk_common import Gtk, GLib
from . import cli_helper
from . import language_selector
from . import about_helper
from . import get_icon_path
from .lang_utils import create_translator
import threading
import os


class InputDialog(Gtk.MessageDialog):
	def __init__(self, parent):
		# Initialize without default buttons and with OTHER message type to avoid default icons
		super().__init__(parent=parent, flags=0, buttons=Gtk.ButtonsType.NONE, message_type=Gtk.MessageType.OTHER)
		
		# Create translator
		_ = create_translator()
		
		self.set_title("Input")
		self.set_decorated(False)
		
		# Hide the icon by setting an empty image
		empty_image = Gtk.Image()
		self.set_image(empty_image)

		# Add custom buttons using our translation system
		self.add_button(_('cancel_btn_label'), Gtk.ResponseType.CANCEL)
		ok_button = self.add_button(_('ok_btn_label'), Gtk.ResponseType.OK)
		
		# Set OK button as default
		ok_button.set_can_default(True)
		ok_button.grab_default()

		content_area = self.get_content_area()

		main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
		content_area.add(main_box)

		# Simple prompt label with extra bold formatting
		prompt_label = Gtk.Label()
		prompt_label.set_markup(f"<span weight='ultrabold' size='large'>{_('script_name_prompt')}</span>")
		prompt_label.set_margin_bottom(10)
		main_box.pack_start(prompt_label, False, False, 0)

		# Entry field without placeholder text
		self.entry_name = Gtk.Entry()
		main_box.pack_start(self.entry_name, False, False, 0)
		
		# Connect Enter key to OK response
		self.entry_name.connect("activate", lambda widget: self.response(Gtk.ResponseType.OK))

		main_box.set_margin_start(35)
		main_box.set_margin_bottom(15)
		main_box.set_margin_end(35)

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
	def __init__(self, parent_window=None, on_language_changed=None):
		super().__init__()
		_ = create_translator()
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

		self.about_item = Gtk.ModelButton(label=_("about_title"))
		# Try to load LinuxToys icon, fallback to applications-utilities
		try:
			icon_path = get_icon_path("linuxtoys.svg")
			if icon_path:
				# For SVG files in menu, use smaller size
				from .gtk_common import GdkPixbuf
				try:
					pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
						icon_path, 16, 16, True
					)
					about_icon = Gtk.Image.new_from_pixbuf(pixbuf)
				except Exception:
					# Fallback if SVG loading fails
					about_icon = Gtk.Image.new_from_icon_name("applications-utilities", Gtk.IconSize.MENU)
			else:
				raise FileNotFoundError("linuxtoys.svg not found")
		except Exception:
			about_icon = Gtk.Image.new_from_icon_name("applications-utilities", Gtk.IconSize.MENU)
		
		self.about_item.set_image(about_icon)
		self.about_item.connect("clicked", self.__on_about)

		vbox.pack_start(self.load_manifest, True, True, 0)
		vbox.pack_start(self.language_select, True, True, 0)
		vbox.pack_start(self.about_item, True, True, 0)
		vbox.show_all()

		pop.add(vbox)

		self.set_popover(pop)

	def refresh_menu_translations(self):
		"""Refresh menu items with new translations"""
		_ = create_translator()
		self.load_manifest.set_label(_("load_manifest"))
		self.language_select.set_label(_("select_language"))
		self.about_item.set_label(_("about_title"))

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

	def __on_about(self, widget):
		"""Handle about menu item click"""
		if self.parent_window and hasattr(self.parent_window, 'translations'):
			about_helper.show_about_dialog(self.parent_window, self.parent_window.translations)

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

		if self.results:
			self.parent_window.open_term_view(self.results)

	def __temp_script(self, packages, flatpaks):
		lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs', 'linuxtoys.lib')

		script_content = '''#!/bin/bash
source "''' + lib_path + '''"

_packages=("''' + ' '.join(packages) + '''")
[ "${#_packages[@]}" -eq 0 ] || { sudo_rq; _install_; }

_flatpaks=("''' + ' '.join(flatpaks) + '''")
_flatpak_
'''
		with open(self._temp_sh, 'w+') as f:
			f.write(script_content)