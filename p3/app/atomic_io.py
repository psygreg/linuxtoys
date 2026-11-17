"""Atomic file writes for explicitly migrated cache/persistence sites.

Every helper stages content in a uniquely named temporary file inside the
target's directory and moves it into place with ``os.replace``, so readers
never observe a partial file. Ordinary failures attempt to clean up the staging file;
a process crash can leave it behind. File fsync is optional; directory fsync
and read-modify-write locking are not provided.

Sites that previously used deterministic ``<path>.tmp`` names get a
``mkstemp``-generated name instead: concurrent writers can no longer clobber
each other's staging file, and no reader ever looks for the temporary name.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any


def atomic_write_bytes(
    path: str | os.PathLike[str],
    data: bytes,
    *,
    mode: int | None = None,
    tmp_suffix: str = ".tmp",
    fsync: bool = False,
) -> None:
    """Atomically write raw *data* to *path*.

    Args:
        path: Destination file (created if missing, parents included).
        data: Raw bytes to write.
        mode: Optional permission bits applied to the staged file before the
            replace. Without it, mkstemp's private 0600 mode is retained,
            including when replacing an existing destination.
        tmp_suffix: Suffix for the staged temporary file.
        fsync: Flush and fsync the staged file before the replace, for sites
            that need the content on disk before proceeding.
    """
    path = os.fspath(path)
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=os.path.basename(path) + ".", suffix=tmp_suffix, dir=directory
    )
    try:
        handle = os.fdopen(fd, "wb")
        fd = None  # Ownership transferred to the file object.
        with handle:
            handle.write(data)
            if fsync:
                handle.flush()
                os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
        tmp = None
    finally:
        if fd is not None:
            os.close(fd)
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def atomic_write_text(
    path: str | os.PathLike[str],
    text: str,
    *,
    mode: int | None = None,
    encoding: str = "utf-8",
    tmp_suffix: str = ".tmp",
    fsync: bool = False,
) -> None:
    """Atomically write *text* to *path* (see :func:`atomic_write_bytes`)."""
    atomic_write_bytes(
        path,
        text.encode(encoding),
        mode=mode,
        tmp_suffix=tmp_suffix,
        fsync=fsync,
    )


def atomic_write_json(
    path: str | os.PathLike[str],
    value: Any,
    *,
    mode: int | None = None,
    tmp_suffix: str = ".tmp",
    fsync: bool = False,
    **json_kwargs: Any,
) -> None:
    """Atomically write *value* as JSON to *path*.

    ``json_kwargs`` are forwarded to ``json.dumps`` so each call site keeps
    its exact historical serialization (compact separators, ``ensure_ascii``,
    indentation, ...).
    """
    atomic_write_text(
        path,
        json.dumps(value, **json_kwargs),
        mode=mode,
        tmp_suffix=tmp_suffix,
        fsync=fsync,
    )
