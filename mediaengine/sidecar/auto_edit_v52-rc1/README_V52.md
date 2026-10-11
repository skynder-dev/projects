# MediaEngine AUTO_EDIT V52 — Output FPS

Candidate: `MEDENG_AUTO_EDIT_V52_VIDEO_QUALITY_SIDECAR_RC1`  
Slot: `v52-rc1`

V52 inherits V50 cover-position behavior and adds per-job output frame rate.

- `output_fps: 30` is the default and is byte/render-identity compatible with V50.
- `output_fps: 60` creates a distinct render identity and produces 60 fps 16:9 and 9:16 reels.
- FPS propagates through AUTO, automatic alternatives, and human override.
- Approval, retry, cover mode, and cover position remain operational policies and do not rerender an unchanged FPS job.
- The inherited mute path remains labeled `MUTED_SILENT_AAC_V47` in published metadata.
- `semantic_selection_claim` remains false.

## V52 — per-job output FPS
- `output_fps`: `30` (default, V50-compatible) or `60`.
- 60 fps is part of render identity and propagates through AUTO, alternatives, and human override.
- Approval/retry/cover policies remain operational and do not rerender an unchanged FPS job.
- Example: `AUTO_EDIT_PRESET_60FPS_EXAMPLE.json`.


## V52 — per-job video quality
- `video_quality`: `standard` (default, V51-compatible) or `high`.
- `high` uses libx264 CRF 16 / veryfast; standard remains CRF 20 / ultrafast.
- Quality is render identity and propagates through AUTO, alternatives, and human override.
- Approval/retry/cover policies do not rerender an unchanged quality job.
- Example: `AUTO_EDIT_PRESET_HIGH_QUALITY_EXAMPLE.json`.
