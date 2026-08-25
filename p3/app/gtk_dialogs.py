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

    kwargs = {
        "flags": 0,
        "message_type": message_type,
        "buttons": Gtk.ButtonsType.NONE,
        "text": title,
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