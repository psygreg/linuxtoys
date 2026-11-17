"""Authoritative architecture policy. No GUI, native extension or network imports.

Names are selection hints, never permission to execute. Installation also requires
payload inspection through architecture_files. aarch64 additionally requires
explicit evidence everywhere; x86_64 keeps the historical matcher
(neutral unlabelled assets, 32-bit last-resort fallback) the installed base
relies on.

Scripts and repository listings follow sane defaults with explicit handling:
content is x86_64-only by presumption, and aarch64 eligibility is declared in
the tree itself — a script's ``# architectures:`` header, a listing record's
``architectures`` marker, or git-db.json release-asset evidence for its repo.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import fnmatch
import json
from pathlib import Path
import platform
import re
from typing import Any, Iterable, Mapping


class ArchitectureError(ValueError):
    """A route or payload lacks consistent, supported architecture evidence."""


SCRIPT_API = 1


def require_api(text: str) -> None:
    """Reject explicit newer/older/conflicting script capability requirements.

    The scripts tree is a live-synced upstream catalog, so this header is the
    only version gate: a script written for a different script API must never
    run against this client's bash core.
    """
    requirements = re.findall(r"(?m)^# requires-script-api:\s*(.*)$", text)
    if requirements and any(value.strip() != str(SCRIPT_API) for value in requirements):
        raise ArchitectureError(
            f"Script requires a different client script API (installed: {SCRIPT_API})"
        )


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
    return _asset_tier(asset, machine) is not None


# 32-bit x86 aliases collapse onto the i686 evidence token, mirroring the
# historical matcher's alias table.
_X86_32_EVIDENCE = frozenset({"i386", "i486", "i586", "i686", "ia32", "x86"})


def _evidence_tier(hints: Iterable[str], arch: Architecture) -> tuple[int, bool] | None:
    """Rank one asset's combined architecture evidence, or None when refused.

    x86_64 keeps the installed base's historical three-tier matcher: assets
    without any architecture evidence stay neutral (tier 0, ranked below
    explicitly named ones), 32-bit x86 assets remain a last-resort fallback
    (tier 1), and any evidence naming the host qualifies. aarch64 keeps the
    reviewed-evidence-only policy of this integration: exactly one consistent
    native declaration, no unlabelled payloads and no fallbacks. Actual
    execution keeps payload verification (architecture_files, require_native)
    authoritative on every ISA.
    """
    evidence: set[str] = set()
    for value in hints:
        value = str(value).lower()
        if value in _ALIASES:
            evidence.add(_ALIASES[value].value)
        elif value in _X86_32_EVIDENCE:
            evidence.add("i686")
        else:
            evidence.add(value)
    if arch is Architecture.AARCH64:
        try:
            require_native(sorted(evidence), arch.value)
        except ArchitectureError:
            return None
        return (0, True)
    if not evidence:
        return (0, False)
    if arch.value in evidence:
        return (0, True)
    if "i686" in evidence:
        return (1, True)
    return None


def _asset_tier(
    asset: Mapping[str, Any], machine: str | None = None
) -> tuple[int, bool] | None:
    """Eligibility + ranking tier for one release asset, or None when refused."""
    arch = host() if machine is None else normalize(machine)
    hints = asset_architectures(str(asset.get("name", "")))
    metadata = asset.get("architectures")
    if metadata is not None:
        if not isinstance(metadata, list) or not all(
            isinstance(x, str) for x in metadata
        ):
            return None
        # Cached/declared evidence cannot override contradictory filename hints.
        hints += metadata
    if asset.get("content_kind") in {"data", "source"}:
        return (0, False) if (
            not hints and asset.get("architecture_independent") is True
        ) else None
    return _evidence_tier(hints, arch)


def select_asset(
    assets: Iterable[Mapping[str, Any]],
    *,
    machine: str | None = None,
    pattern: str = "*",
    formats: tuple[tuple[str, ...], ...] | None = None,
    exact: bool = False,
    source: bool = False,
) -> Mapping[str, Any]:
    """Select exactly one best native release asset for the host.

    Ranking mirrors the historical three-tier matcher: explicitly named host
    assets outrank architecture-unlabelled ones, and the 32-bit x86 fallback
    ranks last. Foreign or contradictory evidence never qualifies.
    """
    arch = host() if machine is None else normalize(machine)
    candidates: list[tuple[tuple[int, int, int], Mapping[str, Any]]] = []
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
        tiers = _asset_tier(candidate, arch.value)
        if tiers is None:
            continue
        fallback_tier, explicit = tiers
        format_rank = (
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
        if format_rank >= 0:
            candidates.append(((fallback_tier, format_rank, 0 if explicit else 1), asset))
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


def _declaration_allowed(values: Any, arch: Architecture) -> bool:
    if not isinstance(values, list) or not values:
        return False
    try:
        return arch in {normalize(value) for value in values}
    except ArchitectureError:
        return False


# Release-asset kinds a git-type entry can actually install from. Tarball
# assets only count for tar entries, and bin entries need their exact
# declared asset; anything else is presumed x86_64-only.
_GIT_KINDS = frozenset({"appimage", "flatpak", "snap", "pacman", "rpm", "deb", "eopkg"})


def _git_db_for(source: Any) -> dict[str, Any]:
    """Load the git-db release index of the tree that owns a listing record."""
    if not isinstance(source, str) or not source:
        return {}
    directory = Path(source).resolve().parent
    for _ in range(4):
        candidate = directory / "git-db.json"
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text())
            except (OSError, ValueError):
                return {}
            repositories = data.get("repositories") if isinstance(data, dict) else None
            return repositories if isinstance(repositories, dict) else {}
        if directory.parent == directory:
            break
        directory = directory.parent
    return {}


def _git_db_asset_architectures(asset: Mapping[str, Any]) -> set[str]:
    """Explicit architecture evidence of one cached asset; unlabelled = none."""
    values = asset.get("architectures")
    if not isinstance(values, list):
        return set()
    return {
        value.strip().lower()
        for value in values
        if isinstance(value, str) and value.strip().lower() in ("x86_64", "aarch64")
    }


def _proven_record_architectures(
    record: Mapping[str, Any], git_db: Mapping[str, Any]
) -> set[str]:
    """ISAs a repository listing is explicitly proven for, beyond x86_64.

    Assets without architecture evidence, single-binary assets and tarball
    assets are presumed x86_64-only; only explicit aarch64 evidence grants
    the ISA, and only through an installable kind for the entry's type.
    """
    proven: set[str] = set()
    entry_type = str(record.get("type") or "git")
    record_data = git_db.get(str(record.get("repo") or ""))
    if not isinstance(record_data, dict):
        return proven
    assets = record_data.get("assets")
    if not isinstance(assets, list):
        return proven
    if entry_type == "git":
        wanted_kinds = _GIT_KINDS
    elif entry_type == "tar":
        wanted_kinds = {"tar"}
    elif entry_type == "bin":
        wanted_kinds = None  # exact declared asset only
    else:
        return proven
    wanted_asset = str(record.get("package-name") or "").strip()
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if wanted_kinds is None:
            if str(asset.get("name") or "") != wanted_asset:
                continue
        elif asset.get("kind") not in wanted_kinds:
            continue
        if "aarch64" in _git_db_asset_architectures(asset):
            proven.add("aarch64")
    return proven


def _record_declared_architectures(record: Mapping[str, Any]) -> list[str] | None:
    """Explicit per-record declaration, validated against the supported ISAs."""
    values = record.get("architectures")
    if values is None:
        return None
    if (
        isinstance(values, list)
        and values
        and all(
            isinstance(value, str) and value.strip().lower() in ("x86_64", "aarch64")
            for value in values
        )
    ):
        ordered: list[str] = []
        for value in values:
            token = value.strip().lower()
            if token not in ordered:
                ordered.append(token)
        return ordered
    raise ArchitectureError(
        f"Record {record.get('name')!r} declares invalid architectures: {values!r}"
    )


def _listing_record(entry: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Locate the listing record an entry was materialized from.

    Reads the record from its own listing file (never the materialized copy),
    preferring an exact name+repo match over a name-only match.
    """
    source = entry.get("_list_source") or entry.get("_architecture_source")
    if not isinstance(source, str) or not source:
        return None
    name = entry.get("name") or entry.get("appstream-name")
    repo = str(entry.get("repo") or "")
    fallback: Mapping[str, Any] | None = None
    try:
        records = json.loads(Path(source).read_text())
    except (OSError, ValueError, TypeError):
        return None
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list):
        return None
    for candidate in records:
        if not isinstance(candidate, dict):
            continue
        if (candidate.get("name") or candidate.get("appstream-name")) != name:
            continue
        if str(candidate.get("repo") or "") == repo:
            return candidate
        if fallback is None:
            fallback = candidate
    return fallback


def require_script(text: str, machine: str | None = None) -> None:
    """Check a script's ISA declarations before its preamble can mutate.

    Sane default: scripts are presumed x86_64-only unless a
    ``# architectures:`` header tags them otherwise; an aarch64 host needs
    that explicit tag to run anything. Call require_script_path for files.
    """
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
        values = ["x86_64"]
    if not _declaration_allowed(values, arch):
        raise ArchitectureError(
            f"This installer is not qualified for {arch.value}. "
            "Choose a verified native route before continuing."
        )


def require_entry(entry: Mapping[str, Any], machine: str | None = None) -> None:
    """Enforce ISA eligibility on catalog metadata before hooks/dependencies run.

    Repository listings are x86_64-only by sane default. An entry qualifies
    for aarch64 through an explicit ``architectures`` marker in its own
    listing record or through git-db.json release-asset evidence for its repo
    (an asset without architecture evidence, a single-binary asset or a
    tarball asset never grants ARM). AppStream native/Flatpak/Snap/Homebrew
    sources declare the host: the package managers and Flatpak resolve
    architecture at their own discretion.
    """
    arch = host() if machine is None else normalize(machine)
    if entry.get("name") == "Volt":
        raise ArchitectureError(
            "Volt's external Flatpak extension build requires native preflight qualification"
        )
    if entry.get("is_appstream_entry") and entry.get("type") in {
        "native", "flathub", "snap", "homebrew",
    }:
        # Self-managed sources: the AppStream data, snapd and Homebrew only
        # offer what the host can use, and their installers resolve ISA.
        # Only explicit dependency markers are honored here; payload-level
        # verification stays authoritative at execution time.
        for dependency in entry.get("dependencies") or []:
            if "architectures" in dependency and not _declaration_allowed(
                dependency["architectures"], arch
            ):
                raise ArchitectureError(
                    "A required dependency does not support this architecture"
                )
        return
    record = _listing_record(entry)
    declared = (
        _record_declared_architectures(record) if record is not None else None
    )
    if declared is not None:
        values = declared
    else:
        proven = _proven_record_architectures(
            record or {}, _git_db_for(entry.get("_list_source") or entry.get("_architecture_source"))
        )
        values = ["x86_64", *sorted(proven - {"x86_64"})]
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
    """Apply the shared ISA policy to a script file before execution."""
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
            # Inline hook snippets are x86_64-only by the same sane default;
            # ARM-qualified entries declare their hooks as header-tagged files.
            if arch is not Architecture.X86_64:
                raise ArchitectureError(
                    f"Inline {phase} hook lacks {arch.value} eligibility; "
                    "convert it to a header-tagged file hook"
                )
        else:
            raise ArchitectureError("Invalid installer hook declaration")
