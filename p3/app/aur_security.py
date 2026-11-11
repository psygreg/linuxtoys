"""Statically inspect AUR package sources before they may be installed.

Shared by the GUI AppStream runner and the TUI executor (and through them
the MCP server): the same shallow clone with hooks disabled, the same
obfuscation rules and the same findings contract. Nothing from the
repository is sourced or executed — PKGBUILD and every regular
``*.install`` file are only read.

The GitHub provenance cross-check is opt-in (``check_provenance=True``):
it is supplemental evidence and never overrides the local AUR source
inspection. Functions here are BLOCKING (network clone) and must run in
a worker thread.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# Status codes surfaced to the runners: OK flows through, UNAVAILABLE
# degrades to a warning, BLOCKED refuses the installation.
AUR_SECURITY_OK = 0
AUR_SECURITY_UNAVAILABLE = 125
AUR_SECURITY_BLOCKED = 126

AUR_SCAN_MAX_FILE = 1024 * 1024

# High-confidence obfuscation indicators only. This is intentionally not a
# general "suspicious shell" scanner: ordinary PKGBUILDs legitimately use
# curl, sed, awk, eval-like configure machinery, etc.
AUR_OBFUSCATION_RULES = (
    (
        "encoded data is decoded and executed by a shell",
        re.compile(
            r"""(?ix)
            (?:base64\s+(?:-[A-Za-z]*d|--decode)|openssl\s+(?:enc\s+)?-[A-Za-z0-9_-]*d|
               xxd\s+-r|(?:gzip|bzip2|xz)\s+-d[c]?|python[23]?\s+-c\s+[^;\n]*(?:b64decode|fromhex))
            [^;\n|]{0,240}\|\s*(?:ba|z|k|da)?sh\b
            """
        ),
    ),
    (
        "decoded or generated content is passed to eval",
        re.compile(
            r"""(?ix)
            \beval\b[^\n]{0,300}
            (?:base64|b64decode|fromhex|xxd\s+-r|openssl\s+(?:enc\s+)?-|
               printf\s+['"][^'"]*\\x[0-9a-f]{2})
            """
        ),
    ),
    (
        "eval executes command substitution",
        re.compile(r"""(?ix)\beval\s+["']?\s*\$\(\s*[^)\n]{4,}\)"""),
    ),
    (
        "a large encoded payload is embedded in the build script",
        re.compile(
            r"""(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{600,}={0,2}(?![A-Za-z0-9+/])"""
        ),
    ),
    (
        "a large hexadecimal payload is embedded in the build script",
        re.compile(r"""(?i)(?<![0-9a-f])(?:[0-9a-f]{2}){300,}(?![0-9a-f])"""),
    ),
    (
        "long hexadecimal escape sequence suggests hidden executable text",
        re.compile(r"""(?i)(?:\\x[0-9a-f]{2}){40,}"""),
    ),
)


def scan_aur_text_for_obfuscation(filename: str, text: str) -> list[str]:
    """Scan one text against the AUR obfuscation rules.

    Each rule reports at most once, at its first match.

    Args:
        filename: Name shown in the findings, relative to the repo.
        text: File content to inspect.

    Returns:
        Findings formatted as ``"<filename>:<line>: <description>"``.
        Empty if nothing matched.
    """
    findings = []
    for description, pattern in AUR_OBFUSCATION_RULES:
        match = pattern.search(text)
        if match is None:
            continue
        line = text.count("\n", 0, match.start()) + 1
        findings.append(f"{filename}:{line}: {description}")
    return findings


def _github_repo_from_url(value):
    """Return (owner, repo) for a public github.com repository URL."""
    text = str(value or "").strip()
    text = re.sub(r"^(?:git\+)+", "", text, flags=re.IGNORECASE)
    match = re.match(
        r"^(?:https?://|git://|ssh://git@|git@)?github\.com(?::|/)"
        r"([^/\s]+)/([^/#?\s]+)",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    owner = match.group(1).strip()
    repo = re.sub(r"\.git$", "", match.group(2).strip(), flags=re.IGNORECASE)
    if not owner or not repo:
        return None
    return owner.casefold(), repo.casefold()


def _github_repositories_from_pkgbuild(text):
    """Extract GitHub repository identities without evaluating the PKGBUILD."""
    repos = set()
    pattern = re.compile(
        r"(?ix)(?:(?:git\+)?https?://github\.com/|"
        r"(?:git\+)?git://github\.com/|"
        r"(?:git\+)?ssh://git@github\.com/|git@github\.com:)"
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
    )
    for match in pattern.finditer(text):
        repo = _github_repo_from_url(match.group(0))
        if repo is not None:
            repos.add(repo)
    return repos


def _github_api_repository(owner, repo):
    """Fetch public GitHub repository metadata without credentials."""
    owner = urllib.parse.quote(owner, safe="")
    repo = urllib.parse.quote(repo, safe="")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "LinuxToys-AUR-security-check",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError,
            TimeoutError, OSError, ValueError):
        # Repository reputation is supplemental. Failure to obtain GitHub
        # metadata must not override the local AUR source inspection.
        return None
    return payload if isinstance(payload, dict) else None


def _check_github_source_provenance(pkgbuild_text):
    """Return high-confidence GitHub source/upstream inconsistencies.

    Fork status alone is harmless. A fork is blocked only when its own
    parent/source repository is also named by the PKGBUILD, showing that
    the package declares one upstream while fetching executable source
    from another repository in that same GitHub fork network.
    """
    repositories = _github_repositories_from_pkgbuild(pkgbuild_text)
    if not repositories:
        return []

    findings = []
    metadata = {}
    for identity in sorted(repositories):
        data = _github_api_repository(*identity)
        if data is None:
            continue
        metadata[identity] = data
        if bool(data.get("disabled")):
            findings.append(
                f"GitHub repository {identity[0]}/{identity[1]} is disabled"
            )

        # Popularity/activity metadata is deliberately weak evidence. Never
        # block on one or two of these characteristics: small, new and niche
        # upstreams are perfectly legitimate. Require at least three distinct
        # signals before treating the repository as suspicious.
        weak_signals = []

        created_at = str(data.get("created_at") or "").strip()
        if created_at:
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                age_days = max(
                    0,
                    (datetime.now(timezone.utc) - created.astimezone(timezone.utc)).days,
                )
                if age_days < 30:
                    weak_signals.append(f"repository is only {age_days} days old")
            except (TypeError, ValueError):
                pass

        try:
            if int(data.get("stargazers_count") or 0) == 0:
                weak_signals.append("repository has no stars")
        except (TypeError, ValueError):
            pass

        try:
            if int(data.get("forks_count") or 0) == 0:
                weak_signals.append("repository has no forks")
        except (TypeError, ValueError):
            pass

        # subscribers_count is GitHub's watcher count. watchers_count mirrors
        # stargazers_count and must not be counted as a separate signal.
        try:
            if int(data.get("subscribers_count") or 0) == 0:
                weak_signals.append("repository has no watchers")
        except (TypeError, ValueError):
            pass

        try:
            # GitHub reports repository size in KiB. A tiny repository is only
            # corroborating evidence and is never sufficient by itself.
            if int(data.get("size") or 0) < 64:
                weak_signals.append("repository is unusually small")
        except (TypeError, ValueError):
            pass

        if len(weak_signals) >= 3:
            findings.append(
                f"GitHub repository {identity[0]}/{identity[1]} has multiple "
                f"low-reputation signals: " + "; ".join(weak_signals)
            )

    for (owner, repo), data in metadata.items():
        if not bool(data.get("fork")):
            continue
        ancestors = set()
        for key in ("parent", "source"):
            ancestor = data.get(key)
            if not isinstance(ancestor, dict):
                continue
            full_name = str(ancestor.get("full_name") or "").strip()
            if "/" not in full_name:
                continue
            ancestor_owner, ancestor_repo = full_name.split("/", 1)
            ancestors.add((ancestor_owner.casefold(), ancestor_repo.casefold()))

        matched = ancestors & repositories
        if matched:
            upstream = ", ".join(
                f"{a}/{r}" for a, r in sorted(matched)
            )
            findings.append(
                f"GitHub source {owner}/{repo} is a fork while the PKGBUILD "
                f"also identifies its upstream repository as {upstream}"
            )
    return findings


def check_aur_package_security(
    package: str, *, check_provenance: bool = False
) -> tuple[int, str]:
    """Statically check AUR package sources for obfuscated code.

    BLOCKING: call from a worker thread (network clone, 45 s timeout).

    Shallow-clones ``https://aur.archlinux.org/<package>.git`` into a
    temporary directory with git hooks disabled, then scans the
    ``PKGBUILD`` and every ``*.install`` file against the obfuscation
    rules. Nothing from the repository is executed. Symbolic links and
    the ``.git`` directory are skipped, files over 1 MiB are reported
    as findings instead of being scanned, and the temporary directory
    is always removed. Expected failures are returned, not raised.

    Args:
        package: AUR package name. Must match ``[A-Za-z0-9@._+:-]+``.
        check_provenance: Also cross-check GitHub sources named by the
            PKGBUILD against the GitHub API (used by the GUI runner; see
            :func:`_check_github_source_provenance`).

    Returns:
        A ``(status, message)`` tuple:

        - ``(AUR_SECURITY_OK, "")``: no findings.
        - ``(AUR_SECURITY_BLOCKED, findings)``: at most 20 findings,
          one per line.
        - ``(AUR_SECURITY_UNAVAILABLE, reason)``: the check could not
          run (git missing, invalid name, clone failure or timeout,
          unreadable or missing PKGBUILD).
    """
    git = shutil.which("git")
    if not git:
        return (
            AUR_SECURITY_UNAVAILABLE,
            "Git is required to verify the AUR package sources.",
        )

    safe_package = str(package or "").strip()
    if not safe_package or not re.fullmatch(
        r"[A-Za-z0-9@._+:-]+", safe_package
    ):
        return (
            AUR_SECURITY_UNAVAILABLE,
            "The AUR package name could not be safely verified.",
        )

    temp_root = tempfile.mkdtemp(prefix="linuxtoys-aur-verify-")
    repo_dir = os.path.join(temp_root, "repo")
    try:
        repository = f"https://aur.archlinux.org/{safe_package}.git"
        try:
            result = subprocess.run(
                [
                    git,
                    "-c",
                    "protocol.file.allow=never",
                    "clone",
                    "--quiet",
                    "--depth",
                    "1",
                    "--no-tags",
                    "--config",
                    "core.hooksPath=/dev/null",
                    repository,
                    repo_dir,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=45,
                check=False,
                env={
                    **os.environ,
                    "GIT_TERMINAL_PROMPT": "0",
                    "GIT_CONFIG_NOSYSTEM": "1",
                },
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return (
                AUR_SECURITY_UNAVAILABLE,
                f"Could not fetch the AUR repository for verification: {exc}",
            )

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            if len(detail) > 1000:
                detail = detail[-1000:]
            return (
                AUR_SECURITY_UNAVAILABLE,
                "Could not fetch the AUR repository for verification."
                + (f"\n\n{detail}" if detail else ""),
            )

        candidates = []
        pkgbuild = os.path.join(repo_dir, "PKGBUILD")
        if os.path.isfile(pkgbuild) and not os.path.islink(pkgbuild):
            candidates.append(pkgbuild)

        # .install files are package-manager hooks executed around package
        # installation/removal. Scan all regular ones tracked in the AUR repo,
        # which also covers PKGBUILDs that choose the hook indirectly.
        for root, dirs, files in os.walk(repo_dir, followlinks=False):
            dirs[:] = [d for d in dirs if d != ".git"]
            for filename in files:
                if not filename.endswith(".install"):
                    continue
                path = os.path.join(root, filename)
                if os.path.isfile(path) and not os.path.islink(path):
                    candidates.append(path)

        if not candidates or pkgbuild not in candidates:
            return (
                AUR_SECURITY_UNAVAILABLE,
                "The AUR repository did not contain a readable PKGBUILD.",
            )

        findings = []
        pkgbuild_source = None
        for path in candidates:
            try:
                size = os.path.getsize(path)
                if size > AUR_SCAN_MAX_FILE:
                    relative = os.path.relpath(path, repo_dir)
                    findings.append(
                        f"{relative}: file is too large to safely inspect "
                        f"({size} bytes)"
                    )
                    continue
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    source = handle.read(AUR_SCAN_MAX_FILE + 1)
            except OSError as exc:
                return (
                    AUR_SECURITY_UNAVAILABLE,
                    f"Could not read an AUR source file for verification: {exc}",
                )

            relative = os.path.relpath(path, repo_dir)
            if path == pkgbuild:
                pkgbuild_source = source
            findings.extend(
                scan_aur_text_for_obfuscation(relative, source)
            )

        if check_provenance and pkgbuild_source is not None:
            findings.extend(
                _check_github_source_provenance(pkgbuild_source)
            )
        if findings:
            return (
                AUR_SECURITY_BLOCKED,
                "\n".join(findings[:20]),
            )
        return AUR_SECURITY_OK, ""
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
