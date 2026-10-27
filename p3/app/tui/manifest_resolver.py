"""Resolve and validate manifest entries for the TUI, without executing.

Mirrors the validation pipeline of the CLI ``run_manifest_mode`` but never
prints, prompts, installs or touches the UI. ``resolve_manifest`` returns
a :class:`ManifestPlan` that the caller can review, confirm and execute.

Supported entry syntax:

- ``script:<id>[@<source>]``: LinuxToys script by stable ID, optionally
  forced to one source (``native``, ``flatpak``, ``snap`` or
  ``homebrew``).
- ``package:<name>`` or ``pkg:<name>``: native package.
- ``flatpak:<id>``, ``snap:<name>`` and ``homebrew:<formula>``.
- ``require:flathub``: declares that Flathub must be ready.
- Any other entry is auto-detected: LinuxToys script by name first, then
  Flatpak ID, then native package.

Missing prerequisites (Flatpak/Flathub, Homebrew) are flagged in
``ManifestPlan.bootstrap`` and never installed here, because setting them
up may need ``sudo`` and therefore a real terminal.

``resolve_manifest`` is BLOCKING (subprocesses and ``asyncio.run``), so
it must be called from a worker thread, never from the Textual event
loop.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field

from app import homebrew_catalog
from app.manifest_helper import (
    _prepare_homebrew_manifest_entries,
    _select_manifest_source,
    appstream_cache,
    appstream_parser,
    check_flatpaks_async,
    check_package_exists,
    find_script_by_id,
    find_script_by_name,
    get_system_compat_keys,
    is_containerized,
    materialize_repo_script,
    script_is_compatible,
    script_is_container_compatible,
    valid_flatpak_id,
    valid_manifest_value,
    valid_package_name,
)

_ENTRY_PREFIXES = frozenset(
    {"script", "package", "pkg", "flatpak", "snap", "homebrew", "require"}
)
_SOURCE_OVERRIDES = frozenset({"native", "flatpak", "snap", "homebrew"})
_SUPPORTED_REQUIREMENTS = frozenset({"flathub"})
_FORMULA_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+_.@-]*")


@dataclass
class ManifestPlan:
    """Result of resolving a manifest against the current system.

    The plan is safe to execute only if ``is_valid`` is True and
    ``bootstrap`` is None. ``errors`` are blocking: if any is present,
    nothing must be executed. ``warnings`` are non-blocking and list items
    skipped for compatibility reasons.

    ``bootstrap`` is ``"flatpak"`` or ``"homebrew"`` when a prerequisite
    must be set up before the manifest can be resolved. The plan is then
    incomplete and must be discarded: set the prerequisite up, then call
    ``resolve_manifest`` again. Resolution never performs the bootstrap
    itself, because it may need ``sudo`` and therefore a real terminal.

    Attributes:
        scripts: Runnable script info dicts (LinuxToys, repository,
            AppStream and Homebrew entries), without duplicates.
        packages: Native package names, without duplicates.
        snaps: Snap names, without duplicates.
        flatpaks: Flatpak IDs confirmed in the configured remotes.
        errors: Blocking problems, as user-facing messages.
        warnings: Skipped items, as user-facing messages.
        bootstrap: Prerequisite to set up first (``"flatpak"`` or
            ``"homebrew"``), or None.
        bootstrap_script: Script info that sets Homebrew up. Only set
            when ``bootstrap`` is ``"homebrew"``.
    """

    scripts: list[dict] = field(default_factory=list)
    packages: list[str] = field(default_factory=list)
    snaps: list[str] = field(default_factory=list)
    flatpaks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bootstrap: str | None = None
    bootstrap_script: dict | None = None

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def total(self) -> int:
        return (
            len(self.scripts)
            + len(self.packages)
            + len(self.snaps)
            + len(self.flatpaks)
        )


@dataclass
class _Entries:
    """Manifest entries grouped by how they were declared.

    Attributes:
        scripts: ``(script_id, source)`` pairs from ``script:`` entries.
            ``source`` is an empty string when no override was given.
        packages: Names from ``package:`` and ``pkg:`` entries.
        snaps: Names from ``snap:`` entries.
        flatpaks: IDs from ``flatpak:`` entries.
        homebrew: Formula names from ``homebrew:`` entries.
        auto: Unprefixed entries, left for auto-detection.
        requirements: Supported ``require:`` values, lowercased.
    """

    scripts: list[tuple[str, str]] = field(default_factory=list)
    packages: list[str] = field(default_factory=list)
    snaps: list[str] = field(default_factory=list)
    flatpaks: list[str] = field(default_factory=list)
    homebrew: list[str] = field(default_factory=list)
    auto: list[str] = field(default_factory=list)
    requirements: set[str] = field(default_factory=set)


def resolve_manifest(names: list[str], translations=None) -> ManifestPlan:
    """Classify and validate manifest entries without executing anything.

    BLOCKING: call from a worker thread (subprocesses and
    ``asyncio.run``). Do not call it from the Textual event loop or from
    a thread that already runs an asyncio loop.

    Each call uses a fresh resolver, so calls are independent. The result
    may be incomplete: resolution stops early when a prerequisite must be
    bootstrapped or when Homebrew formulae are invalid. Always check
    ``ManifestPlan.bootstrap`` and ``ManifestPlan.errors``. Invalid
    entries are reported in ``errors``, not raised.

    Args:
        names: Raw manifest entries, e.g. ``"script:<id>@flatpak"``,
            ``"flatpak:org.mozilla.firefox"`` or an unprefixed name.
        translations: Optional translations mapping, forwarded to the
            script lookups.

    Returns:
        The resolved plan.
    """
    return _ManifestResolver(translations).resolve(names)


def refresh_appstream_after_flathub() -> None:
    """Rebuild the AppStream cache so Flathub entries become visible.

    BLOCKING: call from a worker thread (forces a full cache refresh).

    Call it after the Flathub bootstrap and before resolving the manifest
    again. It refreshes the on-disk cache, then clears the in-memory
    parser cache. Mirrors the tail of the CLI's
    ``_bootstrap_flatpak_for_manifest``.
    """
    appstream_cache.refresh_cache(force=True)
    appstream_parser.clear_runtime_cache()


def _flathub_ready() -> bool:
    """Return True when Flatpak is installed and the Flathub remote exists.

    BLOCKING: runs ``flatpak remote-list`` (30 s timeout). A missing
    binary, a non-zero exit, a timeout or an OS error all return False
    instead of raising.
    """
    if shutil.which("flatpak") is None:
        return False
    try:
        remote = subprocess.run(
            ["flatpak", "remote-list", "--columns=name"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
            env=os.environ.copy(),
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    remotes = {line.strip() for line in remote.stdout.splitlines()}
    return remote.returncode == 0 and "flathub" in remotes


def _split_script_source(value: str) -> tuple[str, str]:
    """Split ``id@source`` into ``(id, source)``; source is '' if absent."""
    script_id, separator, source = value.rpartition("@")
    if separator and source.casefold() in _SOURCE_OVERRIDES:
        return script_id, source.casefold()
    return value, ""


class _ManifestResolver:
    """Single-use resolver that builds one :class:`ManifestPlan`.

    The constructor captures the system compatibility keys, the container
    state and whether the system is SteamOS. The plan accumulates inside
    the instance, so create a new resolver for each manifest.

    BLOCKING: see ``resolve_manifest``.

    Args:
        translations: Optional translations mapping, forwarded to the
            script lookups.
    """

    def __init__(self, translations=None) -> None:
        self._translations = translations
        self._plan = ManifestPlan()
        self._compat_keys = get_system_compat_keys()
        self._containerized = is_containerized()
        self._steamos = "steamos" in self._compat_keys
        self._auto_flatpaks: list[str] = []

    def resolve(self, names: list[str]) -> ManifestPlan:
        """Run the whole resolution pipeline and return the plan.

        Stages, in order: parse, Flatpak prerequisite, Homebrew formulae,
        native packages, snaps, explicit scripts, auto-detected items,
        Flatpak batch check and de-duplication. The pipeline returns the
        partial plan early when a prerequisite needs a bootstrap or when
        Homebrew formulae are invalid. Errors from the later stages are
        then not collected.

        De-duplication keeps the first occurrence and the original
        order. Scripts are compared by ``(name, path)``.

        Args:
            names: Raw manifest entries.

        Returns:
            The resolved, possibly incomplete, plan.
        """
        entries = self._parse(names)

        if not self._flatpak_available(entries):
            return self._plan
        if not self._add_homebrew(entries.homebrew):
            return self._plan

        for name in entries.packages:
            self._add_package(name)
        for name in entries.snaps:
            self._add_snap(name)

        self._add_explicit_scripts(entries.scripts)
        if self._plan.bootstrap:
            return self._plan
        for name in entries.auto:
            self._add_auto_item(name)

        self._add_flatpaks(entries.flatpaks + self._auto_flatpaks)

        self._plan.packages = list(dict.fromkeys(self._plan.packages))
        self._plan.snaps = list(dict.fromkeys(self._plan.snaps))
        unique_scripts: dict[tuple, dict] = {}
        for script in self._plan.scripts:
            key = (script.get("name"), script.get("path"))
            unique_scripts.setdefault(key, script)
        self._plan.scripts = list(unique_scripts.values())
        return self._plan

    def _parse(self, names: list[str]) -> _Entries:
        """Group raw entries by prefix.

        The prefix match is case-insensitive. Entries without a known
        prefix are left in ``auto`` for auto-detection. An empty value
        after a known prefix, or an unsupported ``require:`` value, is
        recorded as an error.

        Args:
            names: Raw manifest entries.

        Returns:
            The grouped entries.
        """
        entries = _Entries()
        for raw_name in names:
            prefix, separator, value = raw_name.partition(":")
            kind = prefix.lower()
            if not separator or kind not in _ENTRY_PREFIXES:
                # Unprefixed entries keep the CLI auto-detection.
                entries.auto.append(raw_name)
                continue

            value = value.strip()
            if not value:
                self._plan.errors.append(
                    f"Entrada vazia no manifesto: '{raw_name}'."
                )
            elif kind == "script":
                entries.scripts.append(_split_script_source(value))
            elif kind in {"package", "pkg"}:
                entries.packages.append(value)
            elif kind == "homebrew":
                entries.homebrew.append(value)
            elif kind == "snap":
                entries.snaps.append(value)
            elif kind == "require":
                requirement = value.casefold()
                if requirement in _SUPPORTED_REQUIREMENTS:
                    entries.requirements.add(requirement)
                else:
                    self._plan.errors.append(
                        f"Requisito de manifesto desconhecido: '{value}'."
                    )
            else:
                entries.flatpaks.append(value)
        return entries

    def _flatpak_available(self, entries: _Entries) -> bool:
        """Check that Flathub is ready when the manifest needs it.

        BLOCKING: may run ``flatpak remote-list``.

        Flatpak is needed by ``require:flathub``, by ``flatpak:`` entries
        and by ``script:`` entries forced to the ``flatpak`` source. If it
        is needed but not ready, ``plan.bootstrap`` is set to
        ``"flatpak"``.

        Args:
            entries: The parsed entries.

        Returns:
            False if resolution must stop for a Flatpak bootstrap, True
            otherwise.
        """
        needs_flatpak = (
            "flathub" in entries.requirements
            or bool(entries.flatpaks)
            or any(source == "flatpak" for _id, source in entries.scripts)
        )
        if needs_flatpak and not _flathub_ready():
            self._plan.bootstrap = "flatpak"
            return False
        return True

    def _add_homebrew(self, names: list[str]) -> bool:
        """Validate Homebrew formulae, then check that Brew is present.

        Names are de-duplicated and validated before anything else. If
        the Homebrew catalog is disabled, the ``brew`` script is stored in
        ``plan.bootstrap_script`` and ``plan.bootstrap`` is set to
        ``"homebrew"``, or an error is recorded if that script is missing.
        Otherwise the prepared entries are appended to ``plan.scripts``.

        Args:
            names: Formula names from ``homebrew:`` entries.

        Returns:
            True if there is nothing to do or the formulae were added.
            False if resolution must stop (invalid names, bootstrap
            needed or preparation failure).
        """
        if not names:
            return True

        formulae = list(dict.fromkeys(names))
        invalid = [
            formula
            for formula in formulae
            if not valid_manifest_value(formula)
            or not _FORMULA_RE.fullmatch(formula)
        ]
        if invalid:
            self._plan.errors.extend(
                f"Nome de fórmula Homebrew inválido: {formula!r}."
                for formula in invalid
            )
            return False

        if not homebrew_catalog.enabled():
            brew_script = find_script_by_id("brew", self._translations)
            if brew_script is None:
                self._plan.errors.append(
                    "Não foi possível preparar o Homebrew exigido por este "
                    "manifesto: o script 'brew' não foi encontrado."
                )
            else:
                self._plan.bootstrap = "homebrew"
                self._plan.bootstrap_script = brew_script
            return False

        try:
            self._plan.scripts.extend(
                _prepare_homebrew_manifest_entries(
                    formulae, self._translations
                )
            )
        except ValueError as exc:
            self._plan.errors.append(str(exc))
            return False
        return True

    def _add_package(self, name: str, *, auto: bool = False) -> None:
        """Validate a native package and record it in the plan.

        BLOCKING: ``check_package_exists`` may run external commands.

        Outcomes: an invalid name is an error. On SteamOS the package is
        skipped with a warning, because native packages are not
        supported there. A package that exists is added to
        ``plan.packages``, and a missing one is an error.

        Args:
            name: Package name.
            auto: True when the entry had no prefix and matched neither a
                script nor a Flatpak ID. Only changes the error messages.
        """
        if not valid_package_name(name):
            kind = "Item inseguro ou malformado" if auto else "Pacote inválido"
            self._plan.errors.append(f"{kind}: '{name}'.")
        elif self._steamos:
            # The CLI refuses native packages on SteamOS; say so up front.
            self._plan.warnings.append(
                f"Pacote '{name}' ignorado: pacotes nativos não são "
                "suportados no SteamOS."
            )
        elif check_package_exists(name):
            self._plan.packages.append(name)
        elif auto:
            self._plan.errors.append(
                f"'{name}' não é um script do LinuxToys nem um pacote "
                "disponível."
            )
        else:
            self._plan.errors.append(
                f"Pacote '{name}' não encontrado nos repositórios disponíveis."
            )

    def _add_snap(self, name: str) -> None:
        """Validate a snap name and add it to the plan.

        Only the name format is checked. The snap's existence is not
        verified.

        Args:
            name: Snap name.
        """
        if valid_package_name(name):
            self._plan.snaps.append(name)
        else:
            self._plan.errors.append(f"Nome de snap inválido: '{name}'.")

    def _add_flatpaks(self, candidates: list[str]) -> None:
        """Validate Flatpak IDs, then check them in one async batch.

        BLOCKING: runs ``asyncio.run``, so the calling thread must not
        already have a running event loop.

        IDs are de-duplicated and validated first, and invalid ones are
        recorded as errors. The rest are checked together, and IDs not
        found in the configured remotes become errors. Results are paired
        with the IDs by position.

        Args:
            candidates: Flatpak IDs from ``flatpak:`` entries and from
                auto-detected items.
        """
        valid_ids = []
        for name in dict.fromkeys(candidates):
            if valid_flatpak_id(name):
                valid_ids.append(name)
            else:
                self._plan.errors.append(f"ID Flatpak inválido: '{name}'.")
        if not valid_ids:
            return

        found = asyncio.run(check_flatpaks_async(valid_ids))
        for name, exists in zip(valid_ids, found):
            if exists:
                self._plan.flatpaks.append(name)
            else:
                self._plan.errors.append(
                    f"Flatpak '{name}' não encontrado nos remotes "
                    "configurados."
                )

    def _add_explicit_scripts(self, entries: list[tuple[str, str]]) -> None:
        """Resolve ``script:`` entries strictly through stable IDs.

        Unknown IDs are errors, unless Flathub is not ready. In that case
        ``plan.bootstrap`` is set to ``"flatpak"`` and the method returns
        without adding anything, because a Flathub-only AppStream app is
        not visible on a fresh system. When a source is given, the entry
        is narrowed to that source, and an ID that does not offer it is an
        error. Accepted scripts are appended to ``plan.scripts``.

        Args:
            entries: ``(script_id, source)`` pairs, where ``source`` is
                empty if not overridden.
        """
        resolved: list[tuple[str, str, dict]] = []
        unresolved: list[tuple[str, str]] = []
        for script_id, source in entries:
            info = find_script_by_id(script_id, self._translations)
            if info is None:
                unresolved.append((script_id, source))
            else:
                resolved.append((script_id, source, info))

        # A portable ID may point to a Flathub-only AppStream app that is not
        # visible on a fresh system: ask the caller to bootstrap and retry.
        if unresolved and not _flathub_ready():
            self._plan.bootstrap = "flatpak"
            return

        for script_id, _source in unresolved:
            self._plan.errors.append(
                f"ID do LinuxToys '{script_id}' não encontrado neste sistema."
            )

        for script_id, source, info in resolved:
            display = f"script:{script_id}"
            if source:
                info = _select_manifest_source(info, source)
                display = f"{display}@{source}"
                if info is None:
                    self._plan.errors.append(
                        f"O ID '{script_id}' não oferece a fonte '{source}' "
                        "neste sistema."
                    )
                    continue
            script = self._accept_script(info, display)
            if script is not None:
                self._plan.scripts.append(script)

    def _add_auto_item(self, name: str) -> None:
        """Resolve an unprefixed manifest entry.

        Order of detection: LinuxToys/AppStream script by name, then a
        Flatpak ID (deferred to the batch check in ``_add_flatpaks``),
        then a native package.

        Args:
            name: Raw entry without a known prefix.
        """
        info = find_script_by_name(name, self._translations)
        if info is None:
            # Not a LinuxToys/AppStream entry: try Flatpak, then package.
            if valid_flatpak_id(name):
                self._auto_flatpaks.append(name)
            else:
                self._add_package(name, auto=True)
            return

        script = self._accept_script(info, name)
        if script is not None:
            self._plan.scripts.append(script)

    def _accept_script(self, info: dict, display: str) -> dict | None:
        """Apply the source-specific checks to a resolved script.

        Homebrew entries need the Homebrew catalog enabled. Repository
        entries are materialized once, only to validate them, so a bad
        entry aborts before anything runs. Other entries need a real file
        path (virtual ``://`` paths are rejected) and must be compatible
        with the system and, in containers, with containers.
        Incompatibility is a warning, the rest are errors.

        The returned dict is always the original ``info``. The runner
        materializes Homebrew and repository entries again right before
        execution (the generated file is deterministic), so that
        ``is_repo_entry`` stays available to ``script_environment``.

        Args:
            info: Script info dict.
            display: Label used in messages, e.g. ``"script:<id>@snap"``.

        Returns:
            ``info`` if the script can run, otherwise None with an error
            or warning recorded in the plan.
        """
        if info.get("appstream_source") == "homebrew":
            if not homebrew_catalog.enabled():
                self._plan.errors.append(
                    f"Homebrew não está habilitado para '{display}'."
                )
                return None
            return info

        if info.get("is_repo_entry"):
            # Validate now so a bad entry aborts before anything runs.
            try:
                materialize_repo_script(info)
            except (ValueError, NotImplementedError, OSError) as exc:
                self._plan.errors.append(
                    f"Não foi possível preparar '{display}': {exc}"
                )
                return None
            return info

        path = info.get("path") or ""
        if not path or "://" in path:
            # Safety net: a virtual path that nothing can materialize would
            # crash the runner when it tries to open the file.
            self._plan.errors.append(
                f"'{display}' não possui um script executável neste sistema."
            )
            return None
        if not script_is_compatible(path, self._compat_keys):
            self._plan.warnings.append(
                f"'{display}' não é compatível com este sistema."
            )
            return None
        if self._containerized and not script_is_container_compatible(path):
            self._plan.warnings.append(
                f"'{display}' não é compatível com sistemas em container."
            )
            return None
        return info
