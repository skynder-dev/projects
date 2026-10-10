# MediaEngine handoff

Social already rendered `final/reel.mp4` with its built-in renderer. This folder carries the same
package in a renderer-neutral form so MediaEngine (Social HD preset, 1080x1920) can re-render it:

- `stills/segment_NN.png` — final composed frame for each segment (1080x1920)
- `audio/segment_NN.wav` — narration per segment; `audio/narration.wav` — full track with pauses
- `timeline.json` — start/end of every clip in seconds (measured from the audio)

Exact package identity: see `../package_manifest.json` (SHA-256 of every file, including these).
