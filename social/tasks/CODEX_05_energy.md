# CODEX_05: one USA.gov page with several programs becomes several topics

## Work without stopping
- Work autonomously from start to finish in ONE run. Never ask for permission, approval or confirmation. Never wait
  for a reply. The owner is not watching and will not answer.
- No internet access is needed: all tests are offline. If a step fails, fix it and continue. If something is
  ambiguous, pick the simplest option that keeps the rules below and list the choice in your final report.
  Never end the run with a question.

## Context
CODEX_04 (`socialreel/usagov_facts.py`, `select_for_core`) is merged into `social/late-core-20261028`.
Live runs on the owner's PC, 04.11.2026:
- `unclaimed` and `unclaimed_tax_refunds` work: 5 claims each, good viewer-facing ideas.
- `energy` (https://www.usa.gov/help-with-energy-bills) is refused every time:
  `claim selection REFUSED: No current facts fit with their complete mandatory conditions; no clipping or admission
  bypass`. The dropped keys show sections and list items for LIHEAP («find-out-if-you-are-eligible-for-liheap-and-
  appl…»), WAP («find-out-if-you-are-eligible-for-wap-and-apply…») and the page `identity`, all with reason
  `complete_unit_budget_or_dependency`. Raising `concept_core.SOURCE_CONTEXT_BYTES` from 8192 to 16384 (already done
  by Claude, keep it) did not help, so the problem is the dependency unit, not the byte cap: the page holds three
  programs (LIHEAP bill help, WAP weatherization, help when utilities were disconnected) and their conditions are
  treated as one unit.

Start from the latest `social/late-core-20261028`, work in branch `codex/social-energy`, open a pull request into
`social/late-core-20261028`.

## Hard rules
Same as `social/tasks/CODEX_04_usagov_facts.md`. All existing tests must still pass (88 core, 190 full suite now).
Never clip or rewrite source text; a fact never loses its own conditions.

## What to build
1. Program units: when a USA.gov page has separate program sections (by heading, for example «Find out if you are
   eligible for LIHEAP and apply», «… for WAP and apply», «… if your utilities were disconnected»), conditions are
   attached to the program they belong to, not to the whole page. Page-wide conditions (for example «rules differ by
   state») stay attached to every program.
2. `select_for_core` may then pick ONE program unit (with its complete conditions plus the page-wide ones) when the
   whole page does not fit. Record which program was chosen, which were left out and why.
3. `source` command: option `--program NAME` (or index) to build the bundle for a chosen program; without it, pick
   the first program that fits and say so. `topics` from USA.gov may list one topic per program (topic_id like
   `usagov:energy:liheap`).
4. Keep the existing behaviour for pages that fit as a whole (unclaimed, tax refunds).

## Tests
- synthetic HTML with the same structure as the energy page (three program sections with lists, a page-wide state
  note), marked synthetic: whole page refused as today, one program accepted with its own conditions and the
  page-wide note, the other two listed as left out with reasons;
- exact quotes, locators and SHA-256 kept; nothing clipped;
- unclaimed and tax-refund fixtures unchanged;
- no network.

## Final report
In the pull request description, in plain short Russian for a non-programmer: what was done; what was checked
(offline only); what was NOT checked; choices on ambiguous points; exact commands.
