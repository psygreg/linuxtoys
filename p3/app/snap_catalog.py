"""Snap Store metadata ingestion for the LinuxToys AppStream-style catalog."""
from __future__ import annotations
import http.client, json, os, socket, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SNAPD_SOCKET = "/run/snapd.socket"
CACHE_MAX_AGE = 14 * 24 * 60 * 60

_CATEGORY_MAP = {
    # Translate Snap Store sections/categories into freedesktop AppStream tags.
    # The normal LinuxToys AppStream resolver then handles these exactly like
    # native/Flatpak metadata, including Main+Additional expression rules.
    "art-and-design": ("Graphics", "2DGraphics"),
    "books-and-reference": ("Office", "Viewer"),
    "development": ("Development",),
    "devices-and-iot": ("System",),
    "education": ("Education",),
    "entertainment": ("AudioVideo",),
    "finance": ("Office", "Finance"),
    "games": ("Game",),
    "health-and-fitness": ("HealthFitness",),
    "music-and-audio": ("AudioVideo", "Audio"),
    "news-and-weather": ("Network", "News"),
    "personalisation": ("Settings", "DesktopSettings"),
    # This Store category mixes image and video applications, so keep it broad
    # instead of incorrectly forcing every entry into Photography or Video.
    "photo-and-video": ("Graphics",),
    "productivity": ("Office",),
    "science": ("Science",),
    "security": ("System", "Security"),
    "server-and-cloud": ("System", "Network"),
    "social": ("Network", "Chat"),
    "utilities": ("Utility",),
}


def _category_names(value, section=""):
    """Collect Store category names from the result plus the queried section."""
    result = []

    def add(raw):
        key = str(raw or "").strip().casefold().replace("_", "-").replace(" ", "-")
        if key and key not in result:
            result.append(key)

    add(section)
    raw = value.get("categories") if isinstance(value, dict) else None
    if isinstance(raw, str):
        add(raw)
    elif isinstance(raw, (list, tuple)):
        for item in raw:
            if isinstance(item, dict):
                add(item.get("name") or item.get("slug") or item.get("category"))
            else:
                add(item)
    return result


def _appstream_categories(value, section=""):
    """Map Snap Store taxonomy onto tags understood by the AppStream resolver."""
    out = []
    for category in _category_names(value, section):
        for tag in _CATEGORY_MAP.get(category, ()):
            if tag not in out:
                out.append(tag)
    # Unknown/new Store categories should remain visible through the generic
    # utility fallback rather than disappearing from the LinuxToys catalog.
    return out or ["Utility"]



class _SnapdConnection(http.client.HTTPConnection):
    """HTTPConnection transported over snapd's local Unix socket."""

    def __init__(self, timeout=25):
        super().__init__("localhost", timeout=timeout)

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(SNAPD_SOCKET)
        self.sock = sock


def _request(path, params=None, timeout=25):
    """Return the `result` payload from one synchronous snapd REST request."""
    if params:
        path += "?" + urlencode(params, doseq=True)

    connection = _SnapdConnection(timeout=timeout)
    try:
        connection.request(
            "GET",
            path,
            headers={
                "Accept": "application/json",
                "User-Agent": "LinuxToys/1 snap-catalog",
            },
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    finally:
        connection.close()

    if response.status != 200:
        message = ""
        if isinstance(payload, dict):
            result = payload.get("result")
            if isinstance(result, dict):
                message = str(result.get("message") or "")
        raise OSError(message or f"snapd returned HTTP {response.status}")

    if not isinstance(payload, dict) or payload.get("type") != "sync":
        raise ValueError("invalid snapd response")

    return payload.get("result")


def _sections():
    """Return the Store sections exposed by the running snapd."""
    values = _request("/v2/sections")
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _results_for_section(section):
    """Return stable Store snaps for one section, filtered by snapd for this host."""
    values = _request("/v2/find", {"section": section})
    return values if isinstance(values, list) else []


def _publisher_name(value):
    publisher = value.get("publisher")
    if isinstance(publisher, dict):
        return str(publisher.get("display-name") or publisher.get("display_name") or
                   publisher.get("username") or publisher.get("name") or "").strip()
    return str(value.get("developer") or "").strip()

def _media(value):
    icon = ""
    screenshots = []

    media = value.get("media")
    if isinstance(media, list):
        for item in media:
            if not isinstance(item, dict):
                continue

            url = str(item.get("url") or "").strip()
            kind = str(item.get("type") or "").strip().lower()
            if not url:
                continue

            if kind == "icon" and not icon:
                icon = url
            elif kind in {"screenshot", "banner"}:
                screenshots.append({
                    "images": [{
                        "url": url,
                        "width": int(item.get("width") or 0),
                        "height": int(item.get("height") or 0),
                    }]
                })

    # Prefer the Store media icon because it is normally a directly usable
    # remote asset. snapd's top-level icon may instead be a snapd-relative URL.
    if not icon:
        candidate = str(value.get("icon") or "").strip()
        if candidate.startswith(("https://", "http://", "/v2/")):
            icon = candidate

    return icon or "application-x-executable", screenshots

def _common_ids(value):
    raw=value.get("common-ids")
    if raw is None: raw=value.get("common_ids")
    if isinstance(raw,str): raw=[raw]
    return [str(x).strip() for x in (raw or []) if str(x).strip()]

def normalize(value, category=""):
    if not isinstance(value,dict): return None
    name=str(value.get("name") or "").strip()
    if not name: return None
    common_ids=_common_ids(value)
    component_id=common_ids[0] if common_ids else f"io.snapcraft.{name}"
    icon,screenshots=_media(value)
    categories=_appstream_categories(value, category)
    return {
        "identity": f"snap:{name}",
        "id": component_id,
        "name": str(value.get("title") or name).strip(),
        "summary": str(value.get("summary") or "").strip(),
        "description_blocks": [{"type":"paragraph","spans":[{"text":str(value.get("description") or "").strip()}]}],
        "developer": _publisher_name(value),
        "icon": icon,
        "screenshots": screenshots,
        "categories": categories,
        "packages": [name],
        "source": "snap",
        "origin": "snapcraft",
        "homepage": str(value.get("website") or "").strip(),
        "contact": str(value.get("contact") or "").strip(),
        "license": str(value.get("license") or "").strip(),
        "version": str(value.get("version") or "").strip(),
        "snap_name": name,
        "snap_id": str(value.get("snap-id") or value.get("id") or "").strip(),
        "snap_common_ids": common_ids,
        "snap_confinement": str(value.get("confinement") or "").strip(),
        "snap_channel": str(value.get("channel") or "stable").strip() or "stable",
    }

def load_or_refresh(cache_path, force=False):
    path=Path(cache_path)
    if not force:
        try:
            if time.time()-path.stat().st_mtime < CACHE_MAX_AGE:
                data=json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data,list): return data
        except (OSError,ValueError,TypeError):
            pass
    previous=[]
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data,list): previous=data
    except (OSError,ValueError,TypeError): pass
    try:
        merged={}
        for section in _sections():
            for value in _results_for_section(section):
                item=normalize(value,section)
                if item: merged[item["snap_name"]]=item
        values=sorted(merged.values(), key=lambda x:x["name"].casefold())
        if values:
            path.parent.mkdir(parents=True,exist_ok=True)
            tmp=path.with_suffix(path.suffix+".tmp")
            tmp.write_text(json.dumps(values,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
            os.replace(tmp,path)
            return values
    except (OSError,ValueError,TypeError,json.JSONDecodeError):
        pass
    return previous
