# tools

Scripts used to produce 055 in the migration session. They were run in that session's workspace
(paths at the top of each script point there), so treat them as a record of how the release was built.

- `patch055.py`, `patch055b.py` — exact-match source patches applied to the 054 tree (each pattern must match exactly once).
- `build055.py` — manifest/integrity update, static acceptance (49 checks), headless self-test, deterministic ZIP (built twice, compared).

Headless self-test that ships inside the app and runs on Windows too:
`app/Merch_Forge_A5_Current/MerchForgeResearchDraftSelfTest.ps1 -OutputPath <file> [-LegacyPackageRoot <054 inner folder>]`
