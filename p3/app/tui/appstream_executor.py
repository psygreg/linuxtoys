"""Build the shell scripts and commands that run AppStream installs.

TUI port of the job logic of the GUI ``AppStreamRunner``, without GTK.
Nothing here runs an install: the functions write temporary ``.sh``
scripts under ``_OVERRIDES_DIR`` or return argv lists for the runner
to execute. The module also provides a static security check for AUR
package sources.

Constants:
    AUR_SECURITY_OK: Status returned when no suspicious pattern was
        found.
    AUR_SECURITY_UNAVAILABLE: Status returned when the check could not
        run (missing git, network failure, missing or unreadable
        PKGBUILD).
    AUR_SECURITY_BLOCKED: Status returned when the sources look
        obfuscated.
"""

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from app import repo_parser
from app.appstream_resolver import resolve_native_appstream_package
from app.library_loader import _appstream_phase_lines

_OVERRIDES_DIR = "/tmp/linuxtoys/appstream-overrides"

AUR_SECURITY_OK = 0
AUR_SECURITY_UNAVAILABLE = 125
AUR_SECURITY_BLOCKED = 126
_AUR_SCAN_MAX_FILE = 1024 * 1024
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
        re.compile(
            r"""(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{600,}={0,2}(?![A-Za-z0-9+/])"""
        ),
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


def _write_temp_script(lines: list[str], prefix: str) -> str:
    """Write shell lines to a private, executable temporary script.

    Creates ``_OVERRIDES_DIR`` (mode 0700) if needed, then writes a
    bash shebang followed by ``lines`` joined with newlines. The file
    is ``chmod`` 0700. The caller owns the file and must delete it.

    Args:
        lines: Shell lines to write after the shebang.
        prefix: Filename prefix for the temporary file.

    Returns:
        Absolute path of the created script.
    """
    os.makedirs(_OVERRIDES_DIR, mode=0o700, exist_ok=True)
    fd, path = tempfile.mkstemp(
        prefix=prefix, suffix=".sh", dir=_OVERRIDES_DIR, text=True
    )
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("#!/usr/bin/env bash\n")
        handle.write("\n".join(lines))
        handle.write("\n")
    os.chmod(path, 0o700)
    return path


def _dependency_lines(dependencies) -> list[str]:
    """Convert a manifest dependency list into shell install lines.

    Maps each package by dependency type: ``native`` to ``pkg_install``,
    ``flathub`` to ``pkg_flat`` and ``snap`` to ``pkg_snap``. Package
    names are shell-quoted. Malformed entries, blank package names and
    unknown types are skipped silently.

    Args:
        dependencies: List of dicts with ``type`` and ``packages`` keys.
            Any other type yields no lines.

    Returns:
        One shell line per package, in manifest order.
    """
    if not isinstance(dependencies, list):
        return []

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
    return lines


def _override_lines(overrides: dict, phase: str) -> list[str]:
    """Convert manifest overrides into shell lines for one phase.

    For ``pre`` and ``post``, an inline script string is used as is and
    a ``{"script": ...}`` mapping becomes a ``run_list_hook`` call. For
    ``flatpak``, each override becomes a shell-quoted
    ``flatpak_override`` call with scope, type, setting and target.

    Args:
        overrides: Manifest ``overrides`` mapping. Any other type
            yields no lines.
        phase: One of ``"pre"``, ``"post"`` or ``"flatpak"``. Other
            values yield no lines.

    Returns:
        Shell lines for the requested phase.
    """
    if not isinstance(overrides, dict):
        return []

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
    return lines


def _resolve_native_package_env(script_info: dict) -> str | None:
    """Resolve the single native package of an AppStream entry.

    Only applies to entries whose ``appstream_source`` is ``"native"``
    and that declare exactly one ``package-name`` (a string or a
    list/tuple of strings). Resolution is delegated to
    ``resolve_native_appstream_package``.

    Args:
        script_info: Entry info mapping.

    Returns:
        The resolved package name, or None if the entry is not native
        or does not have exactly one package.
    """
    if script_info.get("appstream_source") != "native":
        return None

    package_value = script_info.get("package-name")
    if isinstance(package_value, str):
        packages = [package_value.strip()] if package_value.strip() else []
    elif isinstance(package_value, (list, tuple)):
        packages = [str(v).strip() for v in package_value if str(v).strip()]
    else:
        packages = []

    if len(packages) != 1:
        return None

    return resolve_native_appstream_package(
        packages[0],
        component_id=script_info.get("appstream_id"),
        desktop_id=script_info.get("appstream_launchable"),
        name=script_info.get("name"),
    )


def build_install_script(entry: dict) -> str:
    """Build one install script covering every phase of an entry.

    Phases run in this order: ``pre``, dependencies, install, flatpak
    overrides and ``post``. Empty phases are omitted, and a status
    check between phases makes the first failing phase stop the rest.
    The install body comes from ``repo_parser.create_install_script``;
    its temporary file is read and removed, and its shebang is dropped.

    The caller owns the returned file and must delete it.

    Args:
        entry: AppStream entry info dict.

    Returns:
        Path of the generated executable script.

    Raises:
        OSError: If the install script cannot be read or the final
            script cannot be written.
    """
    install_path = repo_parser.create_install_script(entry)
    try:
        install_text = Path(install_path).read_text(encoding="utf-8")
    finally:
        try:
            os.remove(install_path)
        except OSError:
            pass

    lines = install_text.splitlines()
    if lines and lines[0].startswith("#!"):
        lines = lines[1:]
    install_body = "\n".join(lines).strip()

    pre, dependencies, flatpak, post = _appstream_phase_lines(entry)

    phases = []
    if pre:
        phases.append("\n".join(pre))
    if dependencies:
        phases.append("\n".join(dependencies))
    phases.append(install_body)
    if flatpak:
        phases.append("\n".join(flatpak))
    if post:
        phases.append("\n".join(post))
    gate = '\n_lt_rc=$?; [ "$_lt_rc" -eq 0 ] || exit "$_lt_rc"\n'
    script_body = gate.join(phases)

    os.makedirs(_OVERRIDES_DIR, mode=0o700, exist_ok=True)
    fd, path = tempfile.mkstemp(
        prefix="appstream-install-",
        suffix=".sh",
        dir=_OVERRIDES_DIR,
        text=True,
    )
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("#!/usr/bin/env bash\n\n")
        handle.write(script_body)
        handle.write("\n")
    os.chmod(path, 0o700)
    return path


def build_flatpak_extension_command(info: dict, remove: bool) -> list[str]:
    """Build the ``flatpak`` argv to install or remove an extension.

    The scope flag comes from ``flatpak_scope`` and
    ``flatpak_installation``: ``--user`` for user scope,
    ``--installation=<name>`` for a named non-default installation, and
    ``--system`` otherwise. Installs use ``flatpak_remote`` (default
    ``flathub``); the remote is ignored on removal. The command is
    non-interactive (``-y``).

    Args:
        info: Entry info with ``flatpak_ref`` and, optionally,
            ``flatpak_scope``, ``flatpak_installation`` and
            ``flatpak_remote``.
        remove: True to uninstall, False to install.

    Returns:
        Argument list ready for ``subprocess``.

    Raises:
        ValueError: If ``flatpak_ref`` is missing or blank.
    """
    ref = str(info.get("flatpak_ref") or "").strip()
    if not ref:
        raise ValueError("Extension has no flatpak_ref")

    scope = str(info.get("flatpak_scope") or "").strip()
    installation = str(info.get("flatpak_installation") or "").strip()
    if scope == "user":
        scope_args = ["--user"]
    elif installation and installation != "default":
        scope_args = [f"--installation={installation}"]
    else:
        scope_args = ["--system"]

    argv = ["flatpak", *scope_args]
    if remove:
        argv += ["uninstall", "-y", ref]
    else:
        remote = (
            str(info.get("flatpak_remote") or "flathub").strip() or "flathub"
        )
        argv += ["install", "-y", remote, ref]
    return argv


def build_snap_revert_command(info: dict) -> list[str]:
    """Build the command that reverts a snap.

    Args:
        info: Entry info with the ``snap_name`` key.

    Returns:
        ``["pkg_snap_revert", <snap_name>]``. ``pkg_snap_revert`` is a
        LinuxToys shell helper, so the command must run in a shell
        that has the helper loaded.

    Raises:
        ValueError: If ``snap_name`` is missing or blank.
    """
    snap_name = str(info.get("snap_name") or "").strip()
    if not snap_name:
        raise ValueError("Entry has no snap_name")
    return ["pkg_snap_revert", snap_name]


def _scan_aur_text_for_obfuscation(filename: str, text: str) -> list[str]:
    """Scan one text against the AUR obfuscation rules.

    Each rule reports at most once, at its first match.

    Args:
        filename: Name shown in the findings, relative to the repo.
        text: File content to inspect.

    Returns:
        Findings formatted as ``"<filename>:<line>: <description>"``.
        Empty if nothing matched.
    """
    findings = []
    for description, pattern in _AUR_OBFUSCATION_RULES:
        match = pattern.search(text)
        if match is None:
            continue
        line = text.count("\n", 0, match.start()) + 1
        findings.append(f"{filename}:{line}: {description}")
    return findings


def check_aur_package_security(package: str) -> tuple[int, str]:
    """Statically check AUR package sources for obfuscated code.

    BLOCKING: call from a worker thread (network clone, 45 s timeout).

    Shallow-clones ``https://aur.archlinux.org/<package>.git`` into a
    temporary directory with git hooks disabled, then scans the
    ``PKGBUILD`` and every ``*.install`` file against the obfuscation
    rules. Nothing from the repository is executed. Symbolic links and
    the ``.git`` directory are skipped, files over 1 MiB are reported
    as findings instead of being scanned, and the temporary directory
    is always removed. Expected failures are returned, not raised.

    Args:
        package: AUR package name. Must match ``[A-Za-z0-9@._+:-]+``.

    Returns:
        A ``(status, message)`` tuple:

        - ``(AUR_SECURITY_OK, "")``: no findings.
        - ``(AUR_SECURITY_BLOCKED, findings)``: at most 20 findings,
          one per line.
        - ``(AUR_SECURITY_UNAVAILABLE, reason)``: the check could not
          run (git missing, invalid name, clone failure or timeout,
          unreadable or missing PKGBUILD).
    """
    git = shutil.which("git")
    if not git:
        return (
            AUR_SECURITY_UNAVAILABLE,
            "Git is required to verify the AUR package sources.",
        )

    safe_package = str(package or "").strip()
    if not safe_package or not re.fullmatch(
        r"[A-Za-z0-9@._+:-]+", safe_package
    ):
        return (
            AUR_SECURITY_UNAVAILABLE,
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
                    "-c",
                    "protocol.file.allow=never",
                    "clone",
                    "--quiet",
                    "--depth",
                    "1",
                    "--no-tags",
                    "--config",
                    "core.hooksPath=/dev/null",
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
                AUR_SECURITY_UNAVAILABLE,
                f"Could not fetch the AUR repository for verification: {exc}",
            )

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            if len(detail) > 1000:
                detail = detail[-1000:]
            return (
                AUR_SECURITY_UNAVAILABLE,
                "Could not fetch the AUR repository for verification."
                + (f"\n\n{detail}" if detail else ""),
            )

        candidates = []
        pkgbuild = os.path.join(repo_dir, "PKGBUILD")
        if os.path.isfile(pkgbuild) and not os.path.islink(pkgbuild):
            candidates.append(pkgbuild)

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
                AUR_SECURITY_UNAVAILABLE,
                "The AUR repository did not contain a readable PKGBUILD.",
            )

        findings = []
        for path in candidates:
            try:
                size = os.path.getsize(path)
                if size > _AUR_SCAN_MAX_FILE:
                    relative = os.path.relpath(path, repo_dir)
                    findings.append(
                        f"{relative}: file is too large to safely inspect "
                        f"({size} bytes)"
                    )
                    continue
                with open(
                    path, "r", encoding="utf-8", errors="replace"
                ) as handle:
                    source = handle.read(_AUR_SCAN_MAX_FILE + 1)
            except OSError as exc:
                return (
                    AUR_SECURITY_UNAVAILABLE,
                    f"Could not read an AUR source file for verification: {exc}",
                )

            relative = os.path.relpath(path, repo_dir)
            findings.extend(_scan_aur_text_for_obfuscation(relative, source))

        if findings:
            return (AUR_SECURITY_BLOCKED, "\n".join(findings[:20]))
        return (AUR_SECURITY_OK, "")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def build_aur_install_script(package: str) -> str:
    """Write a minimal script that installs one AUR package.

    The script only calls ``pkg_install`` with the shell-quoted name
    and does not use ``repo_parser.create_install_script``. It does not
    verify the package, so run ``check_aur_package_security`` first.
    The caller owns the file and must delete it.

    Args:
        package: AUR package name.

    Returns:
        Path of the generated executable script.
    """
    os.makedirs(_OVERRIDES_DIR, mode=0o700, exist_ok=True)
    fd, path = tempfile.mkstemp(
        prefix="aur-install-", suffix=".sh", dir=_OVERRIDES_DIR, text=True
    )
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("#!/usr/bin/env bash\n")
        handle.write(f"pkg_install {shlex.quote(package)}\n")
    os.chmod(path, 0o700)
    return path
