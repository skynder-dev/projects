# NEXT ACTION

Owner: nothing required. One optional yes/no is open: may the forge-app server be changed so research notes are linked to niches? (Without it, drafts carry 0 linked notes. Nothing breaks.)

Autonomous queue: see `ROADMAP.md` → "Ход работы" (10-hour plan, blocks 1–10).

Owner-only gates (unchanged): paid generation, publishing/submission, backend writes, creative acceptance.

## Where things live
`skynder-dev/projects` → `forge/`: `app/` = current tree (+ `HOW_TO_USE_RU.txt`), `releases/` = ZIPs, `archive/` = 054/050, `ci/` = Windows CI (window phases, install test), `tools/build_release.py` = release build, `docs/` = these files. CI results: branch `forge-ci-results`.

## Working agreement (owner, 2026-10-09)
- Work directly in `main`. No pull requests, no asking the owner to merge or approve engineering steps.
- Every push to `forge/**` runs forge-windows on real Windows. Green → `forge-last-green` is updated (safety copy). Red → fix forward immediately.
- The owner is involved only in owner-only gates.
