# RevEng — resume state (2026-10-09/10)

**Objective:** program-driven, independent business-discovery instrument (not chat research, not owner-biased).
**Authoritative:** scoring `reveng_v6_independent`; global winner = NONE until a real scan produces one; user-fit OFF for global ranking.

## Done
- Phase A: 2959 G280 baseline files hash-verified. G280 modules reused unmodified (hash-pinned `vendor/g280/VENDOR_MANIFEST.json`).
- Node engine (`src/`, stdlib only): discover -> resolve evidence -> hard gates -> v6 scoring + integrity guard -> deep screen -> decide -> report. Hard spend guard.
- **Legal-by-design:** no scraping of third-party pages. Fetcher allowlist = official APIs only (HN Algolia, GitHub, StackExchange, npm, iTunes). Evidence comes only from the LLM provider's web-search citations.
- **Two-phase research protocol:** phase 1 (search ON) prose notes + provider citations; phase 2 (search OFF) JSON citing evidence by ref `C#` (provider excerpt = verified) / `S#` (search URL only = search_confirmed). Invented refs dropped. >=2 verified items required by gate.
- Fail-fast discovery (2 consecutive failures abort), diagnostics file, `smoke` command (1 research + 1 JSON call).
- Tests: 50/50 pass (`node --test test/*.test.js`), also in CI.
- GitHub Actions `scan.yml` (repo `skynder-dev/projects`, dir `reveng/`): dispatch `mode=smoke|full`; output on branch `results` (`reveng/runs/console.log`, `smoke_result.json`, `REPORT.md`).

## Live full run #1 (run_20261010_031655, results branch)
- 40 candidates / 10 families, 30 passed gates, $6.60, scoring v6. Deep screen interrupted: Anthropic credit balance too low (owner must top up). 5/8 deep-screened (old protocol), top 3 (EDU-01, MED-04, EDU-04) not screened -> verdict NO_WINNER (correct: unmet hard blocker).
- Findings fixed after run: kill reasons were narrative-only -> now structured (fatal/major/minor + cited ref) with a `deep_kill` gate (fatal + verified excerpt kills); killed leaders are replaced (deep screen continues down the ranking until top-2 survivors are screened, cap deep.max_total=16); deep revised-edge schema slips keep the original edge; deep resumable per candidate (workflow input `resume=run_...`); MANIFEST EISDIR fixed.

## Manual (free) deep screen of top-3, 2026-10-10 -> `manual/deep_screen_2026-10-10.md`
- EDU-01, MED-04, EDU-04 all KILLED (free/cheaper incumbents: TutorTab $0, free sponsor lists/DBs, SPED Goals app free/$2.99). Evidence class agent-reported. Still NO winner.
- Engine fix to do ($0): gate edge against the CHEAPEST credible alternative (incl. free), not the incumbent the LLM names.

## Spend policy (owner correction 2026-10-10)
- Owner never approved a specific amount; ~$20 API balance was exhausted (incl. my failed first live run). `allow_spend` is now **false** in config.json: every paid call is blocked until the owner explicitly authorizes a stated amount.
- Known flaw: Budget cap is per process (resets each run), knows nothing of the real account balance. To do: cumulative ledger across runs + ask owner for a dollar figure before ANY paid run.

## Owner correction 2026-10-10: work on the EXISTING app
- The product is the owner's G280 app (browser JS + `server/` contracts + Supabase `reveng` schema + desktop csproj). My Node engine (`reveng/src`) is a reference implementation, not the product. See `ROADMAP.md` (A0–A7) for the 10-hour plan to improve the app.
- Audit of G280 baseline (offline, $0): post-G280 closure verifier 41/41; old g280-final verifier 69/77 (manifest/stage drift only); runtime .mjs tests 82/85 standalone (g271 passes with REVENG_ROOT; g151/g152 fail, cause not established); 492 python tests not run yet.
- Gaps vs v6: app scoring is v1 (default `autonomy_first`); discovery capped at 12 candidates / 5 classes and tied to the owner mandate; no cheapest-alternative gate; OpenAI-only provider contract, never live-verified; no cumulative spend ledger; results of the 40-idea scan are not in `catalog_candidate_inbox`.
- Supabase advisory (not reveng schema): RLS disabled on 5 `public.godog_gdconst_*` tables. Not changed; owner decides.

## NOT done
- Live smoke of the two-phase protocol not yet confirmed (need `excerpts_returned>0` and `verified>0`). Earlier smoke (old single-call design) returned 0 citations -> redesign.
- Fresh 30+ candidate / 8+ family live scan not run => no valid global winner.
- Not Windows-verified; no prototype (no leader); no UI; user-fit overlay not built (needs owner facts).

## Next
0. OWNER: top up Anthropic credits. 1. Dispatch `mode=full` with `resume=run_20261010_031655` (re-screens the pool with protocol 2; discovery is NOT paid again). 3. Read REPORT.md, calibrate gates honestly (never manufacture a winner), repeat for stability. 4. Phase E only if a leader exists.
Owner-gated: paid spend, publication, outreach, purchases, credentials, legal commitments. Not a lawyer: ToS compliance claims are design intent, not legal advice.
