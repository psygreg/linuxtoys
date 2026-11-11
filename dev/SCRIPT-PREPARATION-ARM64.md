# M3C: native Ubuntu ARM64 script preparation

Baseline: `1bf0f8f40b321ca06f5b974de901a0488d723deb` (M3B).
Scope: verification of the preparation tool and workflow definition, not execution
of GitHub Actions, publication, packaging or new application qualification.
See [native evidence](script-preparation-arm64-evidence.json).

## Environment and isolation

The user's VMware guest is Ubuntu 26.04.1 LTS/AArch64, Python 3.14.4,
Rust/Cargo 1.93.1. PyYAML 6.0.3 is already installed. ShellCheck 0.11.0 was
already retained at `/tmp/linuxtoys-m1-tools/root/usr/bin/shellcheck`.
Actionlint and Ruby are unavailable; no packages, dependencies or tools were
installed. Ruff 0.12.3 lint/format ran on the Mac; Python AST and shell checks
also ran natively. No emulation or native amd64 environment was used.

Source was copied to `/home/ta/linuxtoys-m3c-qualification/source`; disposable
profiles/artifacts are under `run-03`. The Desktop checkout, installed LinuxToys,
system configuration and release workflows were untouched. Bytecode generation
was disabled. Tests use isolated fixtures, including local Git test repositories;
no project or remote tag, mirror or GitHub write occurred.

## Results

| Check | Native evidence |
| --- | --- |
| Preparation and artifact generation | Real CLI `--check` and two `--check --artifact-dir` runs passed. |
| Standard verification | Real `--check --verify-artifact` passed for both outputs. |
| Independent verification | A separate reader inspected the actual tar members, unique/sorted inventory, regular types, modes, uid/gid/mtime, every raw digest, hidden manifest, report and checksums without calling the archive generator. |
| Reproducibility | All three output files are identical between native exports **and** M3B's macOS/Python 3.13.7 evidence. The native tool uses Python 3.14.4. |
| Focused tests | 27 passed, no skips. |
| Full Python suite | 95 passed, no skips, including existing architecture, payload, updater and native Rust/ctypes layout fixtures. No application/library rebuild or GUI test is claimed. |
| Hidden files/malformed content | Manifest and required hidden-data inclusion; missing dotfiles, duplicate JSON keys, incompatible API/policy, unsafe paths, changed inventory and tampering are refused. |
| Filesystem types | Real symlinks, FIFOs and a Unix socket in disposable sources are refused. The existing `/dev/null` character device is refused by the regular-file reader without opening it. Block-device/socket metadata fixtures also pass; no device node was created. |
| Failure/immutability | Existing revisions, symlink/empty destinations, incomplete outputs, write/readback/cleanup failures and tampered archives/reports/checksums are refused. |
| Production integrity | Before/after snapshots around every test and CLI operation preserved content, modes, owners and mtimes across 443 production paths: scripts, their manifest, revision lock and architecture policy. 122 guarded test runs plus 10 guarded CLI operations passed. Separately, all 839 baseline `p3` file contents match in the VM. |
| Workflow validation | Installed PyYAML parsed the YAML; the exact capability allowlist passed natively. `bash -n` and native ShellCheck passed for the extracted run block, with no ShellCheck findings at any severity. The block was never executed as a workflow. |

The approved revision is unchanged:
`083138ce4b55ccf533a215c995bf27db25eae80d60b487150ae710f14d245e5f`.
The archive SHA-256 remains
`ee16612ea2530214eb8fcbab5d493838f4639cd759c2dd8a991c71861fefea37`.
There are 337 declared payload files plus the manifest (338 tar members).

## Verification-only changes

M3B's optional YAML audit required Ruby. On this guest that would skip the audit
despite installed PyYAML. The test now reuses either existing parser; it adds no
dependency or application import path. A Linux-only test exercises the real Unix
socket and existing character device rather than relying only on metadata mocks.

`dev/tests/native_script_preparation_smoke.py` makes the qualification repeatable.
It runs the actual CLI, independently inspects artifacts, compares M3B hashes,
and guards production paths around the focused/full tests and failed operations.
An explicit optimization guard and regression test prevent `-O` from disabling
the probe's assertion-based qualification checks before any output is created.
No preparation implementation defect was found. The preparer, application code,
scripts, manifest, approval lock, architecture policy, dependencies and all
workflow definitions are byte-identical to the baseline.

On macOS, the final suite has 95 tests: 91 pass and four Linux-only tests skip
(the three existing checks plus the new native socket/device test).
Ruff lint/format, AST/JSON parsing and `git diff --check` pass.

## Workflow capability review

The unchanged workflow has only `workflow_dispatch`, without inputs or an
automatic/chained trigger. Its only repository permission is `contents: read`.
Checkout uses `${{ github.sha }}`, an immutable action reference and
`persist-credentials: false`; there is no mirror checkout or custom token secret.
The three run-block lines enable strict shell handling, run preparation tests
and call **only** `--check --artifact-dir`. No `--write`, Git publisher, tag,
release, package, deployment or remote API writer is present.

The other pinned action is upload-artifact: future manual execution could write
an Actions **review artifact** with `overwrite: false`, error on missing output
and seven-day retention. This explicit storage capability is not a Git repository
publisher. No cross-workflow publisher for this artifact was found in this
checkout. No workflow/action was run and no Actions artifact was uploaded or downloaded.
External action code and hosted-runner execution are not qualified by static
inspection or by running the local preparation tool.

## Reproduction and remaining boundaries

With the existing guest tools and a fresh isolated source copy:

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 dev/tests/native_script_preparation_smoke.py --workspace NEW_DIRECTORY
```

The probe refuses a non-native Linux ARM64 host, an existing workspace and `-O`.
Its `evidence.json` and stderr test log record the exact operations. Fixtures
change only their disposable data; production source is never modified to
simulate failure. Failed output directories are handled under the M3B rules.

Actionlint is unavailable and was not installed. Native ShellCheck supplements
YAML parsing/capability assertions but does not replace GitHub's server-side
workflow validation. Actual Actions checkout/storage, mirror consistency,
publication and rollout remain untested and require separate authorization.
Native amd64 application qualification is still a separate gate. No Ubuntu ARM64
packaging qualification, application feature promotion or deployment began.
The existing trusted-client/filesystem-owner assumptions and lack of new signing
provenance remain unchanged.
