"""Runtime translation helpers shared by the app page and the MCP server.

GUI-free: every function here is safe to call from headless contexts
(CLI, TUI, MCP service) as well as from GTK widgets.
"""

import hashlib
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import appstream_cache
from .lang_utils import detect_system_language


def normalized_language(value):
    """Reduce a locale string ("pt_BR", "pt-BR") to its base language code."""
    value = str(value or "").strip().replace("_", "-")
    return value.split("-", 1)[0].casefold() if value else ""


def translation_cache_path(app_id, blocks, target_language):
    """Cache file path for one translated description (shared with the GUI)."""
    app_id = str(app_id or "").strip()
    target = normalized_language(target_language or detect_system_language())
    payload = json.dumps(
        blocks or [], ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    key = hashlib.sha256(f"{app_id}\0{target}\0{digest}".encode("utf-8")).hexdigest()
    cache_dir = appstream_cache.CACHE_DIR / "translations"
    return cache_dir / f"{key}.json"


def load_cached_description_translation(app_id, blocks, target_language=None):
    """Return the cached translated block list, or None."""
    path = translation_cache_path(app_id, blocks, target_language)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, list) else None
    except (OSError, ValueError, TypeError):
        return None


def save_cached_description_translation(app_id, blocks, translated, target_language=None):
    """Persist a translated block list next to the GUI's own cache."""
    path = translation_cache_path(app_id, blocks, target_language)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(translated, handle, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    except OSError:
        pass


def translate_text(text, target_language):
    """Best-effort translation through Google's public web endpoint.

    Use POST rather than putting the description in the URL. Besides avoiding
    URL-length failures, this behaves better with punctuation and non-ASCII
    AppStream prose. This remains an unofficial endpoint and may be throttled.
    """
    text = str(text or "")
    if not text.strip():
        return text

    data = urlencode({
        "client": "gtx",
        "sl": "auto",
        "tl": target_language,
        "dt": "t",
        "q": text,
    }).encode("utf-8")
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
        # Keep the concrete HTTP status in stderr; the UI remains best-effort.
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        raise RuntimeError(
            f"Google Translate HTTP {exc.code}: {detail or exc.reason}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Google Translate connection failed: {exc.reason}") from exc

    segments = payload[0] if isinstance(payload, list) and payload else []
    translated = "".join(
        str(segment[0]) for segment in segments
        if isinstance(segment, list) and segment and segment[0] is not None
    )
    if not translated:
        raise ValueError("Google Translate returned an empty translation")
    return translated


def translate_spans(spans, target_language):
    """Translate a description span list, keeping code spans verbatim."""
    result = []
    for span in spans or ():
        item = dict(span)
        styles = set(item.get("styles") or ())
        if "code" not in styles:
            item["text"] = translate_text(item.get("text", ""), target_language)
        result.append(item)
    return result


def translate_blocks(blocks, target_language):
    """Translate a structured description (paragraph and list blocks)."""
    translated = []
    for block in blocks or ():
        copy_block = {"type": block.get("type")}
        if block.get("type") == "paragraph":
            copy_block["spans"] = translate_spans(
                block.get("spans") or (), target_language
            )
        elif block.get("type") in ("unordered_list", "ordered_list"):
            copy_block["items"] = [
                translate_spans(item, target_language)
                for item in block.get("items") or ()
            ]
        else:
            copy_block.update(block)
        translated.append(copy_block)
    return translated
