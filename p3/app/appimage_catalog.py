"""Cached discovery metadata from the AppImage community feed.

This module does not resolve releases or download AppImages. Network access is
limited to one feed request when the cache is stale.
"""
from __future__ import annotations

import json
import contextlib
import html
import platform
import re
import tempfile
import shutil
from urllib.parse import urlparse, quote, urlsplit, urlunsplit
import logging
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

FEED_URL = "https://appimage.github.io/feed.json"
# The hub serves per-app artwork under /database/<app>/...; the feed lists
# those paths relative to this base.
FEED_ASSET_BASE = "https://appimage.github.io/database/"
MAX_FEED_BYTES = 20 * 1024 * 1024
REFRESH_SECONDS = 14 * 24 * 60 * 60

def _strings(value):
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [x for x in value if isinstance(x, str) and x]
    return []

def _feed_asset_url(value):
    """Normalize feed artwork, preserving existing URL escapes and path case."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if not value:
        return ""
    if value.startswith("//"):
        value = "https:" + value
    elif not value.startswith("https://"):
        if value.startswith(("http://", "/v2/")) or ":" in value.split("/")[0]:
            return ""
        # Relative artwork is stored below the community database directory.
        if value.startswith("/"):
            value = value.lstrip("/")
        value = FEED_ASSET_BASE + value
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc:
        return ""
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%:@!$&'()*+,;=-._~"), parts.query, ""))


def _feed_links(value):
    """Read typed feed links, including repository slugs without a URL scheme."""
    if not isinstance(value, list):
        return _urls(value)
    links = []
    for item in value:
        if not isinstance(item, dict):
            links.extend(_urls(item))
            continue
        kind = str(item.get("type") or "").casefold()
        raw = str(item.get("url") or "").strip()
        if kind in ("github", "codeberg") and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", raw):
            raw = f"https://{'github.com' if kind == 'github' else 'codeberg.org'}/{raw}"
        if raw.startswith("https://") and raw not in links:
            links.append(raw)
    return links

def _split_description(text):
    """First sentence becomes the summary; the whole text stays the long one."""
    text = re.sub(r"(?i)<br\s*/?>", "\n", text or "")
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)  # feed descriptions may carry HTML
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    paragraphs = []
    for raw in re.split(r"\n\s*\n", text):
        paragraph = " ".join(raw.split())
        if paragraph:
            paragraphs.append(paragraph)
    if not paragraphs:
        return "", []
    first = paragraphs[0]
    # Sentence boundary: terminator + whitespace + a capital/opening quote, so
    # version numbers ("Qt 5.") do not terminate the summary.
    match = re.match(r"^(.{10,}?[.!?])(?:\s+(?=[A-Z0-9\"'])|$)", first)
    summary = match.group(1).strip() if match else first
    blocks = [
        {"type": "paragraph", "spans": [{"type": "text", "text": paragraph}]}
        for paragraph in paragraphs
    ]
    return summary, blocks

def _urls(value):
    if isinstance(value, str):
        return [value] if value.startswith("https://") else []
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_urls(item))
        return result
    if isinstance(value, dict):
        result = []
        for key in ("url", "href", "link", "download", "icon", "image", "src", "github", "git", "homepage", "website", "repository"):
            if key in value:
                result.extend(_urls(value[key]))
        return result
    return []

def _developer_names(authors):
    """The community feed is not strictly typed; never reject a whole feed over authors."""
    if not isinstance(authors, list):
        return ""
    names = []
    for author in authors:
        if isinstance(author, dict):
            name = author.get("name")
        elif isinstance(author, str):
            name = author
        else:
            continue
        if isinstance(name, (str, int, float)) and not isinstance(name, bool):
            value = str(name).strip()
            if value and value not in names:
                names.append(value)
    return ", ".join(names)


def normalize(feed):
    """Normalize conservative, directly supported presentation fields.

    Downloadability is deliberately not asserted until an installer can resolve
    a real upstream asset. Entries lacking a URL are skipped.
    """
    if isinstance(feed, dict):
        feed = feed.get("apps", feed.get("items", feed.get("applications", [])))
    if not isinstance(feed, list):
        raise ValueError("Unexpected AppImage feed structure")
    result = []
    seen = set()
    for item in feed:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        links = _feed_links(item.get("links")) + _urls(item.get("download"))
        if not links:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        icons = [
            url for url in (_feed_asset_url(icon) for icon in _strings(item.get("icons")))
            if url
        ]
        screenshots = [
            url for url in (_feed_asset_url(shot) for shot in _strings(item.get("screenshots")))
            if url
        ]
        description = item.get("description")
        if not isinstance(description, str):
            description = ""
        description = description.strip()
        summary, description_blocks = _split_description(description)
        # Null category entries mean "uncategorized": route them through the
        # "None" bucket so they still resolve to a destination.
        raw_categories = item.get("categories")
        if isinstance(raw_categories, list):
            categories = [
                "None" if c is None else str(c).strip()
                for c in raw_categories
                if c is None or (isinstance(c, str) and c.strip())
            ]
            categories = [c for c in categories if c]
        elif isinstance(raw_categories, str) and raw_categories.strip():
            categories = [raw_categories.strip()]
        else:
            categories = []
        result.append({
            "id": "appimage.community." + "".join(c if c.isalnum() else "-" for c in key).strip("-"),
            "name": name,
            "summary": summary,
            "packages": [name],
            "description_blocks": description_blocks,
            "origin": "appimage-community",
            "license": str(item.get("license") or ""),
            "developer": _developer_names(item.get("authors")),
            "description": summary,
            "categories": categories,
            "icon": icons[0] if icons else "",
            "screenshots": screenshots,
            "source": "appimage",
            "appimage_links": links,
            "appimage_needs_resolution": True,
        })
    return result

def load_or_refresh(path, *, force=False):
    path = Path(path)
    cached = None
    if path.is_file():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if not force and time.time() - path.stat().st_mtime < REFRESH_SECONDS:
                return normalize(cached)
        except (OSError, ValueError, TypeError):
            cached = None
    try:
        request = Request(FEED_URL, headers={"User-Agent": "LinuxToys AppImage Catalog", "Accept": "application/json"})
        with urlopen(request, timeout=15) as response:
            payload = response.read(MAX_FEED_BYTES + 1)
        if len(payload) > MAX_FEED_BYTES:
            raise ValueError("AppImage feed exceeds size limit")
        feed = json.loads(payload)
        entries = normalize(feed)
        if not entries:
            raise ValueError("AppImage feed has no usable entries")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        try:
            tmp.write_bytes(payload)
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
        return entries
    except Exception as exc:
        logging.warning("AppImage community feed unavailable: %s", exc)
        if cached is not None:
            try:
                return normalize(cached)
            except (ValueError, TypeError):
                pass
        return []

MAX_APPIMAGE_BYTES = 4 * 1024 * 1024 * 1024

def file_signature(path):
    stat = os.stat(path)
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns

def _get_json(url):
    req = Request(url, headers={"User-Agent": "LinuxToys AppImage Installer", "Accept": "application/json"})
    with urlopen(req, timeout=20) as response:
        data = response.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError("Release metadata too large")
    return json.loads(data)

def _arch_match(filename):
    name = filename.lower()
    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        wanted, rejected = ("x86_64", "amd64", "x64"), ("aarch64", "arm64", "armhf", "i386", "i686")
    elif arch in ("aarch64", "arm64"):
        wanted, rejected = ("aarch64", "arm64"), ("x86_64", "amd64", "i386", "i686")
    else:
        return False
    return not any(x in name for x in rejected) and (
        any(x in name for x in wanted) or not any(x in name for x in ("arm", "x86", "amd", "i386", "i686"))
    )

def _release_asset(assets):
    candidates = []
    for asset in assets:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or asset.get("download_url") or "")
        if not re.search(r"(?i)\.appimage$", name) or not url.startswith("https://"):
            continue
        if _arch_match(name):
            candidates.append((name, url))
    if len(candidates) != 1:
        raise ValueError(f"Expected one compatible AppImage release asset; found {len(candidates)}")
    return candidates[0][1]

def resolve_download(info):
    """Return (asset URL, repository URL, release tag) with on-demand API calls."""
    links = info.get("appimage_links") or []
    for raw in links:
        url = str(raw)
        parsed = urlparse(url)
        if parsed.scheme != "https":
            continue
        if re.search(r"(?i)\.appimage$", parsed.path):
            return url, "", ""
        parts = [p for p in parsed.path.split("/") if p]
        if parsed.hostname in ("github.com", "www.github.com") and len(parts) >= 2:
            owner, repo = parts[:2]
            if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in (owner, repo)):
                continue
            release = _get_json(f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
            return _release_asset(release.get("assets", [])), f"https://github.com/{owner}/{repo}", str(release.get("tag_name") or "")
        if parsed.hostname == "codeberg.org" and len(parts) >= 2:
            owner, repo = parts[:2]
            if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in (owner, repo)):
                continue
            release = _get_json(f"https://codeberg.org/api/v1/repos/{owner}/{repo}/releases/latest")
            return _release_asset(release.get("assets", [])), f"https://codeberg.org/{owner}/{repo}", str(release.get("tag_name") or "")
    raise ValueError("No supported direct AppImage download or GitHub/Codeberg release link")

@contextlib.contextmanager
def download_for_install(info):
    url, repository, version = resolve_download(info)
    with tempfile.TemporaryDirectory(prefix="linuxtoys-appimage-") as directory:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", str(info.get("name") or "AppImage")).strip(".-")[:80]
        path = Path(directory) / f"{safe_name or 'AppImage'}.AppImage"
        req = Request(url, headers={"User-Agent": "LinuxToys AppImage Installer"})
        with urlopen(req, timeout=40) as response, path.open("wb") as target:
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_APPIMAGE_BYTES:
                    raise ValueError("AppImage download exceeds 4 GiB")
                target.write(chunk)
        if path.stat().st_size < 4096:
            raise ValueError("Downloaded AppImage is unexpectedly small")
        with path.open("rb") as handle:
            header = handle.read(4)
        if header != b"\x7fELF":
            raise ValueError("Downloaded asset is not an ELF AppImage")
        yield str(path), {"repository": repository, "version": version, "download_url": url}
