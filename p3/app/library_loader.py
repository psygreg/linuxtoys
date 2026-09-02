"""Detect Bash library requirements without executing the inspected code."""

import os
from pathlib import Path
import re
import shlex

LIBRARY_FLAGS = {
    "fsops.bash": "FS_OPS",
    "packages.bash": "PACKAGE_OPS",
    "boot.bash": "BOOT_OPS",
    "misc.bash": "MISC_OPS",
    "sysd.bash": "SYSD_OPS",
}
_FUNCTION = re.compile(
    r"^\s*(?:function\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(\s*\))?"
    r"|([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\))\s*\{", re.MULTILINE
)
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _words(text):
    # Keep quoted words: callbacks and commands in substitutions/strings may
    # name library functions too. This intentionally errs toward loading more.
    return set(_WORD.findall(re.sub(r"(?m)^\s*#.*$", "", text)))


def library_flags(script_text, script_dir):
    """Return flags for direct references and transitive library dependencies.

    This is conservative static detection, not a Bash parser. Computed function
    names cannot be inferred; scripts can still explicitly set an *_OPS flag
    and source linuxtoys.bash for those cases.
    """
    libs = Path(script_dir) / "libs"
    texts = {name: (libs / name).read_text(encoding="utf-8")
             for name in LIBRARY_FLAGS}
    functions = {
        name: {first or second for first, second in _FUNCTION.findall(text)}
        for name, text in texts.items()
    }
    required = _words(script_text)
    # Core functions (notably init_transmap -> prep_tmp) need dependencies too.
    for name in ("linuxtoys.bash", "sysinfo.bash"):
        required.update(_words((libs / name).read_text(encoding="utf-8")))

    # These explicitly summoned libraries may also call the split modules.
    for function, filename in (("summon_helpers", "helpers.lib"),
                               ("summon_optimizers", "optimizers.lib")):
        if function in _words(script_text) and (libs / filename).is_file():
            required.update(_words((libs / filename).read_text(encoding="utf-8")))

    selected = set()
    while True:
        added = {name for name in texts if name not in selected
                 and functions[name] & required}
        if not added:
            break
        selected.update(added)
        for name in added:
            required.update(_words(texts[name]))
    return {flag: "1" if name in selected else ""
            for name, flag in LIBRARY_FLAGS.items()}


def script_preamble(script_text, script_dir):
    """Set invocation-local flags and always load the core before script code."""
    script_dir = os.path.abspath(script_dir)
    flags = library_flags(script_text, script_dir)
    lines = ["export SCRIPT_DIR=" + shlex.quote(script_dir)]
    lines.extend("export " + key + "=" + shlex.quote(value)
                 for key, value in flags.items())
    lines.append("source " + shlex.quote(str(Path(script_dir) / "libs/linuxtoys.bash"))
                 + " || exit $?")
    return "\n".join(lines) + "\n"


def script_command(script_path, script_dir):
    """Build argv without interpolating the script path into shell code.

    $0 and BASH_SOURCE continue to identify the original script; the final
    source command propagates its return/exit status.
    """
    script_path = os.path.abspath(script_path)
    text = Path(script_path).read_text(encoding="utf-8")
    return ["/bin/bash", "-c", script_preamble(text, script_dir)
            + 'source "$0" "$@"\n', script_path]


if __name__ == "__main__":
    # call_script uses this entry point for nested scripts. exec preserves the
    # child's exit status and lets the existing Bash caller manage transactions.
    import sys

    if len(sys.argv) < 2:
        sys.exit("Usage: script_libraries.py SCRIPT [ARG ...]")
    command = script_command(sys.argv[1], os.environ["SCRIPT_DIR"])
    os.execv(command[0], command + sys.argv[2:])
