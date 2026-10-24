"""Busy native package-manager preflight shared by every script runner.

Native package managers (apt, pacman, dnf, ...) serialize their transactions
with filesystem locks and fail opaquely when another process is already
holding them. Runs that would enter a native package transaction consult this
module before touching the package manager: when another process of the
distribution's native package manager is already running — a user terminal,
another LinuxToys instance, or a distro background service — the run is
waited for (bounded) and only refused after the timeout, with a translated
message.

The detection is deliberately conservative in both directions. It only counts
a script as a native transaction when it actually reaches a *transactional*
manager command, and it ignores container-scoped and read-only manager calls.
Like the helpers' own pacman_lock_guard and interrupted_apt_guard, the scan is
a best-effort preflight; it cannot close the race between the check and the
package-manager call itself.
"""

from __future__ import annotations

import functools
import os
import re
import shutil
import time
from pathlib import Path

from .library_loader import library_flags

BUSY_TITLE_KEY = "package_manager_busy_title"
BUSY_MESSAGE_KEY = "package_manager_busy_message"
BUSY_TITLE_FALLBACK = "Waiting for the package manager"
BUSY_MESSAGE_FALLBACK = (
    "Another package operation is currently running, so LinuxToys is standing "
    "by until it finishes. Package managers can't handle operations in "
    "parallel. No action is needed — your operation will start automatically "
    "as soon as the current one completes."
)

TIMEOUT_TITLE_KEY = "package_manager_timeout_title"
TIMEOUT_MESSAGE_KEY = "package_manager_timeout_message"
TIMEOUT_TITLE_FALLBACK = "Package operation taking too long"
TIMEOUT_MESSAGE_FALLBACK = (
    "Another package operation is still running and is taking too long. "
    "Please wait for the ongoing operation to finish, then try again."
)

# Seconds to wait for a busy native package manager before refusing. Shared by
# the terminal runner and the background AppStream queue so both cases behave
# the same way.
BUSY_WAIT_TIMEOUT_SECONDS = 300.0

# Library helpers whose execution reaches a native package transaction,
# directly (pkg_install/pkg_remove) or through their internals (pkg_make
# installs build dependencies, pkg_fromfile drives the dpkg/rpm file-install
# path). pkg_appimage and pkg_npm are deliberately NOT here: their native
# footprint is a single small dependency (fuse, npm) and treating a pure
# AppImage/npm script as a full native transaction refuses it whenever any
# manager process exists. They are still covered because their internals call
# pkg_install, which is itself gated at run time.
_NATIVE_HELPER_WORDS = frozenset({
    "pkg_install", "pkg_remove", "pkg_rm", "pkg_fromfile", "pkg_make",
})

# Raw native manager commands inside plain script bodies. dpkg/rpm are
# deliberately absent: script bodies overwhelmingly use them for read-only
# queries, and their installation paths run through pkg_fromfile. These are
# the command NAMES; whether a name actually starts a transaction is decided
# per-line by _line_enters_native_transaction below.
_RAW_MANAGER_WORDS = frozenset({
    "pacman", "paru", "pamac", "apt", "apt-get",
    "dnf", "dnf5", "zypper", "rpm-ostree", "eopkg",
})

_NATIVE_TRANSACTION_WORDS = _NATIVE_HELPER_WORDS | _RAW_MANAGER_WORDS

# Command wrappers whose presence on a line means the manager call runs inside
# a container/VM and never touches the host's package manager. Matching is
# word-boundary, case-insensitive.
_CONTAINER_PREFIX_RE = re.compile(
    r"(?:^|[\s;|&()])(?:distrobox(?:-enter)?|podman|docker|toolbox|"
    r"systemd-nspawn|flatpak-spawn|bwrap|chroot)(?=[\s;|&)])",
    re.IGNORECASE,
)

# Substrings that mark a line as a read-only or config query rather than a
# transaction even when a manager command is present (pacman-key, apt-key,
# --simulate, needs-restarting, config-manager, etc.). Kept broad on purpose:
# a false "not a transaction" only risks a late failure, while a false
# "is a transaction" wrongly refuses the user up front. These are matched
# before transactional verbs, so they must not overlap with real mutation
# flags (e.g. never "-s ", which would swallow "pacman -Syu").
_NON_TRANSACTIONAL_HINTS = (
    "pacman-key", "apt-key", "rpm-key",
    "--simulate", "--just-print", "--dry-run", "--download-only",
    "needs-restarting", "needs-rebooting", "config-manager",
    "addrepo", "add-repo", "refresh-md", "--refresh-md", "makecache",
    "check-update", "--version", "--help", "--print-uris",
    "list-installed", "--query", "repoquery", "whatprovides",
    "list-updates", "--quiet-cache",
)

# Per-manager transactional verbs/flags. A raw manager line counts as a native
# transaction only when it carries one of these. Anything else (query, key,
# repo config) is ignored. Substring matching is intentional and conservative:
# a match means "may mutate the package database".
_TRANSACTIONAL_HINTS = {
    "apt": (
        "install", "remove", "purge", "upgrade", "dist-upgrade",
        "full-upgrade", "autoremove", "autoclean", "clean", "update",
    ),
    "apt-get": (
        "install", "remove", "purge", "upgrade", "dist-upgrade",
        "full-upgrade", "autoremove", "autoclean", "clean", "update",
        "--fix-broken", "dselect-upgrade",
    ),
    "pacman": (
        "--sync", "--remove", "--upgrade", "--refresh",
        "-s ", "-sy", "-syu", "-syy", "-syyu", "-r ", "-rns", "-rdd",
        "-u ", "-uh", "-scc", "-sc",
    ),
    "paru": ("--sync", "--remove", "-s ", "-syu", "-r "),
    "pamac": (
        "install", "remove", "upgrade", "update", "build", "clean",
    ),
    "dnf": (
        "install", "remove", "erase", "upgrade", "update", "distro-sync",
        "group install", "reinstall", "swap", "autoremove",
    ),
    "dnf5": (
        "install", "remove", "erase", "upgrade", "update", "distro-sync",
        "reinstall", "swap", "autoremove",
    ),
    "zypper": (
        "install", "remove", "upgrade", "update", "dup", "dist-upgrade",
        "purge-kernels", "in ", "rm ",
    ),
    "rpm-ostree": (
        "install", "uninstall", "override", "reset", "rebase", "deploy",
        "upgrade", "update", "cleanup",
    ),
    "eopkg": (
        "install", "remove", "upgrade", "emerge", " rmo ", " up ",
    ),
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


# Process names per native transaction family. Flatpak and Snap are excluded
# on purpose: their transactions queue inside their own daemons, so parallel
# operations are safe there.
#
# Names are matched against /proc/<pid>/comm exactly, and comm is truncated to
# 15 characters, so entries use the truncated form where that matters
# (e.g. "apt.systemd.dai" for "apt.systemd.daily"). PackageKit (packagekitd/
# pkcon) is included because it holds the apt/dpkg locks while a parallel native
# transaction would collide with it — PackageKit is how GUI software centres and
# derivative updaters (e.g. Zorin) drive apt. apt's download helpers (http/https)
# are deliberately NOT watched: their names are too generic and would match
# unrelated processes.
_FAMILY_MANAGER_PROCESSES = {
    "debian": (
        "apt", "apt-get", "apt-key", "dpkg", "dpkg-deb", "unattended-upgr",
        "apt.systemd.dai", "packagekitd", "pkcon",
    ),
    "arch": ("pacman", "paru", "pamac", "pamac-daemon", "yay"),
    "ostree": ("rpm-ostree",),
    "fedora": ("dnf", "dnf5", "dnf-automatic"),
    "suse": ("zypper", "zypp-refresh"),
    "solus": ("eopkg",),
}


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


def _strip_comments(text):
    """Drop full-line and trailing (inline) shell comments.

    Manager words that only appear as documentation must never flag a run.
    A '#' inside a word (rare, e.g. "${var#prefix}") is left alone: comment
    stripping only applies when '#' begins a token or follows whitespace.
    """
    cleaned_lines = []
    for line in text.splitlines():
        # Remove trailing inline comments: a '#' preceded by whitespace.
        line = re.sub(r"(?:(?<=\s)|^)#.*$", "", line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _line_enters_native_transaction(line):
    """Decide whether one (comment-stripped) line can start a native transaction."""
    lowered = line.lower()

    if _CONTAINER_PREFIX_RE.search(lowered):
        return False

    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_.-]*", lowered))
    for manager in _RAW_MANAGER_WORDS:
        if manager not in words:
            continue
        if _manager_line_is_transactional(lowered, manager):
            return True
    return False


def _manager_line_is_transactional(lowered, manager):
    """Whether a manager command's line mutates the package database.

    Read-only, key-management, repo-config and dry-run forms are excluded so a
    script that merely queries or configures a manager is never gated. If the
    classification is ambiguous, the line is treated as transactional: a late
    manager failure is recoverable, while a wrongly-refused run is not.
    """
    if any(hint in lowered for hint in _NON_TRANSACTIONAL_HINTS):
        return False

    # Single-dash simulate/quiet forms ("apt-get -s autoremove", "dnf -q ...")
    # are dry-run/read-only even when they carry a mutating verb. A "-s" that is
    # part of a combined short flag ("pacman -Syu") is not matched here.
    if re.search(r"(?:^|\s)-(?:s|y\s+--simulate)(?:\s|$)", lowered) or \
            re.search(r"(?:^|\s)-[a-z]*s[a-z]*(?:\s|$)", lowered) and "pacman" not in lowered:
        return False

    verbs = _TRANSACTIONAL_HINTS.get(manager, ())
    return any(verb in lowered for verb in verbs)


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

    # Helper calls are always transactions (their internals reach the manager).
    if referenced & _NATIVE_HELPER_WORDS:
        return True

    # Raw manager commands need per-line review to skip container-scoped and
    # read-only calls.
    cleaned = _strip_comments(text)
    for line in cleaned.splitlines():
        if _line_enters_native_transaction(line):
            return True
    return False


def native_transaction_conflict(script_path, script_dir):
    """Return a running native package-manager process name when dispatching
    this script would collide with it, else None."""
    if not script_enters_native_transaction(script_path, script_dir):
        return None
    return busy_native_manager_process()


def wait_for_idle(timeout=BUSY_WAIT_TIMEOUT_SECONDS, poll_interval=1.0):
    """Poll until no native package manager is running.

    Returns (True, None) once idle, or (False, name) after ``timeout`` seconds
    with a manager still running. Shared by the terminal runner and the
    background queue so both cases wait first and only report a timeout.
    """
    deadline = time.monotonic() + float(timeout)
    while True:
        name = busy_native_manager_process()
        if name is None:
            return True, None
        if time.monotonic() >= deadline:
            return False, name
        time.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))


def busy_texts(translations=None):
    """Return the (title, message) pair explaining a refused transaction."""
    if translations is None:
        from .lang_utils import load_translations
        translations = load_translations()

    return (
        translations.get(BUSY_TITLE_KEY, BUSY_TITLE_FALLBACK),
        translations.get(BUSY_MESSAGE_KEY, BUSY_MESSAGE_FALLBACK),
    )


def timeout_texts(translations=None):
    """Return the (title, message) pair for a wait that timed out.

    Replaces the immediate busy refusal: the run waited for the ongoing
    operation and it is still going after BUSY_WAIT_TIMEOUT_SECONDS.
    """
    if translations is None:
        from .lang_utils import load_translations
        translations = load_translations()

    return (
        translations.get(TIMEOUT_TITLE_KEY, TIMEOUT_TITLE_FALLBACK),
        translations.get(TIMEOUT_MESSAGE_KEY, TIMEOUT_MESSAGE_FALLBACK),
    )
