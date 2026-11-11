"""Actual offline dpkg lifecycle tests; run as root in disposable ARM64 Docker.

Each mode requires a separate prepared runtime-container clone. No dependency
downloads, service starts, force-dependency options or host operations exist.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import signal
import struct
import subprocess
import sys
import tarfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p3"))
from app.architecture import LABELS, host, label  # noqa: E402

CANCELLED_DIALOGS: list[str] = []


def run(
    args: list[str],
    *,
    good: bool = True,
    timeout: int = 60,
    decline_password: bool = False,
) -> subprocess.CompletedProcess:
    # Cancel real first-run metadata credential dialogs inside this container.
    # No credentials, backend substitutes or privilege grants are supplied.
    stopped = threading.Event()

    def cancel_dialogs() -> None:
        uid = pwd.getpwnam("testuser").pw_uid
        while not stopped.wait(0.1):
            for entry in Path("/proc").iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    if entry.stat().st_uid != uid:
                        continue
                    argv = (entry / "cmdline").read_bytes().split(b"\0")
                    password = b"--password" in argv
                    auth_error = b"--error" in argv and b"Authentication Failed" in argv
                    if argv[0].rsplit(b"/", 1)[-1] == b"zenity" and (
                        password or auth_error
                    ):
                        os.kill(int(entry.name), signal.SIGTERM)
                        CANCELLED_DIALOGS.append(
                            "password" if password else "authentication-error"
                        )
                except (FileNotFoundError, ProcessLookupError):
                    pass

    worker = (
        threading.Thread(target=cancel_dialogs, daemon=True)
        if decline_password
        else None
    )
    if worker is not None:
        worker.start()
    try:
        result = subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    finally:
        stopped.set()
        if worker is not None:
            worker.join()
    if (result.returncode == 0) != good:
        raise RuntimeError(
            f"Unexpected result {args}: {result.returncode}\n{result.stdout}\n{result.stderr}"
        )
    return result


def inspect(package: Path) -> dict:
    architecture = run(["dpkg-deb", "-f", str(package), "Architecture"]).stdout.strip()
    assert architecture == label("deb")
    control = subprocess.check_output(["dpkg-deb", "--ctrl-tarfile", str(package)])
    with tarfile.open(fileobj=io.BytesIO(control)) as archive:
        assert {m.name.removeprefix("./") for m in archive if m.isfile()} == {
            "control",
            "md5sums",
        }
    data = subprocess.check_output(["dpkg-deb", "--fsys-tarfile", str(package)])
    elf = []
    count = 0
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            name = member.name.removeprefix("./")
            assert (member.uid, member.gid) == (0, 0), name
            assert member.isdir() or member.isfile(), name
            assert member.mode in (0o644, 0o755), (name, oct(member.mode))
            if name in ("", "."):
                assert member.isdir() and member.mode == 0o755
                continue
            assert name == "usr" or name.startswith("usr/"), name
            if member.isdir():
                assert member.mode == 0o755
                continue
            count += 1
            stream = archive.extractfile(member)
            assert stream is not None
            with stream:
                body = stream.read()
            for forbidden in (
                b"/Users/tahax09/",
                b"/home/ta/linuxtoys",
                b"/tmp/linuxtoys-m2",
            ):
                assert forbidden not in body, name
            if body.startswith(b"\x7fELF"):
                assert body[4:6] == b"\x02\x01"
                assert struct.unpack("<H", body[18:20])[0] == LABELS[host()].elf_machine
                assert name.startswith("usr/lib/linuxtoys/app/"), name
                elf.append(name)
    assert set(elf) == {
        "usr/lib/linuxtoys/app/_catalog_rs.abi3.so",
        "usr/lib/linuxtoys/app/liblinuxtoys_gui.so",
    }
    return {
        "file": package.name,
        "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
        "architecture": architecture,
        "version": run(["dpkg-deb", "-f", str(package), "Version"]).stdout.strip(),
        "depends": run(["dpkg-deb", "-f", str(package), "Depends"]).stdout.strip(),
        "payload_files": count,
        "elf_files": elf,
        "maintainer_scripts": [],
        "ownership_permissions_and_no_host_paths": True,
    }


def normal(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return run(
        [
            "runuser",
            "-u",
            "testuser",
            "--",
            "env",
            "-u",
            "PYTHONPATH",
            "HOME=/home/testuser",
            "PYTHONDONTWRITEBYTECODE=1",
            "LINUXTOYS_TIMEFIX=0",
            "LINUXTOYS_TEST_APP_DIR=/usr/lib/linuxtoys",
            "GIO_USE_VFS=local",
            *args,
        ],
        **kwargs,
    )


def canaries() -> dict[str, str]:
    user = pwd.getpwnam("testuser")
    assert user.pw_uid != 0
    created = []
    for suffix in (
        ".config/linuxtoys/package-canary",
        ".local/share/linuxtoys/package-canary",
        ".cache/linuxtoys/package-canary",
    ):
        path = Path(user.pw_dir) / suffix
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("user data preserved across package operations\n")
        created.append(path)
    for path in Path(user.pw_dir).rglob("*"):
        os.chown(path, user.pw_uid, user.pw_gid)
    return {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in created
    }


def preserved(expected: dict[str, str]) -> None:
    for name, sha in expected.items():
        path = Path(name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
        assert path.stat().st_uid == pwd.getpwnam("testuser").pw_uid


def configured() -> None:
    assert (
        run(["dpkg-query", "-W", "-f=${db:Status-Abbrev}", "linuxtoys"]).stdout == "ii "
    )
    assert not run(["dpkg", "--audit"]).stdout.strip()
    assert not run(["dpkg", "--verify", "linuxtoys"]).stdout.strip()


def system_state() -> dict:
    """Configuration/package guards; ordinary icon/MIME triggers are expected."""
    return {
        "etc": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path("/etc").rglob("*")
            if p.is_file() and not p.is_symlink()
        },
        "packages": sorted(
            line
            for line in run(
                [
                    "dpkg-query",
                    "-W",
                    "-f=${binary:Package} ${Version} ${db:Status-Abbrev}\\n",
                ]
            ).stdout.splitlines()
            if not line.startswith("linuxtoys ")
        ),
    }


def app_checks(probe: Path) -> dict:
    for option in ("--help", "--version", "--list"):
        result = normal(["/usr/bin/linuxtoys", option], timeout=90)
        if option == "--list":
            assert all(
                name in result.stdout
                for name in ("Atkinson Hyperlegible", "OpenDyslexic", "Nerd Fonts")
            ), result.stdout
    normal(
        [
            "python3",
            "-c",
            "import os; assert os.getuid()!=0; assert not os.access('/usr/lib/linuxtoys',os.W_OK)",
        ]
    )
    logs = {}
    for mode in ("imports", "tui", "mcp", "widgets", "gui", "launcher"):
        command = [
            "python3",
            "-B",
            str(probe),
            mode,
            "--profile",
            f"/home/testuser/package-{mode}",
        ]
        if mode in ("widgets", "gui", "launcher"):
            command = [
                "xvfb-run",
                "-a",
                "dbus-run-session",
                "--",
                "env",
                "GDK_BACKEND=x11",
                *command,
            ]
        result = normal(
            command, timeout=100, decline_password=mode in ("gui", "launcher")
        )
        logs[mode] = [
            line for line in result.stdout.splitlines() if line.startswith("{")
        ]
    normal(
        [
            "desktop-file-validate",
            "/usr/share/applications/toys.linux.LinuxToys.desktop",
        ]
    )
    normal(
        [
            "appstreamcli",
            "validate",
            "--no-net",
            "/usr/share/metainfo/toys.linux.LinuxToys.metainfo.xml",
        ]
    )
    logs["cancelled_credential_dialogs"] = CANCELLED_DIALOGS.copy()
    return logs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("inspect", "lifecycle", "missing", "interrupt")
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("--upgrade", type=Path)
    parser.add_argument("--probe", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (
        sys.flags.optimize
        or os.geteuid() != 0
        or not Path("/.dockerenv").is_file()
        or host().value != "aarch64"
    ):
        raise SystemExit(
            "Requires unoptimized Python as root in disposable native ARM64 Docker"
        )
    report = {"mode": args.mode, "package": inspect(args.package), "steps": []}
    if args.mode == "inspect":
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        return
    saved = canaries()
    before = system_state()
    if args.mode == "lifecycle":
        if args.upgrade is None or args.probe is None:
            raise SystemExit("Lifecycle requires --upgrade and --probe")
        run(["dpkg", "-i", str(args.package)])
        configured()
        report["application"] = app_checks(args.probe)
        # Preserve actual app-created settings/token/data too, not only markers.
        state = {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path("/home/testuser").rglob("*")
            if p.is_file()
        }
        for operation, command in (
            ("upgrade", ["dpkg", "-i", str(args.upgrade)]),
            ("rollback", ["dpkg", "-i", str(args.package)]),
            ("remove", ["dpkg", "--remove", "linuxtoys"]),
            ("reinstall", ["dpkg", "-i", str(args.upgrade)]),
            ("purge", ["dpkg", "--purge", "linuxtoys"]),
        ):
            run(command)
            preserved(saved)
            for name, sha in state.items():
                assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == sha, name
            if operation in ("upgrade", "rollback", "reinstall"):
                configured()
                normal(["/usr/bin/linuxtoys", "--version"])
            else:
                assert not Path("/usr/bin/linuxtoys").exists()
                assert not Path("/usr/lib/linuxtoys").exists()
            report["steps"].append(operation)
        report["user_files_preserved"] = len(state)
    elif args.mode == "missing":
        run(["dpkg", "--remove", "python3-gi-cairo"])
        result = run(["dpkg", "-i", str(args.package)], good=False)
        assert "python3-gi-cairo" in result.stderr
        preserved(saved)
        report["dependency_failure"] = result.stderr
        candidates = list(
            Path("/var/cache/apt/archives").glob("python3-gi-cairo_*.deb")
        )
        assert len(candidates) == 1, candidates
        run(["dpkg", "-i", str(candidates[0])])
        run(["dpkg", "--configure", "linuxtoys"])
        configured()
        normal(["/usr/bin/linuxtoys", "--version"])
        report["steps"] = [
            "real dependency removal",
            "configure refused",
            "offline dependency reinstall",
            "configure recovered",
        ]
    else:
        process = subprocess.Popen(
            ["dpkg", "--status-fd=1", "--unpack", str(args.package)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        messages = []
        assert process.stdout is not None
        for line in process.stdout:
            messages.append(line.strip())
            if "status: linuxtoys" in line and "half-installed" in line:
                deadline = time.monotonic() + 10
                payload = Path("/usr/lib/linuxtoys")
                while not payload.exists() or not any(
                    p.is_file() for p in payload.rglob("*")
                ):
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError(
                            "dpkg did not expose an interruptible partial payload"
                        )
                    time.sleep(0.001)
                os.kill(process.pid, signal.SIGSTOP)
                stopped, status = os.waitpid(process.pid, os.WUNTRACED)
                assert stopped == process.pid and os.WIFSTOPPED(status)
                report["partial_payload_files_before_kill"] = sum(
                    p.is_file() for p in payload.rglob("*")
                )
                os.kill(process.pid, signal.SIGKILL)
                break
        process.communicate(timeout=20)
        assert process.returncode == -signal.SIGKILL, (process.returncode, messages)
        preserved(saved)
        report["interrupted_exit"] = process.returncode
        report["status_messages"] = messages
        report["audit_after_kill"] = run(["dpkg", "--audit"]).stdout
        run(["dpkg", "-i", str(args.package)])
        configured()
        normal(["/usr/bin/linuxtoys", "--version"])
        report["steps"] = [
            "actual dpkg half-installed state",
            "SIGSTOP and SIGKILL",
            "real dpkg reinstall/configure recovery",
        ]
    preserved(saved)
    assert system_state() == before, (
        "Unexpected system configuration or other-package change"
    )
    report["system_configuration_and_other_packages_preserved"] = True
    report["canaries_preserved"] = True
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
