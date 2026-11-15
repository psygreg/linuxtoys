"""Package-state decisions only: every mutating package command is a shell fake."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
DPKG_QUERY = shutil.which("dpkg-query")
MANAGERS = (
    "debian",
    "ubuntu",
    "arch",
    "cachy",
    "manjaro",
    "fedora",
    "ostree",
    "suse",
    "rhel",
    "solus",
)


class ShellCase(unittest.TestCase):
    def run_shell(
        self,
        action="pkg_exists nala; dump",
        *,
        states=None,
        output="install ok installed",
        query_exit=0,
        real=False,
        manager="ubuntu",
        audit="",
        configure_exit=0,
        raw_database=None,
        missing_database=False,
        unreadable_database=False,
        alternate_root=False,
        repair=False,
        repair_query_exit=0,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "var/lib/dpkg" if alternate_root else root / "db"
            db.mkdir(parents=True)
            status = db / "status"
            records = {"nala": "install ok installed"} if states is None else states

            def record(name, state):
                # dpkg rejects trigger states without their matching fields.
                extra = {
                    "triggers-awaited": "Triggers-Awaited: fixture-dependency\n",
                    "triggers-pending": "Triggers-Pending: fixture-trigger\n",
                }.get(state.split()[-1], "")
                return (
                    f"Package: {name}\nStatus: {state}\nArchitecture: all\n"
                    "Version: 0.16.0\nMaintainer: Fixture <fixture@example.invalid>\n"
                    "Description: temporary query fixture\n" + extra + "\n"
                )

            data = (
                "".join(record(name, state) for name, state in records.items())
                if raw_database is None
                else raw_database
            )
            repaired_data = "".join(
                record(
                    name,
                    (
                        state
                        if state.endswith(
                            (" ok installed", " ok config-files", " ok not-installed")
                        )
                        else "install ok installed"
                    ),
                )
                for name, state in records.items()
            )
            repaired_status = root / "repaired-status"
            repaired_status.write_text(repaired_data)
            if not missing_database:
                status.write_text(data)
                if unreadable_database:
                    status.chmod(0)
            events = root / "events"
            # Also refuse direct `command apt-get`/sudo/etc if a future change
            # bypasses the shell fakes below. Only dpkg-query's absolute path
            # is allowed to inspect the temporary database in native tests.
            blocked = root / "blocked-bin"
            blocked.mkdir()
            for name in (
                "apt",
                "apt-get",
                "dpkg",
                "dpkg-query",
                "sudo",
                "pkexec",
                "pacman",
                "pamac",
                "rpm",
                "rpm-ostree",
                "dnf",
                "zypper",
                "eopkg",
            ):
                command = blocked / name
                command.write_text(
                    "#!/bin/sh\necho 'Forbidden external package operation' >&2\nexit 97\n"
                )
                command.chmod(0o700)
            env = {
                **os.environ,
                "HOME": str(root),
                "SCRIPT_DIR": str(root),
                "MANAGER": manager,
                "EVENTS": str(events),
                "QUERY_OUTPUT": output,
                "QUERY_EXIT": str(query_exit),
                "AUDIT_OUTPUT": audit,
                "CONFIGURE_EXIT": str(configure_exit),
                "UPD_SERVICE": "0",
                "REPAIR_FIXTURE": str(int(repair)),
                "REPAIR_QUERY_EXIT": str(repair_query_exit),
                "REAL_QUERY": str(int(real)),
                "QUERY_DB": str(db),
                "REPAIRED_STATUS": str(repaired_status),
                "PATH": str(blocked) + os.pathsep + os.environ.get("PATH", ""),
            }
            env.pop("DPKG_ROOT", None)
            env.pop("DPKG_ADMINDIR", None)
            env["DPKG_ROOT" if alternate_root else "DPKG_ADMINDIR"] = str(
                root if alternate_root else db
            )
            predicates = "\n".join(
                f'is_{name}() {{ [[ "$MANAGER" == {name} ]]; }}' for name in MANAGERS
            )
            query = (
                "command " + shlex.quote(DPKG_QUERY) + ' "$@"'
                if real
                else 'printf "%s" "$QUERY_OUTPUT"; return "$QUERY_EXIT"'
            )
            script = f"""
source {shlex.quote(str(ROOT / 'p3/libs/packages.bash'))}
{predicates}
record() {{ printf '%s\\n' "$*" >> "$EVENTS"; }}
die() {{ printf '%s\\n' "$*" >&2; exit 1; }}
fatal() {{ die "$@"; }}
dump() {{ printf 'found:%s\\nmissing:%s\\nincomplete:%s\\n' "${{pkg_found[*]}}" "${{pkg_notfound[*]}}" "${{_pkg_dpkg_incomplete[*]}}"; }}
trap 'record "arrays:${{#pkg_found[@]}}:${{#pkg_notfound[@]}}:${{#_pkg_dpkg_incomplete[@]}}"' EXIT
dpkg-query() {{ record "query:$*"; {query}; }}
_architecture_check() {{ record "architecture:$*"; }}
askpass() {{ record askpass; }}
runner_lock() {{ record "lock:$*"; }}
runner_unlock() {{ record unlock; }}
_append_transmap() {{ record "transmap:$*"; }}
info() {{ record info; }}
apt_busy_wait() {{ record busy; }}
_apt_lock_actively_held() {{ return 1; }}
sudo_() {{
    record "sudo:$*"
    case "$1" in dpkg|apt-get) "$@" ;; *) die 'Unexpected privileged fixture call' ;; esac
}}
dpkg() {{
    record "dpkg:$*"
    case "$*" in
        --audit) printf '%s' "$AUDIT_OUTPUT" ;;
        '--configure -a')
            [[ "$CONFIGURE_EXIT" == 0 ]] || return "$CONFIGURE_EXIT"
            if [[ "$REPAIR_FIXTURE" == 1 ]]; then
                if [[ "$REAL_QUERY" == 1 ]]; then
                    # Simulate a metadata transition only in this temporary DB.
                    cp "$REPAIRED_STATUS" "$QUERY_DB/status"
                else
                    QUERY_OUTPUT='install ok installed'
                    QUERY_EXIT="$REPAIR_QUERY_EXIT"
                fi
            fi
            ;;
        *) die 'Unexpected dpkg fixture call' ;;
    esac
}}
apt-get() {{ record "apt-get:$*"; }}
pacman() {{ record "pacman:$*"; [[ "$2" == present ]]; }}
rpm() {{ record "rpm:$*"; [[ "$2" == present ]]; }}
eopkg() {{ record "eopkg:$*"; printf 'present 1.0\\n'; }}
{action}
"""
            result = subprocess.run(
                ["bash", "-c", script],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            recorded = events.read_text().splitlines() if events.exists() else []
            if status.is_file():
                status.chmod(0o600)
                self.assertEqual(
                    status.read_text(),
                    (
                        repaired_data
                        if real
                        and repair
                        and configure_exit == 0
                        and "dpkg:--configure -a" in recorded
                        else data
                    ),
                    "Unexpected temporary database change",
                )
            return result, recorded

    def assert_closed(self, result, events):
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Unable to determine dpkg package state", result.stderr)
        self.assertEqual(
            [e for e in events if not e.startswith("query:")], ["arrays:0:0:0"]
        )


class PackageStateDecisionTests(ShellCase):
    def test_installed_is_a_noop_without_authorization_or_recovery(self):
        for manager in ("debian", "ubuntu"):
            with self.subTest(manager=manager):
                result, events = self.run_shell("pkg_install nala", manager=manager)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    [e for e in events if not e.startswith("query:")], ["arrays:1:0:0"]
                )

    def test_query_errors_stop_even_when_install_is_in_a_conditional(self):
        for status in (2, 126, 127, 130):
            with self.subTest(status=status):
                result, events = self.run_shell(
                    "pkg_install nala || record fallback", output="", query_exit=status
                )
                self.assert_closed(result, events)

    def test_partial_query_failure_is_not_absence(self):
        result, events = self.run_shell(output="install ok installed", query_exit=1)
        self.assert_closed(result, events)

    def test_missing_query_result_means_absent_only_for_exit_one(self):
        result, _ = self.run_shell(output="", query_exit=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("missing:nala\n", result.stdout)
        result, events = self.run_shell(output="", query_exit=0)
        self.assert_closed(result, events)

    def test_unknown_or_multiple_statuses_fail_closed(self):
        for output in (
            "install mystery installed",
            "install ok mystery",
            "mystery ok installed",
            "install ok installed\ninstall ok installed",
            "installed",
        ):
            with self.subTest(output=output):
                result, events = self.run_shell(output=output)
                self.assert_closed(result, events)

    def test_missing_database_is_not_an_absent_package(self):
        result, events = self.run_shell(missing_database=True)
        self.assert_closed(result, events)
        self.assertFalse(any(e.startswith("query:") for e in events))

    def test_query_error_clears_previous_classifications(self):
        result, events = self.run_shell(
            'dpkg-query() { record "query:$*"; if [[ "${@: -1}" == present ]]; then '
            "printf 'install ok installed'; else return 2; fi; }; pkg_exists present nala",
        )
        self.assert_closed(result, events)

    def test_recovered_preexisting_package_is_not_recorded_as_a_new_install(self):
        result, events = self.run_shell(
            "pkg_install nala",
            output="install ok unpacked",
            audit="unconfigured fixture\n",
            repair=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        ordered = [
            "architecture:packages apt nala",
            "askpass",
            "lock:package-transaction",
            "dpkg:--audit",
            "dpkg:--configure -a",
            "apt-get:--fix-broken install -y",
        ]
        self.assertEqual([e for e in events if e in ordered], ordered)
        self.assertEqual(sum(e.startswith("query:") for e in events), 2)
        self.assertIn("unlock", events)
        self.assertFalse(
            any(e.startswith(("apt-get:install", "transmap:")) for e in events)
        )

    def test_still_incomplete_after_recovery_stops_without_install(self):
        result, events = self.run_shell(
            "pkg_install nala || record fallback",
            output="install ok unpacked",
            audit="unconfigured fixture\n",
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Failed to recover interrupted dpkg operation", result.stderr)
        self.assertEqual(sum(e.startswith("query:") for e in events), 2)
        self.assertFalse(
            any(
                e.startswith(("apt-get:install", "transmap:")) or e == "fallback"
                for e in events
            )
        )

    def test_recovery_noop_preserves_the_bypass_lock_contract(self):
        result, events = self.run_shell(
            "pkg_install --bypass nala",
            output="install ok unpacked",
            audit="unconfigured fixture\n",
            repair=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(e.startswith("lock:") or e == "unlock" for e in events))
        self.assertFalse(
            any(e.startswith(("apt-get:install", "transmap:")) for e in events)
        )

    def test_recovery_query_error_is_also_fail_closed(self):
        result, events = self.run_shell(
            "pkg_install nala",
            output="install ok unpacked",
            audit="unconfigured fixture\n",
            repair=True,
            repair_query_exit=2,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Unable to determine dpkg package state", result.stderr)
        self.assertIn("arrays:0:0:0", events)
        self.assertFalse(
            any(e.startswith(("apt-get:install", "transmap:")) for e in events)
        )

    def test_recovery_failure_prevents_install_and_transaction_record(self):
        result, events = self.run_shell(
            "pkg_install nala || record fallback",
            output="install ok unpacked",
            audit="unconfigured fixture\n",
            configure_exit=42,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Failed to recover interrupted dpkg operation", result.stderr)
        self.assertIn("dpkg:--configure -a", events)
        self.assertFalse(
            any(
                e.startswith(("apt-get:install", "transmap:")) or e == "fallback"
                for e in events
            )
        )

    def test_incomplete_packages_remain_removable(self):
        result, events = self.run_shell("pkg_remove nala", output="install ok unpacked")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("apt-get:remove -y --allow-unauthenticated nala", events)

    def test_residual_conffiles_do_not_trigger_remove_or_purge(self):
        result, events = self.run_shell(
            "pkg_remove nala", output="deinstall ok config-files"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [e for e in events if not e.startswith("query:")], ["arrays:0:1:0"]
        )

    def test_query_errors_also_stop_removal(self):
        result, events = self.run_shell("pkg_remove nala", output="", query_exit=2)
        self.assert_closed(result, events)


class OtherManagerCompatibilityTests(ShellCase):
    def test_existing_queries_and_array_results_are_preserved(self):
        for manager in MANAGERS[2:]:
            with self.subTest(manager=manager):
                result, events = self.run_shell(
                    "pkg_exists present absent; dump", manager=manager
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    result.stdout, "found:present\nmissing:absent\nincomplete:\n"
                )
                self.assertFalse(any(e.startswith("query:") for e in events))
                command = (
                    "eopkg:"
                    if manager == "solus"
                    else (
                        "pacman:" if manager in ("arch", "cachy", "manjaro") else "rpm:"
                    )
                )
                self.assertEqual(sum(e.startswith(command) for e in events), 2)
                if manager == "solus":
                    self.assertEqual(events[:2], ["eopkg:list-installed"] * 2)
                else:
                    flag = "-Qi" if command == "pacman:" else "-qi"
                    self.assertEqual(
                        events[:2],
                        [command + flag + " present", command + flag + " absent"],
                    )

    def test_installed_packages_still_skip_all_manager_transactions(self):
        for manager in MANAGERS[2:]:
            with self.subTest(manager=manager):
                result, events = self.run_shell("pkg_install present", manager=manager)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(
                    any(
                        e.startswith(("architecture:", "lock:", "apt-get:"))
                        or e == "askpass"
                        for e in events
                    )
                )

    def test_previous_debian_incomplete_list_cannot_leak_to_another_manager(self):
        result, _ = self.run_shell(
            "_pkg_dpkg_incomplete=(stale); pkg_exists present absent; dump",
            manager="fedora",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("incomplete:\n", result.stdout)


@unittest.skipUnless(DPKG_QUERY, "Requires existing dpkg-query; never install it")
class NativeDpkgQueryTests(ShellCase):
    def classify(self, state, *, package="nala", **kwargs):
        return self.run_shell(
            "pkg_exists " + shlex.quote(package) + "; dump",
            states={} if state is None else {"nala": state},
            real=True,
            **kwargs,
        )

    def test_actual_installed_state_is_independent_of_requested_selection(self):
        for want in ("install", "hold", "deinstall", "purge", "unknown"):
            with self.subTest(want=want):
                result, _ = self.classify(want + " ok installed")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "found:nala\nmissing:\nincomplete:\n")

    def test_real_absent_and_residual_states_are_not_installed(self):
        for state in (
            None,
            "unknown ok not-installed",
            "deinstall ok config-files",
            "purge ok config-files",
        ):
            with self.subTest(state=state):
                result, _ = self.classify(state)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "found:\nmissing:nala\nincomplete:\n")

    def test_all_incomplete_states_cannot_skip_install_recovery(self):
        states = [
            "install ok " + state
            for state in (
                "half-installed",
                "unpacked",
                "half-configured",
                "triggers-awaited",
                "triggers-pending",
            )
        ]
        states.append("install reinstreq installed")
        for state in states:
            with self.subTest(state=state):
                result, events = self.run_shell(
                    "pkg_install nala",
                    states={"nala": state},
                    real=True,
                    audit="interrupted fixture\n",
                    repair=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("dpkg:--configure -a", events)
                self.assertEqual(sum(e.startswith("query:") for e in events), 2)
                self.assertFalse(
                    any(e.startswith(("apt-get:install", "transmap:")) for e in events)
                )

    def test_residual_conffiles_reach_install_dispatch(self):
        result, events = self.run_shell(
            "pkg_install nala", states={"nala": "deinstall ok config-files"}, real=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("apt-get:install -y nala", events)

    def test_corrupt_and_unreadable_databases_fail_closed(self):
        result, events = self.run_shell(real=True, raw_database="malformed\n")
        self.assert_closed(result, events)
        if os.getuid() != 0:
            result, events = self.run_shell(real=True, unreadable_database=True)
            self.assert_closed(result, events)

    def test_actual_unknown_dpkg_state_fails_closed(self):
        result, events = self.classify("install ok unexpected-state")
        self.assert_closed(result, events)

    def test_standard_dpkg_root_location_is_respected(self):
        result, _ = self.classify("install ok installed", alternate_root=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("found:nala\n", result.stdout)

    def test_qualified_name_and_version_request_keep_query_semantics(self):
        result, _ = self.classify("install ok installed", package="nala:all")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("found:nala:all\n", result.stdout)
        result, _ = self.classify("install ok installed", package="nala=0.16.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("missing:nala=0.16.0\n", result.stdout)

    def test_mixed_states_keep_partial_packages_removable(self):
        states = {
            "present": "hold ok installed",
            "residual": "deinstall ok config-files",
            "partial": "install ok unpacked",
        }
        result, _ = self.run_shell(
            "pkg_exists present residual partial absent; dump", states=states, real=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "found:present\nmissing:residual partial absent\nincomplete:partial\n",
        )
        result, events = self.run_shell(
            "pkg_remove present residual partial absent", states=states, real=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "apt-get:remove -y --allow-unauthenticated present partial", events
        )

    def test_ambiguous_multi_package_query_fails_closed(self):
        result, events = self.run_shell(
            "pkg_exists 'nala*'",
            real=True,
            states={
                "nala": "install ok installed",
                "nala-other": "install ok installed",
            },
        )
        self.assert_closed(result, events)

    def test_recovery_then_new_install_records_only_the_absent_package(self):
        result, events = self.run_shell(
            "pkg_install partial absent",
            states={"partial": "install ok unpacked"},
            real=True,
            audit="interrupted fixture\n",
            repair=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("apt-get:install -y absent", events)
        self.assertIn("transmap:pkg absent", events)
        self.assertNotIn("transmap:pkg partial absent", events)


if __name__ == "__main__":
    unittest.main(verbosity=2)
