#!/usr/bin/env python3
"""Small CLI bridge between the Bash Nix helpers and ``nix_extensions``.

The extension selection and rendering live in Python, while ``nixsys.bash``
owns module publication (user vs root-owned system files) and rebuilds. This
script keeps the shell free of JSON/Nix rendering and imports the application
package once per invocation.

Commands (stdout is machine-readable; diagnostics go to stderr):

``hosts <module>``
    Print one host attribute per line for the module's recorded selection.

``pairs <module>``
    Print ``host<TAB>plugin`` lines; used by the registry sync.

``installed``
    Print the current extension host state as JSON.

``apply <scope> <module> <queue> <output>``
    Apply this scope's queued extension operations, then render the module to
    ``output``. Nothing is published by this script; the shell does that.

``empty <scope>``
    Print an empty extension module (used before the first selection).

``remove-hosts <scope> <module> <output> <host>...``
    Drop entire host entries (used by ``nix_remove_packages``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
P3_DIR = APP_DIR.parent
if str(P3_DIR) not in sys.path:
    sys.path.insert(0, str(P3_DIR))

from app import nix_extensions  # noqa: E402


def command_hosts(arguments):
    if len(arguments) != 1:
        print("hosts requires exactly one module path.", file=sys.stderr)
        return 2
    for host in sorted(nix_extensions.read_state(arguments[0])):
        print(host)
    return 0


def command_pairs(arguments):
    if len(arguments) != 1:
        print("pairs requires exactly one module path.", file=sys.stderr)
        return 2
    for host, entry in sorted(nix_extensions.read_state(arguments[0]).items()):
        for plugin_attr in entry["plugins"]:
            print(f"{host}\t{plugin_attr}")
    return 0


def command_installed(_arguments):
    print(
        json.dumps(
            {
                scope: sorted(nix_extensions.installed_hosts(scope))
                for scope in ("home-manager", "system")
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0


def command_apply(arguments):
    if len(arguments) != 4:
        print(
            "apply requires <scope> <module> <queue> <output>.",
            file=sys.stderr,
        )
        return 2
    try:
        _state, _changed, warnings = nix_extensions.apply_queue(*arguments)
    except (OSError, ValueError) as error:
        print(f"Nix extensions: {error}", file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"Nix extensions: {warning}", file=sys.stderr)
    return 0


def command_empty(arguments):
    if len(arguments) != 1 or arguments[0] not in ("home-manager", "system"):
        print("empty requires a home-manager or system scope.", file=sys.stderr)
        return 2
    sys.stdout.write(nix_extensions.empty_module(arguments[0]))
    return 0


def command_remove_hosts(arguments):
    if len(arguments) < 4:
        print(
            "remove-hosts requires <scope> <module> <output> <host>...",
            file=sys.stderr,
        )
        return 2
    scope, module, output, *hosts = arguments
    try:
        changed = nix_extensions.remove_hosts(scope, module, hosts, output)
    except (OSError, ValueError) as error:
        print(f"Nix extensions: {error}", file=sys.stderr)
        return 1
    print("1" if changed else "0")
    return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    command = argv[1]
    arguments = argv[2:]
    try:
        if command == "hosts":
            return command_hosts(arguments)
        if command == "pairs":
            return command_pairs(arguments)
        if command == "installed":
            return command_installed(arguments)
        if command == "apply":
            return command_apply(arguments)
        if command == "empty":
            return command_empty(arguments)
        if command == "remove-hosts":
            return command_remove_hosts(arguments)
        print(f"Unknown command: {command}", file=sys.stderr)
        return 2
    except Exception as error:  # Never leave the shell without a reason.
        print(f"Could not update Nix extension state: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
