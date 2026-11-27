"""Resolve the active Home Manager and NixOS configuration files.

Home Manager does not record which source directory or file produced a
generation, and NixOS does not record the flake/config path either. LinuxToys
therefore resolves those paths from explicit overrides, its own durable record,
the conventional locations and a bounded discovery pass. When an existing
environment cannot be mapped back to a source path, the resolver reports it as
unresolved instead of silently creating a new default environment.
"""

from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path

if __package__:
    from .atomic_io import atomic_write_text
else:  # Executed as ``python3 app/nix_paths.py`` from the Bash libraries.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.atomic_io import atomic_write_text

SCHEMA = 1
MAX_SCAN_DIRS = 2000
_MAX_FILE_BYTES = 128 * 1024
_CACHE = None
_ENV_KEYS = (
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_STATE_HOME",
    "HOME_MANAGER_CONFIG",
    "LINUXTOYS_NIX_HM_DIR",
    "LINUXTOYS_NIX_HM_MODULE",
    "LINUXTOYS_NIX_SYSTEM_DIR",
    "LINUXTOYS_NIX_SYSTEM_MODULE",
    "NIXOS_CONFIG",
    "NIX_PATH",
)
_HOME_FLAKE_MARKERS = (
    "homeConfigurations",
    "homeManagerConfiguration",
    "home-manager.lib",
)
_HOME_CLASSIC_MARKERS = (
    "home.username",
    "home.homeDirectory",
    "home.stateVersion",
)
_SYSTEM_FLAKE_MARKERS = (
    "nixosConfigurations",
    "nixosSystem",
)
_SYSTEM_CLASSIC_MARKERS = (
    "environment.systemPackages",
    "boot.loader",
    "networking.hostName",
    "services.",
)
_FLAKE_REFERENCE_PATTERN = re.compile(r"\./([A-Za-z0-9_./-]+\.nix)")
_SCAN_PRUNE = {
    ".cache",
    ".local",
    ".mozilla",
    ".thunderbird",
    ".var",
    ".steam",
    ".npm",
    ".cargo",
    ".rustup",
    ".gradle",
    ".android",
    "node_modules",
    "Downloads",
    "Documents",
    "Pictures",
    "Music",
    "Videos",
    "VirtualBox VMs",
}
_KNOWN_HOME_DIRS = (
    "home-manager",
    "hm",
    "nix-config",
    "nixos-config",
    "nixcfg",
    "nixos",
    "nix",
    "dotfiles",
    ".dotfiles",
)
_KNOWN_HOME_CONFIG_DIRS = (
    "home-manager",
    "home-manager-config",
    "nixpkgs",
    "nix-config",
    "nixos-config",
)
_KNOWN_SYSTEM_DIRS = (
    "nixos",
    "nixos-config",
    "nix-config",
    "nixcfg",
    "dotfiles/nixos",
    ".config/nixos",
)


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or _home() / ".config")


def _xdg_state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or _home() / ".local" / "state")


def state_path() -> Path:
    """Durable record of the paths LinuxToys last resolved successfully."""
    return _xdg_state_home() / "linuxtoys" / "nix" / "active-paths.json"


def default_home_dir() -> Path:
    return _xdg_config_home() / "home-manager"


def default_system_dir() -> Path:
    return Path("/etc/nixos")


def _expand(value) -> Path | None:
    text = str(value or "").strip()
    return Path(os.path.expanduser(text)) if text else None


def _read_text(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(_MAX_FILE_BYTES)
    except OSError:
        return ""


def _has_markers(path: Path, markers: tuple[str, ...]) -> bool:
    if not path.is_file():
        return False
    text = _read_text(path)
    return any(marker in text for marker in markers)


def _first_file(directory: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def _referenced_config(
    directory: Path, flake_text: str, markers: tuple[str, ...]
) -> Path | None:
    for reference in _FLAKE_REFERENCE_PATTERN.findall(flake_text):
        candidate = directory / reference
        if _has_markers(candidate, markers):
            return candidate
    return None


def _home_layout(directory: Path) -> dict | None:
    """Return the Home Manager layout rooted at *directory*, if any."""
    if not directory.is_dir():
        return None
    flake = directory / "flake.nix"
    if flake.is_file():
        flake_text = _read_text(flake)
        if any(marker in flake_text for marker in _HOME_FLAKE_MARKERS):
            config = _referenced_config(
                directory, flake_text, _HOME_CLASSIC_MARKERS
            )
            return {
                "flake": True,
                "config": config
                or _first_file(directory, ("home.nix", "default.nix")),
            }
    for name in ("home.nix", "default.nix"):
        candidate = directory / name
        if _has_markers(candidate, _HOME_CLASSIC_MARKERS):
            return {"flake": False, "config": candidate}
    return None


def _system_layout(directory: Path) -> dict | None:
    """Return the NixOS layout rooted at *directory*, if any."""
    if not directory.is_dir():
        return None
    config = directory / "configuration.nix"
    flake = directory / "flake.nix"
    if flake.is_file():
        flake_text = _read_text(flake)
        if any(marker in flake_text for marker in _SYSTEM_FLAKE_MARKERS):
            referenced = _referenced_config(
                directory, flake_text, _SYSTEM_CLASSIC_MARKERS
            )
            return {
                "flake": True,
                "config": config if config.is_file() else referenced,
            }
    if config.is_file():
        return {"flake": False, "config": config}
    return None


def _is_nixos() -> bool:
    if Path("/etc/NIXOS").exists():
        return True
    if Path("/etc/nixos/configuration.nix").is_file():
        return True
    for line in _read_text(Path("/etc/os-release")).splitlines():
        key, separator, value = line.partition("=")
        if not separator or key not in ("ID", "ID_LIKE"):
            continue
        tokens = value.strip().strip('"').lower().split()
        if "nixos" in tokens or any(token.startswith("nixos-") for token in tokens):
            return True
    return False


def _standalone_generation_exists() -> bool:
    home = _home()
    return (
        (home / ".local" / "state" / "home-manager" / "gcroots" / "current-home").exists()
        or (home / ".local" / "state" / "nix" / "profiles" / "home-manager").exists()
    )


def _json_path(value) -> str:
    return os.fspath(value) if value else ""


def _record_paths(home: dict, system: dict) -> None:
    payload = {
        "schema": SCHEMA,
        "home": {
            "dir": _json_path(home["dir"]),
            "config": _json_path(home["config"]),
            "module": _json_path(home["module"]),
            "flake": bool(home["flake"]),
            "source": home["source"],
            "explicit": bool(home.get("explicit")),
        },
        "system": {
            "dir": _json_path(system["dir"]),
            "config": _json_path(system["config"]),
            "module": _json_path(system["module"]),
            "flake": bool(system["flake"]),
            "source": system["source"],
            "explicit": bool(system.get("explicit")),
        },
    }
    import json

    path = state_path()
    try:
        if path.is_file() and path.read_text(encoding="utf-8").strip():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing == payload:
                return
    except (OSError, ValueError, TypeError, UnicodeError):
        pass
    try:
        atomic_write_text(
            os.fspath(path),
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            mode=0o600,
        )
    except OSError:
        # Path tracking is best effort; never block setup because the state
        # directory is read-only.
        pass


def _load_recorded() -> dict:
    path = state_path()
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, UnicodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        return {}
    return payload


def _state_entry(scope: str, layout) -> dict | None:
    recorded = _load_recorded().get(scope)
    if not isinstance(recorded, dict):
        return None
    directory = _expand(recorded.get("dir"))
    if directory is None or not directory.is_dir():
        return None
    layout_data = layout(directory)
    if layout_data is None:
        return None
    config = _expand(recorded.get("config"))
    flake = bool(recorded.get("flake"))
    if not recorded.get("explicit"):
        config = layout_data["config"] or config
        flake = bool(layout_data["flake"])
    module = _expand(recorded.get("module"))
    return {
        "dir": directory,
        "config": config,
        "module": module or directory / "linuxtoys.nix",
        "flake": flake,
        "source": "state",
    }


def _candidate_dirs() -> list[Path]:
    home = _home()
    candidates = [home / name for name in _KNOWN_HOME_DIRS]
    candidates.extend(_xdg_config_home() / name for name in _KNOWN_HOME_CONFIG_DIRS)
    return candidates


def _walk_configs(roots: list[Path], names: set[str]) -> list[Path]:
    """Find configuration files in shallow, non-data directories."""
    found: list[Path] = []
    visited = 0
    for root in roots:
        if not root.is_dir():
            continue
        base_depth = len(root.parts)
        for directory, child_dirs, files in os.walk(root, topdown=True):
            visited += 1
            if visited > MAX_SCAN_DIRS:
                return found
            depth = len(Path(directory).parts) - base_depth
            if depth >= 3:
                child_dirs[:] = []
            else:
                child_dirs[:] = sorted(
                    name
                    for name in child_dirs
                    if name not in _SCAN_PRUNE
                    and (not name.startswith(".") or name in {".config", ".dotfiles"})
                )
            if names.intersection(files):
                found.append(Path(directory))
    return found


def _discover_home() -> list[dict]:
    seen: set[str] = set()
    found: list[dict] = []
    directories = list(_candidate_dirs())
    if _xdg_config_home().is_dir():
        directories.extend(
            child for child in _xdg_config_home().iterdir() if child.is_dir()
        )
    scan_roots = [_home(), _xdg_config_home()]
    directories.extend(_walk_configs(scan_roots, {"flake.nix", "home.nix", "default.nix"}))
    for directory in directories:
        try:
            resolved = directory.resolve()
        except OSError:
            continue
        key = os.fspath(resolved)
        if key in seen:
            continue
        seen.add(key)
        layout = _home_layout(directory)
        if layout is None:
            continue
        found.append(
            {
                "dir": directory,
                "config": layout["config"],
                "module": directory / "linuxtoys.nix",
                "flake": bool(layout["flake"]),
                "source": "discovered",
            }
        )
    return found


def _discover_system() -> list[dict]:
    seen: set[str] = set()
    found: list[dict] = []
    home = _home()
    directories = [default_system_dir()]
    directories.extend(home / name for name in _KNOWN_SYSTEM_DIRS)
    directories.extend(
        _walk_configs(
            [home],
            {"configuration.nix", "flake.nix"},
        )
    )
    for directory in directories:
        try:
            resolved = directory.resolve()
        except OSError:
            continue
        key = os.fspath(resolved)
        if key in seen:
            continue
        seen.add(key)
        layout = _system_layout(directory)
        if layout is None:
            continue
        found.append(
            {
                "dir": directory,
                "config": layout["config"],
                "module": directory / "linuxtoys.nix",
                "flake": bool(layout["flake"]),
                "source": "discovered",
            }
        )
    return found


def _home_from_env() -> dict | None:
    module = _expand(os.environ.get("LINUXTOYS_NIX_HM_MODULE"))
    config = _expand(os.environ.get("HOME_MANAGER_CONFIG"))
    directory = _expand(os.environ.get("LINUXTOYS_NIX_HM_DIR"))
    if module is None and config is None and directory is None:
        return None
    if module is not None:
        directory = module.parent
    elif config is not None:
        config = config.resolve(strict=False)
        directory = config if config.is_dir() else config.parent
    assert directory is not None
    layout = _home_layout(directory)
    if config is not None and config.is_dir():
        config = layout["config"] if layout else _first_file(
            directory, ("home.nix", "default.nix")
        )
    elif config is None and layout is not None:
        config = layout["config"]
    explicit_file = config is not None and not config.is_dir()
    return {
        "dir": directory,
        "config": config,
        "module": module or directory / "linuxtoys.nix",
        "flake": bool(layout and layout["flake"]) and not explicit_file,
        "source": "env",
        "explicit": True,
    }


def _system_from_env() -> dict | None:
    module = _expand(os.environ.get("LINUXTOYS_NIX_SYSTEM_MODULE"))
    config = _expand(os.environ.get("NIXOS_CONFIG"))
    directory = _expand(os.environ.get("LINUXTOYS_NIX_SYSTEM_DIR"))
    if module is None and config is None and directory is None:
        for entry in os.environ.get("NIX_PATH", "").split(":"):
            key, separator, value = entry.partition("=")
            if separator and key == "nixos-config" and value.strip():
                config = _expand(value)
                break
    if module is None and config is None and directory is None:
        return None
    if module is not None:
        directory = module.parent
    elif config is not None:
        config = config.resolve(strict=False)
        directory = config if config.is_dir() else config.parent
    assert directory is not None
    layout = _system_layout(directory)
    if config is not None and config.is_dir():
        config = layout["config"] if layout else None
    elif config is None and layout is not None:
        config = layout["config"]
    explicit_file = config is not None and not config.is_dir()
    return {
        "dir": directory,
        "config": config,
        "module": module or directory / "linuxtoys.nix",
        "flake": bool(layout and layout["flake"]) and not explicit_file,
        "source": "env",
        "explicit": True,
    }


def _resolve_home() -> dict:
    from_env = _home_from_env()
    if from_env is not None:
        return {**from_env, "resolved": True, "candidates": []}

    recorded = _state_entry("home", _home_layout)
    if recorded is not None:
        return {**recorded, "resolved": True, "candidates": []}

    default = default_home_dir()
    if _home_layout(default) is not None:
        layout = _home_layout(default)
        return {
            "dir": default,
            "config": layout["config"],
            "module": default / "linuxtoys.nix",
            "flake": bool(layout["flake"]),
            "source": "default",
            "resolved": True,
            "candidates": [],
        }

    # On NixOS, Home Manager is commonly owned by the system configuration.
    # Without a standalone generation there is no reliable way to tell an
    # unrelated user flake from the active setup, so only explicit/recorded/
    # conventional paths may activate the standalone scope.
    if _is_nixos() and not _standalone_generation_exists():
        return {
            "dir": default,
            "config": None,
            "module": default / "linuxtoys.nix",
            "flake": False,
            "source": "unresolved",
            "resolved": False,
            "candidates": [],
        }

    discovered = _discover_home()
    if len(discovered) == 1:
        return {**discovered[0], "resolved": True, "candidates": []}
    if len(discovered) > 1:
        return {
            "dir": default,
            "config": None,
            "module": default / "linuxtoys.nix",
            "flake": False,
            "source": "unresolved",
            "resolved": False,
            "candidates": [os.fspath(item["dir"]) for item in discovered],
        }

    # A first-time standalone setup may create the conventional directory.
    # On NixOS, Home Manager is often owned by the system configuration; a
    # missing standalone generation/config must not create a second one.
    if not _is_nixos() and not _standalone_generation_exists():
        return {
            "dir": default,
            "config": None,
            "module": default / "linuxtoys.nix",
            "flake": False,
            "source": "new",
            "resolved": True,
            "candidates": [],
        }
    return {
        "dir": default,
        "config": None,
        "module": default / "linuxtoys.nix",
        "flake": False,
        "source": "unresolved",
        "resolved": False,
        "candidates": [],
    }


def _resolve_system() -> dict:
    from_env = _system_from_env()
    if from_env is not None:
        return {**from_env, "resolved": True, "candidates": []}

    recorded = _state_entry("system", _system_layout)
    if recorded is not None:
        return {**recorded, "resolved": True, "candidates": []}

    default = default_system_dir()
    layout = _system_layout(default)
    if layout is not None:
        return {
            "dir": default,
            "config": layout["config"],
            "module": default / "linuxtoys.nix",
            "flake": bool(layout["flake"]),
            "source": "default",
            "resolved": True,
            "candidates": [],
        }

    if not _is_nixos():
        return {
            "dir": default,
            "config": None,
            "module": default / "linuxtoys.nix",
            "flake": False,
            "source": "unavailable",
            "resolved": False,
            "candidates": [],
        }

    discovered = _discover_system()
    if len(discovered) == 1:
        return {**discovered[0], "resolved": True, "candidates": []}
    return {
        "dir": default,
        "config": None,
        "module": default / "linuxtoys.nix",
        "flake": False,
        "source": "unresolved",
        "resolved": False,
        "candidates": [os.fspath(item["dir"]) for item in discovered],
    }


def _cache_key():
    try:
        stat = state_path().stat()
        state_signature = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        state_signature = None
    return (
        state_signature,
        tuple(os.environ.get(key, "") for key in _ENV_KEYS),
    )


def resolve(refresh: bool = False) -> dict:
    """Return the active paths, discovering and recording them if needed."""
    global _CACHE
    key = _cache_key()
    if _CACHE is not None and not refresh and _CACHE[0] == key:
        return _CACHE[1]
    home = _resolve_home()
    system = _resolve_system()
    result = {"home": home, "system": system}
    _record_paths(home, system)
    _CACHE = (_cache_key(), result)
    return result


def record_flake(scope: str, directory, config=None, module=None) -> dict:
    """Record a newly generated flake as the active scope configuration."""
    if scope not in ("home-manager", "system"):
        raise ValueError("Invalid scope")
    paths = resolve()
    home = paths["home"]
    system = paths["system"]
    key = "system" if scope == "system" else "home"
    entry = paths[key]
    entry.update(
        {
            "dir": Path(directory).expanduser(),
            "config": Path(config).expanduser() if config else None,
            "module": Path(module).expanduser()
            if module
            else Path(directory).expanduser() / "linuxtoys.nix",
            "flake": True,
            "source": "generated-flake",
            "resolved": True,
            "candidates": [],
            "explicit": False,
        }
    )
    _record_paths(home, system)
    reset_cache()
    return paths


def reset_cache() -> None:
    """Forget the in-process resolution (tests and environment changes)."""
    global _CACHE
    _CACHE = None


def _shell_value(value: Path | str | None) -> str:
    if value is None:
        return ""
    return os.fspath(value)


def shell_assignments(paths: dict | None = None) -> str:
    """Render Bash assignments for the active paths."""
    paths = paths or resolve()
    home = paths["home"]
    system = paths["system"]
    fields = {
        "_NIX_ACTIVE_HOME_DIR": _shell_value(home.get("dir")),
        "_NIX_ACTIVE_HOME_CONFIG": _shell_value(home.get("config")),
        "_NIX_ACTIVE_HOME_MODULE": _shell_value(home.get("module")),
        "_NIX_ACTIVE_HOME_FLAKE": "1" if home.get("flake") else "0",
        "_NIX_ACTIVE_HOME_RESOLVED": "1" if home.get("resolved") else "0",
        "_NIX_ACTIVE_HOME_SOURCE": str(home.get("source") or ""),
        "_NIX_ACTIVE_SYSTEM_DIR": _shell_value(system.get("dir")),
        "_NIX_ACTIVE_SYSTEM_CONFIG": _shell_value(system.get("config")),
        "_NIX_ACTIVE_SYSTEM_MODULE": _shell_value(system.get("module")),
        "_NIX_ACTIVE_SYSTEM_FLAKE": "1" if system.get("flake") else "0",
        "_NIX_ACTIVE_SYSTEM_RESOLVED": "1" if system.get("resolved") else "0",
        "_NIX_ACTIVE_SYSTEM_SOURCE": str(system.get("source") or ""),
    }
    lines = [f"{key}={shlex.quote(str(value))}" for key, value in fields.items()]
    lines.append("_NIX_ACTIVE_PATHS_READY=1")
    return "\n".join(lines)


def unresolved_message(scope: str, paths: dict | None = None) -> str:
    paths = paths or resolve()
    entry = paths.get("system" if scope == "system" else "home", {})
    candidates = entry.get("candidates") or []
    if scope == "system":
        message = (
            "Could not determine the active NixOS configuration. Set "
            "NIXOS_CONFIG, NIX_PATH's nixos-config entry, "
            "LINUXTOYS_NIX_SYSTEM_DIR or LINUXTOYS_NIX_SYSTEM_MODULE to the "
            "active configuration so LinuxToys does not create a second NixOS "
            "configuration."
        )
    else:
        message = (
            "Could not determine the active Home Manager configuration. Set "
            "HOME_MANAGER_CONFIG, LINUXTOYS_NIX_HM_DIR or "
            "LINUXTOYS_NIX_HM_MODULE to the active home.nix or flake "
            "directory so LinuxToys does not create a second Home Manager "
            "environment."
        )
    if candidates:
        message += " Candidate directories: " + ", ".join(candidates)
    return message


def _main(argv: list[str] | None = None) -> int:
    import json
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "shell"
    if command == "shell":
        print(shell_assignments())
        return 0
    if command == "json":
        print(
            json.dumps(
                resolve(refresh="--refresh" in args),
                ensure_ascii=False,
                default=str,
            )
        )
        return 0
    if command == "message":
        scope = args[1] if len(args) > 1 else "home-manager"
        print(unresolved_message(scope))
        return 0
    if command == "record-flake" and len(args) >= 3:
        record_flake(
            args[1],
            args[2],
            args[3] if len(args) > 3 and args[3] else None,
            args[4] if len(args) > 4 and args[4] else None,
        )
        return 0
    print(f"Unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
