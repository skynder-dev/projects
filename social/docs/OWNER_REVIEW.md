# OWNER REVIEW — Social pilot

_2026-10-10 · branch `social/v1` · workflow `social-reel` · results branch `social-results`_

## Result
| Counter | Before (Supabase) | Now |
|---|---|---|
| Live topic | 1/1 | live Grants.gov search every run (3 keyword queries, ~14 detailed records scored) |
| Real Reel packages | 0/3 | **2 accepted** (+2 retracted, see below) |
| Finished Reel (playable MP4) | 0/1 | **2** — 1080×1920, H.264/AAC, 45–46 s |
| Repeatability | — | `rebuild` re-renders each package **byte-identical** (same SHA-256) |

Accepted Reels (live run 38020401436):
| Opportunity | Video SHA-256 | Length |
|---|---|---|
| 363902 OJJDP FY 2026 Community and Schools Youth Drug Prevention ($12 million, up to $750,000, 16 awards, closes Oct 29, 2026) | `d3532e4261b0153809220d32b474d858417ba482fd43b7c242c8f02d42e46a8d` | 45.8 s |
| 363998 DOT Small Business Transportation Technical Assistance Center, Region 3 (up to $231,183, closes Oct 31, 2026) | `f24e3360642799f0902cf2a2817047b80b50567177b7450625ab6fc3b16e7b0c` | 44.9 s |

Every check passed on the real files: ffprobe (codec, 1080×1920, 30 fps, AAC), duration = measured timeline, full decode clean, loudness ≈ −19 dB mean, and **speech recognition of the narration matches the script** (all numbers heard).

## Found and fixed during the pilot
The first live Reel named **"Lynn Bailey Grantor" as the agency**: Grants.gov's `synopsis.agencyName` sometimes holds the grantor contact. Both first-run Reels were retracted (`social-results/RETRACTED.md`); the agency now comes from `agencyDetails`/`topAgencyDetails` and contact-like strings are rejected (unit-tested). Also fixed: boilerplate "This is a notice of funding opportunity…" quotes are skipped; regional copies of the same program count as one topic.

## Honest limits
- **MediaEngine itself was not run** (it is not in this repo / not reachable from here). Reels are rendered by Social's built-in renderer; each package also carries a MediaEngine handoff folder (stills, per-segment audio, timeline, hashes). The exact FolderToReel input format still needs to be matched.
- Writer is the deterministic template (no spend): accurate but plain. The Claude writer is implemented and validated by the same checker, but **off** until you allow spend.
- Voice is free Piper (`en_US-ryan-high`): clear, recognisably synthetic.
- The repo is **public**, so videos on `social-results` and run artifacts are publicly downloadable. Nothing was posted to any social network.

## Needs your decision
1. Allow Claude writer spend? (uses the repo's existing `ANTHROPIC_API_KEY`; ~2 calls per Reel, capped in `config.json`).
2. Disable the old Supabase Social: 38 `social.*` cron jobs and 11 `social-*` functions (reversible: jobs set inactive, functions left in place).
3. Schedule: e.g. one Reel every weekday.
4. Keep results in the public repo, or move Social to a private repo.
