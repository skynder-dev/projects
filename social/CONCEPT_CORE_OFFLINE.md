# Offline concept core, not the Social runtime

This additive slice recovers pure concept/context primitives into canonical
`social/socialreel/`. It does not wire the CLI, frontend, runtime, dispatcher,
model server, source import, rewrite, or any media pipeline. Existing canonical
modules are unchanged. No fixture represents a captured real source or model run.

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

Run from the repository root:

    python -B .ci/tests/run_social_concept_core.py

Requires Python 3.11+ and `pypdf==6.10.0` for the generated-in-memory PDF tests.
The runner verifies canonical import locations, owns temporary storage and rejects
network connections/listeners and native process launches. It runs 28 tests.
The existing broader Social suites are not run by this command.

`ConceptStore` is only extracted durable storage plumbing with a required root.
It does not register source provenance, queue work, or establish eligible jobs.
The tests explicitly insert synthetic-only rows. Full application integration
must not treat these rows or a ledger read as source validation or approval.

Remaining prerequisites for the original end-to-end concept workflow include
canonical preparation/request binding, source-quality observation, runtime config
validation and actual frontend/Handler source. The original native dispatcher,
local model adapter and rewrite imports are deliberately not included. The
legacy non-OJP normalizer's optional NSF parser is not included or exercised.
