# G281 overlay (RevEng app improvements)

The frozen G280 package is not stored here (52 MB zip, owner's original). This folder holds only what G281 adds or changes: `files/` mirrors the package paths; `files/docs/REVA2_G281_OVERLAY_MANIFEST.json` lists every added/modified file with SHA-256.

    ./apply_overlay.sh <extracted G280 dir> <new G281 dir>

The script refuses to run if the modified file (`app/index.html`) differs from frozen G280, copies the overlay, and runs `verify_reva2_g281_overlay.py` (lineage + all G281 tests). Needs node 20+, Python 3 with Playwright and Chromium at `/usr/bin/chromium` for the page test.

What it contains and what was found: `files/docs/REVA2_G281_GLOBAL_PATH.md`. Scan 2 and 3 results (all killed, no winner): `files/docs/REVA2_G281_SCAN2_REPORT_RU.md`.
Owner-gated and NOT done: writing to Supabase, paid provider calls, provider choice, native exe, RLS on `public.godog_gdconst_*`.
