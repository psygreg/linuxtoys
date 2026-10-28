import os
import re
import threading
from collections.abc import Mapping
from enum import Enum, auto
from typing import Any

from app import appstream_cache
from app.lang_utils import load_translations
from app.search_helper import (
    CategoryCache,
    ScriptCache,
    SearchEngine,
    create_search_engine,
)

translations = load_translations()

_category_cache: CategoryCache | None = None
_script_cache: ScriptCache | None = None
_search_engine: SearchEngine | None = None
_cache_lock = threading.Lock()
SPECIALS_PREFIX = "specials://"
SPECIALS_ROOT = "specials://root"
HOMEBREW_PREFIX = "homebrew://"
APPIMAGE_PREFIX = "appimages://"
APPIMAGE_ROOT = "appimages://root"


def make_widget_id(identifier: str) -> str:
    """Build a valid, stable Textual widget id from an identifier.

    Characters outside ``[a-zA-Z0-9_-]`` become ``_``. If the result
    is empty or does not start with a letter or underscore (a Textual
    requirement), the ``id_`` prefix is added.

    Pass only language-independent keys such as script paths. Never
    pass translated text, or the id changes with the UI language.

    Args:
        identifier: Stable unique key of the widget.

    Returns:
        A valid widget id.
    """
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", identifier)
    # Textual exige que o id comece com letra ou underscore
    if not slug or not (slug[0].isalpha() or slug[0] == "_"):
        slug = f"id_{slug}"
    return slug


def is_search_ready() -> bool:
    return _search_engine is not None and _category_cache is not None


def is_registered_entry(info: Mapping[str, Any], registry_data) -> bool:
    candidates = (
        info.get("registry_name"),
        info.get("appstream_id"),
        info.get("name"),
        info.get("appstream_canonical_name"),
    )
    return any(
        str(candidate).strip() in registry_data
        for candidate in candidates
        if candidate
    )


def is_removable(
    script_name: str,
    script_path: str,
    is_repo_entry: bool,
    is_appstream_entry: bool,
    is_script: bool = True,
    info: dict | None = None,
) -> bool:
    script_cache = _script_cache
    if script_cache is None:
        return False

    script_info = dict(info or {})
    script_info.update(
        name=script_name,
        path=script_path,
        is_script=is_script,
        is_repo_entry=is_repo_entry,
        is_appstream_entry=is_appstream_entry,
    )
    return script_cache.is_script_removable(script_info)


def invalidate_search_caches() -> None:
    """Invalidates cached search and category structures."""
    global _category_cache, _script_cache, _search_engine
    with _cache_lock:
        _category_cache = None
        _script_cache = None
        _search_engine = None


def warm_search_and_category_index(trans=None) -> SearchEngine:
    """Populates CategoryCache concurrently, links ScriptCache in memory,
    and warms the Rust SearchIndex. Thread-safe and reusable.

    Deliberately local-only: the AppStream catalog build stays off this
    path so callers can show the interface first and schedule the catalog
    refresh on a background worker afterwards, mirroring the GUI launch
    sequence.
    """
    global _category_cache, _script_cache, _search_engine
    active_translations = trans or translations

    with _cache_lock:
        if _search_engine is not None:
            return _search_engine

        # 1. Parse categories concurrently (ThreadPoolExecutor)
        cat_cache = CategoryCache()
        cat_cache.populate(active_translations, max_workers=4)

        # 2. Build script cache directly from category data without re-reading the filesystem
        scr_cache = ScriptCache()
        scr_cache.populate_from_category_cache(cat_cache)

        # 3. Create SearchEngine and warm the Rust index
        engine = create_search_engine(active_translations, scr_cache)
        engine._ensure_rust_search_index()

        _category_cache = cat_cache
        _script_cache = scr_cache
        _search_engine = engine

        return _search_engine


def get_scripts_for_category_cached(category_path: str) -> list[dict]:
    """Retrieves scripts from the warmed CategoryCache if available,
    falling back to parser only if not yet populated.
    """
    if _category_cache is not None and _category_cache.is_populated:
        return _category_cache.get_scripts_for_category(category_path)
    from app.parser import get_scripts_for_category

    return get_scripts_for_category(category_path, translations=translations)


def search_scripts_fast(query: str) -> list[dict]:
    """Fast search leveraging the pre-warmed Rust index."""
    if not query.strip() or _search_engine is None:
        return []

    groups = _search_engine.search(query.strip())
    # Flatten items or return grouped
    return [
        result.item_info for group in groups for result in group["scripts"]
    ]


def refresh_removable_state() -> None:
    """Recompute the cached removable state after install/removal.

    Does nothing if the caches are not warm.
    """
    script_cache = _script_cache
    if script_cache is not None:
        script_cache.refresh_removable_cache()


def get_categories(trans=None) -> list[dict]:
    """Retrieves top-level categories.
    Returns from CategoryCache if populated, otherwise falls back to parser.
    """
    if _category_cache is not None and _category_cache.is_populated:
        return _category_cache.get_categories()
    from app.parser import get_categories as parser_get_categories

    return parser_get_categories(translations=trans or translations)


def is_specials_path(path: str) -> bool:
    return path.startswith(SPECIALS_PREFIX)


def is_homebrew_path(path: str) -> bool:
    return path.startswith(HOMEBREW_PREFIX)


def is_appimage_path(path: str) -> bool:
    return path.startswith(APPIMAGE_PREFIX)


def get_specials_items(path: str, trans=None) -> list[dict]:
    """Resolve a virtual ``specials://`` path into items to render.
    - ``specials://root``: the curated categories.
    - ``specials://category/{name}``: the curated scripts of the
      category with that name.

    Args:
        path: Virtual path to resolve.
        trans: Translations mapping. Defaults to ``translations``.

    Returns:
        Item dicts. Empty if the cache is not populated or ``path``
        matches no category.
    """
    cache = _category_cache
    if cache is None or not cache.is_populated:
        return []

    active_translations = trans or translations
    categories = cache.get_linuxtoys_special_categories(active_translations)

    if path == SPECIALS_ROOT:
        return categories

    for category in categories:
        if category["path"] == path:
            return cache.get_linuxtoys_special_scripts(
                category["specials_category_path"]
            )

    return []


def is_homebrew_catalog_valid() -> bool:
    """Return whether the Homebrew catalog is ready to use.

    True only if Homebrew is enabled, its source is marked complete,
    a binary snapshot exists and the stored fingerprint matches the
    current one (the snapshot is up to date).
    """
    from app import homebrew_catalog

    if not homebrew_catalog.enabled():
        return False
    from app import appstream_cache

    source = appstream_cache.get_state().get("sources", {}).get("homebrew", {})
    return bool(
        source.get("complete")
        and homebrew_catalog.binary_snapshot_available()
        and source.get("fingerprint") == homebrew_catalog.fingerprint()
    )


def refresh_homebrew_catalog() -> dict:
    """Refresh the Homebrew catalog cache.

    BLOCKING: call only from a worker thread. If the refresh succeeds
    and changed something, rebuilds the runtime context and cache,
    then preloads the Homebrew entries.

    Returns:
        The refresh result dict, or
        ``{"success": False, "error": <message>}`` if an exception
        is raised.
    """
    from app import appstream_cache, appstream_parser

    try:
        result = appstream_cache.refresh_homebrew_cache()
        if result.get("success"):
            if result.get("changed"):
                ensure_homebrew_context()
                appstream_parser.prepare_runtime_cache()
            appstream_parser.get_homebrew_entries()
        return result
    except Exception as error:  # noqa: BLE001
        return {"success": False, "error": str(error)}


def get_homebrew_items() -> list[dict]:
    from app import appstream_parser

    ensure_homebrew_context()
    return appstream_parser.get_homebrew_entries()


def search_homebrew_items(query: str) -> list[dict]:
    """Search the Homebrew catalog only (Rust index).

    BLOCKING: call from a worker thread.

    Args:
        query: Search text.

    Returns:
        Matching entry dicts without scores. Empty if Homebrew is
        disabled.
    """
    from app import homebrew_catalog

    if not homebrew_catalog.enabled():
        return []
    from app import appstream_parser

    ensure_homebrew_context()
    results = appstream_parser.search_homebrew_entries(query)
    return _unwrap_entries(results)


def get_specials_root_item(trans=None) -> dict:
    active_translations = trans or translations
    return {
        "name": active_translations.get("specials", "Specials"),
        "description": active_translations.get(
            "specials_desc", "LinuxToys-curated software and scripts."
        ),
        "path": SPECIALS_ROOT,
        "is_script": False,
        "widget_id": "is_linuxtoys_specials",
    }


def homebrew_category_info(trans=None) -> dict:
    active_translations = trans or translations
    return {
        "name": "Homebrew",
        "description": active_translations.get(
            "homebrew_category_desc", "Packages from Homebrew."
        ),
        "icon": "brew.png",
        "path": "homebrew://catalog",
        "type": "category",
        "is_script": False,
        "is_subcategory": False,
        "is_homebrew_category": True,
    }


def ensure_homebrew_context() -> bool:
    """Ensure the ``appstream_parser`` runtime context exists.

    BLOCKING: call from a worker thread. Uses the same arguments as
    the GUI (``parser.get_appstream_entries``) but does not
    materialize the catalog; it only needs ``_LAST_LOAD_CONTEXT`` to
    be published.

    Returns:
        True if the context is ready, False if building it failed.
    """
    from app import appstream_parser, parser

    if appstream_parser._LAST_LOAD_CONTEXT is not None:
        return True
    try:
        appstream_parser._runtime_catalog(
            parser.SCRIPTS_DIR,
            curated_entries=parser._get_appstream_curated_entries(
                translations
            ),
            category_paths=parser._indexed_category_paths(),
        )
    except Exception:
        return False
    return True


class ScriptResult(Enum):
    SUCCESS = auto()
    CANCELLED = auto()
    TERMINAL_CLOSED = auto()
    ERROR = auto()


def _classify_exit_code(exit_code: int | None) -> ScriptResult:
    """Classify a script's exit code into a result category.

    - None: terminal closed unexpectedly, session was restarted
    - 0: success
    - 100 or 128-192: user cancellation / signal termination (not a real error)
    - anything else: real error
    """
    if exit_code is None:
        return ScriptResult.TERMINAL_CLOSED
    if exit_code == 0:
        return ScriptResult.SUCCESS
    if exit_code == 100 or 128 <= exit_code <= 192:
        return ScriptResult.CANCELLED
    return ScriptResult.ERROR


def appimage_relative(path: str) -> str:
    """Strip the ``appimages://`` prefix from a virtual path.

    Assumes ``path`` starts with the prefix (see
    ``is_appimage_path``).

    Examples:
        >>> appimage_relative("appimages://root")
        ''
        >>> appimage_relative("appimages://a/b")
        'a/b'
    """
    rel = path[len(APPIMAGE_PREFIX) :].strip("/")
    return "" if rel == "root" else rel


def appimage_category_info(relative: str = "", trans=None) -> dict:
    from app import parser

    active = trans or translations
    relative = str(relative or "").strip("/")
    leaf = relative.rsplit("/", 1)[-1] if relative else ""
    name = active.get("appimage_category", "AppImages")
    icon = "appimages.webp"
    description = active.get(
        "appimage_category_desc",
        "Browse applications distributed as AppImages.",
    )
    if leaf:
        category_dir = os.path.join(parser.SCRIPTS_DIR, *relative.split("/"))
        metadata = parser._parse_metadata_file(
            os.path.join(category_dir, "category-info.txt"),
            {"icon": "folder-open", "description": ""},
            active,
        )
        name = active.get(leaf, leaf)
        icon = metadata.get("icon") or "folder-open"
        description = metadata.get("description") or ""
    return {
        "name": name,
        "description": description,
        "icon": icon,
        "path": "appimages://" + (relative or "root"),
        "type": "category",
        "is_script": False,
        "is_subcategory": bool(leaf),
        "is_appimage_category": True,
        "appimage_relative_category": relative,
    }


def _unwrap_entries(results) -> list[dict]:
    """Normalize parser results into a list of entry dicts.

    ``search_*`` functions return ``(dict, score)`` tuples, while
    ``get_*_entries`` return plain dicts.

    Args:
        results: Iterable of entries or ``(entry, score)`` tuples.

    Returns:
        The entry dicts, scores dropped.
    """
    return [e[0] if isinstance(e, tuple) else e for e in results]


def get_appimage_items(path: str) -> list[dict]:
    """Espelha a hierarquia LT. BLOQUEANTE: executar em thread."""
    from app import appstream_parser

    ensure_homebrew_context()
    prefix = appimage_relative(path)
    children = appstream_parser.get_appimage_subcategories(prefix)
    entries = []
    if not children or prefix:
        entries = _unwrap_entries(
            appstream_parser.get_appimage_entries(prefix)
        )
    entries.sort(key=lambda item: str(item.get("name") or "").casefold())
    return [appimage_category_info(c) for c in sorted(children)] + entries


def search_appimage_items(query: str) -> list[dict]:
    """Search AppImage entries only.

    BLOCKING: call from a worker thread.

    Args:
        query: Search text.

    Returns:
        Matching entry dicts without scores.
    """
    from app import appstream_parser

    ensure_homebrew_context()
    return _unwrap_entries(appstream_parser.search_appimage_entries(query))
