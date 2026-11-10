"""Exercise the three curated font routes in disposable native Linux profiles.

Usage: PYTHONPATH=p3:p3/vendor python3 dev/tests/native_font_smoke.py OUTPUT_DIR
Downloads pinned data, installs only in OUTPUT_DIR, tests registry removal and
restoration, and injects offline/HTTP/integrity failures before installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "p3"), str(ROOT / "p3/vendor")]
from app.library_loader import script_command, script_info_from_path  # noqa: E402

ROUTES = {
    "atkinson": (
        "health/accessibility/atkinson.sh",
        ("AtkinsonHyperlegibleMono", "AtkinsonHyperlegible"),
        6,
    ),
    "opendyslexic": ("health/accessibility/opendyslexic.sh", ("OpenDyslexic",), 4),
    "nerdfonts": (
        "utils/nerdfonts.sh",
        ("JetBrainsMono", "FiraCode", "Hack", "Meslo", "AdwaitaMono"),
        210,
    ),
}


def main(output: Path, asset_cache: Path | None = None) -> None:
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for name, (relative, targets, count) in ROUTES.items():
        for scenario in ("fresh", "existing", "offline", "unavailable", "tampered"):
            home = output / f"{name}-{scenario}"
            home.mkdir()
            os.environ.update(
                HOME=str(home),
                XDG_CONFIG_HOME=str(home / ".config"),
                XDG_CACHE_HOME=str(home / ".cache"),
                XDG_DATA_HOME=str(home / ".local/share"),
                SCRIPT_DIR=str(ROOT / "p3"),
                CACHE_DIR=str(ROOT / "p3/scripts"),
                DISABLE_ZENITY="1",
                LINUXTOYS_TIMEFIX="0",
                EASY_CLI="1",
                TRANSMAP_PATH=str(home / "transmap"),
                DISPLAY="",
                WAYLAND_DISPLAY="",
            )
            env = os.environ.copy()
            fonts = home / ".local/share/fonts"
            if scenario == "existing":
                for target in targets:
                    (fonts / target).mkdir(parents=True)
                    (fonts / target / "original.txt").write_text("preserve user data")
            if asset_cache is not None:
                tools = home / "replay-tools"
                tools.mkdir()
                replay = """#!/usr/bin/python3
import pathlib, shutil, sys
from urllib.parse import urlsplit, unquote
args = sys.argv[1:]
output = pathlib.Path(args[args.index('--output') + 1])
source = pathlib.Path(CACHE) / unquote(pathlib.PurePosixPath(urlsplit(args[-1]).path).name)
shutil.copyfile(source, output)
""".replace("CACHE", repr(str(asset_cache)))
                (tools / "curl").write_text(replay)
                (tools / "curl").chmod(0o755)
                env["PATH"] = str(tools) + os.pathsep + env["PATH"]
            if scenario in ("offline", "unavailable", "tampered"):
                tools = home / "tools"
                tools.mkdir()
                body = (
                    "#!/bin/sh\nexit " + ("7" if scenario == "offline" else "22") + "\n"
                )
                if scenario == "tampered":
                    body = '#!/bin/sh\nwhile [ "$#" -gt 0 ]; do if [ "$1" = --output ]; then shift; printf tampered > "$1"; exit 0; fi; shift; done\nexit 1\n'
                (tools / "curl").write_text(body)
                (tools / "curl").chmod(0o755)
                env["PATH"] = str(tools) + os.pathsep + env["PATH"]
            path = ROOT / "p3/scripts" / relative
            with (home / "install.log").open("w") as log:
                result = subprocess.run(
                    script_command(str(path), str(ROOT / "p3")),
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=240,
                )
            if scenario in ("offline", "unavailable", "tampered"):
                assert result.returncode != 0, (name, scenario, "false success")
                assert not fonts.exists(), (
                    name,
                    scenario,
                    "installed before validation",
                )
                records.append(
                    {
                        "route": name,
                        "scenario": scenario,
                        "refused_before_install": True,
                    }
                )
                continue
            assert result.returncode == 0, (
                name,
                scenario,
                (home / "install.log").read_text()[-1500:],
            )
            installed = sorted([*fonts.rglob("*.ttf"), *fonts.rglob("*.otf")])
            assert len(installed) == count, (name, scenario, len(installed), count)
            visible = subprocess.check_output(
                ["fc-list", "--format", "%{file}\n"], env=env, text=True
            )
            assert all(str(file) in visible for file in installed), (
                name,
                "fontconfig detection failed",
            )
            hashes = {
                str(file.relative_to(fonts)): hashlib.sha256(
                    file.read_bytes()
                ).hexdigest()
                for file in installed
            }
            from app.easy_cli import _save_script_to_registry
            from app.revert_helper import build_uninstall_script_entry
            from app.search_helper import ScriptCache
            from app.registry_utils import parse_registry_file

            info = script_info_from_path(str(path), str(ROOT / "p3"), env)
            info["is_script"] = True
            identity = info.get("registry_name") or info["name"]
            _save_script_to_registry(identity, env["TRANSMAP_PATH"])
            assert identity in parse_registry_file(), (name, "registry detection")
            assert ScriptCache().is_script_removable(info), (
                name,
                "installed-state detection",
            )
            reverse = build_uninstall_script_entry(info)
            assert reverse is not None, (name, "no removal plan")
            with (home / "remove.log").open("w") as log:
                removal = subprocess.run(
                    script_command(reverse["path"], str(ROOT / "p3")),
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=60,
                )
            assert removal.returncode == 0, (
                name,
                (home / "remove.log").read_text()[-1500:],
            )
            assert identity not in parse_registry_file(), (name, "registry removal")
            remaining_visible = subprocess.check_output(
                ["fc-list", "--format", "%{file}\n"], env=env, text=True
            )
            assert not any(str(file) in remaining_visible for file in installed), (
                name,
                "fontconfig removal detection",
            )
            for target in targets:
                if scenario == "fresh":
                    assert not (fonts / target).exists(), (name, "removal failed")
                else:
                    assert (
                        fonts / target / "original.txt"
                    ).read_text() == "preserve user data"
                    assert len(list((fonts / target).iterdir())) == 1, (
                        name,
                        "rollback failed",
                    )
                assert not (fonts / (target + ".bak")).exists()
            records.append(
                {
                    "route": name,
                    "scenario": scenario,
                    "font_files": count,
                    "fontconfig_visible": True,
                    "registry_detection": True,
                    "removal_or_restoration": True,
                    "installed_sha256": hashes,
                    "transport": "verified artifact replay"
                    if asset_cache
                    else "live HTTPS",
                }
            )
            print(name, scenario, "passed", flush=True)
    (output / "results.json").write_text(json.dumps(records, indent=2) + "\n")
    print("All 15 native font scenarios passed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--asset-cache",
        type=Path,
        help="Explicit test-only replay of previously downloaded artifacts; production checks remain active",
    )
    args = parser.parse_args()
    main(
        args.output.resolve(), args.asset_cache.resolve() if args.asset_cache else None
    )
