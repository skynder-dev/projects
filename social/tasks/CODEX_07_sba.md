# CODEX_07: SBA.gov as a source for the small-business channel

## Work without stopping
- Work autonomously from start to finish in ONE run. Never ask for permission, approval or confirmation. Never wait
  for a reply. The owner is not watching and will not answer.
- No internet access is needed: all tests are offline. If a step fails, fix it and continue. If something is
  ambiguous, pick the simplest option that keeps the rules below and list the choice in your final report.
  Never end the run with a question.

## Context
The owner split Social into four channels (08.11.2026): help for people, education, small business, professions.
Live run 08.11: for small business, Grants.gov topics were a housing-authority program, family planning and nuclear
licensing: nothing a small-business owner can use. Small-business viewers need the U.S. Small Business
Administration: loans, grants that really exist for businesses (SBIR/STTR), free counseling (SBDC, SCORE, Women's
Business Centers), disaster loans, government contracting help. USA.gov support is already built
(`socialreel/usagov.py`, `usagov_facts.py`, `select_for_core`, program units from CODEX_05): reuse the same approach.

Start from the latest `social/late-core-20261028`, branch `codex/social-sba`, pull request into
`social/late-core-20261028`.

## Hard rules
Same as CODEX_04/05 (only `social/`, public repo, stdlib only, no paid APIs, protected core unchanged, offline tests,
exact quotes with locators and SHA-256, no clipping, conditions kept, expired marked). All existing tests must pass.

## What to build
1. `socialreel/sba.py` with a page catalog (names -> official sba.gov URLs) for: loans overview, 7(a) loans,
   microloans, SBIR/STTR (America's Seed Fund), grants (what SBA says about grants for businesses, including that most
   are not for starting a business), local assistance (SBDC, SCORE, WBC), disaster loans, government contracting
   basics. Write the URLs you believe are right, mark each «URL not checked live» in a comment and in the report.
2. Facts from sba.gov pages by structure (sections, lists, tables), page-wide conditions attached to every program,
   same claim shape as USA.gov so `concept_core` and `select_for_core` accept them unchanged.
3. `python -m socialreel source --source sba --page NAME --out DIR` (and `--program` when a page holds several).
4. In `topics.py`, rubric `small_business_nonprofit` should prefer SBA pages for the small-business channel; Grants.gov
   records in that rubric only when small businesses (code 23) are a main applicant category, not one of many.

## Tests
- synthetic sba.gov-like HTML (sections, list of programs, table), marked synthetic;
- «most SBA grants are not for starting a business» style condition survives into claims;
- no network.

## Final report
In the pull request description, in plain short Russian for a non-programmer: what was done; what was checked
(offline only); what was NOT checked (live URLs and formats); choices on ambiguous points; exact commands.
