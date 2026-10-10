# CURRENT STATE — Merch Forge

## Current release: 056_Merch_Forge_WINDOWS_FIXES_RC
`forge/releases/056_Merch_Forge_WINDOWS_FIXES_RC.zip` (SHA-256 in the `.sha256` file next to it). App `2.9.1-forge-windows-fixes`, backend minimum `forge-app 0.2.70` (unchanged). Rollback: 055 (releases/), 054 and frozen 050 (archive/).

## How proof works now
Every push that touches `forge/` runs the **forge-windows** GitHub workflow on a real Windows machine (free for this public repo):
1. the app's own startup preflight, exactly as the launcher runs it (integrity, PowerShell parser, real WPF XAML load);
2. the research-draft self-test under **Windows PowerShell 5.1**, including the 054 rollback reading 055+ state;
3. the **real app window driven by button clicks** in two processes (create, then restart), with screenshots.

Results (JSON, screenshots, app logs) are published to the branch **`forge-ci-results`** (`latest/`), and failures also appear as annotations on the run.
The app gets a labelled fixture only for `discover_snapshot`; every other backend or network call fails by construction. No secrets, no paid calls.

## Proven on real Windows (run 38018060642, commit 707a704)
| Step | Result |
|---|---|
| Startup preflight as the launcher runs it | PASS (52 integrity files, 28 PowerShell files, XAML load OK) |
| Research-draft self-test, Windows PowerShell 5.1 | 67/67 |
| WPF window: Discover → Create draft → KEEP → edit/save rev 2 → brief → RU | 38/38 |
| WPF window after restart: draft listed, rev 2, KEEP and RU kept | 12/12 |

## Features in the app (055 + 056)
- Discover → select niche → **Create concept draft**: a LOCAL draft bound to its research (niche id, row SHA-256, snapshot time, explicitly linked notes only). It appears in Ideas with KEEP/EDIT/REGEN/SKIP, supports local revisions (a new revision resets the decision) and a no-dispatch brief. Generate and live server actions are blocked for drafts.
- 056 fixes found by the first Windows run: a language switch no longer resets live screens; the status bar no longer sticks on "Working…"; PS 5.1 spool cleanup works.

## Known, not yet fixed
- **The optional provider pipeline self-test fails on Windows** ("Valid owner-attested Amazon profile did not produce a policy profile binding"). The launcher does not run it, so the app starts. The code is byte-identical since ≤054, so this predates migration. It points at the local Amazon policy-profile check (Checks/Publish stage). It is reported as a non-gating warning on every CI run.
- At the CI window width (~1024 px), the Discover header text wraps into a narrow column, and the Discover title appears twice (header + page). Cosmetic, pre-existing.
- Forge.PrintChecks.ps1 has non-ASCII text without a BOM (pre-existing).
- Live `discover_snapshot` field names for niche id and note links are not yet confirmed against real data. Matching is defensive and fail-closed (0 notes rather than wrong notes).

## Not authorized / not done
No backend deployment, Supabase write, paid generation, acceptance on the owner's behalf, publication or external contact.

## Process
Direct-to-`main` (owner's decision). Rollback point = branch `forge-last-green` (updated automatically by CI after every green run on main); before this change: tag `safe/main-before-direct-work`.
