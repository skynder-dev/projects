# RevEng v6 independent — owner-review packet
Run: `import_20261010_012547`  ·  scoring: `reveng_v6_independent` (profile balanced; no owner context)  ·  **PROVISIONAL (evidence not engine-verified)**

## Verdict: **NO_WINNER**

Unmet conditions:
- raw_candidates 16<30  **(blocks winner)**
- families 4<8  **(blocks winner)**
- required_families_underrepresented(<3): games,services,marketplaces,digital_or_data_products,media_or_content  **(blocks winner)**
- provisional_run: evidence not engine-verified  **(blocks winner)**
- no_candidate_survived_hard_gates  **(blocks winner)**

Candidates: 16 · families: 4 · survived hard gates: 0 · integrity violations: 0

## Ranking (gate survivors, adjusted score, balanced profile)

| # | id | family | adjusted | raw | conf | auto/bal/def rank |
|---|---|---|---|---|---|---|
| – | none survived | | | | | |

## All candidates and first failed gate

| id | name | family | adjusted(unranked) | result |
|---|---|---|---|---|
| SAS-01 | Failed-payment recovery add-on for tiny Stripe SaaS | saas_or_micro_saas | 28 | reject: entrant_edge — no_measured_advantage(inc=0,ent=19) |
| SAS-02 | Missed-call text-back for home-service trades | saas_or_micro_saas | 23.6 | reject: entrant_edge — no_measured_advantage(inc=14,ent=14) |
| SAS-03 | State sales-tax nexus tracker for small SaaS/ecommerce sellers | saas_or_micro_saas | 25.1 | reject: entrant_edge — no_measured_advantage(inc=0,ent=15) |
| SAS-04 | Simple e-signature for small landlords/contractors | saas_or_micro_saas | 24.8 | reject: entrant_edge — no_measured_advantage(inc=0,ent=9) |
| DEV-01 | Webhook capture and replay for small teams | b2b_api_devtools | 30.6 | reject: entrant_edge — no_measured_advantage(inc=0,ent=9) |
| DEV-02 | Cron/heartbeat monitoring for small projects | b2b_api_devtools | 27.4 | reject: entrant_edge — no_measured_advantage(inc=0,ent=5) |
| DEV-03 | Normalized SEC XBRL financials API for indie quant/AI builders | b2b_api_devtools | 30.8 | reject: entrant_edge — no_measured_advantage(inc=0,ent=5) |
| DEV-04 | Hosted MCP server generator for SaaS APIs | b2b_api_devtools | 28.8 | reject: entrant_edge — no_measured_advantage(inc=0,ent=29) |
| ECO-01 | Generic AliExpress/CJ-to-Shopify dropshipping store | ecommerce_or_dropshipping | 19.1 | reject: entrant_edge — incumbent_source_not_in_evidence |
| ECO-02 | Niche personalized POD gifts on Etsy (pet memorial / specialty nursing / hobby journals) | ecommerce_or_dropshipping | 23.8 | reject: entrant_edge — incumbent_source_not_in_evidence |
| ECO-03 | Thrift/estate-sale sourcing resold on eBay (vintage and branded) | ecommerce_or_dropshipping | 21.6 | reject: entrant_edge — no_measured_advantage(inc=12,ent=12) |
| ECO-04 | Amazon online/retail arbitrage and wholesale reselling | ecommerce_or_dropshipping | 18.2 | reject: entrant_edge — incumbent_source_not_in_evidence |
| PHY-01 | Private-label China-sourced Amazon kitchen gadget | physical_products | 17.6 | reject: entrant_edge — no_measured_advantage(inc=3000,ent=3000) |
| PHY-02 | 3D-printed original-design hobby organizers/accessories sold on Etsy | physical_products | 24.1 | reject: entrant_edge — incumbent_source_not_in_evidence |
| PHY-03 | Private-label natural skincare via contract manufacturer | physical_products | 18.3 | reject: entrant_edge — no_measured_advantage(inc=3000,ent=3000) |
| PHY-04 | Private-label children's/baby product (toys, plush, apparel accessories) | physical_products | 16.1 | reject: entrant_edge — no_measured_advantage(inc=3000,ent=4150) |

## Evidence classes (not promoted into each other)

- source/static verified: engine code + frozen G280 vendor hashes checked at load
- internal tests verified: see test results in checkpoint (node --test)
- runtime verified: NOT for market data in this run
- live-provider verified: NOT RUN (no provider calls in this run)
- market validated: NO — research evidence only; no customer/commercial test performed
- commercial result observed: NO