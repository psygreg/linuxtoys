"""Persistent hidden-PTY runner and session queue for AppStream installations."""

import os
import re
import shutil
from collections import deque
import select
import shlex
import subprocess
import tempfile
import json
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request
import threading
import uuid

from .antenna import antenna
from .gtk_common import GLib
from .library_loader import script_command, script_environment
from .appstream_resolver import resolve_native_appstream_package
from .term_registry import ExecutionRegistry


class AppStreamRunner:
    """Serialize AppStream jobs through one session-lifetime PTY."""

    # PTY captures contain terminal protocol that VTE normally consumes rather
    # than displays. Keep failure dialogs textual without changing the terminal
    # session itself.
    _ANSI_CSI_RE = re.compile(
        rb"\x1b\[[0-?]*[ -/]*[@-~]"
    )
    _ANSI_OSC_RE = re.compile(
        rb"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"
    )
    _ANSI_SINGLE_RE = re.compile(
        rb"\x1b[@-_]"
    )

    # Internal result used when the AUR pre-install inspection blocks a package.
    _AUR_SECURITY_BLOCKED = 126
    _AUR_SECURITY_UNAVAILABLE = 125
    _AUR_SCAN_MAX_FILE = 1024 * 1024

    # High-confidence obfuscation indicators only. This is intentionally not a
    # general "suspicious shell" scanner: ordinary PKGBUILDs legitimately use
    # curl, sed, awk, eval-like configure machinery, etc.
    _AUR_OBFUSCATION_RULES = (
        (
            "encoded data is decoded and executed by a shell",
            re.compile(
                r"""(?ix)
                (?:base64\s+(?:-[A-Za-z]*d|--decode)|openssl\s+(?:enc\s+)?-[A-Za-z0-9_-]*d|
                   xxd\s+-r|(?:gzip|bzip2|xz)\s+-d[c]?|python[23]?\s+-c\s+[^;\n]*(?:b64decode|fromhex))
                [^;\n|]{0,240}\|\s*(?:ba|z|k|da)?sh\b
                """
            ),
        ),
        (
            "decoded or generated content is passed to eval",
            re.compile(
                r"""(?ix)
                \beval\b[^\n]{0,300}
                (?:base64|b64decode|fromhex|xxd\s+-r|openssl\s+(?:enc\s+)?-|
                   printf\s+['"][^'"]*\\x[0-9a-f]{2})
                """
            ),
        ),
        (
            "eval executes command substitution",
            re.compile(r"""(?ix)\beval\s+["']?\s*\$\(\s*[^)\n]{4,}\)"""),
        ),
        (
            "a large encoded payload is embedded in the build script",
            re.compile(r"""(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{600,}={0,2}(?![A-Za-z0-9+/])"""),
        ),
        (
            "a large hexadecimal payload is embedded in the build script",
            re.compile(r"""(?i)(?<![0-9a-f])(?:[0-9a-f]{2}){300,}(?![0-9a-f])"""),
        ),
        (
            "long hexadecimal escape sequence suggests hidden executable text",
            re.compile(r"""(?i)(?:\\x[0-9a-f]{2}){40,}"""),
        ),
    )

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


    def enqueue_local_package(self, package_path, metadata=None):
        """Queue a local package through the same hidden PTY used by AppStream."""
        package_path = os.path.realpath(os.fspath(package_path))
        try:
            stat = os.stat(package_path)
        except OSError:
            return None
        metadata = dict(metadata or {})
        name = str(metadata.get("name") or os.path.basename(package_path))
        payload = {
            "name": name,
            "description": str(metadata.get("description") or ""),
            "icon": str(metadata.get("icon_name") or "package-x-generic"),
            "registry_name": name,
            "is_local_package": True,
            "local_package_path": package_path,
            "local_package_kind": str(metadata.get("kind") or ""),
            "local_package_signature": (
                stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns
            ),
        }
        ids = self.enqueue([payload])
        return ids[0] if ids else None

    def enqueue_extension(self, info):
        """Queue a Flatpak extension install through the persistent PTY."""
        payload = dict(info)
        payload["is_flatpak_extension"] = True
        return self.enqueue([payload])

    def enqueue_extension_removal(self, info, record_id=None):
        """Queue removal of a Flatpak extension without Action Registry state."""
        self._ensure_started()
        ref = str(info.get("flatpak_ref") or "").strip()
        if not ref:
            return None
        with self._condition:
            record = None
            if record_id:
                record = next((item for item in self._records if item["id"] == record_id), None)
            if record is None:
                record = next((item for item in reversed(self._records)
                    if item["status"] == "success"
                    and str(item["info"].get("flatpak_ref") or "").strip() == ref), None)
            if record is None:
                record = {
                    "id": uuid.uuid4().hex, "info": dict(info),
                    "name": info.get("name", ref),
                    "icon": info.get("icon", "application-x-addon-symbolic"),
                    "status": "queued", "exit_code": None,
                }
                self._records.append(record)
            elif record["status"] in ("queued", "running"):
                return None
            else:
                record["status"] = "queued"
                record["exit_code"] = None
            record["action"] = "extension_remove"
            self._jobs.append(record)
            self._condition.notify()
        self._notify_changed()
        return record["id"]

    def status_for_extension_ref(self, flatpak_ref):
        target = str(flatpak_ref or "").strip()
        if not target:
            return None
        with self._condition:
            matches = [r for r in self._records if str(r["info"].get("flatpak_ref") or "").strip() == target]
            if any(r.get("action") == "extension_remove" and r["status"] in ("queued", "running") for r in matches):
                return "removing"
            if any(r["status"] in ("queued", "running") for r in matches):
                return "queued"
            if any(r["status"] == "success" and r.get("action") != "extension_remove" for r in matches):
                return "installed"
        return None

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

    def enqueue_snap_revert(self, app_info):
        """Queue a Snap revision revert through the persistent PTY."""
        snap_name = str(
            app_info.get("snap_name") or app_info.get("package-name") or ""
        ).strip()
        if not snap_name:
            return None

        self._ensure_started()
        with self._condition:
            appstream_id = str(app_info.get("appstream_id", "") or "").casefold()
            if any(
                item["status"] in ("queued", "running")
                and str(item["info"].get("appstream_id", "") or "").casefold() == appstream_id
                for item in self._records
            ):
                return None

            record = {
                "id": uuid.uuid4().hex,
                "info": dict(app_info),
                "name": app_info.get("name", snap_name),
                "icon": app_info.get("icon", "application-x-executable"),
                "status": "queued",
                "exit_code": None,
                "action": "snap_revert",
                "snap_name": snap_name,
            }
            self._records.append(record)
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
            ["script", "-qefc", "stty -echo rows 24 cols 120; exec bash --noprofile --norc", "/dev/null"],
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
                aur_job = str(record["info"].get("appstream_source", "") or "") == "aur"
                failure_output = ""
                if record.get("action") == "remove" and aur_job:
                    exit_code, failure_output = self._run_aur_removal_job(record["remove_info"])
                elif record.get("action") == "remove":
                    exit_code = self._run_removal_job(record["remove_info"])
                elif aur_job:
                    exit_code, failure_output = self._run_aur_job(record["info"])
                elif record.get("action") == "snap_revert":
                    exit_code = self._run_snap_revert(record["info"], record["snap_name"])
                elif record.get("action") == "extension_remove":
                    exit_code = self._run_flatpak_extension(record["info"], remove=True)
                elif record["info"].get("is_flatpak_extension"):
                    exit_code = self._run_flatpak_extension(record["info"], remove=False)
                elif record["info"].get("is_local_package"):
                    exit_code = self._run_local_package_job(record["info"])
                else:
                    exit_code = self._run_job(record["info"])

                with self._condition:
                    record["exit_code"] = exit_code
                    if record.get("action") in ("remove", "extension_remove") and exit_code == 0:
                        # The generated uninstall script has already removed the
                        # reverted registry transaction. Retire its session record.
                        try:
                            self._records.remove(record)
                        except ValueError:
                            pass
                    else:
                        record["status"] = "success" if exit_code == 0 else "failed"
                if aur_job and exit_code == self._AUR_SECURITY_BLOCKED:
                    callback = getattr(self.parent, "_show_aur_security_blocked", None)
                    if callback is not None:
                        GLib.idle_add(
                            callback,
                            record.get("name", "AUR package"),
                            failure_output,
                        )
                elif aur_job and exit_code == self._AUR_SECURITY_UNAVAILABLE:
                    callback = getattr(self.parent, "_show_aur_security_unavailable", None)
                    if callback is not None:
                        GLib.idle_add(
                            callback,
                            record.get("name", "AUR package"),
                            failure_output,
                        )
                elif aur_job and exit_code not in (0, 100) and failure_output:
                    callback = getattr(self.parent, "_show_aur_operation_failure", None)
                    if callback is not None:
                        GLib.idle_add(callback, record.get("name", "AUR package"), failure_output)
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

    def _run_aur_job(self, script_info):
        """Run an AUR install through normal pkg_install/registry machinery and capture PTY output."""
        if self._process is None or self._process.poll() is not None:
            self._close_pty()
            self._spawn_shell()
        registry_name = script_info.get("registry_name", script_info.get("name", "AUR package"))
        package = str(script_info.get("package-name") or "").strip()
        if not package:
            return 2, "Missing AUR package name"

        security_status, security_details = self._verify_aur_package_sources(package)
        if security_status != 0:
            return security_status, security_details

        # Only record/execute the transaction after the AUR repository has passed
        # the pre-install source inspection.
        antenna.add_script_to_history(script_info.get("name", "AUR package"))
        directory = "/tmp/linuxtoys/appstream-overrides"
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, path = tempfile.mkstemp(prefix="aur-install-", suffix=".sh", dir=directory, text=True)
        transmap_path = self._new_transmap()
        self._mark_no_manifest_export(transmap_path)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("#!/usr/bin/env bash\n")
                handle.write(f"pkg_install {shlex.quote(package)}\n")
            os.chmod(path, 0o700)
            env = script_environment(script_info, os.environ.copy())
            env["TRANSMAP_PATH"] = transmap_path
            env.pop("LINUXTOYS_RUNNER_STATE", None)
            exit_code, output = self._dispatch_path(path, env, capture_output=True)
            self._finish_job(registry_name, transmap_path, exit_code)
            return exit_code, output
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    @classmethod
    def _scan_aur_text_for_obfuscation(cls, filename, text):
        findings = []
        for description, pattern in cls._AUR_OBFUSCATION_RULES:
            match = pattern.search(text)
            if match is None:
                continue
            line = text.count("\n", 0, match.start()) + 1
            findings.append(f"{filename}:{line}: {description}")
        return findings

    @staticmethod
    def _github_repo_from_url(value):
        """Return (owner, repo) for a public github.com repository URL."""
        text = str(value or "").strip()
        text = re.sub(r"^(?:git\\+)+", "", text, flags=re.IGNORECASE)
        match = re.match(
            r"^(?:https?://|git://|ssh://git@|git@)?github\\.com(?::|/)"
            r"([^/\\s]+)/([^/#?\\s]+)",
            text,
            flags=re.IGNORECASE,
        )
        if match is None:
            return None
        owner = match.group(1).strip()
        repo = re.sub(r"\\.git$", "", match.group(2).strip(), flags=re.IGNORECASE)
        if not owner or not repo:
            return None
        return owner.casefold(), repo.casefold()

    @classmethod
    def _github_repositories_from_pkgbuild(cls, text):
        """Extract GitHub repository identities without evaluating the PKGBUILD."""
        repos = set()
        pattern = re.compile(
            r"(?ix)(?:(?:git\\+)?https?://github\\.com/|"
            r"(?:git\\+)?git://github\\.com/|"
            r"(?:git\\+)?ssh://git@github\\.com/|git@github\\.com:)"
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
        )
        for match in pattern.finditer(text):
            repo = cls._github_repo_from_url(match.group(0))
            if repo is not None:
                repos.add(repo)
        return repos

    @staticmethod
    def _github_api_repository(owner, repo):
        """Fetch public GitHub repository metadata without credentials."""
        owner = urllib.parse.quote(owner, safe="")
        repo = urllib.parse.quote(repo, safe="")
        request = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "LinuxToys-AUR-security-check",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError,
                TimeoutError, OSError, ValueError):
            # Repository reputation is supplemental. Failure to obtain GitHub
            # metadata must not override the local AUR source inspection.
            return None
        return payload if isinstance(payload, dict) else None

    @classmethod
    def _check_github_source_provenance(cls, pkgbuild_text):
        """Return high-confidence GitHub source/upstream inconsistencies.

        Fork status alone is harmless. A fork is blocked only when its own
        parent/source repository is also named by the PKGBUILD, showing that
        the package declares one upstream while fetching executable source
        from another repository in that same GitHub fork network.
        """
        repositories = cls._github_repositories_from_pkgbuild(pkgbuild_text)
        if not repositories:
            return []

        findings = []
        metadata = {}
        for identity in sorted(repositories):
            data = cls._github_api_repository(*identity)
            if data is None:
                continue
            metadata[identity] = data
            if bool(data.get("disabled")):
                findings.append(
                    f"GitHub repository {identity[0]}/{identity[1]} is disabled"
                )

            # Popularity/activity metadata is deliberately weak evidence. Never
            # block on one or two of these characteristics: small, new and niche
            # upstreams are perfectly legitimate. Require at least three distinct
            # signals before treating the repository as suspicious.
            weak_signals = []

            created_at = str(data.get("created_at") or "").strip()
            if created_at:
                try:
                    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    age_days = max(
                        0,
                        (datetime.now(timezone.utc) - created.astimezone(timezone.utc)).days,
                    )
                    if age_days < 30:
                        weak_signals.append(f"repository is only {age_days} days old")
                except (TypeError, ValueError):
                    pass

            try:
                if int(data.get("stargazers_count") or 0) == 0:
                    weak_signals.append("repository has no stars")
            except (TypeError, ValueError):
                pass

            try:
                if int(data.get("forks_count") or 0) == 0:
                    weak_signals.append("repository has no forks")
            except (TypeError, ValueError):
                pass

            # subscribers_count is GitHub's watcher count. watchers_count mirrors
            # stargazers_count and must not be counted as a separate signal.
            try:
                if int(data.get("subscribers_count") or 0) == 0:
                    weak_signals.append("repository has no watchers")
            except (TypeError, ValueError):
                pass

            try:
                # GitHub reports repository size in KiB. A tiny repository is only
                # corroborating evidence and is never sufficient by itself.
                if int(data.get("size") or 0) < 64:
                    weak_signals.append("repository is unusually small")
            except (TypeError, ValueError):
                pass

            if len(weak_signals) >= 3:
                findings.append(
                    f"GitHub repository {identity[0]}/{identity[1]} has multiple "
                    f"low-reputation signals: " + "; ".join(weak_signals)
                )

        for (owner, repo), data in metadata.items():
            if not bool(data.get("fork")):
                continue
            ancestors = set()
            for key in ("parent", "source"):
                ancestor = data.get(key)
                if not isinstance(ancestor, dict):
                    continue
                full_name = str(ancestor.get("full_name") or "").strip()
                if "/" not in full_name:
                    continue
                ancestor_owner, ancestor_repo = full_name.split("/", 1)
                ancestors.add((ancestor_owner.casefold(), ancestor_repo.casefold()))

            matched = ancestors & repositories
            if matched:
                upstream = ", ".join(
                    f"{a}/{r}" for a, r in sorted(matched)
                )
                findings.append(
                    f"GitHub source {owner}/{repo} is a fork while the PKGBUILD "
                    f"also identifies its upstream repository as {upstream}"
                )
        return findings

    @classmethod
    def _verify_aur_package_sources(cls, package):
        """Fetch and statically inspect AUR-controlled install sources.

        Nothing from the repository is sourced or executed. We inspect PKGBUILD
        plus every regular *.install file shipped in the AUR Git repository.
        """
        git = shutil.which("git")
        if not git:
            return (
                cls._AUR_SECURITY_UNAVAILABLE,
                "Git is required to verify the AUR package sources.",
            )

        safe_package = str(package or "").strip()
        if not safe_package or not re.fullmatch(r"[A-Za-z0-9@._+:-]+", safe_package):
            return (
                cls._AUR_SECURITY_UNAVAILABLE,
                "The AUR package name could not be safely verified.",
            )

        temp_root = tempfile.mkdtemp(prefix="linuxtoys-aur-verify-")
        repo_dir = os.path.join(temp_root, "repo")
        try:
            repository = f"https://aur.archlinux.org/{safe_package}.git"
            try:
                result = subprocess.run(
                    [
                        git,
                        "-c", "protocol.file.allow=never",
                        "clone",
                        "--quiet",
                        "--depth", "1",
                        "--no-tags",
                        "--config", "core.hooksPath=/dev/null",
                        repository,
                        repo_dir,
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=45,
                    check=False,
                    env={
                        **os.environ,
                        "GIT_TERMINAL_PROMPT": "0",
                        "GIT_CONFIG_NOSYSTEM": "1",
                    },
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return (
                    cls._AUR_SECURITY_UNAVAILABLE,
                    f"Could not fetch the AUR repository for verification: {exc}",
                )

            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip()
                if len(detail) > 1000:
                    detail = detail[-1000:]
                return (
                    cls._AUR_SECURITY_UNAVAILABLE,
                    "Could not fetch the AUR repository for verification."
                    + (f"\n\n{detail}" if detail else ""),
                )

            candidates = []
            pkgbuild = os.path.join(repo_dir, "PKGBUILD")
            if os.path.isfile(pkgbuild) and not os.path.islink(pkgbuild):
                candidates.append(pkgbuild)

            # .install files are package-manager hooks executed around package
            # installation/removal. Scan all regular ones tracked in the AUR repo,
            # which also covers PKGBUILDs that choose the hook indirectly.
            for root, dirs, files in os.walk(repo_dir, followlinks=False):
                dirs[:] = [d for d in dirs if d != ".git"]
                for filename in files:
                    if not filename.endswith(".install"):
                        continue
                    path = os.path.join(root, filename)
                    if os.path.isfile(path) and not os.path.islink(path):
                        candidates.append(path)

            if not candidates or pkgbuild not in candidates:
                return (
                    cls._AUR_SECURITY_UNAVAILABLE,
                    "The AUR repository did not contain a readable PKGBUILD.",
                )

            findings = []
            pkgbuild_source = None
            for path in candidates:
                try:
                    size = os.path.getsize(path)
                    if size > cls._AUR_SCAN_MAX_FILE:
                        relative = os.path.relpath(path, repo_dir)
                        findings.append(
                            f"{relative}: file is too large to safely inspect "
                            f"({size} bytes)"
                        )
                        continue
                    with open(path, "r", encoding="utf-8", errors="replace") as handle:
                        source = handle.read(cls._AUR_SCAN_MAX_FILE + 1)
                except OSError as exc:
                    return (
                        cls._AUR_SECURITY_UNAVAILABLE,
                        f"Could not read an AUR source file for verification: {exc}",
                    )

                relative = os.path.relpath(path, repo_dir)
                if path == pkgbuild:
                    pkgbuild_source = source
                findings.extend(
                    cls._scan_aur_text_for_obfuscation(relative, source)
                )


            if pkgbuild_source is not None:
                findings.extend(
                    cls._check_github_source_provenance(pkgbuild_source)
                )
            if findings:
                return (
                    cls._AUR_SECURITY_BLOCKED,
                    "\n".join(findings[:20]),
                )
            return 0, ""
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def _run_aur_removal_job(self, script_info):
        """Run an AUR registry revert and retain terminal output when it fails."""
        if self._process is None or self._process.poll() is not None:
            self._close_pty()
            self._spawn_shell()
        transmap_path = self._new_transmap()
        env = script_environment(script_info, os.environ.copy())
        env["TRANSMAP_PATH"] = transmap_path
        env.pop("LINUXTOYS_RUNNER_STATE", None)
        try:
            exit_code, output = self._dispatch_path(script_info.get("path", "true"), env, capture_output=True)
            ExecutionRegistry._cleanup_tmp_noram_dirs(transmap_path)
            self._remove_transmap(transmap_path)
            return exit_code, output
        finally:
            cleanup_path = script_info.get("cleanup_path")
            if cleanup_path:
                try:
                    os.remove(cleanup_path)
                except OSError:
                    pass

    def _run_snap_revert(self, app_info, snap_name):
        """Execute pkg_snap_revert through the normal LinuxToys script wrapper."""
        if self._process is None or self._process.poll() is not None:
            self._close_pty()
            self._spawn_shell()

        directory = "/tmp/linuxtoys/appstream-overrides"
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, path = tempfile.mkstemp(
            prefix="snap-revert-", suffix=".sh", dir=directory, text=True
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("#!/usr/bin/env bash\n")
                handle.write(f"pkg_snap_revert {shlex.quote(snap_name)}\n")
            os.chmod(path, 0o700)

            env = script_environment(app_info, os.environ.copy())
            env.pop("LINUXTOYS_RUNNER_STATE", None)
            return self._dispatch_path(path, env)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def _flatpak_scope_args(self, info):
        scope = str(info.get("flatpak_scope") or "").strip()
        installation = str(info.get("flatpak_installation") or "").strip()
        if scope == "user":
            return ["--user"]
        if installation and installation != "default":
            return [f"--installation={installation}"]
        return ["--system"]

    def _run_flatpak_extension(self, info, remove=False):
        if self._process is None or self._process.poll() is not None:
            self._close_pty()
            self._spawn_shell()
        ref = str(info.get("flatpak_ref") or "").strip()
        if not ref:
            return 2
        argv = ["flatpak", *self._flatpak_scope_args(info)]
        if remove:
            argv += ["uninstall", "-y", ref]
        else:
            remote = str(info.get("flatpak_remote") or "flathub").strip() or "flathub"
            argv += ["install", "-y", remote, ref]
        return self._dispatch_argv(argv)

    def _dispatch_argv(self, argv):
        token = uuid.uuid4().hex
        marker = f"__LINUXTOYS_APPSTREAM_DONE_{token}__"
        command = " ".join(shlex.quote(str(part)) for part in argv)
        mid = len(marker) // 2
        dispatch = (
            f"_lt_marker={shlex.quote(marker[:mid])};"
            f"_lt_marker=\"$_lt_marker\"{shlex.quote(marker[mid:])}; "
            f"{command}; _lt_status=$?; "
            f"printf '\\n%s:%s\\n' \"$_lt_marker\" \"$_lt_status\"\n"
        )
        self._process.stdin.write(dispatch.encode("utf-8"))
        self._process.stdin.flush()
        return self._read_until_marker(marker)

    def _run_local_package_job(self, script_info):
        package_path = os.path.realpath(str(script_info.get("local_package_path") or ""))
        expected = tuple(script_info.get("local_package_signature") or ())
        try:
            stat = os.stat(package_path)
            current = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
        except OSError:
            return 1
        if expected and current != expected:
            print(f"Local package changed before installation: {package_path}", file=os.sys.stderr)
            return 1

        kind = str(script_info.get("local_package_kind") or "")
        function = "pkg_appimage" if kind == "appimage" else "pkg_fromfile"
        directory = "/tmp/linuxtoys"
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, script_path = tempfile.mkstemp(prefix="local-package-", suffix=".sh", dir=directory, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("#!/usr/bin/env bash\n")
                handle.write(f"{function} {shlex.quote(package_path)}\n")
            os.chmod(script_path, 0o700)
            payload = dict(script_info)
            payload["path"] = script_path
            return self._run_job(payload)
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass

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
        if script_info.get("is_local_package"):
            self._mark_no_manifest_export(transmap_path)
        env = script_environment(script_info, os.environ.copy())
        env["TRANSMAP_PATH"] = transmap_path
        env.pop("LINUXTOYS_RUNNER_STATE", None)

        # Resolve misleading AppStream native package ownership before any
        # background script starts.  The generated AppStream script consumes
        # this value instead of asking pkg_install to reinterpret its argument.
        env.pop("LINUXTOYS_APPSTREAM_PACKAGE", None)
        if script_info.get("appstream_source") == "native":
            package_value = script_info.get("package-name")
            if isinstance(package_value, str):
                packages = [package_value.strip()] if package_value.strip() else []
            elif isinstance(package_value, (list, tuple)):
                packages = [str(value).strip() for value in package_value if str(value).strip()]
            else:
                packages = []

            # A single AppStream package is the only case where semantic
            # promotion is unambiguous. Multi-package entries keep their
            # materialized pkg_install commands unchanged.
            if len(packages) == 1:
                original_package = packages[0]
                resolved_package = resolve_native_appstream_package(
                    original_package,
                    component_id=script_info.get("appstream_id"),
                    desktop_id=script_info.get("appstream_launchable"),
                    name=script_info.get("name"),
                )
                env["LINUXTOYS_APPSTREAM_PACKAGE"] = resolved_package
                if resolved_package != original_package:
                    print(
                        f"Resolved AppStream package '{original_package}' to "
                        f"'{resolved_package}'.",
                        file=os.sys.stderr,
                    )

        override_paths = []
        try:
            overrides = script_info.get("appstream_overrides")
            if not isinstance(overrides, dict):
                overrides = {}

            pre_path = self._new_override_script(overrides, "pre")
            if pre_path:
                override_paths.append(pre_path)
                exit_code = self._dispatch_path(pre_path, env)
                if exit_code != 0:
                    self._finish_job(registry_name, transmap_path, exit_code)
                    return exit_code

            dependency_path = self._new_dependency_script(
                script_info.get("appstream_dependencies")
            )
            if dependency_path:
                override_paths.append(dependency_path)
                exit_code = self._dispatch_path(dependency_path, env)
                if exit_code != 0:
                    self._finish_job(registry_name, transmap_path, exit_code)
                    return exit_code

            # Keep the ordinary AppStream installation completely unchanged.
            # Overlay hooks/dependencies are separate runner phases around it rather
            # than being folded into the generated AppStream installation script.
            exit_code = self._dispatch_path(script_info.get("path", "true"), env)
            if exit_code != 0:
                self._finish_job(registry_name, transmap_path, exit_code)
                return exit_code

            # Permission overrides only make sense for the Flatpak source. Native
            # alternatives still receive pre/post hooks but skip this phase.
            if script_info.get("appstream_source") == "flatpak":
                flatpak_path = self._new_override_script(overrides, "flatpak")
                if flatpak_path:
                    override_paths.append(flatpak_path)
                    exit_code = self._dispatch_path(flatpak_path, env)
                    if exit_code != 0:
                        self._finish_job(registry_name, transmap_path, exit_code)
                        return exit_code

            post_path = self._new_override_script(overrides, "post")
            if post_path:
                override_paths.append(post_path)
                exit_code = self._dispatch_path(post_path, env)
                if exit_code != 0:
                    self._finish_job(registry_name, transmap_path, exit_code)
                    return exit_code

            self._finish_job(registry_name, transmap_path, 0)
            return 0
        finally:
            for path in override_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _dispatch_path(self, path, env, capture_output=False):
        """Execute one LinuxToys script phase through the persistent AppStream PTY."""
        argv = script_command(path, env["SCRIPT_DIR"])
        token = uuid.uuid4().hex
        marker = f"__LINUXTOYS_APPSTREAM_DONE_{token}__"
        assignments = " ".join(
            f"{key}={shlex.quote(str(value))}" for key, value in env.items()
        )
        command = " ".join(shlex.quote(part) for part in argv)
        marker_mid = len(marker) // 2
        marker_left = marker[:marker_mid]
        marker_right = marker[marker_mid:]

        start_marker = f"__LINUXTOYS_APPSTREAM_START_{token}__"
        dispatch = (
            f"_lt_marker={shlex.quote(marker_left)};"
            f"_lt_marker=\"$_lt_marker\"{shlex.quote(marker_right)}; "
            + (f"printf '%s\\n' {shlex.quote(start_marker)}; " if capture_output else "")
            + f"env {assignments} {command}; "
            f"_lt_status=$?; "
            f"printf '\\n%s:%s\\n' \"$_lt_marker\" \"$_lt_status\"\n"
        )
        self._process.stdin.write(dispatch.encode("utf-8"))
        self._process.stdin.flush()
        return self._read_until_marker(
            marker,
            capture_output=capture_output,
            start_marker=start_marker if capture_output else None,
        )

    @staticmethod
    def _new_dependency_script(dependencies):
        """Materialize reviewed AppStream dependencies for LinuxToys helpers."""
        if not isinstance(dependencies, list):
            return None

        lines = []
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            dependency_type = dependency.get("type")
            packages = dependency.get("packages")
            if not isinstance(packages, list):
                continue
            for package in packages:
                package = str(package or "").strip()
                if not package:
                    continue
                if dependency_type == "native":
                    lines.append(f"pkg_install {shlex.quote(package)}")
                elif dependency_type == "flathub":
                    lines.append(f"pkg_flat {shlex.quote(package)}")
                elif dependency_type == "snap":
                    lines.append(f"pkg_snap {shlex.quote(package)}")

        if not lines:
            return None

        directory = "/tmp/linuxtoys/appstream-overrides"
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, path = tempfile.mkstemp(
            prefix="dependencies-", suffix=".sh", dir=directory, text=True
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("#!/usr/bin/env bash\n")
                handle.write("\n".join(lines))
                handle.write("\n")
            os.chmod(path, 0o700)
        except Exception:
            try:
                os.remove(path)
            except OSError:
                pass
            raise
        return path

    @staticmethod
    def _new_override_script(overrides, phase):
        """Materialize one reviewed AppStream overlay phase for LinuxToys helpers."""
        if not isinstance(overrides, dict):
            return None

        lines = []
        if phase in ("pre", "post"):
            value = overrides.get(phase)
            if isinstance(value, str) and value.strip():
                lines.append(value.strip())
            elif isinstance(value, dict):
                script = str(value.get("script", "") or "").strip()
                if script:
                    lines.append(f"run_list_hook {shlex.quote(script)}")
        elif phase == "flatpak":
            values = overrides.get("flatpak")
            if isinstance(values, list):
                for override in values:
                    if not isinstance(override, dict):
                        continue
                    lines.append(
                        "flatpak_override "
                        f"{shlex.quote(str(override.get('scope', '')).strip())} "
                        f"{shlex.quote(str(override.get('type', '')).strip())} "
                        f"{shlex.quote(str(override.get('setting', '')).strip())} "
                        f"{shlex.quote(str(override.get('target', '')).strip())}"
                    )

        if not lines:
            return None

        directory = "/tmp/linuxtoys/appstream-overrides"
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, path = tempfile.mkstemp(
            prefix=f"{phase}-", suffix=".sh", dir=directory, text=True
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("#!/usr/bin/env bash\n")
                handle.write("\n".join(lines))
                handle.write("\n")
            os.chmod(path, 0o700)
        except Exception:
            try:
                os.remove(path)
            except OSError:
                pass
            raise
        return path

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

    @classmethod
    def _clean_captured_pty_output(cls, raw):
        """Convert a bounded PTY transcript into plain text for error dialogs."""
        # OSC must be removed before CSI/single-character escapes because OSC
        # payloads can themselves contain bytes that resemble other sequences.
        raw = cls._ANSI_OSC_RE.sub(b"", raw)
        raw = cls._ANSI_CSI_RE.sub(b"", raw)
        raw = cls._ANSI_SINGLE_RE.sub(b"", raw)

        # Model the two terminal editing controls that commonly leak into command
        # output. CR returns to column zero; for a textual log, normalizing it to
        # LF is more useful than preserving an overwrite operation.
        raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        while b"\x08" in raw:
            raw = re.sub(rb"[^\n]\x08", b"", raw)
            raw = raw.replace(b"\x08", b"")

        text = raw.decode("utf-8", errors="replace")
        lines = [line.rstrip() for line in text.splitlines()]

        # Collapse PTY-induced vertical whitespace without disturbing normal
        # multiline diagnostics.
        cleaned = []
        blank = False
        for line in lines:
            if not line.strip():
                if cleaned and not blank:
                    cleaned.append("")
                blank = True
                continue
            cleaned.append(line)
            blank = False
        return "\n".join(cleaned).strip()

    def _read_until_marker(self, marker, capture_output=False, start_marker=None):
        marker_bytes = (marker + ":").encode("utf-8")
        start_bytes = start_marker.encode("utf-8") if start_marker else None
        pending = b""
        captured = bytearray()
        capture_started = not bool(start_bytes)
        capture_limit = 512 * 1024
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

            if capture_output:
                if capture_started:
                    captured.extend(chunk)
                elif start_bytes in pending:
                    _before_start, after_start = pending.split(start_bytes, 1)
                    # Drop the marker's own line ending. Everything before it is
                    # stale shell/prompt/control traffic from the persistent PTY.
                    after_start = after_start.lstrip(b"\r\n")
                    captured.extend(after_start)
                    capture_started = True

                if len(captured) > capture_limit:
                    del captured[:len(captured) - capture_limit]

            if marker_bytes not in pending:
                pending = pending[-max(4096, len(marker_bytes) * 2, len(start_bytes or b"") * 2):]
                continue

            _before, after = pending.split(marker_bytes, 1)
            line = after.splitlines()[0].strip()
            try:
                status = int(line)
            except ValueError as exc:
                raise RuntimeError("invalid AppStream runner completion status") from exc
            if not capture_output:
                return status

            raw = bytes(captured)
            marker_at = raw.rfind(marker_bytes)
            if marker_at >= 0:
                raw = raw[:marker_at]
            return status, self._clean_captured_pty_output(raw)
        return (100, "") if capture_output else 100

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
    def _mark_no_manifest_export(path):
        """Mark a registry transaction as intentionally non-portable."""
        try:
            with open(path, "a", encoding="utf-8") as transmap:
                transmap.write("manifest-export skip\n")
        except OSError:
            pass

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
