"""LinuxToys URI parsing and stable target resolution.

This module is deliberately GUI-agnostic.  It validates browser-facing
``linuxtoys://`` install URIs and resolves their stable target IDs into the
same script-info dictionaries consumed by the normal LinuxToys UI. Nix targets
(``nix:<attr>`` and ``nix-flake:<reference>``) resolve even when the Nix
subsystem is not enabled yet, so the GUI can offer to prepare it first.
"""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from . import manifest_helper, parser


_TARGET_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._+-]{0,127}")
_NIX_PACKAGE_PREFIX = "nix:"
_NIX_FLAKE_PREFIX = "nix-flake:"
_NIX_ATTR_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'-]*")
_NIX_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_NIX_REFERENCE_MAX = 512


def parse_nix_target(target_id):
    """Parse a stable Nix target ID into its kind and value.

    Supported forms are ``nix:<attr>`` for a nixpkgs package and
    ``nix-flake:<reference>`` for a flake import. Flake references may contain
    URL separators; browsers must percent-encode characters that would
    otherwise start the outer URI's query or fragment.
    """
    if not isinstance(target_id, str):
        return None
    value = target_id.strip()
    if not value:
        return None

    if value.startswith(_NIX_FLAKE_PREFIX):
        reference = value[len(_NIX_FLAKE_PREFIX):]
        if not reference or reference != reference.strip():
            return None
        if len(reference) > _NIX_REFERENCE_MAX or _NIX_CONTROL_RE.search(reference):
            return None
        return {"kind": "flake", "reference": reference}

    if value.startswith(_NIX_PACKAGE_PREFIX):
        attr = value[len(_NIX_PACKAGE_PREFIX):]
        if not _NIX_ATTR_RE.fullmatch(attr):
            return None
        return {"kind": "package", "attr": attr}

    return None


def _is_nix_target(target_id):
    return isinstance(target_id, str) and target_id.strip().startswith(
        (_NIX_PACKAGE_PREFIX, _NIX_FLAKE_PREFIX)
    )


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

    if _is_nix_target(target):
        return target if parse_nix_target(target) is not None else None

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
    """Return arguments needed to resolve the same AppStream universe as the UI.

    Delegates to ``parser.appstream_context`` with the repository-entry set
    (``curated=False``), preserving the historical resolution scope.
    """
    return parser.appstream_context(translations, curated=False)


def find_appstream_entry_by_id(appstream_id, translations=None):
    """Resolve a stable AppStream component ID after LinuxToys source selection."""
    if not isinstance(appstream_id, str) or not appstream_id.strip():
        return None

    from . import appstream_parser

    scripts_dir, curated_entries, category_paths = _appstream_entries_context(translations)
    return appstream_parser.find_entry_by_id(
        scripts_dir,
        appstream_id,
        curated_entries,
        category_paths,
    )


def find_appstream_entry_by_name(name, translations=None):
    """Resolve an exact localized or canonical AppStream display name."""
    if not isinstance(name, str) or not name.strip():
        return None

    from . import appstream_parser

    scripts_dir, curated_entries, category_paths = _appstream_entries_context(translations)
    return appstream_parser.find_entry_by_name(
        scripts_dir,
        name,
        curated_entries,
        category_paths,
    )


def _default_nix_scope():
    """Pick the native scope an external Nix install should target."""
    try:
        from . import nix_catalog

        scopes = nix_catalog.scopes()
        if nix_catalog.is_nixos() and "system" in scopes:
            return "system"
        if "home-manager" in scopes:
            return "home-manager"
        if "system" in scopes:
            return "system"
        return "system" if nix_catalog.is_nixos() else "home-manager"
    except Exception:
        return "home-manager"


def _nix_package_uri_entry(attr, translations=None):
    from . import nix_catalog, nix_metadata, nix_registry

    appstream_id = f"nix:{attr}"
    if nix_catalog.enabled():
        try:
            entry = find_appstream_entry_by_id(appstream_id, translations)
        except Exception:
            entry = None
        if isinstance(entry, dict):
            candidates = [entry]
            candidates.extend(
                option
                for option in entry.get("source_options") or ()
                if isinstance(option, dict)
            )
            for candidate in candidates:
                if str(candidate.get("appstream_source") or "") != "nix":
                    continue
                candidate_attr = str(
                    candidate.get("nix_name")
                    or candidate.get("package-name")
                    or ""
                ).strip()
                if candidate_attr != attr:
                    continue
                candidate = dict(candidate)
                scope = str(candidate.get("nix_scope") or "").strip()
                if not scope:
                    scope = _default_nix_scope()
                    candidate["nix_scope"] = scope
                scopes = candidate.get("nix_scopes")
                if not isinstance(scopes, list):
                    scopes = []
                if scope not in scopes:
                    scopes.insert(0, scope)
                candidate["nix_scopes"] = scopes
                candidate.setdefault("registry_name", nix_registry.registry_name(attr))
                return candidate

    try:
        registry_name = nix_registry.registry_name(attr)
    except Exception:
        registry_name = f"Nix: {attr}"

    try:
        description = (translations or {}).get(
            "uri_nix_package_description",
            "Install '{name}' from nixpkgs.",
        ).format(name=attr)
    except Exception:
        description = f"Install '{attr}' from nixpkgs."

    info = {
        "name": attr,
        "description": description,
        "appstream_source": "nix",
        "appstream_id": appstream_id,
        "nix_name": attr,
        "nix_scope": _default_nix_scope(),
        "nix_scopes": [],
        "icon": "nix.svg",
        "repo": "nixpkgs",
        "path": "",
        "is_script": True,
        "is_appstream_entry": True,
        "revert": "yes",
        "reboot": "no",
        "registry_name": registry_name,
    }
    info["nix_scopes"] = [info["nix_scope"]]
    try:
        info = nix_metadata.enrich_index(info) or info
    except Exception:
        pass
    return info


def _nix_flake_uri_entry(reference, translations=None):
    from . import nix_flakes

    try:
        normalized = nix_flakes.validate_reference(reference)
    except Exception:
        return None

    name = normalized
    description = ""
    try:
        for record in nix_flakes.imports():
            values = {
                str(record.get("reference") or "").strip(),
                str(record.get("original_url") or "").strip(),
                str(record.get("url") or "").strip(),
            }
            if normalized not in values:
                continue
            description = str(record.get("description") or "").strip()
            if description:
                name = description
            break
    except Exception:
        pass

    if not description:
        try:
            description = (translations or {}).get(
                "uri_nix_flake_description",
                "Import this Nix flake into the LinuxToys Nix configuration.",
            )
        except Exception:
            description = "Import this Nix flake into the LinuxToys Nix configuration."

    return {
        "name": name,
        "description": description,
        "appstream_source": "nix-flake",
        "appstream_id": f"nix-flake:{normalized}",
        "nix_flake_reference": normalized,
        "icon": "nix.svg",
        "repo": normalized if normalized.startswith(("http://", "https://")) else "",
        "path": "",
        "is_script": True,
        "is_appstream_entry": True,
        "revert": "no",
        "reboot": "no",
    }


def _resolve_nix_target(target_id, translations=None):
    parsed = parse_nix_target(target_id)
    if parsed is None:
        return None
    if parsed["kind"] == "package":
        return _nix_package_uri_entry(parsed["attr"], translations)
    return _nix_flake_uri_entry(parsed["reference"], translations)


def resolve_install_target(target_id, translations=None):
    """Resolve a browser-facing stable ID, with curated LinuxToys entries first.

    Existing script/repository-list IDs retain priority.  AppStream component IDs
    are a fallback, so adding a distro catalog can never override an explicitly
    curated LinuxToys target using the same identifier. Nix targets are
    resolved without requiring the subsystem to be enabled so the caller can
    offer to prepare it first.
    """
    if not isinstance(target_id, str):
        return None

    target_id = target_id.strip()
    if not target_id:
        return None

    if _is_nix_target(target_id):
        return _resolve_nix_target(target_id, translations)

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
