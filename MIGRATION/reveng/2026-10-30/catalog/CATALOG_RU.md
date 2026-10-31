# REVENG - каталог восстановленных записей

Срез: 30 октября 2026 года. Это последовательное чтение выбранных проектных таблиц, не полная резервная копия БД и не транзакционно согласованный снимок. Исходные утверждения и оценки сохранены как исторические данные, не как заново проверенные факты.

## Реестр файлов и точные количества

- `catalog_business_models.json`: 13 записей.
- `catalog_candidate_inbox.json`: 23 записей.
- `catalog_candidate_sources.json`: 4 записей.
- `catalog_claim_evidence.json`: 51 записей.
- `catalog_claims.json`: 50 записей.
- `catalog_evidence_sources.json`: 8 записей.
- `catalog_markets.json`: 2 записей.
- `catalog_niches.json`: 4 записей.
- `catalog_opportunities.json`: 5 записей.
- `evidence_items.json`: 359 записей.
- `niche_dossiers.json`: 20 записей.
- `niches.json`: 37 записей.
- `opportunities.json`: 4 записей.
- `opportunity_score_runs.json`: 7 записей.
- `opportunity_scoring_versions.json`: 1 записей.
- `opportunity_validation_gates.json`: 49 записей.
- `research_queue.json`: 57 записей.
- `score_runs.json`: 86 записей.
- `scoring_dimensions.json`: 14 записей.
- `scoring_versions.json`: 5 записей.
- `workspace_opportunity_state.json`: 6 записей.
- `workspaces.json`: 3 записей.

## Главные границы интерпретации

RevEng является независимым сканером бизнес-возможностей, не персональной рекомендательной моделью на выдуманных ресурсах владельца. Владелец 9 октября отверг наличие сети 40 контактов в грузоперевозках. Исторические `EDGE-TRUCK-NETWORK-01`, `evidenced`, `research_finalist`, `finalist_ready` и старые оценки в исходном JSON не являются текущим подтверждением. Позднее исправление: 7 доказательств отозваны с весом 0; направления repair/DOT/billing/bookkeeping получили 40.50 и `REJECTED`, referral получил 33.75 и `REJECTED`. Решения владельца в `analysis/history.md` имеют приоритет над старым статусом.

102 исходные идеи CSV не складываются с 5 оставшимися: эти 5 являются подмножеством банка 102, со статусами 3 `uncertain` и 2 `queued`. Остальные 97 имеют исторические вердикты 81 `killed` и 16 `rejected`, не прямой отказ владельца от каждой идеи. Это отдельное поколение данных по отношению к 37 старым нишам, 4 старым возможностям и 5 `catalog_opportunities`. Разные сущности нельзя объединять по совпадению количества.

Три рабочие области каталога являются искусственными контрольными примерами. Их 6 состояний не означают приёмку владельцем в рабочей системе. Оценки, утверждения, доказательства и досье составляют историческую исследовательскую базу, не подтверждённые продажи или свежую проверку ссылок. Поле `reason_short` в CSV уже сокращено в исходном файле; полный глубокий разбор нельзя восстановить из одного CSV.

Источник CSV: https://github.com/skynder-dev/projects/blob/82a034efb536ca2cda7315c465df935027673fa2/reveng/ideas_102.csv ; объект Git `8edf46082bbee1a8d9e8e892244efdf4a6c760bc`.

Названия, причины и тела исходных записей ниже сохранены на исходном языке. Это точные исторические данные, а не новый авторский текст.

## Исходный банк - все 102 идеи

### 1. Verified-active creator lists for indie Steam launches
- `G281-SCAN1-GAM-01`; семейство `games`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -305
- Исходная причина: Killed on two majors. (1) The wedge (genre-matched creators with recent activity, no email/key chores) is already covered at $0: Steam Curator Connect (active-only list, 'No need to mess with e-mails or keys'), SullyGnome/LetsPlayIndex, and key platforms that 

### 2. Pre-built local weekly trivia packs for independent venues
- `G281-SCAN1-GAM-02`; семейство `games`; проход 1
- Статус: очередь (не решено); вердикт `queued`; глубоко проверено нет
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: не указана

### 3. One-time-priced session-prep kit for a single TTRPG system
- `G281-SCAN1-GAM-03`; семейство `games`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -2574
- Исходная причина: Free or near-free tools already cover the wedge (Session Zero Labs: free forever, premium from $5/mo; free ChatGPT; pay-what-you-want GM sheets; $8 Lazy DM ebook; $5 prewritten Paizo bounties), and the 4-hour prep pain is overstated (43% of 3,663 DMs prep <=1 

### 4. Simple flat-priced live-quiz tool for teachers and small trainers
- `G281-SCAN1-GAM-04`; семейство `games`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -707
- Исходная причина: The wedge is a price/limit edge and both halves are already covered: Blooket hosts live games free for up to 60 players (class size) and sells Plus at about $4.99/mo billed annually ($2.99 on other pages) with a 300-player cap, so $5/mo flat or $29/yr saves a 

### 5. GummySearch exit migration monitor
- `G281-SCAN1-SAS-01`; семейство `saas_or_micro_saas`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -1068
- Исходная причина: The only differentiator (an importer for GummySearch data) expires when GummySearch deletes all data on 2026-12-01, about 7 weeks from today (2026-10-10), leaving ~5 weeks after the entrant's day-17 launch; afterwards it is an undifferentiated $8 Reddit monito

### 6. Website and social archive for solo/small RIAs
- `G281-SCAN1-SAS-02`; семейство `saas_or_micro_saas`; проход 1
- Статус: очередь (не решено); вердикт `uncertain`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -2717
- Исходная причина: Need is real (Rule 204-2: copy of each advertisement kept 5 years), but the deciding facts could not be read: Patrina, Smarsh, Archive Intel, ArchiveSocial and PageFreezer pages were blocked this session and search budget was spent, so no incumbent price or we

### 7. Pay-per-capture web evidence with independent timestamp
- `G281-SCAN1-SAS-03`; семейство `saas_or_micro_saas`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: FREE_OR_CHEAPER_ALTERNATIVE: Snapoena's free tier already provides server-side capture, PDF, HTML, SHA-256 and an independent RFC 3161 token, which is everything the $15 offer sells. ProofSnap's $4.99 one-time pack of 10 captures undercuts the $15/month price 

### 8. Fivetran bill auditor and migration planner
- `G281-SCAN1-SAS-04`; семейство `saas_or_micro_saas`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: FREE_OR_CHEAPER_ALTERNATIVE: The diagnosis half (per-connector, per-table MAR and cost) is already free from Fivetran's dashboard, Platform Connector and dbt package, plus free vendor tools from Hevo and Sigma. Fivetran exposes no usage API, so ingestion requi

### 9. GPSR listing-field and label generator for US sellers (with Responsible Person referral)
- `G281-SCAN1-ECO-01`; семейство `ecommerce_or_dropshipping`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено нет
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: HARD_GATE_FAILED: entrant_edge=no_measured_advantage(inc=162,ent=191)

### 10. CSV landed-cost and margin auditor for post-de-minimis AliExpress-style dropshippers
- `G281-SCAN1-ECO-02`; семейство `ecommerce_or_dropshipping`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: FREE_OR_CHEAPER_ALTERNATIVE: Several free tools (Sticky.io, TrueProfit, tariffstool, tariffsnap, DHL MyGTS) and DropShip Intelligence's free tier already cover most of the landed-cost and margin wedge. The only possible differentiator, bulk per-SKU CSV audit, 

### 11. Flat-fee FBA lost-inventory reimbursement claim generator for very small Amazon sellers
- `G281-SCAN1-ECO-03`; семейство `ecommerce_or_dropshipping`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: FREE_OR_CHEAPER_ALTERNATIVE: The flat-fee edge already exists: Sellerboard at $15-19/mo bundles reimbursement with analytics, and Sellerise and Jarvio are also zero-commission. The real price gap is $3-7/mo. Amazon's automatic reimbursements shrank the address

### 12. Flat-fee chargeback evidence packets with human review for tiny Shopify stores
- `G281-SCAN1-ECO-04`; семейство `ecommerce_or_dropshipping`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -250.5
- Исходная причина: No edge. Review-before-submit and low price are already offered free or cheap: DisputePack has a free plan, Chargeback Copilot gives 3 free evidence PDFs a month, Chargeback Protector charges $4.99 a report, ChargebackWiz lets the merchant review and submit; S

### 13. SAM.gov entity-validation unblock and renewal service
- `G281-SCAN1-SVC-01`; семейство `services`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: FREE_OR_CHEAPER_ALTERNATIVE: A free government-backed substitute (APEX, 267 locations, plus the Federal Service Desk) covers the same pain in every state. The price edge is thin: about $99 against SBC's $200, not the 6x implied by the stale $597 baseline. Paid

### 14. Google Business Profile suspension evidence-pack reinstatement
- `G281-SCAN1-SVC-02`; семейство `services`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -3488
- Исходная причина: Killed, no structural edge. Google's own appeal tool and free guides already list the evidence documents; one guide says most straightforward suspensions can be self-filed and paid help is mainly worth it for account-level cases, which a $149 template cannot f

### 15. Amazon seller suspension Plan of Action drafting (simple categories)
- `G281-SCAN1-SVC-03`; семейство `services`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -6342
- Исходная причина: Killed, moderate confidence: the only edge is price ($495 vs $1,500), which is not an edge. An attorney incumbent offers a free review and free advice (covers the $99 review tier), sells 'human attorney review only' with about 610 reviews, calls non-law-firm p

### 16. Flat-fee human-reviewed dispute packs for non-drug medical bills (ER and ambulance)
- `G281-SCAN1-SVC-04`; семейство `services`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -537
- Исходная причина: No structural edge: human review of a templated letter is labour any rival can copy. Free or near-free substitutes cover most of the wedge: Dollar For (free, human advocates, hospital bills, 36,000+ patients), a free AI appeal-letter tool, a $20 denial-letter 

### 17. Exclusive-lead, pay-on-booking exchange for one home-service trade in one metro
- `G281-SCAN1-MKT-01`; семейство `marketplaces`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -1950
- Исходная причина: Killed on three major reasons: (1) paid homeowner traffic (~$149/lead non-branded, 25-40% booking) costs far more per booked job than the $100 fee, triggering the scan-1 falsifier; (2) the only cheaper route is SEO/rank-and-rent, 3-6 months and copyable, so no

### 18. Flat-fee exit marketplace for sub-$10K directories and micro-sites
- `G281-SCAN1-MKT-02`; семейство `marketplaces`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -710
- Исходная причина: Killed on three major reasons: (1) ExitBid's primary page confirms a flat $199 with 0% commission (4% of a $5K sale), under the entrant's 5% = $250, triggering the scan-1 falsifier; (2) escrow and niche focus are not edges, since directories already have categ

### 19. Low-commission niche storefront and marketplace for fee-squeezed Etsy sellers
- `G281-SCAN1-MKT-03`; семейство `marketplaces`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -4135
- Исходная причина: Killed on three major reasons. (1) A 5-8% all-in take cannot fund itself: Stripe lists 2.9% + 30c per charge, $2 per active connected account per month and 0.25% + 25c per payout, leaving about $0.24 of a $15 order (model). (2) The low-fee wedge already exists

### 20. VIN-based parts fitment marketplace for salvage, rebuilt and unsupported Teslas
- `G281-SCAN1-MKT-04`; семейство `marketplaces`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено нет
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: HARD_GATE_FAILED: entrant_edge=incumbent_source_not_https; evidence_depth=missing_verified_kinds:incumbent_price

### 21. County-level weekly permit lead email for local trade contractors
- `G281-SCAN1-DAT-01`; семейство `digital_or_data_products`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено нет
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: HARD_GATE_FAILED: entrant_edge=improvement_below_threshold(0.06451612903225806); evidence_depth=missing_verified_kinds:constraint

### 22. Catalog-matched recall alerts for small online sellers
- `G281-SCAN1-DAT-02`; семейство `digital_or_data_products`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено нет
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: HARD_GATE_FAILED: entrant_edge=no_measured_advantage(inc=80,ent=108)

### 23. DROP companion: California data-broker deletion verification report
- `G281-SCAN1-DAT-03`; семейство `digital_or_data_products`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -1600.74
- Исходная причина: The state already gives each DROP user a free status page where brokers must report DELETED/EXEMPT/OPTED-OUT/RECORD NOT FOUND; Consumer Reports tells users to re-check sites themselves; Optery's paid plans include before/after screenshots and EasyOptOuts remov

### 24. Failed restaurant inspection lead feed for uncovered metros
- `G281-SCAN1-DAT-04`; семейство `digital_or_data_products`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено нет
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: HARD_GATE_FAILED: evidence_depth=missing_verified_kinds:constraint

### 25. Model-specific replacement knobs for discontinued appliances
- `G281-SCAN1-PHY-01`; семейство `physical_products`; проход 1
- Статус: очередь (не решено); вердикт `uncertain`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -1296
- Исходная причина: Uncertain, leaning negative. The two decisive checks (orders per model-specific SKU; today's Etsy/eBay/RepairClinic listings by model number at or below $25) could not be done: WebSearch budget was gone and every Etsy, eBay-listing, Printables, RepairClinic, P

### 26. Post-Nest thermostat swap kits and trim plates
- `G281-SCAN1-PHY-02`; семейство `physical_products`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено нет
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: HARD_GATE_FAILED: entrant_edge=no_measured_advantage(inc=12.99,ent=12.99)

### 27. Wear-part kits for out-of-warranty prosumer gadgets
- `G281-SCAN1-PHY-03`; семейство `physical_products`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено нет
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: HARD_GATE_FAILED: entrant_edge=improvement_below_threshold(0.2)

### 28. No-minimum micro-volume FBA prep for small Amazon sellers
- `G281-SCAN1-PHY-04`; семейство `physical_products`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -5475
- Исходная причина: The wedge (no monthly minimum, flat per-unit price) is already sold: one directory lists 60 no-minimum prep centers and Honeybee publishes a flat $1/unit all-in rate with no minimum, which triggers the case's own falsifier. Underpricing at $0.70 is 'cheaper', 

### 29. Flat-fee caption and transcript backlog for small-government meeting video
- `G281-SCAN1-MED-01`; семейство `media_or_content`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -825
- Исходная причина: Three major problems. (1) A free path covers the wedge: YouTube publishes automatic captions on its own and owners can edit them in YouTube Studio at no fee; Whisper is MIT-licensed, so there is no moat. (2) A back catalog created before the compliance date is

### 30. Vertical-specific city-agenda alert digest (e.g. short-term-rental rules)
- `G281-SCAN1-MED-02`; семейство `media_or_content`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: 755
- Исходная причина: The only claimed edge is price ($15 vs $40), which is not structural. Topic-level agenda alerts already exist free or near-free across the same cities (Voterheads: free for 5 orgs, $2.50/org beyond, 1,500+ cities; Legistar native keyword alerts), the data laye

### 31. Non-Amazon AI audiobook proofing and finishing service for indie authors
- `G281-SCAN1-MED-03`; семейство `media_or_content`; проход 1
- Статус: очередь (не решено); вердикт `queued`; глубоко проверено нет
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: не указана

### 32. Sponsor-finding lead sheets for micro-newsletters
- `G281-SCAN1-MED-04`; семейство `media_or_content`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: FREE_OR_CHEAPER_ALTERNATIVE: several sponsor databases already exist, including a free list (Gumroad) and paid ones; no differentiation shown; lead-data legality unconfirmed.

### 33. Wyzant exit kit: flat-fee roster import, scheduling and recurring invoicing for solo tutors
- `G281-SCAN1-EDU-01`; семейство `education_training`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: FREE_OR_CHEAPER_ALTERNATIVE: TutorTab is $0 for tutors (scheduling, invoicing, booking page), so a $9/mo exit kit is not cheaper; the only wedge left (Wyzant roster import) is unproven and contract-restricted.

### 34. Homeschool target-college requirement gap check
- `G281-SCAN1-EDU-02`; семейство `education_training`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено нет
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: HARD_GATE_FAILED: entrant_edge=no_measured_advantage(inc=19,ent=19)

### 35. Teachers Pay Teachers listing migration utility
- `G281-SCAN1-EDU-03`; семейство `education_training`; проход 1
- Статус: очередь (не решено); вердикт `uncertain`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -131
- Исходная причина: Leans kill but I could not re-verify the two facts a kill needs: seller earnings (case file says most TPT sellers earn $0-$100/month) and any existing migration tool. Verified: sellers own their IP and keep their own files, TPT can close accounts and withhold 

### 36. Local-first IEP caseload and review-deadline tracker for individual special-education teachers
- `G281-SCAN1-EDU-04`; семейство `education_training`; проход 1
- Статус: отклонена/убита; вердикт `rejected`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: FREE_OR_CHEAPER_ALTERNATIVE: SPED Goals IEP Tracker is free up to 20 students (premium $2.99/mo); the entrant at $5/mo is more expensive than the real incumbent.

### 37. Flat-price outbound webhooks with DPA included for small API vendors
- `G281-SCAN1-DEV-01`; семейство `b2b_api_devtools`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -281
- Исходная причина: Killed. Outbound webhooks with retries, signing and a customer portal are already free and permissively licensed (Svix MIT, Hookdeck Outpost Apache-2.0, which also sells a managed tier from $10 per million events with SOC 2), and a DPA is a free CC BY 4.0 temp

### 38. Curated third-party API change alerts for a niche vertical
- `G281-SCAN1-DEV-02`; семейство `b2b_api_devtools`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: 91
- Исходная причина: Killed on edge and alternatives; payment is unproven. For vendors that publish OpenAPI specs, free open-source tools already diff, flag breaking changes and alert (oasdiff, openapi-changes, apibreak CI action), and the CC0 APIs.guru directory auto-updates a cu

### 39. Fixed-price hosted MCP server for small API/SaaS vendors
- `G281-SCAN1-DEV-03`; семейство `b2b_api_devtools`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -1036
- Исходная причина: The wedge (OpenAPI spec to hosted MCP server with generic OAuth) is already sold self-serve by funded vendors at $0-$41/month (Gram free tier, API to MCP $0/$6.99, Zuplo incl. free plan), OAuth is available as an open-source Cloudflare library, and Fiverr offe

### 40. Direct API monetization layer for indie API sellers leaving marketplace fees
- `G281-SCAN1-DEV-04`; семейство `b2b_api_devtools`; проход 1
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -133
- Исходная причина: Both pitched niches are first-party or free elsewhere: Stripe documents metered billing, prepaid credit grants (real-time drawdown via its own Metronome) and agent pay-per-call 'Machine payments' (MPP/x402) with starter code, and Zuplo lists API monetization (

### 41. Cross-state normalized highway pay-item unit-price benchmark built from state DOT bid tabulations
- `G281-SCAN2-DAT-1`; семейство `digital_or_data_products`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the multi-agency incumbent (Bid Express, $54-60/mo) and free DOT tools cover most of the wedge, the cross-state crosswalk is copyable labor over public records, and the price ceiling caps gross profit; no structural edge is evidenced.

### 42. Death Master File match API / batch service run as a certified LADMF licensee for small pension plans, insurers and credit unions
- `G281-SCAN2-DAT-2`; семейство `digital_or_data_products`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: licence-intrinsic edge exists but is purchasable and already held by certified incumbents, and the documented fixed NTIS costs (about $19k in year one plus assessor and security) break the $10k reference-entrant capital limit.

### 43. A la carte FDA Form 483 / EIR archive and citation-trend subscription for small FDA-regulated manufacturers and consultants
- `G281-SCAN2-DAT-3`; семейство `digital_or_data_products`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the only differentiator is a lower price, FOIA supply is slow and non-exclusive, and the incumbent (47,000+ documents, instant access) plus FDA's free reading room and dashboard cover the wedge.

### 44. Contractor insurance and bond expiry (x-date) calendar with carrier-switch history, built from open state contractor-licence registers
- `G281-SCAN2-DAT-4`; семейство `digital_or_data_products`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: free state files and pay-per-record packagers already supply the expiry dates; the compounding carrier-switch history is a real but unvalidated and slow-to-build add-on that cannot produce differentiated revenue within 365 days.

### 45. Success-fee IEEPA tariff-refund filing service for small e-commerce importers
- `G281-SCAN2-ECO-1`; семейство `ecommerce_or_dropshipping`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the refund-filing step is customs business (ECO1-E4) and CAPE submission is restricted to the IOR or its licensed broker (ECO1-E7), a free self-file path and incumbents (FreightRight, Ayar Law, Leyton) cover the wedge (ECO1-E5, ECO1-E2, ECO1-E1), carri

### 46. Multi-country EU packaging-EPR authorised-representative subscription for non-EU direct-to-consumer sellers
- `G281-SCAN2-ECO-2`; семейство `ecommerce_or_dropshipping`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -11645
- Исходная причина: Killed. The wedge is already sold with published prices: Eldris per-country all-in (DE GBP 185), Lizenzero 31 countries with the representative included (EUR 299-499), Ecosistant EUR 250. Local seats are a cost, not an edge: a German UG alone is about EUR 5,50

### 47. California Prop 65 notice early-warning feed for online sellers
- `G281-SCAN2-ECO-3`; семейство `ecommerce_or_dropshipping`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the data is the AG's free register (ECO3-E3), labs publish free monthly analyses (ECO3-E6), an Apify actor sells the same structured search for $0.01 per 1,000 results (ECO3-E1), warning display apps cost $4.99 per month (ECO3-E2), and I found no evide

### 48. Amazon seller liability-insurance agency (certificate-of-insurance placement and renewals)
- `G281-SCAN2-ECO-4`; семейство `ecommerce_or_dropshipping`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: Amazon's Accelerator network (ECO4-E3) and carriers selling direct from about $25 per month (ECO4-E1, ECO4-E4) fully cover the wedge at no extra cost to the seller, the only moat (a producer licence) is open to anyone, and commission of roughly 10-20% 

### 49. Steam sales-actuals benchmark panel for indie developers
- `G281-SCAN2-GAM-1`; семейство `games`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the data edge is real in principle (Steamworks actuals are private and sharing is allowed, GAM-1-E3), but free survey benchmarks cover the headline metric (GAM-1-E6), the only demonstrated collector of developer actuals needed a large newsletter audien

### 50. Success-fee royalty statement review for developers on publisher deals
- `G281-SCAN2-GAM-2`; семейство `games`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: demand exists (day rates of GBP 500-1,000, GAM-2-E1; about $16m recovered by two firms since 2002, GAM-2-E2) but the market is small and episodic (GAM-2-E3, GAM-2-E4), success-fee terms are not exclusive to an entrant (GAM-2-E6), books access runs thro

### 51. Premium Godot add-ons sold through the official Godot Asset Store
- `G281-SCAN2-GAM-3`; семейство `games`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -1110
- Исходная причина: Edge not real: official paid listings are not live (free-only beta, selected creators first, no date, fee set per upload and unpublished) and the in-editor store is open to any approved seller, while itch.io and Getly already sell Godot add-ons. Demand is thin

### 52. Curated pay-what-you-want tabletop RPG bundle storefront
- `G281-SCAN2-GAM-4`; семейство `games`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: buyers do pay (GAM-4-E1, GAM-4-E3) but the compounding asset is a buyer list and publisher trust that the incumbent built over 13 years (GAM-4-E4); organizer guidance says bundles depend on people who already know and trust you (GAM-4-E5), the tool is 

### 53. Open-slot exchange for small-farm meat processing (inspected plants)
- `G281-SCAN2-MKT-1`; семейство `marketplaces`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the scarce resource is plant capacity, which a booking layer cannot create; plants already buy scheduling software with customer portals (MKT-1-E4, MKT-1-E5, MKT-1-E6) and discovery is free (MKT-1-E3), so no structural edge or payer was found. Not veri

### 54. Lab-bid exchange for children's-product compliance testing
- `G281-SCAN2-MKT-2`; семейство `marketplaces`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: ComplianceGate already sells a booking and price-comparison platform from 199 USD a year (MKT-2-E1, MKT-2-E3), and free lab lists exist (MKT-2-E4, MKT-2-E5); a quote dataset is not an exclusive asset. Not verified: ComplianceGate's lab count or revenue

### 55. Acquired niche hobby forum with paid seller membership classifieds
- `G281-SCAN2-MKT-3`; семейство `marketplaces`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -3348.5
- Исходная причина: Killed. (1) No exclusive edge: where a seller fee was made mandatory, members listed on both sites and 'Sold Elsewhere' ads rose (D6), Audiogon fee rises pushed sellers to a rival (D8), and Reverb, Facebook and Reddit swap subs with free trade-confirmation fla

### 56. Price-listed booking directory for immigration medical exams (Form I-693 civil surgeons)
- `G281-SCAN2-MKT-4`; семейство `marketplaces`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: easyIME already offers a free, price-listed, online-booking directory for civil-surgeon exams (MKT-4-E3, MKT-4-E4), the supply list is a public USCIS registry (MKT-4-E1), and exams are one-time purchases. Not verified: easyIME's clinic count, traffic a

### 57. Marketplace-bought niche newsletter (1k-10k subscribers) held for sponsor income
- `G281-SCAN2-MED-1`; семейство `media_or_content`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Buying small newsletters is a real, priced market (about 2x annual profit; sponsors pay per-issue CPMs), but the price per subscriber ($1.84 on the 8.3k listing) is inside the cost of renting subscribers ($1.50-$2.50), so there is no measurable structural edge

### 58. Acquired evergreen podcast back-catalog (10k+ monthly downloads) monetized through ad marketplaces
- `G281-SCAN2-MED-2`; семейство `media_or_content`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -10044
- Исходная причина: The only qualifying listing (Flippa, 11k downloads/mo, $7,960-$9,950) is cheap because it is decaying: seller-reported revenue fell from $32,852 (2022) to a projected $8,887 (2026). That revenue (~$67 per 1,000 downloads) is about 4x what open ad marketplaces 

### 59. State-qualified weekly newspaper that carries statutory legal notices
- `G281-SCAN2-MED-3`; семейство `media_or_content`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: The statutory qualification barrier is real but accrues to incumbent papers: Texas requires 12 months of continuous weekly publication plus second-class mail, so a $10k entrant earns no notice revenue in year one, and the only priced paper listing asks $154,90

### 60. Pooled AI licensing agency for small-publisher archives
- `G281-SCAN2-MED-4`; семейство `media_or_content`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: AI buyers pay large sums to a few large rights holders, but for the long tail the market 'settles toward a value of zero', and TollBit, ProRata and Cloudflare already offer small publishers free or revenue-share intermediation. No exclusive supply or buyer acc

### 61. Approved second-source supplier of simple spare parts to the Defense Logistics Agency (Source Approval route, 40% split award)
- `G281-SCAN2-PHY-1`; семейство `physical_products`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -14190
- Исходная причина: Killed. Public DLA and NAVSUP pages say SAR approval goes to the actual manufacturer (distributors are not approved), needs prior Government production history, and the approval would sit on the machine shop's CAGE, so a broker using contract shops gets no edg

### 62. Managed right-to-repair parts-and-tools desk for small consumer-hardware brands (official parts store plus price-parity compliance log)
- `G281-SCAN2-PHY-2`; семейство `physical_products`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -4890
- Исходная причина: Killed. Parts must be sold at cost or on authorized-provider terms (PHY2-E2, PHY-2-D11), so revenue is a retainer plus per-order fee only. A brand can meet the duty itself for $0-$39/month or via the replacement-product off-ramp (D1); enforcement is attorney-g

### 63. UL 2271-certified drop-in replacement battery packs for CPSC-warned Rad Power e-bike batteries
- `G281-SCAN2-PHY-3`; семейство `physical_products`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the demand is real (31 fires, no OEM remedy; PHY3-E1, PHY3-E2) but certification of a pack design is an estimated $34,000-$56,000+ (PHY3-E5), certified Rad-fit packs already exist or are pre-selling (PHY3-E3, PHY3-E4, PHY3-E7), and no structural edge i

### 64. Hazmat-trained dangerous-goods prep and ship service for small Amazon sellers (lithium, aerosols, flammables)
- `G281-SCAN2-PHY-4`; семейство `physical_products`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: no structural edge. The compliance credential is a $299 course (PHY4-E3), 36 hazmat prep centers already compete at $0.40-$1.25 per unit and one charges no hazmat surcharge (PHY4-E2), and a DIY route is cheaper for sellers who prefer to self-prep.

### 65. Success-fee late-delivery refund auditor for small UPS/FedEx shippers
- `G281-SCAN2-SAS-1`; семейство `saas_or_micro_saas`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: same success-fee model is already sold by Refund Retriever (50%) and Lojistic (29% contingency, $0 bundle), DIY manual claims cover low-volume shippers, and a lower percentage is 'cheaper', not an edge (SAS-1-E1, SAS-1-E2, SAS-1-E6). Only unresolved it

### 66. HFC refrigerant leak-rate log and repair clock for small HVAC/refrigeration contractors
- `G281-SCAN2-SAS-2`; семейство `saas_or_micro_saas`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: a real EPA duty exists (SAS-2-E1) but at least four products plus a free template already cover the wedge at $0-$149 per month, records are exportable so lock-in is weak, and the one competitor with public revenue shows $0/mo (SAS-2-E2, SAS-2-E3, SAS-2

### 67. Pre-built vendor sub-processor change monitor with change history
- `G281-SCAN2-SAS-3`; семейство `saas_or_micro_saas`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: compounding-history edge is only claimed and every piece of the wedge except a prebuilt URL list is already free or under $14 per month (PageCrawl, changedetection.io, Visualping, Apify), and the dedicated actor shows 2 total users (SAS-3-E1, SAS-3-E4,

### 68. Lab-neutral SKU certificate register for CPSC eFiling (small consumer-product importers)
- `G281-SCAN2-SAS-4`; семейство `saas_or_micro_saas`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -3892
- Исходная причина: The lab-neutral gap is already sold: Comply PRO+ markets supplier logins, data collection, certificate generation and one-click Product Registry filing to Amazon sellers (D1, D2, D4), ComplianceGate sells a certificate platform from $199/yr (D5), and the Regis

### 69. Flat-fee health-lien reduction desk for small personal-injury firms
- `G281-SCAN2-SVC-1`; семейство `services`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: no structural edge. The Medicare step is a CMS portal (SVC1-E6), in-house staff already do the rest (SVC1-E7), specialists already sell flat-fee resolution up to about $1,800 per case (SVC1-E1, SVC1-E8), and the outcome-based pricing that could have be

### 70. Utility-program backflow assembly testing and annual-agreement route
- `G281-SCAN2-SVC-2`; семейство `services`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -6285
- Исходная причина: Killed. The licence is no moat: Oregon needs a 5-day course, no experience, a $97.50 fee (D15, D16); Marin Water lists 63 testers from 34 firms (D17); ECUA lists ~57 (SVC2-E5). Utility contracts are experience-weighted and contested (EWEB: experience 40 of 100

### 71. EU responsible-person subscription for non-EU product sellers (GPSR)
- `G281-SCAN2-SVC-3`; семейство `services`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the demand is real and recurring (SVC3-E3, SVC3-E4) and the relabeling lock-in is real (SVC3-E6), but a new provider has no acquisition edge against EAS (4,000+ businesses at EUR 199 a year and up, SVC3-E1, SVC3-E7) or a free EU importer route (SVC3-E2

### 72. Contingency-fee duty-drawback and IEEPA tariff-refund recovery for small importers
- `G281-SCAN2-SVC-4`; семейство `services`; проход 2
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the IEEPA refund wedge is covered by the free CAPE portal and carrier auto-filing (SVC4-E5, SVC4-E6) and filing rights sit with the importer or the broker that filed the entries (SVC4-E3); drawback is already sold at 15 to 30 percent contingency (SVC4-

### 73. Acquired sub-$10k Amazon-Associates content site (marketplace purchase, links re-pointed to the buyer's own Associates account)
- `G281-SCAN3-AFF-1`; семейство `affiliate_or_referral`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Sub-$10k affiliate sites do exist and sell (a $10,000-reserve Amazon site sold on Flippa), but at 25-38x monthly profit they pay back in about 28-34 months on seller-reported numbers, the Amazon commission relationship cannot be assigned and is terminable at w

### 74. Independent franchise-broker practice earning franchisor-paid commission on each franchise sold (free to the prospective buyer)
- `G281-SCAN3-AFF-2`; семейство `affiliate_or_referral`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Franchisors do pay brokers only on a closed sale, but entry is open (1,000+ association members keeping 100% of commissions, 68+ FranNet consultants), the buyer pays nothing anywhere so price is no edge, a stranger has no evidenced prospect channel, and regist

### 75. Freight-factoring referral partner for newly authorised US truckers (published bounties from factoring companies), sourced from the public FMCSA new-authority data
- `G281-SCAN3-AFF-3`; семейство `affiliate_or_referral`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Published bounties are real (Outgo $500 per truck up to $2,500, Summar 15% per load) and lead data is nearly free, which is exactly why there is no edge: any dispatcher, rival referrer or the factoring companies' own sales teams use the same feed and terms. Th

### 76. Niche shopping-assistant Chrome extension (price-drop alerts or coupon finder) earning affiliate commission on user-initiated purchases
- `G281-SCAN3-AFF-4`; семейство `affiliate_or_referral`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Affiliate extensions are lawful only with a transparent user benefit and a user action per link, Amazon forbids its links in extensions, and free incumbents (Honey, CamelCamelCamel, Keepa) already cover price tracking with far larger audiences; no structural e

### 77. Small merchant-services residual portfolio bought from an exiting sales agent (processor-approved assignment of recurring card-processing residuals)
- `G281-SCAN3-AFF-5`; семейство `affiliate_or_referral`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Residuals are recurring and portfolios trade at 20-40x monthly residuals, but $10,000 buys only about $500 a month (about 22-25 month payback, negative in the pessimistic case), the stream is controlled by processor consent and unilateral split changes, and no

### 78. Pay-per-event SEC EDGAR Form 4 insider-transaction data Actor sold through the Apify Store
- `G281-SCAN3-API-1`; семейство `b2b_api_devtools`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the cheapest credible alternative is $0 and covers the wedge (official SEC API plus MIT edgartools), a paid convenience layer already exists at $49/month (sec-api.io), and the only edge is a claimed Apify Store position that any copycat can contest. No

### 79. Stripe Dashboard app that benchmarks a merchant's subscription metrics against a panel built from the accounts that install it
- `G281-SCAN3-API-2`; семейство `b2b_api_devtools`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the compounding-data edge is prohibited by Stripe's own app rules (cannot resell or publish Stripe-user data) and already provided first-party by Stripe Billing analytics. Not verified: the web-search budget was exhausted and Baremetrics, ChartMogul an

### 80. Paid GitHub Marketplace app that flags abandoned or maintainer-changed dependencies
- `G281-SCAN3-API-3`; семейство `b2b_api_devtools`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the free Scorecard API and dataset and free Marketplace apps with tens of thousands of installs cover the wedge's signals, the history asset is not exclusive, and GitHub's paid-listing gate (about 100 installations plus verified publisher) blocks a str

### 81. Adopted abandoned WordPress.org plugin monetised with a paid add-on or hosted service
- `G281-SCAN3-API-4`; семейство `b2b_api_devtools`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: adopting is a genuine, free way to inherit an audience that a new plugin cannot get (new listings show fewer than 10 installs), but the adoptable supply is only 18 plugins topped at 1,000+ installs, free substitutes exist, and the directory's rules lim

### 82. Long-retention Stripe webhook-event archive with replay, offered as a Stripe App
- `G281-SCAN3-API-5`; семейство `b2b_api_devtools`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: Stripe documents a free recovery path (event-ID log plus the Events API, resend for 15 to 30 days) that fully covers the wedge at $0, Hookdeck's free plan and open-source Svix and Convoy cover queueing and retries, and the claimed system-of-record edge

### 83. Acquired WooCommerce B2B/wholesale plugin business with renewing annual licences
- `G281-SCAN3-B2B-1`; семейство `b2b_operations`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -9209
- Исходная причина: Killed. Every public listing of a plugin business with renewing licences starts near $30k (Flippa $30,000 for ~$6.7k revenue with 60% churn; Acquire $31,500 for $8.9k revenue; Flippa $149,300 for $47k), while the sub-$10k listings seen were lifetime-licence ($

### 84. Annual FTC Safeguards Rule evidence pack for non-bank financial firms (scans, board report, training, breach-notice log)
- `G281-SCAN3-B2B-2`; семейство `b2b_operations`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: no structural edge (portable record; open-source scanner and AGPL compliance platform exist: B2B-2-E7/E8/E9; the Qualified Individual may be any employee, affiliate or provider: B2B-2-E5) and the recurring testing and board-report duties do not bind fi

### 85. Medicare enrollment-revalidation desk for small provider and supplier practices
- `G281-SCAN3-B2B-3`; семейство `b2b_operations`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: no structural edge (the due-date list is public and CMS itself notifies providers: B2B-3-E3/E4), a free guided CMS tool covers the filing (B2B-3-E7), and a 5-year cycle (B2B-3-E1/E6) leaves no repeat revenue. Not checked: whether any consultants charge

### 86. Open Payments (Sunshine Act) annual reporting service for small drug and device makers
- `G281-SCAN3-B2B-4`; семейство `b2b_operations`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: no structural edge (CMS runs the submission system and publishes the data: B2B-4-E4/E7; the ledger is portable), and nothing shows a stranger can reach small makers or that they pay outsiders. Penalty exposure (B2B-4-E1/E3) is real, so a stronger entra

### 87. SEC-registered transfer agent and shareholder-ledger service for micro-cap and private issuers
- `G281-SCAN3-B2B-5`; семейство `b2b_operations`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -7260
- Исходная причина: Open question settled enough to kill. A micro-agent under 500 items per six months is exempt from the accountant report (D3, D4), so the old cost stack was overstated, but the market is crowded and priced against the entrant: StartEngine Secure bundles an SEC-

### 88. Acquired sub-$10k consumer subscription iOS app (marketplace purchase, App Store transfer) with US web-checkout billing
- `G281-SCAN3-CON-1`; семейство `consumer_products`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -10229.41
- Исходная причина: Killed. (1) Under $10k the market sells almost no verifiable subscription revenue: listings that disclose MRR or subscribers ask about 17-27x the monthly figure ($15k-$52k, D3-D5); the one cheap outlier (Jawsi, $10k ask, $1,296/mo profit seller-reported, $30k 

### 89. Paid personal-data-broker removal subscription for US consumers
- `G281-SCAN3-CON-2`; семейство `consumer_products`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: a free official deletion channel (DROP, mandatory broker processing from August 1, 2026, California residents), a free maintained opt-out list and more than a dozen paid services already cover the wedge, and a stranger has no exclusive input. Paid-serv

### 90. Hosted campsite-cancellation alert subscription for non-technical campers (Recreation.gov and state-park systems)
- `G281-SCAN3-CON-3`; семейство `consumer_products`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: free MIT-licensed camply already provides continuous cancellation search across Recreation.gov and state systems with SMS, Slack, Telegram and push alerts, newer free watchers are appearing, and the claimed cancellation-history edge is unevidenced. Pai

### 91. Contingency-fee residential property-tax appeal service for homeowners, re-filed every year
- `G281-SCAN3-CON-4`; семейство `consumer_products`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: Ownwell already sells the same contingency-fee annual appeal service, publishes free DIY guides and cites $774 average savings, so the entrant has no exclusive input beyond a lower percentage; Texas registration is open to any qualified applicant. No a

### 92. Class-action settlement and refund claim-discovery subscription app for consumers
- `G281-SCAN3-CON-5`; семейство `consumer_products`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: demand is proven by one incumbent app at $1.2M ARR, but it is a one-year-old leader out of reach at its $2.655M asking price, the claimed data edge is not exclusive, and official refund programs are free (some automatic) while the FTC warns against pay

### 93. Florida condo/HOA board-member certification and annual-CE online course (DBPR-approved provider)
- `G281-SCAN3-EDU-1`; семейство `education_training`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: a free regulator course (EDU1-E2) and a free large-manager course (EDU1-E1) already cover the 4-hour certification, about 320 provider entries are approved (EDU1-E5), and approval is open to any applicant (EDU1-E4). Not verified: any paid price in this

### 94. Florida court-approved online parenting / divorce-education course (DCF-approved provider, fee per parent)
- `G281-SCAN3-EDU-2`; семейство `education_training`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: a one-time $14 to $30 purchase (EDU2-E1, EDU2-E2) sold by dozens of approved online providers (EDU2-E5, a 2014 snapshot) with open DCF approval (EDU2-E4) and no recurring revenue. Not verified: current DCF approved-provider count (the DCF table did not

### 95. State-approved cannabis responsible-vendor (RVT) worker-training provider (Maryland rolling approval; Illinois odd-year window)
- `G281-SCAN3-EDU-3`; семейство `education_training`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: a $21 approved course already exists (EDU3-E1) among 8 Maryland and 18 Illinois approved providers (EDU3-E5, EDU3-E8), approval is open to anyone for $500 (EDU3-E3), Illinois is closed until August 2027 (EDU3-E6), and New York is free (EDU3-E9). Not ve

### 96. Acquired small online continuing-education / exam-prep school bought on a business marketplace, run for renewal-cycle learners
- `G281-SCAN3-EDU-4`; семейство `education_training`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the profitable approved school found costs $1.85 million (EDU4-E1), sub-$25,000 education listings earn at most $500 a month or lose money (EDU4-E2, EDU4-E5), and provider approvals are non-transferable where checked (EDU4-E3, EDU4-E4) and cheap to get

### 97. Pennsylvania Act 48 approved-provider online teacher professional-development courses (per-hour, five-year renewal cycle)
- `G281-SCAN3-EDU-5`; семейство `education_training`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: open approval (EDU5-E4), rivals already selling the same hours at $165 per 45 hours (EDU5-E1, EDU5-E6), free state courses and district in-service (EDU5-E3, EDU5-E5), and no sourced channel for a stranger. Real demand and a recurring five-year cycle ex

### 98. Owner-operated small pool-service route bought from an exiting operator (under 25 accounts, seller note, 90-day retention holdback)
- `G281-SCAN3-LOC-1`; семейство `local_businesses`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: the smallest routes ask a median $33K with seller financing on about 3% of listings (LOC1-E3, LOC1-E4), the purchased account base is month-to-month with 5-20% early churn and already priced in (LOC1-E1, LOC1-E6), and the buyer ends up doing about 14 h

### 99. Used-cooking-oil free-pickup collection route (locked containers, vacuum truck, month-to-month restaurant accounts)
- `G281-SCAN3-LOC-2`; семейство `local_businesses`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: an $80K-$150K truck-based business (LOC2-E1, LOC2-E4) selling a service rivals already give away on month-to-month, cancel-anytime terms (LOC2-E6), with thin per-stop profit and an 18-24 month ramp. Not verified: a current yellow-grease price per pound

### 100. Restaurant kitchen-exhaust (hood and duct) cleaning on recurring NFPA 96 cycles, sold on contract with digital service certificates
- `G281-SCAN3-LOC-3`; семейство `local_businesses`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: -16215
- Исходная причина: Killed. Demand is real (code-mandated cycles; a listed NorCal firm shows ~600 repeat clients, $375K revenue, $90K cash flow) but a stranger has no structural edge: the IKECA exam is open ($750 non-member, no stated prerequisite), photo records are commodity so

### 101. Leveraged 50-account pool-service route (SBA or seller-note financed) run by hired technicians so the entrant does not work the pools
- `G281-SCAN3-LOC-4`; семейство `local_businesses`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: stated SDE margins of 76-79% (LOC4-E6) include the owner's own labour; replacing that labour with a hired technician and adding about $860 a month of debt service leaves almost nothing on the baseline and a loss under the pessimistic case, with no stru

### 102. Restaurant back-of-house route bundle: free used-cooking-oil pickup as the door-opener, hood cleaning as the paid recurring service (composite hypothesis)
- `G281-SCAN3-LOC-5`; семейство `local_businesses`; проход 3
- Статус: отклонена/убита; вердикт `killed`; глубоко проверено да
- Пессимистическая прибыль первого года в долларах США по исторической модели: нет значения
- Исходная причина: Killed: a composite hypothesis that depends on an $80K-$150K oil-collection truck (LOC5-E2) to win a door-opener that restaurants can cancel at any time (LOC5-E1), with no evidence that oil-pickup accounts buy hood cleaning. The hood-cleaning half is carried i

## niches - все записи

### Contractor estimate → invoice → job-cost reconciliation
```json
{
  "id": "3bc02868-241b-4077-a59d-7a8b662f50e1",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "contractor_estimate_invoice_reconciliation_20261003",
  "name": "Contractor estimate → invoice → job-cost reconciliation",
  "plain_ru_description": "Для малых подрядчиков: сводить смету, изменения объёма, инвойс и фактические расходы без ручной сверки нескольких систем и Excel.",
  "buyer": "Small construction / specialty contractor owner, office manager, bookkeeper",
  "purchase_trigger": "Scope changes create mismatches between estimate, invoices and job-cost records; manual reconciliation consumes office time and delays billing.",
  "differentiation_hypothesis": "Narrow reconciliation layer instead of another all-in-one contractor OS: ingest estimate/invoice/expense evidence, flag mismatches, require human approval, export back to existing accounting workflow.",
  "primary_channel": "Direct web / app marketplace / accounting-contractor ecosystem",
  "status": "rejected",
  "source_batch": "live_web_scan_20261003_01",
  "confidence_grade": "B",
  "current_adjusted_score": "38.07",
  "unknowns": {
    "churn_risk": "unknown",
    "reentry_condition": "Evidence a structural entrant edge: controlled distribution, proprietary data, embedded workflow position, or structural unit-economics advantage.",
    "buyer_segment_size": "unknown",
    "api_integration_access": "unknown",
    "exact_wtp_for_narrow_reconciliation": "unknown"
  },
  "kill_conditions": [
    "No repeated pain outside isolated anecdotes",
    "Existing tools solve reconciliation cleanly at <$30/mo",
    "Required integrations are closed or uneconomic",
    "Support burden exceeds gross margin"
  ],
  "feedback_state": {
    "user_feedback": null
  },
  "created_at": "2026-10-03 06:39:35.061737+00",
  "updated_at": "2026-10-03 07:09:26.028157+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small-carrier trucking bookkeeping and financial back-office
```json
{
  "id": "7dd5fa33-63a9-4f9f-a711-8e4bd78f1ddc",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V5-04",
  "name": "Small-carrier trucking bookkeeping and financial back-office",
  "plain_ru_description": "Owner-operators и малые fleets, которым нужен ежемесячный bookkeeping: settlements, fuel/repair/insurance expenses, reconciliations, truck-level P&L, factoring/payment tracking и CPA-ready books — без tax-return preparation или CPA/assurance work на старте.",
  "buyer": "Chicago-area owner-operators and small trucking fleets, initially 1–10 power units, reachable through the existing owner-confirmed trucking network.",
  "purchase_trigger": "Books are behind or unclear, tax/CPA handoff is painful, factoring/settlement reconciliation is messy, fleet grows beyond one truck, lender/insurance/management needs clean P&L, or owner wants monthly truck-level profitability.",
  "differentiation_hypothesis": "The qualifying entrant edge is warm access to an existing ~40-contact trucking network. Trucking-domain knowledge helps chart-of-accounts and transaction interpretation but is not counted as unique. The model is rejected if it is merely generic bookkeeping with no efficient trucking-specific workflow.",
  "primary_channel": "Existing owner-confirmed trucking network first; referrals second. No paid lead volume is assumed.",
  "status": "rejected",
  "source_batch": "reveng_v5_edge_first_wave3_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Actual monthly transaction volume and service hours by 1-truck vs 2-10-truck account are unknown.",
    "Software/client-file cost per account is unmodeled.",
    "Catch-up/cleanup labor can be much larger than recurring monthly close.",
    "Actual network willingness to outsource bookkeeping is unmeasured.",
    "Bookkeeping quality-control/review process must be defined.",
    "Tax-return preparation, tax advice, attest/assurance and CPA-title use must remain out of launch scope unless proper credentials/requirements are satisfied.",
    "Retention/churn is unknown."
  ],
  "kill_conditions": [
    "Reject if full managed recurring price is materially below ~$350/account without a correspondingly lighter scope.",
    "Reject if routine recurring service exceeds roughly 5 hours/account/month at ~$350 realized price after workflow stabilization.",
    "Reject if cleanup/catch-up cannot be separately priced and scheduled.",
    "Reject if the warm network produces no qualified bookkeeping demand in a future approved test.",
    "Reject if QA/review requires founder-only accounting expertise that cannot be standardized or hired.",
    "Reject if customers primarily demand regulated tax/CPA/assurance services outside the bounded launch scope.",
    "Reject if warm-network buying interest is weak at $249-$299/month.",
    "Reject or redesign if routine recurring work exceeds 5 hours/account/month.",
    "Reject if acquisition requires generic paid leads because the service itself is not differentiated."
  ],
  "feedback_state": {
    "stage": "v5_edge_first_candidate",
    "corrected_at": "2026-10-09T05:02:31.243543+00:00",
    "not_a_finalist": true,
    "user_fit_applied": false,
    "v6_global_status": "rejected_hard_gate",
    "correction_reason": "Prior global score used retracted/current-user-specific trucking-network assumptions. Independent entrant edge is not evidenced.",
    "global_scoring_version": "reveng_v6_independent",
    "user_specific_edge_removed": true,
    "external_actions_authorized": false
  },
  "created_at": "2026-09-24 22:32:53.675481+00",
  "updated_at": "2026-10-09 05:02:31.243543+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Special-ed transition/vocational job-skill curriculum series
```json
{
  "id": "f63633f2-2e10-488f-92c4-7304994dfd06",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "33f19f48-fe61-4c6f-bce4-190f21ad2241",
  "niche_key": "B2-01",
  "name": "Special-ed transition/vocational job-skill curriculum series",
  "plain_ru_description": "Серия возрастно-адекватных учебных модулей для перехода во взрослую жизнь и рабочих навыков.",
  "buyer": "special-ed teachers / transition programs",
  "purchase_trigger": "учебная программа и подготовка к работе",
  "differentiation_hypothesis": "job-specific simulations + differentiated levels",
  "primary_channel": "TPT",
  "status": "paused",
  "source_batch": "batch2",
  "confidence_grade": "B",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Realtor closing house-photo puzzle
```json
{
  "id": "4f325193-4577-4458-b12b-47fc2e9cb39b",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "57484d82-05fc-4482-a6bc-d63dac5608dd",
  "niche_key": "B2-17",
  "name": "Realtor closing house-photo puzzle",
  "plain_ru_description": "Пазл с фото/иллюстрацией дома и брендингом/данными closing.",
  "buyer": "realtors/homebuyers",
  "purchase_trigger": "closing gift",
  "differentiation_hypothesis": "house photo/address -> automated stylization + POD",
  "primary_channel": "Etsy + own site",
  "status": "paused",
  "source_batch": "batch2",
  "confidence_grade": "B",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Personalized GPX/Strava race-route poster engine
```json
{
  "id": "f8fe34a4-2435-4e15-828c-14c168622289",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "45a39d22-f8f2-49ed-b2ca-592997caf8df",
  "niche_key": "B2-16",
  "name": "Personalized GPX/Strava race-route poster engine",
  "plain_ru_description": "Персонализированный постер/принт по GPX/Strava маршруту, времени, bib и дате.",
  "buyer": "runners/cyclists",
  "purchase_trigger": "завершение гонки / достижение / подарок",
  "differentiation_hypothesis": "structured data -> deterministic rendering + premium variants",
  "primary_channel": "Etsy + own site",
  "status": "rejected",
  "source_batch": "batch2",
  "confidence_grade": "B",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [
    "Owner rejected the core value proposition: decorative GPX poster is not a meaningful enough business opportunity to justify finalist status.",
    "Current market already contains close substitutes with GPX/Strava/elevation/self-serve features.",
    "Low repeat/LTV and weak functional value make automation insufficient as a business moat."
  ],
  "feedback_state": {
    "reason": "automation bias / insufficient customer-value gate",
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore_v2",
    "previous_role": "incorrectly treated as niche/finalist",
    "required_architecture": "customer-owned GPX upload; no Strava API dependency; OSM attribution",
    "ontology_reset_20260924": true,
    "owner_feedback_20260924": "Rejected as a weak/low-value business concept despite technical feasibility.",
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false,
    "v2_finalist_result_invalidated": true
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Personalized road-trip / destination activity books
```json
{
  "id": "5667b708-151e-44bb-950d-772cb31d6472",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "45a39d22-f8f2-49ed-b2ca-592997caf8df",
  "niche_key": "N01",
  "name": "Personalized road-trip / destination activity books",
  "plain_ru_description": "Персонализированная детская activity-книга под конкретную поездку/место назначения.",
  "buyer": "родители/семьи",
  "purchase_trigger": "поездка / отпуск / перелёт",
  "differentiation_hypothesis": "имя + destination + маршрут/местные элементы",
  "primary_channel": "Etsy + own site",
  "status": "paused",
  "source_batch": "batch1",
  "confidence_grade": "B",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Realtor open-house branded kids kits
```json
{
  "id": "46ad5c25-523b-4afc-943b-7f57685b91d2",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "8fdc0e98-43e9-436e-89da-74a709809644",
  "niche_key": "N07",
  "name": "Realtor open-house branded kids kits",
  "plain_ru_description": "Цифровые детские наборы для open house с брендингом агента и локальными/штатными вариантами.",
  "buyer": "риелторы/брокеры",
  "purchase_trigger": "open house / client event / lead-gen",
  "differentiation_hypothesis": "state/local editions + agent branding + self-serve delivery",
  "primary_channel": "Etsy + own site",
  "status": "paused",
  "source_batch": "batch1",
  "confidence_grade": "B",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Pet-photo coloring/adventure books
```json
{
  "id": "eea3c526-ed25-41fc-9e26-5e544bbe053c",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "45a39d22-f8f2-49ed-b2ca-592997caf8df",
  "niche_key": "N05",
  "name": "Pet-photo coloring/adventure books",
  "plain_ru_description": "Фото питомца превращается в персонализированную раскраску/приключение.",
  "buyer": "владельцы питомцев / gift buyers",
  "purchase_trigger": "подарок / память / развлечение",
  "differentiation_hypothesis": "сюжет/тема + фото, а не просто line-art",
  "primary_channel": "Etsy + own site",
  "status": "paused",
  "source_batch": "batch1",
  "confidence_grade": "B",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Bilingual personalized child books
```json
{
  "id": "c98df6c8-6958-4103-bb2f-bfcd92bda56c",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "45a39d22-f8f2-49ed-b2ca-592997caf8df",
  "niche_key": "N03",
  "name": "Bilingual personalized child books",
  "plain_ru_description": "Двуязычная персонализированная детская книга/активити.",
  "buyer": "двуязычные семьи",
  "purchase_trigger": "языковое развитие + подарок",
  "differentiation_hypothesis": "language pair + name/theme personalization",
  "primary_channel": "Etsy + own site",
  "status": "paused",
  "source_batch": "batch1",
  "confidence_grade": "B",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Mobile-detailing quote and true-margin toolkit
```json
{
  "id": "e7ecd0ed-f5fb-4247-90ad-c81468618726",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "8fdc0e98-43e9-436e-89da-74a709809644",
  "niche_key": "B2-22",
  "name": "Mobile-detailing quote and true-margin toolkit",
  "plain_ru_description": "Калькулятор сметы/маржи и рабочий набор для mobile detailing.",
  "buyer": "mobile detailers",
  "purchase_trigger": "быстро дать цену и не потерять маржу",
  "differentiation_hypothesis": "true-margin workflow + quote output",
  "primary_channel": "Etsy + own site",
  "status": "paused",
  "source_batch": "batch2",
  "confidence_grade": "B",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Equipment-specific maintenance log series
```json
{
  "id": "2649460f-7033-4ed7-83c0-5e5de8cba066",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "f2483590-3e7f-4413-a78f-8ecfa3efcdc0",
  "niche_key": "B2-09",
  "name": "Equipment-specific maintenance log series",
  "plain_ru_description": "Серия журналов обслуживания по типам техники: skid steer/excavator/loader и др.",
  "buyer": "owner-operators/small fleets",
  "purchase_trigger": "service interval / asset history",
  "differentiation_hypothesis": "machine-specific digital + physical variants",
  "primary_channel": "own site + Amazon selectively",
  "status": "paused",
  "source_batch": "batch2",
  "confidence_grade": "C",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Screen-free family travel kit
```json
{
  "id": "801049fa-771f-4c3d-b373-fd2b140f77b3",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "63ee8f47-8345-4506-9293-d9c8014a06c1",
  "niche_key": "B2-26",
  "name": "Screen-free family travel kit",
  "plain_ru_description": "Наш персонализированный activity-продукт плюс безскладские аксессуары поставщиков.",
  "buyer": "traveling families",
  "purchase_trigger": "trip prep / screen-free travel",
  "differentiation_hypothesis": "owned IP anchor + curated supplier cross-sell",
  "primary_channel": "own site",
  "status": "paused",
  "source_batch": "batch2",
  "confidence_grade": "C",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Restaurant/hospitality branded activity packs
```json
{
  "id": "ef24e875-5cb1-4a5a-9fd8-32b8491ba349",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "8fdc0e98-43e9-436e-89da-74a709809644",
  "niche_key": "N09",
  "name": "Restaurant/hospitality branded activity packs",
  "plain_ru_description": "Брендированные детские activity-наборы для ресторанов/гостиниц.",
  "buyer": "restaurants/hospitality",
  "purchase_trigger": "семейный guest experience",
  "differentiation_hypothesis": "white-label branded pack + repeat replenishment path",
  "primary_channel": "own site",
  "status": "paused",
  "source_batch": "batch1",
  "confidence_grade": "C",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Small-carrier billing packet, POD and invoice operations
```json
{
  "id": "3f8f5d40-23c5-4a61-b922-1caabeaeafd9",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "FC2-01",
  "name": "Small-carrier billing packet, POD and invoice operations",
  "plain_ru_description": "Малые carriers и owner-operators, которым после доставки нужно быстро собрать POD/BOL/другие документы, подготовить корректный invoice/factoring packet и поддерживать понятный статус оплаты без превращения сервиса в лицензируемое debt collection.",
  "buyer": "Owner-operators and small fleets, initially 1–10 trucks, reachable through the existing owner-confirmed trucking network.",
  "purchase_trigger": "Delivered loads create a repetitive post-dispatch billing job: missing POD/BOL or other documents delay invoice submission/factoring and create payment-status follow-up work.",
  "differentiation_hypothesis": "Do not compete as generic trucking software. Initial thesis is a bounded human billing desk sold through the owned warm trucking channel; collection activity is excluded or limited to creditor-name notifications within applicable law.",
  "primary_channel": "Existing owner-confirmed trucking network first; referrals second; no paid lead assumption.",
  "status": "rejected",
  "source_batch": "fast_cash_scanner_20261003_v1",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "actual documents/loads per account per month",
    "minutes per billing packet",
    "factoring/TMS workflow variance",
    "client willingness to pay for billing-only scope",
    "Illinois collection-agency boundary for any overdue follow-up beyond creditor-name notifications",
    "retention/churn"
  ],
  "kill_conditions": [
    "Reject if warm-network buyers will not pay enough to support measured packet labor.",
    "Reject if typical work exceeds viable contribution at observed $149-$199/month price anchors.",
    "Do not perform licensed debt-collection activity without required licensing; keep initial scope to billing/document workflow and lawful creditor-name notices.",
    "Reject if actual recurring delivery exceeds 5 owner hours/account/month at ~$199 realized price.",
    "Reject if buyers require unlimited/high-volume billing at flat pricing below viable contribution.",
    "Reject or re-scope if value depends on licensed debt-collection activity rather than billing/document administration."
  ],
  "feedback_state": {
    "edge_status": "owned_trucking_network_evidenced",
    "corrected_at": "2026-10-09T05:02:31.243543+00:00",
    "planning_offer": "$199/month per active truck, workload-bounded",
    "validation_gate": "actual loads/packet minutes + warm-channel paid willingness",
    "user_fit_applied": false,
    "v6_global_status": "rejected_hard_gate",
    "correction_reason": "Prior global score used retracted/current-user-specific trucking-network assumptions. Independent entrant edge is not evidenced.",
    "deep_screen_ready": false,
    "fast_cash_scanner": "PROMOTED_DEEP_SCREEN",
    "collections_boundary": "no independent debt collection",
    "global_scoring_version": "reveng_v6_independent",
    "user_specific_edge_removed": true
  },
  "created_at": "2026-10-03 20:37:38.136737+00",
  "updated_at": "2026-10-09 05:02:31.243543+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Occupation-specific workplace English modules
```json
{
  "id": "1d30033e-6774-4e23-835c-f39c5c3c6872",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": "33f19f48-fe61-4c6f-bce4-190f21ad2241",
  "niche_key": "B2-03",
  "name": "Occupation-specific workplace English modules",
  "plain_ru_description": "Модули workplace English по конкретным профессиям: warehouse/trucking/construction/hospitality.",
  "buyer": "adult ESL/workforce programs",
  "purchase_trigger": "onboarding/job communication",
  "differentiation_hypothesis": "occupation-specific + bilingual variants",
  "primary_channel": "TPT + own site",
  "status": "paused",
  "source_batch": "batch2",
  "confidence_grade": "C",
  "current_adjusted_score": null,
  "unknowns": [],
  "kill_conditions": [],
  "feedback_state": {
    "correct_role": "offer/product hypothesis requiring a parent niche before any future use",
    "score_origin": "reveng_v2_evidence_complete_rescore",
    "previous_role": "incorrectly treated as niche/finalist",
    "ontology_reset_20260924": true,
    "evidence_complete_rescore_at": "2026-09-24T21:50:00Z",
    "full_component_vector_pending": false
  },
  "created_at": "2026-09-24 19:41:32.069967+00",
  "updated_at": "2026-09-24 20:40:00.419217+00",
  "analysis_level": "offer",
  "parent_niche_id": null
}
```

### Owner-operator truck repair estimate/invoice audit and savings recovery
```json
{
  "id": "450bdfbf-7555-4542-afbf-9543597fd760",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "FC2-04",
  "name": "Owner-operator truck repair estimate/invoice audit and savings recovery",
  "plain_ru_description": "Owner-operators и small fleets загружают repair estimate/invoice; сервис проверяет labor, parts, duplicate/extra charges и возможную warranty coverage, затем выдаёт dispute/negotiation packet или помогает оспорить сумму. Оплата — фиксированная или contingency от подтверждённой экономии.",
  "buyer": "Owner-operators and small fleets that outsource truck repairs and are reachable through the owned trucking network.",
  "purchase_trigger": "Large repair estimate arrives, owner suspects overbilling/warranty miss, or final invoice differs from approved scope.",
  "differentiation_hypothesis": "Use owned trucking distribution plus domain knowledge for qualification; monetize only when measurable savings are found or via bounded fixed-fee review. Do not claim unique repair expertise until audit accuracy is evidenced.",
  "primary_channel": "Existing owner-confirmed trucking network; conditional future support from repair/service-center footprint.",
  "status": "rejected",
  "source_batch": "fast_cash_scanner_20261003_batch2",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "actual percentage of invoices with recoverable/avoidable overcharge",
    "time per estimate/invoice review",
    "access to labor guides/rate cards/warranty history",
    "shop negotiation success rate",
    "whether fixed-fee or contingency converts better",
    "liability if a challenged repair is safety-critical"
  ],
  "kill_conditions": [
    "Reject if accurate audits require expensive proprietary data/tools that destroy economics.",
    "Reject if average audit/negotiation time is too high relative to realized savings fee.",
    "Do not give mechanical safety guarantees or direct repair instructions beyond evidence-backed cost/document review.",
    "Reject if owner network does not generate enough recurring repair-audit volume."
  ],
  "feedback_state": {
    "tooling": "Mitchell 1 TruckLabor Plus $99/month",
    "edge_status": "owned_trucking_network_evidenced",
    "corrected_at": "2026-10-09T05:02:31.243543+00:00",
    "supporting_edge": "repair-center access remains conditional",
    "pure_contingency": "not approved until hit-rate measured",
    "user_fit_applied": false,
    "v6_global_status": "rejected_hard_gate",
    "correction_reason": "Prior global score used retracted/current-user-specific trucking-network assumptions. Independent entrant edge is not evidenced.",
    "deep_screen_ready": false,
    "fast_cash_scanner": "PROMOTED_DEEP_SCREEN",
    "preferred_validation": "$49 fixed review and/or hybrid review + success fee",
    "global_scoring_version": "reveng_v6_independent",
    "user_specific_edge_removed": true
  },
  "created_at": "2026-10-04 01:52:42.071738+00",
  "updated_at": "2026-10-09 05:02:31.243543+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Carrier factoring/fuel/dispatch vendor referral desk
```json
{
  "id": "49954272-6103-4e91-b681-c614092d3177",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "FC2-03",
  "name": "Carrier factoring/fuel/dispatch vendor referral desk",
  "plain_ru_description": "Owner-operators и малые fleets, которым нужны factoring, fuel-card, dispatch или authority-сервисы. Модель — не оказывать эти услуги самим, а через прозрачные vendor partner/referral programs направлять carriers к провайдерам и получать payout от vendor.",
  "buyer": "Owner-operators and small fleets reachable through the existing owner-confirmed trucking network.",
  "purchase_trigger": "Carrier needs cash-flow, fuel savings, dispatch or startup services and would otherwise choose a vendor independently.",
  "differentiation_hypothesis": "Use the owned trucking network as the distribution asset and monetize through vendor-paid referral programs with near-zero service labor. Do not advise/procure regulated financing beyond the contractually permitted referral role.",
  "primary_channel": "Existing owner-confirmed trucking network; vendor-run applications; no paid lead assumption.",
  "status": "rejected",
  "source_batch": "fast_cash_scanner_20261003_batch2",
  "confidence_grade": "C",
  "current_adjusted_score": "33.75",
  "unknowns": [
    "Signed vendor contract restrictions, attribution, clawbacks and final commission schedule.",
    "Product-specific demand among the approximately 40 owner-network trucking prospects.",
    "Illinois transaction-specific legal confirmation before compensated factoring referrals.",
    "Conflict/disclosure requirements and reputational risk if a referred vendor underperforms."
  ],
  "kill_conditions": [
    "Reject factoring referral component if compensated referral activity requires licensing/registration not held.",
    "Reject if vendor programs cannot be joined on workable terms or payouts are too delayed/conditional.",
    "Reject if actual network product demand is weak and referral revenue requires paid acquisition.",
    "Do not present as financial adviser, lender, broker or insurance producer unless separately authorized/licensed."
  ],
  "feedback_state": {
    "legal_gate": "CLOSED_CONSERVATIVE_FACToring_CONDITIONAL",
    "edge_status": "owned_trucking_network_evidenced",
    "corrected_at": "2026-10-09T05:02:31.243543+00:00",
    "batch2_decision": "PARK_SCREENED_NOT_DEEP_SCREEN",
    "user_fit_applied": false,
    "v6_global_status": "rejected_hard_gate",
    "correction_reason": "Prior global score used retracted/current-user-specific trucking-network assumptions. Independent entrant edge is not evidenced.",
    "deep_screen_ready": false,
    "fast_cash_scanner": "promoted_from_FC2B-RAW-01",
    "network_demand_gate": "MACRO_PASS_NETWORK_SPECIFIC_FAIL_NO_OUTREACH",
    "global_scoring_version": "reveng_v6_independent",
    "last_internal_review_at": "2026-10-04T09:24:51.714983+00:00",
    "user_specific_edge_removed": true
  },
  "created_at": "2026-10-04 01:52:42.071738+00",
  "updated_at": "2026-10-09 05:02:31.243543+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small-carrier employer-paid CDL driver recruiting
```json
{
  "id": "5531d420-3449-4804-b471-60b9aa6fe6e9",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "FC2-02",
  "name": "Small-carrier employer-paid CDL driver recruiting",
  "plain_ru_description": "Малые carriers, у которых простаивает truck или открыт водительский seat, и которым нужен employer-paid recruiter: найти, отфильтровать и рекомендовать CDL-кандидатов без каких-либо fees с водителя.",
  "buyer": "Small carriers with open Class A CDL seats / idle trucks, initially reachable through the existing owner-confirmed driver/carrier network.",
  "purchase_trigger": "An empty truck or open driver seat destroys revenue; hiring urgency can justify per-placement fees when the recruiter supplies screened candidates.",
  "differentiation_hypothesis": "Use the owned driver/carrier network as the initial two-sided channel. Operate only within the Illinois employer-paid recruiting/consulting exclusion: compensation solely from employer and no direct/indirect fee to candidate.",
  "primary_channel": "Existing owner-confirmed trucking network first; employer-paid only; no candidate fees; paid ads not assumed.",
  "status": "rejected",
  "source_batch": "fast_cash_scanner_20261003_v1",
  "confidence_grade": "C",
  "current_adjusted_score": "33.75",
  "unknowns": [
    "how many current network contacts are actual job-seeking CDL drivers vs employers",
    "carrier fee tolerance at $650+ per hire",
    "candidate screening/background/MVR workflow cost",
    "hire and 30/60-day retention rate",
    "whether any contemplated activity falls outside Illinois recruiting-consulting exclusion",
    "paid-ad dependence"
  ],
  "kill_conditions": [
    "Reject if driver/candidate supply cannot be sourced from owned/referral channels without paid lead spend.",
    "Reject if employers will not pay a placement fee that supports screening and replacement risk.",
    "Never charge drivers/candidates any fee; if business model drifts outside employer-paid consulting/recruiting exclusion, stop until licensing requirements are resolved."
  ],
  "feedback_state": {
    "reason": "owned trucking network exists, but current two-sided recruiting liquidity is not verified",
    "edge_status": "owned_trucking_network_evidenced_but_two_sided_strength_unproven",
    "corrected_at": "2026-10-09T05:02:31.243543+00:00",
    "user_fit_applied": false,
    "v6_global_status": "rejected_hard_gate",
    "correction_reason": "Prior global score used retracted/current-user-specific trucking-network assumptions. Independent entrant edge is not evidenced.",
    "deep_screen_ready": false,
    "fast_cash_scanner": "REJECTED_EDGE_GATE",
    "reentry_conditions": [
      "evidence of current hiring carriers in owned/referral network",
      "evidence of current available/job-seeking CDL drivers or repeatable driver-referral supply",
      "no dependence on paid candidate leads for initial cohort"
    ],
    "global_scoring_version": "reveng_v6_independent",
    "user_specific_edge_removed": true
  },
  "created_at": "2026-10-03 20:37:38.136737+00",
  "updated_at": "2026-10-09 05:02:31.243543+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small government contractors: opportunity discovery, bid/no-bid, and proposal operations
```json
{
  "id": "ef049add-66b2-4878-bc30-b8baf5a5509a",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-01",
  "name": "Small government contractors: opportunity discovery, bid/no-bid, and proposal operations",
  "plain_ru_description": "Малые американские подрядчики, которые хотят продавать федеральным, штатным и местным госзаказчикам, но теряют время и сделки из-за раздробленных порталов, позднего обнаружения RFP и тяжёлого proposal-процесса.",
  "buyer": "US small government contractors, roughly 2–50 employees, especially founder-led service/construction/IT firms without a full capture/proposal department.",
  "purchase_trigger": "Need to find qualified public-sector opportunities early enough, decide bid/no-bid quickly, and submit compliant proposals without consuming founder/SME capacity.",
  "differentiation_hypothesis": "Potential wedge is not another generic bid feed: vertical-specific opportunity intelligence + historical award/incumbent context + reusable evidence/content operations + disciplined bid/no-bid workflow for small teams.",
  "primary_channel": "Direct/SEO/partner channels through APEX ecosystem, industry associations, govcon communities, and search demand.",
  "status": "rejected",
  "source_batch": "reveng_v4_reset_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need quantified SMB count by active bidding frequency",
    "Need win-rate/CAC benchmarks by vertical",
    "Need validate willingness to switch from free SAM/state portals",
    "Need determine which state/local feeds can be obtained legally/reliably"
  ],
  "kill_conditions": [
    "If target buyers will not pay materially above simple alert-tool pricing",
    "If reliable state/local data acquisition is not scalable/legal",
    "If proposal workflow value cannot improve bid selectivity or labor cost enough to justify recurring spend"
  ],
  "feedback_state": {
    "stage": "v4_prescreen",
    "reason": "HigherGov + free SAM already cover the proposed core workflow.",
    "not_a_finalist": true,
    "v5_entrant_edge_kill_20260924": true
  },
  "created_at": "2026-09-24 20:48:47.645222+00",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small Medicare-certified home health agencies: compliance and survey-readiness operations
```json
{
  "id": "9b1c6bd9-b470-494f-849d-41b68916b757",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-07",
  "name": "Small Medicare-certified home health agencies: compliance and survey-readiness operations",
  "plain_ru_description": "Небольшие Medicare-certified home health agencies, которые должны постоянно отслеживать CoP, staff credentials, policies, training, audit evidence и готовность к survey при маленькой административной команде.",
  "buyer": "US Medicare-certified home health agencies, especially small/midsize operators with roughly <=75 staff or a few locations.",
  "purchase_trigger": "Continuous regulatory compliance, staff credential expirations, documentation and survey readiness create recurring owner/compliance-director workload with material reimbursement/licensure risk.",
  "differentiation_hypothesis": "A vertical compliance operating system plus optional managed readiness service can be narrower and more actionable than generic policy libraries or enterprise home-health suites.",
  "primary_channel": "Home-health associations, accreditation consultants, billing/EMR partners, compliance search demand, targeted outbound.",
  "status": "rejected",
  "source_batch": "reveng_v4_reset_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need buyer interviews on current survey-prep spend",
    "Need map exact compliance liability and advisory boundaries",
    "Need compare integrations with common home-health EMRs",
    "Need quantify target agencies by staff/location size"
  ],
  "kill_conditions": [
    "If market is too small for efficient acquisition",
    "If regulations require extensive expert consulting per account",
    "If EMR vendors already bundle sufficient compliance workflow"
  ],
  "feedback_state": {
    "stage": "v4_prescreen",
    "reason": "Ordo/SurveyReady already implement the exact home-health compliance OS wedge.",
    "not_a_finalist": true,
    "v5_entrant_edge_kill_20260924": true
  },
  "created_at": "2026-09-24 20:48:47.645222+00",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small public-works contractors: certified-payroll and prevailing-wage operations
```json
{
  "id": "d36e51b7-1543-497d-87f0-cdaa2bdf37c6",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-12",
  "name": "Small public-works contractors: certified-payroll and prevailing-wage operations",
  "plain_ru_description": "Небольшие contractors/subcontractors на federal/federally assisted public works, которым каждую неделю надо правильно собирать payroll, classifications, wage determinations, fringe benefits и certified reports.",
  "buyer": "US small contractors/subcontractors performing Davis-Bacon or similar prevailing-wage public work, particularly firms without dedicated payroll-compliance staff.",
  "purchase_trigger": "Covered work creates weekly payroll/compliance obligations; classification, fringe and multi-jurisdiction complexity can consume back-office time and create underpayment/audit risk.",
  "differentiation_hypothesis": "A viable wedge must go beyond filling WH-347 because DOL now provides a free generator; value would need to live in payroll imports, multi-project/multi-state rules, fringe logic, subcontractor oversight, anomaly detection and submission evidence.",
  "primary_channel": "Public-works associations, payroll/accounting partners, APEX/public-contracting ecosystem, construction CPAs and search.",
  "status": "rejected",
  "source_batch": "reveng_v4_wave2_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "63.90",
  "unknowns": [
    "Need target count of small contractors actually doing covered work",
    "Need measure multi-state/state-specific complexity beyond federal WH-347",
    "Need validate willingness to pay after DOL free generator",
    "Need assess payroll integration and compliance-liability requirements"
  ],
  "kill_conditions": [
    "If DOL/free payroll-provider tools eliminate most small-contractor pain",
    "If remaining complexity is too state-specific and services-heavy",
    "If low-cost current entrants make customer acquisition uneconomic"
  ],
  "feedback_state": {
    "stage": "v4_prescreen_wave2",
    "not_a_finalist": true,
    "v4_kill_reason_20260924": "Generic certified-payroll software is weakened by DOL free WH-347 generation; no sufficiently strong broader wedge evidenced yet."
  },
  "created_at": "2026-09-24 20:54:26.109857+00",
  "updated_at": "2026-09-24 21:05:06.256699+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small custom/job-shop manufacturers: RFQ quoting and estimating operations
```json
{
  "id": "16a4e673-969e-4a31-864e-810ebcc035f8",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-09",
  "name": "Small custom/job-shop manufacturers: RFQ quoting and estimating operations",
  "plain_ru_description": "Небольшие job shops и contract manufacturers, где RFQ приходит с drawings/CAD, а estimator вручную сводит material, setup/run time, outside processes, margin и исторические аналоги — часто в Excel и tribal knowledge.",
  "buyer": "US small custom manufacturers/job shops, especially CNC, fabrication and mixed-process shops with roughly 5–50 employees and meaningful RFQ volume.",
  "purchase_trigger": "Quote turnaround and accuracy determine whether work is won profitably; estimators spend scarce senior labor pricing jobs that may never convert.",
  "differentiation_hypothesis": "A strong wedge would preserve each shop’s costing logic and historical quote/job knowledge while accelerating RFQ triage and estimator review, rather than pretending geometry can fully replace an estimator.",
  "primary_channel": "Manufacturing associations, ERP/CAM/accounting partners, machine-tool/service ecosystems, search, vertical outbound.",
  "status": "rejected",
  "source_batch": "reveng_v4_wave2_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need segment count for custom/job-shop subset within manufacturing",
    "Need typical RFQ volume and estimator labor cost by shop type",
    "Need actual incumbent ACV and switching friction",
    "Need determine how much quoting accuracy can improve without deep CAM/ERP integration"
  ],
  "kill_conditions": [
    "If quoting remains too shop-specific for repeatable onboarding",
    "If entrenched ERP/CPQ products already cover the 5–50 employee segment at acceptable price",
    "If estimator review remains so heavy that software cannot create strong ROI"
  ],
  "feedback_state": {
    "stage": "v4_prescreen_wave2",
    "reason": "Paperless Parts already implements machine-shop RFQ/estimating with integrations; hypothetical data moat is not evidence.",
    "not_a_finalist": true,
    "v4_redteam_20260924": "Survived current direct-substitute sweep; continue deep screen on onboarding/CAC and exact target segment.",
    "v5_entrant_edge_kill_20260924": true
  },
  "created_at": "2026-09-24 20:54:26.109857+00",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Specialty contractors and suppliers: payment-rights, lien-deadline, waiver and collections operations
```json
{
  "id": "ab66685e-a6d9-4403-8d80-88f3dae16881",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-13",
  "name": "Specialty contractors and suppliers: payment-rights, lien-deadline, waiver and collections operations",
  "plain_ru_description": "Коммерческие subcontractors и material suppliers, которым после выполнения работ нужно не потерять lien rights, правильно собирать/выдавать waivers, держать notice deadlines и дожимать оплату/retainage.",
  "buyer": "US commercial specialty contractors and material suppliers with recurring receivables across multiple projects and enough project volume that lien/notice/waiver tracking no longer fits in spreadsheets.",
  "purchase_trigger": "Payment delays, retainage and paperwork errors can strand working capital; missed preliminary-notice or lien deadlines can destroy leverage that helps secure payment.",
  "differentiation_hypothesis": "A viable wedge is not another waiver generator: it would connect pay-app/AR aging, statutory deadline intelligence, notice/lien workflow, waiver exchange and escalation evidence into one payment-protection operating layer.",
  "primary_channel": "Construction accountants, trade associations, ERP/accounting partners, bonding/insurance ecosystem, construction finance communities and vertical outbound.",
  "status": "rejected",
  "source_batch": "reveng_v4_wave3_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need state-by-state legal/compliance scope and unauthorized-practice-of-law boundaries",
    "Need segment annual receivables/retainage and missed-rights incidence by contractor size",
    "Need quantify current incumbent ACV and partner CAC",
    "Need determine whether payment-rights workflow can be productized without attorney-heavy exceptions"
  ],
  "kill_conditions": [
    "If state-specific legal complexity forces high-cost manual expert review per project",
    "If Levelset/Siteline/GCPay-class incumbents already dominate the target segment with low switching friction",
    "If buyers see lien-rights workflow as occasional legal service rather than recurring operations"
  ],
  "feedback_state": {
    "stage": "v4_prescreen_wave3",
    "not_a_finalist": true,
    "v4_redteam_kill_20260924": "Siteline/Levelset already occupy the proposed integrated payment-rights/AR workflow; no evidenced entry wedge."
  },
  "created_at": "2026-09-24 21:02:09.606686+00",
  "updated_at": "2026-09-24 21:08:22.557586+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Multi-site commercial businesses: utility-bill error recovery and tariff/rate optimization
```json
{
  "id": "6fb1d9ab-bf51-421d-b9f4-345538c5a521",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-14",
  "name": "Multi-site commercial businesses: utility-bill error recovery and tariff/rate optimization",
  "plain_ru_description": "Мультисайтовые commercial/facility operators с заметными electricity/gas/water bills, где ошибки rate class, meters, taxes, tariffs и contract terms могут месяцами создавать переплаты.",
  "buyer": "US commercial and light-industrial organizations spending materially on utilities, especially multi-site portfolios and facilities with complex meters, tariffs, demand charges or tax treatment.",
  "purchase_trigger": "Utility billing errors and misapplied tariffs create direct recoverable leakage; rising utility spend also raises the value of continuous validation and rate optimization.",
  "differentiation_hypothesis": "The opportunity would need to combine contingency recovery with recurring monitoring and multi-site tariff intelligence; a one-time manual audit alone is a service, not a defensible engine.",
  "primary_channel": "Facility-management partners, commercial property/accounting firms, energy consultants/brokers where permitted, multi-site operators and targeted outbound.",
  "status": "rejected",
  "source_batch": "reveng_v4_wave3_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need independent incidence data on commercial billing errors/recoveries",
    "Need state/utility restrictions on representing customers and sharing savings",
    "Need quantify acquisition path to businesses spending >$50k utilities/year",
    "Need separate repeatable software monitoring from bespoke tariff consulting"
  ],
  "kill_conditions": [
    "If recoveries are too episodic to support repeat/LTV",
    "If expert tariff analysis dominates labor and cannot be standardized",
    "If regulated energy-broker/consulting requirements constrain scalable delivery"
  ],
  "feedback_state": {
    "stage": "v4_prescreen_wave3",
    "reason": "TrueMeter/Utility Audit/MeterID already cover the proposed multi-site utility recovery/monitoring wedge.",
    "not_a_finalist": true,
    "v5_entrant_edge_kill_20260924": true
  },
  "created_at": "2026-09-24 21:02:09.606686+00",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Independent specialty medical practices: commercial-payer underpayment and contract-variance recovery
```json
{
  "id": "a64e06fc-c979-4388-80d8-c2563c3b1dcf",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-16",
  "name": "Independent specialty medical practices: commercial-payer underpayment and contract-variance recovery",
  "plain_ru_description": "Independent specialty practices, которые уже получили payment по claim, но могут не видеть систематические short-pay, downcoding, bundling и fee-schedule mismatches, потому что claim закрывается с zero balance.",
  "buyer": "US independent specialty physician practices and small groups with meaningful commercial payer volume and enough claim complexity that manual expected-vs-paid contract reconciliation is impractical.",
  "purchase_trigger": "Underpayments hide inside apparently paid/closed claims; reimbursement pressure is already material, so recovering contractually earned dollars can have direct bottom-line value.",
  "differentiation_hypothesis": "A viable wedge is a recovery operating system for smaller specialty groups: contract-rate modeling, 835 variance detection, prioritized appeals/follow-up and contract-renewal evidence, sold as contingency/hybrid rather than enterprise RCM software.",
  "primary_channel": "RCM/billing-company white-label partnerships, specialty associations, healthcare CPAs/consultants, clearinghouse integrations and direct specialty-practice outreach.",
  "status": "rejected",
  "source_batch": "reveng_v4_wave3_20260924",
  "confidence_grade": "C",
  "current_adjusted_score": "33.75",
  "unknowns": [
    "Need independent estimate of underpayment incidence/recoverable dollars in 2-20 physician specialty practices",
    "Need payer-contract normalization/onboarding effort",
    "Need HIPAA/BAA/security architecture and appeal/legal boundaries",
    "Need compare contingency economics against incumbent RCM vendors and human recovery labor",
    "Need determine which specialties have enough commercial volume/contract complexity"
  ],
  "kill_conditions": [
    "If contract loading/modeling is too bespoke for small-account economics",
    "If appeal/follow-up labor consumes recovery fees",
    "If security/integration requirements create enterprise cost before product-market fit",
    "If established RCM vendors can bundle the function at negligible incremental CAC"
  ],
  "feedback_state": {
    "stage": "v4_prescreen_wave3",
    "reason": "Existing 835 underpayment/recovery platforms plus no independent target leakage proof; no entrant edge.",
    "not_a_finalist": true,
    "v5_entrant_edge_kill_20260924": true
  },
  "created_at": "2026-09-24 21:02:09.606686+00",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Mid-market parcel shippers: carrier invoice audit and refund/spend recovery
```json
{
  "id": "936c5602-d948-4618-9534-e4e30dde57a4",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-15",
  "name": "Mid-market parcel shippers: carrier invoice audit and refund/spend recovery",
  "plain_ru_description": "Ecommerce brands, 3PL и другие shippers с заметным UPS/FedEx/DHL spend, где late-service guarantees, duplicate/incorrect surcharges и contract/rate errors теряются в тысячах invoice lines.",
  "buyer": "US ecommerce brands, 3PLs and other mid-market shippers with enough parcel volume that manual carrier invoice review is uneconomic.",
  "purchase_trigger": "Carrier billing/service errors and missed guarantees create direct recoverable dollars, while surcharge/rate analytics can affect future shipping cost.",
  "differentiation_hypothesis": "The base refund audit is already commoditized; a credible wedge would have to extend into contract optimization, multi-carrier spend intelligence, loss/damage claims or embedded 3PL workflow.",
  "primary_channel": "3PL/accounting/fulfillment partners, ecommerce agencies, carrier consultants, Shopify ecosystem and direct high-volume shipper outreach.",
  "status": "rejected",
  "source_batch": "reveng_v4_wave3_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "65.88",
  "unknowns": [
    "Need count of addressable shippers by annual parcel spend",
    "Need validate carrier guarantee/refund policy stability and API/data access",
    "Need CAC/channel economics in a mature contingency market",
    "Need identify non-commodity layer strong enough to create retention and defensibility"
  ],
  "kill_conditions": [
    "If buyers view providers as interchangeable contingency auditors",
    "If carriers continue narrowing service guarantees/refund eligibility",
    "If incremental analytics cannot support pricing beyond commodity gainshare"
  ],
  "feedback_state": {
    "stage": "v4_prescreen_wave3",
    "not_a_finalist": true,
    "v4_kill_reason_20260924": "Core parcel refund audit is explicitly commoditized by current market participants; no defensible adjacent wedge evidenced yet."
  },
  "created_at": "2026-09-24 21:02:09.606686+00",
  "updated_at": "2026-09-24 21:05:06.256699+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Specialty contractors: change-order and T&M revenue-capture operations
```json
{
  "id": "6db874b6-b4d1-4090-8153-649d71c9bb63",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-10",
  "name": "Specialty contractors: change-order and T&M revenue-capture operations",
  "plain_ru_description": "Коммерческие subcontractors/specialty trades, которые выполняют extra work до формального change order и теряют cash flow/margin из-за бумажных T&M tickets, слабой документации, поздних approvals и разрыва field-to-office.",
  "buyer": "US specialty contractors/subcontractors, especially 5–50 employee commercial electrical, mechanical, plumbing, concrete, civil and similar trades.",
  "purchase_trigger": "Extra work must be documented, priced, approved and billed; weak field evidence or late processing turns performed work into disputed/uncollected revenue.",
  "differentiation_hypothesis": "The opportunity is a revenue-capture operating layer, not a generic change-order form: field proof, rate sheets, scope linkage, approval trail, billing handoff and aging/recovery visibility for subs.",
  "primary_channel": "Trade associations, construction accountants, insurance/bonding partners, field-service ecosystems, GC/sub networks, SEO and vertical outbound.",
  "status": "rejected",
  "source_batch": "reveng_v4_wave2_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need quantify average annual at-risk change-order dollars by target contractor size",
    "Need determine incumbent penetration and integration expectations",
    "Need measure field adoption/support burden",
    "Need separate actual recovered-revenue effect from vendor marketing claims"
  ],
  "kill_conditions": [
    "If simple $49-$150/month tools fully solve the pain with low switching friction",
    "If GC-controlled approval process limits vendor ability to affect collections",
    "If field adoption requires enterprise implementation that breaks two-person launch feasibility"
  ],
  "feedback_state": {
    "stage": "v4_prescreen_wave2",
    "not_a_finalist": true,
    "v4_redteam_kill_20260924": "Direct current substitutes already implement the proposed T&M/change-order revenue workflow; Clearstory even has a free entry tier and network effects."
  },
  "created_at": "2026-09-24 20:54:26.109857+00",
  "updated_at": "2026-09-24 21:08:22.557586+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small for-hire fleets: detention and accessorial revenue recovery operations
```json
{
  "id": "5791b304-7281-4152-9529-b7123ae077fd",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-11",
  "name": "Small for-hire fleets: detention and accessorial revenue recovery operations",
  "plain_ru_description": "Малые carrier fleets и owner-operators, которые зарабатывают detention/TONU/layover/lumper/accessorial charges, но не документируют или не дожимают небольшие claims из-за разных broker rules, доказательств и follow-up.",
  "buyer": "US owner-operators and small for-hire truckload fleets, especially 1–20 trucks using brokers/spot freight and lacking a dedicated billing/recovery team.",
  "purchase_trigger": "Waiting and other accessorial events create earned but frequently uncollected revenue; each claim is small enough that manual chasing often loses economically.",
  "differentiation_hypothesis": "A wedge could combine ELD/GPS proof capture, broker-specific claim rules, same-day submission, follow-up workflow and optional contingency recovery rather than merely generating an invoice.",
  "primary_channel": "ELD/integration partners, factoring companies, dispatch services, insurance/service ecosystems, carrier communities and direct fleet outreach.",
  "status": "rejected",
  "source_batch": "reveng_v4_wave2_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need validate what share of unpaid detention is contractually recoverable",
    "Need broker-by-broker submission rule data and legal collection boundaries",
    "Need quantify recoverable dollars for 1–20 truck fleets specifically",
    "Need model ELD integration coverage and contingency-service labor"
  ],
  "kill_conditions": [
    "If most unpaid detention is not legally/contractually collectible",
    "If broker/customer friction causes unacceptable carrier churn",
    "If collection operations require too much human follow-up for the account value",
    "If ELD/invoice tools already reduce the gap enough that willingness to pay is low"
  ],
  "feedback_state": {
    "stage": "v4_prescreen_wave2",
    "not_a_finalist": true,
    "v4_redteam_kill_20260924": "Multiple 2026 direct substitutes already implement rate-con parsing, detention evidence, claim generation and managed recovery for small fleets at low price/contingency."
  },
  "created_at": "2026-09-24 20:54:26.109857+00",
  "updated_at": "2026-09-24 21:08:22.557586+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small fleets: DOT/safety compliance operations for 2-25 vehicles
```json
{
  "id": "334af3f0-184f-4d90-832b-b9ada09ea76a",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-02",
  "name": "Small fleets: DOT/safety compliance operations for 2–25 vehicles",
  "plain_ru_description": "Малые автопарки и перевозчики, где владелец или маленький офис вручную ведёт DQ-файлы, medical cards, MVR, страховки, инспекции, renewals и готовность к аудиту.",
  "buyer": "US motor carriers and DOT-regulated service fleets with about 2–25 vehicles and no dedicated compliance department.",
  "purchase_trigger": "Recurring expirations, driver qualification records, audit readiness, insurance/compliance requirements and the cost of missed deadlines or out-of-service events.",
  "differentiation_hypothesis": "A workflow/managed-ops layer focused on the smallest fleets can combine deadline intelligence, document completeness, exception handling and optional human remediation instead of selling a generic fleet-management suite.",
  "primary_channel": "Direct industry outreach, insurance/broker partnerships, repair/truck-service ecosystems, SEO, owner-operator communities.",
  "status": "rejected",
  "source_batch": "reveng_v4_reset_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need exact count of active 2–25 vehicle target fleets",
    "Need churn and willingness-to-pay by 2–6 vs 7–25 fleets",
    "Need map legal boundary between software reminders and regulated compliance advice",
    "Need quantify support burden for managed remediation"
  ],
  "kill_conditions": [
    "If most 2–25 fleets solve the problem adequately with spreadsheets/free reminders",
    "If regulatory support burden makes <$200 MRR accounts uneconomic",
    "If established compliance vendors already dominate acquisition at sustainable CAC"
  ],
  "feedback_state": {
    "stage": "v4_prescreen",
    "reason": "Current direct competitors already implement the proposed core wedge for the same buyer; no unique distribution/data/workflow advantage evidenced.",
    "not_a_finalist": true,
    "v4_direct_substitute_kill_20260924": true
  },
  "created_at": "2026-09-24 20:48:47.645222+00",
  "updated_at": "2026-09-24 21:09:34.871372+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Independent and small healthcare practices: payer credentialing and enrollment operations
```json
{
  "id": "c140835e-90a0-48c5-97eb-b2e0c96e6e9f",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-05",
  "name": "Independent and small healthcare practices: payer credentialing and enrollment operations",
  "plain_ru_description": "Независимые врачи, терапевты и небольшие клиники, которым нужно быстро подключать провайдеров к payer networks и постоянно поддерживать CAQH, recredentialing, licenses и enrollment без отдельного credentialing department.",
  "buyer": "US solo and small-group healthcare practices adding providers, opening locations or expanding payer panels.",
  "purchase_trigger": "A provider cannot reliably bill in-network until payer credentialing/enrollment closes; applications, CAQH upkeep, revalidation and payer follow-up are recurring administrative work tied directly to revenue.",
  "differentiation_hypothesis": "A hybrid software + specialist model could compete on transparent status, fast exception handling, reusable provider data, recurring maintenance and white-label distribution through billing/RCM firms.",
  "primary_channel": "Medical billing/RCM partnerships, specialty associations, practice-launch search demand, accountant/legal/startup-practice partners.",
  "status": "rejected",
  "source_batch": "reveng_v4_reset_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need validate cycle-time improvement we can realistically influence",
    "Need specialty/state segmentation for payer complexity",
    "Need HIPAA/security/legal review for stored provider data",
    "Need quantify acquisition cost through RCM/billing partners"
  ],
  "kill_conditions": [
    "If payer-specific manual follow-up prevents attractive automation leverage",
    "If trust/security requirements force enterprise-grade costs too early",
    "If established credentialing services win solely on relationships and labor scale"
  ],
  "feedback_state": {
    "stage": "v4_prescreen",
    "reason": "Current direct competitors already implement the proposed core wedge for the same buyer; no unique distribution/data/workflow advantage evidenced.",
    "not_a_finalist": true,
    "v4_direct_substitute_kill_20260924": true
  },
  "created_at": "2026-09-24 20:48:47.645222+00",
  "updated_at": "2026-09-24 21:09:34.871372+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Independent dental practices: insurance benefit-verification operations
```json
{
  "id": "b535be1b-4255-4ea3-be1f-8cd3932fb53b",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-06",
  "name": "Independent dental practices: insurance benefit-verification operations",
  "plain_ru_description": "Независимые стоматологии, где front desk ежедневно тратит время на eligibility и detailed benefits через разные страховые порталы/телефоны, а ошибки влияют на patient estimates, collections и загрузку команды.",
  "buyer": "US independent dental practices and small dental groups with meaningful insurance volume but without centralized enterprise revenue-cycle operations.",
  "purchase_trigger": "Before visits and treatment plans, staff repeatedly verify eligibility and benefit details across inconsistent payer portals; the work is high-frequency, labor-intensive and directly affects collections and patient experience.",
  "differentiation_hypothesis": "Potential wedge is reliable hybrid automation/human QA for full dental benefit breakdowns, integrated into practice workflow and priced for independent offices rather than enterprise DSOs.",
  "primary_channel": "Dental associations/communities, dental consultants, practice-management integrations, RCM partners, SEO.",
  "status": "rejected",
  "source_batch": "reveng_v4_reset_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need payer-by-payer automation coverage and failure rates",
    "Need HIPAA/data security scope",
    "Need determine labor economics for exception handling",
    "Need measure willingness to switch from existing outsourced verification vendors"
  ],
  "kill_conditions": [
    "If payer portals block reliable automation at scale",
    "If human verification cost consumes most gross margin",
    "If incumbents can match pricing and integrations with no defensible wedge"
  ],
  "feedback_state": {
    "stage": "v4_prescreen",
    "reason": "Current direct competitors already implement the proposed core wedge for the same buyer; no unique distribution/data/workflow advantage evidenced.",
    "not_a_finalist": true,
    "v4_direct_substitute_kill_20260924": true
  },
  "created_at": "2026-09-24 20:48:47.645222+00",
  "updated_at": "2026-09-24 21:09:34.871372+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Growing multistate ecommerce sellers: sales-tax compliance operations
```json
{
  "id": "0f298acf-316d-43ac-a7b1-6dbd89d3fc1a",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-08",
  "name": "Growing multistate ecommerce sellers: sales-tax compliance operations",
  "plain_ru_description": "Растущие ecommerce-компании, которые уже пересекли nexus в нескольких штатах и теперь должны отслеживать thresholds, registrations, filings, deadlines и exceptions, но enterprise tax software для них дорого и сложно.",
  "buyer": "US ecommerce merchants with economic/physical nexus in several states, typically beyond DIY spreadsheets but below enterprise tax-department scale.",
  "purchase_trigger": "Multi-state nexus, registration, filing cadence and changing state rules create recurring compliance work; mistakes create penalties while existing platforms can become expensive as states/transactions grow.",
  "differentiation_hypothesis": "Potential wedge would be service-first clarity and exception handling for a sharply defined merchant profile, possibly distributed through ecommerce accountants/CPAs rather than another generic tax calculator.",
  "primary_channel": "Ecommerce CPA/bookkeeper partnerships, Shopify ecosystem, tax communities, SEO, agency partners.",
  "status": "rejected",
  "source_batch": "reveng_v4_reset_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need define precise merchant revenue/state-count band with unmet need",
    "Need tax-practice/legal boundary and filing licenses/authorization requirements",
    "Need model filing labor and state fees",
    "Need determine whether partner distribution can beat incumbent CAC"
  ],
  "kill_conditions": [
    "If compliance liability and human filing work destroy margins",
    "If incumbents have already saturated the affordable SMB tier",
    "If differentiation cannot exceed price/support claims"
  ],
  "feedback_state": {
    "stage": "v4_prescreen",
    "reason": "Current direct competitors already implement the proposed core wedge for the same buyer; no unique distribution/data/workflow advantage evidenced.",
    "not_a_finalist": true,
    "v4_direct_substitute_kill_20260924": true
  },
  "created_at": "2026-09-24 20:48:47.645222+00",
  "updated_at": "2026-09-24 21:09:34.871372+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small and midsize GCs/property operators: subcontractor and vendor compliance operations
```json
{
  "id": "6446431d-ac46-41d7-9601-8ef19ae8f5e5",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-03",
  "name": "Small and midsize GCs/property operators: subcontractor and vendor compliance operations",
  "plain_ru_description": "Генподрядчики, property/facility managers и другие операторы, которым приходится постоянно собирать и проверять COI, лицензии, W-9, endorsements и сроки действия у десятков или сотен подрядчиков.",
  "buyer": "US general contractors, property managers and facility operators managing roughly 25–500 active subcontractors/vendors without an enterprise compliance team.",
  "purchase_trigger": "Vendor onboarding and continuous proof-of-insurance/license/tax-document compliance; missing or expired documents create audit, insurance and project risk.",
  "differentiation_hypothesis": "Opportunity would need a small/mid-market wedge: fast vendor self-service collection, industry-specific compliance rules, managed exception review, and transparent pricing below enterprise minimums.",
  "primary_channel": "Construction/property associations, insurance brokers, accounting/bookkeeping partners, SEO, vertical outbound.",
  "status": "rejected",
  "source_batch": "reveng_v4_reset_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need segment-specific willingness to pay by vendor count",
    "Need measure vendor response/chase workload",
    "Need compare liability of automated COI interpretation vs human review",
    "Need identify underserved verticals rather than generic COI market"
  ],
  "kill_conditions": [
    "If generic COI tools have already commoditized the small-business segment",
    "If accurate endorsement/compliance review requires expensive licensed human labor",
    "If no vertical wedge yields materially lower CAC or higher retention"
  ],
  "feedback_state": {
    "stage": "v4_prescreen",
    "reason": "Current COI platforms already cover the proposed workflow; no structural edge.",
    "not_a_finalist": true,
    "v5_entrant_edge_kill_20260924": true
  },
  "created_at": "2026-09-24 20:48:47.645222+00",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Grant-funded nonprofits: post-award restricted-fund and reporting operations
```json
{
  "id": "e9576b7c-a5bd-495a-8926-74dd314bb7e3",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V4-04",
  "name": "Grant-funded nonprofits: post-award restricted-fund and reporting operations",
  "plain_ru_description": "Некоммерческие организации с несколькими грантами, где finance и program teams вручную сводят restricted funds, budget-vs-actual, дедлайны, документы и отчёты для funders.",
  "buyer": "US nonprofits managing multiple restricted grants/government contracts, especially organizations too complex for spreadsheets but too small for enterprise grant-management systems.",
  "purchase_trigger": "After award, staff must track restricted spending, reporting deadlines, supporting documentation, budget changes and cross-team handoffs; failures risk audit findings, clawbacks or renewal problems.",
  "differentiation_hypothesis": "A focused post-award operations layer can differentiate from grant-discovery tools by integrating accounting data, funder obligations, spenddown and evidence packets without forcing a full ERP replacement.",
  "primary_channel": "Nonprofit finance/grants communities, CPA/bookkeeper partners, nonprofit associations, QuickBooks ecosystem, SEO.",
  "status": "rejected",
  "source_batch": "reveng_v4_reset_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Need size target by annual grant volume and active-grant count",
    "Need test integration complexity with QuickBooks and common nonprofit accounting stacks",
    "Need quantify compliance/reporting hours saved",
    "Need determine whether $300–$1000 MRR buyer segment is reachable without long enterprise sales"
  ],
  "kill_conditions": [
    "If buyers primarily want grant discovery rather than post-award workflow",
    "If accounting-system integration makes onboarding/services too heavy",
    "If nonprofit budgets cannot support sustainable CAC for the target ACV"
  ],
  "feedback_state": {
    "stage": "v4_prescreen",
    "reason": "Instrumentl/Actually already cover post-award finance/spenddown workflow.",
    "not_a_finalist": true,
    "v5_entrant_edge_kill_20260924": true
  },
  "created_at": "2026-09-24 20:48:47.645222+00",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Chicago-area small trucking operators: commercial insurance placement and renewal
```json
{
  "id": "0eaecc25-13a0-428d-957e-b06d604d7bd9",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V5-01",
  "name": "Chicago-area small trucking operators: commercial insurance placement and renewal",
  "plain_ru_description": "Малые trucking companies и owner-operators в Chicagoland, которым нужно покупать/перестраивать commercial auto, cargo, physical damage и связанные покрытия при новом authority, покупке/замене truck, renewal, росте fleet или проблемах с carrier.",
  "buyer": "Chicago-area owner-operators and small trucking fleets, initially roughly 1–10 power units, especially businesses interacting with a trusted repair/service ecosystem.",
  "purchase_trigger": "New authority, annual renewal, adding/replacing equipment, premium shock, cancellation/non-renewal, claim-history change, new lanes/cargo, or need for required insurance filings.",
  "differentiation_hypothesis": "The initial hypothesis is NOT “better trucking insurance.” The only qualifying entrant edge is embedded access to qualified trucking buyers through an existing repair/service environment at natural purchase triggers; market access and service quality must still be competitive.",
  "primary_channel": "Embedded repair/service distribution first; referrals and renewal book second; paid lead generation is not assumed.",
  "status": "rejected",
  "source_batch": "reveng_v5_edge_first_wave1_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Exact weekly qualified traffic and current-policy renewal calendar are unknown.",
    "Bind rate from repair/service referrals is unknown.",
    "Carrier/MGA access for new trucking risks and new ventures must be verified contractually.",
    "Net commission after aggregator/MGA splits and service workload must be modeled.",
    "Illinois producer/entity licensing and any agency registration requirements must be completed before selling.",
    "Retention and remarketing workload for small trucking accounts is unknown."
  ],
  "kill_conditions": [
    "If embedded channel produces fewer than 5 qualified trucking insurance conversations per month after launch.",
    "If market-access partners cannot place the dominant local risk profiles competitively.",
    "If net first-year commission after splits/service cost is too low to support the sales and servicing workload.",
    "If annual retention is weak enough that renewal economics do not compound.",
    "If repair-shop access cannot be formalized or becomes non-exclusive/low-quality traffic."
  ],
  "feedback_state": {
    "stage": "v5_edge_first_candidate",
    "reason": "Mandatory producer licensing blocks immediate lawful revenue validation; exact trucking carrier commission remains contract-specific and unverified.",
    "corrected_at": "2026-10-09T05:02:31.243543+00:00",
    "fast_cash_lane": "paused_until_license",
    "not_a_finalist": true,
    "user_fit_applied": false,
    "v6_global_status": "rejected_hard_gate",
    "correction_reason": "Prior global score used retracted/current-user-specific trucking-network assumptions. Independent entrant edge is not evidenced.",
    "reopen_conditions": [
      "required Illinois producer license obtained",
      "at least one trucking market-access path confirmed for target classes",
      "actual new/renewal carrier commission schedule received",
      "E&O/service cost known"
    ],
    "global_scoring_version": "reveng_v6_independent",
    "user_specific_edge_removed": true
  },
  "created_at": "2026-09-24 21:29:45.207463+00",
  "updated_at": "2026-10-09 05:02:31.243543+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small trucking operators: repair, equipment and working-capital access
```json
{
  "id": "88328b74-e704-4810-8234-d5f5123d14ac",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V5-02",
  "name": "Small trucking operators: repair, equipment and working-capital access",
  "plain_ru_description": "Малые trucking companies и owner-operators, которым нужен быстрый доступ к капиталу при major repair, покупке оборудования, сезонном cash-flow gap или переходе между factoring/working-capital providers.",
  "buyer": "Chicago-area and broader US owner-operators/small fleets, initially 1–10 trucks, with real repair/equipment/cash-flow needs and limited internal treasury capacity.",
  "purchase_trigger": "Major breakdown/repair invoice, equipment purchase/replacement, slow broker/shipper payment cycle, insurance/fuel/payroll squeeze, or need to replace/change factoring/working-capital provider.",
  "differentiation_hypothesis": "The qualifying entrant edge is existing access to a small-carrier/driver network at moments when financing/referral needs can surface. The thesis is not to become a lender; it is to monetize qualified distribution into vetted third-party capital/protection programs.",
  "primary_channel": "Existing owner-confirmed trucking network; repair-center embedded placement only if separately revalidated.",
  "status": "rejected",
  "source_batch": "reveng_v5_edge_first_wave1_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "42.00",
  "unknowns": [
    "Qualified finance/capital need frequency across the existing network is unknown.",
    "Average payout and residual economics vary materially by partner.",
    "Referral/finance compliance and disclosure requirements must be checked by product/state.",
    "Partner underwriting/approval quality and customer complaints can damage the core relationship.",
    "Repair-center physical access remains conditional, not gate evidence."
  ],
  "kill_conditions": [
    "If fewer than 10% of qualified network contacts create a monetizable capital/referral event over 12 months.",
    "If realized revenue per qualified lead is too small to justify relationship risk and admin.",
    "If partner outcomes/complaints damage trust with the trucking network.",
    "If no recurring/residual partner economics can be secured and the model remains low-value one-off referral income."
  ],
  "feedback_state": {
    "stage": "v5_edge_first_deep_screen",
    "reason": "Capital-access need is real, but with the currently evidenced distribution asset the obtainable referral economics support an ancillary cross-sell layer, not a standalone niche business.",
    "not_a_finalist": true,
    "v5_redteam_rejected": true
  },
  "created_at": "2026-09-24 21:39:10.550768+00",
  "updated_at": "2026-09-24 21:46:49.742777+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

### Small-carrier managed DOT compliance and safety administration
```json
{
  "id": "f5ebd322-a409-4433-85fe-22d27321b4e3",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "engine_id": null,
  "niche_key": "V5-03",
  "name": "Small-carrier managed DOT compliance and safety administration",
  "plain_ru_description": "Малые trucking companies и owner-operators с 1–10 trucks, которым постоянно нужно вести DQ files, Clearinghouse, renewals/filings, audit readiness и связанные DOT-compliance процессы.",
  "buyer": "Chicago-area owner-operators and small trucking fleets, initially 1–10 power units, reachable through the existing owner-confirmed trucking network.",
  "purchase_trigger": "New authority, hiring a driver, annual/quarterly compliance cycle, MCS-150/UCR/IFTA deadlines, Clearinghouse requirements, medical-card expiration, roadside/enforcement issues, or new-entrant/audit preparation.",
  "differentiation_hypothesis": "The proposed wedge is not generic managed compliance or automation. The only qualifying entrant edge is warm access to an existing owner-confirmed ~40-contact trucking network; trucking experience improves delivery but is not counted as the edge.",
  "primary_channel": "Existing owner-confirmed trucking network first; referrals second. Repair-center placement remains conditional and is not counted.",
  "status": "rejected",
  "source_batch": "reveng_v5_edge_first_wave2_20260924",
  "confidence_grade": "B",
  "current_adjusted_score": "40.50",
  "unknowns": [
    "Actual service minutes per account and monthly workload are unmeasured.",
    "Professional-liability/general-liability needs and exact scope disclaimers must be verified before launch.",
    "Current network willingness to outsource compliance administration is unmeasured.",
    "Retention/churn and support intensity are unknown.",
    "Economics of testing/MVR/Clearinghouse/vendor pass-through must be modeled precisely.",
    "Scale beyond the initial network must not depend on paid leads until CAC is measured."
  ],
  "kill_conditions": [
    "Reject if routine recurring service cannot be standardized to roughly <=2 owner-hours/account/month at realistic realized pricing.",
    "Reject if onboarding/exception labor or liability/security cost removes positive labor-adjusted contribution.",
    "Reject if low-cost substitutes force realized price below a sustainable level.",
    "Reject if the warm network fails to produce qualified compliance conversations in a future approved test.",
    "Reject if liability exposure cannot be bounded with SOPs, insurance and clear scope.",
    "Reject if founder labor cannot transition to repeatable account-management workflows.",
    "Reject if warm-network buyers will not pay at least ~$149/month for human managed support given $25/unit low-cost alternatives.",
    "Reject or redesign if recurring owner time exceeds 2 hours/account/month; hard kill at 3 hours without higher realized price.",
    "Do not include Form 2290 preparation without separate tax-preparer compliance/partner workflow.",
    "Do not perform Clearinghouse/testing functions outside registered/designated C/TPA or partner scope."
  ],
  "feedback_state": {
    "stage": "v5_edge_first_candidate",
    "corrected_at": "2026-10-09T05:02:31.243543+00:00",
    "not_a_finalist": true,
    "user_fit_applied": false,
    "v6_global_status": "rejected_hard_gate",
    "correction_reason": "Prior global score used retracted/current-user-specific trucking-network assumptions. Independent entrant edge is not evidenced.",
    "global_scoring_version": "reveng_v6_independent",
    "user_specific_edge_removed": true,
    "external_actions_authorized": false
  },
  "created_at": "2026-09-24 22:22:17.552364+00",
  "updated_at": "2026-10-09 05:02:31.243543+00",
  "analysis_level": "niche",
  "parent_niche_id": null
}
```

## opportunities - все записи

### Small-carrier trucking insurance brokerage through an existing carrier/driver network
```json
{
  "id": "27871e15-c603-4274-adfb-79e1371c4f99",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "opportunity_key": "OPP-V5-01-A",
  "niche_id": "0eaecc25-13a0-428d-957e-b06d604d7bd9",
  "primary_engine_id": "b1552ab6-0809-4566-9d68-40b1d2747e5f",
  "name": "Small-carrier trucking insurance brokerage through an existing carrier/driver network",
  "thesis": "Build a focused commercial P&C brokerage for Chicago-area 1-10 truck operators, using the owner’s existing small-carrier/driver network as the qualifying initial distribution edge. The business earns commissions on large recurring insurance spend and compounds only if renewals/retention and market access are strong.",
  "status": "finalist_ready",
  "confidence_grade": "B",
  "current_adjusted_score": "67.14",
  "entrant_edge": {
    "status": "evidenced",
    "not_edge": [
      "Russian/Romanian language",
      "trucking experience alone",
      "better service",
      "cheaper quotes"
    ],
    "edge_type": "existing_owned_audience_customer_base_or_partner_channel",
    "evidence_refs": [
      212
    ],
    "edge_asset_key": "EDGE-TRUCK-NETWORK-01",
    "strength_status": "commercial_strength_unproven",
    "conditional_supporting_asset": "EDGE-TRUCK-SERVICE-DISTRIBUTION-01"
  },
  "business_model": {
    "primary": "commission brokerage / agency",
    "secondary": "adjacent licensed/compliant referral rev-share",
    "revenue_units": [
      "new-business commission",
      "renewal commission",
      "optional adjacent commercial-line commission"
    ],
    "explicit_non_thesis": [
      "generic insurance website",
      "language-only positioning",
      "cheapest quote positioning"
    ]
  },
  "economics_summary": {
    "status": "scenario, not forecast",
    "must_verify": [
      "actual trucking commission",
      "renewal commission",
      "market-access fees/splits",
      "service cost/account",
      "retention"
    ],
    "producer_path": {
      "use": "lower-capital future validation path after licensing; not evidence of our own contract",
      "evidence": "current trucking producer program pays 50% new and 50% renewal agency commission while agency supplies software/x-dates"
    },
    "known_low_cost_path": {
      "WebCE_PC_course_usd": 174.95,
      "known_cost_exclusions": [
        "E&O",
        "bond if required by placement model",
        "NIPR transaction fees",
        "entity formation if needed",
        "exam fees beyond ordering assumptions"
      ],
      "TIS_starter_first_year_usd": 1887,
      "IL_resident_producer_fee_usd": 215,
      "IL_business_entity_fee_usd_if_used": 150
    },
    "acquisition_time_sensitivity": {
      "purpose": "owner-time sensitivity; not measured",
      "network_contacts": 40,
      "total_initial_outreach_hours": [
        20,
        40
      ],
      "if_outreach_followup_hours_per_contact": [
        0.5,
        1
      ],
      "owner_hours_per_bound_account_if_3_to_6_binds": "approximately 3.3 to 13.3 before quote/servicing time"
    },
    "known_first_year_fixed_floor": {
      "excludes": [
        "E&O premium",
        "bond premium if required",
        "NIPR transaction fees",
        "entity formation/registered-agent costs",
        "phone/software outside TIS",
        "service labor",
        "taxes"
      ],
      "includes": [
        "TIS Starter 12 months + setup",
        "current WebCE P&C prelicense package",
        "two P&C line exam-order assumptions",
        "Illinois resident producer fee",
        "business-entity fee only in entity scenario"
      ],
      "interpretation": "fixed-cost coverage arithmetic only; not profit forecast",
      "individual_path_usd": 2460.95,
      "with_business_entity_fee_usd": 2610.95,
      "gross_bound_accounts_to_cover_known_floor": {
        "at_960_commission": 3,
        "at_1500_commission": 2,
        "at_2250_commission": 2
      }
    },
    "stress_case_research_feasibility": {
      "purpose": "research feasibility stress-test only; empirical net contribution remains a market-validation gate",
      "excludes": [
        "direct servicing labor",
        "taxes",
        "unexpected licensing/tech costs"
      ],
      "stress_components": [
        "known entity-path floor 2610.95",
        "modeled E&O stress allowance 2000",
        "optional Big I membership 630",
        "member bond program 25"
      ],
      "fixed_cost_stress_usd": 5265.95,
      "network_size_reference": 40,
      "gross_commission_scenarios_usd": [
        960,
        1500,
        2250
      ],
      "binds_to_cover_stress_fixed_cost": [
        6,
        4,
        3
      ],
      "overall_contact_to_bind_thresholds": [
        0.15,
        0.1,
        0.075
      ]
    },
    "verified_premium_reference_usd_year": {
      "low": 12000,
      "high": 21000
    },
    "modeled_first_year_gross_commission_examples_usd": [
      960,
      1500,
      2250
    ],
    "illustrative_accounts_for_150k_gross_commission_at_1500_each": 100
  },
  "acquisition_strategy": {
    "primary": "existing owner-confirmed network of roughly 40 driver/carrier prospects",
    "not_assumed": [
      "paid lead generation",
      "exclusive local access",
      "organic SEO volume"
    ],
    "conditional_future": "repair/service-center embedded placement only after access is revalidated/formalized"
  },
  "two_person_plan": {
    "phase_1": "one licensed producer plus founder-operated intake/quoting/admin",
    "constraint": "no sales before licensing/market access; owner time must be measured per quote and renewal"
  },
  "scale_path": {
    "phase_2": "CSR/account manager when renewal book supports payroll",
    "phase_3": "additional producer or replicated trucking-service/referral channels only after one channel’s economics are proven"
  },
  "risks": [
    "local trucking-insurance competition is strong",
    "carrier/MGA access can determine whether quotes are competitive",
    "one major Great West referral route excludes the seven Chicagoland counties",
    "licensing/E&O/bond/agency compliance add fixed and operating cost",
    "the 40-prospect network may not convert or may decay",
    "truck accounts can be service-intensive and cancellation-sensitive"
  ],
  "evidence_refs": [
    201,
    202,
    203,
    204,
    205,
    206,
    207,
    208,
    209,
    210,
    211,
    212
  ],
  "unknowns": [
    "Exact weekly qualified traffic and current-policy renewal calendar are unknown.",
    "Bind rate from repair/service referrals is unknown.",
    "Carrier/MGA access for new trucking risks and new ventures must be verified contractually.",
    "Net commission after aggregator/MGA splits and service workload must be modeled.",
    "Illinois producer/entity licensing and any agency registration requirements must be completed before selling.",
    "Retention and remarketing workload for small trucking accounts is unknown."
  ],
  "kill_conditions": [
    "If embedded channel produces fewer than 5 qualified trucking insurance conversations per month after launch.",
    "If market-access partners cannot place the dominant local risk profiles competitively.",
    "If net first-year commission after splits/service cost is too low to support the sales and servicing workload.",
    "If annual retention is weak enough that renewal economics do not compound.",
    "If repair-shop access cannot be formalized or becomes non-exclusive/low-quality traffic."
  ],
  "feedback_state": {
    "finalist": false,
    "interpretation": "Passed all research gates; requires separate owner-approved market validation before winner status.",
    "v5_opportunity_layer": true,
    "empirically_validated": false,
    "research_finalist_20260924": true
  },
  "created_at": "2026-09-24 21:37:10.152863+00",
  "updated_at": "2026-09-24 21:59:05.74998+00"
}
```

### Small-carrier repair/equipment/working-capital referral desk through an existing carrier network
```json
{
  "id": "9942c38f-afe7-4db9-a0f9-31ee6e9b377a",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "opportunity_key": "OPP-V5-01-B",
  "niche_id": "88328b74-e704-4810-8234-d5f5123d14ac",
  "primary_engine_id": "99b58e03-a6b8-4af7-9ca8-fae57396aa74",
  "name": "Small-carrier repair/equipment/working-capital referral desk through an existing carrier network",
  "thesis": "Use the owner-confirmed small-carrier/driver network to route qualified repair, equipment, factoring and working-capital needs to vetted third-party providers. Revenue comes from referral/rev-share economics; the business is attractive only if annual revenue per network contact materially exceeds relationship/admin cost.",
  "status": "rejected",
  "confidence_grade": "B",
  "current_adjusted_score": "38.00",
  "entrant_edge": {
    "status": "evidenced",
    "not_edge": [
      "Russian/Romanian language",
      "trucking experience alone",
      "better service",
      "cheaper quotes"
    ],
    "edge_type": "existing_owned_audience_customer_base_or_partner_channel",
    "evidence_refs": [
      212
    ],
    "edge_asset_key": "EDGE-TRUCK-NETWORK-01",
    "strength_status": "commercial_strength_unproven",
    "conditional_supporting_asset": "EDGE-TRUCK-SERVICE-DISTRIBUTION-01"
  },
  "business_model": {
    "primary": "referral / revenue-share distribution",
    "delivery": "qualified handoff to third-party licensed/finance providers",
    "revenue_units": [
      "fixed funded-deal fee",
      "percentage/referral commission",
      "possible residual/rev share depending on partner"
    ],
    "explicit_non_thesis": [
      "becoming a lender",
      "generic lead resale",
      "building a loan marketplace before proving channel economics"
    ]
  },
  "economics_summary": {
    "status": "partner-specific, not forecast",
    "interpretation": "economics can be very low-touch but are materially smaller per customer than insurance brokerage unless residual factoring or higher-value finance compensation is secured",
    "verified_examples": [
      {
        "program": "Big Rig Lending",
        "funded_referral_fee_usd": 100
      },
      {
        "program": "Total360",
        "agreement_referral_fee_usd": 250
      },
      {
        "split": "50/50",
        "program": "Factor Finders",
        "reported_active_deals": 657,
        "trucking_active_deals": 383,
        "reported_partner_commissions_2025_usd": 214566.84
      }
    ]
  },
  "acquisition_strategy": {
    "primary": "same owner-confirmed trucking network used by OPP-V5-01-A",
    "trigger": "major repair, equipment need, working-capital/factoring pain",
    "conditional_future": "repair-shop placement if revalidated"
  },
  "two_person_plan": {
    "phase_1": "one person can qualify and route leads using partner portals",
    "compliance": "referral compensation and disclosures must follow applicable law/partner terms",
    "service_burden": "low after handoff if partner owns underwriting/servicing"
  },
  "scale_path": {
    "phase_2": "add more vetted finance/protection partners only where buyer need and compensation are measured",
    "phase_3": "replicate through additional repair/service partners if referral attribution and economics remain positive"
  },
  "risks": [
    "low per-deal referral fees can cap revenue",
    "partner owns underwriting and often the customer economics",
    "attribution and payout terms vary",
    "financial-product referral rules can vary by product/state",
    "buyer trust can be damaged by poor partner outcomes",
    "not all repair events create finance demand"
  ],
  "evidence_refs": [
    201,
    202,
    203,
    204,
    205,
    206,
    207,
    208,
    209,
    210,
    211,
    212,
    213,
    214,
    215,
    216
  ],
  "unknowns": [
    "qualified finance/referral conversations per month",
    "funding/close rate by partner",
    "average payout and payout timing",
    "residual vs one-time compensation",
    "customer consent/compliance requirements",
    "partner quality/default/complaint risk"
  ],
  "kill_conditions": [
    "If realized revenue per qualified lead is too small to justify attention.",
    "If fewer than 10% of qualified network contacts create a finance/protection referral opportunity over 12 months.",
    "If partner complaints/default outcomes damage the core trucking network relationship."
  ],
  "feedback_state": {
    "role": "compare against brokerage model",
    "reason": "At the evidenced ~40-contact channel scale, verified referral payouts are too small/irregular for a standalone business. Keep as possible ancillary monetization only if another trucking business already owns the customer relationship.",
    "finalist": false,
    "v5_redteam_rejected": true,
    "v5_opportunity_layer": true
  },
  "created_at": "2026-09-24 21:38:13.122329+00",
  "updated_at": "2026-09-24 21:46:49.742777+00"
}
```

### Managed DOT compliance subscription for small trucking fleets through the existing carrier/driver network
```json
{
  "id": "c00b91c0-5358-4ee2-8c89-bad490bd9972",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "opportunity_key": "OPP-V5-03-A",
  "niche_id": "f5ebd322-a409-4433-85fe-22d27321b4e3",
  "primary_engine_id": "60f7899e-19e9-44d1-bb8c-4b079f10140e",
  "name": "Managed DOT compliance subscription for small trucking fleets through the existing carrier/driver network",
  "thesis": "Operate a focused recurring compliance desk for 1–10 truck carriers, combining DQ/renewal/deadline/audit-readiness administration with third-party testing/MVR/Clearinghouse infrastructure where appropriate. Initial acquisition comes from the owner-confirmed trucking network, not from paid leads.",
  "status": "finalist_ready",
  "confidence_grade": "B",
  "current_adjusted_score": "67.41",
  "entrant_edge": {
    "status": "evidenced",
    "not_edge": [
      "trucking experience alone",
      "Russian/Romanian language",
      "automation",
      "generic managed service"
    ],
    "edge_type": "existing_owned_audience_customer_base_or_partner_channel",
    "edge_asset_key": "EDGE-TRUCK-NETWORK-01",
    "strength_status": "commercial_strength_unproven",
    "conditional_supporting_asset": "EDGE-TRUCK-SERVICE-DISTRIBUTION-01"
  },
  "business_model": {
    "primary": "recurring managed compliance subscription",
    "secondary": [
      "setup/remediation fees",
      "pass-through third-party testing/MVR costs",
      "ancillary partner referrals only if compliant"
    ],
    "explicit_non_thesis": [
      "generic reminder software",
      "one-time filing shop",
      "affiliate-only compliance referrals"
    ]
  },
  "economics_summary": {
    "status": "scenario, not forecast",
    "must_verify": [
      "service minutes/account",
      "backend software/partner cost",
      "testing/MVR/Clearinghouse pass-through economics",
      "professional-liability insurance",
      "retention",
      "support burden"
    ],
    "interpretation": "Revenue arithmetic only; no labor-adjusted profit forecast until service workload is measured.",
    "research_gate_status": "unit economics structurally feasible; actual net contribution remains empirical",
    "research_sensitivity": {
      "not_forecast": true,
      "modeled_accounts": 10,
      "monthly_price_usd": 199,
      "labor_value_usd_hour": 50,
      "contribution_margin_at_2h": 0.247,
      "fixed_backend_stress_usd_month": 499,
      "break_even_near_hours_per_account_month": 3,
      "routine_service_target_hours_per_account_month": "<=2",
      "contribution_at_2h_before_other_overhead_usd_month": 491
    },
    "published_price_anchors": {
      "owner_operator_monthly_usd": [
        149,
        199
      ],
      "small_fleet_up_to_5_monthly_usd": 499,
      "low_price_managed_substitute_per_unit_monthly_usd": 25
    },
    "illustrative_revenue_only": {
      "blended_10_account_arr_usd": 30000,
      "10_accounts_at_blended_250_mrr_usd": 2500,
      "5_small_fleet_accounts_at_499_mrr_usd": 2495,
      "10_owner_operator_accounts_at_199_mrr_usd": 1990
    }
  },
  "acquisition_strategy": {
    "primary": "existing owner-confirmed network of roughly 40 driver/carrier prospects",
    "not_assumed": [
      "paid leads",
      "repair-center exclusivity",
      "organic SEO volume"
    ],
    "conditional_future": "repair/service-center distribution only after access is refreshed/formalized"
  },
  "two_person_plan": {
    "phase_1": "one founder handles sales/account intake while the second person/admin stack handles recurring document/deadline workflow; testing/MVR backend may be partnered",
    "constraint": "Do not claim two-person feasibility until monthly service minutes and exception workload are bounded"
  },
  "scale_path": {
    "phase_2": "standardized SOPs and compliance-management platform for a larger book",
    "phase_3": "dedicated compliance account manager/CSR when recurring MRR supports payroll; expand through partner/referral channels only after retention and CAC evidence"
  },
  "risks": [
    "strong Chicago/national compliance competition",
    "low-price software and managed substitutes compress pricing",
    "regulatory mistakes can create customer harm and liability",
    "service labor may scale poorly",
    "customer documents contain sensitive business/driver data and require strong security",
    "warm network may not convert"
  ],
  "evidence_refs": [
    242,
    243,
    244,
    245,
    246,
    247,
    248,
    249,
    250,
    251
  ],
  "unknowns": [
    "Actual service minutes per account and monthly workload are unmeasured.",
    "Professional-liability/general-liability needs and exact scope disclaimers must be verified before launch.",
    "Current network willingness to outsource compliance administration is unmeasured.",
    "Retention/churn and support intensity are unknown.",
    "Economics of testing/MVR/Clearinghouse/vendor pass-through must be modeled precisely.",
    "Scale beyond the initial network must not depend on paid leads until CAC is measured."
  ],
  "kill_conditions": [
    "Reject if routine recurring service cannot be standardized to roughly <=2 owner-hours/account/month at realistic realized pricing.",
    "Reject if onboarding/exception labor or liability/security cost removes positive labor-adjusted contribution.",
    "Reject if low-cost substitutes force realized price below a sustainable level.",
    "Reject if the warm network fails to produce qualified compliance conversations in a future approved test.",
    "Reject if liability exposure cannot be bounded with SOPs, insurance and clear scope.",
    "Reject if founder labor cannot transition to repeatable account-management workflows."
  ],
  "feedback_state": {
    "finalist": false,
    "interpretation": "All research gates passed; winner status requires owner-approved measured channel response, CAC and net contribution.",
    "research_stage": "finalist_ready",
    "v5_opportunity_layer": true,
    "empirically_validated": false,
    "research_finalist_20260924": true
  },
  "created_at": "2026-09-24 22:22:17.552364+00",
  "updated_at": "2026-09-24 22:28:01.40387+00"
}
```

### Trucking bookkeeping subscription through the existing carrier/driver network
```json
{
  "id": "e40e49ba-3c3f-4b05-a0f1-3b656ddca1d7",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "opportunity_key": "OPP-V5-04-A",
  "niche_id": "7dd5fa33-63a9-4f9f-a711-8e4bd78f1ddc",
  "primary_engine_id": "60f7899e-19e9-44d1-bb8c-4b079f10140e",
  "name": "Trucking bookkeeping subscription through the existing carrier/driver network",
  "thesis": "Provide a bounded monthly bookkeeping/financial back-office service for 1-10 truck carriers: reconciliations, trucking-specific categorization, settlement/factoring review, truck-level P&L and CPA-ready books. Tax-return preparation, CPA titles and assurance work are excluded from launch scope.",
  "status": "finalist_ready",
  "confidence_grade": "B",
  "current_adjusted_score": "68.49",
  "entrant_edge": {
    "status": "evidenced",
    "not_edge": [
      "generic bookkeeping",
      "trucking knowledge alone",
      "automation",
      "low price"
    ],
    "edge_type": "existing_owned_audience_customer_base_or_partner_channel",
    "evidence_refs": [
      259
    ],
    "edge_asset_key": "EDGE-TRUCK-NETWORK-01",
    "strength_status": "commercial_strength_unproven"
  },
  "business_model": {
    "primary": "recurring managed bookkeeping subscription",
    "secondary": [
      "separately priced catch-up/cleanup",
      "fleet reporting add-ons"
    ],
    "explicit_non_thesis": [
      "tax-return preparation at launch",
      "CPA/assurance services",
      "generic SMB bookkeeping without trucking-specific workflow"
    ]
  },
  "economics_summary": {
    "status": "pricing evidence, unit economics open",
    "must_verify": [
      "service hours/account",
      "software/file cost",
      "review/QA labor",
      "cleanup frequency",
      "retention"
    ],
    "not_forecast": true,
    "research_gate_status": "unit economics and two-person capacity structurally feasible; actual net contribution remains empirical",
    "research_sensitivity": {
      "cleanup": "separately priced/scheduled",
      "not_forecast": true,
      "contribution_at_350_4h_usd": 100,
      "contribution_at_350_5h_usd": 50,
      "contribution_at_500_6h_usd": 150,
      "routine_target_hours_per_account_month": "<=4-5",
      "full_service_target_price_floor_usd_month": 350,
      "break_even_hours_at_350_price_50_software_50_labor": 6
    },
    "low_price_substitute_usd_per_truck_month": 125,
    "published_small_fleet_price_range_usd_month": [
      199,
      1200
    ],
    "published_owner_operator_price_range_usd_month": [
      129,
      500
    ]
  },
  "acquisition_strategy": {
    "future": "referrals and public carrier prospecting only after measured CAC/retention",
    "primary": "existing owner-confirmed ~40-contact trucking network",
    "not_assumed": [
      "paid leads",
      "SEO volume",
      "repair-center exclusivity"
    ]
  },
  "two_person_plan": {
    "phase_1": "founder intake plus standardized monthly-close workflow",
    "constraint": "do not pass two-person gate until recurring and cleanup hours/account are bounded"
  },
  "scale_path": {
    "phase_2": "dedicated bookkeeper when book supports payroll",
    "phase_3": "review lead/controller and compliant tax/CPA partner channel if customer demand supports it"
  },
  "risks": [
    "crowded category with low-price substitutes",
    "bookkeeping errors can damage customer decisions/tax handoff",
    "catch-up cleanup can create large one-time labor",
    "financial data security/privacy",
    "customers may expect tax advice outside scope",
    "warm network may not convert"
  ],
  "evidence_refs": [
    252,
    253,
    254,
    255,
    256,
    257,
    258,
    259
  ],
  "unknowns": [
    "Actual monthly transaction volume and service hours by 1-truck vs 2-10-truck account are unknown.",
    "Software/client-file cost per account is unmodeled.",
    "Catch-up/cleanup labor can be much larger than recurring monthly close.",
    "Actual network willingness to outsource bookkeeping is unmeasured.",
    "Bookkeeping quality-control/review process must be defined.",
    "Tax-return preparation, tax advice, attest/assurance and CPA-title use must remain out of launch scope unless proper credentials/requirements are satisfied.",
    "Retention/churn is unknown."
  ],
  "kill_conditions": [
    "Reject if full managed recurring price is materially below ~$350/account without a correspondingly lighter scope.",
    "Reject if routine recurring service exceeds roughly 5 hours/account/month at ~$350 realized price after workflow stabilization.",
    "Reject if cleanup/catch-up cannot be separately priced and scheduled.",
    "Reject if the warm network produces no qualified bookkeeping demand in a future approved test.",
    "Reject if QA/review requires founder-only accounting expertise that cannot be standardized or hired.",
    "Reject if customers primarily demand regulated tax/CPA/assurance services outside the bounded launch scope."
  ],
  "feedback_state": {
    "finalist": false,
    "interpretation": "All research gates passed/not-applicable; winner status requires owner-approved measured response, CAC and net contribution.",
    "research_stage": "finalist_ready",
    "v5_opportunity_layer": true,
    "empirically_validated": false,
    "research_finalist_20260924": true
  },
  "created_at": "2026-09-24 22:32:53.675481+00",
  "updated_at": "2026-09-24 22:34:01.700913+00"
}
```

## catalog_candidate_inbox - все записи

### Employer-paid CDL driver recruiting
```json
{
  "id": "25cd7933-d82f-4612-95ee-9cc70463f59b",
  "fingerprint": "fa453c77cf68ce4ae4d30d3843ad1bd24dffa89c12e107bb9ab10720787dfbd3",
  "candidate_key": "FC2-RAW-02",
  "analysis_level": "niche",
  "raw_name": "Employer-paid CDL driver recruiting",
  "normalized_name": "Small-carrier employer-paid CDL driver recruiting",
  "buyer_segment": "Small carriers with empty seats / idle trucks that need Class A drivers",
  "core_job": "Source, screen and recommend CDL candidates for employer-paid placement without charging drivers.",
  "primary_outcome": "Fill revenue-producing seats faster.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 3,
  "evidence_hints": [
    {
      "url": "https://truckdispatchingusa.com/driver-recruiting.html",
      "signal": "$650 per hire, screened driver, DQ file build, 60-day guarantee",
      "source": "Truck Dispatching USA"
    },
    {
      "url": "https://boostpoint.com/industries-trucking/truck-driver-recruiting-agency-cost/",
      "signal": "2026 agency-placement benchmark $2,500-$6,000+ per Class A driver",
      "source": "Boostpoint"
    },
    {
      "url": "https://www.ilga.gov/ftp/ILCS/Ch%200225/Act%200515/022505150K1.1.html",
      "signal": "Employer-only paid consulting/recruiting exclusion from Private Employment Agency definition if statutory conditions are met",
      "source": "Illinois General Assembly"
    }
  ],
  "rejection_reason": "POST_SCREEN_EDGE_GATE_FAILED: macro CDL hiring demand and employer WTP are verified, but owned-network two-sided liquidity is not. Re-enter only if current hiring-carrier + available-driver supply is evidenced without paid lead dependence.",
  "metadata": {
    "edge": "EDGE-TRUCK-NETWORK-01",
    "fast_cash": "screen",
    "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
    "external_actions": false,
    "candidate_fee_forbidden": true
  },
  "first_seen_at": "2026-10-03 20:37:09.407505+00",
  "last_seen_at": "2026-10-03 23:40:02.731914+00"
}
```

### Printable activity product business
```json
{
  "id": "4eb16a33-04dc-43bc-9fbb-4ac4a1fad874",
  "fingerprint": "1715b59e9aa135ec72ebf8f9539de755",
  "candidate_key": "fixture-candidate-a",
  "analysis_level": "business_opportunity",
  "raw_name": "Printable activity product business",
  "normalized_name": "Printable activity products for parents",
  "buyer_segment": "Parents of children ages 4-8",
  "core_job": "Keep children engaged with useful offline activities",
  "primary_outcome": "Convenient themed activity packs",
  "suggested_model_key": "digital_download",
  "suggested_market_key": "family_activities",
  "status": "normalized",
  "source_count": 2,
  "evidence_hints": [],
  "rejection_reason": null,
  "metadata": {
    "fixture": true,
    "duplicate_test": true
  },
  "first_seen_at": "2026-09-25 05:04:46.68536+00",
  "last_seen_at": "2026-09-25 05:04:46.68536+00"
}
```

### Dinosaur coloring PDF
```json
{
  "id": "9cd9a4d8-ac8e-48a9-90e5-1d91a2073292",
  "fingerprint": "bd5def6dac7ae3a4a4e7efbf6327663b",
  "candidate_key": "fixture-offer-only",
  "analysis_level": "offer",
  "raw_name": "Dinosaur coloring PDF",
  "normalized_name": "Dinosaur coloring PDF",
  "buyer_segment": "Parents of children ages 4-8",
  "core_job": "Keep children engaged with useful offline activities",
  "primary_outcome": "One dinosaur coloring PDF",
  "suggested_model_key": "digital_download",
  "suggested_market_key": "family_activities",
  "status": "new",
  "source_count": 1,
  "evidence_hints": [],
  "rejection_reason": null,
  "metadata": {
    "fixture": true
  },
  "first_seen_at": "2026-09-25 05:04:46.68536+00",
  "last_seen_at": "2026-09-25 05:04:46.68536+00"
}
```

### Digital home inventory organizer for renters
```json
{
  "id": "95f17bc8-8723-46db-bf7b-b24c64091acf",
  "fingerprint": "a5c1c263bf983d28a29dd65c5c043940",
  "candidate_key": "alpha-clean-digital-inventory",
  "analysis_level": "business_opportunity",
  "raw_name": "Digital home inventory organizer for renters",
  "normalized_name": "Digital home inventory organizer for renters",
  "buyer_segment": "Apartment renters and frequent movers",
  "core_job": "Document possessions and move-related details quickly",
  "primary_outcome": "Reusable structured inventory, move and claim-ready records",
  "suggested_model_key": "digital_download",
  "suggested_market_key": "home_inventory_tools",
  "status": "promoted",
  "source_count": 1,
  "evidence_hints": [],
  "rejection_reason": null,
  "metadata": {
    "fixture": true,
    "revsoft": "140",
    "tenant_neutral": true,
    "promoted_opportunity_id": "777118d4-c16b-40a4-9c85-70a96ab85b77"
  },
  "first_seen_at": "2026-09-25 06:23:48.466324+00",
  "last_seen_at": "2026-09-25 06:23:48.466324+00"
}
```

### Carrier billing / POD / invoice desk
```json
{
  "id": "53c2e73f-30b2-4635-b217-3fe3b2aabfb4",
  "fingerprint": "5c5aecaad4f774a5218438ec050c3ecde0cd930b037201d4e6ea8d4ea009ef29",
  "candidate_key": "FC2-RAW-01",
  "analysis_level": "niche",
  "raw_name": "Carrier billing / POD / invoice desk",
  "normalized_name": "Small-carrier billing packet, POD and invoice operations",
  "buyer_segment": "Owner-operators and small fleets, initially 1-10 trucks",
  "core_job": "Turn delivered loads into complete billing packets/invoices and keep payment status organized without acting as a collection agency.",
  "primary_outcome": "Faster correct invoicing and fewer missing-document/payment-status gaps.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "promoted",
  "source_count": 4,
  "evidence_hints": [
    {
      "url": "https://truck-owner.com/",
      "signal": "Billing & payments $199 per active truck/month",
      "source": "Fleet Assist"
    },
    {
      "url": "https://www.adwafreight.com/",
      "signal": "Owner-operator back-office tier $149/month includes billing packet readiness/invoice workflow",
      "source": "Adwa Freight"
    },
    {
      "url": "https://getclearlane.com/pricing/",
      "signal": "Managed billing/POD/AR desk sold as a standalone outsourced function",
      "source": "ClearLane"
    },
    {
      "url": "https://ilga.gov/legislation/ilcs/fulltext?DocName=020507400K2.03",
      "signal": "Creditor-name debt notifications have a statutory exemption; broader collection activity requires licensing",
      "source": "Illinois General Assembly"
    }
  ],
  "rejection_reason": null,
  "metadata": {
    "edge": "EDGE-TRUCK-NETWORK-01",
    "fast_cash": "screen",
    "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
    "external_actions": false
  },
  "first_seen_at": "2026-10-03 20:37:09.407505+00",
  "last_seen_at": "2026-10-03 20:37:09.407505+00"
}
```

### Standalone DQ-file setup/audit
```json
{
  "id": "63f5bce4-fe42-4c4b-a622-51b83766b8a9",
  "fingerprint": "8b7030d7b21c9e122b42d2125b0d39ba89db645ddd7463b2e064b9261a122a9f",
  "candidate_key": "FC2-RAW-03",
  "analysis_level": "niche",
  "raw_name": "Standalone DQ-file setup/audit",
  "normalized_name": "Driver qualification file setup/audit for small carriers",
  "buyer_segment": "Small carriers hiring or maintaining CDL drivers",
  "core_job": "Build, review and remediate DQ files.",
  "primary_outcome": "Audit-ready driver files.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 3,
  "evidence_hints": [
    {
      "url": "https://truckingcomply.com/service/driver-qualification-file",
      "signal": "$179 new DQ file / $95 annual renewal",
      "source": "Trucking Comply"
    },
    {
      "url": "https://www.usdot.co/services/dq-file",
      "signal": "$160/driver DQ-file service",
      "source": "USDOT.co"
    },
    {
      "url": "https://www.getuptime.ai/",
      "signal": "$60/file under 50 drivers for compliance audit",
      "source": "Uptime"
    }
  ],
  "rejection_reason": "MERGE_EXISTING_DOT: same buyer/problem cluster as V5-03 managed DOT compliance; use as an offer/wedge, not a duplicate niche.",
  "metadata": {
    "fast_cash": "offer_wedge",
    "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
    "merge_niche_key": "V5-03"
  },
  "first_seen_at": "2026-10-03 20:37:09.407505+00",
  "last_seen_at": "2026-10-03 20:37:09.407505+00"
}
```

### DataQs challenge support
```json
{
  "id": "204e5d4e-de59-4b7c-a8e9-b4fa19aa3b60",
  "fingerprint": "d5de45fc22c15f2c3ab0846c04d0498050ad899b8d8890196157e68bfd59446b",
  "candidate_key": "FC2-RAW-04",
  "analysis_level": "niche",
  "raw_name": "DataQs challenge support",
  "normalized_name": "Small-carrier FMCSA DataQs review/filing support",
  "buyer_segment": "Carriers/drivers with incorrect or disputable FMCSA crash/inspection/violation data",
  "core_job": "Assemble evidence and draft/track Requests for Data Review.",
  "primary_outcome": "Correct inaccurate safety data when evidence supports a challenge.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 3,
  "evidence_hints": [
    {
      "url": "https://dataqs.fmcsa.dot.gov/HelpCenter/Faqs?topic_id=1",
      "signal": "RDR system is free; carriers, drivers and public users can submit requests",
      "source": "FMCSA DataQs"
    },
    {
      "url": "https://www.tenfourcompliance.com/pricing",
      "signal": "DataQs drafting sold at $99; market comparison $25-$250 each",
      "source": "TenFour"
    },
    {
      "url": "https://safehaulsolutions.com/pricing",
      "signal": "Data Q Assistance $50",
      "source": "Safe Haul Solutions"
    }
  ],
  "rejection_reason": "MERGE_EXISTING_DOT: event-driven support fits inside V5-03 compliance/audit-readiness instead of a separate recurring niche.",
  "metadata": {
    "fast_cash": "offer_wedge",
    "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
    "merge_niche_key": "V5-03"
  },
  "first_seen_at": "2026-10-03 20:37:09.407505+00",
  "last_seen_at": "2026-10-03 20:37:09.407505+00"
}
```

### New authority setup coordination
```json
{
  "id": "1d784954-ea16-41e2-9fb4-a9014d80ae6d",
  "fingerprint": "883e12c666e8edf063a85531325823bae960ddef322c016ae922a4dc90ba9252",
  "candidate_key": "FC2-RAW-05",
  "analysis_level": "niche",
  "raw_name": "New authority setup coordination",
  "normalized_name": "New-carrier authority setup and activation coordination",
  "buyer_segment": "New owner-operators starting interstate authority",
  "core_job": "Sequence USDOT/MC/UCR/BOC-3/insurance/compliance setup and track activation.",
  "primary_outcome": "Get authority operational without missing required steps.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 3,
  "evidence_hints": [
    {
      "url": "https://truckdispatchingusa.com/mc-authority-setup.html",
      "signal": "Published $649 service fee for MC authority setup",
      "source": "Truck Dispatching USA"
    },
    {
      "url": "https://www.fmcsa.dot.gov/registration/process-agents/pa",
      "signal": "Motor carriers require process-agent designation; BOC-3 filing belongs to authorized process-agent path",
      "source": "FMCSA"
    },
    {
      "url": "https://truckingcomply.com/",
      "signal": "Filing services from $70 per filing",
      "source": "Trucking Comply"
    }
  ],
  "rejection_reason": "MERGE_EXISTING_DOT: one-time onboarding/setup is a natural acquisition wedge for V5-03, not a separate defensible niche.",
  "metadata": {
    "fast_cash": "offer_wedge",
    "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
    "merge_niche_key": "V5-03"
  },
  "first_seen_at": "2026-10-03 20:37:09.407505+00",
  "last_seen_at": "2026-10-03 20:37:09.407505+00"
}
```

### IFTA quarterly filing concierge
```json
{
  "id": "cb30be2e-b575-4958-be72-5659f620207d",
  "fingerprint": "1a5631cb7fbf64d27cc02783c350b73554e1d8878e8dacfe914748c7bd0204b7",
  "candidate_key": "FC2-RAW-06",
  "analysis_level": "niche",
  "raw_name": "IFTA quarterly filing concierge",
  "normalized_name": "IFTA quarterly return preparation/filing concierge",
  "buyer_segment": "Owner-operators and small fleets subject to IFTA",
  "core_job": "Turn fuel/mileage records into quarterly filing-ready returns.",
  "primary_outcome": "Avoid quarterly filing work/errors.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 4,
  "evidence_hints": [
    {
      "url": "https://www.milebinder.com/",
      "signal": "$15/quarter one truck; $57/quarter five trucks",
      "source": "MileBinder"
    },
    {
      "url": "https://iftaplus.com/pricing/",
      "signal": "$39 per quarter for 1-2 trucks filing preparation",
      "source": "IFTA Plus"
    },
    {
      "url": "https://www.truckopedia.com/pricing/",
      "signal": "$34.99 quarterly report for 0-2 vehicles",
      "source": "Truckopedia"
    },
    {
      "url": "https://sandbox.iftae-file.com/pricing/",
      "signal": "$20/quarter/truck individual + $15 e-file service",
      "source": "Truck e-Services"
    }
  ],
  "rejection_reason": "LOW_ARPU_COMMODITY: current public prices around $15-$39 per quarter for 1-2 trucks leave too little standalone gross profit relative to support/error burden; retain only as DOT/bookkeeping add-on.",
  "metadata": {
    "fast_cash": "reject_standalone",
    "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
    "merge_niche_key": "V5-03"
  },
  "first_seen_at": "2026-10-03 20:37:09.407505+00",
  "last_seen_at": "2026-10-03 20:37:09.407505+00"
}
```

### Truck maintenance coordination
```json
{
  "id": "e90f2b95-c4e1-4f14-be4f-d9d365fc8842",
  "fingerprint": "b18237385838e63454f806411239195417abf62a60f458733b92996c2cf56e20",
  "candidate_key": "FC2-RAW-07",
  "analysis_level": "niche",
  "raw_name": "Truck maintenance coordination",
  "normalized_name": "Small-carrier maintenance and repair coordination",
  "buyer_segment": "Owner-operators and small fleets with breakdown/repair/admin burden",
  "core_job": "Find shops, review estimates, schedule/follow repairs and maintain service history.",
  "primary_outcome": "Reduce owner time lost coordinating repairs.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 2,
  "evidence_hints": [
    {
      "url": "https://truck-owner.com/services/fleet-maintenance",
      "signal": "$49 per active truck/month, 24/7 maintenance coordination",
      "source": "Fleet Assist"
    },
    {
      "signal": "Repair-center access exists only as conditional/unconfirmed EDGE-TRUCK-SERVICE-DISTRIBUTION-01",
      "source": "RevEng edge asset"
    }
  ],
  "rejection_reason": "EDGE_NOT_READY_AND_LOW_PRICE: $49/truck/month with 24/7 expectations is weak without confirmed embedded repair-center distribution/vendor economics.",
  "metadata": {
    "fast_cash": "reject_for_now",
    "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
    "conditional_edge": "EDGE-TRUCK-SERVICE-DISTRIBUTION-01"
  },
  "first_seen_at": "2026-10-03 20:37:09.407505+00",
  "last_seen_at": "2026-10-03 20:37:09.407505+00"
}
```

### Realtor listing reel editing
```json
{
  "id": "3b0c0841-a399-4c6a-942c-d5f0d75437ed",
  "fingerprint": "d89d16046bbb72ab86b610fb4920d0a9753f39f1bfc571197c607a6eaf6a9606",
  "candidate_key": "FC2-RAW-08",
  "analysis_level": "niche",
  "raw_name": "Realtor listing reel editing",
  "normalized_name": "Real-estate listing reel editing from existing photos/video",
  "buyer_segment": "Residential real-estate agents with active listings",
  "core_job": "Turn existing listing media into social-ready vertical videos.",
  "primary_outcome": "More listing/agent social content without another shoot.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 4,
  "evidence_hints": [
    {
      "url": "https://listingcut.com/",
      "signal": "$99-$199 per listing",
      "source": "ListingCut"
    },
    {
      "url": "https://www.gemsmedia.co/real-estate",
      "signal": "$225 single reel / $549 three-video launch / $995 monthly",
      "source": "GEMS Media"
    },
    {
      "url": "https://rephotoschicago.com/services/real-estate-reels/",
      "signal": "Chicagoland reels from $125 for three cuts as shoot add-on",
      "source": "Novo Chicago"
    },
    {
      "signal": "MediaEngine/Forge automation exists but is explicitly not a v5 entrant edge",
      "source": "RevEng edge asset"
    }
  ],
  "rejection_reason": "ENTRANT_EDGE_HARD_GATE_FAILED: WTP exists, but no gate-eligible realtor distribution exists yet; editing automation alone cannot pass v5.",
  "metadata": {
    "fast_cash": "reject_until_distribution",
    "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
    "conditional_edge": "EDGE-TOWNCOUSINS-LOCAL-REAL-ESTATE-01"
  },
  "first_seen_at": "2026-10-03 20:37:09.407505+00",
  "last_seen_at": "2026-10-03 20:37:09.407505+00"
}
```

### DQ-file maintenance
```json
{
  "id": "d9e4436d-352f-4931-80ff-7cfb415b5fd7",
  "fingerprint": "4f2b903071ac47968cb5b910dba56c0bb882f4c611667cc77efd1040cb9ad75d",
  "candidate_key": "FC2B-RAW-06",
  "analysis_level": "niche",
  "raw_name": "DQ-file maintenance",
  "normalized_name": "Managed DQ-file build and maintenance",
  "buyer_segment": "Small fleets with employed CDL drivers",
  "core_job": "Build, remediate and maintain Part 391 driver files.",
  "primary_outcome": "Audit-ready DQ files.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 3,
  "evidence_hints": [
    {
      "signal": "$75 setup + $30/driver/month maintenance",
      "source": "DotFleet"
    },
    {
      "signal": "$39-$149/month software",
      "source": "DQTrack"
    },
    {
      "signal": "same buyer/compliance workflow",
      "source": "V5-03 DOT"
    }
  ],
  "rejection_reason": "MERGE_EXISTING_DOT: paid service is valid but duplicates the core V5-03 DOT scope.",
  "metadata": {
    "fast_cash": "offer_wedge",
    "merge_niche_key": "V5-03"
  },
  "first_seen_at": "2026-10-04 01:52:00.328993+00",
  "last_seen_at": "2026-10-04 01:52:00.328993+00"
}
```

### Real-estate transaction coordination
```json
{
  "id": "9543a9e0-a320-4da6-ab62-422c9056eec5",
  "fingerprint": "752237003f6380d95f377d369e8593d37efdd25eaef97327579912cb392d87d0",
  "candidate_key": "FC2-RAW-09",
  "analysis_level": "niche",
  "raw_name": "Real-estate transaction coordination",
  "normalized_name": "Per-file residential real-estate transaction coordination",
  "buyer_segment": "Real-estate agents/brokerages with closed/pending transaction volume",
  "core_job": "Coordinate deadlines/documents/communications from contract to close.",
  "primary_outcome": "Reduce agent administrative load per transaction.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 2,
  "evidence_hints": [
    {
      "url": "https://cloudcoordinator.io/transaction-coordinator-cost",
      "signal": "2026 planning range $300-$500 per closed file",
      "source": "CloudCoord"
    },
    {
      "url": "https://www.virtustant.com/blog/real-estate-transaction-coordinator",
      "signal": "US transaction coordinators commonly quoted $300-$500/file",
      "source": "Virtustant"
    }
  ],
  "rejection_reason": "ENTRANT_EDGE_HARD_GATE_FAILED: attractive per-file WTP, but no proven owned realtor/brokerage channel; Town Cousins real-estate surface remains conditional.",
  "metadata": {
    "fast_cash": "reject_until_distribution",
    "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
    "conditional_edge": "EDGE-TOWNCOUSINS-LOCAL-REAL-ESTATE-01"
  },
  "first_seen_at": "2026-10-03 20:37:09.407505+00",
  "last_seen_at": "2026-10-03 20:37:09.407505+00"
}
```

### Construction takeoff service
```json
{
  "id": "4b61728a-b951-4ce0-a175-4e69510ffc85",
  "fingerprint": "ccadd87f9e5f2fe03abbeffb10e61ad4cff1d7deaaa063fd4c9b519b94759ac1",
  "candidate_key": "FC2-RAW-10",
  "analysis_level": "niche",
  "raw_name": "Construction takeoff service",
  "normalized_name": "Residential/small-commercial construction takeoff and estimating service",
  "buyer_segment": "Contractors who need bids/takeoffs without a full-time estimator",
  "core_job": "Read plans, quantify materials/trades and produce estimate/takeoff packages.",
  "primary_outcome": "Submit more bids without adding estimator payroll.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 2,
  "evidence_hints": [
    {
      "url": "https://p2cconstruction.com/construction-estimating-services-cost-2026/",
      "signal": "2026 single-trade residential takeoff roughly $200-$400; commercial $250-$900",
      "source": "P2C Construction"
    },
    {
      "url": "https://www.takeoffmonkey.com/how-much-do-construction-takeoff-services-cost/",
      "signal": "Outsourced takeoff market is active and project-priced",
      "source": "Takeoff Monkey"
    }
  ],
  "rejection_reason": "ENTRANT_EDGE_HARD_GATE_FAILED: no gate-eligible contractor distribution or specialist estimating capability is evidenced; generic automation/low price is not an edge.",
  "metadata": {
    "fast_cash": "reject",
    "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5"
  },
  "first_seen_at": "2026-10-03 20:37:09.407505+00",
  "last_seen_at": "2026-10-03 20:37:09.407505+00"
}
```

### Carrier vendor referral monetization
```json
{
  "id": "b796957a-5214-485e-ad24-da9bab575bb8",
  "fingerprint": "3cb690346623ed9b36ad164657e443aa6f059d39128a4fc3413a483e91656719",
  "candidate_key": "FC2B-RAW-01",
  "analysis_level": "niche",
  "raw_name": "Carrier vendor referral monetization",
  "normalized_name": "Carrier factoring/fuel/dispatch vendor referral desk",
  "buyer_segment": "Owner-operators and small fleets reachable through the owned trucking network",
  "core_job": "Match carriers to vendor-run factoring, fuel-card, dispatch or authority services and earn vendor referral/partner payouts without performing the underlying service.",
  "primary_outcome": "Very low-delivery revenue from existing relationships when a referred carrier activates/uses a vendor service.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "promoted",
  "source_count": 6,
  "evidence_hints": [
    {
      "signal": "$250 factoring, $100 fuel-card, $100 dispatch, $20 authority-service referral payouts",
      "source": "QP Ambassador"
    },
    {
      "signal": "10% recurring factoring referral commission",
      "source": "Summar Partner Hub"
    },
    {
      "signal": "monthly commission agent program",
      "source": "RTS Referral"
    },
    {
      "signal": "one-time or lifetime percentage of gross revenue",
      "source": "Porter Freight Funding"
    },
    {
      "signal": "up to $1,000 per approved fleet after 4,000 gallons",
      "source": "RoadFlex"
    },
    {
      "signal": "broad loan-broker definition requires regulatory boundary review before compensated finance referrals",
      "source": "Illinois Loan Brokers Act"
    }
  ],
  "rejection_reason": null,
  "metadata": {
    "edge": "EDGE-TRUCK-NETWORK-01",
    "fast_cash": "screen",
    "delivery_labor": "very_low",
    "external_actions": false
  },
  "first_seen_at": "2026-10-04 01:52:00.328993+00",
  "last_seen_at": "2026-10-04 01:52:00.328993+00"
}
```

### Truck repair invoice audit / warranty recovery
```json
{
  "id": "3e24dfaf-dd14-46d3-aeac-e269b930d2ec",
  "fingerprint": "4f0d8f63ab009d2e5cea51a7ecd4b4c30725841fcb4daead380ee8cb01708a9d",
  "candidate_key": "FC2B-RAW-02",
  "analysis_level": "niche",
  "raw_name": "Truck repair invoice audit / warranty recovery",
  "normalized_name": "Owner-operator truck repair estimate/invoice audit and recovery",
  "buyer_segment": "Owner-operators and small fleets that outsource truck repairs",
  "core_job": "Review repair estimates/invoices for labor/parts/warranty errors and negotiate/document savings before or after payment.",
  "primary_outcome": "Reduce repair overpayment and recover warranty/billing leakage on a contingency or fixed-fee basis.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "promoted",
  "source_count": 5,
  "evidence_hints": [
    {
      "signal": "40% of recovered savings, no upfront cost",
      "source": "Fleet Cost Shield"
    },
    {
      "signal": "commercial fleet repair estimate/invoice audit product",
      "source": "FleetLens"
    },
    {
      "signal": "$39.99 estimate review / $99.99 advocacy",
      "source": "Big Brother Automotive"
    },
    {
      "signal": "$49/truck/month maintenance coordination with estimate review",
      "source": "Fleet Assist"
    },
    {
      "signal": "owned trucking buyer network; repair-center access not required for initial remote audit",
      "source": "owner edge"
    }
  ],
  "rejection_reason": null,
  "metadata": {
    "edge": "EDGE-TRUCK-NETWORK-01",
    "fast_cash": "screen",
    "external_actions": false,
    "conditional_supporting_edge": "EDGE-TRUCK-SERVICE-DISTRIBUTION-01"
  },
  "first_seen_at": "2026-10-04 01:52:00.328993+00",
  "last_seen_at": "2026-10-04 01:52:00.328993+00"
}
```

### Independent truck dispatch
```json
{
  "id": "80f093e7-34f4-4d38-b0f4-8de2d0acd43c",
  "fingerprint": "91efd15c972227e643b2176dc3b5a3afff7cd4903edb9e2c63d9bf53f6491046",
  "candidate_key": "FC2B-RAW-03",
  "analysis_level": "niche",
  "raw_name": "Independent truck dispatch",
  "normalized_name": "Owner-operator load booking and dispatch service",
  "buyer_segment": "Owner-operators and small fleets",
  "core_job": "Find/negotiate/book loads and coordinate trips.",
  "primary_outcome": "Keep trucks loaded and reduce owner booking/admin time.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 3,
  "evidence_hints": [
    {
      "signal": "$799/truck/month dispatch",
      "source": "Fleet Assist"
    },
    {
      "signal": "3-10% or $300/week/truck",
      "source": "Grow Trucking"
    },
    {
      "signal": "dispatch/bona fide agent vs broker boundary requires case-specific compliance",
      "source": "FMCSA"
    }
  ],
  "rejection_reason": "OWNER_TIME_AND_REGULATORY_RISK: high-touch daily operations, intense competition, and FMCSA broker/bona-fide-agent boundary make this inferior to lower-labor carrier services.",
  "metadata": {
    "edge": "EDGE-TRUCK-NETWORK-01",
    "fast_cash": "reject"
  },
  "first_seen_at": "2026-10-04 01:52:00.328993+00",
  "last_seen_at": "2026-10-04 01:52:00.328993+00"
}
```

### Detention/accessorial recovery
```json
{
  "id": "f888c308-f135-4a4e-ba73-8f4570402c88",
  "fingerprint": "4bd14cf18cbb90152d0a10575cdfeebfc02609464ba8eed6937427e00c3c60c0",
  "candidate_key": "FC2B-RAW-04",
  "analysis_level": "niche",
  "raw_name": "Detention/accessorial recovery",
  "normalized_name": "Carrier detention and accessorial recovery service",
  "buyer_segment": "Small for-hire carriers with unpaid detention/layover/TONU/accessorials",
  "core_job": "Prepare evidence, follow claims and recover documented earned accessorial revenue.",
  "primary_outcome": "Recover otherwise abandoned small-dollar carrier revenue.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 4,
  "evidence_hints": [
    {
      "signal": "20% of cash actually recovered",
      "source": "Freight Claim Recovery"
    },
    {
      "signal": "market pain/competitors already researched",
      "source": "existing V4-11"
    },
    {
      "signal": "compensated debt recovery for another can cross collection-agency boundary",
      "source": "Illinois collection boundary"
    },
    {
      "signal": "evidence packet/payment-status workflow can be an offer wedge without separate recovery niche",
      "source": "FC2-01 billing"
    }
  ],
  "rejection_reason": "MERGE_BILLING_AND_LEGAL_RISK: keep evidence-pack/accessorial documentation inside FC2-01 billing; do not create separate contingency debt-recovery business without licensing analysis.",
  "metadata": {
    "fast_cash": "offer_wedge",
    "merge_niche_key": "FC2-01"
  },
  "first_seen_at": "2026-10-04 01:52:00.328993+00",
  "last_seen_at": "2026-10-04 01:52:00.328993+00"
}
```

### ELD/HOS log audit
```json
{
  "id": "c0ea621f-22b9-4305-976a-a0deaf75c161",
  "fingerprint": "85551d1c72218b43efac4bcd795b39bd87cf6d1dbbb0d6f2c5a678839c4a5dd0",
  "candidate_key": "FC2B-RAW-05",
  "analysis_level": "niche",
  "raw_name": "ELD/HOS log audit",
  "normalized_name": "Managed ELD/HOS log auditing for small fleets",
  "buyer_segment": "Small fleets with HOS exposure",
  "core_job": "Review logs, flag violations/trends, coach corrections and prepare audit evidence.",
  "primary_outcome": "Reduce HOS violations and audit risk.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 4,
  "evidence_hints": [
    {
      "signal": "$49/driver/month sample log review",
      "source": "Lili Safety"
    },
    {
      "signal": "$20-$50/driver/month log audit tiers",
      "source": "DOT Doctor"
    },
    {
      "signal": "$8/audit or $49 base + $0.75/log",
      "source": "Waypoint True"
    },
    {
      "signal": "same buyer/compliance workflow",
      "source": "V5-03 DOT"
    }
  ],
  "rejection_reason": "MERGE_EXISTING_DOT: good paid add-on/wedge, but not a separate niche from V5-03 managed DOT compliance.",
  "metadata": {
    "fast_cash": "offer_wedge",
    "merge_niche_key": "V5-03"
  },
  "first_seen_at": "2026-10-04 01:52:00.328993+00",
  "last_seen_at": "2026-10-04 01:52:00.328993+00"
}
```

### IRP/UCR/MCS-150 filing concierge
```json
{
  "id": "bf430b3f-49e1-445a-b267-b925b38e6392",
  "fingerprint": "7c07abf2660f45efa85c13adcbd0d54c641603ce4be7d69227df732050577833",
  "candidate_key": "FC2B-RAW-07",
  "analysis_level": "niche",
  "raw_name": "IRP/UCR/MCS-150 filing concierge",
  "normalized_name": "Carrier registration and recurring filing concierge",
  "buyer_segment": "Illinois owner-operators/small fleets",
  "core_job": "Prepare/coordinate recurring registration filings and deadlines.",
  "primary_outcome": "Avoid missed registrations/renewals.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 4,
  "evidence_hints": [
    {
      "signal": "IRP renewals online for fleets <250; licensed remitter field exists",
      "source": "Illinois SOS"
    },
    {
      "signal": "MCS-150 $110-$399, UCR $45-$310, IFTA $30-$150 public market ranges",
      "source": "TenFour"
    },
    {
      "signal": "filings already fit managed DOT compliance",
      "source": "V5-03 DOT"
    }
  ],
  "rejection_reason": "MERGE_EXISTING_DOT: recurring filing admin is a DOT offer component; IRP remitter mechanics create additional boundary and standalone differentiation is weak.",
  "metadata": {
    "fast_cash": "offer_wedge",
    "merge_niche_key": "V5-03"
  },
  "first_seen_at": "2026-10-04 01:52:00.328993+00",
  "last_seen_at": "2026-10-04 01:52:00.328993+00"
}
```

### Toll cost management
```json
{
  "id": "5876a050-2dea-4e6e-8b6e-e2b18238aa5d",
  "fingerprint": "abfc127e03b634093db14a98eaddfca1509b4941e30727b872264751d6b9131e",
  "candidate_key": "FC2B-RAW-08",
  "analysis_level": "niche",
  "raw_name": "Toll cost management",
  "normalized_name": "Small-fleet toll route/cost management",
  "buyer_segment": "Small fleets operating toll-heavy lanes",
  "core_job": "Estimate, reconcile and optimize toll spend by route/truck.",
  "primary_outcome": "Reduce unexpected toll cost and improve load profitability.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 2,
  "evidence_hints": [
    {
      "signal": "API $49/month for 50k calls",
      "source": "DrayToll"
    },
    {
      "signal": "toll management bundled into $10-$15/truck/month fleet software",
      "source": "HaulNex"
    }
  ],
  "rejection_reason": "LOW_ARPU_SOFTWARE_COMMODITY: tooling is cheap and bundled; no strong human-service WTP or structural gap evidenced.",
  "metadata": {
    "fast_cash": "reject"
  },
  "first_seen_at": "2026-10-04 01:52:00.328993+00",
  "last_seen_at": "2026-10-04 01:52:00.328993+00"
}
```

### CSA/SMS monitoring
```json
{
  "id": "4da46890-3277-468a-815c-7a514af55d32",
  "fingerprint": "fbbd15537895592641c41f79196c301b221bac64f57237074f55e39ca4e6e2f2",
  "candidate_key": "FC2B-RAW-09",
  "analysis_level": "niche",
  "raw_name": "CSA/SMS monitoring",
  "normalized_name": "Carrier safety-score monitoring and alerts",
  "buyer_segment": "Small carriers monitoring FMCSA safety performance",
  "core_job": "Monitor public SMS/authority/safety changes and surface issues.",
  "primary_outcome": "Catch safety issues before renewals/interventions.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 4,
  "evidence_hints": [
    {
      "signal": "public/current SMS data",
      "source": "FMCSA CSA"
    },
    {
      "signal": "$49/month up to 100 carriers for agency monitoring",
      "source": "CSA Sentry"
    },
    {
      "signal": "monthly SMS BASIC reporting included in managed safety plans",
      "source": "AIST Safety"
    },
    {
      "signal": "same compliance buyer/job",
      "source": "V5-03 DOT"
    }
  ],
  "rejection_reason": "MERGE_EXISTING_DOT: public-data monitoring is a feature/add-on inside managed DOT, not a separate fast-cash niche.",
  "metadata": {
    "fast_cash": "offer_wedge",
    "merge_niche_key": "V5-03"
  },
  "first_seen_at": "2026-10-04 01:52:00.328993+00",
  "last_seen_at": "2026-10-04 01:52:00.328993+00"
}
```

### Cargo/freight claims recovery
```json
{
  "id": "02d5deb6-d5fb-4fc5-a120-79e27a8a916d",
  "fingerprint": "1f1f76972b8d0221aa50690b0a537b2ec575cf499e734d0257698dbaaa7a4621",
  "candidate_key": "FC2B-RAW-10",
  "analysis_level": "niche",
  "raw_name": "Cargo/freight claims recovery",
  "normalized_name": "Freight claims recovery administration",
  "buyer_segment": "Shippers/importers/freight buyers with recurring loss/damage claims",
  "core_job": "Prepare/file/follow freight claims and charge contingency on recovered dollars.",
  "primary_outcome": "Recover cargo/freight claim leakage.",
  "suggested_model_key": null,
  "suggested_market_key": null,
  "status": "rejected",
  "source_count": 4,
  "evidence_hints": [
    {
      "signal": "20% contingency on recovered funds",
      "source": "Ladingly"
    },
    {
      "signal": "10% recovery fee, $500 minimum",
      "source": "FreightBid360"
    },
    {
      "signal": "contingency-based no recovery/no fee",
      "source": "Nasratic"
    },
    {
      "signal": "our gate-ready asset reaches carriers, not recurring shipper claims buyers",
      "source": "edge audit"
    }
  ],
  "rejection_reason": "ENTRANT_EDGE_HARD_GATE_FAILED: current gate-ready distribution is small carriers/drivers, while cargo-claims recovery buyer is primarily shipper/freight buyer; no owned channel evidenced.",
  "metadata": {
    "fast_cash": "reject_edge_gate"
  },
  "first_seen_at": "2026-10-04 01:52:00.328993+00",
  "last_seen_at": "2026-10-04 01:52:00.328993+00"
}
```

## catalog_opportunities - все записи

### Fixture Opportunity
```json
{
  "id": "a442b222-c210-4a55-ac73-3719a403e737",
  "opportunity_key": "fixture_opportunity",
  "niche_id": "1840bcd6-319f-4a2f-91c2-388da2ce4a25",
  "business_model_id": "1c4cc94d-48f1-4753-983e-17e8531ad01d",
  "name": "Fixture Opportunity",
  "thesis": "Regression-only opportunity used to test tenant isolation and exact revision acceptance.",
  "customer_value": "fixture",
  "acquisition_hypothesis": "fixture",
  "scale_hypothesis": "fixture",
  "catalog_status": "researched",
  "source_kind": "curated",
  "global_eligible": false,
  "metadata": {
    "fixture": true,
    "exclude_from_discovery": true
  },
  "created_at": "2026-09-25 05:00:54.392543+00",
  "updated_at": "2026-09-25 05:00:54.392543+00"
}
```

### Fixture Licensed Opportunity
```json
{
  "id": "ba717581-9470-4ae1-9b0a-e39747247095",
  "opportunity_key": "fixture_licensed_opportunity",
  "niche_id": "1840bcd6-319f-4a2f-91c2-388da2ce4a25",
  "business_model_id": "77ad6142-b95e-4561-9318-f6916b38ea2a",
  "name": "Fixture Licensed Opportunity",
  "thesis": "Regression-only licensed/high-touch comparator.",
  "customer_value": "fixture",
  "acquisition_hypothesis": "fixture",
  "scale_hypothesis": "fixture",
  "catalog_status": "researched",
  "source_kind": "curated",
  "global_eligible": false,
  "metadata": {
    "fixture": true,
    "exclude_from_discovery": true
  },
  "created_at": "2026-09-25 05:03:12.762074+00",
  "updated_at": "2026-09-25 05:03:12.762074+00"
}
```

### Digital home inventory organizer
```json
{
  "id": "777118d4-c16b-40a4-9c85-70a96ab85b77",
  "opportunity_key": "opp-a5c1c263bf983d28a29d",
  "niche_id": "2f728159-dc30-43c6-8f3e-42486e30f590",
  "business_model_id": "1c4cc94d-48f1-4753-983e-17e8531ad01d",
  "name": "Digital home inventory organizer",
  "thesis": "A bounded digital-download business can package reusable home-inventory and move-record workflows for renters without inventory, licensing or recurring human service.",
  "customer_value": "Faster, more structured household documentation with reusable files.",
  "acquisition_hypothesis": "Search, marketplace and owned-site testing can measure intent without a high-touch sales process.",
  "scale_hypothesis": "Additional packs, formats and adjacent renter workflows can expand the catalog without proportional service labor.",
  "catalog_status": "testable",
  "source_kind": "discovery",
  "global_eligible": false,
  "metadata": {
    "fixture": true,
    "candidate_id": "95f17bc8-8723-46db-bf7b-b24c64091acf",
    "candidate_key": "alpha-clean-digital-inventory",
    "discovery_fingerprint": "a5c1c263bf983d28a29dd65c5c043940"
  },
  "created_at": "2026-09-25 06:23:48.466324+00",
  "updated_at": "2026-09-25 06:32:15.929214+00"
}
```

### Fixture thermal-label-printer pilot
```json
{
  "id": "da06df72-129f-4139-be4a-5e2741303274",
  "opportunity_key": "fixture_g180_thermal_label_printer_pilot",
  "niche_id": "e4dcc31a-5aa5-474f-b137-c65807d1f054",
  "business_model_id": "abec7b74-60be-4147-bbda-7105a969e8a4",
  "name": "Fixture thermal-label-printer pilot",
  "thesis": "Fixture-only opportunity for validating a thermal-label-printer package against exact permitted public evidence without production execution.",
  "customer_value": "Shippers can evaluate a dedicated 4-inch thermal label printer with exact product facts before any commercial action.",
  "acquisition_hypothesis": "Fixture harness only; no acquisition execution is authorized.",
  "scale_hypothesis": "Fixture harness only; no scaling conclusion is authorized.",
  "catalog_status": "researched",
  "source_kind": "curated",
  "global_eligible": false,
  "metadata": {
    "fixture": true,
    "g180_harness": true,
    "semantic_scope": "thermal-label-printer pilot / shipping-label workflow",
    "exclude_from_discovery": true,
    "g180_fixture_package_id": "real-evidence-package:thermal-label-printer-pilot-v1"
  },
  "created_at": "2026-09-30 08:30:07.338851+00",
  "updated_at": "2026-09-30 08:30:07.338851+00"
}
```

### Fixture insufficient-evidence opportunity
```json
{
  "id": "976fec4d-aa9d-4f0f-9d09-69aad03744d6",
  "opportunity_key": "fixture_g181_insufficient_evidence",
  "niche_id": "e17a0200-e4c1-4682-b051-cfef2eb2cd50",
  "business_model_id": "abec7b74-60be-4147-bbda-7105a969e8a4",
  "name": "Fixture insufficient-evidence opportunity",
  "thesis": "Fixture-only opportunity intentionally missing supporting evidence and economics to prove fail-closed decision behavior.",
  "customer_value": "No decision-ready customer value claim is verified.",
  "acquisition_hypothesis": "Unknown until supporting evidence exists.",
  "scale_hypothesis": "Unknown until supporting evidence exists.",
  "catalog_status": "researched",
  "source_kind": "curated",
  "global_eligible": false,
  "metadata": {
    "fixture": true,
    "g181_harness": true,
    "semantic_scope": "fail-closed decision path with missing evidence",
    "insufficient_evidence": true,
    "exclude_from_discovery": true,
    "g181_fixture_package_id": "insufficient-evidence-package:g181-v1"
  },
  "created_at": "2026-09-30 08:57:35.188849+00",
  "updated_at": "2026-09-30 08:57:35.188849+00"
}
```

## niche_dossiers - все записи

### ef049add-66b2-4878-bc30-b8baf5a5509a
```json
{
  "niche_id": "ef049add-66b2-4878-bc30-b8baf5a5509a",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US small government contractors, roughly 2–50 employees, especially founder-led service/construction/IT firms without a full capture/proposal department.",
  "painful_job": "Need to find qualified public-sector opportunities early enough, decide bid/no-bid quickly, and submit compliant proposals without consuming founder/SME capacity.",
  "economic_importance": "Public-sector contracts are high-value; missed qualified opportunities and founder/SME proposal hours can materially affect revenue.",
  "spend_wtp_evidence": [
    {
      "signal": "GovBidWire Premium $39/mo; Team $149/mo"
    },
    {
      "signal": "Enterprise bid-intelligence alternatives reportedly reach five-figure annual contracts"
    },
    {
      "signal": "Small contractors report substantial proposal-management labor"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "FY2025 federal small-business prime awards were about $179B; prime+subcontract total nearly $273B"
    },
    {
      "signal": "SAM.gov exposes current opportunities and public data/API access"
    }
  ],
  "acquisition_paths": [
    "SEO around bid/RFP discovery",
    "APEX/consultant partnerships",
    "industry associations",
    "govcon communities",
    "vertical outbound"
  ],
  "competitors_substitutes": [
    "SAM.gov/free public portals",
    "GovBidWire",
    "GovWin/Deltek",
    "consultants/proposal shops",
    "manual portal monitoring"
  ],
  "defensibility_paths": [
    "vertical-specific award/history dataset",
    "buyer-specific relevance models",
    "accumulated proposal evidence library",
    "partner distribution",
    "workflow data improving bid/no-bid"
  ],
  "business_model_options": [
    "subscription intelligence/workflow",
    "managed capture/proposal operations",
    "data/API licensing",
    "performance-linked advisory where lawful"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "needs segment-specific CAC and contribution modeling"
  },
  "two_person_feasibility": {
    "assessment": "plausible only if launch scope is narrow; deep screen must identify which tasks can be automated and which require specialist labor",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist contractor/ops support after repeatable demand",
    "phase_3": "channel partnerships and dedicated sales/support if ACV supports it"
  },
  "risks": [
    "Need quantified SMB count by active bidding frequency",
    "Need win-rate/CAC benchmarks by vertical",
    "Need validate willingness to switch from free SAM/state portals",
    "Need determine which state/local feeds can be obtained legally/reliably"
  ],
  "offer_hypotheses": [
    "matched opportunity intelligence",
    "bid/no-bid decision workspace",
    "proposal evidence/content library",
    "managed proposal compliance review"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "entrant_edge": {
    "status": "not_evidenced",
    "evidence_refs": [
      "turn230108search3",
      "turn230108search0"
    ],
    "rejection_reason": "HigherGov + free SAM already cover the proposed core workflow."
  }
}
```

### 9b1c6bd9-b470-494f-849d-41b68916b757
```json
{
  "niche_id": "9b1c6bd9-b470-494f-849d-41b68916b757",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US Medicare-certified home health agencies, especially small/midsize operators with roughly <=75 staff or a few locations.",
  "painful_job": "Continuous regulatory compliance, staff credential expirations, documentation and survey readiness create recurring owner/compliance-director workload with material reimbursement/licensure risk.",
  "economic_importance": "Survey/compliance failures can threaten reimbursement, accreditation and operations; requirements and credential expirations are recurring.",
  "spend_wtp_evidence": [
    {
      "signal": "Current vertical tools publish approximately $149-$399/month for small/mid agencies"
    },
    {
      "signal": "Compliance is ongoing rather than one-time"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "CMS current Home Health Care Agencies dataset contains 12,460 registered Medicare agencies"
    },
    {
      "signal": "CMS maintains continuous home-health quality reporting requirements"
    }
  ],
  "acquisition_paths": [
    "home-health associations",
    "accreditation consultants",
    "billing/EMR partners",
    "compliance SEO",
    "targeted outbound"
  ],
  "competitors_substitutes": [
    "manual binders/spreadsheets",
    "consultants",
    "Ordo-class compliance software",
    "home-health EMR compliance modules"
  ],
  "defensibility_paths": [
    "regulatory control map",
    "agency evidence history",
    "survey-readiness benchmarks",
    "accreditation consultant channel",
    "EMR integrations"
  ],
  "business_model_options": [
    "compliance SaaS",
    "managed survey-readiness service",
    "credential/training monitoring",
    "policy/evidence operations subscription"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "needs segment-specific CAC and contribution modeling"
  },
  "two_person_feasibility": {
    "assessment": "plausible only if launch scope is narrow; deep screen must identify which tasks can be automated and which require specialist labor",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist contractor/ops support after repeatable demand",
    "phase_3": "channel partnerships and dedicated sales/support if ACV supports it"
  },
  "risks": [
    "Need buyer interviews on current survey-prep spend",
    "Need map exact compliance liability and advisory boundaries",
    "Need compare integrations with common home-health EMRs",
    "Need quantify target agencies by staff/location size"
  ],
  "offer_hypotheses": [
    "survey-readiness dashboard",
    "staff credential/training tracker",
    "managed monthly compliance review",
    "audit/evidence packet service"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "entrant_edge": {
    "status": "not_evidenced",
    "evidence_refs": [
      "turn551661search0",
      "turn551661search10"
    ],
    "rejection_reason": "Ordo/SurveyReady already implement the exact home-health compliance OS wedge."
  }
}
```

### d36e51b7-1543-497d-87f0-cdaa2bdf37c6
```json
{
  "niche_id": "d36e51b7-1543-497d-87f0-cdaa2bdf37c6",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US small contractors/subcontractors performing Davis-Bacon or similar prevailing-wage public work, particularly firms without dedicated payroll-compliance staff.",
  "painful_job": "Covered work creates weekly payroll/compliance obligations; classification, fringe and multi-jurisdiction complexity can consume back-office time and create underpayment/audit risk.",
  "economic_importance": "Weekly prevailing-wage reporting is mandatory on covered work and errors can create back-pay, audit and contract risk, but basic form generation now has a free federal substitute.",
  "spend_wtp_evidence": [
    {
      "signal": "CertifiedPayrollPro publishes $49/$99/$249 monthly tiers plus per-report charges"
    },
    {
      "signal": "Certiwage publishes $29-$59/month positioning for small subcontractors"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "BLS Q1 2026: 597,918 private specialty-trade establishments is a broad upper bound; only a subset performs covered public work"
    },
    {
      "signal": "DOL confirms weekly certified payroll is required on DBRA-covered work"
    }
  ],
  "acquisition_paths": [
    "public-works contractor associations",
    "payroll/accounting partners",
    "APEX ecosystem",
    "construction CPAs",
    "search"
  ],
  "competitors_substitutes": [
    "DOL free WH-347 web generator",
    "payroll-provider exports",
    "CertifiedPayrollPro",
    "Certiwage",
    "legacy certified-payroll vendors",
    "manual spreadsheets"
  ],
  "defensibility_paths": [
    "multi-jurisdiction rule library",
    "payroll integrations",
    "historical classification/fringe exception data",
    "subcontractor network workflow",
    "audit evidence history"
  ],
  "business_model_options": [
    "prevailing-wage compliance SaaS",
    "managed certified-payroll review",
    "payroll integration/add-on",
    "subcontractor compliance service"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "needs segment-specific CAC, onboarding and contribution modeling"
  },
  "two_person_feasibility": {
    "assessment": "plausible only with a sharply bounded first workflow; deep screen must isolate high-value automation from specialist/manual exceptions",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + software/automation",
    "phase_2": "specialist ops or implementation contractor after repeatable demand",
    "phase_3": "channel partnerships and dedicated support/sales if ACV supports it"
  },
  "risks": [
    "Need target count of small contractors actually doing covered work",
    "Need measure multi-state/state-specific complexity beyond federal WH-347",
    "Need validate willingness to pay after DOL free generator",
    "Need assess payroll integration and compliance-liability requirements"
  ],
  "offer_hypotheses": [
    "multi-project certified payroll workspace",
    "fringe/classification anomaly review",
    "payroll-import compliance workflow",
    "managed weekly certified-payroll desk"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:05:06.256699+00",
  "entrant_edge": {}
}
```

### 16a4e673-969e-4a31-864e-810ebcc035f8
```json
{
  "niche_id": "16a4e673-969e-4a31-864e-810ebcc035f8",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US small custom manufacturers/job shops, especially CNC, fabrication and mixed-process shops with roughly 5–50 employees and meaningful RFQ volume.",
  "painful_job": "Quote turnaround and accuracy determine whether work is won profitably; estimators spend scarce senior labor pricing jobs that may never convert.",
  "economic_importance": "Slow quoting loses time-sensitive RFQs while inaccurate quoting destroys margin; senior estimator time is scarce and every RFQ has uncertain conversion.",
  "spend_wtp_evidence": [
    {
      "signal": "ManufactureQuote Starter NZ$149/mo, Professional NZ$269, Business NZ$399"
    },
    {
      "signal": "ManufacturingBase paid RFQ access starts at $200/month annual-billed equivalent and scales much higher"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "Census 2023: 284,452 US manufacturing employer establishments"
    },
    {
      "signal": "237,060 manufacturing establishments had fewer than 50 employees, broad upper-bound proxy for small/mid shops"
    }
  ],
  "acquisition_paths": [
    "manufacturing associations",
    "ERP/CAM/accounting partners",
    "machine-tool/service partners",
    "SEO around quoting/estimating",
    "vertical outbound"
  ],
  "competitors_substitutes": [
    "Excel/homegrown sheets",
    "ERP estimating modules",
    "Paperless Parts",
    "ProShop",
    "ManufactureQuote",
    "manual senior-estimator workflow"
  ],
  "defensibility_paths": [
    "shop-specific historical quote/job dataset",
    "costing-logic configuration",
    "ERP/CAM integrations",
    "win/loss feedback loop",
    "supplier/material-price data"
  ],
  "business_model_options": [
    "quoting/estimating SaaS",
    "implementation + workflow configuration",
    "RFQ triage copilot",
    "benchmark/data module"
  ],
  "customer_economics": {
    "model_status": "scenario only",
    "must_measure": "RFQ volume, estimator value, onboarding/integration cost and CAC",
    "software_anchor": "low hundreds/month through custom enterprise pricing"
  },
  "two_person_feasibility": {
    "assessment": "plausible only with a sharply bounded first workflow; deep screen must isolate high-value automation from specialist/manual exceptions",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + software/automation",
    "phase_2": "specialist ops or implementation contractor after repeatable demand",
    "phase_3": "channel partnerships and dedicated support/sales if ACV supports it"
  },
  "risks": [
    "Need segment count for custom/job-shop subset within manufacturing",
    "Need typical RFQ volume and estimator labor cost by shop type",
    "Need actual incumbent ACV and switching friction",
    "Need determine how much quoting accuracy can improve without deep CAM/ERP integration"
  ],
  "offer_hypotheses": [
    "RFQ inbox + triage workspace",
    "historical-similar-job quoting assistant",
    "configurable estimator workbench",
    "quote-to-job learning loop"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "entrant_edge": {
    "status": "not_evidenced",
    "evidence_refs": [
      "turn623117search12"
    ],
    "rejection_reason": "Paperless Parts already implements machine-shop RFQ/estimating with integrations; hypothetical data moat is not evidence."
  }
}
```

### ab66685e-a6d9-4403-8d80-88f3dae16881
```json
{
  "niche_id": "ab66685e-a6d9-4403-8d80-88f3dae16881",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US commercial specialty contractors and material suppliers with recurring receivables across multiple projects and enough project volume that lien/notice/waiver tracking no longer fits in spreadsheets.",
  "painful_job": "Payment delays, retainage and paperwork errors can strand working capital; missed preliminary-notice or lien deadlines can destroy leverage that helps secure payment.",
  "economic_importance": "Late payment and retainage tie up subcontractor working capital; missing statutory notice/lien deadlines can eliminate a powerful payment remedy and weaken collections leverage.",
  "spend_wtp_evidence": [
    {
      "signal": "Levelset currently charges $349 for a lien and $59/recipient for certain notices/warnings while waiver exchange can be free"
    },
    {
      "signal": "LienDone publishes $49/month for unlimited waiver workflows"
    },
    {
      "signal": "Current category products extend into AR/payment workflow and lien-rights management"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "BLS reports 597,918 private specialty-trade contractor establishments in Q1 2026 as a broad upper-bound buyer universe"
    },
    {
      "signal": "2026 Siteline survey of 492 construction finance/ops professionals found 56% of subcontractors missed a critical lien deadline in the prior two years"
    }
  ],
  "acquisition_paths": [
    "construction accountants",
    "trade associations",
    "ERP/accounting partners",
    "bonding/insurance partners",
    "construction finance communities",
    "vertical outbound"
  ],
  "competitors_substitutes": [
    "spreadsheets/calendar reminders",
    "construction attorneys",
    "Levelset",
    "LienDone",
    "GCPay/Siteline-class platforms",
    "manual waiver/notice services"
  ],
  "defensibility_paths": [
    "state/project payment-rights rules engine",
    "project/notice/lien deadline history",
    "AR/pay-app integrations",
    "payment-risk intelligence",
    "construction accountant/ERP distribution"
  ],
  "business_model_options": [
    "payment-rights/AR SaaS",
    "managed notice/lien/waiver operations",
    "collections-escalation workflow",
    "accounting/ERP embedded add-on"
  ],
  "customer_economics": {
    "status": "scenario only",
    "key_issue": "current integrated incumbents + state/legal complexity; must prove narrower wedge and labor economics"
  },
  "two_person_feasibility": {
    "assessment": "possible only with narrow initial segment and bounded exception workflow; deep screen required before finalist status",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist ops/compliance staff where recovery exceptions require humans",
    "phase_3": "partner distribution and dedicated account operations if ACV/LTV supports it"
  },
  "risks": [
    "Need state-by-state legal/compliance scope and unauthorized-practice-of-law boundaries",
    "Need segment annual receivables/retainage and missed-rights incidence by contractor size",
    "Need quantify current incumbent ACV and partner CAC",
    "Need determine whether payment-rights workflow can be productized without attorney-heavy exceptions"
  ],
  "offer_hypotheses": [
    "deadline/payment-rights portfolio dashboard",
    "managed preliminary-notice and waiver desk",
    "AR-to-lien escalation workflow",
    "retainage/payment-risk monitoring"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:08:22.557586+00",
  "entrant_edge": {}
}
```

### 6fb1d9ab-bf51-421d-b9f4-345538c5a521
```json
{
  "niche_id": "6fb1d9ab-bf51-421d-b9f4-345538c5a521",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US commercial and light-industrial organizations spending materially on utilities, especially multi-site portfolios and facilities with complex meters, tariffs, demand charges or tax treatment.",
  "painful_job": "Utility billing errors and misapplied tariffs create direct recoverable leakage; rising utility spend also raises the value of continuous validation and rate optimization.",
  "economic_importance": "Utility spend is a large recurring operating expense; billing/tariff errors can create direct cash recoveries and ongoing avoidable cost.",
  "spend_wtp_evidence": [
    {
      "signal": "Current contingency utility-audit market commonly advertises zero upfront and roughly 25%-50% of verified recoveries/savings"
    },
    {
      "signal": "EnergyCAP utility-management software pricing starts around $4,000/year according to current G2 pricing"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "EIA reports $200.316B of 2025 U.S. commercial-sector electricity revenue alone, before commercial gas/water spend"
    },
    {
      "signal": "Target is the much smaller multi-site/complex-billing subset"
    }
  ],
  "acquisition_paths": [
    "facility-management partners",
    "commercial property managers",
    "CPAs",
    "energy consultants/brokers where permitted",
    "multi-site operator outbound"
  ],
  "competitors_substitutes": [
    "manual facility/accounting review",
    "utility audit consultants",
    "energy brokers",
    "EnergyCAP-class utility management",
    "do nothing"
  ],
  "defensibility_paths": [
    "multi-utility tariff/rate library",
    "historical bill/meter anomaly data",
    "verified recovery playbooks",
    "multi-site benchmark dataset",
    "partner distribution"
  ],
  "business_model_options": [
    "contingency recovery audit",
    "recurring utility-monitoring subscription",
    "managed tariff/rate optimization",
    "partner/consulting white-label"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "requires segment-specific contribution/CAC and labor model"
  },
  "two_person_feasibility": {
    "assessment": "possible only with narrow initial segment and bounded exception workflow; deep screen required before finalist status",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist ops/compliance staff where recovery exceptions require humans",
    "phase_3": "partner distribution and dedicated account operations if ACV/LTV supports it"
  },
  "risks": [
    "Need independent incidence data on commercial billing errors/recoveries",
    "Need state/utility restrictions on representing customers and sharing savings",
    "Need quantify acquisition path to businesses spending >$50k utilities/year",
    "Need separate repeatable software monitoring from bespoke tariff consulting"
  ],
  "offer_hypotheses": [
    "no-upfront commercial bill audit",
    "continuous invoice/tariff validator",
    "multi-site utility anomaly dashboard",
    "managed recovery + monitoring program"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "entrant_edge": {
    "status": "not_evidenced",
    "evidence_refs": [
      "turn179082search3",
      "turn179082search0",
      "turn179082search12"
    ],
    "rejection_reason": "TrueMeter/Utility Audit/MeterID already cover the proposed multi-site utility recovery/monitoring wedge."
  }
}
```

### 936c5602-d948-4618-9534-e4e30dde57a4
```json
{
  "niche_id": "936c5602-d948-4618-9534-e4e30dde57a4",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US ecommerce brands, 3PLs and other mid-market shippers with enough parcel volume that manual carrier invoice review is uneconomic.",
  "painful_job": "Carrier billing/service errors and missed guarantees create direct recoverable dollars, while surcharge/rate analytics can affect future shipping cost.",
  "economic_importance": "Carrier invoice/service errors create direct leakage that can be recovered with little operational disruption, but the base audit function is mature and price-competitive.",
  "spend_wtp_evidence": [
    {
      "signal": "AuditShipment publishes 50% of recovered refunds up to $500k annual shipping spend and 40% for $500k-$1M"
    },
    {
      "signal": "Shipware offers gainshare/no-upfront recovery and claims 1%-9% of invoice value may be recoverable"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "Pitney Bowes reports 23.1B U.S. parcels in 2025, up 3.3% YoY"
    },
    {
      "signal": "Target is the much smaller subset of mid/high-volume commercial shippers"
    }
  ],
  "acquisition_paths": [
    "3PL/fulfillment partners",
    "ecommerce agencies",
    "accounting/CFO partners",
    "Shopify ecosystem",
    "direct shipper outreach"
  ],
  "competitors_substitutes": [
    "carrier self-service claims",
    "Parcel Recovery",
    "AuditShipment",
    "Shipware",
    "parcel consultants",
    "3PL/TMS analytics"
  ],
  "defensibility_paths": [
    "multi-carrier contract/rate dataset",
    "shipper spend benchmarks",
    "claims outcome history",
    "embedded 3PL/fulfillment integrations",
    "contract negotiation intelligence"
  ],
  "business_model_options": [
    "contingency refund audit",
    "flat-fee spend analytics",
    "carrier contract optimization",
    "3PL/fulfillment embedded audit"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "requires segment-specific contribution/CAC and labor model"
  },
  "two_person_feasibility": {
    "assessment": "possible only with narrow initial segment and bounded exception workflow; deep screen required before finalist status",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist ops/compliance staff where recovery exceptions require humans",
    "phase_3": "partner distribution and dedicated account operations if ACV/LTV supports it"
  },
  "risks": [
    "Need count of addressable shippers by annual parcel spend",
    "Need validate carrier guarantee/refund policy stability and API/data access",
    "Need CAC/channel economics in a mature contingency market",
    "Need identify non-commodity layer strong enough to create retention and defensibility"
  ],
  "offer_hypotheses": [
    "carrier invoice audit/gainshare",
    "refund + surcharge leakage dashboard",
    "contract-rate compliance monitor",
    "carrier-negotiation analytics"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:05:06.256699+00",
  "entrant_edge": {}
}
```

### 6db874b6-b4d1-4090-8153-649d71c9bb63
```json
{
  "niche_id": "6db874b6-b4d1-4090-8153-649d71c9bb63",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US specialty contractors/subcontractors, especially 5–50 employee commercial electrical, mechanical, plumbing, concrete, civil and similar trades.",
  "painful_job": "Extra work must be documented, priced, approved and billed; weak field evidence or late processing turns performed work into disputed/uncollected revenue.",
  "economic_importance": "Performed extra work can become disputed or unpaid revenue; change-order delay directly affects subcontractor cash flow and margin.",
  "spend_wtp_evidence": [
    {
      "signal": "Scope Snap PRO publishes $49/month"
    },
    {
      "signal": "REQ Suite publishes $150/month for commercial subcontractors around $1M-$20M revenue"
    },
    {
      "signal": "SubTrack publishes from $45/user/month for T&M/LEM subcontractor workflow"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "BLS Q1 2026: 597,918 private specialty-trade contractor establishments"
    },
    {
      "signal": "Census 2023 employer-establishment count for NAICS 238 was 521,315"
    }
  ],
  "acquisition_paths": [
    "trade associations",
    "construction accounting partners",
    "field-service ecosystems",
    "GC/sub networks",
    "SEO and outbound"
  ],
  "competitors_substitutes": [
    "paper/PDF/T&M tickets",
    "Excel logs",
    "Procore/GC suites",
    "Clearstory",
    "Scope Snap",
    "REQ Suite",
    "SubTrack",
    "TrakSlip"
  ],
  "defensibility_paths": [
    "field-to-office event/evidence history",
    "customer/GC approval behavior data",
    "rate-sheet and scope knowledge",
    "accounting/pay-app integrations",
    "recovered-revenue analytics"
  ],
  "business_model_options": [
    "revenue-capture SaaS",
    "managed change-order/T&M documentation desk",
    "recovery/aging service",
    "accounting/ERP add-on"
  ],
  "customer_economics": {
    "model_status": "scenario only",
    "must_measure": "annual at-risk dollars/account, recovered-revenue lift, onboarding/support and CAC",
    "software_anchor": "$45-$150/mo current point tools"
  },
  "two_person_feasibility": {
    "assessment": "plausible only with a sharply bounded first workflow; deep screen must isolate high-value automation from specialist/manual exceptions",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + software/automation",
    "phase_2": "specialist ops or implementation contractor after repeatable demand",
    "phase_3": "channel partnerships and dedicated support/sales if ACV supports it"
  },
  "risks": [
    "Need quantify average annual at-risk change-order dollars by target contractor size",
    "Need determine incumbent penetration and integration expectations",
    "Need measure field adoption/support burden",
    "Need separate actual recovered-revenue effect from vendor marketing claims"
  ],
  "offer_hypotheses": [
    "mobile T&M/extra-work evidence capture",
    "change-order aging and recovery dashboard",
    "field-to-pay-app workflow",
    "managed documentation/recovery desk"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:08:22.557586+00",
  "entrant_edge": {}
}
```

### 5791b304-7281-4152-9529-b7123ae077fd
```json
{
  "niche_id": "5791b304-7281-4152-9529-b7123ae077fd",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US owner-operators and small for-hire truckload fleets, especially 1–20 trucks using brokers/spot freight and lacking a dedicated billing/recovery team.",
  "painful_job": "Waiting and other accessorial events create earned but frequently uncollected revenue; each claim is small enough that manual chasing often loses economically.",
  "economic_importance": "Detention creates direct fleet cost and lost productivity; much earned detention/accessorial revenue is not collected because documentation and chasing are uneconomic at small claim sizes.",
  "spend_wtp_evidence": [
    {
      "signal": "ATRI found 94.5% of fleets charge detention but fewer than half of invoices are paid"
    },
    {
      "signal": "Hauliner publishes $15.99/mo solo and $49-$349/mo fleet plans"
    },
    {
      "signal": "Current owner-operator discussion describes 10% contingency to a dispatcher for recovered detention"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "Census 2023: 60,137 long-distance truckload employer establishments; 55,035 had fewer than 20 employees"
    },
    {
      "signal": "ATRI estimated $3.6B direct expenses and $11.5B lost productivity from detention industry-wide in 2023"
    }
  ],
  "acquisition_paths": [
    "ELD partners",
    "factoring companies",
    "dispatch services",
    "carrier communities",
    "truck service/insurance ecosystems"
  ],
  "competitors_substitutes": [
    "manual dispatch/billing follow-up",
    "ELD timestamps + email",
    "Hauliner",
    "factoring/dispatch admin",
    "do nothing/eat the claim"
  ],
  "defensibility_paths": [
    "broker-specific submission-rule knowledge",
    "ELD/GPS evidence integrations",
    "claim outcome history",
    "factoring/dispatch distribution",
    "recovery operations playbooks"
  ],
  "business_model_options": [
    "detention/accessorial SaaS",
    "contingency recovery service",
    "dispatch/factoring white-label tool",
    "facility/broker performance intelligence"
  ],
  "customer_economics": {
    "model_status": "scenario only",
    "must_measure": "recoverable dollars/fleet and labor/paid claim",
    "hybrid_recovery": "10%-20% of recovered cash hypothesis",
    "software_anchor": "$15.99-$349/mo current competitor"
  },
  "two_person_feasibility": {
    "assessment": "plausible only with a sharply bounded first workflow; deep screen must isolate high-value automation from specialist/manual exceptions",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + software/automation",
    "phase_2": "specialist ops or implementation contractor after repeatable demand",
    "phase_3": "channel partnerships and dedicated support/sales if ACV supports it"
  },
  "risks": [
    "Need validate what share of unpaid detention is contractually recoverable",
    "Need broker-by-broker submission rule data and legal collection boundaries",
    "Need quantify recoverable dollars for 1–20 truck fleets specifically",
    "Need model ELD integration coverage and contingency-service labor"
  ],
  "offer_hypotheses": [
    "automatic detention evidence packet",
    "broker-rule claim submitter/follow-up queue",
    "contingency detention recovery service",
    "fleet accessorial leakage dashboard"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:08:22.557586+00",
  "entrant_edge": {}
}
```

### 334af3f0-184f-4d90-832b-b9ada09ea76a
```json
{
  "niche_id": "334af3f0-184f-4d90-832b-b9ada09ea76a",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US motor carriers and DOT-regulated service fleets with about 2–25 vehicles and no dedicated compliance department.",
  "painful_job": "Recurring expirations, driver qualification records, audit readiness, insurance/compliance requirements and the cost of missed deadlines or out-of-service events.",
  "economic_importance": "Missed compliance deadlines can create fines, out-of-service time, audit exposure and insurance problems; workload recurs continuously.",
  "spend_wtp_evidence": [
    {
      "signal": "Dotra publishes $149.99/mo for 1-9 vehicles and $249.99/mo for 10-24"
    },
    {
      "signal": "DotFleet publishes $30/driver/month managed DQ maintenance plus setup"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "FMCSA 2025 traffic-enforcement activity includes >202k inspections/enforcements for 1-6 power-unit carriers and >87k for 7-20 power-unit carriers"
    },
    {
      "signal": "Direct competitors explicitly price 1-24 vehicle fleets"
    }
  ],
  "acquisition_paths": [
    "insurance and compliance partners",
    "truck repair/service ecosystems",
    "owner-operator communities",
    "SEO",
    "targeted fleet outreach"
  ],
  "competitors_substitutes": [
    "spreadsheets/calendar reminders",
    "Dotra",
    "DotFleet",
    "compliance consultants",
    "larger fleet-management suites"
  ],
  "defensibility_paths": [
    "fleet-specific compliance history",
    "document completeness graph",
    "partner distribution through brokers/service centers",
    "human exception playbooks"
  ],
  "business_model_options": [
    "compliance SaaS subscription",
    "managed compliance desk",
    "one-time audit/remediation",
    "broker/insurance referral partnerships"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "needs segment-specific CAC and contribution modeling"
  },
  "two_person_feasibility": {
    "assessment": "plausible only if launch scope is narrow; deep screen must identify which tasks can be automated and which require specialist labor",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist contractor/ops support after repeatable demand",
    "phase_3": "channel partnerships and dedicated sales/support if ACV supports it"
  },
  "risks": [
    "Need exact count of active 2–25 vehicle target fleets",
    "Need churn and willingness-to-pay by 2–6 vs 7–25 fleets",
    "Need map legal boundary between software reminders and regulated compliance advice",
    "Need quantify support burden for managed remediation"
  ],
  "offer_hypotheses": [
    "deadline/document compliance workspace",
    "managed DQ-file maintenance",
    "new-entrant/audit readiness package",
    "renewal/remediation concierge"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:09:34.871372+00",
  "entrant_edge": {}
}
```

### c140835e-90a0-48c5-97eb-b2e0c96e6e9f
```json
{
  "niche_id": "c140835e-90a0-48c5-97eb-b2e0c96e6e9f",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US solo and small-group healthcare practices adding providers, opening locations or expanding payer panels.",
  "painful_job": "A provider cannot reliably bill in-network until payer credentialing/enrollment closes; applications, CAQH upkeep, revalidation and payer follow-up are recurring administrative work tied directly to revenue.",
  "economic_importance": "Credentialing delay can prevent or delay in-network billing, directly tying administrative throughput to clinician revenue.",
  "spend_wtp_evidence": [
    {
      "signal": "Current services commonly publish/quote roughly $100-$300+ per provider-payer application"
    },
    {
      "signal": "Full initial panels commonly cluster around roughly $1,500-$3,500 per provider, with recurring maintenance"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "CMS shows ~1.52M Medicare providers by specialty as a broad provider universe"
    },
    {
      "signal": "Credentialing software category has dozens of active products/services, indicating established spend"
    }
  ],
  "acquisition_paths": [
    "medical billing/RCM firms",
    "practice-launch consultants",
    "specialty associations",
    "SEO",
    "accountant/legal partners"
  ],
  "competitors_substitutes": [
    "DIY CAQH/payer portals",
    "credentialing freelancers/services",
    "billing companies",
    "credentialing platforms such as symplr/Medallion-class tools"
  ],
  "defensibility_paths": [
    "payer workflow knowledge base",
    "provider reusable data layer",
    "status/history data",
    "RCM white-label channel",
    "specialist exception operations"
  ],
  "business_model_options": [
    "managed credentialing",
    "hybrid workflow software + specialist exceptions",
    "recurring maintenance subscription",
    "white-label service for RCM/billing firms"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "needs segment-specific CAC and contribution modeling"
  },
  "two_person_feasibility": {
    "assessment": "plausible only if launch scope is narrow; deep screen must identify which tasks can be automated and which require specialist labor",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist contractor/ops support after repeatable demand",
    "phase_3": "channel partnerships and dedicated sales/support if ACV supports it"
  },
  "risks": [
    "Need validate cycle-time improvement we can realistically influence",
    "Need specialty/state segmentation for payer complexity",
    "Need HIPAA/security/legal review for stored provider data",
    "Need quantify acquisition cost through RCM/billing partners"
  ],
  "offer_hypotheses": [
    "practice-launch credentialing package",
    "ongoing CAQH/recredentialing maintenance",
    "payer-expansion project",
    "white-label credentialing operations for RCM firms"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:09:34.871372+00",
  "entrant_edge": {}
}
```

### b535be1b-4255-4ea3-be1f-8cd3932fb53b
```json
{
  "niche_id": "b535be1b-4255-4ea3-be1f-8cd3932fb53b",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US independent dental practices and small dental groups with meaningful insurance volume but without centralized enterprise revenue-cycle operations.",
  "painful_job": "Before visits and treatment plans, staff repeatedly verify eligibility and benefit details across inconsistent payer portals; the work is high-frequency, labor-intensive and directly affects collections and patient experience.",
  "economic_importance": "Benefit verification is high-frequency front-office labor tied to patient estimates, collections and scheduling; industry spend is measured in billions.",
  "spend_wtp_evidence": [
    {
      "signal": "Published full-benefit verification pricing commonly clusters around $5-$9.95 per patient, often with monthly minimums"
    },
    {
      "signal": "ADA/CAQH reported $2.1B in dental eligibility/benefit verification spending"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "ADA reports 135,665 US dental-practice establishments"
    },
    {
      "signal": "Only 16% of dentists were DSO-affiliated as of 2024, leaving a large independent/small-group base"
    }
  ],
  "acquisition_paths": [
    "dental consultants",
    "practice-management integrations",
    "RCM partners",
    "dental associations",
    "SEO"
  ],
  "competitors_substitutes": [
    "front-desk manual portals/calls",
    "outsourced verification services",
    "RCM firms",
    "dental automation vendors"
  ],
  "defensibility_paths": [
    "payer-specific verification knowledge",
    "practice integrations",
    "exception-quality data",
    "RCM/dental consultant distribution",
    "hybrid QA operations"
  ],
  "business_model_options": [
    "per-verification managed service",
    "monthly verification subscription",
    "workflow/API software",
    "broader dental revenue-ops service"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "needs segment-specific CAC and contribution modeling"
  },
  "two_person_feasibility": {
    "assessment": "plausible only if launch scope is narrow; deep screen must identify which tasks can be automated and which require specialist labor",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist contractor/ops support after repeatable demand",
    "phase_3": "channel partnerships and dedicated sales/support if ACV supports it"
  },
  "risks": [
    "Need payer-by-payer automation coverage and failure rates",
    "Need HIPAA/data security scope",
    "Need determine labor economics for exception handling",
    "Need measure willingness to switch from existing outsourced verification vendors"
  ],
  "offer_hypotheses": [
    "next-day full-benefit verification service",
    "daily verification queue subscription",
    "practice-management-integrated eligibility workflow",
    "managed front-office insurance ops"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:09:34.871372+00",
  "entrant_edge": {}
}
```

### 0f298acf-316d-43ac-a7b1-6dbd89d3fc1a
```json
{
  "niche_id": "0f298acf-316d-43ac-a7b1-6dbd89d3fc1a",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US ecommerce merchants with economic/physical nexus in several states, typically beyond DIY spreadsheets but below enterprise tax-department scale.",
  "painful_job": "Multi-state nexus, registration, filing cadence and changing state rules create recurring compliance work; mistakes create penalties while existing platforms can become expensive as states/transactions grow.",
  "economic_importance": "Nexus/filing mistakes create penalties and cleanup costs while multi-state compliance is recurring and grows with merchant scale.",
  "spend_wtp_evidence": [
    {
      "signal": "2026 comparison data puts representative SMB multi-state sales-tax compliance in the low-thousands to >$20k/year depending on provider/profile"
    },
    {
      "signal": "Merchants report paying recurring software/filing fees once nexus expands"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "US retail ecommerce sales were $340.2B in Q2 2026, 17.1% of retail sales"
    },
    {
      "signal": "Target is the smaller subset crossing multi-state nexus"
    }
  ],
  "acquisition_paths": [
    "ecommerce CPAs/bookkeepers",
    "Shopify agencies/ecosystem",
    "tax communities",
    "SEO",
    "commerce-platform partners"
  ],
  "competitors_substitutes": [
    "DIY spreadsheets/state portals",
    "TaxJar",
    "Avalara",
    "TaxCloud",
    "Kintsugi/Numeral/Zamp-class platforms",
    "CPA-managed filing"
  ],
  "defensibility_paths": [
    "merchant transaction/nexus history",
    "accountant partner distribution",
    "state workflow playbooks",
    "exception-service layer",
    "verticalized merchant segmentation"
  ],
  "business_model_options": [
    "nexus/filing workflow SaaS",
    "managed registration/filing service",
    "CPA white-label platform",
    "subscription + per-filing hybrid"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "needs segment-specific CAC and contribution modeling"
  },
  "two_person_feasibility": {
    "assessment": "plausible only if launch scope is narrow; deep screen must identify which tasks can be automated and which require specialist labor",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist contractor/ops support after repeatable demand",
    "phase_3": "channel partnerships and dedicated sales/support if ACV supports it"
  },
  "risks": [
    "Need define precise merchant revenue/state-count band with unmet need",
    "Need tax-practice/legal boundary and filing licenses/authorization requirements",
    "Need model filing labor and state fees",
    "Need determine whether partner distribution can beat incumbent CAC"
  ],
  "offer_hypotheses": [
    "nexus exposure monitor",
    "managed registrations",
    "filing calendar + evidence workspace",
    "CPA white-label multistate compliance operations"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:09:34.871372+00",
  "entrant_edge": {}
}
```

### 6446431d-ac46-41d7-9601-8ef19ae8f5e5
```json
{
  "niche_id": "6446431d-ac46-41d7-9601-8ef19ae8f5e5",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US general contractors, property managers and facility operators managing roughly 25–500 active subcontractors/vendors without an enterprise compliance team.",
  "painful_job": "Vendor onboarding and continuous proof-of-insurance/license/tax-document compliance; missing or expired documents create audit, insurance and project risk.",
  "economic_importance": "Expired/missing vendor documents create insurance, audit and project-delay risk; compliance chasing recurs with every vendor and renewal.",
  "spend_wtp_evidence": [
    {
      "signal": "Multiple current SMB COI tools publish roughly $49-$499/month"
    },
    {
      "signal": "Managed COI programs can cost thousands/year depending on vendor count"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "BLS reports ~953,703 private construction establishments in Q1 2026"
    },
    {
      "signal": "Multiple COI vendors target small businesses and small GCs/property managers"
    }
  ],
  "acquisition_paths": [
    "insurance brokers",
    "construction/property associations",
    "accounting partners",
    "SEO",
    "vertical outbound"
  ],
  "competitors_substitutes": [
    "spreadsheets/email",
    "VendorCover",
    "COI Dash",
    "Certificial/myCOI-style platforms",
    "managed compliance services"
  ],
  "defensibility_paths": [
    "vertical compliance templates",
    "vendor network/history",
    "broker partnerships",
    "managed exception review",
    "workflow integrations"
  ],
  "business_model_options": [
    "vendor-compliance SaaS",
    "managed certificate/license review",
    "vendor onboarding service",
    "broker/insurer embedded offering"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "needs segment-specific CAC and contribution modeling"
  },
  "two_person_feasibility": {
    "assessment": "plausible only if launch scope is narrow; deep screen must identify which tasks can be automated and which require specialist labor",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist contractor/ops support after repeatable demand",
    "phase_3": "channel partnerships and dedicated sales/support if ACV supports it"
  },
  "risks": [
    "Need segment-specific willingness to pay by vendor count",
    "Need measure vendor response/chase workload",
    "Need compare liability of automated COI interpretation vs human review",
    "Need identify underserved verticals rather than generic COI market"
  ],
  "offer_hypotheses": [
    "vendor self-service compliance portal",
    "managed COI/license review desk",
    "vendor onboarding packet workflow",
    "broker-embedded compliance dashboard"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "entrant_edge": {
    "status": "not_evidenced",
    "evidence_refs": [
      "turn540334search1",
      "turn540334search3",
      "turn540334search2"
    ],
    "rejection_reason": "Current COI platforms already cover the proposed workflow; no structural edge."
  }
}
```

### e9576b7c-a5bd-495a-8926-74dd314bb7e3
```json
{
  "niche_id": "e9576b7c-a5bd-495a-8926-74dd314bb7e3",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US nonprofits managing multiple restricted grants/government contracts, especially organizations too complex for spreadsheets but too small for enterprise grant-management systems.",
  "painful_job": "After award, staff must track restricted spending, reporting deadlines, supporting documentation, budget changes and cross-team handoffs; failures risk audit findings, clawbacks or renewal problems.",
  "economic_importance": "Restricted-fund mistakes, missed reports and weak audit trails consume staff time and can threaten grant renewals or create audit/clawback risk.",
  "spend_wtp_evidence": [
    {
      "signal": "Instrumentl Full Lifecycle publishes $999/month for post-award spend tracking/reporting"
    },
    {
      "signal": "Organizations still report Excel-based grant tracking"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "IRS recognized nearly 2.1M tax-exempt organizations in FY2025; target is the grant-funded subset"
    },
    {
      "signal": "Instrumentl says it serves 5,500+ nonprofits"
    }
  ],
  "acquisition_paths": [
    "nonprofit CPAs/bookkeepers",
    "QuickBooks ecosystem",
    "nonprofit associations",
    "grants/finance communities",
    "SEO"
  ],
  "competitors_substitutes": [
    "Excel/Google Sheets",
    "Instrumentl",
    "Airtable/monday.com",
    "grant-management suites",
    "accounting-system workarounds"
  ],
  "defensibility_paths": [
    "accounting/grant obligation data model",
    "funder-report mappings",
    "embedded finance/grant workflows",
    "CPA partner network"
  ],
  "business_model_options": [
    "post-award SaaS",
    "managed grant-reporting service",
    "accounting connector/add-on",
    "fractional grant-finance operations"
  ],
  "customer_economics": {
    "stage": "prescreen",
    "economics_status": "needs segment-specific CAC and contribution modeling"
  },
  "two_person_feasibility": {
    "assessment": "plausible only if launch scope is narrow; deep screen must identify which tasks can be automated and which require specialist labor",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist contractor/ops support after repeatable demand",
    "phase_3": "channel partnerships and dedicated sales/support if ACV supports it"
  },
  "risks": [
    "Need size target by annual grant volume and active-grant count",
    "Need test integration complexity with QuickBooks and common nonprofit accounting stacks",
    "Need quantify compliance/reporting hours saved",
    "Need determine whether $300–$1000 MRR buyer segment is reachable without long enterprise sales"
  ],
  "offer_hypotheses": [
    "restricted-grant spenddown dashboard",
    "funder reporting packet workflow",
    "finance-program reconciliation service",
    "monthly managed grant-close process"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "entrant_edge": {
    "status": "not_evidenced",
    "evidence_refs": [
      "turn419596search0",
      "turn419596search3",
      "turn419596search2"
    ],
    "rejection_reason": "Instrumentl/Actually already cover post-award finance/spenddown workflow."
  }
}
```

### a64e06fc-c979-4388-80d8-c2563c3b1dcf
```json
{
  "niche_id": "a64e06fc-c979-4388-80d8-c2563c3b1dcf",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "US independent specialty physician practices and small groups with meaningful commercial payer volume and enough claim complexity that manual expected-vs-paid contract reconciliation is impractical.",
  "painful_job": "Underpayments hide inside apparently paid/closed claims; reimbursement pressure is already material, so recovering contractually earned dollars can have direct bottom-line value.",
  "economic_importance": "Commercial-payer underpayments are earned revenue leakage. For independent practices facing stagnant rates and rising costs, recovering correct contracted payment can directly improve margin.",
  "spend_wtp_evidence": [
    {
      "signal": "Attergo publishes $1,299/location/month for a platform tier including payer contract engine and underpayment recovery workflow"
    },
    {
      "signal": "Aspirion and Vareo both advertise contingency-based underpayment recovery"
    },
    {
      "signal": "One current specialist service publishes $1,900/seat/month fixed-fee recovery operations"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "AMA reports 42.2% of physicians worked in private practice in 2024"
    },
    {
      "signal": "47.4% of physicians worked in practices of 10 or fewer physicians in 2024; exact overlap with target private specialty groups remains to be quantified"
    }
  ],
  "acquisition_paths": [
    "RCM/billing-company white-label",
    "specialty associations",
    "healthcare CPAs/consultants",
    "clearinghouse/835 integrations",
    "direct specialty-practice outreach"
  ],
  "competitors_substitutes": [
    "manual billing/RCM review",
    "payer portals",
    "Aspirion",
    "Revecore",
    "Attergo",
    "Vareo",
    "contract-management/RCM platforms"
  ],
  "defensibility_paths": [
    "payer-contract normalization library",
    "specialty-specific expected reimbursement models",
    "variance/appeal outcome history",
    "RCM white-label distribution",
    "contract-renewal benchmarking"
  ],
  "business_model_options": [
    "contingency underpayment recovery",
    "hybrid platform + recovery specialists",
    "fixed subscription contract-variance monitoring",
    "white-label service for billing/RCM firms"
  ],
  "customer_economics": {
    "status": "scenario only",
    "key_issue": "underpayment leakage and recovery labor for target small practices not independently verified; HIPAA/BAA/security required"
  },
  "two_person_feasibility": {
    "assessment": "possible only with narrow initial segment and bounded exception workflow; deep screen required before finalist status",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founders + automation",
    "phase_2": "specialist ops/compliance staff where recovery exceptions require humans",
    "phase_3": "partner distribution and dedicated account operations if ACV/LTV supports it"
  },
  "risks": [
    "Need independent estimate of underpayment incidence/recoverable dollars in 2-20 physician specialty practices",
    "Need payer-contract normalization/onboarding effort",
    "Need HIPAA/BAA/security architecture and appeal/legal boundaries",
    "Need compare contingency economics against incumbent RCM vendors and human recovery labor",
    "Need determine which specialties have enough commercial volume/contract complexity"
  ],
  "offer_hypotheses": [
    "835 expected-vs-paid variance audit",
    "contingency recovery desk",
    "specialty payer contract monitor",
    "RCM white-label underpayment module"
  ],
  "evidence_confidence": "C",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:15:18.573295+00",
  "entrant_edge": {
    "status": "not_evidenced",
    "evidence_refs": [
      "turn701666search13",
      "turn514064search1",
      "turn701666search9"
    ],
    "rejection_reason": "Existing 835 underpayment/recovery platforms plus no independent target leakage proof; no entrant edge."
  }
}
```

### 0eaecc25-13a0-428d-957e-b06d604d7bd9
```json
{
  "niche_id": "0eaecc25-13a0-428d-957e-b06d604d7bd9",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "Chicago-area owner-operators and small trucking fleets, initially roughly 1–10 power units, especially businesses interacting with a trusted repair/service ecosystem.",
  "painful_job": "New authority, annual renewal, adding/replacing equipment, premium shock, cancellation/non-renewal, claim-history change, new lanes/cargo, or need for required insurance filings.",
  "economic_importance": "Commercial trucking insurance is mandatory/mission-critical for many for-hire carriers; the premium is a large recurring annual expense and loss of acceptable coverage can stop operations or authority use.",
  "spend_wtp_evidence": [
    {
      "signal": "Chicago/Naperville owner-operator market quote guidance currently places typical own-authority stacks around $1,000-$1,750/month, depending on risk."
    },
    {
      "signal": "Independent commercial-line commissions commonly sit in double-digit percentage ranges, but actual trucking commission/splits must be confirmed with the chosen market-access partner."
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "FMCSA publishes monthly all-active motor-carrier census data including power units, drivers, operation/classification and contacts, allowing the target 1-10-unit carrier universe to be measured rather than guessed."
    }
  ],
  "acquisition_paths": [
    "Existing owner-confirmed driver/carrier network (~40 direct prospects)",
    "Referral loops from bound clients if service/placement quality earns referrals",
    "Repair/service embedded presence only if separately revalidated and formalized",
    "Paid lead generation is not assumed"
  ],
  "competitors_substitutes": [
    "Progressive direct/commercial",
    "Reliance Partners",
    "Chicago-area independent trucking agencies and brokers",
    "specialty trucking MGAs/wholesalers",
    "direct-to-carrier online quoting"
  ],
  "defensibility_paths": [
    "physical distribution embedded at truck-service trigger",
    "renewal book compounds if retention is strong",
    "customer/policy history and remarketing workflow may improve over time",
    "carrier-market access can become an operational capability but is not assumed proprietary"
  ],
  "business_model_options": [
    "independent commercial P&C brokerage",
    "subproducer/market-access network model",
    "agency plus renewal/remarketing service",
    "cross-sell adjacent commercial coverages where licensed and suitable"
  ],
  "customer_economics": {
    "stage": "deep_screen_required",
    "must_model": "premium x commission x split x retention x service cost x bind rate",
    "not_forecast": true
  },
  "two_person_feasibility": {
    "assessment": "possible only after licensing and market access; one licensed producer can sell while admin/quoting workflow is increasingly systematized",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "licensed producer + founder-operated intake/quoting",
    "phase_2": "CSR/account-management help once renewal book is meaningful",
    "phase_3": "additional producers or repair/service locations if channel economics repeat"
  },
  "risks": [
    "Exact weekly qualified traffic and current-policy renewal calendar are unknown.",
    "Bind rate from repair/service referrals is unknown.",
    "Carrier/MGA access for new trucking risks and new ventures must be verified contractually.",
    "Net commission after aggregator/MGA splits and service workload must be modeled.",
    "Illinois producer/entity licensing and any agency registration requirements must be completed before selling.",
    "Retention and remarketing workload for small trucking accounts is unknown."
  ],
  "offer_hypotheses": [
    "annual renewal/remarketing brokerage",
    "new-venture authority insurance placement",
    "add/replace truck endorsement and remarketing workflow",
    "fleet insurance review bundled with service-shop referral intake"
  ],
  "evidence_confidence": "B",
  "dossier_status": "deep_screen",
  "updated_at": "2026-09-24 21:33:10.446174+00",
  "entrant_edge": {
    "status": "evidenced",
    "not_edge": [
      "Russian/Romanian language",
      "trucking experience alone",
      "better service",
      "cheaper quotes"
    ],
    "edge_type": "existing_owned_audience_customer_base_or_partner_channel",
    "evidence_refs": [
      212
    ],
    "edge_asset_key": "EDGE-TRUCK-NETWORK-01",
    "strength_status": "commercial_strength_unproven",
    "conditional_supporting_asset": "EDGE-TRUCK-SERVICE-DISTRIBUTION-01"
  }
}
```

### 88328b74-e704-4810-8234-d5f5123d14ac
```json
{
  "niche_id": "88328b74-e704-4810-8234-d5f5123d14ac",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "Chicago-area and broader US owner-operators/small fleets, initially 1–10 trucks, with real repair/equipment/cash-flow needs and limited internal treasury capacity.",
  "painful_job": "Major breakdown/repair invoice, equipment purchase/replacement, slow broker/shipper payment cycle, insurance/fuel/payroll squeeze, or need to replace/change factoring/working-capital provider.",
  "economic_importance": "A broken or underfunded truck is a revenue interruption. Repair/equipment/cash-flow capital can restore earning capacity, but the opportunity’s own economics depend on partner referral/rev-share terms rather than the loan amount itself.",
  "spend_wtp_evidence": [
    {
      "signal": "Truck repair finance products currently advertise limits up to $10,000 or specialize in repairs $15,000+."
    },
    {
      "signal": "Big Rig Lending pays $100 per funded referral; Total360 advertises $250 per sold repair-program agreement."
    },
    {
      "signal": "Factor Finders reported 383 active trucking referral commission deals in 2025 and a 50/50 commission split program."
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "The existing owner trucking network is the reachable initial market; broad national TAM is not used as justification before local conversion is measured."
    }
  ],
  "acquisition_paths": [
    "Existing owner-confirmed small-carrier/driver network",
    "Repair/service-center presence only after separate revalidation",
    "Referrals from insurance clients only if the insurance business is independently viable"
  ],
  "competitors_substitutes": [
    "Big Rig Lending and other truck repair/equipment finance brokers",
    "CFX Solutions partner/referral programs",
    "Factor Finders and trucking factoring brokers",
    "direct lender/fintech products targeting owner-operators"
  ],
  "defensibility_paths": [
    "trust/access to real small-carrier buyers",
    "partner selection and referral workflow quality",
    "possible future multi-location repair/service distribution if separately secured"
  ],
  "business_model_options": [
    "fixed referral-fee distribution",
    "commission/revenue-share factoring or finance referrals",
    "embedded repair-finance partner program",
    "future marketplace/broker model only if volume justifies compliance and technology"
  ],
  "customer_economics": {
    "stage": "deep_screen",
    "key_metric": "revenue per qualified capital event and per network contact/year",
    "not_forecast": true
  },
  "two_person_feasibility": {
    "assessment": "very easy operationally as referral model; primary risk is weak dollar economics, not execution capacity",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "manual qualified referral + partner tracking",
    "phase_2": "automated routing/CRM after repeatable volume",
    "phase_3": "additional repair/service partner locations only if one-location economics prove attractive"
  },
  "risks": [
    "Qualified finance/capital need frequency across the existing network is unknown.",
    "Average payout and residual economics vary materially by partner.",
    "Referral/finance compliance and disclosure requirements must be checked by product/state.",
    "Partner underwriting/approval quality and customer complaints can damage the core relationship.",
    "Repair-center physical access remains conditional, not gate evidence."
  ],
  "offer_hypotheses": [
    "repair financing referral",
    "equipment-finance referral",
    "factoring/working-capital referral",
    "commercial equipment repair-protection referral"
  ],
  "evidence_confidence": "B",
  "dossier_status": "rejected",
  "updated_at": "2026-09-24 21:46:49.742777+00",
  "entrant_edge": {
    "status": "evidenced",
    "edge_type": "existing_owned_audience_customer_base_or_partner_channel",
    "evidence_refs": [
      "owner_context:trucking_network_and_approx_40_prospects"
    ],
    "edge_asset_key": "EDGE-TRUCK-NETWORK-01",
    "strength_status": "commercial_strength_unproven",
    "conditional_supporting_asset": "EDGE-REPAIR-HUB-01"
  }
}
```

### 7dd5fa33-63a9-4f9f-a711-8e4bd78f1ddc
```json
{
  "niche_id": "7dd5fa33-63a9-4f9f-a711-8e4bd78f1ddc",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "Chicago-area owner-operators and small trucking fleets, initially 1–10 power units, reachable through the existing owner-confirmed trucking network.",
  "painful_job": "Books are behind or unclear, tax/CPA handoff is painful, factoring/settlement reconciliation is messy, fleet grows beyond one truck, lender/insurance/management needs clean P&L, or owner wants monthly truck-level profitability.",
  "economic_importance": "Clean monthly books affect tax handoff, cash visibility, lender readiness, truck-level profitability and owner decision-making. Current trucking-specialist providers charge recurring monthly fees.",
  "spend_wtp_evidence": [
    {
      "signal": "Published owner-operator prices span roughly $129 to $500/month across current providers."
    },
    {
      "signal": "Published small-fleet prices include roughly $199 to $1,200/month depending on scope."
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "FMCSA active carrier data makes the small-carrier target universe measurable beyond the initial network."
    }
  ],
  "acquisition_paths": [
    "Existing owner-confirmed ~40-contact trucking network",
    "referrals from satisfied accounts",
    "public carrier prospecting only after CAC evidence",
    "paid leads not assumed"
  ],
  "competitors_substitutes": [
    "QuickStart",
    "KDP Ledger",
    "Accountlet",
    "Trip Sheet Central",
    "general bookkeepers/QuickBooks ProAdvisors",
    "DIY software"
  ],
  "defensibility_paths": [
    "warm-network acquisition",
    "trucking-specific monthly close/checklists",
    "repeat transaction mappings and truck-level reporting can improve efficiency",
    "no proprietary moat assumed"
  ],
  "business_model_options": [
    "monthly bookkeeping subscription",
    "catch-up/cleanup separately priced",
    "fleet-level financial back-office",
    "CPA/tax-preparer partnership later if separately compliant"
  ],
  "customer_economics": {
    "stage": "deep_screen_required",
    "must_model": "monthly fee - software - review labor - bookkeeping labor - exception/catch-up allocation",
    "not_forecast": true
  },
  "two_person_feasibility": {
    "assessment": "plausible but unproven; recurring monthly close is batchable, while transaction volume and cleanup exceptions can overwhelm a two-person team",
    "initial_team": 2
  },
  "scale_hiring_path": {
    "phase_1": "founder intake + standardized bookkeeping/review workflow",
    "phase_2": "dedicated bookkeeper once MRR supports payroll",
    "phase_3": "review lead/controller and partner tax/CPA channel only if economics support it"
  },
  "risks": [
    "Actual monthly transaction volume and service hours by 1-truck vs 2-10-truck account are unknown.",
    "Software/client-file cost per account is unmodeled.",
    "Catch-up/cleanup labor can be much larger than recurring monthly close.",
    "Actual network willingness to outsource bookkeeping is unmeasured.",
    "Bookkeeping quality-control/review process must be defined.",
    "Tax-return preparation, tax advice, attest/assurance and CPA-title use must remain out of launch scope unless proper credentials/requirements are satisfied.",
    "Retention/churn is unknown."
  ],
  "offer_hypotheses": [
    "trucking monthly bookkeeping",
    "fleet P&L and reconciliation",
    "separately priced catch-up cleanup"
  ],
  "evidence_confidence": "B",
  "dossier_status": "deep_screen",
  "updated_at": "2026-09-24 22:32:53.675481+00",
  "entrant_edge": {
    "status": "evidenced",
    "not_edge": [
      "trucking experience alone",
      "automation",
      "generic bookkeeping",
      "cheaper service"
    ],
    "edge_type": "existing_owned_audience_customer_base_or_partner_channel",
    "evidence_refs": [
      259
    ],
    "edge_asset_key": "EDGE-TRUCK-NETWORK-01",
    "strength_status": "commercial_strength_unproven"
  }
}
```

### f5ebd322-a409-4433-85fe-22d27321b4e3
```json
{
  "niche_id": "f5ebd322-a409-4433-85fe-22d27321b4e3",
  "project_id": "c5ca88b5-a166-479a-9038-fd85d68d3ab5",
  "buyer_segment": "Chicago-area owner-operators and small trucking fleets, initially 1–10 power units, reachable through the existing owner-confirmed trucking network.",
  "painful_job": "New authority, hiring a driver, annual/quarterly compliance cycle, MCS-150/UCR/IFTA deadlines, Clearinghouse requirements, medical-card expiration, roadside/enforcement issues, or new-entrant/audit preparation.",
  "economic_importance": "DOT compliance is recurring and operationally consequential; current providers sell these workflows on recurring monthly plans.",
  "spend_wtp_evidence": [
    {
      "type": "low_cost_benchmark",
      "price": "$25/unit/month for 1-3",
      "meaning": "very strong managed-service price pressure; premium cannot be justified by DQ/Clearinghouse/filings alone",
      "provider": "Trucking Comply"
    },
    {
      "type": "software_plus_setup",
      "price": "$149.99/month for 1-9",
      "meaning": "alerts/files/audit prep plus one-business-day setup already exist at target price",
      "provider": "Dotra"
    },
    {
      "type": "human_managed",
      "price": "$199/month + $199 setup",
      "meaning": "market evidence for human follow-through, summaries and corrective-action tracking",
      "provider": "Lili Safety"
    },
    {
      "type": "local_human",
      "price": "$149/month owner-operator",
      "meaning": "local high-touch service is sold at the planned base price",
      "provider": "AR Safety Support"
    }
  ],
  "market_depth_evidence": [
    {
      "signal": "FMCSA maintains a continuously refreshed active motor-carrier universe; exact target segmentation is measurable."
    }
  ],
  "acquisition_paths": [
    "Existing owner-confirmed trucking network (~40 direct prospects)",
    "Referrals after proven service/retention",
    "Repair/service-center distribution only if separately revalidated",
    "Paid leads not assumed"
  ],
  "competitors_substitutes": [
    {
      "name": "Trucking Comply",
      "type": "managed low-cost",
      "price": "from $25/unit/month",
      "threat": "covers most baseline features plus filings/audit support"
    },
    {
      "name": "Dotra",
      "type": "software + onboarding",
      "price": "$149.99/month for 1-9",
      "threat": "strong automation, alerts, DQ/vehicle files, audit prep, rapid setup"
    },
    {
      "name": "Lili Safety",
      "type": "human managed",
      "price": "from $199/month",
      "threat": "direct substitute for premium human-management thesis"
    },
    {
      "name": "AR Safety Support",
      "type": "local human managed",
      "price": "$149/month owner-operator",
      "threat": "direct local/high-touch substitute"
    }
  ],
  "defensibility_paths": [
    "Owner-controlled warm trucking distribution is the only evidenced structural edge.",
    "Do not claim software, automation, language or trucking knowledge as moat.",
    "Potential service wedge: founder-accountable exception handling + audit-readiness + monthly management summary, but this is a value hypothesis, not an evidenced moat.",
    "Partner backend may reduce regulated execution burden and owner time; partner economics are not yet contracted."
  ],
  "business_model_options": [
    {
      "model": "bounded managed compliance desk",
      "scope": "human exception/accountability layer plus audit-readiness; partner-backed regulated testing/Clearinghouse",
      "status": "validation_offer",
      "setup_usd": 199,
      "monthly_usd": 149
    },
    {
      "model": "high-touch managed compliance",
      "scope": "only if buyers value management summary/corrective action enough to clear low-cost substitutes",
      "status": "secondary_test",
      "monthly_usd": 199
    },
    {
      "model": "backend/referral layer",
      "scope": "if premium service WTP fails, monetize partner/referral relationship rather than carrying high-touch service",
      "status": "fallback"
    }
  ],
  "customer_economics": {
    "not_forecast": true,
    "setup_test_usd": 199,
    "direct_backend_costs": "not fully contracted; excluded/pass-through where unknown",
    "price_test_usd_month": [
      149,
      199
    ],
    "owner_time_hard_kill_hours": 3,
    "base_contribution_at_149_2h_usd": 74,
    "base_contribution_at_199_2h_usd": 124,
    "base_contribution_at_149_1_5h_usd": 89,
    "owner_time_review_threshold_hours": 2,
    "owner_time_target_hours_account_month": 1.5
  },
  "two_person_feasibility": {
    "status": "unproven until measured",
    "initial_team": 2,
    "pilot_capacity": "5-10 accounts if routine work stays <=2h/account/month",
    "regulated_backend": "partner/registered C-TPA preferred for testing/Clearinghouse execution",
    "review_10_accounts_hours_month": 20,
    "target_10_accounts_hours_month": 15
  },
  "scale_hiring_path": {
    "phase_1": "founder sales/intake + standardized admin + partner backend",
    "phase_2": "dedicated compliance account manager when MRR supports payroll",
    "phase_3": "replicate channels only after retention/CAC evidence"
  },
  "risks": [
    "A $25/unit managed competitor covers most baseline compliance features, so generic compliance administration has no pricing power.",
    "Human/accountability premium is not validated with the warm channel.",
    "Actual exception/support minutes per account are unmeasured.",
    "Partner/backend contract economics are not verified.",
    "Clearinghouse/testing must remain within registered/designated C/TPA/partner scope.",
    "Form 2290 tax-return preparation is excluded from self-delivered pilot scope.",
    "Security, liability and document-handling controls must be ready before paid operations."
  ],
  "offer_hypotheses": [
    {
      "buyer": "1-3 truck owner-operator / small carrier",
      "offer": "DOT Managed Exceptions Desk",
      "promise": "You keep driving; one accountable person keeps the compliance exception list, deadlines and audit-readiness moving.",
      "excluded": [
        "legal representation or guarantee of compliance",
        "Form 2290 tax-return preparation",
        "direct drug/alcohol/MRO functions outside partner/registered C-TPA role",
        "fines/fees/tests/third-party query balances unless separately quoted"
      ],
      "included": [
        "initial carrier/profile and document-gap review",
        "prioritized open-items list",
        "DQ file checklist and expiration tracking",
        "MCS-150/UCR deadline coordination",
        "monthly compliance status summary",
        "exception follow-up and missing-document chase list",
        "audit-readiness document index/checklist",
        "partner coordination for regulated testing/Clearinghouse"
      ],
      "setup_usd": 199,
      "monthly_usd": 149,
      "premium_reason_hypothesis": "accountability, exceptions and human follow-through rather than software feature count"
    }
  ],
  "evidence_confidence": "B",
  "dossier_status": "deep_screen",
  "updated_at": "2026-10-03 18:52:58.334875+00",
  "entrant_edge": {
    "status": "evidenced",
    "not_edge": [
      "trucking experience alone",
      "language",
      "automation",
      "generic managed service"
    ],
    "edge_type": "existing_owned_audience_customer_base_or_partner_channel",
    "evidence_refs": [
      251
    ],
    "edge_asset_key": "EDGE-TRUCK-NETWORK-01",
    "strength_status": "commercial_strength_unproven",
    "conditional_supporting_asset": "EDGE-TRUCK-SERVICE-DISTRIBUTION-01"
  }
}
```

## Происхождение и ограничения

- `provenance.json` содержит запросы SQL, время чтения и точные количества. Выбраны только проектные таблицы; данные авторизации, секреты и частные операционные журналы не экспортировались.
- Идентификаторы и контрольные суммы сохранены для сопоставления записей. Имена проверяющих и владельцев, частные примечания и переопределения рабочей области, конфигурация источников не включены.
- Фактическое состояние текущей версии на ПК этим экспортом не проверялось. Публикации, модели, очереди и состояния базы не изменялись.
- Сканирование явных признаков секретов и частных путей не выявило совпадений; это не абсолютная гарантия отсутствия любой чувствительной информации.

## Проверка связности и состояний

Все 37 старых ниш имеют состояния: 26 `rejected`, 11 `paused`. Входящие 23 кандидата: 17 `rejected`, 4 `promoted`, 1 `normalized`, 1 `new`. Пять возможностей каталога: 4 `researched`, 1 `testable`, но это искусственные контрольные записи, не приёмка владельцем. 50 утверждений: 48 `supported`, 1 `unverified`, 1 `contested`. Все 51 связь утверждения с доказательством разрешаются к экспортированным 50 утверждениям и 8 источникам. Старые записи относятся к одному проекту с идентификатором `c5ca88b5-a166-479a-9038-fd85d68d3ab5`.
