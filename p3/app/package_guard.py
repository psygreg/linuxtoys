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
import subprocess
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

# Helpers that reach a native package transaction only on some hosts: their
# primary work (an AppImage, an npm package) is manager-free, but their
# internals install a small native dependency (fuse, npm) through pkg_install
# when it is missing. On hosts where that dependency path is taken they are a
# native transaction; on hosts where it is not they are not. This mirrors the
# per-distro branches in libs/packages.bash (pkg_appimage installs fuse/libfuse2,
# pkg_npm installs npm).
_CONDITIONAL_NATIVE_HELPER_WORDS = frozenset({
    "pkg_appimage", "pkg_npm",
})


def helper_reaches_native_manager(name):
    """Whether a library helper can reach a native package transaction.

    ``pkg_install``/``pkg_remove``/``pkg_fromfile``/``pkg_make`` always can.
    ``pkg_appimage``/``pkg_npm`` only when their native-dependency install
    branch applies to this host (the fuse / npm package). Pure AppImage and
    npm installs on hosts without that branch never touch the native manager,
    so gating them would wrongly refuse a run whenever any manager process
    happens to be present.
    """
    if name in _NATIVE_HELPER_WORDS:
        return True
    if name in _CONDITIONAL_NATIVE_HELPER_WORDS:
        return _conditional_helper_installs_native_dep(name)
    return False


def _conditional_helper_installs_native_dep(name):
    """Whether pkg_appimage/pkg_npm install a native dependency on this host."""
    family = _native_manager_family()
    if name == "pkg_appimage":
        # fuse/libfuse2 branches: debian, fedora/ostree/rhel, arch, solus.
        return family in {"debian", "fedora", "ostree", "arch", "solus"}
    if name == "pkg_npm":
        # pkg_npm installs the npm package itself wherever it is missing.
        return family != ""
    return False

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
# (e.g. "apt.systemd.dai" for "apt.systemd.daily").
#
# A bare process name is NOT sufficient evidence of a busy manager: several of
# these are RESIDENT daemons that are alive whenever a software centre or an
# auto-update timer is installed, yet only hold the package lock during a real
# transaction. packagekitd (PackageKit — GNOME Software / Discover / pamac),
# unattended-upgr, apt.systemd.dai, pamac-daemon, dnf-automatic and zypp-refresh
# all run constantly on their distros. Counting them as "busy" makes the guard
# fire on every install — the reported over-trigger. So names are split into
# transaction tools (a running instance IS a transaction) and resident daemons
# (only count when they actively hold the package lock, below).
#
# The "ostree" family must be decided differently still: its transaction tool
# and the resident system daemon share ONE comm name ("rpm-ostree" — the daemon
# is spawned by the same binary: rpm-ostreed.service runs `rpm-ostree
# start-daemon`), so process presence alone can never separate an idle rpm-ostree
# host from a busy one. busy_native_manager_process() asks the daemon's own
# state instead (see _rpm_ostree_transaction_active).
_FAMILY_MANAGER_PROCESSES = {
    "debian": ("apt", "apt-get", "dpkg", "dpkg-deb", "pkcon"),
    "arch": ("pacman", "paru", "pamac", "yay"),
    "ostree": ("rpm-ostree",),
    "fedora": ("dnf", "dnf5"),
    "suse": ("zypper",),
    "solus": ("eopkg",),
}

# Resident daemons per family: alive most of the time, but only evidence of a
# transaction when they hold the package lock. Matched the same way (comm, 15
# chars) but gated on an active lock below.
_FAMILY_DAEMON_PROCESSES = {
    "debian": ("unattended-upgr", "apt.systemd.dai", "packagekitd", "apt-key"),
    "arch": ("pamac-daemon",),
    # rpm-ostree-automatic drives unattended rpm-ostree staging/deploys on
    # Universal Blue / Silverblue / Kinoite / Bazzite hosts. Its comm truncates
    # to "rpm-ostree-auto". Presence alone is not busy: like every rpm-ostree
    # process it is classified through the daemon-state probe in
    # busy_native_manager_process, because all of them share the "rpm-ostree"
    # comm and the sysroot locks they hold live inside the daemon's private
    # mount namespace (MountFlags=slave), invisible to the host's /proc.
    "ostree": ("rpm-ostree-auto",),
    "fedora": ("dnf-automatic",),
    "suse": ("zypp-refresh",),
    "solus": (),
}

# Lock files / markers that mean "a transaction is in progress" per family.
# These mirror pacman_lock_guard/interrupted_apt_guard in libs/packages.bash.
# A present lock is necessary but not sufficient — a stale lock after a crash
# should not block forever — so a lock only counts as busy when some process
# actually holds it (see _lock_actively_held).
_FAMILY_LOCK_FILES = {
    "debian": (
        "/var/lib/dpkg/lock-frontend", "/var/lib/dpkg/lock",
        "/var/lib/apt/lists/lock", "/var/cache/apt/archives/lock",
    ),
    "arch": ("/var/lib/pacman/db.lck",),
    # No "ostree" entry on purpose: the sysroot locks rpm-ostree holds during a
    # transaction live inside the daemon's private mount namespace
    # (MountFlags=slave in rpm-ostreed.service), so host-visible lock paths are
    # not observable and a lock check would silently see "idle" during a real
    # transaction. This family is decided by the daemon's own state instead
    # (see _rpm_ostree_transaction_active).
    "fedora": ("/var/lib/dnf/rpmdb.lock", "/run/dnf.pid", "/var/lib/dnf/lock"),
    "suse": ("/run/zypp.pid", "/var/run/zypp.pid"),
    "solus": (),
}


def native_manager_process_names():
    """Process names of the distribution's native package-manager path."""
    return _FAMILY_MANAGER_PROCESSES.get(_native_manager_family(), ())


def _running_comm_names():
    """Set of comm names currently present in /proc (15-char, casefolded)."""
    found = set()
    try:
        entries = list(os.scandir("/proc"))
    except OSError:
        return found
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            with open(os.path.join(entry.path, "comm"), "r",
                      encoding="utf-8", errors="replace") as handle:
                comm = handle.readline().strip().casefold()
        except OSError:
            continue
        if comm:
            found.add(comm)
    return found


def _lock_actively_held(path):
    """Whether a package lock is held by a live process right now.

    A lock file merely existing is not evidence of a transaction (a crash can
    leave a stale lock behind). The reliable signal is an open file descriptor
    held by another process — the same test pacman_lock_guard uses with lsof.
    We read /proc/<pid>/fd directly so no external tool is required.
    """
    try:
        stat = os.stat(path)
    except OSError:
        return False

    target = (stat.st_dev, stat.st_ino)
    try:
        entries = list(os.scandir("/proc"))
    except OSError:
        return False

    for entry in entries:
        if not entry.name.isdigit():
            continue
        fd_dir = os.path.join(entry.path, "fd")
        try:
            fds = list(os.scandir(fd_dir))
        except OSError:
            continue
        for fd in fds:
            try:
                link = os.readlink(fd.path)
            except OSError:
                continue
            # Symlink resolves to the inode we care about.
            if link == path or link == f"{path} (deleted)":
                return True
            try:
                fd_stat = os.stat(fd.path)
            except OSError:
                continue
            if (fd_stat.st_dev, fd_stat.st_ino) == target:
                return True
    return False


def _family_lock_held(family):
    """Whether any of the family's package locks is actively held."""
    for path in _FAMILY_LOCK_FILES.get(family, ()):
        if _lock_actively_held(path):
            return True
    return False


def _rpm_ostree_transaction_active(timeout=25.0):
    """Whether the rpm-ostree daemon itself reports a transaction in progress.

    The only authoritative busy signal for the "ostree" family: client,
    system daemon and read-only status readers share one process name, and
    the sysroot locks the daemon holds live inside its private mount
    namespace (MountFlags=slave in rpm-ostreed.service), so neither process
    presence nor host-visible lock files can separate an idle rpm-ostree
    host from a busy one.

    ``rpm-ostree status`` is a read-only client call: it needs no elevation,
    works in every daemon state and is safe to issue while a transaction is
    running. Its header line carries the daemon's own classification —
    "State: idle" when nothing is running (a staged deployment merely
    awaiting a reboot still reports idle) and "State: busy" (plus a
    "Transaction:" line) while an install, upgrade, rebase or an
    automatic stage/apply update drives the sysroot.

    Any failure to read a clear state (missing binary, timeout, unexpected
    output) counts as NOT busy: the guard never blocks on its own broken
    machinery.
    """
    try:
        result = subprocess.run(
            ["rpm-ostree", "status"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if result.returncode != 0:
        return False
    header = result.stdout.decode("utf-8", errors="replace")
    for line in header.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("state:"):
            return "busy" in stripped.lower()
    return False


def busy_native_manager_process():
    """Return the name of a running native package manager, else None.

    Reports a manager only when a transaction is genuinely in progress: either
    a transaction tool (apt, pacman, dnf, ...) is running, or a resident daemon
    (packagekitd, unattended-upgr, ...) is running AND actively holding the
    package lock. A resident daemon on its own is idle and must not block a run.

    On the "ostree" family the tool and daemon share one comm, so the verdict
    is the daemon's own busy state instead (see _rpm_ostree_transaction_active).
    """
    family = _native_manager_family()
    if not family:
        return None

    tools = set(_FAMILY_MANAGER_PROCESSES.get(family, ()))
    daemons = set(_FAMILY_DAEMON_PROCESSES.get(family, ()))
    if not tools and not daemons:
        return None

    running = _running_comm_names()

    # rpm-ostree: process presence alone is meaningless for this family (the
    # transaction tool and the always-startable system daemon share the same
    # comm, and read-only status callers keep the daemon resident). Gate on
    # what the daemon says about itself.
    if family == "ostree":
        if not (tools | daemons) & running:
            return None
        return "rpm-ostree" if _rpm_ostree_transaction_active() else None

    # A running transaction tool is itself proof of a transaction.
    for name in sorted(tools & running):
        return name

    # A resident daemon only counts while it holds the package lock.
    if (daemons & running) and _family_lock_held(family):
        for name in sorted(daemons & running):
            return name

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

    # Helper calls: unconditional helpers always reach the manager; conditional
    # ones (pkg_appimage/pkg_npm) only when their native-dependency branch runs
    # on this host. This is what keeps a pure AppImage/npm install from being
    # gated on an unrelated manager process.
    for word in referenced:
        if helper_reaches_native_manager(word):
            return True

    # Raw manager commands need per-line review to skip container-scoped and
    # read-only calls.
    cleaned = _strip_comments(text)
    for line in cleaned.splitlines():
        if _line_enters_native_transaction(line):
            return True
    return False


def job_enters_native_transaction(command_text):
    """Statically decide whether a generated job command reaches a native
    transaction.

    Used by the AppStream/queue dispatcher, which builds the concrete command
    (``pkg_install X``, ``pkg_appimage /path``, ``pkg_fromfile /path``) rather
    than a script path. Falls back to a line scan so raw manager commands in a
    generated body are still seen.
    """
    if not command_text:
        return False

    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", command_text))
    for word in words:
        if helper_reaches_native_manager(word):
            return True

    cleaned = _strip_comments(command_text)
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
