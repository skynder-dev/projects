# Worklog

## 2026-10-10 — migration from Supabase
- Audited Supabase (read-only): Grants.gov connector worked; package generator blocked on OpenAI gates (5 gates, never ran);
  38 self-acceptance cron jobs; package_variants were `platform: fake`; render_jobs were seed rows.
  Supabase traffic warnings come from `godog_*` polling (~68k REST + ~14k function calls/day), not from Social.
- Exported the 3 prepared generation inputs (12 claims) and 3 real normalized Grants.gov records to `fixtures/`.
- Built `socialreel`: live Grants.gov → claims → validated script → Piper narration → 1080×1920 MP4 → ffprobe verification → SHA-256 package + MediaEngine handoff.
- 15 unit tests pass. Offline fixture run renders a correct 37 s video (silent test voice, correctly NOT accepted).

## 2026-10-10 — first live runs on GitHub Actions
- Run 38020038390: 2 Reels rendered and auto-accepted, then **retracted by review**: agency taken from `synopsis.agencyName` = grantor contact ("Lynn Bailey Grantor").
- Fix: agency from `agencyDetails`/`topAgencyDetails`, `clean_agency` guard, informative purpose sentence, topic-family dedupe, ASR (faster-whisper base.en) narration check. 20 tests.
- Run 38020401436: 2 Reels accepted (363902 OJJDP, 363998 DOT SBTTAC R3); rebuild byte-identical; ASR recall 0.85/0.88, all numbers heard.
