# ARM64 support and development status

Updated 2026-11-15. Development branch: **`arm64-support`**. This summary covers
the work through source commit `02b4d92766e5c8310d468662cd0c2f4157d43167`.
Historical reports retain the source IDs and conditions actually tested.

## Current support

LinuxToys has an experimental native Ubuntu ARM64 path with central architecture
enforcement, native Rust/Python integration and a bounded set of qualified
installation routes. The tested environment is Ubuntu 26.04.1 AArch64 on a
native ARM64 VM, with GTK3, VTE, Wayland and Xwayland. No AMD64 emulation was used.

| Area | Verified scope |
| --- | --- |
| Native application | Locked native Rust catalog/GUI builds, Python imports, ctypes/PyO3 ABI checks, CLI/TUI and bounded GTK/VTE checks at the source milestones recorded below. |
| Desktop backends | Wayland and X11 through Xwayland. Standalone Xorg, hardware acceleration and long-duration stability remain unqualified. |
| ARM64 installation routes | Atkinson Hyperlegible, OpenDyslexic and Nerd Fonts: pinned independent font data, fresh/existing user directories, integrity failures, removal and restoration. Interactive Nerd Fonts selection was not separately qualified. |
| Ubuntu ARM64 packaging | A local M4A DEB and its install/upgrade/downgrade/remove/reinstall/purge and fault-recovery cases were qualified in disposable native environments. That historical artifact predates the later source fixes. |
| Nala | Actual Ubuntu `0.16.0` architecture-independent payload inspected. The two package-state defects are fixed and query/control-flow tests pass; the full route remains disabled pending real isolated lifecycle qualification. |
| F3 | Actual Ubuntu `9.0-1build1` ARM64 payload inspected. Its separate documentation hook remains approved only for x86-64; the ARM64 route remains disabled. |
| Other applications/distributions | Require route-specific payload, dependency, privilege, integrity and lifecycle evidence. ARM64 filenames or architecture-independent package metadata alone do not grant approval. |

Existing x86-64 eligibility and selector fixtures remain active. They do not
establish fresh native AMD64 build/runtime qualification. ARMv6/ARMv7, ARM64
RPM/AppImage release packages and broad ARM64 support across the upstream
distribution list are not qualified by this work.

## Implemented features and safeguards

**Architecture and payload checks.** A central policy normalizes host architecture
names and refuses unknown/foreign/mixed payloads. Reviewed scripts, catalogs and
hooks are source-bound. Native package/dependency preflight, asset selection,
ELF/DEB/archive inspection and Flatpak runtime/extension architecture resolution
run through the existing installation boundaries. Independent data requires an
explicit reviewed declaration. See [architecture policy](ARCHITECTURE-POLICY.md).

**Safe font routes and native integration.** The three initial font routes use
pinned bytes, private staging, checksum/payload validation and user-only writes.
Existing user content is preserved through tested removal/restoration paths.
Native build fixes retain Cargo's lockfile, correct target/vendor discovery and
the existing GUI ABI. Runner shutdown preserves shared rollback state, and
recorded filesystem reversal paths remain complete and shell-quoted. See
[native ARM64 qualification](ARM64-QUALIFICATION.md).

**Client/script compatibility.** The client approves exact bundle bytes, script
API, architecture-policy digest and revision IDs. Synchronization validates
private staged content before promotion and retains an approved cache/bundle
when remote content is unavailable or refused. Failed restoration retains
recovery material. Developer mode grants no architecture or bundle bypass.
The preparation workflow produces review artifacts through a manual trigger;
it does not automatically publish a script mirror. See
[script rollout](SCRIPT-ROLLOUT.md), [preparation](SCRIPT-PREPARATION.md) and
[native preparation qualification](SCRIPT-PREPARATION-ARM64.md).

**Local native DEB construction.** The DEB path checks native architecture,
rebuilds locked native libraries in private staging and locates Python/native
components together under `/usr/lib/linuxtoys`. Hidden script metadata,
permissions and derived native dependencies are verified. Construction is
separate from signing/upload/publication. See
[DEB qualification](ARM64-DEB-QUALIFICATION.md) and
[installed runtime qualification](ARM64-RUNTIME-QUALIFICATION.md).

**Selected upstream reliability fixes.** Changes adapted from upstream 7.10.1
and 7.10.2 include:

- A shared atomic-write helper used by the Homebrew formula and Antenna history
  caches, preserving caller serialization, permissions and failure behavior.
  It publishes complete replacements through unique sibling temporary files.
  File fsync is optional; directory fsync and read-modify-write locking are not
  provided, and an uncatchable process exit can leave a staging orphan.
- Antenna's parent AppStream-log import, empty/cancelled-report handling, VTE
  string/tuple buffer extraction with viewport fallback, child-exit propagation
  and CLI EOF cancellation. Tests intercept reporting; they send no live report.
- Four loader entry modes: direct file, `python -m app.library_loader`, package
  import and standalone API import. Trusted path bootstrap and the architecture
  guard still precede script-body use.
- AppImage catalog package/direct invocation compatibility with trusted imports
  and fail-closed policy handling. Native tests use local metadata and inert
  fixtures; no real AppImage was mounted, executed or installed.

The loader writer, unrelated upstream changes and version markers were retained.
The atomic-I/O follow-up found no compatible durability improvement to import.
The upstream LATENCYDEVIL change did not apply to the locally resolved catalog
route, so its script/approval bytes were retained.

**Debian package-state correctness.** `pkg_exists` now checks validated dpkg-query
status, distinguishing genuine installation from retained conffiles and
incomplete states. Incomplete installations reach the existing recovery guard,
then are re-queried; repaired pre-existing packages are excluded from new-install
transaction records. Unknown/query-error states fail closed. Partial packages
remain removable, and pacman/RPM/eopkg branches are unchanged. See
[the package-state fix](NALA-PACKAGE-STATE-FIX.md).

## Evidence and test results

Native evidence applies to the exact source/artifact and controls recorded by
each milestone. A prior package or GUI result does not automatically qualify a
later source tree as a new released package.

| Milestone | Completed evidence |
| --- | --- |
| M1–M2 | Native catalog and GUI builds, 39 Rust catalog tests, ABI/GI checks, CLI/TUI/MCP and Wayland/Xwayland probes; three reviewed font routes and adversarial lifecycle scenarios. |
| M3 | Exact script revision/manifest validation, adversarial rollback/offline behavior and native deterministic review-artifact preparation. No publishing workflow was executed. |
| M4A–M4B | Local ARM64 DEB construction and disposable package lifecycle/fault tests; installed CLI/TUI/GTK/VTE/desktop checks under the bounded controls in the reports. Default startup/filtering and cold-launch diagnostics retain their documented limits. |
| U1, `20be59de` | Fresh locked/offline native builds and 39 Rust tests; 114 Python regressions; real ext4 replacement/concurrency/interruption checks and GTK/VTE checks on both backends. No package or report was published. |
| Loader, `f39d2c07` | 12 focused and 110 existing native tests, plus 14 real module/policy entry cases with shell execution intercepted. |
| AppImage catalog, `f8a76280` | 146 final native unittest cases and 14 separate loader/policy cases. HTTP and payload data were fixtures; no real AppImage lifecycle ran. |
| Package-state fix, `02b4d927` | **173 tests passed natively**; **158 passed and 15 skipped on macOS**, where dpkg-query is unavailable. Real native queries use temporary databases; mutating package commands and recovery operations are fakes. |

The last fix passed Black, Pyflakes, Python AST, Bash syntax and whitespace
checks. ShellCheck was unavailable for that phase. No package transaction,
nested sandbox attempt, native rebuild or route promotion was performed by it.

Raw U1/loader/AppImage qualification logs are retained locally under ignored
`target/` directories. Versioned milestone reports contain compact evidence;
raw archives, recovery data, credentials, VM profiles and local tools are not
part of the fork's source publication.

## Remaining qualification and release work

1. Run native AMD64 build/runtime regressions on actual AMD64 hardware.
2. Qualify Nala's actual install, failure, interruption, rollback, removal and
   reinstall path in a suitable disposable environment. The previous Docker/
   Bubblewrap attempts stopped before package bootstrap; they do not count as
   lifecycle passes. F3 additionally needs independent client-controlled hook
   review. Neither route has been promoted.
3. Rebuild and qualify a new ARM64 package for the final source and complete
   normal startup/filtering, deployment and distribution-specific release gates.
4. Coordinate client and exact script-bundle adoption with the upstream
   maintainers before release. Pushing this development branch to a fork grants
   no script-revision approval and publishes no binary release or mirror tag.

The earlier VM qualification environment drifted through a scheduled unattended
glibc/Pillow update. The package-state fix preserved all 2,294 monitored records
relative to its own current starting state; it did not restore the earlier VM.
Historical attribution/evidence recovery and missing-checkpoint caveats remain
documented in the milestone reports. Their original claims and source IDs have
not been rewritten for this summary.

## Building and testing

Use a disposable native Linux environment with the existing locked dependencies
and follow [the build documentation](build/README.md). Upstream install commands
in the main README install the upstream distribution, not this development
branch. There is no new downloadable ARM64 release associated with this push.

The full unittest discovery includes package-producing and local-Git fixtures;
review their effects before running them. The most recent constrained selection,
query-only native controls, exact commands and preservation receipts are in
[NALA-PACKAGE-STATE-FIX.md](NALA-PACKAGE-STATE-FIX.md). Reproduce the relevant
milestone's controls when comparing results rather than treating fixture counts
as real installation or release qualification.
