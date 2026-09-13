import os
import re
import webbrowser

from .gtk_common import Gdk, Gtk, GdkPixbuf, Pango, GLib
from .term_header import InfosHead
from . import get_icon_path


class AppPageView(Gtk.Box):
    """Repository-entry details page with screenshots and install/support actions."""

    def __init__(self, script_info, parent, translations=None, on_install_callback=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.script_info = script_info
        self.parent = parent
        self.translations = translations or {}
        self.on_install_callback = on_install_callback
        self.screenshot_index = 0
        self.screenshot_stack = None
        self.screenshot_counter = None
        self._screenshot_autoplay_source = None
        self.connect("destroy", self._stop_screenshot_autoplay)

        self.header = InfosHead(self.translations, show_terminal_controls=False)
        self.header._update_header_labels(script_info)
        self._build_developer_line()
        self._build_actions()
        self.pack_start(self.header, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.set_margin_left(32)
        content.set_margin_right(32)
        content.set_margin_top(8)
        content.set_margin_bottom(24)
        scroller.add(content)

        screenshots = script_info.get("screenshots") or []
        if screenshots:
            content.pack_start(self._build_screenshot_viewer(screenshots), False, False, 0)

        long_description = str(script_info.get("long_description", "") or "").strip()
        if long_description:
            description = self._build_long_description(
                long_description,
                script_info.get("long_description_format") == "markdown",
            )
            content.pack_start(description, False, False, 0)

        self.pack_start(scroller, True, True, 0)
        self.set_border_width(12)

    def _build_long_description(self, text, is_markdown):
        if not is_markdown:
            description = Gtk.Label(label=text)
            description.set_halign(Gtk.Align.FILL)
            description.set_valign(Gtk.Align.START)
            description.set_xalign(0.0)
            description.set_line_wrap(True)
            description.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            description.set_selectable(False)
            description.set_can_focus(False)
            description.set_focus_on_click(False)
            return description

        # App-page Markdown is rendered directly from the source text instead of
        # going through Python-Markdown -> HTML -> TextBuffer. This deliberately
        # preserves source line structure: adjacent list items stay adjacent and
        # explicit blank lines stay blank lines, without HTML "loose list"
        # paragraphs introducing synthetic spacing.
        view = Gtk.TextView()
        view.set_halign(Gtk.Align.FILL)
        view.set_valign(Gtk.Align.START)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_editable(False)
        view.set_cursor_visible(False)
        view.set_can_focus(False)
        view.set_focus_on_click(False)
        view.set_accepts_tab(False)
        view.set_left_margin(0)
        view.set_right_margin(0)
        view.set_pixels_above_lines(0)
        view.set_pixels_below_lines(0)
        view.set_hexpand(True)

        view.set_buffer(self._markdown_to_textbuffer(text))

        # Gtk.TextView is scrollable and can otherwise claim spare vertical
        # allocation inside the page's viewport. Keep it height-for-content.
        # Measurement is deferred until GTK has completed wrapping/layout.
        view.set_vexpand(False)
        view.set_size_request(-1, 1)
        view._markdown_fit_source = None
        view.connect("size-allocate", self._schedule_markdown_view_height_fit)
        view.connect("map", self._schedule_markdown_view_height_fit)
        view.connect("button-release-event", self._on_markdown_link_clicked)
        return view

    def _markdown_to_textbuffer(self, md_text):
        """Render app-page Markdown directly into a Gtk.TextBuffer.

        Based on the update-dialog renderer, with app-page-specific restrained
        headings and recursive inline parsing so combinations such as
        ``**text with `code`**`` retain both styles.
        """
        buffer = Gtk.TextBuffer()

        tag_bold = buffer.create_tag("md-bold", weight=Pango.Weight.BOLD)
        tag_italic = buffer.create_tag("md-italic", style=Pango.Style.ITALIC)
        tag_code = buffer.create_tag("md-code", family="monospace")
        tag_strike = buffer.create_tag("md-strike", strikethrough=True)
        tag_heading = buffer.create_tag(
            "md-heading",
            weight=Pango.Weight.BOLD,
            scale=1.08,
        )
        tag_quote = buffer.create_tag(
            "md-quote",
            style=Pango.Style.ITALIC,
            left_margin=18,
            right_margin=8,
        )
        tag_list = buffer.create_tag("md-list", left_margin=18, indent=-12)
        tag_rule = buffer.create_tag("md-rule")

        inline_pattern = re.compile(
            r"(`[^`]+`)"
            r"|(\[([^\]]+)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\))"
            r"|(\*\*([^*]+)\*\*)"
            r"|(__([^_]+)__)"
            r"|(~~([^~]+)~~)"
            r"|(\*([^*\n]+)\*)"
            r"|(?<!\w)_([^_\n]+)_(?!\w)"
        )

        def insert(value, *tags):
            if not value:
                return
            end_iter = buffer.get_end_iter()
            if tags:
                buffer.insert_with_tags(end_iter, value, *tags)
            else:
                buffer.insert(end_iter, value)

        link_count = 0

        def insert_inline(value, base_tags=()):
            nonlocal link_count
            pos = 0
            for match in inline_pattern.finditer(value):
                insert(value[pos:match.start()], *base_tags)

                if match.group(1):
                    insert(match.group(1)[1:-1], *base_tags, tag_code)
                elif match.group(2):
                    label = match.group(3)
                    url = match.group(4)
                    link_count += 1
                    tag_link = buffer.create_tag(
                        f"md-link-{link_count}",
                        underline=Pango.Underline.SINGLE,
                    )
                    tag_link.set_data("url", url)
                    insert_inline(label, (*base_tags, tag_link))
                elif match.group(5):
                    insert_inline(match.group(6), (*base_tags, tag_bold))
                elif match.group(7):
                    insert_inline(match.group(8), (*base_tags, tag_bold))
                elif match.group(9):
                    insert_inline(match.group(10), (*base_tags, tag_strike))
                elif match.group(11):
                    insert_inline(match.group(12), (*base_tags, tag_italic))
                else:
                    insert_inline(match.group(13), (*base_tags, tag_italic))

                pos = match.end()

            insert(value[pos:], *base_tags)

        lines = str(md_text or "").splitlines()
        for index, raw_line in enumerate(lines):
            line = raw_line.rstrip()

            heading = re.match(r"^\s*(#{1,6})\s+(.+?)\s*#*\s*$", line)
            unordered = re.match(r"^(\s*)[-+*]\s+(.+)$", line)
            ordered = re.match(r"^(\s*)(\d+)[.)]\s+(.+)$", line)
            quote = re.match(r"^\s*>\s?(.*)$", line)

            if re.match(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$", line):
                insert("────────────────────────", tag_rule)
            elif heading:
                insert_inline(heading.group(2), (tag_heading,))
            elif unordered:
                depth = min(len(unordered.group(1).expandtabs(4)) // 2, 4)
                prefix = f"{'    ' * depth}• "
                insert(prefix, tag_list)
                insert_inline(unordered.group(2), (tag_list,))
            elif ordered:
                depth = min(len(ordered.group(1).expandtabs(4)) // 2, 4)
                prefix = f"{'    ' * depth}{ordered.group(2)}. "
                insert(prefix, tag_list)
                insert_inline(ordered.group(3), (tag_list,))
            elif quote:
                insert_inline(quote.group(1), (tag_quote,))
            else:
                insert_inline(line)

            # Preserve the Markdown source's actual line structure exactly,
            # without adding a synthetic trailing empty line to the TextView.
            if index < len(lines) - 1:
                insert("\n")

        return buffer

    def _schedule_markdown_view_height_fit(self, view, *_args):
        """Measure Markdown after GTK finishes the current layout pass."""
        if getattr(view, "_markdown_fit_source", None) is None:
            view._markdown_fit_source = GLib.idle_add(
                self._fit_markdown_view_height,
                view,
                priority=GLib.PRIORITY_DEFAULT_IDLE,
            )

    def _fit_markdown_view_height(self, view):
        """Keep a wrapped Markdown TextView only as tall as its rendered text."""
        view._markdown_fit_source = None

        # If the widget has not received a real width yet, wait for the next
        # allocation. Text wrapping (and therefore height) depends on that width.
        if view.get_allocated_width() <= 1:
            return False

        buffer = view.get_buffer()
        if buffer.get_char_count() == 0:
            desired_height = 1
        else:
            end = buffer.get_end_iter()
            y, line_height = view.get_line_yrange(end)
            desired_height = max(1, y + line_height)

        current_height = view.get_size_request()[1]
        if current_height != desired_height:
            view.set_size_request(-1, desired_height)
            view.queue_resize()

        return False

    def _on_markdown_link_clicked(self, view, event):
        if event.button != 1:
            return False

        x, y = view.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET,
            int(event.x),
            int(event.y),
        )
        iterator = view.get_iter_at_location(x, y)
        if isinstance(iterator, tuple):
            iterator = iterator[-1]

        for tag in iterator.get_tags():
            url = tag.get_data("url")
            if url:
                try:
                    Gtk.show_uri_on_window(self.parent, url, Gdk.CURRENT_TIME)
                except Exception:
                    webbrowser.open(url)
                return True

        return False

    def _build_developer_line(self):
        developer = str(self.script_info.get("developer", "") or "").strip()
        if not developer:
            return

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_halign(Gtk.Align.START)
        row.set_margin_bottom(5)

        label = Gtk.Label()
        label.set_markup(
            f'<span size="small" weight="bold">{GLib.markup_escape_text(developer)}</span>'
        )
        label.set_halign(Gtk.Align.START)
        label.set_selectable(False)
        label.set_can_focus(False)
        row.pack_start(label, False, False, 0)

        if self.script_info.get("is_verified", False):
            verified_path = get_icon_path("verified.svg")
            if verified_path and os.path.exists(verified_path):
                try:
                    badge_size = 16
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        verified_path, badge_size, badge_size, True
                    )
                    badge = Gtk.Image.new_from_pixbuf(pixbuf)
                    row.pack_start(badge, False, False, 0)
                except Exception:
                    pass

        self.header.vbox_infos.pack_start(row, False, False, 0)

        # InfosHead builds the name first, followed by the description/repository.
        # Reorder the developer row directly below the application name.
        self.header.vbox_infos.reorder_child(row, 1)


    def _format_price(self, option):
        symbol = option.get("currency_symbol") or "$"
        return f"{symbol}{option['price']:.2f}"

    def _commerce_button_label(self, kind, options):
        if kind == "purchase":
            plain_key, plain_fallback = "app_page_purchase", " Purchase "
            price_key, price_fallback = "app_page_purchase_price", " Purchase · ${price} "
        else:
            plain_key, plain_fallback = "app_page_subscribe", " Subscribe "
            price_key, price_fallback = "app_page_subscribe_price", " Subscribe · ${price} "

        if not options:
            return self.translations.get(plain_key, plain_fallback)

        lowest = min(options, key=lambda option: option["price"])
        price_text = self._format_price(lowest)
        if len(options) > 1:
            from_template = self.translations.get("app_page_from_price", "from ${price}")
            price_text = from_template.replace("${price}", price_text)

        template = self.translations.get(price_key, price_fallback)
        return template.replace("${price}", "{price}").format(price=price_text)

    def _subscription_option_label(self, option):
        pieces = []
        name = str(option.get("name") or "").strip()
        if name:
            pieces.append(name)

        months = option.get("months")
        if isinstance(months, int) and months > 0:
            if months == 1:
                unit = self.translations.get("app_page_month", "month")
            else:
                unit = self.translations.get("app_page_months", "months")
            pieces.append(f"{months} {unit}")

        pieces.append(self._format_price(option))
        return " · ".join(pieces)

    def _set_action_button_content(self, button, label, icon_name, dropdown=False):
        """Build consistent action-button contents with explicit horizontal padding."""
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        content.set_margin_start(8)
        content.set_margin_end(8)

        content.pack_start(
            Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON),
            False,
            False,
            0,
        )

        text = Gtk.Label(label=str(label).strip())
        content.pack_start(text, False, False, 0)

        if dropdown:
            content.pack_start(
                Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.BUTTON),
                False,
                False,
                0,
            )

        button.add(content)

    def _build_commerce_button(self, kind, options, fallback_url=""):
        label = self._commerce_button_label(kind, options)

        # Tiered purchases and subscriptions with multiple tiers/time frames use
        # a highlighted MenuButton so every choice stays inside the main action.
        if len(options) > 1:
            button = Gtk.MenuButton()
            self._set_action_button_content(
                button, label, "emblem-web-symbolic", dropdown=True
            )
            menu = Gtk.Menu()
            for option in options:
                if kind == "subscription":
                    option_label = self._subscription_option_label(option)
                else:
                    name = str(option.get("name") or "").strip()
                    option_label = " · ".join(
                        part for part in (name, self._format_price(option)) if part
                    )
                item = Gtk.MenuItem(label=option_label)
                item.connect("activate", self._open_url, option["url"])
                menu.append(item)
            menu.show_all()
            button.set_popup(menu)
        else:
            button = Gtk.Button()
            self._set_action_button_content(button, label, "emblem-web-symbolic")
            target_url = options[0]["url"] if options else fallback_url
            button.connect("clicked", self._open_url, target_url)

        button.get_style_context().add_class("suggested-action")
        return button

    def _build_actions(self):
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        install_label = self.translations.get("skills_install_label", " Install ")
        install_button = Gtk.Button(label=install_label)
        install_button.set_image(
            Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        )
        install_button.set_size_request(125, 35)
        install_button.connect("clicked", self._on_install_clicked)
        controls.pack_start(install_button, False, False, 0)

        purchase_url = self.script_info.get("purchase_url") or ""
        purchase_options = self.script_info.get("purchase_options") or []
        subscription_options = self.script_info.get("subscription_options") or []
        purchase_price = self.script_info.get("purchase_price")
        subscription_price = self.script_info.get("subscription_price")
        donate_url = self.script_info.get("donate_url") or ""

        # Backward compatibility for script_info produced by an older parser.
        if not purchase_options and purchase_url and purchase_price is not None:
            purchase_options = [{
                "name": "",
                "price": purchase_price,
                "currency_symbol": self.script_info.get("purchase_currency_symbol") or "$",
                "url": purchase_url,
            }]
        if not subscription_options and purchase_url and subscription_price is not None:
            subscription_options = [{
                "name": "",
                "months": 1,
                "price": subscription_price,
                "currency_symbol": self.script_info.get("subscription_currency_symbol") or "$",
                "url": purchase_url,
            }]

        if purchase_options:
            controls.pack_start(
                self._build_commerce_button("purchase", purchase_options, purchase_url),
                False, False, 0
            )

        if subscription_options:
            controls.pack_start(
                self._build_commerce_button("subscription", subscription_options, purchase_url),
                False, False, 0
            )

        if purchase_url and not purchase_options and not subscription_options:
            controls.pack_start(
                self._build_commerce_button("purchase", [], purchase_url),
                False, False, 0
            )

        if donate_url:
            donate_button = Gtk.Button()
            self._set_action_button_content(
                donate_button,
                self.translations.get("app_page_donate", " Donate "),
                "emblem-favorite-symbolic",
            )
            if not purchase_url and not purchase_options and not subscription_options:
                donate_button.get_style_context().add_class("suggested-action")
            donate_button.connect("clicked", self._open_url, donate_url)
            controls.pack_start(donate_button, False, False, 0)

        self.header.vbox_infos.pack_start(controls, False, False, 10)

    def _build_screenshot_viewer(self, screenshots):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        previous_button = Gtk.Button.new_from_icon_name(
            "go-previous-symbolic", Gtk.IconSize.BUTTON
        )
        next_button = Gtk.Button.new_from_icon_name(
            "go-next-symbolic", Gtk.IconSize.BUTTON
        )
        previous_button.set_tooltip_text(
            self.translations.get("app_page_previous_screenshot", "Previous screenshot")
        )
        next_button.set_tooltip_text(
            self.translations.get("app_page_next_screenshot", "Next screenshot")
        )
        previous_button.connect("clicked", self._on_screenshot_nav_clicked, -1)
        next_button.connect("clicked", self._on_screenshot_nav_clicked, 1)

        self.screenshot_stack = Gtk.Stack()
        self.screenshot_stack.set_hexpand(True)
        self.screenshot_stack.set_transition_duration(220)

        valid_count = 0
        for index, path in enumerate(screenshots):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    path, 760, 430, True
                )
            except Exception:
                continue

            image = Gtk.Image.new_from_pixbuf(pixbuf)
            image.set_halign(Gtk.Align.CENTER)
            image.set_valign(Gtk.Align.CENTER)
            frame = Gtk.Frame()
            frame.set_shadow_type(Gtk.ShadowType.IN)
            frame.add(image)
            self.screenshot_stack.add_named(frame, f"shot_{valid_count}")
            valid_count += 1

        if not valid_count:
            return outer

        self._screenshot_count = valid_count
        self.screenshot_stack.set_visible_child_name("shot_0")
        row.pack_start(previous_button, False, False, 0)
        row.pack_start(self.screenshot_stack, True, True, 0)
        row.pack_start(next_button, False, False, 0)
        outer.pack_start(row, False, False, 0)

        self.screenshot_counter = Gtk.Label()
        self.screenshot_counter.set_halign(Gtk.Align.CENTER)
        self._update_screenshot_counter()
        outer.pack_start(self.screenshot_counter, False, False, 0)

        if valid_count == 1:
            previous_button.set_sensitive(False)
            next_button.set_sensitive(False)
        else:
            self._screenshot_autoplay_source = GLib.timeout_add_seconds(
                7, self._auto_cycle_screenshot
            )

        return outer

    def _on_screenshot_nav_clicked(self, _button, direction):
        """Stop autoplay permanently once the user navigates the carousel."""
        self._stop_screenshot_autoplay()
        self.cycle_screenshot(direction)

    def _auto_cycle_screenshot(self):
        """Advance the carousel every seven seconds while autoplay is active."""
        if not self.screenshot_stack or getattr(self, "_screenshot_count", 0) < 2:
            self._screenshot_autoplay_source = None
            return False

        self.cycle_screenshot(1)
        return True

    def _stop_screenshot_autoplay(self, *_args):
        if self._screenshot_autoplay_source is not None:
            GLib.source_remove(self._screenshot_autoplay_source)
            self._screenshot_autoplay_source = None

    def cycle_screenshot(self, direction):
        if not self.screenshot_stack or getattr(self, "_screenshot_count", 0) < 2:
            return

        if direction > 0:
            self.screenshot_stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT
            )
        else:
            self.screenshot_stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_RIGHT
            )

        self.screenshot_index = (
            self.screenshot_index + direction
        ) % self._screenshot_count
        self.screenshot_stack.set_visible_child_name(
            f"shot_{self.screenshot_index}"
        )
        self._update_screenshot_counter()

    def _update_screenshot_counter(self):
        if self.screenshot_counter is not None:
            self.screenshot_counter.set_text(
                f"{self.screenshot_index + 1} / {self._screenshot_count}"
            )

    def _on_install_clicked(self, _button):
        if self.on_install_callback:
            self.on_install_callback(self.script_info)

    def _open_url(self, _button, url):
        try:
            Gtk.show_uri_on_window(self.parent, url, Gdk.CURRENT_TIME)
        except Exception:
            webbrowser.open(url)
