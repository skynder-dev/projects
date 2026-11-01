# Explicit opt-in concept result contract

This is a cloud-only follow-on proposal, not a change to the original application
runtime. Set concept_first.result_contract to SOCIAL_CONCEPT_RESULT_V2 only in a
consumer that understands both branches. Existing callers default to the original
SOCIAL_PROPOSED_CONCEPT_COMPACT_V1 result contract. Unknown versions fail closed.
Existing saved cards are not migrated or reinterpreted. Both contract versions
receive stronger modality/scope/causality prompt wording; legacy prompt bytes are
therefore changed, although its default response shape is compatible. Only V2
changes the opening instruction to explicitly permit abstention. The supported 1–3-card
object shape is unchanged. Validation describes those cards as concepts_proposed,
not semantically supported or approved ideas.

The later source-producer fixes preserve both response shapes, but input evidence
is stricter: old saved claims missing full nonempty record description/eligibility
context fail with a rebuild-required error. Stale text, locators or tracked receipts
also fail; no saved evidence is silently migrated, synthesized or approved. Fresh
producer output carries the full bounded context separately from short summaries.

The new disjoint response branch has status no_supported_concept, the exact
input_identity supplied by the builder, reason_ru, missing_evidence_ru, and known
reviewed_basis_claim_keys or reviewed_basis_excerpt_ids. Reasons and gaps are
bounded and nonblank. Reviewed references are nonempty, unique, and drawn from
supplied evidence. Empty concepts and mixed shapes are rejected. The input identity
is a schema constant and an explicit prompt field to copy, not a hash the model
must calculate. A mutated input or stale result identity is rejected.

Abstention is an explicit non-success requiring review. Structural validation does
not prove that evidence is missing, that no useful idea exists, or that an explanation
is true. Neither branch grants approval or establishes quality, entailment,
distinctness, interest or language correctness. Prompt wording now requires source
modality, conditions, exceptions and historical scope to remain intact, but wording
is not an enforcement guarantee. No model outputs or model quality were tested.

Builder tests inspect the real request and then raise before token admission.
They do not simulate a successful tokenizer or report token counts. Actual missing
pinned tokenizer assets continue to block admission. PDF/excerpt tests use generated
synthetic bytes with the actual extractor and binding checks. No runtime, dispatcher,
UI, private source, model, network, media or paid service is activated.
