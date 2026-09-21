"""Persistent hidden-PTY runner and session queue for AppStream installations."""

import os
from collections import deque
import select
import shlex
import subprocess
import tempfile
import threading
import uuid

from .antenna import antenna
from .gtk_common import GLib
from .library_loader import script_command, script_environment
from .term_registry import ExecutionRegistry


class AppStreamRunner:
    """Serialize AppStream jobs through one session-lifetime PTY."""

    def __init__(self, parent):
        self.parent = parent
        self._jobs = deque()
        self._records = []
        self._condition = threading.Condition()
        self._thread = None
        self._process = None
        self._master_fd = None
        self._stopping = threading.Event()
        self._start_lock = threading.Lock()

    def enqueue(self, scripts):
        if not scripts:
            return []
        self._ensure_started()
        added = []
        with self._condition:
            for script_info in scripts:
                record = {
                    "id": uuid.uuid4().hex,
                    "info": dict(script_info),
                    "name": script_info.get("name", "Unknown application"),
                    "icon": script_info.get("icon", "application-x-executable"),
                    "status": "queued",
                    "exit_code": None,
                }
                self._records.append(record)
                self._jobs.append(record)
                added.append(record["id"])
            self._condition.notify()
        self._notify_changed()
        return added

    def enqueue_removal(self, app_info, remove_info, record_id=None):
        """Queue an AppStream uninstall through the persistent PTY."""
        self._ensure_started()
        with self._condition:
            record = None
            if record_id:
                record = next(
                    (item for item in self._records if item["id"] == record_id),
                    None,
                )

            if record is None:
                appstream_id = str(app_info.get("appstream_id", "") or "").casefold()
                record = next(
                    (
                        item for item in reversed(self._records)
                        if item["status"] == "success"
                        and str(
                            item["info"].get("appstream_id", "") or ""
                        ).casefold() == appstream_id
                    ),
                    None,
                )

            if record is None:
                record = {
                    "id": uuid.uuid4().hex,
                    "info": dict(app_info),
                    "name": app_info.get("name", "Unknown application"),
                    "icon": app_info.get("icon", "application-x-executable"),
                    "status": "queued",
                    "exit_code": None,
                }
                self._records.append(record)
            elif record["status"] in ("queued", "running"):
                return None
            else:
                record["status"] = "queued"
                record["exit_code"] = None

            record["action"] = "remove"
            record["remove_info"] = dict(remove_info)
            self._jobs.append(record)
            self._condition.notify()

        self._notify_changed()
        return record["id"]

    def snapshot(self):
        """Return newest-first copies suitable for the GTK queue view."""
        with self._condition:
            return [
                {**record, "info": dict(record["info"])}
                for record in reversed(self._records)
            ]

    def cancel(self, job_id):
        """Cancel a job only while it is still waiting to start."""
        changed = False
        with self._condition:
            for record in self._records:
                if record["id"] != job_id or record["status"] != "queued":
                    continue
                record["status"] = "cancelled"
                try:
                    self._jobs.remove(record)
                except ValueError:
                    # The worker may have taken it between the state check and here;
                    # in that case _run_record's transition wins.
                    if record["status"] == "cancelled":
                        record["status"] = "queued"
                    return False
                changed = True
                break
        if changed:
            self._notify_changed()
        return changed

    def has_started(self):
        return self._thread is not None

    def has_pending_operations(self):
        """Return True while an AppStream operation is queued or running."""
        with self._condition:
            return any(
                record["status"] in ("queued", "running")
                for record in self._records
            )

    def remove_record(self, record_id):
        """Remove one completed record from this session's queue/history."""
        changed = False
        with self._condition:
            for record in list(self._records):
                if record["id"] != record_id:
                    continue
                # Never remove an operation that is still pending or executing.
                if record["status"] in ("queued", "running"):
                    return False
                self._records.remove(record)
                changed = True
                break
        if changed:
            self._notify_changed()
        return changed

    def status_for_appstream_id(self, appstream_id):
        """Return the current-session state for an AppStream component."""
        target = str(appstream_id or "").strip().casefold()
        if not target:
            return None
        with self._condition:
            matches = [
                record for record in self._records
                if str(record["info"].get("appstream_id", "") or "").strip().casefold() == target
            ]
            if any(
                record.get("action") == "remove"
                and record["status"] in ("queued", "running")
                for record in matches
            ):
                return "removing"
            if any(record["status"] in ("queued", "running") for record in matches):
                return "queued"
            if any(record["status"] == "success" for record in matches):
                return "installed"
            # A failed removal leaves the original registry transaction intact.
            if any(
                record.get("action") == "remove" and record["status"] == "failed"
                for record in matches
            ):
                return "installed"
        return None

    def shutdown(self):
        self._stopping.set()
        with self._condition:
            self._condition.notify_all()

        process = self._process
        if process is not None and process.poll() is None:
            try:
                process.stdin.write(b"exit\n")
                process.stdin.flush()
            except (AttributeError, BrokenPipeError, OSError):
                pass
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.terminate()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._close_pty()

    def _ensure_started(self):
        with self._start_lock:
            if self._thread and self._thread.is_alive():
                return
            self._stopping.clear()
            self._spawn_shell()
            self._thread = threading.Thread(
                target=self._worker,
                name="linuxtoys-appstream-runner",
                daemon=True,
            )
            self._thread.start()

    def _spawn_shell(self):
        env = os.environ.copy()
        env["HISTFILE"] = "/dev/null"

        self._process = subprocess.Popen(
            ["script", "-qefc", "stty -echo; exec bash --noprofile --norc", "/dev/null"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            bufsize=0,
        )
        self._master_fd = self._process.stdout.fileno()

        self._process.stdin.write(b"set +o history\n")
        self._process.stdin.flush()

    def _worker(self):
        while not self._stopping.is_set():
            with self._condition:
                while not self._jobs and not self._stopping.is_set():
                    self._condition.wait(timeout=0.5)
                if self._stopping.is_set():
                    break
                record = self._jobs.popleft()
                if record["status"] != "queued":
                    continue
                # This transition happens while holding the same lock used by
                # cancel(), so a job can never be cancelled after it has started.
                record["status"] = "running"
            self._notify_changed()

            exit_code = None
            try:
                # Keep the proven installation path completely unchanged. Removal
                # is additive and has its own execution path so it cannot alter
                # installation registry/transmap behavior.
                if record.get("action") == "remove":
                    exit_code = self._run_removal_job(record["remove_info"])
                else:
                    exit_code = self._run_job(record["info"])

                with self._condition:
                    record["exit_code"] = exit_code
                    if record.get("action") == "remove" and exit_code == 0:
                        # The generated uninstall script has already removed the
                        # reverted registry transaction. Retire its session record.
                        try:
                            self._records.remove(record)
                        except ValueError:
                            pass
                    else:
                        record["status"] = "success" if exit_code == 0 else "failed"
            except Exception as exc:
                with self._condition:
                    record["exit_code"] = -1
                    record["status"] = "failed"
                print(f"AppStream background runner failed: {exc}", file=os.sys.stderr)
            self._notify_changed()
            if exit_code == 0:
                refresh = getattr(self.parent, "_refresh_installed_packages_async", None)
                if refresh is not None:
                    GLib.idle_add(refresh, True)

    def _run_job(self, script_info):
        if self._process is None or self._process.poll() is not None:
            self._close_pty()
            self._spawn_shell()

        script_name = script_info.get("name", "unknown")
        registry_name = script_info.get("registry_name", script_name)
        antenna.add_script_to_history(script_name)

        if script_info.get("reboot") == "yes":
            self.parent.reboot_required = True

        transmap_path = self._new_transmap()
        env = script_environment(script_info, os.environ.copy())
        env["TRANSMAP_PATH"] = transmap_path
        env.pop("LINUXTOYS_RUNNER_STATE", None)

        argv = script_command(script_info.get("path", "true"), env["SCRIPT_DIR"])
        token = uuid.uuid4().hex
        marker = f"__LINUXTOYS_APPSTREAM_DONE_{token}__"
        assignments = " ".join(f"{key}={shlex.quote(str(value))}" for key, value in env.items())
        command = " ".join(shlex.quote(part) for part in argv)
        marker_mid = len(marker) // 2
        marker_left = marker[:marker_mid]
        marker_right = marker[marker_mid:]

        dispatch = (
            f"_lt_marker={shlex.quote(marker_left)};"
            f"_lt_marker=\"$_lt_marker\"{shlex.quote(marker_right)}; "
            f"env {assignments} {command}; "
            f"_lt_status=$?; "
            f"printf '\\n%s:%s\\n' \"$_lt_marker\" \"$_lt_status\"\n"
        )

        self._process.stdin.write(dispatch.encode("utf-8"))
        self._process.stdin.flush()
        exit_code = self._read_until_marker(marker)
        self._finish_job(registry_name, transmap_path, exit_code)
        return exit_code

    def _run_removal_job(self, script_info):
        """Execute a generated registry-revert script without recording a new transaction."""
        if self._process is None or self._process.poll() is not None:
            self._close_pty()
            self._spawn_shell()

        transmap_path = self._new_transmap()
        env = script_environment(script_info, os.environ.copy())
        env["TRANSMAP_PATH"] = transmap_path
        env.pop("LINUXTOYS_RUNNER_STATE", None)

        argv = script_command(script_info.get("path", "true"), env["SCRIPT_DIR"])
        token = uuid.uuid4().hex
        marker = f"__LINUXTOYS_APPSTREAM_DONE_{token}__"
        assignments = " ".join(
            f"{key}={shlex.quote(str(value))}" for key, value in env.items()
        )
        command = " ".join(shlex.quote(part) for part in argv)
        marker_mid = len(marker) // 2
        marker_left = marker[:marker_mid]
        marker_right = marker[marker_mid:]

        dispatch = (
            f"_lt_marker={shlex.quote(marker_left)};"
            f"_lt_marker=\"$_lt_marker\"{shlex.quote(marker_right)}; "
            f"env {assignments} {command}; "
            f"_lt_status=$?; "
            f"printf '\\n%s:%s\\n' \"$_lt_marker\" \"$_lt_status\"\n"
        )

        try:
            self._process.stdin.write(dispatch.encode("utf-8"))
            self._process.stdin.flush()
            exit_code = self._read_until_marker(marker)

            # The generated uninstall script owns the registry mutation. Its
            # transmap is only execution scratch and must never become a new
            # Action Registry transaction.
            ExecutionRegistry._cleanup_tmp_noram_dirs(transmap_path)
            self._remove_transmap(transmap_path)
            return exit_code
        finally:
            cleanup_path = script_info.get("cleanup_path")
            if cleanup_path:
                try:
                    os.remove(cleanup_path)
                except OSError:
                    pass

    def _read_until_marker(self, marker):
        marker_bytes = (marker + ":").encode("utf-8")
        pending = b""
        while not self._stopping.is_set():
            if self._process is None or self._process.poll() is not None:
                raise RuntimeError("persistent AppStream PTY shell exited unexpectedly")
            readable, _, _ = select.select([self._master_fd], [], [], 0.5)
            if not readable:
                continue
            chunk = os.read(self._master_fd, 4096)
            if not chunk:
                raise RuntimeError("persistent AppStream PTY closed unexpectedly")
            pending += chunk
            if marker_bytes not in pending:
                pending = pending[-max(4096, len(marker_bytes) * 2):]
                continue
            line = pending.split(marker_bytes, 1)[1].splitlines()[0].strip()
            try:
                return int(line)
            except ValueError as exc:
                raise RuntimeError("invalid AppStream runner completion status") from exc
        return 100

    def _notify_changed(self):
        callback = getattr(self.parent, "_on_appstream_queue_changed", None)
        if callback is not None:
            GLib.idle_add(callback)

    @staticmethod
    def _new_transmap():
        directory = "/tmp/linuxtoys"
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, path = tempfile.mkstemp(prefix="appstream-transmap-", dir=directory, text=True)
        os.close(fd)
        os.chmod(path, 0o600)
        return path

    @staticmethod
    def _remove_transmap(path):
        try:
            os.remove(path)
        except OSError:
            pass

    @staticmethod
    def _finish_job(registry_name, transmap_path, exit_code):
        if exit_code == 0:
            ExecutionRegistry._save_to_registry(registry_name, transmap_path)
            ExecutionRegistry._cleanup_tmp_noram_dirs(transmap_path)
            AppStreamRunner._remove_transmap(transmap_path)
            return
        if exit_code == 100:
            ExecutionRegistry._cleanup_tmp_noram_dirs(transmap_path)
            AppStreamRunner._remove_transmap(transmap_path)
            return
        ExecutionRegistry._save_to_registry(registry_name, transmap_path)
        print(f"AppStream installation '{registry_name}' exited with status {exit_code}", file=os.sys.stderr)

    def _close_pty(self):
        process = self._process
        if process is not None:
            for stream in (process.stdin, process.stdout):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass
        self._process = None
        self._master_fd = None
