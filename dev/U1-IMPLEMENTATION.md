# U1 implementation review — 2026-11-12

U1 source implementation is complete and left unstaged for review on
`codex/u1-atomic-reporting`. **The full history/evidence preservation gate fails
because a concurrent attribution rewrite changed refs and two historical evidence
files during this task.** No U1 operation performed that rewrite or repaired its
artifacts. Do not interpret passing source tests as clearance of this gate.

## Source provenance and exact patch

The task began at `8d8ced68cb58c8d74598b97144a3731c6d12078b`, file tree
`cbe4f4aa8292b36a51613597ab9e66a6ec721d4c` (also `a7ed93bb`'s tree).
The new U1 branch was created there. Selected upstream code came from exact
`7d291e3ac54f67e57ddc0a9a58a6fb381c37e1cc`, read through the ignored review
repository; no network retrieval or upstream execution occurred.

During implementation the concurrent attribution operation moved the new branch
and HEAD to `0f516736477449f05040cd92bf3f47773cf87041`. Both old/new HEAD trees
are identical. The U1 patch still applies to the requested M4B file baseline.
The external operation's `target/commit-attribution/verification.json` explicitly
records leaving concurrent U1 worktree edits in place. That file and its recovery
bundle were only read by this task.

Exact source/document files changed or added:

| File | Change |
| --- | --- |
| `p3/app/atomic_io.py` (new) | Upstream bytes/text/JSON helper; unique sibling staging, replace, optional mode/encoding/fsync, best-effort failure cleanup. Clarified durability/default-mode docs and closed the descriptor if `fdopen` fails. |
| `p3/app/homebrew_catalog.py` | Only the validated raw formula-cache publication uses the helper. Bytes, default 0600 mode, fsync, source checks/lock and warning/cached fallback remain. Popularity and generated scripts are unchanged. |
| `p3/app/antenna/antenna.py` | History cache uses default JSON serialization, explicit 0600 and existing directory 0700/silent failure. Correct parent-package AppStream-log import; prepend background logs; classify logs-field HTTP 422 as `EmptyReportError`. Token/bootstrap storage is unchanged. |
| `p3/app/term_reporting.py` | Absolute cursor-row-plus-viewport VTE range before viewport fallback; string/tuple/empty handling. Explain exit-100 cancellation and server-rejected empty reports; preserve manual confirmation, local empty guard, registry/clipboard/captured-log fallbacks and auto-report opt-in. |
| `p3/app/term_runner.py` | One assignment records the decoded child exit status for the reporting guard; the remaining callback is unchanged. |
| `p3/app/easy_cli.py` | One exception tuple adds EOFError to confirmation cancellation. Batch failure/continuation branches are unchanged. |
| `dev/tests/test_atomic_io.py` (new) | Ten focused helper fixtures. |
| `dev/tests/test_u1_reporting.py` (new) | Fifteen whole-module mocked-import/cache/report/VTE/CLI fixtures. |
| `.ai/ARCHITECTURE.md` (new) | Adapted local architecture map including M1–M4 contracts and U1 boundaries. |
| `dev/U1-IMPLEMENTATION.md` (new) | This review report. |

The selected writers are deliberately narrow. Formula metadata is validated
before publication; history is a best-effort diagnostic cache in an already
modified module. The history helper retains last-ten trimming in its caller.
Homebrew popularity was considered but retained because its existing cleanup
failure can propagate; adopting the shared helper would suppress that secondary
error. Writers with historical umask-derived permissions, settings transactions,
secret/bootstrap caches and guarded script writers remain unchanged.

The new helper intentionally retains mkstemp's 0600 default even when replacing
an existing destination. This matches the formula writer; history already
explicitly required 0600. It must not be applied indiscriminately to 0644/umask-
derived caches. No directory fsync or cross-process read-modify-write lock is
claimed. Failed writes preserve the prior cache and retain the callers' fallback
or silent-failure result.

## Tests and static checks

Final selected run on host Python **3.13.7**: **103 tests passed, zero failures,
zero skips**. Of these, **25 are new focused U1 tests**, and 78 are existing
regressions:

| Suite/selection | Passed |
| --- | ---: |
| `test_atomic_io` | 10 |
| `test_u1_reporting` | 15 |
| `test_architecture`, excluding the package-producing DEB fixture | 36 |
| `test_font_routes` | 4 |
| `test_script_compat`, excluding five local-Git-commit fixtures | 17 |
| `test_deb_packaging`, excluding its builder-entry fixture | 6 |
| `test_native_build.ApplicationLifecycleTests` only | 1 |
| `test_script_preparation`: pre-archive refusal/static workflow checks only | 14 |

The helper tests cover old-reader/new-reader replacement, unique same-directory
staging, default/explicit modes before publication, UTF-16 and UTF-8/JSON options,
parent creation/relative paths, serialization/encoding failures, flushed file
content before fsync/replace, opt-in fsync, creation/open/write/fsync/chmod/replace
failures, descriptor closure, missing-target failure, eight concurrent writers
and one failed writer alongside a successful writer.

The integration fixtures import the complete touched modules with fake native,
GTK, HTTP and execution dependencies. Sockets/external processes are denied in
the new integration tests; fake HTTP captures payloads in memory. No real report
or token bootstrap is sent. They cover exact cache bytes/modes/fsync/fallback,
disabled sources, history silent failure, parent AppStream import/log ordering,
empty/control-only reports, logs-field 422 versus unrelated errors and malformed
response details, outdated-version cancellation, actual child-exit status
propagation, denied consent, empty/cancelled/manual/automatic paths, VTE string/
tuple/scrollback/zero-height/missing/error cases and CLI EOF/interrupt cancellation.
Batch fixtures explicitly retain exit-1 continuation, generic/exit-100 prompts,
and exit-130 termination.

Initial test runs found and corrected an Antenna docstring typo and fixture setup
errors. A test assuming ANSI escape-sequence removal was narrowed to control
characters because existing client sanitization does not strip whole ANSI
sequences; that behavior was not expanded in U1. The final run above is green.

Static verification passed:

- Compiled all **121 Python files** under `p3`/`dev` (excluding vendored/generated
  bytecode directories) in memory, without producing bytecode.
- Parsed the six runtime files and two new test files using Python 3.12 syntax
  rules. This is not execution on Python 3.12.
- AST comparison against original `8d8ced68` proves the entire CLI differs only
  by the EOF exception tuple, and the runner only by the exit-status assignment.
- Caller audit finds exactly the two reviewed modules importing `atomic_io` and
  confirms the parent-package AppStream-log import.
- `git diff --check` passed. No formatter/linter dependency was installed.

To reproduce the selected run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 target/u1-implementation/run_regressions.py
PYTHONDONTWRITEBYTECODE=1 python3 target/u1-implementation/check_static.py
PYTHONDONTWRITEBYTECODE=1 python3 target/u1-implementation/check_preservation.py
git diff --check
```

The preservation script records a false full-preservation result for the known
external drift; its exit status alone is not that acceptance gate. The runner
excludes seven named tests and never loads the native build-driver/ABI tests or
successful script-archive preparation tests. Package builders, application/Rust
builds and temporary Git staging/commits were not run. The six DEB tests inspect
metadata/source and temporary-file safety; they do not generate a DEB package.

New, ignored review artifacts are under `target/u1-implementation/`: pre-U1
snapshot `before.json`, `tests.log`, `static.json`, `preservation.json`, the three
reproduction scripts, `source-files.json`, `patch.diff` and `SHA256SUMS`.
The exact patch includes the new untracked files without staging them.
Pre-existing `.repowise/` files were left alone.

## Preservation results and external drift

Passes:

- **970 of 975 baseline tracked files are byte-identical.** The only five changed
  tracked files are the runtime files listed above (the helper is new).
- Scripts, helper Bash libraries, architecture approvals/routes, hidden script
  manifest, revision locks, dependency manifests/locks, version markers, Rust,
  MCP code/skills, startup-removal/privilege policy, installers/builders/workflows
  and all tracked historical M1–M4 evidence remain byte-identical.
- `library_loader.py` is byte-identical. Its package/direct-file imports were not
  migrated, so no new standalone import dependency was introduced.
- The raw index SHA-256 is unchanged and staged diff is empty.
- **2019 of 2021 existing evidence/recovery files** match the pre-U1 snapshot.
  The assessment and its ignored review repository remain unchanged.
- Original M4A DEB remains SHA-256
  `83173db3b42d8ef966b6bde02f064beb42ee71b4593bfd727a3fefefdb862f04`.
- All **71 entries in the current runtime checksum inventory** validate. This
  validates its current content, not preservation of the original inventory.

Failures, recorded without rewriting/restoring anything:

- Seven pre-existing milestone branch refs changed attribution commits; the new
  U1 branch/HEAD also moved. Every changed milestone branch retains its original
  tree. A Codex internal checkpoint ref also disappeared; exact before/after refs
  are in `preservation.json`.
- `target/m4b-runtime/completion-status.json` changed from SHA-256
  `b1daa68ac265ad596a29005b667af024d5a9f3375d5bdb4dbe5c1c051dd37983` to
  `a42d67e260d02058098049cb1f45458468859396d00b841df35d5f7019906724`.
- `target/m4b-runtime/SHA256SUMS` changed from SHA-256
  `819eb5a4c9a62b380a54267966c29f749e72a24ce0e79aa2229ad03f51d8651d` to
  `7e0addb6266205f17d0312600029582f13f4cf060b0420b8922abbd748d75f8d`.
- The assessment's 80-file protected M4B inventory therefore has exactly these
  two mismatches. Full preservation cannot be certified for the shared workspace.

No U1 staging, commit, push, history rewrite, recovery rewrite, installation,
application build, package generation, VM change, live report, service change,
publication or deployment was performed. Creating the requested local branch was
the sole intentional U1 ref mutation. The concurrent rewrite remains outside
this patch and requires separate user review.

## Limitations and remaining U1 work

No requested U1 source implementation remains. Review the patch and resolve the
external preservation-gate failure before accepting this phase. Further cache
migrations and `library_loader.py` atomic/import changes remain deliberately
unadopted; any later loader change needs tests of both entry styles.

VTE/GTK behavior here is mocked. Native AArch64 rebuild/import/GUI/real-VTE and
subsequent DEB/VM qualification remain a separately authorized phase. No native
AMD64, minimum-language-runtime, distribution or fresh artifact claim is made.
No upstream 200-line report cap, clipboard removal, global privilege gate,
automatic registry removal, MCP lifecycle change, Rust consolidation, npm repair,
script conversion, default-setting change or version bump was ported.

Atomic replacement is not transaction locking or directory-fsync power-loss
protection. Best-effort cleanup can fail, and process crashes can leave temporary
files. History retains its pre-existing potential for lost concurrent updates.
Client secret redaction and server-side sanitization were not certified or
contacted. Existing automatic-report consent behavior is retained; tests do not
enable it in a real application. Old M2/M4A/M4B runtime and recovery evidence
continues to describe only its original qualified sources/artifacts.

## Authorized evidence recovery and VTE correction addendum — 2026-11-12

This addendum records a later user-authorized operation. All preceding text is
retained verbatim as the original U1 review record. The forensic report and old
U1 patch, source manifest, logs, inventories and attribution material are
unchanged. Current `codex/u1-atomic-reporting` HEAD remains
`0f516736477449f05040cd92bf3f47773cf87041`; no Git refs were changed.

Before either recovery write, the complete current worktree and `.git` were
archived and every regular archive member verified against a separately captured
pre-recovery manifest. Read-only `worktree-before.tar` (81,080,320 bytes) and
`git-before.tar` (66,529,280 bytes) preserve 3,039 and 308 regular members,
respectively, plus links/directories. The raw index, refs, reflogs, all 20,335
available Git objects (including unreachable objects), old U1 patch and recovery
bundle are preserved under `target/u1-implementation/recovery-2026-11-12/`.
The pre-recovery manifest covers 3,356 files/links. Archives, original-state
records, candidates and separate incident exhibits have read-only mode 0400.
This is filesystem read-only protection, not a hardware-immutable archive.

The edited completion file and inventory were copied to separate incident
exhibits before recovery. Their retained hashes are, respectively,
`a42d67e260d02058098049cb1f45458468859396d00b841df35d5f7019906724` and
`7e0addb6266205f17d0312600029582f13f4cf060b0420b8922abbd748d75f8d`.
Provenance and source timestamps are in `incident-exhibits.json`.

Both historical files were recovered from the forensic report's Appendix A,
using UTF-8/LF bytes including the final newline. Each candidate was independently
read back and checked against the user's exact length/hash requirements, the
assessment's protected inventory and the pre-U1 snapshot before either historical
file was replaced. The checksum inventory was **not regenerated**.

| Recovered file under `target/m4b-runtime/` | Exact bytes | SHA-256 |
| --- | ---: | --- |
| `completion-status.json` | 833 | `b1daa68ac265ad596a29005b667af024d5a9f3375d5bdb4dbe5c1c051dd37983` |
| `SHA256SUMS` | 6360 | `819eb5a4c9a62b380a54267966c29f749e72a24ce0e79aa2229ad03f51d8651d` |

Attribution mapping and recovery provenance remain in separate sidecars. The
historical completion record again names its original `8d8ced68` source;
historical qualification claims were not reinterpreted or changed. These are
verified reconstructions, not newly discovered pristine original copies.

The only additional application change is
`BugReporting._get_vte_buffer_text()` in `p3/app/term_reporting.py`. It retains
valid absolute-range output and supported string/first-string-tuple formats.
Missing/non-callable, failed, malformed or whitespace-only range exports now
attempt `get_text_format()`. Fallback failures/unusable output safely return an
empty string. No malformed value is stringified or another tuple field salvaged.
Binding-error handlers surround only the API attempts; result normalization
errors and BaseException interruptions propagate. Clipboard/captured-log and
report-consent behavior are unchanged.

Seven added tests in `dev/tests/test_u1_reporting.py` cover these paths, including
preserved range preference, one-item tuples, no misleading partial text, fallback
failure, interrupts and unrelated result-processing exceptions. The new tests
reproduced the defect before the fix. Final verification:

- **110 selected U1/existing tests passed**, including 32 U1 fixtures and the same
  78 existing regressions as the original run; zero failures/skips.
- **Six independent recovery acceptance tests passed**; **nine focused VTE tests
  passed** (included in the 110-test run). No live report/network use occurred.
- All **80/80 assessment-protected files**, **2021/2021 original evidence entries**
  and **71/71 original runtime checksum entries** match; both exact recovered
  lengths/hashes and incident exhibits were rechecked.
- All **121 Python source files** compiled in memory, and the eight changed/new
  U1 source/test files passed Python 3.12 syntax parsing. Whole-module mocked
  imports, AST change-boundary checks and `git diff --check` passed.
- Original M4A DEB remains SHA-256
  `83173db3b42d8ef966b6bde02f064beb42ee71b4593bfd727a3fefefdb862f04`.
- Current refs, raw index, all pre-existing Git metadata/object bytes, recovery
  bundle and forensic report remain unchanged. Only the two authorized evidence
  files, VTE method, added VTE tests and this appended report changed among
  pre-recovery files. The worktree changes remain unstaged and uncommitted.
- The original U1 ten-file manifest matches the archived pre-correction files.
  It intentionally differs from the current tree only for the VTE source, its
  tests and this addendum. The old patch is byte-preserved and reverse-checks
  against the saved original U1 files; it is not presented as the corrected patch.

Detailed comparisons are in `recovery-2026-11-12/verification.json`. The new
`source-files-after-recovery.json`, `u1-after-recovery.patch` and
`recovery-change.patch` identify the corrected review state without overwriting
old artifacts. See the separate concise `recovery-2026-11-12/INCIDENT.md` and
`recovery-provenance.json`. Recovery tests and all new logs are in that directory.

Evidence-byte preservation is repaired. **Original Git-history preservation is
not repaired or claimed**: the user explicitly chose to keep rewritten attribution
history and not recreate missing refs. All available objects are preserved in the
Git archive, including the missing-ref tree and amended-away commit. The original
full history/evidence gate therefore cannot be marked passed. Native VTE/GTK,
minimum-runtime and fresh AArch64 artifact/DEB/VM qualification remain unperformed
and require a separate authorized phase. No package/build/VM/service/network/
workflow/live-report/publication action, staging, commit or ref update occurred.
