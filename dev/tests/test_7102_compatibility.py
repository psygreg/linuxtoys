"""7.10.2 compatibility fixtures: real policy, fake HTTP, no payload execution."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
P3 = ROOT / "p3"
sys.path.insert(0, str(P3))
from app import architecture, library_loader, script_compat  # noqa: E402


OBSERVER = r"""
import atexit, importlib.abc, io, json, os, platform, socket, struct, sys
from pathlib import Path
from urllib import request
events = []
native = platform.machine().lower() in ('aarch64', 'arm64')
native_name, foreign_name = ('arm64', 'x86_64') if native else ('x86_64', 'arm64')
scenario = os.environ['APPIMAGE_SCENARIO']
def audit(event, args):
    forbidden = ('subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn')
    if event.startswith('socket.') or event in forbidden:
        raise AssertionError('external execution/network forbidden: ' + event)
sys.addaudithook(audit)
class Response(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.headers = {'Content-Length': str(len(data))}
def fake_open(req, **kwargs):
    url = req.full_url
    events.append({'request_fixture': url})
    release_url = 'https://api.github.com/repos/example/probe/releases/latest'
    if url == release_url:
        names = ([foreign_name] if scenario == 'foreign-asset'
                 else [foreign_name, native_name])
        return Response(json.dumps({'tag_name': 'v1', 'assets': [
            {'name': 'Probe-' + name + '.AppImage',
             'browser_download_url': ('https://fixture.invalid/Probe-'
                                      + name + '.AppImage')}
            for name in names]}).encode())
    if url != 'https://fixture.invalid/Probe-' + native_name + '.AppImage':
        raise AssertionError('unexpected fixture URL: ' + url)
    data = bytearray(4096)
    data[:6] = b'\x7fELF\x02\x01'
    machine = 183 if native else 62
    if scenario == 'foreign-payload':
        machine = 62 if native else 183
    data[18:20] = struct.pack('<H', machine)
    if scenario == 'malformed':
        data[:4] = b'NOPE'
    return Response(bytes(data))
request.urlopen = fake_open
class MissingGuard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == os.environ.get('APPIMAGE_MISSING'):
            raise ImportError('required fixture guard unavailable: ' + fullname)
sys.meta_path.insert(0, MissingGuard())
def profile(frame, event, arg):
    guards = ('asset_eligible', 'select_asset', 'validate_file')
    if event == 'call' and frame.f_code.co_name in guards:
        events.append({'guard': frame.f_code.co_name, 'file': frame.f_code.co_filename})
sys.setprofile(profile)
@atexit.register
def save():
    sys.setprofile(None)
    names = ('app', 'app.architecture', 'app.architecture_files',
             'app.appimage_catalog', '__main__')
    modules = {name: getattr(module, '__file__', None)
               for name, module in sys.modules.items() if name in names}
    payload = {'events': events, 'modules': modules}
    Path(os.environ['APPIMAGE_TRACE']).write_text(json.dumps(payload))
"""

API = """
import json,sys
from app import appimage_catalog
try:
    result = appimage_catalog.resolve_for_update('probe', sys.argv[1], sys.argv[2])
except Exception as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
print(json.dumps(result))
"""


class AppImageInvocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="appimage imports ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bootstrap = self.root / "bootstrap"
        self.bootstrap.mkdir()
        (self.bootstrap / "sitecustomize.py").write_text(OBSERVER)
        self.shadow = self.root / "shadow"
        (self.shadow / "app").mkdir(parents=True)
        self.marker = self.root / "shadow-executed"
        hostile = (
            f"from pathlib import Path\nPath({str(self.marker)!r}).touch()\n"
            "raise AssertionError('untrusted module imported')\n"
        )
        for name in ("architecture.py", "architecture_files.py", "atomic_io.py"):
            (self.shadow / name).write_text(hostile)
            (self.shadow / "app" / name).write_text(hostile)
        (self.shadow / "app/__init__.py").write_text(hostile)
        self.native_name = architecture.label("vendor")
        self.foreign_name = (
            "x86_64" if architecture.host().value == "aarch64" else "arm64"
        )

    def invoke(
        self, mode, scenario="native", *, release=False, missing="", usage=False
    ):
        case = Path(tempfile.mkdtemp(dir=self.root))
        output = case / "output/Probe.AppImage"
        trace_path = case / "trace.json"
        paths = [self.bootstrap]
        if mode != "file":
            paths.append(P3)
        paths.append(self.shadow)
        env = {
            "PATH": os.environ["PATH"],
            "HOME": str(case),
            "TMPDIR": str(case),
            "XDG_CONFIG_HOME": str(case / "config"),
            "XDG_CACHE_HOME": str(case / "cache"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.pathsep.join(map(str, paths)),
            "SCRIPT_DIR": str(self.shadow),
            "APPIMAGE_SCENARIO": scenario,
            "APPIMAGE_TRACE": str(trace_path),
            "APPIMAGE_MISSING": missing,
        }
        name = self.foreign_name if scenario == "foreign-name" else self.native_name
        url = (
            "https://github.com/example/probe"
            if release
            else f"https://fixture.invalid/Probe-{name}.AppImage"
        )
        command = [sys.executable, "-B"]
        if mode == "package":
            command += ["-c", API, url, str(output)]
        else:
            command += (
                ["-m", "app.appimage_catalog"]
                if mode == "module"
                else [str(P3 / "app/appimage_catalog.py")]
            )
            if not usage:
                command += ["--resolve-for-update", "probe", url, str(output)]
        result = subprocess.run(
            command, cwd=self.root, env=env, capture_output=True, text=True, timeout=15
        )
        trace = json.loads(trace_path.read_text())
        self.assertFalse(self.marker.exists(), result.stderr)
        for module, path in trace["modules"].items():
            if module in {
                "app",
                "app.architecture",
                "app.architecture_files",
                "app.appimage_catalog",
            }:
                self.assertTrue(Path(path).is_relative_to(P3 / "app"), (module, path))
        return result, output, trace

    def test_direct_and_module_usage_keep_exit_two_without_guard_imports(self):
        for mode in ("file", "module"):
            with self.subTest(mode=mode):
                result, output, trace = self.invoke(mode, usage=True)
                self.assertEqual(
                    (result.returncode, result.stdout, result.stderr), (2, "", "")
                )
                self.assertFalse(output.exists())
                self.assertEqual(trace["events"], [])
                self.assertNotIn("app.architecture", trace["modules"])

    def test_direct_url_uses_real_architecture_and_payload_guards_in_all_modes(self):
        for mode in ("file", "module", "package"):
            with self.subTest(mode=mode):
                result, output, trace = self.invoke(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output.stat().st_size, 4096)
                guards = [
                    event["guard"] for event in trace["events"] if "guard" in event
                ]
                self.assertEqual(guards, ["asset_eligible", "validate_file"])
                for event in trace["events"]:
                    if "guard" in event:
                        self.assertTrue(Path(event["file"]).is_relative_to(P3 / "app"))
                if mode == "package":
                    self.assertEqual(json.loads(result.stdout)["app_id"], "probe")
                else:
                    self.assertEqual(result.stdout, "\n")

    def test_release_selection_uses_real_native_selector_in_all_modes(self):
        for mode in ("file", "module", "package"):
            with self.subTest(mode=mode):
                result, output, trace = self.invoke(mode, release=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                guards = [
                    event["guard"] for event in trace["events"] if "guard" in event
                ]
                self.assertIn("select_asset", guards)
                self.assertIn("validate_file", guards)
                self.assertTrue(output.is_file())
                self.assertIn("v1", result.stdout)

    def test_foreign_direct_url_is_refused_before_body_request_or_output(self):
        for mode in ("file", "module", "package"):
            with self.subTest(mode=mode):
                result, output, trace = self.invoke(mode, "foreign-name")
                self.assertEqual(result.returncode, 1)
                self.assertIn("verified native architecture", result.stderr)
                self.assertFalse(output.parent.exists())
                self.assertFalse(
                    any("request_fixture" in event for event in trace["events"])
                )

    def test_foreign_release_assets_are_refused_before_payload_request(self):
        for mode in ("file", "module", "package"):
            with self.subTest(mode=mode):
                result, output, trace = self.invoke(mode, "foreign-asset", release=True)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(output.parent.exists())
                self.assertEqual(
                    sum("request_fixture" in event for event in trace["events"]), 1
                )
                self.assertTrue(result.stderr)

    def test_foreign_and_malformed_payloads_fail_closed_in_all_modes(self):
        for mode in ("file", "module", "package"):
            for scenario in ("foreign-payload", "malformed"):
                with self.subTest(mode=mode, scenario=scenario):
                    result, output, trace = self.invoke(mode, scenario)
                    self.assertEqual(result.returncode, 1)
                    self.assertTrue(result.stderr)
                    # Existing behavior leaves the refused file in the caller's
                    # temporary output; it is never executed or integrated.
                    self.assertTrue(output.exists())
                    if scenario == "foreign-payload":
                        self.assertTrue(
                            any(
                                e.get("guard") == "validate_file"
                                for e in trace["events"]
                            )
                        )

    def test_missing_required_guards_never_fall_back_to_shadow_modules(self):
        for mode in ("file", "module", "package"):
            for missing in ("app.architecture", "app.architecture_files"):
                with self.subTest(mode=mode, missing=missing):
                    result, output, trace = self.invoke(mode, missing=missing)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("required fixture guard unavailable", result.stderr)
                    self.assertFalse(self.marker.exists())
                    if missing == "app.architecture":
                        self.assertFalse(output.exists())


class LatencyDevilResolutionTests(unittest.TestCase):
    def test_local_target_is_repo_entry_not_case_mismatched_physical_script(self):
        tree = P3 / "scripts"
        self.assertEqual(
            [p.name for p in tree.rglob("*.sh") if p.stem.casefold() == "latencydevil"],
            [],
        )
        body = (tree / "extra/pdefaults.sh").read_text()
        self.assertEqual(
            re.findall(r"^\s*call_script (latencydevil)\s*$", body, re.MULTILINE),
            ["latencydevil"],
        )
        record = json.loads(
            (tree / "lists/latencydevil/latencydevil.json").read_text()
        )[0]
        self.assertEqual(record["name"], "LatencyDevil")
        record["_list_source"] = str(tree / "lists/latencydevil/latencydevil.json")
        architecture.require_entry(record, "x86_64")
        with self.assertRaises(architecture.ArchitectureError):
            architecture.require_entry(record, "aarch64")
        script_compat.require_bundle(tree)
        architecture.require_script_path(tree / "extra/pdefaults.sh", "x86_64")
        with self.assertRaises(architecture.ArchitectureError):
            architecture.require_script_path(tree / "extra/pdefaults.sh", "aarch64")

    def test_repo_resolver_normalizes_all_cases_without_generating_scripts(self):
        parser = ModuleType("app.repo_parser")
        parser.find_repo_entry_declarations = Mock(return_value=[])
        parser.load_repo_entries = Mock(return_value=[{"repo_app_id": "LATENCYDEVIL"}])
        parser.materialize_repo_script = Mock(return_value={"fixture": "not generated"})
        parser.repo_entry_statically_valid = Mock(return_value=True)
        with (
            patch.dict(sys.modules, {"app.repo_parser": parser}),
            patch.object(
                library_loader,
                "_resolution_scripts_trees",
                return_value=[str(P3 / "scripts")],
            ),
        ):
            for name in ("latencydevil", "LATENCYDEVIL", "LatencyDevil"):
                self.assertEqual(
                    library_loader.materialize_repo_by_app_id(name, str(P3)),
                    ("found", {"fixture": "not generated"}),
                )
            parser.materialize_repo_script.assert_called_with(
                {"repo_app_id": "LATENCYDEVIL"}
            )
            parser.load_repo_entries.return_value = []
            parser.find_repo_entry_declarations.return_value = [
                {"name": "LatencyDevil"}
            ]
            self.assertEqual(
                library_loader.materialize_repo_by_app_id("latencydevil", str(P3)),
                ("incompatible", None),
            )
            parser.find_repo_entry_declarations.assert_called_with(
                str(P3 / "scripts"), "LATENCYDEVIL"
            )

    def test_physical_find_name_matching_remains_case_sensitive(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "LATENCYDEVIL.sh"
            target.write_text("# harmless fixture, never executed\n")
            for name, expected in (
                ("latencydevil.sh", ""),
                ("LATENCYDEVIL.sh", str(target) + "\n"),
            ):
                result = subprocess.run(
                    ["find", directory, "-maxdepth", "3", "-type", "f", "-name", name],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertEqual(result.stdout, expected)
        shell = (P3 / "libs/linuxtoys.bash").read_text()
        self.assertIn('-name "$script_file"', shell)
        self.assertNotIn('-iname "$script_file"', shell)


if __name__ == "__main__":
    unittest.main()
