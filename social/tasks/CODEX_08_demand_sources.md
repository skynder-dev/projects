# CODEX_08 — read the pages people actually look up (from analytics.usa.gov demand)

Work alone, in one run, ask nothing. Stdlib only, no paid API, no new dependencies. Open a PR into `social/late-core-20261028`.

## Context
`social/trial/gov_demand.py` writes `demand.json`: ranked official pages (`url`, `host`, `title`, `views_30d`, `channel`).
Today Social builds facts only from USA.gov pages (`social/socialreel/usagov.py`, by page structure: sections, lists,
table rows, program units, each fact with quote, locator, SHA-256). Most demand is on irs.gov, ssa.gov, sba.gov, va.gov, hud.gov.

## Do
1. Add a source `govpage` (`social/socialreel/govpage.py`), same record/claim shape and checks as `usagov.py`, for an allowlist
   of hosts in `social/public_sources_config.json`: www.irs.gov, www.ssa.gov, www.sba.gov, www.va.gov, www.hud.gov,
   www.fema.gov, www.fns.usda.gov, www.medicare.gov. Read the main content area only (skip nav/header/footer/"related" blocks).
   Refuse (clear error, no record) pages that are JS shells, forms, login, payment, tools/calculators, or too little text.
2. `python -m socialreel source --source govpage --url URL --out DIR` (URL must be on the allowlist, https, no query string).
3. `python -I social/trial/demand_pick.py DEMAND_JSON OUT --per-channel 3` : picks top pages per channel that `govpage` or
   `usagov` can read, skips pages already used (list in `social/demand_used.json`), writes `picks.json` (url, channel, views).
4. `concept_trial.py --bundle` must work with govpage bundles unchanged (check it); channel goes from the pick to the card.
5. Offline tests with saved HTML fixtures (at least: one IRS, one SSA, one SBA, one VA page; one refused JS shell; one refused
   form/login page). Full suite must stay green (`python -m pytest social`), core tests untouched.
6. Short note `social/docs/DEMAND.md` (what, how to run, limits). No network in tests.
