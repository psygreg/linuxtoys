"""On-demand metadata enrichment for the Nix subsystem.

The nixpkgs snapshot built by ``nix search`` carries only names, versions and
short descriptions. The Nix Software API (api.nixsoftware.org) adds logos,
translated names, long descriptions, screenshots, categories, maintainers and
licenses.

Two cache layers keep this cheap:

* a small GUI-package index fetched once every 14 days (one paginated API
  sweep) and used to decorate browse/search cards;
* a per-package detail cache fetched when a metadata-bearing card becomes
  visible (prefetched off GTK) or, as a fallback, when its app page opens.

Both layers are optional: failures retain the previous cache and every caller
must work with unenriched entries.
"""

from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import logging
import os
import queue
import re
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from .atomic_io import atomic_write_json

API_BASE = "https://api.nixsoftware.org/api/v1"
API_HOST = "api.nixsoftware.org"
API_STORAGE_BASE = "https://api.nixsoftware.org/storage/"

_CACHE_ROOT = Path(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
) / "linuxtoys" / "nix-metadata"
INDEX_PATH = _CACHE_ROOT / "index.json"
DETAIL_DIR = _CACHE_ROOT / "details"

INDEX_TTL = 14 * 24 * 60 * 60
DETAIL_TTL = 30 * 24 * 60 * 60
MISSING_TTL = 3 * 24 * 60 * 60
MAX_INDEX_BYTES = 24 * 1024 * 1024
MAX_DETAIL_BYTES = 4 * 1024 * 1024
MAX_INDEX_PAGES = 16
INDEX_PER_PAGE = 5000
REQUEST_TIMEOUT = 30
USER_AGENT = "LinuxToys Nix metadata"

_INDEX_LOCK = threading.RLock()
_INDEX_REFRESH_LOCK = threading.RLock()
_DETAIL_LOCK = threading.RLock()
_INDEX_MEMORY = {"token": None, "payload": None}
_DETAIL_LOCKS = {}

PREFETCH_WORKERS = 2
PREFETCH_MAX_QUEUE = 96
PREFETCH_FAIL_BACKOFF = 10 * 60
_PREFETCH_LOCK = threading.RLock()
_PREFETCH_QUEUE = queue.Queue(maxsize=PREFETCH_MAX_QUEUE)
_PREFETCH_PENDING = set()
_PREFETCH_BACKOFF = {}
_PREFETCH_STARTED = False

_SAFE_IMAGE_SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".svg",
)
_MODERN_IMAGE_SUFFIXES = (
    ".avif",
    ".jxl",
)
_SAFE_WEB_SCHEMES = ("https://", "http://")
_LOGGER = logging.getLogger(__name__)


def nix_attr(info):
    """Return the nixpkgs attribute of one entry/detail record."""
    if not isinstance(info, dict):
        return ""
    attr = str(info.get("nix_name") or "").strip()
    if attr:
        return attr
    value = info.get("package-name")
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        for item in value:
            item = str(item or "").strip()
            if item:
                return item
    return ""


def entry_has_nix(info):
    """True when the entry is Nix itself or carries a Nix source option."""
    if not isinstance(info, dict):
        return False
    if str(info.get("appstream_source") or "").strip() == "nix":
        return True
    for option in info.get("source_options") or ():
        if isinstance(option, dict) and str(
            option.get("appstream_source") or ""
        ).strip() == "nix":
            return True
    return False


def api_language(language=None):
    """Map a LinuxToys locale to a Nix Software API language code."""
    if not language:
        try:
            from .lang_utils import detect_system_language

            language = detect_system_language()
        except Exception:
            language = "en"
    value = str(language or "en").strip().replace("_", "-")
    base = value.split("-", 1)[0].lower() or "en"
    return {
        "nb": "no",
        "zh": "zh-CN",
    }.get(base, base)


def _clean_text(value, limit):
    """Plain, bounded text from an untrusted API field."""
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = " ".join(paragraph.split())
        if paragraph:
            paragraphs.append(paragraph)
    text = "\n\n".join(paragraphs).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def _safe_slug(value):
    slug = str(value or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        return ""
    return slug


def derive_slug(attr):
    """Best-effort API slug from a nixpkgs attribute name."""
    value = str(attr or "").strip().lower()
    if not value:
        return ""
    value = value.lstrip("_")
    value = re.sub(r"[._\s]+", "-", value)
    value = re.sub(r"[^a-z0-9-]+", "", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


def _safe_asset_url(value, *, allow_modern=False, allow_external=False):
    """Only https image assets are accepted; hosted or external per caller."""
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("//"):
        text = "https:" + text
    elif not text.startswith(("https://", "http://")):
        text = urljoin(API_STORAGE_BASE, text.lstrip("/"))
    parts = urlsplit(text)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host:
        return ""
    if parts.username or parts.password:
        return ""
    api_hosted = host == API_HOST or host.endswith("." + API_HOST)
    if not api_hosted:
        if not allow_external:
            return ""
        if (
            host in {"localhost", "localhost.localdomain"}
            or host.endswith((".local", ".internal", ".lan", ".home"))
            or "." not in host
        ):
            return ""
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            return ""
    suffix = parts.path.lower()
    allowed = _SAFE_IMAGE_SUFFIXES + (
        _MODERN_IMAGE_SUFFIXES if allow_modern else ()
    )
    if not suffix.endswith(allowed):
        return ""
    return text


def _safe_web_url(value):
    text = str(value or "").strip()
    if not text or not text.startswith(_SAFE_WEB_SCHEMES):
        return ""
    if len(text) > 2048 or any(character in text for character in "\r\n\t"):
        return ""
    return text


def _http_json(url, *, max_bytes, language="en"):
    parts = urlsplit(url)
    if parts.scheme != "https" or (parts.hostname or "").lower() != API_HOST:
        raise ValueError("Refusing a non-Nix Software API URL")
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": language or "en",
        },
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("Nix Software API response exceeds the size limit")
    return json.loads(raw.decode("utf-8"))


def _valid_index(payload):
    return (
        isinstance(payload, dict)
        and payload.get("schema") == 1
        and isinstance(payload.get("packages"), dict)
        and isinstance(payload.get("updated"), (int, float))
    )


def _read_index():
    try:
        payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, UnicodeError):
        return None
    return payload if _valid_index(payload) else None


def _load_index():
    with _INDEX_LOCK:
        try:
            stat = INDEX_PATH.stat()
            token = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            return {}
        if _INDEX_MEMORY["token"] == token and _INDEX_MEMORY["payload"] is not None:
            return _INDEX_MEMORY["payload"]
        payload = _read_index()
        packages = payload["packages"] if payload else {}
        _INDEX_MEMORY["token"] = token
        _INDEX_MEMORY["payload"] = packages
        return packages


def index_record(attr):
    return _load_index().get(str(attr or "").strip())


def index_needs_refresh():
    payload = _read_index()
    if payload is None:
        return True
    return time.time() - float(payload.get("updated") or 0) >= INDEX_TTL


def index_available():
    return bool(_load_index())


def index_identity_map():
    """Return ``attr -> display name`` for indexed GUI applications.

    The shared AppStream catalog uses this map to give Nix components their
    real application name and to merge them with matching native, Flatpak or
    Snap sources. Only packages the API knows as GUI applications participate:
    command-line and library attributes often collide with unrelated app names
    (``ark`` is the R kernel, not KDE Ark).
    """
    identities = {}
    for attr, record in _load_index().items():
        if not isinstance(record, dict):
            continue
        name = str(record.get("name") or "").strip()
        if attr and name:
            identities[str(attr)] = name
    return identities


def _identity_key(value):
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def index_merge_identities():
    """Return ``attr -> (display name, mergeable)`` for catalog generation.

    A display name shared by several Nix attributes is not an identity: two
    different packages can both be called "Notes" or "Calculator". Those keep
    their display name but are excluded from by-name merging so a source
    selector can never install the wrong package.
    """
    identities = index_identity_map()
    counts = {}
    for name in identities.values():
        key = _identity_key(name)
        counts[key] = counts.get(key, 0) + 1
    return {
        attr: (name, counts[_identity_key(name)] == 1)
        for attr, name in identities.items()
    }


def index_identity_fingerprint(identities=None):
    """Stable digest of the identity map, used in catalog cache keys."""
    if identities is None:
        identities = index_identity_map()
    payload = json.dumps(
        identities,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(
        payload.encode("utf-8", "surrogatepass")
    ).hexdigest()


def _normalize_index_row(row):
    if not isinstance(row, dict):
        return None
    attr = str(row.get("attr_path") or "").strip()
    if not attr or "." in attr:
        return None
    slug = _safe_slug(row.get("slug")) or derive_slug(attr)
    if not slug:
        return None
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    translation = (
        meta.get("translation")
        if isinstance(meta.get("translation"), dict)
        else {}
    )
    name = _clean_text(translation.get("name"), 200)
    summary = _clean_text(translation.get("summary"), 500)
    logo = _safe_asset_url(meta.get("logo_path"))
    if not (name or summary or logo):
        return None
    return {
        "slug": slug,
        "name": name,
        "summary": summary,
        "logo": logo,
    }


def _has_next_page(payload):
    links = payload.get("links") if isinstance(payload, dict) else None
    if not isinstance(links, dict):
        return False
    candidate = str(links.get("next") or "").strip()
    if not candidate:
        return False
    parts = urlsplit(candidate)
    return parts.scheme == "https" and (parts.hostname or "").lower() == API_HOST


def refresh_index(force=False):
    """Fetch the GUI package index when stale. Returns True if refreshed."""
    with _INDEX_REFRESH_LOCK:
        if not force and not index_needs_refresh():
            return False
        packages = {}
        for page in range(1, MAX_INDEX_PAGES + 1):
            url = API_BASE + "/packages?" + urlencode(
                [
                    ("per_page", str(INDEX_PER_PAGE)),
                    ("app_type[]", "gui"),
                    ("page", str(page)),
                ]
            )
            payload = _http_json(
                url,
                max_bytes=MAX_INDEX_BYTES,
                language="en",
            )
            rows = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise ValueError("Invalid Nix Software package list")
            for row in rows:
                record = _normalize_index_row(row)
                if record is not None:
                    packages[str(row.get("attr_path")).strip()] = record
            if not rows or not _has_next_page(payload):
                break
        if not packages:
            raise ValueError("Empty Nix Software package index")
        previous = _read_index()
        previous_count = len(previous.get("packages", {})) if previous else 0
        if len(packages) < 50 or (
            previous_count and len(packages) < previous_count // 2
        ):
            raise ValueError("Suspiciously small Nix Software package index")
        value = {
            "schema": 1,
            "updated": int(time.time()),
            "packages": packages,
        }
        atomic_write_json(
            INDEX_PATH,
            value,
            separators=(",", ":"),
            ensure_ascii=False,
            fsync=True,
        )
        with _INDEX_LOCK:
            _INDEX_MEMORY["token"] = None
            _INDEX_MEMORY["payload"] = None
        return True


def _detail_path(slug, language):
    digest = hashlib.sha256(
        f"{slug}\0{language}".encode("utf-8")
    ).hexdigest()
    return DETAIL_DIR / f"{digest}.json"


def _read_detail(slug, language):
    path = _detail_path(slug, language)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, UnicodeError):
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != 1
        or payload.get("slug") != slug
        or payload.get("language") != language
        or not isinstance(payload.get("updated"), (int, float))
    ):
        return None
    return payload


def _detail_slug(info):
    if not isinstance(info, dict):
        return ""
    slug = _safe_slug(info.get("nix_api_slug"))
    if slug:
        return slug
    record = index_record(nix_attr(info))
    if record:
        slug = _safe_slug(record.get("slug"))
        if slug:
            return slug
    return derive_slug(nix_attr(info))


def _detail_is_fresh(payload):
    if not payload:
        return False
    if payload.get("missing"):
        return time.time() - float(payload["updated"]) < MISSING_TTL
    return time.time() - float(payload["updated"]) < DETAIL_TTL


def detail_needs_refresh(info, language=None):
    slug = _detail_slug(info)
    if not slug:
        return False
    return not _detail_is_fresh(_read_detail(slug, api_language(language)))


def has_detail(info, language=None):
    slug = _detail_slug(info)
    if not slug:
        return False
    payload = _read_detail(slug, api_language(language))
    return bool(
        payload
        and not payload.get("missing")
        and isinstance(payload.get("data"), dict)
    )


def _apply_index(entry, record):
    if not record:
        return
    slug = _safe_slug(record.get("slug"))
    if slug:
        entry["nix_api_slug"] = slug
    name = _clean_text(record.get("name"), 200)
    if name:
        entry["name"] = name
        entry["nix_api_name"] = name
    summary = _clean_text(record.get("summary"), 500)
    if summary:
        entry["description"] = summary
        entry["nix_api_summary"] = summary
    logo = _safe_asset_url(record.get("logo"))
    if logo:
        entry["icon"] = logo
        entry["nix_api_logo"] = logo


_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")


def _description_blocks(value):
    """Markdown-ish API prose to AppStream paragraph blocks.

    Nix package descriptions sometimes contain ATX headings (``### Section``).
    AppStream's renderer has no heading concept and the Markdown renderer
    would produce a larger visual hierarchy than an app page should have, so
    headings become ordinary bold paragraphs.
    """
    text = "" if value is None else str(value)
    text = html.unescape(text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    blocks = []
    paragraph = []
    in_fence = False

    def flush_paragraph():
        if not paragraph:
            return
        joined = " ".join(part for part in paragraph if part).strip()
        paragraph.clear()
        if joined:
            blocks.append(
                {"type": "paragraph", "spans": [{"text": joined}]}
            )

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            flush_paragraph()
            continue
        if in_fence:
            if stripped:
                paragraph.append(stripped)
            continue
        line = " ".join(raw_line.split())
        if not line:
            flush_paragraph()
            continue
        heading = None
        if not raw_line.startswith(("    ", "\t")):
            heading = _HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            title = heading.group(2).strip().strip("#").strip()
            title = re.sub(r"\*\*(.+?)\*\*", r"\1", title)
            title = re.sub(r"__(.+?)__", r"\1", title)
            title = title.replace("`", "").strip()
            if title:
                blocks.append(
                    {
                        "type": "paragraph",
                        "spans": [{"text": title, "styles": ["bold"]}],
                    }
                )
            continue
        paragraph.append(line)
    flush_paragraph()
    return blocks


def _apply_detail(entry, payload, language):
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    translation = (
        meta.get("translation")
        if isinstance(meta.get("translation"), dict)
        else {}
    )
    name = _clean_text(translation.get("name"), 200)
    if name:
        entry["name"] = name
        entry["nix_api_name"] = name
    summary = _clean_text(translation.get("summary"), 500)
    if summary:
        entry["description"] = summary
    long_description_source = (
        translation.get("description") or data.get("description") or ""
    )
    blocks = _description_blocks(long_description_source)
    if blocks:
        entry["long_description"] = "\n\n".join(
            " ".join(
                str(span.get("text") or "")
                for span in block.get("spans") or ()
                if isinstance(span, dict)
            ).strip()
            for block in blocks
        ).strip()
        entry["long_description_blocks"] = blocks
        entry["long_description_format"] = "appstream"
        entry["long_description_locale"] = (
            "en" if translation.get("is_fallback") else api_language(language)
        )
    screenshots = meta.get("screenshots")
    if isinstance(screenshots, list):
        clean_shots = []
        for screenshot in screenshots[:12]:
            safe = _safe_asset_url(
                screenshot, allow_modern=True, allow_external=True
            )
            if safe:
                clean_shots.append(safe)
        if clean_shots:
            entry["screenshots"] = clean_shots
    logo = _safe_asset_url(meta.get("logo_path"))
    if logo:
        entry["icon"] = logo
        entry["nix_api_logo"] = logo
    homepage = data.get("homepage")
    if isinstance(homepage, str):
        homepage = [homepage]
    if isinstance(homepage, list):
        for value in homepage:
            safe = _safe_web_url(value)
            if safe:
                entry["homepage_url"] = safe
                break
    maintainers = data.get("maintainers")
    if isinstance(maintainers, list):
        names = []
        for maintainer in maintainers[:3]:
            if isinstance(maintainer, dict):
                value = _clean_text(maintainer.get("name"), 120)
                if value:
                    names.append(value)
        if names:
            entry["developer"] = ", ".join(names)
    licenses = data.get("licenses")
    if isinstance(licenses, list):
        names = []
        for license_entry in licenses[:3]:
            if not isinstance(license_entry, dict):
                continue
            value = _clean_text(
                license_entry.get("full_name")
                or license_entry.get("spdx_id"),
                160,
            )
            if value:
                names.append(value)
        if names:
            entry["license"] = ", ".join(names)
    version = _clean_text(data.get("version"), 120)
    if version:
        entry["nix_api_version"] = version
    category = meta.get("category")
    if isinstance(category, dict):
        name = _clean_text(category.get("name"), 120)
        if name:
            entry["nix_api_category"] = name
    app_type = _clean_text(meta.get("app_type"), 40)
    if app_type:
        entry["nix_api_app_type"] = app_type
    updated = _clean_text(data.get("updated_at"), 80)
    if updated:
        entry["nix_api_updated"] = updated
    channel = (
        data.get("package_channel")
        if isinstance(data.get("package_channel"), dict)
        else {}
    )
    for source_key, entry_key in (
        ("is_broken", "nix_api_broken"),
        ("is_insecure", "nix_api_insecure"),
        ("is_unfree", "nix_api_unfree"),
        ("is_unsupported", "nix_api_unsupported"),
    ):
        if source_key in channel:
            entry[entry_key] = bool(channel.get(source_key))
    vulnerabilities = channel.get("known_vulnerabilities")
    if isinstance(vulnerabilities, list):
        entry["nix_api_vulnerabilities"] = [
            _clean_text(item, 120)
            for item in vulnerabilities[:20]
            if _clean_text(item, 120)
        ]


def _enrich_entry(info, *, include_detail, language=None):
    if not isinstance(info, dict):
        return info

    source_is_nix = str(info.get("appstream_source") or "").strip() == "nix"
    options = info.get("source_options")
    has_nix_options = isinstance(options, list) and any(
        isinstance(option, dict)
        and str(option.get("appstream_source") or "").strip() == "nix"
        for option in options
    )
    if not source_is_nix and not has_nix_options:
        return info

    result = info
    if source_is_nix:
        attr = nix_attr(info)
        record = index_record(attr) if attr else None
        detail = None
        if include_detail and attr:
            slug = _detail_slug(info)
            language_code = api_language(language)
            payload = _read_detail(slug, language_code) if slug else None
            if payload and not payload.get("missing"):
                detail = payload
        if not record and not detail and not has_nix_options:
            return info
        result = dict(info)
        _apply_index(result, record)
        if detail is not None:
            _apply_detail(result, detail, language)

    if has_nix_options:
        if result is info:
            result = dict(info)
        result["source_options"] = [
            _enrich_entry(option, include_detail=False, language=language)
            if isinstance(option, dict)
            and str(option.get("appstream_source") or "").strip() == "nix"
            else option
            for option in options
        ]
    return result


def enrich_index(info):
    """Decorate cards/search rows using the cached index only."""
    return _enrich_entry(info, include_detail=False)


def enrich(info, language=None):
    """Decorate an app-page entry with index and cached detail metadata."""
    return _enrich_entry(info, include_detail=True, language=language)


def _detail_lock(key):
    with _DETAIL_LOCK:
        lock = _DETAIL_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _DETAIL_LOCKS[key] = lock
        return lock


def fetch_detail(info, language=None, force=False):
    """Fetch and cache one package detail. Returns enriched info or None.

    Same-package callers serialize on a per-key lock. A prefetch already in
    flight therefore satisfies a later app-page request instead of issuing a
    duplicate API call.
    """
    slug = _detail_slug(info)
    if not slug:
        return None
    language_code = api_language(language)
    key = (slug, language_code)
    lock = _detail_lock(key)
    with lock:
        if not force and not detail_needs_refresh(info, language_code):
            return enrich(info, language_code)
        try:
            url = API_BASE + "/packages/" + quote(slug, safe="")
            try:
                payload = _http_json(
                    url,
                    max_bytes=MAX_DETAIL_BYTES,
                    language=language_code,
                )
            except HTTPError as error:
                if error.code == 404:
                    atomic_write_json(
                        _detail_path(slug, language_code),
                        {
                            "schema": 1,
                            "updated": int(time.time()),
                            "slug": slug,
                            "language": language_code,
                            "missing": True,
                        },
                        separators=(",", ":"),
                        ensure_ascii=False,
                        fsync=True,
                    )
                    return None
                raise
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict):
                return None
            atomic_write_json(
                _detail_path(slug, language_code),
                {
                    "schema": 1,
                    "updated": int(time.time()),
                    "slug": slug,
                    "language": language_code,
                    "data": data,
                },
                separators=(",", ":"),
                ensure_ascii=False,
                fsync=True,
            )
            return enrich(info, language_code)
        except Exception as error:
            _LOGGER.warning("Nix metadata fetch for %s failed: %s", slug, error)
            return None


def _prefetch_worker():
    while True:
        info, key = _PREFETCH_QUEUE.get()
        try:
            fetch_detail(info, language=key[1])
        except Exception:
            pass
        finally:
            with _PREFETCH_LOCK:
                _PREFETCH_PENDING.discard(key)
                payload = _read_detail(key[0], key[1])
                if not _detail_is_fresh(payload):
                    _PREFETCH_BACKOFF[key] = time.time()
            _PREFETCH_QUEUE.task_done()


def _ensure_prefetch_workers():
    global _PREFETCH_STARTED
    with _PREFETCH_LOCK:
        if _PREFETCH_STARTED:
            return
        _PREFETCH_STARTED = True
        for index in range(PREFETCH_WORKERS):
            threading.Thread(
                target=_prefetch_worker,
                daemon=True,
                name=f"linuxtoys-nix-prefetch-{index}",
            ).start()


def prefetch(info, language=None):
    """Warm one visible Nix card's app-page detail in the background.

    Only packages present in the metadata index are queued, the work is
    deduplicated and bounded, and failures back off instead of retrying every
    time the card re-enters view.
    """
    if not isinstance(info, dict):
        return False
    if str(info.get("appstream_source") or "").strip() != "nix":
        return False
    attr = nix_attr(info)
    if not attr:
        return False
    if not index_record(attr) and not info.get("nix_api_slug"):
        return False
    slug = _detail_slug(info)
    if not slug:
        return False
    language_code = api_language(language)
    key = (slug, language_code)
    if _detail_is_fresh(_read_detail(slug, language_code)):
        return False
    now = time.time()
    with _PREFETCH_LOCK:
        if key in _PREFETCH_PENDING:
            return False
        if now - _PREFETCH_BACKOFF.get(key, 0) < PREFETCH_FAIL_BACKOFF:
            return False
        if _PREFETCH_QUEUE.qsize() >= PREFETCH_MAX_QUEUE:
            return False
        _PREFETCH_PENDING.add(key)
    _ensure_prefetch_workers()
    try:
        _PREFETCH_QUEUE.put_nowait((info, key))
    except queue.Full:
        with _PREFETCH_LOCK:
            _PREFETCH_PENDING.discard(key)
        return False
    return True
