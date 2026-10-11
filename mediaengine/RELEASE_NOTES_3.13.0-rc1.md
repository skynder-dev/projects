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
Start-menu "MediaEngine". A newer Setup adds its own build folder next to the old one (rollback = start the old
folder's `Start MediaEngine.vbs`). Uninstall (Settings → Apps → MediaEngine) refuses while MediaEngine runs, removes
the build folders and shortcuts, keeps `MediaEngine Data`. CI: silent install into a Cyrillic folder, start from the
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
VBS from a Cyrillic folder, data outside the release, next release sees the projects, restart, second copy refused,
Quit) · packaged-Python E2E with the firewall blocking it · release folder unchanged by the checks · 4K/long
footage build time (measured).

## Known limitations

- AI selection quality has not been judged by a person; use "Compare blind" on real projects.
- AI mode with the real model is proven for the engine (R2, command 1214) but not yet through this GUI on the
  owner PC: "Check this PC → Build a test reel with the AI model" is the one-click check.
- Auto sound follows the accepted P11 rule: if some moments have no sound, the whole reel is muted (choose Source
  to keep the sound).
- Technical-only selection is decided on the accepted 960-px previews; the reel itself is cut from the originals.
- `/media` routes serve Private items to the local owner UI (loopback only), as in 3.12.42.
- Camcorder `.MTS` reading depends on the bundled FFmpeg build (checked in CI on Windows).
