#!/usr/bin/env python3
"""
Skills Fetcher — busca skills em skills.sh sem autenticação.
Usado pelo script skills-seeker.sh via linha de comando.
"""
import sys
import os
import json
import html
import re
import time
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_DIR = os.path.expanduser("~/.cache/linuxtoys/skills_cache")
CACHE_TTL = 3600
CACHE_MAX_FILES = 200
API_BASE = "https://skills.sh"


def _cache_path(key):
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', key)
    return os.path.join(CACHE_DIR, f"{safe}.json")


def _cache_get(key):
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        ttl = data.get("ttl", CACHE_TTL)
        if time.time() - data.get("ts", 0) > ttl:
            return None
        return data.get("value")
    except (json.JSONDecodeError, ValueError):
        _cache_evict(path)
        return None
    except Exception:
        return None


def _cache_set(key, value, ttl=None):
    path = _cache_path(key)
    _cache_evict_if_full()
    try:
        payload = {"ts": time.time(), "value": value}
        if ttl is not None:
            payload["ttl"] = ttl
        with open(path, 'w') as f:
            json.dump(payload, f)
    except Exception:
        pass


def _cache_evict(path):
    try:
        os.remove(path)
    except Exception:
        pass


def _cache_evict_if_full():
    try:
        files = [
            os.path.join(CACHE_DIR, f)
            for f in os.listdir(CACHE_DIR)
            if f.endswith(".json")
        ]
        if len(files) >= CACHE_MAX_FILES:
            files.sort(key=lambda p: os.path.getmtime(p))
            for old in files[: len(files) - CACHE_MAX_FILES + 10]:
                _cache_evict(old)
    except Exception:
        pass


def _fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "LinuxToys/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, resp.read().decode("utf-8")
    except Exception:
        return False, None


def search_skills(query, limit=20):
    cache_key = f"search_{query}_{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    url = f"{API_BASE}/api/search?q={urllib.parse.quote(query)}&limit={limit}"
    ok, text = _fetch(url)
    if not ok:
        _cache_set(cache_key, {"query": query, "skills": []}, ttl=60)
        return {"query": query, "skills": []}
    try:
        data = json.loads(text)
    except Exception:
        return {"query": query, "skills": []}
    skills = []
    for s in data.get("skills", []):
        skills.append({
            "id": s.get("id", ""),
            "skillId": s.get("skillId", ""),
            "name": s.get("name", ""),
            "installs": s.get("installs", 0),
            "source": s.get("source", ""),
        })
    result = {"query": data.get("query", query), "skills": skills}
    _cache_set(cache_key, result)
    return result


def _page_description(page_text: str) -> str:
    """Best-effort description from a skill page's description meta tag.

    The server-rendered skill page carries the summary in the standard
    ``<meta name="description">``/``og:description`` tag (HTML-escaped).
    Returns an empty string when the tag is missing, so callers degrade
    to the identity fields instead of failing.
    """
    match = re.search(
        r'<meta[^>]+(?:name="description"|property="og:description")'
        r'[^>]*\bcontent="([^"]*)"',
        page_text,
        re.I,
    )
    if match is None:
        return ""
    return html.unescape(match.group(1)).strip()


def detail_skills(source: str, slug: str) -> dict:
    """Fetch one skill's record for the Details dialog.

    skills.sh serves the full record (file tree with contents) only on
    the OIDC-authenticated ``/api/v1`` endpoint, which a desktop client
    cannot use. The unauthenticated surfaces are the search API and the
    server-rendered skill page, so this composes both: the search entry
    carries identity and install count, the page's description meta tag
    carries the summary. The ``files`` list stays empty until upstream
    exposes an unauthenticated file tree.

    Args:
        source: Skill source (the id's part before the last ``/``).
        slug: Skill slug (the id's last segment).

    Returns:
        Dict with ``id``, ``skillId``, ``name``, ``source``,
        ``installs``, ``description`` and ``files``. Cached for the
        regular TTL.

    Raises:
        RuntimeError: When the skill cannot be resolved on skills.sh
            (offline, unknown skill). ``main`` reports that as a failed
            fetch (exit 1) so callers show their error dialog instead
            of an empty detail view.
    """
    cache_key = f"detail_{source}/{slug}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    skill_id = f"{source}/{slug}"
    entry = None
    ok, text = _fetch(
        f"{API_BASE}/api/search?q={urllib.parse.quote(slug)}&limit=30"
    )
    if ok:
        try:
            for s in json.loads(text).get("skills", []):
                if s.get("id", "") == skill_id:
                    entry = s
                    break
        except Exception:
            entry = None
    if entry is None:
        raise RuntimeError(f"skill not found: {skill_id}")

    description = ""
    ok, text = _fetch(
        f"{API_BASE}/{urllib.parse.quote(source, safe='/')}"
        f"/{urllib.parse.quote(slug, safe='/')}",
        timeout=15,
    )
    if ok:
        description = _page_description(text)

    result = {
        "id": entry.get("id", skill_id),
        "skillId": entry.get("skillId", slug),
        "name": entry.get("name", ""),
        "source": entry.get("source", source),
        "installs": entry.get("installs", 0),
        "description": description,
        "files": [],
    }
    if description:
        _cache_set(cache_key, result)
    else:
        # The page enrich failed (transient network); cache briefly so the
        # next view retries the description instead of keeping an empty one.
        _cache_set(cache_key, result, ttl=60)
    return result


def _search_worker(term, limit=10, timeout=8):
    try:
        data = search_skills(term, limit)
        return data.get("skills", []), True
    except Exception:
        return [], False


POPULAR_TERMS = ["git", "claude", "docker", "python", "typescript", "github", "testing", "react"]


def fetch_popular(limit=50):
    cache_key = f"popular_{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    seen = {}
    network_ok = False
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_search_worker, term, 10, 8): term for term in POPULAR_TERMS}
        for future in as_completed(futures):
            try:
                skills, ok = future.result()
                if ok:
                    network_ok = True
                for s in skills:
                    sid = s.get("id", "")
                    if sid and sid not in seen:
                        seen[sid] = s
            except Exception:
                continue
    if not network_ok:
        return {"view": "popular", "skills": []}
    skills = sorted(seen.values(), key=lambda x: x.get("installs", 0), reverse=True)[:limit]
    result = {"view": "popular", "skills": skills}
    _cache_set(cache_key, result)
    return result


def _is_network_ok(timeout=5):
    url = f"{API_BASE}/api/search?q=test&limit=1"
    ok, _ = _fetch(url, timeout=timeout)
    return ok


def _repair_empty_cache():
    if not _is_network_ok():
        return
    try:
        for f in os.listdir(CACHE_DIR):
            if not f.endswith(".json"):
                continue
            path = os.path.join(CACHE_DIR, f)
            try:
                with open(path, "r") as fh:
                    data = json.load(fh)
                value = data.get("value", {})
                if value.get("skills") == []:
                    _cache_evict(path)
            except Exception:
                continue
    except Exception:
        pass


def clear_cache():
    try:
        for f in os.listdir(CACHE_DIR):
            os.remove(os.path.join(CACHE_DIR, f))
    except Exception:
        pass


def main():
    _repair_empty_cache()
    if len(sys.argv) < 2:
        print("Usage: skills_fetcher.py <command> [args...]", file=sys.stderr)
        sys.exit(1)
    cmd = sys.argv[1]
    try:
        if cmd == "search":
            query = sys.argv[2] if len(sys.argv) > 2 else ""
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
            result = search_skills(query, limit)
        elif cmd == "detail":
            source = sys.argv[2] if len(sys.argv) > 2 else ""
            slug = sys.argv[3] if len(sys.argv) > 3 else ""
            result = detail_skills(source, slug)
        elif cmd == "popular":
            result = fetch_popular(int(sys.argv[2]) if len(sys.argv) > 2 else 50)
        elif cmd == "clear_cache":
            clear_cache()
            result = {"ok": True}
        else:
            print(f"Unknown command: {cmd}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
