import os
import re
import sys
import webbrowser

from ..gtk_common import Gdk, GLib, Gtk, Pango

from . import __version__


class DialogBase(Gtk.MessageDialog):
    def __init__(self, parent, title, message, buttons, message_type):
        super().__init__(
            title=title,
            parent=parent,
            flags=0,
            buttons=Gtk.ButtonsType.NONE,
            message_type=message_type,
            modal=True,
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
            parent,
            "Update complete!",
            "<b>Restart the app to access the newest features and improvements.</b>",
            [("Restart", Gtk.ResponseType.OK), ("Cancel", Gtk.ResponseType.CANCEL)],
            Gtk.MessageType.OTHER,
        )

    def _on_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            self.destroy()
            os.execv(sys.executable, [sys.executable, *sys.argv])
        elif response_id == Gtk.ResponseType.CANCEL:
            self.destroy()


class DialogError(DialogBase):
    def __init__(self, parent, error_message):
        super().__init__(
            parent,
            "Error",
            f"<b>An error occurred during the update process.</b>\n{error_message}",
            [("OK", Gtk.ResponseType.OK)],
            Gtk.MessageType.ERROR,
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
        self.changelog = changelog or {"tag_name": "", "body": ""}
        self.parent = parent

        self.add_button(
            "Install Update", Gtk.ResponseType.OK
        ).get_style_context().add_class("suggested-action")
        self.add_button("Ignore", Gtk.ResponseType.NO)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_start(18)
        vbox.set_margin_end(18)
        vbox.set_margin_top(14)
        vbox.set_margin_bottom(12)

        self._labels = [
            f"<b>A new version {self.changelog.get('tag_name', '0.0.0')} of LinuxToys is available.</b>",
            f"Current version: <b>{__version__}</b>",
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
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_left_margin(12)
        self.textview.set_right_margin(12)
        self.textview.set_top_margin(10)
        self.textview.set_bottom_margin(10)
        self.textview.set_pixels_above_lines(2)
        self.textview.set_pixels_below_lines(2)

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

    def _restart_after_update(self):
        marker = "/tmp/.self_update_lt_complete"
        if not os.path.exists(marker):
            return True

        try:
            os.remove(marker)
        except OSError:
            pass

        os.execv(sys.executable, [sys.executable, *sys.argv])
        return False

    def _run_process(self):
        self.destroy()
        try:
            marker = "/tmp/.self_update_lt_complete"
            try:
                os.remove(marker)
            except FileNotFoundError:
                pass

            with open("/tmp/.self_update_lt", "w") as f:
                script_content = f"""#!/bin/bash
source "$SCRIPT_DIR/libs/linuxtoys.lib"
sudo_rq
curl -fsSL https://linux.toys/install.sh | bash && touch {marker!r}
"""
                f.write(script_content)

            os.chmod("/tmp/.self_update_lt", 0o700)
            GLib.timeout_add(500, self._restart_after_update)

            self.parent.open_term_view(
                [
                    {
                        "icon": "linuxtoys.svg",
                        "name": "Update LinuxToys",
                        "description": "Update to new version of LinuxToys.",
                        "repo": "https://github.com/psygreg/linuxtoys/releases",
                        "path": "/tmp/.self_update_lt",
                        "self_update": True,
                        "is_script": True,
                        "auto_run": True,
                    }
                ]
            )
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
            "link" in t.get_property("name") for t in tags if t.get_property("name")
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
        """Render common GitHub release-note Markdown in a Gtk.TextBuffer.

        This deliberately stays dependency-free. It supports headings, bold,
        italics, inline code, links, unordered and ordered lists, blockquotes,
        and horizontal rules. Unsupported Markdown remains readable as text.
        """
        buffer = Gtk.TextBuffer()
        self.link_tags.clear()

        tag_bold = buffer.create_tag("bold", weight=Pango.Weight.BOLD)
        tag_italic = buffer.create_tag("italic", style=Pango.Style.ITALIC)
        tag_code = buffer.create_tag(
            "code",
            family="monospace",
        )
        tag_quote = buffer.create_tag(
            "quote",
            style=Pango.Style.ITALIC,
            left_margin=18,
            foreground="#808080",
        )
        tag_list = buffer.create_tag("list", left_margin=18, indent=-12)
        tag_rule = buffer.create_tag("rule", foreground="#808080")

        heading_tags = {
            level: buffer.create_tag(
                f"heading-{level}",
                weight=Pango.Weight.BOLD,
                scale=max(1.0, 1.55 - ((level - 1) * 0.1)),
                pixels_above_lines=8 if level <= 2 else 5,
                pixels_below_lines=3,
            )
            for level in range(1, 7)
        }

        inline_pattern = re.compile(
            r"(`[^`]+`)"
            r"|(\[([^\]]+)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\))"
            r"|(\*\*([^*]+)\*\*)"
            r"|(__([^_]+)__)"
            r"|(\*([^*\n]+)\*)"
            r"|(?<!\w)_([^_\n]+)_(?!\w)"
        )

        def insert(text, *tags):
            if not text:
                return
            end_iter = buffer.get_end_iter()
            if tags:
                buffer.insert_with_tags(end_iter, text, *tags)
            else:
                buffer.insert(end_iter, text)

        def insert_inline(text, base_tags=()):
            pos = 0
            for match in inline_pattern.finditer(text):
                insert(text[pos:match.start()], *base_tags)

                if match.group(1):
                    insert(match.group(1)[1:-1], *base_tags, tag_code)
                elif match.group(2):
                    label = match.group(3)
                    url = match.group(4)
                    tag_link = buffer.create_tag(
                        f"link-{len(self.link_tags) + 1}",
                        foreground="#4169E1",
                        underline=Pango.Underline.SINGLE,
                    )
                    self.link_tags[tag_link] = url
                    insert(label, *base_tags, tag_link)
                elif match.group(5):
                    insert(match.group(6), *base_tags, tag_bold)
                elif match.group(7):
                    insert(match.group(8), *base_tags, tag_bold)
                elif match.group(9):
                    insert(match.group(10), *base_tags, tag_italic)
                else:
                    insert(match.group(11), *base_tags, tag_italic)

                pos = match.end()

            insert(text[pos:], *base_tags)

        for raw_line in str(md_text or "No changelog available.").splitlines():
            line = raw_line.rstrip()

            heading = re.match(r"^\s*(#{1,6})\s+(.+?)\s*#*\s*$", line)
            unordered = re.match(r"^(\s*)[-+*]\s+(.+)$", line)
            ordered = re.match(r"^(\s*)(\d+)[.)]\s+(.+)$", line)
            quote = re.match(r"^\s*>\s?(.*)$", line)

            if re.match(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$", line):
                insert("────────────────────────", tag_rule)
            elif heading:
                level = len(heading.group(1))
                insert_inline(heading.group(2), (heading_tags[level],))
            elif unordered:
                depth = min(len(unordered.group(1).expandtabs(4)) // 2, 4)
                insert(f"{'    ' * depth}• ", tag_list)
                insert_inline(unordered.group(2), (tag_list,))
            elif ordered:
                depth = min(len(ordered.group(1).expandtabs(4)) // 2, 4)
                insert(f"{'    ' * depth}{ordered.group(2)}. ", tag_list)
                insert_inline(ordered.group(3), (tag_list,))
            elif quote:
                insert_inline(quote.group(1), (tag_quote,))
            else:
                insert_inline(line)

            insert("\n")

        return buffer
