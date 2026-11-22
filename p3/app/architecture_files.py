"""Read-only payload inspection before privilege, integration or replacement.

Only installed metadata tools are used. Downloaded executables are never run.
Archive members are inspected without extracting them to the filesystem.
Payload-sized metadata-tool output (dpkg-deb --fsys-tarfile, rpm2cpio and
bsdtar -cf - stream the decompressed payload itself) is consumed
incrementally from a bounded reader: decompressed payloads are never
buffered whole in memory and never written to disk.
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
from typing import BinaryIO, Iterable, Protocol

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
_MACHO_MAGIC = (
    b"\xcf\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xce",
)

_TOOL_TIMEOUT = 60.0
_TOOL_CHUNK = 1024**2
_METADATA_LIMIT = 256 * 1024**2
_METADATA_LIMIT_MESSAGE = "Metadata tool output exceeds 256 MiB inspection limit"
_PAYLOAD_LIMIT_MESSAGE = "Payload tool output exceeds the archive inspection limit"
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
    # Set for the `guest` content kind: the package legitimately embeds
    # foreign-platform binaries (VM guest assets, multi-platform prebuilds)
    # as declared inert data; only this ISA's ELFs remain payload evidence.
    guest_isa: str | None = None
    # True when a declared guest walk tolerated foreign-platform content
    # (Windows/macOS binaries, other-ISA or unqualified ELFs). An
    # all/noarch package must stay free of it: independent metadata
    # conflicts with any native payload, declared or not.
    foreign_binaries: bool = False


class _Readable(Protocol):
    """Blocking full-read stream consumed by the payload inspectors."""

    def read(self, size: int = -1) -> bytes: ...


class _ToolStream:
    """Bounded blocking reader over a metadata tool's stdout.

    Every read enforces the shared deadline and an output bound: the
    metadata cap for buffered queries (`_run`), or the payload-level
    archive bound for tools that stream the decompressed payload itself
    (dpkg-deb --fsys-tarfile, rpm2cpio, bsdtar -cf -). The tool is killed
    as soon as the stream is abandoned or a bound is exceeded.
    """

    def __init__(self, args: list[str], *, limit: int, limit_message: str) -> None:
        self._args = args
        self._limit = limit
        self._limit_message = limit_message
        self._total = 0
        self._selector: selectors.BaseSelector | None = None
        try:
            self._process = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ArchitectureError(
                f"Cannot inspect payload using {args[0]}; a native metadata tool is required"
            ) from error
        self._deadline = time.monotonic() + _TOOL_TIMEOUT
        try:
            self._selector = selectors.DefaultSelector()
            self._selector.register(self._process.stdout, selectors.EVENT_READ)
        except OSError as error:
            self._shutdown()
            raise ArchitectureError(
                f"Cannot inspect payload using {args[0]}; a native metadata tool is required"
            ) from error

    def read(self, size: int = -1) -> bytes:
        """Return exactly `size` bytes unless the tool's output ends first."""
        chunks: list[bytes] = []
        pending = None if size is None or size < 0 else size
        while pending is None or pending > 0:
            chunk = self._pull(
                _TOOL_CHUNK if pending is None else min(pending, _TOOL_CHUNK)
            )
            if not chunk:
                break
            chunks.append(chunk)
            if pending is not None:
                pending -= len(chunk)
        return b"".join(chunks)

    def tell(self) -> int:
        return self._total

    def finish(self) -> None:
        """Consume the tool's remaining output and require a clean exit."""
        try:
            while self._pull(_TOOL_CHUNK):
                pass
            if self._process.wait(
                timeout=max(0.1, self._deadline - time.monotonic())
            ):
                raise ArchitectureError(
                    f"{self._args[0]} could not inspect the payload"
                )
        except subprocess.TimeoutExpired as error:
            raise ArchitectureError(
                f"{self._args[0]} could not inspect the payload"
            ) from error
        finally:
            self._shutdown()

    def _pull(self, size: int) -> bytes:
        while True:
            remaining = self._deadline - time.monotonic()
            if remaining <= 0:
                raise ArchitectureError("Payload inspection timed out")
            if not self._selector.select(min(remaining, 1)):
                continue
            try:
                chunk = os.read(self._process.stdout.fileno(), size)
            except OSError as error:
                raise ArchitectureError(
                    f"Cannot inspect payload using {self._args[0]}; a native metadata tool is required"
                ) from error
            if not chunk:
                return b""
            self._total += len(chunk)
            if self._total > self._limit:
                raise ArchitectureError(self._limit_message)
            return chunk

    def _shutdown(self) -> None:
        if self._selector is not None:
            self._selector.close()
            self._selector = None
        if self._process.poll() is None:
            self._process.kill()
        self._process.wait()
        self._process.stdout.close()

    def __enter__(self) -> _ToolStream:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._shutdown()


def _run(args: list[str]) -> bytes:
    """Bound small metadata-tool output and time without executing downloaded code."""
    try:
        with _ToolStream(
            args, limit=_METADATA_LIMIT, limit_message=_METADATA_LIMIT_MESSAGE
        ) as stream:
            data = stream.read(-1)
            stream.finish()
        return data
    except (OSError, subprocess.SubprocessError) as error:
        raise ArchitectureError(
            f"Cannot inspect payload using {args[0]}; a native metadata tool is required"
        ) from error


def _payload_stream(args: list[str]) -> _ToolStream:
    """Open a payload-sized metadata tool under the archive-level output bound.

    dpkg-deb --fsys-tarfile, rpm2cpio and bsdtar -cf - emit the decompressed
    payload itself, which the archive inspectors account under MAX_BYTES;
    the metadata cap would falsely refuse legitimate large packages
    (e.g. Electron .debs decompressing well past 256 MiB).
    """
    return _ToolStream(args, limit=MAX_BYTES, limit_message=_PAYLOAD_LIMIT_MESSAGE)


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
    name: str, size: int, handle: _Readable | None, payload: Payload, depth: int = 0
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
    if header.startswith(b"\x7fELF"):
        try:
            arch = _elf(header)
        except ArchitectureError:
            if payload.guest_isa is None:
                raise
            # Unqualified 32-bit class/machine inside a declared guest
            # payload: an inert foreign-platform prebuild.
            payload.foreign_binaries = True
            return
        if payload.guest_isa is not None and arch != payload.guest_isa:
            # Other-ISA ELF inside a declared guest payload: inert data.
            payload.foreign_binaries = True
            return
        payload.architectures.add(arch)
    elif payload.guest_isa is not None and (
        header[:2] == b"MZ" or header[:4] in _MACHO_MAGIC
    ):
        # Declared Windows/macOS guest asset: inert data on the Linux host.
        payload.foreign_binaries = True
        return
    elif header[:2] == b"MZ" or header[:4] in _MACHO_MAGIC:
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


def _tar_members(
    archive: tarfile.TarFile, payload: Payload, depth: int = 0,
    package_manager: bool = False,
) -> None:
    """Apply the shared member policy to a sequentially iterated tar.

    `package_manager` marks the outer payload of a deb/rpm/Arch package
    file: its members are unpacked at the filesystem root by the native
    package manager, which resolves declared link targets itself. Absolute
    and ..-relative targets are standard packaging there (an /usr/bin
    launcher symlink, a ../lib relative doc link), and the inspection never
    extracts anything itself. This application unpacks only the plain
    tarball route (pkg_tarball), where an escaping link target stays a real
    extraction hazard and the strict guard applies.
    """
    for member in archive:
        if member.issym() or member.islnk():
            target = PurePosixPath(member.linkname)
            if not package_manager and (
                target.is_absolute() or ".." in target.parts
            ):
                raise ArchitectureError(f"Unsafe archive link: {member.name}")
        elif not member.isfile() and not member.isdir():
            raise ArchitectureError(f"Unsupported archive member: {member.name}")
        stream = archive.extractfile(member) if member.isfile() else None
        _member(member.name, member.size, stream, payload, depth)


def _tar_stream(
    handle: _Readable, payload: Payload, depth: int = 0,
    package_manager: bool = False,
) -> None:
    """Inspect an uncompressed tar streamed by a payload-sized metadata tool.

    Streaming mode consumes the tool's output incrementally: members the
    policy does not read are drained through the bounded reader, so the
    decompressed payload is never buffered whole and nothing is extracted.
    """
    try:
        with tarfile.open(fileobj=handle, mode="r|") as archive:
            _tar_members(archive, payload, depth, package_manager)
    except (OSError, EOFError, ValueError, tarfile.TarError) as error:
        if isinstance(error, ArchitectureError):
            raise
        raise ArchitectureError("Cannot inspect archive payload") from error


def _archive(
    handle: BinaryIO, payload: Payload, depth: int = 0,
    package_manager: bool = False,
) -> None:
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
                _tar_members(archive, payload, depth, package_manager)
    except (
        OSError,
        EOFError,
        ValueError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as error:
        if isinstance(error, ArchitectureError):
            raise
        raise ArchitectureError("Cannot inspect archive payload") from error


class _CpioSlice:
    """Bounded forward reader over one cpio member's data region."""

    def __init__(self, handle: _Readable, size: int) -> None:
        self._handle = handle
        self._left = size
        self._pos = 0
        self.truncated = False

    def read(self, size: int = -1) -> bytes:
        want = self._left if size is None or size < 0 else min(size, self._left)
        chunks: list[bytes] = []
        while want > 0:
            chunk = self._handle.read(want)
            if not chunk:
                self.truncated = True
                break
            chunks.append(chunk)
            want -= len(chunk)
        data = b"".join(chunks)
        self._pos += len(data)
        self._left -= len(data)
        return data

    def tell(self) -> int:
        return self._pos


def _discard(handle: _Readable, count: int) -> bool:
    """Drain `count` bytes from a non-seekable stream; True when it ends early."""
    while count > 0:
        chunk = handle.read(min(count, _TOOL_CHUNK))
        if not chunk:
            return True
        count -= len(chunk)
    return False


def _cpio(handle: _Readable, payload: Payload) -> None:
    """Inspect rpm2cpio's newc format without extracting files or executing hooks.

    The decompressed cpio stream is consumed incrementally from the bounded
    tool reader: member data is read only as far as the member policy needs
    and the rest is discarded in place.
    """
    while True:
        header = handle.read(110)
        if len(header) < 110:
            raise ArchitectureError("Incomplete RPM archive")
        if header[:6] not in (b"070701", b"070702"):
            raise ArchitectureError("Unsupported RPM payload archive")
        try:
            size = int(header[54:62], 16)
            namesize = int(header[94:102], 16)
            mode = int(header[14:22], 16)
        except ValueError as error:
            raise ArchitectureError("Invalid RPM archive metadata") from error
        if namesize < 1:
            raise ArchitectureError("Truncated RPM member name")
        raw_name = handle.read(namesize)
        if len(raw_name) < namesize:
            raise ArchitectureError("Truncated RPM member name")
        name = raw_name[:-1].decode("utf-8", errors="strict")
        if _discard(handle, (-(110 + namesize)) % 4):
            raise ArchitectureError("Incomplete RPM archive")
        if name == "TRAILER!!!":
            return
        skip = size
        if mode & 0o170000 == 0o100000:
            slice_stream = _CpioSlice(handle, size)
            _member(name, size, slice_stream, payload)
            if slice_stream.truncated:
                raise ArchitectureError("Truncated RPM payload")
            skip = size - slice_stream.tell()
        # The data region starts 4-aligned, so its padding is -size % 4.
        if _discard(handle, skip + (-(size) % 4)):
            raise ArchitectureError("Truncated RPM payload")


def validate_file(
    path: str | Path, *, machine: str | None = None, content_kind: str = "native"
) -> Payload:
    """Require consistent package/filename/ELF evidence before any mutation.

    Package metadata labels are canonicalized first: microarchitecture levels
    (CachyOS x86_64_v3 .PKGINFO, ALHP x86_64_v2 RPMs, APT amd64v3 variants) are
    native x86_64 evidence, not foreign ISAs.
    `data` and `source` are explicit declarations and cannot contain native code.
    `guest` is an explicit declaration that the package legitimately embeds
    foreign-platform binaries (VM guest assets, multi-platform prebuilds) as
    inert data: they are tolerated, while the package metadata label and any
    host-ISA ELF must still prove native compatibility.
    An all/noarch package is accepted only when its payload contains no native code.
    """
    arch = host() if machine is None else normalize(machine)
    file = Path(path).resolve(strict=True)
    if not file.is_file() or file.stat().st_size > MAX_BYTES:
        raise ArchitectureError("Payload missing or exceeds inspection limit")
    if content_kind not in {"native", "data", "source", "guest"}:
        raise ArchitectureError("Unknown content kind")
    payload = Payload(guest_isa=arch.value if content_kind == "guest" else None)
    metadata: str | None = None
    independent = content_kind in {"data", "source"}
    lower = file.name.lower()
    if lower.endswith(".deb"):
        metadata = canonical_package_architecture(
            _run(["dpkg-deb", "--field", str(file), "Architecture"]).decode().strip()
        )
        if metadata != "all":
            require_native([metadata], arch.value)
        with _payload_stream(["dpkg-deb", "--fsys-tarfile", str(file)]) as stream:
            _tar_stream(stream, payload, package_manager=True)
            stream.finish()
        independent = metadata == "all"
    elif lower.endswith(".rpm"):
        metadata = canonical_package_architecture(
            _run(["rpm", "-qp", "--qf", "%{ARCH}", str(file)]).decode().strip()
        )
        if metadata != "noarch":
            require_native([metadata], arch.value)
        with _payload_stream(["rpm2cpio", str(file)]) as stream:
            _cpio(stream, payload)
            stream.finish()
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
        # pacman -U unpacks the payload itself, so declared link targets are
        # the package manager's own domain (same relaxation as deb/rpm).
        if lower.endswith((".pkg.tar.zst", ".pacman")):
            with _payload_stream(["bsdtar", "-cf", "-", "@" + str(file)]) as stream:
                _tar_stream(stream, payload, package_manager=True)
                stream.finish()
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
        if payload.architectures or hints or payload.foreign_binaries:
            raise ArchitectureError(
                "Architecture-independent metadata conflicts with native payload/name"
            )
    else:
        if not payload.architectures and not metadata:
            raise ArchitectureError(
                "Native payload architecture is unknown; missing metadata is not compatibility"
            )
        if content_kind == "guest" and not payload.architectures:
            raise ArchitectureError("Guest payload lacks host-ISA code evidence")
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
