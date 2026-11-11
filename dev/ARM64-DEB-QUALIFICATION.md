# Native Ubuntu ARM64 DEB qualification (M4A)

Baseline: `50f65ad9864b14d779e181c6f86bab9c41d7601b`. Local engineering only;
no release, workflow, publication or third-party route promotion.

## Construction and policy

The old DEB driver combined construction with Launchpad API queries, source
signing and upload, hardcoded `amd64`, removed existing output, and staged native
libraries under `/usr/share`. It was audited, not executed.

`dev/build/deb/build.sh` now constructs a local binary package only. It requires
native Linux, agreement between the shared M1 DEB label and both dpkg host/native
architectures, an explicit source timestamp, the repository upstream version,
and a new output directory outside the checkout. It verifies the approved script
bundle, copies source into private staging, discards the two known development
extensions and rebuilds both libraries through the existing locked source build.
No foreign library, architecture override or prebuilt wheel input is accepted.
The finished package passes the existing M1 package/payload validator.

Python and native components share `/usr/lib/linuxtoys` to retain the application's
relative discovery paths. `/usr/bin/linuxtoys` invokes the distribution Python.
Desktop, SVG icon, MIME definition, AppStream metadata and copyright use their
standard `/usr/share` locations. Payload ownership is root:root; directory and
executable modes are 0755, other files 0644. Existing `.lib` aliases to regular
sibling helper files are materialized as regular files. Absolute, escaping,
chained and directory links and special files are rejected before copying.
The finished payload passes M1 validation, and independent inspection confirms
exactly the two required native libraries. Hidden script metadata is unchanged. Pure-Python Textual/pyte and their existing vendored runtime
ship privately; their direct pins remain in `p3/requirements.txt`.

`dpkg-shlibdeps` derives native ELF dependencies from the build distribution's
package database. Explicit dependencies cover Python/GI/Cairo, GTK/VTE/AppStream
typelibs, the existing runtime command tools and image/icon integration. They
resolve for the package architecture; no dependency is assumed to be `all`.
PyO3 extension symbols intentionally resolve from the Python interpreter rather
than a linked `libpython`, so dpkg-shlibdeps reports those unresolved symbols.
Missing linked libraries or package metadata still fail the build.

There are **no maintainer scripts**, conffiles, service units, network actions,
package-manager calls, privilege escalation or home-directory payloads in the
DEB. Normal installed MIME/icon package triggers may update their system caches.
Application actions run only after an explicit user launch and remain governed
by the unchanged M1/M3A route and revision policy.

## Repeating the build

Prepare dependencies only in an isolated native Ubuntu ARM64 container. Required
build tools include Cargo/rustc, Python development headers, maturin, pip,
pkg-config, GTK3 development files, patchelf, dpkg-dev and binutils; the runtime
dependencies must be available for the native shlibs database. Reuse a reviewed
pure-Python vendor input or let the existing vendor script materialize its pins.
No host bootstrap or upload command is part of this builder.

```bash
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
export SOURCE_REVISION="$(git rev-parse HEAD)"
export DEB_REVISION=1~m4a1
bash dev/build/deb/build.sh "$(cat src/ver)" /work/new-output
```

For an offline build with populated Cargo sources, set `CARGO_NET_OFFLINE=true`
and `CARGO_HOME` to that cache. The private Cargo target is always new. The
output includes the DEB, SHA256SUMS, source/build staging and external
`build-provenance.json` (toolchain, source input hashes, vendor versions and
installed build-package versions). Keep binary artifacts outside Git. The
builder refuses existing output instead of deleting it. Source paths are remapped
in Rust artifacts; all staged timestamps are normalized to SOURCE_DATE_EPOCH.
Python transitive dependencies are not newly locked by this milestone: retain and
compare the recorded input inventory when reproducing a package.

The historical release workflow still expects the previous source/PPA build
contract and is intentionally unchanged. This local constructor does not replace
that publication integration. Adapting release/PPA automation requires a separate
review and authorization.

## Native verification

The [machine-readable evidence](arm64-deb-qualification-evidence.json) records
Ubuntu 26.04.1 LTS, kernel 7.0.0-43-generic, aarch64 / dpkg arm64, Docker 29.8.0,
Python 3.14.4, Rust/Cargo 1.93.1 and maturin 1.9.4. Build tools and runtime
prerequisites were installed only in disposable clones of the supplied
`linuxtoys-m4a` container. Copies used the Docker API, with no host bind mounts
or privileged containers. The original container stayed running with identical
configuration, image, mounts and filesystem-diff inventory. The guest's dpkg/APT
database hashes and running-service set remained unchanged.

| Check | Verified result |
| --- | --- |
| Native build | Both libraries compiled from source with the committed Cargo lockfile in fresh target trees, using cached crate sources offline. No development `.so` was reused. The two builds' stripped ELF bytes match. |
| Inventory | 1,830 regular payload files; exactly two ELF64 little-endian AArch64 libraries under `/usr/lib/linuxtoys/app`; root ownership, modes, payload host paths and ELF build paths checked. No maintainer scripts, services or home payload. |
| Runtime | Installed PyO3 and GUI libraries loaded from `/usr/lib/linuxtoys/app`, ABI 20, 8-byte pointers; required GI/Cairo imports passed. Native Rust declarations match all ctypes layouts in the full suite. |
| Interfaces | Actual installed CLI help/version/catalog, TUI startup/search/exit, MCP authentication/tool discovery/font search/shutdown, GUI search/close and launcher passed as UID 1001. Display probes used Xvfb **X11**, private D-Bus and no network. |
| Widgets | 100 native construction/destruction cycles; VTE spawned a harmless shell and verified output/exit. Resident memory was equal at cycles 10 and 100; no general leak claim. |
| Lifecycle | Real `dpkg -i` install, upgrade to `1~m4a2`, downgrade/rollback to `1~m4a1`, remove, reinstall and purge passed. `dpkg --verify` and `--audit` were clean after successful configuration. All 64 actual user files, including application-created data, and canaries survived operations; `/etc` and other package states were unchanged. |
| Dependency failure | Removed GI Cairo normally in an independent clone; configuration failed with its exact missing-dependency message. Reinstalled its cached Ubuntu DEB offline, then configured LinuxToys successfully without force flags. |
| Interrupted unpack | In another clone, stopped and killed real dpkg after its half-installed event **and a partial payload file existed**. Audit reported incomplete/missing package control data. A normal reinstall/configure recovered; data/configuration guards passed. This is not a power-loss simulation. |
| Integration | Desktop file validated; AppStream validation succeeded offline (existing summary-dot informational notice). MIME/icon files were installed through dpkg, including ordinary dependency triggers. No actual desktop-menu activation was tested. |
| Regression/static | 102 Python tests, 39 Rust catalog tests; GUI crate has zero unit tests. Ruff 0.15.7 check/format, ShellCheck 0.11.0 for builder/installed launcher, Bash syntax, 102 application Python source syntax parses, approved-manifest verification and Git diff checks passed. |
| Output safeguards | Existing output, output inside source and symlinked output were rejected before compilation or mutation. External links/FIFOs were rejected; legitimate sibling helper aliases were accepted. |

Tests ran in independent `--network none` runtime clones. The first-run GUI
requested APT metadata credentials in this minimal image. Tests terminated the
actual password and subsequent authentication-error Zenity dialogs (explicit
cancellation), then verified normal application shutdown. No credentials were
provided, metadata refresh granted, or optional backend replaced for the GUI.
The existing TUI probe separately retains its explicit optional-backend failure
injection. Test-only installed-root discovery prevents source-tree imports from
standing in for installed application imports.

The container's inherited umask was 0000. Initial inspection exposed mode 0777
at the archive root, and an overly broad link check rejected the repository's
three helper aliases. The final builder uses umask 022, canonical root/child
permissions, validates safe sibling aliases and rejects unsafe links. A
reproducibility comparison also exposed vendor-directory mtimes; normalizing all
timestamps removes that difference. Staging/archiving was rerun after these
packaging-only corrections using the native products; Rust inputs and project
dependencies were unchanged.

## Artifacts and reproducibility

Qualified artifact: `linuxtoys_7.9.8-1~m4a1_arm64.deb`.

```text
Version: 7.9.8-1~m4a1
Architecture: arm64
SHA-256: 83173db3b42d8ef966b6bde02f064beb42ee71b4593bfd727a3fefefdb862f04
SOURCE_DATE_EPOCH: 1794389593
```

The complete dependency field is in the evidence. Dynamic minima include
`libc6 >= 2.39`, GTK3, Cairo, GLib, GdkPixbuf, Pango and libgcc; the explicit
runtime list includes the GI typelibs and Cairo bridge. Those minima do not
qualify older Ubuntu releases.

Independent restaging/archiving matched the complete DEB byte-for-byte, including
when using native products from the other fresh source build. Upgrade test
artifact `7.9.8-1~m4a2` has SHA-256
`fd80e8c4bddee635df028d5869b4d898b58e51b2f68daa55b41cd7d528e860ae`;
its application payload matches the first revision. Local binaries, external
build provenance and raw logs are retained in ignored `target/m4a-artifacts/`,
not committed. Construction in qualification used an explicitly identified
baseline plus working-tree changes; provenance records source-input hashes
rather than falsely identifying that tree as the unmodified baseline.

Run each driver mode **as root only in a fresh offline disposable runtime
container**, with prepared dependencies, cached GI Cairo DEB and a `testuser`
account. GUI checks additionally require Xvfb, xauth and private D-Bus tools:

```bash
python3 -B /work/src/dev/tests/native_deb_lifecycle.py lifecycle \
  /work/packages/linuxtoys_7.9.8-1~m4a1_arm64.deb \
  --upgrade /work/packages/linuxtoys_7.9.8-1~m4a2_arm64.deb \
  --probe /work/src/dev/tests/native_application_smoke.py \
  --output /work/lifecycle.json
# Separate clones: use modes missing and interrupt with their own output paths.
```

## Remaining gates

Native amd64 qualification remains unavailable. Existing x86 alias, selector,
optimizer, native-build-driver and DEB metadata fixtures pass; they are not
native amd64 build/runtime evidence. No shared source build or architecture
policy was changed.

This milestone qualifies the application DEB in this Ubuntu ARM64 Docker rootfs,
not Wayland, a physical desktop install, other distributions, historical package
migrations, live self-updates, general power-loss recovery or third-party feature
installations. Two package revisions of the same application exercise lifecycle
semantics; they do not establish upgrade compatibility with all older releases.
Rustfmt was unavailable and no Rust source was modified. Release/PPA adaptation,
native amd64 testing and any live script/release rollout remain separately
reviewed work. No ARMv7/ARMv6, RPM, AppImage or release workflow claim is added.
