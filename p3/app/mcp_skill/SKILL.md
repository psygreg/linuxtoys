---
name: linuxtoys-mcp
description: Enable and drive the LinuxToys MCP server to manage Linux apps on the user's machine like a user would - search the catalog, read app pages (descriptions, screenshots, donation links), install and remove apps, install local package files (.deb, .rpm, .appimage and more, optionally downloaded from a URL), install and remove Flathub app extensions/addons, clean up the leftover data of uninstalled Flatpak apps, run the app's full system update, handle questions/warnings raised by scripts (ask the user before the run; relay warnings), watch every job to completion in the submission call itself (submissions block until the run finishes and return its outcome; batches of jobs can run through subagents), check for and apply LinuxToys app updates, change LinuxToys settings, and translate descriptions. Use when the user asks to install or remove software through LinuxToys, asks to install a package file or app extension, asks to clean up leftovers of an uninstalled Flatpak app, asks to run a full system update, asks to update or check the version of LinuxToys itself, change its settings, or when configuring AI agent access to LinuxToys.
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
| `server_info` | Version, endpoint, service state, busy jobs, cached script-gate state |
| `get_update_status` | Fresh networked check of LinuxToys itself: running vs newest published release, releases behind, whether the app can update itself on this host, script-gate state |
| `update_linuxtoys` | Run the official LinuxToys self-update as a tracked job (ask the user first — it changes the whole app); the call blocks until it finishes and returns the outcome; then restart the service |
| `update_system` | Run the app's full system update ("Update System" card): distro packages, Flatpaks, Snaps, Homebrew/Bun, orphan and leftover-shortcut cleanup; ask the user first — needs root (password dialog on their screen) and runs very long; the call blocks until it finishes (delegate it to a subagent to stay responsive); may also answer `requires_answers` (release-upgrade choice) before running |
| `list_categories` | Catalog categories |
| `search_apps(query, limit?)` | Search every catalog (scripts, repos, Flathub/Snap, AppImages); returns stable `id`s |
| `get_app_details(app_id)` | App page: description, screenshots URLs, homepage/donate/purchase links, version, install state (and leftover `~/.var/app` data state for Flatpak apps) |
| `get_screenshot(app_id, index?)` | Returns an image so you can see the app's screenshots |
| `install_app(app_id, answers?, wait?, wait_seconds?)` | Install and watch the job to completion: the response is the job's final record (`final: true` — state, exit code, log tail, `warnings`/`live_prompts`/`error_detail`). Curated scripts may first answer `requires_answers`: ask the user the listed questions, then re-call with `answers`. Pass `wait: false` to get a `job_id` at once (multitasking), or `wait_seconds` to cap the block |
| `fetch_package_url(url)` | Download a package file (.deb/.rpm/.pkg.tar.*/.pacman/.eopkg/.flatpak/.flatpakref/.snap/.appimage) from an http(s) URL into a private staging directory; returns its local path |
| `get_package_file_details(path)` | Inspect a local package file like the GUI's package view does: name, version, architecture, maintainer, description, size, format, and whether that package type is supported on this system |
| `install_package_file(path, wait?, wait_seconds?)` | Install a local package file through the same guarded machinery, watching the job to completion like `install_app` |
| `list_app_extensions(app_id)` | List a Flathub app's extensions/addons (VLC plugins, Steam compatibility tools, ...), each with its installed state |
| `install_app_extension(app_id, extension, wait?, wait_seconds?)` | Install one extension of an app by its component id or full flatpak ref, watching the job to completion |
| `remove_app_extension(app_id, extension, wait?, wait_seconds?)` | Remove one installed extension of an app, watching the job to completion |
| `remove_app(app_id, wait?, wait_seconds?)` | Remove an app installed through LinuxToys, watching the removal to completion |
| `remove_flatpak_data(app_id, wait?, wait_seconds?)` | Remove the leftover user data (`~/.var/app/<AppID>`) of a Flatpak app that is no longer installed — the GUI's "Remove data" button on that app's page; refuses apps still installed; watches the removal to completion |
| `get_job(job_id, tail_lines?, wait_seconds?)` | Re-attach to a queued job: state (`queued`/`running`/`success`/`error`), exit code, log tail (filled in while the script runs); `wait_seconds` (max 20) blocks until the job finishes; plus the script's dialog events: `warnings` (attention to relay), `live_prompts` (dialogs the user answered live), `error_detail` (fatal message on failure). Submissions already watch to completion — use this after a `wait: false` submission or a cut-off call |
| `list_jobs()` | Recent jobs (find a job id here if a submission was cut off) |
| `get_settings()` / `set_settings(...)` | Automatic updates, automatic bug reports, language |
| `translate_text(text, target_language?)` | Same translation method as the app page; defaults to the user's language |
| `translate_app_description(app_id, target_language?)` | Translate a full app description (shares the GUI cache) |
| `get_registry_entries(query?, limit?)` | Action Registry: everything installed through LinuxToys, with changes |
| `export_registry_manifest(destination?)` | Portable manifest of installed apps (`linuxtoys --manifest <file>` to replay) |
| `open_support_link(app_id, kind, index?)` | Open one of the app's own links (homepage/donate/purchase/subscription) |

## 5. Typical flows

**Install something:** `search_apps` → show the best matches to the user →
`get_app_details` on the chosen one (tell the user what it does) → confirm →
`install_app` → the call itself runs the install and its response is the
job's final record (`final: true`, `state: "success"`/`"error"`) → report
the outcome (log tail on failure; relay any `warnings`). Installs that need
root pop the password dialog on the user's screen while the call runs; tell
the user to expect it and wait for them to finish — do not ask them to
paste the password to you.

**Install a package file (the user gave you a link or a local file such as
.deb/.rpm/.appimage):** `fetch_package_url(url)` when the file still needs
downloading → `get_package_file_details(path)` → tell the user what the file
is (name, version, format) and stop if it is not supported on this system →
confirm → `install_package_file(path)` → the response is the job's final
record. It goes through the same guarded machinery as a package-view
install, so the usual root password dialog appears on the user's screen
when needed.

**Scripts that ask questions, warn or fail with dialogs:** script dialogs
do not pop on your behalf, and the machine tells you about them:

- *Questions* (yes/no prompts, single/multi selections, text entries): `install_app` and
  `update_system` return `requires_answers` with a `questions` list instead
  of queueing anything. This covers every installation shape: curated
  scripts, repository-list entries (the composed pipeline and its pre/post
  hook scripts) and AppStream overlays (hook scripts on top of an
  AppStream component). Present **each** question to the user through your
  own question UI (`title`/`message`, the listed options, and the suggested
  default), then re-call the same tool with
  `answers={question id: choice}`. Every listed id must be covered; radio
  choices must match one listed option exactly; multi-select accepts
  option string(s) comma-separated or an array; yes/no prompts take the
  literal question id with "yes" or "no"; a text entry (`kind: "input"`)
  takes the exact text the user typed, on one line of at most 1024
  characters, and its `default` is only the suggestion to offer. The run
  then uses those answers instead of dialogs, so the user decides without
  any popups. The service
  pre-filters by branch: only questions whose enclosing branch actually
  matches this host are listed (host-detectable conditions are evaluated
  for real; conditions written as previous-step results — `call_script`
  exports included — presume success; `skipped_branches` counts the
  call sites filtered out, and the note points it out).
- *Warnings*: the job record — the submission's response, or `get_job`
  while re-attached — carries a `warnings` list. These are messages the
  script raised that need attention — relay them to the user promptly,
  whether the job still runs or ends successfully. They are **not**
  failures: a completed run with warnings still worked; do not frame them
  as "the update failed".
- *Fatal dialogs / errors*: on a failed run (`state: "error"`) the fatal
  dialog's message arrives in `error_detail` (the log tail has more):
  report the failure with that message, not just the exit code.
- Prompts the service could not preset (variable-based) are shown live to
  the user and listed in `live_prompts`: let the user know what was asked
  on screen and what they answered. Informational popups are omitted
  entirely; their text lives in the log tail. Password dialogs always
  appear on the user's screen as usual.

**Flathub app extensions (VLC plugins, Steam compatibility tools, ...):**
when `get_app_details` reports `extensions_available`, run
`list_app_extensions` (each entry shows its installed state) → tell the user
which one you will add or remove → confirm → `install_app_extension` /
`remove_app_extension` (pass the component id or full flatpak ref from the
list) → the response is the job's final record → verify with
`list_app_extensions`. These are plain
`flatpak install/uninstall` operations: system-scope ones may pop a password
dialog on the user's screen, and unlike app installs they are not recorded in
the Action Registry — the installed state comes from `list_app_extensions`.

**Flatpak leftover data (an app you can no longer see installed):** Flatpak
keeps per-app user data in `~/.var/app/<AppID>`, which outlives the app. When
`get_app_details` of a Flatpak app reports `flatpak_residual_data` (there is
also a `flatpak_residual_note` naming the exact directory), tell the user
what would be deleted and confirm → `remove_flatpak_data(app_id)` → the
response is the job's final record → verify with `get_app_details`
(`flatpak_residual_data` turns false). No password appears: the data lives
in the user's home. The tool
always refuses apps that are still installed — if the user wants both the
app and its data gone, run `remove_app` first, and only then the data
cleanup.

**Remove something:** check `get_registry_entries` / `get_app_details`
(install state) → confirm with the user → `remove_app` → the response is
the job's final record.

**Update LinuxToys itself:** `get_update_status` (networked; tells you current
version vs the newest published release, how many releases behind it sits,
and whether the app can update itself) → tell the user what changed
(`release_notes`) and get their OK → `update_linuxtoys` → the call runs the
update and its response is the job's final record → on success, restart the
service so the running MCP server picks up the new code:

```bash
systemctl --user restart linuxtoys-mcp.service
```

The GUI also needs reopening. If `update_linuxtoys` fails with "cancelled",
the user closed the password dialog — tell them and let them decide.

**Run the full system update:** `update_system` runs the app's own
"Update System" operation — the same sysup run the GUI's menu card and the
automatic-update service use. It is separate from `update_linuxtoys`: the
app keeps updating itself, the system updates within its current release
(no release upgrade unless the user accepts a prompt). Ask the user first
(it changes the whole system) → `update_system` → the call runs the whole
update and its response is the job's final record; it can outlast any
client timeout, so delegate it to a subagent to stay responsive. The run
needs root: the password dialog appears on the user's screen — wait for
them to type it. Ubuntu and Fedora may also pop a release-upgrade question
there; that answer belongs to the user. Skip when the user's answer is no.
Report milestones, `warnings` and the reboot recommendation from the log
tail; when the run finishes, report what it printed: orphan cleanup
results and whether a reboot is recommended. If it ends `error`, read the
log tail and report exactly where it stopped — a package transaction can
need the user's hands — and do not blindly re-submit the same run.

**Several jobs at once (a batch):** jobs execute one at a time, but you do
not have to babysit them one by one. When the user gives a batch ("install
A, B and C" or a manifest-like list), confirm the whole list once, then
spawn one subagent per job (your platform's subagent/task tool) and tell
each exactly which submission tool and arguments to call — the
`requires_answers` question rounds are yours, handled before spawning (you
can also have each subagent handle its own app's round; then keep it
responsible for that app end to end). Each subagent makes its own blocking
submission and reports its job's final record; relay every outcome as the
subagents return. A queued subagent's call simply waits its turn (installs
serialize), so its password dialog appears when its job starts. Delegate
very long single jobs (like `update_system`) to a subagent the same way,
and keep the main conversation free while the runs unfold.

**If a submission is cut off:** a blocking submission can outlast your
client's tool timeout (opencode's default `mcp.timeout.execution` is 10
minutes). Nothing is lost: the run continues. Find the job id with
`list_jobs` and re-attach with `get_job` (optionally `wait_seconds: 20`)
until `state` is `success` or `error`. To block on long jobs comfortably,
raise the execution timeout (opencode, globally or per-server):

```jsonc
{ "mcp": { "timeout": { "execution": 600000 } } }
```

Job ids are in-memory per service run — they do not survive a restart.

**Change settings:** `set_settings` with only the fields to change
(`automatic_updates`, `automatic_bug_reports`, `language`). A running GUI
applies a language change on its next launch.

**Translate for the user:** `translate_app_description` (or `translate_text`
for arbitrary strings).

## 6. Rules

- Script dialogs are yours to handle, not to suppress: when
  `install_app`/`update_system` answer `requires_answers`, ask every listed
  question of the user before running (answers must match the offered
  options, and a text entry takes what the user typed; every id must be
  covered). Once the run is queued, the submission's response — or
  `get_job` while re-attached — relays
  `warnings` as attention-required messages without calling
  the run a failure — only `state: "error"` with `error_detail` is a
  failure — and mentions `live_prompts` (dialogs the user answered on
  screen). Informational popups are omitted; their text is in the log.
- Job submissions block until the job finishes by default (`wait`, default
  true; `wait_seconds` caps the block; `wait: false` answers at once with
  the `job_id`). If your client times the call out, the run continues:
  find the job id with `list_jobs` and re-attach with `get_job` — never
  re-submit the same app to "check" on it.
- For a user-given batch of jobs, spawn one subagent per job after
  confirming the whole batch with the user; each subagent runs its own
  submission and reports the outcome. Jobs still execute one at a time.
  Never start installs the user did not ask for just because a subagent
  could.
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
- Flatpak leftover data (`remove_flatpak_data`) permanently deletes
  `~/.var/app/<AppID>`. Only run it when the user asked for exactly that or
  confirmed it, show them the directory first (`flatpak_residual_path`),
  and never treat the flag as something to "clean up" proactively for apps
  they may want to reinstall — deleting the data also deletes its saved
  settings and profiles. The tool is the judge of eligibility: it refuses
  apps that are still installed, and a refusal message explains why.
- Updating LinuxToys itself changes the whole app: call `get_update_status`
  first, show the user what is new, and only run `update_linuxtoys` after
  they agree. After a successful update, restart
  `linuxtoys-mcp.service` and reopen the GUI so everything runs the new
  version.
- The full system update (`update_system`) changes the whole system: get the
  user's explicit OK first, tell them the password prompt (and a possible
  release-upgrade question on Ubuntu/Fedora) appears on their screen, and
  never start it while the LinuxToys self-update is active. It is refused,
  like every LinuxToys script run, when the installed app is more than two
  releases behind — offer `update_linuxtoys` first in that case.
- When `install_app`, `remove_app` or `update_system` is refused because the
  installed LinuxToys is more than two releases behind the newest one, do
  not look for workarounds: explain the refusal to the user, offer
  `update_linuxtoys`, and retry after it succeeds. Package installs
  (Flathub/Snap apps, AppImages, AUR, Homebrew, local package files) are
  not affected by this gate.
- Never ask for or accept the user's password; privilege prompts appear on
  their screen on their own.
- Installs are serialized: one job runs at a time. Never re-submit the same
  app while its job is queued or running — re-attach with `get_job`
  instead. `update_linuxtoys` runs in the same queue and refuses to start
  while any other job is active; wait for the queue to finish first.
- Jobs are in-memory; if the service restarts mid-way, re-check the app's
  state with `get_app_details` before retrying. For package files, re-check
  the file path: the install re-verifies the exact file that was inspected.
- If an action fails, read the job log tail and report it; don't blindly retry.
