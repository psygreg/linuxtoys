"""Smoke-test the built PyO3 catalog against the authoritative architecture policy.

Usage: PYTHONPATH=p3 python3 dev/tests/native_catalog_smoke.py /path/to/lib_catalog_rs.so
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "p3"))


def main(library_path: str) -> None:
    spec = importlib.util.spec_from_file_location("app._catalog_rs", library_path)
    if spec is None or spec.loader is None:
        raise SystemExit("Cannot load native catalog library")
    module = importlib.util.module_from_spec(spec)
    sys.modules["app._catalog_rs"] = module
    spec.loader.exec_module(module)
    assert module.git_asset_architectures("tool-x64.AppImage") == ["x86_64"]
    assert module.git_asset_architectures("tool-arm64.deb") == ["aarch64"]
    assert module.git_asset_architectures("tool.deb") == []

    # Exercise the Rust -> Python policy bridge, not just the exported alias helper.
    entries = module.build_repo_catalog(
        str(root / "p3/scripts"),
        ["ubuntu", "systemd"],
        False,
        False,
        False,
        False,
        False,
        "aarch64",
        "{}",
        "en",
    )
    names = {entry["name"] for entry in entries}
    assert "Figma" in names, names
    assert "OpenBoardView" not in names, names  # cached unlabelled/incorrect bundle
    print(
        f"Native PyO3 policy bridge passed ({len(entries)} structurally eligible records)"
    )

    # Frontend eligibility adds reviewed declaration/hook policy to structural indexing.
    from app import repo_parser

    with patch("app.architecture.platform.machine", return_value="x86_64"):
        baseline = repo_parser._build_repo_entries(
            str(root / "p3/scripts"), compat_keys={"ubuntu", "systemd"}
        )
        assert "Figma" in {entry["name"] for entry in baseline}
        assert "Volt" not in {entry["name"] for entry in baseline}
    arm_entries = repo_parser._build_repo_entries(
        str(root / "p3/scripts"), compat_keys={"ubuntu", "systemd"}
    )
    assert "Figma" not in {entry["name"] for entry in arm_entries}
    print("Frontend x86 baseline and ARM route-gating smoke tests passed")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: native_catalog_smoke.py /path/to/lib_catalog_rs.so")
    main(sys.argv[1])
