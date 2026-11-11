# Artifact-only script preparation

Date: 2026-11-10. Baseline: M3A `e4f44a1f19a8870a8a760e6531fdc42a5f8ac728`.
Local engineering only. Neither workflow was run; no upstream service changed.
The [M3A contract](SCRIPT-ROLLOUT.md), approved revision and ISA policy are unchanged.

## Audit and replacement

At the baseline, `.github/workflows/sync-scripts.yml` had these risks:

| Baseline lines | Risk | Prepared replacement |
| --- | --- | --- |
| 4–7 | Push to master automatically synchronized scripts. | Only manual `workflow_dispatch`, without inputs, schedule or chained workflow. |
| 16–23 | Mutable checkout action/default repository branches; `SCR_TOKEN` authorized a second repository. | Pinned checkout action, explicit event commit SHA, `contents: read`, credentials not persisted; no second repository or secret. |
| 27–31 | Deleted the remote checkout tree before verifying replacement data. | Never checks out, deletes or writes a mirror tree. |
| 32 | `scripts/*` omitted the required hidden manifest and suppressed copy errors. | Enumerates the exact approved inventory, including hidden files; any failure stops preparation. |
| 35–40 | Committed and pushed automatically, without a review artifact or revision contract. | Prepares an archive/report/checksums and stores only a workflow review artifact after successful validation. |

Related code inspected: `dev/prepare_script_rollout.py`,
`p3/app/script_compat.py`, `architecture-routes.json`, `script-revisions.json`,
`scripts/.linuxtoys-scripts.json`, `git_scripts_manager.py` and other workflows.
M3A runtime synchronization already fetches an approved versioned tag into staging
and validates it before promotion. That application path is unchanged. No workflow
consumer/chained publisher for the new review artifact was found in this checkout.
Unrelated release workflows are unchanged.

The replacement uses Ubuntu 24.04 and immutable action references. Repository
permissions are read-only; no write permission, deployment environment, release
step, remote Git command, token secret or approval-writing command exists.
The two actions are checkout and upload-artifact. Future manual execution would
use Actions' read token for checkout and runtime artifact storage authorization;
it is **not credential-free CI**. Local Python preparation needs no credentials,
Git executable, network connection or third-party Python dependency.

GitHub Actions review artifact storage is an explicit output capability. There
is no Git repository, tag, release, package, mirror or deployment publisher. The
artifact name includes commit/run/attempt, `overwrite` is false and missing output
is an error. Upload follows successful commands only. The ZIP wrapper/retention
metadata of Actions storage are outside the reproducibility claim.

## Local preparation and verification

Use the trusted client checkout paired with its existing approval files:

```sh
python3 dev/prepare_script_rollout.py --check
python3 dev/prepare_script_rollout.py --check --artifact-dir /tmp/script-review
# Substitute the exact approved revision directory printed above:
python3 dev/prepare_script_rollout.py --check --verify-artifact /tmp/script-review/REVISION
```

Each new `OUTPUT_ROOT/REVISION/` contains exactly:

- `scripts.tar`: sorted regular members under `scripts/`, including the manifest.
- `validation.json`: API, architecture-policy hash, revision, file counts, payload
  bytes, archive hash and completed validation checks. No timestamp/host path.
- `SHA256SUMS`: SHA-256 of the archive and report; it does not authenticate itself.

`REVISION` remains SHA-256 of the **existing raw manifest**, not a newly generated
approval. The production value remains
`083138ce4b55ccf533a215c995bf27db25eae80d60b487150ae710f14d245e5f`.
No changed scripts, architectures, policy, lock or manifest are approved here.
The retained `--write` mode is a separate, explicit future client-review operation;
it cannot be combined with artifact/export/verification flags and is never called
by the workflow. This milestone did not invoke it or refresh route digests.

The archive is canonical POSIX pax: regular files only, sorted names, uid/gid and
mtime zero, empty owner names, mode 0755 for `.sh` and 0644 otherwise. File bytes
and manifest line endings are preserved. Input location, modification times,
permission bits and enumeration order do not affect artifact bytes. Source file
modes are not a new execution-eligibility signal. The existing `--export NEW_DIR`
also uses the strict snapshot, preserves dotfiles and refuses an existing target;
tree filesystem timestamps are not part of the reproducibility claim.

Validation rejects malformed/duplicate JSON keys, incompatible schema/API/policy,
unapproved revisions, invalid hashes/paths, traversal, case and file/directory
collisions, missing/extra files or directories, symlinks and special files. Reads
are bounded and no-follow, and digests are freshly checked after M3A validation.
CLI preflight checks file types before invoking legacy manifest-generation logic,
so a declared FIFO cannot block an ordinary read. No installer body is executed.

Preparation deliberately has **no runtime metadata exceptions**: `.git`, root
README/LICENSE or any empty/extra directory is refused in the source/export.
M3A's separate mirror-envelope exceptions remain unchanged at runtime. Limits
are 1 MiB manifest, 10,000 declared files, 16 MiB/file and 64 MiB total payload.
Installed client code/policy/lock and the local filesystem owner remain trusted;
this is not a sandbox against concurrent same-user/root interference.

The revision directory is reserved exclusively, including when an existing path
is empty or a symlink. It is never overwritten, even with matching bytes. During
writing it has `.incomplete`; every output is read back before removing that
marker. Handled failures remove only the newly created revision directory. A crash
or cleanup failure may leave an incomplete directory: verification refuses it,
and subsequent preparation refuses to overwrite it. Inspect/recover it manually
or use a fresh output root. No force/replacement option exists.

`--verify-artifact` reconstructs the exact expected archive/report/checksum bytes
from the trusted client snapshot. It does not trust a downloaded report, checksum
file, directory label or tar metadata to approve content. Run this **before**
extracting an artifact. Hashes establish correspondence, not new signatures or
publisher identity.

## Future maintainer publication procedure

These are review instructions for a separately authorized operation, not an
implemented publishing command or permission to act now:

1. Obtain native amd64 application regression evidence separately. A preparation
   job on an x86 runner tests this tool, not native LinuxToys/GTK/Rust parity.
   Keep Ubuntu ARM64 packaging qualification on hold until its gates are met.
2. Review the exact client commit, production lock, manifest, architecture policy,
   workflow and validation report. Distribute the compatible client/bundled pair
   before exposing scripts requiring its API. Keep legacy default-branch scripts
   for older clients; default branch HEAD never grants new-client eligibility.
3. Prepare and verify a fresh artifact locally. Extract the verified archive to a
   new isolated directory, never over an existing checkout. Review the source
   diff and licensing. Root repository README/LICENSE, if retained for licensing
   and context, are separately reviewed non-executable mirror metadata; they are
   not part of the artifact or approval. Do not introduce other extra files.
4. For **each** mirror, inspect the intended content-addressed tag and target
   commit. If a tag exists, verify it and leave it untouched. Matching existing
   content is a no-op; any conflict stops publication. Never force, delete, move
   or recreate a tag. A missing mirror may be populated only after separate
   authorization and verification of the already reviewed commit/tag object.
5. With publication authorization, use the same reviewed commit/tag object on
   both mirrors. Code/catalog bytes and raw manifest must match the artifact;
   retain licensing metadata consistently. Use exactly
   `linuxtoys-script-api-1-REVISION`. No default-branch overwrite or remote-tree
   deletion is needed. There is no publisher in this repository preparation path.
6. Read back both mirrors into separate disposable directories. Verify identical
   tag/commit objects, raw manifest revision, API, policy and payload inventory
   using the paired M3A client verifier. Review any permitted root README/LICENSE
   separately. Require mirror consistency before calling rollout complete; one
   successful mirror or a tag name alone is insufficient evidence.
7. Roll back by restoring the previously reviewed client/policy/bundle pair,
   subject to its existing release-age gate, or by separately reviewing a new
   compatible revision into a client allowlist. Do not overwrite an immutable tag
   or accept unknown scripts. The current production lock has one entry and does
   not approve M1/M2 font bodies or an older production rollback revision.

## Verification and limitations

See [preparation evidence](script-preparation-evidence.json). Tests run locally on
macOS ARM64/Python 3.13.7. The 25 focused tests exercise malformed manifests,
dotfiles, source/artifact tampering, inventory changes, API/policy mismatch,
unknown and duplicate revisions, FIFOs, special-file metadata fixtures, failed
writes/cleanup, strict legacy export, reproducibility, credential-free CLI and
workflow capabilities. Actual socket binding was unavailable in the session;
socket/device rejection is exercised with file-type metadata fixtures.

The full suite contains 93 tests: 90 pass and three Linux-only tests are skipped.
Ruff 0.12.3 lint/format, AST, Ruby/Psych YAML parsing, Bash syntax for the workflow
run block, manifest/artifact verification and diff checks pass. Actionlint and
ShellCheck are unavailable locally; no such result is claimed. No dependencies
were installed, workflows executed or GitHub/mirror writes performed.
Linux workflow execution, artifact upload/download, mirrors and native amd64 are
unverified. Existing native ARM64 evidence remains the prior M2/M3A evidence;
no application build/runtime qualification or packaging work is added here.

Files changed: `.github/workflows/sync-scripts.yml`,
`dev/prepare_script_rollout.py`, `dev/tests/test_script_preparation.py`, this
report, `dev/script-preparation-evidence.json`, `dev/SCRIPT-ROLLOUT.md`,
`dev/ARCHITECTURE-POLICY.md`, `dev/ARM64-ASSESSMENT.md` and
`dev/ARM64-QUALIFICATION.md`. No application, script payload, production manifest,
approval lock, dependency or other workflow file changed.

## M3C native verification follow-up

[SCRIPT-PREPARATION-ARM64.md](SCRIPT-PREPARATION-ARM64.md) records subsequent
native Ubuntu ARM64/Python 3.14.4 verification: focused/full tests, real Unix
socket/device checks, independent tar verification and byte parity with these
M3B artifacts. The workflow audit now reuses installed PyYAML when Ruby is absent.
Preparation code, workflow definitions and production approvals remain unchanged;
no workflow was run or artifact uploaded. Historical M3B limitations above remain
the record of that Mac-only milestone, rather than new native evidence.
