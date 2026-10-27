from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass

from app.skills_fetcher import fetch_popular as _fetch_popular
from app.skills_fetcher import search_skills as _search_skills

SKILLS_SH_URL = "https://skills.sh"

LIST_TIMEOUT = 30
INSTALL_TIMEOUT = 120
REMOVE_TIMEOUT = 60
# (config directory parts under $HOME, agent id used by ``npx skills -a``)
_AGENT_DIRS: tuple[tuple[tuple[str, ...], str], ...] = (
    ((".claude",), "claude-code"),
    ((".codex",), "codex"),
    ((".config", "opencode"), "opencode"),
    ((".cursor",), "cursor"),
    ((".windsurf",), "windsurf"),
    ((".gemini",), "gemini-cli"),
    ((".agents",), "cline"),
    ((".roo",), "roo"),
    ((".trae",), "trae"),
    ((".kilocode",), "kilo"),
    ((".factory",), "droid"),
    ((".copilot",), "github-copilot"),
)

_MOCK_INSTALLED = [
    {
        "name": "react-expert",
        "agents": ["claude-code", "opencode"],
        "source": "ai-agents",
    },
    {"name": "python-debugger", "agents": ["claude-code"], "source": "devs"},
    {
        "name": "docker-helper",
        "agents": ["codex", "claude-code"],
        "source": "devs",
    },
    {
        "name": "git-workflow",
        "agents": ["opencode", "cline"],
        "source": "ai-agents",
    },
    {"name": "test-generator", "agents": ["claude-code"], "source": "devs"},
]


class SkillsError(Exception):
    """Base class for all errors of the skills domain."""


class NpxNotFoundError(SkillsError):
    """Raised when ``npx`` (Node.js) is not available in ``PATH``."""


class MissingSourceError(SkillsError):
    """Raised when a skill lacks the data an operation needs.

    That means no ``source`` or skill id for an install, or no
    ``name`` for a removal.
    """


class CommandError(SkillsError):
    """Raised when an npx command fails; ``str(e)`` is the raw message."""


@dataclass(frozen=True)
class OpResult:
    """Immutable result of an npx operation.

    Attributes:
        ok: True if the command succeeded (for removals, if every
            command succeeded).
        stdout: Captured standard output, stripped.
        stderr: Captured standard error, stripped, or the joined error
            messages.
        timed_out: True if the command hit its timeout.
    """

    ok: bool
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @property
    def message(self) -> str:
        return self.stdout or self.stderr


def is_dev_mode() -> bool:
    return os.environ.get("DEV_MODE") == "1"


def format_installs(count) -> str:
    """Format an install count with a K or M suffix.

    Examples:
        >>> format_installs(1200)
        '1.2K'
        >>> format_installs(3_500_000)
        '3.5M'
        >>> format_installs("abc")
        '0'

    Args:
        count: Number of installs. A value that cannot be converted
            to ``int`` is treated as zero.

    Returns:
        The formatted text. Values below one thousand are returned
        unchanged.
    """
    try:
        count = int(count)
    except (TypeError, ValueError):
        return "0"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def detect_agents() -> list[str]:
    """Return the AI agents found on this system.

    An agent is detected when its configuration directory exists in
    the home directory (see ``_AGENT_DIRS``).

    Returns:
        Agent ids accepted by ``npx skills -a``, in the order of
        ``_AGENT_DIRS``.
    """
    home = os.path.expanduser("~")
    return [
        agent
        for parts, agent in _AGENT_DIRS
        if os.path.isdir(os.path.join(home, *parts))
    ]


def find_npx() -> str | None:
    return shutil.which("npx")


def skill_url(skill: dict) -> str | None:
    source = skill.get("source", "")
    skill_id = skill.get("skillId") or skill.get("id", "")
    if not source or not skill_id:
        return None
    return f"{SKILLS_SH_URL}/{source}/{skill_id}"


def open_skill_url(skill: dict) -> bool:
    """Open the skill page in the default browser (``xdg-open``).

    Does not wait for the browser and discards its output.

    Args:
        skill: Skill dict.

    Returns:
        True if the browser was launched. False if the URL cannot be
        built or ``xdg-open`` cannot be started.
    """
    url = skill_url(skill)
    if not url:
        return False
    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return True


def _normalize(raw: dict) -> dict:
    """Keep only the fields the TUI uses, with safe defaults.

    Args:
        raw: Skill dict returned by ``app.skills_fetcher``.

    Returns:
        Dict with ``id``, ``skillId``, ``name``, ``installs`` (0 by
        default) and ``source``.
    """
    return {
        "id": raw.get("id", ""),
        "skillId": raw.get("skillId", ""),
        "name": raw.get("name", ""),
        "installs": raw.get("installs", 0),
        "source": raw.get("source", ""),
    }


def load_popular(limit: int = 50) -> list[dict]:
    return [_normalize(s) for s in _fetch_popular(limit).get("skills", [])]


def search(query: str, limit: int = 20) -> list[dict]:
    return [
        _normalize(s) for s in _search_skills(query, limit).get("skills", [])
    ]


def _run_npx(args: tuple[str, ...], timeout: int) -> OpResult:
    """Run ``npx`` with ``args`` and capture its output.

    BLOCKING: call from a worker thread.

    Args:
        args: Arguments for ``npx`` (e.g. ``("skills", "list")``).
        timeout: Maximum run time in seconds.

    Returns:
        An ``OpResult``. ``ok`` is True on exit code 0. A timeout sets
        ``timed_out``. An ``OSError`` puts its message in ``stderr``.

    Raises:
        NpxNotFoundError: If ``npx`` is not in ``PATH``.
    """
    npx = find_npx()
    if not npx:
        raise NpxNotFoundError
    try:
        r = subprocess.run(
            [npx, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return OpResult(False, timed_out=True)
    except OSError as e:
        return OpResult(False, stderr=str(e))
    return OpResult(r.returncode == 0, r.stdout.strip(), r.stderr.strip())


def install_skill(skill: dict, agent: str) -> OpResult:
    """Install a skill globally for one agent (``npx skills add``).

    Runs non-interactively (``-y``) with the global flag (``-g``) and
    the ``INSTALL_TIMEOUT`` limit. BLOCKING: call from a worker
    thread.

    Args:
        skill: Skill dict with ``source`` and ``skillId`` (or ``id``).
        agent: Agent id from ``detect_agents`` (value of ``-a``).

    Returns:
        The operation result.

    Raises:
        MissingSourceError: If the skill has no source or id.
        NpxNotFoundError: If ``npx`` is not available.
    """
    source = skill.get("source", "")
    slug = skill.get("skillId") or skill.get("id", "")
    if not source or not slug:
        raise MissingSourceError
    return _run_npx(
        ("skills", "add", source, "--skill", slug, "-a", agent, "-g", "-y"),
        INSTALL_TIMEOUT,
    )


def list_installed() -> list[dict]:
    """List the globally installed skills (``npx skills list``).

    In developer mode it returns sample data instead of running npx.
    BLOCKING: call from a worker thread.

    Returns:
        Skill dicts; the code relies on ``name`` and ``agents``.
        Empty if the output is empty or is not a JSON list.

    Raises:
        NpxNotFoundError: If ``npx`` is not available.
        CommandError: If the command fails or times out, or its output
            is not valid JSON.
    """
    if is_dev_mode():
        return list(_MOCK_INSTALLED)
    res = _run_npx(("skills", "list", "--json", "-g"), LIST_TIMEOUT)
    if not res.ok:
        raise CommandError(res.stderr or "timeout")
    try:
        data = json.loads(res.stdout or "[]")
    except json.JSONDecodeError as e:
        raise CommandError(str(e)) from e
    return data if isinstance(data, list) else []


def remove_skill(skill: dict) -> OpResult:
    """Remove a skill from every agent it is linked to.

    Runs ``npx skills remove`` once per agent in ``skill["agents"]``,
    or once without ``-a`` if the skill has no agents. Agent names are
    converted to ids on a best-effort basis (lowercase, spaces to
    hyphens), the same mapping the GUI uses. A failing command does
    not stop the others. BLOCKING: call from a worker thread.

    Args:
        skill: Skill dict with ``name`` and, optionally, ``agents``.

    Returns:
        ``OpResult`` whose ``ok`` is True only if every command
        succeeded. ``stderr`` joins the errors of the failed ones.

    Raises:
        MissingSourceError: If the skill has no name.
        NpxNotFoundError: If ``npx`` is not available.
    """
    name = skill.get("name", "")
    agents = skill.get("agents", [])
    if not name:
        raise MissingSourceError

    if agents:
        commands = [
            (
                "skills",
                "remove",
                name,
                "-a",
                a.lower().replace(" ", "-"),
                "-g",
                "-y",
            )
            for a in agents
        ]
    else:
        commands = [("skills", "remove", name, "-g", "-y")]

    errors: list[str] = []
    for cmd in commands:
        res = _run_npx(cmd, REMOVE_TIMEOUT)
        if not res.ok:
            errors.append(
                res.stderr or ("timeout" if res.timed_out else "error")
            )
    return OpResult(not errors, stderr="\n".join(errors))
