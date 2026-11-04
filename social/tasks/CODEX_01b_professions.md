# CODEX_01b: profession rubric, exact matching, future rounds

## Work without stopping
- Work autonomously from start to finish in ONE run. Never ask for permission, approval or confirmation. Never wait
  for a reply. The owner is not watching and will not answer.
- No internet access is needed: all tests are offline. If a step fails, fix it and continue. If something is
  ambiguous, pick the simplest option that keeps the rules below and list the choice in your final report.
  Never end the run with a question.

## Context
CODEX_01 (`socialreel/topics.py`, `topics_config.json`, `tests/test_topics.py`, `docs/TOPICS.md`) is merged into
branch `social/late-core-20261028`. Its task file got three additions after you started; build them now on top of
your own code. Start from the latest `social/late-core-20261028`, work in branch `codex/social-professions`, open
a pull request into `social/late-core-20261028`.

## Hard rules
Same as `social/tasks/CODEX_01_topics.md` (only `social/`, public repo, stdlib only, no paid APIs, protected core
files unchanged, offline tests, byte-exact snapshots, never invent facts). All existing tests must still pass
(88 core, 130 full suite now).

## What to build
1. Rubric `profession`: grants for a clear professional audience even when the applicant is an organization
   (fire departments -> firefighters, rural clinics -> medical staff, farms -> farmers, schools -> teachers,
   veterans programs -> veterans, workforce training and apprenticeships -> workers, police -> police officers).
   Keep a config table of professions with words and phrases. Each kept topic records `audience_profession`.
   In this rubric an organization-only applicant list is NOT a reason to exclude; pure university research with
   no clear profession still is.
2. Exact matching. Measured 03.11.2026 on live Grants.gov (posted only): exact words find few records
   (firefighter 1, nurse 9, farmer 16, apprenticeship 21, police 22, teacher 36, veteran 46), while multi-word
   queries like "fire department" (406) or "rural health" (442) are noise because the search matches words
   separately. So: search with single words, then keep a record for a profession only when a configured word or
   phrase appears as a whole word or exact phrase in title, synopsis or eligibility text. Record which phrase
   matched and where.
3. Future rounds: also search `forecasted` records. Mark `recurring_program: true` with the matched words when the
   title or synopsis says it is an annual or fiscal-year program (for example "FY 2027", "annual", "fiscal year").
   Forecasted records get their own timing rule (no close date is not a penalty; note "forecasted" in reasons).
4. Audience score for `profession`: how large and clear the profession is (config table of points per profession,
   with a comment that the numbers are editorial choices, not measured data).

## Tests (extend `social/tests/test_topics.py` or a new file)
- fire-department grant kept in `profession` with `audience_profession` = firefighters and the matched phrase;
- university-only research grant with no profession excluded with a reason;
- "fire" inside "firewall" or "farmer" inside "farmers market policy research" style false matches: decide a rule,
  test it, explain it in the report;
- forecasted FY record marked `recurring_program` and not penalised for a missing close date;
- no network in tests.

## Final report
In the pull request description, in plain short Russian for a non-programmer: what was done; what was checked
(offline only); what was NOT checked; choices on ambiguous points; exact commands.
