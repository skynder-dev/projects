# MediaEngine status

Updated: 2026-10-14 (UTC). Costs so far: $0 (GitHub-hosted Actions minutes only).

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
- **AI+ (optional, 2026-10-13)**: a stronger model, PE-Core L/14 (Meta, Apache-2.0, ONNX int8, pinned commit,
  SHA-256 checked), downloaded once on Check this PC; choose AI or AI+ per reel / variant, compare blind. Separate
  engine path (`p13_*`, `--semantic-model pe_core_l14`), the accepted AI path unchanged. See RELEASE_NOTES → AI+.
  **Themes** (AI+): 13 themes (sea, mountains, children, family, celebration, animals, sunset, nature, snow, city,
  food, sport, road trip) - a reel of the matching moments of all the videos; a new theme for analysed videos needs
  no frame looked at again. **Library → Find by theme (AI+)**: each video indexed once from its preview frames,
  instant search (4 ms in CI), opens at the best moment, "Make a reel about this theme"; Private / rejected never
  indexed or shown. Check this PC shows the AI+ speed measured on the PC.
  **Prepare AI+ for the whole Library (2026-10-14)**: one button does the search index and then, in the engine
  (`p13_prepare_scout.py`, below normal priority, overnight-safe), what AI+ reels need for every Library video, into
  the shared cache every AI+ build reads: a later AI+ reel / theme from them looks at no frame (CI: `scout_embed_s` 0).
  Pauses while a reel is built, Stop, continues where it stopped, never looks at Private videos (re-read before every
  video), camcorder streams / odd sizes / recordings without a length left to the reel.
  Measured (model lab, public photos): COCO photo↔caption — AI+ finds the right photo for a caption 85.5 % (AI 60.2 %;
  original fp32 model 85.8 %, so int8 loses ~nothing); plain landscape scenes — no advantage (86 % vs 89 %).
  Speed (CI runners): 0.4–2.5 s per frame looked at depending on the CPU, up to 48 frames per video; threads tuned
  from lab measurements; what AI+ saw in a video is kept once for all projects.
- **Horizontal Full HD 1920×1080 (2026-10-13)**: a fourth format (TV, YouTube); the R3 refusal of 16x9 + social_hd
  is removed (the engine's own size), robustness check builds it.
- **Own music and a title (optional, 2026-10-13)**: "Music and title" on the new-reel page and for every variant —
  title + second line for the first 3 s, your own song (with the videos' quieter sound or only music; loudness-
  normalised, fades, seamless repeats), all in the reel's single final encode; nothing set = the reel as before.
  **Cuts on the beat (2026-10-14)**, on by default with own music: the beat is found on the PC (`p13_beats.py`), every
  cut and the end move to the beat nearest to their planned place (the reel stays within ~1.5 beats of its length),
  the final encode takes exactly the frames to the beat; no clear beat (drone, speech, a jingle) = cuts unchanged.
  CI: drum songs in AAC (also a short one that repeats) - every cut within 40 ms of a true beat in the result, the
  picture and the reel's sound; real Commons music against librosa: workflow `mediaengine-realmusic`.
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

## Whole-program review (2026-10-14 evening)

The owner asked for a deep review of the whole program with fixes and what is missing. Four review areas (Auto Edit,
Library, engine, install/safety) plus two fresh-eyes reviews of the changes. Done (details: RELEASE_NOTES, section
"Everyday use"): one-step Save MP4, small copy for messengers, reels up to 2 minutes, a reel for every day of a big
folder, Library → Make a reel, whole picture with blurred edges for vertical reels, the same reel with the original
sound, recording time from the video header, delete archived projects, free all caches, switch to another installed
version, the reel being made shown on every page, background test reel, recent folders, project filter, What's new.
Safety: database/settings copies (before a new build opens them, daily), missing data folder / damaged database
banner, settings written safely. Faster variants with identical output (hash, camera-drop, segment-length and
moment-choice caches). Found and fixed before any release: `Referrer-Policy: no-referrer` made every form button fail
in a real browser (new real-browser check in CI, Edge); FFmpeg's final encode of a beat-synced reel stood still now
and then on Windows (now watched and run again; faulthandler dumps in long checks showed where).

## Owner PC test of b100 (2026-10-14 night, through the app's own pages in the desktop app's browser pane)

Owner PC: 16 logical cores, 69 GB RAM, Windows 10.0.26300, FFmpeg 7.1 (gyan). Worked: "Download the AI model",
AI test reel (32.1 s), a 30 s Horizontal Full HD AI reel from `D:\100MEDIA` (18 drone videos 4K, 29 GB; 12 used,
6 moments, sound off by Auto - no useful sound in drone videos), Save MP4 (68.9 MB, checked against the version).
A vertical variant of it took 2 min 18 s (analysis reused), the crop of the drone footage is fine; "Small copy for
messengers" works. Found: the AI analysis took 64 min, one video after another; measured here, cutting the 8 moment clips per video
from 4K (x264 `fast`) was most of it -> next build: `veryfast`/crf 16 clips (1.9-2.2x faster, picture not worse)
and up to 3 videos at once (a copy of a video is analysed once - two threads once wrote the same file). Five 1-2 s
drone clips were "could not be analysed" (the folder page said "too short") -> "too short". The replace list showed
the same window twice -> one line.

## Owner PC test of b113 (2026-10-15)

First AI reel from `D:\100MEDIA` (18 drone videos 4K, 30 s horizontal): **42 min** (b100: 64 min), the same 6 moments.
Worker time (3 videos at once): candidate clips cut in 4K 4002 s, AI analysis 1353 s, measuring clips 418 s; stages:
inputs 50 s, analysis 38 min, select 39 s, boundaries 70 s, pieces 33 s, joining 25 s. A second project from the same
folder (vertical 30 s): **2 min 16 s** (analysis 9 s, 93 clips from the shared cache). Next (b114): candidates as
previews, the reel cut from the originals.

## Owner PC test of b117 (2026-10-16 night)

A reel from `D:\100MEDIA` (30 s horizontal, AI; the AI reports of b113 were in the shared cache, the previews new):
**18 min 27 s** (b113: 42 min, b100: 64 min). Stages: inputs 23 s, analysis 15.5 min - all of it cutting the 90
previews (908 s), one video after another, the 16-thread PC 42 % busy; measuring 21 s, select 31 s, boundaries 7 s,
pieces 93 s, joining 21 s. Fixed after it (b119): videos analysed before go three at once too, and count as new work
until their clips are made; AI+ cuts a video's clips three at once.
Then from scratch (shared cache freed): **Prepare in advance** (AI, 30 s) 17 min 53 s; the reel after it **54 s**
(analysis 1 s, pieces 27 s, joining 21 s) - the same 6 moments as the reel above. An AI+ variant with the theme
"Aerial view (drone)": 35 min (AI+ frames + model 758 s, ranking with the closer look 283 s, 85 previews cut one
after another 866 s - three at once since b119); its 6 moments all from above (looked at on the filmstrip), as
are the AI reel's - the owner's videos have little take-off or landing in them.

## Owner PC test of b121 (2026-10-16 evening)

Check this PC: graphics card NVIDIA GeForce RTX 3060; "Test the graphics card": not used - one cut alone 0.8x the
processor (16 threads, idle). Prepare in advance from scratch on `D:\100MEDIA` (AI, 30 s): **19 min** (b117: 17 min 53
s) - inputs 54 s (the SHA-256 of 29 GB again: the shared cache was freed), analysis 16 min, clip edges and pieces 74
s; worker time (3 videos at once): previews 1525 s, the accepted analysis 1196 s (frames 468 s, the closer look at the
best three windows 689 s, the model 18 s), measuring 27 s; **the processor 96 % busy**. The reel after it: **48 s**.
So the processor is the limit; b122 tests the card with several cuts at once (as in a build).
b122 on the owner's PC (2026-10-17 night), "Test the graphics card" with 4 cuts at once: every frame identical with
`cuda`, `d3d11va`, `d3d12va` and `dxva2` (all three test clips), but slower than the processor under load too
(0.66-0.85x; H.264: 4 cuts 3.3 s on the card vs 2.1 s on the processor) - not used. The full 4K frames have to come
back to the processor for the accepted scaling; the card does not pay here.

## Evidence

Windows CI (GitHub-hosted runner — not the owner PC), synthetic videos only, Technical mode (the model is not in git).
Latest full run: **38983106755 on `c564596` (2026-10-17) — all green, build b122**: as b121, plus the graphics-card
test under load (several cuts at once) and its whole result for support.

Previous: **38891840332 on `7944b86` (2026-10-16) — all green, build b121**: as b120, plus "cut with the
graphics card" next to the build time of a version cut with it. Drone check on the same code (run 38891868446):
15/15; AI+ prepare of the 10 Commons drone videos 603 s (was 961-1011 s: AI+ clips three at once), the reel after it
22 s; the AI reel 238 s (was 324-330 s). Real-footage check on the same code (run 38891901637, 22 Commons videos):
10/10 - AI 30 s 455 s, AI+ 30 s 1284 s, AI+ theme reels (kids, sea, animals, party) 42-95 s.

Previous: **38877326081 on `efdc956` (2026-10-16) — all green, build b120**: as b119, plus decoding on the
graphics card where the PC proves it (unit 119/119 on Windows: the real test on the runner's Hyper-V adapter found no
usable method - `dxva2` "decoded" by falling back to the processor, 1.0x, not used; AI glue 20/20 with the failing
method and with the card's code path `-hwaccel none`: every preview byte-identical), the first choice of moments on
several cores (400 random cases + the largest 30 s search identical to the accepted function: 18.8 s -> 10.9 s on 2
workers; the packaged-runtime E2E 76/76 with the search forced onto worker processes), prepare in advance for every
day. 4K/long AI on this runner: first project 541 s, a second one 123 s.

Previous: **38856904315 on `6343e9a` (2026-10-16) — all green, build b119**: as b117, plus the full-quality
recut with x264 ultrafast (b118: pieces 65 s instead of 109 s on the same kind of runner), videos analysed before cut
their clips three at once (AI glue 18/18 with the new "reports kept, clips gone" build), AI+ clips three at once, the
timing of a preparation on its card.

Previous: **38812143542 on `c08edcc` (2026-10-15) — all green, build b117**: as b114, plus Prepare in advance
(E2E 7 videos 78/78 and 2 videos 83/83 with prepare then build: the build's analysis 0.02-0.04 s; AI glue 17/17: the
build after preparing analyses, cuts and measures nothing, the same reel), the AI+ theme Aerial view (drone), the
choice of moments and probe results shared across projects, where the accepted AI analysis spends its time. 4K/long
AI on this runner: first project 382 s (worker time: frames looked at 171 s, closer look at the best three windows
185 s, model 6 s, preview clips 151 s), a second project 100 s. Drone check on 10 Commons drone videos (run
38814688890, ground parts pinned): 15/15, no pick on the ground; prepare 1011 s, the reel after it 28 s.

Previous: **38795441766 on `9d5e6c7` (2026-10-15) — all green, build b114**: AI / AI+ candidates as previews
(at most 960 px), the reel cut from the originals. 4K/long AI, first project: **606 s** (b113: 963 s) - analysis 424 s
instead of 766 s (worker time: candidate clips 180 s instead of 637 s, measuring them 7 s instead of 84 s), boundary
check 7 s instead of 65 s, pieces 109 s instead of 58 s (now cut from the 4K originals); the runner's 4 cores busy 99 %
while finding moments. A second project from the same videos: 174 s. Next on `d2453f0`..`7528ee2`: Prepare in
advance, the AI+ theme Aerial view (drone), the choice of moments and probe results shared across projects.

Previous: **38737154855 on `a66dfd4` (2026-10-15) — all green, build b113**: as b110, plus the pieces of a
reel cut up to three at once (AI glue 14/14 with the "three at once" build, E2E 2 videos 80/80 cutting three at once),
the building page mentions the notification. (b112 failed only on a missing Russian progress text; fixed.)

Previous: **38719705555 on `b309ad2` (2026-10-15) — all green, build b110**: as b109, plus picture signatures
remembered; 4K/long AI: first project 824 s, a second project from the same videos 108 s (analysis 1.5 s, boundary
check 2.3 s instead of 34 s).

Previous: **38704652129 on `8f6a15c` (2026-10-15) — all green, build b109**: as b108, plus clip boundaries
in one pass (CI glue: the same rows as the accepted seeks with the app's OpenCV); 4K/long AI on a slower runner:
first project 863 s (trim 71 s instead of 139 s), second project 146 s (analysis 1.4 s).

Previous: **38693512243 on `59099a0` (2026-10-15) — all green, build b108** (artifacts
`MediaEngine-3.13.0-rc1-b108-Setup` and ZIP): as b105, plus AI mode with the real model on the 4K/long footage -
3 videos (two 4K, one 5-min 1080p) on the 4-core runner: 666 s, two at once through one shared model session; a second
project from the same videos: analysis 1.2 s instead of 450 s (shared cache), the same moments.

Previous: **38682362436 on `6d61d30` (2026-10-15) — all green, build b105** (artifacts
`MediaEngine-3.13.0-rc1-b105-Setup` and ZIP): fast checks 106/106 (incl. a Windows notification shown on the runner) ·
R3 = R2 29/29 · robustness 32/32 · AI glue 11/11 (one by one = three at once, shared cache: a new project analyses and
cuts nothing, an older project hands its files over) · AI+ glue 21/21 · E2E 75/75, 80/80, 70/70 · titles and music
40/40 · Library 38/38 · real models 17/17 · Russian 156 pages, 0 English, 0 network · Edge 11/11 · package smoke PASS
(switching builds: the next build's launcher no longer stops at the previous one's lock) · Setup smoke PASS
(Start-menu shortcut with the app id for notifications) · 4K/long footage.

Previous: **38639054567 on `a620e0a` (2026-10-14 evening) — all green, build b100** (results branch
`mediaengine-ci-results`, artifacts `MediaEngine-3.13.0-rc1-b100-Setup` and `MediaEngine-3.13.0-rc1-b100` (ZIP)): fast
checks 101/101 · R3 = R2 29/29 · robustness 32/32 · E2E 75/75 (7 videos), 80/80 (2 videos + files), 70/70 (phone) ·
titles, own music, beat cuts, blurred edges 40/40 · Library 38/38 · AI+ glue 21/21 · real models 17/17 · Russian 156
pages, 0 English, 0 network · real browser (Edge) 11/11 · package smoke PASS (incl. switching builds) · Setup smoke
PASS · 4K/long footage 5/5. Big Library (600 videos, run 38624456914): every page under 1 s, a theme reel 3.2 s.

Previous: **38575715807 on `762f1d5` (2026-10-14) — all green, build b89** (results branch
`mediaengine-ci-results`, artifacts `MediaEngine-3.13.0-rc1-b89-Setup` and `MediaEngine-3.13.0-rc1-b89` (ZIP)): fast
checks 94/94 · R3 = R2 29/29 · robustness 32/32 · E2E 72/72 · titles, own music and cuts on the beat 39/39 · Library
37/37 · AI+ glue 21/21 · real models 17/17 (the AI model downloaded by the app itself into its data folder, 7 s;
prepare AI+ for the Library, then an AI+ reel looks at no frame) · Russian 152 pages, 0 English, 0 network · package
smoke PASS · Setup smoke PASS · 4K/long footage 347 s.
b89 (owner, 2026-10-14): MediaEngine keeps everything in its own folder - Setup installs into `D:\projects\medeng`
(nothing at the root of D:), the AI model is downloaded by the app into `MediaEngine Data\models` ("Download the AI
model", 30 MB), no Archivist folder is used. Launcher: a patient check for a running build fixes the flaky
"switch to the next release" (b80, b88).
b82 / b83 failed one check on Windows (a picture cut one frame off the beat): the Windows FFmpeg build can start a
segment one frame late; found with the manual probe workflow `mediaengine-probe`, fixed in b85.
**Real music** (`mediaengine-realmusic`, 14–18 public Commons recordings): MediaEngine's beats against librosa's -
median agreement 1.0 on tracks with a clear beat (mean 0.86; one off-beat lock on a disco track, one rock track at
2/3 of librosa's tempo); reels with that music: every cut on a beat.
**Big Library** (run 38534200173, 600 videos): 12/12 - preparing AI+ for the whole Library (stand-in model) 396 s,
status of the Library card 42 ms, search 40 ms.
**Real footage** (`mediaengine-realfootage`, 22 pinned public amateur videos from Wikimedia Commons, free licences,
never the owner's): before / after the AI+ tuning of 2026-10-13 — general AI+ reel: twigs and a promo graphic gone,
now mountain view, children, parade, two wedding dances, sunset; themes kids / sea / party 3 of 3 fitting, animals
from 2 of 3 to 3 of 3; a new theme over the 22 videos 60–117 s instead of 218–345 s. Sheets + attribution: branch
`mediaengine-realfootage-results`; reels: artifact `real-footage-reels`.
**Big Library** (`mediaengine-scale`, run 38473553220, 600 videos in one camera folder): 11/11 — scan 2 s, Import +
analyse 1.08 s per video, Library pages under 1 s, the whole folder's day list 0.2 s, AI+ search preparation 442 s
(stand-in model; previews), search 68 ms, database 11.7 MB.
Same day, all green too: b75 (run 38380700935), b71, b69, b66.
Model lab (`mediaengine-model-lab`, run 38373248463): COCO caption→photo R@1 AI+ 0.855 / AI 0.602 / original fp32
0.858; Intel scenes top-1 theme 0.86 / 0.89 / 0.88; speed matrix (threads, two sessions, batch 2 refused).
Before: b62 (run 38279572931): fast checks 83/83 · Library 20/20 · Russian 148 pages · 4K/long footage 366 s.
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
| I01 clean launch without terminal | PASS (owner PC) | owner installed b100 with Setup and started it himself (2026-10-14); CI: Start menu and `Start MediaEngine.vbs` in Cyrillic folders |
| I02 2 and 7 files, skip damaged | PARTIAL | synthetic fixtures; still video skipped |
| I03 adaptive default, Length/Format/Sound only | PASS (owner PC) | b117, `D:\100MEDIA` (27 min of 4K): "30 s · recommended", only length, format, sound and the way of choosing |
| I04 R2 semantic=required started from the GUI | PASS (owner PC) | b100: the app downloaded the model, AI test reel 32.1 s, AI reel from 18 real 4K drone videos (64 min, then the speed work of b101+) |
| I05 960×540 / 540×960 / 1080×1920 | PASS (owner PC) | owner PC: 1920×1080, 1080×1920 and 540×960 (b117, 2026-10-16: the 540×960 variant probed 540×960, 30.0 s) from real 4K; all four in E2E |
| I06 one preset per run | PASS (owner PC) | every version one format (project 5 on the owner's PC: R001 1920×1080, R004 540×960, R005 60 s 1920×1080) |
| I07 15/30/60 and 5 for short footage | PASS (owner PC) | owner PC b117: 30 s and a 60 s variant of 13 moments, 59.9 s, in 3 min 19 s (choice 13 s); shortfall shown (E2E) |
| I08 Sound Source/Auto/Mute | PARTIAL | applied sound shown; no loudness listening test |
| I09 selection quality, camera-drop | NOT_STARTED | human blind review pending |
| I10 player / seek / source links in GUI | PASS (owner PC) | b117 in the app's own browser pane: the reel plays, "show in reel" seeks (14.2 s asked, playing from there), video served with byte ranges (206) |
| I11 manual override | PASS (owner PC) | b117: a moment removed and another moved up on the page -> R003 has exactly that order, built in 39 s; trim/replace/add in E2E |
| I12 variant reuses analysis | PASS (owner PC) | vertical variant of the 18-video AI reel in 2 min 18 s (analysis reused); keeps removed moments and edits |
| I13 Accept/Revert, immutable revisions | PASS (owner PC) | b117: accept R001, accept R004, "go back" -> R001 again; versions kept |
| I14 cancel / resume / crash | PASS (owner PC) | b117: a build cancelled while checking clip edges -> cancelled, nothing published; Retry -> done in 27 s; restart marking interrupted jobs in E2E |
| I15 idempotent repeat, input change isolated | PASS (owner PC) | b117: the same variant asked again -> "This version already exists", no new job; Private change forces a new build (E2E) |
| I16 export verified accepted only, safe name, no overwrite | PASS (owner PC) | Save MP4 68.9 MB "checked: exactly the accepted version"; small copy for messengers |
| I17 restart keeps projects | PARTIAL | |
| I18 originals unchanged, path safety, absent drive | PARTIAL | unplugged source drive tested (project says so, nothing deleted, export works, builds again when back) |
| I19 offline, no Supabase/GoDog | PARTIAL | app process blocked from non-loopback in tests; packaged Python behind a firewall rule on Windows CI |
| I20 clean package, no Python in user's hands | PARTIAL | per-user Setup.exe (no admin) and ZIP; uninstall keeps the data; switching builds; old builds removable |
| I21 full-video convert | PARTIAL | Windows CI: 1440p60 → 1080p keeps fps and every frame; portrait upright; HDR colours |
| I22 other real media | PARTIAL | owner PC: 18 real DJI 4K drone videos (29 GB, 1-2 s shots skipped as too short); synthetic phone/camera files (rotation, HEVC, VFR, HDR, camcorder MTS, 5-min 1080p, wide pixels, 18 more formats) |
| I23 public git clean | PARTIAL | |

## Deferred / waiting

- `/media` file routes serve Private items to the local owner UI only (loopback + Host check) — kept by design (D17).
- Per-cut sync on real camera footage (synthetic flash/beep: within ±7 ms; also checked on Windows CI).
- Human review of AI selection quality on the owner's own footage (blind comparison is built in).
- Owner decision (not asked again): a private repo with the model for CI (AI mode in CI).

## Next exact action

Owner: b117 installed and measured (see above). Newest: `MediaEngine-3.13.0-rc1-b122-Setup` (run 38983106755, link sent 2026-10-16 evening); after
installing it: Check this PC -> "Test the graphics card" (a minute or two), then a reel from `D:\100MEDIA`. Then (through the app's pages in the desktop app's browser pane,
never computer use): a reel from `D:\100MEDIA` timed against b113's 42 min (the AI reports of b113 are reused, the
previews are cut new) and the time breakdown read from the page (`data-timing`); "Prepare in advance" and the theme
"Aerial view (drone)" on his own drone videos.
