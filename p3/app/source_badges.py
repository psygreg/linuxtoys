"""Source-badge hover descriptions shared by the GUI card factory and the app page.

Every source badge drawn in the top-right corner of a card (and beside the
developer line on the app page) carries a short hover description: the artwork
alone does not tell users which repository or store an entry comes from.
Descriptions are keyed by badge artwork and translated through the standard
language files; badges whose description is only a store's brand name
("Flathub", "FlatPark", "Homebrew", the "Snap Store") stay literal in every
language.
"""

from pathlib import PurePath

# Badge artwork identifier → (translation key, English floor). Identifiers are
# derived from the badge image path produced by ``get_icon_path``: the file
# stem, prefixed with the parent directory name when the artwork lives under
# ``distros/`` (which disambiguates the top-level icons/linuxtoys.svg). A key
# of ``None`` marks a literal description that must not be translated.
_BADGE_TOOLTIPS = {
    "ltverified": (
        "badge_tooltip_official",
        "Officially distributed by LinuxToys",
    ),
    "verified": (
        "badge_tooltip_flathub_verified",
        "Flathub, developer verified",
    ),
    "distros/linuxtoys": (
        "badge_tooltip_curated",
        "Curated by LinuxToys",
    ),
    "distros/arch": ("badge_tooltip_native", "Native package repository"),
    "distros/cachy": ("badge_tooltip_native", "Native package repository"),
    "distros/debian": ("badge_tooltip_native", "Native package repository"),
    "distros/fedora": ("badge_tooltip_native", "Native package repository"),
    "distros/manjaro": ("badge_tooltip_native", "Native package repository"),
    "distros/redhat": ("badge_tooltip_native", "Native package repository"),
    "distros/solus": ("badge_tooltip_native", "Native package repository"),
    "distros/suse": ("badge_tooltip_native", "Native package repository"),
    "distros/ubuntu": ("badge_tooltip_native", "Native package repository"),
    "distros/flathub": (None, "Flathub"),
    "distros/flatpark": (None, "FlatPark"),
    "appimages": ("badge_tooltip_appimage", "AppImage Community Catalog"),
    "aur": ("badge_tooltip_aur", "Arch User Repository"),
    "brew": (None, "Homebrew"),
    "snapbadge": (None, "Snap Store"),
}


def badge_tooltip_identifier(badge_path: str) -> str:
    """
    Return the badge artwork identifier for a badge image path.

    Args:
        badge_path: Badge image path as resolved by ``get_icon_path`` (the
            empty string is allowed and maps to "").

    Returns:
        str: Artwork identifier such as "ltverified" or "distros/flathub",
        or "" when no path is given.
    """
    if not badge_path:
        return ""
    path = PurePath(badge_path)
    parent = path.parent.name
    if parent == "distros":
        return f"distros/{path.stem}"
    return path.stem


def badge_tooltip_text(badge_path: str, translations: dict | None = None) -> str:
    """
    Return the hover description for a source badge image path.

    Args:
        badge_path: Badge image path as resolved by ``get_icon_path`` (the
            empty string is allowed and maps to "").
        translations: Loaded language dictionary; translatable descriptions
            fall back to the English floor when the key is missing.

    Returns:
        str: Translated (or literal) badge description, or "" when the
        artwork is unknown or no path is given.
    """
    entry = _BADGE_TOOLTIPS.get(badge_tooltip_identifier(badge_path))
    if entry is None:
        return ""
    key, english = entry
    if key is None:
        return english
    if translations:
        return str(translations.get(key, "") or english)
    return english
