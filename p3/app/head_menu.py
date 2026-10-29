from .gtk_common import Gdk, Gtk, GLib, resolve_symbolic_icon
from . import manifest_helper
from . import language_selector
from . import about_helper
from . import action_registry
from . import get_icon_path
from . import git_scripts_manager
from . import compat
from .lang_utils import (
    create_translator,
    get_automatic_updates,
    save_automatic_updates,
    get_automatic_error_reports,
    save_automatic_error_reports,
    get_mcp_server_enabled,
    save_mcp_server_enabled,
)
from .gtk_dialogs import WaitDialog
import threading
import asyncio
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
		hamburger_icon = Gtk.Image.new_from_icon_name(resolve_symbolic_icon("open-menu-symbolic"), Gtk.IconSize.BUTTON)
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
		
		# Add action registry button
		self.action_registry_item = Gtk.ModelButton(label=_("action_registry"))
		self.action_registry_item.set_image(Gtk.Image.new_from_icon_name("document-properties", Gtk.IconSize.MENU))
		self.action_registry_item.connect("clicked", self.__on_action_registry)

		self.update_scripts_item = Gtk.ModelButton(label=_("scripts_resync"))
		self.update_scripts_item.set_image(Gtk.Image.new_from_icon_name("view-refresh", Gtk.IconSize.MENU))
		self.update_scripts_item.connect("clicked", self.__on_update_scripts)
		
		# Add separator
		separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
		# Add auto error reports checkbox
		self.auto_error_reports = Gtk.CheckButton(label=_("auto_error_reports"))
		# Persisted like automatic updates: the MCP server can also toggle it.
		self.auto_error_reports.set_active(get_automatic_error_reports())
		self.auto_error_reports.connect("toggled", self.__on_auto_error_reports_toggled)

		# Translators: automatic_updates = "Automatic updates"
		auto_updates_label = _("autosysup")
		if auto_updates_label == "autosysup":
			auto_updates_label = "Automatic updates"
		self.auto_updates = Gtk.CheckButton(label=auto_updates_label)
		# GregOS ships LinuxToys inside its image and only updates with the image,
		# so the automatic-updates option is disabled and forced off there. Every
		# other host keeps the stored preference.
		if compat.self_updates_disabled():
			self.auto_updates.set_active(False)
			self.auto_updates.set_sensitive(False)
		else:
			self.auto_updates.set_active(get_automatic_updates())
		self.auto_updates.connect("toggled", self.__on_auto_updates_toggled)

		# Opt-in MCP agent server. The toggle installs/enables the systemd
		# --user service (`linuxtoys-mcp.service`) that the app ships but never
		# enables on its own. When systemd user services are unavailable the
		# checkbox mirrors the stored preference only.
		mcp_label = _("mcp_agent_server")
		if mcp_label == "mcp_agent_server":
			mcp_label = "MCP Agent Server"
		self.mcp_server_toggle = Gtk.CheckButton(label=mcp_label)
		# GTK tooltips and nested popovers both open a separate surface, which
		# misplaces or fails inside this menu popover on Wayland. The hint is
		# a revealer inside the menu instead, shown while the pointer is over
		# the checkbox.
		self.mcp_server_tooltip_label = Gtk.Label(label=_("mcp_agent_server_tooltip"), xalign=0)
		self.mcp_server_tooltip_label.set_line_wrap(True)
		self.mcp_server_tooltip_label.set_max_width_chars(40)
		self.mcp_server_tooltip_label.set_margin_start(24)
		self.mcp_server_tooltip_label.get_style_context().add_class("dim-label")
		self.mcp_server_tooltip = Gtk.Revealer()
		self.mcp_server_tooltip.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
		self.mcp_server_tooltip.add(self.mcp_server_tooltip_label)
		self.mcp_server_toggle.add_events(
			Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK
		)
		self.mcp_server_toggle.connect("enter-notify-event", self.__on_mcp_hover)
		self.mcp_server_toggle.connect("leave-notify-event", self.__on_mcp_leave)
		self._mcp_applying = False
		# Fast preference first; the real service state lands on the checkbox
		# from a background probe (systemctl calls must not delay startup).
		self.mcp_server_toggle.set_active(get_mcp_server_enabled())
		self.mcp_server_toggle.connect("toggled", self.__on_mcp_toggled)
		threading.Thread(target=self.__mcp_state_probe, daemon=True).start()

		vbox.pack_start(self.load_manifest, True, True, 0)
		vbox.pack_start(self.language_select, True, True, 0)
		vbox.pack_start(self.about_item, True, True, 0)
		vbox.pack_start(self.action_registry_item, True, True, 0)
		vbox.pack_start(self.update_scripts_item, True, True, 0)
		vbox.pack_start(separator, False, False, 0)
		vbox.pack_start(self.auto_error_reports, False, False, 0)
		vbox.pack_start(self.auto_updates, False, False, 0)
		vbox.pack_start(self.mcp_server_toggle, False, False, 0)
		vbox.pack_start(self.mcp_server_tooltip, False, False, 0)
		vbox.show_all()

		pop.add(vbox)

		self.set_popover(pop)
		pop.connect("closed", self.__on_menu_closed)

	def __on_mcp_hover(self, widget, event):
		self.mcp_server_tooltip.set_reveal_child(True)
		return False

	def __on_mcp_leave(self, widget, event):
		self.mcp_server_tooltip.set_reveal_child(False)
		return False

	def __on_menu_closed(self, popover):
		self.mcp_server_tooltip.set_reveal_child(False)

	def refresh_menu_translations(self):
		"""Refresh menu items with new translations"""
		_ = create_translator()
		self.load_manifest.set_label(_("load_manifest"))
		self.language_select.set_label(_("select_language"))
		self.about_item.set_label(_("about_title"))
		self.action_registry_item.set_label(_("action_registry"))
		self.update_scripts_item.set_label(_("scripts_resync"))
		self.auto_error_reports.set_label(_("auto_error_reports"))
		auto_updates_label = _("autosysup")
		self.auto_updates.set_label("Automatic updates" if auto_updates_label == "autosysup" else auto_updates_label)
		mcp_label = _("mcp_agent_server")
		self.mcp_server_toggle.set_label("MCP Agent Server" if mcp_label == "mcp_agent_server" else mcp_label)
		self.mcp_server_tooltip_label.set_label(_("mcp_agent_server_tooltip"))

	def __mcp_initial_state(self):
		"""Service enablement is the source of truth; the stored preference is
		only the fallback when systemd user services cannot be queried."""
		try:
			from . import mcp_server
			status = mcp_server.service_status()
			if status.get("available"):
				return bool(status.get("enabled"))
		except Exception:
			pass
		return get_mcp_server_enabled()

	def __mcp_state_probe(self):
		state = self.__mcp_initial_state()
		GLib.idle_add(self.__mcp_state_probe_done, state)

	def __mcp_state_probe_done(self, state):
		if not self.mcp_server_toggle.get_sensitive() or self.mcp_server_toggle.get_active() == state:
			return False
		self._mcp_applying = True
		self.mcp_server_toggle.set_active(state)
		self._mcp_applying = False
		return False

	def __on_mcp_toggled(self, widget):
		"""Install/enable or disable the MCP agent server systemd service."""
		if self._mcp_applying:
			return  # Programmatic state restore, not a user action.
		self._mcp_applying = True
		is_enabled = widget.get_active()
		save_mcp_server_enabled(is_enabled)
		widget.set_sensitive(False)
		threading.Thread(
			target=self.__mcp_service_worker,
			args=(is_enabled,),
			daemon=True,
		).start()

	def __mcp_service_worker(self, is_enabled):
		error = ""
		try:
			from . import mcp_server
			ok, message = mcp_server.apply_service_state(is_enabled, session_env=os.environ)
			if not ok:
				error = message
			elif is_enabled:
				# Noninteractive skill fetch: primary path is `bun x skills add`
				# through the hidden AppStream PTY (queued, serialized, visible
				# in the queue view); the script itself ends with an offline
				# bundled-copy fallback when bun or every source is unavailable.
				runner = getattr(self.parent_window, "_appstream_runner", None)
				if runner is not None:
					try:
						runner.enqueue_skill_install(mcp_server.skill_install_script())
					except Exception as skill_error:
						print(f"MCP skill install could not be queued: {skill_error}")
						mcp_server.install_agent_skill()
				else:
					mcp_server.install_agent_skill()
		except Exception as exc:
			error = str(exc)
		GLib.idle_add(self.__mcp_service_done, is_enabled, error)

	def __mcp_service_done(self, is_enabled, error):
		self.mcp_server_toggle.set_sensitive(True)
		if error:
			_ = create_translator()
			dialog = Gtk.MessageDialog(
				transient_for=self.get_toplevel(),
				flags=0,
				message_type=Gtk.MessageType.ERROR,
				buttons=Gtk.ButtonsType.OK,
				text=_("mcp_service_failed_title"),
			)
			dialog.format_secondary_text(error)
			dialog.run()
			dialog.destroy()
			# Reflect the actual state after a failed transition, without
			# re-triggering the service operation.
			actual = self.__mcp_initial_state()
			if self.mcp_server_toggle.get_active() != actual:
				self.mcp_server_toggle.handler_block_by_func(self.__on_mcp_toggled)
				self.mcp_server_toggle.set_active(actual)
				self.mcp_server_toggle.handler_unblock_by_func(self.__on_mcp_toggled)
		self._mcp_applying = False
		return False

	def __on_auto_error_reports_toggled(self, widget):
		"""Handle auto error reports checkbox toggle"""
		is_enabled = widget.get_active()
		# Persist the preference and apply it to the current window.
		save_automatic_error_reports(is_enabled)
		if self.parent_window:
			self.parent_window.auto_error_reports_enabled = is_enabled

	def __on_auto_updates_toggled(self, widget):
		"""Persist automatic updates and notify the main window."""
		is_enabled = widget.get_active()
		# GregOS self-updates only with its system image; never persist an enable.
		if compat.self_updates_disabled():
			is_enabled = False
		save_automatic_updates(is_enabled)
		if self.parent_window:
			self.parent_window.set_automatic_updates_enabled(is_enabled)

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

	def __on_action_registry(self, widget):
		"""Handle action registry menu item click"""
		action_registry.show_action_registry_dialog(self.parent_window)

	def __on_update_scripts(self, widget):
		"""Force an immediate update of the cached scripts repository."""
		_ = create_translator()
		self.update_scripts_item.set_sensitive(False)
		self.dlg = WaitDialog(self.get_toplevel(), _("scripts_init_updating"))
		self.dlg.start()
		threading.Thread(target=self.__update_scripts_thread, daemon=True).start()

	def __update_scripts_thread(self):
		git_scripts_manager.force_update_scripts()
		GLib.idle_add(self.__close_wait_dialog)

	def __close_wait_dialog(self):
		if self.dlg is not None:
			self.dlg.stop()
			self.dlg = None

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
			scripts_name = manifest_helper.load_manifest(dialog.get_filename())
		dialog.destroy()

		return scripts_name

	def __wrapper_t(self, scripts_name):
		_ = create_translator()
		packages_to_install = []
		flatpaks_to_install = []
		potential_flatpaks = []
		items_to_check = []

		for script_name in scripts_name:
			script_info = manifest_helper.find_script_by_name(script_name)
			if script_info is not None:
				self.results.append(script_info)
			else:
				# If not a script, identify if it's a potential flatpak or package
				if script_name.count('.') >= 2:
					potential_flatpaks.append(script_name)
				else:
					items_to_check.append(script_name)

		# Check flatpaks asynchronously
		if potential_flatpaks:
			exists_results = asyncio.run(manifest_helper.check_flatpaks_async(potential_flatpaks))
			for name, exists in zip(potential_flatpaks, exists_results):
				if exists:
					flatpaks_to_install.append(name)
				else:
					# If not a flatpak, check if it's a package
					if manifest_helper.check_package_exists(name):
						packages_to_install.append(name)

		# Check other items for packages
		for name in items_to_check:
			if manifest_helper.check_package_exists(name):
				packages_to_install.append(name)

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
			deps = asyncio.run(self.parent_window._process_needed_scripts(self.results))
			self.parent_window.open_term_view(deps)

	def __temp_script(self, packages, flatpaks):
		lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs', 'linuxtoys.bash')

		script_content = '''#!/bin/bash
source "''' + lib_path + '''"

_packages=("''' + ' '.join(packages) + '''")
[ "${#_packages[@]}" -eq 0 ] || { sudo_rq; _install_; }

_flatpaks=("''' + ' '.join(flatpaks) + '''")
_flatpak_
'''
		with open(self._temp_sh, 'w+') as f:
			f.write(script_content)