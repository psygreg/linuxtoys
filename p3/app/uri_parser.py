"""LinuxToys URI parsing and stable target resolution.

This module is deliberately GUI-agnostic.  It validates browser-facing
``linuxtoys://`` install URIs and resolves their stable target IDs into the
same script-info dictionaries consumed by the normal LinuxToys UI.
"""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from . import manifest_helper, parser


_TARGET_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._+-]{0,127}")


def parse_install_uri(argument):
    """Return the stable LinuxToys target ID from a supported install URI."""
    try:
        parsed = urlparse(argument)
    except (TypeError, ValueError):
        return None

    if parsed.scheme.casefold() != "linuxtoys":
        return None
    if parsed.netloc.casefold() != "install":
        return None
    if parsed.query or parsed.fragment or parsed.params:
        return None

    target = unquote(parsed.path.lstrip("/"))

    # Repository-list names may contain spaces. Percent-decode first, then
    # retain the existing conservative character set. Encoded separators,
    # controls and leading/trailing whitespace remain invalid.
    if target != target.strip():
        return None
    if not _TARGET_RE.fullmatch(target):
        return None
    return target


def _appstream_entry_id(entry):
    """Return the stable AppStream component ID exposed by a resolved entry."""
    value = entry.get("appstream_id") or entry.get("appstream-id")
    if value:
        return str(value).strip()

    path = str(entry.get("path") or "")
    if path.startswith("appstream://"):
        # appstream://<source>/<component-id>
        remainder = path[len("appstream://"):]
        _source, separator, component_id = remainder.partition("/")
        if separator:
            return component_id.strip()
    return ""


def _appstream_entries_context(translations=None):
    """Return arguments needed to resolve the same AppStream universe as the UI."""
    return parser.SCRIPTS_DIR, parser.get_repo_entries(translations)


def find_appstream_entry_by_id(appstream_id, translations=None):
    """Resolve a stable AppStream component ID after LinuxToys source selection."""
    if not isinstance(appstream_id, str) or not appstream_id.strip():
        return None

    from . import appstream_parser

    scripts_dir, curated_entries = _appstream_entries_context(translations)
    return appstream_parser.find_entry_by_id(
        scripts_dir,
        appstream_id,
        curated_entries,
    )


def find_appstream_entry_by_name(name, translations=None):
    """Resolve an exact localized or canonical AppStream display name."""
    if not isinstance(name, str) or not name.strip():
        return None

    from . import appstream_parser

    scripts_dir, curated_entries = _appstream_entries_context(translations)
    return appstream_parser.find_entry_by_name(
        scripts_dir,
        name,
        curated_entries,
    )


def resolve_install_target(target_id, translations=None):
    """Resolve a browser-facing stable ID, with curated LinuxToys entries first.

    Existing script/repository-list IDs retain priority.  AppStream component IDs
    are a fallback, so adding a distro catalog can never override an explicitly
    curated LinuxToys target using the same identifier.
    """
    if not isinstance(target_id, str):
        return None

    target_id = target_id.strip()
    if not target_id:
        return None

    # Curated LinuxToys IDs retain absolute priority.
    entry = manifest_helper.find_script_by_id(target_id, translations)
    if entry is not None:
        return entry

    # Stable AppStream IDs remain valid and take precedence over display names.
    entry = find_appstream_entry_by_id(target_id, translations)
    if entry is not None:
        return entry

    # Pretty-name links use the same source-selected AppStream universe shown by
    # LinuxToys. Matching is exact apart from case, never fuzzy/substring based.
    return find_appstream_entry_by_name(target_id, translations)
