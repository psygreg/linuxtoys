"""Offline candidate guards and lifecycle fault fixtures; never install packages."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p3"))
from app import architecture, architecture_cli, architecture_files, revert_helper


def candidate(name):
    source = ROOT / "p3/scripts/repos.json"
    record = next(
        item for item in json.loads(source.read_text()) if item.get("name") == name
    )
    return {**record, "_list_source": str(source)}


class CandidateFailureTests(unittest.TestCase):
    def test_f3_catalog_remains_unapproved_on_arm64(self):
        with self.assertRaises(architecture.ArchitectureError):
            architecture.require_entry(candidate("F3 (Fight Flash Fraud)"), "aarch64")

    def test_f3_separate_hook_approval_remains_x86_only(self):
        overrides = candidate("F3 (Fight Flash Fraud)")["overrides"]
        digest = hashlib.sha256(overrides["post"].strip().encode()).hexdigest()
        self.assertEqual(
            digest, "c87a49ca4b0b79b5bd0b8067717e43ae278677c49db059f8bae1a727c9c8f12c"
        )
        self.assertEqual(
            architecture.route_policy()["inline_hooks"][digest]["architectures"],
            ["x86_64"],
        )
        with patch.object(architecture.platform, "machine", return_value="aarch64"):
            with self.assertRaises(architecture.ArchitectureError):
                architecture.require_overrides(overrides, str(ROOT / "p3"))

    def test_changed_nala_source_cannot_inherit_approval(self):
        # This exercises metadata authority only, not x86 execution/emulation.
        record = candidate("Nala")
        architecture.require_entry(record, "x86_64")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "repos.json"
            record.pop("_list_source")
            record["package-name"] = "unreviewed-package"
            source.write_text(json.dumps([record]))
            with self.assertRaises(architecture.ArchitectureError):
                architecture.require_entry(
                    {**record, "_list_source": str(source)}, "x86_64"
                )

    def test_foreign_elf_fixture_rejected_before_execution(self):
        data = bytearray(4096)
        data[:6] = b"\x7fELF\x02\x01"
        data[18:20] = struct.pack("<H", 62)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "foreign-fixture"
            path.write_bytes(data)
            with self.assertRaises(architecture.ArchitectureError):
                architecture_files.validate_file(path, machine="aarch64")

    def test_missing_architecture_metadata_does_not_start_solver(self):
        with (
            patch.object(architecture.platform, "machine", return_value="aarch64"),
            patch.object(
                architecture_cli.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, "Package: nala\n", ""),
            ) as run,
        ):
            with self.assertRaises(architecture.ArchitectureError):
                architecture_cli.native_packages(["nala"], "apt")
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][0], "apt-cache")

    def test_interruption_before_recorded_changes_has_no_invented_reversal(self):
        with tempfile.TemporaryDirectory() as directory:
            transmap = Path(directory) / "empty-transmap"
            transmap.touch()
            self.assertIsNone(
                revert_helper.build_auto_revert_script_entry(
                    {"name": "Nala"}, str(transmap)
                )
            )

    def test_failed_generated_reversal_keeps_registry_and_user_data(self):
        # Actual production generator/shell; external package helper is a failing
        # fixture. This is not counted as native APT rollback qualification.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "libs").mkdir()
            (root / "libs/linuxtoys.bash").write_text(
                "sudo_rq() { return 0; }\npkg_remove() { return 42; }\n"
            )
            (root / "libs/helpers.bash").write_text("")
            registry = root / "registry"
            original = (
                b"[2026-11-14T10:00:00] Script: Nala\nChanges:\n  - pkg nala\n---\n\n"
            )
            registry.write_bytes(original)
            canary = root / "user-data"
            canary.write_text("preserve")
            with (
                patch.dict(os.environ, SCRIPT_DIR=str(root)),
                patch.object(
                    revert_helper, "get_linuxtoys_cache_dir", return_value=str(root)
                ),
                patch.object(
                    revert_helper, "_detect_package_manager", return_value="apt"
                ),
            ):
                entry = revert_helper.build_uninstall_script_entry({"name": "Nala"})
            self.assertIsNotNone(entry)
            try:
                result = subprocess.run(
                    ["bash", entry["path"]], capture_output=True, text=True
                )
                self.assertEqual(result.returncode, 42, result.stderr)
                self.assertEqual(registry.read_bytes(), original)
                self.assertEqual(canary.read_text(), "preserve")
            finally:
                Path(entry["path"]).unlink()

    def test_lifecycle_harness_refuses_the_host(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "dev/tests/native_m5_candidates.py"),
                "lifecycle",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Requires the pinned disposable native M5 container", result.stderr
        )


@unittest.skipUnless(
    shutil.which("dpkg-query"),
    "Requires existing native dpkg-query; no installation allowed",
)
class NativeDpkgStateFixtures(unittest.TestCase):
    """Real dpkg over temporary status records; no actual package installation."""

    def classify(self, status):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = (
                ""
                if status is None
                else (
                    "Package: nala\nStatus: "
                    + status
                    + "\nPriority: optional\nSection: admin\n"
                    "Maintainer: Test Fixture <fixture@example.invalid>\nArchitecture: all\n"
                    "Version: 0.16.0\nDescription: isolated status fixture\n\n"
                )
            )
            (root / "status").write_text(record)
            code = (
                "is_debian() { return 0; }; is_ubuntu() { return 0; }; "
                "source "
                + shlex.quote(str(ROOT / "p3/libs/packages.bash"))
                + '; pkg_exists nala; printf "FOUND=%s MISSING=%s\\n" "${#pkg_found[@]}" "${#pkg_notfound[@]}"'
            )
            result = subprocess.run(
                ["bash", "-c", code],
                env={
                    **os.environ,
                    "HOME": str(root),
                    "SCRIPT_DIR": str(ROOT / "p3"),
                    "DPKG_ADMINDIR": str(root),
                },
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip()

    def test_absent_is_not_installed(self):
        self.assertEqual(self.classify(None), "FOUND=0 MISSING=1")

    def test_configured_is_installed(self):
        self.assertEqual(self.classify("install ok installed"), "FOUND=1 MISSING=0")

    def test_residual_conffiles_are_not_an_installed_application(self):
        self.assertEqual(
            self.classify("deinstall ok config-files"), "FOUND=0 MISSING=1"
        )

    def test_interrupted_unpacked_state_requires_completion(self):
        self.assertEqual(self.classify("install ok unpacked"), "FOUND=0 MISSING=1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
