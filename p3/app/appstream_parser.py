"""Adapt cached AppStream components to LinuxToys repository-style entries."""

from __future__ import annotations

import os
import json
import re
import threading

from . import appstream_cache, repo_parser
from . import _catalog_rs as _catalog_rs
from .compat import get_system_compat_keys
from .lang_utils import detect_system_language


_CACHE_LOCK = threading.RLock()
_RUNTIME_CACHE = {}  # cache-key -> Rust AppStreamCatalog
_DERIVED_REFRESHING = set()

# Persistent acceleration cache for the final LinuxToys-ready AppStream entries.
# catalog.json remains authoritative; this file is disposable and regenerated
# whenever any input represented by the runtime cache key changes.
RUNTIME_CACHE_SCHEMA = 18
RUNTIME_CACHE_PATH = appstream_cache.CACHE_DIR / "runtime-entries-rs.bin"

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
        "org.kde.ghostwriter": {"all": "native"},
    },
}

# Developer-facing category override for AppStream entries whose upstream
# categories resolve to the wrong LinuxToys destination. Match by AppStream ID;
# a trailing .desktop is ignored and matching is case-insensitive.
#
# Values are LinuxToys category paths (for example "utils", "game/emu", etc.).
# The destination must exist in the active scripts tree.
APPSTREAM_CATEGORY_OVERRIDE = {
    "com.valvesoftware.Steam": "game",
}

# Developer-facing hard lock for applications that must use the system Flathub
# installation. Match by AppStream/Flatpak application ID; a trailing .desktop
# is ignored. The lock is applied only when a system-scope Flathub entry exists.
# When active, native and user-scope Flatpak alternatives are intentionally hidden.
SYSTEM_FLATPAK_ONLY = {
    "io.github.ilya_zlobintsev.LACT",
    "com.dec05eba.gpu_screen_recorder"
}

# Developer-facing denylist for AppStream applications that must not be offered
# through the generic AppStream installer. Use this when LinuxToys has (or needs)
# a dedicated installation procedure for an application. Match by AppStream ID,
# Flatpak application ID, or native package name. AppStream IDs ending in
# .desktop are normalized automatically. Matching is case-insensitive.
APPSTREAM_OMIT = {
    "virtualbox",
    "virt-manager",
    "org.virt_manager.virt-manager",
    "com.heroicgameslauncher.hgl"
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




















def _appstream_omit_keys():
    result = set()
    for value in APPSTREAM_OMIT:
        key = str(value or "").strip().casefold()
        if key.endswith(".desktop"):
            key = key[:-8]
        if key:
            result.add(key)
    return result




def _system_flatpak_lock_ids():
    result = set()
    for value in SYSTEM_FLATPAK_ONLY:
        component_id = str(value or "").strip().casefold()
        if component_id.endswith(".desktop"):
            component_id = component_id[:-8]
        if component_id:
            result.add(component_id)
    return result












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


def _runtime_catalog(scripts_dir, curated_entries=None, category_paths=None, *, force_rebuild=False):
    """Return the Rust-owned, indexed AppStream runtime catalog."""
    global _LAST_LOAD_CONTEXT

    scripts_dir = os.path.realpath(scripts_dir)
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
    appstream_overlays = repo_parser.load_appstream_overlays(scripts_dir)
    overlay_signature = tuple(sorted((key, repr(value)) for key, value in appstream_overlays.items()))
    lang_code = detect_system_language()
    curated_signature = tuple(sorted((
        str(entry.get("name", "")), str(entry.get("type", "")),
        repr(entry.get("package-name")),
        str(entry.get("appstream-id", entry.get("appstream_id", ""))),
    ) for entry in curated_entries))
    category_paths = tuple(sorted(str(path) for path in (category_paths or ())))
    cache_key = (
        tuple(sorted(_system_flatpak_lock_ids())),
        tuple(sorted(_appstream_omit_keys())),
        scripts_dir,
        catalog_mtime,
        curated_signature,
        overlay_signature,
        lang_code,
        category_paths,
    )
    if not force_rebuild:
        with _CACHE_LOCK:
            cached = _RUNTIME_CACHE.get(cache_key)
            if cached is not None:
                return cached

    curated_ids, curated_packages, curated_names = _curated_identity_sets(curated_entries)
    omit_keys = _appstream_omit_keys()
    category_config = {
        "main": MAIN_CATEGORY_CANDIDATES,
        "additional": ADDITIONAL_CATEGORY_CANDIDATES,
        "expressions": CATEGORY_EXPRESSION_RULES,
        "standalone_priority": STANDALONE_PURPOSE_PRIORITY,
        "main_priority": MAIN_CATEGORY_PRIORITY,
        "overrides": APPSTREAM_CATEGORY_OVERRIDE,
    }
    rust_cache_key = json.dumps({
        "schema": RUNTIME_CACHE_SCHEMA,
        "catalog_mtime": catalog_mtime,
        "omit": sorted(omit_keys),
        "category_paths": list(category_paths),
        "category_config": category_config,
        "source_preferences": APPSTREAM_SOURCE_PREFERENCE,
        "system_flatpak_locks": sorted(_system_flatpak_lock_ids()),
        "host_os_keys": sorted(_host_os_keys()),
        "compat_keys": sorted(get_system_compat_keys()),
        "language": lang_code,
        "curated_ids": sorted(curated_ids),
        "curated_packages": sorted(curated_packages),
        "curated_names": sorted(curated_names),
        "overlays": appstream_overlays,
        "native_badge": _native_distro_badge(),
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    catalog = _catalog_rs.build_appstream_catalog_index(
        os.fspath(appstream_cache.CATALOG_PATH), sorted(omit_keys), list(category_paths),
        json.dumps(category_config, ensure_ascii=False, separators=(",", ":")),
        json.dumps(APPSTREAM_SOURCE_PREFERENCE, ensure_ascii=False, separators=(",", ":")),
        sorted(_system_flatpak_lock_ids()), sorted(_host_os_keys()),
        sorted(get_system_compat_keys()), lang_code, sorted(curated_ids),
        sorted(curated_packages), sorted(curated_names),
        json.dumps(appstream_overlays, ensure_ascii=False, separators=(",", ":")),
        _native_distro_badge(), os.fspath(RUNTIME_CACHE_PATH), rust_cache_key,
        force_rebuild,
    )
    with _CACHE_LOCK:
        _RUNTIME_CACHE.clear()
        _RUNTIME_CACHE[cache_key] = catalog

    # A stale but complete binary generation is intentionally returned immediately.
    # Refresh it off-thread so startup/category/search callers never block on the
    # authoritative JSON rebuild merely because policy, locale, or catalog mtime
    # changed. The forced worker atomically publishes the replacement generation.
    if not force_rebuild and not catalog.cache_is_current(rust_cache_key):
        refresh_token = rust_cache_key
        with _CACHE_LOCK:
            should_start = refresh_token not in _DERIVED_REFRESHING
            if should_start:
                _DERIVED_REFRESHING.add(refresh_token)
        if should_start:
            def _refresh_stale_generation():
                try:
                    _runtime_catalog(
                        scripts_dir,
                        curated_entries=curated_entries,
                        category_paths=category_paths,
                        force_rebuild=True,
                    )
                finally:
                    with _CACHE_LOCK:
                        _DERIVED_REFRESHING.discard(refresh_token)

            threading.Thread(
                target=_refresh_stale_generation,
                name="linuxtoys-appstream-derived-cache",
                daemon=True,
            ).start()
    return catalog


def load_entries(scripts_dir, curated_entries=None, category_paths=None):
    """Compatibility API: materialize the complete Rust-owned catalog."""
    return list(_runtime_catalog(scripts_dir, curated_entries, category_paths).all_entries())

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

    # Keep the previous in-memory/binary generation available while this worker
    # builds the replacement. Rust writes the new binary cache to a temporary
    # file and atomically renames it only after the complete payload is synced.
    # _runtime_catalog() swaps the process cache only after that rebuild returns.
    try:
        _runtime_catalog(
            scripts_dir,
            curated_entries=curated_entries,
            category_paths=category_paths,
            force_rebuild=True,
        )
    except Exception:
        return False
    return True


def find_entry_by_id(scripts_dir, appstream_id, curated_entries=None, category_paths=None):
    """Return the already source-selected AppStream entry matching a component ID."""
    target = str(appstream_id or "").strip().casefold()
    if not target:
        return None

    return _runtime_catalog(scripts_dir, curated_entries, category_paths).find_by_id(target)


def find_entry_by_name(scripts_dir, name, curated_entries=None, category_paths=None):
    """Resolve an exact AppStream pretty name after normal source selection.

    Both the localized LinuxToys display name and the canonical/default AppStream
    name are accepted. Matching is case-insensitive but deliberately not fuzzy.
    """
    target = str(name or "").strip().casefold()
    if not target:
        return None

    return _runtime_catalog(scripts_dir, curated_entries, category_paths).find_by_name(target)


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

    return list(
        _runtime_catalog(scripts_dir, curated_entries, category_paths)
        .entries_for_category(category)
    )


def get_browse_entries_for_category(
    scripts_dir,
    category_path,
    structural_items,
    known_popular,
    curated_entries=None,
    category_paths=None,
):
    """Rank and materialize one complete browse category inside Rust.

    Only the comparatively small structural LinuxToys slice crosses into Rust;
    AppStream entries remain indexed/native until the final ordered result is
    materialized back to Python.
    """
    try:
        category = os.path.relpath(
            os.path.realpath(category_path),
            os.path.realpath(scripts_dir),
        ).replace(os.sep, "/")
    except ValueError:
        return list(structural_items or ())
    if category == "." or category.startswith("../"):
        return list(structural_items or ())
    return list(
        _runtime_catalog(scripts_dir, curated_entries, category_paths)
        .browse_entries_for_category(
            category,
            list(structural_items or ()),
            sorted({str(value) for value in (known_popular or ()) if str(value).strip()}),
        )
    )

def search_entries(scripts_dir, query, translated_new="new", translated_official="official", curated_entries=None, category_paths=None):
    """Search AppStream inside Rust and materialize only matching entries."""
    return list(
        _runtime_catalog(scripts_dir, curated_entries, category_paths)
        .search(str(query or ""), str(translated_new or ""), str(translated_official or ""))
    )


def get_featured_descriptors(scripts_dir, curated_entries=None, category_paths=None):
    """Return lightweight review-eligible Featured metadata without decoding payloads."""
    return list(
        _runtime_catalog(scripts_dir, curated_entries, category_paths)
        .featured_descriptors()
    )


def materialize_featured_entries(scripts_dir, indices, curated_entries=None, category_paths=None):
    """Decode only selected AppStream Featured payloads."""
    clean_indices = sorted({
        int(index) for index in (indices or ())
        if isinstance(index, int) or str(index).isdigit()
    })
    if not clean_indices:
        return []
    return list(
        _runtime_catalog(scripts_dir, curated_entries, category_paths)
        .materialize_featured(clean_indices)
    )



def get_installed_entries(
    scripts_dir,
    native_packages,
    flatpak_ids,
    executed_names=(),
    curated_entries=None,
    category_paths=None,
):
    """Materialize only AppStream entries matching observed/Registry installs."""
    return list(
        _runtime_catalog(scripts_dir, curated_entries, category_paths).installed_entries(
            sorted({str(value) for value in (native_packages or ()) if str(value).strip()}),
            sorted({str(value) for value in (flatpak_ids or ()) if str(value).strip()}),
            sorted({str(value) for value in (executed_names or ()) if str(value).strip()}),
        )
    )
