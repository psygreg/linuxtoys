"""Native ARM64 preparation evidence, independent tar checks and guarded tests.

Run on Ubuntu ARM64: python3 dev/tests/native_script_preparation_smoke.py
    --workspace NEW_DIRECTORY
No system installation, external request, workflow or publisher is invoked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tarfile
import unittest
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "dev"), str(ROOT / "p3")]
sys.dont_write_bytecode = True
import prepare_script_rollout as prep  # noqa: E402
from app.architecture import host  # noqa: E402


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def protected_snapshot() -> dict[str, tuple[Any, ...]]:
    """Check real production paths even while fixtures replace compat globals."""
    paths = [
        ROOT / "p3/app/script-revisions.json",
        ROOT / "p3/app/architecture-routes.json",
    ]
    paths += list((ROOT / "p3/scripts").rglob("*"))
    result = {}
    for path in paths:
        info = path.lstat()
        value = sha(path.read_bytes()) if stat.S_ISREG(info.st_mode) else None
        result[path.relative_to(ROOT).as_posix()] = (
            info.st_mode,
            info.st_uid,
            info.st_gid,
            info.st_mtime_ns,
            value,
        )
    return result


class GuardedResult(unittest.TextTestResult):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.integrity_checks = 0
        self.before: dict[str, tuple[Any, ...]] = {}

    def startTest(self, test: unittest.TestCase) -> None:
        self.before = protected_snapshot()
        super().startTest(test)

    def stopTest(self, test: unittest.TestCase) -> None:
        try:
            assert protected_snapshot() == self.before, (
                "Production files changed during test"
            )
        except AssertionError:
            self.addFailure(test, sys.exc_info())
        self.integrity_checks += 1
        super().stopTest(test)


def run_tests(pattern: str) -> dict[str, int]:
    suite = unittest.TestLoader().discover(str(ROOT / "dev/tests"), pattern=pattern)
    result = unittest.TextTestRunner(verbosity=2, resultclass=GuardedResult).run(suite)
    assert result.wasSuccessful(), "Native test failure; qualification is incomplete"
    return {
        "total": result.testsRun,
        "skipped": len(result.skipped),
        "passed": result.testsRun - len(result.skipped),
        "production_integrity_checks": result.integrity_checks,
    }


def independent_verify(directory: Path) -> dict[str, str]:
    """Inspect actual archive bytes without calling the preparation generator."""
    tree = ROOT / "p3/scripts"
    raw = (tree / prep.compat.MANIFEST).read_bytes()
    manifest = json.loads(raw)
    expected = {**manifest["files"], prep.compat.MANIFEST: sha(raw)}
    assert directory.name == sha(raw)
    assert {p.name for p in directory.iterdir()} == {
        "scripts.tar",
        "validation.json",
        "SHA256SUMS",
    }
    total = 0
    with tarfile.open(directory / "scripts.tar", mode="r:") as archive:
        members = archive.getmembers()
        assert [m.name for m in members] == [
            "scripts/" + name for name in sorted(expected)
        ]
        for member in members:
            assert member.isfile() and not member.issym() and not member.islnk()
            assert (
                member.uid,
                member.gid,
                member.mtime,
                member.uname,
                member.gname,
            ) == (0, 0, 0, "", "")
            name = member.name.removeprefix("scripts/")
            assert member.mode == (0o755 if name.endswith(".sh") else 0o644)
            assert member.size == (tree / name).stat().st_size
            stream = archive.extractfile(member)
            assert stream is not None
            with stream:
                data = stream.read(member.size + 1)
            assert sha(data) == expected[name], name
            if name == prep.compat.MANIFEST:
                assert data == raw
            total += len(data)
    hashes = {
        name: sha((directory / name).read_bytes()) for name in prep.ARTIFACT_FILES
    }
    report = json.loads((directory / "validation.json").read_bytes())
    assert report["status"] == "validated" and report["publication"] is False
    assert (
        report["revision"] == sha(raw)
        and report["script_api"] == prep.compat.SCRIPT_API
    )
    assert report["architecture_policy_sha256"] == sha(
        prep.compat.POLICY_PATH.read_bytes()
    )
    assert (
        report["archive_files"] == len(expected)
        and report["manifest_files"] == len(expected) - 1
    )
    assert (
        report["payload_bytes"] == total
        and report["archive_sha256"] == hashes["scripts.tar"]
    )
    checksums = (directory / "SHA256SUMS").read_text().splitlines()
    assert checksums == [
        f"{hashes[name]}  {name}" for name in ("scripts.tar", "validation.json")
    ]
    return hashes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    if sys.flags.optimize:
        raise SystemExit("Run without -O so qualification assertions execute")
    if platform.system() != "Linux" or host().value != "aarch64":
        raise SystemExit("Native Linux ARM64 required")
    workspace = args.workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    home = workspace / "home"
    home.mkdir()
    os.environ.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        XDG_CACHE_HOME=str(home / ".cache"),
        XDG_DATA_HOME=str(home / ".local/share"),
        PYTHONDONTWRITEBYTECODE="1",
        LINUXTOYS_TIMEFIX="0",
    )
    original = protected_snapshot()
    commands = []

    def command(*options: str, success: bool = True) -> None:
        before = protected_snapshot()
        result = subprocess.run(
            [sys.executable, str(ROOT / "dev/prepare_script_rollout.py"), *options],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert protected_snapshot() == before, "Production changed during CLI operation"
        assert (result.returncode == 0) == success, result.stdout + result.stderr
        commands.append(
            {
                "options": list(options),
                "exit": result.returncode,
                "production_unchanged": True,
            }
        )

    command("--check")
    revision = prep.compat.client_revisions()["preferred_revision"]
    outputs = []
    for name in ("first", "second"):
        output = workspace / name
        command("--check", "--artifact-dir", str(output))
        outputs.append(output / revision)
        command("--check", "--verify-artifact", str(outputs[-1]))
    first, second = outputs
    first_hashes = independent_verify(first)
    assert independent_verify(second) == first_hashes
    # This also establishes M3B macOS/3.13 versus Ubuntu/3.14 byte parity.
    m3b = json.loads((ROOT / "dev/script-preparation-evidence.json").read_bytes())
    assert first_hashes == m3b["artifact_file_sha256"]
    command("--check", "--artifact-dir", str(first.parent), success=False)
    assert independent_verify(first) == first_hashes
    for name in prep.ARTIFACT_FILES:
        path = first / name
        data = path.read_bytes()
        try:
            path.write_bytes(data + b"tampered")
            command("--check", "--verify-artifact", str(first), success=False)
        finally:
            path.write_bytes(data)
    marker = first / ".incomplete"
    marker.touch()
    try:
        command("--check", "--verify-artifact", str(first), success=False)
    finally:
        marker.unlink()
    assert independent_verify(first) == first_hashes
    focused = run_tests("test_script_preparation.py")
    full = run_tests("test_*.py")
    assert protected_snapshot() == original
    result = {
        "schema": 1,
        "os": platform.platform(),
        "architecture": host().value,
        "python": platform.python_version(),
        "revision": revision,
        "source_root": str(ROOT),
        "workspace": str(workspace),
        "independent_tar_verification": True,
        "hidden_manifest_in_tar": True,
        "artifact_sha256": first_hashes,
        "two_native_exports_identical": True,
        "matches_m3b_macos_python313": True,
        "cli_operations": commands,
        "focused": focused,
        "full": full,
        "production_content_modes_owners_mtimes_unchanged": True,
        "protected_paths": len(original),
        "workflow_executed": False,
        "artifacts_uploaded": False,
        "package_installation": False,
    }
    (workspace / "evidence.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
