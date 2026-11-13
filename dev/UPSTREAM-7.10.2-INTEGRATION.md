# Selective 7.10.2 compatibility integration

2026-11-13. Baseline: `f39d2c07cee56831b3a45c0ede57a45a3a6dfc78`.
This is a compatibility backport, not a broad release merge or version bump.

Pinned upstream sources, retrieved read-only with explicit user authorization
into a new ignored review repository:

- Release: `efbaaca4a6d0e8f7949f46209c6bef244b22af18`.
- Dual imports: `16daa9780c31460972395a25fa87697ce019c4c9`.
- Repository-call case: `8ae64f14ed9de4f0c745a387a85f875fa3229171`.

The commits form the direct chain from the retained 7.10.1 source
`7d291e3ac54f67e57ddc0a9a58a6fb381c37e1cc`. Exact functional patches and
source provenance are retained under `target/upstream-7.10.2-review/`.
The previous review repository and all historical evidence were not modified.

## Applicability and implementation

Upstream changes `atomic_io` imports in both the loader and AppImage catalog.
Neither local module has that import or needs the upstream writer migration.
No atomic writer, loader, generated-script or cache behavior was imported.

`library_loader.py` is byte-identical to U2. Its package-relative imports and
trusted caller-root bootstrap remain, and the architecture guard still precedes
command body reading/preamble construction. All four qualified entry modes
are regression-tested: direct file, `-m app.library_loader`, package API and
standalone API with the app directory on `PYTHONPATH`.

The local AppImage updater has a separate reproducible defect: direct-file
resolution reaches M1's package-relative architecture imports without a package
context and fails. The same fixture succeeds through package import. The only
production change is to **three lazy architecture imports** and a direct-mode
bootstrap in `appimage_catalog.py`:

- Package imports remain relative and lazy.
- Direct mode derives the trusted `p3` root from the resolved source `__file__`,
  prepends it to the import search path, and uses qualified `app.architecture`
  and `app.architecture_files` imports. Cwd, `SCRIPT_DIR` and bare sibling module
  names do not supply those guards.
- The real ISA selector and ELF/payload validator remain mandatory. Import
  failures propagate through the existing CLI error path; there is no fallback
  to an unguarded download or installation.
- URLs, cache writers/formats, release resolution, public signatures, output
  metadata, usage status 2 and ordinary failure status 1 are unchanged. Existing
  refused downloads may remain in the caller's temporary output; this patch
  does not change cleanup policy or perform integration/execution.

All real caller files were inspected: `appstream_cache.py` (feed discovery),
`app_page.py` (repository availability), `appstream_runner.py`, `mcp_server.py`
and `tui/runner_helper.py` (package APIs), and `libs/packages.bash`
(`pkg_appimage_update` directly invokes the file). MCP's direct entry already
bootstraps the package root; no protocol or caller changes are needed.

## LATENCYDEVIL: no local script change

There is no physical `latencydevil.sh` or `LATENCYDEVIL.sh` in the approved
bundle. The target is `lists/latencydevil/latencydevil.json`, whose entry name is
`LatencyDevil`, normalized to repository ID `LATENCYDEVIL`. `call_script` first
performs case-sensitive physical `find -name`; its repository fallback passes
the supplied ID to the loader, which already applies `.strip().upper()`.
The Rust repository-ID function also uppercases its result. Lowercase, mixed
case and uppercase calls therefore identify the same entry. Upstream's case
substitution does not correct a demonstrated local mismatch.

`pdefaults.sh` and the LatencyDevil catalog route remain qualified for x86_64
only; tests confirm AArch64 refusal. These are policy-input checks, not AMD64
execution or emulation. The script bytes, SHA-256 declarations, architecture
policy, manifest and approved revision are unchanged. No approval regeneration
or remote revision acceptance occurred. Revision remains
`083138ce4b55ccf533a215c995bf27db25eae80d60b487150ae710f14d245e5f`.

## Validation and preservation

Host: macOS arm64, Python 3.13.7. **No new Ubuntu/GTK/Rust native qualification**
is claimed. The prior U2 native evidence remains unchanged and covers its exact
committed source; this AppImage fix needs a separately authorized native run.

- **10 new tests passed**: AppImage package/direct/module execution with fake
  HTTP and real policy, native selection, foreign-name/asset/payload rejection,
  malformed payloads, usage status, missing required guards, hostile import
  search paths, case-sensitive physical lookup, normalized repository lookup,
  real bundle validation and unchanged architecture restrictions.
- **122 existing regressions passed**, including the 12 focused U2 loader tests
  covering all four invocation modes and U1 reporting/atomic-write safeguards.
- **14 additional host subprocess loader probes passed** using the real policy
  and approved bundle. CLI exec handoffs were intercepted before Bash; API
  rejection precedes the loader body read and preamble. The guard itself reads
  a foreign architecture header; unapproved-revision API inputs are refused
  before any target-body read. No installer bodies ran.
- Black checks cover the complete new test and changed AppImage line ranges;
  full new-test lint (88-column limit), fatal lint and in-memory compile/AST
  checks passed. Static AST comparison confirms only the bootstrap/import
  dispatch changed in production. Script preparation `--check` and Bash syntax
  checking passed without generating artifacts or rewriting approvals.
- **80/80** protected M4B files, **2021/2021** original evidence entries,
  **2198/2198** pre-existing target artifacts, all **17** protected policy/lock/
  version files and **470** script/library paths matched their approved hashes.
  Original M4A artifact SHA-256 remains
  `83173db3b42d8ef966b6bde02f064beb42ee71b4593bfd727a3fefefdb862f04`.

No report was submitted, live feed queried, payload executed, installer invoked,
package operation/build performed, VM/system/service changed or workflow run.
Only upstream source retrieval used the network. No push/publication/deployment
occurred. Git history is retained with one new local source commit; prior
attribution rewriting and its documented original-ref/checkpoint caveat remain.
No historical qualification claims or recovery artifacts were rewritten.

Exact committed files: `p3/app/appimage_catalog.py`,
`dev/tests/test_7102_compatibility.py`, and this report. Detailed logs, commands,
source diff, before/after preservation and final commit verification are kept in
the new ignored `target/upstream-7.10.2-review/` directory. Remaining limits:
HTTP is mocked, optional GTK/native catalog consumers are inspected rather than
launched, repository materialization is stubbed in normalization tests, and real
AppImage installation/update/runtime remains unqualified by this host-only run.
