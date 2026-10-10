# RevEng v6 independent scan — research brief (same for every agent)

Date of scan: 2026-10-09. Use WebSearch/WebFetch (lawful public sources only). No outreach, no signups, no purchases, no posting.

## Reference entrant (identical for ALL candidates; NOT the owner)
Anonymous solo founder, US-based, no network, no audience, no licenses, no prior industry experience, <= $10,000 startup cash,
~20 h/week, can build software with modern AI coding tools. Any advantage must be one this unknown entrant can actually obtain.
Generic demand / "big market" / "uses AI" / "cheaper" / "better UX" is NOT an entrant edge.

## Task
Your assigned families: see your prompt. For EACH family find exactly 4 DISTINCT raw candidates (different buyer/pain, not variants of
one idea). Derive them from current evidence (pain threads, marketplace listings, price pages, public data, app-store/Steam charts, etc.),
not from imagination. Be intellectually honest: do not pick only ideas you expect to win; include a mix, and reject weak ones.
Research depth must be EQUAL for every candidate: >=3 evidence items each (>=1 substitute/incumbent pricing page, >=1 demand/pain
evidence, >=1 for cost/regulatory/platform constraint), each with exact URL, publisher, date observed/published (YYYY-MM-DD or "undated"),
and a short factual statement of what it shows. Never invent a URL or a number; if you could not verify it, put it in "unknowns".
Mark each number as fact (from source) / inference / model.

## Output
Write ONE JSON file to the path given in your prompt: a list of candidate objects:
{
 "id": "<FAMILY_CODE>-NN",            // e.g. GAM-01
 "name": str, "family": str, "category": str,
 "buyer": str, "pain": str,
 "evidence": [ {"url":str,"publisher":str,"date":str,"shows":str,"kind":"incumbent_price|demand|constraint|other","class":"fact|inference"} ],
 "substitutes": [ {"name":str,"price_point":str,"url":str} ],
 "entrant_wedge": str,
 "entrant_edge": {
    "criterion": "cash_cost|owner_time|cycle_time|step_count|channel_reach|required_tool_count",
    "direction": "lower_is_better|higher_is_better",
    "unit": str, "incumbent_value": number, "incumbent_source_url": str,
    "entrant_value": number, "entrant_basis": "how an unknown entrant gets this value, concrete",
    "falsifier": str },
 "startup_cash_usd": number, "time_to_first_revenue_days": number,
 "owner_hours_per_week_steady": number, "automation_potential_pct": number (0-100),
 "unit_economics": {"price_usd":number|null,"variable_cost_usd":number|null,"contribution_margin_pct":number|null,"notes":str,"class":"model|fact"},
 "regulatory_or_platform_dependency": str, "major_uncertainty": str,
 "dimension_scores": {  // integers 0..5 using the rubric below; every one needs a one-line reason in dimension_reasons
   "contribution_economics":n,"demand_signal":n,"acquisition_efficiency":n,"automation":n,"competition_gap":n,"defensibility":n,
   "owner_time_efficiency":n,"capital_efficiency":n,"launch_speed":n,"platform_resilience":n,"scale_without_hiring":n,
   "fulfillment_simplicity":n,"regulatory_simplicity":n },
 "dimension_reasons": { same 13 keys -> one-line reason citing evidence },
 "pre_deep_verdict": "accept|reject", "verdict_reason": str
}

## Rubric (0 = terrible, 5 = excellent, for the reference entrant)
contribution_economics: 0 negative/<10% margin after realistic costs ... 5 >=70% margin and clear $ per unit/month
demand_signal: 0 none ... 5 many dated, independent, paying-behavior signals (not just search volume)
acquisition_efficiency: 0 only paid ads at CAC>LTV ... 5 credible organic/free channel proven by evidence for this niche
automation: 0 manual per customer ... 5 >=90% automatable
competition_gap: 0 saturated with strong free incumbents ... 5 identifiable underserved gap WITH evidence
defensibility: 0 trivially cloned ... 5 data/network/regulatory/switching moat attainable by entrant
owner_time_efficiency: 0 >40h/wk ... 5 <=3h/wk steady
capital_efficiency: 0 >$10k ... 5 <=$200
launch_speed: 0 >12 months to first revenue ... 5 <=14 days
platform_resilience: 0 depends on one platform that can ban/change terms ... 5 independent channels/own distribution
scale_without_hiring: 0 linear with headcount ... 5 near-zero marginal labor
fulfillment_simplicity: 0 complex logistics/support ... 5 instant digital delivery
regulatory_simplicity: 0 license/compliance heavy ... 5 none material
Be conservative and consistent: a 4-5 needs cited evidence. Default to 2 where evidence is absent and say so.
