# NEXT ACTION

Owner: nothing required.

Autonomous queue (in order):
1. Confirm the live `discover_snapshot` field names (niche id, note→niche link) by reading the deployed forge-app function source / schema **read-only**, and align draft provenance matching with them.
2. Performance screen: the same honesty rules as Portfolio. Sales only from verified receipts plus imported CSV. Show winners and needs-attention from real linked rows; keep empty states truthful.
3. Cosmetic: duplicated page titles and the narrow Discover header at ~1024 px.

Owner-only gates (unchanged): paid generation, publishing/submission, backend write contract for promoting KEEP'd drafts to server ideas.

## Where things live
`skynder-dev/projects` → `forge/`: `app/` = current tree, `releases/` = ZIPs, `archive/` = 054/050, `ci/` = Windows CI, `tools/build_release.py` = release build, `docs/` = these files. CI results: branch `forge-ci-results`.

## Working agreement (owner, 2026-10-09)
- Work directly in `main`. No pull requests, no asking the owner to merge or to approve engineering steps.
- Every push to `forge/**` runs the forge-windows workflow on real Windows. A green run updates **`forge-last-green`**, the safety copy and rollback point. If a run is red, fix it forward immediately; `main` must not stay red.
- The owner is involved only in owner-only gates: paid generation, publishing/submission, backend writes, and creative decisions.
