"""Cached discovery metadata from the AppImage community feed.

This module does not resolve releases or download AppImages. Network access is
limited to one feed request when the cache is stale. Entries are classified
against LinuxToys' finer categories from their own name and description so
swept-in feed taxonomy does not misplace them.
"""
from __future__ import annotations

import json
import contextlib
import html
import platform
import re
import tempfile
import shutil
import urllib.error
from urllib.parse import urlparse, quote, urlsplit, urlunsplit
import logging
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

FEED_URL = "https://appimage.github.io/feed.json"
# The hub serves per-app artwork under /database/<app>/...; the feed lists
# those paths relative to this base.
FEED_ASSET_BASE = "https://appimage.github.io/database/"
MAX_FEED_BYTES = 20 * 1024 * 1024
REFRESH_SECONDS = 14 * 24 * 60 * 60

def _strings(value):
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [x for x in value if isinstance(x, str) and x]
    return []

def _feed_asset_url(value):
    """Normalize feed artwork, preserving existing URL escapes and path case."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if not value:
        return ""
    if value.startswith("//"):
        value = "https:" + value
    elif not value.startswith("https://"):
        if value.startswith(("http://", "/v2/")) or ":" in value.split("/")[0]:
            return ""
        # Relative artwork is stored below the community database directory.
        if value.startswith("/"):
            value = value.lstrip("/")
        value = FEED_ASSET_BASE + value
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc:
        return ""
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%:@!$&'()*+,;=-._~"), parts.query, ""))


_FORGE_HOSTS = ("github.com", "www.github.com", "codeberg.org", "gitlab.com")


def _link_pairs(item):
    """(link type, raw url) pairs from the links/download fields."""
    pairs = []
    raw_links = item.get("links")
    if isinstance(raw_links, list):
        for link in raw_links:
            if isinstance(link, dict):
                pairs.append((str(link.get("type") or ""), str(link.get("url") or "").strip()))
            elif isinstance(link, str) and link.strip():
                pairs.append(("", link.strip()))
    for url in _urls(item.get("download")):
        pairs.append(("Download", url))
    return pairs


def _canonical_link(url):
    """Full https URL for a feed link; expands the owner/repo shorthand."""
    url = url.strip()
    if "://" not in url:
        if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", url):
            return "https://github.com/" + url
        return ""
    return url if url.startswith("https://") else ""


def _is_repo_page(url):
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    return parsed.hostname in _FORGE_HOSTS and 2 <= len(parts) <= 3


def _website_and_install_links(pairs):
    """Return (website, install links) for one feed entry.

    The website prefers the forge repository page (the app's canonical home);
    install links keep every https URL resolve_download understands.
    """
    website = ""
    install_links = []
    for _link_type, raw in pairs:
        url = _canonical_link(raw)
        if not url or url in install_links:
            continue
        install_links.append(url)
        if not website and _is_repo_page(url):
            website = url
    if not website and install_links:
        website = install_links[0]
    return website, install_links


def _split_description(text):
    """First sentence becomes the summary; the whole text stays the long one."""
    text = re.sub(r"(?i)<br\s*/?>", "\n", text or "")
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)  # feed descriptions may carry HTML
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    paragraphs = []
    for raw in re.split(r"\n\s*\n", text):
        paragraph = " ".join(raw.split())
        if paragraph:
            paragraphs.append(paragraph)
    if not paragraphs:
        return "", []
    first = paragraphs[0]
    # Sentence boundary: terminator + whitespace + a capital/opening quote, so
    # version numbers ("Qt 5.") do not terminate the summary.
    match = re.match(r"^(.{10,}?[.!?])(?:\s+(?=[A-Z0-9\"'])|$)", first)
    summary = match.group(1).strip() if match else first
    blocks = [
        {"type": "paragraph", "spans": [{"type": "text", "text": paragraph}]}
        for paragraph in paragraphs
    ]
    return summary, blocks

def _urls(value):
    if isinstance(value, str):
        return [value] if value.startswith("https://") else []
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_urls(item))
        return result
    if isinstance(value, dict):
        result = []
        for key in ("url", "href", "link", "download", "icon", "image", "src", "github", "git", "homepage", "website", "repository"):
            if key in value:
                result.extend(_urls(value[key]))
        return result
    return []

def _developer_names(authors):
    """The community feed is not strictly typed; never reject a whole feed over authors."""
    if not isinstance(authors, list):
        return ""
    names = []
    for author in authors:
        if isinstance(author, dict):
            name = author.get("name")
        elif isinstance(author, str):
            name = author
        else:
            continue
        if isinstance(name, (str, int, float)) and not isinstance(name, bool):
            value = str(name).strip()
            if value and value not in names:
                names.append(value)
    return ", ".join(names)


# ---------------------------------------------------------------------------
# Intent classification for community feed entries.
#
# The feed carries upstream-written categories that are far broader than the
# LinuxToys tree, and the resolver maps those broad tags literally (a CAD
# package tagged "Graphics" would land under creative instead of office/eng,
# the canonical complaint). Instead of pinning individual app IDs, entries are
# classified from their own name and description with weighted keyword
# patterns per destination, offline and deterministically:
#
# - Name evidence (weight 3.0) outranks description evidence; names are short
#   and product-specific. CamelCase names are split so tokens like CAD in
#   "LibreCAD"/"QymCAD" still match.
# - Unambiguous multi-token phrases score 3.0, ordinary phrases 2.0 and loose
#   single tokens 1.0. A destination wins only at >= 2.5: a lone loose phrase
#   can never flip an entry on its own.
# - At most one destination emits per entry (the highest-scoring spec, spec
#   order breaking ties): the classifier picks the app's one evident purpose
#   rather than accumulating every topic it mentions.
# - Guards veto a whole spec when a contradicting context matches (terminal
#   emulators, QEMU/virtualization vs games, "video downloader" vs video
#   editing, AI-farm chat clients vs messaging, ...). Silence beats a
#   misclassification.
# - Inferred tags are appended, never replaced: the AppStream resolver's own
#   specificity engine (cross-main rules, generic-vs-specific priority) then
#   decides. A precise feed main category ("Game") therefore outranks weak
#   inference, while a vague bucket ("Utility", "None", toolkit tags) is
#   legitimately overturned by strong evidence.
#
# Every emitted tag is routed by the AppStream category config in
# appstream_parser (mirroring snap_catalog._CATEGORY_MAP), so no resolver
# change is needed; tuples such as ("Network", "P2P") deliberately pair a Main
# and Additional tag so an expression refines a generic feed main.
# ---------------------------------------------------------------------------

_INTENT_NAME_WEIGHT = 3.0
_INTENT_STRONG_WEIGHT = 3.0
_INTENT_PHRASE_WEIGHT = 2.0
_INTENT_TERM_WEIGHT = 1.0
_INTENT_THRESHOLD = 2.5

# (destination tags, name patterns, strong phrases, phrases, terms, guards).
# Order matters only for score ties: the earlier spec wins.
_INTENT_SPECS = (
    # Engineering: CAD, CAM/3D printing, PCB/EDA.
    (
        ("Engineering",),
        (r"\bcad\b", r"cad$", r"openscad", r"kicad"),
        (
            r"computer[- ]aided",
            r"\bcad\b",
            r"3d print",
            r"\bslicer\b",
            r"\bg[- ]?code\b",
            r"parametric (model|design|part|cad)",
            r"pcb design",
            r"solid model",
            r"mechanical (design|engineering|cad)",
            r"technical drawing",
            r"engineering\b",
            r"\bcam\b",
            r"finite element",
            r"\bcnc\b",
            r"circuit (design|simulat)",
            r"schematic",
            r"\bpcb\b",
            r"verilog",
            r"vhdl",
            r"\bfpga\b",
            r"\beda\b",
            r"\bgerber\b",
        ),
        (r"\btoolpath\b", r"logic analyzer"),
        (r"\bdwg\b", r"\bdxf\b", r"\biges\b", r"\bstl\b", r"\bspice\b"),
        (r"software engineer", r"reverse engineering", r"web ?cam|camera", r"coding"),
    ),
    # Music production / audio editing (not playback).
    (
        ("Audio",),
        (r"\bsynth\b", r"\bsequencer\b", r"\bmidi\b"),
        (
            r"digital audio workstation",
            r"\bdaw\b",
            r"audio (edit|editor|editing)",
            r"music production",
            r"\bmidi\b",
            r"synthesizer",
            r"sound design",
            r"vst",
            r"multitrack",
            r"\boscilloscope\b",
        ),
        (r"music (studio|tool|tools|software)",),
        (r"\bwaveform\b", r"\bsample library\b"),
        (r"video.{0,12}audio|audio.{0,12}video", r"video (edit|editing|editor)"),
    ),
    # Video creation: editors, recorders, streamers, converters.
    (
        ("AudioVideo", "AudioVideoEditing"),
        (),
        (
            r"video[/ !]?(?:and |/?)(?:edit|editing|editor)",
            r"video[/ ]audio",
            r"non[- ]linear (edit|editing|editor)",
            r"\bnle\b",
            r"screen (record|recording|recorder)",
            r"screencast",
            r"stop[- ]motion",
            r"chroma key",
            r"subtitle editor",
            r"animation (studio|software|tools?)",
            r"green screen",
            r"live streaming",
            r"video converter",
        ),
        (r"\bvfx\b", r"(video|clip) (cutter|trimmer)", r"(video|clip) trim"),
        (r"\bffmpeg\b", r"\bmp4\b", r"\bwebm\b"),
        (r"downloader",),
    ),
    # Photo workflows.
    (
        ("Graphics", "Photography"),
        (),
        (
            r"photo (editing|editor|retouch|workflow|manag)",
            r"(raw|dng) (processing|develop|editing|converter)",
            r"image (edit|editing|editor)",
            r"\bhdr\b",
            r"focus stacking",
            r"photography",
            r"darkroom",
            r"portrait retouch",
            r"film (emul|simulation)",
        ),
        (r"image toolbox", r"photo filter"),
        (r"\bdng\b", r"\bexif\b"),
        (),
    ),
    # Digital art / drawing / painting (never CAD; never screenshots).
    (
        ("Graphics", "2DGraphics"),
        (),
        (
            r"digital paint",
            r"drawing (software|app|tool|tablet|pad|program)",
            r"(picture|painting|art) tablet",
            r"comic (book|panel|creator)",
            r"vector (draw|graphics editor)",
            r"image generat",
        ),
        (r"\bpainting\b", r"\bsketch\b", r"pixel art", r"\bdraw\b", r"illustrat"),
        (r"\bbrush(es)?\b",),
        (r"screenshot",),
    ),
    # Transfers: torrent and other download/transfer clients.
    (
        ("Network", "P2P"),
        (),
        (
            r"torrent (client|downloader|search|manager)",
            r"\btorrents?\b",
            r"magnet link",
            r"peer[- ]to[- ]peer",
            r"file sharing",
            r"\bftp\b",
            r"video downloader",
        ),
        (r"share files", r"download manager", r"download videos"),
        (r"\bmagnet\b", r"\bseeding\b"),
        (),
    ),
    # Messaging and social apps (mail clients included; AI bots excluded).
    (
        ("Chat",),
        (r"\bmessenger\b",),
        (
            r"messenger",
            r"chat (client|app|service)",
            r"instant messaging",
            r"whatsapp",
            r"telegram",
            r"discord",
            r"matrix (client|protocol|homeserver)",
            r"irc client",
            r"e[- ]?mail (client|app|service)",
            r"voip",
            r"sip client",
            r"team communication",
        ),
        (r"\bchat\b", r"\bsocial\b"),
        (),
        (
            r"chat ?bot",
            r"\bgpt\b",
            r"\bllm\b",
            r"ai (assistant|agent|chat|bots?)",
            r"claude",
            r"anthropic",
            r"openai",
            r"gemini",
        ),
    ),
    # Web browsers.
    (
        ("Network", "WebBrowser"),
        (r"\bbrowser\b",),
        (
            r"web browser",
            r"browsing (experience|needs)",
            r"privacy[- ]focused browser",
        ),
        (r"\bbrowser\b", r"ad block"),
        (r"\bchromium\b", r"\bgecko\b"),
        (r"browser (automation|framework|e?xtensi)", r"(web|site) scraping"),
    ),
    # Remote access and desktop sharing.
    (
        ("RemoteAccess",),
        (),
        (
            r"remote (desktop|control|management|access|session)",
            r"\bvnc\b",
            r"\brdp\b",
            r"ssh client",
            r"desktop sharing",
            r"screen (mirroring|share)",
        ),
        (r"\bremote\b", r"\bssh\b"),
        (),
        (r"(git|github|repository) remote", r"remote (repo|database|administration)"),
    ),
    # Terminal emulators and shells.
    (
        ("TerminalEmulator",),
        (r"\bterminal\b",),
        (
            r"terminal emulator",
            r"terminal (multiplexer|session)",
            r"\bash\b",
        ),
        (r"\bterminal\b", r"command[- ]line"),
        (r"\bshell\b", r"\btty\b"),
        (),
    ),
    # Document viewers/editors: PDF, ebooks, word processing, notes.
    (
        ("WordProcessor",),
        (r"\bnotes?\b",),
        (
            r"pdf (reader|viewer|editor|converter)",
            r"e[- ]?book reader",
            r"word processor",
            r"markdown (editor|notes|writer)",
            r"note[- ]taking",
            r"taking notes",
            r"spreadsheet",
            r"latex (editor|typesetting)",
            r"writing (tool|app|platform)",
            r"digital book reader",
            r"organize notes",
        ),
        (r"documents? (reader|viewer)", r"\bepub\b", r"read documents"),
        (r"\bpdf\b", r"\bodt\b"),
        (),
    ),
    # Planning, boards and scheduling (not system task managers).
    (
        ("Office", "ProjectManagement"),
        (r"\bcalendar\b",),
        (
            r"project management",
            r"\bkanban\b",
            r"\bgantt\b",
            r"task (management|tracking)",
            r"to[- ]?do (list|app)",
            r"time track",
            r"\bagile\b",
            r"\bscrum\b",
        ),
        (
            r"plan(?:n?er|ning)",
            r"\bcalendar\b",
            r"task (tracker|list|planner)",
            r"organize (tasks|projects)",
            r"habit track",
        ),
        (),
        # Task managers that mean process/system monitors are not planners.
        (
            r"task manager",
            r"system monitor",
            r"\bprocess(es)?\b",
            r"\bcpu\b",
            r"\bwine\b",
            r"windows (software|apps?)",
        ),
    ),
    # Personal finance.
    (
        ("Finance",),
        (r"\bwallet\b",),
        (
            r"\bbudget(s|ing)?\b",
            r"\bwallet\b",
            r"invoic",
            r"accounting",
            r"expense (track|manag)",
            r"money (manager|management)",
            r"personal finance",
            r"stock (portfolio|trading)",
            r"crypto (wallet|portfolio|tracking)",
            r"bank",
        ),
        (r"trading", r"currency", r"portfolio"),
        (r"\btax\b",),
        (r"mining",),
    ),
    # Health and self-care.
    (
        ("HealthFitness",),
        (),
        (
            r"fitness",
            r"workout",
            r"exercis",
            r"\bdiet\b",
            r"nutrition",
            r"calorie",
            r"wellness",
            r"medication",
            r"symptom",
            r"period track",
            r"pregnancy",
            r"sleep (track|analysis)",
        ),
        (),
        (r"\bdaylio\b",),
        (),
    ),
    # Accessibility tooling.
    (
        ("HealthFitness", "Accessibility"),
        (),
        (
            r"screen reader",
            r"screen magnifier",
            r"\bbraille\b",
            r"dyslexia",
            r"assistive",
            r"accessibility (tool|feature|features|app|apps)",
        ),
        (),
        (),
        (),
    ),
    # Astronomy.
    (
        ("Science", "Astronomy"),
        (),
        (
            r"astronomy",
            r"planetarium",
            r"telescope",
            r"star map",
            r"observator",
        ),
        (),
        (r"\bplanets?\b", r"\bspace\b"),
        (),
    ),
    # AI assistants and agents (not image/media AI features).
    (
        ("ArtificialIntelligence",),
        (r"\bgpt\b", r"\bollama\b"),
        (
            r"ai (assistant|agent|agents|coding|chat|model|toolkit)",
            r"\bllms?\b",
            r"large language model",
            r"\bchatbot\b",
            r"\bclaude\b",
            r"\bopenai\b",
            r"machine learning (model|framework)",
        ),
        (),
        (),
        (),
    ),
    # Emulators and ROM management (never terminal emulation, VMs or film
    # simulation; "BitTorrent ratio emulator" stays a transfer utility).
    (
        ("Emulator",),
        (),
        (
            r"\bemulat(e|es|ion|or|ors)\b",
            r"console emulation",
            r"retro (gaming|console)",
        ),
        (r"\broms?\b", r"\bnes\b", r"\bsnes\b", r"\bgba\b"),
        (r"dreamcast", r"playstation"),
        (
            r"virtual(ization|isation| )?machin",
            r"virtualiz",
            r"\bqemu\b",
            r"virtualbox",
            r"windows (app|applications?)",
            r"\bfilm\b",
            r"terminal",
            r"torrent",
        ),
    ),
    # Passwords, keys and firewalls (not crypto libraries).
    (
        ("Security",),
        (),
        (
            r"password (manager|vault|safe|protection)",
            r"password (vault|safe)",
            r"authenticator",
            r"two[- ]factor",
            r"\b2fa\b",
            r"\bfirewall\b",
            r"password",
        ),
        (r"secure", r"\bencrypt(ed|ion)\b", r"\bkeystore\b"),
        (r"\bgpg\b", r"\bpgp\b", r"\botp\b"),
        (r"cryptography (library|after)",),
    ),
    # Archives, compression and encryption of one's own files (not media).
    (
        ("Archiving",),
        (),
        (
            r"compress(ion|or|\b)",
            r"archiv(er|ing|e manager)",
            r"extract(ing)? files",
            r"7[- ]?zip",
            r"encrypt",
            r"\bencrypt(ed|ion)\b",
        ),
        (r"\bzip\b", r"\brar\b", r"\bgpg\b"),
        (),
        (r"compress(ing|es)? (your |the )?(image|photo|video|audio)",),
    ),
)

_INTENT_COMPILED = tuple(
    (
        tags,
        [re.compile(pattern, re.I) for pattern in name],
        [re.compile(pattern, re.I) for pattern in strong],
        [re.compile(pattern, re.I) for pattern in phrase],
        [re.compile(pattern, re.I) for pattern in term],
        [re.compile(pattern, re.I) for pattern in guard],
    )
    for tags, name, strong, phrase, term, guard in _INTENT_SPECS
)

_CAMEL_SPLIT = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[0-9]+")
_INTENT_TAG_MARKUP = re.compile(r"<(?!\s)[^>]+>")
_INTENT_WHITESPACE = re.compile(r"\s+")


def _intent_name_variants(name):
    """Original name plus a camel-case split copy, for token-style matches."""
    name = name.strip()
    if not name:
        return ""
    tokens = _CAMEL_SPLIT.findall(name)
    if tokens:
        return f"{name.lower()} {' '.join(token.lower() for token in tokens)}"
    return name.lower()


def _intent_about_text(description):
    """Feed description reduced to plain searchable text."""
    text = _INTENT_TAG_MARKUP.sub(" ", description or "")
    return _INTENT_WHITESPACE.sub(" ", text).strip()


def _best_intent(name, description):
    """Return the winning (tags, score) destination for one entry, or None.

    Guards veto a whole destination before scoring; at most one destination
    passes and only at the threshold. Spec order resolves score ties.
    """
    hay_name = _intent_name_variants(name)
    about = _intent_about_text(description)
    if not hay_name and not about:
        return None
    best = None
    for tags, patterns_name, patterns_strong, patterns_phrase, patterns_term, patterns_guard in _INTENT_COMPILED:
        if any(pattern.search(hay_name) or pattern.search(about) for pattern in patterns_guard):
            continue
        score = 0.0
        score += _INTENT_NAME_WEIGHT * sum(1 for pattern in patterns_name if pattern.search(hay_name))
        score += _INTENT_STRONG_WEIGHT * sum(1 for pattern in patterns_strong if pattern.search(about))
        score += _INTENT_PHRASE_WEIGHT * sum(1 for pattern in patterns_phrase if pattern.search(about))
        score += _INTENT_TERM_WEIGHT * sum(1 for pattern in patterns_term if pattern.search(about))
        if score >= _INTENT_THRESHOLD and (best is None or score > best[1]):
            best = (tags, score)
    return best


def refine_entry_categories(categories, name, description):
    """Append this entry's inferred destination tags to its feed categories.

    Returns a new list; the original feed tags are always preserved. Inference
    must never break a feed build, so any unexpected failure keeps the entry
    exactly as the feed supplied it.
    """
    try:
        best = _best_intent(name, description)
    except Exception:  # pragma: no cover - defensive, see docstring
        logging.debug("AppImage intent classification failed", exc_info=True)
        return categories
    if not best:
        return categories
    tags, _score = best
    refined = list(categories)
    for tag in tags:
        if tag not in refined:
            refined.append(tag)
    return refined


def normalize(feed):
    """Normalize conservative, directly supported presentation fields.

    Downloadability is deliberately not asserted until an installer can resolve
    a real upstream asset. Entries lacking a URL are skipped.
    """
    if isinstance(feed, dict):
        feed = feed.get("apps", feed.get("items", feed.get("applications", [])))
    if not isinstance(feed, list):
        raise ValueError("Unexpected AppImage feed structure")
    result = []
    seen = set()
    for item in feed:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        website, links = _website_and_install_links(_link_pairs(item))
        if not links:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        icons = [
            url for url in (_feed_asset_url(icon) for icon in _strings(item.get("icons")))
            if url
        ]
        screenshots = [
            url for url in (_feed_asset_url(shot) for shot in _strings(item.get("screenshots")))
            if url
        ]
        description = item.get("description")
        if not isinstance(description, str):
            description = ""
        description = description.strip()
        summary, description_blocks = _split_description(description)
        # Null category entries mean "uncategorized": route them through the
        # "None" bucket so they still resolve to a destination.
        raw_categories = item.get("categories")
        if isinstance(raw_categories, list):
            categories = [
                "None" if c is None else str(c).strip()
                for c in raw_categories
                if c is None or (isinstance(c, str) and c.strip())
            ]
            categories = [c for c in categories if c]
        elif isinstance(raw_categories, str) and raw_categories.strip():
            categories = [raw_categories.strip()]
        else:
            categories = []
        # Refined routing: the resolver maps tags literally, so entries whose
        # feed tags are too broad to state their purpose (CAD under Graphics,
        # media tools under Utility) gain the classifier's steering tags too.
        categories = refine_entry_categories(categories, name, description)
        result.append({
            "id": "appimage.community." + "".join(c if c.isalnum() else "-" for c in key).strip("-"),
            "name": name,
            "summary": summary,
            "packages": [name],
            "description_blocks": description_blocks,
            "origin": "appimage-community",
            "license": str(item.get("license") or ""),
            "developer": _developer_names(item.get("authors")),
            "description": summary,
            "homepage": website,
            "categories": categories,
            "icon": icons[0] if icons else "",
            "screenshots": screenshots,
            "source": "appimage",
            "appimage_links": links,
            "appimage_needs_resolution": True,
        })
    return result

def load_or_refresh(path, *, force=False):
    path = Path(path)
    cached = None
    if path.is_file():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if not force and time.time() - path.stat().st_mtime < REFRESH_SECONDS:
                return normalize(cached)
        except (OSError, ValueError, TypeError):
            cached = None
    try:
        request = Request(FEED_URL, headers={"User-Agent": "LinuxToys AppImage Catalog", "Accept": "application/json"})
        with urlopen(request, timeout=15) as response:
            payload = response.read(MAX_FEED_BYTES + 1)
        if len(payload) > MAX_FEED_BYTES:
            raise ValueError("AppImage feed exceeds size limit")
        feed = json.loads(payload)
        entries = normalize(feed)
        if not entries:
            raise ValueError("AppImage feed has no usable entries")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        try:
            tmp.write_bytes(payload)
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
        return entries
    except Exception as exc:
        logging.warning("AppImage community feed unavailable: %s", exc)
        if cached is not None:
            try:
                return normalize(cached)
            except (ValueError, TypeError):
                pass
        return []

MAX_APPIMAGE_BYTES = 4 * 1024 * 1024 * 1024

def file_signature(path):
    stat = os.stat(path)
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns

def _get_json(url):
    req = Request(url, headers={"User-Agent": "LinuxToys AppImage Installer", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=20) as response:
            data = response.read(4 * 1024 * 1024 + 1)
    except Exception as exc:
        raise ValueError(_http_failure_text(url, exc)) from exc
    if len(data) > 4 * 1024 * 1024:
        raise ValueError("Release metadata too large")
    try:
        return json.loads(data)
    except ValueError as exc:
        raise ValueError(f"Release metadata is not valid JSON ({url})") from exc


def _http_failure_text(url, exc):
    """One actionable sentence for a failed release/download request.

    Resolution failures used to surface as raw urllib exceptions ("HTTP Error
    404: Not Found"), which told the user nothing about which remote side broke
    or why the install could not continue. Translate the status instead. A
    definite "the forge has no such repository" is raised right away so the
    caller can tell a vanished upstream from a flaky network: the ValueError
    keeps the HTTP error as its cause for that check.
    """
    status = getattr(exc, "code", None)
    if isinstance(status, int) and 400 <= status < 500:
        host = urlparse(url).hostname or "the remote server"
        if status == 404:
            error = ValueError(
                f"The remote repository or release for this AppImage is gone "
                f"({host} returned 404 for {url}). The upstream project was "
                "likely renamed or removed; nothing can be installed until it "
                "publishes an AppImage again."
            )
            raise error from exc
        return f"The remote server refused the request ({host} returned {status} for {url})"
    if isinstance(exc, TimeoutError):
        return f"Timed out contacting {urlparse(url).hostname or 'the remote repository'}"
    return f"Could not reach the remote repository: {exc}"


def repository_gone(info):
    """Whether every link of this entry is a forge repository that no longer exists.

    The community feed is the only catalog source here and it carries no
    liveness data, so this is evaluated for one entry at a time, from the exact
    release lookup the installer performs anyway — never as a bulk scan, which
    would hammer the forge APIs and hit rate limits. A negative answer is kept
    out of the cache: repositories do come back (renames, outages), so a "gone"
    verdict must be re-checked the next time someone tries to install.
    """
    links = info.get("appimage_links") or []
    checked = False
    for raw in links:
        url = str(raw)
        parsed = urlparse(url)
        if parsed.scheme != "https" or re.search(r"(?i)\.appimage$", parsed.path):
            return False
        parts = [p for p in parsed.path.split("/") if p]
        if parsed.hostname in ("github.com", "www.github.com") and len(parts) >= 2:
            api = f"https://api.github.com/repos/{parts[0]}/{parts[1]}/releases/latest"
        elif parsed.hostname == "codeberg.org" and len(parts) >= 2:
            api = f"https://codeberg.org/api/v1/repos/{parts[0]}/{parts[1]}/releases/latest"
        else:
            return False
        if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in parts[:2]):
            return False
        checked = True
        try:
            _get_json(api)
        except ValueError as exc:
            # Only a definite "the forge has no such repository" counts. A
            # missing release, a rate limit or a network hiccup does not prove
            # the project is gone and must not hide the app.
            status = getattr(getattr(exc, "__cause__", None), "code", None)
            if status != 404:
                return False
        else:
            return False
    return checked

def _arch_match(filename):
    name = filename.lower()
    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        wanted, rejected = ("x86_64", "amd64", "x64"), ("aarch64", "arm64", "armhf", "i386", "i686")
    elif arch in ("aarch64", "arm64"):
        wanted, rejected = ("aarch64", "arm64"), ("x86_64", "amd64", "i386", "i686")
    else:
        return False
    return not any(x in name for x in rejected) and (
        any(x in name for x in wanted) or not any(x in name for x in ("arm", "x86", "amd", "i386", "i686"))
    )

def _release_asset(assets):
    candidates = []
    for asset in assets:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or asset.get("download_url") or "")
        if not re.search(r"(?i)\.appimage$", name) or not url.startswith("https://"):
            continue
        if _arch_match(name):
            candidates.append((name, url))
    if len(candidates) == 1:
        return candidates[0][1]
    host_arch = platform.machine().lower()
    if not candidates:
        raise ValueError(
            f"Expected one compatible AppImage release asset; found 0 "
            f"(host architecture: {host_arch})"
        )
    raise ValueError(
        "Expected one compatible AppImage release asset; found "
        f"{len(candidates)} ({', '.join(name for name, _ in candidates)}); "
        "the upstream release does not identify a single installable AppImage"
    )

def tracked_app_id(info):
    """Stable registry identity for one AppImage app.

    Mirrors the key the git-release tracker uses so version records line up
    with an app across installs. The catalog ``id`` (``appimage.community.*``)
    is stable across refreshes; fall back to a slug of the display name for any
    entry lacking it. Returns "" when no stable identity can be derived.
    """
    app_id = str(info.get("id") or "").strip()
    if app_id:
        return app_id
    name = str(info.get("name") or "").strip()
    if not name:
        return ""
    slug = "".join(c if c.isalnum() else "-" for c in name.casefold()).strip("-")
    return "appimage.community." + slug if slug else ""


def resolve_download(info):
    """Return (asset URL, repository URL, release tag) with on-demand API calls.

    A link whose forge repository no longer exists must not abort the whole
    resolution: community feed entries routinely carry several links and only
    one of them has to still publish an AppImage. If none does, the combined
    failure is raised so the caller can report why nothing was installable.
    """
    links = info.get("appimage_links") or []
    failures = []
    for raw in links:
        url = str(raw)
        parsed = urlparse(url)
        if parsed.scheme != "https":
            continue
        if re.search(r"(?i)\.appimage$", parsed.path):
            return url, "", ""
        parts = [p for p in parsed.path.split("/") if p]
        try:
            if parsed.hostname in ("github.com", "www.github.com") and len(parts) >= 2:
                owner, repo = parts[:2]
                if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in (owner, repo)):
                    continue
                release = _get_json(f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
                return _release_asset(release.get("assets", [])), f"https://github.com/{owner}/{repo}", str(release.get("tag_name") or "")
            if parsed.hostname == "codeberg.org" and len(parts) >= 2:
                owner, repo = parts[:2]
                if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in (owner, repo)):
                    continue
                release = _get_json(f"https://codeberg.org/api/v1/repos/{owner}/{repo}/releases/latest")
                return _release_asset(release.get("assets", [])), f"https://codeberg.org/{owner}/{repo}", str(release.get("tag_name") or "")
        except ValueError as exc:
            failures.append(f"{url}: {exc}")
            continue
    if failures:
        raise ValueError("No installable AppImage release found — " + " | ".join(failures))
    raise ValueError("No supported direct AppImage download or GitHub/Codeberg release link")

def _download_appimage(url, dest_path):
    """Download one AppImage to dest_path and validate it as an ELF AppImage."""
    req = Request(url, headers={"User-Agent": "LinuxToys AppImage Installer"})
    try:
        with urlopen(req, timeout=40) as response, dest_path.open("wb") as target:
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_APPIMAGE_BYTES:
                    raise ValueError("AppImage download exceeds 4 GiB")
                target.write(chunk)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(_http_failure_text(url, exc)) from exc
    if dest_path.stat().st_size < 4096:
        raise ValueError("Downloaded AppImage is unexpectedly small")
    with dest_path.open("rb") as handle:
        header = handle.read(4)
    if header != b"\x7fELF":
        raise ValueError("Downloaded asset is not an ELF AppImage")

@contextlib.contextmanager
def download_for_install(info):
    url, repository, version = resolve_download(info)
    with tempfile.TemporaryDirectory(prefix="linuxtoys-appimage-") as directory:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", str(info.get("name") or "AppImage")).strip(".-")[:80]
        path = Path(directory) / f"{safe_name or 'AppImage'}.AppImage"
        _download_appimage(url, path)
        yield str(path), {
            "repository": repository,
            "version": version,
            "download_url": url,
            "app_id": tracked_app_id(info),
        }


def resolve_for_update(app_id, repository, output_path):
    """Resolve and download the latest AppImage for a tracked app to output_path.

    Used by the system updater to refresh a previously installed AppImage. The
    repository alone is enough to re-resolve the newest release; ``app_id`` only
    re-labels the metadata so the recorded identity stays stable. Returns the
    release dict (repository, version, download_url, app_id).
    """
    info = {
        "id": app_id,
        "name": app_id,
        "appimage_links": [repository],
    }
    url, resolved_repo, version = resolve_download(info)
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _download_appimage(url, dest)
    return {
        "repository": resolved_repo or repository,
        "version": version,
        "download_url": url,
        "app_id": app_id,
    }


if __name__ == "__main__":
    import sys

    # CLI used by the system updater to refresh one tracked AppImage.
    #   appimage_catalog.py --resolve-for-update APP_ID REPOSITORY OUTPUT_PATH
    # Prints the resolved version on stdout; the caller installs OUTPUT_PATH.
    if len(sys.argv) == 5 and sys.argv[1] == "--resolve-for-update":
        try:
            release = resolve_for_update(sys.argv[2], sys.argv[3], sys.argv[4])
        except Exception as exc:
            print(f"{exc}", file=sys.stderr)
            sys.exit(1)
        print(release.get("version") or "")
        sys.exit(0)
    sys.exit(2)
