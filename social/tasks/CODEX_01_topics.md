# CODEX_01: topic discovery and scoring for Social

## Work without stopping
- Work autonomously from start to finish in ONE run. Never ask for permission, approval or confirmation. Never wait
  for a reply. The owner is not watching and will not answer.
- Everything you need is in this repository. No internet access is needed: all tests are offline. If something
  needs the internet (for example the Grants.gov eligibility code list), use what the repository already has
  (`socialreel/grants.py`, `tests/`, `fixtures/`), write the table you believe is right, mark it
  "needs check against Grants.gov docs" and continue.
- If a step fails, fix it and continue. If something is ambiguous, pick the simplest option that keeps the rules
  below, and list the choice in your final report. Never end the run with a question.

## Context
Social (folder `social/`, package `socialreel`) turns real official sources into short-video concept ideas.
The mechanism already works end to end on one live Grants.gov record (see `social/trial/concept_trial.py`), but it
picks a topic badly: it takes the nearest-deadline hit for the keyword "community", which gave a grant only
universities can apply for. Your job is the missing first step: find and rank topics that a broad US audience can use.

Start from branch `social/late-core-20261028`. Work in a new branch `codex/social-topics`. Open a pull request
into `social/late-core-20261028` (not into `main`).

## Hard rules
- Touch only `social/`. Never edit other top-level folders. The repo is PUBLIC: no secrets, keys, personal data.
- Python 3.11 standard library only. No new dependencies, no paid APIs, no API keys.
- Do not change the meaning of `concept_core.py`, `concept_admission.py`, `json_contract.py` or their tests.
- Keep raw source snapshots byte-exact (reuse `grants.GrantsGovClient`, it already saves snapshots).
- Never clip, translate or rewrite source text. Never invent facts. Unknown stays unknown.
- Tests must run offline (fake transport, like `tests/test_live_source_context.py`). No network in tests.
- All existing tests must still pass:
  `python -B social/.ci/run_social_concept_core.py` (88) and
  `cd social && python -m unittest discover -s tests -t .` (107 now, more after your tests).

## What to build
1. `social/socialreel/topics.py`
   - Rubrics (config, not hardcoded strings scattered in code):
     - `help_people`: programs individuals can apply for.
     - `small_business_nonprofit`: small businesses and nonprofits.
   - Discovery from Grants.gov search for each rubric. Use the official search API's eligibility filter and
     several keywords per rubric. Put the Grants.gov applicant-eligibility code table in config, with a comment naming where it came from
     (see the rule about the internet above).
   - Exclude records whose eligibility is only universities/colleges, state/local/tribal governments or other
     institutions. Keep the exclusion reason.
   - Fetch detail for the top N candidates only (N in config, default 10) to save API calls.
2. Scoring, transparent and rule based. Each topic gets a total plus every component with a reason:
   - audience: how broad the eligible applicants are;
   - timing: days left until close (too soon and very far are worse; window in config);
   - concreteness: award amount present, eligibility text present, synopsis present;
   - novelty: not already in a `seen` file (path in config; the file lists opportunity IDs used before);
   - missing data lowers the score and is listed, it is never guessed.
3. Output `topics.json`: ranked list, each item with opportunity_id, title, agency, close_date, rubric,
   eligible applicant types as given by the source, score components and reasons, exclusion info for dropped
   items, and source provenance (snapshot file name and SHA-256 that `GrantsGovClient` already records).
4. Command: `python -m socialreel topics --out DIR` (live) and `--fixture PATH` (offline). Follow how the existing
   CLI in `socialreel/__main__.py` is organised.
5. `social/trial/concept_trial.py`: add optional argument `--topics PATH`; when given, use the top-ranked topic's
   opportunity_id instead of the current keyword search. Without it, behaviour stays exactly as now.

## Tests (new file `social/tests/test_topics.py`)
- Institution-only record is excluded with a reason; an individuals record is kept.
- Score components and reasons are present; missing award amount lowers concreteness and is listed.
- A `seen` ID is ranked below an otherwise equal new one.
- Fixture run writes `topics.json`, deterministic order, provenance SHA-256 matches the saved snapshot bytes.
- No network: tests fail if they try to open a real connection.

## Final report
Write it in the pull request description in plain Russian, short, for a non-programmer:
what was done; what was checked (offline only, say so); what was NOT checked (live API, quality of topics);
choices you made on ambiguous points; exact commands to run.
