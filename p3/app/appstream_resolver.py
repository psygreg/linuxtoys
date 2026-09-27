"""Conservative native package correction for AppStream metadata."""

from functools import lru_cache
import re
import shutil
import subprocess


_APT_RDEPENDS_FLAGS = (
    "--no-recommends",
    "--no-suggests",
    "--no-conflicts",
    "--no-breaks",
    "--no-replaces",
    "--no-enhances",
)


def _identity(value, *, desktop=False):
    value = str(value or "").strip().casefold()
    if not value:
        return ""
    if desktop and value.endswith(".desktop"):
        value = value[:-8]
    # AppStream component IDs are frequently desktop IDs. Do not strip an
    # arbitrary reverse-DNS prefix: doing so would turn identity matching into
    # fuzzy guessing. Only normalize separators that package names commonly use.
    value = re.sub(r"[\s_]+", "-", value)
    return value


def _identities(component_id=None, desktop_id=None, name=None):
    values = {
        _identity(component_id, desktop=True),
        _identity(desktop_id, desktop=True),
        _identity(name),
    }
    values.discard("")
    return frozenset(values)


def _apt_reverse_dependencies(package):
    if shutil.which("apt-cache") is None:
        return ()

    try:
        result = subprocess.run(
            ["apt-cache", "rdepends", *_APT_RDEPENDS_FLAGS, package],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ()

    if result.returncode != 0:
        return ()

    candidates = []
    seen = set()
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip().lstrip("|").strip()
        if not line or line == package or line.casefold() == "reverse depends:":
            continue
        # apt-cache can annotate dependency alternatives. Keep only actual
        # Debian binary package names and ignore virtual/formatting records.
        if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9][a-z0-9-]*)?", line):
            continue
        candidate = line.split(":", 1)[0]
        if candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)
    return tuple(candidates)


@lru_cache(maxsize=512)
def _resolve_cached(package, identities):
    candidates = _apt_reverse_dependencies(package)
    if not candidates:
        return package

    exact = [candidate for candidate in candidates if _identity(candidate) in identities]
    if len(exact) == 1:
        return exact[0]

    # A sole hard reverse dependency is still an unambiguous promotion even
    # when AppStream's human-readable identity differs from the distro name.
    if len(candidates) == 1:
        return candidates[0]

    # Multiple candidates without one exact AppStream identity are ambiguous.
    return package


def resolve_native_appstream_package(package, *, component_id=None, desktop_id=None, name=None):
    """Return a conservatively corrected native package name.

    Currently APT is the only implemented backend. Other package managers keep
    AppStream's package unchanged until an equivalent read-only reverse-
    dependency query is implemented and tested for them.
    """
    package = str(package or "").strip()
    if not package:
        return package

    identities = _identities(component_id, desktop_id, name)
    return _resolve_cached(package, identities)
