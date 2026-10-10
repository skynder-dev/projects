MERCH FORGE — LOCAL CHECK REQUEST BUNDLE v2

Forge creates a lineage-bound check request automatically after exact local Accept and refreshes it after listing metadata changes.

Passing evidence rules
- New PASS / NOT_REQUIRED states require forge.local_check_evidence.v3.
- A passing check must declare authority_kind, checked_at, source, and evidence_refs when external evidence is claimed. Every required evidence_ref must be a non-empty string.
- Owner-imported JSON may only create external PASS as owner_attested_external with attested=true and at least one non-empty string evidence_ref. Passing source/checked_at/ref structure is revalidated again at package-gate time.
- Owner JSON cannot self-assert live_backend_exact, verified_worker, or verified_channel_profile authority. Those are reserved for verified ingestion paths.
- The exact evidence file SHA-256 is stored with each imported check.
- Visual PASS remains bound to owner_exact_accept for the exact artwork SHA.
- Policy and metadata PASS / NOT_REQUIRED are listing-scoped: their listing_hash must match the exact current local listing snapshot. Live policy is imported only when live publication fields exactly match that local snapshot.

Package gate
- READY_FOR_MANUAL_UPLOAD requires exact lineage plus authority-valid passing states for IP, visual, print, policy, and metadata.
- Every package includes preupload-gate.json with the exact authority/evidence provenance.
- The publication receipt is v3 and binds to package SHA + lineage fingerprint + listing hash + preupload-gate SHA.

Authority boundary
- owner_attested_external is an owner workflow attestation, not independent verification or legal advice.
- IP pass is never represented as legal clearance and is not a legal opinion.
- No current Amazon print/policy rule is fabricated when a verified channel profile is unavailable.
- Nothing in this bundle submits or publishes anything.

POLICY PROFILE AUTHORITY
A passing/not-required policy check is listing-scoped AND Amazon-profile-scoped. Use the policy channel_profile_fingerprint, marketplace, product_type_key and template_key prefilled by Forge in the exported evidence template. If the current owner-attested Amazon print profile changes or expires, old policy evidence no longer qualifies a READY package.
Live backend policy is imported as authority only when the live listing plus marketplace/product/template match the current valid local Amazon print profile.
