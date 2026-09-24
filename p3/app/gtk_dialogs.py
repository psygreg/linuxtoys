from __future__ import annotations
from typing import Iterable, Optional, Tuple
from .gtk_common import Gtk, get_toplevel_window
from .lang_utils import create_translator

DialogButton = Tuple[str, Gtk.ResponseType]

def run_message_dialog(
    parent: Optional[Gtk.Widget],
    *,
    title: str,
    secondary_text: str = "",
    message_type: Gtk.MessageType = Gtk.MessageType.INFO,
    buttons: Optional[Iterable[DialogButton]] = None,
    default_response: Optional[Gtk.ResponseType] = None,
) -> Gtk.ResponseType:
    """Create, run, and destroy a standard application message dialog."""
    parent_window = get_toplevel_window(parent) if parent else None

    # Dialogs triggered from non-widget helpers (such as Antenna) may not
    # receive a parent explicitly. Tie them to the application's active
    # window instead of creating an unowned top-level window.
    if parent_window is None:
        application = Gtk.Application.get_default()
        if application is not None:
            parent_window = application.get_active_window()

    kwargs = {
        "flags": 0,
        "message_type": message_type,
        "buttons": Gtk.ButtonsType.NONE,
        "text": title,
        "modal": True,
    }

    if parent_window is not None:
        kwargs["transient_for"] = parent_window

    dialog = Gtk.MessageDialog(**kwargs)

    if secondary_text:
        dialog.format_secondary_text(secondary_text)

    for label, response in buttons or []:
        dialog.add_button(label, response)

    if default_response is not None:
        dialog.set_default_response(default_response)

    try:
        return dialog.run()
    finally:
        dialog.destroy()

def show_information(
    parent: Optional[Gtk.Widget],
    *,
    title: str,
    message: str,
) -> None:
    run_message_dialog(
        parent,
        title=title,
        secondary_text=message,
        message_type=Gtk.MessageType.INFO,
        buttons=[("OK", Gtk.ResponseType.OK)],
        default_response=Gtk.ResponseType.OK,
    )

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

def run_startup_recommendations_dialog(parent, translations, recommendations):
    """Ask whether to install recommended host integration features.

    Returns ``(accepted, dont_remind)``. ``recommendations`` contains stable
    internal IDs (flathub, rpmfusion, multilib), while all visible text comes
    from translation keys.
    """
    parent_window = get_toplevel_window(parent) if parent else None
    dialog = Gtk.Dialog(
        title=translations.get(
            "startup_recommendations_title", "Recommended system setup"
        ),
        transient_for=parent_window,
        modal=True,
    )
    dialog.add_button(
        translations.get("startup_recommendations_not_now", "Not now"),
        Gtk.ResponseType.CANCEL,
    )
    dialog.add_button(
        translations.get("startup_recommendations_install", "Install recommended"),
        Gtk.ResponseType.OK,
    )
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.set_resizable(False)

    content = dialog.get_content_area()
    content.set_spacing(12)
    content.set_border_width(18)

    intro = Gtk.Label(
        label=translations.get(
            "startup_recommendations_message",
            "LinuxToys recommends enabling the following features for better software availability on this system:",
        )
    )
    intro.set_xalign(0)
    intro.set_line_wrap(True)
    intro.set_max_width_chars(64)
    content.pack_start(intro, False, False, 0)

    names = {
        "flathub": translations.get("startup_recommendation_flathub", "Flathub"),
        "rpmfusion": translations.get("startup_recommendation_rpmfusion", "RPM Fusion"),
        "multilib": translations.get("startup_recommendation_multilib", "Multilib"),
    }
    features = Gtk.Label(
        label="\n".join(f"• {names[item]}" for item in recommendations if item in names)
    )
    features.set_xalign(0)
    features.set_selectable(False)
    content.pack_start(features, False, False, 0)

    dont_remind = Gtk.CheckButton.new_with_label(
        translations.get(
            "startup_recommendations_dont_remind", "Don't remind me again"
        )
    )
    content.pack_start(dont_remind, False, False, 0)

    dialog.show_all()
    try:
        response = dialog.run()
        return response == Gtk.ResponseType.OK, dont_remind.get_active()
    finally:
        dialog.destroy()
