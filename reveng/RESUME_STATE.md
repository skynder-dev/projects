# RevEng — resume state (2026-10-09/10)

**Objective:** program-driven, independent business-discovery instrument (not chat research, not owner-biased).
**Authoritative:** scoring `reveng_v6_independent`; global winner = NONE until a real scan produces one; user-fit OFF for global ranking.

## Done
- Phase A: 2959 G280 baseline files hash-verified. G280 modules reused unmodified (hash-pinned `vendor/g280/VENDOR_MANIFEST.json`).
- Node engine (`src/`, stdlib only): discover -> resolve evidence -> hard gates -> v6 scoring + integrity guard -> deep screen -> decide -> report. Hard spend guard.
- **Legal-by-design:** no scraping of third-party pages. Fetcher allowlist = official APIs only (HN Algolia, GitHub, StackExchange, npm, iTunes). Evidence comes only from the LLM provider's web-search citations.
- **Two-phase research protocol:** phase 1 (search ON) prose notes + provider citations; phase 2 (search OFF) JSON citing evidence by ref `C#` (provider excerpt = verified) / `S#` (search URL only = search_confirmed). Invented refs dropped. >=2 verified items required by gate.
- Fail-fast discovery (2 consecutive failures abort), diagnostics file, `smoke` command (1 research + 1 JSON call).
- Tests: 44/44 pass (`node --test test/*.test.js`), also in CI.
- GitHub Actions `scan.yml` (repo `skynder-dev/projects`, dir `reveng/`): dispatch `mode=smoke|full`; output on branch `results` (`reveng/runs/console.log`, `smoke_result.json`, `REPORT.md`).

## NOT done
- Live smoke of the two-phase protocol not yet confirmed (need `excerpts_returned>0` and `verified>0`). Earlier smoke (old single-call design) returned 0 citations -> redesign.
- Fresh 30+ candidate / 8+ family live scan not run => no valid global winner.
- Not Windows-verified; no prototype (no leader); no UI; user-fit overlay not built (needs owner facts).

## Next
1. Dispatch smoke; read `results` branch. 2. If ok -> `mode=full` (cap $15). 3. Read REPORT.md, calibrate gates honestly (never manufacture a winner), repeat for stability. 4. Phase E only if a leader exists.
Owner-gated: paid spend, publication, outreach, purchases, credentials, legal commitments. Not a lawyer: ToS compliance claims are design intent, not legal advice.
