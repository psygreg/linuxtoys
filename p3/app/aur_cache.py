"""Opt-in AUR metadata cache backed by catalog-rs."""
import os
import shutil
import subprocess
import threading
from pathlib import Path
from . import _catalog_rs, compat

CACHE_DIR = Path(os.path.expanduser("~/.cache/linuxtoys/aur"))
ARCHIVE_PATH = CACHE_DIR / "packages-meta-ext-v1.json.gz"
CATALOG_PATH = CACHE_DIR / "catalog.bin"
CONFIG_DIR = Path(os.path.expanduser("~/.config/linuxtoys"))
ENABLED_PATH = CONFIG_DIR / "aur-enabled"
_SCRIPT_DIR = CACHE_DIR / "scripts"
_LOCK = threading.RLock()
_CATALOG = None
_CATALOG_MTIME = None

# Developer-facing denylist for AUR packages that LinuxToys should not expose
# through the generic AUR browser/installer. Matching is case-insensitive and
# applies both to the package's exact Name and to normalized Provides entries.
# For example, omitting "foo" also hides a package with Provides=["foo=1.2"].
AUR_OMIT = {
    # "example-package",
}


def _native_repository_packages():
    """Return package names from pacman's enabled sync repositories.

    This is intentionally repository-native rather than AppStream-derived.
    appstream_resolver fixes misleading AppStream ownership at transaction time;
    querying pacman's sync databases here gives the AUR filter the authoritative
    package identities directly, in one subprocess, without bulk resolver calls.
    """
    pacman = shutil.which("pacman")
    if pacman is None:
        return []
    try:
        result = subprocess.run(
            [pacman, "-Slq"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return sorted({
        line.strip().casefold()
        for line in result.stdout.splitlines()
        if line.strip()
    })


def supported():
    """A shared opt-in/cache cannot enable AUR on an incompatible system."""
    keys = set(compat.get_system_compat_keys())
    return bool(keys.intersection({"arch", "cachy", "manjaro"})) and not keys.intersection(
        {"steamos", "dakota", "gnomeos", "kde-linux", "ostree", "ublue"}
    )


def enabled():
    return supported() and ENABLED_PATH.is_file()


def enable():
    if not supported():
        return False
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ENABLED_PATH.touch(exist_ok=True)
    return True


def refresh(force=False):
    if not enabled():
        return False
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # Rust keeps the currently published catalog.bin intact until the complete
    # replacement generation has been built successfully. Do not invalidate the
    # live Python catalog here: _catalog() switches generations lazily by binary
    # mtime, so readers can continue using stale metadata during the refresh.
    return bool(_catalog_rs.refresh_aur_archive(os.fspath(ARCHIVE_PATH), bool(force)))


def refresh_if_stale():
    if not enabled():
        return False
    if (
        not CATALOG_PATH.is_file()
        or not ARCHIVE_PATH.is_file()
        or not _catalog_rs.aur_cache_is_fresh(os.fspath(ARCHIVE_PATH))
    ):
        return refresh(False)
    return False


def _catalog():
    global _CATALOG, _CATALOG_MTIME
    if not enabled() or not CATALOG_PATH.is_file():
        return None
    try:
        appstream_path = CACHE_DIR.parent / "appstream/catalog.json"
        mtime = (CATALOG_PATH.stat().st_mtime_ns,
                 appstream_path.stat().st_mtime_ns if appstream_path.is_file() else None)
    except OSError:
        return None
    with _LOCK:
        if _CATALOG is not None and _CATALOG_MTIME == mtime:
            return _CATALOG
    catalog = _catalog_rs.load_aur_catalog(
        os.fspath(CATALOG_PATH),
        sorted(str(name).strip().casefold() for name in AUR_OMIT if str(name).strip()),
        _native_repository_packages(),
    )
    with _LOCK:
        _CATALOG = catalog
        _CATALOG_MTIME = mtime
    return catalog


def _materialize(entry):
    info = dict(entry)
    package = str(info.get("package-name") or "").strip()
    if not package:
        return None
    # Keep AUR browsing metadata-only. The runner materializes the tiny pkg_install
    # script only for the selected transaction, avoiding tens of thousands of files.
    info["path"] = f"aur://{package}"
    info["registry_name"] = f"AUR: {package}"
    info["recommended_source"] = "aur"
    return info


class AurEntriesView:
    """Lazy sequence over the Rust AUR catalog.

    Only slices requested by the GTK lazy card renderer are converted into Python
    dictionaries. The complete AUR catalog never exists as a Python list.
    """

    def __init__(self, catalog):
        self._catalog = catalog
        self._length = int(catalog.len())

    def __len__(self):
        return self._length

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(self._length)
            if step != 1:
                # This path is not used by the category renderer, but preserve
                # normal sequence semantics without materializing the full catalog.
                return [self[index] for index in range(start, stop, step)]
            if stop <= start:
                return []
            return [
                item
                for item in (
                    _materialize(x)
                    for x in self._catalog.browse(start, stop - start)
                )
                if item
            ]

        index = int(key)
        if index < 0:
            index += self._length
        if index < 0 or index >= self._length:
            raise IndexError(index)
        entries = self._catalog.browse(index, 1)
        if not entries:
            raise IndexError(index)
        item = _materialize(entries[0])
        if item is None:
            raise IndexError(index)
        return item


def browse_entries(limit=0, offset=0):
    catalog = _catalog()
    if catalog is None:
        return []
    limit = int(limit or 0)
    offset = max(0, int(offset or 0))
    if limit <= 0 and offset == 0:
        return AurEntriesView(catalog)
    return [
        item
        for item in (
            _materialize(x) for x in catalog.browse(offset, max(0, limit))
        )
        if item
    ]


def search_entries(query, limit=100):
    catalog = _catalog()
    if catalog is None:
        return []
    result = []
    for entry, score in catalog.search(str(query or ""), int(limit)):
        item = _materialize(entry)
        if item:
            result.append((item, int(score)))
    return result
