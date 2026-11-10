"""Local-only artifact, malformed-input and workflow capability regressions."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "dev"), str(ROOT / "p3")]
import prepare_script_rollout as prep  # noqa: E402
from app import script_compat as compat  # noqa: E402


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tree = self.root / "scripts"
        self.tree.mkdir()
        (self.tree / "font.sh").write_text("# architectures: aarch64, x86_64\ntrue\n")
        (self.tree / ".required-data").write_bytes(b"independent data\n")
        self.lock = self.root / "lock.json"
        patcher = patch.object(compat, "LOCK_PATH", self.lock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.manifest = {
            "schema": 1,
            "requires_api": 1,
            "architecture_policy_sha256": compat.digest(
                compat.POLICY_PATH.read_bytes()
            ),
            "files": {
                name: compat.digest((self.tree / name).read_bytes())
                for name in ("font.sh", ".required-data")
            },
        }
        self.write_manifest()

    def write_manifest(self, value=None, raw=None):
        data = (
            raw
            if raw is not None
            else (json.dumps(self.manifest if value is None else value) + "\n").encode()
        )
        (self.tree / compat.MANIFEST).write_bytes(data)
        self.revision = compat.digest(data)
        # Fixture approval exercises structural checks; no production lock changes.
        self.lock.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "script_api": 1,
                    "preferred_revision": self.revision,
                    "accepted_revisions": [self.revision],
                }
            )
        )

    def prepare(self, name="artifacts"):
        return prep.prepare_artifact(self.tree, self.root / name)

    def assert_refused(self):
        with self.assertRaises((OSError, ValueError)):
            self.prepare()
        self.assertFalse((self.root / "artifacts").exists())

    def test_archive_includes_manifest_and_required_dotfiles(self):
        destination = self.prepare()
        prep.verify_artifact(self.tree, destination)
        with tarfile.open(destination / "scripts.tar") as archive:
            self.assertEqual(
                set(archive.getnames()),
                {
                    "scripts/" + compat.MANIFEST,
                    "scripts/font.sh",
                    "scripts/.required-data",
                },
            )
            for member in archive:
                self.assertTrue(member.isfile())
                self.assertEqual((member.uid, member.gid, member.mtime), (0, 0, 0))
                self.assertEqual(
                    member.mode, 0o755 if member.name.endswith(".sh") else 0o644
                )
        report = json.loads((destination / "validation.json").read_bytes())
        self.assertEqual(report["revision"], self.revision)
        self.assertFalse(report["publication"])
        self.assertEqual(report["archive_files"], 3)

    def test_reproducibility_ignores_path_mtime_permissions_and_iteration_order(self):
        first = self.prepare("first")
        for path in self.tree.iterdir():
            os.utime(path, (123456789, 123456789))
            path.chmod(0o600)
        second = self.prepare("second")
        for name in prep.ARTIFACT_FILES:
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
        files = prep.approved_files(self.tree)
        relocated = self.root / "relocated-source"
        shutil.copytree(self.tree, relocated)
        third = prep.prepare_artifact(relocated, self.root / "third")
        for name in prep.ARTIFACT_FILES:
            self.assertEqual((first / name).read_bytes(), (third / name).read_bytes())
        self.assertEqual(
            prep.artifact_bytes(files),
            prep.artifact_bytes(dict(reversed(list(files.items())))),
        )

    def test_missing_manifest_dotfile_is_refused(self):
        (self.tree / compat.MANIFEST).unlink()
        self.assert_refused()

    def test_missing_required_hidden_file_is_refused(self):
        (self.tree / ".required-data").unlink()
        self.assert_refused()

    def test_missing_or_modified_payload_is_refused(self):
        (self.tree / "font.sh").write_text("# architectures: aarch64\nsudo true\n")
        self.assert_refused()
        (self.tree / "font.sh").unlink()
        self.assert_refused()

    def test_malformed_json_objects_and_duplicate_keys_are_refused(self):
        for data in (
            b"{",
            b"[]",
            b"null",
            b'{"schema":1,"schema":1}',
            b'{"schema":1,"files":{"x":"a","x":"b"}}',
        ):
            with self.subTest(data=data):
                self.write_manifest(raw=data)
                self.assert_refused()

    def test_malformed_fields_and_hashes_are_refused(self):
        for field, value in (
            ("schema", True),
            ("requires_api", True),
            ("schema", 2),
            ("requires_api", 2),
            ("files", []),
            ("files", {}),
            ("architecture_policy_sha256", "0" * 64),
            ("files", {"font.sh": "not-a-sha"}),
        ):
            manifest = {**self.manifest, field: value}
            with self.subTest(field=field, value=value):
                self.write_manifest(manifest)
                self.assert_refused()
        self.write_manifest({**self.manifest, "unknown": 1})
        self.assert_refused()

    def test_unsafe_manifest_paths_and_case_collisions_are_refused(self):
        sha = compat.digest(b"data")
        for name in (
            "../escape",
            "/absolute",
            "a/../font.sh",
            "a//b",
            "a/./b",
            "a\\b",
            "a\nb",
            ".git/config",
            ".Git/config",
            ".incomplete",
            compat.MANIFEST,
            "LICENSE",
            "README.md",
        ):
            with self.subTest(name=name):
                self.write_manifest({**self.manifest, "files": {name: sha}})
                self.assert_refused()
        self.write_manifest({**self.manifest, "files": {"A.sh": sha, "a.sh": sha}})
        self.assert_refused()
        for files in ({"Dir/a": sha, "dir/b": sha}, {"file": sha, "file/child": sha}):
            self.write_manifest({**self.manifest, "files": files})
            self.assert_refused()

    def test_unknown_revision_never_self_approves(self):
        (self.tree / compat.MANIFEST).write_bytes(
            (self.tree / compat.MANIFEST).read_bytes() + b"\n"
        )
        self.assert_refused()

    def test_extra_unhashed_metadata_and_directories_are_refused(self):
        for name in ("extra.sh", ".hidden-extra", "README.md", "LICENSE"):
            path = self.tree / name
            path.write_text("unexpected")
            self.assert_refused()
            path.unlink()
        for name in (".git", "empty-extra"):
            path = self.tree / name
            path.mkdir()
            self.assert_refused()
            path.rmdir()

    def test_symlinked_files_directories_manifest_and_source_are_refused(self):
        file = self.tree / "font.sh"
        target = self.root / "actual.sh"
        file.rename(target)
        file.symlink_to(target)
        self.assert_refused()
        file.unlink()
        target.rename(file)
        link = self.tree / "linked-dir"
        link.symlink_to(self.root, target_is_directory=True)
        self.assert_refused()
        link.unlink()
        manifest = self.tree / compat.MANIFEST
        actual = self.root / "manifest.json"
        manifest.rename(actual)
        manifest.symlink_to(actual)
        self.assert_refused()
        manifest.unlink()
        actual.rename(manifest)
        source = self.root / "linked-source"
        source.symlink_to(self.tree, target_is_directory=True)
        with self.assertRaises(ValueError):
            prep.prepare_artifact(source, self.root / "output")

    def test_fifo_and_special_file_metadata_are_refused_without_reading(self):
        fifo = self.tree / "font.sh"
        original = fifo.read_bytes()
        fifo.unlink()
        os.mkfifo(fifo)
        self.assert_refused()
        fifo.unlink()
        fifo.write_bytes(original)
        for mode in (stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFBLK):
            entry = SimpleNamespace(
                path=str(fifo), stat=lambda **kwargs: SimpleNamespace(st_mode=mode)
            )
            with patch.object(prep.os, "scandir") as scan:
                scan.return_value.__enter__.return_value = iter([entry])
                with self.assertRaisesRegex(
                    ValueError, "Unexpected file, directory or file type"
                ):
                    self.prepare()
                self.assertFalse((self.root / "artifacts").exists())

    def test_bounded_payload_and_script_api_enforced(self):
        with patch.object(prep, "MAX_PAYLOAD", 1):
            self.assert_refused()
        (self.tree / "font.sh").write_text("# requires-script-api: 2\ntrue\n")
        self.manifest["files"]["font.sh"] = compat.digest(
            (self.tree / "font.sh").read_bytes()
        )
        self.write_manifest()
        self.assert_refused()

    def test_fresh_reads_reject_changes_after_client_validation(self):
        original = compat.require_bundle

        def change_after_validation(tree):
            result = original(tree)
            (tree / "font.sh").write_text("tampered")
            return result

        with patch.object(
            compat, "require_bundle", side_effect=change_after_validation
        ):
            self.assert_refused()

    def test_duplicate_revisions_never_overwrite_even_empty_or_symlink_destinations(
        self,
    ):
        destination = self.prepare()
        before = {p.name: p.read_bytes() for p in destination.iterdir()}
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(
            before, {p.name: p.read_bytes() for p in destination.iterdir()}
        )
        for kind in ("empty", "symlink"):
            output = self.root / kind
            output.mkdir()
            claimed = output / self.revision
            if kind == "empty":
                claimed.mkdir()
            else:
                claimed.symlink_to(destination, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                self.prepare(kind)

    def test_failed_write_cleans_only_new_revision_and_retry_is_possible(self):
        original = prep._regular_bytes

        def fail_readback(path, maximum):
            if path.name == "scripts.tar":
                raise OSError("injected readback failure")
            return original(path, maximum)

        with patch.object(prep, "_regular_bytes", side_effect=fail_readback):
            with self.assertRaises(OSError):
                self.prepare()
        self.assertFalse((self.root / "artifacts" / self.revision).exists())
        self.prepare()

    def test_failed_cleanup_retains_incomplete_marker_and_verification_refuses(self):
        with (
            patch.object(Path, "chmod", side_effect=OSError("write failure")),
            patch.object(prep.shutil, "rmtree", side_effect=OSError("cleanup failure")),
        ):
            with self.assertRaises(OSError):
                self.prepare()
        destination = self.root / "artifacts" / self.revision
        self.assertTrue((destination / ".incomplete").exists())
        with self.assertRaises(ValueError):
            prep.verify_artifact(self.tree, destination)
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_tar_report_checksum_and_extra_artifact_tampering_are_refused(self):
        destination = self.prepare()
        for name in prep.ARTIFACT_FILES:
            file = destination / name
            original = file.read_bytes()
            file.write_bytes(original + b"tampered")
            with self.assertRaises(ValueError):
                prep.verify_artifact(self.tree, destination)
            file.write_bytes(original)
        (destination / "extra").touch()
        with self.assertRaises(ValueError):
            prep.verify_artifact(self.tree, destination)

    def test_legacy_tree_export_is_strict_and_never_overwrites(self):
        destination = self.root / "tree-export"
        prep.export_tree(self.tree, destination)
        self.assertEqual(
            prep.approved_files(destination), prep.approved_files(self.tree)
        )
        with self.assertRaises(FileExistsError):
            prep.export_tree(self.tree, destination)
        (self.tree / "README.md").write_text("unhashed")
        with self.assertRaises(ValueError):
            prep.export_tree(self.tree, self.root / "bad-export")
        self.assertFalse((self.root / "bad-export").exists())

    def test_cli_rejects_fifo_before_approval_generation(self):
        client = self.root / "client"
        (client / "p3").mkdir(parents=True)
        self.tree.rename(client / "p3/scripts")
        self.tree = client / "p3/scripts"
        fifo = self.tree / "font.sh"
        fifo.unlink()
        os.mkfifo(fifo)
        with (
            patch.object(prep, "ROOT", client),
            patch.object(sys, "argv", ["prepare_script_rollout.py", "--check"]),
            patch.object(prep, "expected") as generate,
        ):
            with self.assertRaises(ValueError):
                prep.main()
            generate.assert_not_called()

    def test_output_cannot_be_inside_source_or_symlinked(self):
        with self.assertRaises(ValueError):
            prep.prepare_artifact(self.tree, self.tree / "output")
        link = self.root / "link"
        link.symlink_to(self.root / "actual")
        with self.assertRaises(ValueError):
            prep.prepare_artifact(self.tree, link)


class ProductionPreparationTests(unittest.TestCase):
    def test_real_approved_revision_roundtrip_and_no_credentials_required(self):
        protected = [
            compat.LOCK_PATH,
            compat.POLICY_PATH,
            ROOT / "p3/scripts" / compat.MANIFEST,
        ]
        before = {path: path.read_bytes() for path in protected}
        with tempfile.TemporaryDirectory() as temp:
            environment = {"PATH": os.environ["PATH"], "HOME": temp}
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "dev/prepare_script_rollout.py"),
                    "--check",
                    "--artifact-dir",
                    temp,
                ],
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            revision = compat.client_revisions()["preferred_revision"]
            destination = Path(temp) / revision
            prep.verify_artifact(ROOT / "p3/scripts", destination)
            with tarfile.open(destination / "scripts.tar") as archive:
                manifest = archive.extractfile("scripts/" + compat.MANIFEST).read()
                self.assertEqual(
                    manifest, (ROOT / "p3/scripts" / compat.MANIFEST).read_bytes()
                )
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "dev/prepare_script_rollout.py"),
                    "--check",
                    "--verify-artifact",
                    str(destination),
                ],
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(run.returncode, 0, run.stderr)

        self.assertEqual(before, {path: path.read_bytes() for path in protected})

    def test_approval_writer_cannot_be_combined_with_export(self):
        with tempfile.TemporaryDirectory() as temp:
            for flag in ("--artifact-dir", "--export", "--verify-artifact"):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "dev/prepare_script_rollout.py"),
                        "--write",
                        flag,
                        temp,
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("separate review steps", result.stderr)

    def test_preparation_module_has_no_command_or_network_execution(self):
        tree = ast.parse((ROOT / "dev/prepare_script_rollout.py").read_text())
        imports = {
            node.names[0].name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
        }
        imports |= {
            node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        }
        self.assertFalse(
            imports & {"subprocess", "socket", "requests", "urllib", "http.client"}
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                self.assertNotIn(
                    ast.unparse(node.func), {"eval", "exec", "os.system", "os.popen"}
                )

    @unittest.skipUnless(
        shutil.which("ruby"), "Ruby/Psych needed for optional workflow YAML audit"
    )
    def test_workflow_is_manual_read_only_and_artifact_only(self):
        path = ROOT / ".github/workflows/sync-scripts.yml"
        result = subprocess.run(
            [
                "ruby",
                "-rjson",
                "-ryaml",
                "-e",
                "puts JSON.generate(YAML.safe_load(File.read(ARGV[0]), aliases: false))",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        workflow = json.loads(result.stdout)
        self.assertEqual(set(workflow), {"name", "on", "permissions", "jobs"})
        self.assertEqual(workflow["on"], {"workflow_dispatch": None})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(set(workflow["jobs"]), {"prepare-review"})
        job = workflow["jobs"]["prepare-review"]
        self.assertEqual(set(job), {"runs-on", "timeout-minutes", "steps"})
        self.assertEqual(job["runs-on"], "ubuntu-24.04")
        self.assertEqual(job["timeout-minutes"], 10)
        steps = job["steps"]
        self.assertEqual(len(steps), 3)
        self.assertEqual(
            [step.get("uses") for step in steps],
            [
                "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
                None,
                "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
            ],
        )
        self.assertEqual(
            steps[0]["with"], {"ref": "${{ github.sha }}", "persist-credentials": False}
        )
        self.assertEqual(set(steps[1]), {"name", "shell", "run"})
        self.assertEqual(steps[1]["shell"], "bash")
        self.assertEqual(
            steps[1]["run"].splitlines(),
            [
                "set -euo pipefail",
                "python3 -m unittest discover -s dev/tests -p test_script_preparation.py -v",
                'python3 dev/prepare_script_rollout.py --check --artifact-dir "$RUNNER_TEMP/script-preparation"',
            ],
        )
        subprocess.run(["bash", "-n"], input=steps[1]["run"], text=True, check=True)
        self.assertEqual(set(steps[0]), {"name", "uses", "with"})
        self.assertEqual(set(steps[2]), {"name", "uses", "with"})
        self.assertEqual(
            steps[2]["with"],
            {
                "name": "script-review-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}",
                "path": "${{ runner.temp }}/script-preparation/",
                "if-no-files-found": "error",
                "overwrite": False,
                "retention-days": 7,
            },
        )


if __name__ == "__main__":
    unittest.main()
