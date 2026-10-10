# START HERE - FORGE CLAUDE MIGRATION 01

## Mission
Continue Merch Forge as a real product, not as a sequence of UI experiments or paperwork generators. The system should move useful merch ideas toward production-ready products with the least owner friction possible.

## Authoritative state
- **Current working apex:** `canonical/054_Merch_Forge_DISCOVER_RESEARCH_RC.zip`
- **054 outer SHA256:** `c6ea5f5071310848010a3a3f4e23fb75f4128e985a211ced86a61d61358b8383`
- 054 contains Forge desktop `2.8.0-discover-research`, backend minimum/current `forge-app 0.2.70`, Edge version 75, and read-only `forge.discover_snapshot.v1`.
- **Frozen rollback baseline:** `rollback/050_Merch_Forge_CORE_WORKING_RC.zip`. Do not mutate it.
- Supabase `project_current_state` from 2026-10-03 is stale relative to the Library 051-054 release chain. Do not resume from that older state.

## Critical history that still matters
- 051 put KEEP/EDIT/REGEN/SKIP owner review into the app.
- 052 fixed the root cause of owner buttons remaining disabled after live concept load.
- 053 fixed owner-review localization/null-guard behavior and added explicit EN/RU/ES labels.
- 054 added first-class Discover/Research backed by live read-only Forge data.
- 054 static/package acceptance: **37/37 PASS**. Inner integrity: **50/50 PASS**.
- Native Windows WPF runtime proof for exact 054 bytes has **not** been claimed.

## Work rules
Read `ALEX_AUTONOMOUS_WORK_CONTRACT.md` and all numbered files before changing code. Extract 054 into a new working directory. Never edit the ZIP in place.

## Immediate priority
1. Audit and test exact 054.
2. Verify the 052/053 owner-review click + persistence fix remains intact in 054.
3. Add a safe **research -> concept draft** path inside Forge. No paid image generation or external submission.
4. Improve Portfolio/Performance only after that end-to-end internal path works.
5. Produce a new versioned candidate with tests, manifest, hashes, and a concise owner-review result.
