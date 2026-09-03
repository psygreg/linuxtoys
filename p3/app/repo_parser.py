import json
import os
import re
import shlex
import hashlib
from urllib.parse import urlparse

from .compat import get_system_compat_keys
from .dev_mode import get_effective_compat_keys
from . import official_index

OS_KEYS = {
    "debian",
    "ubuntu",
    "cachy",
    "arch",
    "fedora",
    "rhel",
    "suse",
    "ostree",
    "ublue",
    "zorin",
    "solus",
    "pika",
    "deepin",
    "manjaro",
}

VALID_TYPES = {"git", "flathub", "native", "repository", "url"}

URL_PACKAGE_KEYS = {
    "deb",
    "rpm",
    "pacman",
    "pkg.tar.zst",
    "flatpak",
    "appimage",
}

NATIVE_PACKAGE_KEY_PRIORITY = (
    "ublue",
    "deepin",
    "zorin",
    "pika",
    "manjaro",
    "cachy",
    "ostree",
    "ubuntu",
    "debian",
    "fedora",
    "rhel",
    "suse",
    "solus",
    "arch",
)

def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    return []


def _normalize_hardware_key(kind, value):
    value = str(value).strip().lower()

    if value in ("", "all"):
        return None

    if value.startswith(f"{kind}-"):
        return value

    return f"{kind}-{value}"


def _entry_is_compatible(entry, compat_keys):
    # OS compatibility
    os_value = entry.get("os")

    if os_value:
        requested = set(_as_list(os_value))

        if not requested or not requested <= OS_KEYS:
            return False

        if not requested & compat_keys:
            return False

    # Optional init-system compatibility.
    if not _systemd_requirement_matches(entry, compat_keys):
        return False

    install_type = entry.get("type", "git")

    # Flatpak installations implicitly require systemd.
    if install_type == "flathub":
        if "systemd" not in compat_keys:
            return False

    elif install_type == "url":
        resolved = _resolve_url_package(entry, compat_keys)

        if not resolved:
            return False

        package_type, _ = resolved

        if package_type == "flatpak" and "systemd" not in compat_keys:
            return False

    # Hardware compatibility
    hardware = entry.get("hardware", {})
    if hardware:
        if not isinstance(hardware, dict):
            return False

        for kind in ("gpu", "cpu"):
            values = _as_list(hardware.get(kind))

            if not values:
                continue

            required = {
                key
                for value in values
                if (key := _normalize_hardware_key(kind, value))
            }

            if required and not (required & compat_keys):
                return False

    return True


def _required_fields_present(entry):
    return all(
        isinstance(entry.get(field), str) and entry[field].strip()
        for field in ("name", "repo", "description", "category")
    )


def _validate_type(entry):
    install_type = entry.get("type", "git")

    if install_type not in VALID_TYPES:
        return False

    if install_type == "flathub":
        return bool(entry.get("package-name"))

    if install_type == "native":
        return bool(entry.get("package-name"))

    if install_type == "url":
        urls = entry.get("urls")
        if not isinstance(urls, dict) or not urls:
            return False
        return any(
            key in URL_PACKAGE_KEYS and _valid_package_url(value)
            for key, value in urls.items()
        )

    # Placeholder entries shouldn't currently be displayed because
    # they cannot yet be installed correctly.
    if install_type == "repository":
        return False

    return True

def _load_json_entries(path):
    """
    Load repository entries from one JSON file.

    A file may contain either one entry object or a list of entries.
    Invalid/unreadable files are ignored independently.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        return []

    if isinstance(data, dict):
        return [data]

    if isinstance(data, list):
        return data

    return []


def _get_repo_list_paths(scripts_dir):
    """
    Return all repository-list JSON files in deterministic order.

    repos.json is loaded first for backwards compatibility, followed by
    every .json file found recursively under scripts/lists/.
    """
    paths = []

    main_path = os.path.join(scripts_dir, "repos.json")
    if os.path.isfile(main_path):
        paths.append(main_path)

    lists_dir = os.path.join(scripts_dir, "lists")

    if os.path.isdir(lists_dir):
        discovered = []

        for root, dirs, files in os.walk(lists_dir):
            # Make traversal deterministic.
            dirs.sort()

            for filename in sorted(files):
                if filename.lower().endswith(".json"):
                    discovered.append(
                        os.path.join(root, filename)
                    )

        paths.extend(discovered)

    return paths

def load_repo_entries(scripts_dir, translations=None):
    data = []

    for path in _get_repo_list_paths(scripts_dir):
        data.extend(_load_json_entries(path))

    compat_keys = get_effective_compat_keys()
    result = []
    seen_names = set()

    for entry in data:
        if not isinstance(entry, dict):
            continue

        if not _required_fields_present(entry):
            continue

        if not _validate_type(entry):
            continue

        if not _entry_is_compatible(entry, compat_keys):
            continue

        # Script names are also used as registry identities and virtual paths,
        # so duplicate names from separate list files would be ambiguous.
        normalized_name = entry["name"].strip().casefold()

        if normalized_name in seen_names:
            continue

        seen_names.add(normalized_name)

        description = entry["description"]
        description_tag = entry.get("description_tag", "")

        if (
            description_tag
            and translations
            and description_tag in translations
        ):
            description = translations[description_tag]

        item = dict(entry)

        item.update({
            "description": description,
            "description_tag": description_tag,
            "icon": entry.get("icon", "application-x-executable"),
            "type": entry.get("type", "git"),

            # Make it behave exactly like a script in the UI.
            "is_script": True,
            "is_subcategory": False,
            "is_repo_entry": True,
            "revert": "yes",
            "reboot": "no",
            "is_new": False,

            # Virtual identity, NOT an actual shell script.
            "path": f"repo://{entry['name']}",

            "is_verified": official_index.is_verified_name(
                entry["name"]
            ),
        })

        result.append(item)

    return result


def get_entries_for_category(scripts_dir, category_path, translations=None):
    category = os.path.basename(os.path.normpath(category_path))

    return [
        entry
        for entry in load_repo_entries(scripts_dir, translations)
        if entry["category"] == category
    ]


def _resolve_native_package(entry, compat_keys):
    package = entry.get("package-name")

    if isinstance(package, str):
        return package.strip() or None

    if not isinstance(package, dict):
        return None

    for key in NATIVE_PACKAGE_KEY_PRIORITY:
        if key not in compat_keys:
            continue

        value = package.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    value = package.get("all")
    if isinstance(value, str) and value.strip():
        return value.strip()

    return None

def _valid_package_url(value):
    if not isinstance(value, str) or not value.strip():
        return False

    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False

    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _resolve_url_package(entry, compat_keys):
    """
    Resolve the best downloadable package for the current system.

    Returns:
        tuple[str, str] | None:
            (package_type, url)
    """
    urls = entry.get("urls")

    if not isinstance(urls, dict):
        return None

    native_keys = []

    if compat_keys & {
        "debian",
        "ubuntu",
        "deepin",
        "zorin",
        "pika",
    }:
        native_keys.append("deb")

    if compat_keys & {
        "fedora",
        "rhel",
        "suse",
        "ostree",
        "ublue",
    }:
        native_keys.append("rpm")

    if compat_keys & {
        "arch",
        "cachy",
        "manjaro",
    }:
        native_keys.extend(("pkg.tar.zst", "pacman"))

    # Prefer a native package.
    for key in native_keys:
        value = urls.get(key)

        if _valid_package_url(value):
            return key, value.strip()

    # Portable fallbacks.
    for key in ("appimage", "flatpak"):
        value = urls.get(key)

        if _valid_package_url(value):
            return key, value.strip()

    return None


def _metadata_line(value):
    """Keep generated metadata comments to a single harmless line."""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def create_install_script(entry):
    """
    Create the transient .sh consumed by the normal LinuxToys execution flow.

    Returns its filesystem path.
    """
    install_type = entry.get("type", "git")
    name = _metadata_line(entry["name"])
    description = _metadata_line(entry["description"])
    repo = entry["repo"]
    repo_metadata = _metadata_line(repo)
    icon = _metadata_line(entry.get("icon", "application-x-executable"))

    command = None

    if install_type == "git":
        command = f"pkg_fromrelease {shlex.quote(repo)}"

    elif install_type == "flathub":
        package = entry.get("package-name")
        if not isinstance(package, str) or not package.strip():
            raise ValueError("Flathub entry has no package-name")

        command = f"pkg_flat {shlex.quote(package.strip())}"

    elif install_type == "native":
        compat_keys = get_system_compat_keys()
        package = _resolve_native_package(entry, compat_keys)

        if not package:
            raise ValueError(
                "No native package name matches this operating system"
            )

        command = f"pkg_install {shlex.quote(package)}"

    elif install_type == "url":
        compat_keys = get_system_compat_keys()
        resolved = _resolve_url_package(entry, compat_keys)

        if not resolved:
            raise ValueError(
                "No downloadable package URL matches this operating system"
            )

        _, package_url = resolved

        command = f"pkg_fromurl {shlex.quote(package_url)}"

    elif install_type == "repository":
        raise NotImplementedError(
            "Third-party repository entries are not implemented yet"
        )

    else:
        raise ValueError(f"Unknown repository entry type: {install_type}")

    contents = f"""#!/usr/bin/env bash
# name: {name}
# description: {description}
# icon: {icon}
# repo: {repo_metadata}
# revert: yes

PACKAGE_OPS=1
source "$SCRIPT_DIR/libs/linuxtoys.bash"

{command}

info "$finishmsg"
"""

    tmp_dir = "/tmp/linuxtoys/repo-scripts"
    os.makedirs(tmp_dir, mode=0o700, exist_ok=True)

    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-._") or "entry"
    identity = hashlib.sha256(
        f"{entry.get('name', '')}\0{entry.get('repo', '')}".encode("utf-8")
    ).hexdigest()[:12]
    path = os.path.join(tmp_dir, f"{safe_name}-{identity}.sh")
    tmp_path = f"{path}.tmp"

    try:
        with open(tmp_path, "w", encoding="utf-8") as file:
            file.write(contents)

        os.chmod(tmp_path, 0o700)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return path


def materialize_repo_script(script_info):
    """Return an execution-ready copy of a dynamic repository entry."""
    if not script_info.get("is_repo_entry"):
        return script_info

    materialized = dict(script_info)
    materialized["virtual_path"] = script_info.get("path")
    materialized["path"] = create_install_script(script_info)
    return materialized

def _systemd_requirement_matches(entry, compat_keys):
    """
    Check an entry's optional systemd requirement.

    systemd:
      omitted / "" -> neutral
      "yes"        -> requires systemd
      "no"         -> requires non-systemd

    Invalid values make the entry incompatible.
    """
    value = entry.get("systemd", "")

    if value is None:
        value = ""

    if not isinstance(value, str):
        return False

    value = value.strip().lower()

    if not value:
        return True

    if value == "yes":
        return "systemd" in compat_keys

    if value == "no":
        return "systemd" not in compat_keys

    return False