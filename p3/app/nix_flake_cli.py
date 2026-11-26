#!/usr/bin/env python3
"""Small CLI bridge between the Bash Nix helpers and ``nix_flakes``.

The generated Nix module, import state and Action Registry transactions live
in Python. ``nixsys.bash`` calls this script to remove flake state, render the
remaining module and reconcile registry transactions without importing the
whole application package into every shell.

Commands (stdout is machine-readable; diagnostics go to stderr):

``remove <encoded-id>...``
    Remove the given state records, clean up unused wrapper trees and print
    one ``scope<TAB>module-path`` line per affected scope. The shell publishes
    each module and rebuilds that scope.

``remove-reference <reference>...``
    Remove every state record matching the given reference/original/wrapper
    URL. Prints the same ``scope<TAB>module-path`` lines.

``sync-registry [--removed <encoded-id>...]``
    Create/update registry transactions for the current import state. With
    ``--removed`` it first drops those operations (so a successful rebuild
    can retire exactly the removed flake).

``cleanup-wrappers``
    Delete wrapper trees no longer referenced by an imported flake. Called
    after a successful rebuild, never before the generated module is updated.

``list``
    Print the imported flake state as JSON.

``render <scope>``
    Print the generated module for one scope (diagnostics for tooling).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

APP_DIR = Path(__file__).resolve().parent
P3_DIR = APP_DIR.parent
if str(P3_DIR) not in sys.path:
    sys.path.insert(0, str(P3_DIR))

from app import nix_flakes, nix_registry  # noqa: E402


def _decode_ids(values):
    return [unquote(str(value or "")) for value in values or ()]


def _print_modules(scopes):
    for scope in scopes:
        fd, path = tempfile.mkstemp(
            prefix=f"linuxtoys-flake-module-{scope}-", suffix=".nix"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(nix_flakes.render_module(scope))
        except Exception:
            try:
                os.unlink(path)
            except OSError:
                pass
            raise
        print(f"{scope}\t{path}")


def command_remove(arguments):
    ids = _decode_ids(arguments)
    scopes = nix_flakes.remove_imports(ids)
    _print_modules(scopes)
    return 0


def command_remove_reference(arguments):
    references = [str(value or "").strip() for value in arguments or ()]
    references = [value for value in references if value]
    if not references:
        print("No flake reference was provided.", file=sys.stderr)
        return 1
    ids = []
    for reference in references:
        ids.extend(nix_flakes.record_ids_for_reference(reference))
    ids = list(dict.fromkeys(ids))
    if not ids:
        print(
            "No imported flake matches the requested reference.",
            file=sys.stderr,
        )
        return 1
    scopes = nix_flakes.remove_imports(ids)
    _print_modules(scopes)
    return 0


def command_sync_registry(arguments):
    removed = []
    if arguments[:1] == ["--removed"]:
        removed = _decode_ids(arguments[1:])
    count = nix_registry.sync_flakes(
        prune=True,
        removed_ids=removed or None,
    )
    print(count)
    return 0


def command_cleanup_wrappers(_arguments):
    print(nix_flakes.cleanup_wrappers())
    return 0


def command_list(_arguments):
    print(
        json.dumps(
            nix_flakes.imports(),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0


def command_render(arguments):
    if len(arguments) != 1:
        print("render requires exactly one scope.", file=sys.stderr)
        return 2
    sys.stdout.write(nix_flakes.render_module(arguments[0]))
    return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    command = argv[1]
    arguments = argv[2:]
    try:
        if command == "remove":
            return command_remove(arguments)
        if command == "remove-reference":
            return command_remove_reference(arguments)
        if command == "sync-registry":
            return command_sync_registry(arguments)
        if command == "cleanup-wrappers":
            return command_cleanup_wrappers(arguments)
        if command == "list":
            return command_list(arguments)
        if command == "render":
            return command_render(arguments)
        print(f"Unknown command: {command}", file=sys.stderr)
        return 2
    except nix_flakes.FlakeError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Could not update the imported flake state: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
