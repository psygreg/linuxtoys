# Client/script revision compatibility

Local-only follow-up to M2 `fe169397270cbebb83b16bcae0941300e5fb7888`.
Date: 2026-11-10. No publication, packaging qualification or feature promotion.

## Root cause

M2 hardened the three ARM64 font routes and refreshed their architecture-policy
digests. The independently synchronized repository still supplied their M1
bodies. At M2, `git_scripts_manager.get_available_scripts_dir()` trusted the
presence of a Git cache/timestamp; synchronization pulled/reset its mutable HEAD
in place. That selected tree displaced the bundled snapshot before per-route
architecture checks. Correct digest refusal then removed fonts from search.
The released-client age gate (`updater/version_gate.py`) does not establish
script/helper API compatibility and exempts some source/developer installs.

Retained M2 cache commit: `6b0de756183eb439bc7435c41a23367f37547fc4`.
These raw-byte hashes were rechecked in the native guest; all exactly match M1
`97bde46b60542aaca3b60a4ba57e8210119d6f12`. There are no CRLF differences.

| Script under `p3/scripts/` | Cached remote / M1 SHA-256 | Qualified M2 SHA-256 |
| --- | --- | --- |
| `health/accessibility/atkinson.sh` | `1ba44470f759b1ada886f25bf5bcc649dc704ec2ab06827ddd68c14eda118caa` | `46ed8dd9d204872f5f273dc6545fed33ef5e29802b328a545dcc42d0c7c3f7ec` |
| `health/accessibility/opendyslexic.sh` | `60b91d3b966be7ed19917b160a9220437b2fd6d943d2d23ac163b946f629da43` | `f69a6b990bd00057ca77c1a779e4599967d717cfd67b74afde7fb443ba4b4156` |
| `utils/nerdfonts.sh` | `ddf3c7697269a06a0efbee3a6eb8e88fc683213218bb8fe8fd4ec645425f7de7` | `d9d30e8bb83979de406011d32c65ac62e4a959ea23e48ade4b0e9791005a058d` |

All three eligible ARM64 routes were affected. The old Atkinson/OpenDyslexic
scripts used mutable upstream source URLs without M2's pinned hashes/staging;
old Nerd Fonts used latest-release URLs and installed during its download loop.
The correct fix is coordinated approval, not accepting the older bodies.

## Contract and decision rules

`app/script_compat.py` owns script API **1**, exact bundle verification and the
client-owned revision lock. ISA authority remains `app/architecture.py` and
`architecture-routes.json`; no ISA mappings or eligibility lists are duplicated.

1. `scripts/.linuxtoys-scripts.json` declares schema/API, the exact client
   architecture-policy SHA-256, and every executable/catalog/metadata file hash.
   Its own raw SHA-256 is the revision ID. Line endings are significant.
2. The installed `app/script-revisions.json` explicitly approves revision IDs.
   A remote manifest, tag name, display name or architectures header cannot
   approve content. The current client approves **one** revision; M1/M2 remote
   snapshots are not accepted. Future accepted revisions require client review.
3. Git fetches only `linuxtoys-script-api-1-<preferred-revision>` through the
   existing HTTPS sources. The tag is an address, not proof: the entire received
   tree must match the approved manifest before source selection or promotion.
4. Inventory must match exactly. Missing/extra content, symlinks, special files,
   API/policy conflicts and digest changes fail closed. Git metadata and the
   remote's root `README.md`/`LICENSE` are excluded from hashing; these files are
   explicitly refused as execution targets. Manifest/file size limits apply.
5. Synchronization uses private staging and thread/process exclusion. It never
   pulls/resets the active tree. Failed fetch/validation leaves that tree intact.
   Failed promotion restores it; failed restoration retains the recovery copy.
   There is a brief rename gap: readers can use the qualified bundled snapshot
   or refuse a disappearing file, never authorize an unknown replacement.
6. Source selection validates a compatible cache or the approved bundled tree.
   Offline or missing remote tag: retain those qualified bytes. If neither tree
   passes, refuse. Developer mode skips networking, not bundle/ISA validation.
7. File execution and list hooks validate managed membership before preamble or
   session creation. Generated/local scripts retain the M1 explicit ISA contract;
   this does not let synchronized content bypass bundle approval.
8. The three changed font bodies declare `requires-script-api: 1` and invoke
   the installed validator **before loading their installation libraries**.
   Old M1/M2 clients reject the new digests; missing helpers also cause an early
   refusal. Explicit newer/older/conflicting API requirements are rejected.
   EASY_CLI preserves these original files rather than rewriting `BASH_SOURCE`;
   it never deletes them as temporary scripts. API scripts containing
   `xdg-open` currently require a separately reviewed CLI route.

The capability contract supplements the existing release-age/minimum-client
gate; no exemption or dependency/signature bypass was added. M1 and M2 share
release number 7.9.8, so that number alone cannot identify the required helpers.
Incompatible helper/policy changes require an API bump and revised client
approval. Existing old installations cannot be retroactively changed; this
contract refuses *new requiring scripts*, not all previously released code.

The verifier assumes the installed client and its policy/lock are trusted.
Hashes establish correspondence to reviewed client bytes, not new publisher
signatures or a sandbox against same-user/root filesystem interference. Cached
verification fingerprints include inventory, inode, size, mtime and ctime;
execution rechecks the selected file's raw digest.

## Local preparation and safe future rollout

These steps prepare review artifacts, not authorization to publish:

```sh
# Review script changes and ISA declarations first. Refresh existing routes only.
python3 dev/refresh_architecture_routes.py
python3 dev/prepare_script_rollout.py --write
git diff -- p3/app/architecture-routes.json p3/app/script-revisions.json p3/scripts
python3 dev/prepare_script_rollout.py --check --export /tmp/NEW-approved-scripts
```

`--write` prepares only the current reviewed source revision; it does not carry
forward older approvals or add architectures. Review the complete source diff,
manifest and lock together. The export includes the hidden manifest. Recheck
the exported bytes in a clean client environment. Do not export build artifacts.

**Maintainer rollout order, requiring separate publication authorization:**

1. Arrange native amd64 regression evidence separately. Assign the actual client
   release version and retain the existing release-age policy.
2. Coordinate/hold the existing automatic scripts sync *before merging source*.
   `.github/workflows/sync-scripts.yml` currently deletes the remote tree then
   copies `p3/scripts/*`: it omits the hidden manifest, targets mutable default
   history, suppresses copy errors and pushes automatically. It cannot publish
   this contract safely as written. This milestone does not change/run it.
3. Distribute the reviewed client with API, policy, lock and matching bundled
   manifest first. Its approved bundled fonts work while the tag is unavailable.
   Legacy caches do not gain permission. No need to expose new scripts to old
   unversioned clients just to establish availability for the new client.
4. In a separately reviewed scripts checkout, publish the exact exported tree
   under the content-addressed tag printed by `--check`. Preserve the legacy
   default branch for older clients; include dotfiles; do not mutate an existing
   tag. Both mirrors must serve identical approved content. Verify through the
   new client before re-enabling any adapted synchronization workflow.
5. Rollback: restore the prior complete **client/policy/bundle pair**, subject to
   its existing minimum-client gate, or explicitly review a same-policy/API
   revision into a new client allowlist. Never retag unknown bytes or relax
   hashes. Promotion failures already retain/restore the previous local cache.
   Fixture tests of multiple accepted revisions do not approve old production
   ARM64 scripts; this prepared production lock has one entry.

No push, publication, remote tag creation or live-service change occurred here.
The new tag has not been qualified on either public mirror. The retained M2
cache is historical evidence, not a claim about today's live upstream HEAD.

## Verification and boundaries

See [machine-readable evidence](script-rollout-evidence.json) and
[native qualification](ARM64-QUALIFICATION.md). Native probes use M2's retained
ARM64 release libraries; no Rust source/dependency changed or new native build
claim is made. No font/package installation was needed in this milestone.

The TCP Git fixture runs only on the guest loopback interface. It exercises
actual clone/checkout, validation/promotion and native frontend search with the
intended source revision, tampered-tag rejection, offline cache and offline
bundle selection. This is not a live-upstream deployment test or a general
network sandbox. GUI runs test Wayland and Xwayland, not standalone Xorg.
Native amd64 remains unqualified; x86 selector/route fixtures are not runtime
qualification. Ubuntu ARM64 packaging qualification has **not** begun.

## Changed files

- Policy/approval: `p3/app/architecture.py`, `architecture-routes.json`,
  `script_compat.py`, `script-revisions.json`,
  `p3/scripts/.linuxtoys-scripts.json`.
- Source selection/execution: `p3/app/git_scripts_manager.py`, `compat.py`,
  `architecture_cli.py`, `library_loader.py`, `easy_cli.py`.
- Existing font guards only: `p3/scripts/health/accessibility/atkinson.sh`,
  `opendyslexic.sh`, `p3/scripts/utils/nerdfonts.sh`.
- Preparation/tests: `dev/prepare_script_rollout.py`,
  `dev/tests/test_script_compat.py`, `dev/tests/native_script_rollout_smoke.py`.
- Documentation/evidence: this file, `dev/ARCHITECTURE-POLICY.md`,
  `ARM64-ASSESSMENT.md`, `ARM64-QUALIFICATION.md`,
  `arm64-qualification-evidence.json`, `script-rollout-evidence.json`.
