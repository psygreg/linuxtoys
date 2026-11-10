# Native ARM64 qualification (M2)

Date: 2026-11-09. Baseline: M1 `97bde46b60542aaca3b60a4ba57e8210119d6f12`.
Scope: native Ubuntu 26.04.1 AArch64, not an ARM64 distribution/release announcement.
See [the assessment](ARM64-ASSESSMENT.md), [policy](ARCHITECTURE-POLICY.md), and
[qualification evidence](arm64-qualification-evidence.json).

## Environment and isolation

The VMware guest runs Python 3.14.4 and Rust/Cargo 1.93.1. GTK is 3.24.52,
PyGObject 3.56.2, GLib 2.88.0, Cairo 1.18.4, VTE 0.84.0 and AppStream 1.1.2.
The host is an Apple M3 Pro; Linux tests ran in the AArch64 guest over SSH.
No emulation or native amd64 runner was used.

The Desktop checkout and installed system packages were untouched. The test tree
is `/home/ta/linuxtoys-m2-qualification`, also reachable as `/tmp/linuxtoys-m2`.
It was moved from tmpfs after its quota interrupted tool staging. Ninety-five
exact-version Ubuntu packages were downloaded using authenticated APT metadata
and extracted into a private sysroot; the solver plan required **zero upgrades**.
No package maintainer script, system install, service enablement or repository
change was performed. Test profiles disabled automatic application updates and
clock correction, and setup/install prompts were declined. Staged development linker symlinks were relocated to the
VM's existing AArch64 runtime libraries. These extractions are test prerequisites,
not a claim that an unprepared stock image can build the application.

Maturin 1.9.4 was staged as a build tool in that workspace. Project manifests,
requirements and `Cargo.lock` remain unchanged. Textual 8.2.8 and pyte 0.8.2 retain
the existing pins; the resolved pure-Python transitive versions are recorded in
the evidence. All Rust artifacts were built from source in a fresh target tree.

## Qualification results

| Area | Evidence and scope |
| --- | --- |
| Rust catalog | Locked native debug and release builds; Python 3.14 import of the abi3 extension; existing 39 Rust catalog tests passed. |
| Rust GUI | Locked native debug and release builds; ctypes discovery loads the newly built library; ABI version 20. |
| ELF/linker | Both libraries are ELF64/AArch64; linked GTK/GDK/Pango/Cairo/GIO/GObject/GLib libraries resolve. No x86 prebuilt `.so` was staged. |
| Native ABI | Eleven actual Rust `repr(C)` declarations compiled with native rustc and compared against every Python ctypes size, alignment and field offset; pointers are 8 bytes. |
| GI | GTK3, GDK, GLib, GObject, GIO, Pango, GdkPixbuf, VTE 2.91, AppStream 1.0 typelibs and GI Cairo conversion imported. |
| GUI | Main window and actual `linuxtoys.py --gui` launcher exercised on Wayland and X11 **via Xwayland**; first-run setup declined; normal close returned successfully with both debug and release libraries. No standalone Xorg session was tested. |
| Widgets | Native card/sidebar construction, destruction and text rendering exercised. VTE spawned a harmless native shell, displayed its output and reported child exit 0 on both backends. Resident memory was unchanged between cycles 10 and 100 on each backend; this is a bounded smoke check, not a general leak proof. |
| Search | Bundled qualified-font search returned results in GUI, TUI and MCP with connection failures injected. Live synchronization can replace bundled scripts with unqualified remote revisions; see the rollout blocker below. |
| CLI/TUI | Real `--help`, `--version`, `--list` entry points passed; actual TUI pseudoterminal startup/exit and Textual pilot search passed without a display. |
| MCP | Actual headless server health, initialize, 26-tool discovery, authenticated font search, unauthenticated refusal and clean interrupt shutdown passed. No install tool was invoked. |
| Optional backends/offline | Process-scoped connection failures exercised with local GUI/MCP IPC retained; snapd access refused. The unavailable AppImage search error path was injected and recovered. This is fault injection, not a host-wide network sandbox. |
| Updater | Actual installer functions reject a foreign release before privilege in a Linux fixture. Native selection/payload tests remain active. No real application/package upgrade or release installation was performed. |

Initial GUI probes incorrectly destroyed a parent while its first-run modal was
open, producing a timeout/segmentation fault. Corrected probes decline the modal
and use normal window closure; these pass on both backends. No general claim of
crash freedom, long-duration stability or hardware feature support follows.

The final Python suite has 46 tests: all pass on Ubuntu ARM64; macOS passes 43
with three Linux-only skips. The Rust workspace has 39 catalog tests and no GUI
unit tests; GUI coverage comes from the native ABI and application probes.

## Initial feature set

| Route | Verified native guest behavior |
| --- | --- |
| Atkinson Hyperlegible | Six fonts from Google Fonts commit `5bb28733cec313b63fbd415b574b5ae35c8aa8b8`; pinned SHA-256 checks, fontconfig visibility, registry detection, fresh removal and restoration of existing user contents. |
| OpenDyslexic | Four fonts from the repository resource pinned to upstream commit `83244aaf1ca5427e5dd57133f6eaf92a6cc1627d`; same lifecycle checks. |
| Nerd Fonts | All five headless selections, 210 font files from v3.5.1; exact named independent-data assets with pinned SHA-256, same lifecycle checks. Interactive selection UI was not separately qualified. |

Fifteen scenarios cover fresh and existing directories, offline, unavailable and
tampered downloads across all three routes. Live pinned downloads and lifecycle
checks passed. A later live repeat hit a 120-second upstream timeout and refused
before installing; final reproducible repeats explicitly replay the original
12 downloaded artifacts through the same production checksum, architecture,
fontconfig, install and rollback checks. Production has **no cache fallback**.

Downloads are staged privately and inspected as explicit independent data before
installed font paths change. User-only writes never escalate privileges;
escaping parent symlinks, destination font symlinks and existing `.bak` snapshots
are refused. Existing directory contents are snapshotted for rollback. Checksums
pin reviewed bytes; they do not assert an independent publisher signature.
Font versions do not automatically track `latest`: changing a pin requires source
and hash review. Replacement/restoration is tested; arbitrary future-version
migration and multi-update history are not qualified.

Three additional Ubuntu-native candidates have verified `Architecture: all`
metadata and inspected independent payloads: IBus Typing Booster 2.30.4-1,
HTTPie 3.2.4-4 and Nala 0.16.0. They were **not installed or promoted**. Their
native runtime dependencies and full feature routes still need qualification.

## Corrections made during qualification

- Build drivers enforce `--locked`, honor the actual `CARGO_TARGET_DIR`, and find
  the vendor root relative to the script rather than a checkout directory name.
- Shared font helpers pin/check data and preserve user contents. The three
  existing ARM route digests were refreshed without promoting other features.
- Filesystem rollback preserves and shell-quotes the complete recorded path.
  Window shutdown no longer deletes shared `/tmp/linuxtoys` runner state.
- The TUI's existing undefined error-path logger is initialized and its recovery
  path exercised. M1's recorded F821 is resolved.
- Bounded gzip/xz inspection distinguishes compressed documentation from tar
  containers. Foreign ELF and unknown native formats remain rejected after
  decompression, including disguised members; missing metadata remains unknown.

## Remaining blockers and boundaries

Historical M2 status below is retained as evidence. The local-only compatibility
follow-up is documented at the end of this report and in
[SCRIPT-ROLLOUT.md](SCRIPT-ROLLOUT.md); live rollout is still pending.

1. **Remote script rollout:** a live synced Atkinson script had digest
   `1ba44470f759b1ada886f25bf5bcc649dc704ec2ab06827ddd68c14eda118caa`, which
   the M2 policy correctly refused. Online GUI font search returned zero groups
   after synchronization, while the bundled offline snapshot returned one.
   Coordinate matching client/script publication and minimum-client-version
   handling upstream before advertising this feature set. No permissive fallback
   or publication was added here.
2. **Native amd64 infrastructure:** unavailable in this session. Existing x86
   alias/asset/optimizer/route fixtures pass, including explicit amd64 DEBs and
   x64 AppImages. They do not establish native amd64 builds or runtime regression
   qualification. No emulation was substituted.
3. **Unqualified scope:** release package installation/upgrades, DEB/RPM pipelines,
   ARM64 AppImages, non-Ubuntu solvers, hardware/kernel features, arbitrary third
   party applications, a standalone Xorg session and long-running resource tests.
4. Package development/runtime prerequisites must be documented and provided in
   a clean native build environment. ARMv6/ARMv7 remain unsupported.

No project dependencies or release publishing workflows were changed. No UI
layout or visible copy was changed.
Recommended next milestone: native amd64 regression infrastructure plus coordinated
Ubuntu ARM64 source/packaging qualification, before any release-support claim.

## Quality checks and reproducibility

New Python probes/tests and changed payload inspection pass Ruff 0.12.3 lint and
format checks. Changed Python modules pass fatal-error lint and AST parsing;
changed shell scripts pass `bash -n` and ShellCheck 0.11.0 at error severity.
Warning-level font checks retain SC2154 for variables supplied by runtime language
files (`finishmsg`, `msg018`); excluding that established dynamic-source diagnostic
leaves no warning. The C connection-failure fixture compiles with
`-Wall -Wextra -Werror`. `git diff --check` passes. No generated libraries, wheels,
profile data or authentication credentials belong in the commit.

Use the build instructions in [dev/build/README.md](build/README.md). Application
probes require a **new** `--profile` directory; their network/optional-backend
results require the explicit fixture/environment used in the evidence. Fault
injection retains local GUI/MCP IPC and does not change host networking. Successful
GUI search in the qualified bundled snapshot does not qualify unmatched remote
script revisions. Re-run on a native amd64 host before asserting x86 runtime parity.

## Local script compatibility follow-up (2026-11-10)

The [rollout report](SCRIPT-ROLLOUT.md) resolves the local cache/client mismatch
without accepting unqualified remote revisions. The production lock approves a
single API-1 manifest; all three existing ARM64 font routes retain their ISA scope
and add an early client-helper guard. Publication has not occurred.

The final suite passes **68/68 on Ubuntu ARM64**; macOS passes 65 with the same
three Linux-only skips. Twenty-two new tests cover approval, API/policy conflicts,
stale/unknown/tampered content, offline sources, partial synchronization, process
exclusion and rollback failures. Existing x86 eligibility/selector tests remain
fixtures, not native amd64 evidence. Ruff lint/format, fatal lint for existing
changed modules, Python AST, Bash syntax, ShellCheck error checks, manifest
check/export and diff whitespace checks pass.

An isolated loopback TCP Git service supplies the intended approved revision to
the actual native catalog. Search finds Atkinson, OpenDyslexic and Nerd Fonts;
the early validators and CLI preparation accept their original approved files.
Tampering under the same tag is refused before promotion; search still works
with the approved cache and, after its removal, the bundled snapshot offline.
Actual GUI font search returns one Atkinson group and closes normally on both
Wayland and X11 via Xwayland (12.13/12.45-second bounded probes). Native imports,
TUI search/shutdown, CLI help/version/list and authenticated MCP search/shutdown
also pass. CLI uses `EASY_CLI=1` and declines the existing updater prompt via EOF.

Tests reused unchanged M2 native release libraries and staged exact dependencies;
no Rust rebuild, package/font installation or system upgrade was performed.
An initial TUI probe lacked the retained vendor path; a corrected run reused it
successfully. Evidence, commands, profiles and limitations are recorded in
[script-rollout-evidence.json](script-rollout-evidence.json).

Still required: native amd64 regression and separately authorized, coordinated
upstream rollout. At M3A, the automatic sync omitted the hidden manifest. The
subsequent [preparation follow-up](SCRIPT-PREPARATION.md) replaces that design
locally; it adds no native application evidence or publisher. No workflow was
run, no upstream write occurred, and packaging qualification has not begun.
