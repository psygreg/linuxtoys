"""Font-data integrity, failure ordering and user-file rollback regressions."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p3"))


class FontRouteTests(unittest.TestCase):
    def run_shell(self, code: str, home: Path) -> subprocess.CompletedProcess:
        setup = f"""
source {shlex.quote(str(ROOT / "p3/libs/fsops.bash"))}
fatal() {{ echo "$*" >&2; exit 37; }}
_architecture_check() {{ python3 "$SCRIPT_DIR/app/architecture_cli.py" "$@" || fatal refused; }}
_append_transmap() {{ printf '%s\\n' "$*" >> "$HOME/transmap"; }}
sudo_() {{ touch "$HOME/privilege-attempt"; exit 39; }}
"""
        return subprocess.run(
            ["bash", "-c", setup + code],
            capture_output=True,
            text=True,
            env=dict(os.environ, HOME=str(home), SCRIPT_DIR=str(ROOT / "p3")),
        )

    def test_checksum_and_download_failure_precede_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            data = home / "font.ttf"
            data.write_bytes(b"font fixture")
            digest = hashlib.sha256(data.read_bytes()).hexdigest()
            # A downloader can fail or return different bytes; neither is compatibility.
            for downloader, checksum in [("return 22", digest), ("return 0", "0" * 64)]:
                code = f"""curl() {{ {downloader}; }}
font_download https://example.invalid/font.ttf {shlex.quote(str(data))} {checksum}
mkdir "$HOME/installed"
"""
                result = self.run_shell(code, home)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((home / "installed").exists())
                self.assertFalse((home / "privilege-attempt").exists())

    def test_invalid_font_rejected_before_existing_directory_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / ".local/share/fonts/Example"
            target.mkdir(parents=True)
            (target / "original").write_text("preserve")
            font = home / "test.ttf"
            font.write_bytes(b"invalid font")
            result = self.run_shell(
                f"fc-scan() {{ return 1; }}\nfont_install Example {shlex.quote(str(font))}",
                home,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((target / "original").read_text(), "preserve")
            self.assertFalse(target.with_suffix(".bak").exists())
            self.assertFalse((home / "privilege-attempt").exists())

    def test_font_destination_cannot_escape_through_parent_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home, outside = base / "profile", base / "unrelated"
            home.mkdir()
            outside.mkdir()
            (home / ".local/share").mkdir(parents=True)
            (home / ".local/share/fonts").symlink_to(outside, target_is_directory=True)
            font = home / "test.ttf"
            font.write_bytes(b"font fixture")
            result = self.run_shell(
                f"fc-scan() {{ printf family; }}\nfont_install Example {shlex.quote(str(font))}",
                home,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse((home / "privilege-attempt").exists())

    def test_rollback_preserves_paths_with_spaces_and_shell_characters(self):
        from app.revert_helper import (
            _parse_operation,
            _reverse_file_deletion,
            _reverse_file_restoration,
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fonts with spaces; literal"
            path.mkdir()
            (path / "new-font").touch()
            op, operands = _parse_operation(f"created {path}")
            self.assertEqual(operands, [str(path)])
            subprocess.run(
                ["bash", "-c", _reverse_file_deletion(operands[0])], check=True
            )
            self.assertFalse(path.exists())
            path.mkdir()
            (path / "new-font").touch()
            backup = Path(str(path) + ".bak")
            backup.mkdir()
            (backup / "original").write_text("preserve")
            subprocess.run(
                ["bash", "-c", _reverse_file_restoration(str(path))], check=True
            )
            self.assertEqual((path / "original").read_text(), "preserve")
            self.assertFalse(backup.exists())


if __name__ == "__main__":
    unittest.main()
