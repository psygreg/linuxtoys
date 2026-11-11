"""Metadata and safety regressions; actual lifecycle qualification runs in Docker."""

from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p3"))
spec = importlib.util.spec_from_file_location(
    "deb_package", ROOT / "dev/build/deb/package.py"
)
assert spec is not None and spec.loader is not None
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)
from app import architecture  # noqa: E402


class DebPackagingTests(unittest.TestCase):
    def test_control_uses_central_native_architecture_for_arm_and_x86(self):
        for machine in ("aarch64", "x86_64"):
            with (
                tempfile.TemporaryDirectory() as temp,
                patch.object(architecture.platform, "machine", return_value=machine),
            ):
                root = Path(temp)
                (root / "usr/lib/linuxtoys").mkdir(parents=True)
                (root / "usr/lib/linuxtoys/example").write_text("payload")
                arch = architecture.label("deb")
                packaging.control(
                    ROOT, root, "7.9.8-1~fixture", arch, "libc6 (>= 2.38)"
                )
                control = (root / "DEBIAN/control").read_text()
                self.assertIn(f"Architecture: {arch}\n", control)
                self.assertEqual(root.stat().st_mode & 0o777, 0o755)
                self.assertIn("python3-gi-cairo", control)
                self.assertIn("gir1.2-vte-2.91", control)
                self.assertIn("libc6 (>= 2.38)", control)
                self.assertNotIn("Architecture: all", control)
                self.assertEqual(
                    {p.name for p in (root / "DEBIAN").iterdir()},
                    {"control", "md5sums"},
                )
                self.assertIn(
                    "usr/lib/linuxtoys/example", (root / "DEBIAN/md5sums").read_text()
                )

    def test_foreign_metadata_is_rejected_before_control_creation(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(architecture.platform, "machine", return_value="aarch64"),
        ):
            with self.assertRaises(ValueError):
                packaging.control(ROOT, Path(temp), "7.9.8-1", "amd64", "libc6")
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_runtime_symlink_rejected_before_staging(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "p3").mkdir()
            (root / "p3/link").symlink_to("/etc/passwd")
            with self.assertRaisesRegex(ValueError, "file type"):
                packaging.stage(root, root / "stage", root / "native")
            self.assertFalse((root / "stage").exists())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO required")
    def test_runtime_fifo_rejected_before_staging(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "p3").mkdir()
            os.mkfifo(root / "p3/pipe")
            with self.assertRaisesRegex(ValueError, "file type"):
                packaging.stage(root, root / "stage", root / "native")
            self.assertFalse((root / "stage").exists())

    def test_existing_sibling_compatibility_links_are_safe_to_materialize(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "helpers.bash").write_text("data")
            (root / "helpers.lib").symlink_to("helpers.bash")
            packaging.check_inputs(root)
            (root / "directory").mkdir()
            (root / "directory-link").symlink_to("directory")
            with self.assertRaisesRegex(ValueError, "file type"):
                packaging.check_inputs(root)

    def test_builder_is_local_and_reuses_source_build_entry(self):
        builder = ROOT / "dev/build/deb/build.sh"
        text = builder.read_text()
        subprocess.run(["bash", "-n", str(builder)], check=True)
        self.assertIn('architecture_cli.py" label deb', text)
        self.assertIn('"$WORK/build-rust.sh" build --out', text)
        self.assertIn("dpkg-shlibdeps -O", text)
        self.assertIn("--root-owner-group", text)
        self.assertNotIn("dput", text)
        self.assertNotIn("launchpad.net", text)
        self.assertNotIn("debuild -S", text)
        self.assertNotIn('rm -rf "$OUTPUT_PATH"', text)
        self.assertIn("output.exists()", text)
        self.assertIn("--locked", (ROOT / "build-rust.sh").read_text())

    @unittest.skipUnless(
        sys.platform == "linux" and shutil.which("dpkg-architecture"),
        "native Linux dpkg required",
    )
    def test_invalid_output_refused_before_build_or_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            existing = root / "existing"
            existing.mkdir()
            marker = existing / "marker"
            marker.write_text("preserved")
            link = root / "link"
            link.symlink_to(root / "uncreated")
            for output in (existing, link, ROOT / "forbidden-package-output"):
                result = subprocess.run(
                    [
                        "bash",
                        str(ROOT / "dev/build/deb/build.sh"),
                        (ROOT / "src/ver").read_text().strip(),
                        str(output),
                    ],
                    env=dict(os.environ, SOURCE_DATE_EPOCH="1794389593"),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("Output must", result.stderr)
            self.assertEqual(marker.read_text(), "preserved")
            self.assertFalse((root / "uncreated").exists())
            self.assertFalse((ROOT / "forbidden-package-output").exists())


if __name__ == "__main__":
    unittest.main()
