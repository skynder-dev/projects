# MediaEngine handoff boundary

MediaEngine is not part of Social's codebase.

Current useful facts:
- MediaEngine has proven Social HD rendering at 1080x1920.
- It has a proven folder-to-reel / semantic rendering path.
- Accepted MediaEngine stable/V52 state must not be casually replaced by Social work.
- The migration should consume MediaEngine as a renderer.

Preferred handoff artifact:
- one folder per Reel package
- stable filenames
- package manifest with SHA-256
- script/timing/visual/source metadata
- output folder containing final MP4 plus result manifest

Do not claim MediaEngine success from a queued request. Require a real output file.
