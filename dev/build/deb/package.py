#!/usr/bin/env python3
"""Stage the existing private application and native build products for dpkg."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR / "p3"))
from app.architecture import label  # noqa: E402
from app.architecture_files import validate_file  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_inputs(source: Path) -> None:
    # Existing .lib compatibility links name regular siblings. Materialize those
    # as before; never follow directories, chains, absolute or escaping links.
    for path in source.rglob("*"):
        if path.is_symlink():
            target = Path(os.readlink(path))
            sibling = path.parent / target
            if (
                target.is_absolute()
                or len(target.parts) != 1
                or sibling.is_symlink()
                or not sibling.is_file()
            ):
                raise ValueError(f"Unexpected runtime file type: {path}")
        elif not (path.is_file() or path.is_dir()):
            raise ValueError(f"Unexpected runtime file type: {path}")


def stage(root: Path, destination: Path, artifacts: Path) -> None:
    check_inputs(root / "p3")
    app = destination / "usr/lib/linuxtoys"
    shutil.copytree(
        root / "p3",
        app,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    wheels = list(artifacts.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("Exactly one newly built catalog wheel is required")
    with zipfile.ZipFile(wheels[0]) as wheel:
        members = [
            name
            for name in wheel.namelist()
            if Path(name).name == "_catalog_rs.abi3.so"
        ]
        if len(members) != 1:
            raise ValueError("Exactly one abi3 catalog extension is required")
        (app / "app/_catalog_rs.abi3.so").write_bytes(wheel.read(members[0]))
    shutil.copyfile(artifacts / "liblinuxtoys_gui.so", app / "app/liblinuxtoys_gui.so")
    for name in ("_catalog_rs.abi3.so", "liblinuxtoys_gui.so"):
        validate_file(app / "app" / name)
        subprocess.run(
            ["strip", "--strip-unneeded", str(app / "app" / name)], check=True
        )
    expected = dict(
        line.split("==", 1)
        for line in (root / "p3/requirements.txt").read_text().splitlines()
        if line.startswith(("textual==", "pyte=="))
    )
    if set(expected) != {"textual", "pyte"}:
        raise ValueError("Required exact TUI pins are unavailable")
    vendored = {
        d.metadata["Name"].lower(): d.version
        for d in importlib.metadata.distributions(path=[str(app / "vendor")])
    }
    for name, version in expected.items():
        if vendored.get(name) != version:
            raise ValueError(f"Required vendored runtime missing/wrong: {name}")
    for path in app.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Unexpected runtime symlink: {path}")
        if path.is_file():
            if path.suffix in {
                ".so",
                ".pyd",
                ".dylib",
                ".dll",
                ".exe",
                ".a",
            } and path not in {
                app / "app/_catalog_rs.abi3.so",
                app / "app/liblinuxtoys_gui.so",
            }:
                raise ValueError(f"Unexpected native runtime: {path}")
            path.chmod(
                0o755
                if path.suffix in {".sh", ".so"} or path.name == "linuxtoys.py"
                else 0o644
            )
        else:
            path.chmod(0o755)
    assets = {
        "toys.linux.LinuxToys.desktop": "usr/share/applications/toys.linux.LinuxToys.desktop",
        "toys.linux.LinuxToys.metainfo.xml": "usr/share/metainfo/toys.linux.LinuxToys.metainfo.xml",
        "linuxtoys-mimetypes.xml": "usr/share/mime/packages/linuxtoys-mimetypes.xml",
        "linuxtoys.svg": "usr/share/icons/hicolor/scalable/apps/linuxtoys.svg",
    }
    for source, relative in assets.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / "src" / source, target)
        target.chmod(0o644)
    doc = destination / "usr/share/doc/linuxtoys"
    doc.mkdir(parents=True)
    shutil.copyfile(root / "dev/packaging/deb-copyright", doc / "copyright")
    (doc / "copyright").chmod(0o644)
    launcher = destination / "usr/bin/linuxtoys"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("""#!/bin/sh
set -e
export LINUXTOYS_PROCESS_NAME=linuxtoys PYTHONDONTWRITEBYTECODE=1
if [ "$#" -gt 0 ]; then
    case "$1" in
        --gui|-g|--tui|-t|linuxtoys://*) ;;
        *) export EASY_CLI=1 ;;
    esac
fi
cd /usr/lib/linuxtoys
exec /usr/bin/python3 -B /usr/lib/linuxtoys/linuxtoys.py "$@"
""")
    launcher.chmod(0o755)


def control(
    root: Path, destination: Path, version: str, arch: str, shlibs: str
) -> None:
    if arch != label("deb"):
        raise ValueError("Package architecture must match the native M1 policy")
    runtime = [
        "python3 (>= 3.10)",
        "python3-gi",
        "python3-gi-cairo",
        "python3-cairo",
        "python3-requests",
        "python3-urllib3",
        "python3-certifi",
        "gir1.2-gtk-3.0",
        "gir1.2-vte-2.91",
        "gir1.2-appstream-1.0",
        "appstream",
        "bash",
        "git",
        "curl",
        "wget",
        "zenity",
        "jq",
        "util-linux",
        "fontconfig",
        "apt",
        "adwaita-icon-theme",
        "hicolor-icon-theme",
        "librsvg2-common",
        "webp-pixbuf-loader",
        "desktop-file-utils",
        "shared-mime-info",
        "sudo | sudo-rs",
    ]
    files = sorted(p for p in destination.rglob("*") if p.is_file())
    installed_size = sum((p.stat().st_size + 1023) // 1024 for p in files)
    debian = destination / "DEBIAN"
    debian.mkdir()
    (debian / "control").write_text(
        f"Package: linuxtoys\nVersion: {version}\nArchitecture: {arch}\n"
        "Section: utils\nPriority: optional\nMaintainer: Victor Gregory <psygreg@icloud.com>\n"
        f"Installed-Size: {installed_size}\nDepends: {shlibs}, {', '.join(runtime)}\n"
        "Homepage: https://linux.toys\n"
        "Description: Linux tools, tweaks and software manager\n"
        " Native GTK application with CLI, TUI and MCP interfaces.\n"
    )
    (debian / "md5sums").write_text(
        "".join(
            f"{hashlib.md5(p.read_bytes()).hexdigest()}  {p.relative_to(destination).as_posix()}\n"
            for p in files
        )
    )
    # No maintainer scripts, services, conffiles or user-home payloads.
    destination.chmod(0o755)
    for path in destination.rglob("*"):
        if path.is_dir():
            path.chmod(0o755)
    for path in debian.iterdir():
        path.chmod(0o644)


def provenance(root: Path, package: Path, output: Path) -> None:
    tools = {
        name: subprocess.check_output([name, "--version"], text=True).splitlines()[0]
        for name in ("python3", "cargo", "rustc", "maturin", "dpkg-deb")
    }
    inputs = {}
    for directory in (
        root / "p3",
        root / "src",
        root / "dev/build/deb",
        root / "dev/packaging",
    ):
        for path in sorted(directory.rglob("*")):
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and "vendor" not in path.parts
            ):
                inputs[path.relative_to(root).as_posix()] = digest(path)
    for name in ("Cargo.toml", "Cargo.lock", "pyproject.toml", "build-rust.sh"):
        inputs[name] = digest(root / name)
    stack = {
        d.metadata["Name"]: d.version
        for d in importlib.metadata.distributions(path=[str(root / "p3/vendor")])
    }
    record = {
        "schema": 1,
        "package": package.name,
        "sha256": digest(package),
        "architecture": label("deb"),
        "source_revision": os.environ.get("SOURCE_REVISION", "unrecorded"),
        "source_date_epoch": int(os.environ["SOURCE_DATE_EPOCH"]),
        "tools": tools,
        "input_sha256": inputs,
        "vendored_runtime": stack,
        "installed_build_packages": subprocess.check_output(
            ["dpkg-query", "-W", "-f=${binary:Package} ${Version} ${Architecture}\n"],
            text=True,
        ).splitlines(),
    }
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("check-inputs", "stage", "control", "provenance")
    )
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    if args.command == "check-inputs":
        check_inputs(*map(Path, args.paths))
    elif args.command == "stage":
        stage(*map(Path, args.paths))
    elif args.command == "control":
        root, dest, version, arch, shlibs = args.paths
        control(Path(root), Path(dest), version, arch, shlibs)
    else:
        provenance(*map(Path, args.paths))


if __name__ == "__main__":
    main()
