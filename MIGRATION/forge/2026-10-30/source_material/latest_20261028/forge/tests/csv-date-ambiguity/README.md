# CSV slash-date guard: native acceptance contract

Status: PREPARED, NATIVE PARSING AND EXECUTION NOT RUN. No PowerShell host is installed in the preparation workspace. No runtime was installed and no application logic was emulated in Python.

## Product behavior

The date decision changes only in Get-CsvSlashDateOrder. A narrowly matched Test-KnownUiMessage recognition rule preserves the two exact app-authored errors in the existing Show-Error path even when optional translation data is absent; no UI is added. The actual importer invokes it after a read-only, byte-bound CSV snapshot and before reading or mutating application state. There is no existing per-import date-format selector or source-SHA-bound explicit choice.

- Reject a slash-date token with two different valid calendar meanings, regardless of delimiter, PC locale, or other rows. The error gives both meanings and explicitly says no import was performed. This is ambiguity, not file corruption.
- Reject conflicting valid DMY and MDY evidence rather than choosing either. The error gives concrete examples.
- Equal month/day values do not create ambiguity or force an order.
- Validate the actual calendar date under both existing native parser orders. Invalid dates are not evidence; existing undated-row behavior remains.
- Match optional inner whitespace allowed by the native parser and conservatively inspect compact or unsupported time suffixes. A malformed ambiguous-date prefix may therefore be refused even when the full value would otherwise be unreadable. Time-format asymmetry cannot authorize a date interpretation.
- Clear ISO, year-first, dotted, and genuinely unambiguous slash dates retain existing parsing. No source file is rewritten.
- Valid exact-source reimports keep existing idempotence. A previously imported ambiguous source is refused unchanged; its historical interpretation is not treated as fresh authorization.

The legacy broad research self-test is updated only to replace its synthetic ambiguous input with an explicit ISO date for the column/money test, and replace unsafe delimiter-guess assertions with safe/refusal assertions. The rest is unchanged.

## Optional explicit format choice: assessed, not added

No dateOrder parameter or new UI is added. An unwired optional parameter alone would not give the user an accessible choice or define safe exact-source reimport behavior. A future extension should bind the explicit DMY/MDY decision to the captured source SHA, preserve that decision and normalization history, reject conflicting valid order evidence even with a selection, require deliberate approval for changing a saved source interpretation, and keep Cancel write-free. An existing UI could then pass that explicit choice without modifying the original CSV. Until that separate workflow exists, the error requests a separate report export with verified yyyy-MM-dd dates, not edits to the original file.

## Native suite

Test-ForgeCsvDateAmbiguity.ps1 reuses the reviewed Performance native AST extraction, source/test pinning, fresh receipt and fixture-preservation mechanics. It executes actual CSV capture, date parser, overlap detection, normalization, source revalidation, both importer entrypoints, and their actual dependencies. No alternative business implementation is supplied.

The exact ordered 40-case/22-function identity contract is in CsvDatePins.json. Cases cover comma/semicolon ambiguity; unrelated row non-proof; conflicting valid orders; equal month/day; calendar-invalid inputs; leap day; ISO/year-first/dotted forms; AM/PM, whitespace and compact suffixes; locale independence; actual importer rejection before state reads; accepted normalization; overlap Cancel and approval; unchanged exact/renamed reimport; legacy ambiguity refusal; saved-source revalidation Cancel; outer file-dialog Cancel; actual message-recognition/human-error mapping and rejection of broad-prefix/altered-tail errors.

Boundaries are explicit in CsvDateDependencies.json:
- Application state read/write is replaced with isolated synthetic JSON fixture persistence, including detached reads and write counters. Real state-store migration, locking and atomicity are not covered.
- Actual Test-KnownUiMessage, Test-UiTextMessage and Get-HumanErrorMessage functions are tested with empty optional translation tables. The unchanged Show-Error branch is statically inspected; its WPF dialog is not invoked. UI text, errors, confirmations and refresh are synthetic objects/queues/counters. The file-dialog cancel case doubles only its dialog construction. No WPF claim.
- Publication receipts are empty; an unexpected receipt-authority call fails. No package or receipt-authority claim.
- Unexpected model, process, network and command-level mutations fail. This is a regression harness, not a hostile-code sandbox.

## Required external supervision

Do not run against original application files or user state. Reuse the existing reviewed supervisor's private staging and owned-process-tree control; no new launcher is supplied here.

1. Verify the sealed delta and all supplied source/test/fixture/dependency/pins hashes.
2. Stage fresh ordinary non-symlink/non-reparse copies under a private supervisor-owned root. On Windows, verify restrictive ownership/ACLs. Preserve and inventory originals. The six source files must come from the candidate Core and canonical-v2 Workbench, Media, BriefApproval and Localization, plus candidate MessageLocalization, never historical CI substitutions.
3. Select an already installed stable PowerShell Core 7.5+ supporting ConvertFrom-Json -DateKind String. No installation, alternate parser, legacy-host fallback or execution-policy override.
4. Invoke the test in a fresh empty RunRoot outside PackageRoot, with exact PinsPath and a fresh 32-character lowercase-hex RunId. Apply a 90-second wall-clock deadline to the entire owned process tree; ensure descendants are quiescent after every exit.
5. Accept only exit 0 plus a newly produced complete receipt.json, schema forge.csv_date.native_receipt.v1, status PASS, null error, matching nonce/canonical paths/input hashes, exactly the ordered 40 PASS cases and 22 actual function identities in the pins, zero failed cases, and matching before/after source hashes. Independently rehash every supplied input, preserved original, and generated input CSV after quiescence. Verify the sentinel independently. All 22 generated input CSV files must retain their recorded hashes.
6. Timeout, nonzero exit, missing/stale/partial/wrong-run/wrong-shape/changed-input receipts, unsupported host or failed isolation are never PASS. Write a fresh supervisor failure/blocker receipt even if native setup fails before its own receipt can be emitted.

Source-only preparation/reconstruction checks do not prove any native case passed. Full Windows startup, WPF clicks, actual records and financial values remain untested.
