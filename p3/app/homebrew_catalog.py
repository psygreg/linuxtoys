"""Homebrew core formula snapshot for the shared AppStream-style catalog."""
from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

from . import _catalog_rs

CACHE_DIR = Path(os.path.expanduser("~/.cache/linuxtoys/homebrew-catalog"))
FORMULA_PATH = CACHE_DIR / "formula.json"
SIGNAL_PATH = CACHE_DIR / "source-changed"
API_URL = "https://formulae.brew.sh/api/formula.json"
POPULARITY_URL = "https://formulae.brew.sh/api/analytics/install-on-request/homebrew-core/365d.json"
MAX_AGE = 14 * 24 * 60 * 60
MAX_BYTES = 64 * 1024 * 1024
_LOCK = threading.RLock()
logger = logging.getLogger(__name__)
_VALIDATED_SNAPSHOT = None




def brew_executable():
    """Discover Brew without relying on a desktop session's inherited PATH."""
    prefix = os.environ.get("HOMEBREW_PREFIX", "")
    candidates = [
        shutil.which("brew"),
        os.path.join(prefix, "bin", "brew") if prefix else None,
        "/home/linuxbrew/.linuxbrew/bin/brew",
        os.path.expanduser("~/.linuxbrew/bin/brew"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return os.path.abspath(candidate)
    return None


def enabled():
    # Presence is authoritative. No opt-in flag can leave a removed Brew enabled.
    return brew_executable() is not None


def linux_arch():
    machine = platform.machine().lower()
    return {"amd64": "x86_64", "aarch64": "arm64"}.get(machine, machine)


def availability_fingerprint():
    executable = brew_executable()
    try:
        signal = SIGNAL_PATH.stat().st_mtime_ns
    except OSError:
        signal = 0
    return (executable, signal)


def fingerprint():
    executable = brew_executable()
    if executable is None:
        return "unavailable"
    try:
        st = FORMULA_PATH.stat()
        snapshot = (st.st_size, st.st_mtime_ns)
    except OSError:
        snapshot = None
    try:
        st = (CACHE_DIR / "popularity.json").stat()
        popularity = (st.st_size, st.st_mtime_ns)
    except OSError:
        popularity = None
    return json.dumps([executable, linux_arch(), snapshot, popularity], separators=(",", ":"))


def _valid_rows(rows):
    return isinstance(rows, list) and bool(rows) and all(
        isinstance(row, dict) and isinstance(row.get("name"), str)
        and bool(row["name"].strip()) for row in rows
    )


def valid_snapshot():
    """Validate cached metadata on a worker, including empty/corrupt snapshots."""
    global _VALIDATED_SNAPSHOT
    try:
        stat = FORMULA_PATH.stat()
        token = (os.fspath(FORMULA_PATH), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if _VALIDATED_SNAPSHOT == token:
            return True
        if not 0 < stat.st_size <= MAX_BYTES:
            return False
        valid = _catalog_rs.AppStreamGeneration.homebrew_snapshot_valid(
            os.fspath(FORMULA_PATH), MAX_BYTES)
        if valid:
            _VALIDATED_SNAPSHOT = token
        return valid
    except (OSError, ValueError, UnicodeError):
        return False


def cached_path():
    """Return valid local metadata; never download. Call on a worker."""
    return FORMULA_PATH if enabled() and valid_snapshot() else None


def binary_snapshot_available():
    """Cheap UI readiness check; the worker performs full binary validation."""
    if not enabled():
        return False
    try:
        source = FORMULA_PATH.stat()
        binary = FORMULA_PATH.with_suffix(f".{linux_arch()}.bin").stat()
        return source.st_size > 0 and binary.st_size > 0 and binary.st_mtime_ns >= source.st_mtime_ns
    except OSError:
        return False


def needs_refresh():
    if not enabled():
        return False
    if not valid_snapshot():
        return True
    try:
        return (time.time() - FORMULA_PATH.stat().st_mtime >= MAX_AGE
                or SIGNAL_PATH.exists() and SIGNAL_PATH.stat().st_mtime_ns > FORMULA_PATH.stat().st_mtime_ns)
    except OSError:
        return True


def load_or_refresh(force=False):
    """Fetch only with Brew present; retain the last valid snapshot on failure."""
    if not enabled():
        return None
    with _LOCK:
        try:
            fresh = not needs_refresh()
        except OSError:
            fresh = False
        if force or not fresh:
            temporary = None
            try:
                if not enabled():
                    return None
                request = Request(API_URL, headers={"User-Agent": "LinuxToys", "Accept": "application/json"})
                with urlopen(request, timeout=30) as response:
                    data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("Homebrew metadata exceeds the size limit")
                rows = json.loads(data)
                if not _valid_rows(rows):
                    raise ValueError("Invalid Homebrew formula metadata")
                if not enabled():
                    return None
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(prefix="formula-", dir=CACHE_DIR)
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, FORMULA_PATH)
                temporary = None
            except Exception as error:
                logger.warning("Homebrew metadata refresh failed; retaining cached data: %s", error)
            finally:
                if temporary:
                    try:
                        os.unlink(temporary)
                    except OSError:
                        pass
        return cached_path()


def _popularity_counts(payload):
    formulae = payload.get("formulae") if isinstance(payload, dict) else None
    if not isinstance(formulae, dict) or not formulae:
        raise ValueError("Invalid Homebrew analytics metadata")
    counts = {}
    for name, records in formulae.items():
        if not isinstance(name, str) or not isinstance(records, list):
            continue
        total = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            count = str(record.get("count", "")).replace(",", "").strip()
            if count.isdigit():
                total += int(count)
        counts[name] = total
    if not counts:
        raise ValueError("Empty Homebrew analytics metadata")
    return counts


def refresh_popularity(force=False):
    """Fetch requested-install totals on a worker, retaining previous rankings."""
    if not enabled():
        return
    path = CACHE_DIR / "popularity.json"
    with _LOCK:
        temporary = None
        try:
            if not force and path.is_file() and time.time() - path.stat().st_mtime < MAX_AGE:
                try:
                    with path.open(encoding="utf-8") as handle:
                        cached = json.load(handle)
                except (OSError, ValueError):
                    cached = None
                if isinstance(cached, dict) and cached and all(
                        isinstance(v, int) and v >= 0 for v in cached.values()):
                    return
            request = Request(POPULARITY_URL, headers={"User-Agent": "LinuxToys", "Accept": "application/json"})
            with urlopen(request, timeout=30) as response:
                data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("Homebrew analytics exceeds the size limit")
            counts = _popularity_counts(json.loads(data))
            if not enabled():
                return
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix="popularity-", dir=CACHE_DIR)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(counts, handle, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            temporary = None
        except Exception as error:
            logger.warning("Homebrew popularity refresh failed; retaining cached rankings: %s", error)
        finally:
            if temporary:
                os.unlink(temporary)


def installed_names():
    """Observe all formulae, including packages installed outside LinuxToys."""
    executable = brew_executable()
    if not executable:
        return set()
    try:
        result = subprocess.run(
            [executable, "list", "--formula", "-1"], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=60,
            check=False, env={**os.environ, "HOMEBREW_NO_AUTO_UPDATE": "1"},
        )
        if result.returncode:
            return set()
        return {line.strip().casefold() for line in result.stdout.splitlines() if line.strip()}
    except (OSError, subprocess.SubprocessError):
        return set()


def materialize_install(info):
    """Create a script only for the queued formula, using normal shell helpers."""
    name = str(info.get("homebrew_name") or info.get("package-name") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+_.@-]*", name):
        raise ValueError("Invalid Homebrew formula name")
    fd, path = tempfile.mkstemp(prefix="linuxtoys-homebrew-", suffix=".sh")
    import shlex
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write('#!/bin/bash\nset -eo pipefail\nsource "$SCRIPT_DIR/libs/linuxtoys.bash"\n'
                     'source "$SCRIPT_DIR/libs/packages.bash"\n'
                     f'pkg_brew {shlex.quote(name)}\n')
    os.chmod(path, 0o700)
    payload = dict(info)
    payload["path"] = path
    return payload
