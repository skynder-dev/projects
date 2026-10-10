# NEXT ACTION

## 1. Owner, ~5 minutes on the Windows PC (the only remaining proof gate for 055)
1. Extract `055_Merch_Forge_RESEARCH_DRAFT_RC.zip` (Extract All) and run `START_055_MERCH_FORGE.vbs`.
2. Discover → select any niche → **Create concept draft**.
   Expected: the app jumps to Ideas, the draft opens, status "Research draft", and the Overview says the hook and visual direction are missing.
3. Click **KEEP**. Switch to another idea and back: KEEP is still selected.
4. Close and restart Forge: the draft is still in Ideas and KEEP is still selected.
5. Optional: Edit tab → write a hook → Save. KEEP resets to "No decision yet" (this is correct).
6. If anything fails, send `%LOCALAPPDATA%\MerchForge\logs\MerchForge-workbench-runtime.log`.

Optional headless check on Windows (no network):
`powershell -NoProfile -ExecutionPolicy Bypass -File Merch_Forge_A5_Current\MerchForgeResearchDraftSelfTest.ps1 -OutputPath %TEMP%\rd.json`

Alternative: link this Claude task to the Windows PC (Claude desktop app → "Link to this computer") so the next session can run steps 1–5 itself.

## 2. Next autonomous engineering (after 055 native smoke, or in parallel if the owner prefers)
- Confirm the real `discover_snapshot` field names for niche id and note→niche link from one live response. Adjust `Get-DiscoverNicheIdentity` / `Get-DiscoverNotesForNiche` if needed. Read-only.
- Stage 4: Portfolio/Performance — the next read/decision surface. Starting point: an owner-decision summary (KEEP/EDIT/REGEN/SKIP counts per niche, drafts vs server concepts) plus the existing receipt-verified sales. No broad redesign.
- Decide later (owner): whether KEEP'd drafts should be promoted to server concepts. That needs a backend write contract and an explicit authorization.

## Known small items (not blocking)
- Forge.PrintChecks.ps1 is UTF-8 without BOM and contains non-ASCII text (pre-existing). Mojibake risk only in its strings.
- Opening a draft writes LocalCore state 2–3 times (existing Ensure pattern). Harmless, but it widens the "changed in another window" window if two Forge windows are open.

## Where things live
GitHub `skynder-dev/projects`, folder `forge/`: `app/` = 055 tree, `releases/` = 055 ZIP, `archive/` = 054 / 050 references, `docs/` = these files.
