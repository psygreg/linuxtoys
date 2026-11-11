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
import shlex
import tempfile

from app import repo_parser
from app.library_loader import _appstream_phase_lines

_OVERRIDES_DIR = "/tmp/linuxtoys/appstream-overrides"

from app.aur_security import (
    AUR_SECURITY_OK,
    AUR_SECURITY_UNAVAILABLE,
    AUR_SECURITY_BLOCKED,
    check_aur_package_security,
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
    install_text = repo_parser.compose_install_script(entry)
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
