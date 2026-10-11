# MediaEngine (MedEng, formerly Archivist)

Local, privacy-first Windows media workspace: import, library, clips, composer and **Auto Edit** (folder → reel).
Contract and acceptance criteria: [`MIGRATION/mediaengine/`](../MIGRATION/mediaengine/README.md).

## What is in this folder

| Path | What |
| --- | --- |
| `app/` | Application source. First commit = exact stable **3.12.42** (release 132). Later commits are candidate changes. |
| `requirements.txt` | Pinned Windows CPython 3.11 environment of 3.12.42 |
| `sidecar/auto_edit_v52-rc1/` | Exact accepted V52 Auto Edit sidecar (96/96 files match its manifest). Reference only, not modified. |
| `engine/p11_r2/` | Exact P11 FolderToReel R2 engine that passed on Windows 2026-10-08 (command 1214). |
| `engine/p11_adapter/` | Exact FAST_LOCAL ONNX adapter + validator (hash-pinned). |
| `BASELINE_SOURCES.json` | SHA-256 of every baseline file and where it came from |

Not in git: model weights, owner videos, local configs, keys. The app looks for the model on the PC
(`<install>\sidecars\auto_edit\models\FAST_LOCAL`).

## Status

See [`STATUS.md`](STATUS.md). Stable 3.12.42, V52 and release 054 on the owner PC are never modified by this work;
new builds are separate candidates.
