# Archivist Beta Guide

Archivist is local-first. Your media stays on this PC unless you explicitly connect a provider or enable an optional cloud workflow.

No external account or billing is required for local use.

## Making a reel (Auto Edit)

1. Auto Edit -> "Choose folder..." (a folder of videos on this computer) or "Choose videos..." (single files).
   Phone videos: copy them to the computer first.
2. Pick Length, Format and Sound -> "Create reel". Analysis of new videos takes a while; later builds reuse it.
3. Review: remove, replace, trim or reorder moments; every change is a new version, older ones stay.
4. "Accept this version" -> "Export MP4" (or "Export to another folder..."). "Exported reels" at the top of the
   Auto Edit page opens the folder with the finished reels.

One reel takes up to 64 videos. A folder with more (a whole phone, say) shows its shooting days and a tick list.
A camera card can be chosen at its root: the video folders inside it are listed.

Your original files are only read, never changed. "Check this PC" (Home, Settings, Auto Edit) shows whether the
AI model and video tools are found and builds a 5-second test reel. The language switch is at the top right.

**AI+** is a stronger, optional model. Download it once on "Check this PC" (about 650 MB, free), then choose "AI+"
when you make a reel or a variant. The first analysis of new videos takes longer. Use "Compare blind" to see which
mode is better for your videos.

## What can leave this PC

Nothing leaves this PC by default. If you explicitly connect a provider or start an optional upload, authentication data, selected uploads, and provider analytics can be sent to that service.

Provider credentials belong in Windows Credential Manager, not Archivist SQLite or Supabase.

Cloud Vault is off by default. Its upload modes are exports only, selected media, or full archive mirror. Enabling cloud never deletes local or source originals.

Provider analytics retain source provenance and are descriptive. Archivist does not automatically choose a cross-provider winner or create an opaque ranking.

## Recovery and support

Diagnostics stay local by default. Use Activity > Jobs & errors to inspect durable job history. Failed jobs can be retried and running jobs can be cancelled safely.

Update health checks can restore the previous build if a new release fails to start. Recovery never silently weakens privacy settings and never deletes source originals.

Support export/upload is explicit opt-in only. This beta does not auto-upload support data. Raw media and tokens are excluded by default.
