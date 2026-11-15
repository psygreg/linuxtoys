# MCP skill fallback milestone

2026-11-15. Baseline: `03109aa537e6309bf987819925f66fa034414e85`.
Selective adaptation of upstream 7.10.3's `fa53ecd` / `c7cf27a` skill-helper
separation. No Paru/AUR change or broader upstream merge is included.

## Installation contract

`app/mcp_skill.py` uses only the Python standard library. The server re-exports
`install_agent_skill()`, `skill_install_script()` and its existing skill constants.
Both direct-file and module-mode `mcp_server.py --install-skill` dispatch before
application imports, token creation, warmup, binding a port or service changes.
The helper can also be executed directly or imported as `app.mcp_skill`.

The automatic path now installs the bundled reviewed text offline. It does not
execute `bun x skills`, fetch mutable remote instructions or use a package manager.
This is intentional: an external installer cannot provide this milestone's
non-overwrite and no-follow guarantees. Retained repository/timeout constants are
compatibility exports, not active network configuration.

Before any home writes, the helper reads a bounded regular non-symlink bundle,
checks UTF-8 and its client-pinned SHA-256:
`46e7bb34acbee8a9a1140cbc07e2785837fb19c5365d0fe769be0a3170e85414`.
Both existing skill assets remain byte-identical. A future bundled-text update
requires reviewing and updating this helper pin; a missing/corrupt copy fails
closed with diagnostics and status 1. There is no network repair of an invalid
bundle. This content check grants no remote script or architecture approval.

Detected agent roots receive `linuxtoys-mcp/SKILL.md`. The universal `.agents`
root is created only when no supported agent root exists. An unsafe/conflicting
existing root does not justify creating a different universal target. A `.config`
ancestor that cannot safely be inspected stops detection rather than guessing
that the profile is fresh. Individual unsafe detected targets are skipped with
stderr diagnostics; other safe targets may succeed. The legacy list return and
best-effort success semantics remain: at least one verified/new path is success,
so partial success must be read together with the diagnostics.

Existing identical owned regular files with safe permission bits are accepted
without changing their inode, mtime or permissions. Different, customized, older
and empty existing skills are preserved and reported for manual resolution.
There is no automatic upgrade, force-overwrite option or backup deletion.
Legitimate skill symlinks are also refused rather than dereferenced or replaced.

## Publication and security decisions

- Home and destination traversal uses descriptor-relative `O_NOFOLLOW` directory
  opens, including the home path itself. Below the home anchor, existing
  directories must be owned by the current effective user and must not be
  group/world writable. Existing modes are never changed. New directories are
  0700; new skill files and lock files are 0600.
- A persistent regular owned 0600 `.install.lock` serializes cooperating
  installers. Exclusive creation and opening an existing lock are separate
  operations; this also resolves the concurrent-create failure reproduced on
  the host filesystem. Lock waits are bounded to five seconds. Symlink, hardlink
  or unsafe lock files are refused; locks are not unlinked after use.
- A uniquely named, exclusively created 0600 sibling receives the complete bytes
  and a file fsync. An atomic create-only hard link publishes `SKILL.md`. Unlike
  replacing a pathname, this cannot clobber a concurrent creator or follow a
  destination link. A collision is accepted only if the existing safe regular
  file already contains exactly the reviewed bytes.
- Ordinary failure removes only staging files created by this invocation. A
  staging-name collision never deletes the pre-existing file. Partial writes,
  failed file fsync and publication failures cannot expose a partial skill.
  Existing working/customized files are never opened for writing.
- SIGKILL before publication may leave a private staging file; after publication
  it may leave an extra hard link to the complete skill. Subsequent installs
  recognize complete identical contents; stale staging files are not swept or
  reused. Directory fsync is attempted after publication. Failure is reported
  without removing the complete file. Newly created parent directories are not
  individually fsynced: this is not a whole-tree power-loss durability claim.

This is a POSIX local-filesystem contract requiring directory descriptors,
no-follow opens, flock and same-directory hard links. Unsupported filesystems
fail closed; there is no truncating or replacing compatibility fallback.
Symlinked home paths/parents and group-writable shared skill trees require manual
resolution. The trusted application installation and same-UID processes remain
outside a sandbox/security-isolation claim; this is not a defense against a
process that can replace the application or arbitrarily rewrite the user's data.

The U1 atomic helper remains unchanged. It intentionally offers replacement
semantics; this skill contract instead needs descriptor anchoring and create-only
publication. U1 cache/reporting behavior is unaffected.

## Callers and architecture boundary

The menu requests the same helper through `request_skill_install()`. A missing
runner, operational enqueue failure, unavailable optional imports or empty enqueue
result uses the offline helper. If importing the service stack fails while the
user enables MCP, offline skill installation is attempted and the service error
is still delivered to the UI; copying skill text does not pretend the server was
enabled. Disabling MCP never installs a skill.

Queued operations accept only the exact client-generated offline script. It has
an explicit `x86_64, aarch64` declaration for this bounded text-copy operation.
The normal `script_environment` / `script_command` path still invokes M1's
`require_script_path`, API checks, host normalization and preamble validation.
No script validation or managed-bundle approval is bypassed. An enqueue-time
ValueError (including M1 ArchitectureError) propagates rather than invoking a
direct retry. Required import, dispatch or architecture failures in a queued job
produce a controlled failed job, with no unguarded retry. Jobs use private unique
temporary directories, retain transcripts and clean up on ordinary completion.

The direct helper installs data only and imports no policy/application modules;
it is not a shell execution route or native-payload qualification. The generated
header authorizes no Bun/native/package execution. M1 policy, M2 route and user-data
protections, M3 revisions/manifests/approved bytes, M4 packaging/native constraints
and M5 Debian package-state handling are unchanged. U2 loader and U3 AppImage
source and tests retain their existing contracts.

All applicable existing packagers copy the entire application tree: DEB
`package.stage`, RPM `cp -a p3/.`, AppImage `cp -a p3/.`, and Arch's source staging
plus PKGBUILD's staged `usr` copy. Consequently both `app/mcp_skill.py` and
`app/mcp_skill/SKILL.md` are included without changing build recipes or guards.
Tests inspect those copy contracts and execute the helper from representative
copied layouts; no actual package was constructed or installed.

## Verification and remaining limits

Host: macOS ARM64, Python 3.13.7. Commands:

```
python3 -B -m unittest dev.tests.test_mcp_skill -v
python3 -B -m unittest discover -s dev/tests -v
```

- 34 focused tests pass: fresh/detected profiles; missing/corrupt/oversized or
  linked bundles; customized/empty/current skills; unsafe directories, file modes,
  FIFO and symlink targets/parents; lock conflicts/timeouts; atomic visibility;
  partial writes, fdopen/fsync/link failures; staging/concurrent-destination
  collisions; directory-sync failure; cross-process concurrency and SIGKILL
  before/after publication; direct/module legacy flags with broken optional
  imports; caller fallback/refusal paths; generated policy eligibility and
  packaging-copy contracts.
- Full host suite: 231 tests run, 211 passed and 20 platform/tool-dependent skips.
  This includes the relevant U1/U2/U3, architecture, script approval, native-build
  driver, packaging and M5 regression fixtures. Package-manager mutations in
  fixtures are mocked; no real package operation is performed.
- The concurrent-process case was additionally repeated 20 times after correcting
  the creation race (240 installations). It checks exact complete bytes, private
  permissions and absence of normal-completion staging files.
- Black checks pass for the new helper/tests, server import block and changed
  caller-method fragments (normalizing existing tab indentation in memory).
  Pyflakes passes on new modules; baseline comparison finds no new findings in
  the three existing caller files. Existing unrelated lint warnings are retained.
  All changed Python files parse using Python 3.10 grammar; this is not execution
  qualification on Python 3.10. `git diff --check` passes.
- Exact Git comparisons verify unchanged library/package behavior, approved
  script tree, architecture and revision policy, loader/AppImage modules, build
  recipes, native source and both skill assets.

Raw host logs are retained in ignored `target/mcp-skill-fallback-20261115/`.
GTK/menu/queue methods are tested from their actual source with optional runtime,
PTY and service boundaries stubbed; no UI, systemd service or real persistent PTY
was launched. No Linux filesystem/runtime requalification, package build,
installation, VM modification, native AMD64 run or emulation occurred. No new
third-party route, release artifact or distribution support is claimed. Historical
ARM64 evidence and qualification limitations remain unchanged. Native Linux/PTY
and built-package lifecycle verification remain separate future qualification;
they do not block this bounded host-verified source milestone.
