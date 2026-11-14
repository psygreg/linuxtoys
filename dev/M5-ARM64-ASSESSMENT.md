# M5: Ubuntu ARM64 application coverage

Assessment started 2026-11-13; continued 2026-11-14. Baseline:
`f8a762806abdbdc31fbf1b07511f2aef797f38a1`. This is an Ubuntu AArch64
assessment, not an AMD64 qualification or a general ARM64 catalog approval.

The complete pinned-route inventory is [m5-route-inventory.csv](m5-route-inventory.csv):
176 script declarations and 51 catalog declarations, plus nine separately pinned
inline hooks in the existing policy. Three font-data scripts were already ARM64
approved. Generic AppStream discovery is dynamic and is not a fixed list of
applications covered by these 227 declarations.

Ten candidates received the detailed review below. The remaining inventory rows
explicitly retain **not individually reverified** status. A matching filename,
an Ubuntu alternative, or a published Flatpak ref does not qualify a different
local installation route. No broad upstream changes are included.

## Ranked candidates

Ranks favor short installation paths, authenticated inputs, small dependency
closures and reversible effects. Counts are native APT simulations from an empty
status database with existing default recommendations, not installed-package
counts or estimates of changes to this VM. No host APT transaction was run.

| Rank | Route and verified availability | Installation path, dependencies and blockers |
| --- | --- | --- |
| 1 | **Nala**: Ubuntu `0.16.0`, `Architecture: all`; actual 148,792-byte package passes unchanged M1 inspection with no native ELF. | `repos.json` native `nala` → Rust catalog → Python materializer/loader → `pkg_install` → complete native APT plan → privilege helper → APT. No hooks or third-party repository. Python 3, python3-apt, anyio/httpx/rich/typer/tomli/pexpect/debian and socksio recommendation; 87-package empty-status plan. Python maintainer compilation/cleanup and `/etc/nala/nala.conf` are inspected. First container candidate; no install/runtime result yet. |
| 2 | **F3 (Fight Flash Fraud)**: Ubuntu `9.0-1build1` arm64; actual 51,010-byte package passes M1 and contains AArch64 ELF. | Same native pipeline; dependencies libc6, libparted2t64, libudev1; 15-package plan; no maintainer scripts. The separately approved inline documentation/browser hook remains x86-only. A catalog architecture addition alone cannot enable the route. Selected for a bounded experiment, with this refusal retained. No block-device testing. |
| 3 | **IBus Typing Booster**: Ubuntu `2.30.4-1` all; actual package passes M1, 151,061,970 expanded bytes, no direct ELF. | `health/accessibility/typeboost.sh` → shared library → authorization → `pkg_install`. Python/IBus/dconf/m17n/dbus/enchant and optional input/audio/accessibility data; 442-package plan. Existing script lacks the early API-1 guard required for a new ARM approval. Input-session behavior, dependencies and removal are unqualified; no promotion. |
| 4 | **Godot Engine 4**: official stable `4.7.2-stable` ARM64 ZIP; hash verified and actual ELF machine 183; M1 passes. | `devs/ides/godot.sh` downloads latest GitHub asset into a temporary area, validates before changing `~/.local/godot`, backs up existing files, and writes icon/desktop integration. Archive, selector and binary names are hardcoded x86_64. Icon/desktop inputs are mutable upstream files without pinned hashes. Native graphical dependencies and rollback need qualification; no script change. Ubuntu godot3 is not this Godot 4 route. |
| 5 | **Maven**: Ubuntu `3.9.12-1` all; signed package metadata and actual package inspected. | `repos.json` native package mapping → common APT pipeline. Requires native JRE, Maven Java libraries, Jansi and Wagon; 160-package plan. Maintainer scripts register/remove alternatives and retain four `/etc/maven` conffiles. M1 rejects the package's doc link and a dependency's Java class content. Java bytecode is not evidence of x86 code; existing format refusal remains intact. Full native JRE closure unqualified. |
| 6 | **R**: Ubuntu `r-base` `4.5.2-1ubuntu2` all; actual `r-base-core` arm64 inspected. | Existing Ubuntu mapping installs r-base/r-recommended; 400-package plan including compiler/runtime recommendations. Core maintainer scripts migrate conffiles, invoke ucf/paperconf, and manage `/usr/local/lib/R/site-library`. M1 rejects a Java class in the package. Existing remove semantics and user/site libraries need careful qualification; no compiler/package-library execution. |
| 7 | **LocalSend**: official stable `v1.18.2` ARM64 DEB hash verified; official Flathub aarch64 stable ref exists. | Local route is an AppStream overlay with `lists/localsend/localsend.sh`, not the vendor DEB. Hook grants storage-drive filesystem permissions through `flatpak_override`; this hook is x86-only. Runtime origin/scope/dependencies and exact rollback need qualification. The DEB's `arm-64` filename is rejected by unchanged M1 as ambiguous `arm`; it is not renamed to evade the check. Ubuntu AppIndicator/xdg dependencies are declared, not runtime-qualified. |
| 8 | **Audacity**: official stable `Audacity-4.0.2` publishes aarch64 AppImage plus API SHA256; actual Ubuntu `3.7.7+dfsg-1` arm64 DEB passes M1. | Current `repos.json` route defaults to GitHub release selection, not Ubuntu APT. Release helper, AppImage payload/runtime/FUSE behavior and exact chosen asset need qualification. The Ubuntu alternative has GTK/audio/codec dependencies and a 344-package plan. Its inspected DEB is not evidence that the current AppImage installation/removal path works. |
| 9 | **Blender**: actual Ubuntu `5.0.1+dfsg-1ubuntu1` arm64 package, signed SHA256 verified. | Local URL route runs `lists/blender/blender-pre.sh`, may call ROCm/ICR, scrapes only `linux-x64.tar.xz`, then installs tarball/path link/desktop shortcut. The Ubuntu alternative has a 438-package graphical/media/Python closure; M1 refuses embedded `.blend` data. No substitution of the Ubuntu package or ARM filename into the existing route. |
| 10 | **GIMP**: official Flathub aarch64 stable ref exists; Ubuntu `3.2.2-1ubuntu0.26.04.1` arm64 alternative inspected. | `lists/gimp/gimp.json` adds PhotoGIMP: prompts, starts/kills GIMP, backs up user layout/desktop paths, downloads mutable PhotoGIMP ZIP and copies configuration. This is not a neutral package-only route. Flatpak runtime/payload and patch integrity/user-data rollback are unqualified. Ubuntu alternative has a 471-package plan and is rejected by M1 for an archive link. |

OBS was not selected: the queried official aarch64 stable Flathub ref returned
404, while an Ubuntu arm64 alternative does not qualify its existing Flatpak
runtime-extension/permission route. HTTPie's catalog points to **httpie/desktop**;
old evidence for Ubuntu's HTTPie CLI cannot qualify that different application.

## Input provenance and trust

Public official metadata was retrieved through verified HTTPS. The required
gstack browser could not reliably create an active page; its failure artifacts
are retained. The user explicitly authorized official HTTPS APIs and signed
Ubuntu metadata as the fallback. No browser or package was installed and TLS
verification was not disabled.

Native `gpgv` verified Ubuntu's existing archive signatures. Seven main/universe
ARM64 Packages indexes were independently hashed against signed InRelease
SHA256 entries. The private empty-status closure for the two candidates plus
existing runtime tools contains **149 archives, 43,365,890 bytes**. Every archive
matches its exact signed-metadata size and SHA256, has arm64/all control metadata,
and direct ELF inspection found **597 ELF64 AArch64 files** and no foreign direct
ELF. This does not assert arbitrary embedded/static/bytecode formats were fully
audited. The normal architecture policy and APT signature checks remain required.

Two glibc `2.43-2ubuntu2.4` archives had disappeared from the live mirror. They
were recovered from official snapshot `20261111T120000Z` by exact pre-existing
signed hashes; versions and checksums were not silently replaced. Initial failed
downloads and a harness correction for uncompressed APT indexes remain recorded.

Important exact input hashes:

| Input | SHA256 |
| --- | --- |
| Nala 0.16.0 all | `7b9273a4c6b1091f9132b707f11a7f12679ae0b27e57004c619d18cf2b16ff7d` |
| F3 9.0-1build1 arm64 | `4beeec43517f1863e9c1b9cbc7908574d98c52384d15a5776ff42418b042dfdf` |
| Godot 4.7.2-stable ARM64 ZIP | `5dd0d86405cf7e8adf79fb6377b38ba682a2846cb378ffe5364f38c01ad29b9d` |
| LocalSend 1.18.2 ARM64 DEB | `bbd8347b7979f936d3bae176a3f0d9b81431605707c585270d6240f7670feb1f` |
| Signed UbuntuBase 26.04.1 ARM64 tar.gz, 35,092,106 bytes | `5a1906794ced63a71a8119c3f211ef5f0bbe0a243001b4bbd41fdf80c5b219fd` |

The UbuntuBase checksum signature is valid under existing Ubuntu CD Image key
`843938DF228D22F7B3742BC0D94AA3F0EFE21092`. Vendor GitHub digests are publisher
API assertions over HTTPS, not independent detached-signature verification.
Flathub ref existence does not authenticate or inspect its complete runtime.

Sources: [Ubuntu Nala](https://packages.ubuntu.com/resolute/nala),
[F3](https://packages.ubuntu.com/resolute/f3),
[IBus](https://packages.ubuntu.com/resolute/ibus-typing-booster),
[Maven](https://packages.ubuntu.com/resolute/maven),
[R](https://packages.ubuntu.com/resolute/r-base),
[Audacity](https://packages.ubuntu.com/resolute/audacity),
[Blender](https://packages.ubuntu.com/resolute/blender),
[GIMP](https://packages.ubuntu.com/resolute/gimp),
[Godot release](https://github.com/godotengine/godot/releases/tag/4.7.2-stable),
[LocalSend release](https://github.com/localsend/localsend/releases/tag/v1.18.2),
[Audacity release](https://github.com/audacity/audacity/releases/tag/Audacity-4.0.2),
[UbuntuBase](https://cdimage.ubuntu.com/ubuntu-base/releases/26.04/release/).

## Initial qualification boundary

The native VM is Ubuntu 26.04.1 LTS Resolute, Linux 7.0.0-43-generic AArch64,
Python 3.14.4, uid 1000. macOS host tests use Python 3.13.7 on Darwin arm64.
There is no AMD64 execution or emulation claim.

Host source and policy remain unchanged during preparation. An ignored private
source experiment adds aarch64 only to the Nala/F3 catalog declarations, then
uses existing `dev/prepare_script_rollout.py --write` and `--check` to approve an
exact local policy/manifest/lock pair. The separate F3 hook approval is retained,
so its complete route must fail closed. Experimental revision
`d530b7d3bcbc35872020b592596903f838da05cfe5764739b4c9ea32ad1546ad`
has not been published or accepted by the production checkout.

The existing VM user cannot access Docker's socket and has no cached sudo
authorization. Rootless bubblewrap permits only uid 1000 mapping and denies
setgroups, so it cannot qualify the unchanged sudo path. No privilege shim or
policy bypass is used. The user chose a secure local-terminal handoff for the
prepared Docker driver. Its execution/result remains pending; no container result has been observed.

The prepared driver verifies all inputs, imports only the signed base into a new
native image, creates two bounded containers with no network, host binds,
host devices or privileged mode, and copies inputs. All package/configuration
effects are confined to disposable container writable layers. It records exact
commands/results, then removes only its newly created container/image IDs and
compares pre-existing IDs. It does not invoke host APT, change the VM's services,
or mutate the existing M4A qualification container/image.

Planned checks use the real catalog extension verified against M4A, real policy,
materializer/loader, package helpers, sudo, APT, transaction maps, auto-revert and
registry uninstall. Nala runs only --version/--help. F3, if independently allowed
by all gates, would run only f3write/f3read on an 8 MiB noexec tmpfs, never block
devices. F3's browser GUI action is not qualified. Package code runs as root
inside the container; this does not qualify interactive authentication by an
unprivileged desktop user.

Existing removal/rollback deliberately remove recorded explicit packages without
autoremove/purge. Automatic dependencies and conffiles may remain. Qualification
must report that residue, preserve pre-existing packages/configuration and user
canaries, and dispose the container; it must not claim a complete APT snapshot
rollback. No route is promoted on a failed or unavailable experiment.

## Verification and preservation

Results: **132 existing regressions pass on each host** (122 relevant tests plus
10 upstream-compatibility tests). **Eight focused adversarial fixtures pass on
each host** against the private prospective policy. These
cover exact declaration, missing/changed source and origin, changed package/hook,
foreign dependencies, separate F3 hook refusal, unrelated routes, foreign/options
before package tools and missing metadata. Fixture tests are not installs.
Native U2 probes pass **14/14** across all four real loader modes, using real
guards with final shell execution intercepted. Source hashes remain 983/983.
Native import/syntax checks cover 111 Python files. Two harness setup failures
(missing interception helper and relative launch path) are retained; corrected
probes passed without application changes or shell-body execution.

Five additional native read-only preflights pass: Nala/F3 metadata and complete
APT architecture plans succeed; foreign architecture, option injection and a
missing package fail. An audit hook permits only apt-cache reads and apt-get
simulation. No transaction or payload execution is involved. Pyflakes passes
for the four qualification/test drivers checked, AST parsing passes for 14 new
harness files, Bash syntax passes for the container bootstrap, and whitespace,
CSV/JSON and exact bundle checks pass. No production Python code changed.

All **983/983 baseline tracked files**, including the 17 protected policy,
manifest, lock, dependency/version files and all 470 script/library/manifest
files, remain byte-identical. **80/80** assessment-protected M4B files,
**2021/2021** original U1 evidence entries and **2325/2325** pre-existing evidence
files match their pre-task inventories. Independently pinned M4B completion
(833 bytes, `b1daa68ac265ad596a29005b667af024d5a9f3375d5bdb4dbe5c1c051dd37983`),
M4B checksum inventory (6360 bytes,
`819eb5a4c9a62b380a54267966c29f749e72a24ce0e79aa2229ad03f51d8651d`)
and original M4A DEB (8,554,000 bytes,
`83173db3b42d8ef966b6bde02f064beb42ee71b4593bfd727a3fefefdb862f04`)
also match. The VM's **2294/2294** monitored package/application/user records,
including ownership, modes, sizes, mtimes and file hashes, are unchanged after
assessment. This is a check of those roots, not every VM file or private cache.

Before the assessment commit, HEAD, branch, all heads/tags, semantic index and
reflogs match the start snapshot. Exact all-ref equality **does not pass**: two
Codex turn-diff capture/checkpoint names disappeared and two names appeared,
all at the same `889660d5d15602551249e807ae39ef8baa8761f4` object. No ref-mutation
command was used. An app-managed origin is inferred from the namespace; it has
not been independently proven. The full before/after names and values are in
[m5-assessment-evidence.json](m5-assessment-evidence.json). This discrepancy is
not concealed by comparing only object hashes or by rewriting the snapshot.

This source stage contains the assessment, inventory and evidence summary only.
**No ARM64 application route is newly enabled and no installation test is
claimed.** Secure container execution, its actual package effects and any
subsequent tightly approved production eligibility change remain outstanding.
No host package installation, system configuration, service operation, production
write, build, workflow, package generation or publication was performed.

Raw evidence and the prepared immutable container procedure remain under ignored
`target/m5-assessment/` and the new VM-private
`/home/ta/linuxtoys-m5-qualification/`. Earlier recovery/qualification reports are
not rewritten. The historical attribution-rewrite caveat remains: recovered
evidence does not restore original commit identities, and the missing original
Codex checkpoint ref remains unrecovered.
