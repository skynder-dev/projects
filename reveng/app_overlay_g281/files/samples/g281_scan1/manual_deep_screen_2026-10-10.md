# Manual deep screen of run_20261010_031655 top-3 (done in chat, no API spend)

Evidence class: **agent-reported** (public pages read by the assistant via WebSearch/WebFetch on 2026-10-10; not engine-verified). Nothing contacted, published or bought.
Method = the engine's deep checklist: current competitor prices, free substitutes, legal/ToS constraints, does the claimed edge survive.

## EDU-01 Wyzant exit kit (claimed: $9/mo flat vs 25% commission) -> KILL
- Wyzant fee confirmed: 25% platform fee + 9% service fee (support.wyzant.com fee-structure page).
- TutorTab (tutortab.net/compare/wyzant-commission, a page aimed at Wyzant leavers): $0 for tutors, scheduling + invoicing free, Stripe connect, Google Calendar sync, 5-min booking page; parent pays $1/invoice + card fees. => entrant $9/mo is NOT cheaper than a free incumbent.
- TutorBird: $16.95/mo, no free plan, 30-day trial.
- Only remaining wedge = Wyzant roster import; TutorTab page does not mention import (absence NOT proven). Wyzant Independent Tutor Agreement: no explicit non-solicit, but s5/s6 forbid taking direct payment from Wyzant-sourced students (no time limit) and s18(c) allows deactivation for "misappropriation of Tutor's Students" => ToS risk for the customer, and a screenshot/CSV import from Wyzant is a gray zone.
- Kill reason (fatal): free substitute covers the wedge.

## MED-04 Sponsor-finding lead sheets ($19/mo vs Paved 30%) -> KILL
- Already sold/free: Gumroad "Software Newsletter Sponsors" list ($0, 150+ companies with marketing contacts); Who Sponsors Stuff (500+ newsletters tracked, sponsor contacts); Open Rates (10,000+ sponsor DB); SponsorLeads (daily-updated sponsor DB); OhMyNewst (free to join); Sponsorgap marketplace (prices of most not published on the pages read).
- Candidate's own notes: lead-data source legality/scalability unconfirmed; churn high.
- Kill reason (fatal): multiple existing sponsor databases incl. a free one; no differentiation shown.

## EDU-04 Local-first IEP tracker ($5/mo vs Goalbook $595) -> KILL
- Wrong incumbent: SPED Goals: IEP Tracker (iOS, built by a teacher): free up to 20 students with unlimited targets/logs/reminders; Premium $2.99/mo or $19.99/yr; developer states no data collected (self-reported). Entrant at $5/mo is MORE expensive than the real incumbent.
- Districts commonly require student-data-privacy agreements for apps (page titles only; content not verified).
- Kill reason (fatal): cheaper/free incumbent already covers caseload tracking.

## Lesson for the engine (systematic, not luck)
All three top-ranked ideas died to a free or cheaper alternative that discovery did not name, because the first gate compares against the incumbent the LLM chose (the most expensive one). Fix to implement (code-only, $0): require the CHEAPEST credible alternative incl. free, and compute the edge against min(incumbent, cheapest alternative).
