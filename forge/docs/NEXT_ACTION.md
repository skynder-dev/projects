# NEXT ACTION

Owner: nothing required. Merge the open pull request when convenient; everything is already tested on Windows by CI.

Autonomous queue (in order):
1. **Provider pipeline self-test failure on Windows** — find why the owner-attested Amazon profile produces no policy-profile binding on PS 5.1 (probably date/culture or JSON shape). It affects the Checks → Publish path that comes after artwork.
2. **Stage 4 Portfolio/Performance** — the first useful read/decision surface: owner decisions per niche (KEEP/EDIT/REGEN/SKIP, drafts vs server ideas) and receipt-verified sales. Add CI window checks + screenshots for it.
3. Cosmetic: Discover header layout at ~1024 px and the duplicated title (only if cheap; functional work first).

Owner-only gates (unchanged): paid generation, publishing/submission, backend write contract for promoting KEEP'd drafts to server ideas.

## Where things live
`skynder-dev/projects` → `forge/`: `app/` = current tree, `releases/` = ZIPs, `archive/` = 054/050, `ci/` = Windows CI, `tools/build_release.py` = release build, `docs/` = these files. CI results: branch `forge-ci-results`.
