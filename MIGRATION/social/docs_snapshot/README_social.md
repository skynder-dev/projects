# Social

Program that turns a **current real federal funding opportunity** into a **finished, fact-checked vertical Reel** (MP4 1080×1920) — no Supabase, no manual steps.

```
Grants.gov API ──► topic selection ──► claim ledger ──► script ──► narration ──► frames ──► MP4 ──► verification ──► hashed package
 (live, keyless)    (scored, no repeats)  (official fields only)  (template or Claude,  (Piper TTS,   (Pillow)   (ffmpeg)  (ffprobe/decode/   (SHA-256 lineage
                                                                    validated)           free)                           loudness)          source→video)
```

| Path | What |
|---|---|
| `socialreel/` | the program (`python -m socialreel run`) |
| `config.json` | search keywords, selection, writer, voice. **`llm.allow_spend` is false** — no paid calls |
| `tests/` | unit tests (`python -m socialreel selftest`) |
| `fixtures/` | real records exported from the retired Supabase connector (offline tests only; never accepted as a live Reel) |
| `docs/` | `CURRENT_STATE.md`, `NEXT_ACTION.md`, `WORKLOG.md`; `migration_01/` = handoff bundle |
| `assets/fonts/` | Inter (OFL) |

## How it runs
GitHub Actions workflow **social-reel** (`.github/workflows/social-reel.yml`): on push to `social/**` branches or by *Run workflow* (inputs: how many Reels, optional opportunity id).
Results: branch **`social-results`** (`README.md` index, `latest/` = full newest package, `runs/<id>/` = video + review + manifests) and the run's artifact (all full packages).

Locally (Linux/Windows, Python 3.11 + ffmpeg): `pip install -r requirements.txt` then `python -m socialreel run`.

## Why the facts can be trusted
- Claims are **copied from official Grants.gov fields** (`claims.py`); each records the snapshot file, its SHA-256 and the JSON field.
- Writers (deterministic template, or Claude when spend is authorized) may only **cite** claims. The validator rejects any amount, date or number not carried by a cited claim, hype phrases ("free money", "you qualify"…), vague quantities, and a missing "check the official listing" close. An invalid LLM script falls back to the template; nothing unvalidated is rendered.
- Timing is **measured from the synthesized audio**, not guessed.
- The final MP4 is checked with ffprobe + full decode + loudness (`verify.py`); `rebuild` re-renders from the package and must be **byte-identical**.
- Fixture runs and the `silent_test` voice can never be accepted.

## Rules
`docs/migration_01/04_OWNER_RULES.md`: no spend, publishing or external contact without explicit owner approval. Nothing here posts to any social network.
