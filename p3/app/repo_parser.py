import json
import locale
import os
import re
import shlex
import hashlib
import threading
from urllib.parse import urlparse

from .compat import get_system_compat_keys, is_containerized, is_wsl
from .dev_mode import get_effective_compat_keys, get_dev_compat_override, is_dev_mode_enabled
from . import official_index, new_index
from .lang_utils import detect_system_language

from . import _catalog_rs as _rs


# Repository metadata is consumed by several startup caches in parallel.  Keep
# immutable file-backed inputs and the fully resolved entry list memoized so
# those consumers do not repeatedly walk and decode the same repository tree.
_REPO_CACHE_LOCK = threading.RLock()
_REPO_ENTRIES_CACHE = {}
_MONETARY_LOCALE_CACHE = None


def _file_signature(path):
    return _rs.file_signature(os.fspath(path))


def clear_runtime_caches():
    """Drop parser memoization after an in-process repository/source refresh."""
    with _REPO_CACHE_LOCK:
        _REPO_ENTRIES_CACHE.clear()
        global _MONETARY_LOCALE_CACHE
        _MONETARY_LOCALE_CACHE = None


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












def _repo_app_id(name):
    return _rs.repo_app_id(str(name))








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




def _load_json_entries(path):
    return list(_rs.load_json_entries(os.fspath(path)))


def _scan_repo_tree(scripts_dir):
    json_paths, markdown_paths, signatures = _rs.scan_repo_tree(os.fspath(scripts_dir))
    return tuple(json_paths), tuple(markdown_paths), tuple((p, tuple(sig) if sig is not None else None) for p, sig in signatures)


def _get_repo_list_paths(scripts_dir):
    """Return all repository-list JSON files in deterministic order."""
    json_paths, _, _ = _scan_repo_tree(scripts_dir)
    return list(json_paths)


DESCRIPTION_FILE_KEYS = ("descriptions", "description-file")














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




APPSTREAM_OVERLAY_KEYS = {"appstream-name", "purchase", "overrides", "dependencies"}


def _normalize_appstream_overlay_id(value):
    return _rs.normalize_appstream_overlay_id(value) if isinstance(value, str) else ""


def resolve_commerce_metadata(entry):
    """Return the purchase/subscription metadata understood by AppPageView."""
    purchase_url = ""
    purchase_price = None
    purchase_currency_symbol = ""
    subscription_price = None
    subscription_currency_symbol = ""
    purchase_options = []
    subscription_options = []

    purchase = entry.get("purchase") if isinstance(entry, dict) else None
    if isinstance(purchase, dict):
        url = purchase.get("url")
        if _valid_package_url(url):
            purchase_url = url.strip()

        purchase_options = _resolve_purchase_options(purchase, purchase_url)
        subscription_options = _resolve_subscription_options(purchase, purchase_url)

        if purchase_options:
            lowest = min(purchase_options, key=lambda option: option["price"])
            purchase_price = lowest["price"]
            purchase_currency_symbol = lowest["currency_symbol"]
        if subscription_options:
            lowest = min(subscription_options, key=lambda option: option["price"])
            subscription_price = lowest["price"]
            subscription_currency_symbol = lowest["currency_symbol"]

    return {
        "purchase_url": purchase_url,
        "purchase_price": purchase_price,
        "purchase_currency_symbol": purchase_currency_symbol,
        "purchase_options": purchase_options,
        "subscription_price": subscription_price,
        "subscription_currency_symbol": subscription_currency_symbol,
        "subscription_options": subscription_options,
    }


def load_appstream_overlays(scripts_dir, list_paths=None):
    """Return valid metadata overlays keyed by normalized AppStream component ID.

    AppStream overlays never become standalone repository entries. They may add
    commerce metadata, reviewed pre/post/Flatpak overrides, and dependencies to
    an upstream AppStream component without replacing its normal install source.
    """
    if list_paths is None:
        list_paths = _get_repo_list_paths(scripts_dir)

    overlays = {}
    for path in list_paths:
        for entry in _load_json_entries(path):
            if not isinstance(entry, dict) or "appstream-name" not in entry:
                continue

            # _list_source is parser-internal metadata added by _load_json_entries.
            public_keys = set(entry) - {"_list_source"}
            if not public_keys <= APPSTREAM_OVERLAY_KEYS:
                continue

            appstream_id = _normalize_appstream_overlay_id(entry.get("appstream-name"))
            if not appstream_id:
                continue

            overlay = {}
            if isinstance(entry.get("purchase"), dict):
                commerce = resolve_commerce_metadata(entry)
                if commerce["purchase_options"] or commerce["subscription_options"]:
                    overlay.update(commerce)

            if entry.get("dependencies") is not None:
                # Reuse the normal repository dependency schema and resolve native
                # package mappings for this host before the overlay reaches the
                # AppStream runner. The runner can then execute the dependencies
                # directly without invoking the repository-script materializer.
                if not _validate_dependencies(entry):
                    continue
                compat_keys = get_system_compat_keys()
                if not _dependencies_are_compatible(entry, compat_keys):
                    continue
                resolved_dependencies = []
                dependency_valid = True
                for dependency in entry.get("dependencies", []):
                    dependency_type = dependency.get("type")
                    if dependency_type == "native":
                        packages = _resolve_native_package(dependency, compat_keys)
                    else:
                        packages = _normalize_package_names(dependency.get("package-name"))
                    if not packages:
                        dependency_valid = False
                        break
                    resolved_dependencies.append({
                        "type": dependency_type,
                        "packages": list(packages),
                    })
                if not dependency_valid:
                    continue
                if resolved_dependencies:
                    overlay["appstream_dependencies"] = resolved_dependencies

            if entry.get("overrides") is not None:
                # AppStream overlays deliberately support only execution hooks and
                # Flatpak permission overrides. Source-selection controls such as
                # skip-user remain owned by the AppStream source selector itself.
                overrides = entry.get("overrides")
                if not isinstance(overrides, dict) or set(overrides) - {"pre", "post", "flatpak"}:
                    continue
                if not _validate_overrides(entry):
                    continue
                resolved = _resolve_hook_paths(entry, scripts_dir)
                if not isinstance(resolved, dict):
                    continue
                overlay["appstream_overrides"] = resolved

            if not overlay:
                continue

            # Deterministic list order: the first valid declaration wins.
            overlays.setdefault(appstream_id, overlay)

    return overlays


def load_appstream_commerce_overlays(scripts_dir, list_paths=None):
    """Backward-compatible commerce-only view of AppStream overlays."""
    commerce_keys = {
        "purchase_url", "purchase_price", "purchase_currency_symbol",
        "purchase_options", "subscription_price",
        "subscription_currency_symbol", "subscription_options",
    }
    return {
        key: {name: value for name, value in overlay.items() if name in commerce_keys}
        for key, overlay in load_appstream_overlays(scripts_dir, list_paths).items()
        if any(name in commerce_keys for name in overlay)
    }




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



def _build_repo_entries(scripts_dir, translations=None, list_paths=None, compat_keys=None):
    """Build the repository catalog in Rust, then add Python-owned shared metadata."""
    if compat_keys is None:
        compat_keys = get_effective_compat_keys()

    from .dev_mode import should_override_container_checks

    language = detect_system_language()
    translations_json = json.dumps(translations or {}, ensure_ascii=False)
    data = list(_rs.build_repo_catalog(
        os.fspath(scripts_dir),
        sorted(compat_keys),
        bool(is_dev_mode_enabled()),
        bool(get_dev_compat_override()),
        bool(is_containerized()),
        bool(is_wsl()),
        bool(should_override_container_checks()),
        os.uname().machine.lower() if hasattr(os, "uname") else "",
        translations_json,
        language,
    ))

    result = []
    for entry in data:
        if not isinstance(entry, dict):
            continue

        name = entry.get("name", "")
        repo_app_id = _repo_app_id(name)
        if not repo_app_id:
            continue

        item = dict(entry)
        install_type = item.pop("_rust_resolved_type", None)
        item.pop("_list_source", None)
        if "license" in item and isinstance(item["license"], str):
            item["license"] = item["license"].strip()

        # Commerce remains shared Python code because AppStream overlays consume
        # the exact same normalized purchase/subscription representation.
        commerce = resolve_commerce_metadata(entry)
        donate_url = ""
        donate = entry.get("donate")
        if isinstance(donate, str) and _valid_package_url(donate):
            donate_url = donate.strip()
        elif isinstance(donate, dict) and _valid_package_url(donate.get("url")):
            donate_url = donate["url"].strip()

        long_description = item.get("long_description", "")
        screenshots = item.get("screenshots", [])
        item.update({
            "developer": _resolve_developer_name(entry),
            **commerce,
            "donate_url": donate_url,
            "has_app_page": bool(
                long_description or screenshots or commerce["purchase_url"]
                or commerce["purchase_options"] or commerce["subscription_options"]
                or donate_url
            ),
            "type": install_type,
            "is_script": True,
            "is_subcategory": False,
            "is_repo_entry": True,
            "repo_app_id": repo_app_id,
            "revert": "yes",
            "reboot": "no",
            "is_new": new_index.is_new_name(name),
            "path": f"repo://{name}",
            "is_official": official_index.is_verified_name(name),
            "is_verified": official_index.is_verified_name(name),
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
    finish_command = "" if entry.get("is_appstream_entry") else 'info "$finishmsg"'

    contents = f"""#!/usr/bin/env bash
# name: {name}
# description: {description}
# icon: {icon}
# repo: {repo_metadata}
# revert: yes

{pre_override}

{command_block}

{post_override}

{finish_command}
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
