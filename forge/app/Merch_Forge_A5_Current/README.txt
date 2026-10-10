Merch Forge provider operations include draft/final profiles, local + optional online doctor, daily paid-request ceiling, one-request jobs, no automatic paid retry, and an isolated no-network end-to-end provider pipeline self-test.

Purpose
- Keep the 012 CORE lineage/recovery rules and frozen product UI.
- Add a real production-image provider path without coupling Forge to one online backend.

Generation paths
1. Manual bridge remains available: export a brief, create artwork elsewhere, import PNG/JPG.
2. Optional local provider worker: run Configure Image Provider.vbs, store an API key for this Windows user, explicitly enable paid generation, then click Generate in Forge.

Provider safety
- No API credential is shipped in this package.
- Credentials are read from OPENAI_API_KEY or a Windows DPAPI-encrypted per-user secret.
- External image generation is OFF by default.
- A provider call can start only after explicit owner configuration AND an explicit Generate click.
- One active local generation job per exact idea revision is allowed; no hidden retry loop.
- Worker jobs bind concept key + exact revision ID/hash + prompt SHA.
- Results bind the exact job SHA and are re-verified before artwork import.
- Generated artwork is not accepted automatically. Owner must Accept the exact SHA separately.
- Provider worker contains no marketplace publish/submit path.

Image provider adapter
- OpenAI Image API adapter is packaged and disabled by default.
- Default: gpt-image-2.5-sunburst, transparent PNG, 2048x2048, high quality, 3 variants.
- Alternative packaged model: gpt-image-2.5-flare.
- Provider availability/account permissions are not claimed until a real owner-authorized generation succeeds.

Local recovery
- Jobs: %LOCALAPPDATA%\MerchForge\generation-v1\outbox
- Worker results: %LOCALAPPDATA%\MerchForge\generation-v1\results
- Import receipts: %LOCALAPPDATA%\MerchForge\generation-v1\receipts
- Local CORE state remains atomic + last-good protected.

Publication boundaries
- Amazon packaging remains manual-upload only.
- External marketplace submission remains disabled.
- Sales/royalty metrics remain linked to verified publication receipts only.

Startup
- Normal start performs integrity + PowerShell parser + native WPF XAML preflight.
- New provider worker/setup PowerShell files are included in the same preflight automatically.

Provider operations: Configure Image Provider.vbs → Test Image Provider.vbs (local/no network) → optional Test Image Provider Online.vbs (GET model metadata/no image generation) → explicit Generate.

019 first-live safety
- Before one exact imported billable live OpenAI image success, Smoke is mandatory: Flare dated snapshot / 1024x1024 / medium / one image.
- Daily paid-request ceiling is exactly 1 during this first-live gate.
- Draft/Final unlock only after the shared authority validator proves the exact smoke job + exact result/attempt/receipt hashes/provenance and matching LocalCore artwork provenance/local bytes.
- Internal mock attempts never unlock production profiles.

Provider pipeline regression
- Normal startup runs an isolated internal mock generation pipeline once per immutable package and caches the PASS by integrity SHA.
- The self-test uses TEMP/isolated LOCALAPPDATA, makes zero network calls, imports two transparent PNG fixtures through the real result bridge, and performs a headless exact local Accept.
- The internal mock provider cannot be selected in owner configuration and cannot run without the worker's explicit -InternalMock switch.
- Installer/--verify-only preflight skips the mock pipeline; normal owner startup runs it once per package.

017: provider provenance is now end-to-end and default production profiles use dated GPT Image 2.5 snapshots. UI is unchanged.

018: prompt compiler provenance and actual transparent-canvas border validation added; UI unchanged.


020 generation lifecycle recovery
- Never start another paid Generate while an exact completed result is waiting for verified import/recovery.
- A durable completed result is preserved if final attempt-journal persistence fails; Refresh/Artwork recovery completes exact lineage without another provider call.
- Ambiguous paid retries remain explicit-owner only and must follow one linear prior_job_id chain.


021 check request bundle
- Exact local Accept writes a lineage-bound check request + evidence template under local exports.
- Listing metadata save refreshes the request with the exact listing hash.
- Technical facts are evidence only; no Amazon/channel PASS is fabricated without a current verified profile.


022 check evidence authority
- A PASS is no longer trusted merely because imported JSON says state=pass.
- Owner-imported external PASS requires v3 + owner_attested_external + attested=true + evidence_refs.
- live_backend_exact / verified_worker / verified_channel_profile are reserved for verified ingestion paths.
- READY package preupload-gate.json records exact authority/evidence provenance.
- Publication receipt v3 is bound to the exact gate bytes inside the package ZIP.




PRINT / CHANNEL BOUNDARY

- Local PNG/decode/transparency facts are machine-checked.

- Amazon channel dimensions are NOT inferred from historical guidance. Use Data\AmazonPrintProfile.template.json + Import Amazon Print Profile.vbs with the current Amazon product template.

- READY package now binds print-production.json and its SHA through the pre-upload gate and publication receipt.



SPOOL RETENTION

- Generation JSON lineage metadata is retained. Imported provider PNGs may be pruned only after verified import + verified local artwork copy, after the minimum retention window, and never for unimported/ambiguous jobs.

025 PROVIDER RECOVERY
- Cumulative source is exact canonical 024; 021/022 branches are not resumed separately.
- Removed truncated duplicate PowerShell fragments from Configure Image Provider.ps1 and Test Image Provider.ps1 that would be rejected by the unified Parser::ParseFile startup gate.
- Configure/doctor first-live unlock now requires the same exact job/provider/profile/model/result-asset lineage proof as the generation worker.
- Candidate metadata now declares the current publication receipt v3 contract, current integrity count, and current 025 entrypoint/release identity.
- MerchForgeWorkbench.ps1 and all 16 runtime Modules are byte-identical to 024. Product UI/XAML is unchanged.
- No paid provider call, Amazon submission, or external submission was performed. Native Windows parser/runtime verification is still an owner milestone.

026 journal-guard hardening
- Paid-request accounting now fails closed if any provider attempt journal is unreadable, malformed, misnamed, or has an invalid dispatch timestamp.
- New paid generation is blocked if any outbox generation job journal is unreadable or malformed; corrupted history can no longer disappear from the active/ambiguous safety boundary.
- Product readiness, standalone provider doctor, and the separate provider worker enforce the same fail-closed attempt-journal rule.
- The isolated startup provider self-test exercises corrupt outbox + corrupt attempt cases with zero network calls and zero billable requests.
- Workbench/UI/XAML bytes are unchanged from 025.

027 local-core recovery hardening
- A surviving state.lastgood.json is now authoritative recovery input when state.json is missing; first startup no longer creates an empty state over a valid backup.
- Corrupt or structurally incomplete primary state is restored from the exact last-good bytes under the local-core mutation lock, with the replaced primary preserved as a recovery artifact.
- If existing primary/last-good artifacts are both unreadable or invalid, Forge stops fail-closed and preserves them; it does not silently create an empty history.
- The cumulative no-network startup self-test now covers missing-primary recovery, corrupt/structural-primary recovery, double-corruption preservation, legacy v1→v2 migration, and legacy v2 CAS-envelope upgrade.
- Workbench/UI/XAML bytes remain unchanged. No provider call or external submission is performed by these recovery tests.


- Legacy forge.local_core.v2 states with a valid revision/core envelope but no last_write_id are treated as pre-last_write_id history and upgraded to the current CAS envelope on the next safe write.

028 JOURNAL ENVELOPE GUARD
- Parseable generation_job.v4 outbox journals now require the core concept/revision/provider/prompt/render identity envelope before any new paid generation action can be created.
- Readable but truncated v4 history fails closed instead of becoming invisible to current-revision lifecycle/ambiguity analysis.
- Legacy v4 compatibility is preserved: later first-live/lifecycle/concurrency fields are validated when present but are not retroactively required from older legitimate v4 journals.
- Startup no-network regression proves a valid legacy v4 envelope passes and a parseable truncated v4 journal blocks.
- Workbench/UI/XAML unchanged; no paid provider call or external submission performed.


029 SPOOL IMPORT AUTHORITY GUARD
- Spool pruning now reuses the strict generation_import_receipt.v4 lineage validator before any provider PNG can be deleted.
- The receipt asset SHA set must be unique and exactly match the completed result set; every receipt asset must still have a verified local artwork copy.
- A readable but duplicated/incomplete receipt such as [A,A] for result [A,B] cannot authorize deletion of B.
- Startup self-test exercises this regression with zero network calls and zero billable requests.


030 PUBLICATION IDENTITY GUARD
- A verified channel + product_id may be imported idempotently only for the same exact Forge package lineage.
- A conflicting verified package binding for the same channel + product_id fails closed instead of being silently treated as already recorded.
- Unverified legacy receipts do not block a new verified v3 receipt.
- Sales rows link by product_id only when that ID resolves to exactly one verified product_key; ambiguous cross-channel IDs remain unlinked.


031 FIRST-LIVE AUTHORITY GUARD
- Product readiness, standalone generation worker, Configure helper and local Doctor use the same shared no-network first-live authority validator.
- Unlock requires a complete generation_job.v4 envelope, exact SHA-bound completed billable nonmock result/attempt/import receipt, Smoke/one-image/one-request first-live policy, unique exact receipt/result asset parity, and matching LocalCore artwork generation provenance with exact local-file SHA.
- Missing/tampered job history, missing artwork bytes, or mismatched LocalCore generation provenance relocks Draft/Final fail-closed.
- Internal mock attempts never unlock production profiles.
- Workbench/UI/XAML remain byte-identical to 030.


032 EVIDENCE REF GUARD
- PASS / NOT_REQUIRED evidence that requires external/documented refs must contain at least one non-empty string evidence_ref; blank, null, whitespace-only, or non-string refs fail closed.
- Package-gate revalidation now rechecks non-empty source and a valid non-future checked_at timestamp instead of trusting only the import-time validation.
- owner_attested_external semantics are unchanged: it remains owner attestation, not independent verification, and still requires the exact imported evidence-file SHA.
- Startup no-network regression covers valid owner-attested evidence plus blank/null ref, missing source, invalid checked_at, and documented-not-required blank-ref failures.
- Workbench/UI/XAML remain byte-identical to 031; no paid provider call or external submission is performed.

033 PUBLICATION RECEIPT AUTHORITY GUARD
- Verified publication receipts are revalidated against immutable stored READY package lineage every time they drive product identity, sales links, or portfolio counts.
- Current package valid=false does not erase a historical publication; status and immutable lineage must still match.
- Future published_at values fail closed. Tampered or orphaned receipt lineage becomes non-authoritative and sales remain unlinked.
- Legacy v3 receipt/package pairs from before print-production SHA binding remain compatible when neither side contains that later field.

034 temporal authority guard
- Generation job created_at more than 10 minutes in the future fails closed before provider dispatch.
- Provider attempt dispatch_started_at more than 10 minutes in the future fails closed in readiness, doctor, worker and daily paid-request accounting.
- Amazon print profiles require valid_until strictly later than captured_at in import, runtime and trusted worker validation.
- Normal startup no-network selftest covers all three temporal regressions.
- UI/XAML, paid-generation default authority and external submission authority are unchanged.

034 owner milestone
- Extract 034_Merch_Forge_TEMPORAL_AUTHORITY_RC.zip and run START_034_MERCH_FORGE.vbs once on normal Windows.
- Do not perform a paid generation as part of this startup test.


035 package-gate authority hardening
- Publication receipt import re-derives READY authority from preupload-gate.json inside the exact package ZIP; mutable LocalCore package status cannot override immutable DRAFT gate bytes.
- Exact gate lineage/print SHA must match the LocalCore package record.
- Existing package ZIPs are revalidated during publication authority use when present.
- Publication timestamps cannot predate exact package creation beyond the allowed clock-skew tolerance.
- UI/XAML and external-generation authority are unchanged.

036 policy listing authority guard
- Marketplace policy PASS / NOT_REQUIRED is bound to the exact current local listing hash.
- Listing edits reset policy + metadata authority.
- Live policy is imported only when live publication fields exactly match the local listing snapshot.
- Live mismatch re-locks prior live policy authority.

036 owner milestone
- Extract 036_Merch_Forge_POLICY_LISTING_AUTHORITY_RC.zip and run START_036_MERCH_FORGE.vbs once on normal Windows.


037 publication channel authority
- Amazon manual-package publication receipts are channel-bound to amazon_merch.
- marketplace is derived from the exact owner-attested channel profile embedded in print-production.json; it is no longer hardcoded to amazon.com_us.
- New canonical product identity includes marketplace; legacy two-part keys remain readable.
- Sales CSV rows without marketplace remain unlinked if the same product_id exists in multiple verified marketplaces.

038 GENERATION IMPORT MATERIALIZATION AUTHORITY
- generation_import_receipt.v4 is satisfied only when every receipt asset is materialized as a verified local file for the exact concept/revision.
- LocalCore artwork must carry the exact generation job/result/attempt/provider/prompt provenance before completed_pending_import can become imported.
- Missing local bytes or stale/manual provenance re-open completed_pending_import so retained provider spool assets are re-imported before any later paid action.
- Recovery is local/no-network; no automatic paid retry is authorized. UI/XAML unchanged.


039 LOCAL ARTWORK ROOT AUTHORITY
- Generation import/first-live/spool authority accepts materialized artwork only when local_file_path canonically resides inside the LocalCore artwork store.
- A provider-spool PNG cannot masquerade as its own verified local backup even when SHA and provenance match.
- Re-import of an existing artwork record repairs local_file_path back to the canonical LocalCore destination before imported status is restored.
- Recovery remains local/no-network; no automatic paid retry or external submission is authorized. UI/XAML unchanged.


051 IN-APP OWNER REVIEW
- Ideas Overview now contains KEEP / EDIT / REGEN / SKIP decisions directly in the main Forge Workbench.
- Decisions persist in LocalCore and bind to the exact concept revision ID + content hash.
- Changing the concept revision invalidates the prior decision back to UNDECIDED.
- Owner decision buttons do not Generate, Accept, publish, call a paid provider, or mutate Supabase.
- 050 remains the immutable rollback baseline; 051 changes only product UI/local owner-decision state plus package metadata/integrity.

052 OWNER REVIEW CLICK FIX
- Fixed live-mode owner decision buttons remaining disabled after concept load.
- Root cause: owner controls were refreshed while Busy=true; the final Busy=false transition did not refresh them.
- Set-Busy now refreshes owner controls after each Busy transition.
- No Generate, Accept, Submit, paid provider, state sync, or Supabase mutation is performed by this fix.

053 OWNER REVIEW RUNTIME RC
- Includes 052 click-enablement fix.
- Fixes Owner Review EN/RU/ES localization, including title, body, action buttons, clear action, and progress text.
- Owner action enums stored internally remain KEEP/EDIT/REGEN/SKIP; display labels are localized only.

055 RESEARCH -> CONCEPT DRAFT
- Discover > select niche > Create concept draft: creates a LOCAL draft in Ideas with research provenance.
- Provenance: niche identity, exact niche row SHA-256, snapshot time, contract, explicitly linked notes only.
- Hook and visual direction are never invented; the Overview lists what is still missing.
- Edit tab saves local draft revisions; a new revision resets the owner decision to UNDECIDED.
- Export brief works as before (no dispatch). Generate, live Accept, delivery and server actions are blocked for drafts.
- Clicking Create twice on identical research reuses the existing draft.
- Drafts are stored in LocalCore state (research_drafts). 054 can still read and rewrite this state without losing drafts.
- Self-test: MerchForgeResearchDraftSelfTest.ps1 -OutputPath <file> (headless; not a WPF click test).
