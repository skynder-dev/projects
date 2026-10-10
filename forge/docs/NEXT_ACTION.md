# NEXT ACTION

Owner: nothing required.

Autonomous queue (in order):
1. Remaining English in RU/ES: exception texts thrown deep in LocalCore/PrintChecks (shown in error dialogs) and the Performance 'Needs attention' card. Extend `Data/Forge.MessageTranslations.json`.
2. Performance "Leaders / Needs attention": list real linked products (units/royalties per product) and published products without sales. Keep empty states truthful.
3. Cosmetic: duplicated page titles (header + page) and the narrow Discover header at ~1024 px.
4. Owner/backend decision (not autonomous): the live `discover_snapshot` has no note→niche link (the DB `research_notes` table has none either). Drafts therefore get 0 linked notes. Exposing a link needs a forge-app change, which is owner-gated.

Owner-only gates (unchanged): paid generation, publishing/submission, backend write contract for promoting KEEP'd drafts to server ideas.

## Where things live
`skynder-dev/projects` → `forge/`: `app/` = current tree, `releases/` = ZIPs, `archive/` = 054/050, `ci/` = Windows CI, `tools/build_release.py` = release build, `docs/` = these files. CI results: branch `forge-ci-results`.

## Working agreement (owner, 2026-10-09)
- Work directly in `main`. No pull requests, no asking the owner to merge or to approve engineering steps.
- Every push to `forge/**` runs the forge-windows workflow on real Windows. A green run updates **`forge-last-green`**, the safety copy and rollback point. If a run is red, fix it forward immediately; `main` must not stay red.
- The owner is involved only in owner-only gates: paid generation, publishing/submission, backend writes, and creative decisions.
