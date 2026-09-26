"""Internal popularity scoring and session browse ordering for LinuxToys."""

from __future__ import annotations

import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import _catalog_rs


SCORE_MIN = 0
SCORE_MAX = 999
TOP_SECTION_MIN = 900
SECTION_SIZE = 100
NATIVE_SECTION_COUNT = 10
REVIEW_CONFIDENCE_COUNT = 10

# Developer-maintained identities that should always live in the top section.
# Matching is case-insensitive against IDs, package names and canonical/display names.
KNOWN_POPULAR = {
    "Steam",
    "com.valvesoftware.steam",
    "EasyEffects",
    "com.github.wwmm.easyeffects",
    "Mission Center",
    "io.missioncenter.MissionCenter",
    "Haguichi",
    "com.github.ztefn.haguichi",
    "Flatseal",
    "com.github.tchx84.Flatseal",
    "StreamController",
    "com.core447.StreamController",
    "Hardinfo2",
    "hardinfo2",
    "Thunderbird",
    "org.mozilla.thunderbird",
    "Save Desktop",
    "io.github.vikdevelop.SaveDesktop",
    "Prism Launcher",
    "org.prismlauncher.PrismLauncher",
    "ProtonPlus",
    "com.vysp3r.ProtonPlus",
    "Vinegar",
    "org.vinegarhq.Vinegar",
    "Sober",
    "org.vinegarhq.Sober",
    "net.davidotek.pupgui2",
    "Protontricks",
    "com.github.Matoking.protontricks",
    "Osu!",
    "sh.ppy.osu",
    "Greenlight",
    "io.github.unknownskl.greenlight",
    "Moonlight",
    "com.moonlight_stream.Moonlight",
    "Discord",
    "com.discordapp.Discord",
    "Signal",
    "org.signal.Signal",
    "Microsoft Teams",
    "com.github.IsmaelMartinez.teams_for_linux",
    "Slack",
    "com.slack.Slack",
    "Telegram",
    "org.telegram.desktop",
    "ZapZap",
    "com.rtosta.zapzap",
    "Cohesion",
    "io.github.brunofin.Cohesion",
    "Obsidian",
    "md.obsidian.Obsidian",
    "ffmpegthumbnailer",
    "Bottles",
    "com.usebottles.bottles",
    "ONLYOFFICE Desktop Editors",
    "org.onlyoffice.desktopeditors",
    "com.dec05eba.gpu_screen_recorder",
    "org.gimp.GIMP"
}
KNOWN_POPULAR_FOLDED = frozenset(value.casefold() for value in KNOWN_POPULAR)

FLATHUB_POPULAR_URL = "https://flathub.org/api/v2/collection/popular"
FLATHUB_PAGE_SIZE = 100
FLATHUB_MAX_PAGES = 100
FLATHUB_FETCH_WORKERS = 8
NETWORK_TIMEOUT = 12
FLATHUB_CACHE_MAX_AGE = 14 * 24 * 60 * 60
FLATHUB_CACHE_PATH = Path(
    os.path.expanduser("~/.cache/linuxtoys/appstream/flathub-popularity.json")
)

_SESSION_LOCK = threading.RLock()
_SESSION_SCORES = {}
_SESSION_ORDER = {}
_NATIVE_CATEGORY_SCORES = {}


def _identity_values(item):
    values = []
    for key in (
        "id", "appstream_id", "appstream_canonical_name", "canonical_name",
        "registry_name", "repo_app_id", "name",
    ):
        value = item.get(key)
        if value:
            values.append(str(value).strip().casefold())

    package_names = item.get("package-name")
    if isinstance(package_names, str):
        values.append(package_names.strip().casefold())
    elif isinstance(package_names, (list, tuple, set)):
        values.extend(str(value).strip().casefold() for value in package_names if value)

    path = str(item.get("path", "") or "")
    if path:
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if stem:
            values.append(stem.casefold())
    return {value for value in values if value}


def is_known_popular(item):
    return bool(_identity_values(item) & KNOWN_POPULAR_FOLDED)


def _session_key(item):
    identities = sorted(_identity_values(item))
    if identities:
        return identities[0]
    return f"object:{id(item)}"


def _is_local_script(item):
    return ".local/linuxtoys/scripts" in str(item.get("path", "") or "")


def _is_curated_or_linuxtoys_script(item):
    if item.get("is_appstream_entry"):
        return False
    if _is_local_script(item):
        return False
    return bool(item.get("is_repo_entry") or item.get("is_script"))


def is_linuxtoys_curated(item):
    """Return whether an item is curated and shipped by LinuxToys."""
    return _is_curated_or_linuxtoys_script(item)


def _is_flatpak_appstream(item):
    return (
        item.get("is_appstream_entry")
        and str(item.get("appstream_source", "") or "") == "flatpak"
    )


def _is_native_appstream(item):
    return (
        item.get("is_appstream_entry")
        and str(item.get("appstream_source", "native") or "native") == "native"
    )


def _session_random_score(key, low, high):
    with _SESSION_LOCK:
        if key not in _SESSION_SCORES:
            _SESSION_SCORES[key] = random.randint(low, high)
        return _SESSION_SCORES[key]


def review_subscore(item):
    """Return the cached Bayesian ODRS score (0..999), or None when unavailable."""
    value = item.get("review_subscore")
    try:
        return max(SCORE_MIN, min(SCORE_MAX, int(value)))
    except (TypeError, ValueError):
        return None


def apply_review_scores(items):
    """Calculate Bayesian ODRS scores from cached rating/count information.

    Rust owns the population prior and Bayesian weighting pass; Python only
    applies the resulting scores to the existing entry dictionaries.
    """
    items = list(items or ())
    rows = []
    for item in items:
        try:
            rating = float(item.get("review_rating"))
            count = int(item.get("review_count"))
        except (TypeError, ValueError):
            rating = None
            count = None
        rows.append((rating, count))

    scores = _catalog_rs.review_subscores(rows)
    for item, score in zip(items, scores):
        if score is None:
            item.pop("review_subscore", None)
        else:
            item["review_subscore"] = int(score)
    return items


def score_for_item(item):
    """Return the effective 0..999 browse score for one entry.

    AppStream entries with Flathub popularity data receive their category-relative
    score before this function is called. Their popularity_metric remains global/raw.
    """
    key = _session_key(item)

    if is_known_popular(item):
        return _session_random_score(key, TOP_SECTION_MIN, SCORE_MAX)

    if _is_flatpak_appstream(item):
        value = item.get("_category_popularity_score")
        try:
            return max(SCORE_MIN, min(SCORE_MAX, int(value)))
        except (TypeError, ValueError):
            return _session_random_score(key, SCORE_MIN, TOP_SECTION_MIN - 1)

    if _is_native_appstream(item):
        # A preferred native entry can inherit the raw metric from its matching
        # Flathub offer and participate in the same category-relative ranking.
        value = item.get("_category_popularity_score")
        try:
            return max(SCORE_MIN, min(SCORE_MAX, int(value)))
        except (TypeError, ValueError):
            pass

        # Pure native applications are ranked by their weighted ODRS review score,
        # then evenly distributed across the ten sections by
        # apply_native_category_scores().
        value = item.get("_category_native_score")
        try:
            return max(SCORE_MIN, min(SCORE_MAX, int(value)))
        except (TypeError, ValueError):
            # Native scores are normally assigned by the category-aware browse pass.
            return _session_random_score(key, SCORE_MIN, SCORE_MAX)

    if _is_curated_or_linuxtoys_script(item):
        return _session_random_score(key, TOP_SECTION_MIN, SCORE_MAX)

    return _session_random_score(key, SCORE_MIN, TOP_SECTION_MIN - 1)

def score_section(item):
    return min(9, max(0, score_for_item(item) // SECTION_SIZE))


def _session_order(item):
    key = _session_key(item)
    with _SESSION_LOCK:
        if key not in _SESSION_ORDER:
            _SESSION_ORDER[key] = random.random()
        return _SESSION_ORDER[key]


def browse_sort_key(item):
    """Keep structural actions first, then popularity sections, shuffled within each."""
    if item.get("is_create_script", False):
        return (0, 0, 0.0)
    if item.get("is_subcategory", False):
        return (1, 0, str(item.get("name", "")).casefold())
    review = review_subscore(item)
    # Reviews refine ordering inside an already-established popularity section.
    # Unknown review data keeps the old stable session shuffle behavior.
    return (
        2,
        -score_section(item),
        0 if review is None else -1,
        0 if review is None else -review,
        _session_order(item),
    )


def sort_for_browse(items):
    apply_review_scores(items)
    apply_native_category_scores(items)
    apply_category_scores(items)
    items.sort(key=browse_sort_key)
    return items


def flathub_search_tiebreak(item):
    """Use only the cached raw Flathub metric as a search tie-breaker."""
    if not _is_flatpak_appstream(item):
        return None
    try:
        return float(item.get("popularity_metric"))
    except (TypeError, ValueError):
        return None


def apply_native_category_scores(items):
    """Evenly distribute pure-native AppStream entries across all ten sections.

    Reviewed native entries are ranked by their Bayesian ODRS score. Native entries
    without review data retain a neutral session-random rank. The complete native
    population is then dealt into the same ten rank quantiles used for Flathub
    popularity, preventing review-score clustering in the highest sections.
    """
    native = []
    for item in items or ():
        if not _is_native_appstream(item):
            continue
        if is_known_popular(item):
            item["_category_native_score"] = _session_random_score(
                _session_key(item), TOP_SECTION_MIN, SCORE_MAX
            )
            continue

        # Native duplicates carrying an inherited Flathub metric participate in
        # apply_category_scores() instead.
        if item.get("popularity_metric") is not None:
            continue

        native.append(item)

    if not native:
        return items

    rows = []
    for index, item in enumerate(native):
        rows.append((
            index,
            review_subscore(item),
            _session_key(item),
            _session_order(item),
        ))

    for index, section in _catalog_rs.native_rank_sections(rows):
        item = native[index]
        low = section * SECTION_SIZE
        high = SCORE_MAX if section == 9 else low + SECTION_SIZE - 1
        item["_category_native_score"] = _session_random_score(
            f"native-category:{_session_key(item)}:{section}", low, high
        )

    return items


def apply_category_scores(items):
    """Distribute AppStream entries with Flathub metrics across browse sections.

    Real Flathub popularity still determines ordering: entries are sorted by their
    cached popularity_metric, then dealt into ten approximately equal rank buckets.
    Missing statistics do not participate and receive a stable session fallback.
    KNOWN_POPULAR entries remain forced into section 9.
    """
    candidates = []

    for item in items or ():
        # Normal Flatpaks and native entries carrying an inherited Flathub metric
        # share one category-relative popularity population.
        if not (_is_flatpak_appstream(item) or _is_native_appstream(item)):
            continue

        if is_known_popular(item):
            item["_category_popularity_score"] = _session_random_score(
                _session_key(item), TOP_SECTION_MIN, SCORE_MAX
            )
            continue

        try:
            raw_metric = item.get("popularity_metric")
            if raw_metric is None:
                raise TypeError
            metric = float(raw_metric)
        except (TypeError, ValueError):
            # Pure native entries are handled by their ODRS score when available,
            # otherwise by apply_native_category_scores(). Do not manufacture a
            # category-popularity score that would override either path.
            if _is_native_appstream(item):
                item.pop("_category_popularity_score", None)
                continue
            item["_category_popularity_score"] = _session_random_score(
                _session_key(item), SCORE_MIN, SCORE_MAX
            )
            continue

        candidates.append((metric, _session_key(item), item))

    if not candidates:
        return items

    rows = [(index, metric, key) for index, (metric, key, _item) in enumerate(candidates)]
    for candidate_index, section in _catalog_rs.metric_rank_sections(rows):
        _metric, key, item = candidates[candidate_index]
        low = section * SECTION_SIZE
        high = SCORE_MAX if section == 9 else low + SECTION_SIZE - 1
        item["_category_popularity_score"] = _session_random_score(
            f"flatpak-category:{key}:{section}", low, high
        )

    return items


def _collection_items(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("hits", "apps", "items", "results", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _item_id(item):
    if not isinstance(item, dict):
        return ""
    for key in ("id", "app_id", "appstream_id"):
        value = str(item.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _item_downloads(item):
    if not isinstance(item, dict):
        return 0
    for key in ("installs_last_month", "downloads_last_month", "downloads"):
        value = item.get(key)
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            continue
    return 0


def invalidate_flathub_download_cache():
    """Invalidate the persisted snapshot before an explicit AppStream rebuild."""
    try:
        FLATHUB_CACHE_PATH.touch(exist_ok=True)
        os.utime(FLATHUB_CACHE_PATH, (0, 0))
    except OSError:
        pass


def _load_flathub_download_cache():
    """Return a fresh persisted Flathub snapshot, or None when it needs refreshing."""
    try:
        stat = FLATHUB_CACHE_PATH.stat()
        if time.time() - stat.st_mtime > FLATHUB_CACHE_MAX_AGE:
            return None
        with FLATHUB_CACHE_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            return None
        return {
            str(app_id): max(0, int(downloads))
            for app_id, downloads in payload.items()
            if app_id
        }
    except (OSError, ValueError, TypeError):
        return None


def _write_flathub_download_cache(downloads):
    """Atomically persist the last complete Flathub popularity snapshot."""
    try:
        FLATHUB_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = FLATHUB_CACHE_PATH.with_name(
            f"{FLATHUB_CACHE_PATH.name}.{os.getpid()}.tmp"
        )
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(downloads, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, FLATHUB_CACHE_PATH)
    except OSError:
        try:
            tmp_path.unlink(missing_ok=True)
        except (OSError, UnboundLocalError):
            pass


def _fetch_flathub_page(page):
    query = urlencode({
        "page": page,
        "per_page": FLATHUB_PAGE_SIZE,
        "locale": "en",
    })
    request = Request(f"{FLATHUB_POPULAR_URL}?{query}", headers={
        "Accept": "application/json",
        "User-Agent": "LinuxToys-AppStream/1",
    })
    with urlopen(request, timeout=NETWORK_TIMEOUT) as response:
        payload = json.load(response)
    return page, _collection_items(payload)


def _merge_flathub_items(downloads, items):
    for item in items:
        app_id = _item_id(item)
        if app_id:
            downloads[app_id] = max(
                downloads.get(app_id, 0),
                _item_downloads(item),
            )


def fetch_flathub_downloads(force=False):
    """Return Flathub app-id -> monthly downloads.

    A fresh persisted snapshot avoids network work during ordinary AppStream
    rebuilds. When refresh is necessary, pages are fetched in bounded parallel
    batches rather than serially.
    """
    if not force:
        cached = _load_flathub_download_cache()
        if cached is not None:
            return cached

    downloads = {}

    # Probe page 0 synchronously. Besides avoiding a worker pool for an empty
    # collection, this preserves the old endpoint-failure semantics cleanly.
    try:
        _page, first_items = _fetch_flathub_page(0)
    except Exception:
        # Preserve the last known snapshot even when it is stale. Returning an
        # empty dict would make a transient Flathub outage authoritative.
        try:
            with FLATHUB_CACHE_PATH.open("r", encoding="utf-8") as handle:
                stale = json.load(handle)
            if isinstance(stale, dict):
                return {
                    str(app_id): max(0, int(value))
                    for app_id, value in stale.items()
                    if app_id
                }
        except (OSError, ValueError, TypeError):
            pass
        return {}

    if not first_items:
        return {}

    _merge_flathub_items(downloads, first_items)
    if len(first_items) < FLATHUB_PAGE_SIZE:
        _write_flathub_download_cache(downloads)
        return downloads

    # Fetch in bounded waves. Once a short/empty page appears, later pages in
    # that wave may already be in flight, but no additional wave is scheduled.
    next_page = 1
    finished = False
    with ThreadPoolExecutor(max_workers=FLATHUB_FETCH_WORKERS) as executor:
        while next_page < FLATHUB_MAX_PAGES and not finished:
            pages = list(range(
                next_page,
                min(next_page + FLATHUB_FETCH_WORKERS, FLATHUB_MAX_PAGES),
            ))
            futures = {
                executor.submit(_fetch_flathub_page, page): page
                for page in pages
            }

            results = {}
            failed = False
            for future in as_completed(futures):
                page = futures[future]
                try:
                    _returned_page, items = future.result()
                    results[page] = items
                except Exception:
                    failed = True

            # Only consume the contiguous successful prefix. This prevents a
            # failed middle page from silently publishing an incomplete snapshot.
            for page in pages:
                if page not in results:
                    finished = True
                    break
                items = results[page]
                if not items:
                    finished = True
                    break
                _merge_flathub_items(downloads, items)
                if len(items) < FLATHUB_PAGE_SIZE:
                    finished = True
                    break

            if failed:
                finished = True
            next_page += len(pages)

    # Publish only when the fetch reached a natural end. If all 100 pages were
    # full, that is also a bounded complete snapshot for our configured horizon.
    complete = finished or next_page >= FLATHUB_MAX_PAGES
    if complete and downloads:
        _write_flathub_download_cache(downloads)
    return downloads

