#!/usr/bin/env python3
"""Small CLI bridge between the Bash Nix helpers and ``nix_services``.

The service selection and rendering live in Python, while ``nixsys.bash`` owns
module publication (user vs root-owned system files) and rebuilds. This script
keeps the shell free of JSON/Nix rendering and imports the application package
once per invocation.

Commands (stdout is machine-readable; diagnostics go to stderr):

``services <module>``
    Print one installed service attribute per line.

``installed``
    Print the current service state as JSON.

``apply <scope> <module> <queue> <output>``
    Apply this scope's queued service operations, then render the module to
    ``output``. Nothing is published by this script; the shell does that.

``empty <scope>``
    Print an empty service module (used before the first selection).

``remove <scope> <module> <output> <service>...``
    Drop entire service entries (used by ``nix_remove_packages``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
P3_DIR = APP_DIR.parent
if str(P3_DIR) not in sys.path:
    sys.path.insert(0, str(P3_DIR))

from app import nix_services  # noqa: E402


def command_services(arguments):
    if len(arguments) != 1:
        print("services requires exactly one module path.", file=sys.stderr)
        return 2
    for service in sorted(nix_services.read_state(arguments[0])):
        print(service)
    return 0


def command_installed(_arguments):
    print(
        json.dumps(
            {
                scope: sorted(nix_services.installed_services(scope))
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
        _state, _changed, warnings = nix_services.apply_queue(*arguments)
    except (OSError, ValueError) as error:
        print(f"Nix services: {error}", file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"Nix services: {warning}", file=sys.stderr)
    return 0


def command_empty(arguments):
    if len(arguments) != 1 or arguments[0] not in ("home-manager", "system"):
        print("empty requires the home-manager or system scope.", file=sys.stderr)
        return 2
    sys.stdout.write(nix_services.empty_module(arguments[0]))
    return 0


def command_remove(arguments):
    if len(arguments) < 4:
        print(
            "remove requires <scope> <module> <output> <service>...",
            file=sys.stderr,
        )
        return 2
    scope, module, output, *services = arguments
    try:
        changed = nix_services.remove_services(scope, module, services, output)
    except (OSError, ValueError) as error:
        print(f"Nix services: {error}", file=sys.stderr)
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
        if command == "services":
            return command_services(arguments)
        if command == "installed":
            return command_installed(arguments)
        if command == "apply":
            return command_apply(arguments)
        if command == "empty":
            return command_empty(arguments)
        if command == "remove":
            return command_remove(arguments)
        print(f"Unknown command: {command}", file=sys.stderr)
        return 2
    except Exception as error:  # Never leave the shell without a reason.
        print(f"Could not update Nix service state: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
