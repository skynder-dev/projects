# MediaEngine 3.13.0-rc1 — release candidate notes

Not a final release. Side-by-side candidate next to the accepted stable Archivist 3.12.42 (which is not changed).
Evidence lives outside the user ZIP: this file, `STATUS.md`, branch `mediaengine-ci-results` (`latest/`).

## What it is

The existing Archivist/MediaEngine app with **Auto Edit** built in: folder or chosen videos → Length / Format /
Sound → reel built by the bundled engine R3 (Windows-proven P11 R2 + documented fixes) → review, edit, variants,
blind comparison → Accept → Export one MP4. Runs locally, no network, no paid services, no Supabase/GoDog.

## Install / update / rollback (owner PC)

**Installer** (CI artifact `MediaEngine-3.13.0-rc1-b<N>-Setup`): run `MediaEngine-3.13.0-rc1-b<N>-Setup.exe`
(unsigned: SmartScreen → "More info" → "Run anyway"). Per-user, no administrator rights; installs into
`D:\MediaEngine\MediaEngine-3.13.0-rc1-b<N>\` when `D:\Archivist` exists (else `%USERPROFILE%\MediaEngine\`), adds
Start-menu "MediaEngine". A newer Setup adds its own build folder next to the old one; starting it while the old
one runs asks "Switch to …?" (never while a reel is being built). Rollback = start the old folder's
`Start MediaEngine.vbs`. Old builds can be removed on "Check this PC". The header shows the build (e.g. `b21`). Uninstall (Settings → Apps → MediaEngine) refuses while MediaEngine runs, removes
all build folders installed by Setup and the shortcuts, keeps `MediaEngine Data`. Re-running the Setup of the build
that is running is refused (quit first); a newer build can be installed while an older one runs. CI: silent install into a Cyrillic folder, start from the
Start-menu shortcut, data next to the builds, uninstall refused while running, then removes the build, keeps the data.

**ZIP** (same files):
1. Download the CI artifact `MediaEngine-3.13.0-rc1-b<N>` (one ZIP with one folder of the same name).
2. Extract it next to the stable install, e.g. `D:\MediaEngine\MediaEngine-3.13.0-rc1-b<N>\` (never over an older
   build). Start `Start MediaEngine.vbs`. Desktop shortcut: "MediaEngine RC". Port 8775 (stable keeps 8765).
3. Data (projects, database, exports, library) is created once in `D:\MediaEngine\MediaEngine Data\` and remembered
   in `%LOCALAPPDATA%\MediaEngine\data_root.txt`; every later build uses the same data.
4. **Rollback**: Quit, start the previous build folder's `Start MediaEngine.vbs` (the shortcut follows the build that
   was started last). Delete a build folder only when it is not running.
5. Uninstall: Quit, delete the build folder(s), `MediaEngine Data` (contains exports) and the shortcut.

## Language

English or Russian for the whole program: "Русский / English" at the top right of every page (and Settings →
Interface language); the first start follows the language chosen in Setup, else the Windows display language.
Texts are translated as whole phrases, so file names, folder names and titles typed by the user are never changed.
CI opens every page in Russian and lists any English left (`tests/i18n_coverage.py`); the engine's progress lines
are checked too. "Check this PC" is on Home, in Settings and on
Auto Edit; until a test reel has been built on the PC, Auto Edit suggests it first.

## Big folders and camera cards

A folder with more than 64 videos (one reel's limit, e.g. a phone camera roll) is not refused: MediaEngine lists
its shooting days (from names like `VID_20260714_…`, else the file date) with one "Use this day" click each, and a
tick list ("Tick the newest 64"). A camera card chosen at its root lists the video folders inside it (DCIM,
AVCHD, M4ROOT; up to 4 levels). Folders with half an hour of video or more get a note that the first build takes
a while (later builds reuse the analysis; the PC does not sleep while MediaEngine works). "Choose folder…" opens
the Explorer-style folder window (address bar, Quick access) next to the last reel's videos; "Choose videos…"
opens in the last reel's folder. Both are driven by window messages in the Windows CI checks.

## OneDrive and other cloud folders

Videos that OneDrive keeps only in the cloud ("Files On-Demand") are recognised from the folder listing and are
not read — reading even their first bytes would make Windows download them all. They are listed as skipped ("only
in the cloud (OneDrive)…"); a folder that is entirely in the cloud says to choose "Always keep on this device"
first. After the download the same reel is built again with them.

## Recordings without a length

A recording made in a web browser or by a screen recorder (and one stopped by a crash) often has no length written
in the file; it used to be listed as "damaged". MediaEngine now measures it by reading the file once (no decoding),
lists it as usable with a note, and the build uses a copy with the length filled in (made once in the project's
cache, freed with "Free cache"; the original is never changed; media marked Private is never copied).

## Library (Media) fixes found by using it like a user

A new Windows CI step adds a folder on Import, imports and analyses its videos, opens the Library, makes smart
clips, marks one video Private, archives and rejects others, and opens every Library page in Russian - with the data
folder itself named in Cyrillic. Fixed on the way: archive / Staging / Private copies lost every Cyrillic letter of
folder and file names ("_ _ _"); "Find similar" failed (HTTP 500) on a library where Search had never been opened;
videos from folders on this PC showed no length; smart clips failed for recordings without a length; previews
could not be written into a folder with non-Latin letters; quality / privacy codes and sizes were shown in English.
The page crawl also runs with the internet blocked: no page contacts anything.

## AI+ — a stronger, optional model (PE-Core L/14)

Asked for by the owner (2026-10-13): the strongest free model that suits the job. AI+ uses PE-Core L/14 (Meta,
Apache-2.0; ONNX int8 from `onnx-community/PE-Core-L14-336-ONNX`, commit `40c36ae`, 2 files ~677 MB + the CLIP
tokenizer files of the accepted model). It is a separate mode next to AI: the accepted AI (FAST_LOCAL) path is not
changed (R3 = R2 decisions in CI). Moments are ranked by the accepted hook's steps (imported unchanged) with the
stronger model and descriptions written for personal footage (people, children, family, landscapes, travel,
celebrations, pets, action; bad: boring, blurry, accidental, dark, dashboard, no subject).

- Download once on "Check this PC" (huggingface.co, free, every file checked by size and SHA-256, stop button), or
  copy the four files from a folder. Never downloaded on its own; analysis never uses the network. A dropped
  connection is continued where it stopped (HTTP Range, a few automatic tries); a stopped download shows
  "Continue the download".
- Choose "AI+" on the new-reel page or for a variant; compare with AI using "Compare blind". AI and AI+ keep separate
  caches and moments. A missing or changed AI+ model is refused with a clear message, never a silent fallback.
- Speed (GitHub Windows runner, 4 logical / 2 physical CPUs - slower than most desktop PCs): 0.9–1.7 s per frame
  the model looks at (runners differ); the first AI+ analysis looks at up to 48 frames per video (about one per
  second). 7 videos of 14 s: first AI+ analysis 279 s (AI 97 s); a new theme for the same videos 53 s (no frame
  looked at again); AI+ test reel 60 s (AI 26 s). About 1 GB more memory. Measured in the model lab: the graph takes
  one frame per run; all logical CPUs are a bit faster on Windows (used by the engine), two sessions side by side
  are not worth the memory. "Check this PC" shows the speed measured on the owner's PC after an AI+ test reel.
- Quality measured in the model lab (public photos, not the owner's videos; `tests/theme_eval.py`):
  COCO 2014 test photos (300 photos, 1501 human captions: people, children, food, animals, sport, streets) - for a
  caption, its own photo is the best of the 300: **AI+ 85.5 %, AI (FAST_LOCAL) 60.2 %**; for a photo, the best
  caption is one of its own: **94.3 % vs 78.3 %**. The int8 files lose almost nothing against the original
  full-precision model (85.8 % / 95.0 %). Plain landscape photos (Intel scene set, 150 px, 240 photos) with the 13
  themes: the best theme fits for AI+ 86 %, AI 89 %, original model 88 % - on simple landscapes AI+ is not better;
  it is clearly better where people and what they do matter.
- CI compares our adapter with the original open_clip model: identical tokens and preprocessing, int8 embeddings
  cos 0.95–0.98 (images) / 0.99+ (texts), identical zero-shot choices. Windows CI downloads both real models and builds
  AI and AI+ test reels, an AI+ reel and its AI variant (reported; a Hugging Face outage never blocks the package).

### AI+ themes and Library search by theme

- **Theme** (AI+ only, on the new-reel page and for a variant): sea and beach, mountains, children, family and
  friends, celebration, animals, sunset, nature, winter and snow, city, food, sport, road trip. AI+ looks at every
  scout frame of every video once (about one per second, at most 48 per video, cached), so a theme can pick any part
  of any video, and a new theme for analysed videos needs no frame to be looked at again (seconds). Matching moments
  are compared across all videos; when fewer than 3 match, the reel says so and fills up with the best others.
- The text part of the model is kept as fixed numbers on disk after the first use: later builds do not open it at
  all (less memory, faster start; same rankings - checked in CI).
- **Library → "Find by theme (AI+)"**: "Prepare the search" looks at the 8 preview frames of each Library video once
  (Private, rejected and excluded videos are never included); every search after that is instant and opens the video
  at its best moment. The search waits while a reel is being built (one AI+ model in memory at a time).
  "Make a reel about this theme" opens the new-reel page with the matching videos, AI+ and the theme chosen.
- Safety: a link opened from outside the app (e-mail, chat, a document) can no longer make MediaEngine open a
  network share (Windows would send its sign-in to that server); pasting a network path in the app still works.

## Own music and a title (optional)

- "Music and title" on the new-reel page and for every variant: a title and a second line (the shooting date with
  one click), your own audio file (mp3, m4a, wav, flac, ogg, opus, wma; "Choose music…" or paste the path), music
  with the videos' quieter sound or only music. Off by default: a reel without them is exactly as before.
- The title is shown for the first 3 s in the lower third (white text, soft shadow and band - readable on a bright
  sky; Cyrillic; Windows fonts Segoe UI / Arial; emoji the font cannot draw are left out with a note; a very long
  word is broken). The music is loudness-normalised, starts softly and fades out at the end; a short song repeats
  without a gap. Both go into the reel's single final encode (no second generation) and the sound ends exactly
  with the picture.
- Changing only the music or the title is a quick new version (no new analysis); the editor and "choose again" keep
  a version's music, title and theme. A missing, silent or protected music file is refused before the build.
  Titles and music paths are not put into support bundles.

## Faster AI+ for several reels from the same videos

What AI+ saw in each video is kept once for all projects (by the video's SHA-256, about 100 KB per video): a new
reel from videos analysed for another reel needs no frame looked at again. Check this PC shows its size with a
"Free" button; entries of videos marked Private are removed before each build.

## Big Library check

`tests/scale_library_check.py` (own workflow `mediaengine-scale`): 600 videos in one camera folder through the app -
scan, Import + analyse, Library pages, the day list of a whole phone folder, AI+ search preparation and search,
reel from a theme; page times, database size, memory.

## AI model provenance (not in the ZIP, not in git)

FAST_LOCAL is taken from the owner's stable install (`<drive>:\Archivist\sidecars\auto_edit\models`) or imported
through "Choose model folder…"; every file is checked against the pinned hashes before use:
model `844d1a46…0600` (24 281 512 bytes), semantic hook `2b15303e…2d5c`, adapter `d7ef56b5…ff36`, validator `00e14d0d…7a22`.
Without the model only the explicitly chosen "Technical only" mode builds reels.

## Engine R3 vs Windows-proven R2

Runtime modules, adapter and validator byte-identical to R2. Editing decisions identical on the regression set
(CI `engine_regression.py`). Orchestrator differences and why: see `STATUS.md` → "Engine R3 vs Windows-proven R2".

## Checks in every Windows CI run (GitHub-hosted runner, synthetic media)

Fast helper checks · startup self-check · R3 = R2 decisions · robustness (still video, Private file, short footage,
damaged cache, presets, phone files incl. rotation/HEVC/VFR/no audio, HDR HLG+PQ colours, camcorder MTS incl. a hand
trim, HDV/DVD wide pictures in narrow pixels keep their shape, 11 other formats: 5.1 sound, 120 fps HEVC, square,
odd size 4:4:4, MJPEG AVI + PCM, VP9/Opus WebM, 10-bit H.264, two sound tracks, late sound, ProRes, 3GP; older WMV,
FLV, DVD VOB, JVC MOD/TOD, HDV .m2t, DV tape) · A/V sync
at every cut · phone-file E2E · AI-mode glue with a labelled stub · full-video Convert · library re-analysis ·
unplugged drive + no network · 64 long-named videos with Windows long paths OFF · E2E 7 and 2 videos (incl. chosen
files, export folder, blind comparison, free cache, Russian interface, Check this PC) · package smoke (start via
VBS from a Cyrillic folder, desktop shortcut points exactly there, data outside the release, restart, second copy
refused, Quit, the next release started while this one runs takes over and opens the same projects, running a
release adds no files to it) · packaged-Python E2E with the firewall blocking it · release folder unchanged by the
checks · Setup: silent install into a Cyrillic folder, start from the Start-menu shortcut, data next to the
builds, uninstall refused while running, after Quit removes the build and keeps the data · 4K/long footage build
time (measured).

## Known limitations

- AI selection quality has not been judged by a person; use "Compare blind" on real projects.
- AI mode with the real model is proven for the engine (R2, command 1214) but not yet through this GUI on the
  owner PC: "Check this PC → Build a test reel with the AI model" is the one-click check.
- Auto sound follows the accepted P11 rule: if some moments have no sound, the whole reel is muted (choose Source
  to keep the sound).
- Technical-only selection is decided on the accepted 960-px previews; the reel itself is cut from the originals.
- `/media` routes serve Private items to the local owner UI (loopback only), as in 3.12.42.
- Camcorder `.MTS` reading depends on the bundled FFmpeg build (checked in CI on Windows).
