# CODEX_03: second and third source types (USA.gov benefits, student aid)

## Work without stopping
- Work autonomously from start to finish in ONE run. Never ask for permission, approval or confirmation. Never wait
  for a reply. The owner is not watching and will not answer.
- All tests are offline. Do not depend on the internet during the run. If you cannot check a real page or API
  format, write the connector from the official documentation you know, mark it "format not checked live" in
  code comments and the report, and continue. Never end the run with a question.

## Context
Social now reads only Grants.gov (`socialreel/grants.py`), and most Grants.gov records are for organizations.
The channel needs topics for ordinary people too. Add two more source types that feed the SAME downstream path:
record + claims with provenance (`socialreel/claims.py` style), then `concept_core.build_request`.

Start from branch `social/late-core-20261028` (base on `codex/social-topics` if it exists unmerged). Work in branch
`codex/social-sources`. Open a pull request into `social/late-core-20261028`.

## Hard rules
- Touch only `social/`. The repo is PUBLIC: no secrets. Python 3.11 standard library only. No paid APIs.
- If an API needs a free key (for example api.data.gov for College Scorecard), read it ONLY from an environment
  variable, never write it to files or logs, and make the connector fail clearly when it is missing.
- Save raw responses byte-exact with SHA-256, like `GrantsGovClient` does. Every claim keeps its source locator.
- Keep conditions and exceptions: "may", "must", "only", income limits, state limits. Never turn a possibility into
  a promise. A program run by states must say that rules differ by state.
- Do not change the meaning of `concept_core.py`, `concept_admission.py`, `json_contract.py` or their tests.
- All existing tests must still pass (`python -B social/.ci/run_social_concept_core.py`, and the full suite).

## What to build
1. `socialreel/usagov.py`: USA.gov benefit and help pages (for example energy bill help / LIHEAP, unclaimed money,
   unpaid wages). Fetch an official page, keep the raw HTML, extract the main text sections without rewriting them,
   build a record with title, URL, who it is for, what you get, how to apply, conditions, and "rules differ by state"
   when the page says so.
   Known negative cases to keep as regression tests: USA.gov must never be labelled as Grants.gov; an energy-help
   page must not become "everyone gets money"; unpaid-wages help must keep its conditions.
2. `socialreel/studentaid.py`: student aid facts from official US sources (studentaid.gov pages; College Scorecard
   API with a key from an environment variable). Record: program or college, what aid exists, deadlines when the
   source gives them, conditions.
3. Claims builders for both, same shape as Grants.gov claims, so `concept_core.inputs` and `build_request` accept
   them without changes to the core. If the core truly cannot accept them without a change, do not change it:
   write exactly what is missing in the report.
4. Hook into topics if `socialreel/topics.py` exists: new rubrics `help_people` (USA.gov) and `education`
   (student aid). If it does not exist, skip this step and say so.

## Tests (new files `social/tests/test_usagov.py`, `social/tests/test_studentaid.py`)
- fixture HTML/JSON in `social/fixtures/` (write small synthetic ones, mark them synthetic);
- raw bytes saved and SHA-256 matches; conditions and state-difference notes survive into claims;
- the three negative cases above;
- missing API key gives a clear error and no request;
- no network in tests.

## Final report
In the pull request description, in plain short Russian for a non-programmer: what was done; what was checked
(offline only); what was NOT checked (live formats, quality); choices on ambiguous points; exact commands.
