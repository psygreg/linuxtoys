#!/usr/bin/env python3
"""Residual user data of uninstalled Flatpak apps: ~/.var/app/<AppID>.

Uninstalling a Flatpak app never removes its per-user data directory under
~/.var/app, so apps the user no longer has installed keep littering personal
storage. The GUI offers a "Remove data" action on such an app's page
(app_page.py), and the MCP server exposes the same cleanup to AI agents
(mcp_server.py). This module is the single source of truth for that cleanup's
safety rules — both callers import it so their behavior never drifts apart:

- Identity: AppStream IDs for Flatpak applications are normally the Flatpak
  app ID; candidates are regex-gated to a reference-style ID shape, and a
  trailing .desktop suffix is dropped.
- Boundary: the only removable path is ~/.var/app/<AppID>, where <AppID> is a
  validated identity. The path is built, not resolved, and an explicit
  direct-child containment guard keeps that boundary honest even if the ID
  parser changes elsewhere.
- Removal: a symlink at the boundary is unlinked, not followed — the link
  itself is residual data; a directory is removed recursively; anything else
  left on the boundary is unlinked. Nothing outside it is ever touched.
"""

import os
import re
import shutil
from pathlib import Path

# Flatpak application IDs are dot-separated reference-style names (like
# org.videolan.VLC). Requiring a dot keeps single bare words, hidden/dot-prefixed
# entries and traversal fragments from ever becoming an identity.
FLATPAK_APP_ID_RE = re.compile(r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+$")


def flatpak_data_identity(info):
    """Return a safe Flatpak application ID for ~/.var/app/<ID>, or ""."""
    info = info if isinstance(info, dict) else {}
    if str(info.get("appstream_source", "") or "").strip() != "flatpak":
        return ""

    # AppStream IDs for Flatpak applications are normally the Flatpak app ID.
    # Prefer an explicit package/app ID if the catalog supplies one.
    candidates = (
        info.get("flatpak_id"),
        info.get("package-name"),
        info.get("appstream_id"),
        info.get("id"),
    )
    for value in candidates:
        value = str(value or "").strip()
        if value.endswith(".desktop"):
            value = value[:-8]
        if FLATPAK_APP_ID_RE.fullmatch(value):
            return value
    return ""


def flatpak_data_path(app_id):
    """Build, but never resolve through, the only directory we may remove."""
    if not app_id:
        return None
    base = Path.home() / ".var" / "app"
    target = base / app_id
    # app_id validation already forbids '/' and traversal. Keep this explicit
    # guard too so future changes to the ID parser cannot broaden the deletion
    # boundary behind this function's back.
    try:
        if target.parent != base or target.name != app_id:
            return None
    except (OSError, ValueError):
        return None
    return target


def residual_data_present(target):
    """Whether the residual path exists; never follows symlinks."""
    if target is None:
        return False
    try:
        return os.path.lexists(target)
    except OSError:
        return False


def remove_residual_data(target):
    """Remove the residual path; returns None on success or an error string.

    A symlink is unlinked rather than followed: the link itself is residual
    data, and its destination is outside what this cleanup may ever touch.
    """
    try:
        if target.is_symlink():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        elif os.path.lexists(target):
            target.unlink()
    except OSError as exc:
        return str(exc)
    return None
