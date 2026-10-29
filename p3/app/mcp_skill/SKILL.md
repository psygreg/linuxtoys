---
name: linuxtoys-mcp
description: Enable and drive the LinuxToys MCP server to manage Linux apps on the user's machine like a user would - search the catalog, read app pages (descriptions, screenshots, donation links), install and remove apps, install local package files (.deb, .rpm, .appimage and more, optionally downloaded from a URL), install and remove Flathub app extensions/addons, change LinuxToys settings, and translate descriptions. Use when the user asks to install or remove software through LinuxToys, asks to install a package file or app extension, change its settings, or when configuring AI agent access to LinuxToys.
---

# LinuxToys MCP

LinuxToys is a cross-distribution Linux app manager. This skill lets you use it
on the user's behalf, exactly like a user would: browse the catalog, open app
pages, install/remove apps, and change app settings. Password prompts always
appear on the **user's screen** — never ask the user to hand you their password.

## 1. Check whether the server is running

The server is an opt-in systemd **user** service (`linuxtoys-mcp.service`) that
ships with the app but is not enabled by default. Check it without any
credentials:

```bash
curl -fsS http://127.0.0.1:7420/health
```

- A JSON response means the server is up → go to section 3.
- Connection refused means it is not enabled → section 2.

## 2. Enable it (no root required)

First check whether the unit exists:

```bash
systemctl --user cat linuxtoys-mcp.service >/dev/null 2>&1 && echo unit-installed || echo unit-missing
```

- **unit-installed**: enable and start it (user service — no sudo):

  ```bash
  systemctl --user enable --now linuxtoys-mcp.service
  systemctl --user is-active linuxtoys-mcp.service
  ```

- **unit-missing**: the unit is installed by the app when the user first
  switches it on. Ask the user to open **LinuxToys → menu (☰) → MCP Agent
  Server** once. That installs and enables the service immediately; after that
  it also starts on its own at every login (it is tied to the graphical
  session, which is what lets password dialogs reach the user's screen).

Do not run LinuxToys install commands with `sudo` yourself — all privilege
escalation happens through the app's own on-screen askpass dialog.

## 3. Connect as an MCP client

- **Transport:** MCP Streamable HTTP
- **Endpoint:** `http://127.0.0.1:7420/mcp`
- **Auth:** the token is generated at `~/.config/linuxtoys/mcp-token`
  (readable only by the user). Send it as a header:

  ```
  Authorization: Bearer <contents of ~/.config/linuxtoys/mcp-token>
  ```

  (`X-LinuxToys-Token: <token>` is also accepted.)

Configuration examples:

```jsonc
// opencode (~/.config/opencode/opencode.json)
{ "mcp": { "linuxtoys": {
    "type": "remote",
    "url": "http://127.0.0.1:7420/mcp",
    "enabled": true,
    "headers": { "Authorization": "Bearer <TOKEN>" } } } }
```

```bash
# Claude Code
claude mcp add --transport http linuxtoys http://127.0.0.1:7420/mcp \
  --header "Authorization: Bearer $(cat ~/.config/linuxtoys/mcp-token)"
```

After connecting, call `server_info` once to confirm the session works.

## 4. Tools

| Tool | Purpose |
| --- | --- |
| `server_info` | Version, endpoint, service state, busy jobs |
| `list_categories` | Catalog categories |
| `search_apps(query, limit?)` | Search every catalog (scripts, repos, Flathub/Snap, AppImages); returns stable `id`s |
| `get_app_details(app_id)` | App page: description, screenshots URLs, homepage/donate/purchase links, version, install state |
| `get_screenshot(app_id, index?)` | Returns an image so you can see the app's screenshots |
| `install_app(app_id)` | Queue an install; returns a `job_id` |
| `fetch_package_url(url)` | Download a package file (.deb/.rpm/.pkg.tar.*/.pacman/.eopkg/.flatpak/.flatpakref/.snap/.appimage) from an http(s) URL into a private staging directory; returns its local path |
| `get_package_file_details(path)` | Inspect a local package file like the GUI's package view does: name, version, architecture, maintainer, description, size, format, and whether that package type is supported on this system |
| `install_package_file(path)` | Queue the install of a local package file through the same guarded machinery; returns a `job_id` |
| `list_app_extensions(app_id)` | List a Flathub app's extensions/addons (VLC plugins, Steam compatibility tools, ...), each with its installed state |
| `install_app_extension(app_id, extension)` | Install one extension of an app by its component id or full flatpak ref; returns a `job_id` |
| `remove_app_extension(app_id, extension)` | Remove one installed extension of an app; returns a `job_id` |
| `remove_app(app_id)` | Queue a removal; returns a `job_id` |
| `get_job(job_id, tail_lines?)` | Job state (`queued`/`running`/`success`/`error`), exit code, log tail |
| `list_jobs()` | Recent jobs |
| `get_settings()` / `set_settings(...)` | Automatic updates, automatic bug reports, language |
| `translate_text(text, target_language?)` | Same translation method as the app page; defaults to the user's language |
| `translate_app_description(app_id, target_language?)` | Translate a full app description (shares the GUI cache) |
| `get_registry_entries(query?, limit?)` | Action Registry: everything installed through LinuxToys, with changes |
| `export_registry_manifest(destination?)` | Portable manifest of installed apps (`linuxtoys --manifest <file>` to replay) |
| `open_support_link(app_id, kind, index?)` | Open one of the app's own links (homepage/donate/purchase/subscription) |

## 5. Typical flows

**Install something:** `search_apps` → show the best matches to the user →
`get_app_details` on the chosen one (tell the user what it does) → confirm →
`install_app` → poll `get_job` every few seconds until `success`/`error` →
report the outcome (and the log tail on error). Installs that need root pop
the password dialog on the user's screen; tell the user to expect it and wait
for them to finish — do not ask them to paste the password to you.

**Install a package file (the user gave you a link or a local file such as
.deb/.rpm/.appimage):** `fetch_package_url(url)` when the file still needs
downloading → `get_package_file_details(path)` → tell the user what the file
is (name, version, format) and stop if it is not supported on this system →
confirm → `install_package_file(path)` → poll `get_job`. It goes through the
same guarded machinery as a package-view install, so the usual root password
dialog appears on the user's screen when needed.

**Flathub app extensions (VLC plugins, Steam compatibility tools, ...):**
when `get_app_details` reports `extensions_available`, run
`list_app_extensions` (each entry shows its installed state) → tell the user
which one you will add or remove → confirm → `install_app_extension` /
`remove_app_extension` (pass the component id or full flatpak ref from the
list) → poll `get_job` → verify with `list_app_extensions`. These are plain
`flatpak install/uninstall` operations: system-scope ones may pop a password
dialog on the user's screen, and unlike app installs they are not recorded in
the Action Registry — the installed state comes from `list_app_extensions`.

**Remove something:** check `get_registry_entries` / `get_app_details`
(install state) → confirm with the user → `remove_app` → poll `get_job`.

**Change settings:** `set_settings` with only the fields to change
(`automatic_updates`, `automatic_bug_reports`, `language`). A running GUI
applies a language change on its next launch.

**Translate for the user:** `translate_app_description` (or `translate_text`
for arbitrary strings).

## 6. Rules

- Always tell the user what you are about to install or remove, and do it only
  when they asked for it or confirmed.
- Package files (`get_package_file_details` / `install_package_file` /
  `fetch_package_url`) follow the same rule: install only the URL or local
  file the user pointed you at, after showing them what the inspection found.
  Never install a package type that the host-compatibility guard refuses, and
  never pick a package URL yourself for an install the user did not ask for.
- App extensions (`list_app_extensions` / `install_app_extension` /
  `remove_app_extension`) work the same way: only touch the extension the
  user asked about, and never install extensions as a side effect of an app
  install.
- Never ask for or accept the user's password; privilege prompts appear on
  their screen on their own.
- Installs are serialized: one job runs at a time. Poll `get_job` rather than
  re-submitting the same app.
- Jobs are in-memory; if the service restarts mid-way, re-check the app's
  state with `get_app_details` before retrying. For package files, re-check
  the file path: the install re-verifies the exact file that was inspected.
- If an action fails, read the job log tail and report it; don't blindly retry.
