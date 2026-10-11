# REVA2-G281 — global (owner-independent) discovery path

Status: internal overlay on the frozen G280 package. Nothing here is a market claim. No provider call, spend, publication, outreach or external write was performed.

## What this adds
| Module / file | Purpose |
| --- | --- |
| `app/global_ranking_v6.js` | `reveng_v6_independent` scorer: 12 weights, confidence multipliers, entrant-edge hard gate (cap 45), integrity check identical to the database trigger `validate_score_run_integrity`. Owner/user fields are ignored and reported; owner-sourced evidence is dropped; a grade can never exceed what verified evidence allows. |
| `app/global_gates_v6.js` | Hard gates and decision. Compares an idea with the **best/cheapest credible alternative** (free tools, open source, DIY), not with the dearest incumbent. A fatal deep-screen reason kills only when its evidence is provider-verified; uncited fatal claims become unresolved conditions. Verdict is `no_winner`, `conditional_winner` or `winner`; never manufactured. |
| `app/global_scan_v6.js` | Validity of a global scan: ≥30 raw candidates, ≥8 families, ≥3 per required family, no duplicates, one research protocol, no owner context. The mandate-bound pilot scope (`discovery_scope.js`, max 12) is unchanged. |
| `app/evidence_protocol_v6.js` | Two-phase, provider-agnostic evidence protocol (provider citations → `C#` verified, search-result URL → `S#` search_confirmed, imported → agent_reported) and the legal source policy mirrored from `reveng.pilot_allowed_sources` (`server/REVA2_G281_SOURCE_POLICY_SNAPSHOT.json`). Scraping, bulk download, login/paywall/captcha bypass are refused. |
| `app/spend_guard_v6.js` | Production counterpart of the simulation-only budget ledger (G224). No paid call without an explicit dollar authorization confirmed by the owner; cumulative per scope across runs; reservation before every call; a fatal provider error (credits/auth) blocks until a new authorization; estimate calibrated on the measured first scan. |
| `app/global_ranking.html` (+ `.css`, `_page.js`, `_view.js`, `data/g281_scan1_view.js`) | Standalone page linked from the sidebar: verdict banner, scan validity, outcome counts, spend panel, filterable candidate list with evidence classes. It never shows a v6 rank without v6 component scores. |
| `server/REVA2_G281_SCAN1_IMPORT*.{json,sql}` | Dry-run package for the app's own inbox tables (`catalog_discovery_runs`, `catalog_candidate_inbox`, `catalog_discovery_run_candidates`). The SQL ends with `ROLLBACK`; only the owner may switch it to `COMMIT`. |

## Verification (all offline, $0)
- `diagnostics/tests/reva2_g281_global_ranking_v6.mjs` 79 checks (reproduces all 7 real `reveng_v6_independent` rows from `score_runs`).
- `reva2_g281_global_gates_scan_v6.mjs` 39, `reva2_g281_evidence_spend_v6.mjs` 55, `reva2_g281_global_ranking_view.mjs` 15.
- `test_reva2_g281_global_ranking_page.py` 28 (Chromium: content, filters, keyboard, 360/768/1440 px, hostile-data escaping, link from index).
- `diagnostics/tools/dryrun_scan_import_g281.sh`: throw-away local PostgreSQL 16 with the tables and the `guard_global_catalog_candidate_metadata_v1` trigger reconstructed from the live catalog: rollback leaves nothing, a commit yields 1 run / 40 candidates (16 rejected, 24 research_queue) / 40 links, rerun is idempotent. It caught a real defect before any write: a top-level metadata key `owner_independent` is rejected by that trigger (`owner\_%`), so the package uses `global_independent`.
- `diagnostics/tests/verify_reva2_g281_overlay.py`: every G280 file is byte-identical except the declared overlay files.

## Baseline of the frozen G280 package (measured, not claimed)
- Closure verifier `verify_reva2_post_g280_windows_closure.py`: 41/41 on the original; the G281 tree fails its manifest checks by design (it adds files and changes `app/index.html`), which is why G281 has its own overlay verifier.
- Python tests run as-is in a scratch copy: 374 of 492 pass. 96 of the 118 failures are tests of stages G0–G99 whose UI/doc snapshots later stages changed on purpose; five are single-check failures in G128/G133/G144/G146 (G128: later compliance rules require a jurisdiction for `verified`); the delivery/stage-acceptance tests (G250, G258, G259, G263, G275–G280 verifiers) assert G280 state and are superseded by the closure verifier. Tests also write reports into the tree, so the suite is not hermetic: run the closure verifier on a clean copy before running anything else.
- JS runtime tests: 85 files, 83 pass; `reva2_g151_runtime.mjs` and `reva2_g152_runtime.mjs` fail (fake-transport OpenAI execution is not reached); `reva2_g271` needs `REVENG_ROOT`.

## Findings that matter
1. The first scan of the separate Node engine labelled its scores `reveng_v6_independent` but computed them with the G280 v1 *balanced* weights. Those scores are stored with the label `g280_balanced_v1_lens_NOT_reveng_v6` and are not comparable with `score_runs`. No candidate has v6 component scores yet, so there is no v6 ranking.
2. Kills in that scan rest on uncited provider claims (5) or on manual reading by the agent (3), not on engine-verified quotes. They are stored as `rejected` with `rejection_basis` saying so; under the global rules they are strong leads, not hard kills.
3. The app scoring contract `reveng_scoring_profiles_v1` (default `autonomy_first`) is a per-workspace ranking lens, not the global ranking. It is left unchanged and should be treated as the optional owner-fit overlay.

## Owner-gated (not done)
Writing the import to Supabase; any paid provider call (needs a dollar amount and a yes); choice of AI provider (the app contract is OpenAI-only); building the native Windows executable; enabling RLS on the five `public.godog_gdconst_*` tables flagged by the Supabase advisor.
