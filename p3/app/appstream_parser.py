"""Adapt cached AppStream components to LinuxToys repository-style entries."""

from __future__ import annotations

import os
import re
import threading

from . import appstream_cache
from .compat import get_system_compat_keys
from .lang_utils import detect_system_language


_CACHE_LOCK = threading.RLock()
_RUNTIME_CACHE = {}

# Developer-facing source preference filter. Flatpak wins by default when the
# same application exists in both catalogs. Add exceptions here by AppStream ID
# (preferred) or exact display name. Values may be a source string or an OS map.
#
# Examples:
#   "org.example.App": "native",
#   "Example App": {"fedora": "native", "arch": "native", "all": "flatpak"},
#
# Valid source values: "flatpak" and "native".
APPSTREAM_SOURCE_PREFERENCE = {
    "default": "flatpak",
    "apps": {
        # "org.example.App": {"fedora": "native", "all": "flatpak"},
    },
}

# AppStream uses the freedesktop.org Desktop Menu category registry. Keep Main
# and Additional categories separate so the finer Additional mappings can be
# tuned independently without changing the broad Main-category fallback.
#
# Candidate directory names are LinuxToys category directories. The first one
# that exists in the active scripts tree wins.
MAIN_CATEGORY_CANDIDATES = {
    "AudioVideo": ("media", "multimedia"),
    "Audio": ("audio", "multimedia"),
    "Video": ("video", "multimedia"),
    "Development": ("devs", "development"),
    "Education": ("edu", "education"),
    "HealthFitness": ("health", "utilities"),
    "Game": ("game", "games"),
    "Graphics": ("creat", "graphics", "office"),
    "Network": ("network", "utils"),
    "Office": ("office", "productivity"),
    "Science": ("edu", "science", "education"),
    "Settings": ("sysadm", "system", "utils"),
    "System": ("sysadm", "system", "utils"),
    "Utility": ("utils", "utilities"),
}

ADDITIONAL_CATEGORY_CANDIDATES = {
    # Development
    "Building": ("tools", "development"),
    "Debugger": ("tools", "development"),
    "IDE": ("ides", "development"),
    "GUIDesigner": ("ides", "development"),
    "Profiling": ("tools", "development"),
    "RevisionControl": ("tools", "development"),
    "Translation": ("tools", "development"),

    # Office / productivity
    "Calendar": ("planning", "productivity"),
    "ContactManagement": ("chat", "productivity"),
    "Database": ("planning", "devs", "development", "media", "multimedia"),
    "Dictionary": ("langs", "utils", "utilities"),
    "Chart": ("planning", "productivity"),
    "Email": ("chat", "network", "productivity"),
    "Finance": ("fin", "productivity"),
    "FlowChart": ("planning", "productivity"),
    "PDA": ("planning", "productivity"),
    "ProjectManagement": ("planning", "devs", "development", "productivity"),
    "Presentation": ("document", "productivity"),
    "Spreadsheet": ("document", "productivity"),
    "WordProcessor": ("document", "productivity"),

    # Graphics
    "2DGraphics": ("draw", "graphics", "office"),
    "VectorGraphics": ("draw", "graphics", "office"),
    "RasterGraphics": ("draw", "graphics", "office"),
    "3DGraphics": ("creative", "graphics", "office"),
    "Scanning": ("document", "graphics", "office"),
    "OCR": ("creative", "graphics", "office"),
    "Photography": ("photo", "graphics", "office"),
    "Publishing": ("creative", "graphics", "office"),
    "Viewer": ("viewer", "graphics", "office"),
    "TextTools": ("document", "utilities"),

    # Settings
    "DesktopSettings": ("sysadm", "system", "utils"),
    "HardwareSettings": ("sysadm", "system", "utils"),
    "Printing": ("document", "system", "utils"),
    "PackageManager": ("sysadm", "system", "utils"),

    # Network
    "Dialup": ("network", "utils"),
    "InstantMessaging": ("chat", "utils"),
    "Chat": ("chat", "utils"),
    "IRCClient": ("chat", "utils"),
    "Feed": ("network", "utils"),
    "FileTransfer": ("p2p", "utils"),
    "HamRadio": ("tv", "office", "audio", "multimedia"),
    "News": ("network", "utils"),
    "P2P": ("p2p", "utils"),
    "RemoteAccess": ("remote", "utils"),
    "Telephony": ("network", "utils"),
    "TelephonyTools": ("network", "utilities"),
    "VideoConference": ("chat", "utils"),
    "WebBrowser": ("browsers", "utils"),
    "WebDevelopment": ("devs", "development", "network"),

    # Audio / video
    "Midi": ("audio", "multimedia", "media"),
    "Mixer": ("audio", "multimedia", "media"),
    "Sequencer": ("audio", "multimedia", "media"),
    "Tuner": ("tv", "audio", "multimedia", "media"),
    "TV": ("tv", "video", "multimedia", "media"),
    "AudioVideoEditing": ("video", "multimedia", "office"),
    "Player": ("players", "multimedia", "office"),
    "Recorder": ("rec", "multimedia", "office"),
    "DiscBurning": ("rec", "multimedia"),

    # Games
    "ActionGame": ("action", "games"),
    "AdventureGame": ("action", "games"),
    "ArcadeGame": ("classic", "games"),
    "BoardGame": ("classic", "games"),
    "BlocksGame": ("kids", "games"),
    "CardGame": ("classic", "games"),
    "KidsGame": ("kids", "games"),
    "LogicGame": ("kids", "games"),
    "RolePlaying": ("sim", "games"),
    "Shooter": ("action", "games"),
    "Simulation": ("sim", "games"),
    "SportsGame": ("sports", "games"),
    "StrategyGame": ("strategy", "games"),

    # Education / science
    "Art": ("edu", "science", "education"),
    "Construction": ("edu", "science", "education"),
    "Music": ("audio", "education", "media", "multimedia"),
    "Languages": ("langs", "science", "education"),
    "ArtificialIntelligence": ("tech", "science", "education"),
    "Astronomy": ("nature", "science", "education"),
    "Biology": ("nature", "science", "education"),
    "Chemistry": ("nature", "science", "education"),
    "ComputerScience": ("tech", "science", "education"),
    "DataVisualization": ("tech", "science", "education"),
    "Economy": ("math", "science", "education"),
    "Electricity": ("tech", "science", "education"),
    "Geography": ("geo", "science", "education"),
    "Geology": ("nature", "science", "education"),
    "Geoscience": ("nature", "science", "education"),
    "History": ("edu", "science", "education"),
    "Humanities": ("geo", "science", "education"),
    "ImageProcessing": ("photo", "science", "education"),
    "Literature": ("langs", "science", "education"),
    "Maps": ("geo", "science", "education", "utils"),
    "Math": ("math", "science", "education"),
    "NumericalAnalysis": ("math", "science", "education"),
    "MedicalSoftware": ("health", "science", "education"),
    "Physics": ("math", "science", "education"),
    "Robotics": ("tech", "science", "education"),
    "Spirituality": ("health", "science", "education", "utils"),
    "Sports": ("health", "science", "education"),
    "ParallelComputing": ("tech", "science", "education"),

    # General utility / system categories
    "Amusement": ("game", "utilities"),
    "Archiving": ("archive", "utilities"),
    "Compression": ("archive", "utilities"),
    "Electronics": ("eng", "utilities"),
    "Emulator": ("emu", "system", "game", "games"),
    "Engineering": ("eng", "utilities"),
    "FileTools": ("p2p", "sysadm", "system"),
    "FileManager": ("archive", "system", "utils"),
    "TerminalEmulator": ("sys", "system", "utils"),
    "Filesystem": ("sys", "system", "utils"),
    "Monitor": ("sec", "system", "network", "utils"),
    "Security": ("sec", "system", "utils"),
    "Accessibility": ("accessibility", "utils"),
    "Calculator": ("fin", "utilities"),
    "Clock": ("office", "utilities"),
    "TextEditor": ("txt", "utilities"),
    "Documentation": ("misc"),
    "Adult": ("utils", "utilities"),
    "Core": ("sys", "system", "utils"),

    # Toolkit / implementation hints
    "KDE": ("misc", "utilities"),
    "GNOME": ("misc", "utilities"),
    "XFCE": ("misc", "utilities"),
    "GTK": ("misc", "utilities"),
    "Qt": ("misc", "utilities"),
    "Motif": ("misc", "utilities"),
    "Java": ("devs", "utilities"),
    "ConsoleOnly": ("devs", "utilities"),
}

# Additional categories are deliberately considered before Main categories.
# They are more specific, and keeping the priority lists separate makes it easy
# to tune this behavior later alongside the mappings above.
ADDITIONAL_CATEGORY_PRIORITY = tuple(ADDITIONAL_CATEGORY_CANDIDATES)
MAIN_CATEGORY_PRIORITY = (
    "Game",
    "Development",
    "Graphics",
    "AudioVideo",
    "Audio",
    "Video",
    "Office",
    "Education",
    "Science",
    "HealthFitness",
    "Network",
    "Settings",
    "System",
    "Utility",
)


def clear_runtime_cache():
    with _CACHE_LOCK:
        _RUNTIME_CACHE.clear()


def _flatten_package_names(value):
    result = []
    if isinstance(value, str):
        value = value.strip()
        if value:
            result.append(value)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            result.extend(_flatten_package_names(item))
    elif isinstance(value, dict):
        for item in value.values():
            result.extend(_flatten_package_names(item))
    return result


def _curated_identity_sets(curated_entries):
    ids = set()
    packages = set()
    names = set()

    for entry in curated_entries or ():
        name = str(entry.get("name", "") or "").strip()
        if name:
            names.add(name.casefold())

        for key in ("appstream-id", "appstream_id"):
            value = str(entry.get(key, "") or "").strip()
            if value:
                ids.add(value.casefold())

        # Curated LinuxToys entries always win. Package IDs are authoritative for
        # both native packages and Flatpak application IDs.
        packages.update(
            package.casefold()
            for package in _flatten_package_names(entry.get("package-name"))
        )

    return ids, packages, names


def _category_path_lookup(category_paths):
    """Build exact-relative-path and basename lookups from parser's tree index."""
    exact = set()
    by_name = {}

    for raw_path in category_paths or ():
        path = str(raw_path or "").strip().replace(os.sep, "/").strip("/")
        if not path or path == "lists":
            continue
        exact.add(path)
        by_name.setdefault(path.rsplit("/", 1)[-1], []).append(path)

    # Prefer the shallowest match when the same directory basename exists in
    # multiple branches, then use lexical order for deterministic resolution.
    for matches in by_name.values():
        matches.sort(key=lambda path: (path.count("/"), path))

    return exact, by_name


def _resolve_category(appstream_categories, category_paths):
    """Resolve Additional categories first, using the complete indexed tree."""
    categories = set(appstream_categories or ())
    exact, by_name = _category_path_lookup(category_paths)

    for priority, mappings in (
        (ADDITIONAL_CATEGORY_PRIORITY, ADDITIONAL_CATEGORY_CANDIDATES),
        (MAIN_CATEGORY_PRIORITY, MAIN_CATEGORY_CANDIDATES),
    ):
        for appstream_category in priority:
            if appstream_category not in categories:
                continue
            for candidate in mappings[appstream_category]:
                candidate = str(candidate).replace(os.sep, "/").strip("/")
                if candidate in exact:
                    return candidate
                matches = by_name.get(candidate)
                if matches:
                    return matches[0]

    return None


def _is_curated(component, curated_ids, curated_packages, curated_names):
    component_id = str(component.get("id", "") or "").casefold()
    if component_id and component_id in curated_ids:
        return True

    packages = {
        str(package).casefold()
        for package in component.get("packages", ())
        if package
    }
    if packages & curated_packages:
        return True

    name = str(component.get("name", "") or "").strip().casefold()
    return bool(name and name in curated_names)



def _host_os_keys():
    values = set()
    try:
        data = {}
        with open("/etc/os-release", "r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                if "=" not in raw:
                    continue
                key, value = raw.rstrip().split("=", 1)
                data[key] = value.strip().strip('"').strip("'")
        for field in ("ID", "ID_LIKE"):
            values.update(part.casefold() for part in data.get(field, "").split() if part)
    except OSError:
        pass
    # Match LinuxToys' common family keys used by repository-list OS maps.
    aliases = {
        "manjaro": "arch", "endeavouros": "arch",
        "rhel": "fedora", "centos": "fedora", "rocky": "fedora", "almalinux": "fedora",
        "linuxmint": "ubuntu", "pop": "ubuntu",
        "opensuse-tumbleweed": "suse", "opensuse-leap": "suse", "opensuse": "suse",
    }
    values.update(aliases[key] for key in tuple(values) if key in aliases)
    return values


def _is_verified_flatpak(component):
    return (
        str(component.get("source", "native") or "native") == "flatpak"
        and bool(component.get("verified", False))
    )


def _host_prefers_native_appstream():
    """Arch Linux and CachyOS prefer native packages over ordinary Flathub."""
    compat_keys = get_system_compat_keys()
    return "arch" in compat_keys or "cachy" in compat_keys


def _is_steamos_host():
    """SteamOS cannot install native AppStream packages through LinuxToys."""
    return "steamos" in get_system_compat_keys()


def _is_native_preferred_development_component(component, category_paths):
    """Return whether LinuxToys resolves this component into devs or its IDE child."""
    category = _resolve_category(component.get("categories", ()), category_paths)
    return bool(category and category.rsplit("/", 1)[-1] in {"devs", "ides"})


def _group_prefers_native_development(group, category_paths):
    """Development/IDE entries prefer native packages everywhere except SteamOS."""
    return not _is_steamos_host() and any(
        _is_native_preferred_development_component(component, category_paths)
        for component in group
    )


def _inherit_flatpak_popularity(natives, flatpaks):
    """Copy a discarded Flatpak's persistent popularity metric onto native duplicates."""
    donor = next(
        (
            item for item in flatpaks
            if item.get("popularity_metric") is not None
        ),
        None,
    )
    if donor is None:
        return

    for native in natives:
        native["popularity_metric"] = donor.get("popularity_metric")
        native["popularity_downloads"] = donor.get("popularity_downloads")


def _resolve_source_preference(component):
    apps = APPSTREAM_SOURCE_PREFERENCE.get("apps", {})
    component_id = str(component.get("id", "") or "")
    name = str(component.get("name", "") or "")
    value = apps.get(component_id, apps.get(name, APPSTREAM_SOURCE_PREFERENCE.get("default", "flatpak")))
    if isinstance(value, dict):
        os_keys = _host_os_keys()
        for key, choice in value.items():
            if key != "all" and key.casefold() in os_keys:
                return choice
        value = value.get("all", APPSTREAM_SOURCE_PREFERENCE.get("default", "flatpak"))
    return value if value in {"native", "flatpak"} else "flatpak"


def _component_match_keys(component):
    component_id = str(component.get("id", "") or "").strip().casefold()
    if component_id.endswith(".desktop"):
        component_id = component_id[:-8]
    name = str(component.get("name", "") or "").strip().casefold()
    return component_id, name


def _with_source_options(selected, group):
    """Preserve installable native/Flatpak alternatives when source choice is useful."""
    sources = {str(item.get("source", "native") or "native") for item in group}
    if not {"native", "flatpak"} <= sources:
        return selected

    flatpaks = [item for item in group if item.get("source") == "flatpak"]
    selected_source = str(selected.get("source", "native") or "native")

    # A verified Flathub entry remains authoritative when it is the selected
    # default. Otherwise expose both sources and mark the selected one as the
    # LinuxToys recommendation.
    if selected_source == "flatpak" and any(_is_verified_flatpak(item) for item in flatpaks):
        return selected

    result = dict(selected)
    alternatives = []
    seen_sources = set()
    for item in group:
        source = str(item.get("source", "native") or "native")
        if source == selected_source or source in seen_sources:
            continue
        seen_sources.add(source)
        alternatives.append(dict(item))

    if alternatives:
        result["_source_alternatives"] = alternatives
        result["_source_recommended"] = selected_source
    return result


def _prefer_sources(components, category_paths):
    """Collapse native/Flatpak duplicates according to the developer filter."""
    groups = {}
    passthrough = []
    for component in components:
        if not isinstance(component, dict):
            continue
        cid, name = _component_match_keys(component)
        key = ("id", cid) if cid else (("name", name) if name else None)
        if key is None:
            passthrough.append(component)
            continue
        groups.setdefault(key, []).append(component)

    result = list(passthrough)
    # First merge exact IDs. A second conservative name pass catches native IDs
    # that use a desktop-file identifier different from the Flatpak app ID.
    for group in groups.values():
        # The same Flatpak remote can exist at user and system scope. Present one
        # app, preferring user scope because pkg_flat follows the same policy.
        flatpaks = [item for item in group if item.get("source") == "flatpak"]
        natives = [item for item in group if item.get("source", "native") == "native"]
        if flatpaks:
            flatpaks.sort(key=lambda item: (item.get("flatpak_scope") != "user", item.get("flatpak_installation", "")))
            flatpaks = flatpaks[:1]
        group = natives + flatpaks
        sources = {str(item.get("source", "native")) for item in group}
        if len(sources) < 2:
            result.extend(group)
            continue
        verified_flatpaks = [item for item in flatpaks if _is_verified_flatpak(item)]

        # Development tools and IDEs prefer the distro package even when the
        # matching Flathub build is verified. Preserve Flathub's popularity metric
        # on the native entry so browse ranking can still use real usage data.
        if natives and _group_prefers_native_development(group, category_paths):
            _inherit_flatpak_popularity(natives, flatpaks)
            result.extend(_with_source_options(item, group) for item in natives)
            continue

        if verified_flatpaks:
            # Publisher verification normally outranks distro-specific preference.
            result.extend(_with_source_options(item, group) for item in verified_flatpaks)
            continue

        if _host_prefers_native_appstream() and natives:
            result.extend(_with_source_options(item, group) for item in natives)
            continue

        preferred = _resolve_source_preference(group[0])
        chosen = [item for item in group if item.get("source", "native") == preferred]
        selected = chosen or group
        result.extend(_with_source_options(item, group) for item in selected)

    by_name = {}
    unnamed = []
    for component in result:
        name = str(component.get("name", "") or "").strip().casefold()
        if name:
            by_name.setdefault(name, []).append(component)
        else:
            unnamed.append(component)
    final = list(unnamed)
    for group in by_name.values():
        sources = {str(item.get("source", "native")) for item in group}
        if len(sources) < 2:
            final.extend(group)
            continue
        flatpaks = [item for item in group if item.get("source") == "flatpak"]
        natives = [item for item in group if item.get("source", "native") == "native"]
        verified_flatpaks = [item for item in flatpaks if _is_verified_flatpak(item)]

        if natives and _group_prefers_native_development(group, category_paths):
            _inherit_flatpak_popularity(natives, flatpaks)
            final.extend(_with_source_options(item, group) for item in natives)
            continue

        if verified_flatpaks:
            final.extend(_with_source_options(item, group) for item in verified_flatpaks)
            continue

        if _host_prefers_native_appstream() and natives:
            final.extend(_with_source_options(item, group) for item in natives)
            continue

        preferred = _resolve_source_preference(group[0])
        chosen = [item for item in group if item.get("source", "native") == preferred]
        selected = chosen or group
        final.extend(_with_source_options(item, group) for item in selected)
    return final



_DISTRO_BADGES = (
    ("cachy", "cachyos.webp"),
    ("manjaro", "manjaro.webp"),
    ("ubuntu", "ubuntu.webp"),
    ("debian", "debian.webp"),
    ("rhel", "redhat.webp"),
    ("fedora", "fedora.webp"),
    ("suse", "opensuse.webp"),
    ("solus", "solus.webp"),
    ("arch", "arch.webp"),
)


def _native_distro_badge():
    """Return the LinuxToys distro badge selected from host compatibility keys."""
    compat_keys = get_system_compat_keys()
    for key, filename in _DISTRO_BADGES:
        if key in compat_keys:
            return f"distros/{filename}"
    return ""


def _locale_candidates(lang_code):
    """Return AppStream locale keys in LinuxToys preference order."""
    code = str(lang_code or "en").strip().replace("_", "-")
    if not code:
        code = "en"
    language = code.split("-", 1)[0].lower()
    candidates = []
    for value in (code, code.replace("-", "_"), language):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def _has_localized_value(component, field, lang_code):
    """Return whether a field genuinely has content for the active language."""
    language = str(lang_code or "en").strip().replace("_", "-").split("-", 1)[0].lower()
    if language == "en":
        return bool(component.get("summary", ""))

    values = component.get(field)
    if not isinstance(values, dict):
        return False
    normalized = {
        str(key).replace("_", "-").casefold(): value
        for key, value in values.items()
        if value
    }
    return any(
        bool(normalized.get(candidate.replace("_", "-").casefold()))
        for candidate in _locale_candidates(lang_code)
    )


def _localized_value(component, field, lang_code, fallback):
    values = component.get(field)
    if not isinstance(values, dict):
        return fallback
    normalized = {
        str(key).replace("_", "-").casefold(): value
        for key, value in values.items()
        if value
    }
    for candidate in _locale_candidates(lang_code):
        value = normalized.get(candidate.replace("_", "-").casefold())
        if value:
            return value
    return values.get("", fallback) or fallback

def _to_repo_entry(component, category, lang_code):
    component_id = str(component["id"])
    packages = [str(package) for package in component.get("packages", ()) if package]
    name = _localized_value(component, "localized_names", lang_code, component.get("name", ""))
    summary = _localized_value(component, "localized_summaries", lang_code, component.get("summary", ""))
    developer = _localized_value(component, "localized_developers", lang_code, component.get("developer", ""))
    long_description_blocks = _localized_value(
        component, "localized_descriptions", lang_code, component.get("description_blocks") or []
    )
    # Keep a plain fallback for older app-page consumers and page-presence checks.
    long_description = "\n\n".join(
        " ".join(span.get("text", "") for span in block.get("spans", ())).strip()
        if block.get("type") == "paragraph"
        else "\n".join(
            " ".join(span.get("text", "") for span in item).strip()
            for item in block.get("items", ())
        )
        for block in long_description_blocks
    ).strip()
    screenshots = [str(path) for path in component.get("screenshots", ()) if path]
    origin = str(component.get("origin", "") or "").strip()
    source = str(component.get("source", "native") or "native")
    is_flatpak = source == "flatpak"

    entry = {
        "id": component_id,
        "name": str(name),
        # Keep the catalog's canonical/default display name available for stable
        # pretty-name URI resolution even when LinuxToys is using a translation.
        "appstream_canonical_name": str(component.get("name", "") or name),
        "description": str(summary or ""),
        "description_tag": "",
        "description_localized": _has_localized_value(
            component, "localized_summaries", lang_code
        ),
        "long_description": long_description,
        "long_description_blocks": long_description_blocks,
        "long_description_tag": "",
        "long_description_format": "appstream",
        "screenshots": screenshots,
        "homepage_url": str(component.get("homepage", "") or ""),
        "donate": str(component.get("donation", "") or ""),
        "donate_url": str(component.get("donation", "") or ""),
        "license": str(component.get("license", "") or ""),
        "developer": str(developer or ""),
        "icon": str(component.get("icon", "") or "application-x-executable"),
        "category": category,
        "type": "flathub" if is_flatpak else "native",
        "package-name": component_id if is_flatpak else packages,
        "repo": origin or "appstream",
        "revert": "yes",
        "reboot": "no",
        "is_script": True,
        "is_subcategory": False,
        "is_repo_entry": True,
        "is_appstream_entry": True,
        "appstream_id": component_id,
        "appstream_source": source,
        "appstream_origin": origin,
        "flatpak_remote": str(component.get("flatpak_remote", "") or ""),
        "flatpak_scope": str(component.get("flatpak_scope", "") or ""),
        "flatpak_installation": str(component.get("flatpak_installation", "") or ""),
        # Native entries may inherit this from a discarded Flatpak duplicate.
        "popularity_metric": component.get("popularity_metric"),
        "repo_app_id": component_id,
        "is_new": False,
        # For AppStream entries this is specifically the publisher-verification
        # status supplied by Flathub. Native AppStream entries remain unverified.
        "is_verified": bool(is_flatpak and component.get("verified", False)),
        "native_distro_badge": "" if is_flatpak else _native_distro_badge(),
        "appstream_badge": "distros/flathub.webp" if is_flatpak else "",
        "has_app_page": bool(long_description or screenshots),
        "path": f"appstream://{source}/{component_id}",
    }

    alternatives = component.get("_source_alternatives") or ()
    if alternatives:
        source_options = [dict(entry)]
        for alternate in alternatives:
            try:
                option_category = category
                source_options.append(_to_repo_entry(alternate, option_category, lang_code))
            except (KeyError, TypeError, ValueError):
                continue
        if len(source_options) > 1:
            entry["source_options"] = source_options
            entry["recommended_source"] = str(
                component.get("_source_recommended", source) or source
            )

    return entry


def load_entries(scripts_dir, curated_entries=None, category_paths=None):
    """Return cached AppStream components as LinuxToys repository-like entries.

    This function never builds or refreshes AppStream metadata.  It only consumes
    the last atomically published catalog, keeping category parsing fast and safe.
    """
    scripts_dir = os.path.realpath(scripts_dir)
    try:
        catalog_mtime = appstream_cache.CATALOG_PATH.stat().st_mtime_ns
    except OSError:
        catalog_mtime = 0

    curated_entries = list(curated_entries or ())
    lang_code = detect_system_language()
    curated_signature = tuple(
        sorted(
            (
                str(entry.get("name", "")),
                str(entry.get("type", "")),
                repr(entry.get("package-name")),
                str(entry.get("appstream-id", entry.get("appstream_id", ""))),
            )
            for entry in curated_entries
        )
    )
    category_paths = tuple(sorted(str(path) for path in (category_paths or ())))
    cache_key = (scripts_dir, catalog_mtime, curated_signature, lang_code, category_paths)

    with _CACHE_LOCK:
        cached = _RUNTIME_CACHE.get(cache_key)
        if cached is not None:
            return [dict(entry) for entry in cached]

    curated_ids, curated_packages, curated_names = _curated_identity_sets(curated_entries)
    result = []

    for component in _prefer_sources(appstream_cache.load_catalog(), category_paths):
        if not isinstance(component, dict):
            continue
        if _is_curated(component, curated_ids, curated_packages, curated_names):
            continue

        category = _resolve_category(component.get("categories", ()), category_paths)
        if not category:
            continue

        packages = component.get("packages")
        if not isinstance(packages, list) or not packages:
            continue

        try:
            result.append(_to_repo_entry(component, category, lang_code))
        except (KeyError, TypeError, ValueError):
            continue

    result.sort(key=lambda entry: entry["name"].casefold())

    with _CACHE_LOCK:
        _RUNTIME_CACHE.clear()
        _RUNTIME_CACHE[cache_key] = result

    return [dict(entry) for entry in result]


def find_entry_by_id(scripts_dir, appstream_id, curated_entries=None, category_paths=None):
    """Return the already source-selected AppStream entry matching a component ID."""
    target = str(appstream_id or "").strip().casefold()
    if not target:
        return None

    for entry in load_entries(scripts_dir, curated_entries, category_paths):
        if str(entry.get("appstream_id", "") or "").strip().casefold() == target:
            return entry
    return None


def find_entry_by_name(scripts_dir, name, curated_entries=None, category_paths=None):
    """Resolve an exact AppStream pretty name after normal source selection.

    Both the localized LinuxToys display name and the canonical/default AppStream
    name are accepted. Matching is case-insensitive but deliberately not fuzzy.
    """
    target = str(name or "").strip().casefold()
    if not target:
        return None

    for entry in load_entries(scripts_dir, curated_entries, category_paths):
        names = (
            entry.get("name"),
            entry.get("appstream_canonical_name"),
        )
        if any(
            str(candidate or "").strip().casefold() == target
            for candidate in names
        ):
            return entry
    return None


def get_entries_for_category(
    scripts_dir,
    category_path,
    curated_entries=None,
    category_paths=None,
):
    try:
        category = os.path.relpath(
            os.path.realpath(category_path),
            os.path.realpath(scripts_dir),
        ).replace(os.sep, "/")
    except ValueError:
        return []

    if category == "." or category.startswith("../"):
        return []

    return [
        entry
        for entry in load_entries(scripts_dir, curated_entries, category_paths)
        if entry.get("category") == category
    ]
