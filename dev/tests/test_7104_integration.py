"""7.10.4 contracts with fake managers, locks, HTTP, GTK and RAM fixtures.

No system package manager, authentication backend, installer body, service or
network endpoint is invoked. These checks are not package lifecycle evidence.
"""

from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, mock_open, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p3"))
from app import architecture, package_guard  # noqa: E402
from dev.tests.test_mcp_skill import method  # noqa: E402
from dev.tests import test_u1_reporting as reporting_fixtures  # noqa: E402

FAMILIES = ("apt", "dnf", "pacman", "zypper")
REFUSALS = {
    "apt": "Could not get lock /var/lib/dpkg/lock-frontend",
    "dnf": "Failed to obtain the transaction lock",
    "pacman": "error: failed to init transaction (unable to lock database)",
    "zypper": "System management is locked by another application",
}
LOCKS = {
    "apt": "/var/lib/dpkg/lock-frontend",
    "dnf": "/run/dnf.pid",
    "pacman": "/var/lib/pacman/db.lck",
    "zypper": "/run/zypp.pid",
}


class ShellFixtures(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.temp = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.events = self.temp / "events"
        self.library = self.temp / "packages.bash"
        # Only the literal Pacman lock location is redirected; never create or
        # remove a system lock, and execute the actual production functions.
        self.lock = self.temp / "pacman-db.lck"
        self.library.write_text(
            (ROOT / "p3/libs/packages.bash")
            .read_text()
            .replace("/var/lib/pacman/db.lck", str(self.lock))
            .replace(r"/var/lib/pacman/db\.lck", str(self.lock))
        )
        self.env = {
            **os.environ,
            "HOME": str(self.temp),
            "SCRIPT_DIR": str(self.temp),
            "TMPDIR": str(self.temp),
            "FIXTURE": str(self.temp),
            "EVENTS": str(self.events),
            "PATH": "/usr/bin:/bin",
        }
        # Refuse accidental raw mutations even if a future helper bypasses a
        # shell mock. The only executables used are ordinary fixture utilities.
        blocked = self.temp / "bin"
        blocked.mkdir()
        for name in (
            "sudo",
            "apt",
            "apt-get",
            "dpkg",
            "dnf",
            "dnf5",
            "yum",
            "pacman",
            "zypper",
            "rpm",
            "rpm-ostree",
            "eopkg",
            "curl",
            "wget",
            "pkexec",
        ):
            path = blocked / name
            path.write_text(
                "#!/bin/sh\necho 'forbidden external operation' >&2\nexit 97\n"
            )
            path.chmod(0o700)
        (blocked / "python3").symlink_to(sys.executable)
        self.env["PATH"] = str(blocked) + ":/usr/bin:/bin"

    def preamble(self):
        return f"""
set -eo pipefail
# An ordinary variable supplies a deterministic virtual clock in these tests.
unset SECONDS
SECONDS=0
source {shlex.quote(str(self.library))}
record() {{ printf '%s\\n' "$*" >> "$EVENTS"; }}
pgrep() {{ [[ -f "$FIXTURE/process" ]] && [[ "$(cat "$FIXTURE/process")" == "$2" ]]; }}
_proc_fd_links() {{ if [[ -f "$FIXTURE/fds" ]]; then cat "$FIXTURE/fds"; fi; }}
sleep() {{
    record "sleep:$1"
    SECONDS=$((SECONDS + $1))
    if [[ -f "$FIXTURE/release" ]]; then
        rm -f "$FIXTURE/process" "$FIXTURE/fds" "$FIXTURE/release"
    fi
}}
info() {{ record "info:$*"; }}
die() {{ printf '%s\\n' "$*" >&2; exit 1; }}
APT_BUSY_WAIT_TIMEOUT=4
DNF_BUSY_WAIT_TIMEOUT=4
PACMAN_BUSY_WAIT_TIMEOUT=4
ZYPPER_BUSY_WAIT_TIMEOUT=4
fake() {{ record "attempt:$*"; }}
"""

    def shell(self, code, *, env=None):
        return subprocess.run(
            ["/bin/bash", "-c", self.preamble() + code],
            env=self.env if env is None else env,
            text=True,
            capture_output=True,
            timeout=10,
        )

    def event_lines(self):
        return self.events.read_text().splitlines() if self.events.exists() else []

    def attempts(self):
        return [x for x in self.event_lines() if x.startswith("attempt:")]

    def fresh(self):
        for path in self.temp.iterdir():
            if path.is_file() and path != self.library:
                path.unlink()

    def no_temporary_logs(self):
        self.assertEqual(list(self.temp.glob("linuxtoys-package.*")), [])


class TransactionTests(ShellFixtures):
    def test_invalid_family_or_timeout_fails_before_any_command(self):
        for args in ("unknown 4", "apt invalid"):
            with self.subTest(args=args):
                result = self.shell(f"_pkg_transaction {args} fake")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(self.attempts(), [])
                self.no_temporary_logs()

    def test_all_families_succeed_and_preserve_quoted_arguments(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                self.fresh()
                result = self.shell(f'{family}_transaction fake "package with spaces"')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.attempts(), ["attempt:package with spaces"])
                self.no_temporary_logs()

    def test_live_process_or_unknown_fd_holder_is_waited_out_before_transaction(self):
        for family in FAMILIES:
            for evidence in ("process", "fds"):
                with self.subTest(family=family, evidence=evidence):
                    self.fresh()
                    (self.temp / evidence).write_text(
                        family
                        if evidence == "process"
                        else (str(self.lock) if family == "pacman" else LOCKS[family])
                    )
                    (self.temp / "release").touch()
                    result = self.shell(f"{family}_transaction fake")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(self.event_lines(), ["sleep:3", "attempt:"])

    def test_persistent_holder_times_out_without_running_or_removing_any_lock(self):
        for family in FAMILIES:
            for evidence in ("process", "fds"):
                with self.subTest(family=family, evidence=evidence):
                    self.fresh()
                    path = self.temp / evidence
                    path.write_text(
                        family
                        if evidence == "process"
                        else (str(self.lock) if family == "pacman" else LOCKS[family])
                    )
                    before = path.read_bytes(), path.stat().st_ino
                    result = self.shell(f"{family}_transaction fake")
                    self.assertEqual(result.returncode, 124, result.stderr)
                    self.assertEqual(self.attempts(), [])
                    self.assertEqual((path.read_bytes(), path.stat().st_ino), before)
                    self.assertEqual(self.event_lines(), ["sleep:3", "sleep:1"])
                    self.no_temporary_logs()

    def test_stale_pacman_lock_is_never_unlinked_even_without_a_visible_pid(self):
        self.lock.write_text("crash leftover or an invisible live owner")
        before = self.lock.read_bytes(), self.lock.stat().st_ino
        result = self.shell("pacman_transaction fake")
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertEqual(self.attempts(), [])
        self.assertEqual((self.lock.read_bytes(), self.lock.stat().st_ino), before)
        result = self.shell("pacman_lock_guard")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not removed", result.stderr)
        self.assertEqual((self.lock.read_bytes(), self.lock.stat().st_ino), before)

    def test_stale_fcntl_or_pid_marker_is_not_an_owned_lock(self):
        for family in ("apt", "dnf", "zypper"):
            with self.subTest(family=family):
                self.fresh()
                marker = self.temp / "stale.pid"
                marker.write_text("2147483647")
                result = self.shell(f"{family}_transaction fake")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(marker.read_text(), "2147483647")
                self.assertEqual(len(self.attempts()), 1)

    def test_diagnosed_collision_retries_after_holder_releases_or_pid_vanishes(self):
        for family in FAMILIES:
            for holder in (True, False):
                with self.subTest(family=family, holder=holder):
                    self.fresh()
                    start_holder = (
                        f'printf %s {family} > "$FIXTURE/process"; '
                        'touch "$FIXTURE/release"'
                        if holder
                        else ":"
                    )
                    result = self.shell(
                        f"""
fake() {{
    record attempt:
    if [[ ! -f "$FIXTURE/once" ]]; then
        touch "$FIXTURE/once"
        {start_holder}
        printf '%s\\n' {shlex.quote(REFUSALS[family])} >&2
        return 42
    fi
}}
{family}_transaction fake
"""
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(len(self.attempts()), 2)
                    self.assertIn(REFUSALS[family], result.stdout)
                    self.no_temporary_logs()

    def test_failure_with_a_new_unrelated_manager_is_never_replayed(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                self.fresh()
                result = self.shell(
                    f"""
fake() {{
    record attempt:
    printf %s {family} > "$FIXTURE/process"
    echo 'dependency failure'
    return 42
}}
{family}_transaction fake
"""
                )
                self.assertEqual(result.returncode, 42, result.stderr)
                self.assertEqual(len(self.attempts()), 1)

    def test_repeated_lock_refusals_exhaust_exactly_two_retries(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                self.fresh()
                result = self.shell(
                    f"""
fake() {{ record attempt:; echo {shlex.quote(REFUSALS[family])}; return 42; }}
{family}_transaction fake
"""
                )
                self.assertEqual(result.returncode, 42)
                self.assertEqual(len(self.attempts()), 3)
                self.no_temporary_logs()

    def test_one_deadline_covers_entry_and_collision_waits(self):
        (self.temp / "process").write_text("apt")
        (self.temp / "release").touch()
        result = self.shell(
            """
fake() {
    record attempt:
    echo apt > "$FIXTURE/process"
    echo 'Could not get lock'
    return 42
}
apt_transaction fake
"""
        )
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertEqual(self.event_lines(), ["sleep:3", "attempt:", "sleep:1"])

    def test_signals_and_authentication_failures_are_never_retried(self):
        for family in FAMILIES:
            for status in (100, 130, 137, 143):
                with self.subTest(family=family, status=status):
                    self.fresh()
                    diagnostic = "cancelled" if status == 100 else REFUSALS[family]
                    result = self.shell(
                        f"""
fake() {{ record attempt:; echo {shlex.quote(diagnostic)}; return {status}; }}
{family}_transaction fake
"""
                    )
                    self.assertEqual(result.returncode, status)
                    self.assertEqual(len(self.attempts()), 1)
                    self.no_temporary_logs()

    def test_wait_interruption_and_stream_failure_propagate(self):
        (self.temp / "process").write_text("apt")
        result = self.shell("sleep() { return 130; }; apt_transaction fake")
        self.assertEqual(result.returncode, 130)
        self.assertEqual(self.attempts(), [])
        self.fresh()
        result = self.shell('tee() { cat > "$1"; return 77; }; apt_transaction fake')
        self.assertEqual(result.returncode, 77)
        self.assertEqual(len(self.attempts()), 1)
        self.no_temporary_logs()

    def test_sigterm_during_command_keeps_signal_status_and_cleans_stage(self):
        result = self.shell(
            "fake() { record attempt:; /bin/sh -c 'kill -TERM $$'; }; "
            "apt_transaction fake"
        )
        self.assertEqual(result.returncode, 143, result.stderr)
        self.assertEqual(len(self.attempts()), 1)
        self.no_temporary_logs()

    def test_dnf_and_yum_share_detection_and_transaction_guard(self):
        for name in ("dnf", "dnf5", "yum"):
            with self.subTest(name=name):
                self.fresh()
                (self.temp / "process").write_text(name)
                (self.temp / "release").touch()
                result = self.shell("dnf_transaction fake")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.event_lines(), ["sleep:3", "attempt:"])

    def test_idle_resident_daemons_do_not_block(self):
        for family, name in (
            ("apt", "packagekitd"),
            ("dnf", "dnf-automatic"),
            ("pacman", "pamac-daemon"),
            ("zypper", "zypp-refresh"),
        ):
            with self.subTest(family=family):
                self.fresh()
                (self.temp / "process").write_text(name)
                result = self.shell(f"{family}_transaction fake")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.event_lines(), ["attempt:"])

    def test_concurrent_mock_transactions_are_serialized_by_native_mock_lock(self):
        # The mock manager owns an atomic mkdir lock, just as a real manager
        # must own its native lock. Use the POSIX calls directly so EEXIST
        # refuses the losing contender regardless of mkdir tool behavior.
        # LinuxToys never steals this fixture lock.
        code = """
_apt_busy_manager() { return 1; }
_apt_lock_actively_held() { [[ -d "$FIXTURE/manager-lock" ]]; }
sleep() { /bin/sleep 0.02; SECONDS=$((SECONDS + 1)); }
APT_BUSY_WAIT_TIMEOUT=30
fake() {
    if ! python3 -c 'import os,sys; os.mkdir(sys.argv[1])' "$FIXTURE/manager-lock" 2>/dev/null; then
        echo 'Could not get lock'; return 42
    fi
    record enter
    /bin/sleep 0.1
    record leave
    python3 -c 'import os,sys; os.rmdir(sys.argv[1])' "$FIXTURE/manager-lock"
}
apt_transaction fake
"""
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.shell(code), range(2)))
        self.assertEqual([r.returncode for r in results], [0, 0], results)
        self.assertEqual(self.event_lines(), ["enter", "leave", "enter", "leave"])
        self.assertFalse((self.temp / "manager-lock").exists())
        self.no_temporary_logs()


class InstallerTests(ShellFixtures):
    def setUp(self):
        super().setUp()
        self.installer = (ROOT / "install.sh").read_text().split("if [ -t 0 ]", 1)[0]

    def install(
        self, family, *, failure="", extra="", verify_status=0, noninteractive=True
    ):
        # Source production definitions only, with downloads and payload
        # verification replaced by isolated, recorded fixture operations.
        code = (
            self.installer
            + f"""
_package_library={shlex.quote(str(self.library))}
_architecture_work="$FIXTURE"
_deb=fixture.deb; _deb_name=fixture.deb
_rpm=fixture.rpm; _rpm_name=fixture.rpm
_pkg=fixture.pkg; _pkg_name=fixture.pkg
ID=fixture; ID_LIKE=fixture
LINUXTOYS_NONINTERACTIVE={int(noninteractive)}
curl() {{ touch "$FIXTURE/fixture.deb" "$FIXTURE/fixture.rpm" "$FIXTURE/fixture.pkg"; }}
architecture_verify() {{
    record "verify:$*"
    (( {verify_status} == 0 )) || exit {verify_status}
}}
sudo() {{
    record "sudo:$*"
    [[ "$1" != -n ]] || shift
    "$@"
}}
apt() {{ record "apt:$*"; {failure or ':'}; }}
dnf() {{ record "dnf:$*"; {failure or ':'}; }}
yum() {{ record "yum:$*"; {failure or ':'}; }}
zypper() {{ record "zypper:$*"; {failure or ':'}; }}
pacman() {{
    if [[ "$1" == -Qi ]]; then return 1; fi
    record "pacman:$*"; {failure or ':'}
}}
{extra}
{family}
"""
        )
        return self.shell(code)

    def test_all_installer_branches_use_shared_guards_after_payload_verification(self):
        for branch, manager in (
            ("osdeb", "apt"),
            ("osrpm", "dnf"),
            ("osarch", "pacman"),
            ("ossuse", "zypper"),
        ):
            with self.subTest(branch=branch):
                self.fresh()
                result = self.install(branch)
                self.assertEqual(result.returncode, 0, result.stderr)
                lines = self.event_lines()
                self.assertTrue(lines[0].startswith("verify:"), lines)
                self.assertTrue(any(x.startswith(manager + ":") for x in lines), lines)
                self.assertTrue(
                    all(
                        x.startswith("sudo:-n ") for x in lines if x.startswith("sudo:")
                    )
                )
                self.no_temporary_logs()

    def test_payload_refusal_precedes_privileges_and_every_manager(self):
        for branch in ("osdeb", "osrpm", "osarch", "ossuse"):
            with self.subTest(branch=branch):
                self.fresh()
                result = self.install(branch, verify_status=65)
                self.assertEqual(result.returncode, 65)
                self.assertEqual(len(self.event_lines()), 1)
                self.assertTrue(self.event_lines()[0].startswith("verify:"))

    def test_installer_failure_status_is_preserved_without_success_message(self):
        for branch in ("osdeb", "osrpm", "osarch", "ossuse"):
            with self.subTest(branch=branch):
                self.fresh()
                result = self.install(branch, failure="return 42")
                self.assertEqual(result.returncode, 42, result.stderr)
                self.assertNotIn("installed or updated", result.stdout)
                self.no_temporary_logs()

    def test_dependency_and_repository_setup_failures_stop_the_install(self):
        for branch, extra in (
            (
                "ossuse",
                'zypper() { record "zypper:$*"; '
                '[[ "$*" == *fixture.rpm* ]] || return 43; }',
            ),
            (
                "osarch",
                'ID=cachyos; pacman() { [[ "$1" != -Qi ]] || return 1; '
                'record "pacman:$*"; return 43; }',
            ),
            (
                "osrpm",
                "ID=rhel; rpm() { echo 9; }; arch() { echo aarch64; }; "
                "subscription-manager() { record repo-setup; return 43; }",
            ),
        ):
            with self.subTest(branch=branch):
                self.fresh()
                result = self.install(branch, extra=extra)
                self.assertEqual(result.returncode, 43, result.stderr)
                self.assertNotIn("installed or updated", result.stdout)

    def test_yum_fallback_is_guarded_and_noninteractive(self):
        result = self.install(
            "osrpm",
            extra=(
                'unset -f dnf; command() { [[ "$*" != "-v dnf" ]] || return 1; '
                'builtin command "$@"; }'
            ),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            any(x.startswith("yum:install -y ") for x in self.event_lines())
        )

    def test_noninteractive_sudo_failure_does_not_prompt_or_report_success(self):
        result = self.install("osdeb", extra='sudo() { record "sudo:$*"; return 100; }')
        self.assertEqual(result.returncode, 100)
        self.assertEqual(
            len(
                [
                    x
                    for x in self.event_lines()
                    if x.startswith("sudo:") and x != "sudo:-n true"
                ]
            ),
            1,
        )
        self.assertTrue(self.event_lines()[-1].startswith("sudo:-n apt update"))

    def test_terminal_and_tui_update_download_failures_do_not_report_success(self):
        writer = mock_open()
        parent = SimpleNamespace(open_term_view=Mock())
        namespace = {
            "open": writer,
            "os": SimpleNamespace(remove=Mock(), chmod=Mock()),
            "GLib": SimpleNamespace(timeout_add=Mock()),
            "DialogError": Mock(side_effect=AssertionError("unexpected dialog")),
        }
        run = method(
            "updater/update_dialog.py", "UpdateDialog", "_run_process", namespace
        )
        run(
            SimpleNamespace(destroy=Mock(), parent=parent, _restart_after_update=Mock())
        )
        queued = parent.open_term_view.call_args.args[0][0]
        self.assertTrue(queued["self_update"])
        script = writer().write.call_args.args[0]
        marker = self.temp / "complete"
        script = script.replace("/tmp/.self_update_lt_complete", str(marker))
        result = self.shell("curl() { return 22; };\n" + script)
        self.assertEqual(result.returncode, 22)
        self.assertFalse(marker.exists())
        terminal = SimpleNamespace(run_script=Mock())
        decide = method(
            "tui/runner_helper.py",
            "UpdateRunnerMixin",
            "_on_update_decision",
            {"Terminal": object},
        )
        state = SimpleNamespace(
            _show_terminal=Mock(), query_one=Mock(return_value=terminal)
        )
        decide(state, True)
        argv = terminal.run_script.call_args.args[0]
        result = self.shell(
            "curl() { return 22; }; export -f curl; " + shlex.join(argv)
        )
        self.assertEqual(result.returncode, 22)

    def test_installer_reload_keeps_localized_wait_messages(self):
        lang = self.temp / "libs/lang"
        lang.mkdir(parents=True)
        (lang / "en.json").write_text("{}")
        (self.temp / "process").write_text("apt")
        (self.temp / "release").touch()
        result = self.shell(
            self.installer
            + f"""
_package_library={shlex.quote(str(self.library))}
_PKG_GUARD_L10N_DONE=1
jq() {{ printf '%s\\n' 'PKG_GUARD_WAIT=translated-wait'; }}
_lt_installer_transaction apt true
"""
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("translated-wait", result.stderr)

    def test_missing_guard_api_is_not_satisfied_by_an_inherited_marker(self):
        old = self.temp / "old-library"
        old.write_text("apt_transaction() { echo unsafe; return 0; }\n")
        result = self.install(
            "osdeb",
            extra=(
                f"_package_library={shlex.quote(str(old))}; "
                "LINUXTOYS_PACKAGE_GUARD_API=2"
            ),
        )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("unsafe", result.stdout)
        self.assertFalse(any(x.startswith("sudo:") for x in self.event_lines()))

    def test_sourced_library_never_replaces_installer_success_or_parent_traps(self):
        result = self.shell(
            self.installer
            + f"""
_package_library={shlex.quote(str(self.library))}
trap 'record parent-cleanup' EXIT
_lt_installer_transaction apt true
info success
record unreachable
"""
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("success", result.stdout)
        self.assertEqual(self.event_lines(), ["parent-cleanup"])

    def test_failed_installer_dispatch_does_not_fall_through_to_id_like(self):
        # Only /etc/os-release is redirected to a fixture. Release selection
        # executes the real central CLI against an explicit native asset.
        os_release = self.temp / "os-release"
        os_release.write_text("ID=debian\nID_LIKE=ubuntu\n")
        source = self.installer.replace("/etc/os-release", str(os_release))
        asset_arch = architecture.label("deb")
        release = json.dumps(
            {
                "tag_name": "7.10.4",
                "assets": [
                    {
                        "name": "sha256sums.txt",
                        "browser_download_url": "https://fixture.invalid/sums",
                    },
                    {
                        "name": f"linuxtoys_{asset_arch}.deb",
                        "browser_download_url": (
                            f"https://fixture.invalid/linuxtoys_{asset_arch}.deb"
                        ),
                    },
                ],
            }
        )
        result = self.shell(
            source
            + f"""
curl() {{ printf '%s' {shlex.quote(release)}; }}
architecture_prepare() {{
    _architecture_work="$FIXTURE"
    _architecture_cli={shlex.quote(str(ROOT / 'p3/app/architecture_cli.py'))}
    printf '%s' "$_api" > "$FIXTURE/release.json"
}}
requires_appimage() {{ return 1; }}
osdeb() {{ record dispatch; return 42; }}
installer
"""
        )
        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertEqual(self.event_lines(), ["dispatch"])


class DispatchTests(unittest.TestCase):
    def test_self_update_is_native_without_reading_remote_script(self):
        with patch.object(package_guard, "script_enters_native_transaction") as scan:
            self.assertTrue(
                package_guard.dispatch_enters_native_transaction(
                    {"self_update": True}, "missing", "missing"
                )
            )
            scan.assert_not_called()
            scan.return_value = False
            self.assertFalse(
                package_guard.dispatch_enters_native_transaction({}, "ordinary", "root")
            )
            scan.assert_called_once_with("ordinary", "root")

    def test_yum_mutation_is_gated_but_queries_and_container_commands_are_not(self):
        for text, expected in (
            ("yum install example", True),
            ("yum remove example", True),
            ("yum list installed", False),
            ("yum --assumeno --dry-run install example", False),
            ("distrobox enter box -- yum install example", False),
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    package_guard.job_enters_native_transaction(text), expected
                )
        with (
            patch.object(
                package_guard, "_native_manager_family", return_value="fedora"
            ),
            patch.object(package_guard, "_running_comm_names", return_value={"yum"}),
        ):
            self.assertEqual(package_guard.busy_native_manager_process(), "yum")

    def terminal(self, info, busy):
        state = SimpleNamespace(
            parent=SimpleNamespace(),
            script_queue=[info],
            _flatpak_apps_present_before_run=True,
            _release_exclusive_hold_if_done=Mock(),
            vbox_main=SimpleNamespace(_update_header_labels=Mock()),
            _begin_busy_wait=Mock(),
            executed_scripts=[],
        )
        reached = RuntimeError("reached dispatch")
        namespace = {
            "dev_mode": SimpleNamespace(is_dev_mode_enabled=lambda: False),
            "package_guard": package_guard,
            "os": os,
            "antenna": SimpleNamespace(add_script_to_history=Mock(side_effect=reached)),
        }
        run = method("term_runner.py", "TerminalRunner", "_run_next_script", namespace)
        with patch.object(
            package_guard, "busy_native_manager_process", return_value=busy
        ):
            if busy:
                run(state)
            else:
                with self.assertRaisesRegex(RuntimeError, "reached dispatch"):
                    run(state)
        return state

    def test_actual_terminal_dispatch_waits_before_history_or_spawn_for_self_update(
        self,
    ):
        info = {"name": "Update LinuxToys", "self_update": True, "path": "/missing"}
        state = self.terminal(info, "apt")
        state._begin_busy_wait.assert_called_once_with(info)
        self.assertEqual(state.executed_scripts, [])
        self.assertEqual(state.script_queue, [])
        state = self.terminal(info, None)
        state._begin_busy_wait.assert_not_called()
        self.assertEqual(state.executed_scripts, [info])

    def test_queue_resume_timeout_and_destroy_do_not_spawn_or_duplicate_entries(self):
        finish = method("term_runner.py", "TerminalRunner", "_busy_wait_finished", {})
        info = {"self_update": True, "name": "update"}
        for idle, destroyed in ((True, False), (False, False), (True, True)):
            with self.subTest(idle=idle, destroyed=destroyed):
                state = SimpleNamespace(
                    _busy_wait_script=info,
                    _busy_wait_started=True,
                    _destroyed=destroyed,
                    script_queue=[],
                    _set_runner_locked=Mock(),
                    _run_next_script=Mock(),
                    _skip_script_for_slow_manager=Mock(),
                )
                self.assertFalse(finish(state, idle))
                self.assertFalse(state._busy_wait_started)
                self.assertIsNone(state._busy_wait_script)
                self.assertEqual(
                    state.script_queue, [info] if idle and not destroyed else []
                )
                self.assertEqual(
                    state._run_next_script.call_count, int(idle and not destroyed)
                )
                self.assertEqual(
                    state._skip_script_for_slow_manager.call_count,
                    int(not idle and not destroyed),
                )

    def test_release_age_gate_allows_only_self_update_when_installation_is_blocked(
        self,
    ):
        # Extract the actual function so GTK and its constructor never load.
        path = ROOT / "p3/app/updater/update_dialog.py"
        node = next(
            n
            for n in ast.parse(path.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == "scripts_blocked_by_version"
        )
        gate = SimpleNamespace(check=Mock(return_value={"blocked": True}))
        dialogs = SimpleNamespace(run_version_gate_dialog=Mock(return_value=False))
        namespace = {"__package__": "_7104_gate.updater"}
        fake_updater = SimpleNamespace(version_gate=gate)
        with patch.dict(
            sys.modules,
            {
                "_7104_gate.updater": fake_updater,
                "_7104_gate.updater.version_gate": gate,
                "_7104_gate.gtk_dialogs": dialogs,
            },
        ):
            exec(
                compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"),
                namespace,
            )
            check = namespace["scripts_blocked_by_version"]
            self.assertFalse(
                check(None, infos=[{"self_update": True, "is_script": True}])
            )
            gate.check.assert_not_called()
            self.assertFalse(check(None, infos=[{"appstream_source": "native"}]))
            self.assertTrue(
                check(None, infos=[{"self_update": True}, {"is_script": True}])
            )
            gate.check.assert_called_once()

    def test_native_preflight_timeout_uses_a_bounded_monotonic_budget(self):
        with (
            patch.object(
                package_guard, "busy_native_manager_process", return_value="yum"
            ),
            patch.object(package_guard.time, "monotonic", side_effect=[0, 0, 0, 2]),
            patch.object(package_guard.time, "sleep") as sleep,
        ):
            self.assertEqual(package_guard.wait_for_idle(timeout=2), (False, "yum"))
            sleep.assert_called_once_with(1.0)


class LockOwnershipTests(unittest.TestCase):
    def test_stale_file_and_vanished_pid_do_not_count_as_live_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "lock"
            lock.write_text("stale pid 2147483647")
            before = lock.read_bytes(), lock.stat().st_ino
            process = SimpleNamespace(name="2147483647", path=str(root / "vanished"))
            scandir = os.scandir

            def entries(path):
                return [process] if path == "/proc" else scandir(path)

            with patch.object(package_guard.os, "scandir", side_effect=entries):
                self.assertFalse(package_guard._lock_actively_held(str(lock)))
            self.assertEqual((lock.read_bytes(), lock.stat().st_ino), before)

    def test_current_fd_ownership_wins_over_stale_or_reused_pid_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "lock"
            lock.write_text("2147483647")
            fd_dir = root / "process/fd"
            fd_dir.mkdir(parents=True)
            (fd_dir / "3").symlink_to(lock)
            process = SimpleNamespace(name="42", path=str(root / "process"))
            scandir = os.scandir

            def entries(path):
                return [process] if path == "/proc" else scandir(path)

            with patch.object(package_guard.os, "scandir", side_effect=entries):
                self.assertTrue(package_guard._lock_actively_held(str(lock)))
            self.assertEqual(lock.read_text(), "2147483647")

    def test_process_name_disappearance_is_a_safe_preflight_miss(self):
        process = SimpleNamespace(name="42", path="/fixture/vanished")
        with (
            patch.object(package_guard.os, "scandir", return_value=[process]),
            patch("builtins.open", side_effect=FileNotFoundError("PID exited")),
        ):
            self.assertEqual(package_guard._running_comm_names(), set())


class RamReportingTests(unittest.TestCase):
    def setUp(self):
        # Reuse the suite's HTTP/GI/socket-denial fixture without rediscovering
        # its tests under an imported TestCase alias.
        fixture = reporting_fixtures.ReportingTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.antenna = fixture.antenna

    def test_ram_kib_is_reported_in_gib_with_one_decimal(self):
        for line, expected in (
            ("MemTotal: 16777216 kB\n", "16.0 GiB"),
            ("MemTotal: 16437248 kB\n", "15.7 GiB"),
            ("MemFree: 100 kB\nMemTotal: 8388608 kB\n", "8.0 GiB"),
        ):
            with (
                self.subTest(line=line),
                patch("builtins.open", mock_open(read_data=line)),
            ):
                self.assertEqual(self.antenna._get_ram_info(), expected)

    def test_missing_or_malformed_measurement_is_unknown(self):
        for line in (
            "",
            "MemTotal:\n",
            "MemTotal: junk kB\n",
            "MemTotal: 0 kB\n",
            "MemTotal: -1 kB\n",
            "MemTotal: 42 bytes\n",
            "MemTotal: 42\n",
            "MemTotal: " + "9" * 400 + " kB\n",
        ):
            with (
                self.subTest(line=line),
                patch("builtins.open", mock_open(read_data=line)),
            ):
                self.assertEqual(self.antenna._get_ram_info(), "unknown")
        with patch("builtins.open", side_effect=OSError("masked proc")):
            self.assertEqual(self.antenna._get_ram_info(), "unknown")

    def test_context_includes_valid_ram_only_without_changing_other_fields(self):
        stubs = {
            "_get_os_info": {"id": "fixture", "version": "1"},
            "_get_wsl_info": None,
            "_get_cpu_model": "fixture CPU",
            "_get_gpu_info": {"devices": [], "gpu_count": 0},
            "_get_init_system_info": "systemd",
            "_get_desktop_info": {"desktop": "unknown", "wm": "unknown"},
            "_get_interface_mode": "fixture",
        }
        with ExitStack() as stack:
            for name, value in stubs.items():
                stack.enter_context(
                    patch.object(self.antenna, name, return_value=value)
                )
            with patch.object(self.antenna, "_get_ram_info", return_value="15.7 GiB"):
                context = self.antenna.get_system_context()
            with patch.object(self.antenna, "_get_ram_info", return_value="unknown"):
                fallback = self.antenna.get_system_context()
        self.assertIn("RAM: 15.7 GiB", context)
        self.assertNotIn("RAM:", fallback)
        self.assertEqual(context.replace(" | RAM: 15.7 GiB", ""), fallback)


class PreloadAndTranslationTests(ShellFixtures):
    def test_preload_boundaries_invalid_detection_and_cancelled_confirmation(self):
        libs = self.temp / "libs"
        libs.mkdir()
        (libs / "linuxtoys.lib").write_text(
            f'_lang_() {{ source {shlex.quote(str(ROOT / "p3/libs/lang/en.lib"))}; }}\n'
        )
        script = (ROOT / "p3/scripts/extra/preload.sh").read_text()
        minimum = (16 * 1000000000 + 1023) // 1024
        for value, allowed in (
            (str(minimum - 1), False),
            (str(minimum), True),
            (str(minimum + 1), True),
            ("16777216", True),
            ("", False),
            ("junk", False),
            ("0", False),
            ("-1", False),
            ("012345678", False),
            ("9999999999999999999999999", False),
        ):
            with self.subTest(value=value):
                self.fresh()
                result = self.shell(
                    f"""
awk() {{ printf '%s' {shlex.quote(value)}; }}
nonfatal() {{ record "refused:$*"; }}
zenity() {{ record "question:$*"; return 1; }}
sudo_rq() {{ record forbidden; return 97; }}
{script}
"""
                )
                lines = self.event_lines()
                self.assertEqual(
                    any(x.startswith("question:") for x in lines), allowed, result
                )
                self.assertFalse(any(x == "forbidden" for x in lines))
                if allowed:
                    self.assertIn("16GB", lines[0])
                elif value.isdigit() and not value.startswith("0") and len(value) < 13:
                    self.assertIn("16GB", lines[0])
                else:
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn("Unable to detect", lines[0])

    def test_reading_failure_never_becomes_permission_to_install(self):
        libs = self.temp / "libs"
        libs.mkdir()
        (libs / "linuxtoys.lib").write_text("_lang_() { :; }\n")
        result = self.shell(
            "awk() { return 1; }; nonfatal() { record refused; }; "
            "zenity() { record forbidden; };\n"
            + (ROOT / "p3/scripts/extra/preload.sh").read_text()
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.event_lines(), ["refused"])

    def test_preload_stays_x86_only_and_the_exact_bundle_remains_authorized(self):
        path = ROOT / "p3/scripts/extra/preload.sh"
        architecture.require_script_path(path, "x86_64")
        with self.assertRaises(architecture.ArchitectureError):
            architecture.require_script_path(path, "aarch64")

    def test_every_translation_sources_with_the_same_ram_requirement(self):
        for path in sorted((ROOT / "p3/libs/lang").glob("*.lib")):
            with self.subTest(language=path.stem):
                self.assertNotIn(b"\0", path.read_bytes())
                result = self.shell(
                    f"_cram=16; source {shlex.quote(str(path))}; "
                    'printf "%s\\n%s\\n" "$msg208" "$msg228"'
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertIn("16", result.stdout)
                self.assertNotIn("${_cram}", result.stdout)
        chinese = ROOT / "p3/libs/lang/zh.lib"
        result = self.shell(
            f"_cram=16; source {shlex.quote(str(chinese))}; "
            'printf "%s" "$gdrive_guide_text"'
        )
        self.assertIn('"Google Drive API"', result.stdout)

    def test_versions_match_the_integrated_release(self):
        from app.updater import __version__

        self.assertEqual(__version__, "7.10.4")
        self.assertEqual((ROOT / "src/ver").read_text().strip(), __version__)


class BackgroundUpdaterTests(ShellFixtures):
    def test_failed_child_installer_keeps_parent_download_cleanup(self):
        from app.updater import update_helper

        libs = self.temp / "libs"
        libs.mkdir()
        (libs / "linuxtoys.bash").write_text(":\n")
        # This fake downloader only writes a tiny fixture installer. The child
        # installs nothing and deliberately sets its own EXIT trap before failing.
        downloader = self.temp / "bin/curl"
        downloader.write_text(
            r"""#!/bin/sh
cat > "$4" <<'INSTALLER'
trap 'printf "child-cleanup\n" >> "$EVENTS"' EXIT
exit 42
INSTALLER
"""
        )
        original_run = subprocess.run
        scripts = []

        def run(argv, **kwargs):
            script = Path(shlex.split(argv[2])[1])
            scripts.append(script)
            return original_run(
                ["/bin/bash", str(script)],
                capture_output=True,
                text=True,
                env={**kwargs["env"], **self.env},
                timeout=10,
            )

        with (
            patch.object(update_helper.subprocess, "run", side_effect=run),
            patch("builtins.open", mock_open(read_data="ID=fixture\n")),
            patch.dict(os.environ, {"SCRIPT_DIR": str(self.temp)}),
        ):
            success, error = update_helper.run_background_update()
        self.assertFalse(success)
        self.assertIn("42", error)
        self.assertEqual(self.event_lines(), ["child-cleanup"])
        self.assertFalse(list(self.temp.glob("linuxtoys-installer.*")))
        self.assertTrue(scripts)
        self.assertFalse(any(path.exists() for path in scripts))

    def test_background_update_is_noninteractive_and_cleans_temporary_scripts(self):
        from app.updater import update_helper

        for status in (0, 100, 42):
            with self.subTest(status=status), ExitStack() as stack:
                scripts = []

                def run(argv, **kwargs):
                    script = Path(shlex.split(argv[2])[1])
                    text = script.read_text()
                    scripts.append(script)
                    self.assertIn('bash "$_lt_installer"', text)
                    self.assertIn("# architectures: x86_64, aarch64", text)
                    self.assertEqual(kwargs["env"]["LINUXTOYS_NONINTERACTIVE"], "1")
                    return SimpleNamespace(
                        returncode=status,
                        stdout="fixture failure" if status else "",
                        stderr="",
                    )

                stack.enter_context(
                    patch.object(update_helper.subprocess, "run", side_effect=run)
                )
                stack.enter_context(
                    patch("builtins.open", mock_open(read_data="ID=fixture\n"))
                )
                stack.enter_context(
                    patch.dict(os.environ, {"SCRIPT_DIR": str(ROOT / "p3")})
                )
                success, error = update_helper.run_background_update()
                self.assertEqual(success, status == 0)
                if status == 100:
                    self.assertIn("cancelled", error)
                elif status:
                    self.assertEqual(error, "fixture failure")
                self.assertEqual(len(scripts), 1)
                self.assertFalse(scripts[0].exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
