# CURRENT STATE — Merch Forge

## Current release
See `forge/app/FORGE_0xx_CHECKPOINT.json` and the newest ZIP in `forge/releases/` (SHA-256 next to it).
Backend minimum `forge-app 0.2.70` (unchanged). Rollback: branch `forge-last-green` (updated by CI after every green run on main); older ZIPs in `releases/`; 054 and frozen 050 in `archive/`.

## How proof works
Every push to `forge/**` runs the **forge-windows** workflow on a real Windows machine (screen set to 1920×1080):
1. the app's startup preflight exactly as the launcher runs it, and the provider pipeline self-test;
2. the headless self-test under **Windows PowerShell 5.1** (drafts, pipeline, performance, check confirmation, Amazon profile; 054 rollback reads new state);
3. the **real app window driven by clicks** in five processes:
   - `create`: Discover → draft → KEEP → edit → brief → Portfolio → RU
   - `restart`: everything persisted
   - `package`: artwork → accept → Amazon profile form → listing → Confirm-checks form → READY package → receipt → sales → Performance leaders/attention → data copy save/restore
   - `layout`: every section at 1024 / 1366 / 1920 px; fails if any text is cut off at 1366/1920 or any English sentence is left on a Russian screen
   - `offline`: backend down; every button in every section and tab (inside a draft and two offline ideas) is clicked; any crash fails
4. **install test from the release ZIP**: START from the extracted folder (window opens, clean exit), fresh install (dialog answered via UI Automation, shortcut), upgrade over 054 (054 kept as `app.previous`, installed app starts), downgrade guard.

Results (JSON, screenshots, logs) → branch **`forge-ci-results`** (`latest/`) and run annotations. CI data are labelled fixtures; nothing is uploaded or published; "owner attestations" in CI are fixtures, not real reviews.

## What the app does now (055–073)
- Discover → **Create concept draft** (local, bound to its research). Ideas: KEEP / EDIT / REGEN / SKIP, local revisions, brief export. Live server actions blocked for drafts.
- Artwork import → exact Accept → **Amazon print profile form** (PNG template fills size + fingerprint; status and days left; warning 7 days before expiry) → **Confirm checks form** (plain checklist for IP, Amazon policy, listing text; PASS needs a reference and the owner's tick; same importer/validation as JSON) → listing → READY package → receipt → sales.
- **Portfolio pipeline**: counters, next actions; a click opens the tab where work continues.
- **Performance**: Leaders (per product, 30/90 days, verified receipts only) and Needs attention (no sales 30 days, unknown product IDs, profile missing/expiring, unpublished READY packages, undated rows). Home shows the attention count.
- Errors show the real reason in EN/RU/ES (central translator, ~300 messages). Checks list readable in the UI language.
- Layout: no double titles; captions wrap; the idea title comes back in the header.
- **My data** (Home): save a copy of all local work as one ZIP (never keys/secrets) and restore it — verified file by file, previous data saved first, automatic rollback on failure, works on another PC.
- Publish: live listing hints (Amazon lengths, risky wording, HTML/emoji). Ideas: filter by pipeline stage.
- Sales CSV: loose column names, ";" files, decimal commas, per-file day/month order; unreadable rows are counted and shown.
- Fixed old bugs found by the new tests: START_0xx entrypoint never ran (UTF-8 BOM in a .vbs), local image generation never started (`$pid`).

## Known, not yet fixed
- Live `discover_snapshot` has no note→niche link (DB `research_notes` has none) → drafts get 0 linked notes (fail-closed). Exposing it needs a forge-app change — **owner decision**.
- Notes produced deep inside the check worker are still English in RU/ES when they are not in the dictionary.

## Not authorized / not done
No backend deployment, Supabase write, paid generation, acceptance on the owner's behalf, publication or external contact.

## Process
Direct-to-`main` (owner's decision). Another session (reveng) also pushes to main → always `git pull --rebase` before push.
