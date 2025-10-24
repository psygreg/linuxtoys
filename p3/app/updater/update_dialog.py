import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango, Gdk, GLib
import webbrowser, json, re, subprocess, threading, sys, os
from . import __version__


class DialogBase(Gtk.MessageDialog):
    def __init__(self, parent, title, message, buttons, message_type):
        super().__init__(
            title=title,
            parent=parent,
            flags=0,
            buttons=Gtk.ButtonsType.NONE,
            message_type=message_type,
            modal=True
        )
        self.set_markup(message)
        self.add_buttons(buttons)
        self.connect("response", self._on_response)
        self.show_all()

    def add_buttons(self, buttons):
        for button_text, response_type in buttons:
            button = self.add_button(button_text, response_type)
            if response_type == Gtk.ResponseType.OK:
                button.get_style_context().add_class("suggested-action")

    def _on_response(self, dialog, response_id):
        raise NotImplementedError("Response Not Implemented")


class DialogRestart(DialogBase):
    def __init__(self, parent):
        super().__init__(
            parent, "Update complete!",
            "<b>Restart the app to access the newest features and improvements.</b>",
            [("Restart", Gtk.ResponseType.OK), ("Cancel", Gtk.ResponseType.CANCEL)],
            Gtk.MessageType.OTHER
        )

    def _on_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            self.close()
            os.execv(sys.executable, ["python"] + sys.argv)
        elif response_id == Gtk.ResponseType.CANCEL:
            self.destroy()


class DialogError(DialogBase):
    def __init__(self, parent, error_message):
        super().__init__(
            parent, "Error",
            f"<b>An error occurred during the update process.</b>\n{error_message}",
            [("OK", Gtk.ResponseType.OK)],
            Gtk.MessageType.ERROR
        )

    def _on_response(self, dialog, response_id):
        self.destroy()


class UpdateDialog(Gtk.Dialog):
    def __init__(self, changelog, parent):
        super().__init__(title="Update Available")
        self.set_default_size(450, 350)
        self.set_decorated(True)
        self.set_property("skip-taskbar-hint", True)
        self.link_tags = {}
        self.changelog = changelog or "{'tag_name': '', 'body': ''}"
        self.parent = parent

        self.add_button("Install Update", Gtk.ResponseType.OK).get_style_context().add_class("suggested-action")
        self.add_button("Ignore", Gtk.ResponseType.NO)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._labels = [
            f"<b>A new version {self.changelog.get('tag_name', '0.0.0')} of LinuxToys is available.</b>",
            f"Current version: <b>{__version__}</b>"
        ]

        for _l in self._labels:
            _label = Gtk.Label()
            _label.set_use_markup(True)
            _label.set_markup(f"{_l}")
            _label.set_line_wrap(True)
            _label.set_halign(Gtk.Align.CENTER)
            _label.get_style_context()

            vbox.pack_start(_label, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_border_width(5)

        self.textview.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.textview.connect("button-release-event", self._on_event_after)
        self.textview.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.textview.connect("motion-notify-event", self._on_motion_notify)

        self._update_buffer()

        scrolled.add(self.textview)

        vbox.pack_start(scrolled, True, True, 10)

        self.get_content_area().add(vbox)

        self.connect("response", self._on_response)
        self.show_all()

    def _run_process(self):
        self.destroy()
        try:
            with open("/tmp/.self_update_lt", 'w') as f:
                script_content = '''#!/bin/bash\nsource "$SCRIPT_DIR/libs/linuxtoys.lib"\nsudo_rq\ncurl -fsSL https://linux.toys/install.sh | sh\n'''
                f.write(script_content)

            self.parent.open_term_view([{
                'icon': "linuxtoys.svg",
                'name': "Update LinuxToys",
                'description': "Update to new version of LinuxToys.",
                'repo': "https://github.com/psygreg/linuxtoys/releases",
                'path': "/tmp/.self_update_lt",
                'self_update': True,
                'is_script': True
            }])
        except Exception as e:
            DialogError(self.parent, str(e)).show()

    def _on_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            GLib.idle_add(self._run_process)
            self.destroy()

        elif response_id == Gtk.ResponseType.NO:
            self.destroy()

    def _on_motion_notify(self, textview, event):
        x, y = textview.window_to_buffer_coords(
            Gtk.TextWindowType.TEXT, int(event.x), int(event.y)
        )
        success, iter_at_location = textview.get_iter_at_location(x, y)
        if not success:
            textview.get_window(Gtk.TextWindowType.TEXT).set_cursor(None)
            return False

        tags = iter_at_location.get_tags()
        over_link = any(
            "link" in t.get_property("name")
            for t in tags
            if t.get_property("name")
        )

        window = textview.get_window(Gtk.TextWindowType.TEXT)
        display = Gdk.Display.get_default()
        if over_link:
            cursor = Gdk.Cursor.new_for_display(display, Gdk.CursorType.HAND2)
            window.set_cursor(cursor)
        else:
            window.set_cursor(None)

        return False

    def _on_event_after(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE and event.button == 1:
            x, y = self.textview.window_to_buffer_coords(
                Gtk.TextWindowType.TEXT, int(event.x), int(event.y)
            )
            iter_at_location = self.textview.get_iter_at_location(x, y)[1]
            for tag in iter_at_location.get_tags():
                if tag in self.link_tags:
                    url = self.link_tags[tag]
                    webbrowser.open(url)
                    return True
            return False

    def _update_buffer(self):
        body_text = self.changelog.get("body", "No changelog available.")
        buff = self._markdown_to_textbuffer(body_text)
        self.textview.set_buffer(buff)

    def _markdown_to_textbuffer(self, md_text):
        """
        Convert simplified Markdown to Gtk.TextBuffer with tags.
        Supports:
        - **bold**
        - _italic_
        - - lists
        - [link](url) -> clickable
        """
        buffer = Gtk.TextBuffer()

        # Create tags
        tag_bold = buffer.create_tag("bold", weight=Pango.Weight.BOLD)
        tag_italic = buffer.create_tag("italic", style=Pango.Style.ITALIC)
        links_counter = 0

        def insert_with_tag(text, tag=None):
            end_iter = buffer.get_end_iter()
            if tag:
                buffer.insert_with_tags(end_iter, text, tag)
            else:
                buffer.insert(end_iter, text)

        # Split by lines
        for line in md_text.splitlines():
            # Convert lists
            line = re.sub(r"^\s*[-*]\s+", "• ", line)

            pos = 0
            while pos < len(line):
                # Search for bold, italic, link
                m_bold = re.search(r"\*\*(.+?)\*\*", line[pos:])
                m_italic = re.search(r"_(.+?)_", line[pos:])
                m_link = re.search(r"\[([^\]]+)\]\(([^)]+)\)", line[pos:])
                m_title = re.search(r"^(#{1,6})\s*(.+)", line[pos:])

                matches = [m for m in [m_bold, m_italic, m_link, m_title] if m]

                if not matches:
                    insert_with_tag(line[pos:])
                    break

                m_first = min(matches, key=lambda x: x.start())
                start, end = m_first.span()
                insert_with_tag(line[pos : pos + start])

                if m_first == m_title:
                    tag_title = buffer.create_tag(
                        None,
                        weight=Pango.Weight.BOLD,
                        scale=float(2.0 - (len(m_title.group(1)) - 1) * 0.2),
                    )
                    insert_with_tag(m_title.group(2), tag_title)
                elif m_first == m_bold:
                    insert_with_tag(m_first.group(1), tag_bold)
                elif m_first == m_italic:
                    insert_with_tag(m_first.group(1), tag_italic)
                elif m_first == m_link:
                    links_counter += 1
                    tag_link = buffer.create_tag(
                        f"link-{links_counter}",
                        foreground="#4169E1",
                        underline=Pango.Underline.SINGLE,
                    )
                    self.link_tags[tag_link] = m_first.group(2)
                    insert_with_tag(m_first.group(1), tag_link)

                pos += end

            insert_with_tag("\n")

        return buffer
