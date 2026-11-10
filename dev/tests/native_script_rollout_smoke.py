"""Native catalog/search against an isolated TCP Git service; no installs.

Run in the qualified M2 environment with --profile NEW_DIR [--gui].
The fixture is local-only; this does not exercise or publish upstream tags.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p3"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()
    profile = args.profile.resolve()
    profile.mkdir(parents=True, exist_ok=False)
    os.environ.update(
        HOME=str(profile),
        XDG_CONFIG_HOME=str(profile / ".config"),
        XDG_CACHE_HOME=str(profile / ".cache"),
        XDG_DATA_HOME=str(profile / ".local/share"),
        SCRIPT_DIR=str(ROOT / "p3"),
        LINUXTOYS_TIMEFIX="0",
    )
    from app import (
        architecture,
        git_scripts_manager as manager,
        script_compat as compat,
    )
    from app.lang_utils import save_automatic_updates

    assert architecture.host().value == "aarch64", "Native ARM64 evidence only"
    save_automatic_updates(False)
    remote = profile / "remote"
    shutil.copytree(ROOT / "p3/scripts", remote)

    def git(*args):
        subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "user.name=Rollout probe",
                "-c",
                "user.email=rollout-probe@invalid",
                *args,
            ],
            cwd=remote,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-q")
    git("add", ".")
    git("commit", "-qm", "Local-only qualified snapshot")
    git("tag", compat.preferred_tag())
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    daemon = subprocess.Popen(
        [
            "git",
            "daemon",
            "--reuseaddr",
            "--export-all",
            "--listen=127.0.0.1",
            f"--port={port}",
            f"--base-path={profile}",
            str(remote),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                if daemon.poll() is not None:
                    raise RuntimeError("Local Git service exited")
                time.sleep(0.02)
        url = f"git://127.0.0.1:{port}/remote"
        with (
            patch.object(manager, "GITHUB_REPO_URL", url),
            patch.object(manager, "GITLINUXTOYS_REPO_URL", url),
        ):
            online = manager.synchronize_scripts(force=True)
            assert (
                online["success"] and online["path"] == manager.GIT_SCRIPTS_CACHE_DIR
            ), online
            from app import parser as catalog

            def search_fonts(path):
                catalog.set_scripts_dir(path)
                scripts = catalog.get_all_scripts_recursive(path)
                names = {x["name"] for x in scripts}
                expected = {"Atkinson Hyperlegible", "OpenDyslexic", "Nerd Fonts"}
                assert expected <= names, names
                return sorted(names & expected)

            names = search_fonts(online["path"])
            from app.easy_cli import create_temp_file
            from app.library_loader import script_command

            # Execute only the early validator, never the installation body.
            for name in (
                "health/accessibility/atkinson.sh",
                "health/accessibility/opendyslexic.sh",
                "utils/nerdfonts.sh",
            ):
                original = Path(online["path"]) / name
                assert Path(create_temp_file(str(original))) == original
                assert original.is_file()
                assert script_command(original, str(ROOT / "p3"))[-1] == str(original)
                subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "p3/app/script_compat.py"),
                        str(Path(online["path"]) / name),
                    ],
                    check=True,
                )
            # Reusing a tag name cannot authorize different content.
            (remote / "health/accessibility/atkinson.sh").write_text(
                "# architectures: aarch64\nsudo true\n"
            )
            git("add", ".")
            git("commit", "-qm", "Unqualified fixture; must not execute")
            git("tag", "-f", compat.preferred_tag())
            refused = manager.synchronize_scripts(force=True)
            assert not refused["success"] and not refused["changed"], refused
            search_fonts(refused["path"])
            if args.gui:
                from native_application_smoke import gui

                gui()
                assert catalog.SCRIPTS_DIR == manager.GIT_SCRIPTS_CACHE_DIR
            daemon.terminate()
            daemon.wait(timeout=5)
            offline = manager.synchronize_scripts(force=True)
            assert not offline["success"] and offline["path"] == online["path"], offline
            search_fonts(offline["path"])
            shutil.rmtree(manager.GIT_SCRIPTS_CACHE_DIR)
            bundled = manager.get_available_scripts_dir()
            assert bundled == manager.get_bundled_scripts_dir()
            search_fonts(bundled)
            print(
                json.dumps(
                    {
                        "probe": "script-rollout",
                        "architecture": architecture.host().value,
                        "python": sys.version.split()[0],
                        "revision": compat.client_revisions()["preferred_revision"],
                        "transport": "isolated loopback TCP Git daemon",
                        "online_fonts": names,
                        "tampered_remote_refused": True,
                        "offline_cache_search": True,
                        "offline_bundle_search": True,
                        "gui": args.gui,
                    }
                )
            )
    finally:
        if daemon.poll() is None:
            daemon.terminate()
        daemon.wait(timeout=5)


if __name__ == "__main__":
    main()
