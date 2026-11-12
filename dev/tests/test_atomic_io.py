"""Deterministic atomic-write fixtures; no application, network or system mutation."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("u1_atomic_io", ROOT / "p3/app/atomic_io.py")
atomic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(atomic)


class AtomicIOTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.path = self.directory / "cache.json"

    def test_replace_publishes_complete_sibling_and_leaves_old_reader_intact(self):
        self.path.write_bytes(b"old")
        replace = os.replace
        def observe(source, target):
            self.assertEqual(Path(source).parent, self.directory)
            self.assertEqual(Path(source).read_bytes(), b"new")
            self.assertEqual(self.path.read_bytes(), b"old")
            replace(source, target)
        with self.path.open("rb") as old_reader, patch.object(atomic.os, "replace", side_effect=observe):
            atomic.atomic_write_bytes(self.path, b"new", tmp_suffix=".stage")
            self.assertEqual(old_reader.read(), b"old")
        self.assertEqual(self.path.read_bytes(), b"new")
        self.assertEqual(list(self.directory.iterdir()), [self.path])

    def test_private_default_and_explicit_mode_before_replacement(self):
        for mode in (None, 0o640, 0o700):
            with self.subTest(mode=mode):
                self.path.write_bytes(b"old")
                self.path.chmod(0o644)
                replace = os.replace
                def observe(source, target):
                    self.assertEqual(stat.S_IMODE(os.stat(source).st_mode), mode or 0o600)
                    replace(source, target)
                with patch.object(atomic.os, "replace", side_effect=observe):
                    atomic.atomic_write_bytes(self.path, b"new", mode=mode)
                self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), mode or 0o600)

    def test_encoding_json_options_parents_and_relative_path(self):
        nested = self.directory / "nested" / "text"
        atomic.atomic_write_text(nested, "café\n", encoding="utf-16")
        self.assertEqual(nested.read_bytes(), "café\n".encode("utf-16"))
        value = {"é": [1, 2]}
        atomic.atomic_write_json(self.path, value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        self.assertEqual(self.path.read_bytes(), json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode())
        previous = Path.cwd()
        try:
            os.chdir(self.directory)
            atomic.atomic_write_text("relative", "ok")
            self.assertEqual(Path("relative").read_text(), "ok")
        finally:
            os.chdir(previous)

    def test_encoding_and_serialization_fail_before_touching_destination(self):
        self.path.write_bytes(b"old")
        for operation in (
            lambda: atomic.atomic_write_text(self.path, "é", encoding="ascii"),
            lambda: atomic.atomic_write_json(self.path, {"bad": object()}),
        ):
            with self.assertRaises((UnicodeError, TypeError)):
                operation()
            self.assertEqual(self.path.read_bytes(), b"old")
            self.assertEqual(list(self.directory.iterdir()), [self.path])

    def test_fsync_reads_flushed_data_before_replace_and_is_opt_in(self):
        events = []
        replace = os.replace
        def sync(fd):
            staged = next(self.directory.iterdir())
            self.assertEqual(staged.stat().st_ino, os.fstat(fd).st_ino)
            self.assertEqual(staged.read_bytes(), b"complete")
            events.append("sync")
        def publish(source, target):
            events.append("replace")
            replace(source, target)
        with patch.object(atomic.os, "fsync", side_effect=sync) as fsync, patch.object(atomic.os, "replace", side_effect=publish):
            atomic.atomic_write_bytes(self.path, b"complete", fsync=True)
            self.assertEqual(events, ["sync", "replace"])
            fsync.reset_mock()
            atomic.atomic_write_bytes(self.path, b"other")
            fsync.assert_not_called()

    def test_failures_preserve_destination_and_clean_staging(self):
        for operation in ("mkstemp", "fdopen", "write", "fsync", "chmod", "replace"):
            with self.subTest(operation=operation):
                self.path.write_bytes(b"old")
                owner = atomic.tempfile if operation == "mkstemp" else atomic.os
                if operation == "write":
                    # Invalid bytes fail inside the file write, after staging opens.
                    with self.assertRaises(TypeError):
                        atomic.atomic_write_bytes(self.path, object())
                else:
                    with patch.object(owner, operation, side_effect=OSError(operation)), self.assertRaises(OSError):
                        atomic.atomic_write_bytes(self.path, b"new", fsync=True, mode=0o600)
                self.assertEqual(self.path.read_bytes(), b"old")
                self.assertEqual(list(self.directory.iterdir()), [self.path])

    def test_failed_first_write_does_not_publish_destination(self):
        with patch.object(atomic.os, "replace", side_effect=OSError("failed")):
            with self.assertRaises(OSError):
                atomic.atomic_write_bytes(self.path, b"new")
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_fdopen_failure_closes_descriptor(self):
        captured = []
        mkstemp = atomic.tempfile.mkstemp
        def create(**kwargs):
            fd, path = mkstemp(**kwargs)
            captured.append(fd)
            return fd, path
        with patch.object(atomic.tempfile, "mkstemp", side_effect=create), patch.object(atomic.os, "fdopen", side_effect=OSError("open")):
            with self.assertRaises(OSError):
                atomic.atomic_write_bytes(self.path, b"new")
        with self.assertRaises(OSError):
            os.fstat(captured[0])
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_concurrent_writes_use_distinct_staging_and_readers_see_whole_values(self):
        count = 8
        values = [bytes([65 + index]) * 32768 for index in range(count)]
        self.path.write_bytes(b"old")
        barrier = threading.Barrier(count)
        staged = []
        lock = threading.Lock()
        replace = os.replace
        def publish(source, target):
            with lock:
                staged.append(source)
            barrier.wait(timeout=10)
            replace(source, target)
            self.assertIn(self.path.read_bytes(), values)
        with patch.object(atomic.os, "replace", side_effect=publish), ThreadPoolExecutor(max_workers=count) as pool:
            list(pool.map(lambda data: atomic.atomic_write_bytes(self.path, data), values))
        self.assertEqual(len(set(staged)), count)
        self.assertIn(self.path.read_bytes(), values)
        self.assertEqual(list(self.directory.iterdir()), [self.path])

    def test_failed_concurrent_writer_cannot_remove_successful_writer_staging(self):
        barrier = threading.Barrier(2)
        replace = os.replace
        def publish(source, target):
            payload = Path(source).read_bytes()
            barrier.wait(timeout=10)
            if payload == b"failed":
                raise OSError("one writer failed")
            replace(source, target)
        def write(data):
            try:
                atomic.atomic_write_bytes(self.path, data)
                return True
            except OSError:
                return False
        with patch.object(atomic.os, "replace", side_effect=publish), ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(write, [b"failed", b"complete"])), [False, True])
        self.assertEqual(self.path.read_bytes(), b"complete")
        self.assertEqual(list(self.directory.iterdir()), [self.path])


if __name__ == "__main__":
    unittest.main()
