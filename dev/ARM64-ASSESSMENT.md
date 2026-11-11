# Native ARM64 compatibility assessment (M0)

Date: 2026-11-09. Source: `83244aaf1ca5427e5dd57133f6eaf92a6cc1627d`.
Scope: native Linux AArch64, initially Ubuntu 26.04.1 arm64; retain x86-64.
ARMv6/ARMv7 and running x86 applications through emulation are outside M0.

## Executive summary

LinuxToys has **partial architecture awareness, not a qualified ARM64 release**.
The Python application and Rust sources contain no identified requirement for
x86 instructions, but both native Rust libraries and the GTK/Python stack must
be built and tested on Linux arm64. The README explicitly limits support to x86
(`README.md:26`). DEB, RPM, Arch metadata and CI still select x86-64.

The first implementation task should be a shared, fail-closed architecture
policy, applied at execution as well as catalog display. An offline probe
confirmed that the community AppImage matcher accepts `Tool-x64.AppImage` on
ARM64. Other paths accept architecture-unlabelled binaries or select the first
release asset. Publishing an ARM64 application without these safeguards would
expose incompatible third-party installers.

Deliver Ubuntu arm64 source/native application qualification and a small verified
feature set first. Do not advertise every catalog application as supported.
There is no evidence here that all third-party blockers can be solved merely by
changing download suffixes.

## Evidence and environment

- Source findings below are verified against this checkout; line references are
  relative to the repository root at the commit above.
- The requested VM/toolchain (Ubuntu 26.04.1, Python 3.14.4, Rust/Cargo 1.93.1) was
  **user-specified, not accessible or verified**. Available execution environment:
  Darwin 27.2.0 arm64, Python 3.13.7; no `rustc` or `cargo` on PATH.
- No application, installer, build, package transaction or upstream installer was
  executed. No dependencies or system configuration were changed. Only this
  assessment and its companion CSV were added; existing `.repowise/` was left alone.
- Offline probes extracted only the AppImage matching function and embedded
  release selector. The latter used a stubbed HTTP subprocess and synthetic JSON;
  no network or package execution occurred.
- The required gstack browse tool could not launch because its Chromium runtime
  is absent. Nothing was installed to repair it. Current upstream releases,
  Ubuntu package candidates, PPA/COPR settings and PyO3's Python 3.14 support were
  therefore not independently checked.

## Current architecture support

| Layer | Existing behavior | ARM64 consequence |
| --- | --- | --- |
| Rust catalog | `src/catalog-rs/repo.rs:1186–1278` recognizes `aarch64`/`arm64`; `p3/app/repo_parser.py:725–734` supplies the machine | Reuse this groundwork, but unknown asset architectures currently pass. The Git asset availability gate is bypassed for explicit `os` entries and non-`git` types (`src/catalog-rs/repo.rs:1288–1290`). |
| Shell release selector | `p3/libs/packages.bash:2144–2218` maps ARM64 aliases, rejects explicit foreign assets, rejects ambiguous best candidates | Unlabelled assets still pass. The x86-64-to-i686 fallback is explicit and confined to x86-64; do not extend it to ARM. |
| Community AppImage | `p3/app/appimage_catalog.py:900–934,954–970,1026–1031` | ARM rejection list omits `x64`; unlabelled names pass; direct URLs bypass name filtering; downloaded files are checked only for size/ELF magic, not machine. |
| Host/script compatibility | `p3/app/compat.py:359–448,870–892,1128–1333`; `p3/libs/sysinfo.bash:3–98` | OS/vendor/GPU/init/session checks do not form an ISA policy. Ubuntu `resolute` is allowed, but that does not qualify arm64 packages. Intel/AMD CPU vendor detection is not architecture detection. |
| Homebrew | `p3/app/homebrew_catalog.py:53–55`; `src/catalog-rs/appstream.rs:812–829` | Maps AArch64 to `arm64`, uses architecture variations and filters declared requirements. Actual bottles, formula builds and their dependencies remain unverified. |
| Other catalogs | `p3/app/appstream_cache.py:1175–1227`; `p3/app/snap_catalog.py:130–144` | Flatpak source discovery iterates all cached architecture directories; mixed caches need host filtering. Snap Store discovery delegates host selection to snapd. Native metadata depends on the configured distro repositories. |
| Local package UI/MCP | `p3/app/window.py:1883–1899`; `p3/app/mcp_server.py:1891–1908,3893–3929` | Format/OS guards are not package-machine guards, even though inspectors expose architecture. Apply the same validation to URI/file/CLI/MCP paths. |
| Native build | `build-rust.sh:109–201` | Builds for the current environment; no identified x86-only flags/assembly in project Rust. Linux `.so` paths are expected; a macOS ARM build is not a Linux ARM build. Explicit cross-target output paths are not handled. |

The hardcoded x86 User-Agent strings in `p3/app/translate_helper.py:84` and
`p3/app/tui/app_page_translate.py:58`, filename examples in
`p3/app/revert_helper.py:475–484`, icon dimensions and Rust test fixtures are not
CPU execution restrictions.

### Native dependencies

`Cargo.toml` defines catalog and GUI crates. Both use PyO3 `0.24` with
`abi3-py310`/`extension-module`; `Cargo.lock:1227–1258` resolves PyO3 to **0.24.2**.
The catalog is a mandatory native import in `p3/app/repo_parser.py:15` and
`p3/app/appstream_cache.py:28`. The GUI loads `liblinuxtoys_gui.so` through ctypes
and checks GUI ABI 20 (`p3/app/gui_rs.py:123–141`); the GUI crate also declares
PyO3. Neither component can be replaced with an x86 `.so` on ARM64.

Build requirements include Rust/Cargo, maturin, a native C compiler/linker,
Python development files, pkg-config and GTK3 development libraries (GLib/GIO,
GObject, GDK, ATK, Cairo, Pango and GdkPixbuf through `*-sys` crates).
TLS transitively uses `ring 0.17.14` and `cc`, including architecture-dependent
native compilation (`Cargo.lock:1338–1349`). The catalog also uses serde,
MessagePack, XML, URL, SHA-256, Unicode, chrono, walkdir, flate2, tokio, prost,
tonic and ureq; the GUI uses gtk/gdk/glib/gdk-pixbuf, serde_json and ureq.
The lockfile does not contain `openssl-sys`; do not infer an OpenSSL development
requirement for the application from unrelated feature installers.

`abi3-py310` is a CPython ABI floor, **not** proof that this pinned PyO3 version
builds with Python 3.14.4. Test the unchanged lockfile with the requested versions
before deciding whether a separate dependency update is needed. Do not use a
forward-compatibility environment override as release qualification. Test normal
CPython first; free-threaded Python is not claimed. Declared Rust MSRV 1.75 in
both crate manifests also needs reconciliation with the actual locked dependency
graph; the requested Rust 1.93.1 build has not been run.

Python dependencies (`p3/requirements.txt:1–19`) are PyGObject, requests, urllib3,
certifi, Textual 8.2.8 and pyte 0.8.2. PyGObject and its Pycairo/native GI stack
must match Linux arm64 and the interpreter. GUI typelibs include GTK/GDK 3.0 and
VTE 2.91 (`p3/app/gtk_common.py:8–14`), plus AppStream 1.0 in catalog code.
Use distro packages with the distro interpreter where possible; an independently
installed Python 3.14 may not see Ubuntu's GI modules.

The TUI vendor script deliberately rejects `.so`/`.pyd` files and caps wcwidth
below 0.9 (`dev/build/vendor_deps.sh:39–41,82–98`), supporting reuse of a pure
Python vendor tree. However, only top-level pins are exact; transitive versions
and hashes are not locked, and the reuse shortcut checks only those pins
(`:62–77`). Validate vendor purity on reuse and on every architecture. The Nix
shell selects Python 3.12 and omits the current Rust/maturin/TUI build setup
(`shell.nix:5–12,17–55`); it does not validate the requested environment.

## Compatibility matrix

The complete static inventory is [arm64-feature-matrix.csv](arm64-feature-matrix.csv):
**176 shell files plus 52 catalog records** (28 in `repos.json`, 24 nested list
records), with dependencies/hooks, distro restrictions, status and source lines.
Hooks/overrides are included separately, so these are coverage counts, not unique
end-user application counts. Runtime catalogs can add arbitrary external apps;
their individual availability cannot be enumerated or certified from this checkout.
The 228 inventory rows classify as C: 3, M: 28, A: 26, U: 5, N: 166; the
CSV separates integration status from third-party verification status.

Statuses describe the **current integration**:

- **C — ARM64 compatible:** source establishes an architecture-neutral operation
  (for example copying fonts); this is not a VM runtime test.
- **M — ARM64 compatible with modifications:** an identified integration defect
  needs correction; third-party availability remains a separate gate.
- **A — Requires an ARM64 alternative:** the selected artifact/backend cannot be
  accepted for native ARM64; obtain a verified native artifact or an explicitly
  chosen alternative. This does not assert that upstream has no ARM64 product.
- **U — Unsupported on ARM64:** the current operation is explicitly x86-specific.
- **N — Not yet verified:** dependency availability, native plugin, upstream
  installer, kernel or hardware behavior has not been established.

| Feature group | Status | Qualification |
| --- | --- | --- |
| LinuxToys GUI, TUI, CLI, MCP, catalog/search, registry/manifests, removal | M/N | Native libraries, Python 3.14/GI, shared eligibility and transaction tests required. Pure Python UI logic alone does not establish application compatibility. |
| Atkinson/OpenDyslexic/Nerd Fonts | C | Font data operations; download reliability still needs testing. |
| k6, Kind/kubectl, VSCodium, Docker, Mullvad | N | ARM64 selection/configuration exists in source. Release/package/image existence and execution untested. |
| Godot/Sharp, VS Code, JetBrains Toolbox, RStudio, Positron, Rclone UI | M | Select verified native assets/repository architecture rather than fixed x86 or positional API results. |
| Blender, Kdenlive, Zotero, Postman, LM Studio, Photon, Epic, Android Studio, WinBoat, Windscribe, OptiVRAM, OpenLinkHub, WiVRn/WayVR | A | Current routes include fixed x86 payloads, 32-bit x86 dependencies, or an x86-oriented backend. Some restrictions affect only a distro branch; see CSV. |
| Gamescope, MangoJuice, GOverlay, OBS/gpu-screen-recorder, Volt | M | Fixed x86 Flatpak extensions/plugins or rollback refs. GPU/runtime availability must be checked separately. |
| x86-64-v3 APT, split-lock tuning, UMIP, AMD-pstate ondemand, Resolve AAC bridge | U | Hide/refuse these operations on ARM64. Do not remove their x86 behavior. AAC bridge is already disabled by `compat: none` and has an explicit x86 check. |
| Power Optimizer, CachyOS configuration, Waydroid | M | Gate child operations/capabilities; do not treat an ARM CPU as Intel/AMD or request translation intended for an x86 host. Waydroid also currently requires AMD/Intel GPU metadata. |
| DaVinci/FFmpeg Resolve plugin, MetaTrader/Wine, Steam and related launchers | A/N | Verify every native binary/plugin/guest backend. Containers do not themselves translate an ISA. No native support claim from a working installer wrapper. |
| Intel/AMD/NVIDIA/OpenCL, Wi-Fi/DKMS, peripherals, bootloader/security tools | N/M | Qualify per hardware, kernel, distro and architecture. An M3 VM does not establish PCI GPU passthrough, vendor laptop controls or bare-metal ARM support. |
| Other package wrappers, VPNs, repositories, shell tools and system tweaks | N | Every shipped script/record is listed in CSV. Lack of an x86 string is not evidence of package or upstream support. |

The committed release database records ARM-labelled artifacts for OpenLogi,
Figma, Audacity, ZenNotes, QDiskInfo, Helium, HTTPie, Rclone UI and ArtCraft, among
others. This is **cached metadata, not a tested or current support guarantee**
(`p3/scripts/git-db.json:2,53,929`). It also lists `evince-48.1.flatpak` under
OpenBoardView (`:515`), so asset names alone are insufficient provenance evidence.

## Identified blockers and required changes

P0 blocks safe ARM enablement; P1 blocks qualification/distribution; P2 is later
distribution expansion or maintenance. These are source findings, not claims that
every third-party dependency is permanently unavailable.

| ID | Priority | Evidence | Required change |
| --- | --- | --- | --- |
| B01 | P0 | `install.sh:263–278`; self-updaters call it in `p3/app/updater/update_helper.py:253–274`, `p3/app/updater/update_dialog.py:159` | Resolve exactly one host-native release asset for initial install **and update**. DEB/eopkg selection can become multiline with multiple arches; RPM/AppImage choose first; Arch forces x86-64. Reject missing/ambiguous results before removing the old installation. |
| B02 | P0 | `p3/app/compat.py:1128–1333`; `src/catalog-rs/repo.rs:1288–1290,1469–1471`; `p3/libs/linuxtoys.bash:807–976` | Add explicit ISA eligibility for shell scripts, manifests, dependency entries and hooks; enforce again at execution, including direct CLI/MCP calls and developer mode. OS/GPU/CPU vendor conditions cannot substitute for ISA checks. |
| B03 | P0 | `p3/app/appimage_catalog.py:900–911,969–970,1026–1031`; `src/catalog-rs/repo.rs:1271–1278`; `p3/libs/packages.bash:2201–2211` | Fix `x64` rejection; distinguish unknown architecture from genuinely architecture-independent data/source. Validate package metadata/ELF machine before integration/execution, including direct links, tar-contained binaries and native plugins. Never execute a download to discover its architecture. |
| B04 | P0 | `p3/app/window.py:1883–1899`; `p3/app/mcp_server.py:1891–1908,3901–3929`; `p3/libs/packages.bash:1237–1388,1543–1568,1700–1724,2829–2848` | Validate architecture in shared installation code, not just catalog filters. Preserve supported `all`/`noarch` packages, but inspect their declared dependencies and any bundled native payloads. Do not rely on a manager rejecting a bad package after privileged work starts. |
| B05 | P0 | `p3/scripts/extra/pdefaults.sh:19–40`; `p3/scripts/extra/ubuntuv3.sh:13–25`; `p3/scripts/extra/dsplitm.sh:13–20`; `p3/scripts/extra/umip.sh:13–26`; `p3/scripts/extra/ondemand.sh:10–20` | Keep x86-only tunings unavailable on ARM; compose optimizer plans from eligible children. Existing ondemand vendor guard is useful; unavailable children must not produce false aggregate success. |
| B06 | P1 | Both crate manifests `:14`; `Cargo.lock:1227–1258,1338–1349`; `p3/app/gui_rs.py:12–23,113–141`; `p3/app/gtk_common.py:8–14` | Qualify the unchanged Rust/PyO3/ctypes/GTK/GI stack with Linux arm64, Python 3.14.4 and Rust/Cargo 1.93.1. Verify C struct layout, pointer/size types, imports and GUI ABI on both 64-bit architectures. Dependency changes, if needed, belong in a separately reviewed follow-up. |
| B07 | P1 | `dev/build/deb/build.sh:167,199–216,291`; `.github/workflows/release.yml:218–220,317` | Emit arm64 and amd64 DEBs from matching Linux builds, keep native shared-library dependency generation, and qualify Resolute as well as Noble. Verify actual dependency candidates (including `webp-pixbuf-loader`, VTE, AppStream and GTK package names), PPA series and enabled architectures; do not rename an amd64 DEB. |
| B08 | P1 | `.github/workflows/release.yml:220,333,382,441`; artifact paths `:317,367,427,488`; `.github/workflows/sync-scripts.yml:13–40` | Add isolated native arm64/amd64 build/test jobs, architecture-qualified artifacts/cache keys and PR checks. All release build runners are currently `ubuntu-24.04`, with no ARM matrix; Fedora/Arch containers inherit that host ISA. The sync workflow is source copying, not compatibility validation. |
| B09 | P2 | `dev/build/copr/linuxtoys.spec:5`; `dev/build/pkg/PKGBUILD:4`; `resources/optimize-cfg-ostree/rpmbuild/SPECS/linuxtoys-cfg-atom.spec:5`; `resources/optimize-cfg-ublue/rpmbuild/SPECS/optimize-cfg-ublue.spec:5` | Replace x86-only packaging declarations with explicit supported native architectures after qualification. Application packages contain native `.so` files and cannot become `noarch`/`Architecture: all`. Resource-only packages need a payload audit before relabelling. Arch Linux ARM is a separate packaging/repository qualification. |
| B10 | P1/P2 | `dev/build/appimage/build.sh:43–45,360–365,394–412,448–449` | Builder already derives `ARCH`; CI collection does not. Verify native quick-sharun/sharun/appimagetool/runtime and glycin-ng support, pin external build inputs and qualify the Arch-specific library paths, FUSE and host-driver loading. Ubuntu arm64 DEB/source work need not wait for this format. |
| B11 | P0 | Fixed artifacts listed below and in CSV | Replace each route with a verified native artifact, explicit approved alternative, or an unavailable state. Do not add amd64 repositories/multilib to ARM to make an installer appear to work. |
| B12 | P0 | `p3/scripts/game/gscope.sh:30`; `p3/scripts/repos.json:97,135–136,184–185`; `p3/scripts/lists/obs/obs-post.sh:4–15`; `p3/scripts/lists/volt/volt-post.sh:5–7` | Resolve Flatpak runtime architecture/branch from installed app metadata, verify extension availability, and fix both installation and recorded rollback refs. The OBS plugin archive is also unlabelled native code. |
| B13 | P1 | `p3/scripts/sys/drivers/nv-deb.sh:53`; `p3/scripts/sys/drivers/rocm.sh:58–59`; `p3/scripts/extra/archsb.sh:21`; `p3/libs/sysinfo.bash:99–135,286–309`; `p3/app/compat.py:599–892` | Separate hardware capability from CPU ISA. Verify native driver/kernel packages and device IDs; select a supported EFI target only after platform validation. No GPU/laptop driver claim from the M3 VM. |
| B14 | P1 | `p3/libs/packages.bash:785–855,1342–1349`; `p3/scripts/devs/java.sh:27–48`; `p3/scripts/devs/adoptium-jdk.sh:16–23`; `p3/scripts/devs/pyenv.sh:14`; `p3/scripts/utils/peripherals/piper.sh:14–16`; `p3/scripts/sys/sec/cloudflare-warp.sh:23–29` | Preflight repository/codename/architecture/version availability and every required dependency before mutations. `pkg_exists` means installed, not available. Most package failures already abort; retain this, avoid the generic apt-to-dpkg retry for incompatible packages, and report precise causes. WARP falls back from unlisted Resolute to Jammy; other scripts may mutate repos/config first or mask errors with `|| true`. |
| B15 | P1 | `p3/libs/packages.bash:1624–1629,2201–2223`; `p3/scripts/devs/kind.sh:37–60`, `p3/scripts/devs/k6.sh:35–44`; release checksums `.github/workflows/release.yml:525–529`; `install.sh:20,33,162` | Consume authenticated hashes/signatures where provided; checksums are published for LinuxToys but not verified by its installer. Filename/ELF checks establish neither integrity nor publisher authenticity. Pin remote scripts/build inputs; test truncation, tampering, HTTP errors and missing checksum cases. |
| B16 | P1 | `install.sh:54–66`; `p3/libs/packages.bash:1220,1345`; `p3/scripts/repos/rpmfusion.sh:21–32`, `p3/scripts/repos/terra.sh:21`; `p3/scripts/game/sunshine.sh:25,35`; `p3/scripts/creative/video/davinci.sh:273`; `p3/scripts/devs/starship.sh:23`, `p3/scripts/repos/pacstall.sh:14` | Keep the GUI/TUI in the user session; elevate only necessary operations. Audit existing `--nodeps`, `--dangerous`, root APT sandbox, `--nogpgcheck`, TLS `-k` and remote-script-as-root paths. Architecture/integrity preflight must precede elevation. Do not introduce force-architecture or dependency-bypass fixes. |
| B17 | P1 | `p3/app/appstream_cache.py:1191–1227`; `p3/scripts/git-db.json:2,515`; `dev/git_db.py:164–190` | Filter mixed Flatpak caches to native architecture, preserve architecture in identity/selection, and validate release database provenance/freshness. Missing metadata must remain unknown, not native-compatible. |
| B18 | P2 | `dev/build/build_all.sh:46,56,69–73`; `dev/build/README.md:25–34`; `dev/build/copr/build.sh:29–42`; `dev/build/pkg/build.sh:35–46`; `build-rust.sh:173–201` | Repair stale references to absent rpm/nuitka/solus builders when updating build docs. Isolate per-architecture staging and remove prebuilt native artifacts from source bundles (DEB already removes its two known `.so` files at `dev/build/deb/build.sh:51–57`). Do not share `p3/app/*.so` or target directories between host/target builds. |

### Fixed artifact and repository routes (B11)

These references supplement B11; CSV carries per-feature dependency expressions
and all distro guards. Restrictions on a non-Ubuntu branch remain relevant to
later rollout, not a reason to block an independently verified Ubuntu path.

| Location | Restriction |
| --- | --- |
| `p3/scripts/devs/ides/code.sh:15` | APT `arch=amd64`. |
| `p3/scripts/devs/ides/godot.sh:14–35`, `p3/scripts/devs/ides/godotsharp.sh:16–34` | x86 download filters, archive and extracted executable names. |
| `p3/scripts/devs/ides/jetbrains-toolbox.sh:21–24`, `p3/scripts/devs/ides/rstudio.sh:14–20,32` | Generic `linux` key or sorted positional download selection, no ISA discrimination. |
| `p3/scripts/devs/ides/positron.sh:15,28`; `p3/scripts/devs/virtualbox.sh:54` | Fixed x64 downloads; VirtualBox repository advertises amd64. Native Linux ARM backend/product must be verified separately. |
| `p3/scripts/devs/txt/sublimetext.sh:26–44`; `p3/scripts/sys/sec/cloudflare-warp.sh:38` | x86 repository paths/chroot in RPM/Arch/SUSE or RHEL branch. Ubuntu package path still requires verification. |
| `p3/scripts/lists/blender/blender-pre.sh:25`; `p3/scripts/lists/kdenlive/kdenlive-pre.sh:7` | linux-x64 tarball / x86_64 AppImage scraping. |
| `p3/scripts/lists/androidstudio/android-pre.sh:4–20` | Generic Linux IDE tarball plus i386/i686/lib32 packages and enabling i386. |
| `p3/scripts/lists/epic/epic.json:14`; `p3/scripts/lists/photon/photon.json:14`; `p3/scripts/lists/zotero/zotero.json:11` | x86_64 DEB, `arch=x64` Flatpak bundle, `platform=linux-x86_64` tarball. |
| `p3/scripts/repos.json:269,284,294` | Postman `linux64`, LM Studio `linux/x64`, Rclone fixed amd64 AppImage. |
| `p3/scripts/extra/lsw.sh:34,64–80`; `p3/scripts/extra/optivram.sh:20–26` | WinBoat x86 artifacts; Fedora 43 x86-only RPMs. |
| `p3/scripts/sys/sec/windscribe-vpn.sh:36–49`; `p3/scripts/utils/peripherals/openlinkhub.sh:17–18` | amd64 packages; amd64 archive in ostree/SteamOS route. |
| `p3/scripts/utils/peripherals/touchegg.sh:25–26`; `p3/scripts/utils/peripherals/wivrn.sh:28` | amd64 DEB (also suspicious archive/tag URL) in Debian route; x86 WayVR AppImage outside Arch. |
| `p3/scripts/sys/sec/hiddify.sh:26–39`; `p3/scripts/edu/tacwriter.sh:17–19`; `p3/scripts/creative/video/marmalade.sh:20–40` | Unknown-machine fallback selects first Hiddify asset; first Flatpak bundle for Tac Writer; unlabelled ZIP/native `.so` for Marmalade. |
| `resources/cachyos/x11-ssh-askpass-1.2.4.1-8-x86_64.pkg.tar.zst`; `resources/optimize-cfg-{ostree,ublue}/rpmbuild/RPMS/x86_64/*`; `resources/optivram/*/*.rpm` | Bundled x86-specific artifacts. OptiVRAM actively downloads its RPMs; no active installer reference was found for the other listed prebuilt resource packages. Do not assume unused resources block core startup. |

## Recommended implementation sequence

1. **Shared eligibility and validation:** normalize `aarch64`/`arm64` and
   `x86_64`/`amd64` consistently; map separately to DEB, RPM, Rust and vendor
   labels. Keep unknown distinct from architecture-independent. Fix B01–B05,
   B11/B12 guards before enabling ARM installs; add adversarial resolver fixtures.
   Preserve explicit supported x86 behavior and reject unverified ARM routes.
2. **Qualify the native application:** in clean Ubuntu arm64 and amd64 VMs,
   build both native libraries using the unchanged lockfile and requested tools;
   exercise Python/GI and GUI ABI. Resolve any Python 3.14 dependency blocker in
   a separately scoped change, with x86 regression evidence.
3. **Ubuntu package and CI:** parameterize architecture/series, preflight actual
   dependencies, add isolated non-publishing arm64/amd64 jobs and inspect DEB/ELF
   metadata. Keep existing release signing/publishing separate from test jobs.
4. **Small supported feature set:** promote N entries only after native dependency,
   download, install/run/update/remove/rollback tests. Start with fonts and
   distro-native tools; add upstream binaries individually. Disable unsupported
   optimizer children and hardware routes with a clear reason.
5. **Additional formats/distros:** qualify AppImage tooling and runtime, then RPM,
   COPR and Arch Linux ARM independently; audit resource packaging and stale build
   documentation. Broader support should not delay Ubuntu qualification.

## ARM64 and x86-64 testing strategy

| Gate | Required coverage and acceptance |
| --- | --- |
| Policy fixtures, both architectures | Aliases; unknown/ARM32; explicit foreign assets; `x64`; unlabelled binaries vs declared pure data/source; mixed-ISA archives; `all`/`noarch`; zero/multiple matches; missing native release; dependency and hook eligibility; native ELF/package metadata disagreement. Refuse before privilege/configuration/old-version removal. Preserve documented x86/i686 behavior only where explicitly supported. |
| Build/import | Native Linux arm64 and amd64; Ubuntu 26.04.1/Python 3.14.4/Rust+Cargo 1.93.1; retain Noble baseline. Build with lockfile, verify ELF machine, CPython import, GUI ABI/ctypes layout, GTK/VTE/AppStream and pure vendor imports. No host `.so` reuse. Run existing Rust unit tests in `src/catalog-rs/{repo,appstream,aur}.rs`, then add focused policy/integration tests. |
| Application | GUI on Wayland and X11, terminal/TUI and CLI, headless MCP; browse/search/mixed catalogs, batch/manifest imports, file/URI installs, installed detection, registry, uninstall/revert, Flatpak residue cleanup and settings. Every action must use the same eligibility result. Test absent optional backends and offline startup. |
| Packages/updates | Verify DEB `Architecture` and dependency candidates; clean install/upgrade/remove/reinstall; desktop/MIME/MCP service; release assets of both architectures in both orderings; self-update retains architecture. Tampered/truncated downloads and unavailable packages must fail without recording success. Snapshot/revert VM for destructive installer tests. |
| System features | Test sysctl/kernel/boot changes only in disposable snapshots; ensure x86 tunings never run on ARM. Validate matching kernel headers/DKMS and kernel capabilities before changes. USB/GPU/passthrough/virtualization tests need suitable hardware; report skipped explicitly. An M3 guest may lack nested KVM and does not test bare-metal ARM. |
| Regression/release | Native amd64 jobs remain required; compare catalog eligibility, normal install/update/remove and optimizer behavior with baseline. ARM jobs cannot replace x86 tests. QEMU may supplement policy/package tests, but is not native performance/hardware qualification. Require per-format evidence before publishing architecture claims. |

Performed in M0: source/configuration inventory, read-only dependency/lockfile
inspection and offline selector probes. Probe results: ARM64 accepts `x64`
AppImages incorrectly; explicit amd64 DEB is rejected by the generic selector;
arm64 and unlabelled DEBs are selected. Reverse arm64-on-x86 rejection works in
those fixtures. No Rust compilation, VM, package or third-party runtime test ran.

## Upstream contribution considerations and inspected files

Follow `CONTRIBUTING.md:7–51`: safety/privacy, clear unavailable states,
reliability, existing style, and manual PR review. Keep fixes in reviewable PRs:
policy/safety, native qualification, Ubuntu packaging/CI, then individual feature
routes. Update README support language only for tested scope. Architecture fields
must remain compatible with remotely synchronized scripts and older clients;
coordinate minimum-client-version handling with `p3/app/updater/version_gate.py`
and the scripts sync workflow. Do not weaken package signatures or silently add
emulation to claim native compatibility. Preserve GPLv3 notices (`LICENSE`,
`p3/LICENSE`) and third-party redistribution/licensing terms for new artifacts.

Inspection coverage:

- All 176 `p3/scripts/**/*.sh` files were inventoried by headers, dependency calls,
  downloads, hardware and mutation paths; every file has a CSV row. All 28
  `p3/scripts/repos.json` records and 24 `p3/scripts/lists/**` catalog records,
  their hooks and `p3/scripts/git-db.json` were inspected. Localized prose and
  screenshots are not executable compatibility evidence.
- Application paths inspected: `p3/linuxtoys.py`; `p3/app/{compat,dev_mode,
  repo_parser,appimage_catalog,appstream_cache,homebrew_catalog,snap_catalog,
  library_loader,scripts_loader,gui_rs,gtk_common,term_view,easy_cli,window,
  package_view,package_guard,mcp_server,manifest_helper,revert_helper}.py`;
  updater helpers; architecture-related translation references. Inspection was
  targeted, not a claim of line-by-line review of every UI module.
- Build/dependency paths: all three Cargo manifests, `Cargo.lock`, all three
  pyproject files, `p3/requirements.txt`, `build-rust.sh`, `install.sh`,
  `dev/build/**` scripts/PKGBUILD/spec/README, `dev/git_db.py`, both GitHub
  workflows, `flake.nix`/`shell.nix`, package metadata and project docs/license.
- Shell support/resources: all `p3/libs/*.bash`, `packages.json`, architecture
  and package/boot/privilege helpers in particular; `resources/get-optimize-files.sh`,
  optimization configuration/specs and prebuilt package filenames. Rust review
  covered architecture/catalog logic in `src/catalog-rs/{repo,scripts,appstream}.rs`,
  native GUI FFI/build declarations and native dependencies. A repository-wide
  architecture/download/ISA literal search supplemented these targeted reads.

Remaining unknowns are explicit in the matrix. This assessment is a complete
inventory of identified source blockers within that coverage, not a guarantee
that unexecuted upstream installers, binary payloads or current repositories
contain no further architecture restrictions.

## M1 implementation update

The M0 findings and CSV above remain a historical inventory at the recorded base
commit. Current rules are documented in [ARCHITECTURE-POLICY.md](ARCHITECTURE-POLICY.md).

| M0 blocker | M1 disposition |
| --- | --- |
| B01 | Shared native release selection, SHA-256/payload preflight and private staging added to initial install/self-update. No release pipeline changes. |
| B02 | Host/route eligibility enforced at catalog materialization, script preambles and hooks, including developer-mode paths. Reviewed source/declaration digests prevent automatic approval of changed remote routes. |
| B03 | Single alias/selection authority replaces Rust/shell/Python copies. `x64` on ARM, unknown/conflicting assets and positional/foreign fallbacks are rejected; explicit source/data is distinct from unknown. |
| B04 | Shared ELF/package/archive inspection precedes helper installation, chmod, privilege prompts and previous AppImage removal. Whole download batches are checked first; APT file dependency simulation is read-only. Unsupported file formats fail closed. |
| B05 | x86 tuning and the aggregate optimizer are unavailable on ARM64. Existing x86 routes retain explicit baseline declarations; no ARM optimizer behavior is claimed. |
| B11 | Fixed-x86 curated routes are guarded on ARM rather than speculatively ported. Hiddify/Kind/k6 label/selector duplication and unsafe staging were corrected; targeted Godot/Toolbox/Positron/RStudio paths gain payload preflight. Native alternatives remain individual qualification work. |
| B12 | Fixed Flatpak refs replaced with installed-runtime metadata/availability checks. Origin, scope, architecture and branch are retained through scoped rollback. Volt is explicitly blocked pending native build/bundle qualification. Live installs remain unverified. |

Verification: 36 focused tests on macOS (35 passed, one Linux-only skip) and
Ubuntu ARM64 (36 passed, including a real DEB fixture); 39 existing Rust catalog
tests passed, plus a locked native build and PyO3/frontend integration smoke test
on Python 3.14.4/Rust 1.93.1. Read-only APT and snapd candidate checks passed;
no application/package installation was performed. New Python lint/format checks,
changed-source syntax checks, shell error lint, changed Rust bridge formatting
and diff whitespace checks passed. Existing changed-module fatal lint retains
one confirmed baseline F821 (`tui/runner_helper.py:1273`). Detailed commands and
limits are recorded in ARCHITECTURE-POLICY.md. The former environment limitation was
partly removed by authenticated SSH access to the user's VMware guest. Tests
used an isolated `/tmp` copy, not the Desktop checkout.

Remaining: B06 GUI/native application qualification, B07–B10 packaging/CI/formats,
B13 hardware/drivers, full B14 solver qualification, broader B15/B16 upstream
integrity/privilege work, and B18 infrastructure/documentation drift. B17's
mixed-architecture Flatpak cache filtering is implemented; stale/provenance
metadata still requires upstream validation. M1 is an eligibility foundation,
not a general ARM64 software-support announcement.

## M2 native qualification update

The [M2 qualification report](ARM64-QUALIFICATION.md) records native Ubuntu ARM64
build, ELF, Python 3.14, ctypes/GTK/GI, GUI, CLI, TUI, MCP and font evidence. B06's
native application build/import and bounded GUI verification are now demonstrated
for the recorded environment; this does not qualify every distribution or feature.
B15's initial font-data routes now use reviewed pins and SHA-256 checks. B16's
filesystem rollback quoting and broad window-close temporary deletion were
corrected. B14 inspection now handles bounded compressed documentation while
continuing to reject compressed foreign binaries.

The three existing ARM font routes passed lifecycle and failure scenarios. IBus
Typing Booster, HTTPie and Nala are payload-verified independent Ubuntu candidates,
without runtime installation or promotion. B07–B10 packaging, B13 hardware,
broader B14–B18 work, matching remote script rollout and native amd64 runtime
regression remain open. The original M0 matrix stays a historical inventory;
current qualification levels and limitations are explicitly separated in M2.

## Remote-script compatibility follow-up (2026-11-10)

The M2 mismatch affected **all three** curated ARM64 font routes: the retained
remote cache contains exact M1 bodies while M2's client pins their hardened
revisions. The old cache-selection/in-place-pull model did not coordinate client
policy and remote publication. [SCRIPT-ROLLOUT.md](SCRIPT-ROLLOUT.md) records the
exact hashes, cause, version relationships and safe rollout order.

A client-owned manifest allowlist, explicit script API contract, complete-tree
verification and staged synchronization now prevent unknown/stale bodies from
displacing a qualified source. Execution/list-hook checks precede preamble
mutations. Unavailable tags retain approved cache/bundled bytes; rollback never
relaxes the architecture or integrity rules. The font bodies refuse missing
client helpers before installation code. ISA eligibility and the M0 CSV are
unchanged; no additional applications are qualified.

Native Ubuntu ARM64 evidence covers matching TCP Git synchronization, actual
catalog/font search, incompatible-tag refusal, offline source selection and GUI
search/shutdown on Wayland and Xwayland. Test and environment details are in
[script-rollout-evidence.json](script-rollout-evidence.json).
The local compatibility defect is resolved; **live upstream rollout remains
pending**. The [preparation follow-up](SCRIPT-PREPARATION.md) now replaces the
unsafe automatic sync locally with a manual artifact-only workflow; no workflow
was executed and upstream adoption still needs separate coordination.
Native amd64 regression is still unavailable. B07–B10 packaging and the other
M2 limitations remain open; packaging qualification has not begun.

## M3C preparation verification

[Native preparation evidence](SCRIPT-PREPARATION-ARM64.md) qualifies M3B's local
artifact preparation on Ubuntu ARM64, including independent/reproducible exports,
failure refusal and protected-source integrity. It changes no application code,
script, ISA approval or release workflow. Hosted workflow execution, upstream
adoption, native amd64 application regression and packaging remain separate gates.
