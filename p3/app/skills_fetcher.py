#!/usr/bin/env python3
"""
Skills Fetcher — busca skills em skills.sh sem autenticação.
Usado pelo script skills-seeker.sh via linha de comando.
"""
import sys
import os
import json
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
