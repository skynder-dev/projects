# CODEX_02: save concept results and let the owner choose

## Work without stopping
- Work autonomously from start to finish in ONE run. Never ask for permission, approval or confirmation. Never wait
  for a reply. The owner is not watching and will not answer.
- No internet access is needed: all tests are offline. If a step fails, fix it and continue. If something is
  ambiguous, pick the simplest option that keeps the rules below and list the choice in your final report.
  Never end the run with a question.

## Context
`social/trial/concept_trial.py` produces `trial.json`: one live source, its claims, the exact model request, the raw
model answer, the core validation result and up to three concepts (C1..C3). Today the result lives only in that file.
The owner must be able to see the ideas later, choose one (or reject all with a reason), edit a field, and come back
without losing anything. Existing building blocks: `socialreel/concept_store.py` (durable storage with locks and
atomic writes), `socialreel/concept_decision_ledger.py` (read-only ledger integrity), `concept_locks.py`,
`concept_storage.py`, `concept_owner_context.py`. Read them first and reuse them; do not write a parallel store.

Start from branch `social/late-core-20261028` (or from `codex/social-topics` if it already exists and is not merged:
then base on it). Work in branch `codex/social-save-choose`. Open a pull request into `social/late-core-20261028`.

## Hard rules
- Touch only `social/`. The repo is PUBLIC: no secrets, keys, personal data.
- Python 3.11 standard library only. No new dependencies, no paid APIs.
- Do not change the meaning of `concept_core.py`, `concept_admission.py`, `json_contract.py` or their tests.
- Nothing is ever deleted or overwritten in place: every save, decision and edit is a new revision linked to the
  previous one. The raw model answer and rejected variants are kept.
- A decision applies to one exact revision (by its hash). Editing a concept creates a new revision and the old
  decision does NOT carry over to it.
- A stale write (someone saved a newer revision in between) is refused, not merged silently.
- Model output is never marked as owner-approved by the program itself. Only an explicit owner decision does that.
- All existing tests must still pass: `python -B social/.ci/run_social_concept_core.py` and
  `cd social && python -m unittest discover -s tests -t .`

## What to build
1. Import: `python -m socialreel concepts import TRIAL_JSON --store DIR`. Stores the whole trial result as a job
   with its source identity, request hash, raw answer, validation diagnostics and concepts. Importing the same file
   twice is a no-op that says so.
2. List and show: `concepts list --store DIR` (one line per job: date, source title, state, number of concepts,
   latest decision) and `concepts show JOB --store DIR` (all fields, provenance, history of revisions and decisions).
3. Decide: `concepts decide JOB --pick C2 --note TEXT` or `--reject-all --note TEXT`, bound to the current revision
   hash. Allowed only on a structurally valid result.
4. Edit: `concepts edit JOB C2 --field hook --value TEXT` creates a new revision; previous decision becomes stale.
5. Export: `concepts export JOB --md PATH` writes a short Markdown page in Russian for the owner: source title, link,
   close date, each concept's question, angle, what the viewer learns, what is not answered, hook, which facts
   support it, and the current decision state. This is what the owner will read on the phone.
6. Hand-off file for other projects (agreed on `shared/BOARD.md` in repo skynder-dev/pc, 03.11):
   `concepts handoff JOB --out PATH` writes `<id>.json` with `{"id", "topic", "audience", "script", "source_url",
   "facts"}`. `facts` is a list of the claims the chosen concept cites, each with the exact source quote or field
   locator and the snapshot SHA-256. Only for a job with an explicit owner pick; `script` may be empty until a
   script step exists. Never invent a fact or a URL: if the source URL is unknown, the command fails.
7. Recovery: interrupting a write (simulate) leaves the store readable and the previous revision intact.

## Tests (new file `social/tests/test_concept_choose.py`)
- import, list, show, decide, edit, export round trip on a synthetic trial.json;
- re-import is a no-op; decision on an old revision is refused after an edit;
- stale write refused; interrupted write leaves previous revision readable;
- export contains every concept and the decision state, and no field is shortened or translated.

## Final report
In the pull request description, in plain short Russian for a non-programmer: what was done; what was checked
(offline only, say so); what was NOT checked; choices on ambiguous points; exact commands.
