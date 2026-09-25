import os
import threading


_SCRIPT_FILE_CACHE_LOCK = threading.RLock()
_SCRIPT_FILE_CACHE = {}
_SCRIPT_FILE_PATH_LOCKS = {}
_HOST_COMPAT_CACHE_LOCK = threading.RLock()
_HOST_COMPAT_CACHE = {}


def _script_file_signature(path):
    """Return a cheap signature suitable for invalidating cached script data."""
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def seed_script_file_cache(records):
    """Seed parsed script data produced by the Rust structural-index pass.

    Compatibility policy stays in Python; this only prevents those checks from
    reopening files whose content and headers Rust has already parsed.
    """
    prepared = []
    for record in records or ():
        if not isinstance(record, dict):
            continue
        path = os.path.realpath(str(record.get("path") or ""))
        signature = record.get("signature")
        if not path or not isinstance(signature, (tuple, list)) or len(signature) != 2:
            continue
        try:
            normalized_signature = (int(signature[0]), int(signature[1]))
        except (TypeError, ValueError):
            continue
        headers = record.get("headers")
        header_lines = record.get("header_lines")
        content = record.get("content")
        if not isinstance(headers, dict) or not isinstance(content, str):
            continue
        prepared.append((
            path,
            normalized_signature,
            {
                "content": content,
                "header_lines": tuple(header_lines or ()),
                "headers": dict(headers),
            },
        ))

    if not prepared:
        return

    with _SCRIPT_FILE_CACHE_LOCK:
        for path, signature, data in prepared:
            _SCRIPT_FILE_CACHE[path] = (signature, data)


def clear_script_file_cache():
    """Discard cached script headers/content and per-path synchronization state."""
    with _SCRIPT_FILE_CACHE_LOCK:
        _SCRIPT_FILE_CACHE.clear()
        _SCRIPT_FILE_PATH_LOCKS.clear()


def clear_host_compat_cache():
    """Discard cached host probes used to build compatibility context."""
    with _HOST_COMPAT_CACHE_LOCK:
        _HOST_COMPAT_CACHE.clear()


def clear_runtime_caches():
    """Discard all compatibility-layer runtime caches."""
    clear_script_file_cache()
    clear_host_compat_cache()


def _cached_host_value(key, builder):
    """Compute a host property once per process and reuse it safely."""
    with _HOST_COMPAT_CACHE_LOCK:
        if key not in _HOST_COMPAT_CACHE:
            _HOST_COMPAT_CACHE[key] = builder()
        return _HOST_COMPAT_CACHE[key]


def get_script_file_data(script_path):
    """Read and parse a shell script once, allowing unrelated files in parallel.

    A short global lock protects cache/lock dictionaries only. Each physical script
    gets its own lock so concurrent category workers can read different files at the
    same time while callers racing on the same file still coalesce to one read.
    """
    path = os.path.realpath(script_path)
    signature = _script_file_signature(path)
    if signature is None:
        return {"content": "", "header_lines": (), "headers": {}}

    with _SCRIPT_FILE_CACHE_LOCK:
        cached = _SCRIPT_FILE_CACHE.get(path)
        if cached is not None and cached[0] == signature:
            return cached[1]
        path_lock = _SCRIPT_FILE_PATH_LOCKS.setdefault(path, threading.RLock())

    # Serialize only callers targeting this same file. Other script paths can perform
    # their disk reads and header parsing concurrently.
    with path_lock:
        # Another worker may have populated the entry while this caller waited.
        with _SCRIPT_FILE_CACHE_LOCK:
            cached = _SCRIPT_FILE_CACHE.get(path)
            if cached is not None and cached[0] == signature:
                return cached[1]

        try:
            with open(path, "r", encoding="utf-8") as script_file:
                content = script_file.read()
        except (OSError, UnicodeError):
            content = ""

        header_lines = []
        headers = {}
        for line in content.splitlines():
            if not line.startswith("#"):
                break
            header_lines.append(line)
            if line.startswith("# "):
                line_content = line[2:].strip()
                key, separator, value = line_content.partition(":")
                if separator:
                    headers[key.strip().lower()] = value.strip()

        data = {
            "content": content,
            "header_lines": tuple(header_lines),
            "headers": headers,
        }

        with _SCRIPT_FILE_CACHE_LOCK:
            _SCRIPT_FILE_CACHE[path] = (signature, data)
        return data


def _detect_containerized():
    """Perform the actual host container probe without developer overrides."""
    container_env_vars = [
        "container",
        "CONTAINER_ID",
        "DOCKER_CONTAINER",
        "PODMAN_CONTAINER",
    ]

    for var in container_env_vars:
        if os.environ.get(var):
            return True

    for file_path in ("/.dockerenv", "/run/.containerenv"):
        if os.path.exists(file_path):
            return True

    try:
        with open("/proc/1/cgroup", "r") as f:
            cgroup_content = f.read()
        if any(indicator in cgroup_content for indicator in ("docker", "lxc", "containerd", "podman")):
            return True
    except Exception:
        pass

    try:
        if os.system("command -v systemd-detect-virt >/dev/null 2>&1") == 0:
            return os.system("systemd-detect-virt --container >/dev/null 2>&1") == 0
    except Exception:
        pass

    return False


def is_containerized():
    """Return container state, honoring developer simulation and caching host detection."""
    try:
        from .dev_mode import should_simulate_container

        if should_simulate_container():
            return True
    except ImportError:
        pass

    return bool(_cached_host_value("containerized", _detect_containerized))


def get_linuxtoys_cache_dir():
    """Return LinuxToys' cache root, isolated by distro ID inside containers.

    Host executions retain the historical ~/.cache/linuxtoys path. Containerized
    executions use ~/.cache/linuxtoys/<ID>, where ID comes from /etc/os-release.
    """
    base_dir = os.path.expanduser("~/.cache/linuxtoys")
    if not is_containerized():
        return base_dir

    os_id = "container"
    try:
        with open("/etc/os-release", "r", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                key, separator, value = raw_line.rstrip().partition("=")
                if separator and key == "ID":
                    candidate = value.strip().strip('"').strip("'").casefold()
                    # Keep the directory a single safe path component.
                    candidate = "".join(
                        char for char in candidate
                        if char.isalnum() or char in ("-", "_", ".")
                    ).strip(".")
                    if candidate:
                        os_id = candidate
                    break
    except OSError:
        pass

    return os.path.join(base_dir, os_id)

def _detect_wsl():
    try:
        with open("/proc/sys/kernel/osrelease", "r", encoding="utf-8") as f:
            if "microsoft" in f.read().lower():
                return True
    except OSError:
        pass

    try:
        with open("/proc/version", "r", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def is_wsl():
    """Return True when Linux is running under WSL, probing the host once."""
    return bool(_cached_host_value("wsl", _detect_wsl))

def is_supported_system():
    """
    Check if the current system is supported by LinuxToys.

    A system is considered supported if it matches at least one of the
    supported OS compatibility keys (debian, ubuntu, cachy, arch, fedora, rhel, suse, ostree, ublue).

    In developer mode:
    - If COMPAT is set to simulate a specific system, that system's compatibility is checked
    - If COMPAT is not set (show all scripts), returns True (skip the check)

    Returns:
        bool: True if the system is supported, False otherwise
    """
    # Check if developer mode override is active
    try:
        from .dev_mode import get_dev_compat_override, is_dev_mode_enabled

        if is_dev_mode_enabled() and not get_dev_compat_override():
            # Developer mode without specific system simulation - skip check
            return True
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass

    # Explicitly block unsupported distributions
    os_release = {}
    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os_release[k] = v.strip('"')
    except Exception:
        pass

    id_val = os_release.get("ID", "").lower()
    id_like = os_release.get("ID_LIKE", "").lower()

    # Block vanilla OS
    if id_val == "vanilla":
        return False

    # Block unsupported Ubuntu versions (only noble and resolute are supported)
    if id_val == "ubuntu":
        version_codename = os_release.get("VERSION_CODENAME", "").lower()
        if version_codename not in ["noble", "resolute"]:
            return False
    elif "ubuntu" in id_like:
        # For Ubuntu-based distros, check UBUNTU_CODENAME for supported versions
        ubuntu_codename = os_release.get("UBUNTU_CODENAME", "").lower()
        if ubuntu_codename not in ["noble", "resolute"]:
            return False

    # Get system compatibility keys
    compat_keys = get_system_compat_keys()

    # Define the set of supported OS compatibility keys
    supported_os_keys = {
        "debian",
        "ubuntu",
        "cachy",
        "arch",
        "steamos",
        "fedora",
        "rhel",
        "suse",
        "ostree",
        "ublue",
        "zorin",
        "solus",
        "pika",
        "deepin",
        "manjaro"
    }

    # Check if any OS compatibility key matches
    return bool(compat_keys & supported_os_keys)


def get_system_compat_keys():
    """
    Get the system compatibility keys.

    In developer mode, this can be overridden to simulate different systems
    or show all scripts regardless of compatibility.

    Returns:
        set: Set of compatibility keys for the current system
               (OS keys: debian, ubuntu, cachy, arch, fedora, rhel, suse, ostree, ublue;
              GPU keys: gpu, gpu-amd, gpu-intel, gpu-nvidia;
              Desktop keys: desktop, desktop-gnome, desktop-plasma, desktop-hyprland, desktop-sway, desktop-other;
              Init keys: systemd;
              Session keys: x11, wayland)
    """
    # Check if developer mode override is active
    try:
        from .dev_mode import get_effective_compat_keys, is_dev_mode_enabled

        if is_dev_mode_enabled():
            return get_effective_compat_keys()
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass

    with _HOST_COMPAT_CACHE_LOCK:
        cached_keys = _HOST_COMPAT_CACHE.get("system_compat_keys")
        if cached_keys is not None:
            return set(cached_keys)

    keys = set()
    os_release = {}
    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os_release[k] = v.strip('"')
    except Exception:
        pass

    id_val = os_release.get("ID", "").lower()
    id_like = os_release.get("ID_LIKE", "").lower()
    is_rhel_family = (
        id_val in ["rhel", "centos", "almalinux"] or "rhel" in id_like
    )

    if (id_val in ["debian"] or id_val in ["deepin"] or "debian" in id_like) and (id_val not in ["ubuntu"] and "ubuntu" not in id_like):
        keys.add("debian")
    if id_val in ["ubuntu"]:
        # Only add ubuntu compat key for supported versions (noble, resolute)
        version_codename = os_release.get("VERSION_CODENAME", "").lower()
        if version_codename in ["noble", "resolute", "stonking"]:
            keys.add("ubuntu")
    elif "ubuntu" in id_like:
        # For Ubuntu-based distros, check UBUNTU_CODENAME for supported versions
        ubuntu_codename = os_release.get("UBUNTU_CODENAME", "").lower()
        if ubuntu_codename in ["noble", "resolute", "stonking"]:
            keys.add("ubuntu")
    if id_val in ["zorin"] or "zorin" in id_like:
        keys.add("zorin")
    if id_val in ["pika"]:
        keys.add("pika")
    if id_val in ["deepin"]:
        keys.add("deepin")
    if id_val in ["biglinux", "bigcommunity", "manjaro"] or "manjaro" in id_like:
        keys.add("manjaro")
    if id_val in ["cachyos"]:
        keys.add("cachy")
    if id_val == "steamos":
        keys.add("steamos")
    if (
        id_val in ["arch", "archlinux", "artix"]
        or "arch" in id_like
        or "archlinux" in id_like
    ) and id_val not in {"cachyos", "steamos"}:
        keys.add("arch")
    if is_rhel_family:
        keys.add("rhel")
    if id_val in ["fedora"] or ("fedora" in id_like and not is_rhel_family):
        keys.add("fedora")
    if id_val in ["suse", "opensuse"] or "suse" in id_like or "opensuse" in id_like:
        keys.add("suse")
    if id_val in ["solus"]:
        keys.add("solus")

    # Check for rpm-ostree immutable distros
    import os

    if os.system("command -v rpm-ostree >/dev/null 2>&1") == 0:
        if id_val in ["bazzite"] or id_val in ["bluefin"] or id_val in ["aurora"]:
            keys = {"ublue", "ostree"}
        else:
            keys = {"ostree"}  # Override all other keys

    # Add GPU compatibility keys
    gpu_keys = get_gpu_compat_keys()
    keys.update(gpu_keys)

    # Add CPU compat keys
    cpu_keys = get_cpu_compat_keys()
    keys.update(cpu_keys)

    # Add desktop compatibility keys
    desktop_keys = get_desktop_compat_keys()
    keys.update(desktop_keys)

    # Add init system compatibility keys
    init_keys = get_init_compat_keys()
    keys.update(init_keys)

    # Add session type compatibility keys
    session_keys = get_current_session_type()
    keys.update(session_keys)

    with _HOST_COMPAT_CACHE_LOCK:
        _HOST_COMPAT_CACHE["system_compat_keys"] = frozenset(keys)
    return set(keys)


def get_gpu_compat_keys():
    """
    Get the GPU compatibility keys based on detected GPUs.

    Returns:
           set: Set of GPU compatibility keys ('gpu', 'gpu-amd', 'gpu-intel',
               'gpu-nvidia', 'gpu-rocm', 'gpu-xe', 'hybridgpu')
    """
    keys = set()
    try:
        import subprocess

        result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=10)
        lspci_output = result.stdout.lower()

        has_amd = "radeon" in lspci_output or "rx" in lspci_output
        has_intel = False
        has_nvidia = "nvidia" in lspci_output

        # Check Intel GPU by ensuring 'intel' and ('vga' or '3d') are in the same line
        for line in lspci_output.split("\n"):
            if "intel" in line and ("vga" in line or "3d" in line):
                has_intel = True
                break

        if has_amd or has_intel or has_nvidia:
            keys.add("gpu")
        if has_amd:
            keys.add("gpu-amd")
        if has_intel:
            keys.add("gpu-intel")
        if has_nvidia:
            keys.add("gpu-nvidia")
        if _is_rocm_capable():
            keys.add("gpu-rocm")
        if _is_icr_capable():
            keys.add("gpu-xe")
        if has_nvidia and (has_amd or has_intel):
            keys.add("hybridgpu")
    except Exception:
        pass
    return keys


def _is_rocm_capable():
    """Mirror is_rocm_capable from the shell library."""
    import glob
    import re

    for device in glob.glob("/sys/bus/pci/devices/*"):
        try:
            with open(f"{device}/vendor", encoding="utf-8") as f:
                vendor = f.read().strip()
            with open(f"{device}/class", encoding="utf-8") as f:
                device_class = f.read().strip()
            if vendor != "0x1002" or not device_class.startswith("0x03"):
                continue
            for vram_file in glob.glob(f"{device}/drm/card*/device/mem_info_vram_total"):
                with open(vram_file, encoding="utf-8") as f:
                    if int(f.read().strip()) >= 2073741824:
                        return True
        except (OSError, ValueError):
            continue

    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            cpu_model = next(
                (line.split(":", 1)[1].strip() for line in f if line.startswith("model name")),
                "",
            )
        if "AMD Ryzen" not in cpu_model:
            return False
        if "Ryzen AI " in cpu_model:
            return True
        match = re.search(r"Ryzen\s+.*(\d{4})", cpu_model)
        return bool(match and int(match.group(1)) >= 8000 and ("U" in cpu_model or "H" in cpu_model))
    except OSError:
        return False


def _is_icr_capable():
    """Mirror is_icr_capable from the shell library."""
    import glob
    import subprocess

    for device in glob.glob("/sys/bus/pci/devices/*"):
        try:
            with open(f"{device}/vendor", encoding="utf-8") as f:
                vendor = f.read().strip()
            with open(f"{device}/class", encoding="utf-8") as f:
                device_class = f.read().strip()
            if vendor != "0x8086" or not device_class.startswith("0x03"):
                continue
            with open(f"{device}/modalias", encoding="utf-8") as f:
                modalias = f.read().strip()
            result = subprocess.run(
                ["modprobe", "-R", modalias],
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
            if "xe" in result.stdout.splitlines():
                return True
        except (OSError, subprocess.SubprocessError):
            continue
    return False

def get_cpu_compat_keys():
    """
    Get the CPU compatibility keys based on detected CPU vendor.

    Returns:
        Single compatibility key 'intel' or 'amd', generic 'cpu' placeholder for default (no header, compatible with any CPU) scripts
    """
    keys = {"cpu"}
    try:
        vendor_id = None
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("vendor_id"):
                    vendor_id = line.split(":", 1)[1].strip()
                    if "GenuineIntel" in vendor_id:
                        keys.add("cpu-intel")
                    if "AuthenticAMD" in vendor_id:
                        keys.add("cpu-amd")
                    break

    except Exception:
        pass
    return keys

def get_desktop_compat_keys():
    """
    Get the desktop environment compatibility keys based on detected DE.

    Returns:
        set: Set of desktop compatibility keys ('desktop', 'desktop-gnome', 'desktop-plasma', 'desktop-hyprland', 'desktop-sway', 'desktop-other')
    """
    keys = set()
    import os

    desktop_parts = os.environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":")
    if "GNOME" in desktop_parts:
        keys.add("desktop-gnome")
    elif "KDE" in desktop_parts:
        keys.add("desktop-plasma")
    elif "HYPRLAND" in desktop_parts:
        keys.add("desktop-hyprland")
    elif "SWAY" in desktop_parts:
        keys.add("desktop-sway")
    else:
        keys.add("desktop-other")

    if keys:
        keys.add("desktop")

    return keys


def is_systemd():
    """
    Detect if the system is running systemd as the init system.

    Detection method:
    1. Use 'ps 1' to get the init process name
    2. If it contains 'systemd', system is using systemd
    3. If it returns '/sbin/init', check if it's a symlink to systemd

    Returns:
        bool: True if systemd is the init system, False otherwise
    """
    import subprocess

    try:
        # Use ps -p 1 to get the init process
        result = subprocess.run(
            ["ps", "-p", "1", "-o", "comm="],
            capture_output=True,
            text=True,
            timeout=5
        )
        init_process = result.stdout.strip()

        # Check if process is systemd
        if "systemd" in init_process:
            return True

        # If it's /sbin/init, check if it's a symlink to systemd
        if init_process in ["/sbin/init", "init"]:
            try:
                # Check if /sbin/init is a symlink to systemd
                readlink_result = subprocess.run(
                    ["readlink", "/sbin/init"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                symlink_target = readlink_result.stdout.strip()
                if "systemd" in symlink_target:
                    return True
            except Exception:
                pass

    except Exception:
        pass

    return False


def get_init_compat_keys():
    """
    Get the init system compatibility keys based on detected init system.

    Returns:
        set: Set of init system compatibility keys ('systemd' if systemd is running, empty set otherwise)
    """
    keys = set()
    if is_systemd():
        keys.add("systemd")
    return keys

def get_current_session_type():
    """
    Get the current session type (X11 or Wayland).

    Returns:
        set: Set of session type keys ('wayland' if running in a Wayland session, 'x11' if running in an X11/Xlibre session)
    """
    import os
    keys = set()

    # Check for Wayland session
    wayland_display = os.environ.get("WAYLAND_DISPLAY")
    if wayland_display:
        keys.add("wayland")
    else:
        keys.add("x11")
    return keys

def are_optimizations_installed():
    """
    Check if system optimizations have been applied.

    This function checks for the presence of the autopatch state file
    which indicates that LinuxToys optimizations have been installed.

    In developer mode:
    - If OPTIMIZER=1 is set, simulate optimizations being installed (return True)
    - If OPTIMIZER=0 is set, simulate optimizations not being installed (return False)
    - If OPTIMIZER is not set, use actual file detection

    Returns:
        bool: True if optimizations are installed, False otherwise
    """
    import os

    # Check for developer mode optimizer simulation
    try:
        from .dev_mode import (
            should_simulate_optimizations_installed,
            should_simulate_optimizations_not_installed,
        )

        if should_simulate_optimizations_installed():
            return True  # Simulate optimizations installed
        if should_simulate_optimizations_not_installed():
            return False  # Simulate optimizations not installed
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass

    autopatch_state_file = os.path.expanduser("~/.local/.autopatch.state")
    return os.path.exists(autopatch_state_file)



def _script_has_optimized_only_header(script_path):
    """Check whether the cached script header contains optimized-only metadata."""
    return "optimized-only" in get_script_file_data(script_path)["headers"]

def should_show_optimization_script(script_path):
    """
    Determine if an optimization-related script should be shown based on current state.

    Hiding rules:
    - Scripts with '# optimized-only:' header are hidden when optimizations ARE installed

    The '# optimized-only:' header marks scripts as part of the recommended optimizations,
    so they are hidden when the system already has optimizations installed.

    In developer mode:
    - Without OPTIMIZER set: override optimization checks (show all scripts)
    - With OPTIMIZER=1 or OPTIMIZER=0: apply optimization simulation logic

    Args:
        script_path (str): Path to the script file

    Returns:
        bool: True if the script should be shown, False if it should be hidden
    """

    # Check for developer mode optimizer override
    try:
        from .dev_mode import should_override_optimizer_checks

        if should_override_optimizer_checks():
            return True  # Override: always show all optimization scripts
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass

    # Check for optimized-only header
    optimizations_installed = are_optimizations_installed()
    has_optimized_only = _script_has_optimized_only_header(script_path)

    # If script has optimized-only header and optimizations are installed, hide it
    if has_optimized_only and optimizations_installed:
        return False

    return True  # Show all other scripts normally



def script_uses_flatpak_in_lib(script_path):
    """Check if a script uses the flatpak_in_lib function."""
    return "flatpak_in_lib" in get_script_file_data(script_path)["content"]

def _script_installs_container_incompatible_package(content):
    """Detect Flatpak/AppImage installation helpers in a script."""
    import re

    # These package types are sandboxed/desktop-oriented and must not be
    # installed from inside a container. Keep this automatic restriction
    # separate from the optional # nocontainer metadata so it acts as a
    # hard guardrail.
    if re.search(r"\b(?:flatpak_in_lib|pkg_flat|pkg_appimage)\b", content):
        return True

    # pkg_fromurl can also be used for portable packages. Catch the cases
    # that are statically identifiable from the command/URL itself.
    for line in content.splitlines():
        if not re.search(r"\bpkg_fromurl\b", line):
            continue
        lowered = line.lower()
        if any(marker in lowered for marker in (".appimage", ".flatpak", ".flatpakref")):
            return True

    return False



def script_is_container_compatible(script_path):
    """
    Check if a script should be shown in containerized environments.

    Scripts are incompatible when they install sandboxed packages in a
    container, or when their nocontainer metadata excludes the current host.
    """
    try:
        from .dev_mode import should_override_container_checks

        if should_override_container_checks():
            return True
    except ImportError:
        pass

    data = get_script_file_data(script_path)
    content = data["content"]

    try:
        installs_sandboxed_package = _script_installs_container_incompatible_package(content)
        nocontainer_keys = None
        has_invert = False

        for line in data["header_lines"]:
            if line.startswith("# nocontainer"):
                if ":" in line:
                    nocontainer_line = line[line.index(":") + 1 :].strip()
                    if nocontainer_line:
                        keys = [k.strip() for k in nocontainer_line.split(",")]
                        has_invert = "invert" in keys
                        nocontainer_keys = {k for k in keys if k != "invert"}
                    else:
                        nocontainer_keys = set()
                else:
                    nocontainer_keys = set()
                break

        is_in_container = is_containerized()

        if installs_sandboxed_package and is_in_container:
            return False

        if nocontainer_keys is not None:
            if has_invert:
                if not is_in_container:
                    return False
                if nocontainer_keys:
                    return bool(get_system_compat_keys() & nocontainer_keys)
                return True

            if not is_in_container:
                return True
            if not nocontainer_keys:
                return False
            return not bool(get_system_compat_keys() & nocontainer_keys)
    except Exception:
        pass

    return True


def _script_requires_systemd_functions(script_path):
    """Check cached script content for implicit systemd-only helper usage."""
    content = get_script_file_data(script_path)["content"]
    if "pkg_flat" in content:
        return True

    import re
    return bool(re.search(r"\bsysd_\w+", content))

def _detect_host_device_ids():
    """Scan PCI/USB IDs once for device-specific compatibility headers."""
    import glob

    device_ids = set()
    device_buses = (
        ("/sys/bus/pci/devices/*", "vendor", "device"),
        ("/sys/bus/usb/devices/*", "idVendor", "idProduct"),
    )

    for device_glob, vendor_file, product_file in device_buses:
        for device_path in glob.glob(device_glob):
            try:
                with open(f"{device_path}/{vendor_file}", encoding="utf-8") as f:
                    vendor_id = f.read().strip().lower().removeprefix("0x")
                with open(f"{device_path}/{product_file}", encoding="utf-8") as f:
                    product_id = f.read().strip().lower().removeprefix("0x")
                device_ids.update({vendor_id, product_id, f"{vendor_id}:{product_id}"})
            except OSError:
                continue

    return frozenset(device_ids)


def get_host_device_ids():
    """Return cached normalized PCI/USB IDs as a fresh set for callers."""
    return set(_cached_host_value("host_device_ids", _detect_host_device_ids))

def script_is_compatible(script_path, compat_keys):
    """
    Check if a script is compatible with the given compatibility keys.

    In developer mode without COMPAT override, all scripts are considered compatible.

    Args:
        script_path (str): Path to the script file
        compat_keys (set): Set of compatibility keys for the current system

    Returns:
        bool: True if script is compatible, False otherwise
    """
    # Check if developer mode override is active
    try:
        from .dev_mode import get_dev_compat_override, is_dev_mode_enabled

        if is_dev_mode_enabled() and not get_dev_compat_override():
            # Developer mode without specific system simulation - show all scripts
            return True
    except ImportError:
        # dev_mode not available, continue with normal behavior
        pass

    os_compatible = True
    gpu_compatible = True  # Default for unset GPU header
    desktop_compatible = True  # Default for unset desktop header
    systemd_compatible = True  # Default for unset systemd header
    wsl_compatible = True  # Default for unset WSL header (works on WSL and non-WSL)
    wayland_compatible = True  # Default for unset wayland header (presume neutrality)
    cpu_compatible = True # Default for unset cpu header
    hybridgpu_compatible = True  # Default for unset hybridgpu header
    device_compatible = True  # Default for an unset deviceids header
    has_explicit_systemd_header = False  # Track if systemd header was explicitly set

    try:
        for line in get_script_file_data(script_path)["header_lines"]:
                if line.startswith("# compat:"):
                    compat_line = line[len("# compat:") :].strip()
                    key_strings = [k.strip() for k in compat_line.split(",")]
                    include_keys = set()
                    exclude_keys = set()

                    # Parse keys into include (whitelist) and exclude (blacklist)
                    for key_str in key_strings:
                        if key_str.startswith("!"):
                            exclude_keys.add(key_str[1:])
                        else:
                            include_keys.add(key_str)

                    # Check whitelist (include keys) - if specified, script must match at least one
                    if include_keys:
                        os_compatible = bool(compat_keys & include_keys)
                    else:
                        # No whitelist specified, default to True
                        os_compatible = True

                    # Check blacklist (exclude keys) - if specified, script must not match any
                    if exclude_keys:
                        os_compatible = os_compatible and not bool(
                            compat_keys & exclude_keys
                        )
                elif line.startswith("# gpu:"):
                    gpu_value = line[len("# gpu:") :].strip()
                    gpu_values = [v.strip() for v in gpu_value.split(",") if v.strip()]
                    gpu_script_keys = set()
                    for v in gpu_values:
                        v_lower = v.lower()
                        if v_lower == "amd":
                            gpu_script_keys.add("gpu-amd")
                        elif v_lower == "intel":
                            gpu_script_keys.add("gpu-intel")
                        elif v_lower == "nvidia":
                            gpu_script_keys.add("gpu-nvidia")
                        elif v_lower == "rocm":
                            gpu_script_keys.add("gpu-rocm")
                        elif v_lower == "xe":
                            gpu_script_keys.add("gpu-xe")
                        else:
                            # Unknown value, treat as general GPU
                            gpu_script_keys.add("gpu")
                    if gpu_script_keys:
                        gpu_compatible = bool(compat_keys & gpu_script_keys)
                    else:
                        # Empty header, treat as general GPU
                        gpu_compatible = "gpu" in compat_keys
                elif line.startswith("# desktop:"):
                    desktop_value = line[len("# desktop:") :].strip()
                    desktop_values = [
                        v.strip() for v in desktop_value.split(",") if v.strip()
                    ]
                    desktop_script_keys = set()
                    for v in desktop_values:
                        if v.lower() == "gnome":
                            desktop_script_keys.add("desktop-gnome")
                        elif v.lower() == "plasma":
                            desktop_script_keys.add("desktop-plasma")
                        elif v.lower() == "hyprland":
                            desktop_script_keys.add("desktop-hyprland")
                        elif v.lower() == "sway":
                            desktop_script_keys.add("desktop-sway")
                        elif v.lower() == "other":
                            desktop_script_keys.add("desktop-other")
                        else:
                            # Unknown value, treat as general desktop
                            desktop_script_keys.add("desktop")
                    if desktop_script_keys:
                        desktop_compatible = bool(compat_keys & desktop_script_keys)
                    else:
                        # Empty header, treat as general desktop
                        desktop_compatible = "desktop" in compat_keys
                elif line.startswith("# systemd:"):
                    has_explicit_systemd_header = True
                    # systemd header with optional value (e.g., "yes" or "no" - for flexibility)
                    systemd_value = line[len("# systemd:") :].strip().lower()
                    # If header exists and is explicitly "no", script requires non-systemd
                    if systemd_value == "no":
                        systemd_compatible = "systemd" not in compat_keys
                    else:
                        # Default: "yes" or empty means script requires systemd
                        systemd_compatible = "systemd" in compat_keys
                elif line.startswith("# wsl:"):
                    wsl_value = line[len("# wsl:") :].strip().lower()
                    if wsl_value == "yes":
                        wsl_compatible = is_wsl()
                    elif wsl_value == "no":
                        wsl_compatible = not is_wsl()
                    else:
                        # Invalid explicit values fail closed instead of silently
                        # making a script available in the wrong environment.
                        wsl_compatible = False
                elif line.startswith("# wayland:"):
                    wayland_value = line[len("# wayland:") :].strip().lower()
                    if wayland_value in ["yes", "true"]:
                        wayland_compatible = "wayland" in compat_keys
                    elif wayland_value in ["no", "false"]:
                        wayland_compatible = "x11" in compat_keys
                elif line.startswith("# cpu:"):
                    cpu_val = line[len("# cpu:") :].strip()
                    cpu_vals = [v.strip() for v in cpu_val.split(",") if v.strip()]
                    cpu_script_keys = set()
                    for v in cpu_vals:
                        v_lower = v.lower()
                        if v_lower == "amd":
                            cpu_script_keys.add("cpu-amd")
                        elif v_lower == "intel":
                            cpu_script_keys.add("cpu-intel")
                        else:
                            cpu_script_keys.add("cpu")
                    if cpu_script_keys:
                        cpu_compatible = bool(compat_keys & cpu_script_keys)
                    else:
                        # Empty header, treat as general GPU
                        cpu_compatible = "cpu" in compat_keys
                elif line.startswith("# hybridgpu:"):
                    hybridgpu_value = line[len("# hybridgpu:") :].strip().lower()
                    if hybridgpu_value == "only":
                        hybridgpu_compatible = "hybridgpu" in compat_keys
                    elif "hybridgpu" in compat_keys:
                        if hybridgpu_value == "no":
                            hybridgpu_compatible = False
                        elif hybridgpu_value not in ("", "yes"):
                            hybridgpu_values = [
                                value.strip()
                                for value in hybridgpu_value.split(",")
                                if value.strip()
                            ]
                            include_keys = {
                                value for value in hybridgpu_values if not value.startswith("!")
                            }
                            exclude_keys = {
                                value[1:]
                                for value in hybridgpu_values
                                if value.startswith("!") and len(value) > 1
                            }
                            hybridgpu_compatible = (
                                (not include_keys or bool(compat_keys & include_keys))
                                and not bool(compat_keys & exclude_keys)
                            )
                elif line.startswith("# deviceids:"):
                    device_ids = {
                        device_id.strip().lower().removeprefix("0x")
                        for device_id in line[len("# deviceids:") :].split(",")
                        if device_id.strip()
                    }
                    device_compatible = bool(device_ids & get_host_device_ids())
                if not line.startswith("#"):
                    break
    except Exception:
        pass

    # If no explicit systemd header was found, check for implicit systemd requirements
    # via function calls (pkg_flat or sysd_*)
    if not has_explicit_systemd_header and _script_requires_systemd_functions(script_path):
        systemd_compatible = "systemd" in compat_keys

    # If no explicit wayland header, presume neutrality (script works on both X11 and Wayland)
    # wayland_compatible remains True by default

    return os_compatible and gpu_compatible and desktop_compatible and systemd_compatible and wsl_compatible and wayland_compatible and cpu_compatible and hybridgpu_compatible and device_compatible



def script_is_localized(script_path, current_locale):
    """
    Check if a script should be shown for the current locale.
    No localize header means visible by default.
    """
    localize_line = get_script_file_data(script_path)["headers"].get("localize")
    if localize_line is None:
        return True
    localize_keys = {
        key.strip().lower()
        for key in localize_line.split(",")
        if key.strip()
    }
    return current_locale.lower() in localize_keys


def get_revert_capability(script_path, compat_keys=None):
    """Return the script's cached revert capability metadata."""
    if compat_keys is None:
        compat_keys = get_system_compat_keys()

    revert_line = get_script_file_data(script_path)["headers"].get("revert")
    if revert_line is None:
        return "yes"

    revert_line = revert_line.strip().lower()
    if revert_line in ("", "yes"):
        return "yes"
    if revert_line == "no":
        return "no"
    if revert_line == "internal":
        return "internal"

    key_strings = [key.strip() for key in revert_line.split(",")]
    include_keys = set()
    exclude_keys = set()
    for key_string in key_strings:
        if key_string.startswith("!"):
            exclude_keys.add(key_string[1:])
        else:
            include_keys.add(key_string)

    return {
        "type": "conditional",
        "include_keys": include_keys,
        "exclude_keys": exclude_keys,
        "compat_keys": compat_keys,
    }

def should_enable_manual_revert(script_path, compat_keys=None):
    """
    Determine if manual uninstallation (remove button) should be available for a script.

    Returns True if:
    - revert header is 'yes' or not set (default)
    - revert header is conditional and script matches the compat conditions

    Returns False if:
    - revert header is 'no'
    - revert header is 'internal'
    - revert header is conditional and system doesn't match the conditions

    Args:
        script_path (str): Path to the script file
        compat_keys (set): Set of compatibility keys for the current system (optional)

    Returns:
        bool: True if manual revert should be enabled, False otherwise
    """
    if compat_keys is None:
        compat_keys = get_system_compat_keys()

    revert_capability = get_revert_capability(script_path, compat_keys)

    if revert_capability == "yes":
        return True
    elif revert_capability == "no":
        return False
    elif revert_capability == "internal":
        return False
    elif isinstance(revert_capability, dict) and revert_capability.get("type") == "conditional":
        # Check if system matches the compat conditions
        include_keys = revert_capability.get("include_keys", set())
        exclude_keys = revert_capability.get("exclude_keys", set())
        script_compat_keys = revert_capability.get("compat_keys", compat_keys)

        # If include keys specified (whitelist)
        if include_keys:
            matches_include = bool(script_compat_keys & include_keys)
        else:
            # No whitelist specified
            matches_include = True

        # If exclude keys specified (blacklist)
        if exclude_keys:
            matches_exclude = bool(script_compat_keys & exclude_keys)
        else:
            # No blacklist specified
            matches_exclude = False

        return matches_include and not matches_exclude

    return True  # Default to True

def is_script_compatible_with_host(script_path):
    return script_is_compatible(script_path, get_system_compat_keys())

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--check-script":
        sys.exit(
            0 if is_script_compatible_with_host(sys.argv[2]) else 1
        )

    sys.exit(2)
