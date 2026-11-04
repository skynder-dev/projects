# CODEX_04: USA.gov pages give separate facts; fix page list

## Work without stopping
- Work autonomously from start to finish in ONE run. Never ask for permission, approval or confirmation. Never wait
  for a reply. The owner is not watching and will not answer.
- No internet access is needed: all tests are offline. If a step fails, fix it and continue. If something is
  ambiguous, pick the simplest option that keeps the rules below and list the choice in your final report.
  Never end the run with a question.

## Context
CODEX_03 (`socialreel/usagov.py`, `public_sources.py`, `source_intake.py`, `studentaid.py`) is merged into branch
`social/late-core-20261028`. Live check on the owner's PC, 04.11.2026:
- `usagov energy` (https://www.usa.gov/help-with-energy-bills) and `usagov unclaimed`
  (https://www.usa.gov/unclaimed-money) are read, but each page becomes ONE claim: the whole page glued together.
  The concept core needs separate facts (who it is for, what you get, how to apply, conditions, where to search).
- `usagov wages` fails: https://www.usa.gov/unpaid-wages does not exist.
- `studentaid pell` and `studentaid fafsa_deadlines` fail: studentaid.gov returns a JavaScript shell. Leave
  studentaid as it is (it fails clearly, which is correct); do not try to work around it.

Start from the latest `social/late-core-20261028`, work in branch `codex/social-usagov-facts`, open a pull request
into `social/late-core-20261028`.

## Hard rules
Same as `social/tasks/CODEX_03_more_sources.md`. All existing tests must still pass (88 core, 172 full suite now).
Never rewrite, shorten or translate source text inside a claim; each claim keeps an exact quote and its locator
(section heading, table row) and the snapshot SHA-256.

## What to build
1. Split a USA.gov page into claims by structure: one claim per section under a heading (h2/h3), one claim per list
   item where a section is a list of options, and one claim per table row (for example the unclaimed-money table:
   «Employers → Unpaid wages – Search the Department of Labor's database…», «Taxes → Tax refunds…», «Savings
   bonds → TreasuryHunt.gov…»). Each claim: `key` (stable, from heading/row), `statement`, exact `quote`, `locator`
   (heading path or table row and column), snapshot SHA-256. Skip navigation, breadcrumbs, «Was this page helpful»,
   «Call USAGov / Chat with USAGov» and footer.
2. Keep the page-level claim too (title + lead), so existing readers still work.
3. Page list: remove `wages` (dead URL). Add `wage_laws` https://www.usa.gov/wage-laws,
   `unclaimed_tax_refunds` https://www.usa.gov/unclaimed-tax-refunds, `workers_comp`
   https://www.usa.gov/workers-compensation. Keep the old negative regression «unpaid wages help must keep its
   conditions» working on the new wage pages.
4. A statement that a past program period has ended (example from the unclaimed page: «Stimulus checks – The
   period to claim unpaid Economic Impact Payments has ended») must be marked `expired: true` in the claim and
   never offered as current help.
5. Ensure the claims fit the existing core request: if a page gives more claims than the core accepts, choose by
   a documented rule (for example keep table rows and «how to apply» first), record the dropped keys in the bundle,
   never clip text.

## Tests
- synthetic HTML copies of the three structures (sections, list, table) marked synthetic; claim count, keys,
  locators, exact quotes, SHA-256;
- navigation and footer are not claims;
- the «has ended» row is `expired: true`;
- dead page name `wages` is gone and fails clearly if requested;
- no network.

## Final report
In the pull request description, in plain short Russian for a non-programmer: what was done; what was checked
(offline only); what was NOT checked; choices on ambiguous points; exact commands.
