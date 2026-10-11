# Current state

_Updated: 2026-10-10_

- Social moved off Supabase into this repo; runs on GitHub Actions (`social-reel`).
- Supabase project `media-business-projects` still contains the old `social` schema, 11 `social-*` edge functions and 38 `social.*` cron jobs. They are **not used** by this program. Not disabled yet (owner decision pending).
- Writer: deterministic template (no spend). Claude writer implemented, gated by `llm.allow_spend=false`.
- Voice: Piper `en_US-ryan-high` (free, local) with espeak-ng fallback.
- Renderer: built-in (Pillow + ffmpeg). MediaEngine handoff folder is written with every package; MediaEngine itself is not in this repo.

Counters (2026-10-10): real Reel packages 2 accepted (2 retracted); finished playable Reels 2; rebuild byte-identical. Details: `OWNER_REVIEW.md`.
