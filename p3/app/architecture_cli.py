#!/usr/bin/env python3
"""Small shell entry point for the shared architecture policy; exits 1 on refusal."""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.architecture import (
    ArchitectureError,
    asset_architectures,
    canonical_package_architecture,
    host,
    label,
    normalize,
    pkgbuild_architectures,
    pkgbuild_builds_natively,
    require_native,
    require_script_path,
    resolve_hook_path,
    select_asset,
)
from app.architecture_files import validate_files, validate_tree
from app.architecture_flatpak import extension_plan, resolve_refs


# AUR metadata endpoints. pacman's sync databases never cover the AUR, so the
# RPC is the authoritative existence source for AUR-only targets; the RPC does
# not expose an arch field, so the PKGBUILD's static arch array is the ISA
# evidence (architecture.pkgbuild_architectures reads it without evaluating it).
_AUR_RPC_URL = "https://aur.archlinux.org/rpc/v5/info"
_AUR_PKGBUILD_URL = "https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD"
_AUR_HEADERS = {"User-Agent": "LinuxToys-Architecture-preflight"}
_AUR_REQUEST_TIMEOUT = 30
_AUR_NAME = re.compile(r"[A-Za-z0-9@._+:-]+")

# Deadline for the one metadata-fetching retry of the cache-only package
# preflights: repo metadata for a freshly added repository can be slow on
# metered or distant mirrors, so this is deliberately longer than the cache
# listing's 30 s.
_METADATA_FETCH_TIMEOUT = 120


def _aur_get(url: str) -> bytes:
    """Fetch one HTTPS AUR resource; every failure raises ArchitectureError."""
    request = urllib.request.Request(url, headers=_AUR_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=_AUR_REQUEST_TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ArchitectureError(f"Could not fetch {url}: {error}") from error


def _aur_rpc_info(package: str) -> list[dict[str, Any]]:
    """Return the AUR RPC info records for one exact package name."""
    url = f"{_AUR_RPC_URL}?arg[]={urllib.parse.quote(package, safe='')}"
    try:
        payload = json.loads(_aur_get(url).decode("utf-8", "replace"))
    except ValueError as error:
        raise ArchitectureError(
            f"The AUR metadata for {package} is unreadable"
        ) from error
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise ArchitectureError(f"The AUR metadata for {package} is unreadable")
    return [item for item in results if isinstance(item, dict)]


def _aur_candidate(package: str, machine: str) -> None:
    """Preflight one AUR-only package before the paru/pamac build route.

    ``pacman -Si`` is authoritative for sync repositories and never covers the
    AUR, so a missing target is an AUR-only candidate exactly where
    ``pkg_install`` routes one to a helper build (the pacman-driven arch
    family; SteamOS-family hosts have no AUR route). Existence is verified
    against the AUR RPC and the PKGBUILD's static ``arch`` array against the
    host; anything unreadable, foreign or missing is refused before a helper
    could attempt the build.
    """
    try:
        from app.compat import native_package_family
    except ImportError as error:  # staged preflights never take this route
        raise ArchitectureError(
            f"The AUR route could not be verified for {package}: {error}"
        ) from error
    if native_package_family() != "arch":
        raise ArchitectureError(f"No available package metadata for {package}")
    if not _AUR_NAME.fullmatch(package):
        raise ArchitectureError(f"Unsafe AUR package name: {package!r}")
    matches = [
        item for item in _aur_rpc_info(package) if item.get("Name") == package
    ]
    if not matches:
        raise ArchitectureError(
            f"{package} is not available from the pacman repositories or the AUR"
        )
    pkgbase = matches[0].get("PackageBase")
    if not isinstance(pkgbase, str) or not _AUR_NAME.fullmatch(pkgbase):
        raise ArchitectureError(f"The AUR package base for {package} is unreadable")
    pkgbuild = _aur_get(
        f"{_AUR_PKGBUILD_URL}?h={urllib.parse.quote(pkgbase, safe='')}"
    ).decode("utf-8", "replace")
    declared = pkgbuild_architectures(pkgbuild)
    if declared is None:
        raise ArchitectureError(
            f"The AUR PKGBUILD for {package} has no readable arch array"
        )
    if not declared:
        raise ArchitectureError(
            f"The AUR PKGBUILD for {package} declares no architectures"
        )
    if not pkgbuild_builds_natively(declared, machine):
        raise ArchitectureError(
            f"No native candidate for {package} in the AUR: PKGBUILD arch="
            + ", ".join(declared)
        )


def apt_plan(packages: list[str]) -> None:
    """Validate APT's complete simulated installation plan, including dependencies."""
    try:
        result = subprocess.run(
            ["apt-get", "--simulate", "--no-remove", "install", *packages],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "LC_ALL": "C"},
        )
    except subprocess.TimeoutExpired as error:
        raise ArchitectureError(
            f"apt did not finish planning the install of {', '.join(packages)} "
            "within 60s"
        ) from error
    except subprocess.CalledProcessError as error:
        # A bare exit status says nothing: apt reports what it could not
        # satisfy on stdout (the unmet-dependencies table) and stderr, both
        # captured here. The refusal must carry the actual reason so an
        # unavailable dependency is diagnosable instead of reading as a
        # refused or unverified payload. The diagnostic subclass lets the
        # caller annotate unresolvable names without tagging infrastructure
        # failures (timeouts) with repository advice.
        raise _AptPlanDiagnostic(
            f"apt cannot plan the install of {', '.join(packages)}: "
            + _apt_plan_diagnostics(error)
        ) from error
    for line in (result.stdout or "").splitlines():
        if not line.startswith("Inst "):
            continue
        package = line.split()[1]
        if ":" in package:
            require_native([canonical_package_architecture(package.rsplit(":", 1)[1])])
        # Newer APT (e.g. Debian 13) appends an optional trailing reason group
        # after the closing paren: "... Debian:13.7/stable [amd64]) []".
        match = re.search(r"\[([^] ]+)\]\)(?:\s*\[[^]]*\])?\s*$", line)
        if not match:
            raise ArchitectureError(
                f"APT did not identify the planned architecture for {package}"
            )
        if match[1] != "all":
            require_native([canonical_package_architecture(match[1])])


def _apt_plan_diagnostics(error: subprocess.CalledProcessError) -> str:
    """Extract apt's legible problem report from a failed simulation.

    The resolution problem lands on stdout (apt's unmet-dependencies table)
    and its summary on stderr; stdout otherwise carries planner noise. Keep
    every E:/W: line plus the "The following ..." report to its end, so the
    refusal names the packages and constraints apt could not satisfy.
    """
    problem: list[str] = []
    for stream in (error.stderr or "", error.stdout or ""):
        reporting = False
        for raw in stream.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith(("E:", "W:")):
                problem.append(line)
                reporting = False
                continue
            if line.startswith("The following "):
                reporting = True
            if reporting:
                problem.append(line)
    if problem:
        return " ".join(problem)
    return f"apt exited with status {error.returncode}"


def _tool_diagnostics(
    error: subprocess.CalledProcessError | subprocess.TimeoutExpired,
) -> str:
    """Summarize a failed metadata tool's captured output for a refusal.

    The bare exit status says nothing: managers print their reason ("E: No
    packages found", "package 'x' not found", repository/network failures)
    on stdout or stderr. Keep the informative lines so the refusal names the
    actual problem; fall back to the status when the tool stayed silent.
    """
    lines: list[str] = []
    for stream in (error.stderr, error.stdout):
        if isinstance(stream, bytes):
            stream = stream.decode("utf-8", "replace")
        if stream:
            lines.extend(line.strip() for line in stream.splitlines() if line.strip())
    summary = " | ".join(lines[-6:]) if lines else None
    if isinstance(error, subprocess.TimeoutExpired):
        return f"timed out after {error.timeout}s" + (f": {summary}" if summary else "")
    if summary:
        return summary
    status = getattr(error, "returncode", None)
    return f"exit status {status}" if status is not None else "no output captured"


class _AptPlanDiagnostic(ArchitectureError):
    """apt's own unmet-dependency report, not an infrastructure failure.

    The caller annotates unresolvable package names with repository guidance;
    a planning timeout is an infrastructure failure and must stay unannotated.
    """


def _apt_lists_state() -> str:
    """Classify APT's package-list state for unavailable-package reports.

    The cache-only queries read whatever ``apt-get update`` last downloaded;
    a host whose lists were never synced (fresh system, wiped or repeatedly
    failing update) hides every package, not just an unavailable one. The
    list directory is world-readable, so the probe stays unprivileged and
    honors the configured ``Dir::State::lists`` path — ``apt-config`` reports
    that option relative to ``Dir::State`` by default (``lists/``), so the
    two are joined the way apt itself resolves them.
    """
    values: dict[str, str] = {}
    try:
        result = subprocess.run(
            [
                "apt-config", "shell",
                "LT_STATE_DIR", "Dir::State",
                "LT_LISTS", "Dir::State::lists",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "LC_ALL": "C"},
        )
        if result.returncode == 0:
            for match in re.finditer(
                r"^(LT_\w+)='?([^'\n]+)'?", result.stdout, re.M
            ):
                values[match[1]] = match[2]
    except (OSError, subprocess.SubprocessError):
        pass
    state_dir = values.get("LT_STATE_DIR") or "/var/lib/apt"
    if not state_dir.startswith("/"):
        state_dir = "/" + state_dir
    lists = values.get("LT_LISTS") or "lists/"
    if not lists.startswith("/"):
        lists = os.path.join(state_dir, lists)
    if glob.glob(os.path.join(lists.rstrip("/"), "*Packages*")):
        return "present"
    return "absent"


def _apt_unavailable_note(error: ArchitectureError, unlisted: list[str]) -> str:
    """Append the actionable cause to a plan refusal over invisible names.

    The candidate listing cannot see these names at all, so the refusal must
    not claim a native-candidate verdict that was never made: say why the
    plan could not resolve them instead — no downloaded metadata at all, or
    metadata that simply does not carry the package (repository components
    such as Debian's contrib are not enabled by default).
    """
    message = str(error)
    if not unlisted:
        return message
    if _apt_lists_state() == "absent":
        return (
            message
            + " APT package lists are absent on this host: refresh the repository"
            " metadata (apt-get update) and retry."
        )
    return (
        message
        + " APT has no candidate for these names in the configured repositories:"
        " the package may live in a repository component that is not enabled"
        " (Debian: contrib) or require a third-party repository."
    )


def native_packages(packages: list[str], manager: str) -> None:
    """Preflight native package metadata before authentication or transaction locks.

    Manager-reported labels are canonicalized before the ISA gate: optimized
    repositories report microarchitecture levels (CachyOS x86_64_v3/v4 sync
    databases, APT's Architecture-Variant field) that are native x86_64, not
    foreign ISAs. Candidate listings may include foreign-ISA siblings of
    multilib/multiarch same-name packages the manager never selects for a
    bare name, so those require one native or arch-independent candidate;
    explicit foreign requests are refused by the suffix check below.

    pacman's sync databases never cover the AUR: a target pacman cannot see is
    an AUR-only candidate on the pacman-driven arch family (SteamOS-family
    hosts have no AUR route), verified through _aur_candidate instead.

    The cache-only queries cannot see a repository the calling script added
    moments ago: nothing has downloaded its metadata yet, so dnf reports no
    candidate and zypper fails outright although the package is available for
    the host. Those backends get one metadata-fetching retry before any
    refusal: it stays read-only and unprivileged (dnf repoquery / zypper info
    under the invoking user, no transaction lock, no authentication), matches
    the install path's own key-trust policy (--assumeyes mirrors `dnf -y`),
    and the ISA gate below still judges the labels the refreshed metadata
    reports — a genuinely missing package or a foreign-ISA one is refused
    exactly as before, nothing presumes the host ISA.

    APT has no unprivileged metadata fetch, so the candidate listing itself
    never refuses an invisible name: absence from the listing (apt 2.x exits
    silently, apt 3.x reports "No packages found") defers to the simulated
    installation plan, which names the unresolvable target with apt's own
    words — the same verdict the install command would produce — and the
    refusal gains an actionable cause note (no package lists at all, or a
    repository component such as Debian's contrib that is not enabled).
    """
    arch = host()
    for package in packages:
        if package.startswith("-"):
            raise ArchitectureError("Package options are not package names")
        if ":" in package:
            require_native(
                [canonical_package_architecture(package.rsplit(":", 1)[1])], arch.value
            )
        require_native(asset_architectures(package) or [arch.value], arch.value)
    if manager == "apt":
        unlisted: list[str] = []
        for package in packages:
            try:
                candidate = subprocess.run(
                    ["apt-cache", "show", "--no-all-versions", package],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, "LC_ALL": "C"},
                ).stdout
            except subprocess.CalledProcessError:
                # The listing stage only classifies what the cache carries:
                # apt 2.x exits 0 silently and apt 3.x reports "No packages
                # found" for the same absent name. Defer both to the
                # simulated plan below, which carries apt's own reason.
                unlisted.append(package)
                continue
            fields = [
                line.split(":", 1)[1].strip()
                for line in candidate.splitlines()
                if line.startswith("Architecture:")
            ]
            if not fields:
                # Nothing is listed for the bare name: the package is absent
                # from the enabled repositories or purely provided by another
                # package. APT's simulated plan is the authority for both —
                # it either refuses the unresolvable target exactly as the
                # install command would, or selects the provider, whose
                # architecture the plan gate judges like any other payload.
                unlisted.append(package)
                continue
            _require_native_candidate(package, fields, arch.value)
        try:
            apt_plan(packages)
        except _AptPlanDiagnostic as error:
            raise ArchitectureError(
                _apt_unavailable_note(error, unlisted)
            ) from error
    elif manager in {"dnf", "zypper", "pacman", "eopkg"}:
        commands = {
            # dnf5 concatenates the queryformat output of all matching
            # candidates without a separator; the trailing newline keeps one
            # label per candidate line on dnf4 and dnf5 alike.
            "dnf": ["dnf", "--cacheonly", "repoquery", "--qf", "%{arch}\n"],
            "zypper": ["zypper", "--no-refresh", "info"],
            "pacman": ["pacman", "-Si"],
            "eopkg": ["eopkg", "info"],
        }
        # Metadata-fetching retries for the cache-only backends above; the
        # remaining managers (pacman, eopkg) keep their plain refusal paths.
        fetches = {
            "dnf": ["dnf", "--assumeyes", "repoquery", "--qf", "%{arch}\n"],
            "zypper": ["zypper", "--non-interactive", "info"],
        }
        for package in packages:
            result = ""
            try:
                result = subprocess.run(
                    [*commands[manager], package],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, "LC_ALL": "C"},
                ).stdout
            except subprocess.CalledProcessError as error:
                if manager == "pacman":
                    # pacman's sync databases exclude the AUR: a missing target is
                    # an AUR-only candidate on the pacman-driven hosts whose
                    # pkg_install routes it to a paru/pamac build. Verify its AUR
                    # existence and PKGBUILD ISA before the helper runs.
                    _aur_candidate(package, arch.value)
                    continue
                if manager not in fetches:
                    raise ArchitectureError(
                        f"Could not fetch package metadata for {package}: "
                        + _tool_diagnostics(error)
                    ) from error
                result = _fetch_metadata(fetches[manager], package)
            if not result.strip() and manager in fetches:
                result = _fetch_metadata(fetches[manager], package)
            if not result.strip():
                raise ArchitectureError(f"No available package metadata for {package}")
            if manager == "dnf":
                values = result.splitlines()
            else:
                values = [
                    line.split(":", 1)[1].strip()
                    for line in result.splitlines()
                    if line.strip().lower().startswith("architecture") and ":" in line
                ]
            if not values:
                raise ArchitectureError(
                    f"Architecture metadata unavailable for {package}; use an inspected source-build route"
                )
            _require_native_candidate(package, values, arch.value)
    else:
        raise ArchitectureError("Unsupported package preflight backend")


def _fetch_metadata(command: list[str], package: str) -> str:
    """Run one metadata-fetching retry command for a cold-cache package listing.

    Read-only and unprivileged: dnf repoquery / zypper info under the invoking
    user only populate the user metadata cache, never install anything and
    never touch a native transaction lock or credential. Failures are
    ArchitectureErrors with the package named, so the preflight stays
    fail-closed and the refusal stays legible.
    """
    try:
        return subprocess.run(
            [*command, package],
            check=True,
            capture_output=True,
            text=True,
            timeout=_METADATA_FETCH_TIMEOUT,
            env={**os.environ, "LC_ALL": "C"},
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ArchitectureError(
            f"Could not fetch package metadata for {package}: "
            + _tool_diagnostics(error)
        ) from error


def _require_native_candidate(
    package: str, values: Iterable[str], host_arch: str
) -> None:
    """Require one native or arch-independent candidate in manager metadata.

    Candidate listings (apt-cache show, pacman -Si, dnf repoquery) include
    foreign-ISA siblings of multilib/multiarch same-name packages that the
    manager never selects for a bare name; explicit foreign requests are
    refused by native_packages' suffix check. Labels go through the ISA
    authority: manager aliases (amd64) and microarchitecture levels
    (canonical_package_architecture) both count as native x86_64 evidence.
    """
    host = normalize(host_arch).value
    candidates: set[str] = set()
    for value in values:
        value = value.strip()
        if not value or value in {"all", "any", "noarch"}:
            continue
        token = canonical_package_architecture(value)
        try:
            candidates.add(normalize(token).value)
        except ArchitectureError:
            candidates.add(token)
    if not candidates or host in candidates:
        return
    raise ArchitectureError(
        f"No native candidate for {package}: host={host}, "
        f"available={', '.join(sorted(candidates))}"
    )


def snap_packages(packages: list[str]) -> None:
    """Read snapd's host-specific stable candidates before authentication.

    Reuse the catalog's local read-only API. An absent daemon must be configured
    separately; do not bootstrap it before knowing the requested apps exist.
    """
    from app.snap_catalog import _request

    system = _request("/v2/system-info")
    if not isinstance(system, dict):
        raise ArchitectureError("Snap daemon architecture metadata is unavailable")
    require_native([system.get("architecture", "")])
    for package in packages:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", package):
            raise ArchitectureError(
                "Expected a Snap Store package name without options"
            )
        candidates = _request("/v2/find", {"name": package})
        matches = (
            [
                item
                for item in candidates
                if isinstance(item, dict) and item.get("name") == package
            ]
            if isinstance(candidates, list)
            else []
        )
        if len(matches) != 1:
            raise ArchitectureError(
                f"No unique native Snap Store candidate for {package}"
            )
        candidate = matches[0]
        if candidate.get("architecture") is not None:
            require_native([candidate["architecture"]])
        channels = candidate.get("channels")
        stable = channels.get("latest/stable") if isinstance(channels, dict) else None
        if (
            not isinstance(stable, dict)
            or not stable.get("revision")
            or not stable.get("version")
        ):
            raise ArchitectureError(
                f"No native latest/stable Snap channel for {package}"
            )
        if stable.get("architecture") is not None:
            require_native([stable["architecture"]])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    labels = sub.add_parser("label")
    labels.add_argument(
        "system", choices=["host", "deb", "rpm", "rust", "vendor", "flatpak"]
    )
    scripts = sub.add_parser("script")
    scripts.add_argument("path")
    hook = sub.add_parser("hook")
    hook.add_argument("script_dir")
    hook.add_argument("cache_dir")
    hook.add_argument("relative_path")
    files = sub.add_parser("files")
    files.add_argument(
        "--content-kind",
        choices=["native", "data", "source", "guest"],
        default="native",
    )
    files.add_argument("paths", nargs="+")
    tree = sub.add_parser("tree")
    tree.add_argument("--content-kind", choices=["source"], default="source")
    tree.add_argument("path")
    releases = sub.add_parser("release")
    releases.add_argument(
        "--kind",
        choices=["deb", "rpm", "arch", "appimage", "eopkg", "tar", "zip"],
        required=True,
    )
    releases.add_argument("--pattern", default="*")
    releases.add_argument("path")
    packages = sub.add_parser("packages")
    packages.add_argument("manager")
    packages.add_argument("names", nargs="+")
    snap = sub.add_parser("snap")
    snap.add_argument("names", nargs="+")
    flatpak = sub.add_parser("flatpak")
    flatpak.add_argument("remote")
    flatpak.add_argument("scope", choices=["user", "system"])
    flatpak.add_argument("refs", nargs="+")
    extensions = sub.add_parser("extension")
    extensions.add_argument("app")
    extensions.add_argument("extension")
    args = parser.parse_args(argv)
    try:
        host()  # Reject unsupported hosts for every entry point, including data.
        if args.command == "label":
            print(label(args.system))
        elif args.command == "script":
            require_script_path(args.path)
        elif args.command == "hook":
            path = resolve_hook_path(
                args.script_dir, args.relative_path, args.cache_dir
            )
            require_script_path(path)
            print(path)
        elif args.command == "files":
            validate_files(args.paths, content_kind=args.content_kind)
            deb_files = [
                str(Path(path).resolve())
                for path in args.paths
                if path.lower().endswith(".deb")
            ]
            if deb_files:
                apt_plan(deb_files)
        elif args.command == "tree":
            validate_tree(args.path, content_kind=args.content_kind)
        elif args.command == "release":
            release = json.loads(Path(args.path).read_text())
            suffixes = {
                "deb": (".deb",),
                "rpm": (".rpm",),
                "arch": (".pkg.tar.zst",),
                "appimage": (".appimage",),
                "eopkg": (".eopkg",),
                "tar": (".tar.gz", ".tar.xz"),
                "zip": (".zip",),
            }
            asset = select_asset(
                release.get("assets", []),
                pattern=args.pattern,
                formats=(suffixes[args.kind],),
            )
            url = asset.get("browser_download_url", "")
            if (
                not isinstance(url, str)
                or not url.startswith("https://")
                or "\n" in url
            ):
                raise ArchitectureError("Release asset has no valid HTTPS download URL")
            print(url)
        elif args.command == "packages":
            native_packages(args.names, args.manager)
        elif args.command == "snap":
            snap_packages(args.names)
        elif args.command == "flatpak":
            print("\n".join(resolve_refs(args.refs, args.remote, "--" + args.scope)))
        elif args.command == "extension":
            scope, remote, refs = extension_plan(args.app, args.extension)
            print("\n".join([scope.removeprefix("--"), remote, *refs]))
    except (
        ArchitectureError,
        OSError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        print(f"Architecture preflight refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
