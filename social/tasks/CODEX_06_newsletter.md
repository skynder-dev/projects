# CODEX_06: weekly newsletter draft and a sign-up checklist from verified facts

## Work without stopping
- Work autonomously from start to finish in ONE run. Never ask for permission, approval or confirmation. Never wait
  for a reply. The owner is not watching and will not answer.
- No internet access is needed: all tests are offline. If a step fails, fix it and continue. If something is
  ambiguous, pick the simplest option that keeps the rules below and list the choice in your final report.
  Never end the run with a question.

## Context
Plan: short videos lead to a free weekly newsletter (see the owner's project doc «Social: площадки, реклама и
воронки»). Social already has verified facts with exact quotes and source locators: `socialreel source` bundles
(USA.gov, Grants.gov), concept store with owner decisions (`socialreel concepts`, CODEX_02). Build two outputs from
them. Nothing is sent or published by the program: it only writes files for the owner to review.

Start from the latest `social/late-core-20261028`, work in branch `codex/social-newsletter`, open a pull request
into `social/late-core-20261028`.

## Hard rules
Same as earlier tasks (only `social/`, public repo, stdlib only, no paid APIs, protected core unchanged, offline
tests). Every sentence that states a fact must come from a claim with its source URL; no invented facts, amounts
or dates; keep conditions («may», «rules differ by state», «only organizations can apply»); expired claims are
never used; a date before the issue date is never presented as upcoming.

## What to build
1. `python -m socialreel newsletter draft --store DIR --bundles DIR... --out DIR --as-of DATE`:
   an English email draft (Markdown and plain text) with 3-5 items. Item = title, 2-3 short sentences built only
   from claim quotes (quoted or lightly joined, never reworded into a new claim), the official link, and the
   condition line. Prefer ideas the owner picked in the concept store; then fresh bundles. A Russian summary file for
   the owner next to it: what is in the issue and why, what was left out and why.
   Footer placeholders for the sender address and unsubscribe link (the newsletter service fills them); a fixed line
   «We are not a government agency. Always check the official page before applying.»
2. `python -m socialreel newsletter checklist --bundles DIR... --out DIR`: a one-page «Places the government may owe
   you money» checklist (Markdown + simple printable HTML), one line per verified place (from the unclaimed-money
   table rows and similar claims), each with its official link and its condition. Expired rows excluded and listed in
   the Russian summary.
3. No affiliate links in either output. Leave a clearly marked empty slot `[SPONSOR OR AFFILIATE: owner decides]`
   that is off by default.

## Tests
- synthetic bundles: every fact sentence traceable to a claim key; links present; conditions present;
- expired claim excluded; past date not presented as upcoming;
- owner-picked idea goes first; nothing invented when bundles are thin (fewer items, said so in the summary);
- no network.

## Final report
In the pull request description, in plain short Russian for a non-programmer: what was done; what was checked
(offline only); what was NOT checked; choices on ambiguous points; exact commands.
