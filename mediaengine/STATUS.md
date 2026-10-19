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

## Orders from other programs (2026-10-17)

The owner asked how MediaEngine would do orders from his other programs (for example Social) instead of everything by
hand. MediaEngine side only (no other project touched): `app/archivist/orders.py`, `orders_web.py`, the contract
`app/archivist/ORDERS.md` (also copied into `MediaEngine Data\Orders\`), Auto Edit → **Orders** page and
`/api/auto/orders`. A program puts `Orders\Inbox\<id>\` with `order.json` written last; the running app takes it
(`Received`), does it one at a time and answers with ONE folder that appears complete: `Done\<id>\video.mp4 +
result.json` (SHA-256, checks: H.264, size, length, sound, decoded to the end) or `Failed\<id>\result.json` (code and
reason). Kinds: `render_plan` (pictures / video pieces + a sound track, frame-exact, only files inside the order
folder, plain media files only - playlists refused) and `reel_from_videos` (folder, chosen videos or a Library theme;
a normal Auto Edit project). Start at once or "Wait for my OK"; Run / Reject / Stop / Try again / Delete; an order
interrupted by a restart is done again, one started 3 times without finishing waits for the owner; Quit / Restart /
switching builds ask while an order runs; MediaEngine publishes nothing. Check: `tests/orders_check.py` (44 checks,
incl. 30 bad or unsafe orders refused with the right code) in Windows CI, also with the packaged Python offline.

## Night review (2026-10-17): two independent reviewers, findings fixed

- Orders (before any release): a playlist (`.m3u8`) inside an order could make FFmpeg read any file on the PC → only
  plain media containers, each input opened with the demuxer found at the check; a file in the order folder could pose
  as MediaEngine's notes and point a reel order at one of the owner's projects → notes kept outside the order folder;
  a quoted or `//` network path passed the network guard → normalised first; pictures over 50 MP refused; buttons no
  longer wait for a running render; no half-moved folders; Stop never reported as a render error; ids with `..` work.
- Graphics card (b122): a method that Check this PC called "used" never reached the engine (the load numbers made
  every kind "unproven") → fixed and unit-checked; the test now counts FFmpeg error messages as failures (as the
  engine does), compares every run and every cut done at the same time with the processor's frames, and sees a
  driver changed while the app stays open; the engine gives the card 3 minutes per cut, then cuts on the processor;
  interlaced camcorder video never goes to the card. (On the owner's PC the card is not used: it was slower.)
- Prepare in advance: one piece that cannot be prepared no longer fails the whole preparation; "A reel for every day"
  after preparing goes on in the prepared day projects (no second set of projects); Free cache ends "Prepared" and
  Prepare again really prepares.
- Unused code that could have sent a diagnostics report to the old Supabase lab is switched off (it had no caller).
- Second round (a QA walk-through of the Auto Edit pages and a review of the engine's caches), then a third reviewer
  checking these fixes: moments removed by hand came back in a variant of another length or "Let MediaEngine choose
  again" → remembered with the hand-made selection; "Apply my edits" with nothing changed no longer builds a copy;
  a new reel from a folder prepared in advance continues that project; Back after an error keeps what was typed (and
  re-enables the buttons); a restart (Quit, Update, reboot) only interrupts the running build - waiting builds of an
  overnight set go on at the next start; a folder grown past 64 videos says to pick a day; a refused Save MP4 no longer
  changes the chosen version; times never show "0:60.0"; Free (shared AI data) ends "Prepared" too; paths in messages
  stay untranslated in Russian; odd ids / JSON bodies never give a server error; the test reel waits while a build
  runs; a reel with a video marked Private during its build is not kept and such a version cannot be saved; a reel
  made worse by a passing problem (a time-out, a piece from the small preview) is built once more on request; the cut
  pieces of other projects are kept under 60 GB (never a prepared project's); the engine never cuts one AI+ moment
  twice at once (on Windows that could drop a video) and keys finished segments by their start and crop; a graphics
  card test of b122 is not trusted (test again). Checks: unit 121/121, e2e, orders, browser (all on Linux; Windows CI).
- Fourth round (a second look at the orders, a QA walk-through of the Library): a reel order could still pull a
  Private video in through a manifest saved under a video name → every video and music file of an order is checked
  as a plain media file, and FFmpeg may not even open playlists/manifests while checking; an order whose answer the
  program moved away was done again (also a rejected one) → answered orders are never done again by themselves; one
  order folder Windows cannot move no longer holds up the others; Try again takes a Failed answer back in one step;
  closing the app no longer writes "stopped by owner". Library: "Remove from Library" was undone at every app start
  (an old import backfill ran each time) → once only; "Private forever" now hashes the file as it is now (a replaced
  file kept its old hash) and keeps never-hashed Private files out of reels by path; a copy of a Private video is no
  longer shown (Library, theme search, Best Moments, Make a reel); Make a reel never takes a removed video; "ready for
  N of M" no longer stays short for copies or damaged videos; Free (shared AI data) asks first; odd page numbers and
  ids give no server error; Library search texts in Russian.
- Two cameras' videos with the same file name (DJI_0001.MP4 on each card, from two folders or from the Library) are
  both used in one reel: the second is named "DJI_0001 (2).MP4" in the reel (the engine's input list carries the name;
  the technical analysis looks at it under a stand-in), the source preview finds it; before, the new-reel page asked
  to rename the originals and theme reels silently dropped one. Known, not changed: a video renamed or deleted in a
  Library folder leaves its old Library card (kept on purpose: clips and compositions made from it stay).
- Fifth round (a review of rounds 4 and same names, and of install / update / switching): one app per port from the
  very first moment (a named lock: a second copy started while the first was still checking itself could resume the
  same waiting builds and mark the other's build interrupted); shortcuts follow a new build only once it serves, and
  if a switched-to build cannot start, the launcher starts the previous one again (never nothing running); removing a
  version on Check this PC re-points the shortcuts to the running one. A damaged video in a folder order is left out
  (as in the app) instead of refusing the order; same-named recordings without a written length get separate fixed
  copies; reel names stay the same when one of two same-named cards is unplugged; a same-named video that cannot get
  a stand-in is left out with a reason instead of failing the reel; stand-ins count in the 60 GB piece limit; answers
  the program took are listed with Delete; damaged Library videos really leave "ready N of M"; Private no longer
  downloads cloud-only files to hash them; Private copies hidden in search, similar videos and the start page counts.
  Not changed (old builds cannot be fixed): going back to b122 re-adds removed Library videos (its old start code).
- Day review (2026-10-17, rounds 6-9; each by an independent reviewer, every confirmed finding fixed and checked):
  - Auto Edit lifecycle: a project prepared in advance stays prepared after a cancelled / failed build or an unplugged
    card (New reel reuses it; the cache tidy keeps its pieces); Free and delete-for-good move the folder aside under
    one lock with start_job (an order starting meanwhile wrote into a folder being deleted); the engine's input list
    is split on "\n" only (U+2028 etc. are legal in names) and keeps a reel name's leading space; a reel deleted outside
    the app is built again; an unplugged card's fixed copies are kept; a missing video of an order is left out.
  - Convert / Composer / Settings: Python 3.11's Path.exists() raised for a locked or failing card and one such Library
    row made /convert fail - and the start-up check then refused to start the app → path checks never raise in the app
    process (archivist/__init__.py); two Convert jobs could start at once and share one .part → one transaction, each
    output name reserved; the conversion's FFmpeg dies with the app (Windows job) and is stopped on Quit (the job
    resumes); two-pass logs and half-written files never left; empty reserved names swept at start (also Composer /
    clip export); a Composer render counts as busy; Settings sources only as existing folders, Remove by row and path,
    the archive folder stored as a full path and read by one helper (Private Forever recognised archive copies again).
  - Every place that deletes or moves files: "remove an old version" could delete the owner's clips kept inside that
    version's folder (rmtree, no Recycle Bin) → offered only for a folder holding exactly a release's entries, and not
    when a Library source / a reel's folder / an export folder is inside; Private / Rejected / archive names loop to a
    free name and a move or copy never replaces a different file. Checked safe: Private Forever, Reject, Remove from
    Library, Archive, staging, Auto Edit stand-ins (hard links never written), caches, Orders, launcher / updater.
  - Import from cards and phones: a folder added on a USB stick was walked as "fixed" and the stick again as
    "removable"; an import in between used the card file in place and reported success with no copy → a configured
    folder on a removable drive is a card source and the card is walked once, and a "fixed" file on a removable drive
    is copied; "safe to disconnect" waits for every queued import from cards / phones; the watchdog takes a task that
    still hashes / copies its file for alive (I/O counter), gives a grace period after sleep and never restarts the app
    over a reel, an order, AI+ preparation or a Composer render; a resumed import checks space for what is left; a
    failed copy shows on Import again; a swapped card's file always gets its own row (FAT32 hour shift = same file);
    discovery writes in short transactions; pages never wait for adb; a stalled phone copy is stopped; a phone copy of
    unknown size is checked by the phone's SHA-256.
  - Library AI side (round 10): search failed for good on a catalog past ~32k rows (every unchanged rescan marked every
    row for re-indexing, then one SQL list of all of them overflowed SQLite) → re-indexed 500 at a time and only real
    changes mark a row; "similar videos" rebuilt its whole index in one long write transaction at every request (other
    writers could hit "database is locked") → one query, short batches, reused for 20 s; a moment picture of a Private
    video was served (also to other sites) → refused like its thumbnail; a video replaced in its folder kept the old
    video's moments and length → picture made again, moments and length dropped when the length changed (hand-made
    crops stay when only tags were edited); copies of one video prepared and offered twice → once; OneDrive-only videos
    no longer downloaded by "prepare for reels"; AI+ data of videos that left the Library deleted within a minute;
    theme search no longer re-reads every video's numbers when nothing changed.
  - An independent review of rounds 6-10 found one regression (a folder source on a card relabelled "removable" hid a
    Library used in place) and four smaller issues - all fixed the same day (the card's own walk skips such a folder
    instead; one failed copy no longer hides "safe to disconnect"; moments are dropped only when both lengths are known
    and differ; the search trigger migration runs once in one transaction).
  - First run and models (round 12): a download never writes a proxy / sign-in page over the part already downloaded;
    HTTP 401/404 from huggingface.co is not called "no connection"; a remembered model folder that moved is not
    trusted; a new user gets no "New in this version" list; the PC tests and builds never run at the same time; a
    second test reel works while the first is still open. A build that passed its start-up check once on this PC is no
    longer refused later because of the owner's data (it starts and logs the failing page).
  - Social / Composer / clip pages (round 13; nothing there contacts the network or claims a publication): a copy of a
    Private video still reached the clip page, clip export, Composer and Social → one shared visibility rule
    (`db.VISIBLE_SQL`); a render or export made before its video became Private is no longer listed or served; a
    reordered composition becomes a draft again (its old MP4 was the other order); the results CSV no longer stores
    wrong numbers ("variant_id, views" with spaces, an unquoted 1,234, short rows, nan / inf / 20-digit numbers);
    a CSV within its limit no longer gets a bare 413 page. Known, not changed (manual-publishing lab only): a
    composition recorded in local history is then held by its own record in the queue.
  - Editor and engine (round 14, evening): own music whose length FFmpeg only estimates (raw AAC, a VBR MP3 without
    its header) was cut at the guess and restarted early in the reel → the guess is not used; a double click on Revert
    went back two versions → the button carries the version it was shown for; after an edit or a variant the page
    stays on the version it was made from (it jumped to the accepted one); "Undo accept" stays on that version; time
    fields accept h:mm:ss (as the page shows times of long videos); the blind comparison buttons can be pressed once;
    "Saves to" names the folder Save MP4 really uses. Checks: unit, e2e 81/81 (Revert double click), titles and
    music 40/40, browser 12/12, route fuzz.
  - Unattended overnight use (round 15): a batch queued in the evening is checked again when each build really
    starts (a card unplugged since → "plug it in and press Retry" instead of "no supported video files"; a disk filled
    since → refused up front instead of failing half-way); a build whose engine says nothing for 90 minutes (a hung
    read) is stopped so the rest of the queue goes on; the notification at the end of a batch says how many were made
    and how many failed (it described only the last one); an archived prepared project's pieces may be tidied; AI+ preparation for the Library that the
    app's closing interrupted goes on at the next start (Stop, finished or failed runs do not); the watchdog never
    restarts the app over a reel / an order / AI+ preparation (also after repeated Convert stalls). Known, not changed:
    the app does not start itself after a night reboot (the queue continues when it is opened), and the build that was
    running then is marked interrupted (Retry reuses its analysis).
  - Local web security (round 16; the owner browses the web while MediaEngine runs): no high-severity issue (Host
    allow-list, Origin / Referer checks, no CORS, no framing, file routes confined, no shell). Hardened: a request
    another site's page makes is refused by default (an <img> loop could make the app create thumbnails, ask adb or
    run AI+ searches), only a top-level link to the start pages passes; a write whose browser marks it cross-site or
    same-site is refused even without an Origin header (old browsers); Convert results are escaped in the page.
  - New check `tests/route_fuzz.py`: every route with odd input (huge / Unicode-digit ids, damaged forms and JSON) -
    no server error (it found 7 routes, fixed); in Windows CI on a copy of the 7-video home (non-blocking).
  Checks after the fixes (Linux): unit 135/135, e2e 81/81, orders 49/49, library flow 43/43, library 4/4, convert
  23/23, reliability 9/9, engine robustness, AI / AI+ glue, titles and music 40/40, scale library (600 videos) OK,
  browser 12/12 (it caught one slip of round 12 - a second test reel - fixed before any push), Russian pages 0 English
  left, route fuzz 0 server errors.

## Owner feedback 2026-10-17 evening: the switch question after every install
- The owner closes the MediaEngine window before installing, yet the new build always asked "another MediaEngine is
  running, switch?". Cause: closing the window does not quit the app (it keeps running in the background so a reel
  being built goes on); only Quit does. Fix (launcher_v2 `switch_question`): a NEWER build started while an older one
  runs takes over without a question (the older one is asked to quit as with Quit; if it is building a reel it stays
  and says so); an OLDER build or an unknown folder name still asks, worded "a newer build is running". Unit check
  added (136/136).
- Owner asked (22:52): put MediaEngine in the tray so it can be quit like a normal program. Done:
  `app/archivist/tray.py` (plain Win32 through ctypes, no new package), started by `main.py`. Icon in the
  notification area while the app runs; hover text = version and what runs ("Собирается ролик «…»: 45%");
  click = bring the MediaEngine window to the front (or open one); right-click menu = what runs (greyed),
  Открыть MediaEngine, Выход. Выход when idle quits at once; while work runs it asks (same text as the Quit
  button). Quit from the tray or the in-app Quit button also closes the program's windows (Edge app windows whose
  title ends with " · MediaEngine" - the stable uses " · Archivist", a browser tab adds " - Microsoft Edge");
  a switch to another build does not (the Check-this-PC switch page waits in its window). The icon is removed
  before every exit (Quit, switch, watchdog restart). Once per data folder a hint balloon says where the icon is.
  `web.busy_reason()` is now the one check behind the Quit button, the launcher's switch and the tray.
  Checks: unit 140/140 (window title rule, idle/busy texts; on Windows also the Win32 structure sizes 976/80);
  Windows CI installer smoke now quits the installed app through the tray icon's Quit command and reports the
  icon state (shown / no_taskbar). Not checkable in CI: how the icon and menu look - owner's eyes.
  The desktop shortcut while this build already runs now brings its window to the front (launcher
  `focus_app_window`, same title rule) and opens a second window only when there is none or Windows does not
  let the launcher take the front. Launcher 3.9.1. Unit 142/142, e2e 87/87, route fuzz 0 server errors.
- Owner asked (23:30) for updates with a button inside MediaEngine; agreed (23:35) to builds published openly on
  GitHub and to the program going online only when the button is pressed. Done:
  `app/archivist/updater.py` + page `/auto/update` + "Update" in the top bar of installed builds. Windows CI, after
  a fully green run of main, publishes `tools/make_update_bundle.py` output to the orphan branch `mediaengine-update`
  (force-pushed: only the newest): `latest.json` (build, size, SHA-256, runtime id, what is new in EN/RU, run link)
  and the program without .venv as one ZIP. The button: reads latest.json from raw.githubusercontent.com, shows
  what is new, "Update now" downloads into the data folder (size + SHA-256 checked), unpacks into
  `.update-<build>` next to the running build (paths outside the folder, a lying size, an incomplete or foreign
  package refused; nothing left behind), hard-links this build's .venv into it when `runtime.txt` matches (new
  file of every package: Python major.minor + requirements.txt + RUNTIME_REV of the package builder), renames it
  to `MediaEngine-<ver>-b<N>` and switches with `use_build` (the new launcher takes over; refused while work
  runs, then Update now again reuses the finished folder). Another runtime: "the full installer is needed this
  time" with the CI run's link. No signature key: secrets cannot be set from here, and whoever can write to that
  branch can equally change the source on main - the trust root is the owner's GitHub either way (HTTPS + SHA-256
  guard against damage). Uninstall also removes builds made this way (`MediaEngine-*`, `.update-MediaEngine-*`).
  Checks: `tests/update_check.py` 25/25 (local server; found / newest / full installer / damaged / unsafe path /
  oversized / nothing published / no connection / foreign address / turned off / old build / Russian pages);
  i18n 40 pages 0 English 0 network; route fuzz of the update routes and states: no server error. Windows CI:
  the same check, plus the package's Update button finds a next build served from 127.0.0.1, installs it into a
  Cyrillic folder with the runtime hard-linked (fsutil) and takes over (ping answers from the new folder).
  Windows CI b142 (run 39098689249, commit 2fa9886): every step green except one line of the installer smoke - the
  tray icon was SHOWN (`tray: shown` in /api/ping of the installed build), but the check's FindWindowW got PowerShell's
  `$null` as "" and found no window, so the tray Quit was not tried (fixed in the workflow, cd3909a). Update button
  smoke PASS: b142 found `b100142` served from 127.0.0.1, installed it into `upd\Программы\` (2.3 MB ZIP, 164 files),
  python.exe of the runtime has 2 names (hard link), ping answered from the new folder, old build kept and listed,
  nothing half-made. update_check 26/26 on Windows too.
- Independent review of tray / Update / launcher (2026-10-18 night), all confirmed findings fixed:
  (1) a switch that never happened left the page "switching" forever: after starting the new build the old one
  waits 150 s and then says why (launcher's update_status.json: refused because work started / no answer); the
  progress page says "the new version did not start, this one runs again" when the old build answers again after
  being gone; (2) a slow check could reset a running install and allow a second install thread: one install at a
  time (`_APPLY`), a check or a failed check never overwrites it; (3) the switch looked the new folder up among the
  versions the OLD build knows (a future top-level file would have hidden it): the verified folder is started
  directly (`auto_edit.start_build_folder`, shared with Use this version); (4) Quit / tray / switch / watchdog
  restart now wait while an update downloads or unpacks (not during its own switch); unique staging folder made
  inside the try; (5) a takeover started from the shortcut or Setup asks the old build to close its windows (one
  fresh window instead of two; in-app switches keep theirs); (6) the update is published only when every check
  passed, also the non-blocking ones (models, Russian pages, odd input, large footage). Also: rename retried while
  a virus scanner holds the new folder; free space checked before a runtime copy (disks without hard links); tray
  Quit asks when it cannot tell what runs; latest.json fetched past caches and the previous ZIP kept one more
  round; alpha/beta numbers ordered; a project titled "Microsoft …" is still our window. Launcher 3.9.2.
  update_check 33/33, unit 143/143, i18n 40 pages 0 English.
  Verification of those fixes by the same reviewer: no deadlock, the update never blocks its own switch; fixed
  what it found: the old window closed long before the new one opened (the takeover now closes the old windows
  only when the new build answers, right before opening its own - launcher `close_app_windows`; the stop request
  is the plain one again); tray question when the busy check fails says so in words; space checked per copied
  file (one file that cannot be linked no longer demands room for the whole runtime); ZIP fetched with its SHA in
  the address (a re-run with the same build name never gets a cached older ZIP); watchdog waits during the
  switch too; shorter staging name (long runtime paths).
- Start at sign-in (Settings, installed builds on Windows, OFF unless the owner turns it on): a shortcut in the
  user's Startup folder runs this build's launcher with --no-browser (no window; the tray icon shows it runs; the
  first ping resumes reels waiting from before a restart and watches Orders\Inbox). It follows the build started
  last (`sync_autostart` from install_launchers, also after removing a build); uninstall removes it. Closes the
  known gap "after a night reboot the app does not start itself" for an owner who wants that. Windows CI
  installer smoke: turns it on through Settings, checks the shortcut (pythonw, --no-browser, this build) and that
  uninstall removed it.
- A reel being made when the app stops WITHOUT Quit (a PC restart at night, a crash, power) is made again by itself
  at the next start, once (`auto_resumed` column; a second unexpected stop of the same build leaves it interrupted
  with Retry - no loop). Quit, a switch to another build and the watchdog's own restart remove the run mark
  (`DATA/app_running.txt`, `mark_clean_exit`): a build stopped on purpose stays interrupted as before. An order whose
  reel was resumed attaches to the same build (same request key). New check `tests/restart_resume_check.py` (real
  app processes, the process tree killed while the engine runs) 7/7; also in Windows CI. Orders 49/49, library
  flow 43/43, unit 143/143, update 33/33.
- Review of start at sign-in / auto-resume / window swap (same reviewer): nothing breaks Quit, a switch or an update;
  fixed: (1) a rollback to a build older than this feature left start at sign-in on the newer build - the sign-in
  shortcut now carries --at-sign-in and the launcher then starts the build the Start-menu / desktop shortcut points
  at (every build keeps those on itself, old ones too); (2) at sign-in the launcher waits up to 3 min for a
  remembered data folder on a drive that comes later, and starts nothing rather than an empty fallback;
  (3) after a takeover the old windows close only once the new window is there (closing Edge's last window
  first could make Edge drop the new one); `sync_autostart` runs even when the desktop shortcut failed.
  Launcher 3.9.3. Known, accepted: "End task" counts as an unexpected stop (the reel is made once more).
- **Windows CI b148 (run 39116280608, commit a6fd55d): every blocking step green.** Installer smoke: tray `shown`,
  its window found, **Quit from the tray stopped MediaEngine**; start at sign-in off before, on via Settings
  (pythonw ... --no-browser --at-sign-in of this build), removed by uninstall. Update button smoke PASS (b148 →
  b100148 from 127.0.0.1, runtime hard-linked). restart_resume 7/7 and update_check 33/33 on Windows. Package smoke:
  tray shown, takeover to the next release. The update was NOT published: two non-blocking checks failed for test
  reasons - route fuzz POSTed /api/auto/aiplus/import without a path, which opens a Windows folder window that
  waited the whole 600 s (now those two import routes get only odd paths); the Russian check counted project /
  composition titles made by the orders and library tests ("Order reel-damaged", "copy test") as English left (now
  every stored title is user content). Installer: artifact 12135137992 (MediaEngine-3.13.0-rc1-b148-Setup).
- **First real publication**: run 39127136116 (b149, commit 21a607d) fully green, also every non-blocking check, and the
  branch `mediaengine-update` was published: `latest.json` (8 KB, 23 what-is-new items EN+RU, runtime b9810d447e8c86c5 =
  the runtime of b148) + `MediaEngine-3.13.0-rc1-b149-update.zip` (2.3 MB, 164 files). Checked from here with the
  published bytes (raw.githubusercontent.com itself is not reachable from this sandbox): a b100 install with that
  runtime finds b149 (newer, same runtime, 23 notes), downloads, SHA-256 matches, installs MediaEngine-3.13.0-rc1-b149
  next to it with the runtime hard-linked, BUILD.txt commit 21a607d. So b148 (installed by the owner with Setup)
  updates with the button. Next runs also fetch the published files from raw.githubusercontent.com on Windows and
  compare the SHA (non-blocking step "The published update is served ...").
- Run 39138313083 (b150, commit 44bfed1) fully green and published; **on Windows the published update was fetched
  from raw.githubusercontent.com** (the address the Update button reads): latest.json says b150, the ZIP (2,343,573
  bytes) matches its SHA-256 (update_served.txt). The branch now holds b150 and keeps the b149 ZIP one more round.
- **Owner PC (2026-10-18 12:50 Chicago)**: he installed b148 with Setup; the app's own /api/ping (built-in browser
  pane) then answered `build b150`, install `D:\Projects\MedEng\MediaEngine\MediaEngine-3.13.0-rc1-b150`,
  `tray: shown` - the folder b150 next to b148 was made by the Update button from GitHub and took over; no
  unfinished `.update-*` folder left. Older builds there: b28, b100, b113, b117, b121, b122, b131, b137 (his call).
- QA as the owner in Russian through the real pages (independent agent, 8 reels, every link followed): no server
  error; fixed what it found: format names the same everywhere ("Vertical small 540×960", not a bare "Vertical")
  and in the language of the program in saved file names; a quoted path (Windows "Copy as path") accepted on Import
  and Settings, "Folder not found: …" translated; Convert names its real folder (Converted, in the data folder);
  a Library video on the item page says it stays in its folder; First run no longer says the AI is ready without
  the model; a missing source says moved/renamed/deleted and shows where, "View in source" hidden then; a failed
  model download speaks plainly (detail to the console log) and is shown for an hour; Updates page shows the
  version and is linked from Settings, About and Help; the guide got a section on updates, tray and start;
  the sound hint names the real option; Check this PC: an info mark (not a green tick) for things not tested /
  optional, "built in N s"; no Archive / Free cache while a reel is being built; no what's-new list on a first
  install; one decimal for reel lengths; real empty-state texts for Library / Import; "Settings saved".
  Left as is: dot decimals in a few technical numbers, which of two identical videos counts as the duplicate,
  the small copy not listed under saved exports.
  Owner PC 2026-10-18 20:07 Chicago: updated b150 -> b151 with the button (/api/ping build b151, tray shown).
  Windows CI run 39156849185 (b151, commit 7462c01) fully green; published and served from raw.githubusercontent.com
  (b151 ZIP 2,350,880 bytes, SHA-256 matches) - the owner's b150 gets it with Update.
  Then: Russian decimal comma also in clock times (0:14,5) and scores of the replace list; quality badges show a
  whole number. Still left (low value, risk to proven logic): which of two identical videos counts as the duplicate,
  the small copy not listed under saved exports.

## Evidence

Windows CI (GitHub-hosted runner — not the owner PC), synthetic videos only, Technical mode (the model is not in git).
Latest run: **39083521797 on `8c7e647` (2026-10-18) — build b137**: everything of b133 plus review rounds 14-16
(music length guesses, Revert double click, overnight batches, AI+ preparation resumes after a restart, local web
hardening); every check green up to and including the installer smoke; installer artifact
`MediaEngine-3.13.0-rc1-b137-Setup` (https://github.com/skynder-dev/projects/actions/runs/39083521797/artifacts/12122880570).

Before: **39062476347 on `7c83346` (2026-10-17) — build b133**: everything of b131 plus rounds 12-13, the
start-up check rule, the guides and the in-app Social queue buttons; every check green up to and including the
installer smoke (route fuzz 10 min, no server error); installer artifact `MediaEngine-3.13.0-rc1-b133-Setup`
(https://github.com/skynder-dev/projects/actions/runs/39062476347/artifacts/12114239393). The owner installed b131
(seen through the app's pages: b131 serves, Orders page opens, Check this PC all green, projects intact).

Before: **39050990426 on `2bad821` (2026-10-17) — build b131** (day review rounds 6-10 and the independent
review's follow-ups): every check green up to and including the installer smoke (unit, engine regression and
robustness, A/V sync, E2E phone / 7 / 2 videos, AI and AI+ glue, titles and music, Convert, Library, unplugged drive,
64 long names, orders, real AI models, Russian pages, route fuzz, Edge, package smoke, packaged runtime offline,
installer smoke); installer artifact `MediaEngine-3.13.0-rc1-b131-Setup`. The last step (large phone-like footage,
timing only) was cut by the job's 150-minute limit on a slow runner (limit now 190 min, route fuzz at most 9 min). Next build: rounds 12-13, the start-up
check rule and the guides.

Before: **39024722016 on `bee9e2f` (2026-10-17) — all green, build b125**: as b122, plus orders from other
programs (44 checks, also with the packaged Python offline; the Edge check runs an order with the page's button) and
the first night-review fixes (GPU result reaches the engine, prepare fixes). Running next: 39030989741 on `17479da`
(review rounds 2-3).

Previous: **38983106755 on `c564596` (2026-10-17) — all green, build b122**: as b121, plus the graphics-card
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

Owner: b131 is installed. Optional: install `MediaEngine-3.13.0-rc1-b137-Setup` (run 39083521797) when nothing is
being built - it adds rounds 12-16 and the guides. Old versions b28-b122 (~430 MB each) can be removed on Check this PC
(his choice). The sending side of orders in the owner's Social project is not started (only with his permission).
Moment quality on his own footage stays his call (blind comparison is built in). Through the app's pages in the
desktop app's browser pane only (never computer use).
