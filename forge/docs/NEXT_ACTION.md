# NEXT ACTION

Owner: nothing required.

Autonomous queue (in order):
1. **Sweep for the dictionary pattern**: find every function that returns or stores `[ordered]@{}` and is later read via Get-PropertyValue. Fix and test.
2. **Stage 4 Portfolio/Performance**: the first useful read/decision surface. It shows owner decisions per niche (KEEP/EDIT/REGEN/SKIP, drafts vs server ideas) and receipt-verified sales. Add CI window checks and screenshots for it.
3. Confirm the live `discover_snapshot` field names (read-only) when a safe read path is available.
4. Cosmetic: the Discover header layout at ~1024 px and the duplicated title.

Owner-only gates (unchanged): paid generation, publishing/submission, backend write contract for promoting KEEP'd drafts to server ideas.

## Where things live
`skynder-dev/projects` → `forge/`: `app/` = current tree, `releases/` = ZIPs, `archive/` = 054/050, `ci/` = Windows CI, `tools/build_release.py` = release build, `docs/` = these files. CI results: branch `forge-ci-results`.

## Working agreement (owner, 2026-10-09)
- Work directly in `main`. No pull requests, no asking the owner to merge or to approve engineering steps.
- Every push to `forge/**` runs the forge-windows workflow on real Windows. A green run updates **`forge-last-green`**, the safety copy and rollback point. If a run is red, fix it forward immediately; `main` must not stay red.
- The owner is involved only in owner-only gates: paid generation, publishing/submission, backend writes, and creative decisions.
