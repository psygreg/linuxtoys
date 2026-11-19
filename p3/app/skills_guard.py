"""Safety guards for skills.sh references.

Skill sources, ids and agent ids come from the skills.sh catalog:
remote, user-publishable data. The Skills Seeker passes them to the
``npx skills`` CLI and embeds them in a generated bash install script
that auto-runs, so they are validated against a strict slug charset
(no shell metacharacters, no leading dash) and every value is
shell-quoted when it reaches script text. Shared by the GUI and the
TUI.
"""
from __future__ import annotations

import re
import shlex

# One or more ``/``-separated segments of letters, digits, ``.``, ``_``
# and ``-``. Every segment starts alphanumeric, so option-style values
# (``-a``, ``--global``) and shell metacharacters (``$``, quotes,
# whitespace, control characters) are refused outright. ``fullmatch``
# is used so a trailing newline cannot sneak past the end anchor.
_SKILL_REFERENCE_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*"
)

# Filename-component relaxation of the same charset (slashes removed).
_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


class InvalidSkillReferenceError(ValueError):
    """Raised when a skill source, id or agent id fails validation."""


def is_valid_skill_reference(value: object) -> bool:
    """Return True when ``value`` is a safe skill reference.

    Remote skill data flows into shell contexts (generated install
    scripts and ``npx`` argv), so only references built from letters,
    digits, ``.``, ``_``, ``-`` and internal ``/`` separators are
    accepted. Values that start with a dash are refused to prevent
    option-style argument injection into the ``skills`` CLI.
    """
    if not isinstance(value, str) or not value:
        return False
    return _SKILL_REFERENCE_RE.fullmatch(value) is not None


def sanitize_filename_part(value: object, max_length: int = 64) -> str:
    """Reduce a remote skill string to a safe filename component.

    Every character outside the reference charset is replaced by ``_``
    (slashes included, so the result is always a single component) and
    the result is capped so composed filenames stay well below the
    filesystem limit.
    """
    if not isinstance(value, str):
        return "unknown"
    cleaned = _FILENAME_SAFE_RE.sub("_", value).strip("._-")
    return cleaned[:max_length] or "skill"


def build_install_script(
    source: str, slug: str, agent: str, host_value: str
) -> str:
    """Return the bash script text that installs one skill.

    The script follows the generated-script conventions: the host
    ``# architectures:`` header (local/generated scripts are never
    ISA-pinned), the bash core source line, and the ``npx skills add``
    invocation.

    Raises:
        InvalidSkillReferenceError: If ``source``, ``slug`` or
            ``agent`` is not a valid skill reference. No script text is
            built in that case.

    Args:
        source: Skill source from the skills.sh catalog.
        slug: Skill id (``skillId``/``id``) from the catalog.
        agent: Agent id accepted by ``npx skills -a``.
        host_value: Host ISA value for the architectures header.
    """
    if not (
        is_valid_skill_reference(source)
        and is_valid_skill_reference(slug)
        and is_valid_skill_reference(agent)
    ):
        raise InvalidSkillReferenceError(
            "Skill source, id or agent id contains characters that "
            "are not allowed."
        )
    # ``source``/``slug`` are remote, user-publishable data. The charset
    # validation above is the primary control; every value is also
    # shell-quoted so the generated script cannot break out of its
    # quotes even if the charset rule is ever loosened.
    return (
        "#!/bin/bash\n"
        f"# architectures: {host_value}\n"
        f"# name: Install Skill {sanitize_filename_part(slug)}\n"
        f"# description: Install skill {sanitize_filename_part(source)}"
        f" for agent {agent}\n"
        'source "$SCRIPT_DIR/libs/linuxtoys.bash"\n'
        "_lang_\n"
        "pkg_npm npm\n"
        f"npx skills add {shlex.quote(source)} -a {shlex.quote(agent)}"
        f" -g -y --skill {shlex.quote(slug)}\n"
    )
