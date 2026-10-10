MERCH FORGE 055 - RESEARCH -> CONCEPT DRAFT RC

START
1. Extract the whole folder.
2. Run START_055_MERCH_FORGE.vbs.
3. Open Discover, select a niche, click "Create concept draft".

WHAT IS NEW
- Discover can now create a LOCAL concept draft from the selected niche.
- The draft is bound to its research provenance: niche id, exact niche row SHA-256,
  snapshot time, contract forge.discover_snapshot.v1, explicitly linked research notes.
- The draft appears in Ideas (status "Research draft") and uses the normal
  KEEP / EDIT / REGEN / SKIP owner review.
- Hook and visual direction are left empty on purpose (creative choice, never invented).
  Fill them in the Edit tab; saving creates a new local revision and clears any older decision.
- Artwork: Export brief (no dispatch), then import the finished image.
- Generate, live Accept, delivery packages and server actions are blocked for drafts.

SAFETY / STATUS
- No backend change. Drafts are local only (LocalCore state on this Windows account).
- No paid provider call, no publishing, no Supabase mutation.
- Headless self-test: Merch_Forge_A5_Current\MerchForgeResearchDraftSelfTest.ps1 (no network).
- Native Windows WPF execution of 055 is NOT claimed yet.
