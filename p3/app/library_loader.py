"""Detect Bash library requirements without executing the inspected code."""

import os
import atexit
import shutil
import tempfile
import threading
from pathlib import Path
import re
import shlex

_SESSION_LOCK = threading.Lock()
_SESSION_DIR = None


def _execution_session_dir():
    """Share one mirror preflight across runners and nested child processes."""
    inherited = os.environ.get("LINUXTOYS_EXECUTION_SESSION_DIR")
    if inherited:
        return inherited
    global _SESSION_DIR
    with _SESSION_LOCK:
        if _SESSION_DIR is None:
            _SESSION_DIR = tempfile.mkdtemp(prefix="linuxtoys-session-")
            atexit.register(shutil.rmtree, _SESSION_DIR, ignore_errors=True)
        return _SESSION_DIR


LIBRARY_FLAGS = {
    "fsops.bash": "FS_OPS",
    "packages.bash": "PACKAGE_OPS",
    "boot.bash": "BOOT_OPS",
    "misc.bash": "MISC_OPS",
    "sysd.bash": "SYSD_OPS",
    "helpers.bash": "HELPERS_OPS",
    "optimizers.bash": "OPTIMIZER_OPS",
}

LEGACY_SUMMONS = {
    "summon_helpers": "helpers.bash",
    "summon_optimizers": "optimizers.bash",
}

# Raw native package-manager commands in plain script bodies. These bypass the
# pkg_* helpers entirely — and with it the runner_lock preflight in
# linuxtoys.bash — so only scripts referencing them still carry the CachyOS
# mirror preflight through their preamble. (Chaotic/multilib-style repo
# scripts run pacman -Syy before any helper could.)
_RAW_NATIVE_MANAGER_WORDS = {
    "pacman", "paru", "pamac", "apt", "apt-get", "dpkg", "rpm",
    "dnf", "dnf5", "zypper", "rpm-ostree",
}
_FUNCTION = re.compile(
    r"^\s*(?:function\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(\s*\))?"
    r"|([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\))\s*\{", re.MULTILINE
)
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _words(text):
    # Keep quoted words: callbacks and commands in substitutions/strings may
    # name library functions too. This intentionally errs toward loading more.
    return set(_WORD.findall(re.sub(r"(?m)^\s*#.*$", "", text)))

def _list_hook_paths(script_text, script_dir):
    """Return statically referenced run_list_hook scripts."""
    paths = []
    base_paths = []

    cache_dir = os.environ.get("CACHE_DIR")
    if cache_dir:
        base_paths.append(Path(cache_dir) / "scripts" / "lists")

    base_paths.append(Path(script_dir) / "scripts" / "lists")

    for line in script_text.splitlines():
        try:
            words = shlex.split(line, comments=True)
        except ValueError:
            continue

        if len(words) != 2 or words[0] != "run_list_hook":
            continue

        hook = words[1]

        for base in base_paths:
            path = base / hook

            if path.is_file():
                paths.append(path)
                break

    return paths

def library_flags(script_text, script_dir):
    """Return (flags, referenced) for direct references and transitive deps.

    This is conservative static detection, not a Bash parser. Computed function
    names cannot be inferred; scripts can still explicitly set an *_OPS flag
    and source linuxtoys.bash for those cases. `referenced` holds the words
    the script (or its list hooks) itself names, before the transitive closure
    blends in library internals — the level the CachyOS mirror gate evaluates.
    """
    libs = Path(script_dir) / "libs"
    texts = {name: (libs / name).read_text(encoding="utf-8")
             for name in LIBRARY_FLAGS}
    functions = {
        name: {first or second for first, second in _FUNCTION.findall(text)}
        for name, text in texts.items()
    }
    required = _words(script_text)

    for hook_path in _list_hook_paths(script_text, script_dir):
        try:
            required.update(
                _words(hook_path.read_text(encoding="utf-8"))
            )
        except OSError:
            pass

    # Snapshot the words this script (or its list hooks) itself references,
    # before the core merge below adds library internals: linuxtoys.bash and
    # sysinfo.bash are attached to every run, and packages.bash also hosts the
    # Flatpak/Snap/AppImage helpers, so library-level words would make every
    # script look like a native transaction.
    referenced = set(required)

    # Core functions (notably init_transmap -> prep_tmp) need dependencies too.
    for name in ("linuxtoys.bash", "sysinfo.bash"):
        required.update(_words((libs / name).read_text(encoding="utf-8")))

    # Preserve legacy summon_* calls while treating those libraries as first-class
    # dynamic modules. Seeding the selection here also lets their dependencies
    # participate in the normal transitive dependency walk below.
    script_words = _words(script_text)
    selected = {filename for function, filename in LEGACY_SUMMONS.items()
                if function in script_words}
    for name in selected:
        required.update(_words(texts[name]))
    while True:
        added = {name for name in texts if name not in selected
                 and functions[name] & required}
        if not added:
            break
        selected.update(added)
        for name in added:
            required.update(_words(texts[name]))
    flags = {flag: "1" if name in selected else ""
             for name, flag in LIBRARY_FLAGS.items()}
    return flags, referenced


def script_preamble(script_text, script_dir):
    """Set invocation-local flags and always load the core before script code."""
    script_dir = os.path.abspath(script_dir)
    flags, referenced = library_flags(script_text, script_dir)
    lines = ["export SCRIPT_DIR=" + shlex.quote(script_dir),
             "export LINUXTOYS_EXECUTION_SESSION_DIR="
             + shlex.quote(_execution_session_dir())]
    lines.extend("export " + key + "=" + shlex.quote(value)
                 for key, value in flags.items())
    lines.append("source " + shlex.quote(str(Path(script_dir) / "libs/linuxtoys.bash"))
                 + " || exit $?")
    # The CachyOS mirror preflight is lazy: linuxtoys.bash performs it from
    # runner_lock the first time a run actually enters a native package
    # transaction, so helper-based scripts (pkg_install and everything reaching
    # it, including pkg_appimage/pkg_npm/pkg_make internals) need nothing here.
    # Raw manager calls in plain script bodies bypass the helpers entirely
    # (e.g. repos/multilib.sh running pacman -Syy), so only those runs carry
    # the preflight here, before any script code executes. A script header
    # opt-out (`cachyos-mirrors-required: 0`) remains available as an override,
    # and ${LINUXTOYS_REQUIRE_CACHYOS_MIRRORS} keeps exempting plain
    # Flatpak/Snap entries from a failed preflight.
    if (referenced & _RAW_NATIVE_MANAGER_WORDS
            and re.search(r"(?m)^#\s*cachyos-mirrors-required:\s*0\s*$", script_text) is None):
        lines.append(
            'if [[ ${LINUXTOYS_REQUIRE_CACHYOS_MIRRORS:-1} != 0 ]]; then\n'
            '_linuxtoys_prepare_session || exit $?\n'
            'fi'
        )
    return "\n".join(lines) + "\n"



def _requires_cachyos_mirrors(script_info):
    """Only plain non-native AppStream jobs may ignore failed mirror ranking."""
    if script_info.get("is_repo_entry"):
        return True
    if script_info.get("appstream_source") not in {"flatpak", "snap"}:
        return True
    if script_info.get("appstream_overrides") or script_info.get("appstream_dependencies"):
        return True
    return script_info.get("cachyos_mirrors_required", False)


def script_environment(script_info, base_env=None):
    """Return a child environment enriched with invocation-local app metadata."""
    env = dict(os.environ if base_env is None else base_env)
    env.setdefault("LINUXTOYS_EXECUTION_SESSION_DIR", _execution_session_dir())
    # Reset for every invocation: a nested native/curated script must not inherit
    # the exemption granted to its plain Flatpak/Snap caller.
    env["LINUXTOYS_REQUIRE_CACHYOS_MIRRORS"] = (
        "1" if _requires_cachyos_mirrors(script_info) else "0"
    )

    name = str(script_info.get("name") or "unknown")
    description = str(script_info.get("description") or "")
    icon = str(script_info.get("icon") or "application-x-executable")

    # Plain icon filenames always refer to LinuxToys' bundled app/icons directory.
    # Repository-local icons are already resolved to absolute paths by repo_parser.
    if (
        icon != "application-x-executable"
        and not os.path.isabs(icon)
        and "/" not in icon
    ):
        icon_path = Path(env["SCRIPT_DIR"]) / "app" / "icons" / icon
        if icon_path.is_file():
            icon = str(icon_path.resolve())

    identity = script_info.get("id") or script_info.get("script")
    identity_path = str(
        script_info.get("virtual_path")
        or script_info.get("path")
        or ""
    )

    if not identity and identity_path.startswith("repo://"):
        identity = identity_path[len("repo://"):]
    elif not identity and identity_path:
        identity = Path(identity_path).stem

    identity = str(identity or name).strip() or "application"

    env["LINUXTOYS_SCRIPT_NAME"] = name
    env["LINUXTOYS_APP_ID"] = identity
    env["LINUXTOYS_APP_NAME"] = name
    env["LINUXTOYS_APP_DESCRIPTION"] = description
    env["LINUXTOYS_APP_ICON"] = icon

    repo_app_id = script_info.get("repo_app_id")
    if script_info.get("is_repo_entry") and repo_app_id:
        env["LINUXTOYS_REPO_APP_ID"] = str(repo_app_id)
        env["LINUXTOYS_REPO_URL"] = str(script_info.get("repo") or "")
    else:
        env.pop("LINUXTOYS_REPO_APP_ID", None)
        env.pop("LINUXTOYS_REPO_URL", None)

    # AppImage release metadata resolved by the AppStream runner
    # (appimage_catalog.download_for_install). When present, pkg_appimage records
    # it alongside the install so version tracking can find it later — the same
    # role APP_GIT_VERSION / LINUXTOYS_REPO_APP_ID play for git-release entries.
    appimage_release = script_info.get("appimage_release")
    if isinstance(appimage_release, dict):
        for source_key, env_key in (
            ("app_id", "LINUXTOYS_APPIMAGE_ID"),
            ("version", "LINUXTOYS_APPIMAGE_VERSION"),
            ("repository", "LINUXTOYS_APPIMAGE_REPO"),
        ):
            value = str(appimage_release.get(source_key) or "").strip()
            if value:
                env[env_key] = value
            else:
                env.pop(env_key, None)
    else:
        for env_key in (
            "LINUXTOYS_APPIMAGE_ID",
            "LINUXTOYS_APPIMAGE_VERSION",
            "LINUXTOYS_APPIMAGE_REPO",
        ):
            env.pop(env_key, None)

    return env

def script_command(script_path, script_dir):
    """Build argv without interpolating the script path into shell code.

    $0 and BASH_SOURCE continue to identify the original script; the final
    source command propagates its return/exit status.
    """
    script_path = os.path.abspath(script_path)
    text = Path(script_path).read_text(encoding="utf-8")
    return ["/bin/bash", "-c", script_preamble(text, script_dir)
            + 'source "$0" "$@"\n', script_path]

def script_info_from_path(script_path, script_dir, base_env=None):
    """Build canonical script metadata for nested call_script execution."""
    env = os.environ if base_env is None else base_env
    path = Path(script_path).resolve()
    text = path.read_text(encoding="utf-8")

    headers = {}
    for line in text.splitlines():
        match = re.match(r"^#\s*([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            headers.setdefault(match.group(1).lower(), match.group(2).strip())

    name = headers.get("name") or path.stem
    description = headers.get("description") or ""

    # Script headers may contain localization keys rather than display text.
    try:
        import sys
        script_dir = os.path.abspath(script_dir)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        from app.lang_utils import load_translations
        translations = load_translations()
        name = translations.get(name, name)
        description = translations.get(description, description)
    except (ImportError, OSError, KeyError):
        pass

    info = {
        "path": str(path),
        "script": path.stem,
        "name": name,
        "description": description,
        "icon": headers.get("icon") or "application-x-executable",
    }

    source = headers.get("appstream-source")
    if source in {"flatpak", "snap", "native"}:
        info["appstream_source"] = source
        info["cachyos_mirrors_required"] = headers.get("cachyos-mirrors-required") != "0"

    # Repository entries are materialized before reaching this path. Preserve
    # their stable repository identity so script_environment() does not discard it.
    repo_app_id = env.get("LINUXTOYS_REPO_APP_ID")
    if repo_app_id:
        info["id"] = repo_app_id
        info["repo_app_id"] = repo_app_id
        info["repo"] = env.get("LINUXTOYS_REPO_URL", "")
        info["is_repo_entry"] = True

    return info


def exec_script(script_info, script_dir, argv=(), base_env=None):
    """Execute one script with the same canonical app identity as GUI runners."""
    env = script_environment(script_info, base_env)
    command = script_command(script_info["path"], script_dir)
    os.execve(command[0], command + list(argv), env)

def _appstream_phase_lines(entry):
    """Return reviewed AppStream overlay commands in normal runner order."""
    pre = []
    dependencies = []
    flatpak = []
    post = []

    overrides = entry.get("appstream_overrides")
    if not isinstance(overrides, dict):
        overrides = {}

    def hook_lines(phase):
        value = overrides.get(phase)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, dict):
            script = str(value.get("script", "") or "").strip()
            if script:
                return [f"run_list_hook {shlex.quote(script)}"]
        return []

    pre.extend(hook_lines("pre"))
    post.extend(hook_lines("post"))

    values = entry.get("appstream_dependencies")
    if isinstance(values, list):
        for dependency in values:
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
                    dependencies.append(f"pkg_install {shlex.quote(package)}")
                elif dependency_type == "flathub":
                    dependencies.append(f"pkg_flat {shlex.quote(package)}")

    if entry.get("appstream_source") == "flatpak":
        values = overrides.get("flatpak")
        if isinstance(values, list):
            for override in values:
                if not isinstance(override, dict):
                    continue
                flatpak.append(
                    "flatpak_override "
                    f"{shlex.quote(str(override.get('scope', '')).strip())} "
                    f"{shlex.quote(str(override.get('type', '')).strip())} "
                    f"{shlex.quote(str(override.get('setting', '')).strip())} "
                    f"{shlex.quote(str(override.get('target', '')).strip())}"
                )

    return pre, dependencies, flatpak, post


def _refresh_cold_appstream_catalog():
    """Synchronously rebuild the AppStream catalog when the last one is unusable.

    A nested call_script with an AppStream ID resolves against the last
    published catalog.json. On a fresh install that generation can be cold
    (never built) or a native-only starter generation — Flatpak-primary hosts
    excepted — so Flathub component ids such as it.mijorus.gearlever cannot
    resolve, and a newly configured Flathub remote may not even have its local
    AppStream database populated yet. refresh_cache() handles all of this
    (including _refresh_missing_flatpak_appstream), so one synchronous refresh
    makes CLI resolutions match what the AppStream UI already sees.

    Best effort: any failure leaves the previous generation untouched, and the
    caller falls back to the normal not-found behavior.
    """
    import sys

    try:
        from app import appstream_cache
    except ImportError:
        return False

    try:
        if appstream_cache.cache_needs_refresh():
            print("call_script: the AppStream catalog is not ready yet; refreshing it now...",
                  file=sys.stderr)
            appstream_cache.refresh_cache()
    except Exception:
        # A failed refresh keeps the previous published generation. The retry
        # below resolves against whatever generation exists afterwards.
        pass
    return True


def _resolution_scripts_trees(script_dir):
    """Return the scripts trees nested call_script resolution may consume.

    Nested call_script materialization must see the same repository apps the
    GUI lists and call_script's own physical scan searches: the ACTIVE scripts
    source from git_scripts_manager (the synced git cache in normal runs, the
    bundled copy in developer mode or before a first successful clone). The
    caller-provided app bundles tree stays as the fallback so resolution still
    reaches an entry whose app build is newer than the scripts cache, or whose
    listing reached the cache before the app rebuilt. Active tree first: it is
    the source the user actually sees.
    """
    trees = []
    try:
        # Absolute import: this helper also serves direct CLI execution of
        # library_loader.py, where relative imports have no package context.
        from app.git_scripts_manager import get_available_scripts_dir

        active = get_available_scripts_dir()
    except Exception:
        active = None
    if active and os.path.isdir(active):
        trees.append(active)
    bundled = os.path.join(os.path.abspath(script_dir), "scripts")
    if bundled not in trees and os.path.isdir(bundled):
        trees.append(bundled)
    return trees


def materialize_appstream_by_target(target, script_dir):
    """Resolve and materialize an AppStream app for nested call_script execution.

    IDs are preferred; exact localized/canonical display names are accepted as a
    convenience. Source selection and reviewed overlays come from appstream_parser,
    so this follows the same default source choice as the normal AppStream UI.
    """
    import sys

    script_dir = os.path.abspath(script_dir)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from app import appstream_parser, repo_parser

    scripts_dir = _resolution_scripts_trees(script_dir)[0]
    curated_entries = repo_parser.load_repo_entries(scripts_dir, translations=None)
    category_paths = []
    for root, dirs, _files in os.walk(scripts_dir):
        dirs[:] = [name for name in dirs if name != "lists"]
        relative = os.path.relpath(root, scripts_dir).replace(os.sep, "/")
        if relative != ".":
            category_paths.append(relative)

    def find_entry():
        entry = appstream_parser.find_entry_by_id(
            scripts_dir,
            target,
            curated_entries=curated_entries,
            category_paths=category_paths,
        )
        if entry is None:
            entry = appstream_parser.find_entry_by_name(
                scripts_dir,
                target,
                curated_entries=curated_entries,
                category_paths=category_paths,
            )
        return entry

    entry = find_entry()
    if entry is None:
        # The catalog can be cold or starter-only (native components only) on a
        # fresh install. One synchronous refresh repopulates it — including the
        # local Flathub AppStream database — then the lookup is retried once.
        _refresh_cold_appstream_catalog()
        entry = find_entry()
    if entry is None:
        return None

    # create_install_script() deliberately handles only the ordinary AppStream
    # package transaction. Keep overlays in the same order as AppStreamRunner:
    # pre -> dependencies -> install -> Flatpak overrides -> post.
    install_path = repo_parser.create_install_script(entry)
    try:
        install_text = Path(install_path).read_text(encoding="utf-8")
    finally:
        try:
            os.remove(install_path)
        except OSError:
            pass

    pre, dependencies, flatpak, post = _appstream_phase_lines(entry)
    lines = install_text.splitlines()
    if lines and lines[0].startswith("#!"):
        lines = lines[1:]
    install_body = "\n".join(lines).strip()

    contents = "#!/usr/bin/env bash\n"
    contents += f"# name: {str(entry.get('name') or target).replace(chr(10), ' ')}\n"
    contents += f"# description: {str(entry.get('description') or '').replace(chr(10), ' ')}\n"
    contents += f"# icon: {str(entry.get('icon') or 'application-x-executable').replace(chr(10), ' ')}\n"
    contents += "# appstream-source: " + str(entry.get("appstream_source") or "") + "\n"
    contents += "# cachyos-mirrors-required: " + ("1" if _requires_cachyos_mirrors(entry) else "0") + "\n"
    contents += "# revert: yes\n\n"
    for phase in (pre, dependencies):
        if phase:
            contents += "\n".join(phase) + "\n\n"
    contents += install_body + "\n"
    for phase in (flatpak, post):
        if phase:
            contents += "\n" + "\n".join(phase) + "\n"

    directory = "/tmp/linuxtoys/appstream-called"
    os.makedirs(directory, mode=0o700, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", str(entry.get("appstream_id") or target)).strip("-._") or "appstream"
    path = os.path.join(directory, f"{safe}.sh")
    tmp = path + ".tmp"
    try:
        Path(tmp).write_text(contents, encoding="utf-8")
        os.chmod(tmp, 0o700)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise

    return {
        "path": path,
        "name": str(entry.get("name") or target),
        "appstream_id": str(entry.get("appstream_id") or target),
        "source": str(entry.get("appstream_source") or ""),
    }


def materialize_repo_by_app_id(app_id, script_dir):
    """Resolve a repository-list entry by repo_app_id for nested call_script.

    Returns a ``(status, entry)`` pair:

    - ``"found"`` — entry is the execution-ready materialized script info.
    - ``"incompatible"`` — a listing declares this app, but not for this host
      (entry is None). Reported separately from "absent" so call_script can
      skip like it does for incompatible physical scripts instead of dying
      with "not found".
    - ``"absent"`` — no usable listing declares this app id (entry is None).

    Resolution walks the resolution trees (active source first, bundled copy
    as fallback) and accepts exactly one unambiguous match. A faulty tree is
    skipped so one broken source can never hide an otherwise resolvable app.
    A tree that declares the app at all delivers an authoritative verdict for
    this host: an entry excluded by compatibility reports "incompatible"
    without consulting older bundled copies of the same listing.
    """
    import sys

    script_dir = os.path.abspath(script_dir)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from app.repo_parser import (
        find_repo_entry_declarations,
        load_repo_entries,
        materialize_repo_script,
        repo_entry_statically_valid,
    )

    target = str(app_id or "").strip().upper()
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", target):
        return "absent", None

    for tree in _resolution_scripts_trees(script_dir):
        try:
            entries = load_repo_entries(tree, translations=None) or []
        except Exception:
            continue
        matches = [entry for entry in entries if entry.get("repo_app_id") == target]
        if len(matches) == 1:
            return "found", materialize_repo_script(matches[0])
        if len(matches) > 1:
            # Unreachable per tree (the resolved catalog deduplicates repo app
            # ids); kept as a defensive refusal rather than an arbitrary pick.
            return "absent", None
        # No compatible entry in this tree. If its listings declare the app at
        # all — and at least one declaration is schema-valid, so a broken
        # listing is not mistaken for a host restriction — this host cannot
        # install it: report the incompatibility rather than "not found".
        declarations = find_repo_entry_declarations(tree, target)
        if any(repo_entry_statically_valid(item) for item in declarations):
            return "incompatible", None
    return "absent", None


if __name__ == "__main__":
    # call_script uses this entry point for nested scripts. exec preserves the
    # child's exit status and lets the existing Bash caller manage transactions.
    import sys

    if len(sys.argv) >= 3 and sys.argv[1] == "--materialize-appstream":
        entry = materialize_appstream_by_target(sys.argv[2], os.environ["SCRIPT_DIR"])
        if not entry:
            sys.exit(3)
        print(entry["path"])
        print(entry["name"])
        print(entry["appstream_id"])
        print(entry["source"])
        sys.exit(0)

    if len(sys.argv) >= 3 and sys.argv[1] == "--materialize-repo":
        status, entry = materialize_repo_by_app_id(
            sys.argv[2], os.environ["SCRIPT_DIR"]
        )
        if status == "incompatible":
            # Distinct from "not found": the listing declares this repository
            # app, but the current host cannot install it. The Bash caller
            # reports the same skip it uses for incompatible physical scripts.
            sys.exit(4)
        if status != "found" or not entry:
            sys.exit(3)
        print(entry["path"])
        print(entry.get("name", sys.argv[2]))
        print(entry.get("repo", ""))
        sys.exit(0)

    if len(sys.argv) < 2:
        sys.exit("Usage: library_loader.py SCRIPT [ARG ...]")

    script_dir = os.environ["SCRIPT_DIR"]
    script_info = script_info_from_path(sys.argv[1], script_dir, os.environ)
    exec_script(script_info, script_dir, sys.argv[2:], os.environ)
