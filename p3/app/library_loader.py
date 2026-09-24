"""Detect Bash library requirements without executing the inspected code."""

import os
from pathlib import Path
import re
import shlex

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
    """Return flags for direct references and transitive library dependencies.

    This is conservative static detection, not a Bash parser. Computed function
    names cannot be inferred; scripts can still explicitly set an *_OPS flag
    and source linuxtoys.bash for those cases.
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
    return {flag: "1" if name in selected else ""
            for name, flag in LIBRARY_FLAGS.items()}


def script_preamble(script_text, script_dir):
    """Set invocation-local flags and always load the core before script code."""
    script_dir = os.path.abspath(script_dir)
    flags = library_flags(script_text, script_dir)
    lines = ["export SCRIPT_DIR=" + shlex.quote(script_dir)]
    lines.extend("export " + key + "=" + shlex.quote(value)
                 for key, value in flags.items())
    lines.append("source " + shlex.quote(str(Path(script_dir) / "libs/linuxtoys.bash"))
                 + " || exit $?")
    return "\n".join(lines) + "\n"



def script_environment(script_info, base_env=None):
    """Return a child environment enriched with invocation-local app metadata."""
    env = dict(os.environ if base_env is None else base_env)

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

    scripts_dir = os.path.join(script_dir, "scripts")
    curated_entries = repo_parser.load_repo_entries(scripts_dir, translations=None)
    category_paths = []
    for root, dirs, _files in os.walk(scripts_dir):
        dirs[:] = [name for name in dirs if name != "lists"]
        relative = os.path.relpath(root, scripts_dir).replace(os.sep, "/")
        if relative != ".":
            category_paths.append(relative)

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
    """Resolve a compatible repository-list entry by repo_app_id."""
    import sys

    script_dir = os.path.abspath(script_dir)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from app.repo_parser import load_repo_entries, materialize_repo_script

    target = str(app_id or "").strip().upper()
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", target):
        return None

    entries = load_repo_entries(os.path.join(script_dir, "scripts"), translations=None)
    matches = [entry for entry in entries if entry.get("repo_app_id") == target]
    if len(matches) != 1:
        return None

    return materialize_repo_script(matches[0])


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
        entry = materialize_repo_by_app_id(sys.argv[2], os.environ["SCRIPT_DIR"])
        if not entry:
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
