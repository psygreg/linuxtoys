"""Loader invocation/import regressions with isolated files and no shell/network execution."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LOADER = ROOT / 'p3/app/library_loader.py'
MODES = ('file', 'module', 'package', 'standalone')

ARCHITECTURE_FIXTURE = '''
import json,os
from pathlib import Path
class ArchitectureError(RuntimeError): pass
def record(value):
    with open(os.environ['LOADER_EVENTS'], 'a') as handle:
        handle.write(json.dumps(value)+'\\n')
def require_script_path(path):
    record('path-guard')
    if os.environ.get('LOADER_REFUSE'):
        raise ArchitectureError('fixture policy refusal')
def require_script(text): record('text-guard')
def require_overrides(*args): record('override-guard')
def host(): record('host-guard'); return 'aarch64'
def resolve_hook_path(root,path,*args): return str(Path(root)/path)
'''

BOOTSTRAP_FIXTURE = '''
import json,os,socket,subprocess
from pathlib import Path
def forbidden(*args,**kwargs): raise AssertionError('network/process execution forbidden')
socket.socket=forbidden
subprocess.Popen=forbidden
def capture(executable,argv,env):
    Path(os.environ['LOADER_EXEC']).write_text(json.dumps({
        'executable':executable,'argv':argv,
        'environment':{key:env.get(key) for key in (
            'SCRIPT_DIR','LINUXTOYS_SCRIPT_NAME','LINUXTOYS_APP_ID',
            'LINUXTOYS_APP_DESCRIPTION','LINUXTOYS_REQUIRE_CACHYOS_MIRRORS')}
    }))
    raise SystemExit(0)
os.execve=capture
'''


class LoaderImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='loader imports ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.script_dir = self.root / 'p3'
        self.app = self.script_dir / 'app'
        self.app.mkdir(parents=True)
        (self.app / '__init__.py').write_text('')
        shutil.copyfile(LOADER, self.app / 'library_loader.py')
        (self.app / 'architecture.py').write_text(ARCHITECTURE_FIXTURE)
        self.bootstrap = self.root / 'bootstrap'
        self.bootstrap.mkdir()
        (self.bootstrap / 'sitecustomize.py').write_text(BOOTSTRAP_FIXTURE)
        libs = self.script_dir / 'libs'
        libs.mkdir()
        names = ('fsops', 'packages', 'boot', 'misc', 'sysd', 'helpers',
                 'optimizers', 'linuxtoys', 'sysinfo')
        for name in names:
            (libs / (name + '.bash')).write_text('# fixture only; never sourced\n')
        (self.script_dir / 'scripts').mkdir()
        self.script = self.root / "script with 'quotes' and spaces.sh"
        self.script.write_text('# architectures: aarch64, x86_64\n# name: title_key\n# description: desc_key\nprintf NEVER_EXECUTED\n')
        self.events = self.root / 'events.jsonl'
        self.executed = self.root / 'exec.json'
        self.environment = {
            'PATH': os.environ['PATH'], 'HOME': str(self.root),
            'PYTHONDONTWRITEBYTECODE': '1', 'SCRIPT_DIR': str(self.script_dir),
            'LOADER_EVENTS': str(self.events), 'LOADER_EXEC': str(self.executed),
            'LINUXTOYS_EXECUTION_SESSION_DIR': str(self.root / 'uncreated-session'),
        }

    def run_mode(self, mode, action='command', *, refuse=False, no_arguments=False):
        self.events.write_text('')
        self.executed.unlink(missing_ok=True)
        env = dict(self.environment)
        if refuse:
            env['LOADER_REFUSE'] = '1'
        search = [self.bootstrap]
        search.append(self.app if mode == 'standalone' else self.script_dir)
        # Direct file execution must bootstrap app itself, as the Bash caller does.
        if mode == 'file':
            search = [self.bootstrap]
        env['PYTHONPATH'] = os.pathsep.join(map(str, search))
        command = [sys.executable, '-B']
        if mode == 'file':
            command.append(str(self.app / 'library_loader.py'))
        elif mode == 'module':
            command.extend(['-m', 'app.library_loader'])
        else:
            load = 'import library_loader as loader' if mode == 'standalone' else 'from app import library_loader as loader'
            statements = {
                'command': "print(json.dumps(loader.script_command(sys.argv[1],sys.argv[2])))",
                'metadata': "print(json.dumps(loader.script_info_from_path(sys.argv[1],sys.argv[2],{})))",
                'trees': "print(json.dumps(loader._resolution_scripts_trees(sys.argv[2])))",
                'refresh': "print(json.dumps(loader._refresh_cold_appstream_catalog()))",
                'exec': "loader.exec_script(loader.script_info_from_path(sys.argv[1],sys.argv[2],os.environ),sys.argv[2],sys.argv[3:],os.environ)",
            }
            # The production resolver/refresh callers bootstrap this root first.
            setup = 'sys.path.insert(0,sys.argv[2]);' if action in ('trees', 'refresh') else ''
            command.extend(['-c', 'import os,sys,json;' + load + ';' + setup + statements[action]])
        if not no_arguments:
            command.append(str(self.script))
            if mode in ('file', 'module'):
                command.extend(['literal $() ; argument', 'two'])
            else:
                command.append(str(self.script_dir))
                if action == 'exec':
                    command.extend(['literal $() ; argument', 'two'])
        return subprocess.run(command, cwd=self.root, env=env, capture_output=True, text=True, timeout=10)

    def event_values(self):
        return [json.loads(line) for line in self.events.read_text().splitlines()]

    def test_direct_file_and_module_cli_keep_usage_and_start_without_optional_modules(self):
        for mode in ('file', 'module'):
            with self.subTest(mode=mode):
                result = self.run_mode(mode, no_arguments=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertEqual(result.stderr.strip(), 'Usage: library_loader.py SCRIPT [ARG ...]')
                self.assertFalse(self.executed.exists())
                self.assertEqual(self.event_values(), [])

    def test_package_and_standalone_api_guard_and_command_are_identical(self):
        commands = []
        for mode in ('package', 'standalone'):
            with self.subTest(mode=mode):
                result = self.run_mode(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                commands.append(json.loads(result.stdout))
                self.assertEqual(self.event_values(), ['path-guard', 'host-guard', 'text-guard'])
                self.assertFalse(self.executed.exists())
                self.assertFalse((self.root / 'uncreated-session').exists())
        self.assertEqual(commands[0], commands[1])
        self.assertEqual(commands[0][:2], ['/bin/bash', '-c'])
        self.assertEqual(commands[0][-1], str(self.script))
        self.assertTrue(commands[0][2].endswith('source "$0" "$@"\n'))

    def test_policy_failure_precedes_preamble_and_execution_in_all_modes(self):
        self.script.unlink()
        for mode in MODES:
            with self.subTest(mode=mode):
                # CLI reads metadata first, so test its guard with the file present.
                if mode in ('file', 'module'):
                    self.script.write_text('# name: fixture\n')
                else:
                    self.script.unlink(missing_ok=True)
                result = self.run_mode(mode, refuse=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ArchitectureError: fixture policy refusal', result.stderr)
                self.assertNotIn('FileNotFoundError', result.stderr)
                events = self.event_values()
                self.assertIn('path-guard', events)
                self.assertNotIn('host-guard', events)
                self.assertNotIn('text-guard', events)
                self.assertFalse(self.executed.exists())

    def test_required_architecture_import_failures_remain_fail_closed(self):
        required = self.app / 'architecture.py'
        for contents, error in (
            (None, "No module named 'app.architecture'"),
            ('raise ImportError("required policy import failed")\n', 'required policy import failed'),
            ('raise RuntimeError("required policy initialization failed")\n', 'required policy initialization failed'),
        ):
            required.unlink(missing_ok=True)
            if contents:
                required.write_text(contents)
            for mode in MODES:
                with self.subTest(contents=contents, mode=mode):
                    result = self.run_mode(mode)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(error, result.stderr)
                    self.assertFalse(self.executed.exists())
                    self.assertEqual(self.event_values(), [])

    def test_all_entry_styles_preserve_argv_metadata_and_missing_translation_fallback(self):
        results = []
        for mode in MODES:
            with self.subTest(mode=mode):
                result = self.run_mode(mode, 'exec')
                self.assertEqual(result.returncode, 0, result.stderr)
                entry = json.loads(self.executed.read_text())
                results.append(entry)
                self.assertEqual(entry['executable'], '/bin/bash')
                self.assertEqual(entry['argv'][-3:], [str(self.script), 'literal $() ; argument', 'two'])
                self.assertEqual(entry['environment']['LINUXTOYS_SCRIPT_NAME'], 'title_key')
                self.assertEqual(entry['environment']['LINUXTOYS_APP_DESCRIPTION'], 'desc_key')
        self.assertTrue(all(entry == results[0] for entry in results))

    def test_translation_optional_import_failures_keep_existing_fallback(self):
        for error in ('ImportError', 'OSError', 'KeyError'):
            (self.app / 'lang_utils.py').write_text('raise ' + error + '("fixture optional import failure")\n')
            for mode in MODES:
                with self.subTest(error=error, mode=mode):
                    result = self.run_mode(mode, 'exec')
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(self.executed.read_text())['environment']['LINUXTOYS_SCRIPT_NAME'], 'title_key')

    def test_unexpected_translation_import_failure_still_propagates(self):
        (self.app / 'lang_utils.py').write_text('raise RuntimeError("unexpected translation failure")\n')
        for mode in MODES:
            with self.subTest(mode=mode):
                result = self.run_mode(mode, 'exec')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('RuntimeError: unexpected translation failure', result.stderr)
                self.assertFalse(self.executed.exists())

    def test_successful_optional_translation_keeps_localized_metadata(self):
        (self.app / 'lang_utils.py').write_text('def load_translations(): return {"title_key":"Localized title","desc_key":"Localized description"}\n')
        for mode in MODES:
            with self.subTest(mode=mode):
                result = self.run_mode(mode, 'exec')
                self.assertEqual(result.returncode, 0, result.stderr)
                environment = json.loads(self.executed.read_text())['environment']
                self.assertEqual(environment['LINUXTOYS_SCRIPT_NAME'], 'Localized title')
                self.assertEqual(environment['LINUXTOYS_APP_DESCRIPTION'], 'Localized description')

    def test_optional_active_tree_missing_or_failed_keeps_bundled_fallback(self):
        for contents in (None, 'raise ImportError("missing optional backend")\n', 'raise RuntimeError("failed optional backend")\n', 'def get_available_scripts_dir(): raise RuntimeError("failed optional lookup")\n'):
            path = self.app / 'git_scripts_manager.py'
            path.unlink(missing_ok=True)
            if contents:
                path.write_text(contents)
            for mode in ('package', 'standalone'):
                with self.subTest(contents=contents, mode=mode):
                    result = self.run_mode(mode, 'trees')
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout), [str(self.script_dir / 'scripts')])

    def test_optional_active_tree_success_keeps_active_then_bundled_order(self):
        active = self.root / 'active scripts'
        active.mkdir()
        (self.app / 'git_scripts_manager.py').write_text(
            'def get_available_scripts_dir(): return ' + repr(str(active)) + '\n'
        )
        for mode in ('package', 'standalone'):
            with self.subTest(mode=mode):
                result = self.run_mode(mode, 'trees')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), [str(active), str(self.script_dir / 'scripts')])

    def test_optional_cache_missing_or_importerror_returns_false(self):
        for contents in (None, 'raise ImportError("cache import failed")\n'):
            path = self.app / 'appstream_cache.py'
            path.unlink(missing_ok=True)
            if contents:
                path.write_text(contents)
            for mode in ('package', 'standalone'):
                with self.subTest(contents=contents, mode=mode):
                    result = self.run_mode(mode, 'refresh')
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIs(json.loads(result.stdout), False)

    def test_cache_unexpected_import_error_propagates_but_refresh_failure_remains_best_effort(self):
        path = self.app / 'appstream_cache.py'
        for contents, expected in (
            ('raise RuntimeError("cache initialization failed")\n', False),
            ('def cache_needs_refresh(): return True\ndef refresh_cache(): raise RuntimeError("refresh failed")\n', True),
        ):
            path.write_text(contents)
            for mode in ('package', 'standalone'):
                with self.subTest(expected=expected, mode=mode):
                    result = self.run_mode(mode, 'refresh')
                    if expected:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIs(json.loads(result.stdout), True)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn('RuntimeError: cache initialization failed', result.stderr)


if __name__ == '__main__':
    unittest.main()
