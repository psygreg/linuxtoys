# LinuxToys — Architecture

> Companion to `AGENTS.md` (rules) — this document describes *how the project is structured*, not *how to work in it*.

## 1. What LinuxToys is

A cross-distro Linux app installer/manager. A curated catalog of **Bash install scripts** (one script per app, ~500+ files under `p3/scripts/`) is presented through a **PyGObject/GTK3 GUI** (default) or a **Textual TUI** (CLI mode). Execution is mediated by a busy package-manager preflight (`package_guard`), `askpass`/`sudo_` privilege escalation in the bash core, AUR source-security verification (`aur_security`), a transaction lifecycle (transmap + `term_registry.ExecutionRegistry`), a **git-based script sync** (`git_scripts_manager` + `scripts_loader`), and an in-app **self-updater** (`updater/`).

Two native Rust components: **`src/catalog-rs`** → `_catalog_rs` is compiled via PyO3/maturin (catalog JSON parsing/repo-name normalization, git-release asset classification; shared with Python through the `_catalog_rs` module; see `dev/git_db.py`), and **`src/gui-rs`** → `liblinuxtoys_gui.so` is a plain cargo cdylib exposing a C ABI consumed by the Python GUI through ctypes (GTK theming helpers).

## 2. Repository tree (annotated)

```
linuxtoys/
├── install.sh              # User-facing one-shot installer (deb/rpm/arch/suse/appimage routing)
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
│   ├── build/              # Packaging per target: copr/ rpm-spec, deb/ (PPA), pkg/ (AUR), appimage/
│   ├── git_db.py           # Builds p3/scripts/git-db.json (latest git-release assets index)
│   └── build_output/       # (generated) packaging output
├── .github/workflows/
│   ├── release.yml         # version → deb+rpm+arch+appimage → GitHub release
│   └── sync-scripts.yml    # mirror p3/scripts/** → psygreg/scripts repo
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

## 4. Module map — Python application (`p3/app`)

### 4.1 Catalog/data layer

| File | Role |
|---|---|
| `repo_parser.py` | Repo-list layer over `catalog-rs`: entry validation/resolution (Rust), list-JSON walking, install-script materialization (`compose_install_script` builds the text; `create_install_script` writes the transient `.sh` and keeps the runner's appimage "true" convention), git-db consumption, commerce/description overlays. |
| `parser.py` | Catalog core: Rust-assisted scripts-tree index, `.sh` header parsing, compat/visibility policy, `appstream_context` (shared resolution context for URI/MCP), category/repo/AppStream entry materialization, display-name resolution. (§4.3) |
| `search_helper.py` | `SearchEngine` over scripts + AppStream (+local scripts): Rust index overlay, weighted scorer, grouped-by-category results. |
| `appstream_cache.py` | Builds/publishes the persistent AppStream catalog (`~/.cache/linuxtoys/appstream/catalog.json` + `extensions.json`, schema 26): native/Flatpak/Snap/Homebrew/AppImage sources, source fingerprints, ODRS ratings + Snap votes APIs. |
| `appstream_parser.py` | Adapts the cached catalog into LinuxToys entries: source/omit/category policy, Rust runtime catalog (search/browse/installed/featured slices) with stale-while-revalidate. |
| `appstream_runner.py` | Persistent hidden-PTY runner + session queue for AppStream transactions (install/remove/extension/snap-revert/apt-refresh/skill/local-package/AppImage/homebrew/AUR) with completion markers, stall watchdog, transcripts, registry finishing, conflict gating; AUR source-security verification delegates to `aur_security` (provenance cross-check on). |
| `appstream_queue.py` / `appstream_extensions.py` | GTK views: session AppStream queue; embedded Flatpak-extensions view for the app page. |
| `aur_security.py` | Shared AUR source-security scanner (GUI runner + TUI executor + MCP): shallow-clone inspection of PKGBUILD + `*.install` against the obfuscation rules; the GitHub provenance cross-check is the opt-in `check_provenance=True` superset used by the GUI. |
| `aur_cache.py` | Opt-in AUR metadata cache (`catalog.bin` via catalog-rs): enable/refresh lifecycle (`refresh_catalog` is the shared refresh sequence), lazy browse/search views. |
| `homebrew_catalog.py` | Homebrew snapshot cache (formula.json + analytics popularity, 14-day TTL) feeding the AppStream-style catalog; `materialize_install` for queued formulae. |
| `snap_catalog.py` | Snap Store metadata over snapd's Unix socket → AppStream-style entries (14-day cache). |
| `appimage_catalog.py` | AppImage community feed cache + intent-based category inference; release resolution/download for installs and updates (ELF validation, 4 GiB cap). |
| `package_guard.py` | Busy native package-manager preflight shared by every runner (lock detection + bounded wait). |
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
| `term_runner.py` | `TerminalRunner` mixin: VTE execution engine — spawn with library env, serialization vs AppStream runner, package-manager busy-wait, transmap/registry lifecycle, auto-revert queueing, runner-lock channel (`/tmp/linuxtoys/runner-state-*`). |
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
| `compat.py` | Host/compat policy: cached host probes, compat keys (OS/GPU/CPU/desktop/init/session), script-header policy (`# compat/gpu/desktop/…`), privilege checks, container/WSL/GregOS detection, cache dirs. |
| `library_loader.py` | Static bash-library-requirement detection + canonical script execution plumbing (preamble/env/argv, `call_script` nested resolution, CachyOS mirror preflight). CLI for nested execution + AppStream materialization. |
| `lang_utils.py` | Language detection/translation loading/settings persistence (language.conf, updates, error reports, MCP toggle, port). |
| `dev_mode.py` | `DEV_MODE` env simulation + script dry-run validation (bash -n, headers, sudo flow, dependencies). |
| `scripts_loader.py` | Scripts-source bootstrap (sync → scripts dir), `LT_DEBUG`-gated git-sync logging. |

#### Execution & side effects
| File | Role |
|---|---|
| `manifest_helper.py` | Manifest engine: load/validate/replay manifests, registry→manifest export, shared package/flatpak/snap installers, CLI manifest mode driver, sysup resolution. |
| `revert_helper.py` | Registry/transmap-driven reversal: ~20 op families → uninstall/auto-revert script builders over shared plumbing (`_revert_script_preamble`, `_registry_cleanup_heredoc`, `_write_revert_script`, `_revert_entry`, `_flatpak_remove_command`). Entry loading delegates to `registry_utils.load_registry_transactions`. |
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
| `uri_parser.py` | GUI-agnostic `linuxtoys://` validation + stable-target resolution. |
| `translate_helper.py` | GTK-free description translation (Google endpoint) + shared cache — the single pipeline for GUI, TUI and MCP. |
| `needed_helper.py` | Prerequisite-list and run-confirmation dialogs (shared `_script_row`/`_script_list_scroller` list rendering). |
| `local_scripts.py` | `LocalScriptsCtl` mixin: drag-and-drop, create/edit/delete/export of `~/.local/linuxtoys/scripts` (shared confirm/chooser/cleanup helpers for the singular and plural flows). |
| `atomic_io.py` | Atomic file writes shared by every cache/persistence site: `atomic_write_bytes/text/json` (mkstemp staging + `os.replace`, optional fsync/mode, tmp cleanup on failure). |
| `language_selector.py` / `about_helper.py` / `deepin_immutable_helper.py` | Language picker; About dialog (GitHub contributors); Deepin immutable-mode one-shot flow. |
| `skills_fetcher.py` / `skills_view.py` | skills.sh CLI fetcher (TTL cache) + GTK Skills Seeker view. |
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
| `update_helper.py` | Release lookup (GitHub → Gitea fallback), install-source detection (PPA/Copr/git disables self-update), `build_update_script(mode)` — the single installer-text builder for the VTE dialog (`terminal`: library + sudo_rq, bare pipe on SteamOS, optional completion marker), the headless updater (`background`: askpass + download-then-source in the same shell) and the TUI (`tui`: minimal pipe); `is_steamos()`; `run_background_update` via generated bash script; `compare_versions` delegates here from `version_gate` (also used by `kernel_update_helper`). |
| `version_gate.py` | Non-blocking cache-backed gate refusing script runs when more than `GATE_GRACE_RELEASES` releases behind; `update-state.json` cache (atomic write via `app.atomic_io`), daemon-thread refresh, fails open; `compare_versions` is the shared tri-state comparator (right-padded tuples). |
| `update_dialog.py` | GTK dialogs: changelog `UpdateDialog` (own dependency-free Markdown renderer; writes the `build_update_script("terminal", …)` installer to `/tmp/.self_update_lt`), error dialogs, `scripts_blocked_by_version` gate flow for the GUI. |

#### `p3/app/antenna/`

`antenna.py` — bug-report backend: system context string (OS/CPU/GPU/desktop/init), last-10-script history, `LogCapture` stdout/stderr tee, machine-id HMAC token bootstrap against `bug.linux.toys`, `submit_issue` POST, and a global exception hook that auto-submits unhandled exceptions. `install.sh`, CI, and each packager reference none of this directly — it is runtime-only.

## 5. Catalog scripts & data (`p3/scripts`)

The catalog is **data, not code**: one `.sh` per app plus JSON/metadata. Headers are machine-parsed (`parser.py`, `scripts.rs`), so their keys are a contract:

- Script header: `# name:`, `# version:`, `# description: <i18n key>`, `# icon:`, plus policy flags — `# compat:` (e.g. `!solus, !ostree`), `# gpu:`, `# hybridgpu:`, `# desktop:`, `# systemd:`, `# wayland:`, `# cpu:`, `# deviceids:`, `# reboot: yes|ostree`, `# revert:`, `# registry:`, `# negates:` (hides other scripts when this one succeeds), `# localize:`, `# nocontainer`, `# gregos-version:`.
- `category-info.txt` per directory: `ICON:` + `description: <i18n key>`.
- `repos.json` + `lists/*.json`: repository/app entries (source URLs, screenshots, descriptions.json per list with translated long descriptions, hooks under `scripts/lists/<app>/*-pre.sh`/`-post.sh`); git-type repos are resolved via `git-db.json` (built by `dev/git_db.py`).
- `scripts/sysup.sh` + `scripts/sys/` — system-update and driver flows; `scripts/lists/` — upstream hooks.
- i18n: `p3/libs/lang/<code>.json` (app strings) + `<code>.lib` (bash message strings), ~58 languages.

## 6. Bash core libraries (`p3/libs/*.bash`)

Sourced by catalog scripts (via `linuxtoys.lib`/`library_loader.py` static analysis). `linuxtoys.lib`, `helpers.lib` and `optimizers.lib` are **symlinks** to their `.bash` twins, so the two names always stay in sync.

| File | Role |
|---|---|
| `linuxtoys.bash` | Core loader (conditionally sources the rest), zenity compat layer, privilege escalation (`askpass`/`sudo_`), message + question/selector dialogs (`_msg`, `question`, `radioselect`, `listselect`, `userinput` — the radio/list selectors share `_select_parse_options`) with MCP-agent answer passthrough, `_lang_` i18n, runner locks, transmap (transaction map), `call_script` (script→script calling incl. AppStream resolution), CachyOS mirror preflight. |
| `packages.bash` | The package-management core (~3.2k lines): per-manager lock-guard + busy-wait + transaction-retry trios (pacman/apt/dnf/zypper/eopkg/rpm-ostree); `pkg_install`, `pkg_flat`, `pkg_snap(_revert/_file)`, `pkg_fromfile`, `pkg_tarball`, `pkg_binary`, `pkg_fromurl`, `pkg_make`, `pkg_fromrelease`, `pkg_appimage(_update/_rm)` with Gear Lever integration, `pkg_npm`, `pkg_bun`, `pkg_brew(_remove)`, `pkg_remove`. |
| `sysinfo.bash` | `/etc/os-release` detection (`sysdetect`, `is_*` family incl. ostree/ublue/gregos/restricted hosts) + GPU/compute capability probes (NVIDIA/Intel/AMD, ROCm/Rusticl PCI-ID lists, ReBAR, hybrid GPU). |
| `fsops.bash` | Reversible filesystem "prep" ops (backup-before-edit/create/remove → transmap) + Distrobox container variants (`distrobox_prep_dir(_edit)`, `distrobox_copy_`, `distrobox_move_` over the shared `_transfer`/`_distrobox_transfer` flag-splitting + fallback plumbing). |
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
| `repo.rs` | Repo-list (repos.json / lists/*.json) static+runtime validation, git-URL canonicalization, arch alias mapping, full repo-catalog assembly (icons/screenshots/translations, dedupe). ~30 private validators/helpers; JSON/ID helpers delegate to `shared.rs`. Tests: `runtime_compat_tests`. |
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
| `copr/` | RPM + source tarball via `rpmbuild` + `linuxtoys.spec` | cargo-vendors staged tree for sandboxed builds |
| `deb/` | signed source upload to Launchpad PPA + binary `.deb` via `debuild` | Launchpad duplicate guard via API; `LINUXTOYS_TEST_MODE` skips upload probe |
| `pkg/` | AUR: `.tar.xz` + sed-updated `PKGBUILD` + `makepkg` | |
| `appimage/` | `LinuxToys-<v>-<arch>.AppImage` via pkgforge quick-sharun | builds glycin-ng + compat shim, replaces upstream glycin, bundles icon themes |

All four package `p3/` at `/usr/share/linuxtoys` with the same launcher heredoc (`/usr/bin/linuxtoys`) and the same permission normalization; all three distrobox-spec ones run the same maturin+cargo+wheel-extract+assert block.

### CI (`.github/workflows/`)

- `release.yml` — triggers: `workflow_dispatch` (version/upload_ppa/test) or push to master touching `src/ver`. Jobs: `prepare` (version + release notes + `vendor_deps.sh`, uploads `tui-vendor`), `deb-ppa`, `rpm` (fedora container), `arch-pkg` (arch container), `appimage` (arch container), then `release` (sha256sums + `gh release create`). Test mode requires an existing tag; already-tagged push no-ops.
- `sync-scripts.yml` — push to master touching `p3/scripts/**` mirrors the tree into `psygreg/scripts` (wiping everything but LICENSE/README.md).

### Other tooling

- `dev/git_db.py` — manual (unwired) builder of `p3/scripts/git-db.json`: latest-release assets for every git-type repo, arch detection delegated to `_catalog_rs`. Consumed by `p3/app/repo_parser.py` and `src/catalog-rs/repo.rs`.
- `install.sh` (root) — user installer: routes on `/etc/os-release` (`$ID` → `$ID_LIKE`) to deb/rpm/suse/arch/appimage handlers; immutable systems (rpm-ostree/SteamOS/GNOME OS/…) → Gear Lever AppImage flow.
