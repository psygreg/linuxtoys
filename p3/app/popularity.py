"""Internal popularity scoring and session browse ordering for LinuxToys."""

from __future__ import annotations

import random
import threading

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
    "org.gimp.GIMP",
    "com.obsproject.Studio"
}


_SESSION_LOCK = threading.RLock()
_SESSION_ORDER = {}


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
    return bool(_identity_values(item) & {value.casefold() for value in KNOWN_POPULAR})


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
    """Return the catalog-rs session-stable score for this identity."""
    return int(_catalog_rs.session_random_score(str(key), int(low), int(high)))


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
    """Return the direct Bayesian ODRS score for AppStream entries."""
    if _is_flatpak_appstream(item) or _is_native_appstream(item):
        score = review_subscore(item)
        return SCORE_MIN if score is None else max(SCORE_MIN, min(SCORE_MAX, int(score)))
    if is_known_popular(item) or _is_curated_or_linuxtoys_script(item):
        return SCORE_MAX
    return SCORE_MIN


def _session_order(item):
    key = _session_key(item)
    with _SESSION_LOCK:
        if key not in _SESSION_ORDER:
            _SESSION_ORDER[key] = random.random()
        return _SESSION_ORDER[key]


def _is_promoted(item):
    return is_known_popular(item) or _is_curated_or_linuxtoys_script(item)


def _direct_sort_key(item):
    if item.get("is_create_script", False):
        return (0, 0.0, "")
    if item.get("is_subcategory", False):
        return (1, 0.0, str(item.get("name", "")).casefold())
    review = review_subscore(item)
    return (
        2,
        0 if review is not None else 1,
        0.0 if review is None else -float(review),
        _session_order(item),
    )


def _spread_promoted(ranked, promoted):
    """Place promoted entries evenly through the top 10%, with deterministic jitter."""
    if not promoted:
        return ranked

    promoted = sorted(promoted, key=lambda item: (_session_order(item), _session_key(item)))
    total = len(ranked) + len(promoted)
    top_ten = (total + 9) // 10
    # A strict 10% window cannot keep N promoted entries apart when it contains
    # fewer than 2N-1 slots. Expand only as much as needed to preserve a normal
    # result between promoted entries whenever the category has enough entries.
    top_slots = max(top_ten, (2 * len(promoted)) - 1)
    top_slots = min(total, top_slots)

    # Even cell centers keep promoted entries apart. Stable jitter moves each entry
    # within its own cell without allowing neighboring promoted entries to collapse
    # onto the same position.
    positions = []
    count = len(promoted)
    for i, item in enumerate(promoted):
        left = (i * top_slots) // count
        right = max(left, ((i + 1) * top_slots) // count - 1)
        width = right - left + 1
        jitter = int(_session_order(item) * width) if width > 1 else 0
        positions.append(min(top_slots - 1, left + jitter))

    out = list(ranked)
    for pos, item in sorted(zip(positions, promoted), key=lambda pair: pair[0]):
        out.insert(min(pos, len(out)), item)
    return out


def sort_for_browse(items):
    apply_review_scores(items)

    structural = [
        item for item in items
        if item.get("is_create_script", False) or item.get("is_subcategory", False)
    ]
    promoted = [
        item for item in items
        if not item.get("is_create_script", False)
        and not item.get("is_subcategory", False)
        and _is_promoted(item)
    ]
    ranked = [
        item for item in items
        if not item.get("is_create_script", False)
        and not item.get("is_subcategory", False)
        and not _is_promoted(item)
    ]

    structural.sort(key=_direct_sort_key)
    ranked.sort(key=_direct_sort_key)
    items[:] = structural + _spread_promoted(ranked, promoted)
    return items


def browse_sort_key(item):
    """Compatibility key for callers sorting individual entries."""
    return _direct_sort_key(item)


def flathub_search_tiebreak(item):
    """Compatibility helper: use the Bayesian ODRS score."""
    if not _is_flatpak_appstream(item):
        return None
    score = review_subscore(item)
    return None if score is None else float(score)
