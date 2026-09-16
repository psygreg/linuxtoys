import json
import locale
import os
import re
import shlex
import unicodedata
import hashlib
import threading
from urllib.parse import unquote, urlparse

from .compat import get_system_compat_keys, is_containerized, is_wsl
from .dev_mode import get_effective_compat_keys, get_dev_compat_override, is_dev_mode_enabled
from . import official_index, new_index
from .lang_utils import detect_system_language


# Repository metadata is consumed by several startup caches in parallel.  Keep
# immutable file-backed inputs and the fully resolved entry list memoized so
# those consumers do not repeatedly walk and decode the same repository tree.
_REPO_CACHE_LOCK = threading.RLock()
_JSON_ENTRIES_CACHE = {}
_DESCRIPTION_CATALOG_CACHE = {}
_GIT_DB_CACHE = {}
_REPO_ENTRIES_CACHE = {}
_MARKDOWN_TEXT_CACHE = {}
_MONETARY_LOCALE_CACHE = None


def _file_signature(path):
    """Return a cheap signature that changes whenever a regular file changes."""
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def clear_runtime_caches():
    """Drop parser memoization after an in-process repository/source refresh."""
    with _REPO_CACHE_LOCK:
        _JSON_ENTRIES_CACHE.clear()
        _DESCRIPTION_CATALOG_CACHE.clear()
        _GIT_DB_CACHE.clear()
        _REPO_ENTRIES_CACHE.clear()
        _MARKDOWN_TEXT_CACHE.clear()
        global _MONETARY_LOCALE_CACHE
        _MONETARY_LOCALE_CACHE = None

DESKTOP_KEYS = {
    "gnome": "desktop-gnome",
    "plasma": "desktop-plasma",
    "other": "desktop-other",
}

OS_KEYS = {
    "debian",
    "ubuntu",
    "cachy",
    "arch",
    "steamos",
    "fedora",
    "rhel",
    "suse",
    "ostree",
    "ublue",
    "zorin",
    "solus",
    "pika",
    "deepin",
    "manjaro",
}

VALID_TYPES = {"git", "tar", "bin", "make", "flathub", "native", "repository", "url", "external"}

URL_PACKAGE_KEYS = {
    "deb",
    "rpm",
    "pacman",
    "pkg.tar.zst",
    "flatpak",
    "appimage",
    "tar",
    "bin",
}

NATIVE_PACKAGE_KEY_PRIORITY = (
    "ublue",
    "steamos",
    "deepin",
    "zorin",
    "pika",
    "manjaro",
    "cachy",
    "ostree",
    "ubuntu",
    "debian",
    "fedora",
    "rhel",
    "suse",
    "solus",
    "arch",
)

# Use the same specificity ordering for per-OS install-type mappings.
TYPE_KEY_PRIORITY = NATIVE_PACKAGE_KEY_PRIORITY

SYSTEMD_UNIT_SUFFIXES = {
    ".service",
    ".socket",
    ".timer",
    ".path",
    ".mount",
    ".automount",
    ".target",
    ".slice",
    ".scope",
    ".device",
    ".swap",
}

_GIT_ARCH_ALIASES = {
    "x86_64": ("x86_64", "amd64", "x64"),
    "aarch64": ("aarch64", "arm64"),
    "i686": ("i386", "i486", "i586", "i686", "ia32", "x86"),
    "armv7l": ("armv7l", "armv7", "armhf"),
    "armv6l": ("armv6l", "armv6", "armel"),
    "riscv64": ("riscv64",),
    "ppc64le": ("ppc64le", "ppc64el"),
    "ppc64": ("ppc64",),
    "s390x": ("s390x",),
    "loongarch64": ("loongarch64",),
}

_GIT_NATIVE_COMPAT = {
    "pacman": {"arch", "cachy"},
    "rpm": {"fedora", "rhel", "ostree", "ublue"},
    "deb": {"debian", "ubuntu"},
    "eopkg": {"solus"},
}


def _normalize_git_repo_url(value):
    """Return the canonical supported git project URL used by git-db.json."""
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None

    if (
        parsed.scheme != "https"
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or parsed.port
    ):
        return None

    host = (parsed.hostname or "").lower()
    path = unquote(parsed.path).strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/") if path else []

    if any(not part or part in (".", "..") for part in parts):
        return None

    if host in ("github.com", "codeberg.org"):
        if len(parts) != 2:
            return None
    elif host == "gitlab.com":
        if len(parts) < 2:
            return None
    else:
        return None

    return f"https://{host}/{'/'.join(parts)}"


def _load_git_db(scripts_dir):
    """Load git-db.json once per file revision."""
    path = os.path.join(os.path.realpath(scripts_dir), "git-db.json")
    signature = _file_signature(path)
    cache_key = (path, signature)

    with _REPO_CACHE_LOCK:
        cached = _GIT_DB_CACHE.get(cache_key)
        if cached is not None:
            return cached

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        repositories = {}
    else:
        repositories = data.get("repositories", {}) if isinstance(data, dict) else {}
        if not isinstance(repositories, dict):
            repositories = {}

    with _REPO_CACHE_LOCK:
        # Keep only the current revision for this path.
        for key in tuple(_GIT_DB_CACHE):
            if key[0] == path and key != cache_key:
                _GIT_DB_CACHE.pop(key, None)
        _GIT_DB_CACHE[cache_key] = repositories

    return repositories


def _git_asset_matches_machine(asset, machine):
    """Mirror pkg_fromrelease architecture matching for one indexed release asset."""
    canonical = next(
        (arch for arch, aliases in _GIT_ARCH_ALIASES.items() if machine in aliases),
        None,
    )
    if canonical is None:
        return False

    architectures = asset.get("architectures", [])
    if not isinstance(architectures, list) or not architectures:
        return True

    detected = {value for value in architectures if value in _GIT_ARCH_ALIASES}
    if canonical in detected:
        return True

    # pkg_fromrelease permits 32-bit x86 as a fallback on x86_64 hosts.
    return canonical == "x86_64" and "i686" in detected


def _git_db_requirement_matches(entry, compat_keys, scripts_dir):
    """
    Infer compatibility for git installs without an explicit ``os`` header.

    The generated database records the latest release assets. Explicit ``os``
    metadata remains authoritative when present. Missing/failed database records
    fail closed so repository compatibility never silently falls back to a guess.
    """
    if entry.get("os") is not None:
        return True

    if _resolve_install_type(entry, compat_keys) != "git":
        return True

    repo = _normalize_git_repo_url(entry.get("repo"))
    if not repo:
        return False

    record = _load_git_db(scripts_dir).get(repo)
    if not isinstance(record, dict) or record.get("error"):
        return False

    assets = record.get("assets")
    if not isinstance(assets, list):
        return False

    try:
        machine = os.uname().machine.lower()
    except AttributeError:
        return False

    for asset in assets:
        if not isinstance(asset, dict) or not _git_asset_matches_machine(asset, machine):
            continue

        kind = asset.get("kind")
        if kind == "appimage":
            return True
        if kind == "flatpak" and "systemd" in compat_keys:
            return True
        if kind in _GIT_NATIVE_COMPAT and (_GIT_NATIVE_COMPAT[kind] & compat_keys):
            return True

    return False


def _repo_app_id(name):
    """Return a shell-safe stable ID derived from a repository entry display name."""
    ascii_name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    app_id = re.sub(r"[^A-Za-z0-9]+", "_", ascii_name).strip("_").upper()
    if not app_id:
        return None
    if app_id[0].isdigit():
        app_id = f"APP_{app_id}"
    return app_id


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    return []


def _normalize_hardware_key(kind, value):
    value = str(value).strip().lower()

    if value in ("", "all"):
        return None

    if value.startswith(f"{kind}-"):
        return value

    return f"{kind}-{value}"


def _normalize_os_spec(value):
    """Normalize an ``os`` declaration into included and excluded OS keys."""
    if value is None:
        return set(), set()

    values = _as_list(value)
    if not values:
        return None

    included = set()
    excluded = set()

    for item in values:
        if not isinstance(item, str):
            return None

        item = item.strip().lower()
        if not item:
            return None

        is_exclusion = item.startswith("!")
        key = item[1:] if is_exclusion else item

        if not key or key not in OS_KEYS:
            return None

        (excluded if is_exclusion else included).add(key)

    # Contradictory declarations are invalid rather than order-dependent.
    if included & excluded:
        return None

    return included, excluded


def _resolve_install_type(entry, compat_keys):
    """Resolve an entry's install type, including optional per-OS mappings."""
    value = entry.get("type", "git")

    if isinstance(value, str):
        value = value.strip().lower()
        return value if value in VALID_TYPES else None

    if not isinstance(value, dict) or not value:
        return None

    # Reject unknown mapping keys or invalid type values up front.
    if set(value) - (OS_KEYS | {"all"}):
        return None

    normalized = {}
    for key, install_type in value.items():
        if not isinstance(install_type, str):
            return None
        install_type = install_type.strip().lower()
        if install_type not in VALID_TYPES:
            return None
        normalized[key] = install_type

    # Plain developer mode deliberately exposes a superset of every OS key.
    # That set cannot be used to choose a meaningful OS-specific branch:
    # whichever key appears first in TYPE_KEY_PRIORITY would win arbitrarily.
    #
    # When no COMPAT= simulation is active, prefer the generic fallback.
    # Explicit simulations (e.g. DEV_MODE=1 COMPAT=arch) still resolve the
    # distro-specific branch exactly like a real system would.
    if is_dev_mode_enabled() and not get_dev_compat_override():
        return normalized.get("all") or next(iter(normalized.values()), None)

    for key in TYPE_KEY_PRIORITY:
        if key in compat_keys and key in normalized:
            return normalized[key]

    return normalized.get("all")


def _entry_installs_sandboxed_package(entry, compat_keys):
    """Return True when the entry would install Flatpak or AppImage content."""
    install_type = _resolve_install_type(entry, compat_keys)

    if install_type == "flathub":
        return True

    if install_type == "url":
        resolved = _resolve_url_package(entry, compat_keys)
        if resolved and resolved[0] in {"flatpak", "appimage"}:
            return True

    for dependency in entry.get("dependencies", []):
        if dependency.get("type") == "flathub":
            return True

    return False


def _container_requirement_matches(entry, compat_keys):
    """Check explicit and implicit repository-list container compatibility."""
    try:
        from .dev_mode import should_override_container_checks

        if should_override_container_checks():
            return True
    except ImportError:
        pass

    if not is_containerized():
        return True

    # Flatpak and AppImage installs are never supported inside containers,
    # regardless of an explicit "container: allow" setting.
    if _entry_installs_sandboxed_package(entry, compat_keys):
        return False

    return entry.get("container", "allow").strip().lower() == "allow"


def _validate_wsl(entry):
    """Validate the optional WSL compatibility field."""
    value = entry.get("wsl")

    if value is None:
        return True

    return isinstance(value, str) and value.strip().lower() in {"yes", "no"}


def _wsl_requirement_matches(entry):
    """Check an entry's optional WSL-only/non-WSL-only restriction."""
    value = entry.get("wsl")

    if value is None:
        return True

    requires_wsl = value.strip().lower() == "yes"
    return is_wsl() if requires_wsl else not is_wsl()


def _validate_desktop(entry):
    """Validate the optional desktop compatibility field."""
    value = entry.get("desktop")

    if value is None:
        return True

    values = _as_list(value)

    return bool(values) and all(
        isinstance(desktop, str)
        and desktop.strip().lower() in DESKTOP_KEYS
        for desktop in values
    )

def _desktop_requirement_matches(entry, compat_keys):
    """Return True when the current desktop matches an entry's desktop field."""
    value = entry.get("desktop")

    if value is None:
        return True

    requested = {
        DESKTOP_KEYS[desktop.strip().lower()]
        for desktop in _as_list(value)
    }

    return bool(requested & compat_keys)


def _make_command_uses_sudo(entry):
    """Return whether a make entry's effective install command requires sudo."""
    command = entry.get("make-command")
    if command is None:
        command = "sudo make install"
    if not isinstance(command, str) or not command.strip():
        return True
    return bool(re.search(r"(?:^|[\s;|&()])sudo(?:\s|$)", command))


def _steamos_user_make(entry, compat_keys):
    return (
        "steamos" in compat_keys
        and _resolve_install_type(entry, compat_keys) == "make"
        and not _make_command_uses_sudo(entry)
    )


def _steamos_entry_is_compatible(entry, compat_keys):
    """Restrict SteamOS entries to user-level installation flows."""
    if "steamos" not in compat_keys:
        return True

    install_type = _resolve_install_type(entry, compat_keys)
    user_make = _steamos_user_make(entry, compat_keys)

    if install_type in {"git", "flathub", "tar", "bin", "external"}:
        pass
    elif install_type == "make":
        # Make installs are supported only when the application itself installs
        # at user level. LinuxToys may temporarily unlock SteamOS later to install
        # build-only Arch dependencies and base-devel.
        if not user_make:
            return False
    elif install_type == "url":
        resolved = _resolve_url_package(entry, compat_keys)
        if not resolved or resolved[0] not in {"flatpak", "appimage", "tar", "bin"}:
            return False
    else:
        return False

    # Native dependencies remain disallowed for normal portable SteamOS entries.
    # A user-level make entry is the exception: they are treated as build-only
    # dependencies and resolved using the Arch package declaration.
    if not user_make:
        for dependency in entry.get("dependencies", []):
            if (
                isinstance(dependency, dict)
                and dependency.get("type") == "native"
            ):
                return False

    overrides = entry.get("overrides")
    if isinstance(overrides, dict):
        if overrides.get("pre") is not None:
            return False
        if overrides.get("post") is not None and install_type != "tar":
            if install_type != "url":
                return False
            resolved = _resolve_url_package(entry, compat_keys)
            if not resolved or resolved[0] != "tar":
                return False

    services = _normalize_services(entry)
    if services is None or services["system"] or services["user"]:
        return False

    return True


def _entry_is_compatible(entry, compat_keys, scripts_dir=None):

    from .dev_mode import get_dev_compat_override, is_dev_mode_enabled
    if is_dev_mode_enabled() and not get_dev_compat_override():
        # COMPAT-less developer mode still skips normal compatibility checks,
        # but CONTAINER simulation must remain effective.
        return _container_requirement_matches(entry, compat_keys)

    if not _container_requirement_matches(entry, compat_keys):
        return False

    if not _wsl_requirement_matches(entry):
        return False

    if not _steamos_entry_is_compatible(entry, compat_keys):
        return False

    if scripts_dir is not None and not _git_db_requirement_matches(entry, compat_keys, scripts_dir):
        return False

    # OS compatibility. Positive tags are an allow-list; !tags are exclusions
    # that always take precedence. An exclusion-only list means "all except".
    os_value = entry.get("os")

    if os_value is not None:
        os_spec = _normalize_os_spec(os_value)
        if os_spec is None:
            return False

        included, excluded = os_spec

        if excluded & compat_keys:
            return False

        if included and not (included & compat_keys):
            return False

    # Optional desktop-environment compatibility.
    if not _desktop_requirement_matches(entry, compat_keys):
        return False

    # Optional init-system compatibility.
    if not _systemd_requirement_matches(entry, compat_keys):
        return False

    if entry.get("services") is not None and "systemd" not in compat_keys:
        return False

    install_type = _resolve_install_type(entry, compat_keys)

    if not install_type:
        return False

    # Flatpak installations implicitly require systemd.
    if install_type == "flathub":
        if "systemd" not in compat_keys:
            return False

    elif install_type == "url":
        resolved = _resolve_url_package(entry, compat_keys)

        if not resolved:
            return False

        package_type, _, _ = resolved

        if package_type == "flatpak" and "systemd" not in compat_keys:
            return False

    # Hardware compatibility
    hardware = entry.get("hardware", {})
    if hardware:
        if not isinstance(hardware, dict):
            return False

        for kind in ("gpu", "cpu"):
            values = _as_list(hardware.get(kind))

            if not values:
                continue

            required = {
                key
                for value in values
                if (key := _normalize_hardware_key(kind, value))
            }

            if required and not (required & compat_keys):
                return False

    if not _dependencies_are_compatible(entry, compat_keys):
        return False

    return True


def _validate_license(entry):
    """Validate the optional short license identifier shown on app pages."""
    value = entry.get("license")

    if value is None:
        return True

    return isinstance(value, str) and bool(value.strip()) and len(value.strip()) <= 20


def _validate_container(entry):
    value = entry.get("container", "allow")

    if value is None:
        value = "allow"

    return (
        isinstance(value, str)
        and value.strip().lower() in {"allow", "deny"}
    )


def _required_fields_present(entry):
    required = all(
        isinstance(entry.get(field), str) and entry[field].strip()
        for field in ("name", "repo", "category")
    )

    if not required:
        return False

    description = entry.get("description")
    if isinstance(description, str) and description.strip():
        return True

    # A repository-local description catalog may replace the normal inline
    # description/description_tag pair.
    description_file = entry.get("descriptions", entry.get("description-file"))
    return isinstance(description_file, str) and bool(description_file.strip())


def _normalize_package_names(value):
    """Normalize a package-name string/list to a non-empty list of names."""
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else None

    if isinstance(value, list):
        packages = []

        for package in value:
            if not isinstance(package, str) or not package.strip():
                return None
            packages.append(package.strip())

        return packages or None

    return None


def _validate_package_spec(value):
    """Validate package-name, including optional per-OS mappings."""
    if _normalize_package_names(value):
        return True

    if not isinstance(value, dict) or not value:
        return False

    if set(value) - (OS_KEYS | {"all"}):
        return False

    return all(
        _normalize_package_names(packages)
        for packages in value.values()
    )


def _validate_native_package_spec(value):
    """Backward-compatible alias for native package-name validation."""
    return _validate_package_spec(value)

def _validate_release_asset_selector(value):
    """Validate an optional pkg_fromrelease asset name/glob or per-OS mapping."""
    if value is None:
        return True

    def valid_selector(selector):
        if not isinstance(selector, str):
            return False
        selector = selector.strip()
        return bool(
            selector
            and selector not in {".", ".."}
            and "/" not in selector
            and "\\" not in selector
        )

    if isinstance(value, str):
        return valid_selector(value)

    if not isinstance(value, dict) or not value:
        return False

    if set(value) - (OS_KEYS | {"all"}):
        return False

    return all(valid_selector(selector) for selector in value.values())


def _validate_type(entry, compat_keys):
    install_type = _resolve_install_type(entry, compat_keys)

    if not install_type:
        return False

    if install_type in {"flathub", "native"}:
        return _validate_package_spec(entry.get("package-name"))

    if install_type in {"git", "tar"}:
        return _validate_release_asset_selector(entry.get("package-name"))

    if install_type == "make":
        make_source = entry.get("make-source", "git")
        if not isinstance(make_source, str) or make_source.strip().lower() not in {"git", "tar"}:
            return False

        make_command = entry.get("make-command")
        if make_command is not None:
            if not isinstance(make_command, str) or not make_command.strip():
                return False
            # Reversion derives the uninstall flow by replacing the first
            # install target: install -> uninstall, install-user -> uninstall-user.
            if not re.search(r"(?<![A-Za-z0-9_])install(?=$|[-_]|[^A-Za-z0-9_])", make_command):
                return False

        if make_source.strip().lower() == "tar":
            return _validate_release_asset_selector(entry.get("package-name"))
        return entry.get("package-name") is None

    if install_type == "bin":
        asset_name = entry.get("package-name")
        if not isinstance(asset_name, str):
            return False
        asset_name = asset_name.strip()
        return bool(
            asset_name
            and asset_name not in {".", ".."}
            and "/" not in asset_name
            and "\\" not in asset_name
            and not any(char in asset_name for char in "*?[")
        )

    if install_type == "url":
        urls = entry.get("urls")
        if not isinstance(urls, dict) or not urls:
            return False
        return any(
            key in URL_PACKAGE_KEYS and _valid_url_spec(value, entry)
            for key, value in urls.items()
        )

    if install_type == "external":
        script = entry.get("script")
        if not isinstance(script, str) or not script.strip():
            return False

        script = script.strip()
        if _valid_package_url(script):
            return True

        if os.path.isabs(script):
            return False

        normalized = os.path.normpath(script)
        return normalized != ".." and not normalized.startswith("../")

    if install_type == "repository":
        return False

    return True

def _load_json_entries(path):
    """Load one repository JSON file once per file revision."""
    signature = _file_signature(path)
    cache_key = (path, signature)

    with _REPO_CACHE_LOCK:
        cached = _JSON_ENTRIES_CACHE.get(cache_key)
        if cached is not None:
            return [dict(entry) if isinstance(entry, dict) else entry for entry in cached]

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        result = []
    else:
        if isinstance(data, dict):
            entries = [data]
        elif isinstance(data, list):
            entries = data
        else:
            entries = []

        result = []
        for entry in entries:
            if not isinstance(entry, dict):
                result.append(entry)
                continue
            copied = dict(entry)
            copied["_list_source"] = path
            result.append(copied)

    with _REPO_CACHE_LOCK:
        for key in tuple(_JSON_ENTRIES_CACHE):
            if key[0] == path and key != cache_key:
                _JSON_ENTRIES_CACHE.pop(key, None)
        _JSON_ENTRIES_CACHE[cache_key] = result

    return [dict(entry) if isinstance(entry, dict) else entry for entry in result]

def _scan_repo_tree(scripts_dir):
    """Collect repository JSON/Markdown files and signatures in one tree walk."""
    scripts_dir = os.path.realpath(scripts_dir)
    json_paths = []
    markdown_paths = []

    main_path = os.path.join(scripts_dir, "repos.json")
    if os.path.isfile(main_path):
        json_paths.append(main_path)

    lists_dir = os.path.join(scripts_dir, "lists")
    if os.path.isdir(lists_dir):
        discovered_json = []
        discovered_markdown = []
        for root, dirs, files in os.walk(lists_dir):
            dirs.sort()
            for filename in sorted(files):
                path = os.path.join(root, filename)
                lowered = filename.lower()
                if lowered.endswith(".json"):
                    discovered_json.append(path)
                elif lowered.endswith(".md"):
                    discovered_markdown.append(path)

        json_paths.extend(discovered_json)
        markdown_paths.extend(discovered_markdown)

    signatures = tuple(
        (path, _file_signature(path))
        for path in (*json_paths, *markdown_paths)
    )
    return tuple(json_paths), tuple(markdown_paths), signatures


def _get_repo_list_paths(scripts_dir):
    """Return all repository-list JSON files in deterministic order."""
    json_paths, _, _ = _scan_repo_tree(scripts_dir)
    return list(json_paths)


DESCRIPTION_FILE_KEYS = ("descriptions", "description-file")


def _resolve_description_file_path(entry):
    """
    Resolve an optional repository-local description catalog.

    The file must live in the exact same directory as the repository-list JSON.
    This deliberately does not allow ../ or nested paths.
    """
    value = None
    for key in DESCRIPTION_FILE_KEYS:
        candidate = entry.get(key)
        if candidate is not None:
            value = candidate
            break

    if not isinstance(value, str) or not value.strip():
        return None

    value = value.strip()
    if os.path.isabs(value) or os.path.basename(value) != value:
        return None

    if not value.lower().endswith(".json"):
        return None

    source = entry.get("_list_source")
    if not source:
        return None

    source_dir = os.path.realpath(os.path.dirname(source))
    resolved = os.path.realpath(os.path.join(source_dir, value))

    if os.path.dirname(resolved) != source_dir or not os.path.isfile(resolved):
        return None

    return resolved


def _load_description_catalog(entry):
    """Load a sibling description catalog once per file revision."""
    path = _resolve_description_file_path(entry)
    if not path:
        return {}

    signature = _file_signature(path)
    cache_key = (path, signature)
    with _REPO_CACHE_LOCK:
        cached = _DESCRIPTION_CATALOG_CACHE.get(cache_key)
        if cached is not None:
            return cached

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        catalog = {}
    else:
        catalog = data if isinstance(data, dict) else {}

    with _REPO_CACHE_LOCK:
        for key in tuple(_DESCRIPTION_CATALOG_CACHE):
            if key[0] == path and key != cache_key:
                _DESCRIPTION_CATALOG_CACHE.pop(key, None)
        _DESCRIPTION_CATALOG_CACHE[cache_key] = catalog
    return catalog


def _catalog_translation(catalog, language, tag):
    """Resolve a catalog tag for language, falling back to English."""
    if not isinstance(tag, str) or not tag.strip():
        return ""

    tag = tag.strip()
    language = str(language or "en").strip().replace("_", "-")
    candidates = [language]

    base_language = language.split("-", 1)[0]
    if base_language not in candidates:
        candidates.append(base_language)

    if "en" not in candidates:
        candidates.append("en")

    for language_key in candidates:
        strings = catalog.get(language_key)
        if not isinstance(strings, dict):
            continue

        value = strings.get(tag)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _load_markdown_text(path):
    """Load a repository-local Markdown file once per file revision."""
    path = os.path.realpath(path)
    signature = _file_signature(path)
    cache_key = (path, signature)

    with _REPO_CACHE_LOCK:
        cached = _MARKDOWN_TEXT_CACHE.get(cache_key)
        if cached is not None:
            return cached

        try:
            with open(path, "r", encoding="utf-8") as file:
                content = file.read().strip()
        except OSError:
            content = ""

        for key in tuple(_MARKDOWN_TEXT_CACHE):
            if key[0] == path and key != cache_key:
                _MARKDOWN_TEXT_CACHE.pop(key, None)
        _MARKDOWN_TEXT_CACHE[cache_key] = content
        return content


def _resolve_long_description_content(entry, value):
    """
    Resolve the final long-description value.

    Plain strings remain plain text. A value ending in .md is treated as a
    repository-local Markdown file, resolved relative to the JSON file that
    declared the entry. Markdown files may live in that directory or one of
    its subdirectories, but may never escape it.

    Returns:
        tuple[str, str]: (description_text, format)
    """
    if not isinstance(value, str):
        return "", "plain"

    value = value.strip()
    if not value:
        return "", "plain"

    if not value.lower().endswith(".md"):
        return value, "plain"

    if os.path.isabs(value):
        return "", "markdown"

    source = entry.get("_list_source")
    if not source:
        return "", "markdown"

    source_dir = os.path.realpath(os.path.dirname(source))
    resolved = os.path.realpath(os.path.join(source_dir, value))

    try:
        if os.path.commonpath((source_dir, resolved)) != source_dir:
            return "", "markdown"
    except ValueError:
        return "", "markdown"

    if not os.path.isfile(resolved):
        return "", "markdown"

    return _load_markdown_text(resolved), "markdown"


def _resolve_entry_descriptions(entry, translations=None):
    """
    Resolve the short and long descriptions.

    The existing long-description / long-description_tag interface is used for
    both plain text and Markdown. After localization has selected the final
    long-description value, values ending in .md are loaded as repository-local
    Markdown files. This also lets each language map the same long-description
    tag to a different Markdown file.
    """
    description = entry.get("description", "")
    if not isinstance(description, str):
        description = ""
    description = description.strip()

    description_tag = entry.get("description_tag", "")
    if not isinstance(description_tag, str):
        description_tag = ""
    description_tag = description_tag.strip()

    if description_tag and translations and description_tag in translations:
        translated = translations[description_tag]
        if isinstance(translated, str) and translated.strip():
            description = translated.strip()

    long_description = entry.get(
        "long-description", entry.get("long_description", "")
    )
    if not isinstance(long_description, str):
        long_description = ""
    long_description = long_description.strip()

    long_tag = entry.get(
        "long-description_tag", entry.get("long_description_tag", "")
    )
    if not isinstance(long_tag, str):
        long_tag = ""
    long_tag = long_tag.strip()

    if long_tag and translations and long_tag in translations:
        translated = translations[long_tag]
        if isinstance(translated, str) and translated.strip():
            long_description = translated.strip()

    catalog = _load_description_catalog(entry)
    if catalog:
        catalog_short_tag = catalog.get("description_tag", "")
        catalog_long_tag = catalog.get("description_long_tag", "")

        if isinstance(catalog_short_tag, str) and catalog_short_tag.strip():
            description_tag = catalog_short_tag.strip()

        if isinstance(catalog_long_tag, str) and catalog_long_tag.strip():
            long_tag = catalog_long_tag.strip()

        language = detect_system_language()

        catalog_short = _catalog_translation(catalog, language, description_tag)
        if catalog_short:
            description = catalog_short

        catalog_long = _catalog_translation(catalog, language, long_tag)
        if catalog_long:
            long_description = catalog_long

    long_description, long_description_format = _resolve_long_description_content(
        entry, long_description
    )

    return (
        description,
        description_tag,
        long_description,
        long_tag,
        long_description_format,
    )


SCREENSHOT_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".svg")


def _safe_list_relative_path(entry, scripts_dir, value):
    """Resolve a repository-list-relative path without escaping scripts/lists/."""
    if not isinstance(value, str) or not value.strip() or os.path.isabs(value):
        return None

    source = entry.get("_list_source")
    if not source:
        return None

    lists_dir = os.path.realpath(os.path.join(scripts_dir, "lists"))
    source_dir = os.path.realpath(os.path.dirname(source))
    resolved = os.path.realpath(os.path.join(source_dir, value.strip()))

    try:
        if os.path.commonpath((lists_dir, resolved)) != lists_dir:
            return None
    except ValueError:
        return None

    return resolved


def _resolve_list_screenshots(entry, scripts_dir):
    """Resolve screenshot files/directories relative to the repository list."""
    value = entry.get("screenshots")
    if value is None:
        return []

    values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    resolved = []

    for candidate in values:
        path = _safe_list_relative_path(entry, scripts_dir, candidate)
        if not path:
            continue

        if os.path.isdir(path):
            for filename in sorted(os.listdir(path), key=str.casefold):
                image_path = os.path.join(path, filename)
                if (
                    os.path.isfile(image_path)
                    and filename.lower().endswith(SCREENSHOT_EXTENSIONS)
                ):
                    resolved.append(image_path)
        elif os.path.isfile(path) and path.lower().endswith(SCREENSHOT_EXTENSIONS):
            resolved.append(path)

    # Preserve configured/directory order while removing duplicates.
    return list(dict.fromkeys(resolved))


def _system_monetary_locale():
    """Return the process' monetary locale once; it is invariant during a cache build."""
    global _MONETARY_LOCALE_CACHE

    with _REPO_CACHE_LOCK:
        if _MONETARY_LOCALE_CACHE is not None:
            return _MONETARY_LOCALE_CACHE

        previous = None
        try:
            previous = locale.setlocale(locale.LC_MONETARY)
            locale.setlocale(locale.LC_MONETARY, "")
            conventions = locale.localeconv()
        except (locale.Error, ValueError):
            conventions = {}
        finally:
            if previous is not None:
                try:
                    locale.setlocale(locale.LC_MONETARY, previous)
                except locale.Error:
                    pass

        currency_code = str(conventions.get("int_curr_symbol") or "").strip().upper()
        currency_symbol = str(conventions.get("currency_symbol") or "").strip()
        _MONETARY_LOCALE_CACHE = (currency_code, currency_symbol)
        return _MONETARY_LOCALE_CACHE


def _resolve_purchase_price(purchase, price_key="price", prices_key="prices"):
    """Resolve a purchase/subscription price using LC_MONETARY, falling back to base USD."""
    if not isinstance(purchase, dict):
        return None, ""

    base_price = purchase.get(price_key)
    if not (
        isinstance(base_price, (int, float))
        and not isinstance(base_price, bool)
        and base_price >= 0
    ):
        return None, ""

    price = float(base_price)
    symbol = "$"

    localized_prices = purchase.get(prices_key, {})
    if not isinstance(localized_prices, dict):
        localized_prices = {}

    normalized_prices = {
        str(code).strip().upper(): value
        for code, value in localized_prices.items()
        if isinstance(code, str) and code.strip()
    }

    currency_code, currency_symbol = _system_monetary_locale()
    localized_price = normalized_prices.get(currency_code)

    if (
        currency_code
        and currency_code != "USD"
        and isinstance(localized_price, (int, float))
        and not isinstance(localized_price, bool)
        and localized_price >= 0
    ):
        price = float(localized_price)
        symbol = currency_symbol or currency_code

    return price, symbol


def _valid_commerce_url(value, fallback=""):
    """Return an explicit valid HTTPS URL, otherwise a validated fallback."""
    if _valid_package_url(value):
        return value.strip()
    return fallback if _valid_package_url(fallback) else ""


def _resolve_purchase_options(purchase, purchase_url):
    """Normalize legacy or tiered one-time purchases for the app-page UI."""
    tiers = purchase.get("tiers")
    options = []

    if isinstance(tiers, list) and tiers:
        for tier in tiers:
            if not isinstance(tier, dict):
                continue
            name = str(tier.get("name") or "").strip()
            price, symbol = _resolve_purchase_price(tier)
            url = _valid_commerce_url(tier.get("url"), purchase_url)
            if name and price is not None and url:
                options.append({
                    "name": name,
                    "price": price,
                    "currency_symbol": symbol,
                    "url": url,
                })
        return options

    price, symbol = _resolve_purchase_price(purchase)
    if price is not None and purchase_url:
        options.append({
            "name": "",
            "price": price,
            "currency_symbol": symbol,
            "url": purchase_url,
        })
    return options


def _resolve_subscription_options(purchase, purchase_url):
    """Normalize legacy, time-framed, and tiered subscription choices."""
    options = []
    sub_tiers = purchase.get("sub_tiers")

    def add_periods(periods, tier_name="", tier_url=""):
        if not isinstance(periods, list):
            return
        for period in periods:
            if not isinstance(period, dict):
                continue
            months = period.get("months")
            if not (
                isinstance(months, int)
                and not isinstance(months, bool)
                and months > 0
            ):
                continue
            price, symbol = _resolve_purchase_price(period)
            url = _valid_commerce_url(period.get("url"), tier_url or purchase_url)
            if price is None or not url:
                continue
            options.append({
                "name": tier_name,
                "months": months,
                "price": price,
                "currency_symbol": symbol,
                "url": url,
            })

    if isinstance(sub_tiers, list) and sub_tiers:
        for tier in sub_tiers:
            if not isinstance(tier, dict):
                continue
            name = str(tier.get("name") or "").strip()
            if not name:
                continue
            tier_url = _valid_commerce_url(tier.get("url"), purchase_url)
            periods = tier.get("periods")
            if isinstance(periods, list) and periods:
                add_periods(periods, name, tier_url)
                continue

            price, symbol = _resolve_purchase_price(tier)
            if price is not None and tier_url:
                months = tier.get("months", 1)
                if not (isinstance(months, int) and not isinstance(months, bool) and months > 0):
                    months = 1
                options.append({
                    "name": name,
                    "months": months,
                    "price": price,
                    "currency_symbol": symbol,
                    "url": tier_url,
                })
        return options

    sub_periods = purchase.get("sub_periods")
    if isinstance(sub_periods, list) and sub_periods:
        add_periods(sub_periods)
        return options

    price, symbol = _resolve_purchase_price(purchase, "sub_price", "sub_prices")
    if price is not None and purchase_url:
        options.append({
            "name": "",
            "months": 1,
            "price": price,
            "currency_symbol": symbol,
            "url": purchase_url,
        })
    return options


def _resolve_developer_name(entry):
    """Resolve the developer/company name, falling back to the repository namespace."""
    developer = entry.get("developer")
    if isinstance(developer, str) and developer.strip():
        return developer.strip()

    repo = entry.get("repo", "")
    github_owner = official_index.get_github_owner(repo)
    if github_owner:
        return github_owner

    if isinstance(repo, str):
        try:
            parsed = urlparse(repo.strip())
        except ValueError:
            return ""

        if parsed.scheme == "https" and parsed.hostname == "gitlab.com":
            path = parsed.path.strip("/")
            if path.endswith(".git"):
                path = path[:-4]
            parts = path.split("/") if path else []
            if len(parts) >= 2 and all(part not in ("", ".", "..") for part in parts):
                return "/".join(parts[:-1])

    return ""


def _resolve_app_page_metadata(
    entry,
    scripts_dir,
    translations=None,
    resolved_long_description=None,
    resolved_long_tag=None,
    resolved_long_format=None,
):
    """Return normalized optional app-page metadata for a repository entry."""
    if resolved_long_description is None or resolved_long_tag is None:
        (
            _,
            _,
            long_description,
            long_tag,
            long_description_format,
        ) = _resolve_entry_descriptions(entry, translations)
    else:
        long_description = resolved_long_description
        long_tag = resolved_long_tag
        long_description_format = resolved_long_format or "plain"

    screenshots = _resolve_list_screenshots(entry, scripts_dir)

    purchase_url = ""
    purchase_price = None
    purchase_currency_symbol = ""
    subscription_price = None
    subscription_currency_symbol = ""
    purchase_options = []
    subscription_options = []
    purchase = entry.get("purchase")
    if isinstance(purchase, dict):
        url = purchase.get("url")
        if _valid_package_url(url):
            purchase_url = url.strip()

        purchase_options = _resolve_purchase_options(purchase, purchase_url)
        subscription_options = _resolve_subscription_options(purchase, purchase_url)

        # Preserve the old scalar metadata for callers that still consume it.
        # For multi-option commerce these expose the lowest currently resolved price.
        if purchase_options:
            lowest = min(purchase_options, key=lambda option: option["price"])
            purchase_price = lowest["price"]
            purchase_currency_symbol = lowest["currency_symbol"]
        if subscription_options:
            lowest = min(subscription_options, key=lambda option: option["price"])
            subscription_price = lowest["price"]
            subscription_currency_symbol = lowest["currency_symbol"]

    donate_url = ""
    donate = entry.get("donate")
    if isinstance(donate, str) and _valid_package_url(donate):
        donate_url = donate.strip()
    elif isinstance(donate, dict) and _valid_package_url(donate.get("url")):
        donate_url = donate["url"].strip()

    return {
        "developer": _resolve_developer_name(entry),
        "long_description": long_description,
        "long_description_tag": long_tag,
        "long_description_format": long_description_format,
        "screenshots": screenshots,
        "purchase_url": purchase_url,
        "purchase_price": purchase_price,
        "purchase_currency_symbol": purchase_currency_symbol,
        "purchase_options": purchase_options,
        "subscription_price": subscription_price,
        "subscription_currency_symbol": subscription_currency_symbol,
        "subscription_options": subscription_options,
        "donate_url": donate_url,
        "has_app_page": bool(
            long_description
            or screenshots
            or purchase_url
            or purchase_options
            or subscription_options
            or donate_url
        ),
    }


def _resolve_external_script(entry, scripts_dir):
    """Normalize an external installer URL or repository-local script path."""
    script = entry.get("script")

    if not isinstance(script, str) or not script.strip():
        return None

    script = script.strip()
    if _valid_package_url(script):
        return script

    path = _safe_list_relative_path(entry, scripts_dir, script)
    if not path or not os.path.isfile(path):
        return None

    lists_dir = os.path.realpath(os.path.join(scripts_dir, "lists"))
    return os.path.relpath(path, lists_dir)


def _resolve_hook_paths(entry, scripts_dir):
    """
    Normalize repository-local hook scripts to paths relative to scripts/lists/.

    Hook declarations are resolved relative to the JSON file that declared the
    entry, then reduced to a stable lists-relative path for run_list_hook. This
    keeps generated scripts independent from the current CACHE_DIR location.
    """
    overrides = entry.get("overrides")

    if not isinstance(overrides, dict):
        return overrides

    resolved_overrides = dict(overrides)
    lists_dir = os.path.realpath(os.path.join(scripts_dir, "lists"))

    for key in ("pre", "post"):
        value = overrides.get(key)

        if not isinstance(value, dict):
            continue

        script = value.get("script")
        path = _safe_list_relative_path(entry, scripts_dir, script)

        if not path or not os.path.isfile(path):
            return None

        relative = os.path.relpath(path, lists_dir)
        resolved_overrides[key] = {"script": relative}

    return resolved_overrides


def _resolve_list_icon(entry, scripts_dir):
    """
    Resolve repository-list icons.

    Plain filenames keep using the normal app/icons resolver.

    Relative paths such as:
        ./icon.svg
        assets/icon.png

    are resolved relative to the JSON file containing the entry, and must
    remain somewhere below scripts/lists/.
    """
    icon = entry.get("icon", "application-x-executable")

    if not isinstance(icon, str) or not icon.strip():
        return "application-x-executable"

    icon = icon.strip()

    # GTK icon names, or legacy app/icons filenames.
    if "/" not in icon and not icon.startswith("."):
        return icon

    # Repository-list icons must be relative.
    if os.path.isabs(icon):
        return "application-x-executable"

    source = entry.get("_list_source")

    if not source:
        return "application-x-executable"

    lists_dir = os.path.realpath(
        os.path.join(scripts_dir, "lists")
    )
    source_dir = os.path.realpath(
        os.path.dirname(source)
    )
    icon_path = os.path.realpath(
        os.path.join(source_dir, icon)
    )

    # Never allow a repository entry to escape scripts/lists/.
    try:
        if os.path.commonpath((lists_dir, icon_path)) != lists_dir:
            return "application-x-executable"
    except ValueError:
        return "application-x-executable"

    if not os.path.isfile(icon_path):
        return "application-x-executable"

    if not icon_path.lower().endswith((".svg", ".png")):
        return "application-x-executable"

    return icon_path

def _build_repo_entries(scripts_dir, translations=None, list_paths=None, compat_keys=None):
    data = []

    if list_paths is None:
        list_paths = _get_repo_list_paths(scripts_dir)

    for path in list_paths:
        data.extend(_load_json_entries(path))

    if compat_keys is None:
        compat_keys = get_effective_compat_keys()
    result = []
    seen_names = set()
    seen_repo_app_ids = set()

    for entry in data:
        if not isinstance(entry, dict):
            continue

        if not _required_fields_present(entry):
            continue

        if not _validate_type(entry, compat_keys):
            continue

        if not _validate_container(entry):
            continue

        if not _validate_license(entry):
            continue

        if not _validate_wsl(entry):
            continue

        if not _validate_desktop(entry):
            continue

        if not _validate_dependencies(entry):
            continue

        if not _validate_overrides(entry):
            continue

        if not _validate_tarball_post_requirement(entry, compat_keys):
            continue

        if not _validate_services(entry):
            continue

        if not _entry_is_compatible(entry, compat_keys, scripts_dir):
            continue
        # Script names are also used as registry identities and virtual paths,
        # so duplicate names from separate list files would be ambiguous.
        normalized_name = entry["name"].strip().casefold()
        repo_app_id = _repo_app_id(entry["name"])

        if not repo_app_id:
            continue

        if normalized_name in seen_names or repo_app_id in seen_repo_app_ids:
            continue

        seen_names.add(normalized_name)
        seen_repo_app_ids.add(repo_app_id)

        (
            description,
            description_tag,
            long_description,
            long_description_tag,
            long_description_format,
        ) = _resolve_entry_descriptions(entry, translations)

        # A usable short description is still mandatory. If a referenced
        # catalog is missing/invalid and no inline fallback exists, skip it.
        if not description:
            continue

        resolved_overrides = _resolve_hook_paths(entry, scripts_dir)
        if entry.get("overrides") is not None and resolved_overrides is None:
            continue

        install_type = _resolve_install_type(entry, compat_keys)
        resolved_external_script = None
        if install_type == "external":
            resolved_external_script = _resolve_external_script(entry, scripts_dir)
            if resolved_external_script is None:
                continue

        item = dict(entry)
        if "license" in item:
            item["license"] = item["license"].strip()
        if resolved_overrides is not None:
            item["overrides"] = resolved_overrides
        if resolved_external_script is not None:
            item["script"] = resolved_external_script

        app_page_metadata = _resolve_app_page_metadata(
            entry,
            scripts_dir,
            translations,
            resolved_long_description=long_description,
            resolved_long_tag=long_description_tag,
            resolved_long_format=long_description_format,
        )
        item.pop("_list_source", None)

        item.update({
            "description": description,
            "description_tag": description_tag,
            "icon": _resolve_list_icon(entry, scripts_dir),
            "type": install_type,
            **app_page_metadata,

            # Make it behave exactly like a script in the UI.
            "is_script": True,
            "is_subcategory": False,
            "is_repo_entry": True,
            "repo_app_id": repo_app_id,
            "revert": "yes",
            "reboot": "no",

            "is_new": new_index.is_new_name(
                entry["name"]
            ),

            # Virtual identity, NOT an actual shell script.
            "path": f"repo://{entry['name']}",

            "is_verified": official_index.is_verified_name(
                entry["name"]
            ),
        })

        result.append(item)

    return result


def load_repo_entries(scripts_dir, translations=None):
    """Return resolved repository entries, memoized for the active source/locale."""
    scripts_dir = os.path.realpath(scripts_dir)
    compat_keys = get_effective_compat_keys()
    compat_key = tuple(sorted(compat_keys))
    language = detect_system_language()
    dev_mode = is_dev_mode_enabled()
    runtime_key = (
        scripts_dir,
        id(translations),
        language,
        compat_key,
        is_containerized(),
        is_wsl(),
        os.environ.get("DEV_MODE", ""),
    )

    # Normal runtime source changes flow through parser.set_scripts_dir(), which
    # calls clear_runtime_caches(). Avoid walking scripts/lists merely to prove
    # that an already-cached source has not changed on every category lookup.
    # Developer mode keeps revision signatures so direct edits remain visible.
    if not dev_mode:
        with _REPO_CACHE_LOCK:
            cached = _REPO_ENTRIES_CACHE.get(runtime_key)
            if cached is not None:
                return [dict(entry) for entry in cached]

    list_paths, _, source_signature = _scan_repo_tree(scripts_dir)

    git_db_path = os.path.join(scripts_dir, "git-db.json")
    source_signature = source_signature + (
        (git_db_path, _file_signature(git_db_path)),
    )

    cache_key = runtime_key + (source_signature,) if dev_mode else runtime_key

    # A single lock deliberately coalesces simultaneous startup consumers.
    # The first builds the list; search/category/featured consumers reuse it.
    with _REPO_CACHE_LOCK:
        cached = _REPO_ENTRIES_CACHE.get(cache_key)
        if cached is None:
            cached = _build_repo_entries(
                scripts_dir,
                translations,
                list_paths=list_paths,
                compat_keys=compat_keys,
            )
            _REPO_ENTRIES_CACHE.clear()
            _REPO_ENTRIES_CACHE[cache_key] = cached

        return [dict(entry) for entry in cached]


def get_entries_for_category(scripts_dir, category_path, translations=None):
    category = os.path.basename(os.path.normpath(category_path))

    return [
        entry
        for entry in load_repo_entries(scripts_dir, translations)
        if entry["category"] == category
    ]


def _resolve_package_names(entry, compat_keys):
    """Resolve package-name, including optional per-OS mappings."""
    package = entry.get("package-name")

    direct = _normalize_package_names(package)
    if direct:
        return direct

    if not isinstance(package, dict):
        return None

    for key in NATIVE_PACKAGE_KEY_PRIORITY:
        if key not in compat_keys:
            continue

        packages = _normalize_package_names(package.get(key))
        if packages:
            return packages

    return _normalize_package_names(package.get("all"))


def _resolve_native_package(entry, compat_keys):
    """Backward-compatible alias for native package-name resolution."""
    return _resolve_package_names(entry, compat_keys)


_ENV_VAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _normalize_dynamic_url(value):
    """
    Normalize an explicit dynamic URL declaration.

    Supported form:
        {"env": "URL"}

    Returns the environment-variable name or None.
    """
    if not isinstance(value, dict) or set(value) != {"env"}:
        return None

    env_name = value.get("env")
    if not isinstance(env_name, str):
        return None

    env_name = env_name.strip()
    if not _ENV_VAR_RE.fullmatch(env_name):
        return None

    return env_name


def _has_pre_hook(entry):
    """Return True when the entry declares a valid pre-install hook."""
    overrides = entry.get("overrides")
    if not isinstance(overrides, dict):
        return False

    pre = overrides.get("pre")
    return pre is not None and _validate_hook(pre)


def _valid_url_spec(value, entry=None):
    """
    Validate either a normal HTTP(S) URL or an explicit dynamic URL spec.

    Dynamic URLs are only valid when a pre-install hook exists, because that
    hook is responsible for exporting the referenced environment variable.
    """
    if _valid_package_url(value):
        return True

    env_name = _normalize_dynamic_url(value)
    if not env_name:
        return False

    return bool(entry and _has_pre_hook(entry))


def _valid_package_url(value):
    if not isinstance(value, str) or not value.strip():
        return False

    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False

    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _resolve_url_package(entry, compat_keys):
    """
    Resolve the best downloadable package for the current system.

    Returns:
        tuple[str, str, bool] | None:
            (package_type, value, is_environment_variable)

    For dynamic declarations such as {"env": "URL"}, value is the validated
    environment-variable name and is_environment_variable is True.
    """
    urls = entry.get("urls")

    if not isinstance(urls, dict):
        return None

    native_keys = []

    if compat_keys & {
        "debian",
        "ubuntu",
        "deepin",
        "zorin",
        "pika",
    }:
        native_keys.append("deb")

    if compat_keys & {
        "fedora",
        "rhel",
        "suse",
        "ostree",
        "ublue",
    }:
        native_keys.append("rpm")

    if compat_keys & {
        "arch",
        "cachy",
        "manjaro",
    }:
        native_keys.extend(("pkg.tar.zst", "pacman"))

    def resolve_value(package_type):
        value = urls.get(package_type)

        if _valid_package_url(value):
            return package_type, value.strip(), False

        env_name = _normalize_dynamic_url(value)
        if env_name and _has_pre_hook(entry):
            return package_type, env_name, True

        return None

    # Prefer a native package.
    for key in native_keys:
        resolved = resolve_value(key)
        if resolved:
            return resolved

    # Portable fallbacks.
    for key in ("appimage", "flatpak", "tar", "bin"):
        resolved = resolve_value(key)
        if resolved:
            return resolved

    return None


def _metadata_line(value):
    """Keep generated metadata comments to a single harmless line."""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def create_install_script(entry):
    """
    Create the transient .sh consumed by the normal LinuxToys execution flow.

    Returns its filesystem path.
    """
    install_type = entry.get("type", "git")
    name = _metadata_line(entry["name"])
    description = _metadata_line(entry["description"])
    repo = entry["repo"]
    repo_metadata = _metadata_line(repo)
    icon = _metadata_line(entry.get("icon", "application-x-executable"))

    compat_keys = get_system_compat_keys()

    if not _validate_tarball_post_requirement(entry, compat_keys):
        raise ValueError(
            "Tarball repository entries require an overrides.post hook"
        )

    dependency_commands = _create_dependency_commands(
        entry,
        compat_keys,
    )
    steamos_user_make = _steamos_user_make(entry, compat_keys)
    make_build_dependencies = []
    if steamos_user_make:
        make_build_dependencies = [
            cmd[len("pkg_install "):]
            for cmd in dependency_commands
            if cmd.startswith("pkg_install ")
        ]
        dependency_commands = [
            cmd for cmd in dependency_commands if not cmd.startswith("pkg_install ")
        ]
    needs_askpass = any(
        cmd.startswith("pkg_install ")
        for cmd in dependency_commands
    )
    command = None

    if install_type == "git":
        asset_selectors = _resolve_package_names(entry, compat_keys)
        command = f"pkg_fromrelease {shlex.quote(repo)}"
        if asset_selectors:
            command += f" {shlex.quote(asset_selectors[0])}"

    elif install_type == "tar":
        asset_selectors = _resolve_package_names(entry, compat_keys)
        command = f"pkg_fromrelease --tar {shlex.quote(repo)}"
        if asset_selectors:
            command += f" {shlex.quote(asset_selectors[0])}"

    elif install_type == "make":
        make_source = entry.get("make-source", "git").strip().lower()
        make_command = entry.get("make-command")
        command = "pkg_make"
        if make_command is not None:
            command += f" --command {shlex.quote(make_command.strip())}"
        for dependency in make_build_dependencies:
            command += f" --dependency {dependency}"
        if make_source == "tar":
            asset_selectors = _resolve_package_names(entry, compat_keys)
            command += f" --tar {shlex.quote(repo)}"
            if asset_selectors:
                command += f" {shlex.quote(asset_selectors[0])}"
        else:
            command += f" {shlex.quote(repo)}"

    elif install_type == "bin":
        asset_name = entry.get("package-name", "").strip()
        command = (
            f"pkg_fromrelease --bin {shlex.quote(repo)} "
            f"{shlex.quote(asset_name)}"
        )

    elif install_type == "flathub":
        compat_keys = get_system_compat_keys()
        packages = _resolve_package_names(entry, compat_keys)
        if not packages:
            raise ValueError("No Flathub package name matches this operating system")

        skip_user_flag = " --skip-user" if _skip_user_override(entry) else ""
        command = "\n".join(
            f"pkg_flat{skip_user_flag} {shlex.quote(package)}"
            for package in packages
        )

    elif install_type == "native":
        compat_keys = get_system_compat_keys()
        packages = _resolve_package_names(entry, compat_keys)

        if not packages:
            raise ValueError(
                "No native package name matches this operating system"
            )

        command = "\n".join(
            f"pkg_install {shlex.quote(package)}"
            for package in packages
        )
        needs_askpass = True

    elif install_type == "url":
        compat_keys = get_system_compat_keys()
        resolved = _resolve_url_package(entry, compat_keys)

        if not resolved:
            raise ValueError(
                "No downloadable package URL matches this operating system"
            )

        package_type, package_value, is_environment_variable = resolved

        mode_flag = {
            "tar": " --tar",
            "bin": " --bin",
        }.get(package_type, "")

        if is_environment_variable:
            # The variable name has already been strictly validated by
            # _normalize_dynamic_url(). Use ${...} so the shell expands the
            # value exported by the pre hook while preserving it as one arg.
            package_arg = f'"${{{package_value}}}"'
        else:
            package_arg = shlex.quote(package_value)

        skip_user_flag = " --skip-user" if _skip_user_override(entry) else ""
        command = f"pkg_fromurl{mode_flag}{skip_user_flag} {package_arg}"

    elif install_type == "external":
        script = entry.get("script", "").strip()

        if _valid_package_url(script):
            script_arg = shlex.quote(script)
            command = f"""
_external_script=$(mktemp /tmp/linuxtoys-external.XXXXXX.sh) || die "Failed to create temporary external installer"
trap 'rm -f "$_external_script"' EXIT
curl -fL --retry 3 --proto '=https' --tlsv1.2 {script_arg} -o "$_external_script" || die "Failed to download external installer"
chmod 600 "$_external_script" || die "Failed to prepare external installer"
python3 "$SCRIPT_DIR/app/library_loader.py" "$_external_script" || exit $?
rm -f "$_external_script"
trap - EXIT
""".strip()
        else:
            relative = shlex.quote(script)
            command = f"""
_external_relative={relative}
_external_script=""
if [ -n "${{CACHE_DIR:-}}" ] && [ -f "$CACHE_DIR/lists/$_external_relative" ]; then
    _external_script="$CACHE_DIR/lists/$_external_relative"
elif [ -f "$SCRIPT_DIR/scripts/lists/$_external_relative" ]; then
    _external_script="$SCRIPT_DIR/scripts/lists/$_external_relative"
else
    die "External installer script not found: $_external_relative"
fi
python3 "$SCRIPT_DIR/app/library_loader.py" "$_external_script" || exit $?
""".strip()

    elif install_type == "repository":
        raise NotImplementedError(
            "Third-party repository entries are not implemented yet"
        )

    else:
        raise ValueError(f"Unknown repository entry type: {install_type}")

    pre_override = _create_hook_command(entry, "pre")
    post_override = _create_hook_command(entry, "post")

    override_commands = _create_override_commands(entry)
    service_commands = _create_service_commands(entry)

    # Authenticate before any generated pkg_install can engage the runner lock.
    # Keep this at script level so multiple native packages/dependencies share one
    # authentication request. pkg_fromfile handles downloaded native packages itself.
    auth_commands = ["askpass"] if needs_askpass else []

    # A system service also requires authentication, but avoid emitting a second
    # askpass when the package installation already requested it above.
    if needs_askpass and service_commands and service_commands[0] == "askpass":
        service_commands = service_commands[1:]

    commands = (
        auth_commands
        + dependency_commands
        + [command]
        + override_commands
        + service_commands
    )

    command_block = "\n".join(commands)

    contents = f"""#!/usr/bin/env bash
# name: {name}
# description: {description}
# icon: {icon}
# repo: {repo_metadata}
# revert: yes

{pre_override}

{command_block}

{post_override}

info "$finishmsg"
"""

    tmp_dir = "/tmp/linuxtoys/repo-scripts"
    os.makedirs(tmp_dir, mode=0o700, exist_ok=True)

    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-._") or "entry"
    identity = hashlib.sha256(
        f"{entry.get('name', '')}\0{entry.get('repo', '')}".encode("utf-8")
    ).hexdigest()[:12]
    path = os.path.join(tmp_dir, f"{safe_name}-{identity}.sh")
    tmp_path = f"{path}.tmp"

    try:
        with open(tmp_path, "w", encoding="utf-8") as file:
            file.write(contents)

        os.chmod(tmp_path, 0o700)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return path


def materialize_repo_script(script_info):
    """Return an execution-ready copy of a dynamic repository entry."""
    if not script_info.get("is_repo_entry"):
        return script_info

    materialized = dict(script_info)
    materialized["virtual_path"] = script_info.get("path")
    materialized["path"] = create_install_script(script_info)
    return materialized

def _systemd_requirement_matches(entry, compat_keys):
    """
    Check an entry's optional systemd requirement.

    systemd:
      omitted / "" -> neutral
      "yes"        -> requires systemd
      "no"         -> requires non-systemd

    Invalid values make the entry incompatible.
    """
    value = entry.get("systemd", "")

    if value is None:
        value = ""

    if not isinstance(value, str):
        return False

    value = value.strip().lower()

    if not value:
        return True

    if value == "yes":
        return "systemd" in compat_keys

    if value == "no":
        return "systemd" not in compat_keys

    return False

def _validate_dependencies(entry):
    dependencies = entry.get("dependencies", [])

    if dependencies is None:
        return True

    if not isinstance(dependencies, list):
        return False

    for dependency in dependencies:
        if not isinstance(dependency, dict):
            return False

        dependency_type = dependency.get("type")

        if dependency_type not in {"native", "flathub"}:
            return False

        package = dependency.get("package-name")

        if dependency_type == "flathub":
            if not _normalize_package_names(package):
                return False

        elif dependency_type == "native":
            if not _validate_native_package_spec(package):
                return False

    return True

def _dependencies_are_compatible(entry, compat_keys):
    dependencies = entry.get("dependencies", [])

    if not dependencies:
        return True

    for dependency in dependencies:
        dependency_type = dependency.get("type")

        if dependency_type == "flathub":
            if "systemd" not in compat_keys:
                return False

        elif dependency_type == "native":
            dependency_compat = {"arch"} if _steamos_user_make(entry, compat_keys) else compat_keys
            if not _resolve_native_package(dependency, dependency_compat):
                return False

    return True

def _create_dependency_commands(entry, compat_keys):
    commands = []

    for dependency in entry.get("dependencies", []):
        dependency_type = dependency["type"]

        if dependency_type == "native":
            dependency_compat = {"arch"} if _steamos_user_make(entry, compat_keys) else compat_keys
            packages = _resolve_native_package(
                dependency,
                dependency_compat,
            )

            if not packages:
                raise ValueError(
                    "No native package matches a declared dependency"
                )

            commands.extend(
                f"pkg_install {shlex.quote(package)}"
                for package in packages
            )

        elif dependency_type == "flathub":
            packages = _normalize_package_names(
                dependency["package-name"]
            )

            if not packages:
                raise ValueError(
                    "Flathub dependency has no package-name"
                )

            skip_user_flag = " --skip-user" if _skip_user_override(entry) else ""
            commands.extend(
                f"pkg_flat{skip_user_flag} {shlex.quote(package)}"
                for package in packages
            )

    return commands


def _validate_hook(value):
    if isinstance(value, str):
        return bool(value.strip())

    if not isinstance(value, dict):
        return False

    if set(value) != {"script"}:
        return False

    script = value.get("script")

    if not isinstance(script, str) or not script.strip():
        return False

    script = script.strip()

    # Paths must stay below scripts/lists.
    if os.path.isabs(script):
        return False

    normalized = os.path.normpath(script)

    if normalized == ".." or normalized.startswith("../"):
        return False

    return True

def _entry_uses_tarball(entry, compat_keys):
    """Return True when this entry resolves to a tarball installation."""
    install_type = _resolve_install_type(entry, compat_keys)

    if install_type == "tar":
        return True

    if install_type != "url":
        return False

    resolved = _resolve_url_package(entry, compat_keys)
    return bool(resolved and resolved[0] == "tar")


def _validate_tarball_post_requirement(entry, compat_keys):
    """
    Tarballs only unpack application files. Require a valid post-install hook
    so repository-list authors explicitly perform any integration needed by
    the extracted application (desktop entry, launcher, symlinks, etc.).
    """
    if not _entry_uses_tarball(entry, compat_keys):
        return True

    overrides = entry.get("overrides")
    if not isinstance(overrides, dict):
        return False

    post = overrides.get("post")
    return post is not None and _validate_hook(post)


def _validate_overrides(entry):
    overrides = entry.get("overrides")

    if overrides is None:
        return True

    if not isinstance(overrides, dict):
        return False

    # Only supported override types.
    if set(overrides) - {"flatpak", "pre", "post", "skip-user"}:
        return False

    skip_user = overrides.get("skip-user")
    if skip_user is not None and not isinstance(skip_user, bool):
        return False

    # Validate pre/post hooks.
    for key in ("pre", "post"):
        value = overrides.get(key)

        if value is not None and not _validate_hook(value):
            return False

    # Validate Flatpak overrides.
    flatpak = overrides.get("flatpak")

    if flatpak is None:
        return True

    if not isinstance(flatpak, list):
        return False

    valid_scopes = {"user", "system"}
    valid_types = {
        "fs",
        "name",
        "dbus",
        "share",
        "env",
        "runtime",
        "device",
        "socket",
        "filesystem",
        "talk-name",
        "talk-dbus",
    }

    for override in flatpak:
        if not isinstance(override, dict):
            return False

        scope = override.get("scope")
        override_type = override.get("type")
        setting = override.get("setting")
        target = override.get("target")

        if scope not in valid_scopes:
            return False
        if override_type not in valid_types:
            return False
        if not isinstance(setting, str) or not setting.strip():
            return False
        if not isinstance(target, str) or not target.strip():
            return False

    return True

def _skip_user_override(entry):
    """Return whether Flatpak installs for this entry must avoid user scope."""
    overrides = entry.get("overrides", {})
    return isinstance(overrides, dict) and overrides.get("skip-user") is True


def _create_override_commands(entry):
    commands = []

    overrides = entry.get("overrides", {})
    flatpak_overrides = overrides.get("flatpak", [])

    for override in flatpak_overrides:
        commands.append(
            "flatpak_override "
            f"{shlex.quote(override['scope'].strip())} "
            f"{shlex.quote(override['type'].strip())} "
            f"{shlex.quote(override['setting'].strip())} "
            f"{shlex.quote(override['target'].strip())}"
        )

    return commands

def _create_hook_command(entry, key):
    overrides = entry.get("overrides", {})

    if not isinstance(overrides, dict):
        return ""

    value = overrides.get(key)

    if value is None:
        return ""

    # Inline shell.
    if isinstance(value, str):
        return value.strip()

    # Script shipped under scripts/lists.
    if isinstance(value, dict):
        script = value.get("script", "").strip()

        if not script:
            return ""

        quoted = shlex.quote(script)

        return f'run_list_hook {quoted}'

    return ""

def _normalize_service_name(value):
    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    if not any(value.endswith(suffix) for suffix in SYSTEMD_UNIT_SUFFIXES):
        value += ".service"

    return value

def _normalize_services(entry):
    """
    Normalize the services field to:

        {
            "system": [...],
            "user": [...]
        }

    Direct strings/lists default to system scope.
    """
    services = entry.get("services")

    if services is None:
        return {
            "system": [],
            "user": [],
        }

    if isinstance(services, str):
        services = {
            "system": [services],
        }

    elif isinstance(services, list):
        services = {
            "system": services,
        }

    elif isinstance(services, dict):
        # Only supported scopes.
        if set(services) - {"system", "user"}:
            return None

    else:
        return None

    normalized = {
        "system": [],
        "user": [],
    }

    for scope in ("system", "user"):
        values = services.get(scope, [])

        if isinstance(values, str):
            values = [values]

        if not isinstance(values, list):
            return None

        for value in values:
            service = _normalize_service_name(value)

            if not service:
                return None

            normalized[scope].append(service)

    return normalized

def _validate_services(entry):
    return _normalize_services(entry) is not None

def _create_service_commands(entry):
    services = _normalize_services(entry)

    if not services:
        return []

    commands = []

    if services["system"]:
        commands.append("askpass")

        for service in services["system"]:
            quoted = shlex.quote(service)

            commands.extend([
                f"sudo systemctl enable --now {quoted}",
                f'_append_transmap "sysd enabled {service}"',
                f'_append_transmap "sysd started {service}"',
            ])

    for service in services["user"]:
        quoted = shlex.quote(service)

        commands.extend([
            f"systemctl --user enable --now {quoted}",
            f'_append_transmap "sysd usermode enabled {service}"',
            f'_append_transmap "sysd usermode started {service}"',
        ])

    return commands
