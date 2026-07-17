from __future__ import annotations
from typing import Iterable, Optional, Tuple
from .gtk_common import Gtk, get_toplevel_window

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