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
`D:\projects\medeng\MediaEngine-3.13.0-rc1-b<N>\` when `D:\projects` exists (else `%USERPROFILE%\MediaEngine\`;
nothing is put at the root of D:, the owner's rule of 2026-10-14), adds
Start-menu "MediaEngine". A newer Setup adds its own build folder next to the old one; starting it while the old
one runs asks "Switch to …?" (never while a reel is being built). Rollback = start the old folder's
`Start MediaEngine.vbs`. Old builds can be removed on "Check this PC". The header shows the build (e.g. `b21`). Uninstall (Settings → Apps → MediaEngine) refuses while MediaEngine runs, removes
all build folders installed by Setup and the shortcuts, keeps `MediaEngine Data`. Re-running the Setup of the build
that is running is refused (quit first); a newer build can be installed while an older one runs. CI: silent install into a Cyrillic folder, start from the
Start-menu shortcut, data next to the builds, uninstall refused while running, then removes the build, keeps the data.

**ZIP** (same files):
1. Download the CI artifact `MediaEngine-3.13.0-rc1-b<N>` (one ZIP with one folder of the same name).
2. Extract it into its own folder, e.g. `D:\projects\medeng\MediaEngine-3.13.0-rc1-b<N>\` (never over an older
   build). Start `Start MediaEngine.vbs`. Desktop shortcut: "MediaEngine RC". Port 8775 (stable keeps 8765).
3. Data (projects, database, exports, library) is created once in `D:\projects\medeng\MediaEngine Data\` and remembered
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

## Prepare in advance; the AI+ theme "Aerial view (drone)" (2026-10-15)

- **"Prepare in advance"** next to "Create reel": the engine (`--prepare-only`) analyses the videos with the chosen
  mode (AI, AI+, AI+ with a theme, Technical only), measures and chooses the moments for the chosen length once and
  measures the clip edges of every moment that could be chosen - all of it into the caches a build reads; nothing is
  cut or rendered, no version is made (`MediaEngine Prepared.json`: videos, skipped, moments, time). The project then
  says "Prepared in advance" (state PREPARED) with the build form below; the reel made from it starts at "choosing
  moments". A job of its own (request key with `prepare`), the same queue as reels, a Windows notification "Your videos
  are prepared". Videos added to the folder later are analysed by the build. For a folder that takes an hour (the
  owner's 18 drone videos in 4K), e.g. overnight.
- **AI+ theme "Aerial view (drone)"** (`aerial`): the view from high above (fields, roads, water, the coast, a town);
  for this theme only, frames at ground level are bad frames too (`THEME_NEGATIVES`: the ground close by, feet, a
  person next to the camera, the drone or its controller on the ground) - take-off and landing are not chosen. Library
  search by theme has it too (its own bad descriptions kept with the theme). Checked on real drone videos from
  Wikimedia Commons (free licences) in CI: every frame's score, the picks, a prepared folder and the reel
  (`mediaengine-drone`, sheets on branch `mediaengine-drone-results`).

## AI moments analysed on previews, the reel cut from the originals (2026-10-15, measured on the owner's PC)

b113 on the owner's PC (16 threads, 18 drone videos 4K, 29 GB): the first AI reel 42 min instead of 64 (b100), the
same 6 moments; a second project from the same folder (vertical) 2 min 16 s (analysis reused: 9 s). Where the 42 min
went (worker time, 3 videos at once): cutting 90 candidate clips in 4K 4002 s, the AI's own analysis 1353 s,
measuring the clips 418 s - for the 6 moments a 30 s reel uses.

- **Candidates are previews now** (at most 960 px wide, the same x264 settings), in AI and AI+ mode - as the accepted
  technical mode does with its V12 previews. Only the moments in the reel are cut again from the original at full
  quality (`full_quality_clip`, the same settings the candidates had), so the reel's picture is as before. The scores
  hardly move: the accepted scorer looks at every frame at 320 px wide and the signatures at 160 px; the boundary
  check (camera drop) reads the preview like technical mode does. Moment ids are unchanged (edits stay valid).
- The 4K candidate clips of b101-b113 (shared cache and projects) are removed at the next build: gigabytes back.

## The AI's work kept for every reel, time left, a notification (2026-10-15)

- **AI analysis shared by all projects** (`MediaEngine Data\data\auto_edit\shared`, by each video's SHA-256): the AI's
  report per video, the moment clips and the clips' picture measurements. A new reel from videos analysed for another
  reel (another project, a reel for every day, the same folder again) analyses and cuts nothing again; clips are kept
  once. A project made before this hands its files over (moved, not copied). Kept up to 40 GB of clips (the ones used
  longest ago go first; half when the disk has less than 10 GB free); videos marked Private leave it before every
  build. "Check this PC" shows its size with "Free".
- **Picture measurements of the moment clips in parallel** (up to 4 at once): the accepted scorer measured every clip
  again, one after another; it now finds them all in its own cache format and computes exactly as before.
- **One AI model session per build** instead of one per video (the accepted hook and adapter files are unchanged and
  still hash-checked). Videos under 2 s are "too short" at once (the accepted scout needs 3 frames 1 s apart).
- **Time left** while moments are found and while pieces are cut, from the real rate of that stage ("finding moments:
  about 12 min left, then cutting and joining"). The old estimate from the whole job's percentage said "about 2 hours"
  for a job that needed 34 more minutes.
- **Windows notification** when a build that took more than a minute has finished (one at the end for reels for every
  day); a click opens the reel. Local only. Off in Settings. Shown as "MediaEngine" when Setup made the Start-menu
  shortcut (it now carries the app id `MediaEngine.Desktop`), else as "Windows PowerShell".
- **Switching builds**: the launcher of the next build no longer takes the previous build's launcher (still finishing
  a moment after its app answers) for its own and quietly does nothing (CI b101): one lock per program folder.
- "What's new" shows only what came after the last time it was seen.
- Moment clips are cut bit-identically every time (x264 `sync-lookahead=0`: its threaded lookahead made the same cut
  differ in 2-3 runs of 12; without it 30 of 30 identical, same speed on 4K).
- A reel whose videos have no useful sound (drone, action camera) offers "Add music…" next to "The same reel with the
  original sound".
- **Clip boundaries checked 4-8x faster, same result.** The camera-drop check reads a picture every 0.25 s of each
  chosen moment by a seek; a moment clip is one GOP, so every seek decoded from its start (4K: ~40 s per clip here,
  139 s for 6 moments on the CI runner, in every build). Now one pass through the clip takes the frames a seek lands
  on (int(t x fps + 0.5)); on every clip two rows are measured again by a real seek (and a time past the last frame
  must find nothing), otherwise the clip is measured the accepted way. Same rows on 15 test clips (25/29.97/30/59.94/
  60 fps, 4K, rotated, VFR, camcorder) and in the CI glue check with the app's own OpenCV. The rows are kept per clip
  in the shared cache.
- **Picture signatures remembered.** The accepted order and transition planning ask for a signature at the start and
  near the end of every moment twice (a seek near the end of a one-GOP 4K clip decodes the whole clip; 34 s for 6
  moments on the CI runner even for a project whose analysis was shared). Remembered for the build and per clip SHA-256
  in the shared cache - the same float32 numbers, so the same order and transitions (R3 = R2 regression unchanged).
- **The pieces of a reel are cut up to three at once** on a PC with many cores (cores/4; not with cuts on the beat,
  where each piece depends on the one before): every piece is the same FFmpeg command as before, made first in
  parallel, then the usual loop finds them all made. A format variant of a 4K reel spent about half its time here.
  CI: the AI glue check (one by one vs three at once) and one E2E run cut three at once.
- AI+ too: videos ranked before for this theme go first, the engine estimates the time left on the others; the results
  stay in the input order (checked against the previous loop on 9,000 random cases: identical, except that a video
  skipped half-way no longer leaves its theme-deferred moments behind). "Known" means a valid report (a scout file
  alone or a stale report still needs the slow part); with nothing new the app estimates from the stage's rate.
- Found by a fresh-eyes review before release: the AI+ Library preparation (it runs beside a reel build) never prunes
  the shared clips now (it could have deleted clips the build was about to read); the engine estimates the time left
  itself and analyses videos known from before first (a mix of known and new 4K videos showed "less than a minute"
  for minutes of work); a stand-in of a camcorder video (remux) names the real file, so marking the real file
  Private removes the stand-in's report and clips too, as does dropping a fixed copy of a recording without a length;
  clips left without their description by a stopped build are removed after 6 h; the pre-filled score cache is only
  a speed-up (a locked file never fails the build); "too short" only for the scout's too-few-frames or for a video
  under 2.5 s, other errors are reported as they are.

## AI mode with 4K videos (found on the owner's PC, 2026-10-14)

The first AI reel from a folder of 18 drone videos (4K, ~3 min each) analysed ~5 min per video, one after another.
Measured here: cutting the moment clips from 4K (8 per video, x264 `fast`/crf 18) was most of that time.

- **Moment clips**: x264 `veryfast`/crf 16 - the settings the full-quality recut already uses. 1.9-2.2x faster on
  4K (H.264 100 Mbit/s and HEVC 10-bit samples), picture slightly better (SSIM 0.9963 vs 0.9955), files ~9 % larger.
  Clips already made are reused as they are.
- **Several videos at once** on a PC with many cores and enough memory (up to 3: cores/4, RAM/6 GB). Each video is
  analysed on its own, so the moments are the same; a copy of a video under another name is analysed once and the
  copy taken from the cache afterwards (two threads once wrote the same clip file). `MEDENG_SEMANTIC_WORKERS` sets it.
- `semantic_timing` in the result now also for AI mode (analysis, clips, scoring seconds, workers).
- Check: `semantic_glue_check` builds the same folder one by one and three at once - same moments, same order, same
  sound, picture >= 40 dB PSNR on every frame (x264 in FFmpeg 7 is not always bit-identical from run to run - with
  `fast` as with `veryfast`, 1-2 runs in 10 on the same clip, 49-75 dB; the same reel one frame late: 9-18 dB).

## Everyday use (2026-10-14 review of the whole program)

- **Save MP4 in one step** on any finished version (it becomes the chosen one); "Accept" is optional.
- **New reels start like the last one** (format, sound, AI mode, framing). Clearer format names (Vertical Full HD,
  Horizontal Full HD, small copies "quick to send").
- **Horizontal videos in a vertical reel**: "Fill the screen" (cropped to the interesting part, as before, the
  default) or "Whole picture, blurred edges" (the accepted engine's `fit_blur` framing, new `--vertical-framing`).
- **"The same reel with the original sound"** when Auto muted a reel.
- **A reel for every day** of a big folder (a trip) in one click; built one after another. Waiting builds say which
  reel is made first.
- **Library → "Make a reel"** from the selected videos; item page: Open in player, Show in folder, Make a reel from
  this video. Folder picker for Import sources.
- **Recording time from the video header** (MP4/MOV `mvhd`) when the name has no date and the file date is the day
  of the copy: days of a big folder and Library dates. Never read for OneDrive cloud-only files.
- **Delete archived projects** (frees versions and cache; saved MP4 files and originals stay).
- **Check this PC** builds its test reel in the background (the page can be left).
- **Safety**: a copy of the database and settings before a different build opens them, a daily copy and an
  integrity check in the background (`MediaEngine Data\data\backups`, 7 daily + 5 build copies); a missing data
  folder (disk not connected) or a damaged database is said on every page; settings are written to disk before they
  replace the old file, one writer at a time.
- **Faster variants, identical reels**: SHA-256 of the sources remembered by size and change time, camera-drop
  measurements by clip SHA-256, segment lengths with the segment, and the choice of moments for the same moments and
  length (a format variant of a 2-minute reel: the 66 s search is skipped; the same moments, picture and sound
  identical). Engine regression: R3 reel byte-identical.
- **Small things**: "Recent folders" on Auto Edit (one click to a new reel from the same place); a tab icon.
- **Small copy for messengers** next to Save MP4: one quick encode of the version (long side 1280 px) into the export
  folder. **Reels up to 2 minutes** (120 s: about 25 moments; the engine takes up to 30).
- **A reel being made is shown at the top of every page** (with a link), its percent in the tab title.
- **"Use this version"** on Check this PC: switch to another installed build in one click (its launcher asks this one
  to quit, refused while a reel is being made; projects stay the same). **Free the caches of all projects** at once.
- Auto Edit: "Find a project" when there are many; "Videos folder" opens the reel's source folder; a one-time "New
  in this version" card. Home/Import: the phone over USB is shown as optional, not as an error.
- **Simpler navigation**: Social Lab, Devices and Cloud behind "More"; no milestone labels; no "rights unknown" on
  every card; Home shows the reel projects.
- **Real-browser check in CI (Edge)**: form buttons, the More menu, the framing choice, Create reel, Save MP4, Check
  this PC — it found that `Referrer-Policy: no-referrer` (added the same day) made every form button fail
  (`Origin: null`); fixed before any release (`same-origin`).

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
- **Library → "Find by theme (AI+)"**: "Prepare AI+ for the whole Library" first looks at the 8 preview frames of
  each Library video (Private, rejected and excluded videos are never included) - every search after that is instant
  and opens the video at its best moment - and then, in the engine below normal priority, at what an AI+ reel needs
  (about one frame per second, at most 48 per video, into the shared cache every AI+ build uses): a later AI+ reel or
  theme with these videos looks at no frame again. It can run overnight (Windows does not go to sleep meanwhile),
  shows "search / for reels: N / M" with the time left, has a Stop button, waits while a reel is being built (one AI+
  model at a time; the engine step is ended and started again afterwards) and continues where it stopped. Camcorder
  streams and pictures with an odd size are left to the reel itself (the engine analyses a converted copy of them).
  "Make a reel about this theme" opens the new-reel page with the matching videos, AI+ and the theme chosen.
- Safety: a link opened from outside the app (e-mail, chat, a document) can no longer make MediaEngine open a
  network share (Windows would send its sign-in to that server); pasting a network path in the app still works.

## AI+ tuned on real footage

`tests/real_footage_check.py` (own workflow): 22 public amateur videos from Wikimedia Commons (free licences, pinned
list with SHA-256; never the owner's videos), AI / AI+ / theme reels through the app on Windows, a contact sheet of the
chosen moments per reel. What it showed and what changed:
- general AI+ reels took a video's best window even when the whole video was weak (twigs, a promo graphic): now how
  clearly a moment shows something worth seeing is compared across all videos (45 %), next to the video's own
  ranking (35 %) and the accepted technical score (20 %); two more bad-frame descriptions (graphic / logo / text,
  close-up of ground / branches / leaves). After: mountain view, children, parade, wedding dances, sunset.
- themes: kids / sea / party already 3 of 3 fitting; animals 2 of 3 → 3 of 3.
- a new theme decoded and cut moments of every video: now only of moments that match it (the rest only when fewer
  than 3 match) - 60–117 s instead of 218–345 s for 22 videos. Ranking changes never make AI+ look at frames again.
- The accepted AI (FAST_LOCAL) path is unchanged.

## Horizontal Full HD 1920×1080

A fourth format next to Social HD 1080×1920, vertical 540×960 and horizontal 960×540: **horizontal 1920×1080** for a
TV and YouTube (the engine's own size; it was refused before because it was not in the accepted list - the owner
asked for it, 2026-10-13). Titles are drawn for that size too. Checked in CI (robustness + the music/title check).

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
- **Cuts on the beat** (on by default with own music, a checkbox to switch it off): the music's beat is found on the
  PC (`engine_p11/p13_beats.py`: onset strength of 40 log-spaced bands, tempo 55–140 BPM - a fast song at half its
  tempo, so every cut is still on a beat - beats by dynamic programming, beat or off-beat decided by the kick drum
  and the bass), and every cut (a hard cut, or the middle of a dissolve) and the reel's end are moved to the nearest
  beat - at most about one beat away from the plan, never longer than the moment's clip; a moment the user trimmed
  keeps its exact length. The final encode takes exactly the frames up to the beat. Music without a clear beat (a
  drone, speech, quiet ambient music) leaves the cuts where they were, with a note. The review shows "cuts on the
  beat of the music: N/M (BPM)". CI (synthetic): a drum song in AAC under a 20 s reel of 7 videos - every cut within
  40 ms of a true beat in the result, in the picture itself and in the reel's own sound; real music from Commons
  against librosa's beat tracker: own workflow `mediaengine-realmusic`.

## Faster AI+ for several reels from the same videos

What AI+ saw in each video is kept once for all projects (by the video's SHA-256, about 100 KB per video): a new
reel from videos analysed for another reel needs no frame looked at again. Check this PC shows its size with a
"Free" button; entries of videos marked Private are removed before each build.

## Big Library check

`tests/scale_library_check.py` (own workflow `mediaengine-scale`): 600 videos in one camera folder through the app -
scan, Import + analyse, Library pages, the day list of a whole phone folder, AI+ search preparation and search,
reel from a theme; page times, database size, memory.

## AI model provenance (not in the ZIP, not in git)

FAST_LOCAL (about 30 MB) is downloaded by MediaEngine itself - "Download the AI model" on Auto Edit or Check this PC -
from its public, pinned Hugging Face commit into its own data folder (`MediaEngine Data\models`), or copied from a
folder ("Copy from a folder…"). No other program's folder is looked at any more (until 2026-10-14 the model was
taken from the stable Archivist install). Every file is checked against the pinned hashes before use:
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
- Cuts on the beat: checked with synthetic drum songs and against librosa on public Commons music; not yet judged by a
  person on the owner's own songs. A song with a very free rhythm may show "no clear beat" (cuts unchanged).
