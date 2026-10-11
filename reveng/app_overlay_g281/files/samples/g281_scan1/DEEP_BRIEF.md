# Scan 1 queue: deep screen of ONE idea, try to KILL it (read-only research, $0)

Read `/home/claude/reveng/scan2/DEEP_BRIEF.md` first: its rules, work plan, evidence format, verdict definitions and output schema apply to you, with these differences:
- Your input is a case file `/home/claude/reveng/scan1deep/cases/<ID>.json` (idea name, buyer, pain, wedge, the scan-1 edge claim, substitutes noted, evidence from an earlier model-assisted scan; that evidence is `agent_reported` and NOT trusted: re-check what your verdict depends on). Ids look like `GAM-01`, `DEV-03` (two digits). The "open question" is: does a stranger with <= $10k, no audience and no network have a structural edge, and does it survive the cheapest alternative and a pessimistic year-1 model?
- At most ~18 page reads per idea (you may have two ideas: budget them separately).
- New evidence ids are `<ID>-D1`, `<ID>-D2`, ... (e.g. `GAM-01-D1`); you may also cite the old ids from the case file.
- Output file per idea: `/home/claude/reveng/scan1deep/out/<ID>.json` (same schema as the brief; `answers` must answer: (1) what free/cheap alternative covers the wedge, (2) what structural edge exists and who could copy it, (3) who demonstrably pays and how much, (4) legal/platform constraints, (5) year-1 numbers).
- Validate with `node /home/claude/reveng/scan1deep/validate_deep_s1.mjs /home/claude/reveng/scan1deep/out/<ID>.json` until it prints OK.
- If WebSearch or WebFetch is refused or out of budget, do NOT invent evidence: write only what you could verify (a `killed` verdict needs at least one fatal or two major reasons, each backed by a real quote; otherwise use `uncertain` and say what is missing in `unverified`).
- Final reply: at most 6 lines per idea: id, verdict, one phrase of why, what you could not verify.
