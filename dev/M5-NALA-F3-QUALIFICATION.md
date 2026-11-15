# M5 Nala and F3 qualification

Baseline: `ef5eb1a7ddbe8c8103f174620786f5cba05bbe43`, branch
`codex/u1-atomic-reporting`. Native evidence was collected on 2026-11-14–15.
The committed M5 assessment and candidate evidence were reread; the 227-route
inventory was neither repeated nor changed.

**Neither route is qualified or enabled.** Nala has two unresolved package-state
defects demonstrated with real native dpkg over isolated status fixtures. Its
actual installation/removal cases have not completed. F3 additionally retains
an independent, unapproved ARM64 post-hook. No application, shared library,
architecture declaration, script manifest or revision approval was changed.

## Actual inputs and native checks

The existing VM is Ubuntu 26.04.1 LTS, AArch64, Linux `7.0.0-43-generic`, Python
`3.14.4` (GCC 15.2.0). Host-only tests use the existing macOS arm64 Python
`3.13.7` at `/opt/anaconda3/bin/python3`. There was no AMD64 execution/emulation.

| Actual Ubuntu package | Size | SHA-256 | Result |
| --- | ---: | --- | --- |
| Nala `0.16.0`, `all` | 148792 | `7b9273a4c6b1091f9132b707f11a7f12679ae0b27e57004c619d18cf2b16ff7d` | Unchanged M1 accepts actual DEB; no direct ELF; 117 members. |
| F3 `9.0-1build1`, `arm64` | 51010 | `4beeec43517f1863e9c1b9cbc7908574d98c52384d15a5776ff42418b042dfdf` | Unchanged M1 accepts actual DEB; five direct AArch64 ELF files; 31 members. |

All 149 retained archives (43,365,890 bytes) were reverified by exact size/SHA-256
and linked to seven original Ubuntu Packages indexes authenticated with the
existing archive keyring. The earlier direct-ELF scan found 597 ELF64 machine-183
files in this closure. This is not an exhaustive audit of embedded/bytecode data.
The signed UbuntuBase 26.04.1 ARM64 input is 35,092,106 bytes, SHA-256
`5a1906794ced63a71a8119c3f211ef5f0bbe0a243001b4bbd41fdf80c5b219fd`;
its checksum signature validates under existing Ubuntu CD key
`843938DF228D22F7B3742BC0D94AA3F0EFE21092`.

The live VM metadata cache had rotated. Preparation refused the mismatch before
package operations. Exact original index contents were then recovered from
official Ubuntu snapshots using the previously authorized official-metadata
retrieval exception. Original uncompressed hashes/lengths, signed InRelease
entries, compressed hashes and gpgv signatures were independently checked. No
original checksum inventory was regenerated, no package version was silently
substituted, and the failed preparation remains retained. URLs and signature
receipts are in `snapshot-recovery.json` under the private qualification root.
The immutable offline input manifest SHA-256 is
`e54ad1f6e5219997978d870848c35a8eff7a65b33130259f47dacc0681ccbed9`.

Nala's native dependencies include apt/python3-apt, Python 3, anyio, httpx,
pexpect, rich, tomli, typer, typing-extensions, python3-debian and recommended
socksio. Its retained empty-status APT plan has 87 packages. Maintainer scripts
use py3compile/py3clean; `/etc/nala/nala.conf` is a conffile. F3 depends on libc6
`>=2.38`, libparted2t64 `>=3.1` and libudev1 `>=183`; its plan has 15 packages and
no maintainer scripts. These are Ubuntu-resolved availability/compatibility
checks, not successful Nala runtime or full lifecycle qualification.

The installed M4A native catalog extension was reused without a build; its
SHA-256 is `acffca8807cbda8810340bc404496194b63eb12583550161f489def94da86944`.
The real Rust catalog and central policy omit Nala/F3 on the exact baseline.
A private Nala-only eligibility experiment goes through the existing
`prepare_script_rollout.py --write`/`--check` process. Its exact local revision is
`4af7e43600bdfd43d5f8a88a3fcde0f9fe83385fa1be97e3429073a434679d9e`;
Nala appears in the real native catalog, F3 remains absent. This is a disposable
test input, not production approval or a remote accepted revision. Its source
tar SHA-256 is `74f7c9c20afd0c8fac79617aa86b7e7df98e319e69d685bd23308c3461207ca4`.

## Production path and blockers

The reviewed path is source-bound catalog eligibility → real catalog parser →
native installer materialization → loader architecture/override checks → exact
script-bundle compatibility → shared `pkg_install` → architecture metadata and
APT dependency-plan preflight → askpass/sudo → locked APT transaction → transmap
→ action registry → generated removal or automatic reversal. No central guard,
privilege helper, approval or body is replaced by a successful stub in the
planned lifecycle test.

APT retains archive signature and payload hash enforcement. The generic native
path checks architecture metadata/dependency plans; this task does not claim a
new per-archive M1 inspection inside APT. Package removal uses the existing
`apt-get remove -y --allow-unauthenticated` branch, with no new acquisition claim.
Removal deliberately does not purge conffiles or autoremove dependencies.
Transmap reversal records explicit package effects, not a complete package/
filesystem snapshot; a partial install before recording is not guaranteed to
be fully reversed. The generated removal script stops on failure before pruning
the action registry. No stronger rollback guarantee was inferred or added.

Two real native dpkg fixture results block Nala promotion:

- `deinstall ok config-files` makes `dpkg -s` succeed. `pkg_exists` therefore
  reports Nala installed, and `pkg_install` can skip a requested reinstall after
  removal retained its conffile.
- `install ok unpacked` also makes `dpkg -s` succeed. Installation can skip before
  `interrupted_apt_guard` runs, leaving the interrupted state incomplete.

Both tests express the required behavior as expected failures. They are tracked
defects, not waived passing guarantees. No production helper fix or script
approval change was made on fixture evidence alone.

F3's separate inline documentation/browser hook has SHA-256
`c87a49ca4b0b79b5bd0b8067717e43ae278677c49db059f8bae1a727c9c8f12c`
and remains approved only for x86_64. The hook and catalog refusal were exercised
separately on native ARM64, including the private Nala-only experiment. No F3
hook, installer, f3probe/f3fix/device operation or browser launch was executed.
Actual ARM64 Ubuntu package availability cannot approve this local route.

## Disposable execution attempts

The private VM root is `/home/ta/linuxtoys-m5-nala-f3-ef5eb1a7/`; ignored host
copies/logs are under `target/m5-nala-f3-qualification/`. All earlier drivers,
results and rootfs copies remain intact. SSH cannot authenticate noninteractive
sudo; the user executed pinned controllers in their existing root terminal.

1. Docker V1 stopped before bootstrap. Its collector then attempted `docker exec
   dpkg --audit` on a stopped container, masking the initial failure. No package
   operation ran; the empty results list is not a passing test.
2. Docker V2 corrected diagnostic collection. Both `/bin/sleep` and `/bin/bash`
   failed before bootstrap. Kernel audit independently records AppArmor exec
   denial from `snap.docker.dockerd` to `docker-default`, `info="no new privs"`,
   at 2026-11-15 00:52:50 UTC. No binary/parser bug was established. No AppArmor
   profile, service or no-new-privileges setting was relaxed.
3. Authorized existing Bubblewrap 0.11.1 V3 demonstrated six separate namespaces,
   NoNewPrivs=1, effective/permitted/inheritable/ambient capabilities `0xCB` and
   `bwrap//&unpriv_bwrap (enforce)`. Its bounding set was `0x1ffffffffff`, broader
   than required `0xCB`; the strict probe refused bootstrap. Zero package
   operations ran. Its different AppArmor/seccomp boundary is not represented as
   identical to Docker's.
4. V4 retained all isolation requirements and used existing signed-base setpriv
   before probe/bootstrap to drop the bounding set to the five required caps.
   It failed with `setpriv: apply bounding set: Operation not permitted` before
   bootstrap; UID/GID mapping checks and all eight package cases were not
   reached. No host-policy cause beyond this observed EPERM is established.
   The user's second invocation refused the existing `gnupg-driver-v4` directory
   before further setup. That retry is user-reported; the first failure was
   independently read from retained VM summary/command logs. No retry directory,
   result or recovery material was deleted or overwritten.

The bounded procedure uses only new private rootfs/input/result directories,
network namespaces, no host production mounts/sockets/devices, NoNewPrivs,
private minimal `/dev`, read-only `/proc`, empty `/sys`, and newly named job-only
cgroups with 2 GiB memory, no swap, 256 PIDs and 200% CPU. Existing controller
configuration is not edited. New groups must empty/remove on exit. Rootfs copies
remain beneath root-only parents. These controls have not been weakened to
obtain a package test result.

## Tests and verification

| Evidence | Actual result |
| --- | --- |
| Existing regressions: guarded 122-test selection plus 10 upstream-7.10.2 compatibility tests | 132 passed on macOS and 132 passed natively. |
| Focused candidate fixtures on macOS | 8 passed, 4 native-dpkg cases skipped. |
| Focused candidate fixtures on Ubuntu AArch64 | 10 passed, 2 expected failures described above. |
| Actual native Nala lifecycle, removal, reinstall, rollback and adversarial APT cases | Not completed; isolation preflight blocked. |
| Foreign architecture, missing/malformed architecture metadata, empty transaction interruption, reversal failure | Offline fixtures exercised; not native APT fault/lifecycle results. |
| Real APT checksum corruption, missing dependency, malformed signed-index contents, pre-unpack SIGTERM and rollback failure/retry | Prepared eight-case harness; not executed because isolation setup failed. |
| Black, Pyflakes, AST/syntax, Bash syntax, whitespace | Passed for new test sources and retained controllers. |

Reproducible commands (from repository root, existing interpreters only):

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 target/m5-nala-f3-qualification/run_regressions.py
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 -m unittest discover -s dev/tests -p test_7102_compatibility.py -v
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 -m unittest discover -s dev/tests -p test_m5_candidate_failures.py -v
/opt/anaconda3/bin/python3 -m black --check dev/tests/native_m5_candidates.py dev/tests/test_m5_candidate_failures.py
/opt/anaconda3/bin/python3 -m pyflakes dev/tests/native_m5_candidates.py dev/tests/test_m5_candidate_failures.py
git diff --check
```

Native runs use `/usr/bin/python3`, private HOME/XDG/TMP paths, timefix disabled,
denied-IP LD_PRELOAD and dead-loopback proxies from retained `native-env.sh`.
The existing-regression runner blocks sockets, package/build/root/network
commands and local Git fixture commits. Its exclusions and per-test output are
retained. No Rust rebuild/test compilation or package generation was performed;
the actual existing Rust extension/catalog was exercised read-only.

The exact final native commands, run through `bash "$q/native-env.sh"`, were:

```sh
q=/home/ta/linuxtoys-m5-nala-f3-ef5eb1a7
/usr/bin/python3 "$q/run_regressions.py"
/usr/bin/python3 -m unittest discover -s "$q/source/dev/tests" -p test_7102_compatibility.py -v
/usr/bin/python3 -m unittest discover -s "$q/source-fixtures-current/dev/tests" -p test_m5_candidate_failures.py -v
```

Both native source copies match all 986 baseline tracked file hashes. Additional
test/native-extension files are explicit test inputs, not changes to those
baseline files. All 132 existing native regressions and the 12 focused cases
were rerun after the background environment drift described below, with the
same results. No monitored VM records changed during that final regression run.

## Preservation and environment incident

The final local checks matched 986/986 baseline tracked files, 17/17 protected
policy/manifest/lock/dependency/version files, 470/470 script/library/bundle files,
80/80 assessment-protected M4B files, 2021/2021 original U1 evidence entries,
2325/2325 earlier M5 evidence entries and 3450/3450 task-preexisting evidence
files. The source manifest exactly equals the baseline mapping. The original
M4A DEB and recovered historical M4B records independently match their approved
lengths and hashes:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| M4A DEB | 8554000 | `83173db3b42d8ef966b6bde02f064beb42ee71b4593bfd727a3fefefdb862f04` |
| M4B completion record | 833 | `b1daa68ac265ad596a29005b667af024d5a9f3375d5bdb4dbe5c1c051dd37983` |
| M4B checksum inventory | 6360 | `819eb5a4c9a62b380a54267966c29f749e72a24ce0e79aa2229ad03f51d8651d` |

Before the qualification-record commit, HEAD, semantic index, branch/tag values
and reflogs matched task start. Codex-managed capture/checkpoint refs rotated;
the exact four-ref before/after delta is recorded in the accompanying evidence
JSON. No agent ref-update/history-rewrite command was issued. These runtime refs
are not covered by an all-refs-unchanged claim. An initial comparison used short
instead of full reflog selectors; comparison with the original full selector
format confirms the reflogs match. That preliminary output remains retained.
The rewritten attribution history and the earlier missing-checkpoint caveat
remain intact; this work does not repair or reinterpret that history.

**The VM preservation gate did not fully pass.** Of 2294 monitored records,
2290 match content and metadata exactly. Four differ:

- `/var/lib/apt/extended_states`: identical size/hash/ownership/mode; mtime changed.
- `/var/lib/dpkg/status`: 1,795,441 → 1,795,448 bytes; SHA-256
  `11041264ba13aeac6b4657c431e05b2678f477e0171c07886a067aa8321379c2`
  → `d9d24a2460663cb01b4053d0f5a4d670fc08725fdd42d20a80029ddc448fb88a`.
- `/var/log/apt/history.log`: 21,603 → 22,264 bytes; original prefix hash matches.
- `/var/log/dpkg.log`: 228,964 → 235,305 bytes; original prefix hash matches.

APT/dpkg logs record `/usr/bin/unattended-upgrade` at **06:41:52–06:42:17 CET,
2026-11-15**. The independent systemd journal records the scheduled
`apt-daily-upgrade.service` at 05:41:48–05:42:19 UTC. Seven glibc packages
(libc-gconv-modules-extra, libc6, locales, libc-dev-bin, libc-bin, libc6-dbg,
libc6-dev) changed `2.43-2ubuntu2.4` → `2.43-2ubuntu2.7`; python3-pil changed
`12.1.1-2ubuntu1.4` → `12.1.1-2ubuntu1.5`. Logs therefore identify a background
system update independently of the qualification controllers, all of which
record `bootstrap_attempted: false`. Its wider filesystem/runtime effects were
not exhaustively inventoried. No rollback, host package operation, timer/service
change or system repair was attempted by this task. Existing application/user
records still match, and native dpkg-query confirms Nala/F3 are absent on the
VM host; nevertheless the VM is no longer an identical pre-task environment.

V4 reports existing Docker container IDs/configurations/image IDs, AppArmor
enabled state and existing resource-controller configuration unchanged, with
zero cleanup errors. Private failed-attempt rootfs and all recovery/incident
material remain retained. No candidate package was installed anywhere by these
attempts; there was no production data operation or network report/publication.

## Decision and remaining work

This commit records completed investigation, offline regression tests and a
guarded but **unexecuted** native lifecycle harness. It does not qualify either
route. Stop further sandbox variants rather than relaxing AppArmor,
NoNewPrivs, capability bounds, mappings or central architecture enforcement.
A future authorized pass needs a suitable disposable isolation environment,
review of Nala's two package-state defects through the exact script-approval
process, and all eight actual lifecycle/fault cases. F3 additionally needs its
independent client hook review; this task grants no such approval. Preserve the
drifted VM and original evidence as observed, without treating new logs or
matching rewritten inventories as proof that its initial state was preserved.
