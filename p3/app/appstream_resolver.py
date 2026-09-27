"""Conservative native package correction for AppStream metadata."""

from functools import lru_cache
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET


_APT_RDEPENDS_FLAGS = (
    "--no-recommends",
    "--no-suggests",
    "--no-conflicts",
    "--no-breaks",
    "--no-replaces",
    "--no-enhances",
)

_PACKAGE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+_.@:-]*")


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


def _run(args, timeout=8):
    env = os.environ.copy()
    # Package-manager output is parsed below; force stable field names/output.
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    try:
        result = subprocess.run(
            args,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def _dedupe(values, original):
    seen = set()
    out = []
    original_cf = original.casefold()
    for value in values:
        value = str(value or "").strip()
        if not value or value.casefold() == original_cf:
            continue
        if not _PACKAGE_RE.fullmatch(value):
            continue
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            out.append(value)
    return tuple(out)


def _apt_reverse_dependencies(package):
    if shutil.which("apt-cache") is None:
        return ()
    output = _run(["apt-cache", "rdepends", *_APT_RDEPENDS_FLAGS, package])
    if output is None:
        return ()

    candidates = []
    for raw_line in output.splitlines():
        line = raw_line.strip().lstrip("|").strip()
        if not line or line.casefold() == "reverse depends:":
            continue
        if re.fullmatch(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9][a-z0-9-]*)?", line):
            candidates.append(line.split(":", 1)[0])
    return _dedupe(candidates, package)


def _pacman_reverse_dependencies(package):
    """Query required-by relationships from pacman's sync databases."""
    if shutil.which("pacman") is None:
        return ()
    output = _run(["pacman", "-Sii", "--", package])
    if output is None:
        return ()

    candidates = []
    collecting = False
    for raw_line in output.splitlines():
        if re.match(r"^Required By\s*:", raw_line):
            collecting = True
            value = raw_line.split(":", 1)[1].strip()
        elif collecting and raw_line[:1].isspace():
            value = raw_line.strip()
        else:
            collecting = False
            continue

        if value and value != "None":
            candidates.extend(value.split())
    return _dedupe(candidates, package)


def _dnf_reverse_dependencies(package):
    """Query hard reverse dependencies from DNF5 or DNF4 repositories."""
    if shutil.which("dnf5"):
        output = _run([
            "dnf5", "--quiet", "repoquery",
            "--whatrequires", package,
            "--exactdeps",
            "--qf", "%{name}",
        ])
    elif shutil.which("dnf"):
        output = _run([
            "dnf", "--quiet", "repoquery",
            "--whatrequires", package,
            "--exactdeps",
            "--qf", "%{name}",
        ])
    else:
        return ()

    if output is None:
        return ()
    return _dedupe((line.strip() for line in output.splitlines()), package)


def _zypper_reverse_dependencies(package):
    """Use zypper's XML search output to avoid localized table parsing."""
    if shutil.which("zypper") is None:
        return ()
    output = _run([
        "zypper", "--non-interactive", "--xmlout",
        "search", "--type", "package", "--requires-pkg",
        "--match-exact", package,
    ])
    if output is None:
        return ()

    try:
        root = ET.fromstring(output)
    except ET.ParseError:
        return ()

    candidates = []
    for node in root.iter():
        # `solvable` is the package record emitted by zypper search --xmlout.
        if node.tag.rsplit("}", 1)[-1] != "solvable":
            continue
        name = node.attrib.get("name", "").strip()
        if name:
            candidates.append(name)
    return _dedupe(candidates, package)


def _eopkg_reverse_dependencies(package):
    """Solus exposes repository reverse dependencies through `eopkg info`."""
    if shutil.which("eopkg") is None:
        return ()
    output = _run(["eopkg", "info", package])
    if output is None:
        return ()

    candidates = []
    collecting = False
    for raw_line in output.splitlines():
        match = re.match(r"^Reverse Dependencies\s*:\s*(.*)$", raw_line)
        if match:
            collecting = True
            value = match.group(1).strip()
        elif collecting and raw_line[:1].isspace():
            value = raw_line.strip()
        else:
            collecting = False
            continue

        if value and value.casefold() not in {"none", "n/a"}:
            candidates.extend(value.split())
    return _dedupe(candidates, package)


def _reverse_dependencies(package):
    # Detection is deliberately by the native package-manager query tool rather
    # than distro name, so derivatives follow their actual package ecosystem.
    if shutil.which("apt-cache"):
        return _apt_reverse_dependencies(package)
    if shutil.which("pacman"):
        return _pacman_reverse_dependencies(package)
    if shutil.which("dnf5") or shutil.which("dnf"):
        return _dnf_reverse_dependencies(package)
    if shutil.which("zypper"):
        return _zypper_reverse_dependencies(package)
    if shutil.which("eopkg"):
        return _eopkg_reverse_dependencies(package)
    return ()


@lru_cache(maxsize=512)
def _resolve_cached(package, identities):
    candidates = _reverse_dependencies(package)
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

    Supports APT, pacman, DNF/DNF5, zypper and eopkg. If the host has no
    read-only repository reverse-dependency query available, AppStream's
    original package is retained.
    """
    package = str(package or "").strip()
    if not package:
        return package

    identities = _identities(component_id, desktop_id, name)
    return _resolve_cached(package, identities)
