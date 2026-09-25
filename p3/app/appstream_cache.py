"""Persistent AppStream catalog cache for LinuxToys.

The cache builder is deliberately UI-agnostic.  It loads the distribution's
AppStream pool through libappstream, normalizes the useful application metadata
into JSON, checkpoints partial work, and atomically publishes a completed
catalog under ~/.cache/linuxtoys/appstream.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path

from . import popularity
from . import _catalog_rs as _catalog_rs
from .compat import get_linuxtoys_cache_dir


CACHE_SCHEMA = 19
CACHE_MAX_AGE = 14 * 24 * 60 * 60
CHECKPOINT_EVERY = 100

CACHE_DIR = Path(get_linuxtoys_cache_dir()) / "appstream"
STATE_PATH = CACHE_DIR / "state.json"
CATALOG_PATH = CACHE_DIR / "catalog.json"
PARTIAL_PATH = CACHE_DIR / "native.partial.json"
FLATPAK_PARTIAL_PATH = CACHE_DIR / "flatpak.partial.json"
SOURCE_INVENTORY_PATH = CACHE_DIR / "source-inventory.json"
ODRS_RATED_PATH = Path(os.path.expanduser("~/.config/linuxtoys/odrs-ratings.json"))
ODRS_SUBMIT_URL = "https://odrs.gnome.org/1.0/reviews/api/submit"
ODRS_USER_SALT = "linuxtoys-odrs-v1"

_LOCK = threading.RLock()


def _flatpak_supported_host() -> bool:
    """Return whether Flatpak-backed AppStream should be considered on this host.

    LinuxToys treats Flatpak as systemd-only and does not expose Flatpak
    applications from containers.
    """
    try:
        from .compat import get_system_compat_keys, is_containerized

        return (
            not is_containerized()
            and "systemd" in get_system_compat_keys()
        )
    except (ImportError, AttributeError):
        return False


def _atomic_json_write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _read_json(path: Path, default):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return default






















def _safe_call(obj, method, default=None, *args):
    if obj is None:
        return default
    func = getattr(obj, method, None)
    if func is None:
        return default
    try:
        value = func(*args)
    except Exception:
        return default
    return default if value is None else value


def _as_list(value):
    if value is None:
        return []
    try:
        # AppStream 1.x ComponentBox exposes as_array(); older GI versions return
        # an iterable directly.
        converter = getattr(value, "as_array", None) or getattr(value, "asArray", None)
        if converter is not None:
            value = converter()
        return list(value)
    except (TypeError, AttributeError):
        return []


def _icon_value(component) -> str:
    # Prefer a cached local PNG/SVG because LinuxToys can display it directly.
    for icon in _as_list(_safe_call(component, "get_icons", [])):
        for method in ("get_filename", "get_name"):
            value = _safe_call(icon, method, "")
            if not value:
                continue
            value = str(value)
            if os.path.isabs(value) and os.path.isfile(value):
                if value.lower().endswith((".png", ".svg")):
                    return value

    # A stock icon name is the best portable fallback and lets Gtk.IconTheme do
    # the resolution.  JXL/remote icons can be added later without changing the
    # cache schema.
    stock = _safe_call(component, "get_icon_stock")
    for method in ("get_name", "get_filename"):
        value = _safe_call(stock, method, "")
        if value:
            value = str(value)
            if not os.path.isabs(value):
                return value

    return "application-x-executable"


def _local_screenshots(component):
    paths = []
    for screenshot in _as_list(_safe_call(component, "get_screenshots_all", [])):
        images = _as_list(_safe_call(screenshot, "get_images", []))
        for image in images:
            value = _safe_call(image, "get_filename", "")
            if value and os.path.isfile(str(value)):
                path = str(value)
                if path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    paths.append(path)
                    break
    return paths


def _developer_name(component) -> str:
    developer = _safe_call(component, "get_developer")
    return str(_safe_call(developer, "get_name", "") or "").strip()


def _component_homepage(component) -> str:
    """Return the component homepage URL when libAppStream exposes one."""
    try:
        from gi.repository import AppStream

        url_kind = getattr(getattr(AppStream, "UrlKind", None), "HOMEPAGE", None)
        if url_kind is not None:
            value = _safe_call(component, "get_url", "", url_kind)
            if value:
                return str(value).strip()
    except (ImportError, AttributeError):
        pass

    # Keep compatibility with bindings exposing URL items rather than get_url().
    for item in _as_list(_safe_call(component, "get_urls", [])):
        kind = str(_safe_call(item, "get_kind", "") or "").casefold()
        if "homepage" in kind:
            value = _safe_call(item, "get_url", "") or _safe_call(item, "get_value", "")
            if value:
                return str(value).strip()
    return ""


def _component_donation(component) -> str:
    """Return the component donation URL when libAppStream exposes one."""
    try:
        from gi.repository import AppStream

        url_kind = getattr(getattr(AppStream, "UrlKind", None), "DONATION", None)
        if url_kind is not None:
            value = _safe_call(component, "get_url", "", url_kind)
            if value:
                return str(value).strip()
    except (ImportError, AttributeError):
        pass

    # Keep compatibility with bindings exposing URL items rather than get_url().
    for item in _as_list(_safe_call(component, "get_urls", [])):
        kind = str(_safe_call(item, "get_kind", "") or "").casefold()
        if "donation" in kind:
            value = _safe_call(item, "get_url", "") or _safe_call(item, "get_value", "")
            if value:
                return str(value).strip()
    return ""


def _component_license(component) -> str:
    return str(_safe_call(component, "get_project_license", "") or "").strip()


def _component_screenshots(component):
    """Return logical screenshots with all available libAppStream image variants."""
    screenshots = []
    for screenshot in _as_list(_safe_call(component, "get_screenshots_all", [])):
        variants = []
        seen = set()
        for image in _as_list(_safe_call(screenshot, "get_images", [])):
            value = _safe_call(image, "get_filename", "")
            if value and os.path.isfile(str(value)):
                candidate = str(value)
            else:
                candidate = str(_safe_call(image, "get_url", "") or "").strip()
            if not candidate or candidate in seen:
                continue
            if not (
                candidate.startswith(("https://", "http://"))
                or (
                    os.path.isfile(candidate)
                    and candidate.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                )
            ):
                continue
            seen.add(candidate)
            try:
                width = max(0, int(_safe_call(image, "get_width", 0) or 0))
                height = max(0, int(_safe_call(image, "get_height", 0) or 0))
            except (TypeError, ValueError):
                width = height = 0
            variants.append({"url": candidate, "width": width, "height": height})
        if variants:
            variants.sort(key=lambda item: (item.get("width", 0), item.get("height", 0)))
            screenshots.append({"images": variants})
    return screenshots


def _component_identity(component) -> str:
    data_id = str(_safe_call(component, "get_data_id", "") or "").strip()
    if data_id:
        return data_id
    component_id = str(_safe_call(component, "get_id", "") or "").strip()
    origin = str(_safe_call(component, "get_origin", "") or "").strip()
    packages = ",".join(str(p) for p in _as_list(_safe_call(component, "get_pkgnames", [])))
    return f"{origin}\0{component_id}\0{packages}"



def _odrs_user_hash() -> str:
    """Return LinuxToys' stable pseudonymous ODRS identity for this local user."""
    machine_id = ""
    for candidate in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            machine_id = Path(candidate).read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if machine_id:
            break
    username = os.environ.get("USER") or os.environ.get("LOGNAME") or "unknown"
    payload = f"{machine_id}\0{username}\0{ODRS_USER_SALT}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def _odrs_locale() -> str:
    value = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "en_US"
    return value.split(".", 1)[0] or "en_US"


def _odrs_distro() -> str:
    try:
        values = {}
        with open("/etc/os-release", "r", encoding="utf-8") as handle:
            for line in handle:
                if "=" not in line:
                    continue
                key, value = line.rstrip().split("=", 1)
                values[key] = value.strip().strip('"')
        return values.get("PRETTY_NAME") or values.get("NAME") or values.get("ID") or "Linux"
    except OSError:
        return "Linux"


def get_submitted_odrs_rating(app_id: str):
    """Return the locally submitted 1-5 star rating, or None if unrated.

    Current cache entries store {"stars": N, "submitted": timestamp}.  Integer
    values are also accepted for forward/backward compatibility with simpler
    cache formats.  Legacy marker-only entries remain rated, but have no score
    that can be rendered.
    """
    app_id = str(app_id or "").strip()
    if not app_id:
        return None
    data = _read_json(ODRS_RATED_PATH, {})
    if not isinstance(data, dict) or app_id not in data:
        return None

    entry = data.get(app_id)
    value = entry.get("stars") if isinstance(entry, dict) else entry
    try:
        stars = int(value)
    except (TypeError, ValueError):
        return None
    return stars if 1 <= stars <= 5 else None


def has_submitted_odrs_rating(app_id: str) -> bool:
    app_id = str(app_id or "").strip()
    if not app_id:
        return False
    data = _read_json(ODRS_RATED_PATH, {})
    return isinstance(data, dict) and app_id in data


def _record_submitted_odrs_rating(app_id: str, stars: int) -> None:
    data = _read_json(ODRS_RATED_PATH, {})
    if not isinstance(data, dict):
        data = {}
    data[str(app_id)] = {"stars": int(stars), "submitted": int(time.time())}
    _atomic_json_write(ODRS_RATED_PATH, data)


def submit_odrs_rating(app_id: str, stars: int, summary: str, description: str, version: str = "unknown"):
    """Submit one irreversible LinuxToys preset review to ODRS.

    Returns (success, error_message). The local one-rating marker is written only
    after ODRS confirms success.
    """
    app_id = str(app_id or "").strip()
    summary = str(summary or "").strip()
    description = str(description or "").strip()
    version = str(version or "unknown").strip() or "unknown"
    try:
        stars = int(stars)
    except (TypeError, ValueError):
        return False, "invalid rating"
    if not app_id or stars not in (1, 2, 3, 4, 5) or not summary or not description:
        return False, "invalid review data"
    if has_submitted_odrs_rating(app_id):
        return False, "already rated"

    payload = {
        "app_id": app_id,
        "locale": _odrs_locale(),
        "summary": summary,
        "description": description,
        "user_hash": _odrs_user_hash(),
        "user_display": "LinuxToys User",
        "distro": _odrs_distro(),
        "rating": stars * 20,
        "version": version,
    }
    request = Request(
        ODRS_SUBMIT_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "LinuxToys-AppStream/1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
    except HTTPError as exc:
        try:
            result = json.loads(exc.read().decode("utf-8", errors="replace"))
            message = str(result.get("msg") or result.get("message") or exc.reason)
        except Exception:
            message = str(exc.reason or exc)
        return False, message
    except (URLError, OSError, ValueError) as exc:
        return False, str(exc)

    if not isinstance(result, dict) or not result.get("success"):
        message = result.get("msg") if isinstance(result, dict) else None
        return False, str(message or "ODRS rejected the review")

    _record_submitted_odrs_rating(app_id, stars)
    return True, ""

def _fetch_odrs_ratings():
    """Fetch the complete ODRS rating histogram in one HTTP request.

    Returns app-id -> {review_rating, review_count}.  None means the request or
    payload failed, allowing callers to preserve the previous completed cache.
    """
    url = "https://odrs.gnome.org/1.0/reviews/api/ratings"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "LinuxToys-AppStream/1",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    summaries = {}
    for component_id, histogram in payload.items():
        if not isinstance(histogram, dict):
            continue
        try:
            counts = [max(0, int(histogram.get(f"star{i}", 0) or 0)) for i in range(6)]
            count = max(0, int(histogram.get("total", sum(counts)) or 0))
        except (TypeError, ValueError):
            continue

        # ODRS currently publishes entries with at least two ratings.  Trust the
        # histogram itself for the average, but keep the advertised total for the
        # confidence weighting and app-page count.
        histogram_count = sum(counts)
        if count <= 0 or histogram_count <= 0:
            continue
        weighted_total = sum((i * 20) * counts[i] for i in range(6))
        rating = weighted_total / histogram_count
        summaries[str(component_id)] = {
            "review_rating": round(float(rating), 2),
            "review_count": int(count),
        }

    return summaries


def _apply_review_summaries(entries, previous=None):
    """Attach ODRS summaries from one bulk HTTP request.

    A failed download preserves the previous completed cache.  A successful
    download is authoritative: IDs absent from it have no usable ODRS rating.
    """
    previous = previous or {}
    fetched = _fetch_odrs_ratings()

    for item in entries or ():
        component_id = str(item.get("id", "") or "").strip()
        if not component_id:
            continue

        if fetched is None:
            summary = previous.get(component_id)
        else:
            summary = fetched.get(component_id)

        if summary:
            item["review_rating"] = summary.get("review_rating")
            item["review_count"] = summary.get("review_count")
        else:
            item.pop("review_rating", None)
            item.pop("review_count", None)

    return entries

def _native_component_payload(component):
    """Extract libappstream/GI values; Rust performs normalization and hashing."""
    return {
        "identity": _component_identity(component),
        "id": str(_safe_call(component, "get_id", "") or "").strip(),
        "name": str(_safe_call(component, "get_name", "") or "").strip(),
        "summary": str(_safe_call(component, "get_summary", "") or ""),
        "description": str(_safe_call(component, "get_description", "") or ""),
        "packages": [str(v) for v in _as_list(_safe_call(component, "get_pkgnames", []))],
        "categories": [str(v) for v in _as_list(_safe_call(component, "get_categories", []))],
        "launchable": _native_launchable_id(component),
        "icon": _icon_value(component),
        "screenshots": _component_screenshots(component),
        "homepage": _component_homepage(component),
        "donation": _component_donation(component),
        "license": _component_license(component),
        "developer": _developer_name(component),
        "origin": str(_safe_call(component, "get_origin", "") or "").strip(),
        "version": str(_safe_call(_safe_call(component, "get_release_default"), "get_version", "") or "").strip(),
    }


def _normalize_native_payloads(payloads):
    """Normalize a batch of extracted native AppStream components in Rust."""
    if not payloads:
        return []
    return list(_catalog_rs.normalize_native_appstream_components(payloads))







def _native_launchable_id(component) -> str:
    """Return the component's desktop-file launchable ID when AppStream exposes one."""
    for launchable in _as_list(_safe_call(component, "get_launchables", [])):
        value = str(_safe_call(launchable, "get_value", "") or "").strip()
        if value.endswith(".desktop"):
            return value
    component_id = str(_safe_call(component, "get_id", "") or "").strip()
    return component_id if component_id.endswith(".desktop") else ""





def _native_appstream_supported_host() -> bool:
    """Return whether LinuxToys may install native AppStream packages here."""
    try:
        from .compat import get_system_compat_keys

        return "steamos" not in get_system_compat_keys()
    except (ImportError, AttributeError):
        return True


def _load_appstream_components():
    if not _native_appstream_supported_host():
        return []

    import gi

    gi.require_version("AppStream", "1.0")
    from gi.repository import AppStream

    pool = AppStream.Pool()
    set_flags = getattr(pool, "set_flags", None)
    if set_flags is not None:
        # Native catalog only for the first integration milestone. Flatpak will
        # become its own independently refreshable source later.
        flags = AppStream.PoolFlags.LOAD_OS_CATALOG | AppStream.PoolFlags.LOAD_OS_METAINFO
        set_flags(flags)
    pool.load()
    return _as_list(pool.get_components())



def _flatpak_installations():
    """Return Flatpak installations whose local AppStream caches we can consume."""
    result = []
    user_root = Path(os.path.expanduser("~/.local/share/flatpak"))
    if user_root.is_dir():
        result.append(("user", "user", user_root))

    system_root = Path("/var/lib/flatpak")
    if system_root.is_dir():
        result.append(("system", "default", system_root))

    # Flatpak supports additional named system installations. Keep this parser tiny
    # and dependency-free; Path is the only field we need from these INI-ish files.
    config_dir = Path("/etc/flatpak/installations.d")
    if config_dir.is_dir():
        for config in sorted(config_dir.glob("*.conf")):
            current_name = None
            current_path = None
            try:
                for raw in config.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = raw.strip()
                    match = re.match(r'^\[Installation\s+"([^"]+)"\]$', line)
                    if match:
                        if current_name and current_path:
                            result.append(("system", current_name, Path(current_path)))
                        current_name, current_path = match.group(1), None
                    elif current_name and line.lower().startswith("path="):
                        current_path = line.split("=", 1)[1].strip()
                if current_name and current_path:
                    result.append(("system", current_name, Path(current_path)))
            except OSError:
                continue
    return result


def _configured_flatpak_remotes():
    """Enumerate configured remotes without requiring libflatpak GI bindings."""
    remotes = []
    if not shutil.which("flatpak"):
        return remotes
    for scope, installation, root in _flatpak_installations():
        cmd = ["flatpak"]
        if scope == "user":
            cmd.append("--user")
        elif installation == "default":
            cmd.append("--system")
        else:
            cmd.append(f"--installation={installation}")
        cmd += ["remotes", "--columns=name"]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=15, check=False)
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode != 0:
            continue
        for line in proc.stdout.splitlines():
            remote = line.strip()
            if not remote or remote.lower() == "name":
                continue
            remotes.append({"scope": scope, "installation": installation, "root": root, "remote": remote})
    return remotes


def _flatpak_eol_app_ids(source):
    """Return application IDs whose current Flatpak refs are marked EOL.

    EOL is ref/commit metadata, not AppStream XML metadata, so query libflatpak's
    local remote-ref view once per AppStream source instead of probing every app.
    Failure is intentionally non-fatal: AppStream remains usable on systems where
    the Flatpak GI typelib is unavailable.
    """
    try:
        import gi

        gi.require_version("Flatpak", "1.0")
        from gi.repository import Flatpak, Gio

        installation = Flatpak.Installation.new_for_path(
            Gio.File.new_for_path(str(source["root"])),
            source["scope"] == "user",
            None,
        )
        refs = installation.list_remote_refs_sync(source["remote"], None)
    except (ImportError, ValueError, TypeError, AttributeError, Exception):
        return set()

    eol_ids = set()
    for ref in refs or ():
        try:
            # Ignore runtimes/extensions: LinuxToys only publishes application
            # components from this catalog.
            kind = ref.get_kind()
            app_kind = getattr(getattr(Flatpak, "RefKind", None), "APP", None)
            if app_kind is not None and kind != app_kind:
                continue

            # Respect the architecture represented by this AppStream source.
            ref_arch = str(ref.get_arch() or "")
            if ref_arch and ref_arch != str(source.get("arch") or ""):
                continue

            if ref.get_eol():
                app_id = str(ref.get_name() or "").strip()
                if app_id:
                    eol_ids.add(app_id)
        except Exception:
            continue

    return eol_ids













def _refresh_missing_flatpak_appstream():
    """Refresh Flathub AppStream metadata when a configured installation has none.

    Flatpak normally refreshes this metadata itself, but a newly added remote can
    exist before its local AppStream database has been populated. Keep this as a
    narrow safeguard: only installations with a configured Flathub remote and no
    local Flathub AppStream directory are refreshed.
    """
    if not _flatpak_supported_host() or not shutil.which("flatpak"):
        return

    for remote in _configured_flatpak_remotes():
        if remote["remote"] != "flathub":
            continue
        if (remote["root"] / "appstream" / remote["remote"]).is_dir():
            continue

        cmd = ["flatpak"]
        if remote["scope"] == "user":
            cmd.append("--user")
        elif remote["installation"] == "default":
            cmd.append("--system")
        else:
            cmd.append(f"--installation={remote['installation']}")
        cmd += ["update", "--appstream", remote["remote"]]

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            # AppStream refresh is best-effort. Native metadata and any other
            # already-cached Flatpak installation must remain usable.
            continue


def _flatpak_appstream_sources():
    """Locate locally cached AppStream catalogs for configured Flatpak remotes."""
    if not _flatpak_supported_host():
        return []

    sources = []
    for remote in _configured_flatpak_remotes():
        # LinuxToys' pkg_flat currently installs from Flathub explicitly. Do not
        # publish apps from another remote until that installer accepts a remote.
        if remote["remote"] != "flathub":
            continue
        base = remote["root"] / "appstream" / remote["remote"]
        if not base.is_dir():
            continue
        for arch_dir in base.iterdir():
            active = arch_dir / "active"
            if not active.is_dir():
                continue
            xml_path = active / "appstream.xml.gz"
            if not xml_path.is_file():
                xml_path = active / "appstream.xml"
            if xml_path.is_file():
                item = dict(remote)
                item.update({"arch": arch_dir.name, "appstream_dir": active, "xml_path": xml_path})
                sources.append(item)
    return sources


def _load_flatpak_components():
    """Parse and normalize local Flatpak AppStream catalogs in Rust.

    Python still owns source discovery and Flatpak EOL-ref inspection because those
    are host/integration concerns. The expensive XML decode, localized metadata
    extraction, description/screenshot normalization and release counting happen
    in one Rust call per AppStream source.
    """
    if not _flatpak_supported_host():
        return [], []

    entries = []
    source_keys = []
    now = int(time.time())

    for source in _flatpak_appstream_sources():
        source_keys.append(
            f"flatpak:{source['scope']}:{source['installation']}:{source['remote']}:{source['arch']}"
        )
        eol_app_ids = sorted(_flatpak_eol_app_ids(source))
        rust_source = {
            "scope": source.get("scope", ""),
            "installation": source.get("installation", ""),
            "remote": source.get("remote", ""),
            "arch": source.get("arch", ""),
            "appstream_dir": os.fspath(source.get("appstream_dir", "")),
            # Rust reads media_baseurl/media-baseurl directly from the XML root.
            "media_baseurl": "",
        }
        parsed = _catalog_rs.parse_flatpak_appstream_source(
            os.fspath(source["xml_path"]),
            json.dumps(rust_source, ensure_ascii=False, separators=(",", ":")),
            eol_app_ids,
            now,
        )
        entries.extend(item for item in parsed if isinstance(item, dict))

    return entries, sorted(source_keys)

def _path_state(path):
    """Return a cheap metadata signature for one file or directory."""
    path = Path(path)
    try:
        stat = path.stat()
    except OSError:
        return None
    return (str(path), stat.st_mtime_ns, stat.st_size)


def _directory_state(path):
    """Return metadata sufficient to detect directory membership changes."""
    path = Path(path)
    try:
        stat = path.stat()
    except OSError:
        return None
    if not path.is_dir():
        return None
    return (str(path), stat.st_mtime_ns, stat.st_size)


def _source_inventory_default():
    return {
        "schema": 1,
        "native": {"roots": {}},
    }


def _load_source_inventory():
    inventory = _read_json(SOURCE_INVENTORY_PATH, _source_inventory_default())
    if not isinstance(inventory, dict) or inventory.get("schema") != 1:
        return _source_inventory_default()
    native = inventory.get("native")
    if not isinstance(native, dict):
        inventory["native"] = {"roots": {}}
    elif not isinstance(native.get("roots"), dict):
        native["roots"] = {}
    return inventory


def _scan_source_root(root, recursive):
    """Discover source files once and retain only their paths.

    Directory mtimes are tracked separately. A later warm check can therefore
    reuse this file inventory until directory membership changes.
    """
    root = Path(root)
    files = []
    directories = {}

    if not root.exists():
        return {"kind": "missing", "recursive": bool(recursive), "directories": {}, "files": []}

    if root.is_file():
        return {
            "kind": "file",
            "recursive": False,
            "directories": {},
            "files": [str(root)],
        }

    def remember_directory(directory):
        state = _directory_state(directory)
        if state is not None:
            directories[str(directory)] = [state[1], state[2]]

    remember_directory(root)
    try:
        if recursive:
            # os.walk already yields every directory. Tracking each directory's
            # metadata lets us notice additions/removals anywhere below the root
            # without re-running Path.rglob() on an unchanged tree.
            for current, dirnames, filenames in os.walk(root):
                current_path = Path(current)
                remember_directory(current_path)
                for name in filenames:
                    files.append(str(current_path / name))
        else:
            for child in root.iterdir():
                if child.is_file():
                    files.append(str(child))
                elif child.is_dir():
                    # Non-recursive repository directories only need the root
                    # membership mtime; child contents are intentionally ignored.
                    pass
    except OSError:
        pass

    return {
        "kind": "directory",
        "recursive": bool(recursive),
        "directories": directories,
        "files": sorted(set(files)),
    }


def _source_root_inventory_is_current(root, cached):
    """Return True when a cached source inventory can be reused."""
    root = Path(root)
    if not isinstance(cached, dict):
        return False

    kind = cached.get("kind")
    if not root.exists():
        return kind == "missing"

    if root.is_file():
        return kind == "file"

    if not root.is_dir() or kind != "directory":
        return False

    directories = cached.get("directories")
    if not isinstance(directories, dict) or not directories:
        return False

    # A directory mtime changes when an immediate child is added, removed, or
    # renamed. Recursive roots remember every directory from the previous scan,
    # so membership changes anywhere in the tree invalidate only that root.
    for directory, old_state in directories.items():
        state = _directory_state(directory)
        if state is None:
            return False
        try:
            old_mtime, old_size = int(old_state[0]), int(old_state[1])
        except (TypeError, ValueError, IndexError):
            return False
        if state[1] != old_mtime or state[2] != old_size:
            return False

    return True


def _native_source_fingerprint(inventory=None):
    """Fingerprint native AppStream state while avoiding repeated tree discovery.

    Known source trees are persisted separately. On warm checks LinuxToys stats
    the remembered directories/files; Path.rglob()/os.walk is only repeated for
    roots whose directory membership changed.
    """
    if not _native_appstream_supported_host():
        return "unsupported", False

    inventory = inventory if isinstance(inventory, dict) else _source_inventory_default()
    native_inventory = inventory.setdefault("native", {})
    cached_roots = native_inventory.setdefault("roots", {})
    inventory_changed = False

    repo_locations = (
        "/etc/apt/sources.list",
        "/etc/apt/sources.list.d",
        "/etc/yum.repos.d",
        "/etc/dnf/repos.d",
        "/etc/zypp/repos.d",
        "/etc/pacman.conf",
        "/etc/pacman.d",
        "/etc/eopkg",
    )
    appstream_locations = (
        "/usr/share/app-info",
        "/usr/share/appdata",
        "/usr/share/metainfo",
        "/var/cache/app-info",
        "/var/lib/app-info",
        "/var/cache/swcatalog",
    )

    roots = [(location, False) for location in repo_locations]
    roots.extend((location, True) for location in appstream_locations)

    states = []
    active_keys = set()
    for location, recursive in roots:
        key = f"{int(recursive)}:{location}"
        active_keys.add(key)
        cached = cached_roots.get(key)

        if not _source_root_inventory_is_current(location, cached):
            cached = _scan_source_root(location, recursive)
            cached_roots[key] = cached
            inventory_changed = True

        # Keep discovery/policy in Python, but let Rust perform the hot warm-start
        # metadata stat/hash pass over the already-known inventory.
        states.extend((cached.get("directories") or {}).keys())
        states.extend(cached.get("files") or ())

    stale_keys = set(cached_roots) - active_keys
    if stale_keys:
        for key in stale_keys:
            cached_roots.pop(key, None)
        inventory_changed = True

    return _catalog_rs.source_metadata_fingerprint(states), inventory_changed


def _flatpak_source_fingerprint():
    """Fingerprint Flathub configuration and its locally cached AppStream data."""
    if not _flatpak_supported_host():
        return "unsupported"

    states = []
    for source in _flatpak_appstream_sources():
        path_state = _path_state(source["xml_path"])
        states.append((
            source["scope"],
            source["installation"],
            source["remote"],
            source["arch"],
            path_state,
        ))

    payload = {
        "flatpak": bool(shutil.which("flatpak")),
        "sources": sorted(states, key=repr),
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_fingerprints():
    inventory = _load_source_inventory()
    native, inventory_changed = _native_source_fingerprint(inventory)
    result = {
        "native": native,
        "flatpak": _flatpak_source_fingerprint(),
    }
    if inventory_changed or not SOURCE_INVENTORY_PATH.is_file():
        _atomic_json_write(SOURCE_INVENTORY_PATH, inventory)
    return result


def _default_state():
    return {
        "schema": CACHE_SCHEMA,
        "complete": False,
        "last_completed": 0,
        "sources": {
            "native": {"complete": False, "updated": 0, "fingerprint": ""},
            "flatpak": {"complete": False, "updated": 0, "fingerprint": ""}
        },
    }


def get_state():
    state = _read_json(STATE_PATH, _default_state())
    if not isinstance(state, dict) or state.get("schema") != CACHE_SCHEMA:
        return _default_state()
    return state


def load_catalog():
    """Return the last fully published catalog without triggering any work.

    The published JSON remains the on-disk interchange/cache format, but decoding
    is now owned by the Rust catalog backend.
    """
    started = time.perf_counter()
    data = list(_catalog_rs.load_appstream_catalog(os.fspath(CATALOG_PATH)))
    elapsed = time.perf_counter() - started
    print(
        f"[AppStream timing] Rust catalog load: {elapsed:.3f}s "
        f"({len(data)} components)"
    )
    return data


def cache_needs_refresh(now=None) -> bool:
    now = time.time() if now is None else float(now)
    state = get_state()
    if not state.get("complete") or not CATALOG_PATH.is_file():
        return True

    completed = float(state.get("last_completed") or 0)
    if completed <= 0 or now - completed >= CACHE_MAX_AGE:
        return True

    # Refresh early when the installable software universe changed. This is cheap:
    # only repository definitions and local AppStream metadata are stat'ed.
    current = _source_fingerprints()
    sources = state.get("sources", {})
    return (
        current["native"] != sources.get("native", {}).get("fingerprint")
        or current["flatpak"] != sources.get("flatpak", {}).get("fingerprint")
    )


def _load_partial():
    partial = _read_json(PARTIAL_PATH, {})
    if not isinstance(partial, dict) or partial.get("schema") != CACHE_SCHEMA:
        return [], set()
    entries = partial.get("entries")
    if not isinstance(entries, list):
        return [], set()
    processed_values = partial.get("processed")
    if isinstance(processed_values, list):
        processed = {str(value) for value in processed_values if value}
    else:
        processed = {
            str(item.get("identity"))
            for item in entries
            if isinstance(item, dict) and item.get("identity")
        }
    return entries, processed


def _write_partial(entries, processed):
    _atomic_json_write(
        PARTIAL_PATH,
        {
            "schema": CACHE_SCHEMA,
            "entries": entries,
            "processed": sorted(processed),
        },
    )


def refresh_cache(force=False, status_callback=None):
    """Refresh the native AppStream cache synchronously.

    Intended to run on a worker thread.  Returns a result dictionary containing
    ``changed``, ``count`` and, on failure, ``error``.  Existing completed data is
    never destroyed by a failed refresh.
    """
    with _LOCK:
        if not force and not cache_needs_refresh():
            if status_callback:
                status_callback("ready")
            # Do not decode the potentially large catalog merely to report a count.
            # A fresh cache needs no catalog contents in this worker at all.
            state = get_state()
            return {
                "success": True,
                "changed": False,
                "count": int(state.get("count") or 0),
            }

        if status_callback:
            status_callback("building")

        try:
            # The published catalog remains authoritative while the delta is built.
            # Nothing touches catalog.json until the completed candidate is atomically
            # written at the end of this transaction.
            previous = load_catalog()

            # Delta reuse is only valid when the published catalog was produced by
            # this exact schema. A schema bump can change the normalized JSON shape
            # without changing the underlying AppStream metadata hash (for example,
            # schema 15 groups screenshot resolution variants). Reusing a schema-14
            # entry here would therefore preserve the old representation forever.
            published_state = _read_json(STATE_PATH, {})
            reuse_previous_entries = (
                isinstance(published_state, dict)
                and published_state.get("schema") == CACHE_SCHEMA
                and published_state.get("complete") is True
            )
            reusable_previous = previous if reuse_previous_entries else []

            native_supported = _native_appstream_supported_host()
            components = _load_appstream_components()
            entries = []
            processed = set()

            if native_supported:
                # GI/libappstream remains responsible for loading distro metadata, but
                # normalization, filtering, description parsing and fingerprinting are
                # performed in Rust in coarse batches to avoid per-field PyO3 calls.
                for start in range(0, len(components), CHECKPOINT_EVERY):
                    batch = components[start:start + CHECKPOINT_EVERY]
                    payloads = [_native_component_payload(component) for component in batch]
                    normalized = _normalize_native_payloads(payloads)

                    for payload in payloads:
                        identity = str(payload.get("identity", "") or "")
                        if identity:
                            processed.add(identity)

                    entries.extend(item for item in normalized if isinstance(item, dict))

                    _write_partial(entries, processed)

            # Flatpak normally keeps remote AppStream metadata current itself. A
            # freshly configured Flathub remote can briefly have no local AppStream
            # database, though, so populate that missing metadata before discovery.
            _refresh_missing_flatpak_appstream()

            # Flatpak is reconciled independently against the same published catalog.
            # Unchanged XML components reuse their normalized JSON entries verbatim.
            flatpak_entries, _flatpak_catalog_sources = _load_flatpak_components()

            # Keep the last completed popularity metrics available as a fallback.
            # A temporary Flathub statistics failure must not erase useful ranking
            # data from an otherwise successful AppStream refresh.
            previous_review_metrics = {
                str(item.get("id", "")): {
                    "review_rating": item.get("review_rating"),
                    "review_count": item.get("review_count"),
                }
                for item in previous
                if isinstance(item, dict)
                and item.get("id")
                and item.get("review_count")
            }
            previous_flatpak_metrics = {
                str(item.get("id", "")): {
                    "popularity_downloads": item.get("popularity_downloads"),
                    "popularity_metric": item.get("popularity_metric"),
                }
                for item in previous
                if isinstance(item, dict)
                and item.get("source") == "flatpak"
                and item.get("id")
                and item.get("popularity_metric") is not None
            }

            popularity.apply_flathub_metrics(
                flatpak_entries,
                fallback_metrics=previous_flatpak_metrics,
            )
            entries.extend(flatpak_entries)

            # Rust owns the incremental reconciliation step now. It builds the
            # previous identity index once, reuses byte-for-byte normalized entries
            # whose metadata hash is unchanged, drops entries absent from the new
            # source set, and returns deterministic catalog ordering.
            entries = list(_catalog_rs.reconcile_appstream_components(
                reusable_previous,
                entries,
            ))

            # ODRS publishes all rating histograms through one bulk HTTP endpoint.
            # This works independently of the distro's libappstream typelib and
            # avoids one network round-trip per application.
            _apply_review_summaries(entries, previous_review_metrics)

            changed = previous != entries
            _atomic_json_write(CATALOG_PATH, entries)

            now = int(time.time())
            state = _default_state()
            state.update({"complete": True, "last_completed": now, "count": len(entries)})
            # Capture fingerprints only after the successful build so the state
            # describes the exact environment represented by the published catalog.
            fingerprints = _source_fingerprints()
            state["sources"]["native"] = {
                "complete": True,
                "updated": now,
                "fingerprint": fingerprints["native"],
            }
            state["sources"]["flatpak"] = {
                "complete": True,
                "updated": now,
                "fingerprint": fingerprints["flatpak"],
            }
            _atomic_json_write(STATE_PATH, state)

            try:
                PARTIAL_PATH.unlink()
            except FileNotFoundError:
                pass

            if status_callback:
                status_callback("ready")
            return {"success": True, "changed": changed, "count": len(entries)}
        except Exception as error:
            # The published catalog/state were never invalidated, so a failed delta
            # leaves the last complete catalog authoritative. The partial checkpoint
            # is retained only as diagnostic/resume-friendly working state.
            if status_callback:
                status_callback("error")
            return {
                "success": False,
                "changed": False,
                "count": len(load_catalog()),
                "error": str(error),
            }
