# Debian package-state correction

Baseline: `e27e7ce45060e81ebf3ce36e4f171a6e6ba89268`, branch
`codex/u1-atomic-reporting`, 2026-11-15. This corrects the two dpkg-state defects
recorded by the preceding Nala/F3 qualification investigation. **Nala is not
enabled or qualified.** F3, all hook approvals, route eligibility, script
manifests, revision approvals and historical qualification reports are unchanged.

## Caller trace and implementation

Nala's unchanged native catalog entry in `p3/scripts/repos.json` reaches the real
catalog/parser, `repo_parser.materialize_repo_script()` and generated
`pkg_install nala`. Architecture entry/override checks and the loader's exact
script-path/bundle guard precede shell execution. Generated native dependencies
from `repo_parser` and `library_loader` also use `pkg_install`.

The shared `pkg_install` first calls `pkg_exists` and skips packages in
`pkg_found`. For remaining packages it performs `_architecture_check packages`,
then askpass, the transaction lock and `interrupted_apt_guard`, before the APT
transaction and transmap append. The existing guard waits for busy managers,
audits dpkg, invokes configuration/repair when required and checks dependencies.
Its implementation, privilege boundary, locking and failure handling are not
modified by this correction. `sysup.sh` calls the same guard directly; that
updater path is unchanged.

Direct `pkg_exists` consumers were inspected: OBS's Debian dependency path,
Piper's build-dependency bookkeeping, the power-options presence check,
codecfix's rpm-ostree override list and AppImage FUSE checks. The Debian OBS/Piper
paths now see conffile-only and incomplete packages as needing installation;
the non-Debian consumers retain their original queries/results. The separate
direct `dpkg -s libfuse2*` checks inside AppImage installation are outside this
fix and remain unchanged. This is not a claim to fix every dpkg presence check
in the project.

`pkg_remove`/`pkg_rm` and generated reversal scripts also consume these arrays.
An internal incomplete-package list preserves removal of partial packages,
while a conffile-only record no longer initiates a no-op removal. Native remove
arguments, including the existing `--allow-unauthenticated`, and conffile/
dependency retention semantics are unchanged. No purge is added.

The small private `_pkg_dpkg_state` helper uses:

```sh
dpkg-query --admindir="$database" --show --showformat='${Status}\n' -- "$package"
```

It resolves the existing standard `DPKG_ADMINDIR` or `DPKG_ROOT` location, with
`/var/lib/dpkg` as the default. The status database must be a readable regular
file; dpkg-query otherwise reports a missing database like an absent package.
The installed dpkg-query manual documents exit 1 as no match and exit 2 as a
fatal/system/database error. Only exit 1 with empty output becomes absence;
other errors and malformed/empty/multiple status results stop processing with
the package name. Failed queries clear all classification arrays. No localized
stderr parsing or privileged query is introduced.

| Established status | Result |
| --- | --- |
| `* ok installed` with a recognized selection word | Installed; preserve the no-authorization/no-transaction short circuit. Hold/deinstall/purge selection does not erase physically installed state. |
| No entry, `* ok not-installed`, `* ok config-files` | Not installed; conffiles remain untouched and a later install is not skipped. |
| Half-installed, unpacked, half-configured, triggers-awaited, triggers-pending, or `reinstreq` | Incomplete; installation reaches the existing recovery path. Partial packages remain eligible for explicit removal. |
| Unreadable/missing/corrupt database, query failure, unknown or ambiguous result | Fail closed. Initial query errors precede authorization; post-recovery query errors prevent further dispatch/recording. |

After recovery of an initially incomplete request, `pkg_install` re-queries the
pending package list. Persisting incomplete state or a failed query stops the
operation. Already recovered packages are not passed to install or appended as
new installs to the transmap, preventing their later automatic reversal as new
packages. Only still-absent packages continue, with the original flags and
transaction behavior. The bypass flag retains its existing lock semantics.
This does not add a transactional snapshot, solve concurrent database races or
guarantee that every possible package breakage can be repaired.

## Verification boundary

Actual native execution uses existing Ubuntu 26.04.1 AArch64, Linux
`7.0.0-43-generic`, Python `3.14.4`; host execution uses macOS arm64 and existing
`/opt/anaconda3/bin/python3` `3.13.7`. There is no AMD64/emulation claim.

`test_package_states.py` runs the real helper and recovery control flow. Only
native `dpkg-query` executes against temporary databases. Every mutating
package command, authorization helper and busy/lock probe is a shell fake;
denial executables earlier on PATH also block direct external package commands.
Successful configuration is simulated by replacing only temporary fixture
status bytes or mock query output. No actual configuration, APT check, install,
removal, privilege escalation or lifecycle operation is run.

Real native fixtures cover installed selections, absent and conffile-only
states, all recognized incomplete states, reinstreq, corrupt/unreadable/unknown
data, alternative database roots, qualified names, version requests, mixed
states and ambiguous multi-package queries. Fixtures also verify recovery
ordering, recovery/query failure, post-recovery transaction provenance, partial
removal and the installed no-op. Pacman/CachyOS/Manjaro, RPM/Fedora/ostree/SUSE/
RHEL and eopkg/Solus compatibility checks are mocked query/decision tests, not
native qualifications of those distributions.

The previous two `expectedFailure` decorators were removed from
`test_m5_candidate_failures.py`; those assertions now pass unchanged in meaning.
Its temporary database uses standard `DPKG_ADMINDIR` with real dpkg-query.
An initial native fixture run correctly failed on missing mandatory trigger
fields; corrected trigger records include `Triggers-Awaited`/`Triggers-Pending`.
The initial failed log/source and the later passing runs remain retained.

Final commands, results and preservation receipts are recorded under
`target/nala-package-state-fix/`; native user-data copies/logs are under
`/home/ta/linuxtoys-nala-state-e27e7ce4/`. Source copies are private user-data
directories, not a new nested sandbox or an installed application replacement.

| Final selection | macOS arm64 | Native Ubuntu AArch64 |
| --- | --- | --- |
| `test_package_states.py` | 18 passed, 11 skipped (dpkg-query absent) | 29 passed |
| Existing `test_m5_candidate_failures.py` | 8 passed, 4 skipped | 12 passed; no expected failures |
| Established offline regression selector | 122 passed | 122 passed |
| Existing 7.10.2 compatibility regressions | 10 passed | 10 passed |
| Total | **158 passed, 15 skipped** | **173 passed** |

Native Bash is `5.3.9`, dpkg-query `1.23.7`; host Bash is `3.2.57`. Python Black,
Pyflakes and AST checks pass for both changed test files; Bash syntax checks
pass on both platforms, and Git whitespace checks pass. ShellCheck is absent
on both platforms and was not installed. No full native build, Rust compilation,
package-producing test or real package-manager transaction is claimed.

Host commands, from the repository root (existing interpreter only):

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 -m unittest discover -s dev/tests -p test_package_states.py -v
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 -m unittest discover -s dev/tests -p test_m5_candidate_failures.py -v
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 target/m5-nala-f3-qualification/run_regressions.py
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 -m unittest discover -s dev/tests -p test_7102_compatibility.py -v
/opt/anaconda3/bin/python3 -m black --check dev/tests/test_package_states.py dev/tests/test_m5_candidate_failures.py
/opt/anaconda3/bin/python3 -m pyflakes dev/tests/test_package_states.py dev/tests/test_m5_candidate_failures.py
bash -n p3/libs/packages.bash
git diff --check
```

The same four test selections ran with `/usr/bin/python3` in private native
source copies. The 122-test runner was copied into the private root and invoked
there; it refuses network/build/root/package-producing commands and local Git
fixture commits. Its seven explicit exclusions and per-test output are retained.
Native runs use private HOME/XDG/TMP paths, disabled timefix, the existing denied-
IP LD_PRELOAD library and dead-loopback proxies. Exact source/test inputs are
bound by source manifests; all 991 files in the last native copy match its local
input manifest. The final 29-test safety-fence run changed only test infrastructure
after the 122+10+12 regression pass; the runtime helper and candidate regression
bytes remained identical.

Preservation checks matched:

- **17/17** policy/manifest/lock/dependency/version files and **338/338** script
  bundle files. All F3/Nala eligibility declarations and F3's hook are unchanged.
- **131/132** client library files; the only intended library change is
  `packages.bash`. Exact source comparisons confirm the other-manager query and
  install branches, `interrupted_apt_guard`, and the removal body apart from
  inclusion of incomplete packages remain byte-identical.
- **80/80** assessment-protected M4B files, **2021/2021** original U1 evidence
  entries and **4525/4525** task-preexisting evidence files. Recovery material and
  prior qualification reports were not rewritten.
- Independently approved M4A DEB: **8,554,000 bytes**,
  `83173db3b42d8ef966b6bde02f064beb42ee71b4593bfd727a3fefefdb862f04`.
  Historical M4B completion: **833 bytes**,
  `b1daa68ac265ad596a29005b667af024d5a9f3375d5bdb4dbe5c1c051dd37983`.
  Historical M4B inventory: **6360 bytes**,
  `819eb5a4c9a62b380a54267966c29f749e72a24ce0e79aa2229ad03f51d8651d`.
- **2294/2294** monitored current VM package/application/user records, including
  status, APT/dpkg logs, installed LinuxToys and existing application data.
  Private test inputs/results and ordinary SSH activity are outside that claim.

The current VM baseline retains the earlier unattended glibc/Pillow update
recorded in `M5-NALA-F3-QUALIFICATION.md`; this phase neither reverted it nor
claims the original M4B environment was restored. Before staging, HEAD, index,
branch/tag refs and reflogs matched task start. Four refs under
`refs/codex/turn-diffs` rotated to different names pointing to the same object;
their exact delta is retained. No agent ref-repair/history rewrite occurred.
The prior attribution-history and missing-checkpoint caveats remain applicable.

Receipt anchors (SHA-256, ignored evidence directory above):

| Record | SHA-256 |
| --- | --- |
| `preservation.json` | `45fd84d9fe459128701ada108c36c658d070ab894661b9756a49a55cb56a5d78` |
| `vm-preservation.json` | `8fd379cfea3a52732329c5667946a19a552e13cfbaa6507df3a2041801a5ff3e` |
| `native-test-logs.tar` | `da43bdb9f6ddc1a4da727374269d105d82fd15675a764246f68f16a90c81be0e` |
| `native-verified-log.tar` | `5ea03492894ed7af12b2d1b8aa09f93cf2b427552a467f3fabd08f0b72c8adfe` |

## Remaining Nala qualification requirements

This source fix removes two demonstrated state-detection blockers; it does not
qualify Nala's actual runtime, dependencies, installation, failure, interruption,
rollback, user-configuration retention or removal/reinstall lifecycle. Those
still require a separately authorized suitable disposable environment and the
previously documented adversarial cases. No further Docker/Bubblewrap variant,
host package operation, build or package generation was attempted. Future route
promotion still requires the complete evidence and existing client-controlled
architecture/script approval process. F3's independent ARM64 hook-approval
blocker remains unresolved and untouched.
