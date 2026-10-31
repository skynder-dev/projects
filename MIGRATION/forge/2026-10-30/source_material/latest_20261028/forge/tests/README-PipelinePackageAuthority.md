# Pipeline package authority regression

Status when prepared: **all native tests NOT_RUN**. The preparation environment has neither `pwsh` nor `powershell`. No PowerShell parser, Forge function, ZIP authority, or native PNG test ran there. Source/patch integrity checks are separate and are not evidence of runtime correctness.

## Independent repair

`Get-ForgePipelineStage` and the unpublished-package attention branch of `Get-ForgePerformanceInsights` now call the existing `Test-LocalPackageCurrentAuthority` with the actual concept, no cached readiness, and the supplied state. Both call sites fail closed on an exception. Verified publication retains its existing precedence. No money calculation, translation, package builder, publication, or semantic-review implementation is changed.

Saved package `valid/status/revision` fields are not sufficient authority. The existing LocalCore authority checks the current semantic HOLD, readiness, listing, acceptance, profile, physical ZIP/hash/content, native artwork constraints, and archived profile expiry.

## Portable native contract, not a new executor

Use the coordinator's **separately reviewed Windows ACL and process-tree supervisor** with already installed stable **PowerShell Core 7.5+ on Windows**. Windows PowerShell Desktop, preview builds, older versions and non-Windows hosts are unsupported. PowerShell 7.5 `ConvertFrom-Json -DateKind String` and Windows native PNG decoding are required. Do not install, download, invoke the app, import fixtures, or substitute an interpreter.

There is intentionally no bespoke runnable Python launcher in this candidate. The superseded draft launcher was excluded. Reuse the existing reviewed `process_supervisor.py` (SHA-256 `7cec5afad989b2d85d969f3653621974f46edf989088407a711166538a25e057`) under that coordinator. That helper bounds an owned Job/process group; it does not itself establish private Windows ACLs. The coordinator must provision and verify an owner-private nonredirected invocation root before giving this suite access. The native switch acknowledges that contract, not proof of ACL setup.

The coordinator launches a fresh `pwsh -NoProfile -NonInteractive -File Test-PipelinePackageAuthority.ps1` with:

- `-ModuleRoot`: the exact candidate's `forge/app/Merch_Forge_A5_Current/Modules`.
- `-InvocationRoot`: new, nonredirected, owner-private Windows directory prepared and verified by the coordinator.
- `-RunId`: fresh 32-character lowercase GUID token for this invocation.
- `-SourceManifest`: this candidate's `PipelinePackageAuthority.sources.json`.
- `-ExpectedSourceManifestSha256`: independently verified exact manifest SHA-256 from the package provenance, not a silently regenerated lock.
- `-ExternalSupervisorConfirmed`: only after the coordinator actually provides the safety/completion contract.

The native suite rejects redirected path ancestors, compares the externally pinned manifest and its own test hash, extracts 43 exact functions from byte-exact source copies, and never runs module/app top-level code. It writes fixtures and its create-new receipt only under that invocation root. Final checks revalidate all application source/copy bytes, the native test, and the manifest. No Windows execution, ACL provisioning, native parse or runtime pass is claimed during preparation.

## Exact fresh-receipt and failure contract

`PipelinePackageAuthority.sources.json` supplies exact ordered application sources, native test sources, 43 function identities, and 53 case identities (the original 21 behavioral fixtures, 20 focused historical-receipt cases/matrices, nine source-integrity cases, two control-integrity cases, and the complete-identity check). The external supervisor must require those exact lists, not merely a count or a nonempty all-PASS subset.

A valid completion requires all of the following:

- Supervised native exit 0, no timeout, no surviving descendants, fresh matching run ID and timestamps bounded by this invocation.
- A new `native-receipt.json` with matching schema, `status=PASS`, zero failed cases, positive assertion count, and exactly the pinned ordered case/function/source/control identities.
- Every case PASS, exact expected module/test/manifest hashes before and after, unchanged owned source copies, and real Core/stable-version/Windows/DateKind runtime fields.
- Final supervisor-side hashes of all inputs and the manifest still match the reviewed source lock/provenance.

Timeout, crash, nonzero exit, missing/reused/mismatched or incomplete receipt, non-PASS case, unsupported runtime or source drift is failure. A killed host may leave no native receipt; even a written PASS cannot override a timeout or nonzero exit. Missing native runtime is NOT_RUN, never PASS. Retain the entire unique invocation with logs/receipts.

The source lock applies only to this standalone candidate. Other patches will change Pipeline/LocalCore hashes. Review the composed source, add the declared actual dependency functions, update both exact identity lists where required, and deliberately re-pin a new provenance before running it. Never silently refresh a failed source lock.

## Actual application paths and disclosed doubles

The harness loads 43 exact real functions, including both Pipeline entrypoints, `Get-LocalDeliveryReadiness`, `Test-LocalPackageCurrentAuthority`, the semantic-HOLD guard, listing/hash helpers, ZIP content/hash readers, `Get-LocalReadyPackageZipAuthority`, strict JSON parsing, archived PNG decoding/technical validators, current profile-file parsing, and publication receipt authority. It creates real synthetic PNG and ZIP files only when the native suite actually runs. The profile URLs are inert schema fixtures, not network requests or real external attestations.

The inherited prerequisite doubles remain; focused receipt-import state/UI seams are disclosed below:

1. `Read-LocalCoreState`: detached owned synthetic state or a controlled read failure. The import extension reads a dedicated owned synthetic JSON state file.
2. `Get-LocalPackageBriefApprovalSnapshot`: synthetic approval result.
3. `Get-LocalCheckGateSnapshot`: synthetic current-check result.
4. `Get-LocalPrintProductionSnapshot`: synthetic current-capture result/profile; archive expiry and content still use real authority.
5. `Test-ForgeSemanticReviewCurrent`: controlled review outcome; this is not an end-to-end semantic review/source verifier test.
6. `Reconcile-LocalSalesLinks`: empty-sales guard, unrelated to package authority.

`Get-LocalAmazonPrintProfilePath` only redirects the actual profile reader to the owned fixture file. Archive authority, JSON parsing, hashing, PNG decoding, and the target call sites are **not doubled**. Positive controls require a real accepted archive before any negative-path claim. Current readiness prerequisites are synthetic, so the suite is not proof of actual owner approval, real check evidence, or a full-stack app run.

## Cases prepared

- Valid physical, noncanonical package remains ready on both surfaces.
- Saved string/false flags, blocked status, stale revision, and stale listing hash cannot confer readiness.
- Missing ZIP and changed ZIP bytes with stale hash are rejected.
- Self-consistent outer hashes do not hide an invalid archived gate.
- Changed current listing or channel profile invalidates an internally valid old archive.
- Expired captured profile is rejected by actual current authority even with positive prerequisite doubles.
- Lost current approval, checks, or print readiness overrides old package flags.
- A later semantic HOLD and a persisted HOLD absent from supplied state block both surfaces.
- Current-state read failure is fail-closed.
- Real verified historical publication remains published after current profile expiry and gets no upload reminder.
- Unverified receipts do not mask invalid packages.
- Noncanonical/no-package accepted-artwork, KEEP, and null-concept fallbacks remain unchanged.

No real artwork, owner approval, business data, package export, publication, model call, network, remote write, or full application startup is performed.

## Composed source contract

This copy adds seven actual LocalCore aggregation helper extractions because the composed Performance function calls the shared aggregator. All 33 original case identities and assertions are retained. This is new test dependency reconciliation, not original author code or native execution evidence. The standalone source lock is preserved separately; only this composed source lock applies here.


## Bounded historical-receipt extension (2026-10-26)

This derivative **extends the existing suite**, not a new harness. All **33 original case identities remain in order**, and the original 21 executable behavioral fixture blocks are text-identical. There are now **53 total cases** and **43 actual extracted functions**. The three additions are `Import-LocalPublicationReceiptFromPath`, `Read-LocalCheckEvidencePayload`, and `Get-LocalPublicationReceiptBindingDecision` from the exact candidate LocalCore module.

The **20 added focused cases** include matrices for 14 receipt schema/identity/channel/market/event-date guards and six malformed-validity/non-READY variants. They cover:

- Late owner-reported publication against a real exact historical READY ZIP/PNG whose `valid` flag is now explicitly false, including a profile valid at the reported event but expired now.
- Explicit historical confirmation and cancellation; both historical and current-valid exact-source/exact-binding duplicate idempotence; conflicting product bindings backed by two real archives.
- Receipt or ZIP byte changes during confirmation; missing/tampered archives; self-consistent outer hashes with an invalid archived gate; actual strict JSON duplicate-field rejection.
- Detached saved-state persistence; a simulated stale-writer CAS rejection; injected commit-then-verification-error uncertainty followed by duplicate-safe retry; and postcommit UI refresh failure.
- Unchanged current acceptance, approval, checks, saved review history, artwork, archive records and physical PNG/ZIP/source-receipt bytes. The preservation case explicitly seeds a newer active acceptance/current revision/checks on the same concept and requires the entire concept payload to remain byte-equivalent. No restoration of current package readiness.
- No inference of publication from missing, malformed, or earlier `invalidated_at`; the explicit owner-reported event date remains the input and all archive/profile date limits still apply.
- Zero counted calls to guarded generation, package-building, reapproval, process, server API or network boundaries across the entire suite.

**Event evidence is not external verification.** The imported record must explicitly have `publication_evidence_kind = owner_attested_external` and `independent_publication_verification = false`; `historical_package_at_import` records the package's current-validity classification. The real receipt/archive authority verifies exact local lineage and the declared event's permitted date window. It does not independently verify an Amazon publication, and the inherited “verified publication” test labels refer to this existing local lineage authority, not external marketplace observation.

### Additional explicit seams and limits

`Write-LocalCoreState` is a new **test double** using a detached synthetic JSON store, an explicit simulated revision/write-ID CAS, and injectable rejection or commit-then-throw. This is not the actual durable writer, filesystem locking, atomic replacement, recovery, multi-process concurrency or a native application restart. The saved reload case only reloads detached fixture JSON. The six inherited prerequisite doubles and profile-location seam remain disclosed above; archive/PNG/JSON/hash/binding/import logic is **not replaced**.

`Confirm` uses queued bool answers and an optional bounded mutation hook. `Show-Error`, status text and business refresh are synthetic plain controls/counters; refresh failure is injected. These are not Windows/WPF dialogs or visual tests. The suite needs an already-installed stable Windows PowerShell Core 7.5+ and the same independently reviewed private-staging/process-tree supervisor. No such native execution was performed in the cloud preparation workspace; `pwsh`, `powershell` and `dotnet` are absent, and none was installed.

The refreshed source lock and test SHA apply only to this isolated historical-receipt derivative. The sealed local-Reopen candidate remains unchanged. The exact fresh-receipt/timeout/identity contract above now requires all **53** case and **43** function identities; a refreshed pin or Python text check is never native PASS evidence.
