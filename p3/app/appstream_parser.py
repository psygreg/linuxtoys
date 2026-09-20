"""Adapt cached AppStream components to LinuxToys repository-style entries."""

from __future__ import annotations

import os
import pickle
import re
import threading

from . import appstream_cache
from .compat import get_system_compat_keys
from .lang_utils import detect_system_language


_CACHE_LOCK = threading.RLock()
_RUNTIME_CACHE = {}

# Persistent acceleration cache for the final LinuxToys-ready AppStream entries.
# catalog.json remains authoritative; this file is disposable and regenerated
# whenever any input represented by the runtime cache key changes.
RUNTIME_CACHE_SCHEMA = 4
RUNTIME_CACHE_PATH = appstream_cache.CACHE_DIR / "runtime-entries.pickle"

# Most recent inputs used to build the live runtime catalog. This is process-local
# only; it lets the AppStream refresh worker prewarm a newly published catalog
# before GTK is told to switch to it.
_LAST_LOAD_CONTEXT = None


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

# Developer-facing hard lock for applications that must use the system Flathub
# installation. Match by AppStream/Flatpak application ID; a trailing .desktop
# is ignored. The lock is applied only when a system-scope Flathub entry exists.
# When active, native and user-scope Flatpak alternatives are intentionally hidden.
SYSTEM_FLATPAK_ONLY = {
    # "org.example.App",
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

# AppStream categories are tags rather than a strict taxonomy.  Following the
# same basic model used by GNOME Software, LinuxToys resolves meaningful
# Main+Additional expressions before falling back to a broad Main category.
# LinuxToys still chooses one destination, so rules are ordered: first match wins.
#
# A few cross-main overrides come first for cases where the functional tag is more
# informative than the broad main tag (CAD/engineering is the canonical example).
CATEGORY_EXPRESSION_RULES = (
    # Cross-main semantic overrides.
    (("Engineering", "3DGraphics"), ("eng", "utilities")),
    (("Engineering", "2DGraphics"), ("eng", "utilities")),
    (("Engineering", "VectorGraphics"), ("eng", "utilities")),
    (("Engineering", "Graphics"), ("eng", "utilities")),
    (("Electronics", "Graphics"), ("eng", "utilities")),
    (("Development", "Database"), ("devs", "development")),
    (("Development", "Engineering"), ("eng", "devs", "development")),
    (("Development", "Electronics"), ("eng", "devs", "development")),

    # Development.
    (("Development", "IDE"), ("ides", "development")),
    (("Development", "GUIDesigner"), ("ides", "development")),
    (("Development", "Building"), ("tools", "development")),
    (("Development", "Debugger"), ("tools", "development")),
    (("Development", "Profiling"), ("tools", "development")),
    (("Development", "RevisionControl"), ("tools", "development")),
    (("Development", "Translation"), ("tools", "development")),
    (("Development", "WebDevelopment"), ("devs", "development")),

    # Office / productivity.
    (("Office", "Calendar"), ("planning", "productivity")),
    (("Office", "ContactManagement"), ("chat", "productivity")),
    (("Office", "Database"), ("planning", "productivity")),
    (("Office", "Chart"), ("planning", "productivity")),
    (("Office", "Finance"), ("fin", "productivity")),
    (("Office", "FlowChart"), ("planning", "productivity")),
    (("Office", "PDA"), ("planning", "productivity")),
    (("Office", "ProjectManagement"), ("planning", "productivity")),
    (("Office", "Presentation"), ("document", "productivity")),
    (("Office", "Spreadsheet"), ("document", "productivity")),
    (("Office", "WordProcessor"), ("document", "productivity")),

    # Graphics. Engineering overrides above deliberately beat 3D graphics.
    (("Graphics", "Photography"), ("photo", "graphics", "office")),
    (("Graphics", "ImageProcessing"), ("photo", "graphics", "office")),
    (("Graphics", "2DGraphics"), ("draw", "graphics", "office")),
    (("Graphics", "VectorGraphics"), ("draw", "graphics", "office")),
    (("Graphics", "RasterGraphics"), ("draw", "graphics", "office")),
    (("Graphics", "3DGraphics"), ("creative", "graphics", "office")),
    (("Graphics", "Scanning"), ("document", "graphics", "office")),
    (("Graphics", "OCR"), ("creative", "graphics", "office")),
    (("Graphics", "Publishing"), ("creative", "graphics", "office")),
    (("Graphics", "Viewer"), ("viewer", "graphics", "office")),

    # Settings / system.
    (("Settings", "DesktopSettings"), ("sysadm", "system", "utils")),
    (("Settings", "HardwareSettings"), ("sysadm", "system", "utils")),
    (("Settings", "Printing"), ("document", "system", "utils")),
    (("Settings", "PackageManager"), ("sysadm", "system", "utils")),
    (("System", "PackageManager"), ("sysadm", "system", "utils")),
    (("System", "FileManager"), ("sysadm", "system", "utils")),
    (("System", "FileTools"), ("sysadm", "system", "utils")),
    (("System", "TerminalEmulator"), ("sys", "system", "utils")),
    (("System", "Filesystem"), ("sys", "system", "utils")),
    (("System", "Monitor"), ("sec", "system", "network", "utils")),
    (("System", "Security"), ("sec", "system", "utils")),
    (("System", "Emulator"), ("emu", "system", "game", "games")),

    # Network / communication.
    (("Network", "WebBrowser"), ("browsers", "utils")),
    (("Network", "InstantMessaging"), ("chat", "utils")),
    (("Network", "Chat"), ("chat", "utils")),
    (("Network", "IRCClient"), ("chat", "utils")),
    (("Network", "Email"), ("chat", "network", "productivity")),
    (("Network", "VideoConference"), ("chat", "utils")),
    (("Network", "RemoteAccess"), ("remote", "utils")),
    (("Network", "P2P"), ("p2p", "utils")),
    (("Network", "FileTransfer"), ("p2p", "utils")),
    (("Network", "Feed"), ("network", "utils")),
    (("Network", "News"), ("network", "utils")),
    (("Network", "Dialup"), ("network", "utils")),
    (("Network", "Telephony"), ("network", "utils")),
    (("Network", "TelephonyTools"), ("network", "utilities")),
    (("Network", "WebDevelopment"), ("devs", "development", "network")),

    # Audio / video.
    (("Audio", "Midi"), ("audio", "multimedia", "media")),
    (("Audio", "Mixer"), ("audio", "multimedia", "media")),
    (("Audio", "Sequencer"), ("audio", "multimedia", "media")),
    (("Audio", "Tuner"), ("tv", "audio", "multimedia", "media")),
    (("Video", "TV"), ("tv", "video", "multimedia", "media")),
    (("AudioVideo", "AudioVideoEditing"), ("video", "multimedia", "office")),
    (("AudioVideo", "Player"), ("players", "multimedia", "office")),
    (("AudioVideo", "Recorder"), ("rec", "multimedia", "office")),
    (("AudioVideo", "DiscBurning"), ("rec", "multimedia")),

    # Games.
    (("Game", "ActionGame"), ("action", "games")),
    (("Game", "AdventureGame"), ("action", "games")),
    (("Game", "ArcadeGame"), ("classic", "games")),
    (("Game", "BoardGame"), ("classic", "games")),
    (("Game", "BlocksGame"), ("kids", "games")),
    (("Game", "CardGame"), ("classic", "games")),
    (("Game", "KidsGame"), ("kids", "games")),
    (("Game", "LogicGame"), ("kids", "games")),
    (("Game", "RolePlaying"), ("sim", "games")),
    (("Game", "Shooter"), ("action", "games")),
    (("Game", "Simulation"), ("sim", "games")),
    (("Game", "SportsGame"), ("sports", "games")),
    (("Game", "StrategyGame"), ("strategy", "games")),

    # Education / science. Accept either main tag where the desktop spec allows
    # the subject to appear in both contexts.
    (("Education", "Languages"), ("langs", "science", "education")),
    (("Education", "Literature"), ("langs", "science", "education")),
    (("Education", "Astronomy"), ("nature", "science", "education")),
    (("Education", "Biology"), ("nature", "science", "education")),
    (("Education", "Chemistry"), ("nature", "science", "education")),
    (("Education", "Geography"), ("geo", "science", "education")),
    (("Education", "Math"), ("math", "science", "education")),
    (("Education", "NumericalAnalysis"), ("math", "science", "education")),
    (("Science", "ArtificialIntelligence"), ("tech", "science", "education")),
    (("Science", "Astronomy"), ("nature", "science", "education")),
    (("Science", "Biology"), ("nature", "science", "education")),
    (("Science", "Chemistry"), ("nature", "science", "education")),
    (("Science", "ComputerScience"), ("tech", "science", "education")),
    (("Science", "DataVisualization"), ("tech", "science", "education")),
    (("Science", "Economy"), ("math", "science", "education")),
    (("Science", "Electricity"), ("tech", "science", "education")),
    (("Science", "Geography"), ("geo", "science", "education")),
    (("Science", "Geology"), ("nature", "science", "education")),
    (("Science", "Geoscience"), ("nature", "science", "education")),
    (("Science", "ImageProcessing"), ("photo", "science", "education")),
    (("Science", "Maps"), ("geo", "science", "education", "utils")),
    (("Science", "Math"), ("math", "science", "education")),
    (("Science", "NumericalAnalysis"), ("math", "science", "education")),
    (("Science", "MedicalSoftware"), ("health", "science", "education")),
    (("Science", "Physics"), ("math", "science", "education")),
    (("Science", "Robotics"), ("tech", "science", "education")),
    (("Science", "ParallelComputing"), ("tech", "science", "education")),

    # Utility expressions. Implementation/toolkit hints (KDE, GNOME, GTK, Qt,
    # Java, etc.) are intentionally absent: they describe how an app is built,
    # not what the app is for.
    (("Utility", "Archiving"), ("archive", "utilities")),
    (("Utility", "Compression"), ("archive", "utilities")),
    (("Utility", "Engineering"), ("eng", "utilities")),
    (("Utility", "Electronics"), ("eng", "utilities")),
    (("Utility", "Accessibility"), ("accessibility", "utils")),
    (("Utility", "Calculator"), ("fin", "utilities")),
    (("Utility", "TextEditor"), ("txt", "utilities")),
    (("Utility", "TextTools"), ("document", "utilities")),
)

# A deliberately small escape hatch for useful purpose tags found in imperfect
# metadata without a suitable Main category.  Unlike the old Additional-category
# table, these do not include capability or implementation hints.
STANDALONE_PURPOSE_PRIORITY = (
    "Engineering", "Electronics", "MedicalSoftware", "PackageManager",
    "TerminalEmulator", "FileManager", "WebBrowser", "RemoteAccess",
    "IDE", "GUIDesigner", "ProjectManagement", "Finance", "Photography",
    "TextEditor", "Accessibility", "Archiving", "Compression",
)


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


def _first_existing_category(candidates, exact, by_name):
    """Return the first LinuxToys category candidate present in the indexed tree."""
    for candidate in candidates:
        candidate = str(candidate).replace(os.sep, "/").strip("/")
        if candidate in exact:
            return candidate
        matches = by_name.get(candidate)
        if matches:
            return matches[0]
    return None


def _resolve_category(appstream_categories, category_paths):
    """Resolve AppStream's tag set into one semantic LinuxToys category.

    AppStream categories are non-hierarchical tags.  Match curated Main+Additional
    expressions first, then a small set of safe standalone purpose tags, and
    finally broad Main-category fallbacks.
    """
    categories = set(appstream_categories or ())
    exact, by_name = _category_path_lookup(category_paths)

    # Contextual expressions prevent a capability tag from becoming a global
    # classification rule. For example, Graphics+3DGraphics is creative work,
    # while Engineering+3DGraphics is classified as engineering/CAD.
    for required, candidates in CATEGORY_EXPRESSION_RULES:
        if set(required).issubset(categories):
            resolved = _first_existing_category(candidates, exact, by_name)
            if resolved:
                return resolved

    # Some real-world metadata omits the expected Main category. Keep only a
    # conservative set of purpose-like Additional categories as a recovery path.
    for appstream_category in STANDALONE_PURPOSE_PRIORITY:
        if appstream_category not in categories:
            continue
        resolved = _first_existing_category(
            ADDITIONAL_CATEGORY_CANDIDATES[appstream_category], exact, by_name
        )
        if resolved:
            return resolved

    # Broad Main categories are the authoritative fallback.
    for appstream_category in MAIN_CATEGORY_PRIORITY:
        if appstream_category not in categories:
            continue
        resolved = _first_existing_category(
            MAIN_CATEGORY_CANDIDATES[appstream_category], exact, by_name
        )
        if resolved:
            return resolved

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
    """Arch Linux, CachyOS, and Solus prefer native packages over ordinary Flathub."""
    compat_keys = get_system_compat_keys()
    return bool({"arch", "cachy", "solus"} & compat_keys)


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


def _normalized_component_id(component):
    component_id = str(component.get("id", "") or "").strip().casefold()
    if component_id.endswith(".desktop"):
        component_id = component_id[:-8]
    return component_id


def _system_flatpak_lock_ids():
    result = set()
    for value in SYSTEM_FLATPAK_ONLY:
        component_id = str(value or "").strip().casefold()
        if component_id.endswith(".desktop"):
            component_id = component_id[:-8]
        if component_id:
            result.add(component_id)
    return result


def _locked_system_flatpak(group):
    """Return the forced system Flathub candidate for this group, when available."""
    locked_ids = _system_flatpak_lock_ids()
    if not locked_ids:
        return None
    candidates = [
        item for item in group
        if item.get("source") == "flatpak"
        and str(item.get("flatpak_scope", "") or "") == "system"
        and _normalized_component_id(item) in locked_ids
    ]
    if not candidates:
        return None
    # Prefer Flatpak's default system installation over additional named ones.
    candidates.sort(
        key=lambda item: (
            str(item.get("flatpak_installation", "") or "") != "default",
            str(item.get("flatpak_installation", "") or ""),
        )
    )
    selected = dict(candidates[0])
    selected.pop("_source_alternatives", None)
    selected.pop("_source_recommended", None)
    return selected


def _source_option_key(item):
    """Return a stable key that distinguishes Flatpak installation scopes."""
    source = str(item.get("source", "native") or "native")
    if source != "flatpak":
        return source
    scope = str(item.get("flatpak_scope", "") or "")
    installation = str(item.get("flatpak_installation", "") or "")
    return f"flatpak:{scope}:{installation}"


def _expand_source_group(group):
    """Restore source alternatives nested by an earlier duplicate-collapse pass."""
    expanded = []
    seen = set()
    for item in group:
        candidates = [item]
        candidates.extend(
            alternate for alternate in item.get("_source_alternatives", ())
            if isinstance(alternate, dict)
        )
        for candidate in candidates:
            key = _source_option_key(candidate)
            if key in seen:
                continue
            seen.add(key)
            # Nested alternatives belong to the collapsed parent, not the option
            # itself. Rebuild them from the complete group below.
            candidate = dict(candidate)
            candidate.pop("_source_alternatives", None)
            candidate.pop("_source_recommended", None)
            expanded.append(candidate)
    return expanded


def _with_source_options(selected, group):
    """Preserve useful native and Flatpak-scope installation alternatives."""
    flatpaks = [item for item in group if item.get("source") == "flatpak"]
    natives = [item for item in group if item.get("source", "native") == "native"]
    selected_key = _source_option_key(selected)

    # Multiple configured Flathub scopes are independently useful even for
    # verified apps. Native remains hidden for verified Flathub applications.
    selected_verified_flatpak = _is_verified_flatpak(selected)
    candidates = list(flatpaks)
    if not selected_verified_flatpak:
        candidates = natives + candidates

    # A selector is useful for either native-vs-Flatpak choice or Flatpak scope.
    unique = []
    seen = set()
    for item in candidates:
        key = _source_option_key(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    if len(unique) < 2:
        return selected

    result = dict(selected)
    alternatives = [dict(item) for item in unique if _source_option_key(item) != selected_key]
    if alternatives:
        result["_source_alternatives"] = alternatives
        result["_source_recommended"] = selected_key
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
        locked = _locked_system_flatpak(group)
        if locked is not None:
            result.append(locked)
            continue

        # The same Flatpak remote can exist at user and system scope. Present one
        # app, preferring user scope because pkg_flat follows the same policy.
        flatpaks = [item for item in group if item.get("source") == "flatpak"]
        natives = [item for item in group if item.get("source", "native") == "native"]
        if flatpaks:
            # User Flathub is the default Flatpak installation when available, but
            # retain system installations so the app page can expose scope choice.
            flatpaks.sort(key=lambda item: (item.get("flatpak_scope") != "user", item.get("flatpak_installation", "")))
        group = natives + flatpaks
        if not natives and len(flatpaks) > 1:
            result.append(_with_source_options(flatpaks[0], group))
            continue
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
            result.append(_with_source_options(verified_flatpaks[0], group))
            continue

        if _host_prefers_native_appstream() and natives:
            result.extend(_with_source_options(item, group) for item in natives)
            continue

        preferred = _resolve_source_preference(group[0])
        chosen = [item for item in group if item.get("source", "native") == preferred]
        selected = chosen or group
        if selected and selected[0].get("source") == "flatpak":
            selected = selected[:1]
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
        # Exact-ID collapsing may already have nested the other Flatpak scope in
        # _source_alternatives. Expand it again before the conservative name pass
        # so combining that Flatpak entry with a differently-IDed native package
        # does not silently discard the system/user scope alternative.
        group = _expand_source_group(group)
        locked = _locked_system_flatpak(group)
        if locked is not None:
            final.append(locked)
            continue

        flatpaks = [item for item in group if item.get("source") == "flatpak"]
        natives = [item for item in group if item.get("source", "native") == "native"]
        flatpaks.sort(key=lambda item: (item.get("flatpak_scope") != "user", item.get("flatpak_installation", "")))

        # Scope alternatives are still meaningful when every candidate is Flatpak.
        # Handle that before the source-kind early exit, otherwise expanding a
        # previously collapsed user/system pair turns it back into two independent
        # app entries and loses the selector.
        if not natives and len(flatpaks) > 1:
            final.append(_with_source_options(flatpaks[0], flatpaks))
            continue

        sources = {str(item.get("source", "native")) for item in group}
        if len(sources) < 2:
            final.extend(group)
            continue

        verified_flatpaks = [item for item in flatpaks if _is_verified_flatpak(item)]

        if natives and _group_prefers_native_development(group, category_paths):
            _inherit_flatpak_popularity(natives, flatpaks)
            final.extend(_with_source_options(item, group) for item in natives)
            continue

        if verified_flatpaks:
            final.append(_with_source_options(verified_flatpaks[0], group))
            continue

        if _host_prefers_native_appstream() and natives:
            final.extend(_with_source_options(item, group) for item in natives)
            continue

        preferred = _resolve_source_preference(group[0])
        chosen = [item for item in group if item.get("source", "native") == preferred]
        selected = chosen or group
        if selected and selected[0].get("source") == "flatpak":
            selected = selected[:1]
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
    # AppStream cache schema 15 stores each logical screenshot as a mapping
    # containing its available image variants.  Preserve that structure for the
    # app page instead of stringifying the mapping (which turns it into an
    # unusable path such as "{\'images\': [...]}" ).  Legacy string screenshots
    # remain supported for curated/older entries.
    screenshots = []
    for screenshot in component.get("screenshots", ()):
        if isinstance(screenshot, dict):
            variants = []
            for image in screenshot.get("images") or ():
                if not isinstance(image, dict):
                    continue
                url = str(image.get("url", "") or "").strip()
                if not url:
                    continue
                try:
                    width = max(0, int(image.get("width", 0) or 0))
                    height = max(0, int(image.get("height", 0) or 0))
                except (TypeError, ValueError):
                    width = height = 0
                variants.append({"url": url, "width": width, "height": height})
            if variants:
                screenshots.append({"images": variants})
        else:
            path = str(screenshot or "").strip()
            if path:
                screenshots.append(path)
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
        "package-name": packages[0] if is_flatpak and packages else component_id if is_flatpak else packages,
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
        # Generic repo materialization maps this existing override to
        # pkg_flat --skip-user, forcing the system Flatpak installation.
        "overrides": ({"skip-user": True} if is_flatpak and str(component.get("flatpak_scope", "") or "") == "system" else {}),
        # Native entries may inherit this from a discarded Flatpak duplicate.
        "popularity_metric": component.get("popularity_metric"),
        "review_rating": component.get("review_rating"),
        "review_count": component.get("review_count"),
        "appstream_version": str(component.get("version", "") or ""),
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
                component.get("_source_recommended", _source_option_key(component))
                or _source_option_key(component)
            )

    return entry



def _persistent_runtime_cache_key(
    scripts_dir,
    catalog_mtime,
    curated_signature,
    lang_code,
    category_paths,
):
    """Return a stable, pickle-friendly key for the derived runtime cache."""
    return (
        RUNTIME_CACHE_SCHEMA,
        tuple(sorted(_system_flatpak_lock_ids())),
        scripts_dir,
        int(catalog_mtime),
        curated_signature,
        lang_code,
        category_paths,
    )


def _load_persistent_runtime_cache(cache_key):
    """Load final adapted entries when the on-disk cache matches this invocation.

    The cache is derived/disposable. Any read, format, schema, or key mismatch is
    treated as a normal cache miss and falls back to catalog.json.
    """
    try:
        with open(RUNTIME_CACHE_PATH, "rb") as handle:
            payload = pickle.load(handle)
    except (OSError, EOFError, pickle.PickleError, AttributeError, ValueError, TypeError):
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("schema") != RUNTIME_CACHE_SCHEMA:
        return None
    if payload.get("key") != cache_key:
        return None

    entries = payload.get("entries")
    if not isinstance(entries, list):
        return None
    if not all(isinstance(entry, dict) for entry in entries):
        return None
    return entries


def _write_persistent_runtime_cache(cache_key, entries):
    """Atomically publish the final adapted entries as a disposable pickle cache."""
    try:
        RUNTIME_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = RUNTIME_CACHE_PATH.with_name(RUNTIME_CACHE_PATH.name + ".tmp")
        payload = {
            "schema": RUNTIME_CACHE_SCHEMA,
            "key": cache_key,
            "entries": entries,
        }
        with open(tmp, "wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, RUNTIME_CACHE_PATH)
    except (OSError, pickle.PickleError, AttributeError, TypeError, ValueError):
        try:
            tmp.unlink()
        except (OSError, UnboundLocalError):
            pass


def load_entries(scripts_dir, curated_entries=None, category_paths=None):
    """Return cached AppStream components as LinuxToys repository-like entries.

    This function never builds or refreshes AppStream metadata.  It only consumes
    the last atomically published catalog, keeping category parsing fast and safe.
    """
    global _LAST_LOAD_CONTEXT

    scripts_dir = os.path.realpath(scripts_dir)
    # Snapshot the actual parser inputs, not merely their derived signature. A
    # catalog refresh can then rebuild the persistent cache off the GTK thread.
    _LAST_LOAD_CONTEXT = (
        scripts_dir,
        [dict(entry) for entry in (curated_entries or ())],
        tuple(str(path) for path in (category_paths or ())),
    )
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
    cache_key = (
        tuple(sorted(_system_flatpak_lock_ids())),
        scripts_dir,
        catalog_mtime,
        curated_signature,
        lang_code,
        category_paths,
    )

    with _CACHE_LOCK:
        cached = _RUNTIME_CACHE.get(cache_key)
        if cached is not None:
            return [dict(entry) for entry in cached]

    persistent_key = _persistent_runtime_cache_key(
        scripts_dir,
        catalog_mtime,
        curated_signature,
        lang_code,
        category_paths,
    )
    persistent = _load_persistent_runtime_cache(persistent_key)
    if persistent is not None:
        with _CACHE_LOCK:
            _RUNTIME_CACHE.clear()
            _RUNTIME_CACHE[cache_key] = persistent
        return [dict(entry) for entry in persistent]

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

    _write_persistent_runtime_cache(persistent_key, result)
    return [dict(entry) for entry in result]



def prepare_runtime_cache():
    """Prebuild the derived cache for the currently published AppStream catalog.

    Intended for the AppStream refresh worker after catalog.json has been
    atomically replaced and before GTK is notified. The UI can keep using its
    existing in-memory entries while this runs.

    Returns True when a live parser context was available and the new catalog was
    successfully adapted/cached, otherwise False.
    """
    with _CACHE_LOCK:
        context = _LAST_LOAD_CONTEXT

    if context is None:
        return False

    scripts_dir, curated_entries, category_paths = context

    # catalog.json has a new mtime after publication, so clearing the process
    # cache guarantees load_entries() adapts that new catalog and atomically
    # replaces runtime-entries.pickle before the UI refresh is scheduled.
    clear_runtime_cache()
    try:
        load_entries(
            scripts_dir,
            curated_entries=curated_entries,
            category_paths=category_paths,
        )
    except Exception:
        return False
    return True


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
