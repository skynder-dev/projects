# Offline concept core, not the Social runtime

This candidate recovers pure concept/context primitives into canonical
`social/socialreel/` and fixes bounded source/claim producer behavior in the
original `grants`, `claims`, and pre-writer `pipeline` entrypoints. It does not wire
the CLI, frontend, concept runtime, dispatcher, model server, rewrite, or any media
pipeline. No fixture represents a captured real source or model run.

Implemented and tested:
- Bound input/schema checks and explicitly unverified owner context.
- Immutable owner-context revisions, stale-write rejection, isolated atomic writes
  and owned advisory locks.
- Read-only decision-ledger integrity, including orphan/uncommitted-event rejection.
  This is not full decision selection or current source/context eligibility.
- Real synthetic PDF extraction, whole-section projection, lossless quote binding,
  source/view tamper rejection and no-clipping bounds.
- Exact-token admission fails closed without its hash-pinned tokenizer/template.
  No token-count substitute, tokenizer assets, inference or quality proof is supplied.
- Structured claim-source field locators reach the real request without becoming
  invented quotes. They are bounded to 1–16 ASCII dotted names (up to 240 characters
  each), plus the existing `agency_code prefix map` derived-rule label. A lowercase
  64-hex snapshot SHA256 identity is required when `fields` is present. This binds
  supplied provenance metadata; it does not verify snapshot bytes or claim meaning.
  `snapshot_file` is omitted from the prompt, while full-source identity still
  binds it. Invalid locators, filesystem paths and oversized lists fail without clipping.
- All five concept text fields reject empty/whitespace-only content. Identical
  five-field text tuples reject with the two card IDs even if citations differ.
  Input/output text is not rewritten, trimmed, normalized, translated or repaired.
  Surface paraphrases or whitespace variations are not semantic distinctness proof.
- Live discovery keeps the originating search receipt for each retained hit.
  Normalized fields bind to search/detail receipts separately; mixed-source claims
  retain aggregate `fields` for existing readers and `supporting_sources` with
  individual field/snapshot bindings. There is no misleading aggregate snapshot
  hash or observation time. Detail/build time no longer overwrites search times.
  Inconsistent search/detail IDs fail; equivalent integer/string IDs are allowed.
- Full synopsis/eligibility text is separate from short summaries. Raw supplied
  text (including HTML/whitespace) stays exact and is labelled separately from
  normalized legacy text. The two fields have an aggregate 8192-UTF-8-byte bound;
  oversized context or the existing whole-request limit fails without clipping.
  Text, locator and tracked provenance must match the record. Old saved claims
  lacking full nonempty record conditions require an explicit rebuild, not silent
  migration or reconstruction. These are consistency checks, not verification of
  source bytes, currentness, entailment or completeness outside the two fields.

Run from the repository root:

    python -B .ci/tests/run_social_concept_core.py

Requires Python 3.11+, `pypdf==6.10.0` for generated-in-memory PDF tests, and Pillow
for importing the existing pipeline module (no image/media work is executed).
The runner verifies canonical import locations, owns temporary storage and rejects
network connections/listeners and native process launches. It runs 88 tests
(28 baseline, 8 persistence recovery, 10 opt-in contract, 19 source/card guards
and 23 live-producer/full-context cases).
The new source/card tests use stdlib `unittest` and actual core entrypoints. Real
request inspection raises before admission, never simulating tokenizer success.
The existing broader Social suites are not run by this command.
Producer tests use fake connectors and the real connector with a synthetic HTTP
transport. They exercise exact snapshot writes and real discovery/normalization/
claim-building. One run-path check stops before writing a script, before all media
work; concept request inspections stop before admission. No live API is contacted.

`ConceptStore` is only extracted durable storage plumbing with a required root.
It does not register source provenance, queue work, or establish eligible jobs.
The tests explicitly insert synthetic-only rows. Full application integration
must not treat these rows or a ledger read as source validation or approval.

Remaining prerequisites for the original end-to-end concept workflow include
canonical preparation/request binding, source-quality observation, runtime config
validation and actual frontend/Handler source. The original native dispatcher,
local model adapter and rewrite imports are deliberately not included. The
legacy non-OJP normalizer's optional NSF parser is not included or exercised.
