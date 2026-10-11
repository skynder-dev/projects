# NEXT ACTION

Owner: nothing required.

Optional decision (yes/no, nothing breaks without it): may the forge-app server be changed so research notes are linked to niches? Without it, research drafts carry 0 linked notes.

Current release: 077 (`forge/releases/077_Merch_Forge_FOURTH_REVIEW_RC.zip`). Main is green on Windows; `forge-last-green` = main.

Possible next work (not started, owner may reprioritise):
- First real use by the owner: one real idea through artwork → checks → package → manual upload → receipt → sales CSV; fix whatever real data shows.
- Real Amazon Merch sales export sample → confirm the column names (CSV import is tolerant, but unverified on a real file).
- Remaining rare English technical notes in RU/ES.

Owner-only gates (unchanged): paid generation, publishing/submission, backend writes, creative acceptance.

## Where things live
`skynder-dev/projects` → `forge/`: `app/` = current tree (+ `HOW_TO_USE_RU.txt`), `releases/` = ZIPs, `archive/` = 054/050, `ci/` = Windows CI (window phases, install test), `tools/build_release.py` = release build, `docs/` = these files. CI results: branch `forge-ci-results`.

## Working agreement (owner, 2026-10-09)
- Work directly in `main`. No pull requests, no asking the owner to merge or approve engineering steps.
- Every push to `forge/**` runs forge-windows on real Windows. Green → `forge-last-green` is updated (safety copy). Red → fix forward immediately.
- The owner is involved only in owner-only gates.
