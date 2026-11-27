"""Nixpkgs catalog, setup discovery and queued operation materialization.

The Nix subsystem is deliberately self-managed: LinuxToys never installs
packages through ``nix-env``. It maintains a declarative ``linuxtoys.nix``
module for home-manager and for NixOS system packages, then rebuilds the
affected profile when the user applies queued operations.

This module owns discovery, the package snapshot cache and the generated
helper scripts. The heavy normalization/filtering lives in Rust
(``_catalog_rs.NixCatalog``), mirroring the other catalogs. The snapshot is
host-specific: its ``legacyPackages.<system>`` prefix must match the shared
architecture policy (x86_64-linux or aarch64-linux), and unsupported hosts
hide the subsystem instead of falling back to a foreign package set. The
evaluated snapshot also carries nixpkgs' broken/deprecated metadata so those
non-installable entries never reach the catalog.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from . import _catalog_rs
from .atomic_io import atomic_write_text

_CACHE_ROOT = Path(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
)
CACHE_DIR = _CACHE_ROOT / "linuxtoys" / "nix-catalog"
RAW_PATH = CACHE_DIR / "packages.json"
MAX_AGE = 14 * 24 * 60 * 60
MAX_BYTES = 128 * 1024 * 1024
SEARCH_TIMEOUT = 15 * 60
SNAPSHOT_SCHEMA = 2
_SNAPSHOT_MARKER = "_linuxtoys_snapshot"

# ``nix search`` only exposes pname/version/description. The snapshot therefore
# evaluates the top-level package set directly so broken and deprecated
# packages can be filtered by the Rust catalog instead of being offered for
# installation. Every package is isolated with tryEval, matching nix search's
# behaviour for attributes that fail evaluation.
_NIX_SNAPSHOT_EXPRESSION = r"""
pkgs:
let
  names = builtins.attrNames pkgs;
  prefix = "legacyPackages.__SYSTEM__.";
  row = name:
    let
      result = builtins.tryEval (
        let
          package = pkgs.${name};
          meta = package.meta or { };
          problems = meta.problems or { };
        in
        if (package.type or "") != "derivation" then null
        else {
          pname = package.pname or name;
          version = package.version or "";
          description = meta.description or "";
          broken = (meta.broken or false) || ((problems.broken or false) != false);
          deprecated = (meta.deprecated or false) || ((problems.deprecated or false) != false);
        }
      );
    in
    if result.success && result.value != null
    then [{ name = prefix + name; value = result.value; }]
    else [ ];
in
{ "__SNAPSHOT_MARKER__" = { schema = __SNAPSHOT_SCHEMA__; pname = ""; description = ""; }; } //
builtins.listToAttrs (builtins.concatMap row names)
"""

_HM_CONFIG_OVERRIDE = os.environ.get("HOME_MANAGER_CONFIG")
HOME_CONFIG_DIR = (
    Path(_HM_CONFIG_OVERRIDE).expanduser().parent
    if _HM_CONFIG_OVERRIDE
    else Path(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")) / "home-manager"
)
HOME_MODULE_PATH = Path(
    os.environ.get(
        "LINUXTOYS_NIX_HM_MODULE",
        str(HOME_CONFIG_DIR / "linuxtoys.nix"),
    )
)
SYSTEM_MODULE_PATH = Path(
    os.environ.get("LINUXTOYS_NIX_SYSTEM_MODULE", "/etc/nixos/linuxtoys.nix")
)
_ZONEINFO_LINK = Path("/etc/zoneinfo")
_ZONEINFO_SOURCE = Path("/usr/share/zoneinfo")
_ATTR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_'-]*$")
_MODULE_PACKAGE_RE = re.compile(
    r"^\s*pkgs\.([A-Za-z_][A-Za-z0-9_'-]*)\s*(?:#.*)?$", re.MULTILINE
)
_NIX_PACKAGE_RE = re.compile(r"^\s*nix\.package\s*=", re.MULTILINE)
_GPU_ENABLE_RE = re.compile(
    r"\b(?:targets\.genericLinux\.)?gpu\.enable\s*=\s*"
    r"(?:lib\.)?(?:mkDefault\s+|mkForce\s+)?true\b"
)
_GPU_BLOCK_ENABLE_RE = re.compile(
    r"\bgpu\s*=\s*\{[^{}]*\benable\s*=\s*"
    r"(?:lib\.)?(?:mkDefault\s+|mkForce\s+)?true\b",
    re.DOTALL,
)
_LOCK = threading.RLock()
_VALIDATED_SNAPSHOT = None
logger = logging.getLogger(__name__)


def nix_executable():
    """Discover the Nix client without relying on a desktop session PATH."""
    candidates = [
        shutil.which("nix"),
        os.environ.get("NIX_BIN"),
        os.path.expanduser("~/.nix-profile/bin/nix"),
        os.path.expanduser("~/.local/state/nix/profile/bin/nix"),
        "/nix/var/nix/profiles/default/bin/nix",
        "/run/current-system/sw/bin/nix",
        "/usr/bin/nix",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return os.path.abspath(candidate)
    return None


def auto_enabled():
    """Hosts where the Nix subsystem is enabled without a manual opt-in.

    NixOS and its derivatives ship Nix as their native package source, and
    GregOS includes Nix, Home Manager and the host GPU integration in the
    image. Those hosts keep the Nix catalog available even if the binary is
    temporarily missing from the current PATH.
    """
    if is_nixos():
        return True
    try:
        from .compat import is_gregos

        return bool(is_gregos())
    except Exception:
        return False


def enabled():
    # Presence is authoritative, exactly like Homebrew; the shared ISA policy
    # must also support the host before the Nix subsystem is offered. The
    # native Nix hosts (NixOS/derivatives and GregOS) are enabled by default.
    return bool(linux_arch()) and (nix_executable() is not None or auto_enabled())


def home_manager_available():
    if shutil.which("home-manager"):
        return True
    for candidate in (
        Path(os.path.expanduser("~/.nix-profile/bin/home-manager")),
        Path(os.path.expanduser("~/.local/state/nix/profile/bin/home-manager")),
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return True
    return False


def is_nixos():
    """Return True on NixOS and NixOS derivatives (cached host probe)."""
    try:
        from .compat import is_nixos as host_is_nixos

        return host_is_nixos()
    except Exception:
        return os.path.exists("/etc/NIXOS") or os.path.exists("/etc/nixos/configuration.nix")


def linux_arch():
    """Return the nixpkgs system of this host; empty on unsupported hosts.

    Nix itself understands many systems, but LinuxToys' architecture policy
    deliberately supports only x86_64 and aarch64. Returning an empty value
    (rather than silently claiming x86_64) keeps unsupported hosts from
    resolving or exporting a foreign package set.
    """
    try:
        from .architecture import label

        return f"{label('host')}-linux"
    except Exception:
        return ""


def scopes():
    """Available install scopes, user-level first."""
    if not enabled():
        return []
    result = []
    if home_manager_available():
        result.append("home-manager")
    if is_nixos():
        result.append("system")
    return result


def availability_fingerprint():
    return (nix_executable(), home_manager_available(), is_nixos())


def catalog_metadata():
    """Return the API category map and whether NixOS classification applies.

    Only NixOS hosts fold Nix packages into the normal LinuxToys categories.
    Elsewhere unmatched Nix packages stay in their own catalog category.
    """
    nixos = is_nixos()
    if not nixos:
        return {}, False
    try:
        from . import nix_metadata

        categories = nix_metadata.index_category_map()
    except Exception:
        categories = {}
    return categories, nixos


def _path_state(path):
    try:
        stat = path.stat()
        return (stat.st_size, stat.st_mtime_ns)
    except OSError:
        return None


def fingerprint():
    return json.dumps(
        {
            "executable": nix_executable(),
            "arch": linux_arch(),
            "raw": _path_state(RAW_PATH),
            "binary": _path_state(RAW_PATH.with_suffix(".bin")),
            "scopes": scopes(),
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _snapshot_system(path=None):
    """Read the nixpkgs system prefix from the start of a search snapshot.

    The snapshot emits keys such as ``legacyPackages.aarch64-linux.firefox``.
    All rows in one snapshot share the evaluated system, so the first key is
    enough. An empty result means the format was not recognized; callers keep
    the Rust snapshot validation as the authority in that case.
    """
    target = Path(path) if path is not None else RAW_PATH
    try:
        with target.open("rb") as handle:
            head = handle.read(8192)
    except OSError:
        return ""
    match = re.search(rb"legacyPackages\.([A-Za-z0-9_-]+)\.", head)
    return match.group(1).decode("ascii", "replace") if match else ""


def _snapshot_schema(path=None):
    """Read the LinuxToys snapshot schema marker written by the evaluator."""
    target = Path(path) if path is not None else RAW_PATH
    try:
        with target.open("rb") as handle:
            head = handle.read(16384)
    except OSError:
        return 0
    marker = re.escape(_SNAPSHOT_MARKER.encode("ascii"))
    match = re.search(
        rb'"' + marker + rb'"\s*:\s*\{[^{}]*?"schema"\s*:\s*(\d+)',
        head,
    )
    return int(match.group(1)) if match else 0


def valid_snapshot():
    """Validate the cached nixpkgs snapshot on a worker."""
    global _VALIDATED_SNAPSHOT
    expected_system = linux_arch()
    if not expected_system:
        return False
    try:
        stat = RAW_PATH.stat()
        token = (
            os.fspath(RAW_PATH),
            stat.st_size,
            stat.st_mtime_ns,
            stat.st_ctime_ns,
            expected_system,
        )
        if _VALIDATED_SNAPSHOT == token:
            return True
        if not 0 < stat.st_size <= MAX_BYTES:
            return False
        snapshot_system = _snapshot_system()
        if snapshot_system and snapshot_system != expected_system:
            return False
        if _catalog_rs.nix_snapshot_valid(os.fspath(RAW_PATH), MAX_BYTES):
            _VALIDATED_SNAPSHOT = token
            return True
        return False
    except (OSError, ValueError, UnicodeError):
        return False


def cached_path():
    """Return valid local metadata; never download. Call on a worker."""
    return RAW_PATH if enabled() and valid_snapshot() else None


def binary_snapshot_available():
    """Cheap UI readiness check; the Rust loader rebuilds stale binaries."""
    expected_system = linux_arch()
    if not expected_system or not enabled():
        return False
    snapshot_system = _snapshot_system()
    if snapshot_system and snapshot_system != expected_system:
        return False
    try:
        source = RAW_PATH.stat()
        binary = RAW_PATH.with_suffix(".bin").stat()
        return source.st_size > 0 and binary.st_size > 0 and binary.st_mtime_ns >= source.st_mtime_ns
    except OSError:
        return False


def needs_refresh():
    if not enabled():
        return False
    if not valid_snapshot():
        return True
    # Refresh once when an older snapshot lacks broken/deprecated metadata.
    if _snapshot_schema() < SNAPSHOT_SCHEMA:
        return True
    try:
        return time.time() - RAW_PATH.stat().st_mtime >= MAX_AGE
    except OSError:
        return True


def _snapshot_expression(system):
    return (
        _NIX_SNAPSHOT_EXPRESSION
        .replace("__SYSTEM__", system)
        .replace("__SNAPSHOT_MARKER__", _SNAPSHOT_MARKER)
        .replace("__SNAPSHOT_SCHEMA__", str(SNAPSHOT_SCHEMA))
    )


def _nix_snapshot_command(executable, system):
    return [
        executable,
        "--extra-experimental-features",
        "nix-command flakes",
        "eval",
        "--json",
        f"nixpkgs#legacyPackages.{system}",
        "--apply",
        _snapshot_expression(system),
    ]


def load_or_refresh(force=False):
    """Fetch the nixpkgs package list only while Nix is present.

    The previous valid snapshot is retained when a refresh fails, so a transient
    network/registry problem never empties the Nix category.
    """
    if not enabled():
        return None
    with _LOCK:
        try:
            fresh = not needs_refresh()
        except OSError:
            fresh = False
        if force or not fresh:
            temporary = None
            try:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(
                    dir=CACHE_DIR, prefix="packages-", suffix=".json"
                )
                executable = nix_executable()
                if not executable:
                    return None
                expected_system = linux_arch()
                if not expected_system:
                    return None
                environment = {
                    **os.environ,
                    "NIX_CONFIG": (
                        (os.environ.get("NIX_CONFIG", "") + "\n")
                        if os.environ.get("NIX_CONFIG")
                        else ""
                    )
                    + "extra-experimental-features = nix-command flakes\n",
                    "LC_ALL": "C",
                }
                with os.fdopen(fd, "wb") as handle:
                    result = subprocess.run(
                        _nix_snapshot_command(executable, expected_system),
                        stdout=handle,
                        stderr=subprocess.PIPE,
                        timeout=SEARCH_TIMEOUT,
                        check=False,
                        env=environment,
                    )
                if result.returncode:
                    detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
                    raise RuntimeError(
                        detail[-1] if detail else "nix package evaluation failed"
                    )
                size = os.path.getsize(temporary)
                if not 0 < size <= MAX_BYTES:
                    raise ValueError("Nix package metadata is empty or too large")
                if not _catalog_rs.nix_snapshot_valid(temporary, MAX_BYTES):
                    raise ValueError("Invalid Nix package metadata")
                snapshot_system = _snapshot_system(temporary)
                if not expected_system or (
                    snapshot_system and snapshot_system != expected_system
                ):
                    raise ValueError(
                        "Nix package metadata was generated for a different architecture"
                    )
                if not enabled():
                    return None
                os.replace(temporary, RAW_PATH)
                temporary = None
                _VALIDATED_SNAPSHOT = None
                # Force the Rust binary cache to be rebuilt from the new source.
                try:
                    RAW_PATH.with_suffix(".bin").unlink()
                except OSError:
                    pass
                # Warm the compact Rust cache on this worker so opening the
                # category never pays the normalization cost on the GTK thread.
                try:
                    categories, nixos = catalog_metadata()
                    _catalog_rs.NixCatalog(
                        os.fspath(RAW_PATH),
                        scopes(),
                        json.dumps(
                            categories,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                        nixos,
                    )
                except Exception:
                    pass
            except Exception as error:
                logger.warning(
                    "Nix package list refresh failed; retaining cached data: %s", error
                )
            finally:
                if temporary:
                    try:
                        os.unlink(temporary)
                    except OSError:
                        pass
        path = cached_path()
        if path is not None and not binary_snapshot_available():
            # The raw snapshot may already be fresh while the compact Rust cache
            # is missing (first run after an upgrade, for example).
            try:
                categories, nixos = catalog_metadata()
                _catalog_rs.NixCatalog(
                    os.fspath(path),
                    scopes(),
                    json.dumps(
                        categories,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    nixos,
                )
            except Exception:
                pass
        return path


def _flakes_enabled():
    executable = nix_executable()
    if not executable:
        return False
    for args in (["config", "show", "experimental-features"], ["show-config"]):
        try:
            result = subprocess.run(
                [executable, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode:
            continue
        if args[0] == "show-config":
            for line in result.stdout.splitlines():
                key, separator, value = line.partition("=")
                if separator and key.strip() == "experimental-features":
                    return "flakes" in value.split()
            continue
        values = result.stdout.replace(",", " ").split()
        return "flakes" in values
    return False


def _unfree_enabled():
    if os.environ.get("NIXPKGS_ALLOW_UNFREE") in ("1", "true", "yes"):
        return True
    marker = _CACHE_ROOT / "linuxtoys" / "nix" / "allow-unfree"
    try:
        if marker.read_text(encoding="utf-8").strip() == "1":
            return True
    except OSError:
        pass
    candidates = [
        HOME_MODULE_PATH,
        SYSTEM_MODULE_PATH,
        Path(os.path.expanduser("~/.config/nixpkgs/config.nix")),
        HOME_CONFIG_DIR / "home.nix",
        HOME_CONFIG_DIR / "flake.nix",
        Path("/etc/nixos/configuration.nix"),
    ]
    if _HM_CONFIG_OVERRIDE:
        candidates.append(Path(_HM_CONFIG_OVERRIDE).expanduser())
    pattern = re.compile(r"allowUnfree\s*=\s*true")
    for candidate in candidates:
        try:
            if pattern.search(candidate.read_text(encoding="utf-8", errors="replace")):
                return True
        except OSError:
            continue
    return False


def gpu_setup_required():
    """Whether this host needs Home Manager's non-NixOS GPU integration.

    NixOS already exposes /run/opengl-driver, and gregOS installs its own
    kernel-matched driver stack there. Every other host uses the genericLinux
    GPU target when Home Manager manages Nix packages.
    """
    if not enabled() or is_nixos():
        return False
    try:
        from .compat import is_gregos

        if is_gregos():
            return False
    except Exception:
        pass
    return True


def _gpu_config_paths():
    paths = [
        HOME_MODULE_PATH,
        HOME_CONFIG_DIR / "home.nix",
        HOME_CONFIG_DIR / "default.nix",
        HOME_CONFIG_DIR / "flake.nix",
    ]
    if _HM_CONFIG_OVERRIDE:
        paths.append(Path(_HM_CONFIG_OVERRIDE).expanduser())
    seen = set()
    for path in paths:
        key = os.fspath(path)
        if key in seen:
            continue
        seen.add(key)
        yield path


def gpu_configured():
    """Whether the Home Manager configuration enables genericLinux GPU support."""
    if not gpu_setup_required():
        return True
    for path in _gpu_config_paths():
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in content.splitlines():
            if line.lstrip().startswith("#"):
                continue
            if _GPU_ENABLE_RE.search(line):
                return True
        if _GPU_BLOCK_ENABLE_RE.search(content):
            return True
    return False


def _elf32(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(5) == b"\x7fELF\x01"
    except OSError:
        return False


def _host_has_32bit_graphics() -> bool:
    """Whether the host has usable 32-bit graphics drivers for the bundle."""
    icd_dir = Path("/usr/share/vulkan/icd.d")
    try:
        if any(icd_dir.glob("*.i686.json")) or any(icd_dir.glob("*.x86.json")):
            return True
    except OSError:
        pass
    for root in (
        "/usr/lib/i386-linux-gnu",
        "/usr/lib32",
        "/usr/lib",
        "/lib",
    ):
        directory = Path(root)
        if not directory.is_dir():
            continue
        for pattern in ("libvulkan_*.so*", "libGLX_*.so*", "libEGL_*.so*"):
            if any(_elf32(candidate) for candidate in directory.glob(pattern)):
                return True
    return False


def gpu32_setup_required():
    """Whether the non-NixOS host needs the 32-bit Nix GPU complement."""
    if not gpu_setup_required():
        return False
    if os.uname().machine != "x86_64":
        return False
    return _host_has_32bit_graphics()


def gpu32_setup_ready():
    """Whether the 32-bit bundle, service and runtime mount are installed."""
    return (
        Path("/run/opengl-driver-32").exists()
        and Path("/etc/systemd/system/linuxtoys-nix-graphics.service").is_file()
        and Path("/usr/local/lib/linuxtoys/nix-gpu32").is_file()
    )


def gpu_setup_ready():
    """Whether the 64-bit and 32-bit non-NixOS GPU integrations are present."""
    if not gpu_setup_required():
        return True
    if not (gpu_configured() and os.path.exists("/run/opengl-driver")):
        return False
    return not gpu32_setup_required() or gpu32_setup_ready()


def zoneinfo_setup_required():
    """Whether this host needs the /etc/zoneinfo compatibility link.

    Nix packages' bubblewrap wrappers bind /etc/zoneinfo, but some
    distributions keep tzdata only under /usr/share/zoneinfo. NixOS provides
    the path itself, and gregOS ships it in the image.
    """
    if not enabled() or is_nixos():
        return False
    try:
        from .compat import is_gregos

        if is_gregos():
            return False
    except Exception:
        pass
    return _ZONEINFO_SOURCE.is_dir()


def zoneinfo_configured():
    """Whether /etc/zoneinfo exists (as a file, directory or symlink)."""
    if not zoneinfo_setup_required():
        return True
    return os.path.lexists(_ZONEINFO_LINK)


_NIX_GC_MARKER = "systemd.user.services.nix-gc.Service.ExecStart"


def maintenance_setup_required():
    """Whether LinuxToys should manage non-NixOS Nix generation cleanup.

    GregOS ships a Home Manager configuration with a weekly ``nix.gc`` job, so
    the image already owns generation cleanup there.
    """
    if not enabled() or is_nixos():
        return False
    try:
        from .compat import is_gregos

        if is_gregos():
            return False
    except Exception:
        pass
    return True


def maintenance_configured():
    """Whether the module has the cleanup service and its nix.package."""
    if not maintenance_setup_required():
        return True
    script = Path(os.path.expanduser("~/.local/share/linuxtoys/nix-gc.sh"))
    if not script.is_file():
        return False
    try:
        content = HOME_MODULE_PATH.read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError:
        return False
    return _NIX_GC_MARKER in content and bool(_NIX_PACKAGE_RE.search(content))


def setup_status():
    """Return the first-click readiness report used by the setup dialog."""
    flakes = _flakes_enabled()
    unfree = _unfree_enabled()
    home_manager = home_manager_available()
    system = is_nixos()
    gpu_required = gpu_setup_required()
    gpu32_required = gpu32_setup_required()
    gpu32 = gpu32_setup_ready() if gpu32_required else True
    gpu = gpu_setup_ready() if gpu_required else True
    zoneinfo_required = zoneinfo_setup_required()
    zoneinfo = zoneinfo_configured() if zoneinfo_required else True
    maintenance_required = maintenance_setup_required()
    maintenance = maintenance_configured() if maintenance_required else True
    return {
        "nix": bool(nix_executable()),
        "flakes": flakes,
        "unfree": unfree,
        "home_manager": home_manager,
        "system": system,
        "gpu_required": gpu_required,
        "gpu": gpu,
        "gpu32_required": gpu32_required,
        "gpu32": gpu32,
        "zoneinfo_required": zoneinfo_required,
        "zoneinfo": zoneinfo,
        "maintenance_required": maintenance_required,
        "maintenance": maintenance,
        "backend": home_manager or system,
        "ready": bool(nix_executable() and flakes and (home_manager or system)),
    }


def setup_missing(status=None):
    status = status or setup_status()
    missing = []
    if not status["flakes"]:
        missing.append("flakes")
    if not status["unfree"]:
        missing.append("unfree")
    if not status["home_manager"] and not status["system"]:
        missing.append("home-manager")
    if status.get("gpu_required") and not status.get("gpu"):
        missing.append("gpu")
    if status.get("zoneinfo_required") and not status.get("zoneinfo"):
        missing.append("zoneinfo")
    if status.get("maintenance_required") and not status.get("maintenance"):
        missing.append("maintenance")
    return missing


def module_path(scope):
    return SYSTEM_MODULE_PATH if scope == "system" else HOME_MODULE_PATH


def _module_packages(path):
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return set(_MODULE_PACKAGE_RE.findall(content))


def installed_names(scope=None):
    """Observe the packages LinuxToys itself manages through its Nix modules."""
    paths = [module_path(scope)] if scope else [HOME_MODULE_PATH, SYSTEM_MODULE_PATH]
    names = set()
    for path in paths:
        names.update(_module_packages(path))
    return names


def is_installed(info):
    attr = str(
        info.get("nix_name") or info.get("package-name") or ""
    ).strip()
    if not attr:
        return False
    scope = str(info.get("nix_scope") or "").strip()
    return attr in installed_names(scope or None)


def validate_attr(attr):
    value = str(attr or "").strip()
    if not _ATTR_RE.fullmatch(value):
        raise ValueError("Invalid Nix package name")
    return value


def _materialize_script(function, name, description):
    fd, path = tempfile.mkstemp(prefix="linuxtoys-nix-", suffix=".sh")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(
            "#!/usr/bin/env bash\n"
            f"# name: {name}\n"
            f"# description: {description}\n"
            "# icon: nix.svg\n"
            "# architectures: x86_64, aarch64\n"
            "set -eo pipefail\n"
            'source "$SCRIPT_DIR/libs/linuxtoys.bash"\n'
            'source "$SCRIPT_DIR/libs/nixsys.bash"\n'
            f"{function}\n"
        )
    os.chmod(path, 0o700)
    return {
        "name": name,
        "description": description,
        "icon": "nix.svg",
        "path": path,
        "version": "",
        "is_script": True,
        "is_subcategory": False,
        "revert": "no",
        "reboot": "no",
        "repo": "",
    }


def materialize_setup():
    """Script that checks/offers flakes, unfree, home-manager and GPU setup."""
    return _materialize_script(
        "nix_setup",
        "Nix package management setup",
        "Check and configure flakes, unfree packages, home-manager, GPU "
        "acceleration and time zone compatibility.",
    )


def materialize_subsystem_enable():
    """Script that prepares the Nix subsystem without interactive questions."""
    script = _materialize_script(
        "nix_subsystem_ensure",
        "Enable Nix subsystem",
        "Prepare flake support, unfree packages, Home Manager, GPU integration, "
        "time zone compatibility and weekly cleanup.",
    )
    script["registry"] = "no"
    script["cleanup_path"] = script["path"]
    return script


def materialize_apply(translations=None):
    """Script that applies every queued Nix install/removal.

    The terminal viewer renders the run's title and short description, so the
    script metadata carries localized text. The script header keeps the stable
    English identity used by the execution registry.
    """
    if translations is None:
        from .lang_utils import load_translations

        translations = load_translations()
    script = _materialize_script(
        "nix_apply_operations",
        "Apply Nix package operations",
        "Rebuild home-manager and/or the NixOS system profile.",
    )
    script["name"] = translations.get(
        "nix_apply_operations", script["name"]
    )
    script["description"] = translations.get(
        "nix_apply_operations_desc", script["description"]
    )
    script["registry_name"] = "Apply Nix package operations"
    return script


# ---------------------------------------------------------------------------
# Action Registry export/import
# ---------------------------------------------------------------------------

_CATALOG_CACHE = {"key": None, "catalog": None}


def _catalog():
    """Return a cached Rust NixCatalog for attribute/name lookups."""
    path = cached_path()
    if path is None:
        return None
    categories, nixos = catalog_metadata()
    try:
        stat = path.stat()
        category_signature = "unavailable"
        if nixos:
            from . import nix_metadata

            category_signature = nix_metadata.index_category_fingerprint(categories)
        key = (
            os.fspath(path),
            stat.st_size,
            stat.st_mtime_ns,
            tuple(scopes()),
            linux_arch(),
            category_signature,
            nixos,
        )
    except OSError:
        return None
    with _LOCK:
        if _CATALOG_CACHE["key"] == key:
            return _CATALOG_CACHE["catalog"]
        try:
            catalog = _catalog_rs.NixCatalog(
                os.fspath(path),
                scopes(),
                json.dumps(
                    categories,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                nixos,
            )
        except Exception:
            return None
        _CATALOG_CACHE["key"] = key
        _CATALOG_CACHE["catalog"] = catalog
        return catalog


def package_attr(name):
    """Resolve a package name to the exact nixpkgs top-level attribute.

    Used when a manifest's native package can be replaced by a system-level
    Nix package on NixOS. Returns "" when the snapshot is unavailable or the
    name does not match an attribute/pname.
    """
    value = str(name or "").strip()
    if not value:
        return ""
    catalog = _catalog()
    if catalog is None:
        return ""
    try:
        entry = catalog.find_by_name(value)
    except Exception:
        return ""
    if not isinstance(entry, dict):
        return ""
    attr = str(entry.get("nix_name") or "").strip()
    return attr if _ATTR_RE.fullmatch(attr) else ""


def attr_available(attr):
    """Whether an exact top-level nixpkgs attribute exists on this host."""
    value = str(attr or "").strip()
    if not _ATTR_RE.fullmatch(value):
        return False
    catalog = _catalog()
    if catalog is None:
        return False
    try:
        return isinstance(catalog.find_by_attr(value), dict)
    except Exception:
        return False


def installed_packages():
    """Return the LinuxToys-managed Nix package state by scope."""
    return {
        scope: sorted(installed_names(scope))
        for scope in ("home-manager", "system")
    }


def manifest_bundle_dir(manifest_path):
    """Directory that carries a manifest's exported Nix flake and modules."""
    path = Path(manifest_path).expanduser()
    name = path.stem if path.suffix else path.name
    return path.parent / f"{name}-nix"


def _render_package_list(packages):
    return "\n".join(f"    pkgs.{attr}" for attr in sorted(set(packages)))


def render_home_module(packages):
    """Render the home-manager module for an exported manifest."""
    return (
        "{ pkgs, ... }:\n"
        "\n"
        "# Generated by LinuxToys from the Action Registry.\n"
        "{\n"
        "  nixpkgs.config.allowUnfree = true;\n"
        "  home.packages = [\n"
        f"{_render_package_list(packages)}\n"
        "  ];\n"
        "}\n"
    )


def render_system_module(packages):
    """Render the NixOS module for exported system-level packages."""
    return (
        "{ pkgs, ... }:\n"
        "\n"
        "# Generated by LinuxToys from the Action Registry.\n"
        "{\n"
        "  nixpkgs.config.allowUnfree = true;\n"
        "  environment.systemPackages = [\n"
        f"{_render_package_list(packages)}\n"
        "  ];\n"
        "}\n"
    )


def render_flake(system=None):
    """Render a self-contained home-manager flake for the exported module."""
    import getpass

    system = system or linux_arch()
    if not system:
        raise ValueError("Nix export requires a supported x86_64 or aarch64 host")
    user = getpass.getuser()
    home = os.path.expanduser("~")
    user_literal = json.dumps(user, ensure_ascii=False)
    home_literal = json.dumps(home, ensure_ascii=False)
    return (
        "{\n"
        '  description = "LinuxToys exported Nix packages";\n'
        "  inputs = {\n"
        '    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";\n'
        "    home-manager = {\n"
        '      url = "github:nix-community/home-manager";\n'
        '      inputs.nixpkgs.follows = "nixpkgs";\n'
        "    };\n"
        "  };\n"
        "  outputs = { self, nixpkgs, home-manager, ... }:\n"
        "    let\n"
        f'      system = "{system}";\n'
        f"      username = {user_literal};\n"
        f"      homeDirectory = {home_literal};\n"
        "    in {\n"
        "      homeConfigurations.${username} = home-manager.lib.homeManagerConfiguration {\n"
        "        pkgs = import nixpkgs { inherit system; config.allowUnfree = true; };\n"
        "        modules = [\n"
        "          ./linuxtoys.nix\n"
        "          {\n"
        "            home.username = username;\n"
        "            home.homeDirectory = homeDirectory;\n"
        '            home.stateVersion = "24.05";\n'
        "          }\n"
        "        ];\n"
        "      };\n"
        "    };\n"
        "}\n"
    )


def export_manifest_bundle(manifest_path, home_packages, system_packages, names=None):
    """Write the flake and modules that accompany an exported manifest.

    Returns the bundle directory. The manifest itself stays the portable entry
    point; this directory is picked up automatically by the importer.
    """
    home = sorted({validate_attr(attr) for attr in home_packages if attr})
    system = sorted({validate_attr(attr) for attr in system_packages if attr})
    target_system = linux_arch()
    if not target_system:
        raise ValueError("Nix export requires a supported x86_64 or aarch64 host")
    directory = manifest_bundle_dir(manifest_path)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        os.fspath(directory / "linuxtoys.nix"),
        render_home_module(home),
        mode=0o644,
        fsync=True,
    )
    atomic_write_text(
        os.fspath(directory / "linuxtoys-system.nix"),
        render_system_module(system),
        mode=0o644,
        fsync=True,
    )
    atomic_write_text(
        os.fspath(directory / "flake.nix"),
        render_flake(target_system),
        mode=0o644,
        fsync=True,
    )
    metadata = {
        "schema": 1,
        "source_nixos": bool(is_nixos()),
        "source_system": target_system,
        "home": home,
        "system": system,
        "names": {
            str(attr): str((names or {}).get(attr) or attr)
            for attr in sorted(set(home) | set(system))
        },
    }
    atomic_write_text(
        os.fspath(directory / "meta.json"),
        json.dumps(
            metadata,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        fsync=True,
    )
    return directory


def _bundle_candidates(manifest_path):
    path = Path(manifest_path).expanduser()
    yield manifest_bundle_dir(path)
    yield Path(str(path) + ".d")
    parent = path.parent
    if parent.name.endswith("-nix") or (
        (parent / "meta.json").is_file()
        and (parent / "linuxtoys.nix").is_file()
    ):
        yield parent
    # Files literally alongside the manifest: only accept the shared directory
    # when both expected files are present, so an unrelated flake.nix elsewhere
    # is never mistaken for a LinuxToys export.
    if (parent / "flake.nix").is_file() and (parent / "linuxtoys.nix").is_file():
        yield parent


def find_manifest_bundle(manifest_path):
    """Locate the Nix directory exported alongside a manifest, if any."""
    seen = set()
    for candidate in _bundle_candidates(manifest_path):
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if not candidate.is_dir():
            continue
        if any(
            (candidate / name).is_file()
            for name in ("meta.json", "flake.nix", "linuxtoys.nix", "linuxtoys-system.nix")
        ):
            return candidate
    return None


def read_manifest_bundle(manifest_path):
    """Read exported Nix packages from the files next to a manifest.

    Metadata is preferred when present because it preserves the source OS and
    the original scope split. The generated modules are the fallback, so a
    hand-written bundle containing only ``linuxtoys.nix`` also works.
    """
    directory = find_manifest_bundle(manifest_path)
    if directory is None:
        return None

    home = []
    system = []
    names = {}
    source_nixos = False
    source_system = ""
    metadata_path = directory / "meta.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, UnicodeError):
        metadata = None
    if isinstance(metadata, dict) and metadata.get("schema") == 1:
        home = [
            str(attr) for attr in metadata.get("home") or ()
            if _ATTR_RE.fullmatch(str(attr))
        ]
        system = [
            str(attr) for attr in metadata.get("system") or ()
            if _ATTR_RE.fullmatch(str(attr))
        ]
        raw_names = metadata.get("names")
        if isinstance(raw_names, dict):
            names = {
                str(attr): str(name)
                for attr, name in raw_names.items()
                if _ATTR_RE.fullmatch(str(attr)) and str(name).strip()
            }
        source_nixos = bool(metadata.get("source_nixos"))
        source_system = str(metadata.get("source_system") or "").strip()
    else:
        home = sorted(_module_packages(directory / "linuxtoys.nix"))
        system = sorted(_module_packages(directory / "linuxtoys-system.nix"))

    return {
        "dir": os.fspath(directory),
        "home": sorted(set(home)),
        "system": sorted(set(system)),
        "names": names,
        "source_nixos": source_nixos,
        "source_system": source_system,
    }


def materialize_import(manifest_path, home_packages, system_packages):
    """Create a one-shot script that applies an exported manifest's Nix files."""
    home = sorted({validate_attr(attr) for attr in home_packages if attr})
    system = sorted({validate_attr(attr) for attr in system_packages if attr})
    payload = json.dumps(
        {"home": home, "system": system},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    fd, path = tempfile.mkstemp(prefix="linuxtoys-nix-import-", suffix=".sh")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(
            "#!/usr/bin/env bash\n"
            "# name: Import Nix manifest packages\n"
            "# description: Apply the Nix packages exported alongside the manifest.\n"
            "# icon: nix.svg\n"
            "# architectures: x86_64, aarch64\n"
            "set -eo pipefail\n"
            'source "$SCRIPT_DIR/libs/linuxtoys.bash"\n'
            'source "$SCRIPT_DIR/libs/nixsys.bash"\n'
            'json=$(mktemp "${TMPDIR:-/tmp}/linuxtoys-nix-import.XXXXXX")\n'
            "trap 'rm -f -- \"$json\"' EXIT\n"
            "cat >\"$json\" <<'LINUXTOYS_NIX_JSON'\n"
            f"{payload}\n"
            "LINUXTOYS_NIX_JSON\n"
            'nix_import_manifest "$json"\n'
        )
    os.chmod(path, 0o700)
    return {
        "name": "Import Nix manifest packages",
        "description": "Apply the Nix packages exported alongside the manifest.",
        "icon": "nix.svg",
        "path": path,
        "version": "",
        "is_script": True,
        "is_subcategory": False,
        "revert": "no",
        "reboot": "no",
        "repo": "",
        "cleanup_path": path,
    }
