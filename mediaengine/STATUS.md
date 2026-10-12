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

- **Auto Edit** page (nav, Media hub, Home): choose a folder (Windows dialog or pasted path) **or individual videos**
  (multi-select); scan shows usable / damaged / duplicate files, total footage and size; adaptive length default;
  only Length / Format / Sound. Phone/camera files work: rotated portrait (comes out upright), HEVC .MOV, 60 fps,
  variable frame rate, no audio track, Cyrillic names; too-short or still clips are skipped with a reason.
- **Language**: English or Russian for the whole program — "Русский / English" at the top right of every page and in
  Settings; each Setup run applies the language chosen in it once (in-app switch kept until the next Setup), else
  the Windows language (`i18n.py`, `ru_app.py`, `auto_edit_ru.py`; whole-phrase translation so file names/titles
  are never changed; CI coverage check; the engine's progress lines and sizes (МБ/ГБ) are Russian too).
- **OneDrive cloud-only videos** ("Files On-Demand" placeholders) are recognised from the folder listing and skipped
  with a clear reason instead of being read (reading would make Windows download them); a folder that is only in
  the cloud says how to keep it on the PC. Once downloaded, the same reel is built again with them.
- Code review fixes (2026-10-12): a build left "running" by a crashed app no longer blocks Quit/Restart/switching
  (the first request of the new process marks it interrupted); plain "Export MP4" never writes into the reel's own
  source folder (falls back to Exports); double-clicking Accept / Export no longer breaks Revert or makes a "(2)"
  copy; Technical-only variants of an AI-built reel when the model is gone; choosing more than 64 videos opens their
  folder's day list; "tick the newest" ticks the newest of a day; the self-test's time-out stops its FFmpeg too;
  the AI-model search no longer touches network/card-reader drives; updater rollback never replaces a working
  install with a half-written backup; file names, paths and source labels stay untranslated in Russian.
- Walk-through as a new Russian user (2026-10-12) fixed: a variant with a new length chooses moments again (a
  hand-made selection silently kept the old length); "this version already exists" instead of a silent reload;
  top bar wraps at 1024 px; progress shares follow measured stage times and the final stage says it may take a few
  minutes; versions show the real length; trim times checked in the page (other edits kept); a pasted video path
  works; very short clips flagged; Back buttons on setup/day/comparison pages; the comparison result can accept the
  preferred version; days shown as "14 июля 2026"; Check this PC plays the test reel.
  Second walk-through: clips under 2.5 s are skipped up front (2.0 s phone clips always failed the analysis);
  Activity → Jobs lists reel builds; "Folder above" on the setup page; the editor is hidden while a new version
  builds ("a new version with your edits"); typed trim times checked against the clip's length ("Момент 3: …");
  real reel lengths on cards and in comparisons; error codes shown small under the message; Russian names for
  Staging/Private/Rejected; About says MediaEngine.
- **Recordings without a written length** (browser / screen recorder / OBS after a crash; ffmpeg says
  "Duration: N/A") were listed as damaged and refused by Convert. Now measured by one stream-copy read, listed as
  usable, and the build uses a stream copy with the length filled in, made once in the project cache (`work/
  fixed_inputs`, freed with Free cache; Cancel works while it is made; never for Private media; original
  untouched). Library and Convert read their length the same way.
- Overnight fixes (2026-10-12): Russian decimal comma for numbers with units (5,00 с, 16,8 МБ) that never touches
  file names; a running Library job showed its elapsed time off by the UTC offset (5 h in Chicago); elapsed times
  across a clock change; folder/file names with ' [ ] % & ! # ; = , build fine (E2E).
- **Library checked like a user** (new `tests/library_flow_check.py`, Windows CI, data folder with Cyrillic letters):
  add a folder on Import → every video found → Import + analyse → Library with thumbnails, lengths and item pages →
  smart clips → Private (leaves the Library, original untouched, never in a reel) → archive copy → reject; Library
  pages crawled in Russian. Found and fixed on the way: archive / Staging / Private names lost every Cyrillic letter
  ('_ _ _/_ _ _.MOV'); "Find similar" gave HTTP 500 on a new library; local videos had no length in the Library;
  smart clips failed for recordings without a length; previews could not be written into a folder with non-Latin
  letters on Windows (cv2.imwrite); item page codes (technical_ok, private_forever…) and card sizes (MB) were
  English; the SHA-256 widened the page.
- **Folder window**: the Explorer-style one (address bar, Quick access, paste a path), opening next to the last
  reel's videos; the older tree dialog remains as fallback. Driven by window messages in the Windows unit checks.
- **Check this PC** on Home, in Settings and on Auto Edit (Auto Edit suggests it until a test reel was built here).
- **Big folders**: a folder with more videos than one reel takes (64, e.g. a phone camera roll) shows its shooting
  days (date from names like `VID_20260714_…`, else the file date) — one click per day — and a tick list
  ("tick the newest 64"); a day's reel is named after the day. A camera card picked at its root lists the video
  folders inside (DCIM\100GOPRO, PRIVATE\AVCHD\BDMV\STREAM, PRIVATE\M4ROOT\CLIP; up to 4 levels).
- Without the AI model the user must tick **Technical only** explicitly — no silent fallback, also not for variants.
- Background build with real stage progress (per file during analysis), elapsed time, Cancel, Retry, queued jobs listed.
  Restart/Quit of the app is refused while a reel builds (unless forced).
- Review: player, filmstrip with real frames, every moment with source file and source time. **Editor**: reorder (↑↓), trim in
  source time, replace with another candidate, remove, add; every change is a new immutable revision.
  Variants (length / format / sound) keep the base revision's removed moments and manual edits.
- Accept / Revert pointer; Export only the accepted, verified revision to the default folder or **a folder the user picks**
  (remembered; never into the reel's own source folder); Windows-safe name, never overwrites, repeat = no-op;
  completion screen with Open video / Show in folder / Copy path, also on the project cards. Rename / Archive.
- Files marked **Private** in the library are never used in a reel (also not via an older cached build).
- Side-by-side safety: port 8775 (stable keeps 8765; an unreadable `port.txt` stops the app instead of taking 8765),
  own desktop shortcut "MediaEngine RC", own archive/exports, the package ignores a stray `ARCHIVIST_HOME`,
  no update server contact without `updater_config.json`, Remote Lab diagnostics only on an enrolled PC.
- Self-contained Windows package (CPython 3.11.9 + pinned 3.12.42 packages + app-local VC++ runtime), start with
  `Start MediaEngine.vbs`; Quit button; a double start opens the running copy; a second server on the same port refuses to start.
- **One folder per release** (`MediaEngine-<version>-b<build>`, never extracted over an old one). Projects, database,
  exports and library live outside it in `MediaEngine Data` (next to the first release, remembered in
  `%LOCALAPPDATA%\MediaEngine\data_root.txt`), so a new release opens the same projects. **Rollback** = start the
  previous release folder's `Start MediaEngine.vbs`. Settings and About show the data and program folders.
- Full-video **Convert** (existing feature) checked: whole video, original frame rate, every frame, portrait upright.
- **HDR phone video** (iPhone HLG / Dolby Vision 8.4, HDR10 PQ) comes out in normal colours (reel and Convert).
- **Blind comparison** of two versions (sides random, versions hidden until the person decides) for the human
  quality review; results listed on the project. **Free cache** per project; estimate of time left while building.
- Library: re-analysing a video keeps clips used in compositions and hand-made crops (before: deleted by cascade).
- Short Russian guide `ПРОЧТИ.txt` in the package.
- Camcorder files: AVCHD `.MTS`/`.M2TS`, `.TS`, `.MPG`, `.3GP` accepted; interlaced video is de-interlaced (Convert too).
- **Check this PC** page: data/program folders, free space, FFmpeg (+ HDR support), AI model, engine libraries
  (numpy / OpenCV / ONNX Runtime load test), long-path setting, and a 5-second test reel from generated clips.
- If an AI-mode build fails, the project offers "Build without AI (Technical only)" instead of leaving the user stuck.
- MediaEngine opens on the Auto Edit projects page; whole reel rendered in one encode (faster); stage times recorded.
- Optional **Russian interface** for the Auto Edit pages (English default); only visible text is translated.
- "Check this PC" can build the test reel **with the AI model** (semantic=required) - one click proves AI mode on a PC.
- Support bundle includes a redacted Auto Edit summary; friendly messages for disk full / access denied / memory.

### Engine R3 vs Windows-proven R2 (documented differences)

The 11 runtime modules, adapter and validator are byte-identical to R2 (CI-checked). The orchestrator differs:

| Change | Why |
| --- | --- |
| Output preset, progress file, exclusions, manual edits, segment timeline, candidate pool | app features |
| Damaged / duplicate / Private inputs skipped and reported | R2 failed or used them |
| A file the analysis cannot use (e.g. a still video) is skipped and reported | R2 failed the whole reel |
| Technical library built only from the current inputs | R2 rescanned every item ever analysed in the work folder → any removed/replaced/Private file broke all later builds (reproduced) |
| Per-file analysis timeout grows with the longest video (≥120 s, ≤6 h) | R2 fixed 120 s would skip long videos; an hour of 4K 60 fps can take over an hour on a slow PC |
| Selection search bounded (≤10 M combinations) | R2/V52 search for a 60 s reel with ≥30 moments would run for hours; ≤30 s reels are searched exactly as in R2 |
| Too little footage → shorter reel + `LIMITED_TOTAL_FOOTAGE` | R2 stopped with `NO_DIVERSE_TARGET_COMBINATION` |
| Two windows of one source overlapping >50 % → keep the better one | avoid showing the same moment twice (affects semantic mode) |
| Damaged cache entries are rebuilt | R2 failed the project permanently |
| Social HD only as vertical 1080×1920 | acceptance presets |
| `--input-list` (chosen files) as well as `--input-dir` | individual videos |
| Technical mode renders from the ORIGINAL at the same source interval (decisions still made on the V12 previews) | R2 rendered from 960-px, 25-fps previews whose sound was re-zeroed separately (soft, juddery, sound up to 45 ms early); AI mode in R2 already cut from the original |
| Each segment's sound fitted to its picture; fades with whole-frame lengths and exact offsets; blocks joined with the concat filter after normalising pixel aspect / time base | R2 let sound drift at every join (0.39 s at the end of a 30 s reel on Windows) and a 3-decimal fade offset could start a fade one frame late |
| HDR sources converted (HLG direct, PQ tone-mapped) when cutting from the original | grey/dark colours from 10-bit HDR phone video |
| Long-named videos (Windows long paths off) analysed under a short stand-in name; camcorder transport streams analysed as an MP4 remux; interlaced video de-interlaced | analysis failed (FileNotFoundError / too few frames) or combed picture |
| Technical analysis in parallel groups; whole reel in one encode; sound fitted sample-exactly | speed; exact A/V length |
| Wide pictures stored in narrow pixels (HDV/AVCHD 1440×1080, DVD/DV 720×576/480) widened to square pixels when cut from the original | the accepted render scales stored pixels: a square came out 0.70–0.75 as wide (measured) |
| More input formats: WMV/ASF, FLV, DVD .VOB, JVC .MOD/.TOD, HDV .m2t, DV tape .dv (MPEG-2 program/transport streams analysed through the MP4 remux) | older family footage; checked in CI (robustness "older formats") |
| Hand trims and full-quality recuts read the same stand-in the analysis used (camcorder remux, short name) | a trim cut straight from an .MTS stream gave sound without picture; a long Windows path fell back to the 960-px preview |
| Sound keeps its place in time at the final join (`aresample=async=1:first_pts=0` instead of re-zeroing) | a clip whose sound starts after its picture (cameras, phones) came out with the sound up to 0.6 s early when cut from its start (measured; CI `late_sound_stays_in_place`) |
| Cuts from the original take the first audio track FFmpeg can decode and pad it to the picture's length | an extra track FFmpeg cannot read (e.g. iPhone spatial audio) made every cut fall back to the preview; sound ending before a moment ended gave an empty segment |
| Files the analysis could not use are remembered with their SHA-256 (`ANALYSIS_SKIPPED.json`); analysis groups no longer depend on the number of inputs | one unusable 1 s clip made every later build analyse the whole folder again; adding a video moved others to another group (analysed again) |
| A picture with an odd width or height is analysed and cut from an even-size copy (one pixel smaller) | such a video (cropped in a gallery app) was skipped: H.264 4:2:0 cannot store odd sizes |
| AI-mode moment cache reports the file's current name/place; no 8.3 short-path stand-in (a copy instead); an empty input list is a clear error | a renamed HDR file lost its HDR conversion; the 8.3 path was resolved back to the long name by the analysis |

## Evidence

Windows CI (GitHub-hosted runner — not the owner PC), synthetic videos only, Technical mode (the model is not in git).
Latest full run: **38271654976 on `859ae7d` — all green, build b61** (results branch `mediaengine-ci-results`,
artifacts `MediaEngine-3.13.0-rc1-b61-Setup` and `MediaEngine-3.13.0-rc1-b61` (ZIP)): fast checks 83/83 · R3 = R2
decisions 29/29 · robustness 32/32 · A/V sync worst 20 ms, late-starting sound in place · E2E 7 videos 72/72,
2 videos 74/74 (adds a browser recording without a length, in a folder named with ' [ ] % & ! # ; = ,), phone 67/67,
packaged Python behind the firewall 68/68 · **Library like a user 20/20** (new; data folder with Cyrillic letters) ·
library re-analysis 4/4 · Convert 20/20 · unplugged/no network 9/9 · 64 long names with long paths OFF 5/5 · AI
glue 6/6 · **Russian interface: 148 pages, 0 English texts, 0 network attempts** (every page opened with the internet
blocked) · package smoke PASS · Setup smoke PASS · 4K H.264 + 4K HEVC + 5-min 1080p → 30 s Social HD reel in 397 s.
Same day: b58 (run 38262901710) all green.
Before: b47 (run 38242920327): fast checks 71/71 · E2E 72/72, 72/72, 67/67 · 4K/long footage 359 s.
Earlier: b41 (run 38194029514): fast checks 67/67 · E2E 71/71, 71/71, 66/66 · 4K/long footage 503 s.
Previous green builds: b39 (run 38188906561), b34 (run 38181229982), b28 (run 38156678815), which also showed:
AI glue 6/6 · Convert 20/20 · library 4/4 · unplugged/no network 9/9 · 64 long-named videos with long paths OFF
5/5 (cut from the originals) · package smoke (Cyrillic folder, desktop shortcut points exactly there, data outside,
restart, second copy refused, Quit, the next release started while this one runs takes over, 0 files added to the
release by running it) — these steps run in every build. Checks in every run:

| Check | What it proves |
| --- | --- |
| Compile (CPython 3.11) + app startup self-check incl. `/auto` | release would start |
| `tests/engine_regression.py` | runtime modules identical; R3 makes the same decisions as R2 (technical mode, 2 videos, 15 s) |
| `tests/engine_robustness.py` | still video skipped, Private file ignored with old analysis present, short footage, damaged cache, presets |
| `tests/e2e_auto_edit.py` (7 videos + damaged + duplicate; 2 videos) | the whole user flow through the app routes |
| Package smoke on a copy in a non-ASCII folder | start via `Start MediaEngine.vbs`, updates off, own shortcut, restart, second copy refused, Quit |
| E2E with the packaged Python | packaged runtime renders reels |
| Package unchanged by the checks | the uploaded artifact contains no CI data |

Local Linux run 2026-10-11: engine regression 28/28, robustness 6/6, E2E 7 videos 54/54, 2 videos 47/47.

Also in CI: A/V sync at every cut (flash + beep sources), phone/camera files incl. HDR, Convert, unplugged drive,
no network (app process + packaged Python behind a firewall rule), 64 files with long names on Windows with long
paths OFF, chosen files, export folder, blind comparison, library re-analysis, AI-mode glue with a labelled stub,
4K/long footage build time (measured, not a pass/fail gate).

Not proven by CI: AI selection with the real model, selection quality judged by a person, real camera footage.

## Acceptance matrix (MIGRATION/mediaengine/ACCEPTANCE_MATRIX_RU.md)

PARTIAL = passes on a Windows CI runner with synthetic videos; the owner-PC run is still required.

| Row | Status | Note |
| --- | --- | --- |
| I01 clean launch without terminal | PARTIAL | Setup → Start-menu "MediaEngine" and `Start MediaEngine.vbs`, both started on the CI runner (Cyrillic folders) |
| I02 2 and 7 files, skip damaged | PARTIAL | synthetic fixtures; still video skipped |
| I03 adaptive default, Length/Format/Sound only | PARTIAL | |
| I04 R2 semantic=required started from the GUI | NOT_STARTED | needs owner PC (model not in git); one click: Check this PC → test reel with the AI model; AI glue tested with a labelled stub |
| I05 960×540 / 540×960 / 1080×1920 | PARTIAL | all three probed in E2E |
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
| I18 originals unchanged, path safety, absent drive | PARTIAL | unplugged source drive tested (project says so, nothing deleted, export works, builds again when back) |
| I19 offline, no Supabase/GoDog | PARTIAL | app process blocked from non-loopback in tests; packaged Python behind a firewall rule on Windows CI |
| I20 clean package, no Python in user's hands | PARTIAL | per-user Setup.exe (no admin) and ZIP; uninstall keeps the data; switching builds; old builds removable |
| I21 full-video convert | PARTIAL | Windows CI: 1440p60 → 1080p keeps fps and every frame; portrait upright; HDR colours |
| I22 other real media | PARTIAL | synthetic phone/camera files (rotation, HEVC, VFR, HDR, camcorder MTS, 4K, 5-min 1080p, HDV/DVD wide pixels, 18 more formats); real camera footage pending |
| I23 public git clean | PARTIAL | |

## Deferred / waiting

- `/media` file routes serve Private items to the local owner UI only (loopback + Host check) — kept by design (D17).
- Per-cut sync on real camera footage (synthetic flash/beep: within ±7 ms; also checked on Windows CI).
- Owner-PC run with the AI model and human review of selection quality (blind comparison is built in).
- Owner decisions: private repo with the model for CI (AI mode in CI); publishing builds as GitHub Releases
  (public) instead of 90-day CI artifacts.

## Next exact action

Owner: download the newest `MediaEngine-3.13.0-rc1-b<N>-Setup` artifact and run the Setup (or the ZIP: unblock +
extract next to `D:\Archivist`), start "MediaEngine" from the Start menu, open "Check this PC" → "Build a test reel
with the AI model", then make a reel from a real folder.
