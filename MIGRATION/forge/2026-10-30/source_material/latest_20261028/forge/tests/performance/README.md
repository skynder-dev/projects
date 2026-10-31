# Forge Performance focused native regression package

Prepared 2026-10-24. This is the cumulative product candidate. Native execution must use fresh private copies of this candidate; preserved originals and individual sealed candidates are read-only.

## Result and limits

- 46 native PowerShell cases are prepared, **not run**. Neither `pwsh` nor
  `powershell` is installed in this cloud workspace. Nothing was installed.
- In the preserved isolated preparation, 14 Python supervisor contract controls passed. They test process cleanup and receipt
  acceptance only. They do not model or claim to test Forge aggregation.
- The preserved isolated local invocation correctly reported
  `BLOCKED_NATIVE_RUNTIME_UNAVAILABLE`, `native_executed=false`, and identical
  before/after originals, private copies and test inputs. It is not a native pass.
- No model, network, provider, PC, Library, Supabase or remote-write action is used.
- Native parsing, full app/WPF execution, real CSV ingestion, receipt/package
  authority and broader regression all remain unverified. No publication/CI claim.

Historical individual pin snapshots and invocation records remain preserved outside this cumulative candidate. They do not establish execution against these combined bytes. Use the supplied `PerformancePins.portable.json` and the cumulative source manifest.

## Files

- `Test-ForgePerformanceMetrics.ps1`: actual native suite, no Pester dependency.
- `PerformanceFixtures.json`: synthetic case rows and fixed UTC clock.
- `dependencies.json`: exact actual functions and explicitly disclosed doubles.
- `supervise_performance.py`: pins, safe private copies, invocation and acceptance.
- `process_supervisor.py`: supervised process tree, inherited from the existing
  focused harness with one local hardening: close residual POSIX descendants even
  after ordinary/nonzero parent exit. Its original file was not modified.
- `test_supervisor_contract.py`: synthetic orchestration controls, not app behavior.
- `PerformancePins.*.json`: immutable provenance/pin snapshots. A prior snapshot is
  intentionally not overwritten if tests or candidate sources change.

## Actual native scope

The suite asks PowerShell's native Parser for FunctionDefinitionAst nodes from
pinned complete source files, checks native parse errors, requires exactly one
matching function per requested name, then loads each actual Extent.Text. It never
loads module top-level initialization or starts the Workbench. Twenty actual
functions are loaded from four source files, including actual link reconciliation,
amount validation, normalized date handling, royalty aggregation, Home metrics,
per-product Performance computation, formatters, localization and rendering.

All four source files must come from this candidate under `forge/app/Merch_Forge_A5_Current`. LocalCore and Pipeline contain the ordered reviewed product deltas; Workbench and Localization retain their frozen v2 bytes. Do not fall back to the historical CI snapshot or individual partial candidates.

Explicit doubles:
- Receipt authority accepts only a synthetic fixture-owned boolean. This does not
  establish actual package, receipt or cryptographic authority.
- State read returns in-memory synthetic state; Amazon profile returns null.
- UI controls are plain Text objects. Actual rendering function executes without WPF.
- A clock-only rendering adapter calls the retained actual insights ScriptBlock
  with fixed `2026-10-24T12:00:00Z`; it does not replace aggregation logic.
- Unexpected external/mutation command names throw. This is a focused test boundary,
  not a hostile-code sandbox. The caller must trust and review the pinned source.

## Cases

1. USD 10 + EUR 20 stay separate, never become 30 dollars.
2. USD 20/two units ranks above JPY 1000/one unit; equal-unit ties use product keys.
3. Unverified 999 royalty and 99 units are excluded and counted unknown; incomplete
   units do not rank. Unverified receipt rows remain unlinked/unknown products.
4. UTC day 29 is in 30 days, day 30 out; day 89 in 90 days, day 90 out. Day 6 in
   seven days and day 7 out. Future and invalid dates are excluded and counted.
5. Fractional, refund and zero values are preserved. Refund/netzero rows remain
   observed transactions. These tests make no completeness/no-sales inference.
6. Aggregate Home metrics equal summed per-product metrics across 7/30/90 days,
   including per-currency buckets and unknown/observed-row counters.
7. Each units/royalty field is separately tested for missing, null, blank, NaN,
   positive/negative infinity, out-of-bound, unreadable, array, object, boolean,
   missing verification, false verification and string-true verification inputs.
   Singleton numeric and verification arrays must not unwrap into scalar proof.
   Singleton currency/date arrays must remain unknown/undated.
8. Legacy v1 rows with explicit true numeric flags remain valid. Legacy source
   hash/ordinal and product linkage without numeric flags remain unknown; the
   row object and its serialized UTF-8 bytes are preserved after reconciliation.
   Source identity is not numeric proof and receipt authority remains a double.
9. A native es-ES culture probe validates invariant numeric parsing and formatting.
10. Actual EN/RU/ES rendering preserves true currency codes and fractional values,
   uses localized unknown labels, and does not fabricate a dollar symbol.

## Pinning and later invocation

Use the supplied `PerformancePins.portable.json`, with repository-relative provenance paths, from the repository root. Any later source change requires a new independently checked cumulative pin manifest. The generic `pin` helper can select a base fallback and is not the approved source-selection path for this cumulative candidate.

PowerShell Core 7.5+ with explicit DateKind String is mandatory. Unsupported
hosts refuse with a non-pass receipt. Fixture loading uses module-qualified
ConvertFrom-Json -DateKind String, with no compatibility fallback.

When an authorized POSIX environment already has that native PowerShell, run:

    python -B forge/tests/performance/supervise_performance.py run --pins forge/tests/performance/PerformancePins.portable.json --output-parent /absolute/private-test-root --timeout 90

The runner provisions a fresh 0700 owner-owned root with independent empty native
run, suite copy, source copy, HOME and temporary directories. Every source/test is
copied exclusively and rehashed against pins. Originals and copied inputs are
rehashed again after every outcome. It does not reuse fixtures or delete artifacts.
The selected default executable is `pwsh`; no toolchain auto-install or fallback.

The bundled supervisor intentionally supports POSIX owner-private provisioning
only. Windows native execution needs a separately reviewed supervisor establishing
owner-only ACLs, fresh local roots, an owned process job and these same checks. The
`.ps1` itself does not claim to provision ACLs. Do not bypass that precondition by
running into a shared, existing or redirected directory.

## Mandatory acceptance

A native PASS requires all of the following simultaneously:
- The original and copied source/test hashes match the pins before and after run.
- Zero native process exit code, before the configured timeout.
- Fresh nonempty valid receipt in the exact owned run root, correct schema, run
  nonce, roots, fixed clock, test/pin/fixture hashes, actual function list and runtime.
- Exactly all 46 named cases, in their expected order, with PASS and no errors.
- No boundary activity, unchanged synthetic preservation sentinel and no unexpected
  native-run files.
- A supervisor invocation receipt with `PASS_FOCUSED_NATIVE_ONLY`.

Timeout is FAIL even if output or a stale receipt says PASS. The supervisor kills
the entire owned process tree. Nonzero exit is FAIL even if a receipt says PASS.
Zero exit without a receipt, empty/malformed receipt, foreign nonce, missing case,
wrong hash, unsupported native runtime, unexpected side effect or final integrity mismatch is FAIL. Missing
PowerShell is BLOCKED, not skipped success. Do not accept printed text alone.

The supervisor selftests exercise malformed/empty/missing receipts, mismatched
nonce/source/function/case identity, incomplete cases, explicit native FAIL,
nonzero exit with printed PASS, timeout descendant termination, ordinary-exit
residual descendant termination, and a complete synthetic metadata control.
