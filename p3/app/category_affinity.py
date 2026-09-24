"""Offline Myket category-affinity prior used by LinuxToys recommendations."""

from __future__ import annotations

import json
import os
from pathlib import Path


AFFINITY_PATH = Path(__file__).with_name("myket_affinity.json")
EXACT_CATEGORY_AFFINITY = 0.90
SHARED_BUCKET_AFFINITY = 0.65

# Conservative semantic bridge from LinuxToys category directory basenames to
# Myket's observed taxonomy. Ambiguous desktop-only categories are intentionally
# left unmapped rather than inventing statistical evidence that Myket cannot supply.
LINUXTOYS_TO_MYKET = {
    # Media / communication.
    "audio": ("Audio and Music",),
    "players": ("Audio and Music", "Photography and Video"),
    "photo": ("Photography and Video",),
    "video": ("Photography and Video",),
    "rec": ("Photography and Video",),
    "viewer": ("Photography and Video",),
    "tv": ("Entertainment", "Photography and Video"),
    "browsers": ("Social",),
    "chat": ("Social",),
    "network": ("Social", "Utility"),
    "p2p": ("Utility",),
    "remote": ("Business", "Utility"),

    # Productivity / system.
    "document": ("Business",),
    "planning": ("Business",),
    "fin": ("Financial",),
    "geo": ("Travel and Exploration",),
    "archive": ("Utility",),
    "sec": ("Utility",),
    "sys": ("Utility",),
    "sysadm": ("Utility",),
    "txt": ("Utility",),
    "utils": ("Utility",),
    "utilities": ("Utility",),

    # Education / health.
    "edu": ("Educational",),
    "education": ("Educational",),
    "science": ("Educational",),
    "langs": ("Educational", "Book"),
    "math": ("Educational", "Intellectual"),
    "nature": ("Educational",),
    "tech": ("Educational", "Utility"),
    "health": ("Fitness and Wellness", "Medical and Health"),

    # Games. Myket has unusually useful genre-level observations here.
    "game": ("Entertainment",),
    "games": ("Entertainment",),
    "action": ("Thrilling", "Adventure"),
    "classic": ("Intellectual", "Word", "Family"),
    "kids": ("Family",),
    "sim": ("Simulation", "Role-Playing"),
    "sports": ("Sports",),
    "strategy": ("Strategy",),
    "emu": ("Entertainment",),
}

_CACHE = None


def _load():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    try:
        with open(AFFINITY_PATH, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        _CACHE = value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        _CACHE = {}
    return _CACHE


def _category_basename(category):
    value = str(category or "").strip().replace(os.sep, "/").strip("/")
    return value.rsplit("/", 1)[-1].casefold() if value else ""


def myket_categories(category):
    return LINUXTOYS_TO_MYKET.get(_category_basename(category), ())


def affinity(source_category, target_category):
    """Return a 0..1 recommendation affinity between LinuxToys categories.

    Exact LinuxToys categories get a strong 0.90 prior. A genuinely strong Myket
    cross-category relationship can therefore outrank an exact-category sibling.
    Distinct LinuxToys categories mapped to the same broad Myket bucket receive a
    weaker 0.65 prior because Myket cannot resolve that finer desktop distinction.
    """
    source = str(source_category or "").strip().replace(os.sep, "/").strip("/")
    target = str(target_category or "").strip().replace(os.sep, "/").strip("/")
    if not source or not target:
        return 0.0
    if source.casefold() == target.casefold():
        return EXACT_CATEGORY_AFFINITY

    source_myket = myket_categories(source)
    target_myket = myket_categories(target)
    if not source_myket or not target_myket:
        return 0.0

    table = _load().get("affinity", {})
    best = SHARED_BUCKET_AFFINITY if set(source_myket) & set(target_myket) else 0.0
    for source_name in source_myket:
        row = table.get(source_name, {})
        for target_name in target_myket:
            try:
                best = max(best, float(row.get(target_name, 0.0) or 0.0))
            except (TypeError, ValueError):
                pass
    return max(0.0, min(1.0, best))


def affinity_from_sources(source_categories, target_category):
    """Return strongest affinity to target plus a small multi-interest reinforcement."""
    scores = sorted(
        (affinity(source, target_category) for source in source_categories or ()),
        reverse=True,
    )
    scores = [score for score in scores if score > 0.0]
    if not scores:
        return 0.0
    # One strong relationship should dominate; broad libraries must not accumulate
    # an arbitrarily large recommendation advantage merely by containing many areas.
    return min(1.0, scores[0] + (0.20 * sum(scores[1:])))
