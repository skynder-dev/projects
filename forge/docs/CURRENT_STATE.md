# CURRENT STATE — Merch Forge

## Current release: 060_Merch_Forge_LOCALIZED_MESSAGES_RC
`forge/releases/060_Merch_Forge_LOCALIZED_MESSAGES_RC.zip` (SHA-256 in the `.sha256` file next to it). App `2.12.0-forge-localized-messages`, backend minimum `forge-app 0.2.70` (unchanged). Rollback: branch `forge-last-green`; older ZIPs in releases/; 054 and frozen 050 in archive/.

## How proof works now
Every push that touches `forge/` runs the **forge-windows** GitHub workflow on a real Windows machine (free for this public repo):
1. the app's own startup preflight, exactly as the launcher runs it (integrity, PowerShell parser, real WPF XAML load);
2. the research-draft self-test under **Windows PowerShell 5.1**, including the 054 rollback reading 055+ state;
3. the **real app window driven by button clicks** in two processes (create, then restart), with screenshots.

Results (JSON, screenshots, app logs) are published to the branch **`forge-ci-results`** (`latest/`), and failures also appear as annotations on the run.
The app gets a labelled fixture only for `discover_snapshot`; every other backend or network call fails by construction. No secrets, no paid calls.

## Proven on real Windows (commit ce32386, all steps green)
| Step | Result |
|---|---|
| Startup preflight as the launcher runs it | PASS |
| Provider pipeline self-test | PASS |
| Research-draft + pipeline self-test, Windows PowerShell 5.1 | 72/72 |
| Window, phase 1: Discover → draft → KEEP → edit rev 2 → brief → Portfolio board → RU | 45/45 |
| Window, phase 2 (restart): draft, rev 2, KEEP, RU, Portfolio in RU | 13/13 |
| **Window, phase 3 (full local path)**: import artwork → exact accept (button) → Amazon profile via the real importer → listing (Save) → trusted print check → owner evidence from the app's template → **READY_FOR_MANUAL_UPLOAD package** (Build button) → publication receipt → Portfolio "Published" → sales CSV → Performance counts linked rows only; RU status-bar messages | **25/25** |

All CI data are labelled fixtures. Nothing is uploaded or published, and the "owner attestations" in CI are fixtures, not real reviews.

## Features in the app (055–060)
- Discover → select niche → **Create concept draft**: a LOCAL draft bound to its research (niche id, row SHA-256, snapshot time, explicitly linked notes only). It appears in Ideas with KEEP/EDIT/REGEN/SKIP, supports local revisions (a new revision resets the decision) and a no-dispatch brief. Generate and live server actions are blocked for drafts.
- 060: status/busy/error/confirm messages in RU/ES (central translator, `Data/Forge.MessageTranslations.json`, 154 templates).
- 058 Portfolio **pipeline board**: counters (no decision / KEEP / artwork accepted / checks passed / package ready / published), Next actions sorted closest-to-publishing first (click opens the idea), and decisions by niche. Read-only, local data, EN/RU/ES. Home/Portfolio/Performance now use the full window width.
- 056 fixes found by the first Windows run: a language switch no longer resets live screens; the status bar no longer sticks on "Working…"; PS 5.1 spool cleanup works.

## Fixed in 059 (pre-existing; found by the full-path CI phase)
- Selecting an imported or locally generated artwork in the Artwork list **threw** (StrictMode: the list read server-only fields). Local artwork now carries neutral defaults.
- Royalty amounts were **blank** in the Performance/Home texts (`"${2:0.00}"` in double quotes is a variable name). Those texts are now EN/RU/ES.
- Imports were split into dialog + `*FromPath` (same behaviour), and `Import Amazon Print Profile.ps1` gained `-SourcePath/-NonInteractive`. These make the full path testable.

## Fixed in 057 (all pre-existing since ≤054; found by the Windows provider self-test)
- An owner-attested Amazon print profile was **never accepted**: the profile check and the `Import Amazon Print Profile` tool assigned to the read-only `$host` variable.
- The PNG transparent-border check **always threw**, because the comma binds tighter than the minus in `@($x,$bmp.Height-1)`. Every generated image was rejected, and print checks never confirmed transparency.
- The **first trusted print/check after accepting artwork always failed**: a fresh request was a dictionary, so its `request_id` read as empty. Only re-runs worked. The check worker's exit code was also empty on PS 5.1.
- Self-test infrastructure: worker command lines had literal backticks (workers never started), and the spool report was a dictionary (`deleted_count` read as 0). Diagnostics now report the child exit code and output, the last app WARN, and rejection reasons.
- The app now logs **why** a check result is rejected (field name), instead of failing silently.

## Known, not yet fixed
- Page titles appear twice (header + page) on Discover/Portfolio; at ~1024 px the Discover header text wraps narrowly. Cosmetic, pre-existing.
- Live `discover_snapshot` field names for niche id and note links are not yet confirmed against real data. Matching is defensive and fail-closed.
- The dictionary-vs-object sweep was done with an AST scan: one more real case (generation job) was fixed in 058; the rest are API payloads or dot-access, which are safe.

## Not authorized / not done
No backend deployment, Supabase write, paid generation, acceptance on the owner's behalf, publication or external contact.

## Process
Direct-to-`main` (owner's decision). Rollback point = branch `forge-last-green` (updated automatically by CI after every green run on main); before this change: commit `e6c836d` (main after PR #1).
