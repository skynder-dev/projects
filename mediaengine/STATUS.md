# MediaEngine status

Updated: 2026-10-11 (UTC). Costs so far: $0 (GitHub-hosted Actions minutes only).

## Baseline (verified on the owner PC, D:\Archivist) — unchanged

| Item | Status | Evidence |
| --- | --- | --- |
| Stable app 3.12.42 installed | ACCEPTED, untouched | 43/43 files = release zip `58122c3a…`; baseline commit `2cde3c7` |
| V52 Auto Edit sidecar `v52-rc1` | ACCEPTED, untouched | 96/96 files = `V52_PAYLOAD_MANIFEST.json` |
| P11 R2 semantic FolderToReel | WINDOWS_PROVEN (engine via CLI/Remote Lab) | command 1214 / report 1264, reel `1a260504…` |
| FAST_LOCAL model + adapter + validator on PC | present, exact hashes | `844d1a46…`, `d7ef56b5…`, `00e14d0d…` |
| P11 shadow UX modules (job/revision/export/home) | MISSING on PC | only JSON acceptance records exist; rebuilt inside the app |

Known defects of the **stable** 3.12.42 found by the deep review (stable is not changed; fixed only in the candidate):
Private forever could move the user's original file; Remove from Library left the copy in place; a duplicate could be
imported when the first copy no longer existed locally; watchdog ages were wrong in UTC−x time zones; scene detection
filter never matched; partial export/convert files could be left or overwritten.

## Candidate 3.13.0-rc1 — Auto Edit inside the existing app

What a user can do (code: `app/archivist/auto_edit.py`, `auto_edit_web.py`, engine `engine_p11/p11_folder_to_reel_r3.py`):

- **Auto Edit** page (nav, Media hub, Home): choose a folder (Windows dialog or pasted path); scan shows usable /
  damaged / duplicate files, total footage and size; adaptive length default; only Length / Format / Sound.
- Without the AI model the user must tick **Technical only** explicitly — no silent fallback, also not for variants.
- Background build with real stage progress (per file during analysis), elapsed time, Cancel, Retry, queued jobs listed.
  Restart/Quit of the app is refused while a reel builds (unless forced).
- Review: player, segment strip, every moment with source file and source time. **Editor**: reorder (↑↓), trim in
  source time, replace with another candidate, remove, add; every change is a new immutable revision.
  Variants (length / format / sound) keep the base revision's removed moments and manual edits.
- Accept / Revert pointer; Export only the accepted, verified revision (Windows-safe name, never overwrites, repeat = no-op);
  Open video / Show in folder / Copy path, also from the project cards on the Auto Edit home page. Rename / Archive.
- Files marked **Private** in the library are never used in a reel (also not via an older cached build).
- Side-by-side safety: port 8775 (stable keeps 8765; an unreadable `port.txt` stops the app instead of taking 8765),
  own desktop shortcut "MediaEngine RC", own archive/exports, the package ignores a stray `ARCHIVIST_HOME`,
  no update server contact without `updater_config.json`, Remote Lab diagnostics only on an enrolled PC.
- Self-contained Windows package (CPython 3.11.9 + pinned 3.12.42 packages + app-local VC++ runtime), start with
  `Start MediaEngine.vbs`; Quit button; a double start opens the running copy; a second server on the same port refuses to start.

### Engine R3 vs Windows-proven R2 (documented differences)

The 11 runtime modules, adapter and validator are byte-identical to R2 (CI-checked). The orchestrator differs:

| Change | Why |
| --- | --- |
| Output preset, progress file, exclusions, manual edits, segment timeline, candidate pool | app features |
| Damaged / duplicate / Private inputs skipped and reported | R2 failed or used them |
| A file the analysis cannot use (e.g. a still video) is skipped and reported | R2 failed the whole reel |
| Technical library built only from the current inputs | R2 rescanned every item ever analysed in the work folder → any removed/replaced/Private file broke all later builds (reproduced) |
| Per-file analysis timeout grows with the longest video (≥120 s, ≤1 h) | R2 fixed 120 s would skip long videos |
| Selection search bounded (≤10 M combinations) | R2/V52 search for a 60 s reel with ≥30 moments would run for hours; ≤30 s reels are searched exactly as in R2 |
| Too little footage → shorter reel + `LIMITED_TOTAL_FOOTAGE` | R2 stopped with `NO_DIVERSE_TARGET_COMBINATION` |
| Two windows of one source overlapping >50 % → keep the better one | avoid showing the same moment twice (affects semantic mode) |
| Damaged cache entries are rebuilt | R2 failed the project permanently |
| Social HD only as vertical 1080×1920 | acceptance presets |

## Evidence

Windows CI (GitHub-hosted runner — not the owner PC), synthetic videos only, Technical mode (the model is not in git):
see the latest run on branch `mediaengine-ci-results` (`latest/RUN.txt`). Checks in every run:

| Check | What it proves |
| --- | --- |
| Compile (CPython 3.11) + app startup self-check incl. `/auto` | release would start |
| `tests/engine_regression.py` | runtime modules identical; R3 makes the same decisions as R2 (technical mode, 2 videos, 15 s) |
| `tests/engine_robustness.py` | still video skipped, Private file ignored with old analysis present, short footage, damaged cache, presets |
| `tests/e2e_auto_edit.py` (7 videos + damaged + duplicate; 2 videos) | the whole user flow through the app routes |
| Package smoke on a copy in a non-ASCII folder | start via `Start MediaEngine.vbs`, updates off, own shortcut, restart, second copy refused, Quit |
| E2E with the packaged Python | packaged runtime renders reels |
| Package unchanged by the checks | the uploaded artifact contains no CI data |

Local Linux run 2026-10-11 of the same tests: engine regression 28/28, robustness 6/6, E2E 2 videos 47/47 (7-video run see CI).

Not proven by CI: semantic (AI) mode, selection quality judged by a person, real long/4K footage, A/V sync measured on
real footage, absent drive, network disabled.

## Acceptance matrix (MIGRATION/mediaengine/ACCEPTANCE_MATRIX_RU.md)

PARTIAL = passes on a Windows CI runner with synthetic videos; the owner-PC run is still required.

| Row | Status | Note |
| --- | --- | --- |
| I01 clean launch without terminal | PARTIAL | `Start MediaEngine.vbs` on CI runner |
| I02 2 and 7 files, skip damaged | PARTIAL | synthetic fixtures; still video skipped |
| I03 adaptive default, Length/Format/Sound only | PARTIAL | |
| I04 R2 semantic=required started from the GUI | NOT_STARTED | needs owner PC (model not in git) |
| I05 960×540 / 540×960 / 1080×1920 | PARTIAL | 540×960 rendered, not probed |
| I06 one preset per run | PARTIAL | |
| I07 15/30/60 and 5 for short footage | PARTIAL | 60 s bounded search unit-checked; shortfall shown |
| I08 Sound Source/Auto/Mute | PARTIAL | applied sound shown; no loudness listening test |
| I09 selection quality, camera-drop | NOT_STARTED | human blind review pending |
| I10 player / seek / source links in GUI | PARTIAL | user interaction pending |
| I11 manual override | PARTIAL | exclude, trim, reorder, replace, add — through app routes |
| I12 variant reuses analysis | PARTIAL | keeps removed moments and edits |
| I13 Accept/Revert, immutable revisions | PARTIAL | |
| I14 cancel / resume / crash | PARTIAL | cancel + retry; restart marks jobs interrupted |
| I15 idempotent repeat, input change isolated | PARTIAL | Private change forces a new build |
| I16 export verified accepted only, safe name, no overwrite | PARTIAL | |
| I17 restart keeps projects | PARTIAL | |
| I18 originals unchanged, path safety, absent drive | PARTIAL | absent drive not tested |
| I19 offline, no Supabase/GoDog | PARTIAL | no network in Auto Edit; not run with network disabled |
| I20 clean package, no Python in user's hands | PARTIAL | |
| I21 full-video convert | NOT_STARTED | existing Convert feature fixed, not re-verified on Windows |
| I22 other real media | NOT_STARTED | |
| I23 public git clean | PARTIAL | |

## Deferred (known, not fixed yet)

- Media Brain rebuild can cascade over the whole library (D7); `/media` file routes still serve Private items to the
  local UI (D17).
- UI polish from the contract §10: accent colour, completion screen, real filmstrip thumbnails.
- A/V sync at every cut on real footage (total audio/video length differs by ~3 ms on a 30 s synthetic reel, now
  checked in E2E; per-cut sync on real footage not measured yet).
- Owner-PC run with the AI model; human review of selection quality.
