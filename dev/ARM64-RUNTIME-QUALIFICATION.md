# Ubuntu ARM64 VM runtime qualification (M4B Phase 2)

Date: 2026-11-12. Baseline: `9ae26107554e54ddfb6f1f927150f3e58bcdc1d9`.
Result: **bounded runtime checks completed successfully on the actual VM**.
This qualifies the checks and configuration below, not default-mode behavior,
native AMD64, standalone Xorg or other distributions.

The existing `linuxtoys 7.9.8-1~m4a1 arm64` installation was retained. Both
artifact copies matched SHA-256
`83173db3b42d8ef966b6bde02f064beb42ee71b4593bfd727a3fefefdb862f04`.
All 1,830 installed payload files matched the artifact's hashes, ownership and
modes before and after testing; no extra private application files appeared.
`dpkg --audit` and `dpkg --verify linuxtoys` remained clean.

## Environment and controls

Tests ran as `ta`, UID 1000, on the existing Ubuntu 26.04.1 AArch64 VMware VM,
with Python 3.14.4, GTK 3.24.52, VTE 0.84.0 and vendored Textual 8.2.8.
The active GNOME session was Wayland. X11 checks used its actual
`/usr/bin/Xwayland` process and display `:0`; no Xvfb or standalone Xorg was used.

A private disposable HOME and XDG directories held test state. Its cache was
seeded from the verified existing user cache. Automatic updates and error
reports were disabled in that profile. The application's supported `DEV_MODE=1`
suppressed script synchronization and update checks. No `COMPAT` or `CONTAINER`
override was set. Developer mode changes compatibility filtering, so normal
compatibility filtering and default non-developer startup are **not qualified**.
HTTP proxy variables pointed to `127.0.0.1:9`; this is not a network-isolation
claim. Existing system metadata was available; the application's missing-APT-
metadata refresh precondition was false.

Only installed files under `/usr/bin` and `/usr/lib/linuxtoys` were exercised.
Instrumented GUI probes ran the installed `linuxtoys.py` entry with test-only
GLib observers. A separate cold desktop-entry launch ran the actual installed
executable without an in-process test driver. No checkout application code or
replacement native library was loaded.

## Functional evidence

| Check | Actual result |
| --- | --- |
| Native Python/Rust ABI | Installed PyO3 extension, GI, Cairo, Textual and pyte imported; installed GUI library loaded with ABI 20. Native indexing read 161 bundled scripts, including four font-related entries. |
| CLI | Actual `/usr/bin/linuxtoys --version`, `--help` and `--list` exited 0. Version was 7.9.8 and the catalog included font entries. There is no standalone public CLI search command; only filtering the list output was checked. No positional query was used because it can imply installation. |
| TUI | Actual installed executable ran in a 140×40 PTY. Explicit input focus produced the `font` query and visible font results, including Nerd Fonts and FontForge. Keyboard quit exited 0. |
| Wayland GUI | Confirmed `GdkWaylandDisplay` on `wayland-0`, mapped `GdkWaylandWindow`, font search view and font labels. Normal window closure/application quit returned successfully. |
| Xwayland GUI | Confirmed `GdkX11Display` on `:0`, mapped `GdkX11Window`, font search and normal closure/application quit. |
| Native widgets | Installed Rust GTK library created a native card, exposed through PyGObject as `GtkEventBox` in a flowbox, on both backends. |
| VTE | On both backends, a real VTE child ran only `/usr/bin/printf`, exited 0 and produced `M4B VTE OUTPUT OK`. Supported text extraction verified the output. This did not exercise the installer execution pipeline. |
| Desktop entry | `gio launch` of the installed desktop entry exited 0 and reused the existing primary D-Bus owner. A later cold launch started the installed `/usr/lib/linuxtoys/linuxtoys.py --gui` as UID 1000. The user searched and closed it normally; the process disappeared and the application bus name was released. |
| URI/MIME registration | `linuxtoys` scheme and Debian package defaults remained `toys.linux.LinuxToys.desktop`. Registration was queried only; no installer URI or package file was opened. |

## Visual observations and probe failures

Automated VMware console captures were black, even while GTK reported a mapped
window and the compositor reported a display. Visual passes therefore come from
the user's explicit observations in this chat, not screenshots or widget counts:

- Wayland: readable font search results, native card and VTE output.
- Desktop activation: expected icon and one application group.
- Xwayland: readable font search results, native card and VTE output.
- Cold installed launcher: startup, icon/grouping, readable font search and
  manual normal close all worked.

The first TUI probe did not focus its search field. It established startup/exit
only; the focused repeat established search. The first Wayland VTE observer used
deprecated `get_text`, which returned `None` with a VTE critical message and a
probe callback `TypeError`. The probe was corrected to
`get_text_format(Vte.Format.TEXT)`; a separate Wayland repeat verified output and
exit, and the corrected Xwayland probe passed. These were observation-driver
failures; no application changes were made. No unexpected setup, credential,
installation or system-change dialog was observed during the probes.

The cold desktop-launch log also contained `Authorization required, but no
authorization protocol specified` and `xcb_connection_has_error() returned true`.
The user confirmed working Wayland startup/search and normal manual close; the
process and bus name were subsequently absent. The launch environment set
`DISPLAY=:0` without explicitly setting the session `XAUTHORITY` path, which is a
possible test-environment cause, not a verified root cause. This diagnostic is
retained as unresolved; authentication settings and permissions were not changed.
The instrumented Xwayland and corrected standalone VTE probe stderr logs were
empty.

Initial fresh SSH authentication failed. Automatic approval review initially
blocked locating the existing connection; the user explicitly authorized that
lookup, and the authenticated preflight connection was reused without changing
credentials. This access blocker was resolved before recovery preparation.

## Performance evidence

No performance benchmark or acceleration qualification is claimed. CLI version
and help took about 0.3 seconds each, and listing about 2.05 seconds. Instrumented
mapped-window observations were approximately 2.83 seconds on Wayland and 2.34
seconds on Xwayland, with 300 ms polling and a seeded cache. These are individual
observations, not a backend comparison or a cold-cache benchmark. PTY capture
delays do not measure TUI startup latency.

Swap was already heavily used: 3,159,036 KiB total, with only 236,996 KiB free at
the pre-test recheck, 235,488 KiB at Wayland startup and 235,916 KiB at Xwayland
startup (about 2.79 GiB used). The machine-readable evidence records final memory
conditions. No swap or system tuning was performed. Snapshot memory saving took
several minutes and was completed before runtime measurements.

## Recovery and preservation

VMware snapshot **`M4B-PRETEST-2026-11-12-M4A-9ae26107`** completed successfully;
the snapshot list, metadata and VMware completion log verified it. It includes
the already-installed M4A package and the current recheck state.

Private recovery data remains in
`$HOME/linuxtoys-m4b-recovery-20261112` in the guest: directory mode 0700,
archive/manifest/verification files mode 0600. The archive verified 248 members
against live content hashes, modes and ownership; absent paths and MIME/service
state were recorded. Archive SHA-256:
`00891c4704ae336e310d6563969acc04d7313ad06fa37332269be156d44ff3c1`.
It was reverified after testing. Raw backups were not copied into Git.

Preflight drift was found **before runtime**. Guest package logs record an
unrelated `xarchiver` install with `7zip` and `bzip2` at 12:44:48–12:44:50 on
November 12. The existing LinuxToys cache had grown from 15 files/23,930,716
bytes at preflight to 240 files/46,875,997 bytes at recheck; its cause was not
established. The configuration still contained one 22-byte file. These existing
differences were documented and retained, not overwritten with preflight state.

The final checks, including after the cold launcher and cleanup, found:

- Identical pre-test/final package database fingerprints, monitored dpkg/APT
  files, repository definitions and system integration caches.
- All 1,830 installed payload files intact; package audit/verification clean.
- Identical monitored original configuration/cache/data and MIME preferences,
  with the original absent paths still absent and MIME defaults unchanged.
- MCP unit still `not-found`, `inactive`, `dead`; no LinuxToys process remained.

Both disposable-profile uses were removed after evidence capture. No original
user-state restoration was necessary, and no snapshot reversion occurred. The
snapshot and verified private backup remain available. No package installation,
reinstallation, upgrade, removal, dependency change, APT refresh, repository edit,
service enablement, font/third-party installation, installer URI dispatch or
automatic update was performed by this qualification.

## Evidence and remaining limits

[Compact evidence](arm64-runtime-qualification-evidence.json) is versioned with
this report. The requested local report, raw probes, before/after manifests,
snapshot/backup verification, PTY captures and logs are under the ignored
`target/m4b-runtime/` directory. Raw evidence and recovery data stay local.

Installation/lifecycle/fault recovery, installer execution, service activation,
default-mode startup, compatibility filtering, hardware acceleration, native
AMD64 and broader distributions remain untested by M4B. URI/MIME registration
does not establish installer dispatch. No application changes, push,
publication, deployment or remote Git operations were made.
