# Local draft history and market-aware sales identity

**Candidate only; native PowerShell/WPF execution NOT RUN.** This isolated 2026-10-25 derivative preserves the sealed 2026-10-24 composition and its date, numeric/currency, coverage and package-authority repairs.

## Product changes

- Existing History tab displays detached copies of actual saved draft revisions and local review history. Restore uses the existing Edit → Save workflow: confirmation only stages historical content; Save appends a NEW unapproved revision with source ID/hash. Nested production specifications, arrays and timestamp strings are preserved. No manual idea-creation workaround is added.
- Cancellation, stale source, missing/ambiguous/corrupt historical source, confirmation-time navigation and rejected state writes preserve saved records. Publication-dirty state is not cleared before successful commit.
- Revision append and invalidation of current brief approval, artwork acceptance, owner decision, checks, listing context and package readiness occur in one existing optimistic state-store write. Original creative revisions, historical review payloads, publication receipts, artwork file references and package records remain; no artwork or archive bytes are changed. Failed post-commit UI reopening cannot leave accepted/current-ready flags behind.
- CSV normalization preserves explicit channel/marketplace and their raw values. Reconciliation uses the existing receipt compound identity. An explicit wrong channel/marketplace never falls back; missing dimensions link only to a unique compatible identity. Currency is never marketplace evidence. Conflicting receipts for the same compound identity fail closed; duplicate evidence for the same binding is harmless.
- Exact-source revalidation enriches previously discarded identity without appending duplicate transactions, retaining prior normalization history. Overlap warnings compare compatible explicit identities while remaining cautious for missing dimensions.

## Checks and limits

`test_history_sales_static.py`: 10 source/wiring/pin checks. Existing `../test_workbench_reconciliation_static.py`: 22 retained structural checks. Python does not parse PowerShell or execute product behavior.

`Test-ForgeHistoryAndSales.ps1`: **32 prepared native cases, 41 actual extracted functions**, including nested-content preservation, cancel/stale/conflict/navigation flows, atomic invalidation after failed reopen, retained receipts/artwork/archive references, exact/partial/wrong-market identity, CSV import/reimport and inherited ambiguous-date refusal. `HistorySalesDependencies.json` explicitly documents synthetic state/UI/receipt-authority/parser/language boundaries. No full application, WPF, real durable-store, ZIP/package authority or visual test is claimed.

Run only with an already-installed stable PowerShell Core 7.5+ supporting `ConvertFrom-Json -DateKind String`, under the existing private-staging/owned-process supervisor. No installation, policy changes, model/provider/network dispatch or UI windows are authorized. The harness requires `-PackageRoot` (private app source copy), `-PinsPath`, fresh nonce `-RunId` and empty private `-RunRoot`; it is NOT an isolation/timeout supervisor. Acknowledgment alone does not satisfy supervision. Native execution remains blocked in the current cloud workspace because `pwsh`, `powershell` and `dotnet` are absent.

Require exit zero plus a fresh complete `forge.core_history_sales.native_receipt.v1` with PASS, exact nonce/paths/hashes/ordered case and function names, no errors, and unchanged original/private source hashes. Missing, stale, incomplete or mismatched receipts are not success. Existing supervisor schema acceptance wiring and native/WPF execution remain pending; this work does not assert product readiness or authorize publication.

The inherited four focused native suites and original broad suites remain NOT RUN against these bytes. Their current-source pins were refreshed only in this candidate. No remote write, release, install, provider call, user-record import or desktop interaction occurred.
