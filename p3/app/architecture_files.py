"""Read-only payload inspection before privilege, integration or replacement.

Only installed metadata tools are used. Downloaded executables are never run.
Archive members are inspected without extracting them to the filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import io
import gzip
import lzma
import os
import selectors
import time
from pathlib import Path, PurePosixPath
import struct
import subprocess
import tarfile
import zipfile
from typing import BinaryIO, Iterable

from .architecture import (
    ArchitectureError,
    LABELS,
    asset_architectures,
    canonical_package_architecture,
    host,
    normalize,
    require_native,
)

MAX_BYTES = 4 * 1024**3
MAX_MEMBERS = 100_000
MAX_NESTED_BYTES = 64 * 1024**2
_NATIVE_SUFFIXES = (
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".node",
    ".a",
    ".o",
    ".obj",
    ".pyd",
)


@dataclass
class Payload:
    architectures: set[str] = field(default_factory=set)
    members: int = 0
    expanded_bytes: int = 0


def _run(args: list[str]) -> bytes:
    """Bound metadata-tool output and time without executing downloaded code."""
    limit = 256 * 1024**2
    try:
        with subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        ) as process:
            deadline = time.monotonic() + 60
            chunks = []
            total = 0
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while True:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise ArchitectureError("Payload inspection timed out")
                        if not selector.select(min(remaining, 1)):
                            continue
                        chunk = os.read(process.stdout.fileno(), 1024**2)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > limit:
                            raise ArchitectureError(
                                "Metadata tool output exceeds 256 MiB inspection limit"
                            )
                        chunks.append(chunk)
                if process.wait(timeout=max(0.1, deadline - time.monotonic())):
                    raise ArchitectureError(f"{args[0]} could not inspect the payload")
                return b"".join(chunks)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
    except (OSError, subprocess.SubprocessError) as error:
        raise ArchitectureError(
            f"Cannot inspect payload using {args[0]}; a native metadata tool is required"
        ) from error


def _elf(header: bytes) -> str | None:
    if not header.startswith(b"\x7fELF"):
        return None
    if len(header) < 20 or header[4] != 2 or header[5] not in (1, 2):
        raise ArchitectureError("Unsupported or malformed ELF class/byte order")
    machine = struct.unpack("<H" if header[5] == 1 else ">H", header[18:20])[0]
    for arch, labels in LABELS.items():
        if machine == labels.elf_machine:
            return arch.value
    raise ArchitectureError(f"Unsupported ELF machine: {machine}")


def _member(
    name: str, size: int, handle: BinaryIO | None, payload: Payload, depth: int = 0
) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ArchitectureError(f"Unsafe archive member: {name}")
    payload.members += 1
    payload.expanded_bytes += size
    if payload.members > MAX_MEMBERS or payload.expanded_bytes > MAX_BYTES:
        raise ArchitectureError("Archive inspection limit exceeded")
    if handle is None:
        return
    header = handle.read(64)
    arch = _elf(header)
    if arch:
        payload.architectures.add(arch)
    elif header[:2] == b"MZ" or header[:4] in (
        b"\xcf\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xce",
    ):
        raise ArchitectureError(f"Non-Linux binary in payload: {name}")
    elif header.startswith((b"!<arch>\n", b"\x28\xb5\x2f\xfd")):
        raise ArchitectureError(f"Unqualified native/compressed archive: {name}")
    elif name.lower().endswith(_NATIVE_SUFFIXES) or re_shared_object(name):
        raise ArchitectureError(f"Unknown native binary format: {name}")
    if header.startswith(
        (b"PK\x03\x04", b"PK\x05\x06", b"\x1f\x8b", b"\xfd7zXZ\x00")
    ) or name.lower().endswith(
        (".tar", ".tar.gz", ".tar.xz", ".tgz", ".zip", ".whl", ".jar", ".egg")
    ):
        if depth >= 2 or size > MAX_NESTED_BYTES:
            raise ArchitectureError(f"Cannot safely inspect nested archive: {name}")
        data = header + handle.read(MAX_NESTED_BYTES + 1)
        if len(data) > MAX_NESTED_BYTES:
            raise ArchitectureError("Nested archive inspection limit exceeded")
        if header.startswith((b"\x1f\x8b", b"\xfd7zXZ\x00")):
            # Debian packages routinely contain individually compressed manpages,
            # not tarballs. Inspect their bounded decompressed contents too.
            try:
                if header.startswith(b"\x1f\x8b"):
                    with gzip.open(io.BytesIO(data), "rb") as compressed:
                        decoded = compressed.read(MAX_NESTED_BYTES + 1)
                else:
                    decoder = lzma.LZMADecompressor(memlimit=MAX_NESTED_BYTES)
                    decoded = decoder.decompress(data, max_length=MAX_NESTED_BYTES + 1)
                    if not decoder.eof or decoder.unused_data:
                        raise ArchitectureError(
                            "Truncated or multiple nested xz streams"
                        )
            except (OSError, EOFError, lzma.LZMAError) as error:
                raise ArchitectureError(f"Invalid compressed member: {name}") from error
            if len(decoded) > MAX_NESTED_BYTES:
                raise ArchitectureError("Decompressed member inspection limit exceeded")
            if tarfile.is_tarfile(io.BytesIO(decoded)):
                _archive(io.BytesIO(decoded), payload, depth + 1)
            else:
                inner_name = str(PurePosixPath(name).with_suffix(""))
                _member(
                    inner_name, len(decoded), io.BytesIO(decoded), payload, depth + 1
                )
        else:
            _archive(io.BytesIO(data), payload, depth + 1)


def re_shared_object(name: str) -> bool:
    """Recognize versioned shared objects as well as an exact .so suffix."""
    return ".so." in PurePosixPath(name).name


def _zip_metadata_limit(handle: BinaryIO) -> None:
    """Bound central-directory allocation before zipfile constructs its member list."""
    handle.seek(0, 2)
    size = handle.tell()
    handle.seek(max(0, size - 65557))
    tail = handle.read(65557)
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or len(tail) - offset < 22:
        raise ArchitectureError("Missing ZIP directory metadata")
    fields = struct.unpack("<4s4H2LH", tail[offset : offset + 22])
    if fields[1] or fields[2] or fields[4] == 65535:
        raise ArchitectureError("Multivolume/ZIP64 inspection is not qualified")
    if fields[4] > MAX_MEMBERS or fields[5] > 32 * 1024**2:
        raise ArchitectureError("ZIP directory exceeds inspection limit")
    if offset + 22 + fields[7] != len(tail):
        raise ArchitectureError("Conflicting ZIP directory metadata")
    handle.seek(0)


def _archive(handle: BinaryIO, payload: Payload, depth: int = 0) -> None:
    try:
        if zipfile.is_zipfile(handle):
            _zip_metadata_limit(handle)
            with zipfile.ZipFile(handle) as archive:
                for member in archive.infolist():
                    with archive.open(member) as stream:
                        _member(
                            member.filename, member.file_size, stream, payload, depth
                        )
        else:
            handle.seek(0)
            with tarfile.open(fileobj=handle, mode="r:*") as archive:
                for member in archive:
                    if member.issym() or member.islnk():
                        target = PurePosixPath(member.linkname)
                        if target.is_absolute() or ".." in target.parts:
                            raise ArchitectureError(
                                f"Unsafe archive link: {member.name}"
                            )
                    elif not member.isfile() and not member.isdir():
                        raise ArchitectureError(
                            f"Unsupported archive member: {member.name}"
                        )
                    stream = archive.extractfile(member) if member.isfile() else None
                    _member(member.name, member.size, stream, payload, depth)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as error:
        if isinstance(error, ArchitectureError):
            raise
        raise ArchitectureError("Cannot inspect archive payload") from error


def _cpio(data: bytes, payload: Payload) -> None:
    """Inspect rpm2cpio's newc format without extracting files or executing hooks."""
    offset = 0
    while offset + 110 <= len(data):
        header = data[offset : offset + 110]
        if header[:6] not in (b"070701", b"070702"):
            raise ArchitectureError("Unsupported RPM payload archive")
        try:
            size = int(header[54:62], 16)
            namesize = int(header[94:102], 16)
            mode = int(header[14:22], 16)
        except ValueError as error:
            raise ArchitectureError("Invalid RPM archive metadata") from error
        offset += 110
        if namesize < 1 or offset + namesize > len(data):
            raise ArchitectureError("Truncated RPM member name")
        name = data[offset : offset + namesize - 1].decode("utf-8", errors="strict")
        offset = (offset + namesize + 3) & ~3
        if name == "TRAILER!!!":
            return
        if offset + size > len(data):
            raise ArchitectureError("Truncated RPM payload")
        stream = (
            io.BytesIO(data[offset : offset + size])
            if mode & 0o170000 == 0o100000
            else None
        )
        _member(name, size, stream, payload)
        offset = (offset + size + 3) & ~3
    raise ArchitectureError("Incomplete RPM archive")


def validate_file(
    path: str | Path, *, machine: str | None = None, content_kind: str = "native"
) -> Payload:
    """Require consistent package/filename/ELF evidence before any mutation.

    Package metadata labels are canonicalized first: microarchitecture levels
    (CachyOS x86_64_v3 .PKGINFO, ALHP x86_64_v2 RPMs, APT amd64v3 variants) are
    native x86_64 evidence, not foreign ISAs.
    `data` and `source` are explicit declarations and cannot contain native code.
    An all/noarch package is accepted only when its payload contains no native code.
    """
    arch = host() if machine is None else normalize(machine)
    file = Path(path).resolve(strict=True)
    if not file.is_file() or file.stat().st_size > MAX_BYTES:
        raise ArchitectureError("Payload missing or exceeds inspection limit")
    if content_kind not in {"native", "data", "source"}:
        raise ArchitectureError("Unknown content kind")
    payload = Payload()
    metadata: str | None = None
    independent = content_kind in {"data", "source"}
    lower = file.name.lower()
    if lower.endswith(".deb"):
        metadata = canonical_package_architecture(
            _run(["dpkg-deb", "--field", str(file), "Architecture"]).decode().strip()
        )
        if metadata != "all":
            require_native([metadata], arch.value)
        _archive(io.BytesIO(_run(["dpkg-deb", "--fsys-tarfile", str(file)])), payload)
        independent = metadata == "all"
    elif lower.endswith(".rpm"):
        metadata = canonical_package_architecture(
            _run(["rpm", "-qp", "--qf", "%{ARCH}", str(file)]).decode().strip()
        )
        if metadata != "noarch":
            require_native([metadata], arch.value)
        _cpio(_run(["rpm2cpio", str(file)]), payload)
        independent = metadata == "noarch"
    elif lower.endswith(
        (
            ".tar",
            ".tar.gz",
            ".tar.xz",
            ".tgz",
            ".zip",
            ".whl",
            ".pkg.tar.zst",
            ".pkg.tar.xz",
            ".pacman",
        )
    ):
        # zstd Arch archives require an installed native decoder. bsdtar emits
        # an uncompressed tar, which is inspected with the same member policy.
        if lower.endswith((".pkg.tar.zst", ".pacman")):
            _archive(io.BytesIO(_run(["bsdtar", "-cf", "-", "@" + str(file)])), payload)
        else:
            with file.open("rb") as stream:
                _archive(stream, payload)
        if ".pkg.tar." in lower or lower.endswith(".pacman"):
            info = _run(["bsdtar", "-xOf", str(file), ".PKGINFO"]).decode()
            values = [
                line.split("=", 1)[1].strip()
                for line in info.splitlines()
                if line.startswith("arch =")
            ]
            if len(values) != 1:
                raise ArchitectureError("Missing/conflicting Arch package architecture")
            metadata = canonical_package_architecture(values[0])
            independent = metadata == "any"
    elif lower.endswith(".flatpakref"):
        # Reference files are inspected/resolved through Flatpak before install.
        raise ArchitectureError(
            "Flatpak references require remote architecture/availability preflight"
        )
    elif lower.endswith((".flatpak", ".snap", ".eopkg")):
        raise ArchitectureError(
            f"Native payload inspection is not yet qualified for {file.suffix}; use a verified native repository route"
        )
    else:
        with file.open("rb") as stream:
            _member(file.name, file.stat().st_size, stream, payload)
    hints = asset_architectures(file.name)
    if metadata and not independent:
        hints.append(metadata)
    if independent:
        if payload.architectures or hints:
            raise ArchitectureError(
                "Architecture-independent metadata conflicts with native payload/name"
            )
    else:
        if not payload.architectures and not metadata:
            raise ArchitectureError(
                "Native payload architecture is unknown; missing metadata is not compatibility"
            )
        require_native([*hints, *payload.architectures], arch.value)
    return payload


def validate_files(paths: Iterable[str], *, content_kind: str = "native") -> None:
    """Validate an entire batch before its first privileged/destructive action."""
    for path in paths:
        validate_file(path, content_kind=content_kind)


def validate_tree(path: str | Path, *, content_kind: str = "source") -> Payload:
    """Inspect a fetched source tree before installing build deps or invoking make."""
    root = Path(path).resolve(strict=True)
    payload = Payload()
    if not root.is_dir() or content_kind != "source":
        raise ArchitectureError("Expected an explicitly declared source directory")
    for file in root.rglob("*"):
        relative = file.relative_to(root)
        if ".git" in relative.parts:
            continue
        if file.is_symlink():
            if not file.resolve().is_relative_to(root):
                raise ArchitectureError(f"Source link escapes tree: {relative}")
        elif file.is_file():
            with file.open("rb") as stream:
                _member(str(relative), file.stat().st_size, stream, payload)
    if payload.architectures:
        raise ArchitectureError(
            "Explicit source tree contains precompiled native binaries"
        )
    return payload
