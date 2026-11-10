"""Exact-revision rollout tests: local Git transport, no installs or publication."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p3"))
from app import architecture, git_scripts_manager as manager, script_compat as compat  # noqa: E402
from app import library_loader  # noqa: E402


class ScriptCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lock = self.root / "client-lock.json"
        self.cache = self.root / "cache"
        self.cache.mkdir()
        self.bundle = self.root / "bundled"
        self.rev = self.make_bundle(self.bundle)
        self.approve(self.rev)
        for target, name, value in (
            (compat, "LOCK_PATH", self.lock),
            (manager, "CACHE_DIR", str(self.cache)),
            (manager, "GIT_SCRIPTS_CACHE_DIR", str(self.cache / "scripts")),
            (
                manager,
                "LAST_UPDATE_TIMESTAMP_FILE",
                str(self.cache / "last_update.timestamp"),
            ),
            (
                manager,
                "GIT_SCRIPTS_RETIRED_PREFIX",
                str(self.cache / "scripts.retired"),
            ),
            (manager, "is_dev_mode_enabled", lambda: False),
            (manager, "get_bundled_scripts_dir", lambda: str(self.bundle)),
        ):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_bundle(self, tree, *, body=None, api=1, policy=None):
        tree.mkdir(parents=True, exist_ok=True)
        (tree / "font.sh").write_text(
            body or "# architectures: x86_64, aarch64\ntrue\n"
        )
        raw = (
            json.dumps(
                {
                    "schema": 1,
                    "requires_api": api,
                    "architecture_policy_sha256": policy
                    or compat.digest(compat.POLICY_PATH.read_bytes()),
                    "files": {
                        "font.sh": compat.digest((tree / "font.sh").read_bytes())
                    },
                },
                sort_keys=True,
            )
            + "\n"
        ).encode()
        (tree / compat.MANIFEST).write_bytes(raw)
        return compat.digest(raw)

    def approve(self, *revisions):
        self.lock.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "script_api": 1,
                    "preferred_revision": revisions[0],
                    "accepted_revisions": list(revisions),
                }
            )
        )

    def git(self, tree, *args):
        return subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "user.name=Rollout test",
                "-c",
                "user.email=rollout-test@invalid",
                *args,
            ],
            cwd=tree,
            capture_output=True,
            text=True,
            check=True,
        )

    def remote(self):
        tree = self.root / "remote"
        shutil.copytree(self.bundle, tree)
        self.git(tree, "init", "-q")
        self.git(tree, "add", ".")
        self.git(tree, "commit", "-qm", "test-only approved revision")
        self.git(tree, "tag", compat.preferred_tag())
        return tree

    def sync(self, remote):
        with (
            patch.object(manager, "GITHUB_REPO_URL", str(remote)),
            patch.object(manager, "GITLINUXTOYS_REPO_URL", str(remote)),
        ):
            return manager.synchronize_scripts(force=True)

    def test_matching_exact_bytes_and_both_architectures(self):
        compat.require_bundle(self.bundle)
        for arch in ("aarch64", "x86_64"):
            architecture.require_script_path(self.bundle / "font.sh", arch)

    def test_unknown_newer_and_older_revisions_are_not_auto_accepted(self):
        for name in ("older", "newer", "unknown"):
            with self.subTest(revision=name):
                tree = self.root / name
                self.make_bundle(
                    tree, body=f"# architectures: aarch64\n# {name}\ntrue\n"
                )
                with self.assertRaises(architecture.ArchitectureError):
                    architecture.require_script_path(tree / "font.sh", "aarch64")

    def test_api_and_policy_mismatch_even_with_known_manifest(self):
        for api, policy in ((0, None), (2, None), (1, "0" * 64)):
            tree = self.root / f"api-{api}"
            rev = self.make_bundle(tree, api=api, policy=policy)
            self.approve(rev)
            with self.assertRaises(architecture.ArchitectureError):
                compat.require_bundle(tree)

    def test_stale_client_cannot_use_new_contract(self):
        with patch.object(compat, "SCRIPT_API", 0):
            with self.assertRaises(architecture.ArchitectureError):
                compat.require_bundle(self.bundle)

    def test_explicit_api_requirements_must_match(self):
        compat.require_api("# requires-script-api: 1\ntrue\n")
        for value in ("0", "2", "unknown", "1\n# requires-script-api: 2"):
            with self.assertRaises(architecture.ArchitectureError):
                compat.require_api(f"# requires-script-api: {value}\ntrue\n")
            with self.assertRaises(architecture.ArchitectureError):
                architecture.require_script(
                    f"# architectures: x86_64\n# requires-script-api: {value}\ntrue\n",
                    "x86_64",
                )

    def test_manifest_tampering_and_invalid_client_lock(self):
        manifest = self.bundle / compat.MANIFEST
        manifest.write_bytes(manifest.read_bytes() + b"\n")
        with self.assertRaises(architecture.ArchitectureError):
            compat.require_bundle(self.bundle)
        for value in ([], {}, {"schema": 2}):
            self.lock.write_text(json.dumps(value))
            with self.assertRaises(architecture.ArchitectureError):
                compat.require_bundle(self.bundle)

    def test_other_process_lock_does_not_start_a_second_sync(self):
        import fcntl

        with open(self.cache / "scripts.sync.lock", "a") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(manager, "_clone_scripts_repo") as clone:
                result = manager.synchronize_scripts(force=True)
                self.assertFalse(result["performed"])
                self.assertEqual(result["path"], str(self.bundle))
                clone.assert_not_called()

    def test_real_reviewed_x86_routes_remain_eligible(self):
        with patch.object(compat, "LOCK_PATH", ROOT / "p3/app/script-revisions.json"):
            for name in (
                "extra/preload.sh",
                "health/accessibility/atkinson.sh",
                "health/accessibility/opendyslexic.sh",
                "utils/nerdfonts.sh",
            ):
                architecture.require_script_path(ROOT / "p3/scripts" / name, "x86_64")
            with self.assertRaises(architecture.ArchitectureError):
                architecture.require_script_path(
                    ROOT / "p3/scripts/extra/preload.sh", "aarch64"
                )

    def test_tampering_headers_and_line_endings_are_not_permissions(self):
        compat.require_bundle(self.bundle)  # Populate the fast-path cache first.
        file = self.bundle / "font.sh"
        for body in (
            b"# architectures: aarch64\nsudo true\n",
            b"# architectures: x86_64, aarch64\r\ntrue\r\n",
        ):
            file.write_bytes(body)
            with self.assertRaises(architecture.ArchitectureError):
                architecture.require_script_path(file, "aarch64")

    def test_missing_extra_and_symlink_members(self):
        file = self.bundle / "font.sh"
        original = file.read_bytes()
        file.unlink()
        with self.assertRaises(architecture.ArchitectureError):
            compat.require_bundle(self.bundle)
        file.write_bytes(original)
        extra = self.bundle / "extra.sh"
        extra.write_text("true")
        with self.assertRaises(architecture.ArchitectureError):
            compat.require_bundle(self.bundle)
        extra.unlink()
        extra.symlink_to(file)
        with self.assertRaises(architecture.ArchitectureError):
            compat.require_bundle(self.bundle)

    def test_missing_manifest_cannot_downgrade_managed_content(self):
        (self.bundle / compat.MANIFEST).unlink()
        with self.assertRaises(architecture.ArchitectureError):
            architecture.require_script_path(self.bundle / "font.sh", "aarch64")

    def test_repository_documentation_is_not_executable(self):
        (self.bundle / "README.md").write_text("# architectures: aarch64\nsudo true")
        compat.require_bundle(self.bundle)
        with self.assertRaises(architecture.ArchitectureError):
            architecture.require_script_path(self.bundle / "README.md", "aarch64")

    def test_matching_remote_and_offline_cache(self):
        remote = self.remote()
        result = self.sync(remote)
        self.assertTrue(result["success"], result)
        self.assertTrue(result["changed"])
        self.assertEqual(result["path"], manager.GIT_SCRIPTS_CACHE_DIR)
        result = self.sync(self.root / "offline")
        self.assertFalse(result["success"])
        self.assertEqual(result["path"], manager.GIT_SCRIPTS_CACHE_DIR)
        compat.require_bundle(result["path"])

    def test_missing_tag_and_unknown_remote_keep_verified_bundle(self):
        remote = self.remote()
        self.git(remote, "tag", "-d", compat.preferred_tag())
        self.assertFalse(self.sync(remote)["success"])
        self.assertEqual(manager.get_available_scripts_dir(), str(self.bundle))
        # Even a matching tag label cannot authorize different content.
        (remote / "font.sh").write_text("# architectures: aarch64\nsudo true")
        self.git(remote, "add", ".")
        self.git(remote, "commit", "-qm", "unqualified body")
        self.git(remote, "tag", compat.preferred_tag())
        self.assertFalse(self.sync(remote)["success"])
        self.assertEqual(manager.get_available_scripts_dir(), str(self.bundle))

    def test_partial_synchronization_preserves_active_tree(self):
        self.assertTrue(self.sync(self.remote())["success"])

        def partial(args, **kwargs):
            Path(args[-1], "font.sh").write_text("partial")
            return False, "", "interrupted transfer"

        with patch.object(manager, "_run_git_command", side_effect=partial):
            self.assertFalse(manager._clone_scripts_repo())
        compat.require_bundle(manager.GIT_SCRIPTS_CACHE_DIR)
        self.assertEqual(list(self.cache.glob("scripts.updating.*")), [])

    def test_corrupt_legacy_cache_is_not_selected_offline(self):
        cache = Path(manager.GIT_SCRIPTS_CACHE_DIR)
        (cache / ".git").mkdir(parents=True)
        (cache / "font.sh").write_text("# architectures: aarch64\nsudo true")
        Path(manager.LAST_UPDATE_TIMESTAMP_FILE).write_text("9999999999")
        self.assertEqual(manager.get_available_scripts_dir(), str(self.bundle))
        with self.assertRaises(architecture.ArchitectureError):
            architecture.require_script_path(cache / "font.sh", "aarch64")

    def test_rollback_requires_explicit_client_approval(self):
        older = self.root / "older-approved"
        revision = self.make_bundle(
            older, body="# architectures: aarch64\n# old\ntrue\n"
        )
        with self.assertRaises(architecture.ArchitectureError):
            compat.require_bundle(older)
        self.approve(self.rev, revision)
        compat.require_bundle(older)
        compat.require_bundle(self.bundle)
        self.approve(self.rev)  # Revocation immediately removes permission.
        with self.assertRaises(architecture.ArchitectureError):
            compat.require_bundle(older)

    def test_promotion_failure_restores_previous_tree(self):
        self.assertTrue(self.sync(self.remote())["success"])
        staging = self.root / "staging"
        shutil.copytree(self.bundle, staging)
        replace = os.replace

        def fail_stage(source, target):
            if str(source) == str(staging):
                raise OSError("injected rename failure")
            replace(source, target)

        with patch.object(manager.os, "replace", side_effect=fail_stage):
            with self.assertRaises(OSError):
                manager._promote_staged_scripts_cache(str(staging))
        compat.require_bundle(manager.GIT_SCRIPTS_CACHE_DIR)

    def test_invalid_stage_is_rejected_before_any_cache_rename(self):
        staging = self.root / "invalid-stage"
        shutil.copytree(self.bundle, staging)
        (staging / "font.sh").write_text("# architectures: aarch64\nsudo true")
        with patch.object(manager.os, "replace") as rename:
            with self.assertRaises(architecture.ArchitectureError):
                manager._promote_staged_scripts_cache(str(staging))
            rename.assert_not_called()

    def test_restore_failure_retains_recovery_copy(self):
        self.assertTrue(self.sync(self.remote())["success"])
        staging = self.root / "staging"
        shutil.copytree(self.bundle, staging)
        replace = os.replace

        def fail_after_retire(source, target):
            if str(source) != manager.GIT_SCRIPTS_CACHE_DIR:
                raise OSError("injected stage/restore failure")
            replace(source, target)

        with patch.object(manager.os, "replace", side_effect=fail_after_retire):
            with self.assertRaises(OSError):
                manager._promote_staged_scripts_cache(str(staging))
        retired = list(self.cache.glob("scripts.retired.*"))
        self.assertEqual(len(retired), 1)
        compat.require_bundle(retired[0])
        self.assertEqual(manager.get_available_scripts_dir(), str(self.bundle))

    def test_rejection_precedes_preamble_and_session_mutations(self):
        (self.bundle / "font.sh").write_text("# architectures: aarch64\nsudo true")
        with patch.object(library_loader, "script_preamble") as preamble:
            with self.assertRaises(architecture.ArchitectureError):
                library_loader.script_command(self.bundle / "font.sh", str(ROOT / "p3"))
            preamble.assert_not_called()

    def test_early_guard_refuses_client_missing_helper_before_script_body(self):
        for name in (
            "health/accessibility/atkinson.sh",
            "health/accessibility/opendyslexic.sh",
            "utils/nerdfonts.sh",
        ):
            script = ROOT / "p3/scripts" / name
            result = subprocess.run(
                ["bash", str(script)],
                capture_output=True,
                text=True,
                env={**os.environ, "SCRIPT_DIR": str(self.root / "old-client")},
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("script_compat.py", result.stderr)
            self.assertNotIn("linuxtoys.lib", result.stderr)


if __name__ == "__main__":
    unittest.main()
