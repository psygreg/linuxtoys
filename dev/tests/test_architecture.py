"""Offline architecture policy, payload and mutation-order regression tests.

Run: python3 -m unittest discover -s dev/tests -v
No installer, privilege escalation, network request or system change is needed.
"""

from __future__ import annotations

import hashlib
import contextlib
import shutil
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p3"))
from app import architecture as policy  # noqa: E402 - source-tree test bootstrap
from app import architecture_files as files  # noqa: E402
from app import architecture_flatpak as flatpak  # noqa: E402


def elf(machine: int) -> bytes:
    value = bytearray(4096)
    value[:6] = b"\x7fELF\x02\x01"
    value[18:20] = struct.pack("<H", machine)
    return bytes(value)


def tar_bytes(members: dict[str, bytes]) -> bytes:
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode="w") as archive:
        for name, data in members.items():
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    return result.getvalue()


class ArchitectureTests(unittest.TestCase):
    def test_aliases(self):
        for value in ("aarch64", "arm64", "ARM64"):
            self.assertEqual(policy.normalize(value), policy.Architecture.AARCH64)
        for value in ("x86_64", "amd64", "x64"):
            self.assertEqual(policy.normalize(value), policy.Architecture.X86_64)
        for value in ("armhf", "armv7l", "armv6l", "arm", "", "unknown", "riscv64"):
            with self.subTest(value=value), self.assertRaises(policy.ArchitectureError):
                policy.normalize(value)

    def test_label_namespaces(self):
        for machine, expected in [
            (
                "arm64",
                ("aarch64", "arm64", "aarch64", "aarch64-unknown-linux-gnu", "arm64"),
            ),
            ("amd64", ("x86_64", "amd64", "x86_64", "x86_64-unknown-linux-gnu", "x64")),
        ]:
            self.assertEqual(
                tuple(
                    policy.label(x, machine)
                    for x in ("host", "deb", "rpm", "rust", "vendor")
                ),
                expected,
            )

    def test_adversarial_asset_matrix(self):
        for host, name, allowed in [
            ("arm64", "Tool-x64.AppImage", False),
            ("aarch64", "Tool-amd64.deb", False),
            ("aarch64", "Tool-arm64.deb", True),
            ("x86_64", "Tool-arm64", False),
            ("x86_64", "Tool-amd64.deb", True),
            ("amd64", "Tool-x64.AppImage", True),
            ("arm64", "Tool.deb", False),
            ("x86_64", "Tool", False),
            ("arm64", "Tool-armhf.AppImage", False),
            ("x86_64", "Tool-arm64-x86_64.AppImage", False),
            ("arm64", "Tool-arm64-x86_64.AppImage", False),
        ]:
            with self.subTest(host=host, name=name):
                self.assertEqual(policy.asset_eligible({"name": name}, host), allowed)

    def test_explicit_independent_vs_unknown(self):
        self.assertTrue(
            policy.asset_eligible(
                {
                    "name": "fonts.zip",
                    "content_kind": "data",
                    "architecture_independent": True,
                },
                "arm64",
            )
        )
        self.assertFalse(policy.asset_eligible({"name": "fonts.zip"}, "arm64"))
        self.assertFalse(
            policy.asset_eligible(
                {
                    "name": "tool-x64.zip",
                    "content_kind": "data",
                    "architecture_independent": True,
                },
                "arm64",
            )
        )

    def test_metadata_cannot_override_name(self):
        self.assertFalse(
            policy.asset_eligible(
                {"name": "tool-amd64.deb", "architectures": ["aarch64"]}, "arm64"
            )
        )
        self.assertFalse(
            policy.asset_eligible({"name": "tool.deb", "architectures": []}, "arm64")
        )
        self.assertFalse(
            policy.asset_eligible(
                {"name": "tool.deb", "architectures": "arm64"}, "arm64"
            )
        )
        self.assertTrue(
            policy.asset_eligible(
                {"name": "tool.deb", "architectures": ["arm64"]}, "arm64"
            )
        )

    def test_selector_zero_multiple_and_preference(self):
        arm = {"name": "tool-arm64.deb"}
        x86 = {"name": "tool-amd64.deb"}
        self.assertEqual(policy.select_asset([x86, arm], machine="arm64"), arm)
        self.assertEqual(policy.select_asset([arm, x86], machine="amd64"), x86)
        for assets in (
            [],
            [x86],
            [{"name": "tool.deb"}],
            [arm, {"name": "other-arm64.deb"}],
        ):
            with (
                self.subTest(assets=assets),
                self.assertRaises(policy.ArchitectureError),
            ):
                policy.select_asset(assets, machine="arm64")
        appimage = {"name": "tool-arm64.AppImage"}
        self.assertEqual(
            policy.select_asset(
                [arm, appimage], machine="arm64", formats=((".appimage",), (".deb",))
            ),
            appimage,
        )

    def test_source_intent_not_binary_fallback(self):
        source = {"name": "tool.tar.gz"}
        with self.assertRaises(policy.ArchitectureError):
            policy.select_asset([source], machine="arm64")
        self.assertEqual(
            policy.select_asset([source], machine="arm64", source=True), source
        )

    def test_unknown_host_even_for_data(self):
        for machine in ("armv7l", "unknown"):
            with self.assertRaises(policy.ArchitectureError):
                policy.asset_eligible(
                    {
                        "name": "fonts.zip",
                        "content_kind": "data",
                        "architecture_independent": True,
                    },
                    machine,
                )

    def test_script_policy_not_bypassed_by_devmode(self):
        with patch.dict(os.environ, {"DEV_MODE": "1"}):
            with self.assertRaises(policy.ArchitectureError):
                policy.require_script(
                    "# name: foreign\n# architectures: x86_64\nsudo true", "arm64"
                )
            with self.assertRaises(policy.ArchitectureError):
                policy.require_script("# name: unknown\nsudo true", "amd64")
            with self.assertRaises(policy.ArchitectureError):
                policy.require_script("sudo true", "arm64")

    def test_conflicting_script_headers_fail(self):
        policy.require_script(
            "# architectures: x86_64, aarch64\n# architectures: x86_64\ntrue", "amd64"
        )
        with self.assertRaises(policy.ArchitectureError):
            policy.require_script(
                "# architectures: x86_64\n# architectures: aarch64\ntrue", "x86_64"
            )

    def test_reviewed_script_inventory_complete(self):
        reviewed = policy.route_policy()["scripts"]
        for path in (ROOT / "p3/scripts").rglob("*.sh"):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertIn(digest, reviewed, str(path))
            if "architectures:" not in path.read_text():
                self.assertTrue(
                    policy.script_eligible(path.read_text(), "x86_64"), str(path)
                )

    def test_catalog_declaration_change_is_not_auto_approved(self):
        source = ROOT / "p3/scripts/repos.json"
        entry = json.loads(source.read_text())[0]
        item = dict(entry, _list_source=str(source))
        policy.require_entry(item, "x86_64")
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / "repos.json"
            modified = dict(entry, overrides={"pre": "sudo foreign-installer"})
            altered.write_text(json.dumps([modified]))
            with self.assertRaises(policy.ArchitectureError):
                policy.require_entry(
                    dict(modified, _list_source=str(altered)), "x86_64"
                )

    def test_x86_tuning_routes_refused_on_arm(self):
        for name in ("ubuntuv3", "umip", "dsplitm", "ondemand", "pdefaults"):
            self.assertFalse(
                policy.script_eligible(
                    (ROOT / f"p3/scripts/extra/{name}.sh").read_text(), "arm64"
                )
            )

    def test_real_embedded_release_selector(self):
        source = (ROOT / "p3/libs/packages.bash").read_text()
        source = source[source.index("package_url=$(python3") :]
        source = source.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
        for machine, name, expected in [
            ("arm64", "tool-x64.AppImage", False),
            ("arm64", "tool-amd64.deb", False),
            ("arm64", "tool-arm64.deb", True),
            ("amd64", "tool-amd64.deb", True),
            ("arm64", "tool.deb", False),
        ]:
            release = {
                "tag_name": "v1",
                "assets": [
                    {
                        "name": name,
                        "browser_download_url": "https://example.invalid/" + name,
                    }
                ],
            }
            result = subprocess.CompletedProcess([], 0, json.dumps(release))
            argv = [
                "selector",
                "https://github.com/example/tool",
                "*",
                "deb",
                machine,
                "0",
                "0",
                "0",
                "0",
                "0",
            ]
            output = io.StringIO()
            with (
                self.subTest(machine=machine, name=name),
                patch.object(sys, "argv", argv),
                patch.dict(os.environ, SCRIPT_DIR=str(ROOT / "p3")),
                patch.object(subprocess, "run", return_value=result),
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(output),
            ):
                if expected:
                    exec(compile(source, "embedded-release-selector", "exec"), {})
                    self.assertIn("https://example.invalid/" + name, output.getvalue())
                else:
                    with self.assertRaises(SystemExit):
                        exec(compile(source, "embedded-release-selector", "exec"), {})


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def write(self, name, data):
        path = self.base / name
        path.write_bytes(data)
        return path

    def test_elf_native_and_foreign(self):
        arm = self.write("tool-arm64", elf(183))
        x86 = self.write("tool-x64.AppImage", elf(62))
        files.validate_file(arm, machine="arm64")
        files.validate_file(x86, machine="amd64")
        with self.assertRaises(policy.ArchitectureError):
            files.validate_file(x86, machine="arm64")
        with self.assertRaises(policy.ArchitectureError):
            files.validate_file(arm, machine="amd64")

    def test_unknown_unlabelled_and_explicit_data(self):
        path = self.write("tool", b"unknown executable-looking bytes")
        with self.assertRaises(policy.ArchitectureError):
            files.validate_file(path, machine="arm64")
        files.validate_file(path, machine="arm64", content_kind="data")
        with self.assertRaises(policy.ArchitectureError):
            files.validate_file(
                self.write("data", elf(183)), machine="arm64", content_kind="data"
            )

    def test_mixed_and_nested_archives(self):
        mixed = self.write(
            "bundle.tar.gz", tar_bytes({"bin/arm": elf(183), "lib/x86.so": elf(62)})
        )
        for machine in ("arm64", "amd64"):
            with self.assertRaises(policy.ArchitectureError):
                files.validate_file(mixed, machine=machine)
        nested = self.write("outer.tar", tar_bytes({"nested.tar": mixed.read_bytes()}))
        with self.assertRaises(policy.ArchitectureError):
            files.validate_file(nested, machine="arm64")
        native = self.write(
            "native.tar", tar_bytes({"bin/tool": elf(183), "README": b"hello"})
        )
        files.validate_file(native, machine="arm64")

    def test_zip_mixed_architecture(self):
        path = self.base / "bundle.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("arm.so", elf(183))
            archive.writestr("x86.so", elf(62))
        with self.assertRaises(policy.ArchitectureError):
            files.validate_file(path, machine="arm64")

    def test_source_cannot_hide_native_archives(self):
        embedded = io.BytesIO()
        with zipfile.ZipFile(embedded, "w") as archive:
            archive.writestr("foreign", elf(62))
        for name, value in [
            ("vendor.jar", embedded.getvalue()),
            ("vendor.data", embedded.getvalue()),
            ("library.a", b"!<arch>\n" + b"x" * 100),
        ]:
            with self.subTest(name=name), self.assertRaises(policy.ArchitectureError):
                files.validate_file(
                    self.write("source.tar", tar_bytes({name: value})),
                    machine="arm64",
                    content_kind="source",
                )

    def test_package_metadata_conflict(self):
        path = self.write("tool-arm64.deb", b"deb placeholder")
        for metadata, payload in [
            ("amd64", elf(183)),
            ("arm64", elf(62)),
            ("all", elf(183)),
        ]:
            with (
                self.subTest(metadata=metadata),
                patch.object(
                    files,
                    "_run",
                    side_effect=[metadata.encode(), tar_bytes({"bin/tool": payload})],
                ),
            ):
                with self.assertRaises(policy.ArchitectureError):
                    files.validate_file(path, machine="arm64")
        with patch.object(
            files, "_run", side_effect=[b"arm64", tar_bytes({"bin/tool": elf(183)})]
        ):
            files.validate_file(path, machine="arm64")
        data = self.write("fonts_all.deb", b"data package")
        with patch.object(
            files, "_run", side_effect=[b"all", tar_bytes({"font.ttf": b"font data"})]
        ):
            files.validate_file(data, machine="arm64")

    def test_filename_cannot_override_binary(self):
        with self.assertRaises(policy.ArchitectureError):
            files.validate_file(self.write("tool-arm64", elf(62)), machine="arm64")

    def test_archive_traversal_and_unknown_native(self):
        for members in ({"../escape": b"data"}, {"lib/unknown.so": b"not ELF"}):
            with (
                self.subTest(members=members),
                self.assertRaises(policy.ArchitectureError),
            ):
                files.validate_file(
                    self.write("unsafe.tar", tar_bytes(members)), machine="arm64"
                )

    @unittest.skipUnless(
        shutil.which("dpkg-deb"), "native DEB metadata tool unavailable"
    )
    def test_real_deb_metadata_and_payload(self):
        for metadata, binary_machine, allowed in [
            ("arm64", 183, True),
            ("amd64", 62, False),
            ("arm64", 62, False),
        ]:
            package = self.base / f"package-{metadata}-{binary_machine}"
            (package / "DEBIAN").mkdir(parents=True)
            (package / "usr/bin").mkdir(parents=True)
            (package / "DEBIAN/control").write_text(
                f"Package: architecture-fixture\nVersion: 1\nArchitecture: {metadata}\n"
                "Maintainer: Test <test@example.invalid>\nDescription: offline fixture\n"
            )
            (package / "usr/bin/tool").write_bytes(elf(binary_machine))
            output = self.base / f"fixture-{metadata}-{binary_machine}.deb"
            subprocess.run(
                [
                    "dpkg-deb",
                    "--build",
                    "--root-owner-group",
                    str(package),
                    str(output),
                ],
                check=True,
                capture_output=True,
            )
            if allowed:
                files.validate_file(output, machine="arm64")
            else:
                with self.assertRaises(policy.ArchitectureError):
                    files.validate_file(output, machine="arm64")

    def test_missing_package_metadata_fails(self):
        path = self.write("unknown.deb", b"placeholder")
        with patch.object(files, "_run", return_value=b""):
            with self.assertRaises(policy.ArchitectureError):
                files.validate_file(path, machine="arm64")


class FlatpakTests(unittest.TestCase):
    def test_native_ref_and_foreign_rejection(self):
        with patch.object(policy.platform, "machine", return_value="aarch64"):
            with patch.object(
                flatpak, "_query", return_value="app/org.example.App/aarch64/stable"
            ):
                self.assertEqual(
                    flatpak.resolve_refs(["org.example.App"], "flathub", "--user"),
                    ["org.example.App/aarch64/stable"],
                )
            with patch.object(
                flatpak, "_query", return_value="app/org.example.App/x86_64/stable"
            ):
                with self.assertRaises(policy.ArchitectureError):
                    flatpak.resolve_refs(["org.example.App"], "flathub", "--user")

    def test_extension_uses_runtime_metadata_branch(self):
        metadata = "[Runtime]\nname=org.gnome.Platform\n[Extension org.freedesktop.Platform.VulkanLayer]\nversions=25.08;\n"
        with (
            patch.object(policy.platform, "machine", return_value="arm64"),
            patch.object(
                flatpak,
                "_query",
                side_effect=[
                    "org.gnome.Platform/aarch64/50",
                    metadata,
                    "flathub",
                    "runtime/org.freedesktop.Platform.VulkanLayer.MangoHud/aarch64/25.08",
                ],
            ) as query,
        ):
            refs = flatpak.extension_refs(
                "org.example.App", "org.freedesktop.Platform.VulkanLayer.MangoHud"
            )
            self.assertEqual(
                refs, ["org.freedesktop.Platform.VulkanLayer.MangoHud/aarch64/25.08"]
            )
            self.assertIn(
                "org.freedesktop.Platform.VulkanLayer.MangoHud/aarch64/25.08",
                query.call_args.args,
            )

    def test_unavailable_extension_and_missing_branch_fail(self):
        with (
            patch.object(policy.platform, "machine", return_value="arm64"),
            patch.object(
                flatpak,
                "_query",
                side_effect=[
                    "org.gnome.Platform/aarch64/50",
                    "[Extension org.example.Extension]\n",
                ],
            ),
        ):
            with self.assertRaises(policy.ArchitectureError):
                flatpak.extension_refs("org.example.App", "org.example.Extension")
        with patch.object(
            flatpak, "_query", side_effect=policy.ArchitectureError("unavailable")
        ):
            with self.assertRaises(policy.ArchitectureError):
                flatpak.extension_refs("org.example.App", "org.example.Extension")

    def test_scoped_rollback_never_removes_other_installation(self):
        from app.revert_helper import _reverse_flatpak_removal

        ref = "org.freedesktop.Platform.VulkanLayer.MangoHud/aarch64/25.08"
        commands = _reverse_flatpak_removal(["--system", ref])
        self.assertEqual(len(commands), 1)
        self.assertIn("--system", commands[0])
        self.assertNotIn("--user", commands[0])
        self.assertIn(ref, commands[0])
        self.assertIn("sudo_rq", commands[0])
        self.assertEqual(
            _reverse_flatpak_removal(["--user", "--all"]),
            ["false # Invalid Flatpak rollback operand"],
        )


class MutationOrderTests(unittest.TestCase):
    def test_rejected_payload_never_reaches_mutations(self):
        # Execute the real shell helpers with recording stubs. The foreign ELF
        # must be rejected before authentication, filesystem replacement or install.
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            foreign = base / "foreign"
            foreign.write_bytes(
                elf(62 if policy.host() == policy.Architecture.AARCH64 else 183)
            )
            for command in (
                "pkg_binary",
                "pkg_appimage",
                "pkg_fromfile",
                "pkg_tarball",
                "pkg_snap_file",
            ):
                marker = base / "mutated"
                code = f"""
source {str(ROOT / "p3/libs/packages.bash")!r}
die() {{ echo "$*" >&2; exit 37; }}
fatal() {{ die "$@"; }}
_architecture_check() {{ python3 "$SCRIPT_DIR/app/architecture_cli.py" "$@" || die refused; }}
askpass() {{ touch {str(marker)!r}; }}
prep_create() {{ touch {str(marker)!r}; }}
prep_dir() {{ touch {str(marker)!r}; }}
pkg_appimage_rm() {{ touch {str(marker)!r}; }}
{command} {str(foreign)!r}
"""
                env = dict(os.environ, SCRIPT_DIR=str(ROOT / "p3"), HOME=directory)
                proc = subprocess.run(
                    ["/bin/bash", "-c", code], env=env, capture_output=True, text=True
                )
                self.assertNotEqual(
                    proc.returncode, 0, (command, proc.stdout, proc.stderr)
                )
                self.assertFalse(marker.exists(), (command, proc.stdout, proc.stderr))

    def test_standalone_bootstrap_rejects_writable_local_helpers(self):
        code = (
            (ROOT / "install.sh")
            .read_text()
            .split("<<'PYLOCAL'\n", 1)[1]
            .split("\nPYLOCAL", 1)[0]
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "p3/app").mkdir(parents=True)
            (base / "p3").chmod(0o755)
            (base / "p3/app").chmod(0o755)
            for name in (
                "__init__.py",
                "architecture.py",
                "architecture_cli.py",
                "architecture_files.py",
                "architecture_flatpak.py",
            ):
                (base / "p3/app" / name).touch()
                (base / "p3/app" / name).chmod(0o644)
            with patch.object(sys, "argv", ["preflight", str(base)]):
                exec(compile(code, "local-bootstrap-trust", "exec"), {})
                (base / "p3/app/architecture.py").chmod(0o666)
                with self.assertRaises(SystemExit):
                    exec(compile(code, "local-bootstrap-trust", "exec"), {})

    def test_script_preamble_rejects_before_session_creation(self):
        from app import library_loader

        with (
            patch.object(policy.platform, "machine", return_value="arm64"),
            patch.object(library_loader, "_execution_session_dir") as session,
        ):
            with self.assertRaises(policy.ArchitectureError):
                library_loader.script_preamble(
                    "# name: foreign\n# architectures: x86_64\nsudo true",
                    str(ROOT / "p3"),
                )
            session.assert_not_called()

    def test_no_fixed_extension_refs_in_active_routes(self):
        for name in [
            "p3/scripts/repos.json",
            "p3/scripts/game/gscope.sh",
            "p3/scripts/lists/obs/obs-post.sh",
            "p3/scripts/lists/volt/volt-post.sh",
        ]:
            self.assertNotRegex(
                (ROOT / name).read_text(),
                r'org\.freedesktop\.Platform\.[^"\s]*/x86_64/',
            )

    def test_post_hooks_are_rejected_before_any_phase(self):
        from app import library_loader

        with (
            patch.object(policy.platform, "machine", return_value="arm64"),
            patch.object(library_loader, "_execution_session_dir") as session,
        ):
            with self.assertRaises(policy.ArchitectureError):
                library_loader.script_environment(
                    {
                        "name": "OBS",
                        "appstream_overrides": {"post": {"script": "obs/obs-post.sh"}},
                    },
                    {"SCRIPT_DIR": str(ROOT / "p3")},
                )
            session.assert_not_called()
        with self.assertRaises(policy.ArchitectureError):
            policy.resolve_hook_path(str(ROOT / "p3"), "../../escape")

    def test_foreign_transitive_apt_dependency_is_refused(self):
        from app.architecture_cli import apt_plan

        plan = "Inst dependency (1.0 Ubuntu:stable [amd64])\n"
        with (
            patch.object(policy.platform, "machine", return_value="arm64"),
            patch.object(
                subprocess, "run", return_value=subprocess.CompletedProcess([], 0, plan)
            ),
        ):
            with self.assertRaises(policy.ArchitectureError):
                apt_plan(["native-arm-package"])

    def test_snap_candidates_require_native_daemon_and_stable_channel(self):
        from app.architecture_cli import snap_packages

        candidate = {
            "name": "example",
            "channels": {"latest/stable": {"revision": "42", "version": "1.0"}},
        }
        with patch("app.architecture.platform.machine", return_value="aarch64"):
            with patch(
                "app.snap_catalog._request",
                side_effect=[{"architecture": "arm64"}, [candidate]],
            ) as query:
                snap_packages(["example"])
                self.assertEqual(
                    query.call_args_list[-1].args, ("/v2/find", {"name": "example"})
                )
            for system, values in [
                ({"architecture": "amd64"}, [candidate]),
                ({}, [candidate]),
                ({"architecture": "arm64"}, []),
                ({"architecture": "arm64"}, [candidate, candidate]),
                ({"architecture": "arm64"}, [{"name": "example", "channels": {}}]),
                ({"architecture": "arm64"}, [dict(candidate, architecture="amd64")]),
            ]:
                with patch("app.snap_catalog._request", side_effect=[system, values]):
                    with self.assertRaises(policy.ArchitectureError):
                        snap_packages(["example"])

    def test_package_availability_preflight_is_read_only(self):
        from app.architecture_cli import native_packages

        with patch.object(policy.platform, "machine", return_value="arm64"):
            with patch.object(
                subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    [], 0, "Architecture: amd64\n"
                ),
            ) as run:
                with self.assertRaises(policy.ArchitectureError):
                    native_packages(["tool"], "apt")
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.args[0][0], "apt-cache")
            with patch.object(
                subprocess,
                "run",
                side_effect=[
                    subprocess.CompletedProcess([], 0, "Architecture: arm64\n"),
                    subprocess.CompletedProcess([], 0),
                ],
            ) as run:
                native_packages(["tool"], "apt")
                self.assertIn("--simulate", run.call_args.args[0])
                self.assertNotIn("sudo", run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
