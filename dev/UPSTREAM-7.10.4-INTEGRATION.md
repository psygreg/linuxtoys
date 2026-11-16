# Selective LinuxToys 7.10.4 integration

2026-11-16. Local branch: `arm64-support`. This is a selective compatibility
integration, not a merge of all upstream changes or new native qualification.

## Baseline and evidence

- Starting HEAD: `b295c8b147450856af82c75425efe843acdf95e4`, two commits ahead
  of `fork/arm64-support`. No tracked changes existed; untracked `.repowise/`
  was preserved and excluded from the commit.
- Native MCP production baseline:
  `d378deaddd5ef16a2d9d7e2accaf01e95780096e`, an ancestor of HEAD. The only
  intervening commit corrects test fixture permissions; it changes no production
  source.
- The completed record is
  `target/mcp-staging-final-20261116-2c89r7wu/RESULTS.json`, with
  `native_qualification_complete: true` and that exact baseline. Its referenced
  focused/regression, filesystem, legacy CLI, GTK/PTY and representative staged
  payload evidence remains intact. Earlier stopped runs are retained as history;
  they do not replace the completed aggregate result.
- That evidence establishes only its recorded native Ubuntu ARM64 MCP skill
  scope. It does not qualify this integration, package lifecycles, AMD64 runtime,
  full application startup, or live MCP transport/service authentication.
- Previous upstream assessment: `9ee756b6e4bd487b70bbd796c76a9f837f9bfc94`.
  Requested release: `3d19ac5f4851430da0eb2e41d44e85ae1b7807a5` (tag `7.10.4`).
  Package-lock implementation: `faea91605741010fbf01cdc48475354302e458ec`.
  Local/upstream merge base: `83244aaf1ca5427e5dd57133f6eaf92a6cc1627d`.
  The previously assessed upstream commit is not a local ancestor. All eight
  commits in `9ee756b6..3d19ac5` were inspected, including their complete patch.
  No merge, reset, rebase, force update, or attribution rewrite was performed.

## Upstream disposition

| Upstream commit | Decision and local result |
| --- | --- |
| `38fe0cf9` repository links | Adapted to the local architecture map: working relative links to this report and existing policy documentation. The absent upstream `.ai/AGENTS.md` is not restored, and the upstream architecture map is not substituted for the local implementation map. |
| `a8d828a7` Chinese quoting | Adopted escaped quotes in Drive/OneDrive instructions; the Chinese file now sources without accidentally interpreting instruction text as shell syntax. |
| `7c0db3c1` RAM messages | Adopted one `_cram` requirement shared by both messages in all 58 local shell translations. |
| `bb2b7249` Amharic NUL | Adopted removal of the embedded NUL. |
| `9734c329` RAM detection | Adapted KiB/decimal-GB comparison, anchored `MemTotal` parsing and inclusive minimum. Preserve the previously documented **16 GB** floor; reject upstream's reduction to 8 GB and its continuation after an unknown measurement. Malformed, absent, zero, negative, leading-zero or oversized measurements refuse activation. Preload remains x86-only. |
| `e465e39e` report RAM context | Adopted measured GiB with one decimal. Added positive-value/unit validation and safe fallback on malformed input, I/O failure or numeric overflow. Existing context/report behavior remains. |
| `faea9160` installer/dispatch locks | Adapted self-update dispatch gating and native installer transaction coverage. Reuse `libs/packages.bash`; reject duplicated installer lock scanners, automatic Pacman lock deletion and unbounded replay. Details below. |
| `3d19ac5f` version | Adopted `7.10.4` in both `src/ver` and `app/updater/__init__.py`; local metadata was previously `7.9.8`. This version bump does not imply adoption of earlier deferred upstream refactors. |

## Package ownership, concurrency and failure handling

`packages.bash` is the single Bash guard implementation. The standalone
installer obtains it from the same trusted local checkout or immutable release
source as its architecture helper, then requires guard API 2. Local ownership,
permissions and no-symlink checks now include the library and its directory.
An inherited environment marker cannot satisfy the API requirement. Readiness
is checked before installer repository/package mutation; no permissive fallback
uses an older library. Download/checksum/ISA validation still precedes package
operations and existing-installation removal.

A subshell scopes library loading so it cannot replace the installer's
exit-on-success `info()` or the caller's cleanup traps. Guard translation
state is reloaded so inherited loader flags cannot reset messages to English. APT, DNF/DNF5/YUM,
Pacman and Zypper use the same transaction engine as application helpers.
Their existing public entry guards and standby helpers also delegate to that
shared wait routine. Debian interrupted-operation recovery now passes
`dpkg --configure -a` through the guarded APT transaction path.

The engine observes native locks; it never owns or unlinks them. A PID marker
or a missing process/descriptor is not proof that a lock can safely be removed.
Pacman's lock can remain authoritative after its creator closes the descriptor,
so even an apparently stale `db.lck` gets bounded standby and controlled refusal.
Manual recovery requires independently verifying ownership. APT/DNF/Zypper
marker files without live process/descriptor evidence are not treated as held
locks and are left unchanged. No PID-file deletion, kill-by-PID recovery or
replacement-lock unlink race is introduced.

Each transaction shares one nominal 300-second elapsed-time standby budget
across entry and collision waits, with sleep intervals capped by the remaining
budget. Timeout returns 124. A transaction can be retried **at most twice**, and
only after a recognized package-manager lock-refusal diagnostic. An unrelated
manager appearing after a dependency/download/authentication failure does not
justify replay. `LC_ALL=C` is requested for diagnostic matching; unrecognized
messages fail with the original status rather than authorizing speculative
retries. Signal statuses are returned without retry. Stream/temporary-file
failures also stop processing. These bounds do not forcibly terminate an active
native package process or cap a manager's own internal waits.

Output streams through `tee` into a private per-attempt temporary log; manager
status comes from `PIPESTATUS`, including when `pipefail` is disabled. Normal
failure, interruption and completion clean the log without replacing parent
traps. Stdout/stderr are combined in that streamed diagnostic output. SIGKILL,
power loss and native transaction durability are not qualified by these tests.

Installer metadata/setup/dependency failures stop installation, preserve the
failure code and cannot print a success message or fall through into a second
`ID_LIKE` dispatch. DNF prerequisite installs use `-y`; Pacman and Zypper retain
noninteractive flags. Explicit noninteractive mode uses `sudo -n`, so missing
credentials fail promptly rather than waiting for terminal authentication.

Self-updates count as native transactions before terminal dispatch because a
static scan cannot see package commands inside a downloaded installer. Ordinary
entries retain their previous scanner. The existing queue resume, timeout,
destruction, exclusivity and release-age eligibility behavior remains: an
outdated installation can still enqueue its own update, while mixed ordinary
script work retains the version gate. YUM transactions are now recognized in
both process detection and command scanning; read-only YUM queries are excluded.

GUI, TUI and SteamOS update pipes propagate download failures with `pipefail`;
a failed download cannot create a completion marker. The background updater
runs its staged installer in a child Bash so the installer's EXIT trap cannot
replace cleanup of the downloaded script. A failing fixture installer with its
own trap verifies both status propagation and parent cleanup.

## Architecture and exact-byte bundle compatibility

The central ISA helpers, payload validation, availability checks, packaging
policy and all 176 curated route declarations retain their existing architecture
sets. The only curated script body changed is `extra/preload.sh`; its reviewed
digest, bundle manifest and preferred client revision were regenerated together.
No ARM64 feature, vendor build, repository revision or native payload was
promoted. Foreign/unknown payload refusal remains authoritative for both x86-64
and ARM64; this integration adds no override.

New reviewed bundle revision:
`7334b1c53310ff097b6d731727958dee73d2ca5aaec15f56cde85985887fa5c5`.
A deterministic local review artifact was prepared and verified under the new
ignored review directory. Its printed rollout tag is a proposed name only: no
Git tag or remote revision was created or published. Prior bundle and native
qualification evidence remains historical evidence for its original bytes.

The MCP skill helper, server, both reviewed skill assets and menu caller are
byte-identical to `d378dead`. Shared shell/terminal paths changed, so matching
those components does not extend the earlier native qualification to this HEAD.

## Verification

Host: macOS arm64 27.2.1, Python 3.13.7, Bash 3.2.57. No new VM/native Linux run,
native distro package transaction, package build, application startup, report submission,
service change, push, publication or deployment occurred.

- **278 tests run: 258 passed, 20 platform/tool-dependent skips.** This includes
  architecture, payload/installer ordering, package-state/recovery, updater,
  exact-bundle/preparation, MCP, native-build contracts, packaging contracts,
  loader, persistence and reporting regressions.
- **46 new focused tests passed**, with additional family/scenario subtests:
  APT, DNF/DNF5/YUM, Pacman and Zypper safe mocks; stale/held locks; vanished or
  reused PID evidence; concurrent fixture transactions; one wait budget; retry
  exhaustion; dependency/authentication failure; timeout; interruption; actual
  child SIGTERM; stream failure; cleanup; self-update queue/version eligibility;
  RAM thresholds/context; all 58 translations; unchanged ISA restrictions.
- **35 existing MCP tests passed.** Optional runtime/process/HTTP interfaces
  remain mocked where the existing host suites specify them.
- Black 25.11.0 checks passed for new/changed standalone Python helpers and the
  complete new test file; unrelated older module formatting was preserved.
  Complete new-test Flake8 lint (88 columns) and fatal lint across all ten
  changed/new Python files passed. Python 3.10 grammar parsing and in-memory
  compilation passed; this is not Python 3.10 runtime qualification.
- Bash syntax and ShellCheck 0.11.0 error-severity checks passed for all **61**
  changed shell files. Warning-level comparison of the three main shell files
  found **no new warnings**; 17 existing findings remain. No blanket warning
  suppression or unrelated warning cleanup was introduced. ShellCheck came from
  a pinned `shellcheck-py==0.11.0.1` wheel in a disposable `/private/tmp` tool
  directory; no system Python or distro packages were modified.
- Script preparation `--check`, local artifact generation/verification,
  semantic checks for unrelated Python functions, route-policy preservation
  checks and `git diff --check` passed.

All native manager commands use safe fakes. Concurrent fixture success proves
wrapper/mock behavior, not native package-manager lifecycle safety. x86-64 and
ARM64 compatibility is demonstrated by policy/selector/mutation-order fixtures;
there was no native x86-64 execution or emulation. Native manager internal waits,
distribution-specific lock variants/diagnostics, real privilege/TTY behavior,
package scriptlet failures and real installer/update recovery need separate
qualification. Unchanged rpm-ostree/eopkg transaction/migration paths are not
newly qualified or broadly refactored here. Nala/F3 and other deferred feature,
packaging, service, protocol and publication work remain outside this milestone.

## Changed files and preservation

Production: `install.sh`; `p3/libs/packages.bash`; `p3/app/package_guard.py`;
`p3/app/term_runner.py`; `p3/app/tui/runner_helper.py`;
`p3/app/updater/update_helper.py`; `p3/app/updater/update_dialog.py`;
`p3/app/antenna/antenna.py`; `p3/scripts/extra/preload.sh`; all 58
`p3/libs/lang/*.lib` translations; `p3/app/architecture-routes.json`;
`p3/app/script-revisions.json`; `p3/scripts/.linuxtoys-scripts.json`;
`p3/app/updater/__init__.py`; `src/ver`.

Tests: new `dev/tests/test_7104_integration.py`, plus fixture adaptations in
`dev/tests/test_architecture.py` and `dev/tests/test_package_states.py`.
The package-state fixture now persists simulated dpkg recovery in temporary
files, matching an external command's persistence across subshells. The trust
fixture includes and tests the newly required library path. Permission/state
refusals are not weakened.

Documentation: this report and `.ai/ARCHITECTURE.md`. Historical reports and
qualification evidence were not rewritten. All 2,941 inventoried baseline hash
entries were checked: only the 75 intended tracked source/document changes
changed; 2,866 other entries, including prior evidence and `.repowise/`, matched.
No unexpected content change was found. Existing native artifacts were not
rebuilt or replaced. Commit history and the original starting HEAD remain
ancestors of the local milestone commit.

Detailed review patch, baseline/preservation hashes, native MCP source hashes,
static logs, test logs and local bundle artifact are retained under
`target/upstream-7.10.4-review/`. That directory is ignored and is not part of the
source commit. The final task response identifies the completed local commit.
