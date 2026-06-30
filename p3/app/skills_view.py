import os
import subprocess
import threading

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib, Gdk, Gtk, Pango

from . import get_icon_path


def _run_fetcher(command, *args):
    fetcher_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "skills_fetcher.py"
    )
    python = os.environ.get("PYTHON", "python3")
    cmd = [python, fetcher_path, command] + list(args)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, check=False
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except Exception:
        return None


def _format_installs(count):
    try:
        count = int(count)
    except (TypeError, ValueError):
        return "0"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


class InstalledCard(Gtk.EventBox):
    def __init__(self, skill, translations, on_remove_callback):
        super().__init__()
        self.skill = skill
        self.translations = translations
        self.on_remove_callback = on_remove_callback

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_halign(Gtk.Align.START)
        outer.set_valign(Gtk.Align.CENTER)

        icon_size = 40
        icon_value = skill.get("icon", "skill.svg")
        icon_widget = None

        if isinstance(icon_value, str) and (
            icon_value.endswith(".png") or icon_value.endswith(".svg")
        ):
            if not os.path.isabs(icon_value) and "/" not in icon_value:
                icon_path = get_icon_path(icon_value)
            else:
                icon_path = icon_value if os.path.exists(icon_value) else None

            if icon_path and os.path.exists(icon_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        icon_path, icon_size, icon_size, True
                    )
                    icon_widget = Gtk.Image.new_from_pixbuf(pixbuf)
                except Exception:
                    icon_widget = None

        if icon_widget is None:
            icon_widget = Gtk.Image.new_from_icon_name(
                "application-x-executable", Gtk.IconSize.DIALOG
            )
            icon_widget.set_pixel_size(icon_size)

        icon_widget.set_halign(Gtk.Align.START)
        icon_widget.set_valign(Gtk.Align.CENTER)
        outer.pack_start(icon_widget, False, False, 0)

        name = skill.get("name", "Unknown")
        name_label = Gtk.Label(label=name)
        name_label.set_line_wrap(True)
        name_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        name_label.set_justify(Gtk.Justification.LEFT)
        name_label.set_halign(Gtk.Align.START)
        name_label.set_valign(Gtk.Align.CENTER)
        name_label.set_max_width_chars(40)
        outer.pack_start(name_label, False, False, 0)

        agents = skill.get("agents", [])
        if agents:
            agents_str = ", ".join(agents)
            agents_label = Gtk.Label(label=agents_str)
            agents_label.set_line_wrap(True)
            agents_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            agents_label.set_justify(Gtk.Justification.LEFT)
            agents_label.set_halign(Gtk.Align.START)
            agents_label.set_valign(Gtk.Align.CENTER)
            agents_label.set_max_width_chars(50)
            agents_label.get_style_context().add_class("dim-label")
            outer.pack_start(agents_label, False, False, 0)

        remove_btn = Gtk.Button()
        remove_btn.set_image(Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.MENU))
        remove_btn.set_tooltip_text(translations.get("skills_remove_label", "Remove"))
        remove_btn.get_style_context().add_class("destructive-action")
        remove_btn.get_style_context().add_class("installed-card-remove")
        remove_btn.set_relief(Gtk.ReliefStyle.NONE)
        remove_btn.set_can_focus(False)
        remove_btn.connect("clicked", lambda _: on_remove_callback(self.skill))

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.pack_start(outer, True, True, 0)
        box.pack_end(remove_btn, False, False, 0)

        self.add(box)
        self.get_style_context().add_class("script-item")
        self.get_style_context().add_class("installed-card")


class SkillCard(Gtk.EventBox):
    def __init__(self, skill, translations, on_click_callback):
        super().__init__()
        self.skill = skill
        self.translations = translations
        self.on_click_callback = on_click_callback

        self.set_events(
            self.get_events()
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
        )

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)

        icon_size = 48
        icon_value = skill.get("icon", "skill.svg")
        icon_widget = None

        if isinstance(icon_value, str) and (
            icon_value.endswith(".png") or icon_value.endswith(".svg")
        ):
            if not os.path.isabs(icon_value) and "/" not in icon_value:
                icon_path = get_icon_path(icon_value)
            else:
                icon_path = icon_value if os.path.exists(icon_value) else None

            if icon_path and os.path.exists(icon_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        icon_path, icon_size, icon_size, True
                    )
                    icon_widget = Gtk.Image.new_from_pixbuf(pixbuf)
                except Exception:
                    icon_widget = None

        if icon_widget is None:
            icon_widget = Gtk.Image.new_from_icon_name(
                "application-x-executable", Gtk.IconSize.DIALOG
            )
            icon_widget.set_pixel_size(icon_size)

        icon_widget.set_halign(Gtk.Align.CENTER)
        icon_widget.set_valign(Gtk.Align.CENTER)
        outer.pack_start(icon_widget, False, False, 0)

        name = skill.get("name", "Unknown")
        name_label = Gtk.Label(label=name)
        name_label.set_line_wrap(True)
        name_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        name_label.set_justify(Gtk.Justification.CENTER)
        name_label.set_halign(Gtk.Align.CENTER)
        name_label.set_valign(Gtk.Align.CENTER)
        name_label.set_max_width_chars(20)
        outer.pack_start(name_label, False, False, 0)

        installs = skill.get("installs", 0)
        installs_str = _format_installs(installs)

        installs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        installs_box.set_halign(Gtk.Align.CENTER)

        download_icon_path = get_icon_path("download.svg")
        if download_icon_path:
            try:
                download_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    download_icon_path, 16, 16, True
                )
                download_icon = Gtk.Image.new_from_pixbuf(download_pixbuf)
                installs_box.pack_start(download_icon, False, False, 0)
            except Exception:
                pass

        installs_label = Gtk.Label(label=installs_str)
        installs_label.get_style_context().add_class("dim-label")
        installs_box.pack_start(installs_label, False, False, 0)

        outer.pack_start(installs_box, False, False, 0)

        self.add(outer)
        self.get_style_context().add_class("script-item")

        self.connect("enter-notify-event", self._on_enter)
        self.connect("leave-notify-event", self._on_leave)
        self.connect("button-press-event", self._on_click)

    def _on_enter(self, widget, event):
        self.get_style_context().add_class("script-item-hover")
        return False

    def _on_leave(self, widget, event):
        self.get_style_context().remove_class("script-item-hover")
        return False

    def _on_click(self, widget, event):
        if event.button == 1 and self.on_click_callback:
            self.on_click_callback(self.skill)
        return False


class SkillsSeekerView(Gtk.Box):
    def __init__(self, translations, on_install_callback=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.translations = translations
        self.on_install_callback = on_install_callback
        self.all_skills = []
        self.filtered_skills = []
        self._loading = False
        self._current_query = ""
        self._searching = False
        self._loading_installed = False

        # --- Stack switcher (abas: Discover | Installed) ---
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_halign(Gtk.Align.CENTER)
        switcher.set_margin_top(12)
        switcher.set_margin_bottom(8)
        self.pack_start(switcher, False, False, 0)

        self.pack_start(self.stack, True, True, 0)

        # --- Página "Discover" ---
        discover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_margin_start(32)
        self.scrolled.set_margin_end(32)
        self.scrolled.set_margin_bottom(16)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(5)
        self.flowbox.set_activate_on_single_click(False)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_column_spacing(16)
        self.flowbox.set_row_spacing(12)

        self._overlay = Gtk.Overlay()
        self._overlay.add(self.flowbox)

        self._loading_spinner = Gtk.Spinner()
        self._loading_spinner.set_size_request(48, 48)
        self._loading_spinner.set_halign(Gtk.Align.CENTER)
        self._loading_spinner.set_valign(Gtk.Align.CENTER)
        self._loading_spinner.set_margin_top(32)
        self._overlay.add_overlay(self._loading_spinner)

        self._no_results_label = Gtk.Label()
        self._no_results_label.set_text(
            self.translations.get(
                "skills_no_results", "No skills found for your search."
            )
        )
        self._no_results_label.get_style_context().add_class("dim-label")
        self._no_results_label.set_halign(Gtk.Align.CENTER)
        self._no_results_label.set_valign(Gtk.Align.CENTER)
        self._no_results_label.set_margin_top(32)
        self._overlay.add_overlay(self._no_results_label)
        self._no_results_label.hide()

        self.scrolled.add(self._overlay)
        discover_box.pack_start(self.scrolled, True, True, 0)

        self.status_label = Gtk.Label(label="")
        self.status_label.get_style_context().add_class("dim-label")
        self.status_label.set_margin_start(32)
        self.status_label.set_margin_top(4)
        self.status_label.set_margin_bottom(8)
        discover_box.pack_start(self.status_label, False, False, 0)

        self.stack.add_titled(discover_box, "discover", translations.get("skills_tab_discover", "Discover"))

        # --- Página "Installed" ---
        installed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Botão de recarregar
        reload_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        reload_bar.set_margin_start(32)
        reload_bar.set_margin_end(32)
        reload_bar.set_margin_top(8)
        reload_bar.set_margin_bottom(4)
        reload_btn = Gtk.Button(label=translations.get("skills_reload_label", "Reload"))
        reload_btn.connect("clicked", lambda _: self.load_installed())
        reload_bar.pack_end(reload_btn, False, False, 0)
        installed_box.pack_start(reload_bar, False, False, 0)

        installed_scrolled = Gtk.ScrolledWindow()
        installed_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        installed_scrolled.set_margin_start(32)
        installed_scrolled.set_margin_end(32)
        installed_scrolled.set_margin_bottom(16)

        self.installed_flowbox = Gtk.FlowBox()
        self.installed_flowbox.set_valign(Gtk.Align.START)
        self.installed_flowbox.set_max_children_per_line(5)
        self.installed_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.installed_flowbox.set_homogeneous(True)
        self.installed_flowbox.set_column_spacing(16)
        self.installed_flowbox.set_row_spacing(12)
        installed_scrolled.add(self.installed_flowbox)
        installed_box.pack_start(installed_scrolled, True, True, 0)

        self.installed_status_label = Gtk.Label(label="")
        self.installed_status_label.get_style_context().add_class("dim-label")
        self.installed_status_label.set_margin_start(32)
        self.installed_status_label.set_margin_top(4)
        self.installed_status_label.set_margin_bottom(8)
        installed_box.pack_start(self.installed_status_label, False, False, 0)

        self.stack.add_titled(installed_box, "installed", translations.get("skills_tab_installed", "Installed"))

        # Carregar installed ao trocar de aba
        self.stack.connect("notify::visible-child-name", self._on_tab_switched)

    def _show_loading(self, text=None):
        self._loading_spinner.show()
        self._loading_spinner.start()
        self._no_results_label.hide()
        self.status_label.set_text(
            text or self.translations.get("skills_loading", "Loading...")
        )

    def _hide_loading(self):
        self._loading_spinner.stop()
        self._loading_spinner.hide()

    def _reset_searching(self):
        self._searching = False
        return False

    def _npx_path(self):
        import shutil
        return shutil.which("npx")

    def get_flowbox(self):
        return self.flowbox

    def show_all(self):
        super().show_all()
        self._loading = False
        self._searching = False
        self._loading_installed = False
        self._no_results_label.hide()
        GLib.idle_add(self.load_popular)

    def _on_tab_switched(self, stack, _param):
        if stack.get_visible_child_name() == "installed":
            self._hide_loading()
            self.load_installed()

    def _refresh_flowbox(self):
        for child in self.flowbox.get_children():
            child.destroy()

        for skill in self.filtered_skills:
            card = SkillCard(
                skill, self.translations, self._on_card_activated
            )
            self.flowbox.add(card)

        self.flowbox.show_all()
        count = len(self.filtered_skills)
        if count == 0:
            self.status_label.hide()
            self._no_results_label.show()
        else:
            self.status_label.show()
            self.status_label.set_text(f"{count} skill(s)")
            self._no_results_label.hide()

    def do_search(self, query):
        """Chamado pelo window.py quando o usuário digita na search entry do header."""
        if self._searching:
            return
        self._searching = True
        self._current_query = query
        self.stack.set_visible_child_name("discover")
        if not query:
            if self.all_skills:
                self.filtered_skills = list(self.all_skills)
                self._refresh_flowbox()
                self._hide_loading()
                self._searching = False
                self._no_results_label.hide()
                self.status_label.set_text(f"{len(self.filtered_skills)} skill(s)")
            else:
                self._show_loading()
                GLib.idle_add(self.load_popular)
                self.status_label.set_text(
                    self.translations.get("skills_loading", "Loading...")
                )
            return
        self.filtered_skills = []
        self._refresh_flowbox()
        self._show_loading(
            self.translations.get("skills_searching", "Searching...")
        )
        threading.Thread(
            target=self._do_api_search_bg, args=(query,), daemon=True
        ).start()

    def _do_api_search_bg(self, query):
        raw = _run_fetcher("search", query, "20")
        if not raw or self._current_query != query:
            GLib.idle_add(self._refresh_flowbox)
            GLib.idle_add(self._hide_loading)
            GLib.idle_add(self._reset_searching)
            GLib.idle_add(
                self._set_status_error,
                self.translations.get(
                    "skills_no_internet", "Internet connection is required to search and browse skills."
                ),
            )
            return
        try:
            import json

            data = json.loads(raw)
            skills = [
                {
                    "id": s.get("id", ""),
                    "skillId": s.get("skillId", ""),
                    "name": s.get("name", ""),
                    "installs": s.get("installs", 0),
                    "source": s.get("source", ""),
                    "icon": "skill.svg",
                }
                for s in data.get("skills", [])
            ]
            GLib.idle_add(self._on_api_search_done, query, skills)
        except Exception:
            GLib.idle_add(self._refresh_flowbox)
            GLib.idle_add(self._hide_loading)
            GLib.idle_add(self._reset_searching)
            GLib.idle_add(
                self._set_status_error,
                self.translations.get(
                    "skills_error_parse", "Failed to parse skills data."
                ),
            )

    def _set_status_error(self, msg):
        self.status_label.set_text(msg)
        return False

    def _on_api_search_done(self, query, skills):
        self._hide_loading()
        self._searching = False
        if self._current_query == query:
            self.filtered_skills = skills
            self._refresh_flowbox()
        return False

    def _on_card_activated(self, skill):
        self._show_action_dialog(skill)

    def _show_action_dialog(self, skill):
        dialog = Gtk.Dialog(
            title=self.translations.get("skills_action_title", "Action"),
            transient_for=self.get_toplevel(),
            flags=0,
        )
        dialog.set_default_size(400, 200)

        install_label = self.translations.get("skills_install_label", "Install")
        detail_label = self.translations.get("skills_detail_label", "View Details")
        back_label = self.translations.get("skills_back_label", "Back")

        dialog.add_button(back_label, Gtk.ResponseType.CANCEL)
        dialog.add_button(detail_label, Gtk.ResponseType.OK)
        dialog.add_button(install_label, Gtk.ResponseType.YES)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)

        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        name = skill.get("name", "Unknown")
        name_lbl = Gtk.Label()
        name_lbl.set_markup(f"<big><b>{name}</b></big>")
        name_lbl.set_halign(Gtk.Align.START)
        content.pack_start(name_lbl, False, False, 0)

        desc = skill.get("description", "")
        if not desc:
            desc = self.translations.get(
                "skills_seeker_desc", "Browse, search and install AI agent skills."
            )
        desc_lbl = Gtk.Label(label=desc)
        desc_lbl.set_line_wrap(True)
        desc_lbl.set_justify(Gtk.Justification.LEFT)
        desc_lbl.set_halign(Gtk.Align.START)
        desc_lbl.get_style_context().add_class("dim-label")
        content.pack_start(desc_lbl, False, False, 0)

        disclaimer = self.translations.get("ai_agent_disclaimer", "")
        if disclaimer:
            disc_label = Gtk.Label(label=disclaimer)
            disc_label.set_line_wrap(True)
            disc_label.set_justify(Gtk.Justification.LEFT)
            disc_label.set_halign(Gtk.Align.START)
            disc_label.get_style_context().add_class("dim-label")
            content.pack_start(disc_label, False, False, 0)

        dialog.show_all()
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self._handle_install(skill)
        elif response == Gtk.ResponseType.OK:
            self._open_in_browser(skill)

    def _open_in_browser(self, skill):
        source = skill.get("source", "")
        skill_id = skill.get("skillId", skill.get("id", ""))
        if not source or not skill_id:
            self._show_error(
                self.translations.get("skills_error_no_source", "Could not determine skill URL.")
            )
            return
        url = f"https://skills.sh/{source}/{skill_id}"
        import subprocess
        subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _handle_install(self, skill):
        source = skill.get("source", "")
        slug = skill.get("skillId", skill.get("id", ""))
        if not source:
            self._show_error(
                self.translations.get(
                    "skills_error_no_source", "Could not determine skill source."
                )
            )
            return

        agents = self._detect_agents()
        if not agents:
            self._show_error(
                self.translations.get(
                    "skills_no_agents", "No supported AI agents detected on this system."
                )
            )
            return

        agent = self._show_agent_choice_dialog(agents)
        if not agent:
            return

        if self.on_install_callback:
            self.on_install_callback(source, slug, agent)
        else:
            self._run_install_bg_start(source, slug, agent)

    def _detect_agents(self):
        home = os.path.expanduser("~")
        agents = []
        checks = [
            (os.path.join(home, ".claude"), "claude-code"),
            (os.path.join(home, ".codex"), "codex"),
            (os.path.join(home, ".config", "opencode"), "opencode"),
            (os.path.join(home, ".cursor"), "cursor"),
            (os.path.join(home, ".windsurf"), "windsurf"),
            (os.path.join(home, ".gemini"), "gemini-cli"),
            (os.path.join(home, ".agents"), "cline"),
            (os.path.join(home, ".roo"), "roo"),
            (os.path.join(home, ".trae"), "trae"),
            (os.path.join(home, ".kilocode"), "kilo"),
            (os.path.join(home, ".factory"), "droid"),
            (os.path.join(home, ".copilot"), "github-copilot"),
        ]
        for path, name in checks:
            if os.path.isdir(path):
                agents.append(name)
        return agents

    def _show_agent_choice_dialog(self, agents):
        dialog = Gtk.Dialog(
            title=self.translations.get("skills_choose_agent_title", "Choose Agent"),
            transient_for=self.get_toplevel(),
            flags=0,
        )
        dialog.set_default_size(300, 300)

        agent_list = Gtk.ListBox()
        agent_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for agent in agents:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=agent, xalign=0)
            label.set_margin_start(12)
            label.set_margin_end(12)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            row.add(label)
            agent_list.add(row)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(agent_list)

        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.pack_start(scrolled, True, True, 0)

        dialog.add_button(
            self.translations.get("skills_back_label", "Cancel"),
            Gtk.ResponseType.CANCEL,
        )
        dialog.add_button(
            self.translations.get("skills_install_label", "Install"),
            Gtk.ResponseType.OK,
        )
        dialog.set_default_response(Gtk.ResponseType.OK)

        dialog.show_all()
        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            return None

        selected = agent_list.get_selected_row()
        if not selected:
            return None
        label = selected.get_child()
        return label.get_text()

    def _show_error(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message,
        )
        dialog.run()
        dialog.destroy()

    def _run_install_bg_start(self, source, slug, agent):
        npx = self._npx_path()
        if not npx:
            self._show_error(
                self.translations.get(
                    "skills_error_no_npx",
                    "Node.js (npx) is required to install skills.\nPlease install Node.js first."
                )
            )
            return
        self.status_label.set_text(self.translations.get("skills_installing", "Installing..."))
        self.stack.set_visible_child_name("discover")
        import threading
        threading.Thread(
            target=self._run_install_bg, args=(source, slug, agent, npx), daemon=True
        ).start()

    def _run_install_bg(self, source, slug, agent, npx):
        import subprocess
        cmd = [npx, "skills", "add", source, "--skill", slug, "-a", agent, "-g", "-y"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            ok = result.returncode == 0
            msg = result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            ok = False
            msg = self.translations.get("skills_error_timeout", "Installation timed out.")
        except Exception as e:
            ok = False
            msg = str(e)
        GLib.idle_add(self._on_install_done, ok, msg)

    def _on_install_done(self, ok, msg):
        if ok:
            self.status_label.set_text(
                self.translations.get("skills_installed_ok", "Skill installed successfully!")
            )
        else:
            self.status_label.set_text(
                self.translations.get("skills_error_install", "Installation failed.")
            )
        return False

    def load_installed(self):
        """Carrega a lista de skills instaladas em background."""
        if self._loading_installed:
            return
        self._loading_installed = True
        if os.environ.get("DEV_MODE") == "1":
            self._show_loading()
            for child in self.installed_flowbox.get_children():
                child.destroy()
            import threading
            threading.Thread(target=self._load_installed_bg_mock, daemon=True).start()
            return
        npx = self._npx_path()
        if not npx:
            self.installed_status_label.set_text(
                self.translations.get("skills_error_no_npx", "Node.js (npx) is required.")
            )
            self._loading_installed = False
            return
        self._show_loading()
        for child in self.installed_flowbox.get_children():
            child.destroy()
        import threading
        threading.Thread(target=self._load_installed_bg, args=(npx,), daemon=True).start()

    def _load_installed_bg_mock(self):
        mock_skills = [
            {"name": "react-expert",    "agents": ["claude-code", "opencode"],     "source": "ai-agents"},
            {"name": "python-debugger", "agents": ["claude-code"],                  "source": "devs"},
            {"name": "docker-helper",   "agents": ["codex", "claude-code"],         "source": "devs"},
            {"name": "git-workflow",    "agents": ["opencode", "cline"],            "source": "ai-agents"},
            {"name": "test-generator",  "agents": ["claude-code"],                  "source": "devs"},
        ]
        GLib.idle_add(self._on_installed_loaded, mock_skills, None)

    def _load_installed_bg(self, npx):
        import subprocess, json as _json
        try:
            result = subprocess.run(
                [npx, "skills", "list", "--json", "-g"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                GLib.idle_add(self._on_installed_loaded, [], result.stderr.strip())
                return
            skills = _json.loads(result.stdout.strip() or "[]")
            GLib.idle_add(self._on_installed_loaded, skills, None)
        except Exception as e:
            GLib.idle_add(self._on_installed_loaded, [], str(e))

    def _on_installed_loaded(self, skills, error_msg):
        self._hide_loading()
        self._loading_installed = False
        for child in self.installed_flowbox.get_children():
            child.destroy()
        if error_msg:
            self.installed_status_label.set_text(error_msg)
            return False
        if not skills:
            self.installed_status_label.set_text(
                self.translations.get("skills_no_installed", "No skills installed globally.")
            )
            return False
        for skill in skills:
            card = InstalledCard(
                skill, self.translations, self._handle_remove
            )
            self.installed_flowbox.add(card)
        self.installed_flowbox.show_all()
        self.installed_status_label.set_text(f"{len(skills)} skill(s)")
        return False

    def _handle_remove(self, skill):
        """Confirma e executa remoção de uma skill."""
        if os.environ.get("DEV_MODE") == "1":
            self._show_error("Mock mode: removal is disabled.")
            return
        skill_name = skill.get("name", "")
        agents = skill.get("agents", [])

        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=self.translations.get("skills_confirm_remove_title", "Remove Skill?"),
        )
        dialog.format_secondary_text(
            f"{skill_name}\n{self.translations.get('skills_confirm_remove_msg', 'This will remove the skill from all linked agents.')}"
        )
        dialog.add_button(self.translations.get("skills_back_label", "Cancel"), Gtk.ResponseType.CANCEL)
        remove_lbl = self.translations.get("skills_remove_label", "Remove")
        dialog.add_button(remove_lbl, Gtk.ResponseType.OK)

        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return

        npx = self._npx_path()
        if not npx:
            self._show_error(self.translations.get("skills_error_no_npx", "Node.js (npx) is required."))
            return

        self.installed_status_label.set_text(
            self.translations.get("skills_removing", "Removing...")
        )
        import threading
        threading.Thread(
            target=self._run_remove_bg, args=(skill_name, agents, npx), daemon=True
        ).start()

    def _run_remove_bg(self, skill_name, agents, npx):
        import subprocess
        errors = []
        if agents:
            for agent in agents:
                # map display name back to agent id best-effort (lowercase, strip spaces)
                agent_id = agent.lower().replace(" ", "-")
                cmd = [npx, "skills", "remove", skill_name, "-a", agent_id, "-g", "-y"]
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if r.returncode != 0:
                        errors.append(r.stderr.strip())
                except Exception as e:
                    errors.append(str(e))
        else:
            cmd = [npx, "skills", "remove", skill_name, "-g", "-y"]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if r.returncode != 0:
                    errors.append(r.stderr.strip())
            except Exception as e:
                errors.append(str(e))
        ok = not errors
        GLib.idle_add(self._on_remove_done, ok, errors)

    def _on_remove_done(self, ok, errors):
        if ok:
            self.installed_status_label.set_text(
                self.translations.get("skills_removed_ok", "Skill removed.")
            )
            self.load_installed()  # refresh
        else:
            self.installed_status_label.set_text(
                self.translations.get("skills_error_remove", "Removal failed.")
            )
        return False

    def load_popular(self):
        if self._loading:
            return False
        self._loading = True
        self._show_loading()
        threading.Thread(target=self._load_popular_bg, daemon=True).start()
        return False

    def _load_popular_bg(self):
        raw = _run_fetcher("popular", "50")
        skills = []
        error_msg = None
        if raw:
            try:
                import json

                data = json.loads(raw)
                for s in data.get("skills", []):
                    skills.append(
                        {
                            "id": s.get("id", ""),
                            "skillId": s.get("skillId", ""),
                            "name": s.get("name", ""),
                            "installs": s.get("installs", 0),
                            "source": s.get("source", ""),
                            "icon": "skill.svg",
                        }
                    )
            except Exception:
                error_msg = self.translations.get(
                    "skills_error_parse", "Failed to parse skills data."
                )
        else:
            error_msg = self.translations.get(
                "skills_no_internet", "Internet connection is required to search and browse skills."
            )
        GLib.idle_add(self._on_popular_loaded, skills, error_msg)
        return False

    def _on_popular_loaded(self, skills, error_msg=None):
        self._hide_loading()
        self.all_skills = skills
        self.filtered_skills = list(skills)
        self._refresh_flowbox()
        self._loading = False
        if error_msg:
            self.status_label.set_text(error_msg)
        return False
