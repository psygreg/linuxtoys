import os
import re
import shlex
import subprocess
import tempfile
from urllib.parse import urlparse


def _run_ok(cmd):
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
    except Exception:
        return False


def _detect_package_manager():
    if _run_ok(["bash", "-lc", "command -v rpm-ostree >/dev/null 2>&1"]):
        return "rpm-ostree"
    if _run_ok(["bash", "-lc", "command -v apt >/dev/null 2>&1"]):
        return "apt"
    if _run_ok(["bash", "-lc", "command -v dnf >/dev/null 2>&1"]):
        return "dnf"
    if _run_ok(["bash", "-lc", "command -v pacman >/dev/null 2>&1"]):
        return "pacman"
    if _run_ok(["bash", "-lc", "command -v zypper >/dev/null 2>&1"]):
        return "zypper"
    if _run_ok(["bash", "-lc", "command -v eopkg >/dev/null 2>&1"]):
        return "eopkg"
    return None


def _extract_bash_array(content, array_name):
    # Match both = (initial assignment) and += (augmentation)
    matches = re.findall(
        rf"{re.escape(array_name)}\s*(?:=|\+=)\s*\((.*?)\)",
        content,
        flags=re.DOTALL,
    )
    values = set()
    for raw in matches:
        try:
            tokens = shlex.split(raw.replace("\n", " "))
        except Exception:
            continue
        for token in tokens:
            if not token or token.startswith("-") or "$" in token:
                continue
            values.add(token.strip())
    return values


def _parse_flatpak_installs(content):
    flatpaks = set()

    # Preferred path: explicit array declarations used with _flatpak_
    # Note: _flatpak_() library function determines scope at runtime,
    # so we need to check both scopes for each app_id
    for app_id in _extract_bash_array(content, "_flatpaks"):
        if "." in app_id and "/" not in app_id:
            # Mark for both scopes since we'll filter by actual installation later
            flatpaks.add((app_id, "user"))
            flatpaks.add((app_id, "system"))

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "flatpak" not in stripped or "install" not in stripped:
            continue
        try:
            tokens = shlex.split(stripped)
        except Exception:
            continue

        if "flatpak" not in tokens or "install" not in tokens:
            continue

        scope = "system" if "--system" in tokens else "user"
        app_start = None
        if "flathub" in tokens:
            app_start = tokens.index("flathub") + 1
        if app_start is None:
            continue

        for token in tokens[app_start:]:
            if not token or token.startswith("-") or "$" in token:
                continue
            if "/" in token:
                # ignore runtime refs like org.foo.Bar/x86_64/24.08
                continue
            if "." not in token:
                continue
            flatpaks.add((token, scope))

    return flatpaks


def _has_flatpak_bundle_install(content):
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "flatpak" not in stripped or "install" not in stripped:
            continue
        if ".flatpak" in stripped or "TMP_BUNDLE" in stripped:
            return True
    return False


def _parse_direct_package_installs(content):
    packages = set()
    install_markers = (
        " apt install ",
        " apt-get install ",
        " dnf install ",
        " dnf in ",
        " pacman -S ",
        " zypper in ",
        " zypper install ",
        " rpm-ostree install ",
        " eopkg install ",
        " eopkg it ",
    )

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "$" in stripped:
            continue

        lowered = f" {stripped.lower()} "
        if not any(marker in lowered for marker in install_markers):
            continue

        try:
            tokens = shlex.split(stripped)
        except Exception:
            continue

        if "install" in tokens:
            idx = tokens.index("install") + 1
        elif "in" in tokens and ("dnf" in tokens or "zypper" in tokens):
            idx = tokens.index("in") + 1
        elif "it" in tokens and "eopkg" in tokens:
            idx = tokens.index("it") + 1
        elif "-S" in tokens and "pacman" in tokens:
            idx = tokens.index("-S") + 1
        else:
            continue

        for token in tokens[idx:]:
            if not token or token.startswith("-"):
                continue
            if token.endswith((".rpm", ".deb", ".pkg.tar.zst", ".tar.xz", ".tar.gz")):
                continue
            if "/" in token or "=" in token:
                continue
            packages.add(token)

    return packages


def _filter_bootstrap_packages(packages):
    # Avoid removing basic tools often installed only as prerequisites,
    # and system packages that are foundational infrastructure.
    bootstrap = {
        "bash",
        "curl",
        "flatpak",
        "zenity",
        "sudo",
        "wget",
        "git",
        "ca-certificates",
        "gnupg",
        "gpg",
        "lsb-release",
        "software-properties-common",
        "coreutils",
        "grep",
        "sed",
        "tar",
        "gzip",
        "xz",
        "unzip",
        "dbus",
        "xdg-utils",
        "fuse",
        "fuse2",
        # Audio/multimedia infrastructure (core system services)
        "wireplumber",
        "pipewire",
        "pulseaudio",
        # X11/Wayland display infrastructure (needed for many apps)
        "xwayland",
        "xorg-xwayland",
        "xorg-x11-server-xwayland",
        "wayland",
        # Xorg display server and related (legacy but may cause cascading removal)
        "xorg",
        "xorg-server",
        "xorg-apps",
        "xorg-fonts",
        "xorg-xinit",
        "xorg-xserver",
        "x11-common",
        "x11-utils",
    }
    return {pkg for pkg in packages if pkg not in bootstrap}


def _extract_repo_slug(repo_url):
    if not repo_url:
        return ""
    try:
        parsed = urlparse(repo_url)
        path = parsed.path.strip("/")
        if not path:
            return ""
        return path.split("/")[-1].lower()
    except Exception:
        return ""


def _build_flatpak_match_patterns(script_info):
    name = str(script_info.get("name", "")).strip().lower()
    repo_slug = _extract_repo_slug(script_info.get("repo", ""))
    patterns = set()
    if name:
        patterns.add(name)
        compact = re.sub(r"[^a-z0-9]+", "", name)
        if compact:
            patterns.add(compact)
        dashed = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
        if dashed:
            patterns.add(dashed)
    if repo_slug:
        patterns.add(repo_slug)
        patterns.add(repo_slug.replace("-", ""))
    return sorted(p for p in patterns if len(p) >= 3)


def _is_package_installed(pkg, manager):
    if not manager or not pkg:
        return False
    if manager == "apt":
        return _run_ok(["dpkg", "-s", pkg])
    if manager == "pacman":
        return _run_ok(["pacman", "-Qi", pkg])
    if manager in ("dnf", "zypper", "rpm-ostree"):
        return _run_ok(["rpm", "-q", pkg])
    if manager == "eopkg":
        return _run_ok(["bash", "-lc", f"eopkg list-installed | grep -q -- {shlex.quote(pkg)}"])
    return False


def _is_flatpak_installed(app_id, scope):
    if not _run_ok(["bash", "-lc", "command -v flatpak >/dev/null 2>&1"]):
        return False
    scope_flag = "--system" if scope == "system" else "--user"
    return _run_ok(["flatpak", "info", scope_flag, app_id])


def _check_bootstrap_collateral(packages_to_remove, manager):
    """
    Check if removing packages would cause bootstrap packages to be removed as dependencies.
    Returns a set of bootstrap packages that would be affected, or empty set if safe.
    """
    bootstrap = {
        "bash", "curl", "flatpak", "zenity", "sudo", "wget", "git",
        "ca-certificates", "gnupg", "gpg", "lsb-release",
        "software-properties-common", "coreutils", "grep", "sed", "tar",
        "gzip", "xz", "unzip", "dbus", "xdg-utils", "fuse", "fuse2",
        "wireplumber", "pipewire", "pulseaudio", "xwayland",
        "xorg-xwayland", "xorg-x11-server-xwayland", "wayland",
        "xorg", "xorg-server", "xorg-apps", "xorg-fonts", "xorg-xinit",
        "xorg-xserver", "x11-common", "x11-utils",
    }
    
    if not packages_to_remove or not manager:
        return set()
    
    # Dry-run commands for different package managers
    if manager == "apt":
        cmd = ["sudo", "apt", "autoremove", "-s"] + packages_to_remove
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            # Check if bootstrap packages appear in removal output
            affected = set()
            for pkg in bootstrap:
                if f"Removing {pkg} " in result.stdout or f"Remv {pkg} " in result.stdout:
                    affected.add(pkg)
            return affected
        except Exception:
            return set()
    
    elif manager == "pacman":
        cmd = ["pacman", "-Rns", "--dry-run"] + packages_to_remove
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            affected = set()
            for pkg in bootstrap:
                if f"remove {pkg}" in result.stdout:
                    affected.add(pkg)
            return affected
        except Exception:
            return set()
    
    elif manager in ("dnf", "zypper"):
        # These are aggressive about dependencies; safer to check explicitly
        cmd = [manager, "remove", "-y", "--setopt=clean_requirements_on_remove=true", "--dry-run"] + packages_to_remove
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            affected = set()
            for pkg in bootstrap:
                if pkg in result.stdout:
                    affected.add(pkg)
            return affected
        except Exception:
            return set()
    
    elif manager == "eopkg":
        cmd = ["sudo", "eopkg", "remove", "-n"] + packages_to_remove
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            affected = set()
            for pkg in bootstrap:
                if pkg in result.stdout:
                    affected.add(pkg)
            return affected
        except Exception:
            return set()
    
    # For other managers, return empty (no check available)
    return set()


def _detect_java_uninstall_candidates(package_manager):
    """
    Java OpenJDK script builds package names dynamically, so static parsing misses them.
    Return a conservative set of candidate package names by distro family.
    """
    if package_manager == "apt":
        candidates = []
        for v in (8, 11, 17, 21, 24):
            candidates.extend([f"openjdk-{v}-jdk", f"openjdk-{v}-jre"])
        return candidates

    if package_manager in ("dnf", "rpm-ostree"):
        candidates = ["java-1.8.0-openjdk", "java-1.8.0-openjdk-devel"]
        for v in (11, 17, 21, 24):
            candidates.extend([f"java-{v}-openjdk", f"java-{v}-openjdk-devel"])
        return candidates

    if package_manager == "zypper":
        candidates = []
        for v in (8, 11, 17, 21, 24):
            candidates.extend([f"java-{v}-openjdk", f"java-{v}-openjdk-devel"])
        return candidates

    # solus/other fallback based on java.sh behavior
    return ["openjdk-11", "openjdk-17", "openjdk-21"]


def _detect_script_package_candidates(script_basename, package_manager):
    if script_basename == "java.sh":
        return _detect_java_uninstall_candidates(package_manager)
    if script_basename == "positron.sh":
        return ["positron"]
    if script_basename == "rstudio.sh":
        return ["rstudio"]
    return []


def _detect_desktop_cleanup_candidates(script_basename):
    desktop_map = {
        "positron.sh": [
            "~/.local/share/applications/positron.desktop",
            "/usr/share/applications/positron.desktop",
        ],
        "rstudio.sh": [
            "~/.local/share/applications/rstudio.desktop",
            "/usr/share/applications/rstudio.desktop",
        ],
    }
    return desktop_map.get(script_basename, [])


def build_uninstall_script_entry(script_info, translations=None):
    """
    Build a temporary uninstall script for a given LinuxToys script.
    Returns a script_info-like dict or None when no removable components were found.
    """
    script_path = script_info.get("path")
    if not script_path or not os.path.isfile(script_path):
        return None

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    package_manager = _detect_package_manager()
    package_candidates = set()
    package_candidates.update(_extract_bash_array(content, "_packages"))
    package_candidates.update(_parse_direct_package_installs(content))

    script_basename = os.path.basename(script_path).lower()
    package_candidates.update(
        _detect_script_package_candidates(script_basename, package_manager)
    )

    package_candidates = _filter_bootstrap_packages(package_candidates)

    installed_packages = sorted(
        pkg for pkg in package_candidates if _is_package_installed(pkg, package_manager)
    )

    flatpak_candidates = _parse_flatpak_installs(content)
    has_bundle_install = _has_flatpak_bundle_install(content)
    installed_flatpaks = sorted(
        (app_id, scope)
        for app_id, scope in flatpak_candidates
        if _is_flatpak_installed(app_id, scope)
    )
    flatpak_match_patterns = _build_flatpak_match_patterns(script_info)
    desktop_cleanup_candidates = _detect_desktop_cleanup_candidates(script_basename)
    existing_desktop_entries = [
        desktop for desktop in desktop_cleanup_candidates if os.path.exists(os.path.expanduser(desktop))
    ]

    if (
        not installed_packages
        and not installed_flatpaks
        and not has_bundle_install
        and not existing_desktop_entries
    ):
        return None

    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    manager_remove_map = {
        "apt": "sudo apt autoremove -y",
        "dnf": "sudo dnf remove -y",
        "pacman": "sudo pacman -Rns --noconfirm",
        "zypper": "sudo zypper rm -y",
        "rpm-ostree": "sudo rpm-ostree uninstall",
        "eopkg": "sudo eopkg rmf -y",
    }
    pkg_remove_cmd = manager_remove_map.get(package_manager)

    lines = [
        "#!/bin/bash",
        'set -eo pipefail',
        f'SCRIPT_DIR="{script_dir}"',
        'source "$SCRIPT_DIR/libs/linuxtoys.lib"',
        'source "$SCRIPT_DIR/libs/helpers.lib"',
    ]

    needs_sudo = bool(installed_packages) or any(
        scope == "system" for _, scope in installed_flatpaks
    )
    needs_sudo = needs_sudo or any(
        os.path.expanduser(path).startswith("/usr/") for path in existing_desktop_entries
    )
    if needs_sudo:
        lines.append("sudo_rq")

    if installed_packages and pkg_remove_cmd:
        # Check if removing these packages would cause bootstrap packages to be removed
        affected_bootstrap = _check_bootstrap_collateral(installed_packages, package_manager)
        if affected_bootstrap:
            # Skip package removal if it would affect bootstrap packages
            quoted_affected = ", ".join(sorted(affected_bootstrap))
            lines.extend(
                [
                    f'echo "Warning: Removing these packages would also remove critical system packages: {quoted_affected}"',
                    f'echo "Skipping package removal to protect system stability."',
                ]
            )
        else:
            # Safe to remove - no bootstrap packages affected
            quoted = " ".join(shlex.quote(pkg) for pkg in installed_packages)
            lines.extend(
                [
                    f'echo "Removing packages: {quoted}"',
                    f"{pkg_remove_cmd} {quoted} || true",
                ]
            )

    user_flatpaks = [app for app, scope in installed_flatpaks if scope == "user"]
    system_flatpaks = [app for app, scope in installed_flatpaks if scope == "system"]

    if user_flatpaks:
        quoted = " ".join(shlex.quote(app) for app in user_flatpaks)
        lines.extend(
            [
                f'echo "Removing user flatpaks: {quoted}"',
                f"flatpak uninstall --noninteractive -y --delete-data --user {quoted} || true",
            ]
        )
    if system_flatpaks:
        quoted = " ".join(shlex.quote(app) for app in system_flatpaks)
        lines.extend(
            [
                f'echo "Removing system flatpaks: {quoted}"',
                f"flatpak uninstall --noninteractive -y --delete-data --system {quoted} || true",
            ]
        )

    # For scripts that install .flatpak bundles, dynamically locate matching apps by
    # name/app-id patterns and uninstall them from both user/system scopes.
    if has_bundle_install and flatpak_match_patterns:
        lines.extend(
            [
                "",
                "remove_flatpak_matches() {",
                "    local pattern=\"$1\"",
                "    local scope=\"$2\"",
                "    local scope_flag=\"--user\"",
                "    [ \"$scope\" = \"system\" ] && scope_flag=\"--system\"",
                "    flatpak list --app --columns=application,name | while IFS=$'\\t' read -r app_id app_name; do",
                "        [ -z \"$app_id\" ] && continue",
                "        if printf '%s %s\\n' \"$app_id\" \"$app_name\" | grep -qi -- \"$pattern\"; then",
                "            flatpak uninstall --noninteractive -y --delete-data \"$scope_flag\" \"$app_id\" || true",
                "        fi",
                "    done",
                "}",
                "",
            ]
        )
        for pattern in flatpak_match_patterns:
            quoted_pattern = shlex.quote(pattern)
            lines.append(f"remove_flatpak_matches {quoted_pattern} user || true")
            lines.append(f"remove_flatpak_matches {quoted_pattern} system || true")

    user_desktop_entries = [
        os.path.expanduser(path)
        for path in existing_desktop_entries
        if not os.path.expanduser(path).startswith("/usr/")
    ]
    system_desktop_entries = [
        os.path.expanduser(path)
        for path in existing_desktop_entries
        if os.path.expanduser(path).startswith("/usr/")
    ]

    if user_desktop_entries:
        quoted = " ".join(shlex.quote(path) for path in user_desktop_entries)
        lines.extend(
            [
                f'echo "Removing desktop entries: {quoted}"',
                f"rm -f {quoted} || true",
            ]
        )
    if system_desktop_entries:
        quoted = " ".join(shlex.quote(path) for path in system_desktop_entries)
        lines.extend(
            [
                f'echo "Removing system desktop entries: {quoted}"',
                f"sudo rm -f {quoted} || true",
            ]
        )

    lines.append('echo "Removal completed."')

    with tempfile.NamedTemporaryFile(
        mode="w", prefix="linuxtoys-uninstall-", suffix=".sh", delete=False
    ) as temp_script:
        temp_script.write("\n".join(lines) + "\n")
        temp_path = temp_script.name

    os.chmod(temp_path, 0o700)

    script_name = script_info.get("name", "Script")
    remove_name = (
        translations.get("remove_action_name", "Remove {name}")
        if translations
        else "Remove {name}"
    ).format(name=script_name)

    return {
        "icon": script_info.get("icon", "application-x-executable"),
        "name": remove_name,
        "description": translations.get(
            "remove_action_desc",
            "Automatically removes detected components installed by this script.",
        )
        if translations
        else "Automatically removes detected components installed by this script.",
        "repo": script_info.get("repo", ""),
        "path": temp_path,
        "is_script": True,
        "cleanup_path": temp_path,
    }
