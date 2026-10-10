# WORKLOG — FORGE CLAUDE MIGRATION 01 (session of 2026-10-09)

## Assumptions / decisions (reversible, made autonomously)
1. **Drafts are local-only.** 054's backend contract is read-only and Supabase product-data mutation was never authorized. Drafts live in LocalCore `research_drafts[]` inside the unchanged `forge.local_core.v2` envelope. Promotion to server concepts is deferred to an owner decision.
2. **No invented creative copy.** The draft's title comes from the niche name; concept text from the research summary plus linked notes; buyer from the audience; purchase reason from the top 3 score dimensions; differentiation from the existing concept count. Hook and visual direction stay empty.
3. **Evidence = explicit links only.** Notes attach only when the snapshot links them to the niche by id or exact name. There is no fuzzy matching. Snapshot-wide sources are stored but labelled as not niche-specific.
4. **Generate is blocked for drafts.** The no-dispatch brief is the artwork path. Paid generation stays a separate owner gate.
5. **Idempotency:** a repeated click on an identical niche row (same SHA-256) reuses the draft. Changed research creates a new draft.
6. **Revision hash covers all 7 creative fields** (wider than LocalCore's default 5-field fallback), so editing buyer or purchase reason also invalidates a stale decision.
7. Manifest `package_name` was still "053" in 054 (an upstream inconsistency). It is corrected to 055. installer_generation is advanced by 1.

## Steps
- Verified bundle hashes (054 c6ea5f50…, 050 13aaf21c…) against 08_SOURCE_MANIFEST.json.
- Extracted 054. Integrity 50/50 (the first naive check showed 20/50 because of Windows backslash paths; the corrected check gives 50/50). Installed PowerShell 7.4.6; all 26 .ps1 files parse.
- Mapped the code: Discover (ProductNavigation), queue/detail (DataViews), owner review (Workbench + LocalCore), Set-Busy (Gates). Confirmed the 052 fix (Set-Busy → Update-OwnerDecisionControls) and the 053 RU labels.
- Added Modules/Forge.ResearchDrafts.ps1 (UTF-8 BOM, EN/RU/ES strings) and patched Workbench (XAML button, status text, filter item, bindings, workflow label/colors, Set-Dirty, edit-box handler, Overview visual button), Gates (Set-Busy/Save/Generate, Update-AcceptanceControls, Apply-RoleUi; added BOM), DataViews (queue merge, draft open/reload routing), ProductNavigation (draft section routing, Discover refresh), Localization (button, filter), and DomainActions (Save redirect, Generate block, 7 live-action guards).
- The patcher initially failed on CRLF files; fixed so line endings are preserved. A later inline edit converted DataViews to LF; restored to CRLF and added a static check.
- Wrote MerchForgeResearchDraftSelfTest.ps1. It extracts the real workbench functions via the PowerShell AST, dot-sources the real modules, stubs only WPF controls and network, and runs 3 processes (create / restart / 054-rollback read). First run 61/61. Mutation-tested with 3 injected regressions; all caught.
- Found that Refresh/post-action reloads would send draft keys to `concept_detail` and routed Load-Concept locally (+ test).
- An independent reviewer agent found 8 issues: a missing-draft key could still hit the API, stale live variants/evidence showed in the draft view, an uncaught exception in the draft open could crash the app, the Generate button stayed enabled via Update-AcceptanceControls, culture-dependent decimals, a PS 5.1 array serialization risk, and minor items. All were fixed, with 6 new checks → 67/67.
- The provider pipeline self-test needs WPF, so it could not run here. Its inputs are byte-identical to 054.
- Built the deterministic ZIP (fixed timestamps, sorted entries, built twice, identical). Static 49/49, integrity 52/52. Re-verified from a fresh extraction.

## Not done
- Native Windows smoke (needs the owner's PC or a linked session).
- Stage 4 Portfolio/Performance (by plan, only after Stage 3; next session).
