"""Translate AppStream descriptions for the TUI app page.

Port of the translation logic of the GUI ``AppPageView``, without GTK.
Text goes through Google Translate, and results are cached on disk
under ``appstream_cache.CACHE_DIR / "translations"``. Functions that
use the network are BLOCKING and must run in a worker thread.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app import appstream_cache


def google_translate_text(text: str, target_language: str) -> str:
    """Translate text with the unofficial Google Translate endpoint.

    BLOCKING: call from a worker thread (network, 20 s timeout).

    The source language is auto-detected. The endpoint is not a
    documented API, so it may be rate limited or change without notice.

    Args:
        text: Text to translate. None is treated as empty.
        target_language: Target language code, e.g. ``"pt"``.

    Returns:
        The translated text, or ``text`` unchanged if it is blank.

    Raises:
        RuntimeError: On an HTTP error or a connection failure.
        ValueError: If the response has no translation or is not
            valid JSON.
    """
    text = str(text or "")
    if not text.strip():
        return text
    data = urlencode(
        {
            "client": "gtx",
            "sl": "auto",
            "tl": target_language,
            "dt": "t",
            "q": text,
        }
    ).encode("utf-8")
    request = Request(
        "https://translate.googleapis.com/translate_a/single",
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) LinuxToys/1",
            "Accept": "application/json,text/plain,*/*",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Google Translate HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(
            f"Google Translate connection failed: {exc.reason}"
        ) from exc

    segments = payload[0] if isinstance(payload, list) and payload else []
    translated = "".join(
        str(seg[0])
        for seg in segments
        if isinstance(seg, list) and seg and seg[0] is not None
    )
    if not translated:
        raise ValueError("Google Translate returned an empty translation")
    return translated


def _translate_spans(spans: Any, target: str) -> list[dict]:
    """Translate the text of inline spans, leaving code spans intact.

    BLOCKING: makes one network call per translated span.

    Args:
        spans: Iterable of span dicts with ``text`` and an optional
            ``styles`` collection. None is treated as empty.
        target: Target language code.

    Returns:
        New span dicts. Spans styled ``"code"`` are copied untouched.

    Raises:
        RuntimeError: Propagated from ``google_translate_text``.
        ValueError: Propagated from ``google_translate_text``.
    """
    result = []
    for span in spans or ():
        item = dict(span)
        if "code" not in set(item.get("styles") or ()):
            item["text"] = google_translate_text(item.get("text", ""), target)
        result.append(item)
    return result


def translate_description_blocks(blocks: Any, target: str) -> Any:
    """Translate an AppStream description, keeping its structure.

    BLOCKING: call from a worker thread (one network call per span).

    Args:
        blocks: Plain text (str) or a list of block dicts. Spans of
            ``paragraph`` blocks and of every item of
            ``unordered_list`` and ``ordered_list`` blocks are
            translated. Other block types are copied unchanged.
        target: Target language code.

    Returns:
        A translated str for str input, otherwise a new list of
        blocks. The input is not mutated.

    Raises:
        RuntimeError: Propagated from ``google_translate_text``.
        ValueError: Propagated from ``google_translate_text``.
    """
    if isinstance(blocks, str):
        return google_translate_text(blocks, target)
    translated = []
    for block in blocks or ():
        copy_block = {"type": block.get("type")}
        kind = block.get("type")
        if kind == "paragraph":
            copy_block["spans"] = _translate_spans(block.get("spans"), target)
        elif kind in ("unordered_list", "ordered_list"):
            copy_block["items"] = [
                _translate_spans(item, target)
                for item in block.get("items") or ()
            ]
        else:
            copy_block.update(block)
        translated.append(copy_block)
    return translated


def _cache_path(info: dict, blocks: Any, target: str):
    """Return the cache file path for one translation.

    The file name is a SHA-256 hash of the AppStream id
    (``appstream_id``, falling back to ``id``), the target language
    and a canonical JSON digest of ``blocks``. Any change in the
    source text therefore produces a new entry.

    Args:
        info: Entry info dict.
        blocks: Source description (str or list of blocks).
        target: Target language code.

    Returns:
        A ``Path`` under ``CACHE_DIR/translations``. The file may not
        exist yet.
    """
    app_id = str(info.get("appstream_id") or info.get("id") or "").strip()
    payload = json.dumps(
        blocks or [], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    key = hashlib.sha256(
        f"{app_id}\0{target}\0{digest}".encode("utf-8")
    ).hexdigest()
    return appstream_cache.CACHE_DIR / "translations" / f"{key}.json"


def load_cached_translation(info: dict, blocks: Any, target: str) -> Any:
    """Load a cached translation, if any.

    Args:
        info: Entry info dict.
        blocks: Source description (str or list of blocks).
        target: Target language code.

    Returns:
        The cached list or str, or None if the entry is missing,
        unreadable, corrupt or of an unexpected type.
    """
    try:
        with open(
            _cache_path(info, blocks, target), "r", encoding="utf-8"
        ) as fh:
            value = json.load(fh)
        return value if isinstance(value, (list, str)) else None
    except (OSError, ValueError, TypeError):
        return None


def save_cached_translation(
    info: dict, blocks: Any, target: str, translated: Any
) -> None:
    """Store a translation in the cache, on a best-effort basis.

    Writes to a temporary file and moves it into place with
    ``os.replace``, so readers never see a partial file. I/O errors
    are ignored: a failed write only means the translation is not
    cached.

    Args:
        info: Entry info dict.
        blocks: Source description used to build the cache key.
        target: Target language code.
        translated: Translation to store (str or list of blocks).
    """
    path = _cache_path(info, blocks, target)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(
                translated, fh, ensure_ascii=False, separators=(",", ":")
            )
        os.replace(tmp, path)
    except OSError:
        pass
