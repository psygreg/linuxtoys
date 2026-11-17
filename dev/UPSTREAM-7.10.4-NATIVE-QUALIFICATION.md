# LinuxToys 7.10.4 native ARM64 qualification — gates passed, locally reviewed

Updated: 2026-11-17 (Europe/Rome). Production baseline:
`7686ad45461e99927e4a548fbdddfec4cc5cb57f`, branch `arm64-support`.

**All requested remaining gates passed: 278 regression tests passed, zero
failures, zero errors, zero skips; all 46 focused tests passed.** The previously
skipped packaging test also passed separately. Production bytes still match the
requested commit. The two reviewed test-fixture corrections are included in this
qualification change and reported separately below. No push, history rewrite or
deployment occurred.

New native workspace: `/home/ta/linuxtoys-7104-gates-32el_gup`.
Local evidence: `target/upstream-7.10.4-native-gates-29plfbls/`.
Existing evidence and all preceding failures remain intact. Historical symlink
preservation and `.repowise` timestamp causation remain frozen, unresolved
historical exceptions; neither investigation was restarted or treated as an
application failure.

## Fixture review and source identity

Only `dev/tests/test_native_build.py` and
`dev/tests/test_7104_integration.py` differ from the production baseline:

- The installer fixture stages the real shared package-guard library in its new
  disposable checkout so the existing trusted-checkout guard can reach the
  foreign-asset test. Its refusal/no-privilege assertions remain unchanged.
- The concurrent mock manager uses real `os.mkdir`/`os.rmdir` calls rather than
  the previously observed uutils mkdir exit-code race. Serialization, return-code,
  lock-removal and temporary-log assertions remain unchanged.

An AST comparison confirmed every assertion is unchanged; decorators and
production guards were not weakened. The existing patch SHA-256 is
`11044f67d0d2dacd7d80a73302dc574127d4f303f971112523c2c6550a370532`.

The fresh candidate was materialized from the retained exact-commit archive and
the same two reviewed fixture corrections, then baselined before testing. A final
independent `git ls-tree` / `git cat-file --batch` comparison verified all **998**
committed file/link entries against native results: 996 match verbatim; the only
two differing entries are those reviewed test files. Executable mode bits and
committed link targets match. All production source matches the requested commit.
No protected historical link target was accessed.

## Authenticated private tool acquisition

No apt indexes were updated. Copies of the existing official Ubuntu `resolute`
InRelease metadata were verified with `/usr/bin/gpgv` and the installed Ubuntu
archive trust anchor `/usr/share/keyrings/ubuntu-archive-keyring.gpg`. The valid
signer fingerprint was:

```text
F6ECB3762474EDA9D21B7022871920D1991BC93C
```

The full cached `main/binary-arm64/Packages` and
`universe/binary-arm64/Packages` files matched the signed Release SHA-256 and
size records. Packages were downloaded over verified HTTPS from the configured
official `https://archive.ubuntu.com/ubuntu/` repository. Every download matched
the authenticated index's exact size and SHA-256, then its Package/Version/
Architecture fields were cross-checked before private extraction.

| Official package | Architecture | Package version | Verified package SHA-256 |
| --- | --- | --- | --- |
| `shellcheck` | arm64 | `0.11.0-2` | `43a72e6d660310412907c5eb01b04a0c036650b6981e10c7554218c707de98cb` |
| `dpkg-dev` | all | `1.23.7ubuntu1` | `507b526fd78f9dff89696bbc3085af3117059f37fd281542778ac8b97be44690` |
| `libdpkg-perl` | all | `1.23.7ubuntu1` | `984ca70b4b4af43812abeb6aa890ed0e8b7a725c9ac193b00d4df470fca1c1fe` |

`dpkg-deb --extract` placed payloads only in the new private `tools/` directory.
No package was installed; no maintainer script, lifecycle operation or dependency
installation ran. Existing compatible native runtime libraries and Perl were
used. ShellCheck reports **0.11.0** and its ELF machine is **183 (AArch64)**.
The real privately extracted `dpkg-architecture` reports **1.23.7** and detects
**arm64**. Its matching Dpkg Perl modules are selected with process-local
`PERL5LIB=$GATE_ROOT/tools/usr/share/perl5`.

Signed metadata, complete authenticated index copies, verified `.deb` files,
signature status, exact URLs, hashes, extraction commands and runtime output are
retained. Tool executable hashes, downloaded package hashes, the trust anchor
and the original apt index contents were rechecked unchanged after testing.
This is authenticated tool extraction, not system package installation.

## Native commands and results

The VM remains native Ubuntu 26.04.1 AArch64 `igris`, UID/GID 1000:1000, kernel
`7.0.0-43-generic`, Python **3.14.4**, Bash **5.3.9**, inherited umask `0002`.
The previous run's tested environment and two fixture corrections were retained;
no unrelated lint cleanup, permission repair or repeated historical audit ran.

Tests used a fresh read-only-host/source/tools Bubblewrap namespace, isolated
home/tmp/run/proc and private network/PID/user/IPC/UTS namespaces, with process
capabilities dropped. Package transactions, privilege/service commands and
downloaders remained blocked. The packaging script legitimately needs
`dpkg --validate-version VERSION` and `dpkg --print-architecture`; a strict
dispatcher permits only those exact argument forms and executes a hash-matching
private copy of the existing real dpkg binary. Responses are not mocked.
Transaction arguments remain refused. Real `dpkg-query` temporary-database and
tiny `dpkg-deb` archive fixtures remain allowed as before.

With `GATE_ROOT=/home/ta/linuxtoys-7104-gates-32el_gup`, the tool, test and
validation subprocesses included:

```sh
/usr/bin/python3 -I -B "$GATE_ROOT/harness/acquire_tools.py"
/usr/bin/dpkg-deb --extract VERIFIED_PACKAGE.deb "$GATE_ROOT/tools"
"$GATE_ROOT/tools/usr/bin/shellcheck" --version
"$GATE_ROOT/tools/usr/bin/dpkg-architecture" --version
"$GATE_ROOT/tools/usr/bin/dpkg-architecture" -qDEB_HOST_ARCH

"$GATE_ROOT/tools/usr/bin/shellcheck" --severity=error --shell=bash APPLICABLE_61_FILES
/usr/bin/python3 -B "$GATE_ROOT/harness/run_tests.py" targeted
/usr/bin/python3 -B "$GATE_ROOT/harness/run_tests.py" focused
/usr/bin/python3 -B "$GATE_ROOT/harness/run_tests.py" regression
/usr/bin/python3 -B "$GATE_ROOT/harness/source_checks.py"
/usr/bin/python3 -B "$GATE_ROOT/harness/bash_checks.py"
/usr/bin/python3 -B "$GATE_ROOT/source/p3/app/architecture_cli.py" tree --content-kind source "$GATE_ROOT/source/p3"
/usr/bin/python3 -B "$GATE_ROOT/source/dev/prepare_script_rollout.py" --check --artifact-dir "$GATE_ROOT/scratch/bundle-artifact"
```

`VERIFIED_PACKAGE.deb` and `APPLICABLE_61_FILES` are display abbreviations:
the exact expanded paths, complete sandbox/strace argv, exit codes, stdout/stderr
and timings are retained in `native-evidence/evidence/*-command.json`,
`private-extractions.json` and the tool runtime records. The isolated controller
called `qualification.run()` for each action. Its unittest loader uses the actual
repository suites; the final gate additionally requires the exact test count and
zero skips, rather than accepting unittest's skip-tolerant success status.

| Gate | Result |
| --- | --- |
| ShellCheck 0.11.0, error severity | **61 applicable changed shell files pass**, exit 0; no lint cleanup or warning suppression added |
| Formerly skipped `test_invalid_output_refused_before_build_or_mutation` | **1 passed, 0 failures/errors/skips**, using real private `dpkg-architecture` |
| Focused `test_7104_integration.py` | **46 passed, 0 failures/errors/skips** |
| Full `test*.py` regression discovery, 14 modules | **278 passed, 0 failures/errors/skips** |
| Python compatibility/static compilation | **132** files pass Python 3.10 grammar parsing and native Python 3.14 in-memory compilation |
| Native Bash syntax | **256** regular shell files pass Bash `-n` |
| Architecture policy | **176** curated route digests/declarations pass; native host and source-tree CLI validation pass |
| Exact script bundle | Client approval and preparation `--check --artifact-dir` pass |
| Prior formatting/fatal Python lint | Existing results retained unchanged; reviewed fixture hashes still match; no unnecessary rerun |

The targeted and focused tests are subsets of the full regression suite, not
additional distinct-test counts. Approved exact-bundle revision remains
`7334b1c53310ff097b6d731727958dee73d2ca5aaec15f56cde85985887fa5c5`.
The printed rollout tag is only an artifact label; no project Git tag was created.

## Final verification, limitations and local review

The candidate source retained its complete before/after content and stable
metadata baseline, with no observed source atime changes. Bounded relevant
dpkg/APT files, configuration, package logs, running-service list, host mount
listing and capability observations matched the test-phase baseline.
No system installation, apt index update, configuration/service change,
permission repair, ownership/capability change or host mount-setting change
was performed. New private extraction files and normal disposable test fixtures
are the only tool/fixture filesystem outputs. This is not global preservation.

Closed execution traces show **six real private dpkg-architecture executions**
and **twelve real dpkg executions**, all restricted to the two read-only query
forms above. No unexpected system mutator/downloader executions, refusing-stub
hits or IP-family test connections were observed. Tools and source are immutable
inside the test namespace. Acquisition downloads were separate, explicitly
authorized HTTPS package transfers.

Python 3.10 was grammar-checked, not runtime-tested; the executed native Python
is 3.14.4. Package lifecycle behavior, live GUI/application startup and AMD64
execution are not claimed by the fixture suites. The existing historical
exceptions remain unresolved and frozen. Prior broader Black findings and the
observed uutils behavior were not changed or expanded into unrelated cleanup.

**Verdict: all requested native ARM64 qualification gates passed for the exact
production baseline with the two reviewed test-only corrections. Final local
review passed.** This qualification change contains only the two test fixtures
and this report. Production source remains unchanged, and the original production
integration commit remains in history. No tag, push, PR or deployment is included.


---

<details>
<summary>Prior qualification reports and historical evidence — retained verbatim; superseded by the completed gates above</summary>

# LinuxToys 7.10.4 native ARM64 qualification — incomplete

Updated: 2026-11-17 (Europe/Rome). Backup completion was confirmed by the user
before this fresh run. Target HEAD remains
`7686ad45461e99927e4a548fbdddfec4cc5cb57f` on `arm64-support`.

**Final candidate: 277 passed, 0 failed, 1 explicit skip out of 278 regression
tests. All 46 focused tests passed. Qualification is incomplete because
ShellCheck and one packaging-test prerequisite are absent.**
The passing candidate contains two uncommitted test-fixture corrections; it is
not byte-identical to the target commit. No production defect was established.
No dependencies were installed, and no commit, push, publication or deployment
was performed.

## Scope and frozen historical exceptions

This run used a new private native workspace:
`/home/ta/linuxtoys-7104-fresh-t4t65xef`.
Local evidence is retained in
`target/upstream-7.10.4-native-fresh-30251960/`.

Historical symlink target-capture preservation and `.repowise` timestamp
causation remain **unresolved historical exceptions, not application failures**.
Historical preservation-helper development and investigations were not resumed.
No old qualification workspace or evidence directory was reused. The problematic
historical link targets were not accessed, and `.repowise` timestamps were not
investigated. The report preceding this run is retained byte-for-byte as
`qualification-report-before-resume.md`; its historical text follows below.

## Exact source, environment and execution boundary

The local repository was initially at the requested HEAD and branch with no
tracked modifications. Its existing untracked entries were `.repowise/` and this
report. There was no native `/home/ta/linuxtoys/.git` checkout. A new `git archive`
of the target commit was independently compared against Git blob hashes, then
transferred and reverified natively, including all executable bits and all three
committed link targets: **998 entries**. Archive SHA-256:

```text
5c92fd73587d79d3122a8845833a14b5ae8f0f060e039cdc5879c5f4f10b3192
```

Source, workspace and relevant system baselines were recorded before test
tooling. Files were created with safe 0644/0755 modes inside the new 0700
workspace; no existing input permissions were repaired. The exact source stayed
in `source/`. Separate `source-fixed/` and `source-fixed-v2/` trees were created
and baselined for each evidenced correction. The original source and every
failed variant/result remain retained.

| Environment | Observation |
| --- | --- |
| Host / OS | `igris`, Ubuntu 26.04.1 LTS |
| ISA / kernel | Native `aarch64`; `7.0.0-43-generic`; no emulation |
| Python | `3.14.4`, GCC 15.2.0 |
| Bash / Rust | Bash `5.3.9`; rustc `1.93.1` |
| Lock utilities | Existing uutils coreutils `0.10.0` |
| Identity / umask | UID/GID 1000:1000; inherited `0002` |
| Resources at baseline | 2 CPUs; 5,513,572 kB total RAM; 1,142,088 kB available RAM; 14,920,773,632 bytes available disk |
| Existing optional Python modules | PyYAML and GI present; Black, Flake8 and Ruff absent |
| Missing commands | ShellCheck, `dpkg-architecture`, Python 3.10–3.13 |

Tests ran as UID 1000 inside existing Bubblewrap, with a read-only host and
source, isolated home/tmp/run/proc, private user/PID/network/IPC/UTS namespaces,
and dropped process capabilities. Historical home paths and credentials were
absent from that namespace. Only new scratch/profile paths were writable on the
host. Package managers, privilege tools, service commands and downloaders were
shadowed by refusing stubs, including absolute system paths; test-owned fakes
remained available. Existing read-only `dpkg-query` temporary-database tests and
tiny `dpkg-deb` archive fixtures were allowed. The Rust ABI test built only its
tiny dependency-free fixture. No real package transaction or application build
ran. Namespace mounts did not change host mount settings.

## Results, failures and supported fixes

Discovery found **278 tests in 14 modules**. Every discovered test was executed
or explicitly recorded as skipped. Focused/affected runs are subsets and must
not be added to the distinct regression count.

| Source / run | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Exact target, focused 7.10.4 | 46 | 0 | 0 | 0 |
| Exact target, full regression | 276 | 1 | 0 | 1 |
| First fixture correction, affected native-build module | 5 | 0 | 0 | 0 |
| First fixture correction, full regression | 276 | 1 | 0 | 1 |
| Both corrections, affected native-build module | 5 | 0 | 0 | 0 |
| Both corrections, focused 7.10.4 | 46 | 0 | 0 | 0 |
| Both corrections, full regression | **277** | **0** | **0** | **1** |

1. `test_native_build.UpdateArchitectureTests.test_update_release_selection_refuses_foreign_asset_before_privilege`
   failed on the unchanged target. Its disposable checkout lacked
   `p3/libs/packages.bash`, now required by the production trusted-checkout
   guard. It therefore reached `Cannot resolve immutable release source`
   instead of the intended foreign-asset selector. The fixture now stages that
   library alongside the architecture helpers with private fixture permissions.
   Its original refusal diagnostic and no-privilege assertions remain intact.
2. `test_7104_integration.TransactionTests.test_concurrent_mock_transactions_are_serialized_by_native_mock_lock`
   exposed an intermittent fixture-tool assumption on the first full rerun.
   A bounded diagnostic retained the failure again, with `enter, enter, leave,
   leave`. In `race-narrow15.strace`, PID 178379 receives kernel `EEXIST` from
   `mkdirat` and then calls `exit_group(0)`; its competing mkdir succeeds. Both
   utilities identify as uutils 0.10.0. The test now creates/removes its native
   mock lock using Python `os.mkdir`/`os.rmdir`, so the actual syscall's refusal
   controls the loser. Serialization, return-code, lock-removal and temporary-log
   assertions remain unchanged. No system utility or production lock code was
   changed. Five broader traced probes passed; fourteen narrower probes passed
   before the retained fifteenth failure. Those diagnostic passes did not clear
   the failure gate; the supported correction and affected/full reruns did.

The sole final skip is
`test_deb_packaging.DebPackagingTests.test_invalid_output_refused_before_build_or_mutation`.
Its exact decorator reason is `native Linux dpkg required`; specifically, this
VM lacks `dpkg-architecture`. Existing `dpkg-deb` and `dpkg-query` tests ran.
Nothing was installed to bypass the skip.

Three harness failures are separately retained: an explicit unittest package
root rejected this repository's non-package discovery directory before tests;
exclusive evidence creation refused an already-used output pathname; and an
initial whitespace comparison could not see the other new source tree inside
the sandbox. New runner versions, unique evidence names and a narrowly exposed
new-source comparison corrected these without rewriting the failed evidence or
altering production behavior.

## Compatibility, Bash, policy, bundle and missing checks

| Check | Result |
| --- | --- |
| Python compatibility/static compilation | All **132** Python files pass Python 3.10 grammar parsing and in-memory compilation on native Python 3.14.4; repeated after each relevant fixture correction |
| Python 3.10 runtime | Not installed; grammar checks do not qualify that runtime |
| Native Bash syntax | **256** regular `.sh`, `.bash`, `.lib` files pass Bash 5.3.9 `-n`; no scripts were installed or run as application workloads |
| Architecture policy | Native host is `aarch64`; **176** curated route digests/declarations verified; source-tree CLI validation passes |
| Exact script bundle | Client-approved bundle and preparation `--check --artifact-dir` pass; revision `7334b1c53310ff097b6d731727958dee73d2ca5aaec15f56cde85985887fa5c5` |
| Patch whitespace | Local `git diff --check` and corrected native read-only no-index comparison pass |
| Black formatting | Existing macOS Black **25.11.0** passes both edited test files; seven broader findings exactly match unchanged target files; no new formatting findings; not native execution |
| Fatal Python lint | Existing macOS Flake8 **7.0.0** / Pyflakes 3.2.0 passes `E9,F63,F7,F82` across all **12** reviewed Python files; not native execution |
| ShellCheck error-severity lint | **Not run: ShellCheck absent**; requested argv retained |

ShellCheck's absence prevents a passing overall verdict. Black/Flake8 remain
absent on `igris`; the checks above used existing Anaconda Python 3.12.12 tools
on macOS, against fresh exact-source copies. Both edited file hashes were
checked against the native-tested candidate. Unchanged target copies were
checked separately with the same Black version; all seven broader findings
are on byte-identical files and were left unchanged. No compilation result is
substituted for lint, and missing checks are not counted as unittest skips.
No dependency installation was attempted.

The first multi-file Black invocation was denied a local multiprocessing socket
by the desktop sandbox before completing. Its logs are retained. Independent
single-file `--check --diff` invocations avoided that IPC and completed without
modifying source. `host-static-summary.json` records versions, scope, baseline
findings and native-candidate hash matching. Local `RESULTS.json` supplements
the frozen native-only `native-evidence/evidence/RESULTS.json`.

The standalone `native_*` evidence programs are outside unittest discovery.
Real DEB/M5 lifecycle programs were not run under the no-transactions rule;
font-download and built catalog/GUI smoke programs were not qualified here.
Standalone preparation/rollout smoke reports are not claimed: their repository
regression fixtures and the local exact-bundle CLI checks above were run.
Live GTK/application startup, native distro lifecycle behavior, external network
services, other Python runtimes and AMD64 execution remain outside this result.

## Commands and retained receipts

Exact full Bubblewrap/strace argv arrays, status, elapsed time, stdout/stderr and
individual test IDs/outcomes are retained in the fresh evidence. Outer commands
were dispatched over the existing SSH connection as `ta`; no privileged shell
or sudo invocation was used. With
`QUAL_ROOT=/home/ta/linuxtoys-7104-fresh-t4t65xef`, the executed controllers were:

```sh
/usr/bin/python3 -I -B "$QUAL_ROOT/harness/qualification.py" setup
/usr/bin/python3 -I -B "$QUAL_ROOT/harness/qualification.py" discover
/usr/bin/python3 -I -B "$QUAL_ROOT/harness/qualification_v2.py" discover
/usr/bin/python3 -I -B "$QUAL_ROOT/harness/qualification_v3.py" discover
/usr/bin/python3 -I -B "$QUAL_ROOT/harness/qualification_v3.py" focused
/usr/bin/python3 -I -B "$QUAL_ROOT/harness/qualification_v3.py" regression
```

The same v3 `run()` function dispatched `python-checks`, `bash-checks`,
`bundle-check` and `architecture-check`. These inner commands included:

```sh
/usr/bin/python3 -B "$QUAL_ROOT/harness/source_checks.py"
/usr/bin/python3 -B "$QUAL_ROOT/harness/bash_checks.py"
/usr/bin/python3 -B "$QUAL_ROOT/source/dev/prepare_script_rollout.py" --check --artifact-dir "$QUAL_ROOT/scratch/bundle-artifact"
/usr/bin/python3 -B "$QUAL_ROOT/source/p3/app/architecture_cli.py" tree --content-kind source "$QUAL_ROOT/source/p3"
```

The first correction used `qualification_fixed.py affected` and `regression`.
The final correction used the following controllers, each running the unchanged
repository test loader with `test_native_build.py`, `test_7104_integration.py`
or `test*.py` as appropriate:

```sh
/usr/bin/python3 -I -B "$QUAL_ROOT/harness/qualification_fixed_v2.py" affected
/usr/bin/python3 -I -B "$QUAL_ROOT/harness/qualification_fixed_v2.py" focused
/usr/bin/python3 -I -B "$QUAL_ROOT/harness/qualification_fixed_v2.py" regression
/usr/bin/python3 -B "$QUAL_ROOT/harness/source_checks_fixed_v2.py"
```

Some controllers were called through an isolated Python stdin orchestrator using
their same `run()` function; the recorded argv arrays are authoritative for the
actual subprocesses. Diagnostic wrappers and all versions are retained.
Key collected receipts are under local `native-evidence/evidence/` and
`native-evidence/scratch/`: `RESULTS.json`, command JSON/exec traces,
`system-and-connection-analysis.json`, source baselines/after comparisons,
`results-fixed-v2-regression.json`, the single-test race traces and fixture,
requested unavailable check commands, and both patch provenance records.

Additional actual macOS commands used existing tools, with one fresh candidate
or target-baseline file supplied to each Black invocation:

```sh
/opt/anaconda3/bin/black --version
/opt/anaconda3/bin/black --check --diff PATH_TO_FRESH_PYTHON_COPY
/opt/anaconda3/bin/flake8 --select=E9,F63,F7,F82 PATHS_TO_12_FRESH_CANDIDATE_COPIES
git --no-optional-locks diff --check
```

The expanded argv/status/stdout/stderr are retained in
`black-single-file-results.json`, `fatal-lint-candidate-command.json`, and the
host static-check logs. No native Black/Flake8 result is claimed.

## Final workspace, system observations and verdict

All three new source trees matched their respective content/stable-metadata
baselines after testing; zero source atime differences were observed. New
scratch, fixture, profile, runner and evidence output is intentional and retained.
The original exact-commit tree was never patched in place.

Relevant dpkg/APT state, package logs and repository-config content hashes
matched. Host mount listings, process capability observations and running-service
lists matched. **Five baseline reads updated atime** on `/var/lib/dpkg/status`,
`/var/lib/apt/extended_states`, `/var/log/dpkg.log`, `/var/log/apt/history.log`, and
`/etc/apt/sources.list.d/ubuntu.sources.curtin.orig`; before/after-read values
remain recorded and were not restored. Their post-read metadata matched the
final checkpoint. This is a bounded observation, **not global preservation**.

Thirteen primary execution traces record no system manager, privilege, service
or downloader exec attempts and no refusing-stub hits. The **2,884** observed
connection attempts address only the absent Unix name-cache socket
`/var/run/nscd/socket` and fail with ENOENT, including the two resumed calls;
there are no IP-family connects in those traces. Supplemental checks used the
same restricted namespace; no broader trace completeness claim is made.

Only the two test files and this report are intentional local edits. HEAD and
history remain unchanged. No system package/configuration, service, host mount,
ownership or capability change was performed. Permission operations in existing
tests apply only to new disposable fixtures. Fixture-local Git histories are
created by existing tests; the project repository received no commit or tag.

**Verdict: incomplete at missing-prerequisite gates.** The corrected candidate's
native fixture suites pass with the explicit packaging skip. Edited-test Black
formatting and fatal Python lint pass on macOS; ShellCheck remains unexecuted,
and native Black/Flake8 execution is not claimed. The user prohibited dependency
installation, so work stops at the remaining prerequisite. Historical exceptions do not gate this new
application result and are not reopened. No commit/push/publication/deployment
is authorized by these incomplete results.


---

<details>
<summary>Frozen historical report — earlier failures and limitations, superseded by the fresh run above</summary>

# LinuxToys 7.10.4 native ARM64 qualification — blocked

Updated: 2026-11-17 (Europe/Rome); initial attempts: 2026-11-16.
Requested commit: `7686ad45461e99927e4a548fbdddfec4cc5cb57f`.
Local branch: `arm64-support`; HEAD remains the requested commit.

Latest preservation-only review: **both blockers remain unresolved; stopped**.
Descriptor-relative target capture changed disposable symlink atime. The
`.repowise` directory timestamp changes still lack an evidenced cause. The
2026-11-17 preservation-blocker investigation at the end records the policy,
separate privilege results, new fixtures, and an unintended browse-startup
side effect. It does not supersede or erase earlier failures.

**Qualification is incomplete. No LinuxToys qualification tests were executed.** The run
stopped while establishing the historical protected-path preservation baseline,
before source extraction, fixture dispatch or application imports. No production
implementation defect has been established by this attempt.


## Current disposition — 2026-11-17

The original `O_NOATIME` ownership blocker was resolved for five explicit
historical slices using identity-pinned, read-only privileged helpers. Their
closed traces and manifests were independently verified: **363 entries, 352
files, 11 directories and 328,730,258 bytes hashed**. Authentication is no longer
the stopping point for those scans.

The batch then correctly rejected a historical symlink:

```text
/home/ta/linuxtoys-m5-nala-f3-ef5eb1a7/bwrap-rootfs-v3/lifecycle/bin
Rejected: symlink rejected: lifecycle/bin
```

The link was inspected with `AT_SYMLINK_NOFOLLOW`; it was not opened, followed,
read with `readlink`, removed or changed. The explicit requirement to reject
symlinks remains enforced. Nine subsequent batch slices were not run. **The
complete native preservation baseline does not exist, so qualification did not
resume and no native before/after preservation comparison is possible.**

A final local checkpoint additionally found changed mtime/ctime on the existing
`.repowise` directory. All **6,223 file-content hashes** matched; **6,978 of 6,979
stable metadata entries** matched. The directory timestamp change was not
restored, and its cause has not been established. Strict Git refs, HEAD and
working-tree status matched the initial checkpoint; desktop capture refs changed
(two old ref values removed, two new values added). These observations are
retained separately and are not a passing full-preservation result.

**23 native inventory-helper fixture tests passed; zero LinuxToys qualification
tests ran.** No package-manager lifecycle qualification is claimed. The report
remains uncommitted because both completion gates have not passed. Details and
retained preparation failures follow; earlier authentication status below is
historical.

## Native environment actually observed

| Item | Observed value |
| --- | --- |
| Host / OS | Existing `igris`, Ubuntu 26.04.1 LTS (Resolute Raccoon) |
| Architecture | Native `aarch64`; no emulation |
| Kernel | `7.0.0-43-generic`, `#43-Ubuntu SMP PREEMPT_DYNAMIC Fri Oct 23 13:33:03 UTC 2026` |
| Python | `3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]` |
| Bash | `5.3.9(1)-release (aarch64-unknown-linux-gnu)` |
| Effective UID / GID | 1000 / 1000 |
| Inherited umask | `0002`, unchanged |
| Effective capabilities at failure | `0000000000000000` |

Read-only environment commands and a namespace capability probe ran natively.
The probe successfully used existing Bubblewrap to enter private namespaces with
read-only host mounts and a writable private run directory, retaining UID 1000.
A Landlock ABI query returned 8. These are capability observations, not execution
of LinuxToys tests or proof that the planned test sandbox was exercised.

## Failures and stopping point

Two separate preparation attempts and their evidence were retained.

1. Initial run:
   `/home/ta/linuxtoys-7104-native-oc27jr75`, run ID
   `4fefbe65-086b-4b89-b5cf-8af9c5527862`.
   The inventory discovery helper incorrectly requested `O_NOATIME` while
   listing root-owned `/tmp`. Linux returned `PermissionError: [Errno 1]
   Operation not permitted`. No preservation baseline, source extraction or test
   execution followed in that run.
2. A fresh preparation run corrected discovery of non-owned system parent
   directories to ordinary read-only listing, with before/after atime
   observations. Strict `O_NOATIME` and no-follow reads of historical owned
   inputs were retained. No permissions or privileges were changed.
   Fresh root: `/home/ta/linuxtoys-7104-native-9r_jv7o3`, run ID
   `40321492-05f5-4dc6-b9cf-78d46ba903c3`.
   The full protected-path inventory then failed opening:

   ```text
   /home/ta/linuxtoys-m5-nala-f3-ef5eb1a7/bwrap-inputs-v3
   PermissionError: [Errno 1] Operation not permitted
   ```

The second path is an existing historical artifact directory, owned by UID 0
with mode `0755`. UID 1000 can traverse/read it, but cannot perform the required
strict no-atime open with its current capabilities. The exact failing call was
`os.open(path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_NOATIME | O_DIRECTORY)`.
This is an inventory/ownership blocker, not a package-guard or application test
failure.

The second run stopped at that failure. No historical directory was chmodded,
chowned, skipped, rewritten or reopened with weaker historical-input flags.
There was no retry of the failed inventory or test dispatch. Subsequent native
work was limited to read-only diagnostics, verification of the transferred source
archive, environment recording and collection into the fresh evidence directory.

## Requested checks and execution status

| Check | Result in this qualification attempt |
| --- | --- |
| Exact committed source transfer | Verified natively inside the archive: all 998 committed file/link entries match the Git-derived manifest, including executable modes and symlink targets. |
| Archive SHA-256 | `5c92fd73587d79d3122a8845833a14b5ae8f0f060e039cdc5879c5f4f10b3192` |
| Materialized source / test execution | Source directory remains empty; no source was extracted or imported for testing. |
| Complete applicable native suite | Not run; discovery was not reached. |
| All 7.10.4 focused tests | Not run. |
| Native Bash statuses, signals, cleanup, traps and concurrency fixtures | Not run. Bash version observation is not behavior qualification. |
| Package guards, installer dispatch, updater, RAM and translations | Not run. No mock outcomes or native manager lifecycle results are claimed. |
| Architecture policy and exact script-bundle validator | Not run. Archive byte integrity does not replace policy/bundle validation. |
| Python compatibility, shell syntax, formatting and static analysis | Not rerun for this qualification; these remain pending. |
| Platform-specific skips | Undetermined: no tests were discovered or executed. Do not count the unexecuted suite as skipped or reuse the host suite's skip count. |
| Newly exposed source/test failures | None established; the two observed failures are preparation/inventory failures. |

No native APT, DNF, Pacman or Zypper transaction ran. No package installation,
removal, upgrade, configuration, application build, service operation, repository
change, package database mutation or application startup was performed. No native
fixture workload was launched; the planned network preload, subprocess guard,
Landlock restriction and outer strace were not activated for tests.

## Preservation and evidence

Local preservation verification completed before adding this report:
**6,050 file-content hashes and 6,791 stable metadata entries matched**, with no
content/stable-metadata changes, no strict Git ref/HEAD/status changes and no
Desktop capture-ref changes. Nine local atime observations were recorded and
not restored. Original `.repowise/`, historical local qualification evidence,
existing artifacts and production source remain unchanged. This report is the
only newly added working-tree document after that checkpoint.

The second native run recorded 49 protected roots but **did not complete its
before inventory**, so there is no complete native protected-path before/after
comparison. Full guest preservation verification is therefore not claimed.
The directory-discovery record also retains the `/tmp` parent directory's
read-induced atime change; it was not concealed or restored. Historical owned
inputs were read with strict no-atime/no-follow flags until the ownership denial.
Read-only diagnostics verified that the transferred source archive is intact and
that the new source directory is still empty.

Evidence directories retained locally:

- `target/upstream-7.10.4-native-7686ad45-6f6996bx/`: initial preparation failure,
  exact source archive/manifest, controller inputs and SSH command diagnostics.
- `target/upstream-7.10.4-native-7686ad45-v2-nl5snkcz/`: corrected preparation,
  complete failure trace, blocked-directory metadata, native environment,
  directory-discovery observations, protected-root list, archive-integrity proof,
  collected native evidence and local before/after preservation records.

Both native private workspaces remain available. Earlier qualification evidence,
including the completed MCP qualification for exact production baseline
`d378deaddd5ef16a2d9d7e2accaf01e95780096e`, was not rewritten and does not qualify
this integration.

## Original stopping point and commit status

A preservation-safe inventory mechanism for the root-owned historical artifact
is required before native qualification can proceed. Resolve that ownership/
no-atime boundary without weakening historical preservation, then use a fresh
run to execute the requested checks against the unchanged exact commit.

**This report is uncommitted.** The requested condition for committing—successful
checks and preservation verification—has not been met. No commit, history rewrite,
push, publication or deployment occurred.

## Historical preservation-helper development checkpoint

At this earlier checkpoint the preservation mechanism was implemented and
fixture-tested, but privileged inventory was blocked by sudo authentication.
The subsequent authenticated scans and current stopping point are recorded
above and in the final follow-up below.

### Inspected boundary and fixed authority

Descriptor-only inspection confirmed the existing target directory is UID/GID
`0:0`, mode `0755`, device `66306`, inode `2135880`, on the existing ext4 filesystem
on `/dev/nvme0n1p2` with `relatime`. Its enclosing historical workspace is UID/GID
`1000:1000`, mode `0700`, inode `2133004`. `/home` and `/home/ta` identities were
also inspected without following symlinks. The blocked directory's recorded
metadata, including atime/mtime/ctime, matches the retained earlier diagnostics.
Its contents were not read as an unprivileged fallback.

The exact requested commit remains unchanged:
`7686ad45461e99927e4a548fbdddfec4cc5cb57f`.

New active evidence workspace:
`/home/ta/linuxtoys-7104-inventory-nc_43a8j`, UID 1000, mode `0700`.
Local development/evidence directory:
`target/upstream-7.10.4-inventory-helper-p0dsfl_f/`.
The prior uncommitted report was copied there before this update; all older
qualification workspaces and evidence were retained.

### Implemented helper privilege boundary

Reviewed helper: `inventory_helper.py` in that local directory. SHA-256:

```text
2517e7ace8e103542a0ed45403f119d8c025276f219423de0f40e61ccdb78ff3
```

Its privileged entry point accepts no path arguments or environment policy
substitutions. The single inventory-data allowlist entry is:

```text
/home/ta/linuxtoys-m5-nala-f3-ef5eb1a7/bwrap-inputs-v3
```

The helper pins the target and ancestor device/inode/UID/GID/mode identities.
Ancestors are traversed with descriptor-relative `O_PATH`/`O_NOFOLLOW` metadata
access. Every enumerated directory and hashed regular file is opened relative
to a verified descriptor with `O_NOATIME` and `O_NOFOLLOW`; there is no ordinary
read fallback. Each entry must retain UID/GID `0:0`, remain on the expected
filesystem and have no group/other write bits. Symlinks, hard-linked files,
other file types, changed identities, incomplete reads and incomplete traversal
are rejected. Directory names are enumerated again and descriptor/path metadata
is compared before/after access, including atime.

Explicit limits are 20,000 entries, 2 GiB total file bytes and depth 32. Hitting
any limit fails the inventory rather than silently truncating it. Successful
output contains per-entry SHA-256 hashes, ownership, full stable metadata,
separate access-time values, directory membership, byte/entry counts and a
canonical manifest digest.

The root program has no filesystem-writing operations or subprocess/network
imports. It accepts an evidence pipe, drops its own supplementary groups and
process UID/GID to 1000 before emitting the JSON result, and never opens an
evidence pathname. An unprivileged controller snapshots and SHA-pins the helper
bytes, sends that immutable snapshot to `/usr/bin/python3 -I -S -B -` under a
fixed sudo/strace invocation, and creates evidence files as UID 1000 with mode
`0600` in the separate private run directory. No privileged shell is invoked.
`-I -S -B` excludes user/site startup hooks and bytecode writes. Trusted system
interpreter/library startup reads are distinct from the fixed historical-data
inventory phase. This is a reviewed software allowlist, not a sudoers change or
an OS capability grant.

The trace uses raw `read`/`pread64` buffers, avoiding copies of protected file
contents in evidence. The independent verifier checks manifest membership,
ownership/types/flags/counts, actual directory entries, file-read byte counts,
ancestor-only metadata access, absence of mutations, and—when run in privileged
mode—the UID drop before output. Actual privileged output/access verification
remains pending because the privileged command has not executed.

### Verification completed and failures retained

- **23 native unprivileged helper fixture tests passed**, without invoking the
  LinuxToys qualification suites. Coverage includes exact hashes and unchanged
  metadata/atime; symlink roots/files/directories; wrong owners/inodes; unsafe
  modes; FIFO/socket/hard-link rejection; traversal/byte/entry/depth limits;
  replacement and enumeration races; strict no-atime permission failures with
  no retry using ordinary reads; malformed output rejection; and refusal of the
  production entry point under UID 1000.
- A closed native fixture trace independently verified **four protected fixture
  opens, five ancestor metadata opens, two regular files and 32 bytes read**.
  Complete directory membership matched. No outside data reads or input
  mutations were observed. This scan ran under UID 1000; it does not prove
  privileged execution or privilege dropping.
- Five malformed access/output proofs were rejected by the independent
  verifier. The final verifier explicitly distinguishes unprivileged fixture
  acceptance from privileged output/drop verification.
- The first fixture run executed 18 of 23 tests: 17 passed and one failed because
  a socket created under inherited umask `0002` was rejected by the mode guard
  before the fixture's expected file-type diagnostic. Its logs and fixtures
  remain intact. A fresh fixture version created only its disposable socket
  privately at creation; the helper and its permission checks were unchanged.
  That fresh run passed all 23 tests. Five original-run tests were not reached.
- An initial unprivileged caller attempt failed before sudo because
  `ast.literal_eval` did not accept the helper's constant multiplication in the
  2 GiB bound. The caller now uses a bounded literal/multiplication decoder.
  The failed caller version and trace are retained; helper bytes did not change.
- A supplemental status-query wrapper produced a `NameError`; it accessed no
  protected input. A direct read-only status check subsequently confirmed that
  no completed privileged inventory file exists. That diagnostic failure is
  retained.
- The first trace verifier's fixture-only result used an ambiguous privilege-
  drop label. The retained closed trace was rechecked with a stronger verifier
  that reports `privilege_drop_required: false`,
  `privilege_drop_observed: false` and no root-output claim for this fixture.
  This was offline/native trace analysis, not a rerun of historical inventory.
- Black checks, fatal Python lint and Python 3.10 grammar checks passed for the
  final helper, verifier, corrected tests and caller. This is syntax/static
  compatibility, not Python 3.10 runtime qualification.

### Historical authentication blocker and preservation checkpoint

The exact final noninteractive invocation was attempted once through
`run_inventory_v3.py before --noninteractive`. Sudo returned status 1:

```text
sudo: interactive authentication is required
```

The helper did not execute as root. No privileged inventory was accepted, no
complete native preservation baseline exists, and **zero LinuxToys 7.10.4
qualification tests have run**. Platform-specific skips remain undetermined.
No historical input was skipped or read with weaker flags to bypass this gate.

The remaining action is authentication for this exact prepared invocation. In
the existing `igris` terminal, the unprivileged controller can be started with:

```sh
/usr/bin/python3 -I -S -B /home/ta/linuxtoys-7104-inventory-nc_43a8j/run_inventory_v3.py before
```

It invokes only the pinned inventory under strace and retains each attempt in a
separate evidence directory. It does not change sudo policy or open a privileged
shell. Completion must be independently verified before using the result as a
preservation baseline; any newly encountered unsafe or incomplete input remains
a failure. Only then can a fresh exact-commit qualification run begin, followed
by complete protected-path before/after comparison.

Local preservation at the helper-work checkpoint matched **6,101 file-content
hashes and 6,846 stable metadata entries**, including previous qualification
artifacts and the prior uncommitted report. There were no content/stable-metadata
changes, strict Git changes or Desktop capture-ref changes; one local read-atime
observation was retained. This report update is the sole intentional document
change after that checkpoint. Full native subtree/content preservation remains
unverified pending the privileged baseline; metadata-only checks do not replace
it.

No protected permissions, ownership, capability settings, mount options,
services, repositories or package databases were changed. No real package
transaction ran. Evidence and helper versions remain under the new local/native
workspaces. **The report remains uncommitted** because qualification and full
preservation verification have not passed. No push, publication, deployment or
history rewrite occurred.


## Authenticated inventory follow-up — 2026-11-17

### Execution and independent verification

The controller must run as `ta` (UID 1000). An initial direct invocation from the
user's root terminal was refused before scanning; this guard was retained.
The user then started the UID-1000 controllers with `runuser` and authenticated
their fixed sudo invocations. No privileged shell, sudo-policy change or broad
privileged filesystem command was used.

The additional helpers retain the original scanner functions exactly; only
literal policies fixing each allowlisted root and its ancestor identity differ.
An offline AST comparison verified all 14 generated helpers have identical
scanner functions and parse with Python 3.10 grammar. This is not Python 3.10
runtime qualification. Privileged execution uses the pinned helper bytes on
standard input to isolated system Python under strace. Evidence is written by
the UID-1000 controller into the separate private workspace. Each helper drops
supplementary groups and UID/GID before emitting output, including on rejection.
The allowlist and closed-trace checks are the privilege boundary; they are not
an OS sandbox or a claim of constrained sudo policy.

Each successful result was rechecked independently from the collected native
trace: actual directory membership, descriptor-relative access, strict
`O_NOATIME`/`O_NOFOLLOW`, owners/types, file byte counts, no outside inventory-data
reads, no input mutations, and observed privilege drop before output. Trusted
interpreter startup reads are distinguished from the inventory phase. No
ordinary-read fallback was used for historical inputs.

| Complete slice | Entries | Files | Directories | Bytes hashed |
| --- | ---: | ---: | ---: | ---: |
| `linuxtoys-m5-nala-f3-ef5eb1a7/bwrap-inputs-v3` | 170 | 167 | 3 | 163,658,496 |
| `linuxtoys-m4a-qualification` | 9 | 8 | 1 | 921,526 |
| `linuxtoys-m5-nala-f3-ef5eb1a7/bwrap-inputs-v4` | 170 | 167 | 3 | 163,658,496 |
| `linuxtoys-m5-nala-f3-ef5eb1a7/bwrap-results-v3` | 7 | 5 | 2 | 248,268 |
| `linuxtoys-m5-nala-f3-ef5eb1a7/bwrap-results-v4` | 7 | 5 | 2 | 243,472 |
| Total | 363 | 352 | 11 | 328,730,258 |

All roots above are under `/home/ta`. These are complete individual before
inventories, not a complete native baseline or before/after comparison.

The failed rootfs helper's SHA-256 is
`98e928412dfb802b0848de4c580a605fd0f8fdb5a90874c33563854b7a424fdf`.
Its invocation is `invocation-a1b0d05fd6a74d4d86f699492b02b92d` in the active
native workspace's `evidence/` directory. It returned status 1 and
`complete: false`. The trace records no-follow metadata identifying
`lifecycle/bin` as a UID/GID `0:0` symlink, inode `2142218`, mode `0777`.
An offline rejection-trace check confirmed no open/readlink of the link and no
input-mutation syscall in the inventory phase. The helper dropped UID/GID to
1000 before reporting rejection. This partial scan is not accepted as an
inventory and supplies no hashes for the remainder of that subtree.

The batch stopped at this first rejection. Its nine unexecuted slices are
`bwrap-rootfs-v4`, `container-inputs`, `container-inputs-v2`, `container-results`,
`container-results-v2`, `gnupg-driver`, `gnupg-driver-v2`, `gnupg-driver-v3` and
`gnupg-driver-v4`, all within the same historical M5 workspace. They were not
silently omitted from an accepted baseline.

### Additional preparation failures retained

Strict UID-1000 baseline composition first stopped at the root-owned M4
workspace, prompting its separate identity-pinned inventory. A subsequent
composition attempted to reopen a private child of the already verified
`bwrap-inputs-v3` snapshot and failed with `EACCES` before reading data. The
composition was corrected to incorporate every entry of the independently
verified complete privileged manifest, checking the public root identity
without redundant unprivileged reopening. No snapshot entries were discarded.
The next strict scan stopped at `bwrap-inputs-v4`, leading to metadata-only
discovery of the other required privileged slices.

Discovery inspected 101,757 metadata entries, did not read regular file bodies
and did not traverse nonowned roots. It identified the explicit batch roots;
it was never treated as a content inventory. Every failed attempt and helper
version remains available. The final local-preservation assertion also failed
on the directory timestamp discrepancy described above; its result and failed
assertion are retained without restoration or a passing label.

### Source, test scope, evidence and completion

HEAD remains exactly `7686ad45461e99927e4a548fbdddfec4cc5cb57f` on
`arm64-support`; tracked production source and history are unchanged. The
previously verified exact source archive (998 committed file/link entries and
SHA-256 recorded above) remains retained. No new qualification source tree was
extracted and no application code was imported for qualification.

The native inventory-helper fixtures and trace analysis are native ARM64
execution of the preservation mechanism. They are separate from LinuxToys
package, installer, updater, RAM, translation, architecture, MCP, Bash behavior
or regression suites, which remain unexecuted in this qualification. Their
platform-specific skips remain undetermined. Application Python compatibility,
shell syntax, formatting and static checks have not been rerun natively. Prior
host test results are not substituted for these pending checks. Real package
transactions and package-manager lifecycle behavior remain untested.

Current local evidence directory:
`target/upstream-7.10.4-native-resolved-9w345urc/`.
It contains the preserved prior report, collected native receipts/manifests/
traces in `native-final-evidence/`, the original evidence archive,
`verified-final-privileged-results.json`, identity pins in
`remaining-privileged-plan.json`, generated-helper static verification, failed
baseline attempts, and `local-final-preservation.json` with the final discrepancy.
The original helper-development and failed qualification directories remain
preserved. The earlier local checkpoint passed 6,223 hashes and 6,979 stable
entries; the later final checkpoint supersedes it for final status and is not
fully passing. The report update is an intentional document change after that
comparison, with its original bytes saved in `prior-uncommitted-report.md`.

No protected permissions, ownership, capabilities or mount options were changed.
No `igris` services, repositories or package databases were modified. No package
transaction, publication, deployment, history rewrite or push occurred. No
attempt was made to restore observed timestamps or modify historical artifacts.
There is no complete native preservation comparison to establish broader
before/after preservation.

The next genuine blocker is the existing historical symlink under a policy
that explicitly rejects symlinks. Proceeding requires an explicitly revised,
reviewable preservation policy or another authorized mechanism that satisfies
the existing policy; historical links must not be changed to make the scan pass.
The local directory-metadata discrepancy also remains recorded and unresolved.
**No commit was created.**

## Preservation-blocker investigation — 2026-11-17

**Stopped with both blockers unresolved. Zero LinuxToys qualification tests ran.**
HEAD is still `7686ad45461e99927e4a548fbdddfec4cc5cb57f`. No historical
inventory was resumed and no incomplete leaf was accepted into a baseline.

New local evidence and reviewable policy/code/tests:
`target/upstream-7.10.4-preservation-policy-y6wai6zg/`.
New native fixture workspace:
`/home/ta/linuxtoys-preservation-policy-l7x8epfd`.
The preceding report bytes are saved as `prior-uncommitted-report.md` in the new
local workspace. Earlier workspaces, failures, traces and manifests remain intact.

### Symlink decision and access boundaries

`POLICY.md` specifies links as leaf entries, never target traversal. A complete
leaf requires exact target bytes and ownership, mode, device/inode, link count,
size, blocks and nanosecond atime/mtime/ctime. Absolute, relative, dangling,
cyclic and chained targets remain literal bytes. Directory and regular-file
no-follow/no-atime guards remain unchanged. Replacement, authority/device
mismatch, hard links and limits fail closed. Parent/ancestor and membership
checks remain prerequisites for an enclosing complete scan.

The isolated `symlink_policy.py` prototype inspects a leaf through no-follow
metadata and a pinned `O_PATH` descriptor. It emits explicit `complete:false`
and `target_present:false`; its completion gate rejects the record. It has no
successful complete-inventory path and does not replace any retained helper.

On native ext4, six deliberately atime-eligible disposable links showed an
atime-only change for parent-relative `readlinkat` with O_NOATIME on the parent,
empty-path `readlinkat` on O_PATH descriptors, and empty-path reads after
requesting O_PATH|O_NOFOLLOW|O_NOATIME. F_GETFL on those link descriptors returned
O_PATH|O_NOFOLLOW without O_NOATIME. Cases include dangling/relative, absolute,
chain and cyclic targets. Both raw-traced and untraced runs reproduced this.
Pinning a descriptor protected target identity against replacement but did not
protect atime. A post-read rejection cannot undo that violation. **No target
capture was attempted on the historical symlink. Its target remains unknown.**

The retained privileged rejection trace was independently reread through an
APFS clone. It identifies `lifecycle/bin` with AT_SYMLINK_NOFOLLOW: device 66306,
inode 2142218, UID/GID 0:0, mode 0777, nlink 1, size 7, blocks 0,
atime `1794746768022615329`, mtime/ctime `1794746767981851796` (all ns).
It contains no bin open or readlink, and records the UID/GID/groups drop before
rejection output. This is retained metadata evidence, not a fresh root scan.

Fresh UID-1000 descriptor-only inspection confirmed the pinned historical root
identity (inode 2136050, UID/GID 0:0, mode 0700) and unchanged metadata on its
open, then stopped with EACCES at `lifecycle`. No ordinary-read fallback ran.
The fixed `historical_metadata_probe.py` separately refused its unprivileged
entry point before historical access. Its exact noninteractive sudo invocation
was refused: `sudo: interactive authentication is required`. No new privileged
metadata scan or privileged fixture proof was obtained. The retained root trace
does not substitute for new privileged validation of the proposed policy.

### Focused verification and retained failures

Nine preservation-policy tests passed under UID 1000 with raw descriptor
tracing; the same nine passed without tracing. Coverage includes leaf shapes,
authority/device mismatch, hard-linked symlinks, nonlinks, unsafe components,
replacement before/on/after open, pinned-descriptor replacement, chain
non-traversal and target-read atime counterexamples. These are nine distinct
tests in two execution modes, not eighteen distinct tests or qualification tests.

An independent closed-phase verifier accepted exactly two no-follow pathname
stats, two descriptor stats, one O_PATH|O_NOFOLLOW open and one close:
no target/body reads, traversal, mutation or output inside
that phase. Five malformed proofs were rejected. The result explicitly states
UID 1000, `privileged:false`, and `complete_inventory:false`. All six new Python
files parsed with Python 3.10 grammar; this is not Python 3.10 runtime testing.

The first run used strace -yy and retained seven passing tests, one error and
one failure: link descriptor/chain metadata changed. The unchanged tests passed
with raw descriptors and without tracing. Descriptor decoding is therefore not
approved for historical symlink descriptors. That failed run and all fixture
atime changes remain preserved. Intentional fixture-only utime/replacement
operations never addressed historical inputs. The earlier historical rejection
never opened a symlink descriptor, so this experiment does not establish that
its link metadata changed.

### Exact `.repowise` discrepancy and independent current checks

The retained local-before and local-after agree. The retained local-final differs
in stable metadata only at the `.repowise` directory's mtime/ctime. Its directory
atime also differs between checkpoints. Exact recorded values are:

| Directory timestamp (ns) | Retained before/after | Retained final | Current clone-verification checkpoint |
| --- | ---: | ---: | ---: |
| `.repowise` atime | 1794869636168390072 | 1794907603419483354 | 1794908294725328609 |
| `.repowise` mtime | 1794869634918857586 | 1794907602413883924 | 1794908293872739771 |
| `.repowise` ctime | 1794869634918857586 | 1794907602413883924 | 1794908293872739771 |

`.repowise/omissions` has unchanged atime/mtime/ctime across those checkpoints.
The root's device/inode, ownership, mode, size, nlink, blocks and birthtime match.
The retained operation traces cover native inventory access, not the local APFS
directory's writer. No retained local mutation trace identifies the operation
or process responsible. Endpoint hashes and coincident timestamps cannot prove
a transient entry operation or attribute it to SQLite, repowise, Git or Codex.
**Causation remains unresolved. No directory timestamps were restored.**

Disposable APFS fclonefileat verification first demonstrated unchanged source
metadata including atime. The current fixed-path check then hashed clones of
all 6,223 previously recorded regular files, checking original descriptor/path
metadata before/after cloning. All historical file hashes and both `.repowise`
database hashes matched. Two differences from the older retained final were
the subsequently updated report and the browse side effect described below.
All 6,979 fixed-path metadata records were unchanged during that clone-check
interval, including atime. This did not enumerate original directories or prove
absence of new members. It does not establish a complete native comparison.
There are 180 atime differences from the older final snapshot; early ordinary
local discovery/evidence reads were not enclosed by a new atime baseline.
Accordingly no blanket no-atime claim is made for this investigation.
The later final-state checkpoint additionally records 179 paths with atime
differences since the guarded clone-check interval, including both databases.
Their cause is not attributed. Only `.gitignore` recovery and this authorized
report edit differed in stable metadata over that later interval. The final
Git check itself observed no fixed-path metadata changes. These later
observations are retained in `final-state.json` and
`git-and-later-metadata-comparison.json`; they are not passing global preservation.

### Unintended output, final state and stop decision

The requested gstack browse runtime failed before loading a page because its
Chromium executable was absent; nothing was installed. Its startup nevertheless
appended `.gstack/` to the tracked `.gitignore` and created a new `.gstack` startup
error log. The exact added bytes, source implementation (`browse/src/config.ts`
ensureStateDir), clone-verification failure/difference, metadata and error output
are retained in the new workspace. The unwanted line was removed after checking
the remaining bytes against the prior SHA-256; `.gitignore` content matches
again. The new startup directory was moved into `browse-startup-output` for
retention. Its effects on `.gitignore` timestamps were not restored or hidden.
This is an additional preservation failure, not a clean preservation pass.

Tracked content/strict Git refs/HEAD were checked separately: final tracked
content matches HEAD, and strict refs, HEAD and status match the retained Git
checkpoint. Desktop capture-ref differences are retained separately. No commit,
history rewrite, push or deployment was made. Only this report is an
intended working-tree document change; new policy/evidence stays in the fresh
ignored target workspace. No historical permissions, ownership, capabilities,
mount options, package operations or system configuration were changed. The
metadata probe and leaf policy performed no historical target or body reads.
No broad privileged filesystem command ran.

**Neither blocker is resolved. Qualification remains stopped.** Required future
work is a proven preserving target-capture mechanism with separate privileged
validation, and evidenced attribution of the `.repowise` directory mutation.
Neither missing fact is inferred or treated as permission to proceed.


</details>


</details>
