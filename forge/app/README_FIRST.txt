MERCH FORGE 057 Merch Forge AMAZON PROFILE FIX RC

START
1. Extract the whole folder.
2. Run START_057_MERCH_FORGE.vbs.

WHAT IS NEW (057)
- FIX: an owner-attested Amazon print profile was never accepted. The profile check and the
  "Import Amazon Print Profile" tool both assigned to PowerShell's read-only $host variable, which
  always failed silently. Without a valid profile no product could reach "ready to publish";
  this predates the migration (<=054). Profile dates are now read correctly on PowerShell 5.1 and 7.
- Includes 056: language switch keeps live screens, no stuck "Working...", PS 5.1 spool cleanup.
- Includes 055: Discover > "Create concept draft" (local draft bound to research, owner review, no-dispatch brief).

PROOF
- Tested automatically on a real Windows machine by the GitHub workflow "forge-windows"
  (startup preflight, provider pipeline self-test, PS 5.1 self-test, real window clicks + screenshots).

SAFETY
- No backend change, no paid provider call, no publishing, no Supabase mutation.
