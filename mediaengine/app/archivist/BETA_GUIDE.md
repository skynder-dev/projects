# Archivist Beta Guide

Archivist is local-first. Your media stays on this PC unless you explicitly connect a provider or enable an optional cloud workflow.

No external account or billing is required for local use.

## What can leave this PC

Nothing leaves this PC by default. If you explicitly connect a provider or start an optional upload, authentication data, selected uploads, and provider analytics can be sent to that service.

Provider credentials belong in Windows Credential Manager, not Archivist SQLite or Supabase.

Cloud Vault is off by default. Its upload modes are exports only, selected media, or full archive mirror. Enabling cloud never deletes local or source originals.

Provider analytics retain source provenance and are descriptive. Archivist does not automatically choose a cross-provider winner or create an opaque ranking.

## Recovery and support

Diagnostics stay local by default. Use Activity > Jobs & errors to inspect durable job history. Failed jobs can be retried and running jobs can be cancelled safely.

Update health checks can restore the previous build if a new release fails to start. Recovery never silently weakens privacy settings and never deletes source originals.

Support export/upload is explicit opt-in only. This beta does not auto-upload support data. Raw media and tokens are excluded by default.
