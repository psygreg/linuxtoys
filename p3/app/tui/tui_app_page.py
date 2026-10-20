from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping, Sequence
from typing import Any

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.widget import Widget
from textual.widgets import (
    Button,
    Label,
    Rule,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from app import appstream_cache

__all__ = ["AppPageWidget", "FeaturedCard", "show_app_page", "hide_app_page"]

MENU_PANEL = "#menu-panel"
BODY = "#body-home"
LIST_VIEW = "#home-menu"
LOGO = "#logo_lt"
TERMINAL = "#terminal-conteiner"

MIN_CARD_WIDTH = 30
CARD_HEIGHT = 5
MAX_COLUMNS = 5

_BLANK = Select.NULL


def _norm_lang(value: Any) -> str:
    """Normalize a locale string to a lowercase language code.
    Drops the region, encoding and modifiers."""
    value = str(value or "").strip().replace("_", "-")
    return value.split("-", 1)[0].split(".", 1)[0].casefold() if value else ""


#: Maps AppStream span styles to Rich style strings.
_SPAN_STYLES = {
    "bold": "bold",
    "strong": "bold",
    "italic": "italic",
    "emphasis": "italic",
    "em": "italic",
    "code": "#e5c07b on #2a2a2a",
    "underline": "underline",
}


def _spans_to_text(spans: Sequence[Mapping[str, Any]] | str) -> Text:
    """Convert AppStream inline spans into a Rich ``Text``.

    Styles missing from ``_SPAN_STYLES`` are ignored. A span with a
    ``url`` becomes an underlined blue link.

    Args:
        spans: A plain str (returned as is) or span mappings with
            ``text`` and optional ``styles`` and ``url`` keys.

    Returns:
        The styled text.
    """
    if isinstance(spans, str):
        return Text(spans)
    out = Text()
    for span in spans or ():
        styles = [
            _SPAN_STYLES[s]
            for s in (span.get("styles") or ())
            if s in _SPAN_STYLES
        ]
        url = span.get("url")
        if url:
            styles.append(f"underline blue link {url}")
        out.append(str(span.get("text", "")), style=" ".join(styles) or None)
    return out


def blocks_to_text(blocks: Any) -> Text:
    """Render an AppStream description into a Rich ``Text``.

    Paragraphs are separated by a blank line. List items go on their own
    lines, with a bullet (``unordered_list``) or a number
    (``ordered_list``). Other block types are ignored.

    Args:
        blocks: A plain str or a list of block dicts.

    Returns:
        The rendered text.
    """
    if isinstance(blocks, str):
        return Text(blocks)
    out = Text()
    for block in blocks or ():
        if out.plain:
            out.append("\n\n" if block.get("type") == "paragraph" else "\n")
        kind = block.get("type")
        if kind == "paragraph":
            out.append_text(_spans_to_text(block.get("spans") or ()))
        elif kind in ("unordered_list", "ordered_list"):
            for number, item in enumerate(block.get("items") or (), start=1):
                if number > 1:
                    out.append("\n")
                out.append(
                    "  • " if kind == "unordered_list" else f"  {number}. "
                )
                out.append_text(_spans_to_text(item))
    return out


def _script_key(info: Mapping[str, Any]) -> str:
    """Return the key that identifies a script entry.

    Uses ``id``, then ``appstream_id``, then ``name``.

    Args:
        info: Script info mapping.

    Returns:
        The key, or ``""`` if none is set.
    """
    return str(
        info.get("id") or info.get("appstream_id") or info.get("name") or ""
    )


def _fmt_price(option: Mapping[str, Any]) -> str:
    """Format the price of a purchase or subscription option.

    Args:
        option: Mapping with ``price`` and an optional
            ``currency_symbol`` (default ``"$"``).

    Returns:
        The symbol followed by the price with two decimals, e.g.
        ``"$9.99"``.

    Raises:
        KeyError: If ``price`` is missing.
        ValueError: If ``price`` is not numeric.
    """
    return (
        f"{option.get('currency_symbol') or '$'}{float(option['price']):.2f}"
    )


class FeaturedCard(Static, can_focus=True):
    """Focusable card for one entry of the "Try These" grid.

    Shows the name in bold and the description dimmed, which is also the
    tooltip. A click or the Enter key posts ``Selected``.

    Args:
        script_info: Script info mapping of the featured entry.
    """

    BINDINGS = [Binding("enter", "select", "Open", show=False)]

    class Selected(Message):
        def __init__(self, script_info: Mapping[str, Any]) -> None:
            super().__init__()
            self.script_info = script_info

    def __init__(self, script_info: Mapping[str, Any]) -> None:
        desc = str(script_info.get("description") or "").strip()
        text = Text()
        text.append(str(script_info.get("name", "")), style="bold")
        if desc:
            text.append("\n" + desc, style="dim")
        super().__init__(text)
        self.script_info = script_info
        if desc:
            self.tooltip = desc

    def on_click(self) -> None:
        self.action_select()

    def action_select(self) -> None:
        self.post_message(self.Selected(self.script_info))


class AppPageWidget(Vertical):
    """Page that shows one app and its actions.

    Everything it needs comes from the constructor. User actions leave
    as messages for the host to handle: install, uninstall, open URL,
    translate, source change, featured selection and the extension
    actions. After handling them, the host updates the page with
    ``set_install_state``, ``set_translated_blocks``, ``set_user_rating``,
    ``refresh_extensions`` and the ``reset_*_button`` methods.

    The initial source is ``recommended_source`` (or ``appstream_source``)
    when ``source_options`` has it, otherwise the first option. Featured
    candidates exclude the current app and list the same category first.

    Args:
        script_info: Script info mapping of the app.
        translations: UI translations. Missing keys fall back to
            English defaults.
        featured: Candidate entries for the "Try These" grid.
        installed: Whether the app is currently installed.
        system_language: Target language for description translation.
            Defaults to the ``LANG`` environment variable.
        id: Widget id.
        **kwargs: Forwarded to ``Vertical``.
    """

    DEFAULT_CSS = """
    AppPageWidget #app-tabs.no-ext ContentTabs { display: none; }
    AppPageWidget #app-rating-confirm { height: auto; }
    AppPageWidget #app-rating-confirm-text { width: 1fr; height: auto; }
    AppPageWidget .ext-row { height: auto; padding: 0 1; }
    AppPageWidget .ext-info { width: 1fr; height: auto; }
    """

    # ---- mensagens para o host ------------------------------------------- #
    class BackRequested(Message):
        """Posted when the user asks to leave the page."""

    class InstallRequested(Message):
        """Posted when Install is pressed.

        Attributes:
            script_info: The selected source entry.
        """

        def __init__(self, script_info: Mapping[str, Any]) -> None:
            super().__init__()
            self.script_info = script_info

    class OpenRequested(InstallRequested):
        """Posted when Open is pressed. Same payload as the parent."""

    class RateRequested(Message):
        """Reserved for GUI parity. Ratings are sent by the widget.

        Attributes:
            stars: Star count (1 to 5).
            script_info: Script info of the rated app.
        """

        def __init__(self, stars: int, script_info: Mapping[str, Any]) -> None:
            super().__init__()
            self.stars = stars
            self.script_info = script_info

    class UrlRequested(Message):
        """Posted when a purchase, website or donate link is chosen.

        Attributes:
            url: URL the host should open.
        """

        def __init__(self, url: str) -> None:
            super().__init__()
            self.url = url

    class TranslateRequested(Message):
        """Posted when the user asks to translate the description.

        The host should translate in a worker thread and answer with
        ``set_translated_blocks`` (or None on failure).

        Attributes:
            blocks: Description to translate (str or list of blocks).
            target_language: Target language code.
        """

        def __init__(self, blocks: Any, target_language: str) -> None:
            super().__init__()
            self.blocks = blocks
            self.target_language = target_language

    class SourceChanged(Message):
        """Posted after the user picks another install source.

        Attributes:
            script_info: The newly selected source entry.
        """

        def __init__(self, script_info: Mapping[str, Any]) -> None:
            super().__init__()
            self.script_info = script_info

    class FeaturedSelected(Message):
        """Posted when a featured card is chosen.

        Attributes:
            script_info: Script info of the chosen entry.
        """

        def __init__(self, script_info: Mapping[str, Any]) -> None:
            super().__init__()
            self.script_info = script_info

    class UninstallRequested(InstallRequested):
        """Posted when Remove is pressed. Same payload as the parent."""

    class ExtensionInstallRequested(Message):
        """Posted when an extension Install button is pressed.

        Attributes:
            info: Extension info. It already includes
                ``is_flatpak_extension=True``, as in the GUI.
        """

        def __init__(self, info: Mapping[str, Any]) -> None:
            super().__init__()
            self.info = info

    class ExtensionRemoveRequested(Message):
        """Posted when an extension Remove button is pressed.

        Attributes:
            info: Extension info.
            record_id: ID of the finished, successful install job of
                this extension, or None if there is none.
        """

        def __init__(
            self, info: Mapping[str, Any], record_id: Any = None
        ) -> None:
            super().__init__()
            self.info = info
            self.record_id = record_id

    class ExtensionCancelRequested(Message):
        """Posted when a queued extension install is cancelled.

        Attributes:
            job_id: ID of the queued job.
        """

        def __init__(self, job_id: Any) -> None:
            super().__init__()
            self.job_id = job_id

    def __init__(
        self,
        script_info: Mapping[str, Any],
        *,
        translations: Mapping[str, str] | None = None,
        featured: Sequence[Mapping[str, Any]] | None = None,
        installed: bool = False,
        system_language: str | None = None,
        id: str | None = "app-page",
        **kwargs: Any,
    ) -> None:
        super().__init__(id=id, **kwargs)
        self.script_info = script_info
        self.translations = translations or {}
        self._installed = installed
        self._system_language = _norm_lang(
            system_language
            if system_language is not None
            else os.environ.get("LANG", "")
        )

        self._source_options = [
            o
            for o in (script_info.get("source_options") or ())
            if isinstance(o, Mapping)
        ]
        self._selected: Mapping[str, Any] = script_info
        if self._source_options:
            recommended = self._recommended_source()
            self._selected = next(
                (
                    o
                    for o in self._source_options
                    if self._source_key(o) == recommended
                ),
                self._source_options[0],
            )

        self._blocks = (
            script_info.get("long_description_blocks")
            or script_info.get("long_description")
            or script_info.get("description")
            or ""
        )
        self._translated_blocks: Any = None
        self._showing_translation = False

        self._user_rating: int | None = script_info.get("user_rating")
        self._rated = self._user_rating is not None
        self._can_rate = False
        self._rating_busy = False
        self._pending_stars: int | None = None
        self._snap_vote_synced: set[str] = set()

        self._extensions = self._load_extensions()
        self._extension_jobs: list[Mapping[str, Any]] = []
        self._extensions_populated = False

        current = _script_key(script_info)
        category = script_info.get("category")
        cands = [f for f in (featured or ()) if _script_key(f) != current]
        cands.sort(
            key=lambda f: (
                0 if category and f.get("category") == category else 1
            )
        )
        self._featured = cands
        self._featured_signature: tuple | None = None
        self._featured_timer = None
        self._purchase_options: dict[str, list] = {}
        self._previous_border_title: Any = None

    def _t(self, key: str, default: str) -> str:
        return self.translations.get(key, default)

    def _recommended_source(self) -> str:
        return str(
            self.script_info.get("recommended_source")
            or self.script_info.get("appstream_source")
            or ""
        )

    @staticmethod
    def _source_key(entry: Mapping[str, Any]) -> str:
        source = str(entry.get("appstream_source", "") or "").strip()
        if source != "flatpak":
            return source
        return "flatpak:{}:{}".format(
            str(entry.get("flatpak_scope", "") or "").strip(),
            str(entry.get("flatpak_installation", "") or "").strip(),
        )

    def _has_multiple_flatpak_scopes(self) -> bool:
        scopes = {
            str(o.get("flatpak_scope", "") or "").strip()
            for o in self._source_options
            if str(o.get("appstream_source", "") or "").strip() == "flatpak"
        }
        scopes.discard("")
        return len(scopes) > 1

    def _source_label(self, entry: Mapping[str, Any]) -> str:
        source = str(entry.get("appstream_source", "") or "").strip()
        if source == "flatpak":
            scope = str(entry.get("flatpak_scope", "") or "").strip()
            if scope == "system" and self._has_multiple_flatpak_scopes():
                return (
                    f"Flathub ({self._t('app_page_source_system', 'system')})"
                )
            return "Flathub"
        if source == "native":
            return self._t("app_page_source_native", "Native")
        if source == "snap":
            return "Snap"
        if source == "aur":
            return "AUR"
        return source.capitalize() or self._t(
            "app_page_source_native", "Native"
        )

    def _is_snap(self) -> bool:
        return (
            str(self._selected.get("appstream_source", "") or "").strip()
            == "snap"
        )

    def _name_text(self) -> Text:
        """Build the header text: bold name plus dimmed license."""
        text = Text()
        text.append(str(self.script_info.get("name", "") or ""), style="bold")
        license_name = str(self.script_info.get("license", "") or "").strip()
        if license_name:
            text.append(" · " + license_name, style="dim")
        return text

    def _developer_text(self) -> Text | None:
        """Build the developer line, or None without a developer.

        The marker shows the trust level: a green check for official or
        verified entries, a cyan diamond for LinuxToys scripts and
        repository entries, and a dimmed diamond for AppStream entries.
        """
        info = self.script_info
        developer = str(info.get("developer", "") or "").strip()
        if not developer:
            return None
        text = Text()
        if info.get("is_official") or info.get("is_verified"):
            text.append("✔ ", style="bold green")
        elif info.get("is_repo_entry") or info.get("is_script"):
            text.append("◆ ", style="bold cyan")
        elif info.get("is_appstream_entry"):
            text.append("◈ ", style="dim")
        text.append(developer)
        return text

    def _meta_text(self) -> Text | None:
        """Build the repository and rating line, or None if empty.

        The rating applies only to AppStream entries. ``review_rating``
        is on a 0 to 100 scale and is shown as stars out of 5, followed
        by the review count. Invalid ratings and zero counts are hidden.
        """
        info = self.script_info
        text = Text()
        repo = str(info.get("repo", "") or "").strip()
        if repo:
            text.append(repo, style="dim")
        if info.get("is_appstream_entry"):
            try:
                rating = float(info.get("review_rating"))
                count = int(info.get("review_count"))
            except (TypeError, ValueError):
                rating, count = -1.0, 0
            if count > 0 and 0.0 <= rating <= 100.0:
                if text.plain:
                    text.append("   ")
                text.append(f"★ {rating / 20.0:.1f}", style="bold yellow")
                text.append(f" ({count})")
        return text if text.plain else None

    def _commerce_label(
        self, kind: str, options: Sequence[Mapping[str, Any]]
    ) -> str:
        """Build the label of a purchase or subscription control.

        Without options, the plain label is used. Otherwise the
        translated template gets the lowest price, prefixed by "from"
        when there are several options.

        Args:
            kind: ``"purchase"`` or ``"subscription"``.
            options: Option mappings with a ``price``.

        Returns:
            The label text.
        """
        if kind == "purchase":
            plain_k, plain_d = "app_page_purchase", "Purchase"
            price_k, price_d = "app_page_purchase_price", "Purchase · ${price}"
        else:
            plain_k, plain_d = "app_page_subscribe", "Subscribe"
            price_k, price_d = (
                "app_page_subscribe_price",
                "Subscribe · ${price}",
            )
        if not options:
            return self._t(plain_k, plain_d).strip()
        lowest = min(options, key=lambda o: o["price"])
        price_text = _fmt_price(lowest)
        if len(options) > 1:
            price_text = self._t(
                "app_page_from_price", "from ${price}"
            ).replace("${price}", price_text)
        template = self._t(price_k, price_d)
        return template.replace("${price}", price_text).strip()

    def _option_label(self, kind: str, option: Mapping[str, Any]) -> str:
        """Build the label of one option in a purchase selector.

        Joins, with ``" · "``, the option name, the duration (only for
        subscriptions with a positive ``months``) and the price.
        """
        pieces = []
        name = str(option.get("name") or "").strip()
        if name:
            pieces.append(name)
        months = option.get("months")
        if kind == "subscription" and isinstance(months, int) and months > 0:
            unit = (
                self._t("app_page_month", "month")
                if months == 1
                else self._t("app_page_months", "months")
            )
            pieces.append(f"{months} {unit}")
        pieces.append(_fmt_price(option))
        return " · ".join(pieces)

    def _commerce_widget(
        self, kind: str, options: list, fallback_url: str
    ) -> Widget:
        """Build the purchase or subscription control.

        Several options produce a ``Select`` (ids ``app-<kind>-select``),
        and choosing one posts ``UrlRequested``. One option, or none,
        produces a ``Button`` (id ``app-<kind>``) whose ``url`` attribute
        holds the option URL or ``fallback_url``.

        Args:
            kind: ``"purchase"`` or ``"subscription"``.
            options: Option mappings with ``price`` and ``url``.
            fallback_url: URL used when there are no options.

        Returns:
            The ``Select`` or ``Button``.
        """
        label = self._commerce_label(kind, options)
        if len(options) > 1:
            self._purchase_options[kind] = options
            return Select(
                [
                    (self._option_label(kind, o), i)
                    for i, o in enumerate(options)
                ],
                prompt=label,
                allow_blank=True,
                id=f"app-{kind}-select",
                classes="act-select",
            )
        url = options[0]["url"] if options else fallback_url
        button = Button(f"🛒 {label}", variant="primary", id=f"app-{kind}")
        button.url = url  # type: ignore[attr-defined]
        return button

    def compose(self) -> ComposeResult:
        with Horizontal(id="app-top"):
            yield Button("←", id="app-back", tooltip=self._t("back", "Back"))
            yield Static(self._name_text(), id="app-name")

        developer = self._developer_text()
        if developer is not None:
            yield Static(developer, id="app-developer")

        description = self._description_text()
        if description is not None:
            yield Static(description, id="app-description-short")
        meta = self._meta_text()
        if meta is not None:
            yield Static(meta, id="app-meta")

        yield Horizontal(
            *self._primary_actions(),
            *self._link_actions(),
            classes="app-row",
            id="app-actions",
        )
        yield self._rating_row()
        yield self._rating_confirm_row()

        with TabbedContent(
            id="app-tabs", classes="" if self._extensions else "no-ext"
        ):
            with TabPane(
                self._t("app_page_details", "Details"), id="tab-details"
            ):
                yield self._build_content()
            if self._extensions:
                yield self._extensions_pane()

    def _primary_actions(self) -> list[Widget]:
        """Build the install and remove buttons and the source selector."""

        install = Button(
            "⬇ " + self._t("skills_install_label", "Install").strip(),
            variant="success",
            id="app-install",
        )
        install.display = not self._installed
        remove = Button(
            "🗑 " + self._t("app_page_remove", "Remover").strip(),
            variant="error",
            id="app-remove",
        )
        remove.display = self._installed
        widgets: list[Widget] = [install, remove]

        if len(self._source_options) >= 2:
            recommended = self._recommended_source()
            options = []
            for i, entry in enumerate(self._source_options):
                mark = "◆ " if self._source_key(entry) == recommended else ""
                options.append((mark + self._source_label(entry), i))
            current = self._source_options.index(self._selected)
            widgets.append(
                Select(
                    options,
                    value=current,
                    allow_blank=False,
                    id="app-source",
                    classes="act-select",
                )
            )
        return widgets

    def _link_actions(self) -> list[Widget]:
        """Build the purchase, subscription, website and donate controls."""
        info = self.script_info
        purchase_url = info.get("purchase_url") or ""
        purchase = list(info.get("purchase_options") or [])
        subscription = list(info.get("subscription_options") or [])
        if (
            not purchase
            and purchase_url
            and info.get("purchase_price") is not None
        ):
            purchase = [
                {
                    "name": "",
                    "price": info["purchase_price"],
                    "url": purchase_url,
                    "currency_symbol": info.get("purchase_currency_symbol")
                    or "$",
                }
            ]
        if (
            not subscription
            and purchase_url
            and info.get("subscription_price") is not None
        ):
            subscription = [
                {
                    "name": "",
                    "months": 1,
                    "price": info["subscription_price"],
                    "url": purchase_url,
                    "currency_symbol": info.get("subscription_currency_symbol")
                    or "$",
                }
            ]

        widgets: list[Widget] = []
        if purchase:
            widgets.append(
                self._commerce_widget("purchase", purchase, purchase_url)
            )
        if subscription:
            widgets.append(
                self._commerce_widget(
                    "subscription", subscription, purchase_url
                )
            )
        if purchase_url and not purchase and not subscription:
            widgets.append(self._commerce_widget("purchase", [], purchase_url))

        homepage = info.get("homepage_url") or ""
        if homepage:
            b = Button(
                "🌐 " + self._t("app_page_homepage", "Website").strip(),
                id="app-homepage",
            )
            b.url = homepage  # type: ignore[attr-defined]
            widgets.append(b)
        donate = info.get("donate_url") or ""
        if donate:
            only = not purchase_url and not purchase and not subscription
            b = Button(
                "♥ " + self._t("app_page_donate", "Donate").strip(),
                variant="primary" if only else "default",
                id="app-donate",
            )
            b.url = donate  # type: ignore[attr-defined]
            widgets.append(b)
        return widgets

    def _rating_row(self) -> Horizontal:
        """Build the hidden row of five rating buttons.
        Visibility and labels are managed by ``_refresh_rating``.
        """
        row = Horizontal(
            Label(self._t("app_page_rate", "Rate:")),
            *[Button("☆", id=f"app-rate-{i}") for i in range(1, 6)],
            id="app-rating",
            classes="app-row",
        )
        row.display = False
        return row

    def _rating_confirm_row(self) -> Horizontal:
        """Build the hidden rating confirmation row (text, Submit, Cancel)."""
        row = Horizontal(
            Static(id="app-rating-confirm-text"),
            Button(
                self._t("app_page_rate_submit", "Submit"),
                variant="success",
                id="app-rating-submit",
            ),
            Button(
                self._t("cancel_btn_label", "Cancel"),
                id="app-rating-cancel",
            ),
            id="app-rating-confirm",
            classes="app-row",
        )
        row.display = False
        return row

    def _description_text(self) -> str | None:
        description = str(self.script_info.get("description") or "").strip()
        return description or None

    def _build_content(self) -> VerticalScroll:
        """Build the scrollable content of the Details tab."""
        children: list[Widget] = []

        desc_parts: list[Widget] = []
        if self._needs_translation():
            btn = Button(
                "文/A",
                id="app-translate",
                tooltip=self._t("app_page_translate", "Translate"),
            )
            desc_parts.append(Horizontal(btn, id="app-translate-row"))
        desc_parts.append(
            Static(blocks_to_text(self._blocks), id="app-description-text")
        )
        children.append(Vertical(*desc_parts, id="app-description"))

        if self._featured:
            children.append(
                Vertical(
                    Rule(),
                    Label(
                        self._t("featured_scripts", "Try These"),
                        id="app-featured-title",
                    ),
                    Grid(id="featured-grid"),
                    id="app-featured",
                )
            )
            children[-1].display = False
        return VerticalScroll(*children, id="app-content")

    def _load_extensions(self) -> list[Mapping[str, Any]]:
        """Mesma fonte da GUI: addons Flatpak da fonte selecionada."""
        return [
            dict(item)
            for item in appstream_cache.get_flatpak_extensions(
                dict(self._selected)
            )
            or ()
        ]

    def _extensions_pane(self) -> TabPane:
        return TabPane(
            self._t("app_page_extensions", "Extensions"),
            VerticalScroll(id="app-extensions"),
            id="tab-extensions",
        )

    def _extension_state(
        self,
        ref: str,
        installed: set[str],
        jobs: Mapping[str, Mapping[str, Any]],
    ) -> tuple[str, Mapping[str, Any] | None]:
        """Resolve the display state of an extension.

        A queued or running job overrides the installed state. A job
        whose action is ``extension_remove`` becomes ``"removing"``.
        """
        state = "installed" if ref in installed else "available"
        record = jobs.get(ref)
        if record and record.get("status") in ("queued", "running"):
            state = (
                "removing"
                if record.get("action") == "extension_remove"
                else record["status"]
            )
        return state, record

    def _extension_row(
        self,
        info: Mapping[str, Any],
        ref: str,
        state: str,
        record: Mapping[str, Any] | None,
    ) -> Horizontal:
        """Build one row of the Extensions tab."""
        views = {
            "available": (
                str(info.get("summary") or ""),
                "⬇ " + self._t("skills_install_label", "Install").strip(),
                "success",
                "install",
            ),
            "installed": (
                self._t("app_page_installed", "Installed"),
                "🗑 " + self._t("skills_remove_label", "Remove").strip(),
                "error",
                "remove",
            ),
            "queued": (
                self._t("queued", "Waiting to install"),
                self._t("cancel_btn_label", "Cancel"),
                "default",
                "cancel",
            ),
            "removing": (
                self._t("skills_removing", "Removing…"),
                "…",
                "default",
                None,
            ),
            "running": (
                self._t("skills_installing", "Installing…"),
                "…",
                "default",
                None,
            ),
        }
        secondary, label, variant, action = views[state]
        name = str(info.get("name") or info.get("id") or ref)
        text = Text(name, style="bold")
        if secondary:
            text.append("\n" + secondary, style="dim")
        button = Button(label, variant=variant, disabled=action is None)
        button.ext_action = (action, info, record)  # type: ignore[attr-defined]
        return Horizontal(
            Static(text, classes="ext-info"), button, classes="ext-row"
        )

    def refresh_extensions(
        self, jobs: Sequence[Mapping[str, Any]] | None = None
    ) -> None:
        """Update the Extensions tab with the current jobs.

        Nothing is rendered until the tab has been opened once.

        Args:
            jobs: Runner job snapshot (``runner.snapshot()``). None keeps
                the previous snapshot.
        """
        if jobs is not None:
            self._extension_jobs = list(jobs)
        if self._extensions_populated:
            self._render_extensions()

    @work(exclusive=True, group="extensions")
    async def _render_extensions(self) -> None:
        """Rebuild the rows of the Extensions tab.

        Worker. Reads the installed refs in a thread, matches job records
        by ``info.flatpak_ref`` (the first record of each ref wins),
        derives each state and replaces the rows. It is exclusive, so a
        newer refresh cancels a stale one.
        """
        installed = await asyncio.to_thread(
            appstream_cache.installed_flatpak_extension_refs,
            dict(self._selected),
        )
        jobs: dict[str, Mapping[str, Any]] = {}
        for record in self._extension_jobs:
            ref = str(
                (record.get("info") or {}).get("flatpak_ref") or ""
            ).strip()
            if ref:
                jobs.setdefault(ref, record)

        rows = []
        for info in self._extensions:
            ref = str(info.get("flatpak_ref") or "").strip()
            if ref:
                state, record = self._extension_state(ref, installed, jobs)
                rows.append(self._extension_row(info, ref, state, record))
        container = self.query_one("#app-extensions", VerticalScroll)
        await container.remove_children()
        await container.mount_all(rows)

    async def _sync_extensions_tabs(self) -> None:
        """Show the Extensions tab only if the source has extensions.

        Reloads the extensions, adds or removes the pane as needed, and
        toggles the ``no-ext`` class that hides the tab bar. If the
        Extensions tab is already active, it is populated again.
        """
        self._extensions = self._load_extensions()
        self._extensions_populated = False
        tabs = self.query_one("#app-tabs", TabbedContent)
        has_pane = bool(self.query("#tab-extensions"))
        if self._extensions and not has_pane:
            await tabs.add_pane(self._extensions_pane())
        elif not self._extensions and has_pane:
            await tabs.remove_pane("tab-extensions")
        tabs.set_class(not self._extensions, "no-ext")
        if self._extensions and tabs.active == "tab-extensions":
            self._populate_extensions()

    def _populate_extensions(self) -> None:
        """Render the extension rows on the first tab activation."""
        if not self._extensions_populated:
            self._extensions_populated = True
            self._render_extensions()

    def _extension_pressed(
        self,
        button: Button,
        action: str,
        info: Mapping[str, Any],
        record: Mapping[str, Any] | None,
    ) -> None:
        """Handle a press on an extension row button.

        The button is disabled at once to prevent double actions. Then
        the matching message is posted: ``ExtensionInstallRequested``,
        ``ExtensionRemoveRequested`` (with the job id only if the record
        is a successful job) or ``ExtensionCancelRequested``.

        Args:
            button: The pressed button.
            action: ``"install"``, ``"remove"`` or ``"cancel"``.
            info: Extension info.
            record: Matching job record, or None.
        """
        button.disabled = True
        if action == "install":
            self.post_message(
                self.ExtensionInstallRequested(
                    {**info, "is_flatpak_extension": True}
                )
            )
        elif action == "remove":
            done = record is not None and record.get("status") == "success"
            self.post_message(
                self.ExtensionRemoveRequested(
                    dict(info), record["id"] if done else None
                )
            )
        elif action == "cancel" and record is not None:
            self.post_message(self.ExtensionCancelRequested(record["id"]))

    def _needs_translation(self) -> bool:
        info = self.script_info
        if info.get("appstream_source") != "flatpak":
            return bool(info.get("is_appstream_entry", True)) and bool(
                self._blocks
            )
        source = _norm_lang(info.get("long_description_locale"))
        return bool(
            source
            and self._system_language
            and source != self._system_language
        )

    def on_mount(self) -> None:
        self._refresh_rating()
        self._load_rating_state()
        self.call_after_refresh(self._schedule_featured)
        self.call_after_refresh(self._focus_first)

    def _focus_first(self) -> None:
        try:
            self.query_one(
                "#app-install" if not self._installed else "#app-open"
            ).focus()
        except Exception:
            pass

    def on_resize(self) -> None:
        self._schedule_featured()

    @on(TabbedContent.TabActivated)
    def _tab_changed(self) -> None:
        """Populate the Extensions tab when opened and re-layout the grid."""
        tabs = self.query_one("#app-tabs", TabbedContent)
        if tabs.active == "tab-extensions":
            self._populate_extensions()
        self._featured_signature = None
        self._schedule_featured()

    def set_install_state(self, installed: bool) -> None:
        """Update the page after the install state changed."""
        self._installed = installed
        self.query_one("#app-install").display = not installed
        self.query_one("#app-remove").display = installed
        self._refresh_rating()
        self._load_rating_state()

    def set_user_rating(self, stars: int | None) -> None:
        """Set the rating already submitted by the user."""
        self._user_rating = stars
        self._rated = stars is not None
        self._refresh_rating()

    def set_translated_blocks(self, blocks: Any) -> None:
        """Receive the translation result from the host.

        Re-enables the translate button. On success the translated
        description is stored and shown. On failure (None) the original
        text stays and the button tooltip reports the error.

        Args:
            blocks: Translated str or blocks, or None on failure.

        Raises:
            NoMatches: If the page has no translate button.
        """
        btn = self.query_one("#app-translate", Button)
        btn.disabled = False
        btn.label = "文/A"
        if blocks is None:
            btn.tooltip = self._t(
                "app_page_translate_failed", "Translation failed. Try again."
            )
            return
        self._translated_blocks = blocks
        self._show_description(translated=True)

    def _show_description(self, *, translated: bool) -> None:
        blocks = self._translated_blocks if translated else self._blocks
        self.query_one("#app-description-text", Static).update(
            blocks_to_text(blocks)
        )
        self._showing_translation = translated
        btn = self.query_one("#app-translate", Button)
        btn.tooltip = (
            self._t("app_page_show_original", "Show original")
            if translated
            else self._t("app_page_translate", "Translate")
        )
        self._featured_signature = None
        self.call_after_refresh(self._schedule_featured)

    def _rating_supported(self) -> bool:
        """Return True if the app can be rated.

        Same rule as the GUI: only AppStream entries, and never the
        Homebrew source.
        """
        return bool(
            self.script_info.get("is_appstream_entry")
            and self._selected.get("appstream_source") != "homebrew"
        )

    def _refresh_rating(self) -> None:
        try:
            row = self.query_one("#app-rating")
        except NoMatches:
            return
        row.display = self._installed and self._rating_supported()
        snap = self._is_snap()
        tooltip = self._t("app_page_rate_stars", "Rate {stars} stars")
        blocked = (
            not self._installed
            or self._rated
            or self._rating_busy
            or not self._can_rate
        )
        for i in range(1, 6):
            btn = self.query_one(f"#app-rate-{i}", Button)
            if snap:
                btn.display = i in (1, 5)
                btn.label = "👎" if i == 1 else "👍"
                btn.tooltip = "Do not recommend" if i == 1 else "Recommend"
            else:
                btn.display = True
                shown = self._rated and i <= (self._user_rating or 0)
                btn.label = "★" if shown else "☆"
                btn.tooltip = tooltip.format(stars=i)
            btn.disabled = blocked
        row.tooltip = (
            self._t("app_page_rate_done", "You have already rated this app.")
            if self._rated
            else None
        )

    def _rating_app_id(self) -> str:
        info = self.script_info
        return str(info.get("appstream_id") or info.get("id") or "").strip()

    def _snap_identity(self) -> tuple[str, str]:
        info = self._selected
        return (
            str(info.get("snap_id", "") or "").strip(),
            str(
                info.get("snap_name", "") or info.get("package-name", "") or ""
            ).strip(),
        )

    def _read_rating_state(
        self, snap: bool, installed: bool
    ) -> tuple[bool, int | None, bool]:
        """(já avaliou, estrelas enviadas, pode avaliar). Roda em thread."""
        if snap:
            snap_id, snap_name = self._snap_identity()
            if installed and snap_id and snap_id not in self._snap_vote_synced:
                self._snap_vote_synced.add(snap_id)
                appstream_cache.sync_snap_vote(snap_id)
            revision = (
                appstream_cache.get_snap_installed_revision(snap_name)
                if installed and snap_name
                else None
            )
            rated = bool(
                snap_id
                and revision
                and appstream_cache.get_submitted_snap_vote(snap_id, revision)
                is not None
            )
            return rated, None, bool(snap_id and snap_name and revision)
        app_id = self._rating_app_id()
        rated = bool(app_id) and appstream_cache.has_submitted_odrs_rating(
            app_id
        )
        stars = (
            appstream_cache.get_submitted_odrs_rating(app_id)
            if rated
            else None
        )
        return rated, stars, bool(app_id) and not rated

    @work(exclusive=True, group="rating-state")
    async def _load_rating_state(self) -> None:
        if not self._rating_supported():
            return
        state = await asyncio.to_thread(
            self._read_rating_state, self._is_snap(), self._installed
        )
        self._rated, self._user_rating, self._can_rate = state
        self._refresh_rating()

    def _rating_summary(self, stars: int) -> str:
        presets = {
            5: ("app_page_rate_5", "Excellent, this app is a must have!!"),
            4: ("app_page_rate_4", "Very good app. Give it a try."),
            3: ("app_page_rate_3", "Decent pick."),
            2: ("app_page_rate_2", "Needs improvements..."),
            1: ("app_page_rate_1", "Had issues."),
        }
        return self._t(*presets[stars])

    def _rating_confirm_text(self, stars: int) -> Text:
        text = Text(
            self._t("app_page_rate_confirm_title", "Submit Rating?"),
            style="bold",
        )
        if self._is_snap():
            vote = "👍 Recommend" if stars == 5 else "👎 Do not recommend"
            text.append("\n" + vote)
        else:
            warning = (
                self._t(
                    "app_page_rate_confirm_message",
                    "This rating cannot be changed or retracted after it is "
                    "submitted.",
                )
                .replace("\\n", "\n")
                .split("\n\n", 1)[0]
                .strip()
            )
            text.append("\n" + "★" * stars + "☆" * (5 - stars), style="yellow")
            text.append("\n" + warning, style="dim")
        return text

    def _ask_rating_confirmation(self, stars: int) -> None:
        if not self._installed or self._rating_busy or not self._can_rate:
            return
        self._pending_stars = stars
        self.query_one("#app-rating-confirm-text", Static).update(
            self._rating_confirm_text(stars)
        )
        self.query_one("#app-rating-confirm").display = True
        self.query_one("#app-rating-submit", Button).focus()

    def _close_rating_confirmation(self) -> None:
        self._pending_stars = None
        try:
            self.query_one("#app-rating-confirm").display = False
        except NoMatches:
            pass

    def _submit_rating(self) -> None:
        stars = self._pending_stars
        self._close_rating_confirmation()
        if stars is None:
            return
        self._rating_busy = True
        self._refresh_rating()
        self._submit_rating_worker(stars, self._is_snap())

    def _send_rating(self, stars: int, snap: bool) -> tuple[bool, Any]:
        """Envia a avaliação ao backend. Roda em thread."""
        if snap:
            snap_id, snap_name = self._snap_identity()
            revision = appstream_cache.get_snap_installed_revision(snap_name)
            if not snap_id or not snap_name or revision is None:
                return False, None
            voted = appstream_cache.get_submitted_snap_vote(snap_id, revision)
            if voted is not None:
                return False, None
            return appstream_cache.submit_snap_vote(
                snap_id, snap_name, stars == 5
            )
        return appstream_cache.submit_odrs_rating(
            self._rating_app_id(),
            stars,
            self._rating_summary(stars),
            self._t("app_page_rate_signature", "Submitted via LinuxToys"),
            str(self._selected.get("appstream_version", "") or "unknown"),
        )

    @work(group="rating-submit")
    async def _submit_rating_worker(self, stars: int, snap: bool) -> None:
        """Send the rating off the event loop and report the result.

        Worker. Shows a success notification or an error notification
        with the backend detail, then reloads the rating state.
        """
        success, error = await asyncio.to_thread(
            self._send_rating, stars, snap
        )
        self._rating_busy = False
        if success:
            key, default = (
                (
                    "app_page_rate_success_message_snap",
                    "Thank you! Your vote was submitted to Canonical Snap "
                    "ratings.",
                )
                if snap
                else (
                    "app_page_rate_success_message",
                    "Thank you! Your rating was submitted to ODRS.",
                )
            )
            title = self._t("app_page_rate_success_title", "Rating Submitted")
            self.app.notify(self._t(key, default), title=title)
        else:
            message = self._t(
                "app_page_rate_failed_message",
                "Could not submit the rating. Please try again later.",
            )
            self.app.notify(
                f"{message}\n\n{error}" if error else message,
                title=self._t("app_page_rate_failed_title", "Rating Failed"),
                severity="error",
            )
        self._load_rating_state()
        self._refresh_rating()

    def _schedule_featured(self) -> None:
        """Schedule a featured grid layout (debounced, 0.12 s).

        Does nothing without candidates or before the page is mounted.
        """
        if not self._featured or not self.is_mounted:
            return
        if self._featured_timer is not None:
            self._featured_timer.stop()
        self._featured_timer = self.set_timer(0.12, self._refresh_featured)

    def _refresh_featured(self) -> None:
        """Lay out the "Try These" grid in the free vertical space."""
        self._featured_timer = None
        try:
            box = self.query_one("#app-featured")
            scroller = self.query_one("#app-content", VerticalScroll)
            grid = self.query_one("#featured-grid", Grid)
        except Exception:
            return
        viewport_h = scroller.size.height
        width = scroller.size.width - (
            2 if scroller.show_vertical_scrollbar else 0
        )
        if viewport_h <= 1 or width <= 1:
            return

        used = 0
        for child in scroller.children:
            if child is not box:
                used += child.outer_size.height + child.styles.margin.height
        # Rule(1+margens) + título(1+2) = overhead fixo do bloco
        spare = viewport_h - used - 6
        rows = spare // CARD_HEIGHT
        if rows < 1:
            box.display = False
            self._featured_signature = None
            return

        gap = 1
        columns = max(
            1, min(MAX_COLUMNS, (width + gap) // (MIN_CARD_WIDTH + gap))
        )
        count = min(len(self._featured), rows * columns)
        signature = (columns, rows, count)
        if signature != self._featured_signature:
            self._featured_signature = signature
            grid.styles.grid_size_columns = columns
            grid.styles.grid_rows = str(CARD_HEIGHT)
            grid.styles.height = (
                (count + columns - 1) // columns
            ) * CARD_HEIGHT
            grid.remove_children()
            grid.mount(
                *[FeaturedCard(info) for info in self._featured[:count]]
            )
        box.display = True

    def action_back(self) -> None:
        self.post_message(self.BackRequested())

    @on(FeaturedCard.Selected)
    def _featured_selected(self, event: FeaturedCard.Selected) -> None:
        """Re-post a card selection as ``FeaturedSelected``."""
        event.stop()
        self.post_message(self.FeaturedSelected(event.script_info))

    @on(Button.Pressed)
    def _button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        bid = event.button.id or ""
        extension = getattr(event.button, "ext_action", None)
        if extension is not None:
            self._extension_pressed(event.button, *extension)
        elif bid == "app-back":
            self.post_message(self.BackRequested())
        elif bid == "app-install":
            event.button.disabled = True
            event.button.label = "..."
            self.post_message(self.InstallRequested(self._selected))
        elif bid == "app-open":
            self.post_message(self.OpenRequested(self._selected))
        elif bid == "app-remove":
            event.button.disabled = True
            event.button.label = "..."
            self.post_message(self.UninstallRequested(self._selected))
        elif bid == "app-rating-submit":
            self._submit_rating()
        elif bid == "app-rating-cancel":
            self._close_rating_confirmation()
        elif bid.startswith("app-rate-"):
            self._ask_rating_confirmation(int(bid.rsplit("-", 1)[1]))
        elif bid in (
            "app-purchase",
            "app-subscription",
            "app-homepage",
            "app-donate",
        ):
            url = getattr(event.button, "url", "")
            if url:
                self.post_message(self.UrlRequested(url))
        elif bid == "app-translate":
            self._on_translate_pressed(event.button)

    def reset_install_button(self) -> None:
        try:
            button = self.query_one("#app-install", Button)
        except NoMatches:
            return
        button.disabled = False
        button.label = (
            "⬇ " + self._t("skills_install_label", "Install").strip()
        )

    def reset_remove_button(self) -> None:
        """Reabilita e restaura o label do botão Remover, usado quando a
        remoção falha ou é cancelada."""
        try:
            button = self.query_one("#app-remove", Button)
        except NoMatches:
            return
        button.disabled = False
        button.label = "🗑 " + self._t("app_page_remove", "Remover").strip()

    def _on_translate_pressed(self, button: Button) -> None:
        if self._showing_translation:
            self._show_description(translated=False)
        elif self._translated_blocks is not None:
            self._show_description(translated=True)
        else:
            button.disabled = True
            button.label = "…"
            self.post_message(
                self.TranslateRequested(self._blocks, self._system_language)
            )

    @on(Select.Changed)
    async def _select_changed(self, event: Select.Changed) -> None:
        event.stop()
        sid = event.select.id or ""
        if sid == "app-source":
            if event.value is _BLANK:
                return
            self._selected = self._source_options[int(event.value)]
            self._close_rating_confirmation()
            self._rated, self._user_rating, self._can_rate = False, None, False
            self._refresh_rating()
            self._load_rating_state()
            await self._sync_extensions_tabs()
            self._featured_signature = None
            self._schedule_featured()
            self.post_message(self.SourceChanged(self._selected))
        elif sid in ("app-purchase-select", "app-subscription-select"):
            if event.value is _BLANK:
                return
            kind = (
                "purchase" if sid == "app-purchase-select" else "subscription"
            )
            url = self._purchase_options[kind][int(event.value)]["url"]
            event.select.clear()
            self.post_message(self.UrlRequested(url))


async def show_app_page(
    host: Widget,
    script_info: Mapping[str, Any],
    *,
    translations: Mapping[str, str] | None = None,
    featured: Sequence[Mapping[str, Any]] | None = None,
    installed: bool = False,
) -> AppPageWidget:
    """Esconde logo/menu/terminal do #menu-panel e monta a app page no lugar."""
    panel = host.query_one(MENU_PANEL)

    about_open = getattr(host, "_is_about_showing", False)
    if about_open and hasattr(host, "_toggle_about_panel"):
        host._toggle_about_panel(force_hide=True)
    if host.query_one(TERMINAL).display and hasattr(host, "_hide_terminal"):
        host._hide_terminal()

    previous_title = "Menu" if about_open else panel.border_title
    for old in list(host.query(AppPageWidget)):
        previous_title = old._previous_border_title
        await old.remove()

    page = AppPageWidget(
        script_info,
        translations=translations,
        featured=featured,
        installed=installed,
    )
    page._previous_border_title = previous_title

    host.query_one(LOGO).display = False
    host.query_one(LIST_VIEW).display = False
    host.query_one(TERMINAL).display = False
    panel.border_title = str(script_info.get("name") or "")

    await panel.mount(page)
    page.display = True
    return page


async def hide_app_page(host: Widget) -> None:
    """Remove a app page e restaura logo e menu."""
    panel = host.query_one(MENU_PANEL)
    for page in list(host.query(AppPageWidget)):
        panel.border_title = page._previous_border_title
        await page.remove()
    host.query_one(LOGO).display = True
    host.query_one(LIST_VIEW).display = True
    try:
        host.query_one(LIST_VIEW).focus()
    except Exception:
        pass
