# Architecture eligibility (M1)

The authority is `p3/app/architecture.py`. Python catalogs, the Rust catalog's
PyO3 bridge, shell helpers and the standalone installer use this policy. There
is no environment override for the installation architecture. Supported host
aliases are `x86_64`/`amd64`/`x64` and `aarch64`/`arm64`; ARM32 and unknown hosts
are refused. Debian, RPM, Rust, Flatpak, Homebrew and vendor labels are separate
fields, not interchangeable strings.

## Decisions and evidence

1. **Native:** require consistent host-native evidence. Filename tokens can select
   a release candidate, but installation also reads package metadata and ELF
   machine fields. Multiple/conflicting ISAs are refused. A shared library marked
   ARM64 does not become compatible with x86-64 through a filename fallback.
2. **Independent data/source:** require an explicit declaration, or package
   `all`/`noarch`/`any` metadata, and reject bundled native code. Source-build mode
   is explicit; ordinary tarballs are not assumed to contain source.
3. **Unknown:** missing metadata is not native compatibility. Unlabelled release
   assets cannot be automatically chosen. A local unlabelled DEB may pass only
   after its real package metadata/payload establish the native architecture.
4. **Selection:** choose exactly one native candidate in the existing format
   preference. Zero or multiple best candidates fail. There is no implicit
   i686 fallback: no independently qualified 32-bit exception exists in M1.

`architecture_files.py` inspects ELF, DEB, RPM, supported Arch archives, tar and
ZIP payloads without executing downloads. It checks all members, including
bounded nested archives (also identified by ZIP/gzip/xz signatures), and rejects
mixed architectures, unsafe tar paths,
foreign Windows/macOS native formats and unsupported ELF classes. Unqualified static archives and
nested Zstandard streams fail closed. Inspection is
bounded by 4 GiB expanded size, 100,000 members, nesting depth and a 256 MiB
metadata-tool output limit. Unsupported formats fail with an actionable error.
Payload ISA checks establish neither publisher authenticity nor application
runtime compatibility. AppImage checking covers the outer ELF runtime; it does
not certify every file in an embedded SquashFS image.

The official installer additionally consumes the release's SHA-256 manifest.
Standalone bootstrap code comes from the release tag's resolved immutable source
commit over HTTPS. Checksums are not a replacement for signed provenance; no
new publisher-signature guarantee is claimed. There are no force-architecture,
dependency-bypass or unsigned-Snap installation fixes.

## Curated and generated routes

`p3/app/architecture-routes.json` is an explicit M1 route inventory. Existing
curated shell bodies are pinned by SHA-256; catalog declarations are pinned by
canonical JSON digest and repository identity. These declarations retain the
historical x86 route baseline. They are not new third-party runtime guarantees.
Only the three data-only font routes currently receive ARM64 curated eligibility.
Other ARM64 feature promotions require individual qualification.

Changed/new curated scripts need a reviewed `# architectures: x86_64, aarch64`
header or an updated reviewed digest. Missing declarations fail, including in
developer mode. Generated package/removal scripts explicitly declare their host
scope and still call payload/package guards. Architecture metadata is a contract
for trusted installer code, not a sandbox for arbitrary shell or downloaded
third-party installers.

After reviewing a shell change, use `python3 dev/refresh_architecture_routes.py`
to refresh **existing** digests; it never adds routes or promotes architectures.
Catalog changes require review and updating `declarations` with the SHA-256 of
`json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`.
A remote script/catalog change cannot inherit eligibility solely by keeping its
previous display name. Remote scripts using M1 helpers require an M1 client;
coordinate their rollout with the existing minimum-client-version mechanism.

Entry points check eligibility before a script preamble, hook or developer
bypass can execute. Shared helpers validate complete payload batches before
installation, chmod, previous-version removal or privilege prompts. Native APT
availability/dependency simulation precedes authentication. Source-build payload
inspection precedes build-dependency installation. Native package preflights on
other managers query their available metadata; complete solver/runtime
qualification remains distribution-specific. Snap Store preflight reads the local
snapd architecture and its host-filtered latest/stable candidate before
authentication; an absent daemon must be configured separately. Local Snap files
remain refused. Homebrew installation dispatches retain x86-only eligibility
until the bottle/source execution path is qualified for ARM64.

Fixed-x86 routes remain unavailable on ARM64 instead of receiving speculative
replacement URLs, amd64/i386 repositories or multilib workarounds. Hiddify,
Kind/kubectl and k6 now use the central selector/labels; targeted Godot, Toolbox,
Positron and RStudio paths validate staged payloads before installation. This
neither promotes those applications to ARM64 nor verifies their upstream builds.

## Flatpak runtime extensions and rollback

`architecture_flatpak.py` resolves the complete requested batch using
`remote-info --arch=<native> --show-ref` before an installation starts. Missing
remotes must be configured separately; a failed app preflight does not bootstrap
one. Foreign explicit refs are rejected.

`pkg_flat_extension APP_ID EXTENSION_ID` reads the **installed** application's
runtime, the runtime's Extension `version`/`versions` metadata, origin remote and
installation scope. It verifies the exact native refs in that origin/scope.
GNOME/KDE runtime version numbers are never guessed to be Freedesktop extension
branches. The same scope and exact ID/architecture/branch appear in transaction
records and rollback. Legacy unscoped records remain readable; new scoped
records never remove an identical ref from the other installation.

Gamescope, MangoHud, Intel VAAPI and OBS routes no longer request fixed x86
branches. Gaming extension dependencies currently identify installed Steam as
the target runtime; they fail clearly when that target is absent. Volt's external
`make flatpak-install-user` route is blocked before installation because its
bundle/build preflight is unqualified, rather than recording guessed rollback
refs or silently changing its software source.

## Verification and remaining qualification

Run `python3 -m unittest discover -s dev/tests -v`. Fixtures cover aliases,
unknown/ARM32 hosts, x64 AppImages on ARM64, amd64/arm64 DEBs, reverse x86 cases,
unlabelled assets, explicit data/source, mixed/nested archives, zero/multiple
assets, conflicting metadata, reviewed-route tampering, package availability,
Flatpak origin/runtime branches, scoped rollback and mutation-order guards.
The DEB fixture test builds and inspects tiny packages; it never installs them.

M1 validation used macOS arm64/Python 3.13.7 and an isolated Ubuntu AArch64 VM
copy under `/tmp`, with Python 3.14.4 and Rust/Cargo 1.93.1. The Desktop checkout
was not changed. Cargo's locked dependencies and unpacked verification tools
were confined to `/tmp`; no system packages or maintainer scripts were installed.
Final verification results:

- macOS: 36 focused tests, 35 passed and the Linux `dpkg-deb` fixture skipped.
- Ubuntu ARM64: all 36 focused tests passed, including actual DEB metadata/payload
  inspection; all 39 existing Rust catalog tests passed; locked offline native
  catalog build and PyO3/frontend integration smoke checks passed.
- Read-only native APT candidate/dependency preflight (`bash`) and snapd Store
  candidate preflight (`hello-world`) passed in the VM; neither package was installed.
- Ruff 0.12.3 lint and formatting checks passed for new Python modules/tests/tool.
  AST parsing and `bash -n` passed for changed files. ShellCheck 0.11.0 at error
  severity passed for changed shell files; rustfmt 1.8.0 passed for changed Rust
  bridge functions. `git diff --check` passed.
- Fatal Python lint across existing changed modules still reports the base
  revision's undefined `logger` at `p3/app/tui/runner_helper.py:1273` (F821).
  No new fatal lint finding was introduced; that unrelated defect remains open.

These checks qualify the tested catalog build and eligibility paths, not the GTK
GUI or the entire application distribution.

Still unqualified: native amd64 execution (policy/selector regressions are covered
with fixtures), GTK/ctypes GUI builds, end-to-end third-party installs, live
Flatpak extension installs, hardware/kernel features and full additional-distro
solvers. Local Flatpak/Snap/eopkg file payloads are refused until their native
inspection path is qualified. Packages containing non-Linux or unrecognized
native formats may now be refused even on x86; resolve those with explicit
payload evidence, not a permissive fallback. No DEB/RPM release pipeline,
GitHub publishing or ARM64 AppImage support claim is introduced.

## M2 qualification boundary

[ARM64-QUALIFICATION.md](ARM64-QUALIFICATION.md) supersedes the historical M1
"unqualified GUI" status for the exact native environment and probes recorded
there. It distinguishes builds, imports, UI exercise, feature lifecycle tests
and unverified runtime/distribution work. Native amd64 remains unavailable;
fixture-based x86 regression is not described as native qualification.

Compressed gzip/xz members are bounded and inspected after decompression, whether
they contain tar archives, documentation or native binaries. Explicit independent
metadata still cannot conceal foreign code. No unknown native payload becomes
compatible through this correction.

The initial font routes pin exact source/release assets and SHA-256 values, use
private staging, validate font data before installation and perform user-only
writes without elevation. Existing contents are snapshotted and paths remain
within the user profile. A prior backup or a symlink conflict requires resolution
before mutation. Updates to pins require review; automatic tracking of upstream
`latest` and arbitrary version migration are outside the demonstrated scope.

Remote scripts with different bodies remain refused. The qualified bundled
snapshot and its client must be rolled out together upstream; M2 does not promote
older or newer remote bodies merely to keep a menu entry visible. Window closure
also preserves shared runner/rollback state instead of deleting `/tmp/linuxtoys`.
