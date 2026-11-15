"""Candidate lifecycle probes, restricted to a new offline AArch64 container.

The accompanying pinned driver supplies authenticated inputs and the reviewed
prospective Nala-only policy. Never run this on a workstation or the VM host.
Fault injection changes only container APT inputs/configuration, not app code.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time


def require_container() -> None:
    isolated = Path("/.dockerenv").is_file()
    if os.environ.get("M5_ISOLATOR") == "bwrap":
        try:
            host = json.loads(Path("/inputs/host-namespaces.json").read_text())
            status = dict(
                line.split(":", 1)
                for line in Path("/proc/self/status").read_text().splitlines()
                if ":" in line
            )
            isolated = (
                all(
                    os.readlink("/proc/self/ns/" + name) != host[name]
                    for name in ("pid", "net", "mnt", "ipc", "uts", "cgroup")
                )
                and status["NoNewPrivs"].strip() == "1"
                and int(status["CapEff"].strip(), 16) == 0xCB
                and int(status["CapBnd"].strip(), 16) == 0xCB
            )
        except (OSError, ValueError, KeyError):
            isolated = False
    if not (
        isolated
        and os.getuid() == 0
        and platform.machine() == "aarch64"
        and os.environ.get("M5_DISPOSABLE_CONTAINER") == "ef5eb1a7"
    ):
        raise SystemExit("Requires the pinned disposable native M5 container")


def main(case: str) -> None:
    require_container()
    source = Path("/work/source")
    results = Path("/work/results")
    results.mkdir(exist_ok=True)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source / "p3"))
    from app import architecture, library_loader, repo_parser, script_compat
    from app.revert_helper import (
        build_auto_revert_script_entry,
        build_uninstall_script_entry,
    )
    from app.term_registry import ExecutionRegistry
    from app.compat import get_linuxtoys_cache_dir

    manifest = json.loads(Path("/inputs/offline-input-manifest.json").read_text())
    packages = {row["package"]: row for row in manifest["archives"]}
    commands: list[dict] = []
    checks: list[str] = []
    observations: dict = {}
    profile = Path("/root/m5-profile")
    profile.mkdir()
    os.environ.update(
        HOME=str(profile),
        XDG_CACHE_HOME=str(profile / ".cache"),
        SCRIPT_DIR=str(source / "p3"),
        CACHE_DIR=str(source / "p3/scripts"),
    )
    canary = profile / "existing-user-data"
    canary.write_bytes(b"M5 original user data; preserve exactly\n")
    canary_hash = hashlib.sha256(canary.read_bytes()).hexdigest()

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    def run(argv, *, env=None, user=None, expected=None, timeout=180):
        options = (
            {} if user is None else {"user": user, "group": user, "extra_groups": []}
        )
        proc = subprocess.run(
            argv, env=env, capture_output=True, text=True, timeout=timeout, **options
        )
        commands.append(
            {
                "argv": argv,
                "exit": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        )
        if expected is not None:
            check("command exit " + str(expected), proc.returncode == expected)
        return proc

    def state():
        proc = run(
            [
                "dpkg-query",
                "-W",
                "-f=${binary:Package} ${Version} ${db:Status-Status}\n",
            ],
            expected=0,
        )
        return {
            words[0]: {"version": words[1], "status": " ".join(words[2:])}
            for line in proc.stdout.splitlines()
            if len(words := line.split()) >= 3
        }

    def is_installed(name):
        return state().get(name, {}).get("status") == "installed"

    def pool_file(name):
        return Path("/mirror/ubuntu") / packages[name]["control_metadata"]["Filename"]

    def prepare(info, tag, *, fail_after=False, home=profile):
        transmap = home / (tag + ".transmap")
        transmap.touch()
        env = library_loader.script_environment(
            info,
            {
                **os.environ,
                "HOME": str(home),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "TRANSMAP_PATH": str(transmap),
                "CHECKLIST_RUN": "1",
                "DISABLE_ZENITY": "1",
                "LINUXTOYS_TIMEFIX": "0",
                "LANG": "C.UTF-8",
            },
        )
        argv = library_loader.script_command(info["path"], str(source / "p3"))
        if fail_after:
            argv[2] += "\nexit 73\n"
        return argv, env, transmap

    def execute(info, tag, *, expected=0, fail_after=False):
        argv, env, transmap = prepare(info, tag, fail_after=fail_after)
        proc = run(argv, env=env)
        if expected is None:
            check(tag + " fails visibly", proc.returncode != 0)
        else:
            check(tag + " exit", proc.returncode == expected)
        return transmap, proc

    baseline = state()
    report = {
        "case": case,
        "status": "failed",
        "checks": checks,
        "commands": commands,
        "observations": observations,
        "environment": {"uname": list(os.uname()), "python": sys.version},
        "baseline_packages": baseline,
    }
    try:
        script_compat.require_bundle(source / "p3/scripts")
        check("native architecture", architecture.host().value == "aarch64")
        entries = repo_parser.load_repo_entries(str(source / "p3/scripts"))
        entry = next(item for item in entries if item["name"] == "Nala")
        architecture.require_entry(entry)
        info = repo_parser.materialize_repo_script(entry)
        check(
            "real Nala installer", "pkg_install nala" in Path(info["path"]).read_text()
        )
        check("candidate absent initially", not is_installed("nala"))

        if case == "lifecycle":
            transmap, _ = execute(info, "install")
            check("actual Nala installed", is_installed("nala"))
            run(["nala", "--version"], expected=0)
            run(["nala", "--help"], expected=0)
            check("explicit transaction recorded", "pkg nala" in transmap.read_text())
            check(
                "registry written",
                ExecutionRegistry.save_called_script_transaction(
                    info["name"], str(transmap)
                ),
            )
            config = Path("/etc/nala/nala.conf")
            config.write_bytes(
                config.read_bytes() + b"\n# M5 existing configuration canary\n"
            )
            config_hash = hashlib.sha256(config.read_bytes()).hexdigest()
            no_op, _ = execute(info, "already-installed")
            check("already installed is not re-recorded", not no_op.read_text().strip())
            check(
                "existing configuration retained",
                hashlib.sha256(config.read_bytes()).hexdigest() == config_hash,
            )
            uninstall = build_uninstall_script_entry(info)
            check("real registry uninstall generated", uninstall is not None)
            execute(uninstall, "uninstall")
            check("candidate code removed", not is_installed("nala"))
            observations["after_remove"] = state().get("nala")
            check(
                "conffile preserved by removal",
                hashlib.sha256(config.read_bytes()).hexdigest() == config_hash,
            )
            execute(info, "reinstall-after-remove")
            check("reinstall after config-files state works", is_installed("nala"))

        elif case in ("auto-revert", "rollback-failure"):
            transmap, _ = execute(
                info, "install-then-fail", expected=73, fail_after=True
            )
            check("candidate installed before outer failure", is_installed("nala"))
            check("transaction survives failure", "pkg nala" in transmap.read_text())
            revert = build_auto_revert_script_entry(info, str(transmap))
            check("production auto-revert generated", revert is not None)
            if case == "rollback-failure":
                check(
                    "registry saved",
                    ExecutionRegistry.save_called_script_transaction(
                        info["name"], str(transmap)
                    ),
                )
                registry = Path(get_linuxtoys_cache_dir()) / "registry"
                registry_before = registry.read_bytes()
                fault = Path("/etc/apt/apt.conf.d/98m5-rollback-failure")
                fault.write_text('DPkg::Pre-Invoke { "/bin/false"; };\n')
                execute(revert, "failed-auto-revert", expected=None)
                check("failed reversal leaves candidate visible", is_installed("nala"))
                check(
                    "failed reversal retains registry",
                    registry.read_bytes() == registry_before,
                )
                fault.unlink()
            execute(revert, "auto-revert")
            check("reversal removes explicit candidate", not is_installed("nala"))

        elif case in ("checksum", "missing-dependency"):
            if case == "checksum":
                path = pool_file("nala")
                original = path.read_bytes()
                path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                observations["expected_sha256"] = packages["nala"]["sha256"]
                observations["corrupt_sha256"] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
            else:
                dependency = "python3-anyio"
                check(
                    "missing dependency is not already installed",
                    not is_installed(dependency),
                )
                pool_file(dependency).unlink()
                observations["unavailable_dependency"] = dependency
            transmap, proc = execute(info, case, expected=None)
            if case == "checksum":
                check(
                    "APT reports hash mismatch",
                    "Hash Sum mismatch" in proc.stdout + proc.stderr,
                )
            check(
                "failed acquisition records no install",
                not transmap.read_text().strip(),
            )
            check("failed acquisition preserves dpkg state", state() == baseline)

        elif case == "malformed-metadata":
            universe = Path(
                "/mirror/ubuntu/dists/resolute/universe/binary-arm64/Packages"
            )
            original = universe.read_bytes()
            record = next(
                block
                for block in original.split(b"\n\n")
                if block.startswith(b"Package: nala\n")
            )
            altered = record.replace(
                b"Architecture: all\n", b"Architecture: malformed-isa\n"
            )
            check("metadata was actually altered", altered != record)
            universe.write_bytes(original.replace(record, altered, 1))
            for path in Path("/var/lib/apt/lists").iterdir():
                if path.is_file():
                    path.unlink()
            update = run(["apt-get", "update"])
            check("authenticated metadata update fails", update.returncode != 0)
            check(
                "metadata digest mismatch diagnosed",
                "Hash Sum mismatch" in update.stdout + update.stderr,
            )
            transmap, _ = execute(info, case, expected=None)
            check(
                "malformed input records no install", not transmap.read_text().strip()
            )
            check("malformed metadata preserves dpkg state", state() == baseline)

        elif case == "interruption":
            fault = Path("/etc/apt/apt.conf.d/98m5-interruption")
            fault.write_text(
                'DPkg::Pre-Install-Pkgs { "python3 /inputs/barrier.py"; };\n'
            )
            argv, env, transmap = prepare(info, case)
            out = (results / "interrupted.stdout").open("w")
            err = (results / "interrupted.stderr").open("w")
            proc = subprocess.Popen(
                argv, env=env, stdout=out, stderr=err, start_new_session=True
            )
            ready = results / "preinstall-ready"
            try:
                deadline = time.monotonic() + 90
                while (
                    not ready.exists()
                    and proc.poll() is None
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.02)
                check("real APT reached pre-install barrier", ready.is_file())
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                status = proc.wait(timeout=30)
                out.close()
                err.close()
                fault.unlink()
            observations["interrupted_exit"] = status
            check("real installer interruption is nonzero", status != 0)
            check("pre-unpack interruption preserves dpkg state", state() == baseline)
            check(
                "interruption records no completed install",
                not transmap.read_text().strip(),
            )
            check(
                "no fictitious reversal generated",
                build_auto_revert_script_entry(info, str(transmap)) is None,
            )

        elif case == "privilege":
            home = Path("/tmp/m5-unprivileged")
            home.mkdir()
            shutil.chown(home, user=65534, group=65534)
            copied = home / "installer.sh"
            shutil.copyfile(info["path"], copied)
            copied.chmod(0o755)
            unprivileged = {**info, "path": str(copied)}
            argv, env, transmap = prepare(unprivileged, case, home=home)
            shutil.chown(transmap, user=65534, group=65534)
            session = home / "session"
            session.mkdir()
            shutil.chown(session, user=65534, group=65534)
            env["LINUXTOYS_EXECUTION_SESSION_DIR"] = str(session)
            proc = run(argv, env=env, user=65534)
            check("unprivileged caller cannot install", proc.returncode != 0)
            observations["unprivileged_stderr"] = proc.stderr
            check("privilege refusal preserves packages", state() == baseline)
        else:
            raise ValueError("Unknown case: " + case)

        after = state()
        check(
            "existing installed package versions retained",
            all(
                after.get(k) == v
                for k, v in baseline.items()
                if v["status"] == "installed"
            ),
        )
        check(
            "existing user data retained",
            hashlib.sha256(canary.read_bytes()).hexdigest() == canary_hash,
        )
        audit = run(["dpkg", "--audit"], expected=0)
        check("dpkg audit clean", not audit.stdout.strip())
        report["status"] = "passed"
    except BaseException as error:
        report.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        report["final_packages"] = state()
        report["candidate_config_remains"] = Path("/etc/nala/nala.conf").exists()
        report["existing_user_data_preserved"] = (
            hashlib.sha256(canary.read_bytes()).hexdigest() == canary_hash
        )
        (results / "result.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: native_m5_candidates.py CASE (pinned container only)")
    main(sys.argv[1])
