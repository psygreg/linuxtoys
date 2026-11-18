#!/usr/bin/env python3
"""Small shell entry point for the shared architecture policy; exits 1 on refusal."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.architecture import (
    ArchitectureError,
    asset_architectures,
    host,
    label,
    require_native,
    require_script_path,
    resolve_hook_path,
    select_asset,
)
from app.architecture_files import validate_files, validate_tree
from app.architecture_flatpak import extension_plan, resolve_refs


def apt_plan(packages: list[str]) -> None:
    """Validate APT's complete simulated installation plan, including dependencies."""
    result = subprocess.run(
        ["apt-get", "--simulate", "--no-remove", "install", *packages],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "LC_ALL": "C"},
    )
    for line in (result.stdout or "").splitlines():
        if not line.startswith("Inst "):
            continue
        package = line.split()[1]
        if ":" in package:
            require_native([package.rsplit(":", 1)[1]])
        # Newer APT (e.g. Debian 13) appends an optional trailing reason group
        # after the closing paren: "... Debian:13.7/stable [amd64]) []".
        match = re.search(r"\[([^] ]+)\]\)(?:\s*\[[^]]*\])?\s*$", line)
        if not match:
            raise ArchitectureError(
                f"APT did not identify the planned architecture for {package}"
            )
        if match[1] != "all":
            require_native([match[1]])


def native_packages(packages: list[str], manager: str) -> None:
    """Preflight native package metadata before authentication or transaction locks."""
    arch = host()
    for package in packages:
        if package.startswith("-"):
            raise ArchitectureError("Package options are not package names")
        if ":" in package:
            require_native([package.rsplit(":", 1)[1]], arch.value)
        require_native(asset_architectures(package) or [arch.value], arch.value)
    if manager == "apt":
        for package in packages:
            candidate = subprocess.run(
                ["apt-cache", "show", "--no-all-versions", package],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "LC_ALL": "C"},
            ).stdout
            fields = [
                line.split(":", 1)[1].strip()
                for line in candidate.splitlines()
                if line.startswith("Architecture:")
            ]
            if not fields:
                raise ArchitectureError(
                    f"No available native candidate for {package}; configure a supported repository first"
                )
            for value in fields:
                if value != "all":
                    require_native([value], arch.value)
        apt_plan(packages)
    elif manager in {"dnf", "zypper", "pacman", "eopkg"}:
        commands = {
            "dnf": ["dnf", "--cacheonly", "repoquery", "--qf", "%{arch}"],
            "zypper": ["zypper", "--no-refresh", "info"],
            "pacman": ["pacman", "-Si"],
            "eopkg": ["eopkg", "info"],
        }
        for package in packages:
            result = subprocess.run(
                [*commands[manager], package],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "LC_ALL": "C"},
            ).stdout
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
            for value in values:
                if value not in {"all", "any", "noarch"}:
                    require_native([value], arch.value)
    else:
        raise ArchitectureError("Unsupported package preflight backend")


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
        "--content-kind", choices=["native", "data", "source"], default="native"
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
