"""Offline skill publication and caller contracts; no package/network operations."""

from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import hashlib
import io
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "p3/app"
sys.path.insert(0, str(ROOT / "p3"))
from app import architecture, library_loader, mcp_skill as skill  # noqa: E402


def method(filename, class_name, name, namespace):
    """Load an actual caller method without GTK, threads or application imports."""
    tree = ast.parse((APP / filename).read_text())
    cls = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name
    )
    node = next(
        n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name
    )
    namespace = {"__package__": "app", **namespace}
    exec(compile(ast.Module(body=[node], type_ignores=[]), filename, "exec"), namespace)
    return namespace[name]


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.temp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(self.temp).resolve()
        self.root.chmod(0o700)
        self.home = self.root / "home with spaces"
        self.home.mkdir(mode=0o700)
        self.home.chmod(0o700)
        self.stack.enter_context(
            patch.object(skill.os.path, "expanduser", return_value=str(self.home))
        )
        self.stderr = self.stack.enter_context(
            patch("sys.stderr", new_callable=io.StringIO)
        )
        self.data = (APP / "mcp_skill/SKILL.md").read_bytes()
        self.destination = self.home / ".agents/skills/linuxtoys-mcp"
        self.target = self.destination / "SKILL.md"

    def install(self):
        return skill.install_agent_skill()

    def private_directory(self, path):
        """Create only private fixture parents; never chmod existing unsafe paths."""
        relative = path.relative_to(self.home)
        self.assertNotIn("..", relative.parts)
        current = self.home
        for part in relative.parts:
            current = current / part
            try:
                current.mkdir(mode=0o700)
            except FileExistsError:
                pass
            else:
                # mkdir's mode is still masked by umask, including owner bits.
                # Only newly created disposable fixture directories are changed.
                current.chmod(0o700)
            self.assertFalse(current.is_symlink())
            self.assertEqual(current.stat().st_uid, os.geteuid())
            self.assertEqual(stat.S_IMODE(current.stat().st_mode), 0o700)

    def existing(self, data=None, mode=0o640):
        self.private_directory(self.destination)
        self.target.write_bytes(self.data if data is None else data)
        self.target.chmod(mode)

    def test_fresh_profile_creates_only_universal_private_installation(self):
        self.assertEqual(self.install(), [str(self.destination)])
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o600)
        for path in (self.home / ".agents", self.destination.parent, self.destination):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
        self.assertEqual({p.name for p in self.home.iterdir()}, {".agents"})

    def test_detected_agents_do_not_create_an_extra_universal_directory(self):
        for relative in (".claude", ".config/opencode", ".codex"):
            self.private_directory(self.home / relative)
        installed = self.install()
        self.assertEqual(len(installed), 3)
        self.assertFalse((self.home / ".agents").exists())
        self.assertTrue(
            (self.home / ".config/opencode/skill/linuxtoys-mcp/SKILL.md").is_file()
        )

    def test_missing_corrupt_oversized_or_symlink_bundle_never_mutates_home(self):
        bundle = self.root / "bundle"
        bundle.mkdir()
        path = bundle / "SKILL.md"
        for data in (None, b"not reviewed", b"x" * (skill.MAX_SKILL_BYTES + 1)):
            with self.subTest(data=None if data is None else len(data)):
                path.unlink(missing_ok=True)
                if data is not None:
                    path.write_bytes(data)
                with patch.object(skill, "bundled_skill_path", return_value=str(path)):
                    self.assertEqual(self.install(), [])
                self.assertEqual(list(self.home.iterdir()), [])
        path.unlink()
        path.symlink_to(APP / "mcp_skill/SKILL.md")
        with patch.object(skill, "bundled_skill_path", return_value=str(path)):
            self.assertEqual(self.install(), [])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_corrupt_bundle_preserves_a_working_installation(self):
        self.existing()
        before = self.target.stat()
        corrupt = self.root / "corrupt.md"
        corrupt.write_bytes(b"invalid bundled bytes")
        with patch.object(skill, "bundled_skill_path", return_value=str(corrupt)):
            self.assertEqual(self.install(), [])
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertEqual(self.target.stat().st_ino, before.st_ino)
        self.assertEqual(self.target.stat().st_mtime_ns, before.st_mtime_ns)

    def test_bundle_directory_symlink_is_refused(self):
        link = self.root / "bundle"
        link.symlink_to(APP / "mcp_skill", target_is_directory=True)
        with patch.object(
            skill, "bundled_skill_path", return_value=str(link / "SKILL.md")
        ):
            self.assertEqual(self.install(), [])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_identical_existing_skill_preserves_inode_mtime_and_permissions(self):
        self.existing()
        before = self.target.stat()
        self.assertEqual(self.install(), [str(self.destination)])
        after = self.target.stat()
        self.assertEqual(
            (before.st_ino, before.st_mtime_ns, before.st_mode),
            (after.st_ino, after.st_mtime_ns, after.st_mode),
        )

    def test_customized_older_and_empty_skills_are_preserved(self):
        self.private_directory(self.destination)
        for data in (b"custom instructions", b"older version", b""):
            with self.subTest(data=data):
                self.target.write_bytes(data)
                self.target.chmod(0o600)
                before = self.target.stat()
                self.stderr.seek(0)
                self.stderr.truncate(0)
                self.assertEqual(self.install(), [])
                self.assertEqual(self.target.read_bytes(), data)
                self.assertEqual(self.target.stat().st_ino, before.st_ino)
                self.assertEqual(self.target.stat().st_mtime_ns, before.st_mtime_ns)
                self.assertEqual(self.target.stat().st_mode, before.st_mode)
                self.assertFalse((self.home / ".claude").exists())
                self.assertIn(
                    "Existing customized or older skill preserved; resolve manually",
                    self.stderr.getvalue(),
                )
                self.assertNotIn("Skill directories must", self.stderr.getvalue())

    def test_symlink_file_and_directory_targets_preserve_canaries(self):
        canary = self.root / "outside"
        canary.mkdir()
        data = canary / "SKILL.md"
        data.write_bytes(b"preserve outside")
        self.private_directory(self.destination)
        self.target.symlink_to(data)
        self.assertEqual(self.install(), [])
        self.assertEqual(data.read_bytes(), b"preserve outside")
        self.target.unlink()
        # Remove only the helper-created lock before the directory-link case.
        (self.destination / ".install.lock").unlink(missing_ok=True)
        self.destination.rmdir()
        self.destination.symlink_to(canary, target_is_directory=True)
        self.assertEqual(self.install(), [])
        self.assertEqual({p.name for p in canary.iterdir()}, {"SKILL.md"})

    def test_symlink_parents_home_and_agent_roots_are_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        agent = self.home / ".codex"
        agent.symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.install(), [])
        self.assertFalse((self.home / ".agents").exists())
        self.assertEqual(list(outside.iterdir()), [])
        agent.unlink()
        self.private_directory(self.home / ".agents")
        (self.home / ".agents/skills").symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.install(), [])
        self.assertEqual(list(outside.iterdir()), [])
        alias = self.root / "home-alias"
        alias.symlink_to(self.home, target_is_directory=True)
        with patch.object(skill.os.path, "expanduser", return_value=str(alias)):
            self.assertEqual(self.install(), [])

    def test_unsafe_parent_permissions_are_preserved_and_refused(self):
        agent = self.home / ".claude"
        agent.mkdir(mode=0o777)
        agent.chmod(0o777)
        self.assertEqual(self.install(), [])
        self.assertEqual(stat.S_IMODE(agent.stat().st_mode), 0o777)
        self.assertEqual(list(agent.iterdir()), [])
        self.assertFalse((self.home / ".agents").exists())

    def test_group_writable_skill_parents_preserve_existing_contents(self):
        self.existing(data=b"existing skill in an unsafe tree", mode=0o600)
        before = self.target.stat()
        for directory in (
            self.home / ".agents",
            self.destination.parent,
            self.destination,
        ):
            for mode in (0o770, 0o775, 0o777):
                with self.subTest(
                    directory=directory.relative_to(self.home), mode=oct(mode)
                ):
                    directory.chmod(mode)
                    self.stderr.seek(0)
                    self.stderr.truncate(0)
                    self.assertEqual(self.install(), [])
                    self.assertEqual(stat.S_IMODE(directory.stat().st_mode), mode)
                    self.assertEqual(
                        self.target.read_bytes(), b"existing skill in an unsafe tree"
                    )
                    self.assertEqual(self.target.stat().st_ino, before.st_ino)
                    self.assertEqual(self.target.stat().st_mtime_ns, before.st_mtime_ns)
                    self.assertEqual(self.target.stat().st_mode, before.st_mode)
                    self.assertFalse((self.destination / ".install.lock").exists())
                    self.assertIn("Skill directories must", self.stderr.getvalue())
                    self.assertNotIn(
                        "Existing customized or older", self.stderr.getvalue()
                    )
                    # Restore only this test-created directory for the next case,
                    # after proving the installer left its unsafe mode untouched.
                    directory.chmod(0o700)

    def test_existing_writable_skill_and_nonregular_files_are_refused(self):
        self.existing(mode=0o666)
        self.assertEqual(self.install(), [])
        self.assertEqual(self.target.read_bytes(), self.data)
        self.target.unlink()
        os.mkfifo(self.target)
        self.assertEqual(self.install(), [])
        self.assertTrue(stat.S_ISFIFO(self.target.lstat().st_mode))

    def test_unsafe_lock_does_not_follow_symlink_or_modify_canary(self):
        self.private_directory(self.destination)
        canary = self.root / "lock-canary"
        canary.write_text("preserve")
        (self.destination / ".install.lock").symlink_to(canary)
        self.assertEqual(self.install(), [])
        self.assertEqual(canary.read_text(), "preserve")
        self.assertFalse(self.target.exists())

    def test_contended_lock_has_a_bounded_wait_without_mutation(self):
        with (
            patch.object(skill.fcntl, "flock", side_effect=BlockingIOError),
            patch.object(
                skill.time, "monotonic", side_effect=[0, skill.LOCK_TIMEOUT + 1]
            ),
            patch.object(skill.time, "sleep") as sleep,
        ):
            self.assertEqual(self.install(), [])
            sleep.assert_not_called()
        self.assertFalse(self.target.exists())
        self.assertIn("holds the lock", self.stderr.getvalue())

    def test_helper_imports_only_standard_library_modules(self):
        tree = ast.parse((APP / "mcp_skill.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(
                    all(n.name in sys.stdlib_module_names for n in node.names)
                )
            if isinstance(node, ast.ImportFrom):
                self.assertFalse(node.level)
                self.assertIn(node.module, sys.stdlib_module_names)

    def test_atomic_visibility_and_private_stage(self):
        link = skill.os.link

        def publish(source, target, **kwargs):
            self.assertFalse(self.target.exists())
            fd = os.open(source, os.O_RDONLY, dir_fd=kwargs["src_dir_fd"])
            try:
                self.assertEqual(os.read(fd, len(self.data) + 1), self.data)
                self.assertEqual(stat.S_IMODE(os.fstat(fd).st_mode), 0o600)
            finally:
                os.close(fd)
            link(source, target, **kwargs)

        with patch.object(skill.os, "link", side_effect=publish):
            self.assertTrue(self.install())
        self.assertEqual(list(self.destination.glob(".skill-*.tmp")), [])

    def test_write_sync_and_publication_failures_leave_no_partial_skill(self):
        for operation in ("fdopen", "fsync", "link"):
            with self.subTest(operation=operation):
                with patch.object(
                    skill.os, operation, side_effect=OSError("fixture failure")
                ):
                    self.assertEqual(self.install(), [])
                self.assertFalse(self.target.exists())
                self.assertEqual(list(self.destination.glob(".skill-*.tmp")), [])
        self.assertTrue(self.install())

    def test_partial_write_failure_cannot_publish_partial_contents(self):
        fdopen = skill.os.fdopen

        class PartialWriter:
            def __init__(self, handle):
                self.handle = handle

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.handle.close()

            def fileno(self):
                return self.handle.fileno()

            def write(self, data):
                self.handle.write(data[:20])
                self.handle.flush()
                raise OSError("simulated full filesystem")

        with patch.object(
            skill.os,
            "fdopen",
            side_effect=lambda fd, mode: PartialWriter(fdopen(fd, mode)),
        ):
            self.assertEqual(self.install(), [])
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.destination.glob(".skill-*.tmp")), [])
        self.assertTrue(self.install())

    def test_staging_name_collision_preserves_existing_contents(self):
        self.private_directory(self.destination)
        collision = self.destination / ".skill-fixed.tmp"
        collision.write_bytes(b"preexisting staging or user data")
        with patch.object(skill.secrets, "token_hex", return_value="fixed"):
            self.assertEqual(self.install(), [])
        self.assertEqual(collision.read_bytes(), b"preexisting staging or user data")
        self.assertFalse(self.target.exists())

    def test_directory_sync_failure_keeps_complete_published_file(self):
        sync = skill.os.fsync

        def fail_directory(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError("directory sync unavailable")
            return sync(fd)

        with patch.object(skill.os, "fsync", side_effect=fail_directory):
            self.assertTrue(self.install())
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertIn("durability unavailable", self.stderr.getvalue())

    def test_racing_custom_file_or_symlink_is_never_overwritten(self):
        link = skill.os.link
        for symlink in (False, True):
            with self.subTest(symlink=symlink):

                def race(source, target, **kwargs):
                    if symlink:
                        self.target.symlink_to(self.root / "missing-canary")
                    else:
                        self.target.write_bytes(b"concurrent user contents")
                    return link(source, target, **kwargs)

                with patch.object(skill.os, "link", side_effect=race):
                    self.assertEqual(self.install(), [])
                if symlink:
                    self.assertTrue(self.target.is_symlink())
                    self.assertFalse((self.root / "missing-canary").exists())
                else:
                    self.assertEqual(
                        self.target.read_bytes(), b"concurrent user contents"
                    )
                self.target.unlink()

    def child(self, code):
        env = {**os.environ, "HOME": str(self.home), "PYTHONDONTWRITEBYTECODE": "1"}
        return subprocess.run(
            [sys.executable, "-I", "-B", "-c", code],
            env=env,
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_restrictive_umask_cannot_publish_an_unreadable_or_wrong_mode_file(self):
        self.private_directory(self.destination)
        code = f"import os,sys;sys.path.insert(0,{str(ROOT / 'p3')!r});from app.mcp_skill import main;os.umask(0o200);sys.exit(main())"
        result = self.child(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o600)
        self.assertEqual(
            stat.S_IMODE((self.destination / ".install.lock").stat().st_mode), 0o600
        )

    def test_concurrent_processes_publish_one_complete_private_file(self):
        code = f"import sys;sys.path.insert(0,{str(ROOT / 'p3')!r});from app.mcp_skill import main;sys.exit(main())"
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: self.child(code), range(12)))
        self.assertEqual([(r.returncode, r.stderr) for r in results], [(0, "")] * 12)
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o600)
        self.assertEqual(list(self.destination.glob(".skill-*.tmp")), [])

    def test_process_interruption_before_and_after_publication_is_recoverable(self):
        for after in (False, True):
            with self.subTest(after=after):
                code = f"""import os,signal,sys
sys.path.insert(0,{str(ROOT / 'p3')!r})
from app import mcp_skill as s
link=s.os.link
def interrupt(*args,**kwargs):
    if {after!r}: link(*args,**kwargs)
    os.kill(os.getpid(),signal.SIGKILL)
s.os.link=interrupt
s.main()
"""
                result = self.child(code)
                self.assertEqual(result.returncode, -signal.SIGKILL)
                if after:
                    self.assertEqual(self.target.read_bytes(), self.data)
                else:
                    self.assertFalse(self.target.exists())
                self.assertTrue(self.install())
                self.assertEqual(self.target.read_bytes(), self.data)
                self.target.unlink()

    def test_missing_runner_enqueue_failure_and_empty_job_use_same_offline_helper(self):
        for runner in (
            None,
            SimpleNamespace(
                enqueue_skill_install=Mock(
                    side_effect=ImportError("optional dependency")
                )
            ),
            SimpleNamespace(enqueue_skill_install=Mock(return_value=None)),
        ):
            with (
                self.subTest(runner=runner),
                patch.object(
                    skill, "install_agent_skill", return_value=["safe"]
                ) as install,
            ):
                self.assertEqual(skill.request_skill_install(runner), ["safe"])
                install.assert_called_once_with()
        runner = SimpleNamespace(enqueue_skill_install=Mock(return_value="job-id"))
        with patch.object(skill, "install_agent_skill") as install:
            self.assertEqual(skill.request_skill_install(runner), "job-id")
            runner.enqueue_skill_install.assert_called_once_with(
                skill.skill_install_script()
            )
            install.assert_not_called()

    def test_enqueue_policy_refusal_is_not_retried_directly(self):
        runner = SimpleNamespace(
            enqueue_skill_install=Mock(
                side_effect=architecture.ArchitectureError("policy refused")
            )
        )
        with patch.object(skill, "install_agent_skill") as install:
            with self.assertRaises(architecture.ArchitectureError):
                skill.request_skill_install(runner)
            install.assert_not_called()

    def test_legacy_file_module_and_helper_cli_survive_broken_optional_imports(self):
        for target in (
            str(APP / "mcp_server.py"),
            "app.mcp_server",
            str(APP / "mcp_skill.py"),
        ):
            with self.subTest(target=target):
                code = f"""import importlib.abc,runpy,sys
sys.path.insert(0,{str(ROOT / 'p3')!r})
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name.startswith(('app.easy_cli','app._catalog_rs','gi','requests')):
            raise ImportError('optional stack forbidden')
sys.meta_path.insert(0,Block())
sys.argv=[{target!r},'--install-skill']
if {target!r} == 'app.mcp_server': runpy.run_module('app.mcp_server',run_name='__main__')
else: runpy.run_path({target!r},run_name='__main__')
"""
                result = self.child(code)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.target.read_bytes(), self.data)
                self.assertFalse((self.home / ".config/linuxtoys").exists())
                self.assertNotIn("listening", result.stdout)

    def test_invalid_bundle_cli_is_controlled_without_service_side_effects(self):
        layout = self.root / "layout"
        (layout / "app/mcp_skill").mkdir(parents=True)
        shutil.copyfile(APP / "mcp_skill.py", layout / "app/mcp_skill.py")
        shutil.copyfile(APP / "mcp_server.py", layout / "app/mcp_server.py")
        for value in (None, b"corrupt"):
            if value:
                (layout / "app/mcp_skill/SKILL.md").write_bytes(value)
            result = self.child(
                f"import runpy,sys;sys.argv=['server','--install-skill'];runpy.run_path({str(layout / 'app/mcp_server.py')!r},run_name='__main__')"
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(list(self.home.iterdir()), [])

    def test_generated_script_uses_authoritative_policy_without_remote_execution(self):
        path = self.root / "generated.sh"
        path.write_text(skill.skill_install_script())
        for machine in ("aarch64", "x86_64"):
            with patch.object(architecture.platform, "machine", return_value=machine):
                command = library_loader.script_command(path, ROOT / "p3")
                self.assertEqual(command[:2], ["/bin/bash", "-c"])
        with patch.object(architecture.platform, "machine", return_value="armv7l"):
            with self.assertRaises(architecture.ArchitectureError):
                library_loader.script_command(path, ROOT / "p3")
        path.write_text(
            skill.skill_install_script().replace(
                "# architectures: x86_64, aarch64\n", ""
            )
        )
        with self.assertRaises(architecture.ArchitectureError):
            library_loader.script_command(path, ROOT / "p3")
        self.assertNotIn("bun", skill.skill_install_script().split("exec ")[1])
        subprocess.run(
            ["bash", "-n"], input=skill.skill_install_script(), text=True, check=True
        )


class CallerTests(unittest.TestCase):
    setUp = SkillTests.setUp
    child = SkillTests.child

    def queue_method(self):
        # Execute the actual job method. GTK/PTY and environment construction are
        # mocked; dispatch still invokes the real M1 loader before helper execution.
        return method(
            "appstream_runner.py",
            "AppStreamRunner",
            "_run_skill_install_job",
            {
                "os": os,
                "tempfile": SimpleNamespace(
                    TemporaryDirectory=lambda **kwargs: tempfile.TemporaryDirectory(
                        prefix=kwargs["prefix"], dir=self.root
                    )
                ),
                "script_environment": lambda info, env: {
                    **env,
                    "SCRIPT_DIR": str(ROOT / "p3"),
                },
            },
        )

    def runner(self):
        def dispatch(path, env, **kwargs):
            library_loader.script_command(path, ROOT / "p3")
            result = self.child(
                f"import runpy;runpy.run_path({str(APP / 'mcp_skill.py')!r},run_name='__main__')"
            )
            return result.returncode, result.stdout + result.stderr

        return SimpleNamespace(
            _process=SimpleNamespace(poll=lambda: None),
            _dispatch_path=Mock(side_effect=dispatch),
            _append_transcript=Mock(),
            _failure_reason_from_output=lambda reason, output: output or reason,
        )

    def test_queued_install_and_invalid_bundle_failure_are_controlled(self):
        runner = self.runner()
        record = {"script": skill.skill_install_script(), "name": "skill"}
        code, output = self.queue_method()(runner, record)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertEqual(list(self.root.glob("linuxtoys-skill-*")), [])
        runner._dispatch_path.side_effect = None
        runner._dispatch_path.return_value = (1, "Bundled MCP skill is corrupt")
        code, output = self.queue_method()(runner, record)
        self.assertEqual(code, 1)
        self.assertIn("corrupt", output)
        self.assertEqual(self.target.read_bytes(), self.data)

    def test_queued_architecture_and_required_import_failures_do_not_bypass_guard(self):
        for failure in (
            architecture.ArchitectureError("policy refused"),
            ImportError("required guard unavailable"),
        ):
            with (
                self.subTest(failure=failure),
                patch.object(skill, "install_agent_skill") as install,
            ):
                runner = self.runner()
                runner._dispatch_path.side_effect = failure
                code, output = self.queue_method()(
                    runner, {"script": skill.skill_install_script()}
                )
                self.assertEqual(code, 1)
                self.assertIn(str(failure), output)
                install.assert_not_called()
                self.assertFalse(self.target.exists())

    def test_unreviewed_queued_operation_is_rejected_before_execution(self):
        runner = self.runner()
        code, output = self.queue_method()(runner, {"script": "touch unsafe"})
        self.assertEqual(code, 1)
        runner._dispatch_path.assert_not_called()
        enqueue = method(
            "appstream_runner.py", "AppStreamRunner", "enqueue_skill_install", {}
        )
        with self.assertRaises(ValueError):
            enqueue(SimpleNamespace(), "touch unsafe")

    def test_menu_missing_runner_enqueue_failure_and_optional_service_import(self):
        worker = method(
            "head_menu.py",
            "MenuButton",
            "__mcp_service_worker",
            {
                "os": os,
                "GLib": SimpleNamespace(
                    idle_add=lambda callback, *args: callback(*args)
                ),
            },
        )
        server = SimpleNamespace(
            apply_service_state=Mock(return_value=(True, "enabled"))
        )
        for runner in (
            None,
            SimpleNamespace(
                enqueue_skill_install=Mock(side_effect=RuntimeError("queue gone"))
            ),
        ):
            view = SimpleNamespace(
                parent_window=SimpleNamespace(_appstream_runner=runner),
                _MenuButton__mcp_service_done=Mock(),
            )
            # Extracted function isn't name-mangled by a class compiler.
            setattr(view, "__mcp_service_done", view._MenuButton__mcp_service_done)
            with (
                patch.dict(sys.modules, {"app.mcp_server": server}),
                patch.object(
                    skill, "install_agent_skill", return_value=["safe"]
                ) as install,
            ):
                worker(view, True)
                install.assert_called_once()
                getattr(view, "__mcp_service_done").assert_called_once_with(True, "")
        import builtins

        original = builtins.__import__

        def broken(name, globals=None, locals=None, fromlist=(), level=0):
            if level == 1 and "mcp_server" in fromlist:
                raise ImportError("optional service dependency unavailable")
            return original(name, globals, locals, fromlist, level)

        view = SimpleNamespace(__mcp_service_done=Mock())
        with (
            patch("builtins.__import__", side_effect=broken),
            patch.object(
                skill, "install_agent_skill", return_value=["safe"]
            ) as install,
        ):
            worker(view, True)
            install.assert_called_once()
            self.assertIn(
                "optional", getattr(view, "__mcp_service_done").call_args.args[1]
            )

    def test_server_reexports_helper_in_package_and_direct_import_branches(self):
        tree = ast.parse((APP / "mcp_server.py").read_text())
        end = next(
            i
            for i, n in enumerate(tree.body)
            if isinstance(n, ast.If) and "--install-skill" in ast.unparse(n.test)
        )
        # Only bootstrap/import declarations, stopping before application imports.
        code = compile(
            ast.Module(body=tree.body[:end], type_ignores=[]), "mcp_server.py", "exec"
        )
        for package in ("app", ""):
            namespace = {
                "__package__": package,
                "__name__": "fixture",
                "__file__": str(APP / "mcp_server.py"),
            }
            exec(code, namespace)
            self.assertIs(namespace["install_agent_skill"], skill.install_agent_skill)
            self.assertIs(namespace["skill_install_script"], skill.skill_install_script)

    def test_packaging_copies_helper_and_reviewed_asset_in_all_layouts(self):
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), skill.BUNDLED_SHA256)
        self.assertEqual(
            self.data, (ROOT / "skills/linuxtoys-mcp/SKILL.md").read_bytes()
        )
        recipes = {
            "deb": ("dev/build/deb/package.py", 'root / "p3",'),
            "rpm": ("dev/build/copr/linuxtoys.spec", "cp -a p3/."),
            "appimage": ("dev/build/appimage/build.sh", 'cp -a "$ROOT_DIR/p3/."'),
            "arch-source": ("dev/build/pkg/build.sh", 'cp -rf "$ROOT_DIR/p3"/*'),
        }
        for layout, (recipe, copy) in recipes.items():
            with self.subTest(layout=layout):
                self.assertIn(copy, (ROOT / recipe).read_text())
                dest = self.root / layout
                # Same complete tree copy contract; no build/package tool invoked.
                shutil.copytree(
                    APP,
                    dest / "app",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
                self.assertTrue((dest / "app/mcp_skill.py").is_file())
                self.assertEqual(
                    (dest / "app/mcp_skill/SKILL.md").read_bytes(), self.data
                )
                result = self.child(
                    f"import runpy;runpy.run_path({str(dest / 'app/mcp_skill.py')!r},run_name='__main__')"
                )
                self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "cp -rf ${srcdir}/linuxtoys-${pkgver}/usr/*",
            (ROOT / "dev/build/pkg/PKGBUILD").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
