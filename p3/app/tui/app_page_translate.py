"""Translate AppStream descriptions for the TUI app page.

Thin adapter over the shared ``app.translate_helper`` pipeline: the GUI,
MCP server and TUI all use the same Google endpoint, span/block traversal
and on-disk cache (``appstream_cache.CACHE_DIR / "translations"``), so a
translation cached by one interface is reused by the others.

Only the entry-info cache-key mapping (``appstream_id`` falling back to
``id``) and the plain-text shortcut live here. Functions that use the
network are BLOCKING and must run in a worker thread.
"""

from __future__ import annotations

import json
from typing import Any

from app import translate_helper


def _app_id(info: dict) -> str:
    """Cache-key id for an entry: ``appstream_id`` falling back to ``id``."""
    return str(info.get("appstream_id") or info.get("id") or "").strip()


def google_translate_text(text: str, target_language: str) -> str:
    """Translate text through the shared Google endpoint.

    BLOCKING: call from a worker thread (network, 20 s timeout). The
    source language is auto-detected; blank text passes through
    unchanged. Raises ``RuntimeError``/``ValueError`` like the shared
    implementation.
    """
    return translate_helper.translate_text(text, target_language)


def translate_description_blocks(blocks: Any, target: str) -> Any:
    """Translate an AppStream description, keeping its structure.

    BLOCKING: call from a worker thread (one network call per span).

    Plain-text (``str``) input is translated as a whole; block lists keep
    their structure — ``paragraph`` spans and every list item are
    translated, ``code`` spans stay verbatim, other block types are
    copied unchanged. The input is not mutated.
    """
    if isinstance(blocks, str):
        return translate_helper.translate_text(blocks, target)
    return translate_helper.translate_blocks(blocks, target)


def load_cached_translation(info: dict, blocks: Any, target: str) -> Any:
    """Load a cached translation (list or str), or ``None``.

    ``None`` also covers missing, unreadable, corrupt or unexpected-typed
    entries.
    """
    path = translate_helper.translation_cache_path(_app_id(info), blocks, target)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            value = json.load(fh)
        return value if isinstance(value, (list, str)) else None
    except (OSError, ValueError, TypeError):
        return None


def save_cached_translation(
    info: dict, blocks: Any, target: str, translated: Any
) -> None:
    """Store a translation in the cache, on a best-effort basis.

    The write is atomic (staged temporary file + replace); I/O errors are
    ignored: a failed write only means the translation is not cached.
    """
    translate_helper.save_cached_description_translation(_app_id(info), blocks, translated, target)
