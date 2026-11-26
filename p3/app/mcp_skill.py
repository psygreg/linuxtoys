#!/usr/bin/env python3
"""MCP agent skill installation using only the Python standard library.

The reviewed skill text is installed from the upstream repository when it is
reachable (HTTPS fetch, GitHub first and the Gitea mirror as fallback); the
pinned bundled copy is the offline fallback. Existing different contents are
never replaced — an older copy of this same skill (same frontmatter identity)
is the one exception, so newer text can actually land. Descriptor-relative,
no-follow operations anchor writes beneath a private user-owned home tree.
Publication is an atomic create-only hard link, or an atomic rename when it
replaces our own older copy; cooperating installers serialize with flock.
"""

import contextlib
import fcntl
import hashlib
import os
from pathlib import Path
import secrets
import stat
import sys
import time
import urllib.error
import urllib.request

SKILL_NAME = "linuxtoys-mcp"
# Public repository pages; the raw fetch endpoints are derived from them and
# the canonical fetchable copy lives at skills/linuxtoys-mcp/SKILL.md.
SKILL_REPO_URLS = (
    "https://github.com/psygreg/linuxtoys",
    "https://git.linux.toys/psygreg/linuxtoys",
)
SKILL_DEFAULT_BRANCH = "master"
# Compatibility export from the retired remote-CLI flow; the bounded HTTPS
# text fetch uses SKILL_FETCH_TIMEOUT per source instead.
SKILL_INSTALL_TIMEOUT = 180
SKILL_FETCH_TIMEOUT = 10
BUNDLED_SHA256 = "721ce02f84979a753b0a6559f9ddd4ad0c3cab39fa0db78421b928ad2ae91b02"
MAX_SKILL_BYTES = 128 * 1024
LOCK_TIMEOUT = 5.0
TARGETS = (
    (".agents", "skills"),
    (".claude", "skills"),
    (".config", "opencode", "skill"),
    (".codex", "skills"),
    (".cursor", "skills"),
    (".windsurf", "skills"),
    (".gemini", "skills"),
)
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


def bundled_skill_path():
    return str(Path(__file__).resolve().with_name("mcp_skill") / "SKILL.md")


def _read_regular(fd, *, owned=False):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SKILL_BYTES:
        raise OSError("Skill must be a bounded regular file")
    if owned and (info.st_uid != os.geteuid() or info.st_mode & 0o022):
        raise OSError("Unsafe existing skill ownership, links or permissions")
    data = b""
    while len(data) <= MAX_SKILL_BYTES:
        chunk = os.read(fd, min(65536, MAX_SKILL_BYTES + 1 - len(data)))
        if not chunk:
            return data
        data += chunk
    raise OSError("Skill exceeds size limit")


def _bundled_bytes():
    path = Path(bundled_skill_path())
    # The application location is trusted; the asset directory/file cannot be links.
    with contextlib.ExitStack() as stack:
        parent = os.open(path.parent, _DIR_FLAGS)
        stack.callback(os.close, parent)
        fd = os.open(path.name, _FILE_FLAGS, dir_fd=parent)
        stack.callback(os.close, fd)
        data = _read_regular(fd)
    if hashlib.sha256(data).hexdigest() != BUNDLED_SHA256:
        raise ValueError("Bundled MCP skill is corrupt or not the reviewed copy")
    data.decode("utf-8")
    return data


def skill_fetch_urls():
    """Raw content URLs for the canonical skill copy on each known mirror."""
    suffix = f"/{SKILL_DEFAULT_BRANCH}/skills/{SKILL_NAME}/SKILL.md"
    urls = []
    for base in SKILL_REPO_URLS:
        if base.startswith("https://github.com/"):
            urls.append(
                base.replace(
                    "https://github.com/", "https://raw.githubusercontent.com/", 1
                )
                + suffix
            )
        elif base.startswith("https://git.linux.toys/"):
            urls.append(f"{base}/raw/branch{suffix}")
    return tuple(urls)


def _validate_skill_bytes(data):
    """Refuse any text that is not a LinuxToys MCP skill document.

    Remote bytes are data to publish verbatim, never instructions for this
    installer; the shape check only keeps error pages or foreign documents
    from being treated as the reviewed skill.
    """
    text = data.decode("utf-8")  # UnicodeDecodeError is a ValueError
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Remote skill text has no frontmatter")
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "name: linuxtoys-mcp":
            return
        if stripped == "---":
            break
    raise ValueError("Remote skill text is not the LinuxToys MCP skill")


def _fetch_upstream_skill():
    """Latest reviewed skill bytes from upstream, or None when unavailable.

    Every source is HTTPS, timeout-bound, size-bounded and shape-validated;
    one reachable source with valid text wins. This bounded text fetch is
    the helper's only network use.
    """
    for url in skill_fetch_urls():
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "LinuxToys-MCP-Skill/1.0"}
            )
            with urllib.request.urlopen(
                request, timeout=SKILL_FETCH_TIMEOUT
            ) as response:
                if getattr(response, "status", 200) != 200:
                    continue
                data = response.read(MAX_SKILL_BYTES + 1)
        except (urllib.error.URLError, OSError):
            continue
        if len(data) > MAX_SKILL_BYTES:
            continue
        try:
            _validate_skill_bytes(data)
        except ValueError:
            continue
        return data
    return None


def _private_directory(fd):
    info = os.fstat(fd)
    if info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise OSError("Skill directories must be user-owned and not writable by others")


def _open_home(home):
    # Do not resolve symlinks: rejecting them is part of the installation contract.
    path = Path(home)
    if not path.is_absolute() or ".." in path.parts or path == Path("/"):
        raise OSError("Expected an absolute, non-root home directory")
    fd = os.open("/", _DIR_FLAGS)
    try:
        for part in path.parts[1:]:
            child = os.open(part, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
        _private_directory(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _descend(parent, parts, *, create):
    fd = os.dup(parent)
    try:
        for part in parts:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(part, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
            _private_directory(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _skill_state(directory, data):
    """Classify the existing SKILL.md beneath ``directory``.

    Returns "absent", "same" (byte-identical install) or "replaceable" (an
    older copy of this same skill, safe to update). Unsafe or foreign
    existing content raises; callers preserve it for manual resolution.
    """
    try:
        fd = os.open("SKILL.md", _FILE_FLAGS, dir_fd=directory)
    except FileNotFoundError:
        return "absent"
    try:
        existing = _read_regular(fd, owned=True)
    finally:
        os.close(fd)
    if existing == data:
        return "same"
    try:
        _validate_skill_bytes(existing)
    except ValueError:
        raise OSError(
            "Existing customized or foreign skill preserved; resolve manually"
        )
    return "replaceable"


def _publish(directory, data):
    """Publish ``data`` atomically without replacing foreign content.

    A fresh install hard-links a staged 0600 file create-only. An existing
    byte-identical file ends the job unchanged; an older copy of this same
    skill is atomically replaced by rename. Customized, foreign or unsafe
    existing files are refused before anything is written.
    """
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    try:
        lock = os.open(
            ".install.lock", flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory
        )
    except FileExistsError:
        lock = os.open(".install.lock", flags, dir_fd=directory)
    else:
        try:
            os.fchmod(lock, 0o600)
        except BaseException:
            os.close(lock)
            raise
    temporary = None
    try:
        info = os.fstat(lock)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise OSError("Unsafe skill installation lock")
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise OSError("Another MCP skill installation holds the lock")
                time.sleep(0.01)
        state = _skill_state(directory, data)
        if state == "same":
            return
        candidate = ".skill-" + secrets.token_hex(16) + ".tmp"
        fd = os.open(
            candidate,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        temporary = candidate  # Cleanup only a staging file we created.
        try:
            handle = os.fdopen(fd, "wb")
        except BaseException:
            os.close(fd)
            raise
        with handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            if state == "absent":
                os.link(
                    temporary,
                    "SKILL.md",
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                    follow_symlinks=False,
                )
            else:
                # Atomic rename over our own older copy. rename never
                # dereferences the destination entry, so it can never write
                # through a swapped-in link.
                os.replace(
                    temporary, "SKILL.md", src_dir_fd=directory, dst_dir_fd=directory
                )
        except FileExistsError:
            # A noncooperating creator won the race. Never replace its file/link.
            if _skill_state(directory, data) != "same":
                raise OSError("Skill destination changed during installation")
        # The complete file is already visible. A directory-sync failure must not
        # roll it back or destroy an otherwise working installation.
        try:
            os.fsync(directory)
        except OSError as error:
            print(
                f"MCP skill published; directory durability unavailable: {error}",
                file=sys.stderr,
            )
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary, dir_fd=directory)
            except OSError:
                pass
        os.close(lock)


def install_agent_skill():
    """Return verified installed paths; preserve all conflicting user contents.

    Detect agent roots without following links. Create the universal root only
    for a fresh profile with no detected agent root, never to hide a failed or
    unsafe existing target. The upstream text is fetched and validated before
    any home writes; the pinned bundled copy is the offline fallback.
    """
    installed = []
    try:
        data = _fetch_upstream_skill()
        if data is None:
            data = _bundled_bytes()
            print(
                "MCP skill: upstream repository unavailable;"
                " installing the bundled copy",
                file=sys.stderr,
            )
        home = os.path.expanduser("~")
        with contextlib.ExitStack() as stack:
            root = _open_home(home)
            stack.callback(os.close, root)
            targets = []
            for parts in TARGETS:
                try:
                    agent_parent = _descend(root, parts[:-2], create=False)
                except FileNotFoundError:
                    continue
                except OSError as error:
                    # An unsafe ancestor is a conflict, not a fresh profile.
                    print(f"MCP skill: unsafe agent parent: {error}", file=sys.stderr)
                    return []
                try:
                    os.stat(parts[-2], dir_fd=agent_parent, follow_symlinks=False)
                    targets.append(parts)
                except FileNotFoundError:
                    pass
                finally:
                    os.close(agent_parent)
            if not targets:
                targets = [TARGETS[0]]
            for parts in targets:
                try:
                    destination = _descend(root, (*parts, SKILL_NAME), create=True)
                    try:
                        _publish(destination, data)
                    finally:
                        os.close(destination)
                    installed.append(os.path.join(home, *parts, SKILL_NAME))
                except OSError as error:
                    print(
                        f"MCP skill: preserving/refusing {'/'.join(parts)}: {error}",
                        file=sys.stderr,
                    )
    except (OSError, ValueError) as error:
        print(f"MCP skill installation refused: {error}", file=sys.stderr)
    return installed


def skill_install_script():
    """Reviewed data-only operation; M1 validates this header at dispatch.

    The helper fetches the reviewed skill text from the upstream repository
    over HTTPS and falls back to the pinned bundled copy when no source is
    reachable. No external installer, native payload or package manager is
    used; the direct helper deliberately loads no optional application
    dependencies beyond the standard library.
    """
    return """#!/usr/bin/env bash
# architectures: x86_64, aarch64
# Install the upstream LinuxToys MCP skill; the bundled copy is the offline fallback.
exec python3 "$SCRIPT_DIR/app/mcp_skill.py"
"""


def request_skill_install(runner=None):
    """Queue the guarded operation, or run the helper directly on enqueue failure."""
    if runner is not None:
        try:
            job = runner.enqueue_skill_install(skill_install_script())
            if job:
                return job
        except ValueError:
            # M1 ArchitectureError is a ValueError. Operation/policy refusals
            # must reach the caller, never become an unguarded direct retry.
            raise
        except (OSError, RuntimeError, ImportError, AttributeError) as error:
            print(f"MCP skill install could not be queued: {error}", file=sys.stderr)
    return install_agent_skill()


def main():
    installed = install_agent_skill()
    if installed:
        print("LinuxToys MCP skill available at:")
        for path in installed:
            print(f"  {path}")
        return 0
    print("No MCP skill installed; existing contents were preserved.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
