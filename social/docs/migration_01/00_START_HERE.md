# Social -> Claude migration

This bundle is a clean continuation package for the Social project.

## Product contract

Canonical product goal: `SOCIAL_REAL_REELS_V1`

The product is not considered done because research exists, scripts exist, or a UI exists.
The only meaningful acceptance path is:

current real topic -> grounded research -> strong Reel package -> voice/visual assets -> MediaEngine -> playable finished Reel

## Authoritative migration state

- V7 UI/prototype branch was rejected by the owner. Do not resume V1-V7 UI redesign.
- UI is frozen unless a concrete end-to-end defect makes a UI change necessary.
- Grants.gov live research path was proven.
- Real-topic research exists for 3 stories.
- Real grounded Reel packages: 0/3.
- Finished MediaEngine reels: 0/1.
- The old server generation runtime was blocked by a missing OpenAI API key.
- That missing key is NOT a reason to stop in Claude. Treat the provider-bound generation path as legacy architecture.
- Claude should generate or rebuild the grounded package itself from source evidence, preserving citations/claim lineage.
- MediaEngine is the downstream renderer. The migration goal is to hand a real package to MediaEngine and obtain a playable Reel.

Read `09_CLAUDE_START_PROMPT.md` and begin work without asking the owner for routine decisions.

Note: `historical_reference/` from the original bundle (DB runbooks, device checkpoint) is intentionally not stored in this public repo.
