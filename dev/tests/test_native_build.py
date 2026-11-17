"""Build-driver regressions and native Rust/Python GUI ABI qualification.

The driver tests use recording tools, never download or build dependencies.
The ABI test compiles the actual repr(C) declarations with native rustc; it
requires Linux and does not claim that GTK was started or widgets exercised.
"""

from __future__ import annotations

import ctypes
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BuildDriverTests(unittest.TestCase):
    def exercise_build(self, relative: bool) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "checkout with spaces"
            (source / "src/catalog-rs").mkdir(parents=True)
            (source / "src/gui-rs").mkdir(parents=True)
            shutil.copyfile(ROOT / "build-rust.sh", source / "build-rust.sh")
            tools = base / "tools"
            tools.mkdir()
            (tools / "maturin").write_text(
                '#!/bin/sh\nprintf "%s\\n" "$@" > "$BUILD_LOG/maturin"\n'
            )
            (tools / "cargo").write_text(
                '#!/bin/sh\nprintf "%s\\n" "$@" > "$BUILD_LOG/cargo"\n'
                'mkdir -p "$CARGO_TARGET_DIR/release"\n'
                'printf native-fixture > "$CARGO_TARGET_DIR/release/liblinuxtoys_gui.so"\n'
            )
            for tool in tools.iterdir():
                tool.chmod(0o755)
            target = "isolated-target" if relative else str(base / "isolated-target")
            output = base / "artifacts"
            env = dict(
                os.environ,
                PATH=str(tools) + os.pathsep + os.environ["PATH"],
                CARGO_TARGET_DIR=target,
                BUILD_LOG=str(base),
            )
            result = subprocess.run(
                ["bash", str(source / "build-rust.sh"), "build", "--out", str(output)],
                cwd=base,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(
                (output / "liblinuxtoys_gui.so").read_text(), "native-fixture"
            )
            for name in ("cargo", "maturin"):
                self.assertIn("--locked", (base / name).read_text().splitlines())

    def test_external_absolute_target_directory(self):
        self.exercise_build(False)

    def test_external_relative_target_directory(self):
        self.exercise_build(True)


class ApplicationLifecycleTests(unittest.TestCase):
    def test_window_close_does_not_delete_shared_runner_state(self):
        import ast
        from types import SimpleNamespace
        from unittest.mock import Mock

        module = ast.parse((ROOT / "p3/app/window.py").read_text())
        window = next(
            item
            for item in module.body
            if isinstance(item, ast.ClassDef) and item.name == "AppWindow"
        )
        method = next(
            item
            for item in window.body
            if isinstance(item, ast.FunctionDef) and item.name == "_close_application"
        )
        removal = Mock()
        application = SimpleNamespace(quit=Mock())
        runner = SimpleNamespace(shutdown=Mock())
        subject = SimpleNamespace(
            _navigation_prewarm_generation=0,
            _save_window_state=lambda: None,
            _save_featured_sense=lambda: None,
            _appstream_runner=runner,
            get_application=lambda: application,
        )
        namespace = {
            "os": SimpleNamespace(path=SimpleNamespace(exists=lambda path: True)),
            "shutil": SimpleNamespace(rmtree=removal),
        }
        exec(
            compile(ast.Module(body=[method], type_ignores=[]), "window-close", "exec"),
            namespace,
        )
        namespace["_close_application"](subject)
        removal.assert_not_called()
        runner.shutdown.assert_called_once()
        application.quit.assert_called_once()


class UpdateArchitectureTests(unittest.TestCase):
    @unittest.skipUnless(
        sys.platform == "linux", "Linux installer environment required"
    )
    def test_update_release_selection_refuses_foreign_asset_before_privilege(self):
        sys.path.insert(0, str(ROOT / "p3"))
        from app.architecture import host

        foreign = "amd64" if host().value == "aarch64" else "arm64"
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "checkout"
            (source / "p3").mkdir(parents=True)
            (source / ".git").mkdir()
            app = source / "p3/app"
            app.mkdir()
            (app / "__init__.py").write_text("")
            (app / "__init__.py").chmod(0o644)
            for name in (
                "architecture.py",
                "architecture_cli.py",
                "architecture_files.py",
                "architecture_flatpak.py",
            ):
                shutil.copyfile(ROOT / "p3/app" / name, app / name)
                (app / name).chmod(0o644)
            # The installer trusts a local checkout only when its shared
            # package guards are present alongside the architecture helpers.
            libs = source / "p3/libs"
            libs.mkdir()
            shutil.copyfile(ROOT / "p3/libs/packages.bash", libs / "packages.bash")
            (libs / "packages.bash").chmod(0o644)
            for path in (source, source / "p3", app, libs):
                path.chmod(0o755)
            installer = (ROOT / "install.sh").read_text()
            # Exercise the real installer functions, without the interactive entry.
            installer = installer.split("if [ -t 0 ] &&", 1)[0]
            asset = {
                "name": f"linuxtoys_{foreign}.deb",
                "browser_download_url": f"https://example.invalid/linuxtoys_{foreign}.deb",
            }
            import json

            release = {
                "tag_name": "qualification",
                "assets": [
                    asset,
                    {
                        "name": "sha256sums.txt",
                        "browser_download_url": "https://example.invalid/sha256sums.txt",
                    },
                ],
            }
            (base / "release.json").write_text(json.dumps(release))
            installer += '\ncurl() { local next=0 arg output=""; for arg in "$@"; do if [ "$next" = 1 ]; then output="$arg"; next=0; elif [ "$arg" = -o ]; then next=1; fi; done; if [ -n "$output" ]; then : > "$output"; else cat "$FIXTURE/release.json"; fi; }\n'
            installer += (
                'sudo() { touch "$FIXTURE/privileged"; return 99; }\ninstaller\n'
            )
            script = source / "install.sh"
            script.write_text(installer)
            env = dict(
                os.environ,
                FIXTURE=str(base),
                TMPDIR=str(base),
                LINUXTOYS_NONINTERACTIVE="1",
            )
            result = subprocess.run(
                ["bash", str(script)],
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((base / "privileged").exists())
            self.assertIn("No unique verified native", result.stdout)


@unittest.skipUnless(
    sys.platform == "linux" and shutil.which("rustc"), "native Linux rustc required"
)
class NativeGuiAbiTests(unittest.TestCase):
    def test_rust_repr_c_matches_every_ctypes_structure(self):
        spec = importlib.util.spec_from_file_location(
            "qualification_gui_rs", ROOT / "p3/app/gui_rs.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        structures = {
            "LtGui" + name.lstrip("_"): value
            for name, value in vars(module).items()
            if isinstance(value, type) and issubclass(value, ctypes.Structure)
        }
        source = (ROOT / "src/gui-rs/lib.rs").read_text()
        declarations = dict(
            re.findall(r"#\[repr\(C\)\]\s*pub struct (\w+) \{([^}]+)\}", source)
        )
        self.assertEqual(set(structures), set(declarations))
        self.assertEqual(ctypes.sizeof(ctypes.c_void_p), 8)
        program = [
            "use std::ffi::c_char;",
            "use std::mem::{size_of, align_of, MaybeUninit};",
        ]
        assertions = []
        for name, body in declarations.items():
            program.append(f"#[repr(C)]\nstruct {name} {{{body}}}")
            value = structures[name]
            self.assertEqual(
                set(re.findall(r"^\s*(\w+):", body, re.M)),
                {field[0] for field in value._fields_},
            )
            assertions.append(
                f'assert_eq!(size_of::<{name}>(), {ctypes.sizeof(value)}, "{name} size");'
            )
            assertions.append(
                f'assert_eq!(align_of::<{name}>(), {ctypes.alignment(value)}, "{name} alignment");'
            )
            assertions.append(
                f"let storage = MaybeUninit::<{name}>::uninit(); let pointer = storage.as_ptr();"
            )
            for field, _ in value._fields_:
                assertions.append(
                    f"assert_eq!(unsafe {{std::ptr::addr_of!((*pointer).{field}) as usize - pointer as usize}}, "
                    f'{getattr(value, field).offset}, "{name}.{field} offset");'
                )
        program.append("fn main() {" + "\n".join(assertions) + "}")
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "abi.rs"
            executable = Path(directory) / "abi"
            probe.write_text("\n".join(program))
            subprocess.run(
                ["rustc", "--edition=2021", str(probe), "-o", str(executable)],
                check=True,
                timeout=30,
            )
            subprocess.run([str(executable)], check=True, timeout=10)


if __name__ == "__main__":
    unittest.main()
