# LinuxToys — Architecture

> Companion to `AGENTS.md` (rules) — this document describes *how the project is structured*, not *how to work in it*.

## 1. What LinuxToys is

A cross-distro Linux app installer/manager for **x86-64 and AArch64 hosts**. A curated catalog of **Bash install scripts** (one script per app, plus JSON/metadata, under `p3/scripts/`) is presented through a **PyGObject/GTK3 GUI** (default) or a **Textual TUI** (CLI mode). Execution is mediated by a busy package-manager preflight (`package_guard`), an **architecture policy** (`architecture*.py` — every script, catalog entry, release asset and payload is checked against the host ISA before anything privileged runs), a script-API version gate (`architecture.require_api` — scripts written for a different script API are refused), `askpass`/`sudo_` privilege escalation in the bash core, AUR source-security verification (`aur_security`), a transaction lifecycle (transmap + `term_registry.ExecutionRegistry`), a **git-based script sync** (`git_scripts_manager` + `scripts_loader`, tracking the `psygreg/scripts` mirror's default branch so live script fixes flow without a client release), and an in-app **self-updater** (`updater/`).

Two native Rust components: **`src/catalog-rs`** → `_catalog_rs` is compiled via PyO3/maturin (catalog JSON parsing/repo-name normalization, git-release asset classification; shared with Python through the `_catalog_rs` module; see `dev/git_db.py`), and **`src/gui-rs`** → `liblinuxtoys_gui.so` is a plain cargo cdylib exposing a C ABI consumed by the Python GUI through ctypes (GTK theming helpers).

### ISA policy in one paragraph

`architecture.host()` reads `platform.machine()` and cannot be overridden. `x86_64` keeps the historical release-asset matcher the installed base relies on (architecture-unlabelled assets stay visible/neutral, 32-bit x86 assets rank as last-resort fallback); `aarch64` additionally requires explicit reviewed evidence everywhere. Either way, actual execution is gated by payload inspection (`architecture_files`/`architecture_flatpak`/`architecture_cli`): unknown, foreign or contradictory payloads are refused before privileges, and independent data (fonts) needs explicit `architecture_independent` approval. Catalog entries outside the reviewed policy (e.g. **Volt**, whose external Flatpak-extension build route is not qualified) are hidden on every ISA until qualified.

**Defaults by entry kind.** Scripts are presumed x86_64-only unless a `# architectures:` header tags them otherwise (aarch64-capable scripts also carry the `# requires-script-api: 1` marker). AppStream native/Flatpak/Snap and Homebrew entries are self-managed: those sources only offer what the host can use and their installers resolve ISA (AppStream data is per-arch by construction, Flatpak metadata is read from the host-arch directory, brew handles arm64 Linux itself). Repository listings are x86_64-only by presumption: `architecture.require_entry` grants aarch64 at runtime only when `p3/scripts/git-db.json` proves an installable aarch64 asset (explicitly tagged deb/rpm/pacman/appimage for git entries, an explicitly tagged tarball for tar entries, the exact declared asset for bin entries) or the record declares `architectures` explicitly; an asset without architecture evidence, a single-binary asset or a tarball asset never grants ARM. AppStream overlays are likewise x86_64-only by presumption: without an explicit `architectures` list in their record they only apply on x86_64, and an aarch64 host installs the plain app without the overlay's extras. AUR installs are additionally PKGBUILD-checked for aarch64 (`aur_security` refuses packages whose `arch` array lacks aarch64/armv8h/any when running on ARM).

## 2. Repository tree (annotated)

```
linuxtoys/
├── install.sh              # User-facing one-shot installer (deb/rpm/arch/suse/appimage routing) with self-contained package-manager lock guards (busy-wait + pacman stale-lock recovery + transaction retry, mirroring packages.bash); installed-state gate (version match → package-manager integrity check → repair-reinstall or "already up to date" exit) before the release's own architecture validation, which stages, verifies the host, selects exactly one checksum-verified native release asset and payload-verifies every download
├── build-rust.sh           # Rust components driver: build|develop|release|vendor
├── src/
│   ├── ver                 # Single source of truth: app version (read by build tooling)
│   ├── catalog-rs/         # PyO3 crate → _catalog_rs (catalog parsing, repo URL normalization)
│   ├── gui-rs/             # cdylib crate → liblinuxtoys_gui.so (GTK helpers)
│   └── (desktop file, icons, appdata/metainfo, mime)
├── p3/
│   ├── linuxtoys.py        # #!/usr/bin/env python3 entry: sys.path setup + package main
│   ├── requirements.txt    # Pins textual/pyte (single source of truth for vendoring)
│   ├── update_version.py   # manual version-bump helper (run by hand at release time)
│   ├── app/                # The Python application (see §4)
│   ├── libs/*.bash         # Bash helper libraries sourced by catalog scripts (see §6)
│   ├── scripts/            # THE CATALOG (see §5)
│   └── vendor/             # (generated, gitignored) vendored textual/pyte — dev/build/vendor_deps.sh
├── dev/
│   ├── build/              # Packaging per target: copr/ rpm-spec, deb/ (PPA + local native mode), pkg/ (AUR), appimage/
│   ├── git_db.py           # Builds p3/scripts/git-db.json (latest git-release assets index)
│   └── build_output/       # (generated) packaging output
├── .github/
│   ├── ci-images/          # archlinux-aarch64 Dockerfile: ALARM-rootfs CI image for the release arm legs
│   ├── workflows/
│   │   ├── release.yml         # version → ci-image+deb+rpm+arch+appimage → GitHub release
│   │   └── sync-scripts.yml    # mirror p3/scripts/** → psygreg/scripts repo
└── skills/, p3/app/mcp_skill/  # Agent-skill integration (LinuxToys MCP server docs)
```

## 3. Runtime flow

```
/usr/bin/linuxtoys (launcher, written by each packager)
  └─> p3/linuxtoys.py            # prepends p3/vendor to sys.path, then runs app package
        └─> p3/app/main.py       # arg/env parsing: EASY_CLI, linuxtoys:// URL, hybrid-GPU...
              ├─> GUI path: main.run() → Gtk.Application + window.AppWindow (PyGObject + liblinuxtoys_gui.so)
              ├─> TUI path: tui/ (Textual app, EASY_CLI=1)
              └─> linuxtoys:// URL / single-script run paths
```

Every script execution — GUI, TUI, CLI, MCP, AppStream or `call_script` nested — funnels through `library_loader.script_command`/`script_preamble`: the ISA gate (`architecture.host()` + `require_script`, including the script-API version gate), hook validation, then the preamble that sources the bash core (whose own first line re-checks the host before anything else runs).

## 4. Module map — Python application (`p3/app`)

#### Architecture & script-integrity policy (cross-cutting, p3/app top-level)

| File | Role |
|---|---|
| `architecture.py` | The single ISA authority (`ArchitectureError(ValueError)`): `host()` from `platform.machine()` only; alias/foreign-token tables (`LABELS`, `_FOREIGN`); microarchitecture-level canonicalization (`variant_appendix`/`canonicalize` — `amd64v3`-style appendix labels and `x86_64_v3`/`znver4`-style level tags fold into the host ISA while keeping the level for display; unknown variants and foreign ISAs are still refused); release-asset eligibility + three-tier ranking (`asset_eligible`/`select_asset`); script text gate `require_script` (explicit `# architectures:` header, else x86_64 presumption); catalog gate `require_entry` (ISA derived at runtime from the entry's own record — explicit `architectures` marker or `git-db.json` asset evidence — AppStream native/flathub/snap auto-declare the host); hook validation `require_overrides`/`resolve_hook_path` (inline hooks are x86_64-only by presumption); script-API version gate `require_api` (`# requires-script-api:` headers — a script written for another API version is refused). |
| `architecture_files.py` | Read-only native payload inspection: ELF header parse, deb/rpm/arch metadata (arch labels canonicalized through `app.architecture` — microarchitecture levels fold into the host ISA), zip/tar members with nested-archive bounds, declared-source trees must be free of prebuilt binaries (`validate_tree`). Never executes downloads. |
| `architecture_flatpak.py` | Read-only Flatpak ref resolution (`flatpak remote-info --arch=<host>`) and runtime-extension planning from the installed runtime's `[Extension]` metadata — no hardcoded branch lists. |
| `architecture_cli.py` | Subprocess entry point for Bash (`label|script|hook|files|tree|release|packages|snap|flatpak|extension`): the gate `linuxtoys.bash`, `packages.bash` and `install.sh` call. APT plan validation, cache-only native metadata preflights (candidate listings require one native or arch-independent candidate — multilib/multiarch same-name siblings are never selected for a bare name, dnf5's concatenated queryformat output is separated by the trailing-newline queryformat; labels are canonicalized before the gate — microarchitecture levels fold into the host ISA), snapd metadata queries. |

### 4.1 Catalog/data layer

| File | Role |
|---|---|
| `repo_parser.py` | Repo-list layer over `catalog-rs`: entry validation/resolution (Rust), list-JSON walking, install-script materialization (`compose_install_script` builds the text — with the `# architectures:` host header — and `create_install_script` writes the transient `.sh`, keeping the runner's appimage "true" convention), `architecture.require_entry`/`require_overrides` gating per entry (incompatible entries are skipped, never degraded), git-db consumption, `extension-of` dependency resolution, commerce/description overlays; `load_appstream_overlays` applies overlays per host ISA (x86_64 by presumption, `architectures` marker in the record to widen). |
| `parser.py` | Catalog core: Rust-assisted scripts-tree index, `.sh` header parsing, compat/visibility policy, `appstream_context` (shared resolution context for URI/MCP), category/repo/AppStream entry materialization, display-name resolution. (§4.3) |
| `search_helper.py` | `SearchEngine` over scripts + AppStream (+local scripts): Rust index overlay, weighted scorer, grouped-by-category results. |
| `appstream_cache.py` | Builds/publishes the persistent AppStream catalog (`~/.cache/linuxtoys/appstream/catalog.json` + `extensions.json`, schema 26): native/Flatpak/Snap/Homebrew/AppImage sources, source fingerprints, ODRS ratings + Snap votes APIs. |
| `appstream_parser.py` | Adapts the cached catalog into LinuxToys entries: source/omit/category policy, Rust runtime catalog (search/browse/installed/featured slices) with stale-while-revalidate. |
| `appstream_runner.py` | Persistent hidden-PTY runner + session queue for AppStream transactions (install/remove/extension/snap-revert/apt-refresh/skill/local-package/AppImage/homebrew/AUR) with completion markers, stall watchdog, transcripts, registry finishing, conflict gating; AUR source-security verification delegates to `aur_security` (provenance cross-check on). |
| `appstream_queue.py` / `appstream_extensions.py` | GTK views: session AppStream queue; embedded Flatpak-extensions view for the app page. |
| `aur_security.py` | Shared AUR source-security scanner (GUI runner + TUI executor + MCP): shallow-clone inspection of PKGBUILD + `*.install` against the obfuscation rules; the GitHub provenance cross-check is the opt-in `check_provenance=True` superset used by the GUI; on aarch64 hosts the same pass refuses packages whose PKGBUILD `arch` array (read statically) lacks aarch64/armv8h/any. |
| `aur_cache.py` | Opt-in AUR metadata cache (`catalog.bin` via catalog-rs): enable/refresh lifecycle (`refresh_catalog` is the shared refresh sequence), lazy browse/search views. |
| `homebrew_catalog.py` | Homebrew snapshot cache (formula.json + analytics popularity, 14-day TTL) feeding the AppStream-style catalog; `materialize_install` for queued formulae; cache writes go through `atomic_io` (0600). |
| `snap_catalog.py` | Snap Store metadata over snapd's Unix socket → AppStream-style entries (14-day cache). |
| `appimage_catalog.py` | AppImage community feed cache + intent-based category inference; release resolution/download for installs and updates (ELF validation, 4 GiB cap); release/direct-URL selection goes through the architecture policy (`asset_eligible`/`select_asset`) and downloaded AppImages are payload-verified (`architecture_files.validate_file`). |
| `package_guard.py` | Busy native package-manager preflight shared by every runner (lock detection + bounded wait); `dispatch_enters_native_transaction` additionally gates queued self-update entries as native transactions outright, because their package operations live inside the piped install.sh. |
| `installed_packages.py` | RAM+disk cache of user-installed packages relevant to AppStream state; removal-blocker queries. |
| `installed_features.py` / `package_view.py` | GTK views: currently-removable features; local-package-file details/install view. |
| `featured_scripts.py` | `FeaturedCtl` mixin: home/app-page featured strip — eligibility (review-score gates, Myket-affinity personalization), sampling, geometry, crossfades, rotation timers. |
| `popularity.py` | Browse ordering + Bayesian review scoring (Rust-backed); `KNOWN_POPULAR` pinning; session-stable jitter. |
| `category_affinity.py` / `build_myket_affinity.py` | Offline Myket category-affinity prior (`myket_affinity.json`) + its standalone generator CLI. |
| `new_index.py` / `official_index.py` | Developer-maintained sets: "New" badge features; first-party verified scripts + GitHub-URL helpers for bug reporting. |
| `manifest_helper.py` | Manifest engine (validate/install/replay, registry→manifest export, CLI modes). (§4.3) |
| `app_page.py` | App-details page widget. (§4.2) |

The remaining `p3/app` layers follow: GUI (§4.2), core runtime (§4.3), TUI/updater/antenna (§4.4).

### 4.2 GUI layer (p3/app, GTK3 + native Rust)

#### Main window & controllers (mixin composition)
| File | Role |
|---|---|
| `window.py` | `AppWindow(SearchCtl, NavCtl, SidebarCtl, FeaturedCtl, LocalScriptsCtl, ItemWidgetFactory, Gtk.ApplicationWindow)`: header bar, main stack (categories/scripts/search), AppStream bootstrap state machine, background workers (scripts sync, registry self-heal, installed-state observation), window-state persistence, language crossfade transactions, startup checks (ostree/Deepin/GregOS/kernel), package-file inspection flow. |
| `window_items.py` | `ItemWidgetFactory` mixin: native card factory (Rust-built), batch animation, hover/selection/keyboard wiring, removal affordances (`BADGE_EXCLUDED_IDS` = {"sysup","pdefaults"}). |
| `window_nav.py` | `NavCtl` mixin: stack navigation, retained parent views (zero-rebuild Back), category browser page construction, app page, terminal view, utility views, resize-settle prewarm. |
| `window_search.py` | `SearchCtl` mixin: header search entry (140 ms debounce), scope-aware dispatch (AUR/Homebrew/AppImage), smart navigation aliases, grouped native results with lazy population. |
| `window_sidebar.py` | `SidebarCtl` mixin: retractable native overlay sidebar with cascading disclosure, width/view-driven visibility, frozen-exit margins. |

#### App page & shared chrome
| File | Role |
|---|---|
| `app_page.py` | `AppPageView`: entry details — native header/actions, screenshot carousel + lightbox (variant selection, disk cache, autoplay, full-res upgrade), translatable descriptions, source picker, ODRS/Snap ratings, commerce buttons, Flatpak extensions tabs, residual-data cleanup, snap revert, Featured filler. `_WidthNeutral*` widget subclasses prevent content from driving window width. |
| `header.py` / `head_menu.py` | Invisible page header builder; hamburger popover (manifest import, language, about, registry, resync, auto-updates/auto-report/MCP toggles) + `InputDialog`. |
| `term_header.py` / `term_view.py` | `InfosHead` (native header block shared by terminal view and app page); `TermRunScripts` (VTE terminal + controls, removal/revert confirmations, Escape handling). |
| `term_runner.py` | `TerminalRunner` mixin: VTE execution engine — spawn with library env, serialization vs AppStream runner, package-manager busy-wait (self-update entries count as native transactions outright: their package operations live in the piped install.sh, invisible to the static scan), transmap/registry lifecycle, auto-revert queueing, runner-lock channel (`/tmp/linuxtoys/runner-state-*`). |
| `term_registry.py` | `ExecutionRegistry`: persistent per-script transaction registry (save with no-op skip + same-script prune, tmpdir_noram cleanup, auto-revert, expiry pruning) + `python3 term_registry.py save …` CLI used by `p3/libs/linuxtoys.bash`. The canonical save/cleanup that `easy_cli` delegates to. |
| `term_reporting.py` | `BugReporting` mixin: manual + auto bug reports from terminal output via antenna; clipboard copy. |
| `revealer.py` | Checklist footer (`RevealerFooter` + `SupportFooter` links over the shared `_support_links` table) + `BugReportDialog` form. |

#### Shared GTK infrastructure
| File | Role |
|---|---|
| `gtk_common.py` | GTK3/Gdk/Pango/Vte imports + helpers (symbolic-icon resolution with XSI preference, memoized scaled pixbufs, markup escaping, toplevel lookup, `widget_within` subtree test). |
| `gtk_dialogs.py` | Standard dialog helpers: `run_message_dialog` (custom buttons with optional style classes, or built-in localized button sets via `buttons_type`), version-gate + privilege dialogs, `WaitDialog`, startup-recommendations prompt. |
| `gui_rs.py` | ctypes bridge to `liblinuxtoys_gui.so` (ABI 20): spec marshalling, native widget recovery, batch cards/grids/sidebar/search groups/markdown+appstream buffers/local-package inspection; `card_child` is the single named-descendant lookup. |
| `easy_cli.py` | Headless CLI mode: arg parsing/dispatch, script/package/flatpak/snap install+uninstall flows, smart mode, auto-revert, registry saves/cleanup (delegates to `term_registry.ExecutionRegistry` — same no-op-skip/prune path as the GUI), version gate, TUI launcher. |

### 4.3 Core runtime (p3/app top-level)

#### Entry & mode selection
| File | Role |
|---|---|
| `main.py` | GUI/CLI entrypoint. Import-time: GTK stack only when `EASY_CLI != 1`. `run()` order: registry prune (CLI modes) → `UPD_SERVICE` headless sysup → `EASY_CLI` menu → GUI gates (`is_supported_system`, `can_escalate_privileges`) → kernel-check thread → GTK app. `linuxtoys://` URIs and package-file opens via `do_command_line`. |
| `parser.py` | Catalog core: Rust-assisted scripts-tree index, `.sh` header parsing, compat/localization/container visibility policy, category/repo/AppStream entry materialization, display-name resolution. |
| `repo_parser.py` | Repo-list layer over `catalog-rs` (mapped with the catalog/data section). |
| `compat.py` | Host/compat policy: cached host probes, compat keys (OS/GPU/CPU/desktop/init/session), script-header policy (`# compat/gpu/desktop/…`), privilege checks, container/WSL/GregOS detection, cache dirs. Also owns static dependency visibility: a script is only offerable when its `# needed:` prerequisites and unconditioned `call_script` targets are offerable too (needed targets must be fully compatible; called targets must be ISA-eligible — branch-local OS mismatch is left to the runtime `call_script` skip). |
| `library_loader.py` | Static bash-library-requirement detection + canonical script execution plumbing (preamble/env/argv, `call_script` nested resolution, CachyOS mirror preflight). Every dispatch funnels through the architecture policy here: `script_preamble` runs the host gate + `require_script` (bundle + ISA) before any preamble is emitted, `script_environment` validates overrides, `script_command` gates the file; list hooks resolve only through `architecture.resolve_hook_path`. CLI for nested execution + AppStream materialization. |
| `lang_utils.py` | Language detection/translation loading/settings persistence (language.conf, updates, error reports, MCP toggle, port). |
| `dev_mode.py` | `DEV_MODE` env simulation + script dry-run validation (bash -n, headers, sudo flow, dependencies). |
| `scripts_loader.py` | Scripts-source bootstrap (sync → scripts dir), `LT_DEBUG`-gated git-sync logging. |

#### Execution & side effects
| File | Role |
|---|---|
| `manifest_helper.py` | Manifest engine: load/validate/replay manifests, registry→manifest export, shared package/flatpak/snap installers, CLI manifest mode driver, sysup resolution. |
| `revert_helper.py` | Registry/transmap-driven reversal: ~20 op families → uninstall/auto-revert script builders over shared plumbing (`_revert_script_preamble` (carries the `# architectures:` header), `_registry_cleanup_heredoc`, `_write_revert_script`, `_revert_entry`, `_flatpak_remove_command`). Entry loading delegates to `registry_utils.load_registry_transactions`; filesystem records keep single-path operands (spaces safe, shlex-quoted rebuilds), Flatpak reversals honor the recorded `--user`/`--system` scope. |
| `registry_utils.py` | The single registry module: `parse_registry_file` (grouped dict view, mtime-memoized), `load_registry_transactions` (ordered list view for index arithmetic), `normalize_registry_content` (canonical/idempotent rebuild), `remove_script_entries` (exact-name removal → `(removed, ok)`), `search_registry_entries`, git-release/AppImage-release transaction readers + shlex Bash exports (CLI used by linuxtoys.bash). |
| `registry_heal.py` | Finds registry transactions for repo apps no longer offered (auto-revert support). |
| `action_registry.py` | GTK Action Registry viewer with export + cleanup (cleanup delegates to `registry_utils.remove_script_entries`). |
| `reboot_helper.py` | Reboot/ostree-deployment/flatpak-path requirement dialogs (over the shared `_message_dialog` chrome + `_run_reboot_choice`) + per-boot acknowledgement + `systemctl reboot`. |
| `flatpak_residue.py` | Single source of truth for `~/.var/app/<ID>` residue removal (shared GUI+MCP). |
| `gregos_helper.py` | One-shot GregOS post-install script run per `# gregos-version` marker. |
| `kernel_update_helper.py` | psycachy kernel update checker for Ubuntu-family hosts (GTK prompt + installer). |

#### Dialogs, features & misc
| File | Role |
|---|---|
| `mcp_server.py` | Stdlib MCP server (Streamable HTTP, localhost:7420, bearer token): 23 tools over catalog/install/removal/package-files/extensions/residue/settings/translate/registry; serialized `JobManager` with merged job tracking (every job submission blocks until the run finishes and returns its final record by default; `wait=false`/`wait_seconds` to queue-and-return, re-attachable via `get_job`); systemd user-unit management; agent-question pre-answering machinery. |
| `mcp_skill.py` | Stdlib-only MCP agent-skill installer: installs the latest reviewed text from the upstream repository first (bounded, shape-validated HTTPS fetch of `skills/linuxtoys-mcp/SKILL.md` from GitHub raw, then the Gitea mirror), with the sha256-pinned bundled copy (`app/mcp_skill/SKILL.md`) as the offline fallback. `install_agent_skill()` + the generated noninteractive `skill_install_script()` (direct execution of this module — it must never import the application stack; the script carries the `# architectures:` header the dispatch gate requires). Descriptor-relative no-follow reads, flock-serialized atomic publication — create-only hard link for fresh installs, rename over an older copy of the same skill for updates; foreign/customized user content is never replaced. Targets detected agent directories, creating the universal `~/.agents/skills` when none exists. Re-exported by `mcp_server`. |
| `uri_parser.py` | GUI-agnostic `linuxtoys://` validation + stable-target resolution. |
| `translate_helper.py` | GTK-free description translation (Google endpoint) + shared cache — the single pipeline for GUI, TUI and MCP. |
| `needed_helper.py` | Prerequisite-list and run-confirmation dialogs (shared `_script_row`/`_script_list_scroller` list rendering). |
| `local_scripts.py` | `LocalScriptsCtl` mixin: drag-and-drop, create/edit/delete/export of `~/.local/linuxtoys/scripts` (shared confirm/chooser/cleanup helpers for the singular and plural flows); the local-script template carries the host `# architectures:` header. |
| `atomic_io.py` | Atomic file writes for the persistence sites migrated to it (antenna history, Homebrew cache, `version_gate` state): `atomic_write_bytes/text/json` (mkstemp staging + `os.replace`, optional fsync/mode, best-effort tmp cleanup; without an explicit mode the private 0600 staging mode is kept). |
| `skills_guard.py` | Safety guards for skills.sh references, shared by the GUI and TUI Skills Seeker: strict reference-charset validation (`is_valid_skill_reference` — slug segments, no leading dash, no shell metacharacters; `InvalidSkillReferenceError`), remote-data → filename-component sanitization (`sanitize_filename_part`), and `build_install_script` — the shlex-quoted generated `npx skills add` script text consumed by `window.py._install_skill_from_seeker`. |
| `language_selector.py` / `about_helper.py` / `deepin_immutable_helper.py` | Language picker; About dialog (GitHub contributors); Deepin immutable-mode one-shot flow. |
| `skills_fetcher.py` / `skills_view.py` | skills.sh CLI fetcher (TTL cache; `search`/`popular`/`detail` — `detail` composes the unauthenticated search API with the skill page's description meta tag, since the v1 file-tree endpoint requires Vercel OIDC) + GTK Skills Seeker view. |
| `file_watcher.py` | DEV_MODE-only 2s poll triggering UI reload on script/lib changes. |
| `appstream_parser.py`, `appstream_cache.py`, `appstream_runner.py` | Mapped with the catalog/data section. |

### 4.4 TUI, updater, antenna (p3/app/tui, p3/app/updater, p3/app/antenna)

#### `p3/app/tui/` — Textual TUI (CLI mode, `EASY_CLI`)

| File | Role |
|---|---|
| `main.py` | Entry: `SplashScreen` → `HomeScreen` (search input + item panel + logo/menu/terminal panel). `LinuxToys(App)` boots index in threads, persists theme. HomeScreen mixes in six runner/helper mixins; `_menu_items`/`_link_bar_items` are the single source for the home menu and link bar (compose + language refresh share them). |
| `menu_helper.py` | `MenuSelectionMixin` — menu dispatch (registry/language/manifest/update/about/resync). |
| `runner_helper.py` | The execution core: `ScriptRunnerMixin` (script install/remove, category nav incl. Specials/Homebrew/AppImage/AUR, run engine over embedded terminal, registry saves via `easy_cli` → `term_registry`, reboot/auto-revert, parameterized Specials loaders `_catalog_load_async`/`_catalog_search_async` shared by Homebrew/AppImage/AUR), `AppstreamRunnerMixin` (AppStream transactions via executor-built scripts), `ManifestRunnerMixin` (manifest classify → bootstrap → confirm → queue), `UpdateRunnerMixin` (check + in-terminal installer via `update_helper.build_update_script`). |
| `helper.py` | Shared data layer: widget-id slugs, warmed search/category caches, virtual categories (Specials/Homebrew/AppImage), `ScriptResult` exit-code classification, `flathub_ready` (shared Flathub remote check for startup recommendations and the manifest resolver). |
| `my_widgets.py` | Custom widgets: `FocusableLabel`, `InfoButton`, list items, and `Terminal` — pyte-backed embedded terminal over a real PTY with password-prompt detection and exit-marker tracking. |
| `dialog_screen.py` | All `ModalScreen` dialogs (confirm/error/success/reboot/sudo password/language/update/version-gate/AUR consent+security/report-bug). |
| `appstream_executor.py` | Builds shell scripts/argv for AppStream installs (temp `.sh` with RC gates over `repo_parser.compose_install_script`); thin re-export shim for the AUR security scanner (`app/aur_security.py`). |
| `manifest_dialog.py` / `manifest_resolver.py` | Manifest `.txt` picker UI + blocking resolver (entries → scripts/packages/snaps/flatpaks, bootstrap detection). Mirrors CLI pipeline. |
| `tui_app_page.py` | Detail page widget for one app (sources, commerce links, rating, translation, extensions, featured grid); `show_app_page`/`hide_app_page`. |
| `app_page_translate.py` | Thin adapter over `translate_helper` — the TUI shares the GUI/MCP endpoint, traversal and disk cache; only the entry-info cache-key mapping and plain-text shortcut live here. |
| `registry_screen.py` | Action-registry browser (list/details/search/cleanup/export); cleanup delegates to `registry_utils.remove_script_entries`. |
| `skills_core.py` / `skills_view_tui.py` | Skills Seeker: npx `skills` domain ops (install/list/remove, agent detection) + Discover/Installed UI. |
| `startup_recommendation.py` | One-shot startup setup offer (flathub/rpmfusion/multilib/brew) → dependency-aware queue via ManifestRunner. |
| `about_helper.py` / `theme_store.py` | About panel (ANSI logo, tabs, contributors) + theme persistence (cache-dir JSON). |

#### `p3/app/updater/`

| File | Role |
|---|---|
| `__init__.py` | `__version__` constant. |
| `update_helper.py` | Release lookup (GitHub → Gitea fallback), install-source detection (PPA/Copr/git disables self-update), `build_update_script(mode)` — the single installer-text builder for the VTE dialog (`terminal`: library + sudo_rq, bare pipe on SteamOS, optional completion marker), the headless updater (`background`: askpass + download-then-source in the same shell) and the TUI (`tui`: minimal pipe); every mode emits the `# architectures:` header and `set -o pipefail`; `is_steamos()`; `run_background_update` via generated bash script (lock collisions are handled inside install.sh's own guards); `compare_versions` delegates here from `version_gate` (also used by `kernel_update_helper`). |
| `version_gate.py` | Non-blocking cache-backed gate refusing script runs when more than `GATE_GRACE_RELEASES` releases behind; `update-state.json` cache (atomic write via `app.atomic_io`), daemon-thread refresh, fails open; `compare_versions` is the shared tri-state comparator (right-padded tuples). |
| `update_dialog.py` | GTK dialogs: changelog `UpdateDialog` (own dependency-free Markdown renderer; writes the `build_update_script("terminal", …)` installer to `/tmp/.self_update_lt`), error dialogs, `scripts_blocked_by_version` gate flow for the GUI. |

#### `p3/app/antenna/`

`antenna.py` — bug-report backend: system context string (OS/CPU/RAM/GPU/desktop/init), last-10-script history (written through `atomic_io`, 0600), `LogCapture` stdout/stderr tee, machine-id HMAC token bootstrap against `bug.linux.toys`, `submit_issue` POST (an HTTP 422 naming the logs field surfaces as `EmptyReportError` → "empty report" explanation instead of a failure dialog), and a global exception hook that auto-submits unhandled exceptions. `install.sh`, CI, and each packager reference none of this directly — it is runtime-only.

## 5. Catalog scripts & data (`p3/scripts`)

The catalog is **data, not code**: one `.sh` per app plus JSON/metadata. Headers are machine-parsed (`parser.py`, `scripts.rs`), so their keys are a contract:

- Script header: `# name:`, `# version:`, `# description: <i18n key>`, `# icon:`, plus policy flags — `# compat:` (e.g. `!solus, !ostree`), `# gpu:`, `# hybridgpu:`, `# desktop:`, `# systemd:`, `# wayland:`, `# cpu:`, `# deviceids:`, `# reboot: yes|ostree`, `# revert:`, `# registry:`, `# negates:` (hides other scripts when this one succeeds), `# localize:`, `# nocontainer`, `# gregos-version:`, `# cachyos-mirrors-required: 0` (opts a backend that never consults the distro repositories out of the CachyOS mirror preflight).
- ISA contract: scripts declare ISA support in the tree itself — `# architectures: x86_64[, aarch64]` header — and are **x86_64-only by presumption** otherwise: headerless scripts run on x86_64 and are refused elsewhere. Aarch64-capable scripts must also carry `# requires-script-api: 1`. Local/generated scripts always get an explicit host header. The repository-support scripts under `repos/` are tagged individually per upstream ARM availability (Flathub/FlatPark/Homebrew/Cargo/Nix/Pacstall/Pip/RPM Fusion/Snap/Terra dual; Chaotic-AUR and Multilib are x86_64-only upstream). Visibility propagates through dependencies: when a prerequisite (`# needed:`) or an unconditioned `call_script` target is not offerable on the host, every entry that depends on it is hidden too, even if the dependent itself would be ISA-compatible.
- Live catalog: the tree is mirrored verbatim to `psygreg/scripts`, whose default branch is the client's remote sync source — script fixes flow to installed clients without a client release, and nothing pins content digests on the client side. Aarch64 qualification is likewise explicit in the tree: a script header, a listing record's `architectures` marker, or `git-db.json` release-asset evidence (rebuild with `dev/git_db.py` after releases change). `# requires-script-api: 1` marks scripts that use the managed script API; `architecture.require_api` refuses any other value.
- `category-info.txt` per directory: `ICON:` + `description: <i18n key>`.
- `repos.json` + `lists/*.json`: repository/app entries (source URLs, screenshots, descriptions.json per list with translated long descriptions, hooks under `scripts/lists/<app>/*-pre.sh`/`-post.sh`); git-type repos are resolved via `git-db.json` (built by `dev/git_db.py`).
- `scripts/sysup.sh` + `scripts/sys/` — system-update and driver flows; `scripts/lists/` — upstream hooks.
- i18n: `p3/libs/lang/<code>.json` (app strings, plus the bash-side guard/route refusal strings read by `packages.bash` through jq) + `<code>.lib` (bash message strings), ~58 languages.

## 6. Bash core libraries (`p3/libs/*.bash`)

Sourced by catalog scripts (via `linuxtoys.lib`/`library_loader.py` static analysis). `linuxtoys.lib`, `helpers.lib` and `optimizers.lib` are **symlinks** to their `.bash` twins, so the two names always stay in sync.

| File | Role |
|---|---|
| `linuxtoys.bash` | Core loader (conditionally sources the rest); refuses unsupported hosts at source time via `architecture_cli.py label host`; `_architecture_check()` shared preflight helper (its refusal dialog lines are localized through `_lang_`'s `.lib` store, with inline English floors); zenity compat layer, privilege escalation (`askpass`/`sudo_`), message + question/selector dialogs (`_msg`, `question`, `radioselect`, `listselect`, `userinput` — the radio/list selectors share `_select_parse_options`) with MCP-agent answer passthrough, `_lang_` i18n, runner locks, transmap (transaction map), `call_script` (script→script calling incl. AppStream resolution), `run_list_hook` resolving hooks only through the architecture preflight, CachyOS mirror preflight (lazily from the first native `runner_lock`; removals and `*external*` transaction locks — snapd, Homebrew, Flatpak bundle files, make builds, i.e. backends that never consult the distro repositories — skip it). |
| `packages.bash` | The package-management core (~3.2k lines): `_pkg_transaction` subshell wrapper (bounded wait → run → ≤2 diagnosed retries on lock refusals, signal-status preservation) under per-manager lock-guard trios (pacman/apt/dnf|dnf5|yum/zypper/eopkg/rpm-ostree) — native locks are never deleted, a persistent pacman lock dies with a manual-recovery message; `pkg_install` with dpkg state classification (`_pkg_dpkg_state`: installed vs absent/conffile-only vs incomplete; incomplete installs recover through `interrupted_apt_guard` and are never recorded as new), `_architecture_check packages|files|tree` preflights before every payload install, `pkg_flat` with scope parsing + ref resolution through `architecture_cli.py flatpak` (transmap records carry the scope) and `pkg_flat_extension` (runtime extensions resolved from the installed app's metadata), `pkg_snap(_revert/_file)` (snapd arch preflight; external locks), `pkg_fromfile`, `pkg_tarball`, `pkg_binary`, `pkg_fromurl`, `pkg_make` (source-tree validation before build deps), `pkg_fromrelease` (asset selection delegated to `app.architecture.select_asset`), `pkg_appimage(_update/_rm)` with Gear Lever integration (its FUSE gate probes the actual `fuse2` package name on Arch-family/Solus and falls back to `pkg_install fuse2` only when missing), `pkg_npm` (a functional `npm --version` check routes a broken-but-installed npm through `_pkg_npm_repair`, which reinstalls the distro npm package instead of letting the install skip; the `npm` self-upgrade is best-effort via `_pkg_npm_self_upgrade`: an engine-incompatible Node.js skips it with a warning instead of aborting, and escalated calls go through the resolved npm binary so root's PATH cannot miss it), `pkg_bun`, `pkg_brew(_remove)`, `pkg_remove`. The guard l10n block (`_pkg_guard_l10n`: one jq pass of the chosen language over `en.json`, inline English floors) serves both the lock-guard messages and the native-route refusal lines of `pkg_flat`/`pkg_flat_extension`/`pkg_appimage` (`pkg_flat_*`/`pkg_ext_*`/`pkg_appimage_*` keys). Non-distro backends (snapd, Homebrew, Flatpak bundle files, make builds) take `package-transaction-external` locks so the CachyOS mirror preflight only pays for transactions that consult the distro repositories. |
| `sysinfo.bash` | `/etc/os-release` detection (`sysdetect`, `is_*` family incl. ostree/ublue/gregos/restricted hosts) + GPU/compute capability probes (NVIDIA/Intel/AMD, ROCm/Rusticl PCI-ID lists, ReBAR, hybrid GPU). |
| `fsops.bash` | Reversible filesystem "prep" ops (backup-before-edit/create/remove → transmap) + Distrobox container variants (`distrobox_prep_dir(_edit)`, `distrobox_copy_`, `distrobox_move_` over the shared `_transfer`/`_distrobox_transfer` flag-splitting + fallback plumbing) + font routes: `font_download` (HTTPS-only, tracks the upstream's latest published version, data-kind architecture preflight) and `font_install` (fc-scan validation, no-symlink/backup safety, path-escape check, transmap records). |
| `misc.bash` | App-level integrations: `shell_change`, swapfile/distrobox transmap records, `check_disk_space` (DaVinci-space check), `flatpak_override`, `path_link`, `desktop_shortcut`, orphaned-launcher cleanup. |
| `boot.bash` | Bootloader/initramfs/kernel-args/Secure-Boot (MOK) handling per distro family. |
| `sysd.bash` | Thin systemd enable/start/stop/disable (system + user scope, once-per-run daemon-reload latch). |
| `timefix.bash` | Once-per-boot silent clock-skew guard (HTTP-Date reference clock, NTP correction ladder, askpass after-auth hook) — fixes apt/sqv "Not live until" failures. |
| `helpers.bash` | Downloaders (`fetch_from_mirror`), DaVinci Resolve fetch (`getresolve` with the shared `_davinci_parse_release` feed parser), `clinfo_chk`, Debian non-free/backports enablers + legacy shims to catalog scripts. |
| `optimizers.bash` | Block of legacy shims to optimizer catalog scripts (intentional compat surface for old local scripts). |
| `gregos.bash` | Not a library: self-contained GregOS post-install script run headlessly once per `# gregos-version` (theming, bun/opencode, sloth-bash, swapfile). |
| `translator.lib` / `packages.json` | Package-name translation key→distro dictionary used by `pkg_install`-related name mapping. |

## 7. Rust layer

Two cdylib crates, built by `build-rust.sh` (maturin for catalog-rs, plain cargo for gui-rs).

### `src/catalog-rs` → `_catalog_rs` (PyO3, `module-name = app._catalog_rs`)

| File | Role |
|---|---|
| `lib.rs` | Module entrypoint; registers 28 pyfunctions + 3 pyclasses. No logic. |
| `shared.rs` | Cross-module helpers: `json_to_py` (JSON→Python boundary), `normalize_appstream_id` (canonical AppStream ID normalization), `weighted_pick` (single weighted-draw core for the featured samplers). |
| `repo.rs` | Repo-list (repos.json / lists/*.json) static+runtime validation, git-URL canonicalization, full repo-catalog assembly (icons/screenshots/translations, dedupe); git-release architecture matching and asset naming delegate to `app.architecture` over PyO3 — no second alias table lives here. ~30 private validators/helpers; JSON/ID helpers delegate to `shared.rs`. Tests: `runtime_compat_tests`. |
| `appstream.rs` | AppStream ingestion (gz+XML mini-DOM) for Flatpak/native/Homebrew/Snap/AppImage; source-group collapse/preference policy; AppStream→catalog-entry adaptation; `AppStreamGeneration` (incremental builder → published catalog) and `AppStreamCatalog` (runtime index over MessagePack warm cache); `category_index_maps` shared by the category resolvers. Tests: category_resolution/appimage_source/omission_key/homebrew_binary. |
| `popularity.rs` | Session-stable popularity scoring; Bayesian review subscores; weighted sampling for featured grids (draw loop over `shared::weighted_pick`). |
| `featured.rs` | Featured-grid layout planning (large-card placement via deterministic RNG) + app-page Featured ranking with Myket category affinity (sampling over `shared::weighted_pick`). |
| `search.rs` | Minimal weighted substring scorer over Python-built rows (`SearchIndex`). |
| `scripts.rs` | Recursive scripts-tree index: dirs, `.sh` files, shebang-comment headers (`build_script_tree_index`). |
| `snap_ratings.rs` | gRPC client for Canonical's snap ratings service (hand-rolled prost messages + tonic, per-call tokio runtime). |
| `aur.rs` | AUR bulk metadata → versioned MessagePack `catalog.bin` (stale-while-refresh) + `AurCatalog` browser/searcher with library-hiding and variant-collapse heuristics. Tests: `appstream_icon_tests`. |

Deps: pyo3 0.24 (abi3-py310), serde/rmp-serde, quick-xml/flate2, prost/tonic/tokio (snap ratings), ureq + pinned zeroize (AUR, Rust 1.75 MSRV).

### `src/gui-rs` → `liblinuxtoys_gui.so` (pure C ABI via ctypes — no PyO3 module)

`lib.rs` is the single compiled file. All exports are `#[no_mangle] extern "C" lt_gui_*` functions driven by packed spec structs (`LtGuiItemCardSpec`, `LtGuiAppPageHeaderSpec`, …): batch widget construction (cards/search groups/sidebars/list rows/app-page chrome), featured large cards, category watermark rendering, remote/snapd icon fetch+caching, local package inspection (.deb/.rpm/.pkg.tar/.eopkg/.flatpak/.snap/.appimage), and Markdown/AppStream TextBuffer rendering.

### `src/translate_*.py` — one-shot translation helpers (repo root)

| File | Purpose |
|---|---|
| `translate_descriptions.py` | Merge a hand-filled short-description table into a list's `descriptions.json` (validates full 57-language coverage). |
| `translate_json.py` | Legacy inline merge into `p3/libs/lang/<lang>.json` (runs at import top level; `__file__`-anchored paths). |
| `translate_lib.py` | Append `noresolve` message lines across `p3/libs/lang/*.lib` (`__file__`-anchored `LANG_DIR`). |

## 8. Packaging, dev tooling & CI

### Build orchestration

- `build-rust.sh` (root) — `build|develop|release|vendor`. `release` vendors deps, builds+deploys both Rust artifacts, then drives distrobox packagers: fedora→`dev/build/copr/build.sh`, arch→`dev/build/pkg/build.sh` + `dev/build/appimage/build.sh`, ubuntu→`dev/build/deb/build.sh`.
- `dev/build/vendor_deps.sh` — pins textual/pyte from `p3/requirements.txt` into `p3/vendor` (gitignored); refuses to vendor `.so` binaries; `p3/linuxtoys.py` prepends it to `sys.path`.
### Packaging targets (`dev/build/<target>/build.sh`, all take `<version> <output_path>`)

| Target | Output | Notes |
|---|---|---|
| `copr/` | RPM + source tarball via `rpmbuild` + `linuxtoys.spec` | builds natively on x86_64 and aarch64 (`ExclusiveArch` gates the buildable hosts, the binary keeps the build host's arch); cargo-vendors staged tree for sandboxed builds |
| `deb/` | signed source upload to Launchpad PPA + binary `.deb` via `debuild` | Launchpad duplicate guard via API; `LINUXTOYS_TEST_MODE` skips upload probe. `build.sh --binary-only <version> <output>` prepares the identical source tree but builds only the native binary package (no upload/guard/dput) — the release-workflow path for the second architecture leg. `build.sh --native <version> <output>` instead constructs a local native-only DEB on this host (no signing/upload) via `package.py` — the ARM64 development build path: host arch must match `dpkg --print-architecture`, the reviewed script bundle must validate, native extensions are rebuilt from source and `dpkg-shlibdeps` derives real linkage deps. `debian/control` declares `Architecture: any` so Launchpad builds every arch enabled on the PPA |
| `pkg/` | AUR: `.tar.xz` + sed-updated `PKGBUILD` + `makepkg` | PKGBUILD `arch` array covers `x86_64` and `aarch64`; makepkg names the binary package after the build host's CARCH |
| `appimage/` | `LinuxToys-<v>-<arch>.AppImage` via pkgforge quick-sharun | arch comes from the build host's `uname -m`; builds glycin-ng + compat shim, replaces upstream glycin, bundles icon themes; `DEPLOY_PYTHON` copies the build host's `/usr/lib/python3.x` (site-packages incl.) into the AppDir, so the host must have `python-requests` + `python-gobject` (runtime deps that deb/rpm/arch declare as distro dependencies) — guarded pre- and post-deployment |

All four package `p3/` at `/usr/share/linuxtoys` with the same launcher heredoc (`/usr/bin/linuxtoys`) and the same permission normalization; all three distrobox-spec ones run the same maturin+cargo+wheel-extract+assert block.

### CI (`.github/workflows/`)

- `release.yml` — triggers: `workflow_dispatch` (version/upload_ppa/test) or push to master touching `src/ver`. Jobs: `prepare` (version + release notes + `vendor_deps.sh`, uploads `tui-vendor`), `ci-image` (aarch64: fetches the Arch Linux ARM rootfs, verifies its detached signature against ALARM's pinned published key fingerprints, builds `.github/ci-images/archlinux-aarch64/Dockerfile` on the arm runner and pushes it to GHCR — Arch's official images are linux/amd64-only, so the arm legs cannot pull them — and outputs a digest-pinned image reference; the image also disables pacman's download sandbox — Landlock, the syscall filter and the `alpm` privilege drop all fail inside the runner container, the same mitigation Arch's official Docker images ship — initializes the pacman keyring, and normalizes makepkg's `PKGEXT` to Arch's standard `.pkg.tar.zst` (ALARM's makepkg.conf still defaults to `.pkg.tar.xz`, which made the release workflow's package copy step fail on the aarch64 leg)), `deb-ppa`, `rpm` (fedora container), `arch-pkg` (arch container; the aarch64 leg runs the digest-pinned ALARM-based image from `ci-image`), `appimage` (arch container; same aarch64 image), then `release` (sha256sums + `gh release create`). Test mode requires an existing tag; already-tagged push no-ops. Every packaging job runs twice through a native-architecture matrix (x86_64 leg on `ubuntu-24.04`, aarch64 leg on `ubuntu-24.04-arm`, native distro containers — fedora is multi-arch, the Arch aarch64 container is ALARM-based — no emulation/cross toolchains), so the release carries both `amd64`/`x86_64` and `arm64`/`aarch64` assets. Each leg uploads its own `release-assets-<job>-<arch>` artifact; the `.src.rpm` and the AUR tarball + `PKGBUILD` are collected once, from the x86_64 legs, to avoid name collisions in `dist/`. The PPA source upload happens exactly once, from the amd64 deb leg (`build.sh --binary-only` keeps the arm64 deb leg off the PPA); Launchpad can additionally build `arm64` when that arch is enabled on the PPA (`debian/control` declares `Architecture: any`). Local native ARM64 development builds use `dev/build/deb/build.sh --native`.
- `sync-scripts.yml` — push to master touching `p3/scripts/**` mirrors the tree into `psygreg/scripts` (wiping everything but LICENSE/README.md). The synced mirror's default branch is the client's remote sync source; new commits there reach installed clients on the next sync without any tagging step.

### Other tooling

- `dev/git_db.py` — manual (unwired) builder of `p3/scripts/git-db.json`: latest-release assets for every git-type repo, arch detection delegated to `app.architecture` (the same policy the runtime uses). Consumed by `p3/app/repo_parser.py`, `src/catalog-rs/repo.rs` and the runtime ISA derivation in `architecture.require_entry`.
- `install.sh` (root) — user installer: `_resolve_route()` maps `$ID` (with `$ID_LIKE` as the fallback) to the installation handler and the release-asset kind that handler consumes (the Manjaro-family AUR route consumes none; immutable systems and Solus take the Gear Lever AppImage route); only the route's own asset kind is selected, through the staged architecture validation (`architecture_prepare`/`architecture_verify` gates the host, refuses foreign payloads, and payload-verifies every download). When the host's preferred kind has no native asset in the release (an aarch64 host on an x86-only release) but a verified native AppImage exists, the installer warns explicitly and falls back to the AppImage route; with neither candidate it fails closed. Before the architecture staging, `_lt_repair_gate` resolves the installed state: when the installed version already equals the release tag, a plain reinstall would silently no-op and keep any damage (a third-party package operation that deleted a package-owned file — discussion #1500), so the route's package manager verifies the installation instead — dpkg `--verify` + owned-file existence scan, `rpm -V` (mtime/user/group drift ignored), `pacman -Qkk`, or the AppImage desktop-entry/file discovery — an intact installation exits as "already installed and up to date" (skipping all staging and downloads), a damaged one is reinstalled with repair semantics (`_lt_repair`: apt `--reinstall`, dnf/yum `reinstall`, a removal before the pamac build; the AppImage fallback refuses in repair mode), and older, newer or undetectable installations keep the legacy path. `LINUXTOYS_REINSTALL=1` forces the clean reinstall of an intact same-version installation.
