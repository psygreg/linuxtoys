#!/usr/bin/env python3
"""LinuxToys MCP server.

Lets AI agents interact with LinuxToys the way a user would: browse and
search the catalog, read app pages (descriptions, screenshots, donation and
purchase links), install and remove apps, clean up the leftover user data of
uninstalled Flatpak apps (the app page's "Remove data" action), run the
app's full system update (the menu card's "Update System"), change settings
(automatic updates, automatic bug reports, language), translate
descriptions, and read or export the Action Registry.

Design:

- Transport: MCP Streamable HTTP on 127.0.0.1 (see DEFAULT_PORT), JSON-RPC
  2.0 responses with a per-client ``Mcp-Session-Id``. Implemented with the
  standard library only — no new runtime dependencies.
- Auth: a per-install random token stored at ``~/.config/linuxtoys/mcp-token``
  (mode 0600). Requests must present it as ``Authorization: Bearer <token>``
  or ``X-LinuxToys-Token: <token>``. This keeps other local users and browser
  origins from driving installs.
- Privilege escalation: scripts run exactly like GUI/CLI runs. When a step
  needs root, the usual ``askpass`` zenity dialog appears on the user's
  screen — credentials are typed by the user and never touch the agent.
  The systemd user unit bakes the graphical session environment
  (DISPLAY/WAYLAND_DISPLAY/…) so those dialogs reach the user's display.
- Isolation: the service never registers the GUI's application identity and
  holds no GUI single-instance state, so the app keeps launching normally
  through every other method while the MCP server is running.

Entry points: ``linuxtoys --mcp`` (also the systemd ExecStart) or
``python3 -m app.mcp_server`` for development.
"""

import base64
import hashlib
import hmac
import json
import os
import queue
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import OrderedDict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

if __package__:
    from . import easy_cli
    from . import installed_packages
    from . import manifest_helper
    from . import appstream_parser
    from . import appstream_cache
    from . import appstream_logs
    from . import appimage_catalog
    from . import antenna
    from . import flatpak_residue
    from . import parser
    from . import registry_utils
    from . import translate_helper
    from .compat import get_linuxtoys_cache_dir, get_system_compat_keys, script_is_compatible
    from .lang_utils import (
        create_translator,
        detect_system_language,
        get_available_languages,
        get_automatic_error_reports,
        get_automatic_updates,
        get_mcp_server_port,
        get_saved_language,
        save_language,
        load_translations,
        save_automatic_error_reports,
        save_automatic_updates,
        get_config_dir,
    )
    from .library_loader import script_command, script_environment
    from .repo_parser import materialize_repo_script
    from .term_registry import ExecutionRegistry
    from .updater import __version__
else:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import easy_cli
    from app import installed_packages
    from app import manifest_helper
    from app import appstream_parser
    from app import appstream_cache
    from app import appstream_logs
    from app import appimage_catalog
    from app import antenna
    from app import flatpak_residue
    from app import parser
    from app import registry_utils
    from app import translate_helper
    from app.compat import get_linuxtoys_cache_dir, get_system_compat_keys, script_is_compatible
    from app.lang_utils import (
        create_translator,
        detect_system_language,
        get_available_languages,
        get_automatic_error_reports,
        get_automatic_updates,
        get_mcp_server_port,
        get_saved_language,
        save_language,
        load_translations,
        save_automatic_error_reports,
        save_automatic_updates,
        get_config_dir,
    )
    from app.library_loader import script_command, script_environment
    from app.repo_parser import materialize_repo_script
    from app.term_registry import ExecutionRegistry
    from app.updater import __version__


SERVER_NAME = "linuxtoys"
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = frozenset({"2025-03-26", "2025-06-18"})
DEFAULT_PORT = 7420
MAX_BODY_BYTES = 1024 * 1024
MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024
SESSION_IDLE_TTL = 24 * 60 * 60
JOB_LOG_LINES = 400

def shlex_quote(value):
    return shlex.quote(str(value))
UNIT_FILE_NAME = "linuxtoys-mcp.service"
TRANSLATED_FALLBACK = "en"

_TRANSIENT_SERVER = {"server": None, "started": 0.0}


def _translations():
    """Cached, auto-detected translations for catalog identity strings."""
    return load_translations()


def _script_dir():
    """Resolve the LinuxToys scripts tree root (sets SCRIPT_DIR like the CLI)."""
    return easy_cli.resolve_script_dir()


def _tmp_dir():
    directory = "/tmp/linuxtoys"
    os.makedirs(directory, mode=0o700, exist_ok=True)
    return directory


# ---------------------------------------------------------------------------
# Auth token
# ---------------------------------------------------------------------------

def token_path():
    return os.path.join(get_config_dir(), "mcp-token")


def ensure_token():
    """Create the access token file on first use and return the token."""
    path = token_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            token = handle.read().strip()
        if token:
            return token
    except OSError:
        pass
    token = secrets.token_urlsafe(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token + "\n")
        os.chmod(path, 0o600)
    except OSError:
        pass
    return token


def token_matches(presented):
    try:
        with open(token_path(), "r", encoding="utf-8") as handle:
            token = handle.read().strip()
    except OSError:
        return False
    if not token or not presented:
        return False
    return hmac.compare_digest(token, presented.strip())


# ---------------------------------------------------------------------------
# Catalog helpers (GTK-free: parser + appstream_parser only)
# ---------------------------------------------------------------------------

def _stable_id(entry):
    value = str(
        entry.get("appstream_id")
        or entry.get("repo_app_id")
        or entry.get("id")
        or entry.get("script")
        or ""
    ).strip()
    if value:
        return value
    path = str(entry.get("virtual_path") or entry.get("path") or "")
    for prefix in ("repo://", "appstream://", "aur://"):
        if path.startswith(prefix):
            return path[len(prefix):]
    return os.path.splitext(os.path.basename(path))[0] if path else ""


def _entry_kind(entry):
    if entry.get("appstream_source") == "appimage":
        return "appimage"
    source = str(entry.get("appstream_source") or "").strip()
    if entry.get("is_appstream_entry"):
        return source or "appstream"
    if entry.get("is_repo_entry"):
        return "repo"
    return "script"


def _version_gate_refusal():
    """Refusal message when the outdated-version gate blocks script runs, else None.

    Mirrors every other runner surface (GUI terminal, TUI, CLI): a LinuxToys
    too far behind the newest published release refuses script runs. The
    check itself is cache-only and fails open, so an unreachable release
    service can never brick installs.
    """
    try:
        from .updater import version_gate
        gate = version_gate.check()
    except Exception:
        return None
    if not gate.get("blocked"):
        return None
    message = version_gate.refusal_message(gate) or (
        "This LinuxToys installation is too far behind the newest release; "
        "script jobs are disabled until it is updated."
    )
    return (
        f"{message} Call get_update_status, let the user approve "
        "update_linuxtoys, and retry once the app is updated. Package "
        "installs (Flathub/Snap, AppImages, AUR, Homebrew, local files) are "
        "not affected."
    )


def _system_update_entry():
    """The app's own full-system-update script (sysup.sh), or raise ValueError.

    The system update is deliberately not an app page: it is the same plain
    script the GUI's "Update System" card and the automatic-update service
    run, excluded from manifests and registry noise by design (see
    manifest_helper._SYSTEM_UPDATE_NAMES). Agents reach it through the
    dedicated update_system tool, which resolves it by its stable filename
    id instead of through search/login surfaces.
    """
    entry = manifest_helper.find_script_by_id("sysup", _translations())
    if entry is None:
        raise ValueError(
            "The system-update script (sysup) is not available in this "
            "LinuxToys installation's catalog."
        )
    if not str(entry.get("path") or "").strip():
        raise ValueError(
            "The system-update script (sysup) has no runnable path in this "
            "installation."
        )
    return entry


# ---------------------------------------------------------------------------
# Agent script-dialog machinery
#
# Scripts raise dialogs through four helper families in libs/linuxtoys.bash:
# question/zenask, radioselect, listselect and warn/zenwrn/nonfatal/die/fatal.
# Agent behavior:
#
# - Questions: statically extracted from the script text and returned by
#   install_app/update_system BEFORE any run (requires_answers payload).
#   The agent asks the user (options + default are provided), then re-calls
#   the tool with `answers`; the run carries a prepared-answers file that
#   the helpers consult instead of showing a dialog. Calls the service
#   cannot pre-ask (variable args, continuations, exotic escapes) are
#   counted as dynamic prompts: they keep their live dialog behavior and
#   are logged as events so the agent learns they were shown to the user.
# - Warnings (warn/zenwrn/nonfatal) and fatal dialogs (die/fatal): the
#   helpers append structured events to a per-job file that get_job parses
#   live. No dialog blocks an agent run; informational popups are omitted
#   and their text lands in the job log.
#
# Env contract set by _execute_script (never by the GUI/CLI):
#   LT_AGENT_MODE=1        agent-managed run
#   LT_AGENT_EVENTS=...    "kind\ttext" event lines
#   LT_AGENT_ANSWERS=...   "key\tanswer" line file; key = prompt kind plus
#                          the prompt fields joined by \x1f after
#                          \t/\r/\n/\x1f-name normalization — byte parity
#                          with the bash-side lookup (_lt_agent_lookup).
# ---------------------------------------------------------------------------

_UNIT_SEP = "\x1f"
_QUESTION_ID_LEN = 12

_DIALOG_HELPER_RE = re.compile(
    r"(?:^|[^A-Za-z0-9_-])(zenask|question|radioselect|listselect)(?![A-Za-z0-9_-])"
)
_DQ_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
_NAV_FORM_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$|^\$([A-Za-z_][A-Za-z0-9_]*)$")
_LANG_ASSIGN_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$')


def _clean_field(value):
    """One-line, separator-free field value (bash _lt_agent_clean parity)."""
    return re.sub(r"[\t\r\n\x1f]", " ", str(value))


def _agent_key(kind, fields):
    parts = [_clean_field(kind)]
    parts.extend(_clean_field(field) for field in fields)
    return _UNIT_SEP.join(parts)


def _agent_question_id(kind, fields):
    digest = hashlib.sha256(_agent_key(kind, fields).encode("utf-8")).hexdigest()
    return digest[:_QUESTION_ID_LEN]


def _printf_unescape(text):
    """bash printf %b equivalent; None marks a call the service will not
    pre-ask (non-representable escapes), so the dialog keeps its live
    pass-up behavior instead of a wrongly-mapped key."""
    out = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char != "\\":
            out.append(char)
            index += 1
            continue
        if index + 1 >= length:
            return None  # trailing backslash: unpredictable at runtime
        escape = text[index + 1]
        simple = {"a": "\a", "b": "\b", "f": "\f", "n": "\n",
                  "r": "\r", "t": "\t", "v": "\v", "\\": "\\"}
        if escape in simple:
            out.append(simple[escape])
            index += 2
            continue
        if escape == "c":  # %b output terminator: not fixed text
            return None
        if escape == "x":
            digits = ""
            probe = index + 2
            while probe < length and len(digits) < 2 and text[probe] in "0123456789abcdefABCDEF":
                digits += text[probe]
                probe += 1
            if not digits:
                return None
            out.append(chr(int(digits, 16) & 0xFF))
            index = probe
            continue
        if escape == "0":
            digits = ""
            probe = index + 2
            while probe < length and len(digits) < 3 and text[probe] in "01234567":
                digits += text[probe]
                probe += 1
            if not digits:
                return None
            out.append(chr(int(digits, 8) & 0xFF))
            index = probe
            continue
        return None
    return "".join(out)


_BASH_DQ_SPECIAL = {'"': '"', "\\": "\\", "$": "$", "`": "`"}


def _decode_double_quoted(raw):
    """Decode ONE double-quoted literal's content the way bash does.

    Returns (decoded, dynamic): dynamic=True when the literal references a
    shell variable or command substitution instead of fixed text (the
    caller may still try whole-content `$var` resolution).
    """
    out = []
    index = 0
    while index < len(raw):
        char = raw[index]
        if char != "\\":
            if char == "$" or char == "`":
                return "", True
            out.append(char)
            index += 1
            continue
        if index + 1 >= len(raw):
            break  # dangling backslash: runtime sees a bare backslash here
        nxt = raw[index + 1]
        if nxt == "\n":
            index += 2  # quoted continuation: spliced out by bash
            continue
        if nxt in _BASH_DQ_SPECIAL:
            out.append(_BASH_DQ_SPECIAL[nxt])
            index += 2
            continue
        # Escapes that survive into the runtime value untouched (the runtime
        # expands them through printf %b for the question text only).
        out.append(char)
        out.append(nxt)
        index += 2
    return "".join(out), False


def _lang_assignment_value(raw):
    """libs/lang/<code>.lib value ("..." or '...') decoded; None if unusable.

    Double-quoted content referencing another var (finishmsg="$msg018") is
    kept verbatim so _resolve_lang_ref expands it recursively like bash
    does when the script sources the lib.
    """
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        text, dynamic = _decode_double_quoted(raw[1:-1])
        return raw[1:-1] if dynamic else text
    return raw


_LANG_TABLE_CACHE = {"lang": None, "table": {}}


def _lang_table():
    """Script translation variables ($msg2xx style) for $var resolution."""
    lang = str(os.environ.get("LANG") or "").strip()[:2].casefold() or "en"
    if _LANG_TABLE_CACHE["lang"] == lang:
        return _LANG_TABLE_CACHE["table"]
    table = {}
    try:
        directory = os.path.join(_script_dir(), "libs", "lang")
        path = os.path.join(directory, f"{lang}.lib")
        if not os.path.isfile(path):
            path = os.path.join(directory, "en.lib")
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                match = _LANG_ASSIGN_RE.match(line)
                if not match:
                    continue
                value = _lang_assignment_value(match.group(2))
                if value is not None:
                    table[match.group(1)] = value
    except Exception:
        table = {}
    _LANG_TABLE_CACHE["lang"] = lang
    _LANG_TABLE_CACHE["table"] = table
    return table


def _resolve_lang_ref(var_name, table, depth=4):
    """Resolved translation var (file entries may reference other entries);
    None when the name is not a resolvable lib value."""
    if depth < 0:
        return None
    raw = table.get(var_name)
    if raw is None:
        return None
    out = []
    index = 0
    while index < len(raw):
        char = raw[index]
        if char != "$":
            out.append(char)
            index += 1
            continue
        match = _DQ_VAR_RE.match(raw[index:])
        if not match:
            out.append(char)
            index += 1
            continue
        name = match.group(1) or match.group(2)
        nested = _resolve_lang_ref(name, table, depth - 1)
        if nested is None:
            return None
        out.append(nested)
        index += len(match.group(0))
    return "".join(out)


def _agent_prompt_entry(kind, fields, title="", message=""):
    if kind == "question":
        options = ["Yes", "No"]
        default = "Yes"
    elif kind == "radio":
        options = fields
        default = options[0] if options else ""
    else:
        options = fields
        default = ""
    return {
        "id": _agent_question_id(kind, fields),
        "kind": kind,
        "title": title,
        "message": message,
        "options": list(options),
        "default": default,
    }


def _agent_scan_line(line, resolver):
    """All statically extractable helper calls on one physical line.

    `resolver(name)` decides variable arguments: the composed script-local
    + lang table, or None when the value is runtime-only. Anything the
    resolver cannot pin falls back to the runtime dialog (dynamic).
    """
    entries = []
    dynamic = 0
    cursor = 0
    while True:
        match = _DIALOG_HELPER_RE.search(line, cursor)
        if match is None:
            break
        cursor = match.end()
        helper = match.group(1)
        kind = (
            "question" if helper in ("question", "zenask")
            else "radio" if helper == "radioselect"
            else "list"
        )
        fields = []
        dynamic_call = False
        parse_end = match.end()
        index = cursor
        while index < len(line):
            while index < len(line) and line[index] in " \t":
                index += 1
            if index >= len(line):
                break
            char = line[index]
            if char == "\\" and index == len(line) - 1:
                dynamic_call = True  # continuation: the call has more args
                break
            if char == '"':
                closing = index + 1
                while closing < len(line):
                    if line[closing] == "\\":  # keep escapes: decode handles them
                        closing += 2
                        continue
                    if line[closing] == '"':
                        break
                    closing += 1
                if closing >= len(line):
                    dynamic_call = True  # unterminated literal
                    break
                raw_content = line[index + 1:closing]
                decoded, dynamic_res = _decode_double_quoted(raw_content)
                if dynamic_res:
                    # Whole-content `$var` (the dominant translated form,
                    # `question "T" "$msg2xx"`) still resolves.
                    var_match = _NAV_FORM_RE.match(raw_content.strip())
                    resolved = None
                    if var_match:
                        name = var_match.group(1) or var_match.group(2)
                        resolved = resolver(name)
                    if resolved is None:
                        dynamic_call = True
                        break
                    fields.append(resolved)
                else:
                    fields.append(decoded)
                index = closing + 1
                parse_end = index
                continue
            if char == "'":
                closing = line.find("'", index + 1)
                if closing < 0:
                    dynamic_call = True
                    break
                fields.append(line[index + 1:closing])
                index = closing + 1
                parse_end = index
                continue
            var_match = _NAV_FORM_RE.match(line[index:])
            if var_match:
                name = var_match.group(1) or var_match.group(2)
                resolved = resolver(name)
                if resolved is None:
                    dynamic_call = True  # script-local or extended expansion
                    break
                fields.append(resolved)
                index += len(var_match.group(0))
                parse_end = index
                continue
            if char == "#":
                break  # trailing comment: the call's arguments end here
            break  # redirect / pipe / other token: arguments complete

        if dynamic_call:
            dynamic += 1
        elif fields:
            if kind == "question":
                title = fields[0] if fields else ""
                raw_text = fields[1] if len(fields) > 1 else ""
                message = _printf_unescape(raw_text)
                if message is None:
                    dynamic += 1
                    continue
                # The runtime lookup passes the RAW title and the UNescaped
                # text (question() unescapes $2 before consulting answers).
                entries.append(_agent_prompt_entry(
                    "question", [title, message], title=title, message=message,
                ))
            else:
                if len(set(fields)) != len(fields):
                    dynamic += 1  # duplicated options: ambiguous answer key
                    continue
                entries.append(_agent_prompt_entry(kind, fields))
    return entries, dynamic


def _script_agent_questions(path):
    """Static question extraction for one plain script (agent pre-asking).

    Branch-aware: each helper call site is analyzed with the conditions it
    is nested inside, and those conditions are evaluated against THIS host
    before the question is offered:

    - conditions composed purely of read-only host probes (the is_* libs
      predicates, [ ]/[[ ]]/test facts, command -v / grep / package-query
      reads) run for real in a sandboxed bash that sources the same libs
      tree the job will use;
    - conditions carrying runtime values (variables set by previous steps
      in the same script, call_script exports) are presumed to have
      succeeded: they contribute success to the chain, so branches a
      previous step gates into are pre-asked. Should that step fail at
      runtime the usual machinery reports the error to the user, and the
      prepared answer is simply not consulted; on success the run consumes
      it and proceeds as expected, both covered by the fallback answer
      file lookup semantics verified by the integration tests.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return [], 0, 0
    return _agent_script_scan(text)


def _agent_logical_lines(text):
    """Join backslash continuations into logical lines.

    Yields ``(first_physical_line, logical_text)``. Heredoc bodies pass
    through untouched (inert): their content neither opens frames nor
    carries helper calls.
    """
    pending = []
    heredoc = None
    start = 0
    for number, raw in enumerate(text.split("\n"), 1):
        stripped = raw.strip()
        if heredoc is not None:
            if stripped == heredoc:
                heredoc = None
            continue
        marker = re.match(r".*<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?\s*$", raw)
        if marker:
            heredoc = marker.group(1)
            continue
        if not pending:
            start = number
        if raw.endswith("\\"):
            pending.append(raw[:-1])
            continue
        if pending:
            pending.append(raw)
            yield (start, " ".join(part.strip() for part in pending))
            pending = []
        else:
            yield (number, raw)
    if pending:
        yield (start, " ".join(part.strip() for part in pending))


def _agent_strip_comment(line):
    """Drop an unquoted trailing comment; None marks a comment-only line."""
    index = 0
    quote = None
    while index < len(line):
        char = line[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char == "#" and (index == 0 or line[index - 1] in " \t"):
            return line[:index].rstrip() or None
        index += 1
    return line


_AGENT_FUNCDEF_RE = re.compile(
    r"^(?:function\s+)?([A-Za-z_][A-Za-z0-9_-]*)\s*\(\s*\)\s*\{.*$"
)
_AGENT_STRUCT_KW = {
    "if", "then", "elif", "else", "fi", "while", "until", "do", "done",
    "case", "esac", "in", "for",
}
# Frames that a same/matching brace-close `}` pops (func bodies close via
# their own `}` line too, but the brace-gate groups pop as gates).
_AGENT_BRACE_POP_KINDS = ("gate", "block", "func", "case")

# Read-only host predicates and commands observed in the corpus, verified
# against libs/linuxtoys.bash + libs/sysinfo.bash (is_* helpers are pure
# system detection) and libs/packages.bash (dpkg/rpm/pacman/dnf/flatpak/
# snap query reads only; nothing here mutates).
_AGENT_PROBE_FUNCTIONS = frozenset({
    "is_arch", "is_cachy", "is_manjaro", "is_debian", "is_ubuntu", "is_fedora",
    "is_rhel", "is_ostree", "is_ublue", "is_gregos", "is_suse", "is_solus",
    "is_zorin", "is_deepin", "is_steamos", "is_restricted_host", "is_systemd",
    "is_nvidia", "is_intel", "is_amd", "is_icr_capable", "is_rocm_capable",
    "is_rusticl_capable", "is_hybridgpu",
})
_AGENT_PROBE_QUERY_WORDS = frozenset({
    "dpkg", "rpm", "pacman", "dnf", "flatpak", "snap",
})
_AGENT_PROBE_READONLY_FLAGS = {
    "dpkg": {"-s", "-l", "-L"},
    "rpm": {"-q", "-qi", "-qs", "-qa"},
    "pacman": {"-Q", "-Qs", "-Qi", "-Ql"},
    "dnf": {"list"},
    "flatpak": {"list", "info"},
    "snap": {"list"},
}
_AGENT_PRESUME_CALL = "_lt_agent_presume"
_AGENT_WORD_RE = re.compile(r"\s+")
_AGENT_CONDITION_CACHE = {}
_AGENT_PROBE_TTL_SECONDS = 30


def _agent_split_top(text):
    """Top-level alternation units of one condition (bash-ish, forgiving)."""
    result = []
    index = 0
    length = len(text)
    while index < length:
        if text.startswith("&&", index):
            result.append("&&")
            index += 2
            continue
        if text.startswith("||", index):
            result.append("||")
            index += 2
            continue
        if text[index] == ";":
            result.append(";")
            index += 1
            continue
        if text[index] in " \t":
            index += 1
            continue
        if text[index] in "(){}":
            result.append(text[index])
            index += 1
            continue
        start = index
        quote = None
        while index < length:
            char = text[index]
            if quote:
                if char == "\\":
                    index += 2
                    continue
                if char == quote:
                    quote = None
                index += 1
                continue
            if char in ('"', "'"):
                quote = char
                index += 1
                continue
            if char == ";":
                break
            if text.startswith("&&", index) or text.startswith("||", index):
                break
            if char in "(){}":
                break
            index += 1
        token = text[start:index].strip()
        if token:
            result.append(token)
    return result


def _agent_condition_compile_atom(atom):
    """One command/test atom: keep safe probes, else presume success."""
    if atom in ("!", "&&", "||", ";", "{", "}", "(", ")"):
        return atom
    body = atom[1:].strip() if atom.startswith("!") else atom
    if re.search(r"[$`\n]", body):
        return ("! " + _AGENT_PRESUME_CALL) if atom.startswith("!") else _AGENT_PRESUME_CALL
    words = _AGENT_WORD_RE.split(body)
    first = words[0] if words else ""
    if not first:
        return _AGENT_PRESUME_CALL
    if first in _AGENT_PROBE_FUNCTIONS:
        return atom
    if first in ("[", "[[", "test"):
        return atom
    if first in ("command", "grep", "findmnt", "stat", "pgrep", "true", "false"):
        return atom
    # package-manager word probes are host probes only when every flag the
    # atom carries is a read-only one (`rpm -ivh` would not be).
    if first in _AGENT_PROBE_QUERY_WORDS:
        for flag in words[1:]:
            if flag.startswith("-") and flag not in _AGENT_PROBE_READONLY_FLAGS.get(first, set()):
                return _AGENT_PRESUME_CALL
        return atom
    return _AGENT_PRESUME_CALL


def _agent_condition_compile(cond):
    """Rebuild one branch condition for host evaluation.

    Probe-shaped atoms stay verbatim; anything the service cannot classify
    (runtime variables, arbitrary commands, mutations) is substituted with
    a presume-success call, so the branch's host-detectable parts still
    cut it (a false is_fedora excludes the branch for real), while
    previous-step-dictated parts follow the presume-success rule.
    """
    parts = []
    for unit in _agent_split_top(cond):
        if unit in ("&&", "||", "(", ")", "{", "}"):
            parts.append(unit)
            continue
        parts.append(_agent_condition_compile_atom(unit))
    rebuilt = " ".join(part for part in parts if part)
    return rebuilt or None


def _agent_compile_arms(scope_dir, conditions):
    """Evaluate the rebuilt chain conditions in one sandboxed bash.

    Returns a "1"-side bitmap in order. Any failure degrades to taken for
    every condition — never lose a question to an evaluator hiccup.
    """
    if not conditions:
        return []
    key = (scope_dir, tuple(conditions))
    now = time.time()
    cached = _AGENT_CONDITION_CACHE.get(key)
    # Probes read live host state (command -v, file existence): a change
    # between two agent calls must not be served from a stale result, so
    # entries live for a short TTL only.
    if cached is not None and now - cached[1] < _AGENT_PROBE_TTL_SECONDS:
        return list(cached[0])
    script = [
        f"SCRIPT_DIR={shlex_quote(scope_dir)}",
        "FS_OPS= PACKAGE_OPS= BOOT_OPS= MISC_OPS= SYSD_OPS= HELPERS_OPS= OPTIMIZER_OPS=",
        "DISPLAY=; WAYLAND_DISPLAY=",
        "export DISPLAY= WAYLAND_DISPLAY=",
        f"source {shlex_quote(os.path.join(scope_dir, 'libs', 'linuxtoys.bash'))}",
        f"{_AGENT_PRESUME_CALL}() {{ return 0; }}",
        "__flags__=",
    ]
    for condition in conditions:
        script.append(f"__arm() {{ {condition}; }}")
        script.append(
            'if __arm; then __flags__="${__flags__}1"; else __flags__="${__flags__}0"; fi'
        )
    script.append('echo "__flags__=${__flags__}"')
    try:
        proc = subprocess.run(
            ["bash", "-c", "\n".join(script)],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=15,
            env={**os.environ, "DISPLAY": "", "WAYLAND_DISPLAY": "", "LANG": "C"},
            check=False,
        )
        matched = re.search(r"__flags__=([01]+)", proc.stdout or "")
        flags = list(matched.group(1)) if matched else ["1"] * len(conditions)
    except (OSError, subprocess.SubprocessError):
        flags = ["1"] * len(conditions)
    flags = flags[: len(conditions)]
    flags.extend("1" for _ in range(len(conditions) - len(flags)))
    _AGENT_CONDITION_CACHE[key] = (flags, time.time())
    return flags


_AGENT_ASSIGN_RE = re.compile(r"^\s*(?:export\s+|local\s+)?([A-Za-z_][A-Za-z0-9_]*)=(\"[^\"]*\"|'[^']*')\s*$")


def _agent_script_var_table(text):
    """Static constant assignments inside one script (name="literal"), with
    runtime-result assignments deliberately excluded.

    A script-local var may reference a lang var (rmmsg="$msg288"); the
    resolver then expands it through _resolve_lang_ref composed on the
    script table, so args like `zenask "OpenCode" "$rmmsg"` — where the
    script renamed the message — resolve exactly like they do at runtime.
    """
    table = {}
    for line in text.split("\n"):
        original = _agent_strip_comment(line)
        if not original:
            continue
        match = _AGENT_ASSIGN_RE.match(original)
        if not match:
            continue
        value = _lang_assignment_value(match.group(2))
        if value is not None:
            table[match.group(1)] = value
    return table


def _agent_script_scan(text):
    """Structural scan of one script with per-site branch evaluation.

    Returns ``(questions, dynamic, skipped)``. Function-body sites resolve
    through their callers one hop (direct or call_script driven conditions
    are all caller-context frames; presume success applies to step atoms).
    """
    lang_table = _lang_table()
    scope_dir = _script_dir()
    script_vars = _agent_script_var_table(text)
    merged_vars = dict(lang_table)
    merged_vars.update(script_vars)

    def resolver(name):
        return _resolve_lang_ref(name, merged_vars)

    groups = {}   # gid -> list of arm dicts {"kind", "cond"}
    stack = []    # active frames: {"kind", "group", "arm", "name"}
    sites = []    # {"entries", "frames"}
    callers = []  # {"name", "frames"}
    defined = set()
    line_contexts = []  # (stripped_line, pre_snapshot) per logical line
    dynamic = 0

    def take_snapshot():
        return [dict(record) for record in stack]

    # ---- pass one: structure walk, site capture, caller records ------------
    for _line_no, logical in _agent_logical_lines(text):
        line = _agent_strip_comment(logical)
        if not line:
            continue
        stripped = line.strip()
        # Mid-line brace gates (`cond && { more...`, sysup's release-upgrade
        # chain) open one "gate" frame each, and the remainder continues as
        # the line's own body; a same-line `}` balance pops the gate right
        # away. Lines that open a branch natively (if/elif/while/until —
        # their arm compiler already carries the presume-success semantics)
        # never split this way.
        first_word_probe = stripped.split(None, 1)[0] if stripped.split() else ""
        net_braces = 0
        gate_search = None
        if first_word_probe not in _AGENT_STRUCT_KW:
            gate_search = re.search(r"\s*(&&|\|\|)\s*\{\s*", stripped)
        while gate_search:
            prefix = stripped[: gate_search.start()].strip()
            operator = gate_search.group(1)
            stripped = stripped[gate_search.end():]
            if net_braces < 0:
                net_braces = 0
            net_braces += stripped.count("{") - stripped.count("}")
            if prefix:
                compiled_gate = _agent_condition_compile(prefix)
                if compiled_gate is None:
                    compiled_gate = prefix
                if operator == "||":
                    compiled_gate = f"! ( {compiled_gate} )"
                gid = f"g{len(groups)}"
                groups[gid] = [{"kind": "if", "cond": compiled_gate}]
                stack.append({"kind": "gate", "group": gid, "arm": 0, "name": None})
            # Same-line brace balance: each extra `}` closing one group pops
            # the innermost brace-owned frame right away.
            while net_braces < 0:
                for index in range(len(stack) - 1, -1, -1):
                    if stack[index]["kind"] in _AGENT_BRACE_POP_KINDS:
                        del stack[index:]
                        net_braces += 1
                        break
            gate_search = re.search(r"\s*(&&|\|\|)\s*\{\s*", stripped)
        while net_braces < 0:
            for index in range(len(stack) - 1, -1, -1):
                if stack[index]["kind"] in _AGENT_BRACE_POP_KINDS:
                    del stack[index:]
                    net_braces += 1
                    break
        pre_snapshot = take_snapshot()
        line_contexts.append((stripped, pre_snapshot))
        entries, line_dynamic = _agent_scan_line(line, resolver)
        if line_dynamic:
            dynamic += line_dynamic
        if entries:
            sites.append({"entries": entries, "frames": take_snapshot()})
        first_word = stripped.split(None, 1)[0] if stripped.split() else ""

        # openings
        if first_word in ("if", "while", "until"):
            body = stripped.split(None, 1)[1] if len(stripped.split(None, 1)) > 1 else ""
            cond = re.sub(r";\s*(?:then|do)\s*$", "", body).strip()
            gid = f"g{len(groups)}"
            groups[gid] = [{"kind": "if", "cond": cond}]
            stack.append({"kind": "branch", "group": gid, "arm": 0, "name": None})
            continue
        if first_word == "for":
            stack.append({"kind": "for", "group": None, "arm": None, "name": None})
            continue
        if first_word == "case":
            stack.append({"kind": "case", "group": None, "arm": None, "name": None})
            continue
        func_match = _AGENT_FUNCDEF_RE.match(stripped)
        if func_match:
            defined.add(func_match.group(1))
            stack.append({
                "kind": "func",
                "group": None,
                "arm": None,
                "name": func_match.group(1),
            })
            continue
        # arm mutation
        if first_word == "else":
            if stack and stack[-1]["kind"] == "branch":
                gid = stack[-1]["group"]
                groups[gid].append({"kind": "else", "cond": ""})
                stack[-1]["arm"] = len(groups[gid]) - 1
            continue
        if first_word == "elif":
            if stack and stack[-1]["kind"] == "branch":
                gid = stack[-1]["group"]
                cond = re.sub(r";\s*then\s*$", "", stripped.split(None, 1)[1].strip()).strip()
                groups[gid].append({"kind": "elif", "cond": cond})
                stack[-1]["arm"] = len(groups[gid]) - 1
            continue
        # closers
        if first_word == "fi":
            for index in range(len(stack) - 1, -1, -1):
                if stack[index]["kind"] in ("branch", "loop"):
                    del stack[index:]
                    break
            continue
        if first_word == "esac":
            for index in range(len(stack) - 1, -1, -1):
                if stack[index]["kind"] == "case":
                    del stack[index:]
                    break
            continue
        if first_word == "done":
            for index in range(len(stack) - 1, -1, -1):
                if stack[index]["kind"] in ("branch", "loop", "case", "for"):
                    del stack[index:]
                    break
            continue
        if stripped == "}":
            for index in range(len(stack) - 1, -1, -1):
                if stack[index]["kind"] in _AGENT_BRACE_POP_KINDS:
                    del stack[index:]
                    break
            continue
        if first_word in _AGENT_STRUCT_KW:
            continue
        # plain command line: keep a caller record for function resolution
        if re.fullmatch(r"[a-zA-Z_][A-Za-z0-9_-]*", first_word):
            callers.append({"name": first_word, "frames": take_snapshot()})

    # ---- pass 1b: mid-line function calls (chains like `cond && func`) ----
    for stripped, pre_snapshot in line_contexts:
        for name in defined | set(record["name"] for record in callers):
            if not re.search(r"(?:^|[^A-Za-z0-9_-])" + re.escape(name) + r"(?:[^A-Za-z0-9_-]|$)", stripped):
                continue
            if stripped.startswith(name + "()") or stripped.startswith("function " + name):
                continue  # the definition itself, not a call
            first_word = stripped.split(None, 1)[0] if stripped.split() else ""
            caller_cond = None
            if first_word in ("if", "elif", "while", "until"):
                body = stripped.split(None, 1)[1] if len(stripped.split(None, 1)) > 1 else ""
                caller_cond = re.sub(r";\s*(?:then|do)\s*$", "", body).strip()
            elif re.search(r"&&\s*\{\s*$", stripped) or re.search(r"\|\|\s*\{\s*$", stripped):
                prefix = re.split(r"&&\s*\{\s*$|\|\|\s*\{\s*$", stripped)[0].strip()
                negated = bool(re.search(r"\|\|\s*\{\s*$", stripped))
                compiled = _agent_condition_compile(prefix)
                if compiled is not None:
                    caller_cond = f"! ( {compiled} )" if negated else compiled
            caller_frames = [dict(item) for item in pre_snapshot]
            if caller_cond and name in caller_cond:
                # The call lives inside this line's own condition: keep the
                # other atoms as a gate frame, with the call atom itself
                # replaced by the presume-success call.
                pseudo = caller_cond.replace(name, _AGENT_PRESUME_CALL)
                gid = f"g{len(groups)}"
                groups[gid] = [{"kind": "if", "cond": pseudo}]
                caller_frames.append({"kind": "branch", "group": gid, "arm": 0})
            callers.append({"name": name, "frames": caller_frames})

    # ---- pass two: evaluate every arm ONCE, then apply chain rules ---------
    compiled_conditions = []
    position_of = {}  # (gid, arm_idx) -> index in compiled_conditions
    for gid, arms in groups.items():
        for arm_idx, arm in enumerate(arms):
            original = arm.get("cond") or ""
            compiled = _agent_condition_compile(arm["cond"]) if arm.get("cond") else None
            arm["compiled"] = compiled
            # An arm whose condition carries runtime values (previous-step
            # results, call_script exports) is presumed to succeed: its
            # truth is soft and must never disqualify sibling arms.
            arm["presumed"] = bool(re.search(r"[$`@\n]", original)) or (
                compiled is not None and _AGENT_PRESUME_CALL in compiled
            )
            if compiled is not None:
                position_of[(gid, arm_idx)] = len(compiled_conditions)
                compiled_conditions.append(compiled)
    values = _agent_compile_arms(scope_dir, compiled_conditions)

    def arm_ok(gid, arm_idx):
        key = (gid, arm_idx)
        if key not in position_of:
            return True  # absent condition: nothing to falsify
        return values[position_of[key]] == "1"

    def sibling_probe_true(gid, arm_idx):
        """An earlier arm whose condition resolved purely from host probes
        (no presumed atoms) is a hard truth: the run definitely took it.
        An arm containing presumed (previous-step) atoms is soft — its
        value might not have happened, so later arms stay reachable."""
        key = (gid, arm_idx)
        if key not in position_of:
            return False
        arm = (groups.get(gid) or [{}])[arm_idx]
        compiled = arm.get("compiled")
        if compiled is None or _AGENT_PRESUME_CALL in compiled:
            return False
        return values[position_of[key]] == "1"

    def chain_taken(frames):
        """One caller chain is taken when nothing enclosing is probe-false.
        Presumed (previous-step) atoms contribute success inside each arm's
        evaluated value, so only real probes can falsify; an earlier arm
        whose evaluated value is 1 wins the group and later arms (failure
        paths) are unreachable per the presume-success rule."""
        for record in frames:
            if record["kind"] in ("branch", "gate"):
                gid = record["group"]
                arm_idx = record["arm"] or 0
                arm = (groups.get(gid) or [{}])[arm_idx]
                for pos in range(arm_idx):
                    if sibling_probe_true(gid, pos):
                        return False
                if not arm_ok(gid, arm_idx):
                    return False
        return True

    questions = []
    skipped = 0
    seen_ids = set()
    for site in sites:
        taken = True
        for record in site['frames']:
            if record["kind"] == "func":
                name = record["name"]
                caller_hits = [caller for caller in callers if caller["name"] == name]
                if not caller_hits:
                    continue  # the function is never invoked: presume reachable
                any_caller_ok = any(chain_taken(caller["frames"]) for caller in caller_hits)
                if not any_caller_ok:
                    taken = False
                    break
                continue
            if record["kind"] in ("case", "for", "block"):
                continue
            if record["kind"] in ("branch", "loop", "gate"):
                gid = record["group"]
                arm_idx = record["arm"] or 0
                arm = (groups.get(gid) or [{}])[arm_idx]
                for pos in range(arm_idx):
                    if sibling_probe_true(gid, pos):
                        taken = False
                        break
                if taken and not arm_ok(gid, arm_idx):
                    taken = False
                if not taken:
                    break
        if not taken:
            skipped += 1
            continue
        for entry in site["entries"]:
            if entry["id"] in seen_ids:
                continue
            seen_ids.add(entry["id"])
            questions.append(entry)
    return questions, dynamic, skipped


_AGENT_REPO_HOOK_LINE_RE = re.compile(r"^run_list_hook\s+(.+?)\s*$", re.MULTILINE)


def _agent_list_hook_path(hook, scope_dir):
    """Resolve one repository hook path exactly like the runtime helper:
    `$CACHE_DIR/lists/<hook>` first, then `$SCRIPT_DIR/scripts/lists/<hook>`.

    Returns the concrete script file path when one of those locations holds
    it, else None — the runtime reports a missing hook, so the scan just
    skips it instead of inventing a fallback.
    """
    token = str(hook or "").strip()
    if not token:
        return None
    if os.path.isabs(token):
        return token if os.path.isfile(token) else None
    cache_dir = str(os.environ.get("CACHE_DIR") or "").strip()
    for prefix in (
        os.path.join(cache_dir, "lists") if cache_dir else None,
        os.path.join(scope_dir, "scripts", "lists"),
    ):
        if not prefix:
            continue
        path = os.path.join(prefix, token)
        if os.path.isfile(path):
            return path
    return None


def _agent_hook_candidates(overrides, phase, scope_dir):
    """Scan candidates for one pre/post hook phase.

    Runtime parity with the looked-up shapes: an inline shell string and a
    `{"script": <lists-relative path>}` mapping (which the runtime sources
    via run_list_hook) both reach the scan.
    """
    results = []
    if not isinstance(overrides, dict):
        return results
    value = overrides.get(phase)
    if isinstance(value, str) and value.strip():
        results.append({"kind": "text", "text": value.strip()})
    elif isinstance(value, dict):
        script = str(value.get("script", "") or "").strip()
        path = _agent_list_hook_path(script, scope_dir)
        if path:
            results.append({"kind": "path", "path": path})
    return results


def _agent_read_pipeline(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _agent_repo_pipeline_text(entry):
    """The composed install script of one repository-list entry (the same
    text `materialize_repo_script` hands to the job)."""
    try:
        from . import repo_parser
        path = repo_parser.create_install_script(entry)
    except Exception:
        return None
    return _agent_read_pipeline(path)


def _agent_appstream_pipeline_text(entry):
    """The composed install pipeline of one AppStream entry (pre hooks,
    dependencies, install body, Flatpak overrides, post hooks)."""
    try:
        from .tui.appstream_executor import build_install_script
        path = build_install_script(entry)
    except Exception:
        return None
    return _agent_read_pipeline(path)


def _agent_dialog_candidates(entry):
    """Where helper-family dialogs can live for one catalog entry.

    - Curated physical scripts: the entry's own file (existing behavior).
    - Repository-list entries (`is_repo_entry`): the materialized install
      pipeline plus every pre/post hook script it sources.
    - AppStream entries and overlays: the composed AppStream pipeline plus
      the overlay's hook scripts (`appstream_overrides`).
    """
    results = []
    if not (entry.get("is_appstream_entry") or entry.get("is_repo_entry")):
        script_path = str(entry.get("path") or "").strip()
        if script_path and os.path.isfile(script_path):
            results.append({"kind": "text", "text": _read_file_text(script_path)})
        return results
    scope_dir = _script_dir()
    if entry.get("is_repo_entry"):
        pipeline = _agent_repo_pipeline_text(entry)
        if pipeline:
            results.append({"kind": "text", "text": pipeline})
        overrides = entry.get("overrides") or {}
    else:
        pipeline = _agent_appstream_pipeline_text(entry)
        if pipeline:
            results.append({"kind": "text", "text": pipeline})
        overrides = entry.get("appstream_overrides") or {}
    for phase in ("pre", "post"):
        results.extend(_agent_hook_candidates(overrides, phase, scope_dir))
    return results


def _read_file_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _agent_dialog_scan_requests(entry):
    """The branch-aware dialog scan aggregated over one catalog entry's
    candidate scripts; returns ``(questions, dynamic, skipped)`` with
    question ids deduplicated across candidates."""
    questions = []
    dynamic = 0
    skipped = 0
    seen_ids = set()
    for candidate in _agent_dialog_candidates(entry):
        try:
            if candidate["kind"] == "path":
                text = _read_file_text(candidate["path"])
            else:
                text = candidate.get("text") or ""
            entries, line_dynamic, line_skipped = _agent_script_scan(text)
        except Exception:
            continue
        dynamic += line_dynamic
        skipped += line_skipped
        for question in entries:
            if question["id"] in seen_ids:
                continue
            seen_ids.add(question["id"])
            questions.append(question)
    if not questions and not dynamic:
        return [], 0, 0
    return questions, dynamic, skipped


def _agent_records(questions, answers):
    """Validate agent `answers` against extracted questions and build the
    per-job answer file records; ValueError says exactly what is wrong.
    """
    by_id = {entry["id"]: entry for entry in questions}
    answers = dict(answers if isinstance(answers, dict) else {})
    problems = []
    missing = [entry["id"] for entry in questions if entry["id"] not in answers]
    if missing:
        problems.append(
            "answers must cover every question id returned earlier; missing: "
            + ", ".join(missing)
        )
    records = []
    for question_id, value in answers.items():
        entry = by_id.get(str(question_id))
        if entry is None:
            problems.append(f"unknown question id '{question_id}'")
            continue
        kind = entry["kind"]
        if kind == "question":
            if isinstance(value, list):
                value = value[0] if value else ""
            folded = str(value).strip().casefold()
            if folded in ("yes", "y", "true", "1", "on"):
                records.append({
                    "kind": "question",
                    "fields": [entry["title"], entry["message"]],
                    "value": "yes",
                })
            elif folded in ("no", "n", "false", "0", "off"):
                records.append({
                    "kind": "question",
                    "fields": [entry["title"], entry["message"]],
                    "value": "no",
                })
            else:
                problems.append(
                    f"question '{question_id}' expects 'yes' or 'no', got {value!r}"
                )
            continue
        if kind == "radio":
            if isinstance(value, list):
                text = str(value[0]) if len(value) == 1 else None
            else:
                text = str(value)
            if text is None or text not in entry["options"]:
                problems.append(
                    f"radio question '{question_id}' expects exactly one of "
                    "the listed options, got "
                    + ("a list with multiple items" if isinstance(value, list) else repr(value))
                )
                continue
            records.append({
                "kind": "radio",
                "fields": entry["options"],
                "value": _clean_field(text),
            })
            continue
        # list: one string (comma/newline separated) or an array of strings
        if isinstance(value, list):
            selections = [str(item) for item in value]
        else:
            selections = [part for part in re.split(r"[\n,]", str(value)) if part.strip()]
        unknown = [item for item in selections if item not in entry["options"]]
        if unknown:
            problems.append(
                f"multi-select question '{question_id}' only accepts the "
                f"listed options; unknown: {', '.join(unknown)}"
            )
            continue
        records.append({
            "kind": "list",
            "fields": entry["options"],
            "value": _UNIT_SEP.join(_clean_field(sel) for sel in selections),
        })
    if problems:
        raise ValueError("\n".join(problems))
    return records


def _agent_answers_path_write(job, directory):
    """Write the prepared-answers file for one queued job (or None).

    Record values are already clean and single-line (validated in
    _agent_records; list selections join on \x1f without any extra cleanup,
    or the join separator itself would be mangled). An empty record value
    (an answered "none selected") still gets its line, so the helpers take
    the answer instead of re-asking through a pass-up dialog.
    """
    records = job.agent_answer_records
    if not records:
        return None
    with open(os.path.join(directory, "answers"), "w", encoding="utf-8") as handle:
        for record in records:
            key = _agent_key(record["kind"], record["fields"])
            handle.write(f"{key}\t{record['value']}\n")
    return os.path.join(directory, "answers")


def _agent_dir(job):
    """Per-job agent dialog directory (events + answers files)."""
    if job.agent_event_dir:
        return job.agent_event_dir
    directory = os.path.join(_tmp_dir(), f"agent-{job.id}")
    os.makedirs(directory, mode=0o700, exist_ok=True)
    job.agent_event_dir = directory
    return directory


def _agent_events_path(job):
    return os.path.join(_agent_dir(job), "events")


def _read_agent_events(directory):
    """Parse one job's event file: (warnings, live_prompts, fatal_errors)."""
    warnings, prompts, errors = [], [], []
    if not directory:
        return warnings, prompts, errors
    try:
        with open(os.path.join(directory, "events"), "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.rstrip("\n")
                if not line or "\t" not in line:
                    continue
                kind, text = line.split("\t", 1)
                if kind == "warn" and text not in warnings:
                    warnings.append(text)
                elif kind == "prompt" and text not in prompts:
                    prompts.append(text)
                elif kind == "error" and text not in errors:
                    errors.append(text)
    except OSError:
        pass
    return warnings, prompts, errors


def _iter_script_entries():
    """All catalog entries LinuxToys would show: scripts, repo and AppStream."""
    translations = _translations()
    entries = []
    categories = parser.get_categories(translations) or []
    for category in categories:
        if category.get("is_script"):
            entries.append(category)
            continue
        entries.extend(parser.get_all_scripts_recursive(category["path"], translations) or [])
    entries.extend(parser.get_repo_entries(translations) or [])
    return entries


def _search_catalog(query, limit=20):
    """Fuzzy name/description search across every installed catalog source."""
    query = str(query or "").strip().casefold()
    if len(query) < 2:
        return []
    translations = _translations()
    scored = []

    for entry in _iter_script_entries():
        name = str(entry.get("name") or "")
        stable = _stable_id(entry)
        description = str(entry.get("description") or "")
        haystack = f"{name}\n{stable}\n{description}".casefold()
        score = 0
        if query == name.casefold() or query == stable.casefold():
            score = 100
        elif query in name.casefold():
            score = 80
        elif query in stable.casefold():
            score = 70
        elif query in description.casefold():
            score = 30
        else:
            # Loose fallback: every word must appear somewhere.
            words = [w for w in re.split(r"\s+", query) if w]
            if words and all(w in haystack for w in words):
                score = 10
        if score:
            scored.append((score, entry))

    try:
        scripts_dir, curated_entries, category_paths = _appstream_context()
        for entry, score in appstream_parser.search_entries(
            scripts_dir, query, curated_entries=curated_entries, category_paths=category_paths
        ):
            scored.append((max(1, int(score)), entry))
    except Exception:
        pass  # A cold or broken AppStream cache must not hide script matches.

    # Punctuation-heavy queries ("0 A.D.") miss the Rust token index; an exact
    # ID/name resolution is still worth returning.
    if not any(
        str(candidate.get("appstream_id") or "").strip().casefold() == query
        for _score, candidate in scored
        if candidate.get("appstream_id")
    ):
        try:
            scripts_dir, curated_entries, category_paths = _appstream_context()
            exact = (
                appstream_parser.find_entry_by_id(scripts_dir, query, curated_entries, category_paths)
                or appstream_parser.find_entry_by_name(scripts_dir, query, curated_entries, category_paths)
            )
            if exact is not None:
                scored.append((90, exact))
        except Exception:
            pass

    seen = set()
    results = []
    for score, entry in sorted(scored, key=lambda pair: -pair[0]):
        stable = _stable_id(entry)
        key = (stable.casefold(), str(entry.get("name", "")))
        if not stable or key in seen:
            continue
        seen.add(key)
        results.append({
            "id": stable,
            "name": str(entry.get("name") or stable),
            "description": str(entry.get("description") or ""),
            "source": _entry_kind(entry),
            "category": str(entry.get("category") or ""),
            "match_score": score,
        })
        if len(results) >= max(1, int(limit)):
            break
    return results


def _screenshot_urls(entry):
    urls = []
    raw = entry.get("screenshots") or []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                urls.append(item)
            elif isinstance(item, dict):
                for image in (item.get("images") or []):
                    url = str(image.get("url") or "").strip()
                    if url:
                        urls.append(url)
    return urls


def _blocks_to_text(blocks):
    """Flatten structured description blocks into plain text."""
    lines = []
    for block in blocks or ():
        if block.get("type") == "paragraph":
            lines.append("".join(str(s.get("text") or "") for s in (block.get("spans") or ())))
        elif block.get("type") in ("unordered_list", "ordered_list"):
            prefix = "- " if block.get("type") == "unordered_list" else "* "
            for item in (block.get("items") or ()):
                lines.append(prefix + "".join(str(s.get("text") or "") for s in item))
        elif isinstance(block.get("text"), str):
            lines.append(block["text"])
    return "\n\n".join(line for line in lines if line.strip())


def _installed_state(entry):
    """Where LinuxToys currently sees this app, based on registry + packages."""
    registry_data = registry_utils.parse_registry_file()
    identities = {
        str(entry.get("registry_name") or "").strip(),
        str(entry.get("name") or "").strip(),
        _stable_id(entry).casefold(),
    }
    transactions = []
    for identity in identities:
        transactions.extend(registry_data.get(identity) or [])
    observed = None
    try:
        observed = installed_packages.match(entry)
    except Exception:
        observed = None
    return {
        "in_action_registry": bool(transactions),
        "last_transaction": transactions[-1][0] if transactions else "",
        "observed": dict(observed) if observed else None,
        "installed": bool(transactions or observed),
    }


def _app_links(entry):
    links = {}
    homepage = str(entry.get("homepage") or "").strip()
    if homepage:
        links["homepage"] = homepage
    donate = str(entry.get("donate_url") or "").strip()
    if donate:
        links["donate"] = donate
    purchase = str(entry.get("purchase_url") or "").strip()
    if purchase:
        links["purchase"] = purchase
    options = []
    for option in (entry.get("purchase_options") or ()):
        if isinstance(option, dict) and option.get("url"):
            options.append({
                "price": option.get("price", ""),
                "currency_symbol": option.get("currency_symbol", ""),
                "period": option.get("period", ""),
                "url": option.get("url"),
            })
    if options:
        links["purchase_options"] = options
    subscriptions = []
    for option in (entry.get("subscription_options") or ()):
        if isinstance(option, dict) and option.get("url"):
            subscriptions.append({
                "price": option.get("price", ""),
                "currency_symbol": option.get("currency_symbol", ""),
                "period": option.get("period", ""),
                "url": option.get("url"),
            })
    if subscriptions:
        links["subscription_options"] = subscriptions
    return links


def _appstream_context():
    """Resolve the AppStream universe exactly like the GUI catalog views.

    Uses the fuller curated set (repository entries plus curated scripts) so
    MCP search results match the GUI's duplicate suppression.

    ``category_paths`` must be included: without it the Rust category mapping
    drops every non-Homebrew component, and a derived-cache rebuild triggered
    by this server would publish that incomplete generation. (_runtime_catalog
    now also defaults a missing context to the indexed paths, so this stays
    correct even if the explicit context is lost.)
    """
    translations = _translations()
    return (
        parser.SCRIPTS_DIR,
        parser._get_appstream_curated_entries(translations),
        parser._indexed_category_paths(),
    )


def _resolve_entry(app_id):
    """Resolve a stable ID to a full catalog entry, or None."""
    if not isinstance(app_id, str) or not app_id.strip():
        return None
    target = app_id.strip()

    # Curated LinuxToys IDs retain absolute priority (same order as the
    # browser-facing uri_parser).
    entry = manifest_helper.find_script_by_id(target, _translations())
    if entry is not None:
        return entry

    scripts_dir, curated_entries, category_paths = _appstream_context()
    try:
        entry = appstream_parser.find_entry_by_id(
            scripts_dir, target, curated_entries, category_paths
        )
        if entry is None:
            entry = appstream_parser.find_entry_by_name(
                scripts_dir, target, curated_entries, category_paths
            )
        if entry is not None:
            return entry
    except Exception:
        pass

    # The AUR pseudo-catalog is outside resolve_install_target: accept exact
    # package-name matches only, so resolution stays deterministic.
    try:
        from . import aur_cache
        if aur_cache.enabled():
            folded = target.casefold()
            for candidate, _score in aur_cache.search_entries(target, limit=5):
                if str(candidate.get("package-name") or "").strip().casefold() == folded:
                    return candidate
    except Exception:
        pass
    return None


def _app_details(entry):
    """Build the MCP app page payload from one catalog entry."""
    app_id = _stable_id(entry)
    details = {
        "id": app_id,
        "name": str(entry.get("name") or app_id),
        "source": _entry_kind(entry),
        "category": str(entry.get("category") or ""),
        "description": str(entry.get("description") or ""),
        "homepage": str(entry.get("homepage") or ""),
        "links": _app_links(entry),
        "screenshots": _screenshot_urls(entry),
        "icon": str(entry.get("icon") or "application-x-executable"),
        "revertible": str(entry.get("revert", "yes") or "yes") != "no",
        "needs_reboot": str(entry.get("reboot", "no") or "no") == "yes",
        "installed": _installed_state(entry),
    }
    if entry.get("appstream_source"):
        details["appstream_source"] = str(entry.get("appstream_source"))
        details["appstream_version"] = str(entry.get("appstream_version") or "")
        details["developer"] = str(entry.get("developer") or "")
        details["license"] = str(entry.get("license") or "")
        source_options = [
            str(option.get("appstream_source") or "")
            for option in (entry.get("source_options") or ())
            if isinstance(option, dict) and option.get("appstream_source")
        ]
        if source_options:
            details["available_sources"] = sorted(set(source_options))

    blocks = entry.get("long_description_blocks")
    if isinstance(blocks, list) and blocks:
        details["description_blocks"] = blocks
        details["description_format"] = str(entry.get("long_description_format") or "appstream")
        details["description_locale"] = str(entry.get("long_description_locale") or "")
        flat = _blocks_to_text(blocks)
        if flat:
            details["long_description"] = flat
    elif isinstance(entry.get("long_description"), str) and entry["long_description"].strip():
        details["long_description"] = entry["long_description"]
        details["description_format"] = str(entry.get("long_description_format") or "markdown")
        details["description_locale"] = str(entry.get("long_description_locale") or "")
    if entry.get("summary"):
        details["summary"] = str(entry.get("summary"))
    if str(entry.get("appstream_source") or "") == "flatpak":
        # Flathub addon/extension components published next to the app catalog.
        # Cheap signal so agents know list_app_extensions is worth calling.
        try:
            details["extensions_available"] = bool(
                appstream_cache.get_flatpak_extensions(entry)
            )
        except Exception:
            details["extensions_available"] = False

        # Leftover user data under ~/.var/app/<AppID> outlives its Flatpak
        # app; the same leftover the app page's "Remove data" button offers
        # to delete. The presence probe is a cheap lexists; removal goes
        # through remove_flatpak_data under the same guards as the button.
        identity = flatpak_residue.flatpak_data_identity(entry)
        if identity:
            details["flatpak_app_id"] = identity
        residual_path = flatpak_residue.flatpak_data_path(identity)
        details["flatpak_residual_data"] = flatpak_residue.residual_data_present(residual_path)
        if details["flatpak_residual_data"]:
            details["flatpak_residual_path"] = str(residual_path)
            if not _installed_state(entry)["installed"]:
                details["flatpak_residual_note"] = (
                    "This Flatpak app is no longer installed but its user "
                    f"data is still at '{residual_path}'. remove_flatpak_data "
                    "deletes that directory permanently — get the user's "
                    "approval first."
                )
    return details


def _fetch_screenshot(url):
    """Download one screenshot; returns (bytes, mime) or raises RuntimeError."""
    if not re.match(r"^https?://", str(url)):
        raise ValueError("Only http(s) screenshot URLs can be fetched")
    request = Request(url, headers={"User-Agent": "LinuxToys MCP"})
    with urlopen(request, timeout=30) as response:
        data = response.read(MAX_SCREENSHOT_BYTES + 1)
    if len(data) > MAX_SCREENSHOT_BYTES:
        raise ValueError("Screenshot is too large to return")
    if data.startswith(b"\x89PNG"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith(b"GIF8"):
        mime = "image/gif"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError("Unsupported screenshot format")
    return data, mime


# ---------------------------------------------------------------------------
# Local package files (Package View parity, GTK-free)
# ---------------------------------------------------------------------------
#
# The GUI accepts package files through the Package View: an inspector fills
# name/version/architecture/... for the file, a per-kind host guard decides
# whether that package format is installable on this system, and the install
# runs a generated ``pkg_fromfile``/``pkg_appimage`` one-liner through the
# shared script machinery (askpass dialog on the user's screen, native-manager
# busy waits, transmap, Action Registry, auto-revert). The MCP server mirrors
# exactly that flow with a GTK-free inspector: same accepted extensions, same
# probe commands and same fallback to filename-derived metadata.

PACKAGE_STAGING_SUBDIR = "mcp-packages"
# Upper bound for downloads fetched by agents. Generous — driver bundles and
# multi-rpm meta-packages exceed 200 MiB — but never unbounded.
MAX_PACKAGE_DOWNLOAD_BYTES = 4 * 1024 * 1024 * 1024
PACKAGE_KIND_EXTENSIONS = (
    (".deb", "deb"), (".rpm", "rpm"), (".pacman", "arch"),
    (".eopkg", "eopkg"), (".flatpakref", "flatpakref"),
    (".flatpak", "flatpak"), (".snap", "snap"), (".appimage", "appimage"),
)
PACKAGE_KIND_LABELS = {
    "deb": "Debian package",
    "rpm": "RPM package",
    "arch": "Arch Linux package",
    "eopkg": "Solus package",
    "flatpakref": "Flatpak reference",
    "flatpak": "Flatpak bundle",
    "snap": "Snap package",
    "appimage": "AppImage",
}
SUPPORTED_PACKAGE_KINDS_TEXT = (
    ".deb, .rpm, .pkg.tar.*/.pacman, .eopkg, .flatpak, .flatpakref, "
    ".snap, .appimage"
)


def package_staging_dir():
    directory = os.path.join(_tmp_dir(), PACKAGE_STAGING_SUBDIR)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    return directory


def package_file_kind(path):
    """Package kind accepted for a local file, or None (window.py parity)."""
    name = os.path.basename(os.fspath(path)).lower()
    if re.fullmatch(r".+\.pkg\.tar\.(?:zst|xz|gz|lz4)", name):
        return "arch"
    for suffix, kind in PACKAGE_KIND_EXTENSIONS:
        if name.endswith(suffix):
            return kind
    return None


def package_kind_supported_on_host(kind):
    """Same per-kind host guard the GUI applies before opening a package file."""
    keys = get_system_compat_keys()
    if kind == "snap":
        return not keys & {"steamos", "dakota", "gnomeos", "kde-linux"}
    if kind in ("flatpak", "flatpakref"):
        return "systemd" in keys
    if kind == "appimage":
        return True
    if kind == "deb":
        return bool(keys & {"debian", "ubuntu"})
    if kind == "rpm":
        return bool(keys & {"fedora", "rhel", "suse", "ostree"})
    if kind == "arch":
        return bool(keys & {"arch", "cachy", "manjaro"})
    if kind == "eopkg":
        return "solus" in keys
    return False


def package_file_signature(path):
    """Identify one exact file version, the way the GUI queue guards re-runs."""
    stat = os.stat(path)
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def _package_probe_output(argv, timeout=30):
    """Best-effort stdout of a package metadata probe; "" on any failure."""
    try:
        result = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ""
    return (result.stdout or "").strip()


def _control_field_value(control, field):
    """Read a control-style field, merging indented continuation lines."""
    prefix = field + ":"
    value = ""
    collecting = False
    for line in (control or "").splitlines():
        if collecting:
            if line.startswith((" ", "\t")):
                part = line.strip()
                if part and part != ".":
                    value = f"{value} {part}" if value else part
                continue
            break
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            collecting = True
    return value


def _pkginfo_field_value(text, key):
    """Read a `key = value` line from a .PKGINFO payload."""
    prefix = key + " = "
    for line in (text or "").splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""


def inspect_local_package(path):
    """Package View metadata for one local package file (GTK-free).

    Mirrors the native inspector: same extension mapping, same probe commands
    and the same fallback to filename-derived values. The GUI's icon caching
    is intentionally not part of this flow.
    """
    real = os.path.realpath(os.fspath(path))
    basename = os.path.basename(real)
    name = os.path.splitext(basename)[0]
    kind = package_file_kind(real)
    if kind is None:
        return None
    version = architecture = maintainer = description = ""
    try:
        size = os.path.getsize(real)
    except OSError:
        size = 0

    if kind == "deb":
        control = _package_probe_output(["dpkg-deb", "-f", real])
        if control:
            value = _control_field_value(control, "Package")
            if value:
                name = value
            version = _control_field_value(control, "Version")
            architecture = _control_field_value(control, "Architecture")
            maintainer = _control_field_value(control, "Maintainer")
            description = _control_field_value(control, "Description")
    elif kind == "rpm":
        fields = _package_probe_output([
            "rpm", "-qp", "--qf",
            "%{NAME}\\x1f%{VERSION}-%{RELEASE}\\x1f%{ARCH}"
            "\\x1f%{PACKAGER}\\x1f%{SUMMARY}",
            real,
        ]).split("\x1f")
        if fields and fields[0]:
            name = fields[0]
        version = fields[1] if len(fields) > 1 else ""
        architecture = fields[2] if len(fields) > 2 else ""
        maintainer = fields[3] if len(fields) > 3 else ""
        description = fields[4] if len(fields) > 4 else ""
    elif kind == "arch":
        pkginfo = _package_probe_output(["bsdtar", "-xOf", real, ".PKGINFO"])
        if pkginfo:
            value = _pkginfo_field_value(pkginfo, "pkgname")
            if value:
                name = value
            version = _pkginfo_field_value(pkginfo, "pkgver")
            architecture = _pkginfo_field_value(pkginfo, "arch")
            maintainer = _pkginfo_field_value(pkginfo, "packager")
            description = _pkginfo_field_value(pkginfo, "pkgdesc")
    elif kind == "flatpakref":
        try:
            with open(real, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line.startswith("Name="):
                        name = line[len("Name="):].strip()
                    elif line.startswith("Title=") and line[len("Title="):].strip():
                        name = line[len("Title="):].strip()
                    elif line.startswith("Comment="):
                        description = line[len("Comment="):].strip()
        except OSError:
            pass
    elif kind == "appimage" and len(basename) > 9:
        name = basename[:-len(".appimage")].rstrip(".")

    return {
        "kind": kind,
        "format_label": PACKAGE_KIND_LABELS.get(kind, kind),
        "name": name or basename,
        "version": version,
        "architecture": architecture,
        "maintainer": maintainer,
        "description": description,
        "size": size,
    }


# ---------------------------------------------------------------------------
# Flathub app extensions (addon components, GUI app-page parity)
# ---------------------------------------------------------------------------
#
# Several Flathub applications ship optional extension/addon components
# (org.videolan.VLC.Plugin.*, com.valvesoftware.Steam.Compatibilitytool.*, ...).
# They are AppStream components with <extends>, published by the cache into
# extensions.json keyed by their parent app — never part of the app catalog.
# The GUI installs/removes them with plain `flatpak install/uninstall` through
# the queue runner; the MCP server mirrors that (no transmap/registry, since
# extension refs are not Action Registry transactions there either).


def _flatpak_extension_records(app_id):
    """(parent entry, extension list) for one app's Flathub addons, or ValueError."""
    entry = _resolve_entry(app_id)
    if entry is None:
        raise ValueError(f"Unknown app id '{app_id}'. Use search_apps to list valid IDs.")
    if str(entry.get("appstream_source") or "") != "flatpak":
        name = str(entry.get("name") or app_id)
        raise ValueError(
            f"'{name}' has no Flathub extensions. Extensions exist only for apps "
            "installed from a Flatpak source."
        )
    if not shutil.which("flatpak"):
        raise ValueError("Flatpak is not available on this system.")
    return entry, appstream_cache.get_flatpak_extensions(entry)


def _find_app_extension(extension_records, extension):
    """Resolve one extension by component id or flatpak ref, or ValueError."""
    target = str(extension or "").strip().casefold()
    if not target:
        raise ValueError("An extension component id (or flatpak ref) is required.")
    matches = [
        record for record in extension_records
        if str(record.get("id") or "").casefold() == target
        or str(record.get("flatpak_ref") or "").casefold() == target
    ]
    if not matches:
        # Tolerate the compact ref form ("org.../x86_64/3-25.08") and the
        # bare id embedded in a canonical ref ("runtime/org.../x86_64/branch").
        stripped = target
        for prefix in ("runtime/", "app/"):
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):]
                matches = [
                    record for record in extension_records
                    if str(record.get("flatpak_ref") or "").casefold() == stripped
                ]
        if not matches:
            ref_parts = target.split("/")
            if len(ref_parts) >= 3 and ref_parts[1]:
                matches = [
                    record for record in extension_records
                    if str(record.get("id") or "").casefold() == ref_parts[1].casefold()
                ]
    if not matches:
        raise ValueError(
            f"'{extension}' is not an extension of this app. Use "
            "list_app_extensions to see the available ones."
        )
    if len(matches) > 1:
        refs = ", ".join(sorted(str(item.get("flatpak_ref") or "") for item in matches))
        raise ValueError(
            f"'{extension}' matches {len(matches)} extensions ({refs}). Pass the full flatpak ref."
        )
    return matches[0]


def _extension_record_public(record, installed_refs):
    ref = str(record.get("flatpak_ref") or "")
    return {
        "id": str(record.get("id") or ""),
        "name": str(record.get("name") or record.get("id") or ref),
        "summary": str(record.get("summary") or ""),
        "flatpak_ref": ref,
        "installed": bool(ref) and ref in installed_refs,
        "flatpak_scope": str(record.get("flatpak_scope") or ""),
        "flatpak_remote": str(record.get("flatpak_remote") or ""),
    }


def _installed_extension_refs(entry):
    """Refs of this app's extensions currently installed (read-only flatpak)."""
    try:
        return appstream_cache.installed_flatpak_extension_refs(entry)
    except Exception:
        return set()


def _extension_parent_hint(app_id):
    """Name of the app owning an extension id, for install error hints."""
    folded = str(app_id or "").strip().casefold()
    if "." not in folded:
        return ""
    try:
        with open(appstream_cache.EXTENSIONS_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError):
        return ""
    if not isinstance(payload, list):
        return ""
    for record in payload:
        if isinstance(record, dict) and str(record.get("id") or "").casefold() == folded:
            parent = str(record.get("parent_id") or "").strip()
            if parent:
                return (
                    f"'{folded}' is a Flathub extension of '{parent}': install it "
                    "with install_app_extension on that app."
                )
    return ""


def _flatpak_data_blueprint(entry):
    """Validate one catalog entry as a leftover-data target (app page parity).

    Returns (identity, target Path). Raises ValueError with the same reasons
    the GUI's app page refuses to offer its "Remove data" action: not a
    Flatpak component, no safe ~/.var/app/<AppID> mapping, or the app is
    still installed (its live data is never a leftover that may be removed).
    Filesystem presence is probed separately by each caller.
    """
    name = str(entry.get("name") or "").strip()
    if str(entry.get("appstream_source") or "").strip() != "flatpak":
        raise ValueError(
            f"'{name or 'this app'}' is not a Flatpak app. Leftover ~/.var/app "
            "user data only exists for Flatpak apps."
        )
    identity = flatpak_residue.flatpak_data_identity(entry)
    target = flatpak_residue.flatpak_data_path(identity)
    if not identity or target is None:
        raise ValueError(
            f"'{name or 'this app'}' has no Flatpak app ID that maps to a safe "
            "~/.var/app/<AppID> path, so its leftover data cannot be addressed."
        )
    installed = _installed_state(entry)
    if installed["installed"]:
        seen = (
            "registry transaction"
            if installed["in_action_registry"]
            else "installed Flatpak package"
        )
        raise ValueError(
            f"'{name or identity}' is still installed ({seen}). Removing its "
            "data would discard a working installation's data; remove the "
            "app first with remove_app, then retry."
        )
    return identity, target


# ---------------------------------------------------------------------------
# Job manager: serialized install/remove runs with GUI askpass
# ---------------------------------------------------------------------------

class Job:
    __slots__ = (
        "id", "kind", "app_id", "name", "state", "exit_code", "reason",
        "log", "created", "started", "finished",
        "agent_answer_records", "agent_event_dir",
    )

    def __init__(self, kind, app_id):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.app_id = app_id
        self.name = ""
        self.state = "queued"
        self.exit_code = None
        self.reason = ""
        self.log = deque(maxlen=JOB_LOG_LINES)
        self.created = time.time()
        self.started = 0.0
        self.finished = 0.0
        # Agent dialog machinery (script jobs only): prepared answers from
        # a pre-ask flow and the per-job directory with its event file.
        self.agent_answer_records = None
        self.agent_event_dir = ""

    def log_lines(self, tail=None):
        lines = list(self.log)
        if tail is not None:
            lines = lines[-max(1, int(tail)):]
        return lines

    def public(self, tail=None):
        return {
            "job_id": self.id,
            "kind": self.kind,
            "app_id": self.app_id,
            "name": self.name,
            "state": self.state,
            "exit_code": self.exit_code,
            "reason": self.reason,
            "created": self.created,
            "started": self.started or None,
            "finished": self.finished or None,
            "log_tail": self.log_lines(tail),
        }


class JobManager:
    """Runs one install/remove job at a time in a background worker thread."""

    def __init__(self):
        self._jobs = OrderedDict()
        self._queue = queue.Queue()
        self._lock = threading.Lock()
        self._process = None
        self._shutdown = False
        self._worker = threading.Thread(target=self._work, daemon=True, name="linuxtoys-mcp-jobs")
        self._worker.start()

    def submit(self, kind, app_id, agent_answer_records=None):
        entry = _resolve_entry(app_id)
        if entry is None:
            raise ValueError(f"No installable entry found for '{app_id}'. Use search_apps to list valid IDs.")
        # Outdated-version gate: LinuxToys script jobs (plain scripts, repo
        # scripts and registry removals) are refused while the installed
        # release is more than two published releases behind. Package
        # transactions keep working and the check fails open.
        if self._gate_applies(kind, entry):
            refusal = _version_gate_refusal()
            if refusal:
                raise ValueError(refusal)
        job = Job(kind, app_id)
        job.name = str(entry.get("name") or app_id)
        job.agent_answer_records = (
            [dict(record) for record in (agent_answer_records or [])] or None
        )
        self._register(job)
        self._queue.put((job, entry))
        return job

    def submit_update(self):
        """Queue LinuxToys' self-update (the GUI's silent updater machinery).

        Serialized with every other job. Refused while any work is active so
        package operations never race the installation being replaced.
        """
        with self._lock:
            busy = [
                job for job in self._jobs.values()
                if job.state in ("queued", "running")
            ]
        if busy:
            names = ", ".join(
                f"{job.id} ({job.name or job.kind})" for job in busy[:3]
            )
            raise ValueError(
                "The update cannot start while LinuxToys jobs are active: "
                f"{names}. Poll get_job until they finish, then retry."
            )
        job = Job("update", "linuxtoys")
        job.name = "LinuxToys"
        self._register(job)
        self._queue.put((job, None))
        return job

    def submit_system_update(self, agent_answer_records=None):
        """Queue the app's full system update (sysup.sh, "Update System").

        Not the app's own self-update (submit_update); this is the same
        plain script the GUI's main-window card and the automatic-update
        service run: distro packages, Flatpaks, Snaps, Homebrew/Bun,
        orphan and leftover-desktop-shortcut cleanup. It is a LinuxToys
        script run, so the outdated-version gate governs it like any other
        script job, and it is serialized against the LinuxToys self-update
        so it never races the app being replaced. Needs root: the password
        dialog appears on the user's screen. Pre-asked script questions
        (release-upgrade prompts and other questions in sysup) arrive as
        prepared answers through agent_answer_records.
        """
        with self._lock:
            self_update_busy = any(
                job.state in ("queued", "running") and job.kind == "update"
                for job in self._jobs.values()
            )
        if self_update_busy:
            raise ValueError(
                "The system update cannot start while the LinuxToys "
                "self-update is active. Poll get_job until it finishes, "
                "restart the linuxtoys-mcp service, then retry."
            )
        entry = _system_update_entry()
        if self._gate_applies("system_update", entry):
            refusal = _version_gate_refusal()
            if refusal:
                raise ValueError(refusal)
        job = Job("system_update", "sysup")
        job.name = str(entry.get("name") or "System update")
        job.agent_answer_records = (
            [dict(record) for record in (agent_answer_records or [])] or None
        )
        self._register(job)
        self._queue.put((job, entry))
        return job

    def submit_file(self, spec):
        """Queue a package-file install (Package View parity).

        ``spec`` carries path, kind, display metadata and the exact-file
        signature captured before queueing. Run order stays serialized with
        every other job.
        """
        spec = dict(spec or {})
        path = str(spec.get("path") or "")
        if not os.path.isfile(path):
            raise ValueError(f"No package file found at '{path}'.")
        job = Job("install_file", path)
        job.name = str(spec.get("name") or os.path.basename(path))
        self._register(job)
        self._queue.put((job, spec))
        return job

    def submit_extension(self, entry, extension, remove=False):
        """Queue a Flathub app extension install/uninstall.

        ``extension`` is the catalog extension payload (self-sufficient: its
        own flatpak_ref/remote/scope/installation). Mirrors the GUI's queue
        runner: no transmap, no Action Registry state.
        """
        extension = dict(extension or {})
        job = Job("extension_remove" if remove else "extension_install", _stable_id(entry))
        job.name = str(
            extension.get("name") or extension.get("flatpak_ref") or "Flatpak extension"
        )
        self._register(job)
        self._queue.put((job, extension))
        return job

    def submit_flatpak_data(self, entry):
        """Queue the leftover-data cleanup for one uninstalled Flatpak app.

        Mirrors the GUI app page's "Remove data" action: the entry must be a
        Flatpak component that is no longer installed and still owns its
        ~/.var/app/<AppID> directory. The identity/path guards and the probe
        re-run inside the worker, so state changes while queued re-refuse.
        Not a script and not a package transaction: no version gate, no
        transmap, no Action Registry registration.
        """
        identity, target = _flatpak_data_blueprint(entry)
        if not flatpak_residue.residual_data_present(target):
            raise ValueError(
                f"No leftover user data found for '{entry.get('name') or identity}' "
                f"at '{target}' — nothing to remove."
            )
        job = Job("flatpak_data_remove", _stable_id(entry))
        job.name = str(entry.get("name") or identity)
        self._register(job)
        self._queue.put((job, entry))
        return job

    def _register(self, job):
        evicted = []
        with self._lock:
            self._jobs[job.id] = job
            while len(self._jobs) > 100:
                evicted.append(self._jobs.popitem(last=False)[1])
        for stale in evicted:
            # Job payloads live in memory; their dialog directories are root
            # files on /tmp: best-effort removal keeps them from piling up.
            if getattr(stale, "agent_event_dir", ""):
                shutil.rmtree(stale.agent_event_dir, ignore_errors=True)

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(str(job_id or "").strip())

    def snapshot(self, limit=20):
        with self._lock:
            jobs = list(self._jobs.values())[-max(1, int(limit)):]
        return [job.public() for job in reversed(jobs)]

    @staticmethod
    def _gate_applies(kind, entry=None):
        """Whether the outdated-version gate governs this job kind.

        Only LinuxToys script logic is gated: plain scripts, repo scripts,
        registry removals (which run generated uninstall scripts) and the
        full system update (also a plain script run). AppStream, Snap/Flatpak,
        AppImage, AUR and Homebrew instalments and local package files are
        package pipelines and stay ungated — the same split every other
        runner surface uses.
        """
        if kind in ("remove", "system_update"):
            return True
        if kind != "install":
            return False
        entry = entry or {}
        if str(entry.get("appstream_source") or "").strip():
            return False
        if entry.get("is_appstream_entry"):
            return False
        return True

    def shutdown(self):
        self._shutdown = True
        self._queue.put(None)

    def _work(self):
        while not self._shutdown:
            item = self._queue.get()
            if item is None:
                break
            job, entry = item
            self._run(job, entry)
            self._queue.task_done()

    # -- execution ---------------------------------------------------------

    def _run(self, job, entry):
        job.state = "running"
        job.started = time.time()
        try:
            try:
                # Extension installs/uninstalls, app updates and leftover
                # Flatpak data cleanups never enter the bug-report history
                # in the GUI either: they are flatpak-side operations and
                # the app's own update, not app scripts.
                if job.kind not in (
                    "extension_install", "extension_remove", "update", "flatpak_data_remove",
                ):
                    antenna.add_script_to_history(str(job.name))
            except Exception:
                pass  # Bug-report context is best effort.

            # The gate can tighten while a job waits in the queue: re-check it
            # right before the script starts, mirroring the GUI's run gate.
            if job.kind in ("install", "remove", "system_update") and self._gate_applies(job.kind, entry):
                refusal = _version_gate_refusal()
                if refusal:
                    self._log(job, refusal)
                    job.exit_code = 1
                    job.reason = refusal
                    job.state = "error"
                    return

            if job.kind == "update":
                code, reason = self._update_app(job)
            elif job.kind == "install_file":
                code, reason = self._install_file(job, entry)
            elif job.kind in ("extension_install", "extension_remove"):
                code, reason = self._run_extension(
                    job, entry, remove=job.kind == "extension_remove"
                )
            elif job.kind == "install":
                code, reason = self._install(job, entry)
            elif job.kind == "system_update":
                # Same plain-script pipeline as installs (temp-copy filter,
                # compatibility check, package-manager wait, transmap run).
                # sysup.sh opts itself out of the registry and the antenna is
                # recorded above like any GUI script run; the refusals of a
                # failed run mirror what the GUI terminal shows.
                code, reason = self._install(job, entry)
            elif job.kind == "flatpak_data_remove":
                code, reason = self._remove_flatpak_data(job, entry)
            else:
                code, reason = self._remove(job, entry)
            job.exit_code = code
            job.reason = reason
            job.state = "success" if code == 0 else "error"
        except Exception as exc:  # Never crash the worker.
            job.exit_code = 1
            job.reason = f"{exc}"
            job.state = "error"
        finally:
            job.finished = time.time()
            if job.log:
                appstream_logs.append_appstream_log(
                    f"mcp-{job.kind}-{job.name or job.app_id}",
                    "\n".join(job.log),
                )

    def _log(self, job, text):
        if not text:
            return
        for line in str(text).splitlines():
            job.log.append(line)

    def _new_transmap(self):
        directory = _tmp_dir()
        fd, path = tempfile.mkstemp(prefix="mcp-transmap-", dir=directory, text=True)
        os.close(fd)
        os.chmod(path, 0o600)
        return path

    def _install(self, job, entry):
        entry = dict(entry)
        cleanup_paths = []
        try:
            source = str(entry.get("appstream_source", "") or "").strip()
            path_value = str(entry.get("path", "") or "")

            # Provider-specific pipelines first: these entries are also "repo
            # entries", but the generic materialization cannot serve them.
            if source == "homebrew":
                from . import homebrew_catalog
                try:
                    entry = homebrew_catalog.materialize_install(entry)
                except Exception as exc:
                    return 1, f"Could not prepare Homebrew install of '{job.name}': {exc}"
                cleanup_paths.append(entry.get("path"))
            elif source == "appimage":
                return self._install_appimage(job, entry)
            elif source == "aur" or path_value.startswith("aur://"):
                return self._install_aur(job, entry)
            elif entry.get("is_appstream_entry"):
                # Flathub/Snap/native AppStream entries run through the full
                # TUI pipeline: install body plus reviewed dependency and
                # Flatpak-permission phases, in the same order as the GUI
                # queue runner.
                raw_path, prepared = self._prepare_appstream_script(job, entry)
                if raw_path is None:
                    return 1, prepared
                if prepared:
                    cleanup_paths.append(prepared)
                entry = dict(entry)
                entry["path"] = raw_path
            elif entry.get("is_repo_entry"):
                try:
                    entry = materialize_repo_script(entry)
                except (ValueError, NotImplementedError, OSError) as exc:
                    return 1, f"Could not prepare repository entry '{job.name}': {exc}"

            if str(entry.get("path", "")).startswith(("appstream://", "repo://", "aur://")):
                return 1, f"Could not prepare an installer for '{job.name}' (unresolvable entry)."

            path, prepared = self._prepare_run_script(job, entry)
            if path is None:
                return 1, prepared
            if prepared:
                cleanup_paths.append(prepared)

            # Plain physical scripts keep their compatibility checks (same as
            # the CLI and the GUI); repo/AppStream entries were already
            # compatibility-filtered by their parsers.
            if not entry.get("is_appstream_entry") and not entry.get("is_repo_entry"):
                compat_keys = parser.get_system_compat_keys()
                if not script_is_compatible(entry.get("path", ""), compat_keys):
                    return 1, f"'{job.name}' is not compatible with this system."

            return self._execute_script(job, entry)
        finally:
            for path in cleanup_paths:
                try:
                    if path and path != "true" and os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass

    def _prepare_appstream_script(self, job, entry):
        """Return (run_path, cleanup_path) for one AppStream entry, or (None, reason)."""
        try:
            from .tui.appstream_executor import build_install_script
        except ImportError as exc:
            return None, f"AppStream installer unavailable: {exc}"
        try:
            raw_path = build_install_script(entry)
        except (OSError, ValueError) as exc:
            return None, f"Could not build the installer for '{job.name}': {exc}"
        try:
            path = easy_cli.create_temp_file(raw_path)
        finally:
            try:
                os.remove(raw_path)
            except OSError:
                pass
        return path, path

    def _prepare_run_script(self, job, entry):
        """Return (run_path, cleanup_path) for plain/repo scripts, or (None, reason).

        AppStream entries were already prepared by the caller; plain curated
        scripts go through the same xdg-open filter as the CLI.
        """
        if entry.get("is_appstream_entry"):
            return entry.get("path"), None
        path = easy_cli.create_temp_file(entry["path"])
        return path, path

    def _install_aur(self, job, entry):
        """Run the AUR pipeline: source security scan, then pkg_install."""
        package = str(entry.get("package-name") or "").strip()
        if not package:
            return 1, f"AUR entry '{job.name}' has no package name."
        from .tui.appstream_executor import (
            AUR_SECURITY_OK,
            build_aur_install_script,
            check_aur_package_security,
        )
        status, details = check_aur_package_security(package)
        if status != AUR_SECURITY_OK:
            return int(status), (
                f"AUR package '{package}' failed the source security check:\n{details}"
            )
        script_path = build_aur_install_script(package)
        try:
            payload = dict(entry)
            payload["path"] = script_path
            return self._execute_script(job, payload, transmap_mark="manifest-export skip")
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass

    def _install_appimage(self, job, entry):
        """Resolve, download and install an AppImage catalog entry."""
        try:
            code = 1
            with appimage_catalog.download_for_install(entry) as (path, release):
                self._log(job, f"Resolved AppImage release {release.get('version') or '(untagged)'}")
                self._log(job, f"Downloaded {release.get('download_url') or path}")
                directory = _tmp_dir()
                fd, script_path = tempfile.mkstemp(prefix="mcp-appimage-", suffix=".sh", dir=directory, text=True)
                os.close(fd)
                try:
                    with open(script_path, "w", encoding="utf-8") as handle:
                        handle.write("#!/usr/bin/env bash\n")
                        handle.write(f"pkg_appimage {shlex_quote(path)}\n")
                    os.chmod(script_path, 0o700)
                    payload = dict(entry)
                    payload.update({
                        "is_local_package": True,
                        "path": script_path,
                        "appimage_release": release,
                        "local_package_path": path,
                        "local_package_kind": "appimage",
                        "local_package_signature": appimage_catalog.file_signature(path),
                    })
                    code, _ = self._execute_script(
                        job, payload, transmap_mark="manifest-export skip"
                    )
                finally:
                    try:
                        os.remove(script_path)
                    except OSError:
                        pass
            if code != 0:
                return code, f"pkg_appimage exited with status {code}. See the job log for details."
            return 0, ""
        except (OSError, ValueError, RuntimeError) as exc:
            return 1, f"AppImage installation failed: {exc}"

    def _install_file(self, job, spec):
        """Install one local package file through the Package View machinery.

        Mirrors the GUI's local-package job: re-verify the exact file that was
        inspected at queue time (dev/ino/size/mtime signature), then run a
        generated ``pkg_fromfile``/``pkg_appimage`` one-liner through
        `_execute_script`, so askpass, native-manager waits, the registry and
        automatic reversion behave exactly like a user install.
        """
        spec = dict(spec or {})
        path = str(spec.get("path") or "")
        kind = str(spec.get("kind") or "")
        function = "pkg_appimage" if kind == "appimage" else "pkg_fromfile"

        try:
            current = package_file_signature(path)
        except OSError as exc:
            return 1, f"The package file disappeared before installation: {exc}"
        expected = tuple(spec.get("signature") or ())
        if expected and current != expected:
            return 1, f"The package file changed before installation: {path}"

        directory = _tmp_dir()
        fd, script_path = tempfile.mkstemp(prefix="mcp-package-", suffix=".sh", dir=directory, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("#!/usr/bin/env bash\n")
                handle.write(f"{function} {shlex_quote(path)}\n")
            os.chmod(script_path, 0o700)
            payload = {
                "name": str(spec.get("name") or os.path.basename(path)),
                "description": str(spec.get("description") or ""),
                "icon": "package-x-generic",
                "registry_name": str(spec.get("registry_name") or spec.get("name") or os.path.basename(path)),
                "path": script_path,
                "is_local_package": True,
            }
            code, reason = self._execute_script(job, payload, transmap_mark="manifest-export skip")
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass
        if code == 0:
            return 0, ""
        return code, reason or (
            f"{function} exited with status {code}. See the job log for details."
        )

    def _run_extension(self, job, spec, remove=False):
        """flatpak install/uninstall of one Flathub app extension.

        Mirrors the GUI's extension runner: the scope (user/`--installation`
        /system) comes from the extension payload, installs pin the app's
        remote (default flathub), and system-scope operations may raise a
        polkit password dialog on the user's screen. Extensions are not
        Action Registry transactions, so no transmap/registry bookkeeping.
        """
        ref = str(spec.get("flatpak_ref") or "").strip()
        if not ref:
            return 2, "Extension has no flatpak ref."

        scope = str(spec.get("flatpak_scope") or "").strip()
        installation = str(spec.get("flatpak_installation") or "").strip()
        if scope == "user":
            scope_args = ["--user"]
        elif installation and installation != "default":
            scope_args = [f"--installation={installation}"]
        else:
            scope_args = ["--system"]

        argv = ["flatpak", *scope_args]
        if remove:
            argv += ["uninstall", "-y", ref]
        else:
            remote = str(spec.get("flatpak_remote") or "flathub").strip() or "flathub"
            argv += ["install", "-y", remote, ref]

        code, output = self._run_command(job, argv, {})
        if code == 0:
            return 0, ""
        action = "uninstall" if remove else "install"
        return code, self._failure_reason(output) or (
            f"flatpak {action} exited with status {code}. See the job log for details."
        )

    def _remove_flatpak_data(self, job, entry):
        """Remove one uninstalled Flatpak app's leftover ~/.var/app/<AppID>.

        Re-runs the full guard set (flatpak source, safe identity, uninstalled
        state) at execution time: the app may have been installed or removed
        elsewhere while the job waited in the queue. A leftover that vanished
        in the meantime is a no-op success, not an error.
        """
        try:
            identity, target = _flatpak_data_blueprint(entry)
        except ValueError as exc:
            return 1, str(exc)
        if not flatpak_residue.residual_data_present(target):
            self._log(job, "Leftover user data is already gone; nothing to remove.")
            return 0, ""
        self._log(job, f"Removing leftover Flatpak user data: {target}")
        error = flatpak_residue.remove_residual_data(target)
        if error:
            return 1, (
                f"Could not remove leftover user data '{target}': {error}. "
                "See the job log for details."
            )
        self._log(job, f"Removed leftover Flatpak user data: {target}")
        return 0, ""

    def _remove(self, job, entry):
        blockers = installed_packages.dependency_blockers(entry)
        if blockers:
            return 1, "Cannot remove '{}' yet — installed software still depends on it: {}".format(
                job.name, "; ".join(blockers)
            )
        from .revert_helper import build_uninstall_script_entry
        uninstall_entry = build_uninstall_script_entry(entry, None)
        if not uninstall_entry:
            return 1, f"No removable registry entry found for '{job.name}'. Install it through LinuxToys first."
        script_dir = _script_dir()
        try:
            # Uninstalls reach native managers through pkg_remove/pkg_install;
            # wait for any running package operation first, like the CLI does.
            if easy_cli.package_guard.native_transaction_conflict(
                uninstall_entry["path"], script_dir
            ) is not None:
                self._log(job, "Waiting for a running package manager to go idle...")
                if not easy_cli._wait_for_package_manager_cli():
                    return 1, easy_cli.package_guard.timeout_texts()[1]
            code, output = self._run_command(job, script_command(uninstall_entry["path"], script_dir), {})
        finally:
            cleanup_path = uninstall_entry.get("cleanup_path")
            if cleanup_path:
                try:
                    os.remove(cleanup_path)
                except OSError:
                    pass
        if code != 0:
            return code, f"Removal of '{job.name}' failed with exit code {code}. See the job log for details."
        return 0, ""

    def _execute_script(self, job, script_info, transmap_mark=None):
        """Run one prepared script with transmap + registry handling."""
        script_dir = _script_dir()
        if "CACHE_DIR" not in os.environ:
            os.environ["CACHE_DIR"] = os.path.join(script_dir, "scripts")

        registry_name = script_info.get("registry_name", script_info.get("name", "unknown"))
        transmap_path = self._new_transmap()
        if transmap_mark:
            try:
                with open(transmap_path, "a", encoding="utf-8") as handle:
                    handle.write(transmap_mark + "\n")
            except OSError:
                pass
        try:
            env = script_environment(script_info, os.environ.copy())
            env["TRANSMAP_PATH"] = transmap_path
            env.pop("LINUXTOYS_RUNNER_STATE", None)
            env.pop("LINUXTOYS_APPSTREAM_PACKAGE", None)

            # Agent dialog machinery: scripts driven through the MCP service
            # must not block on dialog clicks. The shell helpers consult the
            # events file (warn/die/failed-question events the tools relay)
            # and the prepared-answers file written from validated user
            # choices, and keep password dialogs and any prompt that could
            # not be pre-asked working on the user's screen.
            if not job.agent_event_dir:
                _agent_dir(job)
            env["LT_AGENT_MODE"] = "1"
            env["LT_AGENT_EVENTS"] = _agent_events_path(job)
            answers_path = _agent_answers_path_write(job, job.agent_event_dir)
            if answers_path:
                env["LT_AGENT_ANSWERS"] = answers_path

            # Semantic resolution for single-package native AppStream entries,
            # mirroring the GUI runner.
            if script_info.get("appstream_source") == "native":
                from .appstream_resolver import resolve_native_appstream_package
                value = script_info.get("package-name")
                packages = (
                    [value.strip()]
                    if isinstance(value, str) and value.strip()
                    else [str(v).strip() for v in (value if isinstance(value, (list, tuple)) else ()) if str(v).strip()]
                )
                if len(packages) == 1:
                    resolved = resolve_native_appstream_package(
                        packages[0],
                        component_id=script_info.get("appstream_id"),
                        desktop_id=script_info.get("appstream_launchable"),
                        name=script_info.get("name"),
                    )
                    env["LINUXTOYS_APPSTREAM_PACKAGE"] = resolved

            # A running native package manager wins: wait like every other
            # LinuxToys runner before touching it.
            if easy_cli.package_guard.native_transaction_conflict(
                script_info.get("path", ""), script_dir
            ) is not None:
                self._log(job, "Waiting for a running package manager to go idle...")
                if not easy_cli._wait_for_package_manager_cli():
                    return 1, easy_cli.package_guard.timeout_texts()[1]

            code, output = self._run_command(
                job, script_command(script_info["path"], script_dir), env
            )

            registry_disabled = str(script_info.get("registry", "") or "").strip().lower() == "no"
            if code == 0:
                if not registry_disabled:
                    ExecutionRegistry._save_to_registry(registry_name, transmap_path)
                self._finish_transmap(transmap_path)
                return 0, ""
            if code == 100:
                # User cancelled the askpass dialog or a script prompt.
                self._finish_transmap(transmap_path)
                return 100, "Cancelled on the user's screen (password dialog or prompt)."
            if easy_cli._is_error_exit_code(code):
                revert_info = {
                    "name": script_info.get("name", "unknown"),
                    "registry_name": registry_name,
                    "icon": "application-x-executable",
                    "repo": "",
                }
                self._log(job, "Script failed. Attempting automatic reversion...")
                if easy_cli._try_execute_auto_revert(revert_info, transmap_path):
                    self._log(job, "Automatic reversion completed successfully.")
                    self._finish_transmap(transmap_path)
                    return code, "Script failed, but its changes were automatically reverted."
                # Keep the transaction revertable through the Action Registry.
                ExecutionRegistry._save_to_registry(registry_name, transmap_path)
                return code, self._failure_reason(output) or (
                    f"Script failed with exit code {code}."
                )
            self._finish_transmap(transmap_path)
            return code, ""
        finally:
            try:
                if os.path.exists(transmap_path):
                    os.remove(transmap_path)
            except OSError:
                pass

    def _run_command(self, job, command, env):
        """Run one script subprocess, capturing output into the job log."""
        try:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                errors="replace",
                env=env or None,
                check=False,
            )
        except KeyboardInterrupt:
            return 130, ""
        except Exception as exc:
            self._log(job, f"Failed to launch the script: {exc}")
            return 1, f"Failed to launch the script: {exc}"
        self._log(job, result.stdout)
        return result.returncode, result.stdout

    @staticmethod
    def _failure_reason(output):
        """Prefer the library's die/fatal message (last non-empty line)."""
        lines = [line.strip() for line in (output or "").splitlines() if line.strip()]
        tail = lines[-1] if lines else ""
        if not tail or len(tail) > 300 or re.fullmatch(r"[\W_]+", tail):
            return ""
        return tail

    def _update_app(self, job):
        """Run the official self-updater in this worker thread.

        Delegates to ``run_background_update`` — the GUI's silent update
        path: ``askpass`` pops the password dialog on the user's screen on
        native package hosts, SteamOS uses the user-level AppImage/Gear Lever
        updater, and install.sh runs with ``LINUXTOYS_NONINTERACTIVE=1``.
        """
        try:
            # The updater sources the shell library relative to SCRIPT_DIR;
            # resolve_script_dir() also writes it into os.environ.
            _script_dir()
        except Exception as exc:
            return 1, f"Could not resolve the LinuxToys installation directory to update: {exc}"

        try:
            from .updater.update_helper import run_background_update
        except Exception as exc:
            return 1, f"The updater is unavailable: {exc}"

        self._log(job, "Running the official LinuxToys updater (install.sh)...")
        success, error = run_background_update()
        if success:
            return 0, (
                "LinuxToys updated successfully. Restart the linuxtoys-mcp "
                "service (systemctl --user restart linuxtoys-mcp.service) and "
                "reopen the GUI to switch to the new version."
            )
        if "cancel" in (error or "").casefold():
            return 100, "Update cancelled on the user's screen (password dialog)."
        return 1, error or "The background updater failed without a message."

    @staticmethod
    def _finish_transmap(transmap_path):
        easy_cli._cleanup_tmp_noram_dirs(transmap_path)
        try:
            if os.path.exists(transmap_path):
                os.remove(transmap_path)
        except OSError:
            pass


class _LazyJobs:
    """Create the job worker only when this process actually serves jobs.

    Merely importing mcp_server (GUI menu, CLI status checks) must not spawn
    worker threads.
    """

    def __init__(self):
        self._manager = None
        self._lock = threading.Lock()

    def _get(self):
        with self._lock:
            if self._manager is None:
                self._manager = JobManager()
            return self._manager

class _LazyJobs:
    """Create the job worker only when this process actually serves jobs.

    Merely importing mcp_server (GUI menu, CLI status checks) must not spawn
    worker threads.
    """

    def __init__(self):
        self._manager = None
        self._lock = threading.Lock()

    def _get(self):
        with self._lock:
            if self._manager is None:
                self._manager = JobManager()
            return self._manager

    def submit(self, kind, app_id, agent_answer_records=None):
        return self._get().submit(kind, app_id, agent_answer_records)

    def submit_update(self):
        return self._get().submit_update()

    def submit_system_update(self, agent_answer_records=None):
        return self._get().submit_system_update(agent_answer_records)

    def submit_file(self, spec):
        return self._get().submit_file(spec)

    def submit_extension(self, entry, extension, remove=False):
        return self._get().submit_extension(entry, extension, remove)

    def submit_flatpak_data(self, entry):
        return self._get().submit_flatpak_data(entry)

    def get(self, job_id):
        return self._get().get(job_id)

    def snapshot(self, limit=20):
        return self._get().snapshot(limit)

    def shutdown(self):
        if self._manager is not None:
            self._manager.shutdown()


JOBS = _LazyJobs()


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

def _bool_schema(description):
    return {"type": "boolean", "description": description}


def tool_schemas():
    return [
        {
            "name": "server_info",
            "description": (
                "LinuxToys server status: version, connection info, active jobs, "
                "and whether the systemd service is enabled/active."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "list_categories",
            "description": "List LinuxToys catalog categories (system tools, tweaking, etc.).",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_update_status",
            "description": (
                "Check for LinuxToys app updates (performs a network check): "
                "running version, newest published release, releases behind, "
                "whether the app can update itself on this host, and whether "
                "script jobs are blocked by the outdated-version gate."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "update_linuxtoys",
            "description": (
                "Run the official LinuxToys self-update as a tracked job — "
                "the same silent updater the GUI uses. Always get the user's "
                "approval first. A password dialog may appear on the user's "
                "screen. Poll get_job; afterwards restart the linuxtoys-mcp "
                "service so it runs the new version."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "update_system",
            "description": (
                "Run the app's full system update ('Update System') as a "
                "tracked job: distribution packages, Flatpaks, Snaps, "
                "Homebrew/Bun, orphan cleanup — the same run the GUI's menu "
                "card and the automatic-update service use. Not the app's "
                "own self-update (update_linuxtoys does that). Always get "
                "the user's approval first: it changes the whole system, "
                "needs root (the password dialog appears on the user's "
                "screen) and may take a long time. May return "
                "requires_answers first (release-upgrade choices): ask the "
                "user, then re-call with answers. Refused while LinuxToys "
                "itself is more than two releases behind, like any LinuxToys "
                "script run. Returns a job id — poll get_job."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "answers": {
                        "type": "object",
                        "description": "User choices from an earlier requires_answers response: {question id: choice}.",
                        "additionalProperties": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}},
                            ],
                        },
                    },
                },
            },
        },
        {
            "name": "search_apps",
            "description": (
                "Search every LinuxToys catalog (curated scripts, repositories, "
                "AppStream/Flathub/Snap, AppImages) by name or description. Returns "
                "stable IDs to pass to get_app_details/install_app."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term (min 2 characters)"},
                    "limit": {"type": "integer", "description": "Max results (default 20)"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_app_details",
            "description": (
                "Full app page for one stable ID: description, screenshots URLs, "
                "homepage/donation/purchase links, version, install state. For "
                "Flatpak apps also reports leftover ~/.var/app user data "
                "(flatpak_residual_data) when the app is no longer installed."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {"app_id": {"type": "string", "description": "Stable catalog ID"}},
                "required": ["app_id"],
            },
        },
        {
            "name": "get_screenshot",
            "description": (
                "Fetch one app screenshot image (view it to describe the app to the user)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string"},
                    "index": {"type": "integer", "description": "Screenshot index, default 0"},
                },
                "required": ["app_id"],
            },
        },
        {
            "name": "install_app",
            "description": (
                "Install an app or feature by stable ID. Runs exactly like a user "
                "install: when root is required the password dialog appears on the "
                "user's screen. Curated scripts may ask questions first — when the "
                "tool answers requires_answers, show each question to the user and "
                "re-call it with answers={question id: choice}. Returns a job id "
                "— poll get_job until success/error."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string", "description": "Stable catalog ID"},
                    "answers": {
                        "type": "object",
                        "description": (
                            "User choices for the questions returned in an earlier "
                            "requires_answers response: {question id: choice}. "
                            "question values are 'yes'/'no'; radio expects one "
                            "exact option; multi-select expects option string(s) "
                            "(comma-separated) or an array. All ids must be covered."
                        ),
                        "additionalProperties": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}},
                            ],
                        },
                    },
                },
                "required": ["app_id"],
            },
        },
        {
            "name": "fetch_package_url",
            "description": (
                "Download a package file (.deb, .rpm, .pkg.tar.*, .pacman, .eopkg, "
                ".flatpak, .flatpakref, .snap, .appimage) from an http(s) URL into "
                "LinuxToys' private staging directory and return its local path. "
                "Inspect the path with get_package_file_details before installing."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "http(s) URL of the package file"},
                },
                "required": ["url"],
            },
        },
        {
            "name": "get_package_file_details",
            "description": (
                "Inspect a local package file exactly like the GUI's package view: "
                "name, version, architecture, maintainer, description, size and "
                "format, plus whether that package type is supported on this "
                "system (same compatibility guards as the GUI)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the package file (absolute or ~-prefixed)"},
                },
                "required": ["path"],
            },
        },
        {
            "name": "install_package_file",
            "description": (
                "Queue the install of a local package file (.deb, .rpm, "
                ".pkg.tar.*, .pacman, .eopkg, .flatpak, .flatpakref, .snap, "
                ".appimage) through the same guarded machinery the GUI's package "
                "view uses. When root is needed the password dialog appears on "
                "the user's screen. Returns a job id — poll get_job."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the package file (absolute or ~-prefixed)"},
                },
                "required": ["path"],
            },
        },
        {
            "name": "install_app_extension",
            "description": (
                "Install one Flathub extension/addon of an app (VLC plugins, "
                "Steam compatibility tools, ...). Identify it with "
                "list_app_extensions. Returns a job id — poll get_job."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string", "description": "Stable catalog ID of the app the extension belongs to"},
                    "extension": {"type": "string", "description": "Extension component id (e.g. org.videolan.VLC.Plugin.bdj) or its full flatpak ref"},
                },
                "required": ["app_id", "extension"],
            },
        },
        {
            "name": "remove_app_extension",
            "description": (
                "Remove one installed Flathub extension/addon of an app. "
                "Returns a job id — poll get_job."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string", "description": "Stable catalog ID of the app the extension belongs to"},
                    "extension": {"type": "string", "description": "Extension component id or its full flatpak ref"},
                },
                "required": ["app_id", "extension"],
            },
        },
        {
            "name": "list_app_extensions",
            "description": (
                "List the Flathub extensions/addons of one app, each with its "
                "installed state. Only apps whose get_app_details reports "
                "extensions_available have them."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string", "description": "Stable catalog ID"},
                },
                "required": ["app_id"],
            },
        },
        {
            "name": "remove_app",
            "description": (
                "Remove an app/feature installed through LinuxToys, by stable ID. "
                "Returns a job id — poll get_job until success/error."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {"app_id": {"type": "string", "description": "Stable catalog ID"}},
                "required": ["app_id"],
            },
        },
        {
            "name": "remove_flatpak_data",
            "description": (
                "Remove the leftover user data (~/.var/app/<AppID>) of one "
                "Flatpak app that is no longer installed — the same guarded "
                "cleanup the GUI's 'Remove data' button offers on that app's "
                "page. get_app_details reports flatpak_residual_data when "
                "eligible; the tool refuses apps that are still installed. "
                "Confirm with the user first: the deletion is permanent and "
                "needs no password (the data lives in their home). Returns a "
                "job id — poll get_job."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {"app_id": {"type": "string", "description": "Stable catalog ID"}},
                "required": ["app_id"],
            },
        },
        {
            "name": "get_job",
            "description": (
                "Status, exit code and log tail of one install/remove job. "
                "Also carries the script dialogs that phoned home during the "
                "run: warnings (attention-required messages to relay — not "
                "failures), live_prompts (dialogs answered by the user on "
                "screen) and error_detail (the fatal dialog text when the "
                "run failed)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "tail_lines": {"type": "integer", "description": "Log tail length (default 40)"},
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "list_jobs",
            "description": "Recent install/remove jobs handled by this server.",
            "inputSchema": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
        },
        {
            "name": "get_settings",
            "description": (
                "Current LinuxToys settings: automatic updates, automatic bug "
                "reports, interface language, MCP service state."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "set_settings",
            "description": (
                "Change LinuxToys settings: automatic_updates (bool), "
                "automatic_bug_reports (bool), language (code such as 'en', 'pt'). "
                "Only provided fields change. The running GUI applies a language "
                "change on its next launch."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "automatic_updates": _bool_schema("Automatic system self-updates"),
                    "automatic_bug_reports": _bool_schema("Auto-submit bug reports on script failure"),
                    "language": {"type": "string", "description": "Language code (e.g. 'en', 'pt')"},
                },
            },
        },
        {
            "name": "translate_text",
            "description": (
                "Translate text with the same translation method the app page "
                "uses, for the user's convenience. Defaults to the user's language."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "target_language": {"type": "string", "description": "Language code, e.g. 'pt'"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "translate_app_description",
            "description": (
                "Translate one app's full description into a language, sharing the "
                "GUI's translation cache. Defaults to the user's language."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string"},
                    "target_language": {"type": "string"},
                },
                "required": ["app_id"],
            },
        },
        {
            "name": "get_registry_entries",
            "description": (
                "Action Registry entries: everything installed through LinuxToys "
                "with timestamps and recorded changes. Optional substring filter."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
        {
            "name": "export_registry_manifest",
            "description": (
                "Export installed apps as a portable LinuxToys manifest file "
                "(replayable on another machine via manifest mode)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "Output file path (default ~/linuxtoys-manifest.txt)"},
                },
            },
        },
        {
            "name": "open_support_link",
            "description": (
                "Open one of an app's own links (donate, purchase, homepage, "
                "subscription, purchase option) in the user's browser."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["homepage", "donate", "purchase", "purchase_option", "subscription"],
                    },
                    "index": {"type": "integer", "description": "Index for purchase_option/subscription"},
                },
                "required": ["app_id", "kind"],
            },
        },
    ]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_server_info():
    status = service_status()
    gate_summary = None
    try:
        from .updater import version_gate
        gate = version_gate.check()
        if gate.get("applicable"):
            gate_summary = {
                "scripts_blocked": bool(gate.get("blocked")),
                "releases_behind": int(gate.get("behind") or 0),
                "latest_cached": str(gate.get("latest") or "") or None,
                "fresh_check": "Use get_update_status for a networked check.",
            }
    except Exception:
        pass
    return {
        "server": SERVER_NAME,
        "version": __version__,
        "protocol_version": PROTOCOL_VERSION,
        "endpoint": _endpoint_url(),
        "service": status,
        "uptime_seconds": round(time.time() - _TRANSIENT_SERVER["started"], 1),
        "scripts_source": str(parser.SCRIPTS_DIR),
        "appstream_cache_ready": appstream_cache.CATALOG_PATH.is_file(),
        "active_jobs": sum(
            1 for job in JOBS.snapshot(100) if job.get("state") in ("queued", "running")
        ),
        "askpass": (
            "installs that need root show the password dialog on the user's screen"
        ),
        "version_gate": gate_summary,
    }


def _tool_get_update_status():
    """Networked LinuxToys release check plus the local script-gate state."""
    from .compat import self_updates_disabled
    from .updater import version_gate
    from .updater.update_helper import (
        UpdateHelper,
        get_current_version,
        is_from_repository,
    )

    current = get_current_version()
    helper = UpdateHelper()
    latest = helper._get_latest_version()
    latest_tag = str(latest.get("tag_name") or "")

    result = {
        "current_version": current,
        "latest_version": latest_tag or None,
        "update_available": bool(latest_tag and helper._compare_versions(current, latest_tag) == 1),
        "can_self_update": not (self_updates_disabled() or is_from_repository()),
        "release_notes": str(latest.get("body") or "")[:2000] or None,
    }
    if not latest_tag:
        result["check_note"] = (
            "The release check failed (both sources unreachable). Retry later; "
            "an update can still be run."
        )
    if self_updates_disabled():
        result["self_update_note"] = (
            "LinuxToys ships inside the GregOS image; it only changes when "
            "the system image updates."
        )
    elif is_from_repository():
        result["self_update_note"] = (
            "This installation is owned by a system repository (PPA/Copr/git "
            "checkout); update it through that package manager instead of "
            "install.sh."
        )

    # The script gate is cache-only; warm it for this and future calls.
    version_gate.refresh()
    gate = version_gate.check()
    result["scripts_blocked"] = bool(gate.get("blocked"))
    result["script_gate"] = {
        "applicable": bool(gate.get("applicable")),
        "blocked": bool(gate.get("blocked")),
        "releases_behind": int(gate.get("behind") or 0),
        "grace_releases": version_gate.GATE_GRACE_RELEASES,
        "fetched": bool(gate.get("fetched")),
    }
    if gate.get("blocked"):
        result["blocked_note"] = (
            "LinuxToys script jobs (install_app, remove_app, update_system) "
            "are refused until LinuxToys is updated; run update_linuxtoys "
            "(with the user's approval) and retry afterwards. Package "
            "installs (Flathub/Snap, AppImages, AUR, Homebrew, local files) "
            "keep working."
        )
    return result


def _tool_update_linuxtoys():
    """Run the official self-update as a tracked job."""
    from .compat import self_updates_disabled
    from .updater.update_helper import UpdateHelper, get_current_version, is_from_repository

    if self_updates_disabled():
        raise ValueError(
            "LinuxToys ships inside the GregOS image; update the system image "
            "itself and LinuxToys follows it. There is nothing to install here."
        )
    if is_from_repository():
        raise ValueError(
            "This LinuxToys installation is owned by a system repository "
            "(PPA/Copr/git checkout); update it through that package manager "
            "instead of running install.sh, then restart the service."
        )

    # Refuse a pointless run when the release check is reachable and current.
    current = get_current_version()
    helper = UpdateHelper()
    latest_tag = str(helper._get_latest_version().get("tag_name") or "")
    if latest_tag and helper._compare_versions(current, latest_tag) != 1:
        raise ValueError(
            f"LinuxToys is already on the latest published version ({latest_tag})."
        )

    try:
        job = JOBS.submit_update()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not queue the update: {exc}")

    return {
        "job_id": job.id,
        "name": job.name,
        "state": job.state,
        "note": (
            "The official updater runs the same flow as the app's silent "
            "update: a password dialog may pop on the user's screen for the "
            "grant — wait for them to type it, never ask for the password. "
            "Poll get_job; on success restart the service (systemctl --user "
            "restart linuxtoys-mcp.service) so it runs the new version."
        ),
    }


def _tool_update_system(answers=None):
    """Queue a full system update by running the app's own sysup script."""
    try:
        entry = _system_update_entry()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not queue the system update: {exc}")
    try:
        questions, dynamic_count, branch_skipped = _agent_dialog_scan_requests(entry)
    except Exception:
        questions, dynamic_count, branch_skipped = [], 0, 0
    if questions and answers is None:
        return _requires_answers_payload(entry, questions, dynamic_count, branch_skipped)
    if answers is not None and not questions:
        raise ValueError(
            "The system update carries no pre-answerable script questions; "
            "omit answers and queue it directly."
        )
    try:
        records = _agent_records(questions, answers) if answers is not None else None
    except ValueError:
        raise
    try:
        job = JOBS.submit_system_update(agent_answer_records=records)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not queue the system update: {exc}")
    return {
        "job_id": job.id,
        "name": job.name,
        "state": job.state,
        "note": (
            "This runs the app's full system update: distribution packages, "
            "Flatpaks, Snaps, Homebrew/Bun updates, orphan cleanup and "
            "leftover desktop-shortcut removal. It needs root, so the "
            "password dialog appears on the user's screen — wait for them to "
            "type it, never ask for the password. Ubuntu/Fedora release "
            "upgrade choices come from the answer you validated; warnings "
            "and prompts raised during the run arrive through get_job. Poll "
            "get_job rather than re-submitting and report the reboot "
            "recommendation it prints at the end. update_system updates the "
            "system; the app itself is updated by update_linuxtoys."
        ),
    }


def _tool_categories():
    translations = _translations()
    categories = []
    for category in parser.get_categories(translations) or []:
        if category.get("is_script"):
            continue
        path = str(category.get("path") or "")
        leaf = os.path.basename(path.rstrip("/")) if path else ""
        categories.append({
            "name": str(category.get("name") or leaf),
            "path": leaf,
        })
    return {"categories": categories}


def _tool_get_app_details(app_id):
    entry = _resolve_entry(app_id)
    if entry is None:
        raise ValueError(f"Unknown app id '{app_id}'. Use search_apps to list valid IDs.")
    return _app_details(entry)


def _tool_get_screenshot(app_id, index=0):
    entry = _resolve_entry(app_id)
    if entry is None:
        raise ValueError(f"Unknown app id '{app_id}'.")
    urls = _screenshot_urls(entry)
    if not urls:
        raise ValueError(f"'{entry.get('name') or app_id}' has no screenshots.")
    try:
        index = int(index)
    except (TypeError, ValueError):
        index = 0
    if not 0 <= index < len(urls):
        raise ValueError(f"Screenshot index out of range: 0..{len(urls) - 1}")
    data, mime = _fetch_screenshot(urls[index])
    return {
        "content": [{
            "type": "image",
            "data": base64.b64encode(data).decode("ascii"),
            "mimeType": mime,
        }],
        "url": urls[index],
    }


def _requires_answers_payload(entry, questions, dynamic_count, branch_skipped=0):
    """Response shape when the agent must ask user questions before a run."""
    payload = {
        "requires_answers": True,
        "app": _stable_id(entry),
        "name": str(entry.get("name") or ""),
        "questions": questions,
        "dynamic_prompts": dynamic_count > 0,
        "dynamic_prompts_note": (
            "This script also contains variable-based prompts the service "
            "cannot preset. If their branch runs, each one is shown live to "
            "the user and logged as a prompt event in get_job."
        ) if dynamic_count else "",
        "branch_filter_note": (
            "Only questions whose branch matches this host are listed "
            "here; other, host-irrelevant call sites were skipped."
        ) if branch_skipped else "",
        "note": (
            "No job was queued yet. Present each question to the user as a "
            "standard agent question (options and suggested default are "
            "listed), then call this tool again with "
            "answers={question id: choice}; choices must match the offered "
            "options exactly (question expects 'yes' or 'no', the "
            "multi-select may also take an array of selections). Every "
            "question id must be covered. Warnings and fatal dialogs of the "
            "run arrive through get_job."
        ),
    }
    if branch_skipped:
        payload["skipped_branches"] = branch_skipped
    return payload


def _tool_install(app_id, answers=None):
    entry = _resolve_entry(app_id)
    if entry is None:
        hint = _extension_parent_hint(app_id)
        if hint:
            raise ValueError(
                f"No installable entry found for '{app_id}'. {hint}"
            )
        raise ValueError(f"No installable entry found for '{app_id}'. Use search_apps to list valid IDs.")
    # Scripts of every installation shape — curated physical scripts,
    # repository-list entries (pipeline + pre/post hooks) and AppStream
    # overlays (`appstream_overrides` hooks) — ask questions through the
    # dialog helpers: surface them first when the agent has not supplied
    # choices yet.
    try:
        questions, dynamic_count, branch_skipped = _agent_dialog_scan_requests(entry)
    except Exception:
        questions, dynamic_count, branch_skipped = [], 0, 0
    if questions and answers is None:
        return _requires_answers_payload(entry, questions, dynamic_count, branch_skipped)
    if answers is not None and not questions:
        raise ValueError(
            "This app's run carries no pre-answerable script questions; "
            "omit answers and queue it directly."
        )
    try:
        records = _agent_records(questions, answers) if answers is not None else None
    except ValueError:
        raise
    try:
        job = JOBS.submit("install", app_id, agent_answer_records=records)
    except ValueError as exc:
        hint = _extension_parent_hint(app_id)
        if hint:
            raise ValueError(f"{exc} {hint}")
        raise
    return {
        "job_id": job.id,
        "name": job.name,
        "state": job.state,
        "note": (
            "The install runs like a normal user install. If it needs root, the "
            "password dialog appears on the user's screen — wait for them to "
            "type it. Poll get_job for the outcome; its warnings list relays "
            "the script dialogs you must tell the user about."
        ),
    }


def _tool_fetch_package_url(url):
    """Download one package file into the private staging directory."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("A package file URL is required.")
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        raise ValueError("Only http(s) URLs can be fetched.")

    name = parts.path.rsplit("/", 1)[-1] if parts.path else ""
    sanitized = "".join(
        char if (char.isalnum() or char in "._-") else "_" for char in name
    ).strip("._")[:120]
    if not sanitized or package_file_kind(sanitized) is None:
        raise ValueError(
            "The URL name does not look like a supported package file. "
            f"Supported package file types: {SUPPORTED_PACKAGE_KINDS_TEXT}"
        )
    target = os.path.join(package_staging_dir(), sanitized)

    request = Request(url, headers={"User-Agent": "LinuxToys MCP"})
    tmp_path = target + ".part"
    try:
        with urlopen(request, timeout=60) as response:
            with open(tmp_path, "wb") as handle:
                received = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > MAX_PACKAGE_DOWNLOAD_BYTES:
                        limit_mib = MAX_PACKAGE_DOWNLOAD_BYTES / (1024 * 1024)
                        limit_text = (
                            f"{limit_mib / 1024:g} GiB"
                            if limit_mib >= 1024
                            else f"{limit_mib:g} MiB"
                        )
                        raise ValueError(
                            "The package file is too large to download (limit: "
                            f"{limit_text})."
                        )
                    handle.write(chunk)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, target)
    except OSError as exc:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise ValueError(f"Could not download the package file: {exc}")
    except ValueError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

    try:
        details = _package_details_payload(target)
    except ValueError:
        details = {"name": sanitized, "kind": package_file_kind(target)}
    details["path"] = target
    details["url"] = url
    # "note" stays the compatibility guard's refusal message when present;
    # the download context goes into its own field.
    details["download_note"] = (
        "Downloaded into LinuxToys' staging directory (cleared with /tmp on "
        "reboot). Inspect it with get_package_file_details before installing."
    )
    return details


def _package_details_payload(path):
    """Metadata + host guards for one package file path, Package View parity."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("A package file path is required.")
    requested = path.strip()
    real = os.path.realpath(os.path.expanduser(requested))
    if not os.path.isfile(real):
        raise ValueError(f"No file found at '{requested}'.")
    kind = package_file_kind(real)
    if kind is None:
        raise ValueError(
            "Unsupported package file type. Supported package file types: "
            + SUPPORTED_PACKAGE_KINDS_TEXT
        )
    metadata = inspect_local_package(real) or {
        "kind": kind,
        "format_label": PACKAGE_KIND_LABELS.get(kind, kind),
        "name": os.path.splitext(os.path.basename(real))[0],
    }
    metadata["path"] = real
    metadata["kind"] = kind
    metadata["format_label"] = PACKAGE_KIND_LABELS.get(kind, kind)
    supported = package_kind_supported_on_host(kind)
    metadata["supported_on_host"] = supported
    if not supported:
        metadata["note"] = (
            "This system does not support this package type, so installing it "
            "is refused — the same guard the GUI applies before opening a "
            "package file."
        )
    return metadata


def _tool_get_package_file_details(path):
    """Inspect one local package file (name, version, host compatibility)."""
    return _package_details_payload(path)


def _tool_install_package_file(path):
    details = _package_details_payload(path)
    if not details.get("supported_on_host"):
        raise ValueError(
            details.get("note") or "This package type is not supported on this system."
        )
    real = details["path"]
    spec = {
        "path": real,
        "kind": details["kind"],
        "name": details["name"],
        "description": details.get("description") or "",
        "signature": package_file_signature(real),
    }
    job = JOBS.submit_file(spec)
    return {
        "job_id": job.id,
        "name": job.name,
        "path": real,
        "kind": details["kind"],
        "state": job.state,
        "note": (
            "The install runs exactly like a package-view install. If it needs "
            "root, the password dialog appears on the user's screen — wait for "
            "them to type it. Poll get_job for the outcome."
        ),
    }


def _tool_list_app_extensions(app_id):
    """Every Flathub extension of one app, with its installed state."""
    entry, records = _flatpak_extension_records(app_id)
    installed = _installed_extension_refs(entry)
    return {
        "app": _app_details(entry),
        "extensions": [
            _extension_record_public(record, installed) for record in records
        ],
    }


def _tool_install_app_extension(app_id, extension):
    entry, records = _flatpak_extension_records(app_id)
    target = _find_app_extension(records, extension)
    job = JOBS.submit_extension(entry, target, remove=False)
    return {
        "job_id": job.id,
        "app": _stable_id(entry),
        "extension": str(target.get("id") or target.get("flatpak_ref")),
        "name": job.name,
        "state": job.state,
        "note": (
            "The extension runs through flatpak like a GUI extension install. "
            "System-scope installs may show a password dialog on the user's "
            "screen. Poll get_job for the outcome; verify with list_app_extensions."
        ),
    }


def _tool_remove_app_extension(app_id, extension):
    entry, records = _flatpak_extension_records(app_id)
    target = _find_app_extension(records, extension)
    job = JOBS.submit_extension(entry, target, remove=True)
    return {
        "job_id": job.id,
        "app": _stable_id(entry),
        "extension": str(target.get("id") or target.get("flatpak_ref")),
        "name": job.name,
        "state": job.state,
        "note": (
            "Removal runs flatpak uninstall for that extension ref. Poll get_job "
            "for the outcome; verify with list_app_extensions."
        ),
    }


def _tool_remove(app_id):
    job = JOBS.submit("remove", app_id)
    return {
        "job_id": job.id,
        "name": job.name,
        "state": job.state,
        "note": "Poll get_job for the outcome.",
    }


def _tool_remove_flatpak_data(app_id):
    """Queue the leftover-data cleanup of one uninstalled Flatpak app."""
    entry = _resolve_entry(app_id)
    if entry is None:
        raise ValueError(f"Unknown app id '{app_id}'. Use search_apps to list valid IDs.")
    # Validates flatpak source, safe ~/.var/app/<AppID> mapping and the
    # uninstalled state — the same reasons the app page hides its button.
    identity, target = _flatpak_data_blueprint(entry)
    if not flatpak_residue.residual_data_present(target):
        raise ValueError(
            f"No leftover user data found for '{entry.get('name') or identity}' "
            f"at '{target}' — nothing to remove."
        )
    try:
        job = JOBS.submit_flatpak_data(entry)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not queue the data removal: {exc}")
    return {
        "job_id": job.id,
        "app": _stable_id(entry),
        "name": job.name,
        "path": str(target),
        "state": job.state,
        "note": (
            "The removal is confined to the user's home and needs no password. "
            "Poll get_job; get_app_details afterwards reports "
            "flatpak_residual_data false."
        ),
    }


def _tool_get_job(job_id, tail_lines=40):
    job = JOBS.get(job_id)
    if job is None:
        raise ValueError(f"Unknown or expired job id '{job_id}'. Jobs reset when the service restarts.")
    payload = job.public(tail=tail_lines)
    warnings, prompts, errors = _read_agent_events(job.agent_event_dir)
    payload["warnings"] = warnings
    payload["live_prompts"] = prompts
    if errors:
        payload["error_detail"] = errors[-1]
    if warnings:
        payload["warning_note"] = (
            "These warnings were raised by the script's dialog layer and do "
            "not (by themselves) mean the run failed: convey each of them to "
            "the user as an attention-required message, even while `state` is "
            "still running or the run later succeeds. A failure looks "
            "different here: `state` is `error` and the fatal dialog text "
            "arrives in error_detail."
        )
    if prompts:
        payload["prompt_note"] = (
            "These script dialogs could not be pre-asked, so they were shown "
            "to the user live on screen (they may include questions the "
            "agent cannot preset); relay what was asked and answered."
        )
    return payload


def _tool_list_jobs(limit=20):
    return {"jobs": JOBS.snapshot(limit)}


def _tool_get_settings():
    status = service_status()
    return {
        "automatic_updates": get_automatic_updates(),
        "automatic_bug_reports": get_automatic_error_reports(),
        "language": get_saved_language() or detect_system_language(),
        "available_languages": get_available_languages(),
        "mcp_service": status,
        "mcp_endpoint": _endpoint_url(),
    }


def _tool_set_settings(automatic_updates=None, automatic_bug_reports=None, language=None):
    applied = {}
    rejected = {}
    if automatic_updates is not None:
        save_automatic_updates(bool(automatic_updates))
        applied["automatic_updates"] = bool(automatic_updates)
    if automatic_bug_reports is not None:
        save_automatic_error_reports(bool(automatic_bug_reports))
        applied["automatic_bug_reports"] = bool(automatic_bug_reports)
    if language is not None:
        code = str(language).strip().casefold()
        available = get_available_languages()
        if code in available:
            save_language(code)
            applied["language"] = code
        else:
            rejected["language"] = available
    result = {"applied": applied, "note": "A running GUI applies the new language on its next launch."}
    if rejected:
        result["rejected"] = rejected
    return result


def _tool_translate_text(text, target_language=None):
    target = str(target_language or "").strip() or detect_system_language()
    target = translate_helper.normalized_language(target)
    if not target:
        target = "en"
    translated = translate_helper.translate_text(text, target)
    return {"translated_text": translated, "target_language": target}


def _tool_translate_app_description(app_id, target_language=None):
    entry = _resolve_entry(app_id)
    if entry is None:
        raise ValueError(f"Unknown app id '{app_id}'.")
    details = _app_details(entry)
    target = str(target_language or "").strip() or detect_system_language()
    target = translate_helper.normalized_language(target) or "en"

    blocks = details.get("description_blocks") or []
    if not blocks:
        source_text = details.get("long_description") or details.get("summary") or details.get("description") or ""
        if not source_text.strip():
            return {"translated_text": "", "target_language": target, "note": "The app has no description."}
        translated = translate_helper.translate_text(source_text, target)
        return {"translated_text": translated, "target_language": target}

    app_id_stable = details["id"]
    cached = translate_helper.load_cached_description_translation(app_id_stable, blocks, target)
    if cached is not None:
        return {
            "translated_text": _blocks_to_text(cached),
            "description_blocks": cached,
            "target_language": target,
            "cached": True,
        }
    translated_blocks = translate_helper.translate_blocks(blocks, target)
    translate_helper.save_cached_description_translation(app_id_stable, blocks, translated_blocks, target)
    return {
        "translated_text": _blocks_to_text(translated_blocks),
        "description_blocks": translated_blocks,
        "target_language": target,
        "cached": False,
    }


def _tool_get_registry_entries(query=None, limit=50):
    registry_data = registry_utils.parse_registry_file()
    query = str(query or "").strip().casefold()
    entries = []
    for name, transactions in registry_data.items():
        if query and not (
            query in name.casefold()
            or any(query in op.casefold() for _ts, ops in transactions for op in ops)
        ):
            continue
        entries.append({
            "name": name,
            "transactions": [
                {"timestamp": timestamp, "operations": list(operations)}
                for timestamp, operations in transactions
            ],
        })
        if len(entries) >= max(1, int(limit)):
            break
    return {"entries": entries}


def _tool_export_registry_manifest(destination=None):
    translations = _translations()
    manifest_path, entry_count = manifest_helper.export_registered_manifest(
        output_path=destination or None,
        translations=translations,
    )
    return {
        "path": manifest_path,
        "entries": entry_count,
        "note": "Replay on another machine with: linuxtoys --manifest <file>",
    }


def _tool_open_support_link(app_id, kind, index=0):
    entry = _resolve_entry(app_id)
    if entry is None:
        raise ValueError(f"Unknown app id '{app_id}'.")
    details = _app_details(entry)
    links = details.get("links") or {}
    kind = str(kind or "").strip()
    try:
        index = int(index)
    except (TypeError, ValueError):
        index = 0

    url = ""
    if kind == "homepage":
        url = links.get("homepage", "")
    elif kind == "donate":
        url = links.get("donate", "")
    elif kind == "purchase":
        url = links.get("purchase", "")
    elif kind == "purchase_option":
        options = links.get("purchase_options") or []
        if not options:
            raise ValueError(f"'{details['name']}' has no purchase options.")
        if not 0 <= index < len(options):
            raise ValueError(f"purchase_option index out of range: 0..{len(options) - 1}")
        url = options[index].get("url") or ""
    elif kind == "subscription":
        options = links.get("subscription_options") or []
        if not options:
            raise ValueError(f"'{details['name']}' has no subscription options.")
        if not 0 <= index < len(options):
            raise ValueError(f"subscription index out of range: 0..{len(options) - 1}")
        url = options[index].get("url") or ""
    else:
        raise ValueError("kind must be homepage, donate, purchase, purchase_option or subscription")

    if not url:
        raise ValueError(f"'{details['name']}' has no {kind} link.")
    if not re.match(r"^https?://", url):
        raise ValueError("Refusing to open a non-http(s) link.")
    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise ValueError(f"Could not open the link: {exc}")
    return {"opened": url, "kind": kind, "app": details["name"]}


def dispatch_tool(name, arguments):
    """Run one tool; returns the result dict (may raise ValueError)."""
    arguments = arguments if isinstance(arguments, dict) else {}
    if name == "server_info":
        return _tool_server_info()
    if name == "list_categories":
        return _tool_categories()
    if name == "get_update_status":
        return _tool_get_update_status()
    if name == "update_linuxtoys":
        return _tool_update_linuxtoys()
    if name == "update_system":
        return _tool_update_system(arguments.get("answers"))
    if name == "search_apps":
        return {"results": _search_catalog(arguments.get("query"), arguments.get("limit", 20))}
    if name == "get_app_details":
        return _tool_get_app_details(arguments.get("app_id"))
    if name == "get_screenshot":
        return _tool_get_screenshot(arguments.get("app_id"), arguments.get("index", 0))
    if name == "install_app":
        return _tool_install(arguments.get("app_id"), arguments.get("answers"))
    if name == "fetch_package_url":
        return _tool_fetch_package_url(arguments.get("url"))
    if name == "get_package_file_details":
        return _tool_get_package_file_details(arguments.get("path"))
    if name == "install_package_file":
        return _tool_install_package_file(arguments.get("path"))
    if name == "install_app_extension":
        return _tool_install_app_extension(
            arguments.get("app_id"), arguments.get("extension")
        )
    if name == "remove_app_extension":
        return _tool_remove_app_extension(
            arguments.get("app_id"), arguments.get("extension")
        )
    if name == "list_app_extensions":
        return _tool_list_app_extensions(arguments.get("app_id"))
    if name == "remove_app":
        return _tool_remove(arguments.get("app_id"))
    if name == "remove_flatpak_data":
        return _tool_remove_flatpak_data(arguments.get("app_id"))
    if name == "get_job":
        return _tool_get_job(arguments.get("job_id"), arguments.get("tail_lines", 40))
    if name == "list_jobs":
        return _tool_list_jobs(arguments.get("limit", 20))
    if name == "get_settings":
        return _tool_get_settings()
    if name == "set_settings":
        return _tool_set_settings(
            arguments.get("automatic_updates"),
            arguments.get("automatic_bug_reports"),
            arguments.get("language"),
        )
    if name == "translate_text":
        return _tool_translate_text(arguments.get("text"), arguments.get("target_language"))
    if name == "translate_app_description":
        return _tool_translate_app_description(
            arguments.get("app_id"), arguments.get("target_language")
        )
    if name == "get_registry_entries":
        return _tool_get_registry_entries(arguments.get("query"), arguments.get("limit", 50))
    if name == "export_registry_manifest":
        return _tool_export_registry_manifest(arguments.get("destination"))
    if name == "open_support_link":
        return _tool_open_support_link(
            arguments.get("app_id"), arguments.get("kind"), arguments.get("index", 0)
        )
    raise KeyError(name)


# ---------------------------------------------------------------------------
# JSON-RPC over Streamable HTTP
# ---------------------------------------------------------------------------

class SessionStore:
    def __init__(self):
        self._sessions = {}
        self._lock = threading.Lock()

    def create(self):
        session = uuid.uuid4().hex
        with self._lock:
            self._prune_locked()
            self._sessions[session] = time.time()
        return session

    def validate(self, session):
        with self._lock:
            return bool(session) and session in self._sessions

    def drop(self, session):
        with self._lock:
            return self._sessions.pop(session, None) is not None

    def _prune_locked(self):
        deadline = time.time() - SESSION_IDLE_TTL
        for session in [s for s, seen in self._sessions.items() if seen < deadline]:
            self._sessions.pop(session, None)


SESSIONS = SessionStore()


def _jsonrpc_result(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id, code, message, data=None):
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _initialize_result(requested_version):
    version = str(requested_version or PROTOCOL_VERSION)
    if version not in SUPPORTED_PROTOCOL_VERSIONS:
        version = PROTOCOL_VERSION
    return {
        "protocolVersion": version,
        "capabilities": {
            "tools": {"listChanged": False},
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "title": "LinuxToys",
            "version": __version__,
        },
        "instructions": (
            "LinuxToys is a cross-distro app manager. Typical flow: search_apps "
            "-> get_app_details -> install_app, then poll get_job. A local or "
            "downloaded package file (.deb, .rpm, .appimage, ...) can be "
            "installed the same guarded way: get_package_file_details -> "
            "install_package_file, with fetch_package_url for downloads. "
            "Flathub apps may offer extensions/addons: when get_app_details "
            "reports extensions_available, use list_app_extensions / "
            "install_app_extension / remove_app_extension. Uninstalled "
            "Flatpak apps can leave leftover user data under ~/.var/app: "
            "get_app_details reports it as flatpak_residual_data, and "
            "remove_flatpak_data removes it as a tracked job once the user "
            "confirms — it always refuses apps that are still installed. "
            "Scripts can ask questions: install_app/update_system answer "
            "requires_answers first; show every listed question (options "
            "and default provided) to the user through your own question "
            "UI, then re-call the tool with answers={id: choice}. During "
            "any run get_job relays the script dialogs: warnings are "
            "attention-required messages to convey promptly (they do not "
            "mean failure), live_prompts are dialogs the user answered on "
            "screen, and error_detail carries the fatal message of a "
            "failed run. Installs that need root show the password dialog "
            "on the user's screen; never ask the user to hand you "
            "credentials. Descriptions "
            "and screenshots can be read and translated with translate_text / "
            "translate_app_description. The app updates itself: "
            "get_update_status, then update_linuxtoys with the user's "
            "approval (poll get_job and restart the linuxtoys-mcp service "
            "afterwards). The full system update is separate: "
            "update_system runs the app's own 'Update System' script "
            "after user approval — refused while the app version is too "
            "far behind, like any LinuxToys script run. When install_app "
            "or remove_app is refused because the installed version is "
            "too far behind the newest release, update LinuxToys first — "
            "package installs keep working."
        ),
    }


def handle_jsonrpc(message):
    """Process one JSON-RPC message dict; returns a response dict or None."""
    if not isinstance(message, dict):
        return _jsonrpc_error(None, -32600, "Invalid Request: expected a JSON object")
    request_id = message.get("id")
    method = message.get("method")

    if message.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return _jsonrpc_error(request_id, -32600, "Invalid Request: missing jsonrpc/method")

    if method == "initialize":
        params = message.get("params") or {}
        return _jsonrpc_result(request_id, _initialize_result(params.get("protocolVersion")))

    if method == "ping":
        return _jsonrpc_result(request_id, {})

    if method.startswith("notifications/"):
        return None  # Notifications get no body; the HTTP layer answers 202.

    if method == "tools/list":
        return _jsonrpc_result(request_id, {"tools": tool_schemas()})

    if method == "tools/call":
        params = message.get("params") or {}
        name = str(params.get("name") or "")
        if not name:
            return _jsonrpc_error(request_id, -32602, "Invalid params: missing tool name")
        try:
            result = dispatch_tool(name, params.get("arguments"))
        except KeyError:
            return _jsonrpc_error(request_id, -32602, f"Unknown tool: {name}")
        except (ValueError, KeyError, TypeError) as exc:
            return _jsonrpc_result(request_id, {
                "content": [{"type": "text", "text": f"Error: {exc}"}],
                "isError": True,
            })
        except Exception as exc:
            return _jsonrpc_result(request_id, {
                "content": [{"type": "text", "text": f"Internal error: {exc}"}],
                "isError": True,
            })
        if isinstance(result, dict) and "content" in result:
            payload = result
        else:
            payload = {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
        payload.setdefault("isError", False)
        return _jsonrpc_result(request_id, payload)

    return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")


class MCPRequestHandler(BaseHTTPRequestHandler):
    server_version = f"LinuxToysMCP/{__version__}"
    protocol_version = "HTTP/1.1"

    # -- helpers ------------------------------------------------------------

    def _origin_allowed(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parts = urlsplit(origin)
        host = (parts.hostname or "").casefold()
        return host in ("127.0.0.1", "localhost", "::1") or host == _local_hostname()

    def _authorized(self):
        header = self.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            if token_matches(header[7:]):
                return True
        if token_matches(self.headers.get("X-LinuxToys-Token", "")):
            return True
        return False

    def _send_json(self, payload, status=200, extra_headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def _session_from_headers(self):
        return self.headers.get("Mcp-Session-Id", "").strip()

    # -- verbs --------------------------------------------------------------

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            self._send_json({
                "status": "ok",
                "server": SERVER_NAME,
                "version": __version__,
                "mcp_endpoint": _endpoint_url(),
            })
            return
        if path == "/mcp":
            # Server-initiated SSE streams are not offered.
            self._send_empty(405, {"Allow": "POST, DELETE"})
            return
        self._send_json(_jsonrpc_error(None, -32601, "Unknown path"), 404)

    def do_DELETE(self):
        if urlsplit(self.path).path != "/mcp":
            self._send_json(_jsonrpc_error(None, -32601, "Unknown path"), 404)
            return
        if not self._authorized():
            self._send_json(_jsonrpc_error(None, -32001, "Unauthorized"), 401)
            return
        session = self._session_from_headers()
        if session and SESSIONS.drop(session):
            self._send_empty(204)
        else:
            self._send_empty(204)

    def do_POST(self):
        if urlsplit(self.path).path != "/mcp":
            self._send_json(_jsonrpc_error(None, -32601, "Unknown path"), 404)
            return
        if not self._origin_allowed():
            self._send_json(_jsonrpc_error(None, -32001, "Origin not allowed"), 403)
            return
        if not self._authorized():
            self._send_json(
                _jsonrpc_error(
                    None, -32001,
                    "Unauthorized: pass the MCP token as 'Authorization: Bearer <token>' "
                    "or 'X-LinuxToys-Token: <token>'. The token is at "
                    "~/.config/linuxtoys/mcp-token.",
                ),
                401,
            )
            return

        content_type = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type != "application/json":
            self._send_json(
                _jsonrpc_error(None, -32700, "Content-Type must be application/json"),
                415,
            )
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(_jsonrpc_error(None, -32700, "Invalid request body size"), 400)
            return
        try:
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            self._send_json(_jsonrpc_error(None, -32700, f"Parse error: {exc}"), 400)
            return

        method_name = ""
        if isinstance(payload, dict):
            method_name = str(payload.get("method") or "")
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("method") == "initialize":
                    method_name = "initialize"
                    break

        session = self._session_from_headers()
        if method_name == "initialize":
            session = SESSIONS.create()
        elif method_name == "ping" and not session:
            pass  # Health probes may ping before a session exists.
        elif session and not SESSIONS.validate(session):
            self._send_json(
                _jsonrpc_error(None, -32001, "Unknown session — re-initialize"), 404,
                {"Mcp-Session-Id": session},
            )
            return
        elif not session:
            self._send_json(
                _jsonrpc_error(
                    None, -32001,
                    "Missing Mcp-Session-Id header — initialize first",
                ),
                400,
            )
            return

        if isinstance(payload, list):
            responses = [
                response
                for response in (handle_jsonrpc(item) for item in payload)
                if response is not None
            ]
        else:
            responses = handle_jsonrpc(payload)
            responses = [responses] if responses is not None else []

        if not responses:
            self._send_empty(202, {"Mcp-Session-Id": session} if session else None)
            return

        if len(responses) == 1:
            self._send_json(responses[0], 200, {"Mcp-Session-Id": session} if session else None)
        else:
            self._send_json(responses, 200, {"Mcp-Session-Id": session} if session else None)

    def log_message(self, fmt, *args):
        if os.environ.get("LT_DEBUG") == "1":
            sys.stderr.write("MCP: " + fmt % args + "\n")


def _local_hostname():
    return "localhost"


def _endpoint_url():
    return f"http://127.0.0.1:{get_mcp_server_port()}/mcp"


# ---------------------------------------------------------------------------
# systemd user service management
# ---------------------------------------------------------------------------

SESSION_ENV_KEYS = (
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "XAUTHORITY",
    "DBUS_SESSION_BUS_ADDRESS",
    "GDK_BACKEND",
    "XDG_CURRENT_DESKTOP",
)

EMBEDDED_UNIT_TEMPLATE = """[Unit]
Description=LinuxToys MCP Agent Server
Documentation=https://linux.toys
PartOf=graphical-session.target
After=graphical-session.target

[Service]
Type=simple
ExecStart=@EXEC_START@
Restart=on-failure
RestartSec=5s
@ENVIRONMENT_LINES@
[Install]
WantedBy=graphical-session.target
"""


def user_unit_dir():
    return os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
        "systemd", "user",
    )


def user_unit_path():
    return os.path.join(user_unit_dir(), UNIT_FILE_NAME)


def bundled_unit_path():
    for candidate in (
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "systemd", UNIT_FILE_NAME),
    ):
        if os.path.isfile(candidate):
            return candidate
    return ""


def _exec_start():
    """ExecStart resolved for this installation kind.

    Points at the running app's own tree: AppImage installs re-execute the
    AppImage itself (so the mount is fresh), everything else runs this
    installation's linuxtoys.py directly — a dev checkout gets its own entry,
    never the system package's.
    """
    appimage = os.environ.get("APPIMAGE")
    if appimage and os.path.isfile(appimage):
        return f"{appimage} --mcp"
    script_dir = os.environ.get("SCRIPT_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    entry = os.path.join(script_dir, "linuxtoys.py")
    python = sys.executable or "/usr/bin/python3"
    return f"{python} {entry} --mcp"


def build_unit_text(session_env=None):
    """Render the user unit, baking the graphical session env for askpass.

    Prefers the shipped template (p3/systemd/linuxtoys-mcp.service) and falls
    back to the embedded copy so the server keeps working even if the file is
    missing from an installation.
    """
    session_env = session_env if session_env is not None else os.environ
    environment_lines = []
    for key in SESSION_ENV_KEYS:
        value = str(session_env.get(key) or "").strip()
        if value and "\n" not in value:
            environment_lines.append(f'Environment="{key}={value}"')

    template = EMBEDDED_UNIT_TEMPLATE
    bundled = bundled_unit_path()
    if bundled:
        try:
            with open(bundled, "r", encoding="utf-8") as handle:
                template = handle.read()
        except OSError:
            template = EMBEDDED_UNIT_TEMPLATE

    text = template.replace(
        "@EXEC_START@", _exec_start()
    ).replace(
        "@ENVIRONMENT_LINES@",
        "\n".join(environment_lines) + "\n" if environment_lines else "",
    )
    return text


def _systemctl(*args):
    if not shutil.which("systemctl"):
        return None, "systemctl is not available on this system."
    try:
        result = subprocess.run(
            ["systemctl", "--user", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"systemctl failed: {exc}"
    if result.returncode != 0:
        return None, (result.stderr or result.stdout or "systemctl failed").strip()
    return (result.stdout or "").strip(), ""


def install_service_unit(session_env=None):
    """Install (or refresh) the user unit; no root required."""
    unit_dir = user_unit_dir()
    os.makedirs(unit_dir, exist_ok=True)
    text = build_unit_text(session_env)
    path = user_unit_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)
    output, error = _systemctl("daemon-reload")
    if error:
        return False, error
    return True, path


def enable_service(session_env=None):
    ensure_token()
    installed, message = install_service_unit(session_env)
    if not installed:
        return False, message
    _output, error = _systemctl("enable", "--now", UNIT_FILE_NAME)
    if error:
        return False, error
    return True, f"MCP server enabled at {_endpoint_url()}"


def disable_service():
    _output, error = _systemctl("disable", "--now", UNIT_FILE_NAME)
    # Missing/not-installed units are fine when disabling.
    if error and "not found" not in error and "Failed to disable" not in error:
        return False, error
    return True, "MCP server disabled."


def service_status():
    status = {"installed": os.path.exists(user_unit_path()), "enabled": False, "active": False, "available": True}
    if not shutil.which("systemctl"):
        status["available"] = False
        return status
    output, error = _systemctl("is-enabled", UNIT_FILE_NAME)
    status["enabled"] = bool(output) and output.strip() in ("enabled", "enabled-runtime", "static", "linked")
    output, _error = _systemctl("is-active", UNIT_FILE_NAME)
    status["active"] = bool(output) and output.strip() == "active"
    if error and "not found" in error:
        status["installed"] = False
    return status


def apply_service_state(enabled, session_env=None):
    """Apply the header toggle. Returns (ok, message)."""
    if enabled:
        return enable_service(session_env)
    return disable_service()


def install_agent_skill():
    """Best-effort OFFLINE install of the bundled LinuxToys MCP skill.

    Fallback for when the primary path (``bun x skills add``, run through the
    AppStream runner's hidden PTY) is unavailable — no bun/bunx on PATH or
    every fetch source failed. Reads the bundled copy of the skill
    (``app/mcp_skill/SKILL.md``), which every distribution method packages.

    Returns a list of paths the skill was written to (may be empty).
    """
    home = os.path.expanduser("~")
    skill_root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mcp_skill"
    )
    skill_file = os.path.join(skill_root, "SKILL.md")
    if not os.path.isfile(skill_file):
        return []

    targets = [
        (".agents", "skills"),               # cross-agent convention (skills.sh)
        (".claude", "skills"),
        (".config", "opencode", "skill"),
        (".codex", "skills"),
        (".cursor", "skills"),
        (".windsurf", "skills"),
        (".gemini", "skills"),
    ]
    installed = []
    for parts in targets:
        agent_dir = os.path.join(home, *parts[:-1])
        if not os.path.isdir(agent_dir):
            continue
        destination = os.path.join(home, *parts, "linuxtoys-mcp")
        try:
            os.makedirs(destination, exist_ok=True)
            with open(skill_file, "r", encoding="utf-8") as source:
                content = source.read()
            with open(os.path.join(destination, "SKILL.md"), "w", encoding="utf-8") as handle:
                handle.write(content)
            installed.append(destination)
        except OSError:
            continue
    return installed


# The canonical, fetchable copy of the agent skill lives at the standard
# repository location the `skills` CLI (skills.sh) reads from a git checkout:
# skills/linuxtoys-mcp/SKILL.md at the repository root. It must be kept in
# sync with the bundled fallback copy at app/mcp_skill/SKILL.md (same commit).
SKILL_REPO_URLS = (
    "https://github.com/psygreg/linuxtoys",
    "https://git.linux.toys/psygreg/linuxtoys",  # Gitea mirror fallback
)
SKILL_NAME = "linuxtoys-mcp"
SKILL_INSTALL_TIMEOUT = 180


def skill_install_script():
    """Build the noninteractive skill-installation script.

    Returned as text; the caller (AppStream runner) writes it to a temporary
    file and dispatches it through the hidden PTY. Prompt-free by design,
    because the hidden PTY has nobody to answer questions:

    - ``bun x`` never prompts for package installation (unlike npx), and
      ``CI=1`` additionally tells CLIs to assume a noninteractive environment.
    - The skills CLI skips all confirmations with ``-y``; an explicit
      ``--skill`` prevents the skill picker, and NO ``--agent`` keeps the
      CLI on its default target (every detected agent plus the universal
      ``~/.agents/skills`` directory) — passing ``--agent`` together with
      ``-yg`` is what triggers its interactive scope prompt (upstream
      issue #793).
    - ``timeout`` bounds a hypothetical prompt nobody answers: the first
      source gets one budget, the mirror gets another, and the offline
      bundled copy is the last resort.
    """
    script = """#!/usr/bin/env bash
# Install the LinuxToys MCP agent skill for detected agents (noninteractive).
set -u

_lt_skill_cmd=()
if command -v bun >/dev/null 2>&1; then
    _lt_skill_cmd=(bun x skills)
elif [ -x "$HOME/.bun/bin/bun" ]; then
    _lt_skill_cmd=("$HOME/.bun/bin/bun" x skills)
fi

_lt_try() {
    # --foreground: without it timeout puts the CLI in a background process
    # group, so bun's TTY I/O raises SIGTTIN/SIGTTOU and the process stops
    # forever (TERM cannot reach stopped children, defeating even this bound).
    timeout --foreground %d env CI=1 "${_lt_skill_cmd[@]}" add "$1" --skill %s -g -y
}

_lt_status=1
if [ "${#_lt_skill_cmd[@]}" -gt 0 ]; then
    for _lt_repo in %s; do
        if _lt_try "$_lt_repo"; then
            _lt_status=0
            break
        fi
        echo "Skill source failed: $_lt_repo"
    done
else
    echo "bun/bunx not found; using the bundled skill copy."
fi

if [ "$_lt_status" != "0" ]; then
    python3 "$SCRIPT_DIR/app/mcp_server.py" --install-skill
fi
""" % (
        SKILL_INSTALL_TIMEOUT,
        SKILL_NAME,
        " ".join(shlex_quote(url) for url in SKILL_REPO_URLS),
    )
    return script


# ---------------------------------------------------------------------------
# Server bootstrap
# ---------------------------------------------------------------------------

def _background_warmup():
    """Best-effort startup work: scripts sync and AppStream catalog refresh."""
    try:
        from .scripts_loader import initialize_scripts
        initialize_scripts()
    except Exception:
        pass
    try:
        parser.set_scripts_dir(parser.SCRIPTS_DIR)
    except Exception:
        pass
    # Warm the outdated-version gate cache so install_app/remove_app and the
    # status tool have release data ready (the check itself fails open).
    try:
        from .updater import version_gate
        version_gate.refresh()
    except Exception:
        pass
    try:
        if appstream_cache.cache_needs_refresh():
            appstream_cache.refresh_cache()
    except Exception:
        pass
    # Publish a current derived catalog generation built with the FULL context
    # (curated entries + category paths). When the persisted generation already
    # matches, the Rust builder early-returns; when it is stale (or was last
    # built by a caller with an incomplete context) this rebuilds it correctly.
    try:
        scripts_dir, curated_entries, category_paths = _appstream_context()
        appstream_parser._runtime_catalog(
            scripts_dir,
            curated_entries=curated_entries,
            category_paths=category_paths,
            force_rebuild=True,
        )
    except Exception:
        pass


def run_service():
    """Run the MCP server in the foreground (used by `linuxtoys --mcp`)."""
    port = get_mcp_server_port()
    ensure_token()

    threading.Thread(target=_background_warmup, daemon=True, name="linuxtoys-mcp-warmup").start()

    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), MCPRequestHandler)
    except OSError as exc:
        print(
            f"Error: could not start the LinuxToys MCP server on 127.0.0.1:{port}: {exc}\n"
            "Is another instance already running? Check: systemctl --user status linuxtoys-mcp.service",
            file=sys.stderr,
        )
        return 1

    server.daemon_threads = True
    _TRANSIENT_SERVER["server"] = server
    _TRANSIENT_SERVER["started"] = time.time()

    print(
        f"LinuxToys MCP server v{__version__} listening on http://127.0.0.1:{port}/mcp\n"
        f"Auth token: {token_path()}\n"
        "Press Ctrl+C to stop."
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        JOBS.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    if "--install-skill" in sys.argv:
        # Non-package fallback used by the skill-install job when the bun
        # fetch path is unavailable: copy the bundled skill directly.
        installed = install_agent_skill()
        if installed:
            print("LinuxToys MCP skill installed to:")
            for path in installed:
                print(f"  {path}")
            sys.exit(0)
        print("No supported agent skill directory was found on this system.", file=sys.stderr)
        sys.exit(1)
    sys.exit(run_service())
