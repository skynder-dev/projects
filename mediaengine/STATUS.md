# MediaEngine status

Updated: 2026-10-11 (UTC). Costs so far: $0 (GitHub-hosted Actions minutes only).

## Baseline (verified on the owner PC, D:\Archivist)

| Item | Status | Evidence |
| --- | --- | --- |
| Stable app 3.12.42 installed | ACCEPTED, untouched | 43/43 files = release zip `58122c3a…`; baseline commit `2cde3c7` |
| V52 Auto Edit sidecar `v52-rc1` | ACCEPTED, untouched | 96/96 files = `V52_PAYLOAD_MANIFEST.json` |
| P11 R2 semantic FolderToReel | WINDOWS_PROVEN (engine via CLI/Remote Lab) | command 1214 / report 1264, reel `1a260504…` |
| FAST_LOCAL model + adapter + validator on PC | present, exact hashes | `844d1a46…`, `d7ef56b5…`, `00e14d0d…` |
| P11 shadow UX modules (job/revision/export/home) | MISSING on PC | only JSON acceptance records exist; rebuilt inside the app |

## Candidate 3.13.0-rc1 — Auto Edit inside the app

What exists now (code in `app/archivist/auto_edit.py`, `auto_edit_web.py`, `engine_p11/`):

- **Auto Edit** page in the existing app (nav + Media hub + Home): choose folder (Windows folder dialog or pasted path),
  scan shows usable / damaged / duplicate files and total footage, adaptive length default, only Length / Format / Sound.
- Background job on the bundled engine **R3** (= Windows-proven R2 + output preset, progress file, exclusions, segment
  timeline, candidate pool, damaged/duplicate inputs skipped). Real stage progress, Cancel, Retry.
- Review: player, segment strip, every moment with its source file and source time (Play in reel / View in source),
  exclude moments and rebuild, Make variant (length/format/sound; format/sound-only variants reuse the analysis),
  immutable revisions R001…, Accept / Revert pointer, honest "requested X s, got Y s" note.
- Export only the verified accepted revision: one MP4, Windows-safe name, no overwrite, repeat export is a no-op;
  Open video / Show in folder / Copy path. Projects survive app restart.
- AI model: found in a neighbouring Archivist install, or imported by the user after exact hash validation.
  Without it only the explicitly labelled *Technical only* mode is offered (no silent fallback).
- Side-by-side safety: port 8775 (stable keeps 8765), own desktop shortcut "MediaEngine RC", own archive/exports,
  no update server contact without `updater_config.json`, Remote Lab diagnostics only on an enrolled PC.
- Self-contained Windows package (CPython 3.11.9 + pinned 3.12.42 packages, 68 app files, ~449 MB unpacked),
  start with `Start MediaEngine.vbs`.

### Evidence (Windows, GitHub-hosted runner — not the owner PC)

Run 38112423526 on `ac97da3` (results branch `mediaengine-ci-results`, artifact `MediaEngine-windows-package`):

| Check | Result |
| --- | --- |
| Compile (CPython 3.11) + app startup self-check incl. `/auto` | PASS |
| Engine R3 vs R2: 11 runtime modules + adapter identical, pinned SHAs, all editing decisions | 28/28, reel bytes identical |
| E2E through app routes, 7 videos + damaged + duplicate (30 s Social HD) | 36/36 |
| E2E, 2 videos (adaptive 5 s) | 33/33 |
| Package: launcher start without console → `/api/ping` 3.13.0-rc1, `/auto` 200 | PASS |
| E2E with the packaged Python runtime | 33/33 |
| Screenshots of the real pages in Edge | `auto_home.png`, `auto_setup.png`, `auto_project.png` |

Finding: the accepted V52 segment encoder is not bit-reproducible run-to-run on Linux ffmpeg 6.1 (same call, different
video bytes, same audio); on Windows (imageio-ffmpeg 7.1) R3 and R2 produced identical bytes. Decisions are compared exactly.

## Acceptance matrix (MIGRATION/mediaengine/ACCEPTANCE_MATRIX_RU.md)

PARTIAL = passes on a Windows CI runner with synthetic videos; the owner-PC run is still required.

| Row | Status | Note |
| --- | --- | --- |
| I01 clean launch without terminal | PARTIAL | package launcher on CI runner |
| I02 2 and 7 files, skip damaged | PARTIAL | synthetic fixtures |
| I03 adaptive default, Length/Format/Sound only | PARTIAL | |
| I04 R2 semantic=required started from the GUI | NOT_STARTED | needs owner PC (model not in git) |
| I05 960×540 / 540×960 / 1080×1920 | PARTIAL | 1080×1920 and 960×540 probed; 540×960 rendered, not probed |
| I06 one preset per run | PARTIAL | one MP4 per job by construction |
| I07 15/30/60 and 5 for short footage | PARTIAL | 30 and 5 checked; shortfall shown |
| I08 Sound Source/Auto/Mute | PARTIAL | auto + mute rendered; no loudness listening test |
| I09 selection quality, camera-drop | NOT_STARTED | unchanged R2 logic; human blind review pending |
| I10 player / seek / source links in GUI | PARTIAL | rendered in Edge; user interaction pending |
| I11 manual override | PARTIAL | exclude + rebuild done; trim / reorder / replace not yet |
| I12 variant reuses analysis | PARTIAL | format variant 3× faster, same moments |
| I13 Accept/Revert, immutable revisions | PARTIAL | |
| I14 cancel / resume / crash | PARTIAL | cancel + retry tested; restart marks interrupted jobs Retry-able |
| I15 idempotent repeat, input change isolated | PARTIAL | |
| I16 export verified accepted only, safe name, no overwrite | PARTIAL | |
| I17 restart keeps projects | PARTIAL | process restart in CI |
| I18 originals unchanged, path safety, absent drive | PARTIAL | SHA unchanged, path traversal 404; absent drive not tested |
| I19 offline, no Supabase/GoDog | PARTIAL | no network in Auto Edit; not run with network disabled |
| I20 clean package, no Python in user's hands | PARTIAL | package built and started on CI |
| I21 full-video convert | NOT_STARTED | existing Convert feature not re-verified |
| I22 other real media | NOT_STARTED | |
| I23 public git clean | PARTIAL | baseline scanned for keys/personal paths |

## Next

1. Owner PC: install the package next to `D:\Archivist`, run Auto Edit on real footage with the AI model (I01–I04, I10).
2. Editor: trim (mark-in/out), reorder, replace with another candidate from the pool (I11).
3. Absent-drive and offline tests; 540×960 probe; loudness check (I05, I08, I18, I19).
