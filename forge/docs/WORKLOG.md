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

## Session continuation — GitHub + Windows CI (2026-10-09 evening)
- The owner pointed out that GitHub was given so releases would not be installed by hand. Moved the project into the repo (`forge/`, PR #1 merged by the owner) and built the **forge-windows** workflow: preflight, PS 5.1 self-test, and a real-window click test with screenshots.
- Artifacts and logs live on blob storage that this session cannot reach, so CI now publishes results to the git branch `forge-ci-results` plus annotations.
- First Windows run: draft path 34/34 in the real window. It found 3 pre-existing defects (locale switch resetting live labels, "Working…" status stuck after Discover, PS 5.1 Measure-Object `Sum` in spool cleanup) and 1 CI-driver issue (a background worker holding inherited handles). All fixed in 056. It also exposed the pre-existing provider-pipeline self-test failure (not run by the launcher; tracked).
- Added `forge/tools/build_release.py` (repeatable release build from `forge/app`).
- 056 on Windows: preflight PASS, self-test 67/67, window 38/38, restart 12/12.

## 057 — making the provider pipeline self-test pass on Windows (2026-10-09 night)
- The owner decided to work directly on main, with no PRs. CI saves `forge-last-green` after each green run. Another session (reveng) also pushes to main, so always `pull --rebase` before pushing.
- The provider self-test was peeled layer by layer, adding diagnostics wherever a failure was silent: `$host` read-only (profile + importer) → backtick-quoted worker args (self-test) → comma/minus precedence in PNG border sampling → empty ExitCode on PS 5.1 (check worker) → fresh check request returned as a dictionary → spool report returned as a dictionary. All fixed. Commit 3d42f5c: every CI step is green and the provider pipeline self-test passes on Windows for the first time.

## 058 — Portfolio pipeline board (2026-10-09 night)
- AST sweep for dictionaries read as objects: one real case (the generation job returned as a dict, so the status bar showed an empty job id); fixed.
- New module Forge.Pipeline.ps1: per-idea stage from LocalCore (decision bound to revision, current acceptance, check gate, READY package for current revision, verified receipt), summary, and per-niche decisions. The Portfolio card is read-only; a click opens the idea.
- Windows screenshots exposed a pre-existing layout bug: QueueColumn MinWidth=340 kept an empty column on Home/Portfolio/Performance. Fixed. Counters changed to 3x2. Added RU/ES for 3 untranslated Portfolio captions.
- Tests: 5 headless pipeline checks (72/72); 7 window checks incl. click-to-open and full width (45/45 create, 13/13 restart).

## 059 — full local path in Windows CI (2026-10-09 night)
- Read the live forge-app `discover_snapshot` source read-only via the Supabase connector. Niche id = `niche_key` (already matched). Notes have no niche link, and neither does `merch.research_notes` → drafts get 0 linked notes (fail-closed; recorded as an owner/backend item). Provenance now also stores source url/authority_level/last_checked_at. CI fixtures mirror the live shape.
- Imports split into dialog + FromPath. Profile importer gained `-SourcePath/-NonInteractive`.
- New CI phase "package" drives the real window to READY_FOR_MANUAL_UPLOAD, receipt and sales. It found 2 pre-existing bugs: a StrictMode throw when selecting local artwork, and blank royalty amounts (`${2:0.00}` in double quotes). Both fixed. Performance/Home business texts are localized.
- Removed the "LocalCore byte-identical to 054" build check, since LocalCore now changes legitimately.

## 060 — localized runtime messages
- Added a central translator instead of editing ~190 call sites. Known English templates (154, with {n} variable parts) are rewritten in RU/ES where they are shown: a TextBlock.Text value-changed hook on StatusText/BusyText/LocalCoreStatusText, plus Show-Error and Confirm. CI asserts RU texts after Build and sales import (package phase 25/25).

## 061–067 — 10-hour roadmap, blocks 1–7 (2026-10-10)
- 061: error dialogs show the real reason (known messages as-is, translated); 115 more messages.
- 062: Performance Leaders / Needs attention from verified data only; Home attention count. Found and fixed on the way: `$r`/`$R` and `$F`/`$f` collide in PowerShell (case-insensitive names) — test variables renamed; `@($list)` inside a hashtable literal threw "Argument types do not match" — converted to arrays first.
- 063: Portfolio click opens the tab for the next step (Artwork / Checks / Publish).
- 064: Confirm-checks form + CHECKLIST.txt next to the JSON template; clearer evidence errors; messages built from UI texts count as readable. Found: `$(if(..){@($x)})` unrolls a one-element array → evidence_refs became a string; fixed with direct assignment. XML attributes turn newlines into spaces → `&#10;`.
- 065: Amazon profile card + form; the unchanged standalone importer runs as a child process (validation identical); importer errors translated.
- 066: new CI phase "offline" (backend down, click every button). First run: 0 crashes but shallow (83 clicks, mostly window buttons) → deepened in 067 to every section/tab inside a draft and two offline ideas. Localized checks view; idea title restored in the header after Portfolio.
- 067: no double titles; KPI captions wrap; CI "layout" phase (3 widths, clipped-text detector). Runner screen is 1024×768, so the workflow now sets 1920×1080 first and the phase checks that widths were really reached.
- CI: install/start/upgrade test from the release ZIP (UI Automation answers script-host dialogs).

## 068–069 — review fixes, install test (2026-10-10)
- Independent review (separate agent, read-only, 054→HEAD). HIGH (pre-existing): `$pid=` in Forge.GenerationWorkerBridge (Queue-LocalGeneration and the job status reader) — `$PID` is read-only, so local generation always failed after launching the worker and the job file was deleted; running jobs showed as "ambiguous". Fixed (`$workerPid`) + headless AST guard against assigning read-only automatic variables.
- Also fixed: "no sales for 30 days" only with fresh data (else "no data"/"stale"); sales CSV money (decimal comma, thousands, parentheses) and dates (ISO, US M/d/yyyy, d.M.yyyy; unclear → undated); Amazon profile form requires the source link and refuses an accepted artwork as the template; outer try/catch on new form handlers; async stdout for the profile importer; draft save asks before dropping unsaved listing text; Portfolio keeps its section when the owner cancels.
- CI: crash hunt opens the real WPF dialogs (timer presses OK → validation text → close). Install test (UI Automation answers MsgBox): found the pre-existing UTF-8 BOM in START_0xx_MERCH_FORGE.vbs → WSH "Invalid character" — the owner's double-click START never worked since 054. Fixed in 069; build check `vbs_no_utf8_bom_ascii_only`.

## 070–072 — stage 2 (2026-10-10)
- 070: draft reasoning shown in Checks instead of empty analysis sections.
- 071: RU untranslated-text detector in the layout phase (strict: exact English UI strings; sentences: ≥3 English words outside lists/data). Found the header subtitle and 9 status texts on Artwork/Checks/Publish; translated via the message sinks. Data copy save/restore (Forge.DataBackup.ps1). Tolerant sales CSV. Crash hunt hung on the new Save/Open file dialogs → stubbed those two entry points.
- 072: second independent review (no HIGH). Fixed: hash bytes while zipping; skip temp/worker/earlier copies; strict name whitelist (no trailing dot/space, ~, streams); validate staged state before changes; restore = exact copy (extra files removed, kept in before-restore copy); automatic rollback on a half-way failure; refuse copies from a newer state schema; keep 5 before-restore copies. CSV: resolve columns once, skip rate/currency/type columns, refuse files without units and royalty, count unreadable amounts, per-file day/month order, ISO keeps the written date, per-file counts in the message. "No sales" also needs zero royalties.
