# RevEng — resume state (2026-10-09/10 session)

**Objective:** make RevEng an independent, program-driven business-discovery instrument (not chat research, not owner-biased).
**Authoritative:** `reveng_v6_independent`; global winner = none; user-fit OFF for global ranking.

## Done
- Phase A: all 2959 G280 baseline files hash-verified against split manifest (0 missing, 0 bad). Original combined ZIP not reconstructed (not needed); `08` verifier fails only on that missing combined ZIP.
- Reused from frozen G280 (loaded unmodified, hash-pinned in `vendor/g280/VENDOR_MANIFEST.json`): scoring_profiles (weights), untrusted_source_isolation, economics_contract, decision_snapshot, entrant_advantage.
- Built Node engine `src/`: fetch/cache, 6 public-source adapters, Anthropic+OpenAI providers with web search, hard spend guard, engine-side evidence verification (URL fetch + quote check), 5 hard gates, v6 scoring + integrity guard, deep screen (+pessimistic economics), decision logic, report + G280 decision snapshot, checkpoint/resume, Phase-E measurement hook.
- Tests: 36/36 pass (`node --test test/*.test.js`).
- Provisional import of 16 agent-researched candidates (SAS/DEV/ECO/PHY): 0 survive gates (no measured entrant edge vs free/near-free incumbents) — see `data_provisional/import_*/REPORT.md`. Evidence there was NOT engine-verified.

## Decisions / assumptions
- Engine in Node (G280 is JS; 79 modules are Node-requirable) instead of Python; stdlib only.
- Reference entrant (identical for all candidates): solo, US, <=$10k, ~20h/wk, no network/licences. Not the owner.
- Entrant-edge at scan time = modelled hypothesis gate (needs sourced incumbent number, >=25% improvement, falsifier); G280 `entrant_advantage` (needs measured artifact SHA) is applied in Phase E.
- Judged dimension >3 needs a verified cited evidence id, else capped to 3.
- `require_https_incumbent_source` default true.

## NOT done / blockers
- No live provider call and no live source call ever executed (build env: egress closed by org policy, no API key). Live-provider verified: NOT RUN.
- Fresh 30+ candidate / 8+ family scan not run => **no valid global winner (unchanged)**.
- Not Windows-verified. No prototype built (no leader exists).
- Missing from migration bundle: RevEngResearch source (referenced only by hash), Local_V2 / Research_Live_V1 zips.

## Owner-gated next action (paid spend)
Set `ANTHROPIC_API_KEY`, copy `config.example.json` -> `config.json`, set `budget.allow_spend=true`, fill the 3 prices from the provider's price page, keep a cap; then `reveng doctor`, `reveng run --dry-run`, `reveng run`.

## Exact next step after the live run
Read `REPORT.md`; fix any live-API shape issues (first real run is the live verification); if leader/conditional leader: build smallest internal prototype, measure with `reveng measure`, then re-decide.
