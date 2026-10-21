"""Busy native package-manager preflight shared by every script runner.

Native package managers (apt, pacman, dnf, ...) serialize their transactions
with filesystem locks and fail opaquely when another process is already
holding them. Runs that would enter a native package transaction consult this
module before touching the package manager: when another process of the
distribution's native package manager is already running — a user terminal,
another LinuxToys instance, or a distro background service — the run is
refused up front with a translated message instead.

Like the helpers' own pacman_lock_guard and interrupted_apt_guard, the scan is
a best-effort preflight; it cannot close the race between the check and the
package-manager call itself.
"""

from __future__ import annotations

import functools
import os
import shutil
from pathlib import Path

from .library_loader import library_flags

BUSY_TITLE_KEY = "package_manager_busy_title"
BUSY_MESSAGE_KEY = "package_manager_busy_message"
BUSY_TITLE_FALLBACK = "Package manager busy"
BUSY_MESSAGE_FALLBACK = (
    "Another package operation is already running. Package managers don't "
    "support operations in parallel. Please wait for the ongoing process to "
    "finish before attempting any such operations with LinuxToys."
)

# Library helpers whose execution reaches a native package transaction,
# directly (pkg_install/pkg_remove) or through their internals (pkg_make
# installs build dependencies, pkg_appimage installs fuse, pkg_npm installs
# npm, and pkg_fromfile drives the dpkg/rpm file-install path).
_NATIVE_HELPER_WORDS = frozenset({
    "pkg_install", "pkg_remove", "pkg_rm", "pkg_fromfile",
    "pkg_make", "pkg_appimage", "pkg_npm",
})

# Raw native manager commands inside plain script bodies. dpkg/rpm are
# deliberately absent: script bodies overwhelmingly use them for read-only
# queries, and their installation paths run through pkg_fromfile.
_RAW_MANAGER_WORDS = frozenset({
    "pacman", "paru", "pamac", "apt", "apt-get",
    "dnf", "dnf5", "zypper", "rpm-ostree", "eopkg",
})

_NATIVE_TRANSACTION_WORDS = _NATIVE_HELPER_WORDS | _RAW_MANAGER_WORDS

# Process names per native transaction family. Flatpak and Snap are excluded
# on purpose: their transactions queue inside their own daemons, so parallel
# operations are safe there.
_FAMILY_MANAGER_PROCESSES = {
    "debian": ("apt", "apt-get", "dpkg", "unattended-upgr"),
    "arch": ("pacman", "paru", "pamac", "yay"),
    "ostree": ("rpm-ostree",),
    "fedora": ("dnf", "dnf5"),
    "suse": ("zypper",),
    "solus": ("eopkg",),
}


@functools.lru_cache(maxsize=1)
def _read_os_release():
    fields = {}
    try:
        with open("/etc/os-release", "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                key, separator, value = line.strip().partition("=")
                if separator:
                    fields[key.casefold()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return fields


def _native_manager_family():
    """Return the pkg_install dispatch family of this host ("" = unknown).

    Mirrors the family predicates in libs/sysinfo.bash, so the scan inspects
    exactly the managers the distribution execution path drives.
    """
    fields = _read_os_release()
    os_id = fields.get("id", "").casefold()
    id_like = fields.get("id_like", "").casefold().split()

    def matches(*keys):
        return os_id in keys or any(key in id_like for key in keys)

    # SteamOS ships pacman, but LinuxToys' native path is a no-op there
    # (compat gates): nothing to serialize.
    if os_id == "steamos" or "steamos" in id_like:
        return ""

    # rpm-ostree systems layer through rpm-ostree rather than dnf.
    if matches("fedora", "rhel", "centos") and os.path.exists("/run/ostree-booted") \
            and shutil.which("rpm-ostree"):
        return "ostree"
    if os_id == "cachyos":
        return "arch"
    if matches("arch", "artix", "manjaro", "endeavouros", "garuda"):
        return "arch"
    if matches("suse", "opensuse", "opensuse-leap", "opensuse-tumbleweed"):
        return "suse"
    if os_id == "solus":
        return "solus"
    if matches("fedora", "rhel", "centos", "almalinux", "rocky", "nobara"):
        return "fedora"
    if matches("debian", "ubuntu", "deepin", "kali", "linuxmint", "raspbian", "pop"):
        return "debian"
    return ""


def native_manager_process_names():
    """Process names of the distribution's native package-manager path."""
    return _FAMILY_MANAGER_PROCESSES.get(_native_manager_family(), ())


def busy_native_manager_process():
    """Return the process name of a running native package manager, else None."""
    names = native_manager_process_names()
    if not names:
        return None

    try:
        entries = list(os.scandir("/proc"))
    except OSError:
        return None

    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            with open(os.path.join(entry.path, "comm"), "r",
                      encoding="utf-8", errors="replace") as handle:
                comm = handle.readline().strip().casefold()
        except OSError:
            continue
        if comm in names:
            return comm
    return None


def script_enters_native_transaction(script_path, script_dir):
    """Statically decide whether this run can reach a native package transaction."""
    try:
        text = Path(script_path).read_text(encoding="utf-8")
    except OSError:
        return False

    try:
        _flags, referenced = library_flags(text, script_dir)
    except OSError:
        # Unreadable library tree: the run itself will fail the same way it
        # does today; the guard never blocks on its own broken setup.
        return False
    return bool(referenced & _NATIVE_TRANSACTION_WORDS)


def native_transaction_conflict(script_path, script_dir):
    """Return a running native package-manager process name when dispatching
    this script would collide with it, else None."""
    if not script_enters_native_transaction(script_path, script_dir):
        return None
    return busy_native_manager_process()


def busy_texts(translations=None):
    """Return the (title, message) pair explaining a refused transaction."""
    if translations is None:
        from .lang_utils import load_translations
        translations = load_translations()

    return (
        translations.get(BUSY_TITLE_KEY, BUSY_TITLE_FALLBACK),
        translations.get(BUSY_MESSAGE_KEY, BUSY_MESSAGE_FALLBACK),
    )
