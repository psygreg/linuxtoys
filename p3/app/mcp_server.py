#!/usr/bin/env python3
"""LinuxToys MCP server.

Lets AI agents interact with LinuxToys the way a user would: browse and
search the catalog, read app pages (descriptions, screenshots, donation and
purchase links), install and remove apps, change settings (automatic updates,
automatic bug reports, language), translate descriptions, and read or export
the Action Registry.

Design:

- Transport: MCP Streamable HTTP on 127.0.0.1 (see DEFAULT_PORT), JSON-RPC
  2.0 responses with a per-client ``Mcp-Session-Id``. Implemented with the
  standard library only — no new runtime dependencies.
- Auth: a per-install random token stored at ``~/.config/linuxtoys/mcp-token``
  (mode 0600). Requests must present it as ``Authorization: Bearer <token>``
  or ``X-LinuxToys-Token: <token>``. This keeps other local users and browser
  origins from driving installs.
- Privilege escalation: scripts run exactly like GUI/CLI runs. When a step
  needs root, the usual ``askpass`` zenity dialog appears on the user's
  screen — credentials are typed by the user and never touch the agent.
  The systemd user unit bakes the graphical session environment
  (DISPLAY/WAYLAND_DISPLAY/…) so those dialogs reach the user's display.
- Isolation: the service never registers the GUI's application identity and
  holds no GUI single-instance state, so the app keeps launching normally
  through every other method while the MCP server is running.

Entry points: ``linuxtoys --mcp`` (also the systemd ExecStart) or
``python3 -m app.mcp_server`` for development.
"""

import base64
import hmac
import json
import os
import queue
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import OrderedDict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

if __package__:
    from . import easy_cli
    from . import installed_packages
    from . import manifest_helper
    from . import appstream_parser
    from . import appstream_cache
    from . import appstream_logs
    from . import appimage_catalog
    from . import antenna
    from . import parser
    from . import registry_utils
    from . import translate_helper
    from .compat import get_linuxtoys_cache_dir, get_system_compat_keys, script_is_compatible
    from .lang_utils import (
        create_translator,
        detect_system_language,
        get_available_languages,
        get_automatic_error_reports,
        get_automatic_updates,
        get_mcp_server_port,
        get_saved_language,
        save_language,
        load_translations,
        save_automatic_error_reports,
        save_automatic_updates,
        get_config_dir,
    )
    from .library_loader import script_command, script_environment
    from .repo_parser import materialize_repo_script
    from .term_registry import ExecutionRegistry
    from .updater import __version__
else:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import easy_cli
    from app import installed_packages
    from app import manifest_helper
    from app import appstream_parser
    from app import appstream_cache
    from app import appstream_logs
    from app import appimage_catalog
    from app import antenna
    from app import parser
    from app import registry_utils
    from app import translate_helper
    from app.compat import get_linuxtoys_cache_dir, get_system_compat_keys, script_is_compatible
    from app.lang_utils import (
        create_translator,
        detect_system_language,
        get_available_languages,
        get_automatic_error_reports,
        get_automatic_updates,
        get_mcp_server_port,
        get_saved_language,
        save_language,
        load_translations,
        save_automatic_error_reports,
        save_automatic_updates,
        get_config_dir,
    )
    from app.library_loader import script_command, script_environment
    from app.repo_parser import materialize_repo_script
    from app.term_registry import ExecutionRegistry
    from app.updater import __version__


SERVER_NAME = "linuxtoys"
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = frozenset({"2025-03-26", "2025-06-18"})
DEFAULT_PORT = 7420
MAX_BODY_BYTES = 1024 * 1024
MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024
SESSION_IDLE_TTL = 24 * 60 * 60
JOB_LOG_LINES = 400

def shlex_quote(value):
    return shlex.quote(str(value))
UNIT_FILE_NAME = "linuxtoys-mcp.service"
TRANSLATED_FALLBACK = "en"

_TRANSIENT_SERVER = {"server": None, "started": 0.0}


def _translations():
    """Cached, auto-detected translations for catalog identity strings."""
    return load_translations()


def _script_dir():
    """Resolve the LinuxToys scripts tree root (sets SCRIPT_DIR like the CLI)."""
    return easy_cli.resolve_script_dir()


def _tmp_dir():
    directory = "/tmp/linuxtoys"
    os.makedirs(directory, mode=0o700, exist_ok=True)
    return directory


# ---------------------------------------------------------------------------
# Auth token
# ---------------------------------------------------------------------------

def token_path():
    return os.path.join(get_config_dir(), "mcp-token")


def ensure_token():
    """Create the access token file on first use and return the token."""
    path = token_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            token = handle.read().strip()
        if token:
            return token
    except OSError:
        pass
    token = secrets.token_urlsafe(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token + "\n")
        os.chmod(path, 0o600)
    except OSError:
        pass
    return token


def token_matches(presented):
    try:
        with open(token_path(), "r", encoding="utf-8") as handle:
            token = handle.read().strip()
    except OSError:
        return False
    if not token or not presented:
        return False
    return hmac.compare_digest(token, presented.strip())


# ---------------------------------------------------------------------------
# Catalog helpers (GTK-free: parser + appstream_parser only)
# ---------------------------------------------------------------------------

def _stable_id(entry):
    value = str(
        entry.get("appstream_id")
        or entry.get("repo_app_id")
        or entry.get("id")
        or entry.get("script")
        or ""
    ).strip()
    if value:
        return value
    path = str(entry.get("virtual_path") or entry.get("path") or "")
    for prefix in ("repo://", "appstream://", "aur://"):
        if path.startswith(prefix):
            return path[len(prefix):]
    return os.path.splitext(os.path.basename(path))[0] if path else ""


def _entry_kind(entry):
    if entry.get("appstream_source") == "appimage":
        return "appimage"
    source = str(entry.get("appstream_source") or "").strip()
    if entry.get("is_appstream_entry"):
        return source or "appstream"
    if entry.get("is_repo_entry"):
        return "repo"
    return "script"


def _iter_script_entries():
    """All catalog entries LinuxToys would show: scripts, repo and AppStream."""
    translations = _translations()
    entries = []
    categories = parser.get_categories(translations) or []
    for category in categories:
        if category.get("is_script"):
            entries.append(category)
            continue
        entries.extend(parser.get_all_scripts_recursive(category["path"], translations) or [])
    entries.extend(parser.get_repo_entries(translations) or [])
    return entries


def _search_catalog(query, limit=20):
    """Fuzzy name/description search across every installed catalog source."""
    query = str(query or "").strip().casefold()
    if len(query) < 2:
        return []
    translations = _translations()
    scored = []

    for entry in _iter_script_entries():
        name = str(entry.get("name") or "")
        stable = _stable_id(entry)
        description = str(entry.get("description") or "")
        haystack = f"{name}\n{stable}\n{description}".casefold()
        score = 0
        if query == name.casefold() or query == stable.casefold():
            score = 100
        elif query in name.casefold():
            score = 80
        elif query in stable.casefold():
            score = 70
        elif query in description.casefold():
            score = 30
        else:
            # Loose fallback: every word must appear somewhere.
            words = [w for w in re.split(r"\s+", query) if w]
            if words and all(w in haystack for w in words):
                score = 10
        if score:
            scored.append((score, entry))

    try:
        scripts_dir, curated_entries, category_paths = _appstream_context()
        for entry, score in appstream_parser.search_entries(
            scripts_dir, query, curated_entries=curated_entries, category_paths=category_paths
        ):
            scored.append((max(1, int(score)), entry))
    except Exception:
        pass  # A cold or broken AppStream cache must not hide script matches.

    # Punctuation-heavy queries ("0 A.D.") miss the Rust token index; an exact
    # ID/name resolution is still worth returning.
    if not any(
        str(candidate.get("appstream_id") or "").strip().casefold() == query
        for _score, candidate in scored
        if candidate.get("appstream_id")
    ):
        try:
            scripts_dir, curated_entries, category_paths = _appstream_context()
            exact = (
                appstream_parser.find_entry_by_id(scripts_dir, query, curated_entries, category_paths)
                or appstream_parser.find_entry_by_name(scripts_dir, query, curated_entries, category_paths)
            )
            if exact is not None:
                scored.append((90, exact))
        except Exception:
            pass

    seen = set()
    results = []
    for score, entry in sorted(scored, key=lambda pair: -pair[0]):
        stable = _stable_id(entry)
        key = (stable.casefold(), str(entry.get("name", "")))
        if not stable or key in seen:
            continue
        seen.add(key)
        results.append({
            "id": stable,
            "name": str(entry.get("name") or stable),
            "description": str(entry.get("description") or ""),
            "source": _entry_kind(entry),
            "category": str(entry.get("category") or ""),
            "match_score": score,
        })
        if len(results) >= max(1, int(limit)):
            break
    return results


def _screenshot_urls(entry):
    urls = []
    raw = entry.get("screenshots") or []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                urls.append(item)
            elif isinstance(item, dict):
                for image in (item.get("images") or []):
                    url = str(image.get("url") or "").strip()
                    if url:
                        urls.append(url)
    return urls


def _blocks_to_text(blocks):
    """Flatten structured description blocks into plain text."""
    lines = []
    for block in blocks or ():
        if block.get("type") == "paragraph":
            lines.append("".join(str(s.get("text") or "") for s in (block.get("spans") or ())))
        elif block.get("type") in ("unordered_list", "ordered_list"):
            prefix = "- " if block.get("type") == "unordered_list" else "* "
            for item in (block.get("items") or ()):
                lines.append(prefix + "".join(str(s.get("text") or "") for s in item))
        elif isinstance(block.get("text"), str):
            lines.append(block["text"])
    return "\n\n".join(line for line in lines if line.strip())


def _installed_state(entry):
    """Where LinuxToys currently sees this app, based on registry + packages."""
    registry_data = registry_utils.parse_registry_file()
    identities = {
        str(entry.get("registry_name") or "").strip(),
        str(entry.get("name") or "").strip(),
        _stable_id(entry).casefold(),
    }
    transactions = []
    for identity in identities:
        transactions.extend(registry_data.get(identity) or [])
    observed = None
    try:
        observed = installed_packages.match(entry)
    except Exception:
        observed = None
    return {
        "in_action_registry": bool(transactions),
        "last_transaction": transactions[-1][0] if transactions else "",
        "observed": dict(observed) if observed else None,
        "installed": bool(transactions or observed),
    }


def _app_links(entry):
    links = {}
    homepage = str(entry.get("homepage") or "").strip()
    if homepage:
        links["homepage"] = homepage
    donate = str(entry.get("donate_url") or "").strip()
    if donate:
        links["donate"] = donate
    purchase = str(entry.get("purchase_url") or "").strip()
    if purchase:
        links["purchase"] = purchase
    options = []
    for option in (entry.get("purchase_options") or ()):
        if isinstance(option, dict) and option.get("url"):
            options.append({
                "price": option.get("price", ""),
                "currency_symbol": option.get("currency_symbol", ""),
                "period": option.get("period", ""),
                "url": option.get("url"),
            })
    if options:
        links["purchase_options"] = options
    subscriptions = []
    for option in (entry.get("subscription_options") or ()):
        if isinstance(option, dict) and option.get("url"):
            subscriptions.append({
                "price": option.get("price", ""),
                "currency_symbol": option.get("currency_symbol", ""),
                "period": option.get("period", ""),
                "url": option.get("url"),
            })
    if subscriptions:
        links["subscription_options"] = subscriptions
    return links


def _appstream_context():
    """Resolve the AppStream universe exactly like the GUI catalog views.

    Uses the fuller curated set (repository entries plus curated scripts) so
    MCP search results match the GUI's duplicate suppression.

    ``category_paths`` must be included: without it the Rust category mapping
    drops every non-Homebrew component, and a derived-cache rebuild triggered
    by this server would publish that incomplete generation. (_runtime_catalog
    now also defaults a missing context to the indexed paths, so this stays
    correct even if the explicit context is lost.)
    """
    translations = _translations()
    return (
        parser.SCRIPTS_DIR,
        parser._get_appstream_curated_entries(translations),
        parser._indexed_category_paths(),
    )


def _resolve_entry(app_id):
    """Resolve a stable ID to a full catalog entry, or None."""
    if not isinstance(app_id, str) or not app_id.strip():
        return None
    target = app_id.strip()

    # Curated LinuxToys IDs retain absolute priority (same order as the
    # browser-facing uri_parser).
    entry = manifest_helper.find_script_by_id(target, _translations())
    if entry is not None:
        return entry

    scripts_dir, curated_entries, category_paths = _appstream_context()
    try:
        entry = appstream_parser.find_entry_by_id(
            scripts_dir, target, curated_entries, category_paths
        )
        if entry is None:
            entry = appstream_parser.find_entry_by_name(
                scripts_dir, target, curated_entries, category_paths
            )
        if entry is not None:
            return entry
    except Exception:
        pass

    # The AUR pseudo-catalog is outside resolve_install_target: accept exact
    # package-name matches only, so resolution stays deterministic.
    try:
        from . import aur_cache
        if aur_cache.enabled():
            folded = target.casefold()
            for candidate, _score in aur_cache.search_entries(target, limit=5):
                if str(candidate.get("package-name") or "").strip().casefold() == folded:
                    return candidate
    except Exception:
        pass
    return None


def _app_details(entry):
    """Build the MCP app page payload from one catalog entry."""
    app_id = _stable_id(entry)
    details = {
        "id": app_id,
        "name": str(entry.get("name") or app_id),
        "source": _entry_kind(entry),
        "category": str(entry.get("category") or ""),
        "description": str(entry.get("description") or ""),
        "homepage": str(entry.get("homepage") or ""),
        "links": _app_links(entry),
        "screenshots": _screenshot_urls(entry),
        "icon": str(entry.get("icon") or "application-x-executable"),
        "revertible": str(entry.get("revert", "yes") or "yes") != "no",
        "needs_reboot": str(entry.get("reboot", "no") or "no") == "yes",
        "installed": _installed_state(entry),
    }
    if entry.get("appstream_source"):
        details["appstream_source"] = str(entry.get("appstream_source"))
        details["appstream_version"] = str(entry.get("appstream_version") or "")
        details["developer"] = str(entry.get("developer") or "")
        details["license"] = str(entry.get("license") or "")
        source_options = [
            str(option.get("appstream_source") or "")
            for option in (entry.get("source_options") or ())
            if isinstance(option, dict) and option.get("appstream_source")
        ]
        if source_options:
            details["available_sources"] = sorted(set(source_options))

    blocks = entry.get("long_description_blocks")
    if isinstance(blocks, list) and blocks:
        details["description_blocks"] = blocks
        details["description_format"] = str(entry.get("long_description_format") or "appstream")
        details["description_locale"] = str(entry.get("long_description_locale") or "")
        flat = _blocks_to_text(blocks)
        if flat:
            details["long_description"] = flat
    elif isinstance(entry.get("long_description"), str) and entry["long_description"].strip():
        details["long_description"] = entry["long_description"]
        details["description_format"] = str(entry.get("long_description_format") or "markdown")
        details["description_locale"] = str(entry.get("long_description_locale") or "")
    if entry.get("summary"):
        details["summary"] = str(entry.get("summary"))
    return details


def _fetch_screenshot(url):
    """Download one screenshot; returns (bytes, mime) or raises RuntimeError."""
    if not re.match(r"^https?://", str(url)):
        raise ValueError("Only http(s) screenshot URLs can be fetched")
    request = Request(url, headers={"User-Agent": "LinuxToys MCP"})
    with urlopen(request, timeout=30) as response:
        data = response.read(MAX_SCREENSHOT_BYTES + 1)
    if len(data) > MAX_SCREENSHOT_BYTES:
        raise ValueError("Screenshot is too large to return")
    if data.startswith(b"\x89PNG"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith(b"GIF8"):
        mime = "image/gif"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError("Unsupported screenshot format")
    return data, mime


# ---------------------------------------------------------------------------
# Local package files (Package View parity, GTK-free)
# ---------------------------------------------------------------------------
#
# The GUI accepts package files through the Package View: an inspector fills
# name/version/architecture/... for the file, a per-kind host guard decides
# whether that package format is installable on this system, and the install
# runs a generated ``pkg_fromfile``/``pkg_appimage`` one-liner through the
# shared script machinery (askpass dialog on the user's screen, native-manager
# busy waits, transmap, Action Registry, auto-revert). The MCP server mirrors
# exactly that flow with a GTK-free inspector: same accepted extensions, same
# probe commands and same fallback to filename-derived metadata.

PACKAGE_STAGING_SUBDIR = "mcp-packages"
# Upper bound for downloads fetched by agents. Generous — driver bundles and
# multi-rpm meta-packages exceed 200 MiB — but never unbounded.
MAX_PACKAGE_DOWNLOAD_BYTES = 4 * 1024 * 1024 * 1024
PACKAGE_KIND_EXTENSIONS = (
    (".deb", "deb"), (".rpm", "rpm"), (".pacman", "arch"),
    (".eopkg", "eopkg"), (".flatpakref", "flatpakref"),
    (".flatpak", "flatpak"), (".snap", "snap"), (".appimage", "appimage"),
)
PACKAGE_KIND_LABELS = {
    "deb": "Debian package",
    "rpm": "RPM package",
    "arch": "Arch Linux package",
    "eopkg": "Solus package",
    "flatpakref": "Flatpak reference",
    "flatpak": "Flatpak bundle",
    "snap": "Snap package",
    "appimage": "AppImage",
}
SUPPORTED_PACKAGE_KINDS_TEXT = (
    ".deb, .rpm, .pkg.tar.*/.pacman, .eopkg, .flatpak, .flatpakref, "
    ".snap, .appimage"
)


def package_staging_dir():
    directory = os.path.join(_tmp_dir(), PACKAGE_STAGING_SUBDIR)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    return directory


def package_file_kind(path):
    """Package kind accepted for a local file, or None (window.py parity)."""
    name = os.path.basename(os.fspath(path)).lower()
    if re.fullmatch(r".+\.pkg\.tar\.(?:zst|xz|gz|lz4)", name):
        return "arch"
    for suffix, kind in PACKAGE_KIND_EXTENSIONS:
        if name.endswith(suffix):
            return kind
    return None


def package_kind_supported_on_host(kind):
    """Same per-kind host guard the GUI applies before opening a package file."""
    keys = get_system_compat_keys()
    if kind == "snap":
        return not keys & {"steamos", "dakota", "gnomeos", "kde-linux"}
    if kind in ("flatpak", "flatpakref"):
        return "systemd" in keys
    if kind == "appimage":
        return True
    if kind == "deb":
        return bool(keys & {"debian", "ubuntu"})
    if kind == "rpm":
        return bool(keys & {"fedora", "rhel", "suse", "ostree"})
    if kind == "arch":
        return bool(keys & {"arch", "cachy", "manjaro"})
    if kind == "eopkg":
        return "solus" in keys
    return False


def package_file_signature(path):
    """Identify one exact file version, the way the GUI queue guards re-runs."""
    stat = os.stat(path)
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def _package_probe_output(argv, timeout=30):
    """Best-effort stdout of a package metadata probe; "" on any failure."""
    try:
        result = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ""
    return (result.stdout or "").strip()


def _control_field_value(control, field):
    """Read a control-style field, merging indented continuation lines."""
    prefix = field + ":"
    value = ""
    collecting = False
    for line in (control or "").splitlines():
        if collecting:
            if line.startswith((" ", "\t")):
                part = line.strip()
                if part and part != ".":
                    value = f"{value} {part}" if value else part
                continue
            break
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            collecting = True
    return value


def _pkginfo_field_value(text, key):
    """Read a `key = value` line from a .PKGINFO payload."""
    prefix = key + " = "
    for line in (text or "").splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""


def inspect_local_package(path):
    """Package View metadata for one local package file (GTK-free).

    Mirrors the native inspector: same extension mapping, same probe commands
    and the same fallback to filename-derived values. The GUI's icon caching
    is intentionally not part of this flow.
    """
    real = os.path.realpath(os.fspath(path))
    basename = os.path.basename(real)
    name = os.path.splitext(basename)[0]
    kind = package_file_kind(real)
    if kind is None:
        return None
    version = architecture = maintainer = description = ""
    try:
        size = os.path.getsize(real)
    except OSError:
        size = 0

    if kind == "deb":
        control = _package_probe_output(["dpkg-deb", "-f", real])
        if control:
            value = _control_field_value(control, "Package")
            if value:
                name = value
            version = _control_field_value(control, "Version")
            architecture = _control_field_value(control, "Architecture")
            maintainer = _control_field_value(control, "Maintainer")
            description = _control_field_value(control, "Description")
    elif kind == "rpm":
        fields = _package_probe_output([
            "rpm", "-qp", "--qf",
            "%{NAME}\\x1f%{VERSION}-%{RELEASE}\\x1f%{ARCH}"
            "\\x1f%{PACKAGER}\\x1f%{SUMMARY}",
            real,
        ]).split("\x1f")
        if fields and fields[0]:
            name = fields[0]
        version = fields[1] if len(fields) > 1 else ""
        architecture = fields[2] if len(fields) > 2 else ""
        maintainer = fields[3] if len(fields) > 3 else ""
        description = fields[4] if len(fields) > 4 else ""
    elif kind == "arch":
        pkginfo = _package_probe_output(["bsdtar", "-xOf", real, ".PKGINFO"])
        if pkginfo:
            value = _pkginfo_field_value(pkginfo, "pkgname")
            if value:
                name = value
            version = _pkginfo_field_value(pkginfo, "pkgver")
            architecture = _pkginfo_field_value(pkginfo, "arch")
            maintainer = _pkginfo_field_value(pkginfo, "packager")
            description = _pkginfo_field_value(pkginfo, "pkgdesc")
    elif kind == "flatpakref":
        try:
            with open(real, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line.startswith("Name="):
                        name = line[len("Name="):].strip()
                    elif line.startswith("Title=") and line[len("Title="):].strip():
                        name = line[len("Title="):].strip()
                    elif line.startswith("Comment="):
                        description = line[len("Comment="):].strip()
        except OSError:
            pass
    elif kind == "appimage" and len(basename) > 9:
        name = basename[:-len(".appimage")].rstrip(".")

    return {
        "kind": kind,
        "format_label": PACKAGE_KIND_LABELS.get(kind, kind),
        "name": name or basename,
        "version": version,
        "architecture": architecture,
        "maintainer": maintainer,
        "description": description,
        "size": size,
    }


# ---------------------------------------------------------------------------
# Job manager: serialized install/remove runs with GUI askpass
# ---------------------------------------------------------------------------

class Job:
    __slots__ = (
        "id", "kind", "app_id", "name", "state", "exit_code", "reason",
        "log", "created", "started", "finished",
    )

    def __init__(self, kind, app_id):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.app_id = app_id
        self.name = ""
        self.state = "queued"
        self.exit_code = None
        self.reason = ""
        self.log = deque(maxlen=JOB_LOG_LINES)
        self.created = time.time()
        self.started = 0.0
        self.finished = 0.0

    def log_lines(self, tail=None):
        lines = list(self.log)
        if tail is not None:
            lines = lines[-max(1, int(tail)):]
        return lines

    def public(self, tail=None):
        return {
            "job_id": self.id,
            "kind": self.kind,
            "app_id": self.app_id,
            "name": self.name,
            "state": self.state,
            "exit_code": self.exit_code,
            "reason": self.reason,
            "created": self.created,
            "started": self.started or None,
            "finished": self.finished or None,
            "log_tail": self.log_lines(tail),
        }


class JobManager:
    """Runs one install/remove job at a time in a background worker thread."""

    def __init__(self):
        self._jobs = OrderedDict()
        self._queue = queue.Queue()
        self._lock = threading.Lock()
        self._process = None
        self._shutdown = False
        self._worker = threading.Thread(target=self._work, daemon=True, name="linuxtoys-mcp-jobs")
        self._worker.start()

    def submit(self, kind, app_id):
        entry = _resolve_entry(app_id)
        if entry is None:
            raise ValueError(f"No installable entry found for '{app_id}'. Use search_apps to list valid IDs.")
        job = Job(kind, app_id)
        job.name = str(entry.get("name") or app_id)
        self._register(job)
        self._queue.put((job, entry))
        return job

    def submit_file(self, spec):
        """Queue a package-file install (Package View parity).

        ``spec`` carries path, kind, display metadata and the exact-file
        signature captured before queueing. Run order stays serialized with
        every other job.
        """
        spec = dict(spec or {})
        path = str(spec.get("path") or "")
        if not os.path.isfile(path):
            raise ValueError(f"No package file found at '{path}'.")
        job = Job("install_file", path)
        job.name = str(spec.get("name") or os.path.basename(path))
        self._register(job)
        self._queue.put((job, spec))
        return job

    def _register(self, job):
        with self._lock:
            self._jobs[job.id] = job
            while len(self._jobs) > 100:
                self._jobs.popitem(last=False)

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(str(job_id or "").strip())

    def snapshot(self, limit=20):
        with self._lock:
            jobs = list(self._jobs.values())[-max(1, int(limit)):]
        return [job.public() for job in reversed(jobs)]

    def shutdown(self):
        self._shutdown = True
        self._queue.put(None)

    def _work(self):
        while not self._shutdown:
            item = self._queue.get()
            if item is None:
                break
            job, entry = item
            self._run(job, entry)
            self._queue.task_done()

    # -- execution ---------------------------------------------------------

    def _run(self, job, entry):
        job.state = "running"
        job.started = time.time()
        try:
            try:
                antenna.add_script_to_history(str(job.name))
            except Exception:
                pass  # Bug-report context is best effort.
            if job.kind == "install_file":
                code, reason = self._install_file(job, entry)
            elif job.kind == "install":
                code, reason = self._install(job, entry)
            else:
                code, reason = self._remove(job, entry)
            job.exit_code = code
            job.reason = reason
            job.state = "success" if code == 0 else "error"
        except Exception as exc:  # Never crash the worker.
            job.exit_code = 1
            job.reason = f"{exc}"
            job.state = "error"
        finally:
            job.finished = time.time()
            if job.log:
                appstream_logs.append_appstream_log(
                    f"mcp-{job.kind}-{job.name or job.app_id}",
                    "\n".join(job.log),
                )

    def _log(self, job, text):
        if not text:
            return
        for line in str(text).splitlines():
            job.log.append(line)

    def _new_transmap(self):
        directory = _tmp_dir()
        fd, path = tempfile.mkstemp(prefix="mcp-transmap-", dir=directory, text=True)
        os.close(fd)
        os.chmod(path, 0o600)
        return path

    def _install(self, job, entry):
        entry = dict(entry)
        cleanup_paths = []
        try:
            source = str(entry.get("appstream_source", "") or "").strip()
            path_value = str(entry.get("path", "") or "")

            # Provider-specific pipelines first: these entries are also "repo
            # entries", but the generic materialization cannot serve them.
            if source == "homebrew":
                from . import homebrew_catalog
                try:
                    entry = homebrew_catalog.materialize_install(entry)
                except Exception as exc:
                    return 1, f"Could not prepare Homebrew install of '{job.name}': {exc}"
                cleanup_paths.append(entry.get("path"))
            elif source == "appimage":
                return self._install_appimage(job, entry)
            elif source == "aur" or path_value.startswith("aur://"):
                return self._install_aur(job, entry)
            elif entry.get("is_appstream_entry"):
                # Flathub/Snap/native AppStream entries run through the full
                # TUI pipeline: install body plus reviewed dependency and
                # Flatpak-permission phases, in the same order as the GUI
                # queue runner.
                raw_path, prepared = self._prepare_appstream_script(job, entry)
                if raw_path is None:
                    return 1, prepared
                if prepared:
                    cleanup_paths.append(prepared)
                entry = dict(entry)
                entry["path"] = raw_path
            elif entry.get("is_repo_entry"):
                try:
                    entry = materialize_repo_script(entry)
                except (ValueError, NotImplementedError, OSError) as exc:
                    return 1, f"Could not prepare repository entry '{job.name}': {exc}"

            if str(entry.get("path", "")).startswith(("appstream://", "repo://", "aur://")):
                return 1, f"Could not prepare an installer for '{job.name}' (unresolvable entry)."

            path, prepared = self._prepare_run_script(job, entry)
            if path is None:
                return 1, prepared
            if prepared:
                cleanup_paths.append(prepared)

            # Plain physical scripts keep their compatibility checks (same as
            # the CLI and the GUI); repo/AppStream entries were already
            # compatibility-filtered by their parsers.
            if not entry.get("is_appstream_entry") and not entry.get("is_repo_entry"):
                compat_keys = parser.get_system_compat_keys()
                if not script_is_compatible(entry.get("path", ""), compat_keys):
                    return 1, f"'{job.name}' is not compatible with this system."

            return self._execute_script(job, entry)
        finally:
            for path in cleanup_paths:
                try:
                    if path and path != "true" and os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass

    def _prepare_appstream_script(self, job, entry):
        """Return (run_path, cleanup_path) for one AppStream entry, or (None, reason)."""
        try:
            from .tui.appstream_executor import build_install_script
        except ImportError as exc:
            return None, f"AppStream installer unavailable: {exc}"
        try:
            raw_path = build_install_script(entry)
        except (OSError, ValueError) as exc:
            return None, f"Could not build the installer for '{job.name}': {exc}"
        try:
            path = easy_cli.create_temp_file(raw_path)
        finally:
            try:
                os.remove(raw_path)
            except OSError:
                pass
        return path, path

    def _prepare_run_script(self, job, entry):
        """Return (run_path, cleanup_path) for plain/repo scripts, or (None, reason).

        AppStream entries were already prepared by the caller; plain curated
        scripts go through the same xdg-open filter as the CLI.
        """
        if entry.get("is_appstream_entry"):
            return entry.get("path"), None
        path = easy_cli.create_temp_file(entry["path"])
        return path, path

    def _install_aur(self, job, entry):
        """Run the AUR pipeline: source security scan, then pkg_install."""
        package = str(entry.get("package-name") or "").strip()
        if not package:
            return 1, f"AUR entry '{job.name}' has no package name."
        from .tui.appstream_executor import (
            AUR_SECURITY_OK,
            build_aur_install_script,
            check_aur_package_security,
        )
        status, details = check_aur_package_security(package)
        if status != AUR_SECURITY_OK:
            return int(status), (
                f"AUR package '{package}' failed the source security check:\n{details}"
            )
        script_path = build_aur_install_script(package)
        try:
            payload = dict(entry)
            payload["path"] = script_path
            return self._execute_script(job, payload, transmap_mark="manifest-export skip")
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass

    def _install_appimage(self, job, entry):
        """Resolve, download and install an AppImage catalog entry."""
        try:
            code = 1
            with appimage_catalog.download_for_install(entry) as (path, release):
                self._log(job, f"Resolved AppImage release {release.get('version') or '(untagged)'}")
                self._log(job, f"Downloaded {release.get('download_url') or path}")
                directory = _tmp_dir()
                fd, script_path = tempfile.mkstemp(prefix="mcp-appimage-", suffix=".sh", dir=directory, text=True)
                os.close(fd)
                try:
                    with open(script_path, "w", encoding="utf-8") as handle:
                        handle.write("#!/usr/bin/env bash\n")
                        handle.write(f"pkg_appimage {shlex_quote(path)}\n")
                    os.chmod(script_path, 0o700)
                    payload = dict(entry)
                    payload.update({
                        "is_local_package": True,
                        "path": script_path,
                        "appimage_release": release,
                        "local_package_path": path,
                        "local_package_kind": "appimage",
                        "local_package_signature": appimage_catalog.file_signature(path),
                    })
                    code, _ = self._execute_script(
                        job, payload, transmap_mark="manifest-export skip"
                    )
                finally:
                    try:
                        os.remove(script_path)
                    except OSError:
                        pass
            if code != 0:
                return code, f"pkg_appimage exited with status {code}. See the job log for details."
            return 0, ""
        except (OSError, ValueError, RuntimeError) as exc:
            return 1, f"AppImage installation failed: {exc}"

    def _install_file(self, job, spec):
        """Install one local package file through the Package View machinery.

        Mirrors the GUI's local-package job: re-verify the exact file that was
        inspected at queue time (dev/ino/size/mtime signature), then run a
        generated ``pkg_fromfile``/``pkg_appimage`` one-liner through
        `_execute_script`, so askpass, native-manager waits, the registry and
        automatic reversion behave exactly like a user install.
        """
        spec = dict(spec or {})
        path = str(spec.get("path") or "")
        kind = str(spec.get("kind") or "")
        function = "pkg_appimage" if kind == "appimage" else "pkg_fromfile"

        try:
            current = package_file_signature(path)
        except OSError as exc:
            return 1, f"The package file disappeared before installation: {exc}"
        expected = tuple(spec.get("signature") or ())
        if expected and current != expected:
            return 1, f"The package file changed before installation: {path}"

        directory = _tmp_dir()
        fd, script_path = tempfile.mkstemp(prefix="mcp-package-", suffix=".sh", dir=directory, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("#!/usr/bin/env bash\n")
                handle.write(f"{function} {shlex_quote(path)}\n")
            os.chmod(script_path, 0o700)
            payload = {
                "name": str(spec.get("name") or os.path.basename(path)),
                "description": str(spec.get("description") or ""),
                "icon": "package-x-generic",
                "registry_name": str(spec.get("registry_name") or spec.get("name") or os.path.basename(path)),
                "path": script_path,
                "is_local_package": True,
            }
            code, reason = self._execute_script(job, payload, transmap_mark="manifest-export skip")
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass
        if code == 0:
            return 0, ""
        return code, reason or (
            f"{function} exited with status {code}. See the job log for details."
        )

    def _remove(self, job, entry):
        blockers = installed_packages.dependency_blockers(entry)
        if blockers:
            return 1, "Cannot remove '{}' yet — installed software still depends on it: {}".format(
                job.name, "; ".join(blockers)
            )
        from .revert_helper import build_uninstall_script_entry
        uninstall_entry = build_uninstall_script_entry(entry, None)
        if not uninstall_entry:
            return 1, f"No removable registry entry found for '{job.name}'. Install it through LinuxToys first."
        script_dir = _script_dir()
        try:
            # Uninstalls reach native managers through pkg_remove/pkg_install;
            # wait for any running package operation first, like the CLI does.
            if easy_cli.package_guard.native_transaction_conflict(
                uninstall_entry["path"], script_dir
            ) is not None:
                self._log(job, "Waiting for a running package manager to go idle...")
                if not easy_cli._wait_for_package_manager_cli():
                    return 1, easy_cli.package_guard.timeout_texts()[1]
            code, output = self._run_command(job, script_command(uninstall_entry["path"], script_dir), {})
        finally:
            cleanup_path = uninstall_entry.get("cleanup_path")
            if cleanup_path:
                try:
                    os.remove(cleanup_path)
                except OSError:
                    pass
        if code != 0:
            return code, f"Removal of '{job.name}' failed with exit code {code}. See the job log for details."
        return 0, ""

    def _execute_script(self, job, script_info, transmap_mark=None):
        """Run one prepared script with transmap + registry handling."""
        script_dir = _script_dir()
        if "CACHE_DIR" not in os.environ:
            os.environ["CACHE_DIR"] = os.path.join(script_dir, "scripts")

        registry_name = script_info.get("registry_name", script_info.get("name", "unknown"))
        transmap_path = self._new_transmap()
        if transmap_mark:
            try:
                with open(transmap_path, "a", encoding="utf-8") as handle:
                    handle.write(transmap_mark + "\n")
            except OSError:
                pass
        try:
            env = script_environment(script_info, os.environ.copy())
            env["TRANSMAP_PATH"] = transmap_path
            env.pop("LINUXTOYS_RUNNER_STATE", None)
            env.pop("LINUXTOYS_APPSTREAM_PACKAGE", None)

            # Semantic resolution for single-package native AppStream entries,
            # mirroring the GUI runner.
            if script_info.get("appstream_source") == "native":
                from .appstream_resolver import resolve_native_appstream_package
                value = script_info.get("package-name")
                packages = (
                    [value.strip()]
                    if isinstance(value, str) and value.strip()
                    else [str(v).strip() for v in (value if isinstance(value, (list, tuple)) else ()) if str(v).strip()]
                )
                if len(packages) == 1:
                    resolved = resolve_native_appstream_package(
                        packages[0],
                        component_id=script_info.get("appstream_id"),
                        desktop_id=script_info.get("appstream_launchable"),
                        name=script_info.get("name"),
                    )
                    env["LINUXTOYS_APPSTREAM_PACKAGE"] = resolved

            # A running native package manager wins: wait like every other
            # LinuxToys runner before touching it.
            if easy_cli.package_guard.native_transaction_conflict(
                script_info.get("path", ""), script_dir
            ) is not None:
                self._log(job, "Waiting for a running package manager to go idle...")
                if not easy_cli._wait_for_package_manager_cli():
                    return 1, easy_cli.package_guard.timeout_texts()[1]

            code, output = self._run_command(
                job, script_command(script_info["path"], script_dir), env
            )

            registry_disabled = str(script_info.get("registry", "") or "").strip().lower() == "no"
            if code == 0:
                if not registry_disabled:
                    ExecutionRegistry._save_to_registry(registry_name, transmap_path)
                self._finish_transmap(transmap_path)
                return 0, ""
            if code == 100:
                # User cancelled the askpass dialog or a script prompt.
                self._finish_transmap(transmap_path)
                return 100, "Cancelled on the user's screen (password dialog or prompt)."
            if easy_cli._is_error_exit_code(code):
                revert_info = {
                    "name": script_info.get("name", "unknown"),
                    "registry_name": registry_name,
                    "icon": "application-x-executable",
                    "repo": "",
                }
                self._log(job, "Script failed. Attempting automatic reversion...")
                if easy_cli._try_execute_auto_revert(revert_info, transmap_path):
                    self._log(job, "Automatic reversion completed successfully.")
                    self._finish_transmap(transmap_path)
                    return code, "Script failed, but its changes were automatically reverted."
                # Keep the transaction revertable through the Action Registry.
                ExecutionRegistry._save_to_registry(registry_name, transmap_path)
                return code, self._failure_reason(output) or (
                    f"Script failed with exit code {code}."
                )
            self._finish_transmap(transmap_path)
            return code, ""
        finally:
            try:
                if os.path.exists(transmap_path):
                    os.remove(transmap_path)
            except OSError:
                pass

    def _run_command(self, job, command, env):
        """Run one script subprocess, capturing output into the job log."""
        try:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                errors="replace",
                env=env or None,
                check=False,
            )
        except KeyboardInterrupt:
            return 130, ""
        except Exception as exc:
            self._log(job, f"Failed to launch the script: {exc}")
            return 1, f"Failed to launch the script: {exc}"
        self._log(job, result.stdout)
        return result.returncode, result.stdout

    @staticmethod
    def _failure_reason(output):
        """Prefer the library's die/fatal message (last non-empty line)."""
        lines = [line.strip() for line in (output or "").splitlines() if line.strip()]
        tail = lines[-1] if lines else ""
        if not tail or len(tail) > 300 or re.fullmatch(r"[\W_]+", tail):
            return ""
        return tail

    @staticmethod
    def _finish_transmap(transmap_path):
        easy_cli._cleanup_tmp_noram_dirs(transmap_path)
        try:
            if os.path.exists(transmap_path):
                os.remove(transmap_path)
        except OSError:
            pass


class _LazyJobs:
    """Create the job worker only when this process actually serves jobs.

    Merely importing mcp_server (GUI menu, CLI status checks) must not spawn
    worker threads.
    """

    def __init__(self):
        self._manager = None
        self._lock = threading.Lock()

    def _get(self):
        with self._lock:
            if self._manager is None:
                self._manager = JobManager()
            return self._manager

    def submit(self, kind, app_id):
        return self._get().submit(kind, app_id)

    def submit_file(self, spec):
        return self._get().submit_file(spec)

    def get(self, job_id):
        return self._get().get(job_id)

    def snapshot(self, limit=20):
        return self._get().snapshot(limit)

    def shutdown(self):
        if self._manager is not None:
            self._manager.shutdown()


JOBS = _LazyJobs()


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

def _bool_schema(description):
    return {"type": "boolean", "description": description}


def tool_schemas():
    return [
        {
            "name": "server_info",
            "description": (
                "LinuxToys server status: version, connection info, active jobs, "
                "and whether the systemd service is enabled/active."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "list_categories",
            "description": "List LinuxToys catalog categories (system tools, tweaking, etc.).",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "search_apps",
            "description": (
                "Search every LinuxToys catalog (curated scripts, repositories, "
                "AppStream/Flathub/Snap, AppImages) by name or description. Returns "
                "stable IDs to pass to get_app_details/install_app."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term (min 2 characters)"},
                    "limit": {"type": "integer", "description": "Max results (default 20)"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_app_details",
            "description": (
                "Full app page for one stable ID: description, screenshots URLs, "
                "homepage/donation/purchase links, version, install state."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {"app_id": {"type": "string", "description": "Stable catalog ID"}},
                "required": ["app_id"],
            },
        },
        {
            "name": "get_screenshot",
            "description": (
                "Fetch one app screenshot image (view it to describe the app to the user)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string"},
                    "index": {"type": "integer", "description": "Screenshot index, default 0"},
                },
                "required": ["app_id"],
            },
        },
        {
            "name": "install_app",
            "description": (
                "Install an app or feature by stable ID. Runs exactly like a user "
                "install: when root is required the password dialog appears on the "
                "user's screen. Returns a job id — poll get_job until success/error."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {"app_id": {"type": "string", "description": "Stable catalog ID"}},
                "required": ["app_id"],
            },
        },
        {
            "name": "fetch_package_url",
            "description": (
                "Download a package file (.deb, .rpm, .pkg.tar.*, .pacman, .eopkg, "
                ".flatpak, .flatpakref, .snap, .appimage) from an http(s) URL into "
                "LinuxToys' private staging directory and return its local path. "
                "Inspect the path with get_package_file_details before installing."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "http(s) URL of the package file"},
                },
                "required": ["url"],
            },
        },
        {
            "name": "get_package_file_details",
            "description": (
                "Inspect a local package file exactly like the GUI's package view: "
                "name, version, architecture, maintainer, description, size and "
                "format, plus whether that package type is supported on this "
                "system (same compatibility guards as the GUI)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the package file (absolute or ~-prefixed)"},
                },
                "required": ["path"],
            },
        },
        {
            "name": "install_package_file",
            "description": (
                "Queue the install of a local package file (.deb, .rpm, "
                ".pkg.tar.*, .pacman, .eopkg, .flatpak, .flatpakref, .snap, "
                ".appimage) through the same guarded machinery the GUI's package "
                "view uses. When root is needed the password dialog appears on "
                "the user's screen. Returns a job id — poll get_job."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the package file (absolute or ~-prefixed)"},
                },
                "required": ["path"],
            },
        },
        {
            "name": "remove_app",
            "description": (
                "Remove an app/feature installed through LinuxToys, by stable ID. "
                "Returns a job id — poll get_job until success/error."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {"app_id": {"type": "string", "description": "Stable catalog ID"}},
                "required": ["app_id"],
            },
        },
        {
            "name": "get_job",
            "description": "Status, exit code and log tail of one install/remove job.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "tail_lines": {"type": "integer", "description": "Log tail length (default 40)"},
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "list_jobs",
            "description": "Recent install/remove jobs handled by this server.",
            "inputSchema": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
        },
        {
            "name": "get_settings",
            "description": (
                "Current LinuxToys settings: automatic updates, automatic bug "
                "reports, interface language, MCP service state."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "set_settings",
            "description": (
                "Change LinuxToys settings: automatic_updates (bool), "
                "automatic_bug_reports (bool), language (code such as 'en', 'pt'). "
                "Only provided fields change. The running GUI applies a language "
                "change on its next launch."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "automatic_updates": _bool_schema("Automatic system self-updates"),
                    "automatic_bug_reports": _bool_schema("Auto-submit bug reports on script failure"),
                    "language": {"type": "string", "description": "Language code (e.g. 'en', 'pt')"},
                },
            },
        },
        {
            "name": "translate_text",
            "description": (
                "Translate text with the same translation method the app page "
                "uses, for the user's convenience. Defaults to the user's language."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "target_language": {"type": "string", "description": "Language code, e.g. 'pt'"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "translate_app_description",
            "description": (
                "Translate one app's full description into a language, sharing the "
                "GUI's translation cache. Defaults to the user's language."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string"},
                    "target_language": {"type": "string"},
                },
                "required": ["app_id"],
            },
        },
        {
            "name": "get_registry_entries",
            "description": (
                "Action Registry entries: everything installed through LinuxToys "
                "with timestamps and recorded changes. Optional substring filter."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
        {
            "name": "export_registry_manifest",
            "description": (
                "Export installed apps as a portable LinuxToys manifest file "
                "(replayable on another machine via manifest mode)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "Output file path (default ~/linuxtoys-manifest.txt)"},
                },
            },
        },
        {
            "name": "open_support_link",
            "description": (
                "Open one of an app's own links (donate, purchase, homepage, "
                "subscription, purchase option) in the user's browser."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["homepage", "donate", "purchase", "purchase_option", "subscription"],
                    },
                    "index": {"type": "integer", "description": "Index for purchase_option/subscription"},
                },
                "required": ["app_id", "kind"],
            },
        },
    ]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_server_info():
    status = service_status()
    return {
        "server": SERVER_NAME,
        "version": __version__,
        "protocol_version": PROTOCOL_VERSION,
        "endpoint": _endpoint_url(),
        "service": status,
        "uptime_seconds": round(time.time() - _TRANSIENT_SERVER["started"], 1),
        "scripts_source": str(parser.SCRIPTS_DIR),
        "appstream_cache_ready": appstream_cache.CATALOG_PATH.is_file(),
        "active_jobs": sum(
            1 for job in JOBS.snapshot(100) if job.get("state") in ("queued", "running")
        ),
        "askpass": (
            "installs that need root show the password dialog on the user's screen"
        ),
    }


def _tool_categories():
    translations = _translations()
    categories = []
    for category in parser.get_categories(translations) or []:
        if category.get("is_script"):
            continue
        path = str(category.get("path") or "")
        leaf = os.path.basename(path.rstrip("/")) if path else ""
        categories.append({
            "name": str(category.get("name") or leaf),
            "path": leaf,
        })
    return {"categories": categories}


def _tool_get_app_details(app_id):
    entry = _resolve_entry(app_id)
    if entry is None:
        raise ValueError(f"Unknown app id '{app_id}'. Use search_apps to list valid IDs.")
    return _app_details(entry)


def _tool_get_screenshot(app_id, index=0):
    entry = _resolve_entry(app_id)
    if entry is None:
        raise ValueError(f"Unknown app id '{app_id}'.")
    urls = _screenshot_urls(entry)
    if not urls:
        raise ValueError(f"'{entry.get('name') or app_id}' has no screenshots.")
    try:
        index = int(index)
    except (TypeError, ValueError):
        index = 0
    if not 0 <= index < len(urls):
        raise ValueError(f"Screenshot index out of range: 0..{len(urls) - 1}")
    data, mime = _fetch_screenshot(urls[index])
    return {
        "content": [{
            "type": "image",
            "data": base64.b64encode(data).decode("ascii"),
            "mimeType": mime,
        }],
        "url": urls[index],
    }


def _tool_install(app_id):
    job = JOBS.submit("install", app_id)
    return {
        "job_id": job.id,
        "name": job.name,
        "state": job.state,
        "note": (
            "The install runs like a normal user install. If it needs root, the "
            "password dialog appears on the user's screen — wait for them to "
            "type it. Poll get_job for the outcome."
        ),
    }


def _tool_fetch_package_url(url):
    """Download one package file into the private staging directory."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("A package file URL is required.")
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        raise ValueError("Only http(s) URLs can be fetched.")

    name = parts.path.rsplit("/", 1)[-1] if parts.path else ""
    sanitized = "".join(
        char if (char.isalnum() or char in "._-") else "_" for char in name
    ).strip("._")[:120]
    if not sanitized or package_file_kind(sanitized) is None:
        raise ValueError(
            "The URL name does not look like a supported package file. "
            f"Supported package file types: {SUPPORTED_PACKAGE_KINDS_TEXT}"
        )
    target = os.path.join(package_staging_dir(), sanitized)

    request = Request(url, headers={"User-Agent": "LinuxToys MCP"})
    tmp_path = target + ".part"
    try:
        with urlopen(request, timeout=60) as response:
            with open(tmp_path, "wb") as handle:
                received = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > MAX_PACKAGE_DOWNLOAD_BYTES:
                        limit_mib = MAX_PACKAGE_DOWNLOAD_BYTES / (1024 * 1024)
                        limit_text = (
                            f"{limit_mib / 1024:g} GiB"
                            if limit_mib >= 1024
                            else f"{limit_mib:g} MiB"
                        )
                        raise ValueError(
                            "The package file is too large to download (limit: "
                            f"{limit_text})."
                        )
                    handle.write(chunk)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, target)
    except OSError as exc:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise ValueError(f"Could not download the package file: {exc}")
    except ValueError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

    try:
        details = _package_details_payload(target)
    except ValueError:
        details = {"name": sanitized, "kind": package_file_kind(target)}
    details["path"] = target
    details["url"] = url
    # "note" stays the compatibility guard's refusal message when present;
    # the download context goes into its own field.
    details["download_note"] = (
        "Downloaded into LinuxToys' staging directory (cleared with /tmp on "
        "reboot). Inspect it with get_package_file_details before installing."
    )
    return details


def _package_details_payload(path):
    """Metadata + host guards for one package file path, Package View parity."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("A package file path is required.")
    requested = path.strip()
    real = os.path.realpath(os.path.expanduser(requested))
    if not os.path.isfile(real):
        raise ValueError(f"No file found at '{requested}'.")
    kind = package_file_kind(real)
    if kind is None:
        raise ValueError(
            "Unsupported package file type. Supported package file types: "
            + SUPPORTED_PACKAGE_KINDS_TEXT
        )
    metadata = inspect_local_package(real) or {
        "kind": kind,
        "format_label": PACKAGE_KIND_LABELS.get(kind, kind),
        "name": os.path.splitext(os.path.basename(real))[0],
    }
    metadata["path"] = real
    metadata["kind"] = kind
    metadata["format_label"] = PACKAGE_KIND_LABELS.get(kind, kind)
    supported = package_kind_supported_on_host(kind)
    metadata["supported_on_host"] = supported
    if not supported:
        metadata["note"] = (
            "This system does not support this package type, so installing it "
            "is refused — the same guard the GUI applies before opening a "
            "package file."
        )
    return metadata


def _tool_get_package_file_details(path):
    """Inspect one local package file (name, version, host compatibility)."""
    return _package_details_payload(path)


def _tool_install_package_file(path):
    details = _package_details_payload(path)
    if not details.get("supported_on_host"):
        raise ValueError(
            details.get("note") or "This package type is not supported on this system."
        )
    real = details["path"]
    spec = {
        "path": real,
        "kind": details["kind"],
        "name": details["name"],
        "description": details.get("description") or "",
        "signature": package_file_signature(real),
    }
    job = JOBS.submit_file(spec)
    return {
        "job_id": job.id,
        "name": job.name,
        "path": real,
        "kind": details["kind"],
        "state": job.state,
        "note": (
            "The install runs exactly like a package-view install. If it needs "
            "root, the password dialog appears on the user's screen — wait for "
            "them to type it. Poll get_job for the outcome."
        ),
    }


def _tool_remove(app_id):
    job = JOBS.submit("remove", app_id)
    return {
        "job_id": job.id,
        "name": job.name,
        "state": job.state,
        "note": "Poll get_job for the outcome.",
    }


def _tool_get_job(job_id, tail_lines=40):
    job = JOBS.get(job_id)
    if job is None:
        raise ValueError(f"Unknown or expired job id '{job_id}'. Jobs reset when the service restarts.")
    return job.public(tail=tail_lines)


def _tool_list_jobs(limit=20):
    return {"jobs": JOBS.snapshot(limit)}


def _tool_get_settings():
    status = service_status()
    return {
        "automatic_updates": get_automatic_updates(),
        "automatic_bug_reports": get_automatic_error_reports(),
        "language": get_saved_language() or detect_system_language(),
        "available_languages": get_available_languages(),
        "mcp_service": status,
        "mcp_endpoint": _endpoint_url(),
    }


def _tool_set_settings(automatic_updates=None, automatic_bug_reports=None, language=None):
    applied = {}
    rejected = {}
    if automatic_updates is not None:
        save_automatic_updates(bool(automatic_updates))
        applied["automatic_updates"] = bool(automatic_updates)
    if automatic_bug_reports is not None:
        save_automatic_error_reports(bool(automatic_bug_reports))
        applied["automatic_bug_reports"] = bool(automatic_bug_reports)
    if language is not None:
        code = str(language).strip().casefold()
        available = get_available_languages()
        if code in available:
            save_language(code)
            applied["language"] = code
        else:
            rejected["language"] = available
    result = {"applied": applied, "note": "A running GUI applies the new language on its next launch."}
    if rejected:
        result["rejected"] = rejected
    return result


def _tool_translate_text(text, target_language=None):
    target = str(target_language or "").strip() or detect_system_language()
    target = translate_helper.normalized_language(target)
    if not target:
        target = "en"
    translated = translate_helper.translate_text(text, target)
    return {"translated_text": translated, "target_language": target}


def _tool_translate_app_description(app_id, target_language=None):
    entry = _resolve_entry(app_id)
    if entry is None:
        raise ValueError(f"Unknown app id '{app_id}'.")
    details = _app_details(entry)
    target = str(target_language or "").strip() or detect_system_language()
    target = translate_helper.normalized_language(target) or "en"

    blocks = details.get("description_blocks") or []
    if not blocks:
        source_text = details.get("long_description") or details.get("summary") or details.get("description") or ""
        if not source_text.strip():
            return {"translated_text": "", "target_language": target, "note": "The app has no description."}
        translated = translate_helper.translate_text(source_text, target)
        return {"translated_text": translated, "target_language": target}

    app_id_stable = details["id"]
    cached = translate_helper.load_cached_description_translation(app_id_stable, blocks, target)
    if cached is not None:
        return {
            "translated_text": _blocks_to_text(cached),
            "description_blocks": cached,
            "target_language": target,
            "cached": True,
        }
    translated_blocks = translate_helper.translate_blocks(blocks, target)
    translate_helper.save_cached_description_translation(app_id_stable, blocks, translated_blocks, target)
    return {
        "translated_text": _blocks_to_text(translated_blocks),
        "description_blocks": translated_blocks,
        "target_language": target,
        "cached": False,
    }


def _tool_get_registry_entries(query=None, limit=50):
    registry_data = registry_utils.parse_registry_file()
    query = str(query or "").strip().casefold()
    entries = []
    for name, transactions in registry_data.items():
        if query and not (
            query in name.casefold()
            or any(query in op.casefold() for _ts, ops in transactions for op in ops)
        ):
            continue
        entries.append({
            "name": name,
            "transactions": [
                {"timestamp": timestamp, "operations": list(operations)}
                for timestamp, operations in transactions
            ],
        })
        if len(entries) >= max(1, int(limit)):
            break
    return {"entries": entries}


def _tool_export_registry_manifest(destination=None):
    translations = _translations()
    manifest_path, entry_count = manifest_helper.export_registered_manifest(
        output_path=destination or None,
        translations=translations,
    )
    return {
        "path": manifest_path,
        "entries": entry_count,
        "note": "Replay on another machine with: linuxtoys --manifest <file>",
    }


def _tool_open_support_link(app_id, kind, index=0):
    entry = _resolve_entry(app_id)
    if entry is None:
        raise ValueError(f"Unknown app id '{app_id}'.")
    details = _app_details(entry)
    links = details.get("links") or {}
    kind = str(kind or "").strip()
    try:
        index = int(index)
    except (TypeError, ValueError):
        index = 0

    url = ""
    if kind == "homepage":
        url = links.get("homepage", "")
    elif kind == "donate":
        url = links.get("donate", "")
    elif kind == "purchase":
        url = links.get("purchase", "")
    elif kind == "purchase_option":
        options = links.get("purchase_options") or []
        if not options:
            raise ValueError(f"'{details['name']}' has no purchase options.")
        if not 0 <= index < len(options):
            raise ValueError(f"purchase_option index out of range: 0..{len(options) - 1}")
        url = options[index].get("url") or ""
    elif kind == "subscription":
        options = links.get("subscription_options") or []
        if not options:
            raise ValueError(f"'{details['name']}' has no subscription options.")
        if not 0 <= index < len(options):
            raise ValueError(f"subscription index out of range: 0..{len(options) - 1}")
        url = options[index].get("url") or ""
    else:
        raise ValueError("kind must be homepage, donate, purchase, purchase_option or subscription")

    if not url:
        raise ValueError(f"'{details['name']}' has no {kind} link.")
    if not re.match(r"^https?://", url):
        raise ValueError("Refusing to open a non-http(s) link.")
    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise ValueError(f"Could not open the link: {exc}")
    return {"opened": url, "kind": kind, "app": details["name"]}


def dispatch_tool(name, arguments):
    """Run one tool; returns the result dict (may raise ValueError)."""
    arguments = arguments if isinstance(arguments, dict) else {}
    if name == "server_info":
        return _tool_server_info()
    if name == "list_categories":
        return _tool_categories()
    if name == "search_apps":
        return {"results": _search_catalog(arguments.get("query"), arguments.get("limit", 20))}
    if name == "get_app_details":
        return _tool_get_app_details(arguments.get("app_id"))
    if name == "get_screenshot":
        return _tool_get_screenshot(arguments.get("app_id"), arguments.get("index", 0))
    if name == "install_app":
        return _tool_install(arguments.get("app_id"))
    if name == "fetch_package_url":
        return _tool_fetch_package_url(arguments.get("url"))
    if name == "get_package_file_details":
        return _tool_get_package_file_details(arguments.get("path"))
    if name == "install_package_file":
        return _tool_install_package_file(arguments.get("path"))
    if name == "remove_app":
        return _tool_remove(arguments.get("app_id"))
    if name == "get_job":
        return _tool_get_job(arguments.get("job_id"), arguments.get("tail_lines", 40))
    if name == "list_jobs":
        return _tool_list_jobs(arguments.get("limit", 20))
    if name == "get_settings":
        return _tool_get_settings()
    if name == "set_settings":
        return _tool_set_settings(
            arguments.get("automatic_updates"),
            arguments.get("automatic_bug_reports"),
            arguments.get("language"),
        )
    if name == "translate_text":
        return _tool_translate_text(arguments.get("text"), arguments.get("target_language"))
    if name == "translate_app_description":
        return _tool_translate_app_description(
            arguments.get("app_id"), arguments.get("target_language")
        )
    if name == "get_registry_entries":
        return _tool_get_registry_entries(arguments.get("query"), arguments.get("limit", 50))
    if name == "export_registry_manifest":
        return _tool_export_registry_manifest(arguments.get("destination"))
    if name == "open_support_link":
        return _tool_open_support_link(
            arguments.get("app_id"), arguments.get("kind"), arguments.get("index", 0)
        )
    raise KeyError(name)


# ---------------------------------------------------------------------------
# JSON-RPC over Streamable HTTP
# ---------------------------------------------------------------------------

class SessionStore:
    def __init__(self):
        self._sessions = {}
        self._lock = threading.Lock()

    def create(self):
        session = uuid.uuid4().hex
        with self._lock:
            self._prune_locked()
            self._sessions[session] = time.time()
        return session

    def validate(self, session):
        with self._lock:
            return bool(session) and session in self._sessions

    def drop(self, session):
        with self._lock:
            return self._sessions.pop(session, None) is not None

    def _prune_locked(self):
        deadline = time.time() - SESSION_IDLE_TTL
        for session in [s for s, seen in self._sessions.items() if seen < deadline]:
            self._sessions.pop(session, None)


SESSIONS = SessionStore()


def _jsonrpc_result(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id, code, message, data=None):
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _initialize_result(requested_version):
    version = str(requested_version or PROTOCOL_VERSION)
    if version not in SUPPORTED_PROTOCOL_VERSIONS:
        version = PROTOCOL_VERSION
    return {
        "protocolVersion": version,
        "capabilities": {
            "tools": {"listChanged": False},
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "title": "LinuxToys",
            "version": __version__,
        },
        "instructions": (
            "LinuxToys is a cross-distro app manager. Typical flow: search_apps "
            "-> get_app_details -> install_app, then poll get_job. A local or "
            "downloaded package file (.deb, .rpm, .appimage, ...) can be "
            "installed the same guarded way: get_package_file_details -> "
            "install_package_file, with fetch_package_url for downloads. "
            "Installs that need root show the password dialog on the user's "
            "screen; never ask the user to hand you credentials. Descriptions "
            "and screenshots can be read and translated with translate_text / "
            "translate_app_description."
        ),
    }


def handle_jsonrpc(message):
    """Process one JSON-RPC message dict; returns a response dict or None."""
    if not isinstance(message, dict):
        return _jsonrpc_error(None, -32600, "Invalid Request: expected a JSON object")
    request_id = message.get("id")
    method = message.get("method")

    if message.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return _jsonrpc_error(request_id, -32600, "Invalid Request: missing jsonrpc/method")

    if method == "initialize":
        params = message.get("params") or {}
        return _jsonrpc_result(request_id, _initialize_result(params.get("protocolVersion")))

    if method == "ping":
        return _jsonrpc_result(request_id, {})

    if method.startswith("notifications/"):
        return None  # Notifications get no body; the HTTP layer answers 202.

    if method == "tools/list":
        return _jsonrpc_result(request_id, {"tools": tool_schemas()})

    if method == "tools/call":
        params = message.get("params") or {}
        name = str(params.get("name") or "")
        if not name:
            return _jsonrpc_error(request_id, -32602, "Invalid params: missing tool name")
        try:
            result = dispatch_tool(name, params.get("arguments"))
        except KeyError:
            return _jsonrpc_error(request_id, -32602, f"Unknown tool: {name}")
        except (ValueError, KeyError, TypeError) as exc:
            return _jsonrpc_result(request_id, {
                "content": [{"type": "text", "text": f"Error: {exc}"}],
                "isError": True,
            })
        except Exception as exc:
            return _jsonrpc_result(request_id, {
                "content": [{"type": "text", "text": f"Internal error: {exc}"}],
                "isError": True,
            })
        if isinstance(result, dict) and "content" in result:
            payload = result
        else:
            payload = {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
        payload.setdefault("isError", False)
        return _jsonrpc_result(request_id, payload)

    return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")


class MCPRequestHandler(BaseHTTPRequestHandler):
    server_version = f"LinuxToysMCP/{__version__}"
    protocol_version = "HTTP/1.1"

    # -- helpers ------------------------------------------------------------

    def _origin_allowed(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parts = urlsplit(origin)
        host = (parts.hostname or "").casefold()
        return host in ("127.0.0.1", "localhost", "::1") or host == _local_hostname()

    def _authorized(self):
        header = self.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            if token_matches(header[7:]):
                return True
        if token_matches(self.headers.get("X-LinuxToys-Token", "")):
            return True
        return False

    def _send_json(self, payload, status=200, extra_headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def _session_from_headers(self):
        return self.headers.get("Mcp-Session-Id", "").strip()

    # -- verbs --------------------------------------------------------------

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            self._send_json({
                "status": "ok",
                "server": SERVER_NAME,
                "version": __version__,
                "mcp_endpoint": _endpoint_url(),
            })
            return
        if path == "/mcp":
            # Server-initiated SSE streams are not offered.
            self._send_empty(405, {"Allow": "POST, DELETE"})
            return
        self._send_json(_jsonrpc_error(None, -32601, "Unknown path"), 404)

    def do_DELETE(self):
        if urlsplit(self.path).path != "/mcp":
            self._send_json(_jsonrpc_error(None, -32601, "Unknown path"), 404)
            return
        if not self._authorized():
            self._send_json(_jsonrpc_error(None, -32001, "Unauthorized"), 401)
            return
        session = self._session_from_headers()
        if session and SESSIONS.drop(session):
            self._send_empty(204)
        else:
            self._send_empty(204)

    def do_POST(self):
        if urlsplit(self.path).path != "/mcp":
            self._send_json(_jsonrpc_error(None, -32601, "Unknown path"), 404)
            return
        if not self._origin_allowed():
            self._send_json(_jsonrpc_error(None, -32001, "Origin not allowed"), 403)
            return
        if not self._authorized():
            self._send_json(
                _jsonrpc_error(
                    None, -32001,
                    "Unauthorized: pass the MCP token as 'Authorization: Bearer <token>' "
                    "or 'X-LinuxToys-Token: <token>'. The token is at "
                    "~/.config/linuxtoys/mcp-token.",
                ),
                401,
            )
            return

        content_type = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type != "application/json":
            self._send_json(
                _jsonrpc_error(None, -32700, "Content-Type must be application/json"),
                415,
            )
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(_jsonrpc_error(None, -32700, "Invalid request body size"), 400)
            return
        try:
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            self._send_json(_jsonrpc_error(None, -32700, f"Parse error: {exc}"), 400)
            return

        method_name = ""
        if isinstance(payload, dict):
            method_name = str(payload.get("method") or "")
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("method") == "initialize":
                    method_name = "initialize"
                    break

        session = self._session_from_headers()
        if method_name == "initialize":
            session = SESSIONS.create()
        elif method_name == "ping" and not session:
            pass  # Health probes may ping before a session exists.
        elif session and not SESSIONS.validate(session):
            self._send_json(
                _jsonrpc_error(None, -32001, "Unknown session — re-initialize"), 404,
                {"Mcp-Session-Id": session},
            )
            return
        elif not session:
            self._send_json(
                _jsonrpc_error(
                    None, -32001,
                    "Missing Mcp-Session-Id header — initialize first",
                ),
                400,
            )
            return

        if isinstance(payload, list):
            responses = [
                response
                for response in (handle_jsonrpc(item) for item in payload)
                if response is not None
            ]
        else:
            responses = handle_jsonrpc(payload)
            responses = [responses] if responses is not None else []

        if not responses:
            self._send_empty(202, {"Mcp-Session-Id": session} if session else None)
            return

        if len(responses) == 1:
            self._send_json(responses[0], 200, {"Mcp-Session-Id": session} if session else None)
        else:
            self._send_json(responses, 200, {"Mcp-Session-Id": session} if session else None)

    def log_message(self, fmt, *args):
        if os.environ.get("LT_DEBUG") == "1":
            sys.stderr.write("MCP: " + fmt % args + "\n")


def _local_hostname():
    return "localhost"


def _endpoint_url():
    return f"http://127.0.0.1:{get_mcp_server_port()}/mcp"


# ---------------------------------------------------------------------------
# systemd user service management
# ---------------------------------------------------------------------------

SESSION_ENV_KEYS = (
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "XAUTHORITY",
    "DBUS_SESSION_BUS_ADDRESS",
    "GDK_BACKEND",
    "XDG_CURRENT_DESKTOP",
)

EMBEDDED_UNIT_TEMPLATE = """[Unit]
Description=LinuxToys MCP Agent Server
Documentation=https://linux.toys
PartOf=graphical-session.target
After=graphical-session.target

[Service]
Type=simple
ExecStart=@EXEC_START@
Restart=on-failure
RestartSec=5s
@ENVIRONMENT_LINES@
[Install]
WantedBy=graphical-session.target
"""


def user_unit_dir():
    return os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
        "systemd", "user",
    )


def user_unit_path():
    return os.path.join(user_unit_dir(), UNIT_FILE_NAME)


def bundled_unit_path():
    for candidate in (
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "systemd", UNIT_FILE_NAME),
    ):
        if os.path.isfile(candidate):
            return candidate
    return ""


def _exec_start():
    """ExecStart resolved for this installation kind.

    Points at the running app's own tree: AppImage installs re-execute the
    AppImage itself (so the mount is fresh), everything else runs this
    installation's linuxtoys.py directly — a dev checkout gets its own entry,
    never the system package's.
    """
    appimage = os.environ.get("APPIMAGE")
    if appimage and os.path.isfile(appimage):
        return f"{appimage} --mcp"
    script_dir = os.environ.get("SCRIPT_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    entry = os.path.join(script_dir, "linuxtoys.py")
    python = sys.executable or "/usr/bin/python3"
    return f"{python} {entry} --mcp"


def build_unit_text(session_env=None):
    """Render the user unit, baking the graphical session env for askpass.

    Prefers the shipped template (p3/systemd/linuxtoys-mcp.service) and falls
    back to the embedded copy so the server keeps working even if the file is
    missing from an installation.
    """
    session_env = session_env if session_env is not None else os.environ
    environment_lines = []
    for key in SESSION_ENV_KEYS:
        value = str(session_env.get(key) or "").strip()
        if value and "\n" not in value:
            environment_lines.append(f'Environment="{key}={value}"')

    template = EMBEDDED_UNIT_TEMPLATE
    bundled = bundled_unit_path()
    if bundled:
        try:
            with open(bundled, "r", encoding="utf-8") as handle:
                template = handle.read()
        except OSError:
            template = EMBEDDED_UNIT_TEMPLATE

    text = template.replace(
        "@EXEC_START@", _exec_start()
    ).replace(
        "@ENVIRONMENT_LINES@",
        "\n".join(environment_lines) + "\n" if environment_lines else "",
    )
    return text


def _systemctl(*args):
    if not shutil.which("systemctl"):
        return None, "systemctl is not available on this system."
    try:
        result = subprocess.run(
            ["systemctl", "--user", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"systemctl failed: {exc}"
    if result.returncode != 0:
        return None, (result.stderr or result.stdout or "systemctl failed").strip()
    return (result.stdout or "").strip(), ""


def install_service_unit(session_env=None):
    """Install (or refresh) the user unit; no root required."""
    unit_dir = user_unit_dir()
    os.makedirs(unit_dir, exist_ok=True)
    text = build_unit_text(session_env)
    path = user_unit_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)
    output, error = _systemctl("daemon-reload")
    if error:
        return False, error
    return True, path


def enable_service(session_env=None):
    ensure_token()
    installed, message = install_service_unit(session_env)
    if not installed:
        return False, message
    _output, error = _systemctl("enable", "--now", UNIT_FILE_NAME)
    if error:
        return False, error
    return True, f"MCP server enabled at {_endpoint_url()}"


def disable_service():
    _output, error = _systemctl("disable", "--now", UNIT_FILE_NAME)
    # Missing/not-installed units are fine when disabling.
    if error and "not found" not in error and "Failed to disable" not in error:
        return False, error
    return True, "MCP server disabled."


def service_status():
    status = {"installed": os.path.exists(user_unit_path()), "enabled": False, "active": False, "available": True}
    if not shutil.which("systemctl"):
        status["available"] = False
        return status
    output, error = _systemctl("is-enabled", UNIT_FILE_NAME)
    status["enabled"] = bool(output) and output.strip() in ("enabled", "enabled-runtime", "static", "linked")
    output, _error = _systemctl("is-active", UNIT_FILE_NAME)
    status["active"] = bool(output) and output.strip() == "active"
    if error and "not found" in error:
        status["installed"] = False
    return status


def apply_service_state(enabled, session_env=None):
    """Apply the header toggle. Returns (ok, message)."""
    if enabled:
        return enable_service(session_env)
    return disable_service()


def install_agent_skill():
    """Best-effort OFFLINE install of the bundled LinuxToys MCP skill.

    Fallback for when the primary path (``bun x skills add``, run through the
    AppStream runner's hidden PTY) is unavailable — no bun/bunx on PATH or
    every fetch source failed. Reads the bundled copy of the skill
    (``app/mcp_skill/SKILL.md``), which every distribution method packages.

    Returns a list of paths the skill was written to (may be empty).
    """
    home = os.path.expanduser("~")
    skill_root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mcp_skill"
    )
    skill_file = os.path.join(skill_root, "SKILL.md")
    if not os.path.isfile(skill_file):
        return []

    targets = [
        (".agents", "skills"),               # cross-agent convention (skills.sh)
        (".claude", "skills"),
        (".config", "opencode", "skill"),
        (".codex", "skills"),
        (".cursor", "skills"),
        (".windsurf", "skills"),
        (".gemini", "skills"),
    ]
    installed = []
    for parts in targets:
        agent_dir = os.path.join(home, *parts[:-1])
        if not os.path.isdir(agent_dir):
            continue
        destination = os.path.join(home, *parts, "linuxtoys-mcp")
        try:
            os.makedirs(destination, exist_ok=True)
            with open(skill_file, "r", encoding="utf-8") as source:
                content = source.read()
            with open(os.path.join(destination, "SKILL.md"), "w", encoding="utf-8") as handle:
                handle.write(content)
            installed.append(destination)
        except OSError:
            continue
    return installed


# The canonical, fetchable copy of the agent skill lives at the standard
# repository location the `skills` CLI (skills.sh) reads from a git checkout:
# skills/linuxtoys-mcp/SKILL.md at the repository root. It must be kept in
# sync with the bundled fallback copy at app/mcp_skill/SKILL.md (same commit).
SKILL_REPO_URLS = (
    "https://github.com/psygreg/linuxtoys",
    "https://git.linux.toys/psygreg/linuxtoys",  # Gitea mirror fallback
)
SKILL_NAME = "linuxtoys-mcp"
SKILL_INSTALL_TIMEOUT = 180


def skill_install_script():
    """Build the noninteractive skill-installation script.

    Returned as text; the caller (AppStream runner) writes it to a temporary
    file and dispatches it through the hidden PTY. Prompt-free by design,
    because the hidden PTY has nobody to answer questions:

    - ``bun x`` never prompts for package installation (unlike npx), and
      ``CI=1`` additionally tells CLIs to assume a noninteractive environment.
    - The skills CLI skips all confirmations with ``-y``; an explicit
      ``--skill`` prevents the skill picker, and NO ``--agent`` keeps the
      CLI on its default target (every detected agent plus the universal
      ``~/.agents/skills`` directory) — passing ``--agent`` together with
      ``-yg`` is what triggers its interactive scope prompt (upstream
      issue #793).
    - ``timeout`` bounds a hypothetical prompt nobody answers: the first
      source gets one budget, the mirror gets another, and the offline
      bundled copy is the last resort.
    """
    script = """#!/usr/bin/env bash
# Install the LinuxToys MCP agent skill for detected agents (noninteractive).
set -u

_lt_skill_cmd=()
if command -v bun >/dev/null 2>&1; then
    _lt_skill_cmd=(bun x skills)
elif [ -x "$HOME/.bun/bin/bun" ]; then
    _lt_skill_cmd=("$HOME/.bun/bin/bun" x skills)
fi

_lt_try() {
    # --foreground: without it timeout puts the CLI in a background process
    # group, so bun's TTY I/O raises SIGTTIN/SIGTTOU and the process stops
    # forever (TERM cannot reach stopped children, defeating even this bound).
    timeout --foreground %d env CI=1 "${_lt_skill_cmd[@]}" add "$1" --skill %s -g -y
}

_lt_status=1
if [ "${#_lt_skill_cmd[@]}" -gt 0 ]; then
    for _lt_repo in %s; do
        if _lt_try "$_lt_repo"; then
            _lt_status=0
            break
        fi
        echo "Skill source failed: $_lt_repo"
    done
else
    echo "bun/bunx not found; using the bundled skill copy."
fi

if [ "$_lt_status" != "0" ]; then
    python3 "$SCRIPT_DIR/app/mcp_server.py" --install-skill
fi
""" % (
        SKILL_INSTALL_TIMEOUT,
        SKILL_NAME,
        " ".join(shlex_quote(url) for url in SKILL_REPO_URLS),
    )
    return script


# ---------------------------------------------------------------------------
# Server bootstrap
# ---------------------------------------------------------------------------

def _background_warmup():
    """Best-effort startup work: scripts sync and AppStream catalog refresh."""
    try:
        from .scripts_loader import initialize_scripts
        initialize_scripts()
    except Exception:
        pass
    try:
        parser.set_scripts_dir(parser.SCRIPTS_DIR)
    except Exception:
        pass
    try:
        if appstream_cache.cache_needs_refresh():
            appstream_cache.refresh_cache()
    except Exception:
        pass
    # Publish a current derived catalog generation built with the FULL context
    # (curated entries + category paths). When the persisted generation already
    # matches, the Rust builder early-returns; when it is stale (or was last
    # built by a caller with an incomplete context) this rebuilds it correctly.
    try:
        scripts_dir, curated_entries, category_paths = _appstream_context()
        appstream_parser._runtime_catalog(
            scripts_dir,
            curated_entries=curated_entries,
            category_paths=category_paths,
            force_rebuild=True,
        )
    except Exception:
        pass


def run_service():
    """Run the MCP server in the foreground (used by `linuxtoys --mcp`)."""
    port = get_mcp_server_port()
    ensure_token()

    threading.Thread(target=_background_warmup, daemon=True, name="linuxtoys-mcp-warmup").start()

    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), MCPRequestHandler)
    except OSError as exc:
        print(
            f"Error: could not start the LinuxToys MCP server on 127.0.0.1:{port}: {exc}\n"
            "Is another instance already running? Check: systemctl --user status linuxtoys-mcp.service",
            file=sys.stderr,
        )
        return 1

    server.daemon_threads = True
    _TRANSIENT_SERVER["server"] = server
    _TRANSIENT_SERVER["started"] = time.time()

    print(
        f"LinuxToys MCP server v{__version__} listening on http://127.0.0.1:{port}/mcp\n"
        f"Auth token: {token_path()}\n"
        "Press Ctrl+C to stop."
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        JOBS.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    if "--install-skill" in sys.argv:
        # Non-package fallback used by the skill-install job when the bun
        # fetch path is unavailable: copy the bundled skill directly.
        installed = install_agent_skill()
        if installed:
            print("LinuxToys MCP skill installed to:")
            for path in installed:
                print(f"  {path}")
            sys.exit(0)
        print("No supported agent skill directory was found on this system.", file=sys.stderr)
        sys.exit(1)
    sys.exit(run_service())
