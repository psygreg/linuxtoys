"""Authoritative architecture policy. No GUI, native extension or network imports.

Names are selection hints, never permission to execute. Installation also requires
payload inspection through architecture_files. Unknown is not architecture-neutral.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import fnmatch
import hashlib
import json
from pathlib import Path
import platform
import re
from typing import Any, Iterable, Mapping


class ArchitectureError(ValueError):
    """A route or payload lacks consistent, supported architecture evidence."""


class Architecture(str, Enum):
    X86_64 = "x86_64"
    AARCH64 = "aarch64"


@dataclass(frozen=True)
class ArchitectureLabels:
    aliases: tuple[str, ...]
    deb: str
    rpm: str
    rust: str
    vendor: str
    homebrew: str
    elf_machine: int


LABELS: dict[Architecture, ArchitectureLabels] = {
    Architecture.X86_64: ArchitectureLabels(
        ("x86_64", "amd64", "x64"),
        "amd64",
        "x86_64",
        "x86_64-unknown-linux-gnu",
        "x64",
        "x86_64",
        62,
    ),
    Architecture.AARCH64: ArchitectureLabels(
        ("aarch64", "arm64"),
        "arm64",
        "aarch64",
        "aarch64-unknown-linux-gnu",
        "arm64",
        "arm64",
        183,
    ),
}
# Recognize foreign hints to reject them, not to advertise support for these ISAs.
_FOREIGN = (
    "i386",
    "i486",
    "i586",
    "i686",
    "ia32",
    "x86",
    "armv7l",
    "armv7",
    "armhf",
    "armv6l",
    "armv6",
    "armel",
    "arm32",
    "arm",
    "riscv64",
    "ppc64le",
    "ppc64el",
    "ppc64",
    "s390x",
    "loongarch64",
)
_ALIASES = {alias: arch for arch, labels in LABELS.items() for alias in labels.aliases}
_TOKEN = re.compile(
    r"(?<![a-z0-9])("
    + "|".join(
        re.escape(x) for x in sorted((*_ALIASES, *_FOREIGN), key=len, reverse=True)
    )
    + r")(?![a-z0-9])",
    re.I,
)


def normalize(value: str) -> Architecture:
    """Normalize a supported alias; ARM32 and unknown values fail explicitly."""
    if not isinstance(value, str) or value.strip().lower() not in _ALIASES:
        raise ArchitectureError(
            f"Unsupported architecture {value!r}; supported: x86_64, aarch64"
        )
    return _ALIASES[value.strip().lower()]


def host() -> Architecture:
    """Read the actual host. No environment variable can override installation ISA."""
    return normalize(platform.machine())


def label(system: str, machine: str | None = None) -> str:
    """Map a canonical host to a packaging/toolchain/vendor label."""
    arch = host() if machine is None else normalize(machine)
    if system == "host" or system == "flatpak":
        return arch.value
    if system not in {"deb", "rpm", "rust", "vendor", "homebrew"}:
        raise ArchitectureError(f"Unknown architecture label namespace: {system}")
    return str(getattr(LABELS[arch], system))


def asset_architectures(name: str) -> list[str]:
    """Return canonical hints, including explicitly unsupported foreign tokens."""
    values = {
        _ALIASES[token.lower()].value if token.lower() in _ALIASES else token.lower()
        for token in _TOKEN.findall(name)
    }
    return sorted(values)


def require_native(values: Iterable[str], machine: str | None = None) -> Architecture:
    """Require one consistent native ISA; mixed, foreign and missing evidence fail."""
    arch = host() if machine is None else normalize(machine)
    evidence = {normalize(value) for value in values}
    if evidence != {arch}:
        raise ArchitectureError(
            f"Architecture mismatch or unknown payload: host={arch.value}, "
            f"payload={','.join(sorted(a.value for a in evidence)) or 'unknown'}"
        )
    return arch


def asset_eligible(asset: Mapping[str, Any], machine: str | None = None) -> bool:
    """Check release hints; independent data/source must be explicitly declared."""
    arch = host() if machine is None else normalize(machine)
    hints = asset_architectures(str(asset.get("name", "")))
    metadata = asset.get("architectures")
    if metadata is not None:
        if not isinstance(metadata, list) or not all(
            isinstance(x, str) for x in metadata
        ):
            return False
        # Cached/declared evidence cannot override contradictory filename hints.
        hints += metadata
    if asset.get("content_kind") in {"data", "source"}:
        return not hints and asset.get("architecture_independent") is True
    try:
        require_native(hints, arch.value)
    except ArchitectureError:
        return False
    return True


def select_asset(
    assets: Iterable[Mapping[str, Any]],
    *,
    machine: str | None = None,
    pattern: str = "*",
    formats: tuple[tuple[str, ...], ...] | None = None,
    exact: bool = False,
    source: bool = False,
) -> Mapping[str, Any]:
    """Select exactly one best native asset. There is no positional/foreign fallback."""
    arch = host() if machine is None else normalize(machine)
    candidates: list[tuple[int, Mapping[str, Any]]] = []
    for asset in assets:
        name = asset.get("name")
        if not isinstance(name, str):
            continue
        if not (
            name == pattern
            if exact
            else fnmatch.fnmatchcase(name.lower(), pattern.lower())
        ):
            continue
        if (
            re.search(
                r"(?:^|[._-])(?:debug|debuginfo|debugsource|devel|source|src)(?:[._-]|$)",
                name.lower(),
            )
            and not source
        ):
            continue
        candidate = dict(asset)
        if source:
            # This option is explicit source-build intent, not an automatic guess.
            candidate.update(content_kind="source", architecture_independent=True)
        if not asset_eligible(candidate, arch.value):
            continue
        rank = (
            0
            if formats is None
            else next(
                (
                    i
                    for i, suffixes in enumerate(formats)
                    if name.lower().endswith(suffixes)
                ),
                -1,
            )
        )
        if rank >= 0:
            candidates.append((rank, asset))
    if not candidates:
        raise ArchitectureError(
            f"No verified native release asset for {arch.value} matching {pattern!r}"
        )
    best_rank = min(rank for rank, _ in candidates)
    best = [asset for rank, asset in candidates if rank == best_rank]
    if len(best) != 1:
        raise ArchitectureError(
            "Multiple native release assets; specify an exact selector: "
            + ", ".join(str(a["name"]) for a in best)
        )
    return best[0]


@lru_cache(maxsize=1)
def route_policy() -> dict[str, Any]:
    """Read reviewed route declarations shipped with this application version."""
    return json.loads(Path(__file__).with_name("architecture-routes.json").read_text())


def _declaration_allowed(values: Any, arch: Architecture) -> bool:
    if not isinstance(values, list) or not values:
        return False
    try:
        return arch in {normalize(value) for value in values}
    except ArchitectureError:
        return False


def require_script(text: str, machine: str | None = None) -> None:
    """Check a reviewed script or explicit header, before its preamble can mutate.

    Legacy curated scripts are pinned by source digest. Call require_script_path
    for files: a managed bundle must also pass client-owned revision approval.
    Explicit headers are for trusted local/generated code, not remote approval.
    """
    from .script_compat import require_api

    require_api(text)
    arch = host() if machine is None else normalize(machine)
    headers = re.findall(r"(?mi)^# architectures:\s*(.+)$", text)
    if headers:
        declarations = [
            {value.strip() for value in header.split(",")} for header in headers
        ]
        if any(not _declaration_allowed(list(values), arch) for values in declarations):
            raise ArchitectureError("Conflicting script architecture declarations")
        values = list(declarations[0])
    else:
        digest = hashlib.sha256(text.encode()).hexdigest()
        values = route_policy()["scripts"].get(digest, {}).get("architectures", [])
    if not _declaration_allowed(values, arch):
        raise ArchitectureError(
            f"This installer is not qualified for {arch.value}. "
            "Choose a verified native route before continuing."
        )


def require_entry(entry: Mapping[str, Any], machine: str | None = None) -> None:
    """Enforce ISA eligibility on catalog metadata before hooks/dependencies run."""
    arch = host() if machine is None else normalize(machine)
    if entry.get("name") == "Volt":
        raise ArchitectureError(
            "Volt's external Flatpak extension build requires native preflight qualification"
        )
    values = entry.get("architectures")
    if (
        values is None
        and entry.get("is_appstream_entry")
        and entry.get("type") in {"native", "flathub", "snap"}
    ):
        # Native package managers/Flatpak/snapd supply host-specific metadata.
        # Execution still requires their read-only availability preflight.
        values = [arch.value]
    if values is None:
        declaration = route_policy()["catalogs"].get(
            str(entry.get("name") or entry.get("appstream-name")), {}
        )
        values = declaration.get("architectures", [])
        source = entry.get("_list_source") or entry.get("_architecture_source")
        approved = False
        if isinstance(source, str):
            try:
                records = json.loads(Path(source).read_text())
                if isinstance(records, dict):
                    records = [records]
                for record in records:
                    if not isinstance(record, dict):
                        continue
                    name = record.get("name") or record.get("appstream-name")
                    if name != (entry.get("name") or entry.get("appstream-name")):
                        continue
                    digest = hashlib.sha256(
                        json.dumps(
                            record,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ).encode()
                    ).hexdigest()
                    approved = approved or digest in declaration.get("declarations", [])
            except (OSError, ValueError, TypeError):
                approved = False
        if not approved or declaration.get("repo", "") != entry.get("repo", ""):
            values = []
    if not _declaration_allowed(values, arch):
        raise ArchitectureError(
            f"{entry.get('name', 'Catalog route')} is not qualified for {arch.value}"
        )
    for dependency in entry.get("dependencies") or []:
        if "architectures" in dependency and not _declaration_allowed(
            dependency["architectures"], arch
        ):
            raise ArchitectureError(
                "A required dependency does not support this architecture"
            )
        for token in asset_architectures(json.dumps(dependency)):
            require_native([token], arch.value)


def script_eligible(text: str, machine: str | None = None) -> bool:
    try:
        require_script(text, machine)
    except ArchitectureError:
        return False
    return True


def asset_eligible_json(raw: str, machine: str) -> bool:
    """Narrow Rust/PyO3 bridge; failures must not become compatibility."""
    try:
        value = json.loads(raw)
        return isinstance(value, dict) and asset_eligible(value, machine)
    except (ValueError, TypeError):
        return False


def require_script_path(path: str | Path, machine: str | None = None) -> None:
    """Check managed revision integrity before applying the shared ISA policy."""
    from .script_compat import require_managed_script

    require_managed_script(path)
    text = Path(path).read_bytes().decode("utf-8")
    require_script(text, machine)


def resolve_hook_path(script_dir: str, hook: str, cache_dir: str = "") -> Path:
    """Resolve the same relative hook in preflight and execution; reject escapes."""
    relative = Path(hook)
    if relative.is_absolute() or ".." in relative.parts:
        raise ArchitectureError("Hook paths must remain inside scripts/lists")
    roots = [Path(cache_dir) / "lists"] if cache_dir else []
    roots.append(Path(script_dir) / "scripts/lists")
    for root in roots:
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root.resolve()):
            raise ArchitectureError("Hook symlink escapes scripts/lists")
        if candidate.is_file():
            return candidate
    raise ArchitectureError(f"Installer hook is unavailable: {hook}")


def require_overrides(
    overrides: Mapping[str, Any], script_dir: str, cache_dir: str = ""
) -> None:
    """Validate every hook before any phase of an AppStream/repository job runs."""
    arch = host()
    for phase in ("pre", "post"):
        value = overrides.get(phase)
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(value.get("script"), str):
            require_script_path(resolve_hook_path(script_dir, value["script"], cache_dir))
        elif isinstance(value, str):
            digest = hashlib.sha256(value.strip().encode()).hexdigest()
            declaration = route_policy().get("inline_hooks", {}).get(digest, {})
            if not _declaration_allowed(declaration.get("architectures"), arch):
                raise ArchitectureError(
                    f"Inline {phase} hook lacks reviewed {arch.value} eligibility"
                )
        else:
            raise ArchitectureError("Invalid installer hook declaration")
