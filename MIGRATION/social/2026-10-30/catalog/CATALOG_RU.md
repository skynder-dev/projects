# SOCIAL - каталог восстановленных записей

Срез: 30 октября 2026 года. Это последовательное чтение выбранных проектных таблиц, не полная резервная копия БД и не транзакционно согласованный снимок. Исходные утверждения и оценки сохранены как исторические данные, не как заново проверенные факты.

## Реестр файлов и точные количества

- `candidate_score_history_summary.json`: 776 записей.
- `candidate_source_events.json`: 1322 записей.
- `claim_evidence.json`: 60 записей.
- `claims.json`: 40 записей.
- `content_artifacts.json`: 24 записей.
- `evidence_nodes.json`: 30 записей.
- `factual_cores.json`: 20 записей.
- `latest_candidate_scores.json`: 773 записей.
- `research_packets.json`: 20 записей.
- `review_decisions.json`: 89 записей.
- `scoring_policy_distribution.json`: 5 записей.
- `source_definitions.json`: 7 записей.
- `source_events.json`: 1328 записей.
- `story_candidates.json`: 783 записей.
- `workspaces.json`: 2 записей.

## Как читать каталог

Текущий продукт создаёт идеи и концепты. Исторические поля `narration`, `visual_plan` и `video_script` оставлены для сохранения происхождения; это не разрешение возобновлять видео, голос или публикацию. Все 783 кандидата принадлежат контрольной рабочей области Social Internal Lab. Вторая рабочая область называется Social Test. Серверные статусы `validated` и `researched` не означают приёмку владельцем или готовность текущей версии на ПК.

783 кандидата = 760 `ready_for_research` + 20 `researched` + 3 `merged`. Из 783: 727 USGS, 20 Grants.gov, 16 NIH, 10 NASA и 10 детерминированных начальных записей. Это в основном входящий поток источников, не 783 готовых редакционных концепта.

20 исследованных записей = 10 начальных искусственных примеров C049/C084 + 7 исторических материалов NASA о камерах + 3 Grants.gov. Семь записей NASA нельзя автоматически отождествлять с семью темами локальной проверки 17 октября.

24 сохранённых непустых объекта контента = 10 `seed_import` + 4 `medeng_seed_studio_acceptance` + 1 `live_verified_editorial_v1` + 6 `deterministic_factual_core_v1` + 3 `deterministic_factual_core_v2`. Слово `live` здесь относится к происхождению источника, не к текущей продуктовой проверке. Все 24 имеют сохранённое состояние `validated`; это не доказательство готового текста.

Сохранены последние 773 автоматические оценки, 776 групп истории кандидат/версия/порог и все 5 распределений порогов для `candidate_score_v1`. У 10 начальных записей нет оценки. История содержит 264 963 результата; её повторяющиеся исходные строки намеренно не экспортированы. Сохранены 89 решений проверки без личности проверяющего. Изменение служебного `updated_at` не доказывает нового исследования.

Названия, тезисы и тела исходных записей ниже сохранены на исходном языке. Это точные исторические данные, а не новый авторский текст.

## Все кандидаты (полные title и thesis; подробности и исходные метаданные - JSON)

### 1. NIH, CDC and FDA Small Business Innovation Research Grant (Parent SBIR [R43/R44] Clinical Trial Optional)
- ID: `527fdab2-8418-4aac-b700-895ef63f2aaf`; ключ: `live:grants.gov:359671`
- Сохранённое состояние: `researched`; сохранённая оценка: 70.000; последний расчёт: 70.00 / researched
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and practical audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research",
  "product_vertical_selected",
  "research_frozen"
]
- Создано: 2026-10-03 08:18:13.571358+00; обновлено: 2026-10-30 16:05:00.289387+00

### 2. Region 4 Small Business Transportation Technical Assistance Center (SBTTAC)
- ID: `d13f499f-4caa-4b05-8b3b-ba2fc10e99bd`; ключ: `live:grants.gov:364004`
- Сохранённое состояние: `researched`; сохранённая оценка: 70.000; последний расчёт: 70.00 / researched
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and practical audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research",
  "product_vertical_selected",
  "research_frozen"
]
- Создано: 2026-10-03 08:18:13.334135+00; обновлено: 2026-10-30 16:05:00.289387+00

### 3. Small Business Innovation Research and Small Business Technology Transfer Programs Phase II
- ID: `deadac24-a079-4f81-bc52-9a2d63c7d63d`; ключ: `live:grants.gov:364020`
- Сохранённое состояние: `researched`; сохранённая оценка: 70.000; последний расчёт: 70.00 / researched
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and practical audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research",
  "product_vertical_selected",
  "research_frozen"
]
- Создано: 2026-10-03 08:18:13.415466+00; обновлено: 2026-10-30 16:05:00.289387+00

### 4. Space Camera
- ID: `90fc5ca2-d714-4cff-ace6-0a3e6699cbb2`; ключ: `live:nasa:t2:spinoff:54ed040495dd5ea635f6c481`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: 90.00 / researched
- Тезис: Space Shuttle modifications to Nikon’s F3 produced narrowly documented commercial spinoffs in lubricant and motor design; keep the story distinct from the earlier Skylab/FM operability story.
- Коды причин: [
  "live_source",
  "official_api",
  "nasa_t2",
  "needs_research",
  "live_research_verified",
  "historical_attributed_core",
  "queue_processed"
]
- Создано: 2026-09-24 00:02:39.099495+00; обновлено: 2026-10-30 16:05:00.289387+00

### 5. Nikon Camera
- ID: `8b0e7955-e934-4c11-adc4-ad9553b423a0`; ключ: `live:nasa:t2:spinoff:54ed040695dd5ea535ff4101`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: 90.00 / researched
- Тезис: A camera-operability feature developed for weightless astronaut use was later incorporated into the commercial Nikon FM; keep the claim historical and narrowly attributed.
- Коды причин: [
  "live_source",
  "official_api",
  "nasa_t2",
  "needs_research",
  "live_research_verified",
  "historical_attributed_core",
  "queue_processed"
]
- Создано: 2026-09-24 00:02:39.149634+00; обновлено: 2026-10-30 16:05:00.289387+00

### 6. Night Vision Camera
- ID: `bd426f29-a549-4e72-a05f-36bb0f26005b`; ключ: `live:nasa:t2:spinoff:54ed040795dd5ea735be0d1a`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: 90.00 / researched
- Тезис: A commercial PixelVision low-light CCD camera drew on CCD expertise carried from JPL by former engineer James Janesick; characterize the NASA link as personnel knowledge transfer, not a license or NASA-funded product.
- Коды причин: [
  "live_source",
  "official_api",
  "nasa_t2",
  "needs_research",
  "live_research_verified",
  "personnel_expertise_transfer",
  "queue_processed"
]
- Создано: 2026-09-24 00:02:39.286263+00; обновлено: 2026-10-30 16:05:00.289387+00

### 7. Infrared Camera
- ID: `3b775603-199b-4fe2-ab04-b73a25248a70`; ключ: `live:nasa:t2:spinoff:54ed040895dd5ef936513cc6`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: 90.00 / researched
- Тезис: JPL and Amber/Raytheon developed QWIP infrared-camera technology that NASA later documented in real-world fire hot-spot detection; keep medical applications outside the factual core.
- Коды причин: [
  "live_source",
  "official_api",
  "nasa_t2",
  "needs_research",
  "live_research_verified",
  "historical_attributed_core",
  "medical_claims_excluded",
  "queue_processed"
]
- Создано: 2026-09-24 00:02:39.231025+00; обновлено: 2026-10-30 16:05:00.289387+00

### 8. New Modular Camera No Ordinary Joe
- ID: `549ac962-6c18-4aaa-9641-dedcf9e89bd2`; ключ: `live:nasa:t2:spinoff:54ed040895dd5ef936513cd3`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: 90.00 / researched
- Тезис: NASA SBIR/JPL collaboration helped turn SciMeasure’s Little Joe from a bulky prototype into a compact commercial modular CCD camera; keep performance figures historical and source-attributed.
- Коды причин: [
  "live_source",
  "official_api",
  "nasa_t2",
  "needs_research",
  "live_research_verified",
  "historical_attributed_core",
  "queue_processed"
]
- Создано: 2026-09-24 00:02:39.382643+00; обновлено: 2026-10-30 16:05:00.289387+00

### 9. A Motionless Camera
- ID: `e6deba25-ccc8-4250-a16a-7fda70873cc7`; ключ: `live:nasa:t2:spinoff:54ed040f95dd5ea535c489ab`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: 90.00 / researched
- Тезис: NASA-funded motionless-camera work for space-robot guidance reached the commercial market as Omniview; keep all commercialization details historical and NASA-attributed.
- Коды причин: [
  "live_source",
  "official_api",
  "nasa_t2",
  "needs_research",
  "live_research_verified",
  "historical_attributed_core",
  "queue_processed"
]
- Создано: 2026-09-24 00:02:39.263613+00; обновлено: 2026-10-30 16:05:00.289387+00

### 10. Smart Camera Technology Increases Quality
- ID: `74f95f01-33f9-4a92-a6b0-27aed5071f95`; ключ: `live:nasa:t2:spinoff:54ed041295dd5ea73524f640`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: 90.00 / researched
- Тезис: NASA smart-camera work for DART moved into a commercial SpecterView product through Southern Vision Systems; keep the claim historical and NASA-attributed.
- Коды причин: [
  "live_source",
  "official_api",
  "nasa_t2",
  "needs_research",
  "live_research_verified",
  "historical_attributed_core"
]
- Создано: 2026-09-24 00:02:39.336135+00; обновлено: 2026-10-30 16:05:00.289387+00

### 11. A low-power image sensor developed at JPL for spacecraft became a commercial technology through a JPL-founded spinout, Photobit.
- ID: `e3dc883f-3c0e-4c3d-9c0b-b79ed90128f2`; ключ: `seed:C049-F01:v1`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: нет / нет
- Тезис: The camera sensor story starts with a spacecraft power problem, not a phone.
- Коды причин: [
  "seed_fixture",
  "verified",
  "scripted"
]
- Создано: 2026-09-23 23:23:36.835126+00; обновлено: 2026-09-24 00:33:09.481022+00

### 12. NASA SBIR work helped Aspen Systems turn fragile aerogel into practical flexible insulation and spin out Aspen Aerogels to commercialize it.
- ID: `f504c2ab-bb94-470f-ae26-b789b0102575`; ключ: `seed:C049-F02:v1`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: нет / нет
- Тезис: NASA did not invent aerogel. The more interesting story is what it helped make practical.
- Коды причин: [
  "seed_fixture",
  "verified",
  "scripted"
]
- Создано: 2026-09-23 23:23:36.835126+00; обновлено: 2026-09-23 23:23:36.835126+00

### 13. DOE-funded Argonne cathode research became licensed battery technology used by LG Chem in cells supplied for the Chevrolet Volt.
- ID: `2cd09330-7613-4800-b9a3-d89dc28c8a11`; ключ: `seed:C049-F03:v1`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: нет / нет
- Тезис: A piece of the Chevy Volt battery started as DOE lab research.
- Коды причин: [
  "seed_fixture",
  "verified",
  "scripted"
]
- Создано: 2026-09-23 23:23:36.835126+00; обновлено: 2026-09-23 23:23:36.835126+00

### 14. Decades of NCI tumor-infiltrating lymphocyte research moved through a CRADA and NIH patent licenses into Iovance development and the 2024 FDA approval of Amtagvi.
- ID: `26e127de-cdd8-4b3b-b48c-0c608163aa5b`; ключ: `seed:C049-F04:v1`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: нет / нет
- Тезис: A cancer therapy can take decades to travel from a government lab to a commercial product. Here is the bridge.
- Коды причин: [
  "seed_fixture",
  "verified",
  "scripted"
]
- Создано: 2026-09-23 23:23:36.835126+00; обновлено: 2026-09-23 23:23:36.835126+00

### 15. ORNL microfluidic Lab-on-a-chip technology was licensed by Caliper Life Sciences, became part of its commercial platform, and ORNL links that success to PerkinElmer’s 2011 acquisition of Caliper.
- ID: `e129a4fd-0d37-466e-8b86-89d9a4858d8f`; ключ: `seed:C049-F05:v1`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: нет / нет
- Тезис: What can a laboratory license be worth once it becomes a product platform?
- Коды причин: [
  "seed_fixture",
  "verified",
  "scripted"
]
- Создано: 2026-09-23 23:23:36.835126+00; обновлено: 2026-09-23 23:23:36.835126+00

### 16. Distribution transformers are a grid bottleneck because limited domestic capacity, long procurement timelines, foreign dependence and extreme specification fragmentation make rapid substitution/expansion difficult.
- ID: `44debf27-f78e-4640-a0e2-916172cb039d`; ключ: `seed:C084-F01:v1`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: нет / нет
- Тезис: Why can a box on a utility pole become a national supply-chain problem? Start with 80,000 varieties.
- Коды причин: [
  "seed_fixture",
  "verified",
  "scripted"
]
- Создано: 2026-09-23 23:23:36.835126+00; обновлено: 2026-09-23 23:23:36.835126+00

### 17. The chokepoint in U.S. nuclear fuel is not simply uranium ore: enrichment services remain heavily foreign-sourced while policy is trying to rebuild domestic capacity.
- ID: `f509144b-c01d-464b-9300-0714226bbb9a`; ключ: `seed:C084-F02:v1`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: нет / нет
- Тезис: The nuclear-fuel bottleneck is not where uranium comes out of the ground. It is what happens next.
- Коды причин: [
  "seed_fixture",
  "verified",
  "scripted"
]
- Создано: 2026-09-23 23:23:36.835126+00; обновлено: 2026-09-23 23:23:36.835126+00

### 18. A 2026 U.S. cefotaxime shortage became severe enough that FDA coordinated temporary importation of a Canadian-market product, illustrating how limited approved supply can turn an injectable medicine into a supply-chain chokepoint.
- ID: `d6943861-0e23-4a92-b2a4-10af15f5fa02`; ключ: `seed:C084-F03:v1`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: нет / нет
- Тезис: When a medicine shortage gets bad enough, the supply-chain workaround can cross a border.
- Коды причин: [
  "seed_fixture",
  "verified",
  "scripted"
]
- Создано: 2026-09-23 23:23:36.835126+00; обновлено: 2026-09-23 23:23:36.835126+00

### 19. Rare-earth permanent magnets are a downstream manufacturing chokepoint: U.S. industry has domestic mineral resources but still depends heavily on foreign processing/material and magnet supply chains.
- ID: `5ec9cea0-3902-4f8a-91fd-4371a907de3e`; ключ: `seed:C084-F04:v1`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: нет / нет
- Тезис: Mining rare earths is not the same as making the magnet inside a high-performance motor.
- Коды причин: [
  "seed_fixture",
  "verified",
  "scripted"
]
- Создано: 2026-09-23 23:23:36.835126+00; обновлено: 2026-09-23 23:23:36.835126+00

### 20. Gallium is a semiconductor-material chokepoint because the United States does not produce low-purity primary gallium domestically while global primary production is overwhelmingly concentrated in China.
- ID: `0109348d-8097-458b-b89e-c2affaec2a8b`; ключ: `seed:C084-F05:v1`
- Сохранённое состояние: `researched`; сохранённая оценка: 90.000; последний расчёт: нет / нет
- Тезис: A semiconductor supply chain can depend on a metal the U.S. does not produce in primary form.
- Коды причин: [
  "seed_fixture",
  "verified",
  "scripted"
]
- Создано: 2026-09-23 23:23:36.835126+00; обновлено: 2026-09-23 23:23:36.835126+00

### 21. STARBASE Wright Patt
- ID: `fc09d674-234b-4f26-b5bf-f3b258fdb540`; ключ: `live:grants.gov:329806`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and practical audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:18:12.865572+00; обновлено: 2026-10-30 16:05:00.289387+00

### 22. National Defense Education Program (NDEP) Science, Technology, Engineering, and Mathematics (STEM) Consortia Request for Information (RFI) for the Office of the Under Secretary of Defense (Research &amp; Engineering)
- ID: `f43fd98f-bae0-4220-b315-c6b962928231`; ключ: `live:grants.gov:334905`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and practical audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:18:12.777178+00; обновлено: 2026-10-30 16:05:00.289387+00

### 23. Partnership Intermediary Agreement (PIA)
- ID: `e85c6259-718a-4b09-8eff-b870455ea6c6`; ключ: `live:grants.gov:336962`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and practical audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:18:12.647781+00; обновлено: 2026-10-30 16:05:00.289387+00

### 24. Making America Healthy Again by Addressing Dementia Disparities
- ID: `2f1c2e42-3138-4d84-b7cd-4b3c9ac3cd61`; ключ: `live:grants.gov:355824`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:13:49.981594+00; обновлено: 2026-10-30 16:05:00.289387+00

### 25. Coordinating Center for Language Access Services
- ID: `81874560-480e-4aa3-808a-0a94ad6c46d2`; ключ: `live:grants.gov:355829`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:13:50.023543+00; обновлено: 2026-10-30 16:05:00.289387+00

### 26. Promoting Access with a Language Services Assistance Symbol
- ID: `4800ca56-db52-45bd-89fe-fb69028c9d1a`; ключ: `live:grants.gov:355830`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:13:50.049169+00; обновлено: 2026-10-30 16:05:00.289387+00

### 27. Dissemination and Implementation Research in Health (R01 Clinical Trial Optional)
- ID: `e21ea88a-9ee3-4577-96a6-73c1c4a95140`; ключ: `live:grants.gov:356893`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:13:50.158331+00; обновлено: 2026-10-30 16:05:00.289387+00

### 28. Dissemination and Implementation Research in Health (R03 Clinical Trial Not Allowed)
- ID: `58c77267-338a-43fa-96ae-9c566c93002b`; ключ: `live:grants.gov:356907`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:13:50.209645+00; обновлено: 2026-10-30 16:05:00.289387+00

### 29. Dissemination and Implementation Research in Health (R21 Clinical Trial Optional)
- ID: `4c4e83cb-54a3-4790-82e3-f60c0295ea27`; ключ: `live:grants.gov:356920`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:13:50.184489+00; обновлено: 2026-10-30 16:05:00.289387+00

### 30. Population Approaches to Reducing Alcohol-related Cancer Risk (R01 Clinical Trial Optional)
- ID: `f83d8688-fa80-48f5-994e-c83de648045b`; ключ: `live:grants.gov:357021`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:13:50.234185+00; обновлено: 2026-10-30 16:05:00.289387+00

### 31. Investigator Initiated Clinical Trials of Complementary and Integrative Interventions Delivered Remotely or via mHealth (R01 Clinical Trial Required)
- ID: `2691240b-ead8-4f52-89b0-aa9538753b6b`; ключ: `live:grants.gov:357303`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:13:50.103114+00; обновлено: 2026-10-30 16:05:00.289387+00

### 32. Feasibility Clinical Trials of Mind and Body Interventions for NCCIH High Priority Research Topics (R34 Clinical Trial Required)
- ID: `3552bf99-694f-47ff-a4bf-2281b62b1c38`; ключ: `live:grants.gov:357305`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:13:50.076192+00; обновлено: 2026-10-30 16:05:00.289387+00

### 33. Limited Competition: Small Grant Program for the NCATS Clinical and Translational Science Award (CTSA) Program (R03 Clinical Trial Optional)
- ID: `e5d3e62f-0cc2-4a7f-8411-32f7ccdc82be`; ключ: `live:grants.gov:357658`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:13:50.131642+00; обновлено: 2026-10-30 16:05:00.289387+00

### 34. Small Business Transition Grant for New Entrepreneurs (Parent R43/R44 Clinical Trial Optional)
- ID: `1af1cfb2-1f5a-49a4-9d96-511a321d9c0e`; ключ: `live:grants.gov:362576`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and practical audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:18:12.950357+00; обновлено: 2026-10-30 16:05:00.289387+00

### 35. Small Business Transition Grant for New Entrepreneurs (Parent R41/R42 Clinical Trial Optional)
- ID: `8cbd8242-3d56-4521-94d0-455be9f0e641`; ключ: `live:grants.gov:362577`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and practical audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:18:13.032561+00; обновлено: 2026-10-30 16:05:00.289387+00

### 36. Small Business Transportation Technical Assistance Center (Region 1)
- ID: `0b7ac41f-8334-4223-a5de-5336273e6fdb`; ключ: `live:grants.gov:363996`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and practical audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:18:13.213285+00; обновлено: 2026-10-30 16:05:00.289387+00

### 37. Small Business Transportation Technical Assistance Center (Region 3)
- ID: `bfeb0485-d83e-4b71-9a99-8cdc5d410523`; ключ: `live:grants.gov:363998`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / open
- Тезис: Current U.S. federal funding opportunity. Verify eligibility, deadline, award details and practical audience fit before Reel generation.
- Коды причин: [
  "live_source",
  "official_api",
  "grants_gov",
  "federal_funding",
  "needs_research"
]
- Создано: 2026-10-03 08:18:13.11206+00; обновлено: 2026-10-30 16:05:00.289387+00

### 38. Camera-on-a-Chip
- ID: `2706ea1d-0502-4db0-adb8-36f605f919d8`; ключ: `live:nasa:t2:spinoff:54ed040895dd5ef936513cda`
- Сохранённое состояние: `merged`; сохранённая оценка: 0.000; последний расчёт: 0 / terminal
- Тезис: Official NASA T2 Spinoff record selected for independent research verification.
- Коды причин: [
  "live_source",
  "official_api",
  "nasa_t2",
  "needs_research"
]
- Создано: 2026-09-24 00:02:39.308252+00; обновлено: 2026-10-30 16:05:00.289387+00

### 39. Image Sensors Enhance Camera Technologies
- ID: `b55af967-7e3d-4723-8f4a-8b6f52828cd0`; ключ: `live:nasa:t2:spinoff:54ed040895dd5ef936513ce9`
- Сохранённое состояние: `merged`; сохранённая оценка: 0.000; последний расчёт: 0 / terminal
- Тезис: Official NASA T2 Spinoff record selected for independent research verification.
- Коды причин: [
  "live_source",
  "official_api",
  "nasa_t2",
  "needs_research"
]
- Создано: 2026-09-24 00:02:39.360099+00; обновлено: 2026-10-30 16:05:00.289387+00

### 40. Spherical Camera
- ID: `900eea0b-e4f5-4162-b34d-9976f5d73586`; ключ: `live:nasa:t2:spinoff:54ed040e95dd5ea63514df05`
- Сохранённое состояние: `merged`; сохранённая оценка: 0.000; последний расчёт: 0 / terminal
- Тезис: Official NASA T2 Spinoff record selected for independent research verification.
- Коды причин: [
  "live_source",
  "official_api",
  "nasa_t2",
  "needs_research"
]
- Создано: 2026-09-24 00:02:39.182175+00; обновлено: 2026-10-30 16:05:00.289387+00

### 41. Immuno-electrochemical Detection and Characterization of Melanoma Circulating Cells
- ID: `d7abc8ae-c965-41d4-8679-ec5e671cf928`; ключ: `live:nih:reporter:11211885`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 31.000; последний расчёт: 31.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-24 00:25:10.660635+00; обновлено: 2026-10-30 16:05:00.289387+00

### 42. ENABLING SUBMILLISECOND-TIMESCALE TWO-PHOTON RECORDING OF VOLTAGE DYNAMICS IN THREE DIMENSIONS IN VIVO
- ID: `7a4ef5ee-e386-41c3-8970-47189f6f8e92`; ключ: `live:nih:reporter:11402675`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 35.000; последний расчёт: 35.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-24 00:25:10.611622+00; обновлено: 2026-10-30 16:05:00.289387+00

### 43. Building and InnovatinG: Digital heAlth Technology and Analytics (BIGDATA)
- ID: `2a973451-7e99-47ac-a6ec-f1fe50fa1a6b`; ключ: `live:nih:reporter:11404897`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 35.000; последний расчёт: 35.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-29 03:45:03.963571+00; обновлено: 2026-10-30 16:05:00.289387+00

### 44. A Modular Overground Balance Walkway for Task-Specific Perturbation-based Fall Prevention Assessment and Training
- ID: `3fd9d9fb-dc71-494e-b8cc-64801917b1e4`; ключ: `live:nih:reporter:11407994`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 41.000; последний расчёт: 41.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-24 00:25:10.771142+00; обновлено: 2026-10-30 16:05:00.289387+00

### 45. Novel treatments of chronic pain due to repetitive mild traumatic brain injury
- ID: `44d3b079-1712-4f6a-b54d-6de406285de8`; ключ: `live:nih:reporter:11418233`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 31.000; последний расчёт: 31.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-10-06 04:00:02.406188+00; обновлено: 2026-10-30 16:05:00.289387+00

### 46. Project 1: Modeling brain-state-dependent fluid flow and clearance in mice and humans
- ID: `651e8a31-163e-4f01-932b-ff816ea377d5`; ключ: `live:nih:reporter:11418471`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-24 00:25:10.793338+00; обновлено: 2026-10-30 16:05:00.289387+00

### 47. Project 3: Dissecting the neural and neuromodulatory control mechanisms of arterial dynamics during sleep
- ID: `e36b3c68-701a-49d3-9268-c4ffd14e75bb`; ключ: `live:nih:reporter:11418477`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-24 00:25:10.682022+00; обновлено: 2026-10-30 16:05:00.289387+00

### 48. Evaluation of an Adaptive Lifestyle Intervention for Adults with Type 1 Diabetes
- ID: `9cfb35ea-dab7-4286-aa6e-d3a97fd15b26`; ключ: `live:nih:reporter:11454660`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-24 00:25:10.708445+00; обновлено: 2026-10-30 16:05:00.289387+00

### 49. Understanding expression and signaling of sex hormone receptors in brain cancers
- ID: `f561ede2-ecec-469b-a0de-6d4e17211f0b`; ключ: `live:nih:reporter:11457156`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 33.000; последний расчёт: 33.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-24 00:25:10.840024+00; обновлено: 2026-10-30 16:05:00.289387+00

### 50. Regulation of Cardiac Fibrosis by Substance P Receptors
- ID: `c57d0fff-9048-48b6-b7bf-8e5071459a06`; ключ: `live:nih:reporter:11462774`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 33.000; последний расчёт: 33.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-24 00:25:10.818573+00; обновлено: 2026-10-30 16:05:00.289387+00

### 51. Enabling High-Throughput Analysis and Single-Cell Imaging of Bacterial Signals
- ID: `e1016900-8616-4862-a39e-17b84d9673db`; ключ: `live:nih:reporter:11465845`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-24 00:25:10.745854+00; обновлено: 2026-10-30 16:05:00.289387+00

### 52. Multilayer coordination of stratified epithelial wound closure
- ID: `74acc66f-5536-4c7b-833e-4d9efc5499e2`; ключ: `live:nih:reporter:11499214`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 33.000; последний расчёт: 33.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-29 03:45:03.927868+00; обновлено: 2026-10-30 16:05:00.289387+00

### 53. Cellular Energy Metabolism in Neurons
- ID: `3f21d42c-1567-4edf-b63a-22009f5b8dad`; ключ: `live:nih:reporter:11524645`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-29 03:45:03.987695+00; обновлено: 2026-10-30 16:05:00.289387+00

### 54. 2026 American Society for Matrix Biology (ASMB) Workshop on Basement Membranes
- ID: `9d2f4ce6-0e55-4dcf-922a-e30f0cf19c49`; ключ: `live:nih:reporter:11527297`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 33.000; последний расчёт: 33.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-29 03:45:04.011059+00; обновлено: 2026-10-30 16:05:00.289387+00

### 55. SCH: Integrated AI and Sensing Systems for Mitigating Heart Failure Readmissions in High-Risk Groups with Obesity
- ID: `6fb4eeb4-5165-4fb6-b944-aeeb3a5e95cc`; ключ: `live:nih:reporter:11576378`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-29 03:45:04.076798+00; обновлено: 2026-10-30 16:05:00.289387+00

### 56. Phosphodiesterase 1 (PDE1) Regulation of Myocardial Calcium and Function
- ID: `b7194524-0f57-4615-bae8-21582dbca1b4`; ключ: `live:nih:reporter:11628972`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 33.000; последний расчёт: 33.00 / medical_waiting
- Тезис: NIH-funded research project selected for independent research and commercialization verification. RePORTER metadata alone is not evidence of efficacy, safety, or market adoption.
- Коды причин: [
  "live_source",
  "official_api",
  "nih_reporter",
  "medical_research_metadata_only",
  "needs_research"
]
- Создано: 2026-09-24 00:25:10.726857+00; обновлено: 2026-10-30 16:05:00.289387+00

### 57. M5.5 earthquake - 92 km NNW of Aleneva, Alaska
- ID: `94b389a9-ceaf-4a30-bcab-10b7d564a27f`; ключ: `live:usgs:earthquake:aka2026tuxgky`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 19:00:02.135388+00; обновлено: 2026-10-30 16:05:00.289387+00

### 58. M5.6 earthquake - 43 km NNW of Lake Minchumina, Alaska
- ID: `60ded9d2-2d39-4e88-b46e-5ef9dec705fe`; ключ: `live:usgs:earthquake:aka2026ukynnb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 11:15:01.803535+00; обновлено: 2026-10-30 16:05:00.289387+00

### 59. M4.5 earthquake - 89 km SSE of Akutan, Alaska
- ID: `804984ea-dc11-4574-b1a5-5733749ec91c`; ключ: `live:usgs:earthquake:aka2026vddzqy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 08:15:01.683704+00; обновлено: 2026-10-30 16:05:00.289387+00

### 60. M5.0 earthquake - 163 km W of Port McNeill, Canada
- ID: `ab82437d-d392-406f-bc62-0b900c4cae00`; ключ: `live:usgs:earthquake:attm2hmu`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 09:25:05.866722+00; обновлено: 2026-10-30 16:05:00.289387+00

### 61. M4.8 earthquake - 97 km W of Petrolia, CA
- ID: `efd2f4a8-64f3-4961-baef-58f8d461efa2`; ключ: `live:usgs:earthquake:nc75444322`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 11:50:04.917473+00; обновлено: 2026-10-30 16:05:00.289387+00

### 62. M4.8 earthquake - 21 km W of Preston, Nevada
- ID: `fcee1e99-7dee-42dc-b3e8-8034d6548963`; ключ: `live:usgs:earthquake:nn00924930`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 07:35:03.532566+00; обновлено: 2026-10-30 16:05:00.289387+00

### 63. M6.6 earthquake - 105 km NE of Norsup, Vanuatu
- ID: `162548b9-8987-430d-9475-2a404fcd021f`; ключ: `live:usgs:earthquake:pt26281001`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 09:15:01.577137+00; обновлено: 2026-10-30 16:05:00.289387+00

### 64. M4.7 earthquake - 30 km SE of Khorugh, Tajikistan
- ID: `25865128-2c56-4de0-bb93-dcc2f4fd5813`; ключ: `live:usgs:earthquake:us6000tx16`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 00:48:02.193126+00; обновлено: 2026-10-30 16:05:00.289387+00

### 65. M4.9 earthquake - Scotia Sea
- ID: `66d9dbc7-0264-46a2-8668-5d7d4f5d9793`; ключ: `live:usgs:earthquake:us6000tx23`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 00:48:02.174897+00; обновлено: 2026-10-30 16:05:00.289387+00

### 66. M5.3 earthquake - 51 km WSW of Arauco, Argentina
- ID: `b615794e-cbac-4e8e-90b9-e60e9c6f4468`; ключ: `live:usgs:earthquake:us6000tx29`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 00:48:02.157728+00; обновлено: 2026-10-30 16:05:00.289387+00

### 67. M4.6 earthquake - 106 km WNW of Ternate, Indonesia
- ID: `2c51d1b3-6b8f-4aeb-a15f-170cfcbd614a`; ключ: `live:usgs:earthquake:us6000tx31`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 00:48:02.141107+00; обновлено: 2026-10-30 16:05:00.289387+00

### 68. M5.0 earthquake - Mariana Islands region
- ID: `16377380-5721-47e4-8b88-f384becc4822`; ключ: `live:usgs:earthquake:us6000tx38`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 00:48:02.121965+00; обновлено: 2026-10-30 16:05:00.289387+00

### 69. M5.7 earthquake - 180 km NW of Hihifo, Tonga
- ID: `81c9b18f-87b7-4845-ac63-8565c8ef3833`; ключ: `live:usgs:earthquake:us6000tx3m`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 00:48:02.102551+00; обновлено: 2026-10-30 16:05:00.289387+00

### 70. M4.6 earthquake - south of the Fiji Islands
- ID: `fc2a03ae-d460-488a-85ac-6fc9d0bd5d50`; ключ: `live:usgs:earthquake:us6000tx3n`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 00:48:02.08093+00; обновлено: 2026-10-30 16:05:00.289387+00

### 71. M4.6 earthquake - 59 km WNW of San Antonio de los Cobres, Argentina
- ID: `e253bce1-3f17-4bf0-ab32-1a5232a98019`; ключ: `live:usgs:earthquake:us6000tx4w`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 00:48:02.063645+00; обновлено: 2026-10-30 16:05:00.289387+00

### 72. M4.9 earthquake - 193 km SE of Mata-Utu, Wallis and Futuna
- ID: `71e20a72-17a7-43c6-ac74-482ec0d84d8f`; ключ: `live:usgs:earthquake:us6000tx53`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 00:48:02.04727+00; обновлено: 2026-10-30 16:05:00.289387+00

### 73. M5.0 earthquake - 140 km NNE of Ba, Fiji
- ID: `e49a7748-5d2b-4b0a-bcf6-6078f25ffe8a`; ключ: `live:usgs:earthquake:us6000tx58`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 00:48:02.025337+00; обновлено: 2026-10-30 16:05:00.289387+00

### 74. M4.6 earthquake - 223 km WNW of Abepura, Indonesia
- ID: `832f4921-b195-4378-8893-21270c77e9ed`; ключ: `live:usgs:earthquake:us6000tx7g`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 03:45:02.726255+00; обновлено: 2026-10-30 16:05:00.289387+00

### 75. M4.5 earthquake - 31 km NNW of Komodo, Indonesia
- ID: `9e913b4e-9dc4-464c-9d9e-5cc22d543006`; ключ: `live:usgs:earthquake:us6000tx8q`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 04:00:03.131895+00; обновлено: 2026-10-30 16:05:00.289387+00

### 76. M5.3 earthquake - 15 km SSW of Hilvan, Turkey
- ID: `12854f48-3315-4350-b4c7-44babb6d404e`; ключ: `live:usgs:earthquake:us6000tx9u`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 08:00:03.48695+00; обновлено: 2026-10-30 16:05:00.289387+00

### 77. M4.9 earthquake - Kermadec Islands, New Zealand
- ID: `766ccdef-3724-4d80-bc17-2977a1c44eff`; ключ: `live:usgs:earthquake:us6000txb3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 11:45:03.895119+00; обновлено: 2026-10-30 16:05:00.289387+00

### 78. M5.2 earthquake - 139 km SW of Kokopo, Papua New Guinea
- ID: `655b399d-ccca-4f71-89b0-e04624ee4bc2`; ключ: `live:usgs:earthquake:us6000txbm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 13:00:03.391759+00; обновлено: 2026-10-30 16:05:00.289387+00

### 79. M4.5 earthquake - 106 km SW of Puerto Madero, Mexico
- ID: `916c8e0b-057f-467e-916b-1e9e368cabbc`; ключ: `live:usgs:earthquake:us6000txc1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 18:00:07.023208+00; обновлено: 2026-10-30 16:05:00.289387+00

### 80. M4.6 earthquake - 119 km SW of Abepura, Indonesia
- ID: `ea5cb896-5f18-4080-a2d6-bfca9d556ff0`; ключ: `live:usgs:earthquake:us6000txcw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 18:15:03.906976+00; обновлено: 2026-10-30 16:05:00.289387+00

### 81. M4.6 earthquake - 21 km NNW of Rioblanco, Colombia
- ID: `3c81bb25-1847-4c58-8e56-87b737bf2ca4`; ключ: `live:usgs:earthquake:us6000txdb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 19:30:03.538535+00; обновлено: 2026-10-30 16:05:00.289387+00

### 82. M5.1 earthquake - 32 km S of Kokopo, Papua New Guinea
- ID: `b2be67ef-5aa8-457c-97ee-54fe0a5a76c6`; ключ: `live:usgs:earthquake:us6000txf9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 18:30:04.004539+00; обновлено: 2026-10-30 16:05:00.289387+00

### 83. M4.6 earthquake - 155 km NW of Ternate, Indonesia
- ID: `0643c04a-8d4b-4761-9955-ec91d2eb045d`; ключ: `live:usgs:earthquake:us6000txg5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-24 21:45:03.425917+00; обновлено: 2026-10-30 16:05:00.289387+00

### 84. M4.9 earthquake - Kermadec Islands, New Zealand
- ID: `bc2ebefe-8f39-4824-a0b0-8473e9633719`; ключ: `live:usgs:earthquake:us6000txha`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 00:15:02.903522+00; обновлено: 2026-10-30 16:05:00.289387+00

### 85. M5.3 earthquake - 72 km NW of Finschhafen, Papua New Guinea
- ID: `de229f1d-1126-4e59-935f-b7d4227fde42`; ключ: `live:usgs:earthquake:us6000txhp`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 00:00:04.154443+00; обновлено: 2026-10-30 16:05:00.289387+00

### 86. M4.5 earthquake - 39 km WSW of Sipí, Colombia
- ID: `61852617-663c-4eba-bb74-7a641ce9303b`; ключ: `live:usgs:earthquake:us6000txhs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 03:45:00.829343+00; обновлено: 2026-10-30 16:05:00.289387+00

### 87. M5.0 earthquake - 124 km N of Metinaro, Timor Leste
- ID: `1e8e1643-cd97-41ba-a45a-60b237090b98`; ключ: `live:usgs:earthquake:us6000txim`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 04:55:02.849206+00; обновлено: 2026-10-30 16:05:00.289387+00

### 88. M5.3 earthquake - Vanuatu region
- ID: `fa7282cd-57fc-4ef8-94ac-278377a224ad`; ключ: `live:usgs:earthquake:us6000txjy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 11:45:03.88407+00; обновлено: 2026-10-30 16:05:00.289387+00

### 89. M4.5 earthquake - 72 km E of Thang, India
- ID: `c880171f-58dd-4d99-a392-0d1379206091`; ключ: `live:usgs:earthquake:us6000txk0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 13:05:04.046225+00; обновлено: 2026-10-30 16:05:00.289387+00

### 90. M4.9 earthquake - Drake Passage
- ID: `d0c6cf41-224c-4aa0-9b6d-a0ecb524ea5c`; ключ: `live:usgs:earthquake:us6000txk8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 13:05:04.010263+00; обновлено: 2026-10-30 16:05:00.289387+00

### 91. M4.7 earthquake - 80 km SW of Labuan, Indonesia
- ID: `2446db62-5275-4f4d-a2ff-06427ce46a33`; ключ: `live:usgs:earthquake:us6000txkc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 14:45:05.084375+00; обновлено: 2026-10-30 16:05:00.289387+00

### 92. M5.2 earthquake - 62 km SW of San Antonio, Chile
- ID: `e3045169-6f77-497b-ad1b-ddb2c88727b7`; ключ: `live:usgs:earthquake:us6000txme`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 16:00:04.228693+00; обновлено: 2026-10-30 16:05:00.289387+00

### 93. M4.8 earthquake - 42 km N of Ruteng, Indonesia
- ID: `31e5ea86-1033-4ea0-83bc-ff703cd3c1c9`; ключ: `live:usgs:earthquake:us6000txnq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 20:20:03.07447+00; обновлено: 2026-10-30 16:05:00.289387+00

### 94. M4.6 earthquake - 144 km SE of Lata, Solomon Islands
- ID: `02da01b2-b779-4849-8c81-ec309db37b27`; ключ: `live:usgs:earthquake:us6000txp8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 21:15:02.833573+00; обновлено: 2026-10-30 16:05:00.289387+00

### 95. M4.5 earthquake - south of the Fiji Islands
- ID: `a97eb949-b332-4dc4-9d88-9c33a8a05941`; ключ: `live:usgs:earthquake:us6000txpa`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 21:50:03.016876+00; обновлено: 2026-10-30 16:05:00.289387+00

### 96. M5.0 earthquake - 13 km N of Xunchang, China
- ID: `7275b2d8-be94-4865-9b3f-f467e52faa8a`; ключ: `live:usgs:earthquake:us6000txpf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 21:30:03.061256+00; обновлено: 2026-10-30 16:05:00.289387+00

### 97. M6.6 earthquake - 80 km ENE of Tadine, New Caledonia
- ID: `23fe1970-636f-4689-bf0c-93f485b54a46`; ключ: `live:usgs:earthquake:us6000txpi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 21:50:02.964221+00; обновлено: 2026-10-30 16:05:00.289387+00

### 98. M5.1 earthquake - 78 km ENE of Tadine, New Caledonia
- ID: `40c2d876-044c-419d-ab67-a1fb754fc7b3`; ключ: `live:usgs:earthquake:us6000txq2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-25 22:30:03.44862+00; обновлено: 2026-10-30 16:05:00.289387+00

### 99. M4.9 earthquake - 78 km NE of Tadine, New Caledonia
- ID: `d65cad2c-563a-4c5a-8c96-79d5bd8c4156`; ключ: `live:usgs:earthquake:us6000txqf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 00:05:03.294492+00; обновлено: 2026-10-30 16:05:00.289387+00

### 100. M5.5 earthquake - 61 km ENE of Tadine, New Caledonia
- ID: `a1b598df-2e22-4e67-8e3d-297a2d238a7c`; ключ: `live:usgs:earthquake:us6000txqi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 00:05:03.263524+00; обновлено: 2026-10-30 16:05:00.289387+00

### 101. M5.4 earthquake - 69 km ENE of Tadine, New Caledonia
- ID: `91a580a3-f761-4197-acea-35aefb6bd1cf`; ключ: `live:usgs:earthquake:us6000txqk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 00:25:03.154025+00; обновлено: 2026-10-30 16:05:00.289387+00

### 102. M5.0 earthquake - 15 km NNW of Xunchang, China
- ID: `451ae626-87eb-4b39-bb65-c5255fe23039`; ключ: `live:usgs:earthquake:us6000txql`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 00:25:03.11728+00; обновлено: 2026-10-30 16:05:00.289387+00

### 103. M5.3 earthquake - 58 km ENE of Tadine, New Caledonia
- ID: `89562b9c-c331-459f-b629-dc00d511f2cd`; ключ: `live:usgs:earthquake:us6000txqu`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 01:25:02.89831+00; обновлено: 2026-10-30 16:05:00.289387+00

### 104. M4.5 earthquake - Iceland region
- ID: `c4c30bdb-906e-44bc-a03c-73756e40ecff`; ключ: `live:usgs:earthquake:us6000txr0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 03:20:02.940106+00; обновлено: 2026-10-30 16:05:00.289387+00

### 105. M5.1 earthquake - 64 km ENE of Tadine, New Caledonia
- ID: `064afbf7-7325-4a16-a5b8-cf44f89f8049`; ключ: `live:usgs:earthquake:us6000txrf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 06:15:03.264718+00; обновлено: 2026-10-30 16:05:00.289387+00

### 106. M4.6 earthquake - 25 km W of Roncesvalles, Colombia
- ID: `dfca0a0a-eae5-4101-86f6-3cb9a38f219d`; ключ: `live:usgs:earthquake:us6000txrj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 07:15:04.747381+00; обновлено: 2026-10-30 16:05:00.289387+00

### 107. M5.1 earthquake - 68 km NE of Tadine, New Caledonia
- ID: `175e70df-aee5-4731-8dbf-fcbc469888d7`; ключ: `live:usgs:earthquake:us6000txrn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 07:55:05.445529+00; обновлено: 2026-10-30 16:05:00.289387+00

### 108. M5.0 earthquake - 84 km ENE of Tadine, New Caledonia
- ID: `1523297b-17d0-497c-8ff6-591adfdc28aa`; ключ: `live:usgs:earthquake:us6000txrq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 07:55:05.39891+00; обновлено: 2026-10-30 16:05:00.289387+00

### 109. M5.0 earthquake - 78 km ENE of Tadine, New Caledonia
- ID: `f72ab94b-1656-47e2-998f-176587ad9e1a`; ключ: `live:usgs:earthquake:us6000txrs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 08:50:04.145387+00; обновлено: 2026-10-30 16:05:00.289387+00

### 110. M4.7 earthquake - 97 km NE of Tadine, New Caledonia
- ID: `35ca8ac8-e4f8-4bc0-bc5e-3b55aed0f5e7`; ключ: `live:usgs:earthquake:us6000txrz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 09:30:03.821224+00; обновлено: 2026-10-30 16:05:00.289387+00

### 111. M4.8 earthquake - 97 km NE of Tadine, New Caledonia
- ID: `744764bf-5389-4c1c-a30d-3c81cb2bcb0e`; ключ: `live:usgs:earthquake:us6000txs2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 09:30:03.778334+00; обновлено: 2026-10-30 16:05:00.289387+00

### 112. M4.8 earthquake - 78 km ENE of Tadine, New Caledonia
- ID: `231818d9-fa71-4cf4-983d-8e0828f07bed`; ключ: `live:usgs:earthquake:us6000txs3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 09:45:04.342406+00; обновлено: 2026-10-30 16:05:00.289387+00

### 113. M4.7 earthquake - 71 km ENE of Tadine, New Caledonia
- ID: `e8fc806a-2635-4de4-ae63-5ef10c7c345e`; ключ: `live:usgs:earthquake:us6000txs6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 10:05:03.46847+00; обновлено: 2026-10-30 16:05:00.289387+00

### 114. M4.9 earthquake - 73 km ENE of Tadine, New Caledonia
- ID: `37e48347-5141-496a-9098-48bf5edcecdd`; ключ: `live:usgs:earthquake:us6000txse`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 10:40:04.742595+00; обновлено: 2026-10-30 16:05:00.289387+00

### 115. M4.7 earthquake - North Indian Ocean
- ID: `06d61a24-d3dc-41ff-8331-53a4ae082a54`; ключ: `live:usgs:earthquake:us6000txsh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 11:20:03.302806+00; обновлено: 2026-10-30 16:05:00.289387+00

### 116. M4.7 earthquake - 73 km ENE of Tadine, New Caledonia
- ID: `fdb6b1f8-99e1-4d1c-a05c-1bc2c2759ef5`; ключ: `live:usgs:earthquake:us6000txsy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 13:10:03.169373+00; обновлено: 2026-10-30 16:05:00.289387+00

### 117. M5.0 earthquake - 76 km NE of Tadine, New Caledonia
- ID: `5f592c51-ba01-4371-823f-43a2ac63b58b`; ключ: `live:usgs:earthquake:us6000txsz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 12:35:03.960867+00; обновлено: 2026-10-30 16:05:00.289387+00

### 118. M5.2 earthquake - 58 km NE of Tadine, New Caledonia
- ID: `c1d1832a-483e-4410-a82c-9925f60b1b3b`; ключ: `live:usgs:earthquake:us6000txt0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 12:55:02.349029+00; обновлено: 2026-10-30 16:05:00.289387+00

### 119. M4.6 earthquake - 145 km NE of Maumere, Indonesia
- ID: `d67ab89c-480a-42e8-8ad3-6e788ba1b9c1`; ключ: `live:usgs:earthquake:us6000txt8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 15:25:02.701275+00; обновлено: 2026-10-30 16:05:00.289387+00

### 120. M4.8 earthquake - 86 km NE of Tadine, New Caledonia
- ID: `f929c5d7-b7b4-48f1-bfd8-0b1c9ad7a9f5`; ключ: `live:usgs:earthquake:us6000txt9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 14:25:03.439129+00; обновлено: 2026-10-30 16:05:00.289387+00

### 121. M5.6 earthquake - 74 km ESE of Kokopo, Papua New Guinea
- ID: `ad1a041a-dd07-42d9-9f98-a759b0fec03e`; ключ: `live:usgs:earthquake:us6000txtc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 14:45:04.112888+00; обновлено: 2026-10-30 16:05:00.289387+00

### 122. M5.1 earthquake - 74 km ENE of Tadine, New Caledonia
- ID: `a4139aeb-7e41-4a37-aea2-5ca8c34582dd`; ключ: `live:usgs:earthquake:us6000txtn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 15:25:02.636677+00; обновлено: 2026-10-30 16:05:00.289387+00

### 123. M4.8 earthquake - 72 km E of Tadine, New Caledonia
- ID: `ea00c998-e5e6-4c32-a373-268519171188`; ключ: `live:usgs:earthquake:us6000txty`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 17:45:05.489556+00; обновлено: 2026-10-30 16:05:00.289387+00

### 124. M5.2 earthquake - 148 km NW of Kilmia, Yemen
- ID: `585648df-2684-4c3a-844e-f95934167683`; ключ: `live:usgs:earthquake:us6000txtz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 16:55:03.021174+00; обновлено: 2026-10-30 16:05:00.289387+00

### 125. M4.6 earthquake - south of Africa
- ID: `38412042-5086-41c7-bd08-696673eaf66e`; ключ: `live:usgs:earthquake:us6000txuc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 18:25:05.182227+00; обновлено: 2026-10-30 16:05:00.289387+00

### 126. M4.8 earthquake - 74 km ENE of Tadine, New Caledonia
- ID: `36413992-56bb-4216-9c31-4e54de0f8d03`; ключ: `live:usgs:earthquake:us6000txuf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 19:00:04.185294+00; обновлено: 2026-10-30 16:05:00.289387+00

### 127. M4.7 earthquake - 5 km N of Bowangshan, China
- ID: `e5a299db-cc33-4239-b479-c9b28189a76c`; ключ: `live:usgs:earthquake:us6000txuj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 19:00:04.143246+00; обновлено: 2026-10-30 16:05:00.289387+00

### 128. M5.0 earthquake - 52 km NNW of Ruteng, Indonesia
- ID: `df80d3f1-d4da-4418-845a-4d93b76ff196`; ключ: `live:usgs:earthquake:us6000txur`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 20:15:03.107265+00; обновлено: 2026-10-30 16:05:00.289387+00

### 129. M4.9 earthquake - 78 km ESE of Kokopo, Papua New Guinea
- ID: `134d3be4-fe02-4d7b-9873-de2cc50675cb`; ключ: `live:usgs:earthquake:us6000txv7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-26 22:25:01.668952+00; обновлено: 2026-10-30 16:05:00.289387+00

### 130. M5.0 earthquake - 61 km ENE of Tadine, New Caledonia
- ID: `7907e38f-d981-41d8-9080-b5ff1da20fa0`; ключ: `live:usgs:earthquake:us6000txvu`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 01:45:02.909116+00; обновлено: 2026-10-30 16:05:00.289387+00

### 131. M5.1 earthquake - 90 km ENE of Tadine, New Caledonia
- ID: `5eb08f3a-8139-4e00-bc96-51a86a550f94`; ключ: `live:usgs:earthquake:us6000txw5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 02:40:02.553331+00; обновлено: 2026-10-30 16:05:00.289387+00

### 132. M4.5 earthquake - 145 km WNW of Lebu, Chile
- ID: `e93d9b41-ce0c-42e6-a8f2-4d52797189de`; ключ: `live:usgs:earthquake:us6000txwk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 04:50:03.957278+00; обновлено: 2026-10-30 16:05:00.289387+00

### 133. M4.9 earthquake - 159 km ESE of Gizo, Solomon Islands
- ID: `9223a30b-cf3e-4ab1-a85c-0623b4a497b8`; ключ: `live:usgs:earthquake:us6000txwy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 05:25:04.274279+00; обновлено: 2026-10-30 16:05:00.289387+00

### 134. M4.6 earthquake - Rat Islands, Aleutian Islands, Alaska
- ID: `b277250c-ccd8-4478-ad4f-808bd284c70c`; ключ: `live:usgs:earthquake:us6000txxm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 08:10:03.44207+00; обновлено: 2026-10-30 16:05:00.289387+00

### 135. M5.0 earthquake - 191 km NW of Oula Xiuma, China
- ID: `5f37a697-2c49-4d37-8c10-7a2272fc823c`; ключ: `live:usgs:earthquake:us6000txzj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 17:05:04.536688+00; обновлено: 2026-10-30 16:05:00.289387+00

### 136. M4.5 earthquake - 78 km N of Daocheng, China
- ID: `99d8490b-2824-4b32-b1a9-62b4697afd5e`; ключ: `live:usgs:earthquake:us6000txzx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 19:25:03.219186+00; обновлено: 2026-10-30 16:05:00.289387+00

### 137. M5.0 earthquake - South Sandwich Islands region
- ID: `9891d6ea-2395-4f5c-bc19-99c74a76889c`; ключ: `live:usgs:earthquake:us6000ty0j`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 21:35:01.160642+00; обновлено: 2026-10-30 16:05:00.289387+00

### 138. M4.5 earthquake - 0 km ESE of Naisano Dua, Indonesia
- ID: `a3358187-68c9-441e-a407-11838f601196`; ключ: `live:usgs:earthquake:us6000ty0k`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 01:15:04.23931+00; обновлено: 2026-10-30 16:05:00.289387+00

### 139. M4.8 earthquake - 2 km W of Guaymate, Dominican Republic
- ID: `652d68d9-d322-48e1-a7e3-a96ca6f033cb`; ключ: `live:usgs:earthquake:us6000ty0q`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 22:15:05.322309+00; обновлено: 2026-10-30 16:05:00.289387+00

### 140. M4.6 earthquake - 19 km SW of Sipí, Colombia
- ID: `07e6c23c-0eef-49e8-8868-5d65da7b482d`; ключ: `live:usgs:earthquake:us6000ty0u`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-27 22:50:02.77048+00; обновлено: 2026-10-30 16:05:00.289387+00

### 141. M4.5 earthquake - Fiji region
- ID: `a534c9a0-c124-4bb3-b624-80acd07bab23`; ключ: `live:usgs:earthquake:us6000ty1a`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 02:55:02.465679+00; обновлено: 2026-10-30 16:05:00.289387+00

### 142. M4.5 earthquake - 74 km SE of Ossora, Russia
- ID: `8d530f46-8e67-4fee-a7e0-14d42b958d45`; ключ: `live:usgs:earthquake:us6000ty1j`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 03:35:03.471109+00; обновлено: 2026-10-30 16:05:00.289387+00

### 143. M4.9 earthquake - 43 km W of Palauig, Philippines
- ID: `be5b804b-b7b8-4dd5-b73e-3d961838074c`; ключ: `live:usgs:earthquake:us6000ty1l`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 04:55:02.52093+00; обновлено: 2026-10-30 16:05:00.289387+00

### 144. M4.8 earthquake - 80 km E of Tadine, New Caledonia
- ID: `0184ca7a-fa5f-4f01-8411-e5dc4fc54385`; ключ: `live:usgs:earthquake:us6000ty1m`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 04:15:06.159029+00; обновлено: 2026-10-30 16:05:00.289387+00

### 145. M4.9 earthquake - 195 km WSW of Port McNeill, Canada
- ID: `aed88295-463c-4c11-bc97-e9d579050936`; ключ: `live:usgs:earthquake:us6000ty27`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 03:55:03.137283+00; обновлено: 2026-10-30 16:05:00.289387+00

### 146. M5.3 earthquake - 60 km NE of Tadine, New Caledonia
- ID: `dad0f1c7-7aff-47d0-850c-619a51f95347`; ключ: `live:usgs:earthquake:us6000ty2b`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 03:55:03.100662+00; обновлено: 2026-10-30 16:05:00.289387+00

### 147. M5.1 earthquake - South Sandwich Islands region
- ID: `36b82898-ad9e-403a-be12-5542929883a7`; ключ: `live:usgs:earthquake:us6000ty2e`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 04:15:06.062548+00; обновлено: 2026-10-30 16:05:00.289387+00

### 148. M5.4 earthquake - 231 km WSW of Port McNeill, Canada
- ID: `2d67a643-1c47-4d0a-8bee-4b48a8be4e8c`; ключ: `live:usgs:earthquake:us6000ty2u`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 04:55:02.436446+00; обновлено: 2026-10-30 16:05:00.289387+00

### 149. M4.6 earthquake - northwest of the Kuril Islands
- ID: `72552c75-0764-4159-9644-3d37ef99f249`; ключ: `live:usgs:earthquake:us6000ty2w`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 05:10:03.867901+00; обновлено: 2026-10-30 16:05:00.289387+00

### 150. M4.9 earthquake - South Sandwich Islands region
- ID: `77b7d4eb-4db1-420e-827f-a4c6b3b57c2b`; ключ: `live:usgs:earthquake:us6000ty2y`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 05:10:03.904197+00; обновлено: 2026-10-30 16:05:00.289387+00

### 151. M5.1 earthquake - 78 km ENE of Tadine, New Caledonia
- ID: `f0c9c4f6-f8a7-497c-bc6a-645c0e383fc1`; ключ: `live:usgs:earthquake:us6000ty33`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 06:05:04.109669+00; обновлено: 2026-10-30 16:05:00.289387+00

### 152. M4.9 earthquake - 39 km ENE of Tadine, New Caledonia
- ID: `f55712cc-05a4-44d6-beae-502e214b455f`; ключ: `live:usgs:earthquake:us6000ty36`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 07:05:04.107915+00; обновлено: 2026-10-30 16:05:00.289387+00

### 153. M5.2 earthquake - 67 km ENE of Tadine, New Caledonia
- ID: `eeba8ba4-2f62-45fb-8656-dc2335778cb3`; ключ: `live:usgs:earthquake:us6000ty38`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 06:05:03.997187+00; обновлено: 2026-10-30 16:05:00.289387+00

### 154. M4.6 earthquake - 63 km ENE of Tadine, New Caledonia
- ID: `8f8fd1ac-b7bd-44a0-a773-28dceda2c527`; ключ: `live:usgs:earthquake:us6000ty3a`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 06:45:03.380649+00; обновлено: 2026-10-30 16:05:00.289387+00

### 155. M4.7 earthquake - 149 km NE of Hicks Bay, New Zealand
- ID: `caab1185-270a-4afa-bd87-76181779869c`; ключ: `live:usgs:earthquake:us6000ty3c`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 08:45:01.048079+00; обновлено: 2026-10-30 16:05:00.289387+00

### 156. M4.7 earthquake - 65 km E of Pilar, Philippines
- ID: `7362d01b-1ab4-4d96-b175-3ad9ac936e36`; ключ: `live:usgs:earthquake:us6000ty3w`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 10:05:03.982264+00; обновлено: 2026-10-30 16:05:00.289387+00

### 157. M5.2 earthquake - 190 km WSW of Port McNeill, Canada
- ID: `703bcc19-9bc6-4deb-b7cb-ba0d0b70464e`; ключ: `live:usgs:earthquake:us6000ty43`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 09:45:03.856571+00; обновлено: 2026-10-30 16:05:00.289387+00

### 158. M4.7 earthquake - Fiji region
- ID: `976e7063-120b-4ae3-9c7d-2170b4d6bc34`; ключ: `live:usgs:earthquake:us6000ty4w`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 12:35:05.276424+00; обновлено: 2026-10-30 16:05:00.289387+00

### 159. M5.4 earthquake - north of Svalbard
- ID: `88783d68-2ffc-436e-bf11-fa543c1034a2`; ключ: `live:usgs:earthquake:us6000ty57`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 13:50:03.381496+00; обновлено: 2026-10-30 16:05:00.289387+00

### 160. M4.9 earthquake - 22 km WNW of Malango, Solomon Islands
- ID: `138e90e7-d708-4015-aae2-32b894309a6a`; ключ: `live:usgs:earthquake:us6000ty5b`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 15:00:10.786964+00; обновлено: 2026-10-30 16:05:00.289387+00

### 161. M4.7 earthquake - 115 km WSW of Banda Aceh, Indonesia
- ID: `5154ba47-9f54-43d2-be6f-3d25046e923b`; ключ: `live:usgs:earthquake:us6000ty5h`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 16:55:06.487252+00; обновлено: 2026-10-30 16:05:00.289387+00

### 162. M4.9 earthquake - 124 km SE of Pondaguitan, Philippines
- ID: `afc54cdd-6a32-4f14-89ff-d120a028a81c`; ключ: `live:usgs:earthquake:us6000ty5m`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 15:40:04.531432+00; обновлено: 2026-10-30 16:05:00.289387+00

### 163. M4.8 earthquake - 155 km NNW of Kilmia, Yemen
- ID: `52ce9f9e-29d3-45d4-9687-47c8d82da8b4`; ключ: `live:usgs:earthquake:us6000ty71`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 18:05:07.444741+00; обновлено: 2026-10-30 16:05:00.289387+00

### 164. M4.6 earthquake - 36 km SE of Hualien City, Taiwan
- ID: `304ec0ad-afd3-4ca3-957d-df5cbc85411c`; ключ: `live:usgs:earthquake:us6000ty73`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 19:00:09.389958+00; обновлено: 2026-10-30 16:05:00.289387+00

### 165. M4.9 earthquake - 2 km SW of Sakai, Japan
- ID: `14041062-c598-4686-9a38-022296e9b0d9`; ключ: `live:usgs:earthquake:us6000ty7u`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-28 20:15:06.070832+00; обновлено: 2026-10-30 16:05:00.289387+00

### 166. M4.5 earthquake - 173 km SE of Atlasovo, Russia
- ID: `3176c79f-8128-48de-b4c8-c048db651d52`; ключ: `live:usgs:earthquake:us6000ty9i`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 01:05:04.788784+00; обновлено: 2026-10-30 16:05:00.289387+00

### 167. M5.3 earthquake - 76 km NE of Tadine, New Caledonia
- ID: `9440375a-9816-4f53-8242-76dbeae32249`; ключ: `live:usgs:earthquake:us6000tya5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 03:45:03.691399+00; обновлено: 2026-10-30 16:05:00.289387+00

### 168. M4.8 earthquake - South Sandwich Islands region
- ID: `80e245e1-3ec2-45e9-a911-558d0c2d3cf7`; ключ: `live:usgs:earthquake:us6000tyab`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 04:45:04.089868+00; обновлено: 2026-10-30 16:05:00.289387+00

### 169. M4.8 earthquake - South Sandwich Islands region
- ID: `42127100-7657-43bb-8c14-d4f86875da1d`; ключ: `live:usgs:earthquake:us6000tyat`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 07:05:03.950338+00; обновлено: 2026-10-30 16:05:00.289387+00

### 170. M4.5 earthquake - 95 km SSW of Ocós, Guatemala
- ID: `c7bb769d-1e3e-42ab-8191-6024077b3716`; ключ: `live:usgs:earthquake:us6000tyb6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 12:25:05.130741+00; обновлено: 2026-10-30 16:05:00.289387+00

### 171. M4.5 earthquake - 96 km ENE of Alianza Cristiana, Peru
- ID: `e195ca2e-1091-4d9e-9bdf-5442404e5a56`; ключ: `live:usgs:earthquake:us6000tybk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 10:55:03.804135+00; обновлено: 2026-10-30 16:05:00.289387+00

### 172. M5.0 earthquake - 77 km ENE of Tadine, New Caledonia
- ID: `fc92e473-e965-482e-a4d8-a228251ba518`; ключ: `live:usgs:earthquake:us6000tybr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 11:15:05.184245+00; обновлено: 2026-10-30 16:05:00.289387+00

### 173. M4.8 earthquake - 98 km SW of Port-Vila, Vanuatu
- ID: `43100e5a-27a6-49c3-ac71-4cdc0dc28018`; ключ: `live:usgs:earthquake:us6000tybs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 11:50:04.954445+00; обновлено: 2026-10-30 16:05:00.289387+00

### 174. M5.4 earthquake - 99 km SSE of Pangai, Tonga
- ID: `d46bdd24-f6ff-44b1-867b-4f05e00ce6e1`; ключ: `live:usgs:earthquake:us6000tyc1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 13:05:04.30754+00; обновлено: 2026-10-30 16:05:00.289387+00

### 175. M5.6 earthquake - southern Mid-Atlantic Ridge
- ID: `3ab408c7-b9c7-4831-a1a8-a97d2a2a7bcb`; ключ: `live:usgs:earthquake:us6000tyc3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 13:45:02.867756+00; обновлено: 2026-10-30 16:05:00.289387+00

### 176. M5.0 earthquake - 58 km NW of Pante Makasar, Timor Leste
- ID: `6a491161-aa6f-4d05-b158-98f9e5afdfe4`; ключ: `live:usgs:earthquake:us6000tyc9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 15:20:04.007021+00; обновлено: 2026-10-30 16:05:00.289387+00

### 177. M4.9 earthquake - South Sandwich Islands region
- ID: `3069e4d7-d51e-4ed3-9e17-ef8a1391c1bf`; ключ: `live:usgs:earthquake:us6000tyck`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 17:50:03.307492+00; обновлено: 2026-10-30 16:05:00.289387+00

### 178. M4.8 earthquake - 44 km NNE of Fangale’ounga, Tonga
- ID: `3fe5d0b8-d814-484d-b9ed-119382098976`; ключ: `live:usgs:earthquake:us6000tycv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 17:30:03.867394+00; обновлено: 2026-10-30 16:05:00.289387+00

### 179. M4.6 earthquake - West Chile Rise
- ID: `6d518b54-4d29-419a-abd4-e75a1a8824ad`; ключ: `live:usgs:earthquake:us6000tycz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 18:10:03.533463+00; обновлено: 2026-10-30 16:05:00.289387+00

### 180. M4.7 earthquake - 49 km N of Dicabisagan, Philippines
- ID: `45c6b46f-1542-4a9c-8061-63af80007a8a`; ключ: `live:usgs:earthquake:us6000tyf0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 21:20:03.485493+00; обновлено: 2026-10-30 16:05:00.289387+00

### 181. M4.5 earthquake - 15 km SW of San Antonio, Colombia
- ID: `c3fa7bb4-9a70-4cef-bf50-d2f9eef7d40d`; ключ: `live:usgs:earthquake:us6000tyfk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-29 22:35:03.276039+00; обновлено: 2026-10-30 16:05:00.289387+00

### 182. M4.8 earthquake - 75 km NE of Tadine, New Caledonia
- ID: `d279c1a0-d5c2-4521-8994-c6ba73f561d9`; ключ: `live:usgs:earthquake:us6000tygq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 01:45:01.173925+00; обновлено: 2026-10-30 16:05:00.289387+00

### 183. M4.8 earthquake - 18 km SW of Tayaman, Philippines
- ID: `32059805-403a-4169-b8bd-905205a03bcd`; ключ: `live:usgs:earthquake:us6000tygs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 02:05:04.18664+00; обновлено: 2026-10-30 16:05:00.289387+00

### 184. M4.5 earthquake - 104 km SSE of Sarangani, Philippines
- ID: `f3fa2002-96fb-45e2-bdfb-e8f173d680d3`; ключ: `live:usgs:earthquake:us6000tygz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 03:05:06.312138+00; обновлено: 2026-10-30 16:05:00.289387+00

### 185. M4.5 earthquake - 112 km SSW of Banda Aceh, Indonesia
- ID: `53563d83-8642-4252-867c-ccd75ab0ce10`; ключ: `live:usgs:earthquake:us6000tyh0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 03:05:06.272638+00; обновлено: 2026-10-30 16:05:00.289387+00

### 186. M5.4 earthquake - Balleny Islands region
- ID: `6828c4d3-28d4-4507-8222-50ec0d7c913f`; ключ: `live:usgs:earthquake:us6000tyhi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 05:25:04.282128+00; обновлено: 2026-10-30 16:05:00.289387+00

### 187. M5.6 earthquake - 74 km S of Yonakuni, Japan
- ID: `78dcabd3-a446-4451-a208-589601184bf7`; ключ: `live:usgs:earthquake:us6000tyhk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 05:25:04.245392+00; обновлено: 2026-10-30 16:05:00.289387+00

### 188. M4.6 earthquake - 3 km W of Thívai, Greece
- ID: `b1878255-ce10-4a90-b1ae-9e66dcbb7143`; ключ: `live:usgs:earthquake:us6000tyhn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 09:20:04.016955+00; обновлено: 2026-10-30 16:05:00.289387+00

### 189. M5.0 earthquake - 83 km NE of Tadine, New Caledonia
- ID: `00881088-5b65-4016-be5d-6946c149f46e`; ключ: `live:usgs:earthquake:us6000tyid`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 07:20:03.972373+00; обновлено: 2026-10-30 16:05:00.289387+00

### 190. M5.2 earthquake - Balleny Islands region
- ID: `ca2218f2-057e-4f66-822c-3d39ce34a229`; ключ: `live:usgs:earthquake:us6000tyik`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 07:55:03.670872+00; обновлено: 2026-10-30 16:05:00.289387+00

### 191. M5.1 earthquake - 121 km S of Kokopo, Papua New Guinea
- ID: `b1dcfaaf-c568-4536-8944-d50389887aa6`; ключ: `live:usgs:earthquake:us6000tyit`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 08:45:03.674837+00; обновлено: 2026-10-30 16:05:00.289387+00

### 192. M5.0 earthquake - 27 km N of Kupang, Indonesia
- ID: `208116cd-0c4a-49e0-9684-b165a5fc698f`; ключ: `live:usgs:earthquake:us6000tyjb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 11:25:06.07992+00; обновлено: 2026-10-30 16:05:00.289387+00

### 193. M5.0 earthquake - 142 km SE of Petropavlovsk-Kamchatsky, Russia
- ID: `dd8aa9c8-6978-4b9e-be31-ae99a0d08b9e`; ключ: `live:usgs:earthquake:us6000tyku`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 18:55:05.130223+00; обновлено: 2026-10-30 16:05:00.289387+00

### 194. M4.9 earthquake - 136 km SE of Petropavlovsk-Kamchatsky, Russia
- ID: `61926a2e-aa8a-4e22-9263-358fe17325b6`; ключ: `live:usgs:earthquake:us6000tykw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 19:15:05.404508+00; обновлено: 2026-10-30 16:05:00.289387+00

### 195. M4.6 earthquake - 131 km SE of Itoman, Japan
- ID: `a5762050-ff4d-49cb-a81a-d6c265595724`; ключ: `live:usgs:earthquake:us6000tym9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 21:55:04.66314+00; обновлено: 2026-10-30 16:05:00.289387+00

### 196. M5.6 earthquake - 94 km SW of Tamarindo, Costa Rica
- ID: `e5d87e30-add7-4838-b8bb-ae322073057b`; ключ: `live:usgs:earthquake:us6000tymj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-09-30 22:15:01.207087+00; обновлено: 2026-10-30 16:05:00.289387+00

### 197. M4.6 earthquake - 83 km NE of Ruteng, Indonesia
- ID: `2502f364-3fc1-4018-9434-b53951bca91b`; ключ: `live:usgs:earthquake:us6000tyw9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 10:05:03.146493+00; обновлено: 2026-10-30 16:05:00.289387+00

### 198. M5.1 earthquake - 171 km SE of Lata, Solomon Islands
- ID: `d3b90db8-93dd-4047-b0a6-cf7d915c1c18`; ключ: `live:usgs:earthquake:us6000tywu`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 10:05:03.124834+00; обновлено: 2026-10-30 16:05:00.289387+00

### 199. M5.1 earthquake - 176 km SE of Lata, Solomon Islands
- ID: `4cea07df-c6da-4e60-9627-ff102024909b`; ключ: `live:usgs:earthquake:us6000tyx0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 10:05:03.101874+00; обновлено: 2026-10-30 16:05:00.289387+00

### 200. M4.5 earthquake - 2 km NE of Satte, Japan
- ID: `d1a67d4c-577b-497b-8345-cfe8915c6a40`; ключ: `live:usgs:earthquake:us6000tyxk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 10:05:03.076573+00; обновлено: 2026-10-30 16:05:00.289387+00

### 201. M4.9 earthquake - 97 km S of Panguna, Papua New Guinea
- ID: `fb7e8c11-07e6-47ff-9f8d-32bff935e056`; ключ: `live:usgs:earthquake:us6000tyzg`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 10:05:03.053288+00; обновлено: 2026-10-30 16:05:00.289387+00

### 202. M5.0 earthquake - south of the Fiji Islands
- ID: `715ece1a-7fe7-409d-90ff-6c25a82f2c66`; ключ: `live:usgs:earthquake:us6000tyzi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 10:05:03.029307+00; обновлено: 2026-10-30 16:05:00.289387+00

### 203. M5.1 earthquake - 159 km SE of Gizo, Solomon Islands
- ID: `247c95f6-a648-478f-adc3-95dbe299973c`; ключ: `live:usgs:earthquake:us6000tyzl`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 10:05:03.004905+00; обновлено: 2026-10-30 16:05:00.289387+00

### 204. M4.8 earthquake - 192 km WNW of Tobelo, Indonesia
- ID: `1330b31c-144f-4f0f-bc80-4e0cf9050108`; ключ: `live:usgs:earthquake:us6000tyzt`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 10:05:02.97881+00; обновлено: 2026-10-30 16:05:00.289387+00

### 205. M4.8 earthquake - 35 km SSW of El Colomo, Mexico
- ID: `9654a734-5e4c-4b00-bdbf-40d2cbbe3903`; ключ: `live:usgs:earthquake:us6000tyzx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 10:05:02.925715+00; обновлено: 2026-10-30 16:05:00.289387+00

### 206. M4.5 earthquake - 101 km NE of Ruteng, Indonesia
- ID: `1b144b8a-2da6-4d71-89c3-538cbf348a9c`; ключ: `live:usgs:earthquake:us6000tyzy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 10:05:02.956236+00; обновлено: 2026-10-30 16:05:00.289387+00

### 207. M5.0 earthquake - 63 km SW of Panguna, Papua New Guinea
- ID: `a978bf3e-4818-45f9-a9c6-28c58f3d2ff4`; ключ: `live:usgs:earthquake:us6000tz0x`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 11:35:02.057036+00; обновлено: 2026-10-30 16:05:00.289387+00

### 208. M5.0 earthquake - 6 km E of Inglewood, New Zealand
- ID: `0216dfa8-2022-4419-b9dc-bc794e0c7f52`; ключ: `live:usgs:earthquake:us6000tz1c`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 14:35:04.407978+00; обновлено: 2026-10-30 16:05:00.289387+00

### 209. M4.8 earthquake - 78 km WSW of San Nicolas, Philippines
- ID: `3ef2d6b7-74a5-4e3a-830d-00e902738805`; ключ: `live:usgs:earthquake:us6000tz1q`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 15:55:05.735805+00; обновлено: 2026-10-30 16:05:00.289387+00

### 210. M4.7 earthquake - 5 km NNE of Korumburra, Australia
- ID: `9c197034-1602-4b2d-ac09-728505782199`; ключ: `live:usgs:earthquake:us6000tz1y`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 16:35:05.903912+00; обновлено: 2026-10-30 16:05:00.289387+00

### 211. M5.0 earthquake - 26 km SSW of Güiria, Venezuela
- ID: `e30bd8f2-8473-4227-8a86-08a63fb5ba12`; ключ: `live:usgs:earthquake:us6000tz5h`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 16:55:06.061626+00; обновлено: 2026-10-30 16:05:00.289387+00

### 212. M5.8 earthquake - 165 km SSE of Vilyuchinsk, Russia
- ID: `3719e90b-b036-4393-96d0-0c6d2403836f`; ключ: `live:usgs:earthquake:us6000tz62`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 17:15:03.236545+00; обновлено: 2026-10-30 16:05:00.289387+00

### 213. M5.0 earthquake - 179 km SSE of Vilyuchinsk, Russia
- ID: `4a56df83-084f-471a-8c8b-df88a3108768`; ключ: `live:usgs:earthquake:us6000tz7b`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 18:55:03.224206+00; обновлено: 2026-10-30 16:05:00.289387+00

### 214. M4.9 earthquake - 136 km SSE of Vilyuchinsk, Russia
- ID: `53dbe712-8a11-4d52-8e7e-3d86c14e36bd`; ключ: `live:usgs:earthquake:us6000tz8a`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 21:10:03.38312+00; обновлено: 2026-10-30 16:05:00.289387+00

### 215. M4.6 earthquake - 67 km ESE of Kokopo, Papua New Guinea
- ID: `559d435b-1fa1-431e-ba19-3863d4bb9643`; ключ: `live:usgs:earthquake:us6000tz8b`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 21:50:03.105352+00; обновлено: 2026-10-30 16:05:00.289387+00

### 216. M5.1 earthquake - 199 km SSE of Vilyuchinsk, Russia
- ID: `80952604-f99a-4fc0-9775-639d9705a56a`; ключ: `live:usgs:earthquake:us6000tz8c`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 22:25:03.216337+00; обновлено: 2026-10-30 16:05:00.289387+00

### 217. M4.5 earthquake - 86 km E of Noda, Japan
- ID: `95baabf0-484d-4eb1-a31a-11572850d45d`; ключ: `live:usgs:earthquake:us6000tz8f`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 14:10:03.573349+00; обновлено: 2026-10-30 16:05:00.289387+00

### 218. M4.6 earthquake - 46 km SSW of Paratunka, Russia
- ID: `86b4b4fe-c2c5-438c-939e-0f82480916a4`; ключ: `live:usgs:earthquake:us6000tz8g`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 15:45:06.566315+00; обновлено: 2026-10-30 16:05:00.289387+00

### 219. M5.0 earthquake - 171 km SE of Vilyuchinsk, Russia
- ID: `c85bd7c4-ba9d-4978-afa7-84a874f9518b`; ключ: `live:usgs:earthquake:us6000tz8l`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-02 21:30:03.257749+00; обновлено: 2026-10-30 16:05:00.289387+00

### 220. M4.7 earthquake - 153 km SSE of Vilyuchinsk, Russia
- ID: `f7d7d8c2-324d-458c-bc3f-20f5c81dd7fa`; ключ: `live:usgs:earthquake:us6000tz9s`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 01:05:04.987274+00; обновлено: 2026-10-30 16:05:00.289387+00

### 221. M4.6 earthquake - 174 km SSE of Vilyuchinsk, Russia
- ID: `8e4fd7f5-b531-4d19-894c-62c9f927711c`; ключ: `live:usgs:earthquake:us6000tz9t`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 01:05:04.960692+00; обновлено: 2026-10-30 16:05:00.289387+00

### 222. M4.8 earthquake - 121 km SSE of Vilyuchinsk, Russia
- ID: `76352e6c-5377-45f7-bfc3-711bb3b79244`; ключ: `live:usgs:earthquake:us6000tz9v`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 01:25:03.333828+00; обновлено: 2026-10-30 16:05:00.289387+00

### 223. M4.5 earthquake - 7 km NNW of Ibusuki, Japan
- ID: `762db504-f66d-4642-a447-80a558b609b9`; ключ: `live:usgs:earthquake:us6000tz9w`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 02:25:06.547999+00; обновлено: 2026-10-30 16:05:00.289387+00

### 224. M5.0 earthquake - 163 km SE of Petropavlovsk-Kamchatsky, Russia
- ID: `8b11ed7a-2adc-4ac8-ad77-75c6592544b8`; ключ: `live:usgs:earthquake:us6000tzal`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 03:25:03.290009+00; обновлено: 2026-10-30 16:05:00.289387+00

### 225. M4.8 earthquake - 112 km S of Koshima, Japan
- ID: `1298d268-67da-4e30-a684-18138a071e4e`; ключ: `live:usgs:earthquake:us6000tzb5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 06:45:03.287129+00; обновлено: 2026-10-30 16:05:00.289387+00

### 226. M4.5 earthquake - Kermadec Islands region
- ID: `f8dc89e6-17c2-40a8-b4f5-7f417b6defd8`; ключ: `live:usgs:earthquake:us6000tzcm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 14:30:04.521129+00; обновлено: 2026-10-30 16:05:00.289387+00

### 227. M4.7 earthquake - 52 km SSW of Vilyuchinsk, Russia
- ID: `8f0cd327-8883-4db3-845b-b4ab27bb75c5`; ключ: `live:usgs:earthquake:us6000tzd5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 16:05:06.627986+00; обновлено: 2026-10-30 16:05:00.289387+00

### 228. M4.6 earthquake - 76 km NNE of Lae, Papua New Guinea
- ID: `913001a8-6c31-43c1-bf02-fc4bdfd50cd3`; ключ: `live:usgs:earthquake:us6000tzdj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 18:00:05.368557+00; обновлено: 2026-10-30 16:05:00.289387+00

### 229. M4.9 earthquake - 72 km NE of Sittwe, Burma (Myanmar)
- ID: `68e378a3-6ae6-42fe-9c89-8f0f3cffc016`; ключ: `live:usgs:earthquake:us6000tzdp`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 18:55:07.141852+00; обновлено: 2026-10-30 16:05:00.289387+00

### 230. M5.1 earthquake - 182 km SSE of Vilyuchinsk, Russia
- ID: `16282db3-0ce1-4fb1-bb33-138d09e2dcd8`; ключ: `live:usgs:earthquake:us6000tze2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 20:30:04.334633+00; обновлено: 2026-10-30 16:05:00.289387+00

### 231. M4.5 earthquake - 121 km SW of Puerto Madero, Mexico
- ID: `4ceb234f-eaf1-46e4-8a8a-ead325f67e8c`; ключ: `live:usgs:earthquake:us6000tze6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 21:05:06.227692+00; обновлено: 2026-10-30 16:05:00.289387+00

### 232. M5.9 earthquake - 39 km WSW of Tambolaka, Indonesia
- ID: `d7b9e5ea-6473-4b9d-81af-2a9aadf7230b`; ключ: `live:usgs:earthquake:us6000tzer`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 23:15:03.60098+00; обновлено: 2026-10-30 16:05:00.289387+00

### 233. M4.5 earthquake - 293 km SSE of Tabiauan, Philippines
- ID: `a4c282af-dc5e-442a-a7bf-ab9d74ca50ef`; ключ: `live:usgs:earthquake:us6000tzf7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-03 23:50:03.735778+00; обновлено: 2026-10-30 16:05:00.289387+00

### 234. M5.6 earthquake - 80 km S of Banda Aceh, Indonesia
- ID: `a0a8b60e-6ee3-4814-9404-0c48aeb260df`; ключ: `live:usgs:earthquake:us6000tzfg`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 00:10:04.131089+00; обновлено: 2026-10-30 16:05:00.289387+00

### 235. M4.9 earthquake - 21 km NE of Lae, Papua New Guinea
- ID: `8bf5a985-6cae-4a14-ba19-15c9cad765b4`; ключ: `live:usgs:earthquake:us6000tzfv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 02:15:03.555181+00; обновлено: 2026-10-30 16:05:00.289387+00

### 236. M4.9 earthquake - South Sandwich Islands region
- ID: `a85741a9-d61a-4474-ba44-5e45900ab764`; ключ: `live:usgs:earthquake:us6000tzg0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 03:15:03.72308+00; обновлено: 2026-10-30 16:05:00.289387+00

### 237. M4.6 earthquake - 121 km WNW of Chauk, Burma (Myanmar)
- ID: `42eb48a0-c43c-4ddc-886d-6d21a186554c`; ключ: `live:usgs:earthquake:us6000tzh0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 06:35:04.257548+00; обновлено: 2026-10-30 16:05:00.289387+00

### 238. M5.0 earthquake - 37 km N of Ruteng, Indonesia
- ID: `3c03811f-b678-416e-b2b6-ea76db57d0e5`; ключ: `live:usgs:earthquake:us6000tzi5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 10:35:04.122598+00; обновлено: 2026-10-30 16:05:00.289387+00

### 239. M4.8 earthquake - 43 km N of Ruteng, Indonesia
- ID: `05a65a6a-ca35-4209-8a28-15e8df901d99`; ключ: `live:usgs:earthquake:us6000tzi8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 11:30:04.938809+00; обновлено: 2026-10-30 16:05:00.289387+00

### 240. M4.6 earthquake - 121 km SW of Kokopo, Papua New Guinea
- ID: `96f2a6e2-9258-4cec-946d-e07ef1385482`; ключ: `live:usgs:earthquake:us6000tzic`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 12:25:04.363863+00; обновлено: 2026-10-30 16:05:00.289387+00

### 241. M5.5 earthquake - Volcano Islands, Japan region
- ID: `99094000-34ad-4953-baf8-424d1ae21e63`; ключ: `live:usgs:earthquake:us6000tzid`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 11:45:03.93612+00; обновлено: 2026-10-30 16:05:00.289387+00

### 242. M4.7 earthquake - 21 km SSE of Saimbeyli, Turkey
- ID: `ab2a08ab-692b-4e71-859d-6a02106db5f4`; ключ: `live:usgs:earthquake:us6000tzif`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 12:05:03.986426+00; обновлено: 2026-10-30 16:05:00.289387+00

### 243. M4.7 earthquake - 22 km E of Feke, Turkey
- ID: `fe43231d-9573-4c14-9bd9-b240f77a6c9f`; ключ: `live:usgs:earthquake:us6000tzil`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 12:25:04.27719+00; обновлено: 2026-10-30 16:05:00.289387+00

### 244. M5.0 earthquake - 21 km ESE of Feke, Turkey
- ID: `145cb2da-9c46-4c93-8836-294ce563bb92`; ключ: `live:usgs:earthquake:us6000tzip`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 12:05:03.943872+00; обновлено: 2026-10-30 16:05:00.289387+00

### 245. M4.6 earthquake - 110 km S of Dampit, Indonesia
- ID: `b437480a-8021-4ed1-9049-e1f185a7cdca`; ключ: `live:usgs:earthquake:us6000tziz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 13:25:03.859049+00; обновлено: 2026-10-30 16:05:00.289387+00

### 246. M5.0 earthquake - 295 km S of Burica, Panama
- ID: `724b13d2-5479-4634-bc95-23b70fc0af7b`; ключ: `live:usgs:earthquake:us6000tzj8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 14:45:04.734516+00; обновлено: 2026-10-30 16:05:00.289387+00

### 247. M4.8 earthquake - 32 km SSE of Jurm, Afghanistan
- ID: `d501ed1f-8b37-475c-9b83-650e9c0a1f0d`; ключ: `live:usgs:earthquake:us6000tzkn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-04 21:00:05.173161+00; обновлено: 2026-10-30 16:05:00.289387+00

### 248. M5.3 earthquake - central Mid-Atlantic Ridge
- ID: `839d7181-3534-4493-8590-fc3b34872949`; ключ: `live:usgs:earthquake:us6000tzlp`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 01:55:03.115554+00; обновлено: 2026-10-30 16:05:00.289387+00

### 249. M4.5 earthquake - Kuril Islands
- ID: `460f4f79-9387-4351-b753-5c6dbed5ff62`; ключ: `live:usgs:earthquake:us6000tzm7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 04:45:05.666541+00; обновлено: 2026-10-30 16:05:00.289387+00

### 250. M5.0 earthquake - 71 km E of ‘Ohonua, Tonga
- ID: `a5ff24e6-eeba-4ae3-baa3-cee25b990ba8`; ключ: `live:usgs:earthquake:us6000tzme`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 06:05:03.418163+00; обновлено: 2026-10-30 16:05:00.289387+00

### 251. M4.8 earthquake - 191 km ESE of Sarangani, Philippines
- ID: `05579208-1852-46f2-8a29-facbfbbe4bc4`; ключ: `live:usgs:earthquake:us6000tzmk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 07:00:04.413657+00; обновлено: 2026-10-30 16:05:00.289387+00

### 252. M4.9 earthquake - Volcano Islands, Japan region
- ID: `6bfa513c-07ff-4f7b-9bea-156022cd7294`; ключ: `live:usgs:earthquake:us6000tzmt`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 07:55:03.230651+00; обновлено: 2026-10-30 16:05:00.289387+00

### 253. M5.0 earthquake - 187 km ENE of Saipan, Northern Mariana Islands
- ID: `3b8e4bd6-6a5d-4a9d-8fec-a55e4d7c3efb`; ключ: `live:usgs:earthquake:us6000tzna`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 11:55:03.011205+00; обновлено: 2026-10-30 16:05:00.289387+00

### 254. M4.6 earthquake - 21 km S of Luganville, Vanuatu
- ID: `cf8a500f-9c1f-4a68-afbc-5594f37ca566`; ключ: `live:usgs:earthquake:us6000tznh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 12:15:03.898851+00; обновлено: 2026-10-30 16:05:00.289387+00

### 255. M4.7 earthquake - 75 km NNE of Yonakuni, Japan
- ID: `a9916aa6-7dbd-4c43-9d34-55d5ed1e886f`; ключ: `live:usgs:earthquake:us6000tznu`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 14:30:04.505089+00; обновлено: 2026-10-30 16:05:00.289387+00

### 256. M4.7 earthquake - 105 km WNW of Höfn, Iceland
- ID: `8a0eaff4-71b3-445c-80fe-e35af6479204`; ключ: `live:usgs:earthquake:us6000tzpq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 18:10:05.064679+00; обновлено: 2026-10-30 16:05:00.289387+00

### 257. M4.6 earthquake - 12 km ENE of Metahāra, Ethiopia
- ID: `79c0ea6e-e6cf-4f97-86fa-13cc81b65d80`; ключ: `live:usgs:earthquake:us6000tzry`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 20:25:02.908183+00; обновлено: 2026-10-30 16:05:00.289387+00

### 258. M5.0 earthquake - south of the Fiji Islands
- ID: `fd5e764b-d649-4d15-b66d-ab337840401c`; ключ: `live:usgs:earthquake:us6000tzsc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-05 21:05:03.479716+00; обновлено: 2026-10-30 16:05:00.289387+00

### 259. M4.5 earthquake - 39 km SW of Tambolaka, Indonesia
- ID: `f2a19130-010b-423c-8ad4-83912d014948`; ключ: `live:usgs:earthquake:us6000tzss`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 02:45:01.543625+00; обновлено: 2026-10-30 16:05:00.289387+00

### 260. M4.8 earthquake - 146 km WNW of Panguna, Papua New Guinea
- ID: `39a8381d-5a69-48c7-ab59-ad6df14f3d7d`; ключ: `live:usgs:earthquake:us6000tztg`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 03:15:01.825301+00; обновлено: 2026-10-30 16:05:00.289387+00

### 261. M4.6 earthquake - 31 km S of Tezpur, India
- ID: `7438b738-4dca-4411-bf3f-7459ce9220dc`; ключ: `live:usgs:earthquake:us6000tzth`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 03:15:01.774815+00; обновлено: 2026-10-30 16:05:00.289387+00

### 262. M4.8 earthquake - 86 km N of Ruteng, Indonesia
- ID: `50f014fa-ab19-4769-b264-c798dc2f225f`; ключ: `live:usgs:earthquake:us6000tzuj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 04:15:02.073373+00; обновлено: 2026-10-30 16:05:00.289387+00

### 263. M4.6 earthquake - Izu Islands, Japan region
- ID: `3b5d37cd-83af-4dcd-9a2f-11f69ddf6cf9`; ключ: `live:usgs:earthquake:us6000tzuq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 05:15:01.524175+00; обновлено: 2026-10-30 16:05:00.289387+00

### 264. M4.9 earthquake - State of Yap, Federated States of Micronesia
- ID: `95d2a449-afc8-4881-af1d-68cd9027f015`; ключ: `live:usgs:earthquake:us6000tzus`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 05:15:01.460509+00; обновлено: 2026-10-30 16:05:00.289387+00

### 265. M4.7 earthquake - 36 km WNW of Ollagüe, Chile
- ID: `98195649-0b2e-4e4c-a1c6-270463634abb`; ключ: `live:usgs:earthquake:us6000tzv6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 06:45:03.780449+00; обновлено: 2026-10-30 16:05:00.289387+00

### 266. M4.5 earthquake - 60 km WNW of Colchani, Bolivia
- ID: `3250b897-c2a4-46b9-97a5-b704bc3bc37d`; ключ: `live:usgs:earthquake:us6000tzva`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 07:45:04.0377+00; обновлено: 2026-10-30 16:05:00.289387+00

### 267. M4.9 earthquake - 55 km ESE of Kokopo, Papua New Guinea
- ID: `9c9b0dea-325f-41f8-91c8-503e3fb9d578`; ключ: `live:usgs:earthquake:us6000tzvn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 09:15:04.200992+00; обновлено: 2026-10-30 16:05:00.289387+00

### 268. M4.9 earthquake - 48 km NNE of Semporna, Malaysia
- ID: `74e22f81-c43d-4f66-87e2-1f794d7b4ac5`; ключ: `live:usgs:earthquake:us6000tzwg`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 14:15:05.347909+00; обновлено: 2026-10-30 16:05:00.289387+00

### 269. M4.5 earthquake - Kermadec Islands region
- ID: `aa6d435d-c782-45e0-86d3-04e2e08bd994`; ключ: `live:usgs:earthquake:us6000tzwi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 15:45:01.612746+00; обновлено: 2026-10-30 16:05:00.289387+00

### 270. M4.7 earthquake - Chagos Archipelago region
- ID: `5b72a19e-941f-4198-a7f4-5bb8a72037e8`; ключ: `live:usgs:earthquake:us6000u01m`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 16:15:04.68978+00; обновлено: 2026-10-30 16:05:00.289387+00

### 271. M5.9 earthquake - 264 km SSW of Severo-Kuril’sk, Russia
- ID: `a1c72e4f-3f79-4bf0-82d6-2ba5263b3137`; ключ: `live:usgs:earthquake:us6000u0hy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 17:15:04.338443+00; обновлено: 2026-10-30 16:05:00.289387+00

### 272. M5.1 earthquake - 34 km NNW of Bāgeshwar, India
- ID: `257b2a0e-ec90-4855-b9e8-dbfef71285ad`; ключ: `live:usgs:earthquake:us6000u0hz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 17:15:04.287565+00; обновлено: 2026-10-30 16:05:00.289387+00

### 273. M4.8 earthquake - 85 km ENE of Shikotan, Russia
- ID: `fd4b10c7-33d6-4205-8eb0-db6c992eed2a`; ключ: `live:usgs:earthquake:us6000u0ji`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 21:00:02.768051+00; обновлено: 2026-10-30 16:05:00.289387+00

### 274. M4.9 earthquake - 114 km SW of Turpan, China
- ID: `17f6a383-d522-446b-8c0f-8c7d38fefe4f`; ключ: `live:usgs:earthquake:us6000u0jq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 21:30:01.985063+00; обновлено: 2026-10-30 16:05:00.289387+00

### 275. M4.5 earthquake - 43 km WNW of Bengkulu, Indonesia
- ID: `f80e0100-4cf8-4c01-a172-0956e5a13da0`; ключ: `live:usgs:earthquake:us6000u0k2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 21:30:01.912936+00; обновлено: 2026-10-30 16:05:00.289387+00

### 276. M4.6 earthquake - 14 km NE of Mataram, Indonesia
- ID: `75fc12e1-03a9-436e-b536-5a25a68f2925`; ключ: `live:usgs:earthquake:us6000u0km`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 21:30:01.872513+00; обновлено: 2026-10-30 16:05:00.289387+00

### 277. M4.9 earthquake - 189 km SW of Abepura, Indonesia
- ID: `8a65cbb7-40f0-4294-8aac-0bf96dd6b8d4`; ключ: `live:usgs:earthquake:us6000u0le`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-06 22:30:01.548595+00; обновлено: 2026-10-30 16:05:00.289387+00

### 278. M4.7 earthquake - Kermadec Islands, New Zealand
- ID: `6244fe79-38d8-4433-b53b-2101567f4ca3`; ключ: `live:usgs:earthquake:us6000u0ll`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 03:30:03.515677+00; обновлено: 2026-10-30 16:05:00.289387+00

### 279. M4.5 earthquake - 37 km ESE of Iwaki, Japan
- ID: `45852e70-b049-4b60-9cb1-e4ac3f2c12a1`; ключ: `live:usgs:earthquake:us6000u0mr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 04:30:05.982515+00; обновлено: 2026-10-30 16:05:00.289387+00

### 280. M4.8 earthquake - 57 km E of Petropavlovsk-Kamchatsky, Russia
- ID: `14601983-e3fb-4bad-926e-72ec5fcd8117`; ключ: `live:usgs:earthquake:us6000u0mu`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 04:30:05.860424+00; обновлено: 2026-10-30 16:05:00.289387+00

### 281. M4.6 earthquake - Kuril Islands
- ID: `0882186f-4d44-46ee-978d-4c7a83ae3b2a`; ключ: `live:usgs:earthquake:us6000u0nb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 03:00:01.989431+00; обновлено: 2026-10-30 16:05:00.289387+00

### 282. M4.8 earthquake - 132 km ENE of Tadine, New Caledonia
- ID: `f2f5aae7-ede7-4d04-bf0b-8dc2f1577581`; ключ: `live:usgs:earthquake:us6000u0ns`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 03:30:03.243478+00; обновлено: 2026-10-30 16:05:00.289387+00

### 283. M4.9 earthquake - South Sandwich Islands region
- ID: `b47cfe3a-12fa-43ec-8db4-043d5dabc85d`; ключ: `live:usgs:earthquake:us6000u0pb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 05:45:04.550944+00; обновлено: 2026-10-30 16:05:00.289387+00

### 284. M4.9 earthquake - 80 km SW of El Arenal, Mexico
- ID: `dd5dade4-73ce-4724-a5bd-d867affc7609`; ключ: `live:usgs:earthquake:us6000u0q1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 08:15:05.034784+00; обновлено: 2026-10-30 16:05:00.289387+00

### 285. M4.5 earthquake - south of the Fiji Islands
- ID: `8f8e5563-2a56-4e81-a1bc-eae424621c27`; ключ: `live:usgs:earthquake:us6000u0qs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 11:00:05.875062+00; обновлено: 2026-10-30 16:05:00.289387+00

### 286. M4.7 earthquake - 22 km WNW of Manado, Indonesia
- ID: `f0ae37ac-cc34-4161-a273-de9ee0bb2f2a`; ключ: `live:usgs:earthquake:us6000u0qw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 11:45:05.270378+00; обновлено: 2026-10-30 16:05:00.289387+00

### 287. M5.2 earthquake - Chagos Archipelago region
- ID: `c30456ba-d533-4629-9298-4105e0c7d7d9`; ключ: `live:usgs:earthquake:us6000u0rr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 15:45:01.422249+00; обновлено: 2026-10-30 16:05:00.289387+00

### 288. M4.7 earthquake - 45 km WNW of Ollagüe, Chile
- ID: `7d03751a-a793-4cde-9b27-6a3c5283d393`; ключ: `live:usgs:earthquake:us6000u0rx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 17:00:04.438633+00; обновлено: 2026-10-30 16:05:00.289387+00

### 289. M4.7 earthquake - 34 km E of Sarangani, Philippines
- ID: `72ff764f-87d7-4ead-82f1-b83d770f79c3`; ключ: `live:usgs:earthquake:us6000u0t4`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 17:45:04.237355+00; обновлено: 2026-10-30 16:05:00.289387+00

### 290. M4.6 earthquake - 48 km SSW of Angoram, Papua New Guinea
- ID: `84ed14f5-681c-4526-bd2b-7b4442b03658`; ключ: `live:usgs:earthquake:us6000u0te`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 19:15:03.912333+00; обновлено: 2026-10-30 16:05:00.289387+00

### 291. M4.6 earthquake - south of the Fiji Islands
- ID: `ea883af4-e764-44fc-9ab3-956fac32cd34`; ключ: `live:usgs:earthquake:us6000u0tl`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 18:45:03.736799+00; обновлено: 2026-10-30 16:05:00.289387+00

### 292. M4.8 earthquake - 194 km S of Ust’-Kamchatsk Staryy, Russia
- ID: `05894c31-ba36-476f-9a5b-92d13289447f`; ключ: `live:usgs:earthquake:us6000u0tm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 19:15:03.834861+00; обновлено: 2026-10-30 16:05:00.289387+00

### 293. M4.9 earthquake - 13 km SE of Yokoshiba, Japan
- ID: `60fd8951-91f7-4dcb-a0cf-2d56f7d9166c`; ключ: `live:usgs:earthquake:us6000u0u7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-07 21:15:01.13467+00; обновлено: 2026-10-30 16:05:00.289387+00

### 294. M4.7 earthquake - 101 km NE of Ruteng, Indonesia
- ID: `000c8a8b-6db2-4ef8-be44-b50e1d5049b7`; ключ: `live:usgs:earthquake:us6000u0vw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 03:45:02.872036+00; обновлено: 2026-10-30 16:05:00.289387+00

### 295. M4.9 earthquake - 81 km NNW of Malfa, Italy
- ID: `d42bd6f2-ab17-43f0-8e97-c0e5fec010f2`; ключ: `live:usgs:earthquake:us6000u0w0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 04:15:01.523809+00; обновлено: 2026-10-30 16:05:00.289387+00

### 296. M5.0 earthquake - 92 km N of Ruteng, Indonesia
- ID: `0fd99630-b775-4c88-be86-f780e5bcbed8`; ключ: `live:usgs:earthquake:us6000u0wa`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 05:15:01.356859+00; обновлено: 2026-10-30 16:05:00.289387+00

### 297. M4.7 earthquake - 47 km W of Tambolaka, Indonesia
- ID: `66c6058a-95e5-46cf-9d56-ca32a6309437`; ключ: `live:usgs:earthquake:us6000u0wb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 06:15:01.551701+00; обновлено: 2026-10-30 16:05:00.289387+00

### 298. M4.5 earthquake - 39 km NE of Calama, Chile
- ID: `9fd24284-1bb7-48b5-801d-41854abb5993`; ключ: `live:usgs:earthquake:us6000u0wh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 06:15:01.454242+00; обновлено: 2026-10-30 16:05:00.289387+00

### 299. M5.5 earthquake - west of Macquarie Island
- ID: `2dc267af-d270-4c74-94c7-2cb4500c0f32`; ключ: `live:usgs:earthquake:us6000u0ws`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 07:15:01.51464+00; обновлено: 2026-10-30 16:05:00.289387+00

### 300. M4.6 earthquake - 61 km W of Banda Aceh, Indonesia
- ID: `594c1b9a-e21a-4001-b831-295d6445bcde`; ключ: `live:usgs:earthquake:us6000u0x2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 08:15:01.599851+00; обновлено: 2026-10-30 16:05:00.289387+00

### 301. M5.5 earthquake - 17 km SW of Burias, Philippines
- ID: `aa931f5c-f9e7-45fb-afcb-ea5e0b01f1c2`; ключ: `live:usgs:earthquake:us6000u0x4`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 09:15:01.616076+00; обновлено: 2026-10-30 16:05:00.289387+00

### 302. M6.3 earthquake - 102 km NE of Norsup, Vanuatu
- ID: `4d20aa75-521d-4ed3-8829-deaa70e4b18f`; ключ: `live:usgs:earthquake:us6000u0xi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 10:15:01.711059+00; обновлено: 2026-10-30 16:05:00.289387+00

### 303. M5.1 earthquake - 236 km E of Levuka, Fiji
- ID: `583e8bdc-20ec-4ffb-89ad-a66dad3f1ed6`; ключ: `live:usgs:earthquake:us6000u0xn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 11:15:02.206662+00; обновлено: 2026-10-30 16:05:00.289387+00

### 304. M4.9 earthquake - 113 km NW of Baa, Indonesia
- ID: `5dffba81-cb5e-471d-8b10-a499406c6f12`; ключ: `live:usgs:earthquake:us6000u0yr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 15:15:01.603629+00; обновлено: 2026-10-30 16:05:00.289387+00

### 305. M4.7 earthquake - 84 km WNW of Bengkulu, Indonesia
- ID: `e6293f4e-fbd8-4611-958d-713c9c4566c9`; ключ: `live:usgs:earthquake:us6000u0yy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 20:15:02.389343+00; обновлено: 2026-10-30 16:05:00.289387+00

### 306. M4.8 earthquake - 46 km N of Waingapu, Indonesia
- ID: `9e8f64f0-bab0-4589-959a-ef7968d073c2`; ключ: `live:usgs:earthquake:us6000u10n`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 20:15:02.359412+00; обновлено: 2026-10-30 16:05:00.289387+00

### 307. M4.6 earthquake - Izu Islands, Japan region
- ID: `0ad9dca3-67dc-4b5c-8ad1-5037ddfe6935`; ключ: `live:usgs:earthquake:us6000u10v`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-08 20:15:02.28354+00; обновлено: 2026-10-30 16:05:00.289387+00

### 308. M5.2 earthquake - 117 km SE of Bitung, Indonesia
- ID: `5c49377f-f1b5-47a1-9957-90920d1edff4`; ключ: `live:usgs:earthquake:us6000u13v`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 06:15:01.719397+00; обновлено: 2026-10-30 16:05:00.289387+00

### 309. M4.9 earthquake - south of the Fiji Islands
- ID: `e0c15463-2e24-4d55-a201-c7d316fc274f`; ключ: `live:usgs:earthquake:us6000u13y`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 07:15:01.906058+00; обновлено: 2026-10-30 16:05:00.289387+00

### 310. M4.5 earthquake - 249 km E of Levuka, Fiji
- ID: `9b5aa3c1-c44e-4b90-99c7-750a156e7e09`; ключ: `live:usgs:earthquake:us6000u14e`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 09:15:01.490098+00; обновлено: 2026-10-30 16:05:00.289387+00

### 311. M4.8 earthquake - 97 km E of Levuka, Fiji
- ID: `055739ab-5a9b-429d-92be-bf2f1c00c265`; ключ: `live:usgs:earthquake:us6000u14i`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 09:15:01.417755+00; обновлено: 2026-10-30 16:05:00.289387+00

### 312. M4.6 earthquake - 17 km NNE of Santa Cruz, Philippines
- ID: `5dd7e333-817d-41f7-8edb-7296dd651cf8`; ключ: `live:usgs:earthquake:us6000u14r`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 12:15:01.810785+00; обновлено: 2026-10-30 16:05:00.289387+00

### 313. M4.8 earthquake - northern Mid-Atlantic Ridge
- ID: `ecd87d1c-7486-43d3-8b49-07a8af067c51`; ключ: `live:usgs:earthquake:us6000u14u`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 10:15:01.248863+00; обновлено: 2026-10-30 16:05:00.289387+00

### 314. M4.9 earthquake - 77 km ENE of Tuapejat, Indonesia
- ID: `2bff8269-38df-4a53-be95-f588c3208d49`; ключ: `live:usgs:earthquake:us6000u14w`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 11:15:01.332546+00; обновлено: 2026-10-30 16:05:00.289387+00

### 315. M5.1 earthquake - 72 km SSW of Colchane, Chile
- ID: `420fd76c-97f1-472b-90dc-95c6509f30dc`; ключ: `live:usgs:earthquake:us6000u153`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 11:15:01.290353+00; обновлено: 2026-10-30 16:05:00.289387+00

### 316. M4.8 earthquake - 17 km S of Nandaime, Nicaragua
- ID: `5afc99d6-5c17-4782-9f00-ab0ce2740b6f`; ключ: `live:usgs:earthquake:us6000u15l`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 13:15:01.070178+00; обновлено: 2026-10-30 16:05:00.289387+00

### 317. M5.4 earthquake - 99 km NE of Norsup, Vanuatu
- ID: `bdb94611-e345-4ce4-b500-b0b45b3e2031`; ключ: `live:usgs:earthquake:us6000u15x`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 14:15:00.963742+00; обновлено: 2026-10-30 16:05:00.289387+00

### 318. M5.9 earthquake - west of Macquarie Island
- ID: `9de72d92-4add-4b16-8810-84ca9a3550ea`; ключ: `live:usgs:earthquake:us6000u164`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 15:15:01.795447+00; обновлено: 2026-10-30 16:05:00.289387+00

### 319. M4.6 earthquake - south of the Fiji Islands
- ID: `d25d7b4d-269b-416d-9320-198e02c70bad`; ключ: `live:usgs:earthquake:us6000u168`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 16:15:01.511572+00; обновлено: 2026-10-30 16:05:00.289387+00

### 320. M4.7 earthquake - 138 km SE of Petropavlovsk-Kamchatsky, Russia
- ID: `b00e9e7a-d9f6-457e-836e-4b268d9cbbf7`; ключ: `live:usgs:earthquake:us6000u18d`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 18:15:01.308685+00; обновлено: 2026-10-30 16:05:00.289387+00

### 321. M4.8 earthquake - 191 km SE of Petropavlovsk-Kamchatsky, Russia
- ID: `19da1ab0-39e4-4ce8-a80e-ee0b4ec9c439`; ключ: `live:usgs:earthquake:us6000u18e`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 18:15:01.287285+00; обновлено: 2026-10-30 16:05:00.289387+00

### 322. M7.7 earthquake - 12 km WSW of Pitaloza Arriba, Panama
- ID: `a1dfd894-954e-44a6-a49c-aa7b6c047390`; ключ: `live:usgs:earthquake:us6000u18k`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 18:15:01.236861+00; обновлено: 2026-10-30 16:05:00.289387+00

### 323. M5.5 earthquake - 3 km SW of Bajo Corral, Panama
- ID: `dccb059f-8944-4124-87f2-a093deec9106`; ключ: `live:usgs:earthquake:us6000u18t`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 19:15:02.287868+00; обновлено: 2026-10-30 16:05:00.289387+00

### 324. M5.8 earthquake - 1 km S of El Cacao, Panama
- ID: `e9bb5600-0847-4aa9-bd09-dee4d895562a`; ключ: `live:usgs:earthquake:us6000u18x`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 19:15:02.262561+00; обновлено: 2026-10-30 16:05:00.289387+00

### 325. M5.0 earthquake - 18 km S of Los Asientos, Panama
- ID: `47283106-ee3a-4913-99d7-ab602e2f9bd4`; ключ: `live:usgs:earthquake:us6000u194`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 19:15:02.175322+00; обновлено: 2026-10-30 16:05:00.289387+00

### 326. M5.0 earthquake - 19 km S of Leones Arriba, Panama
- ID: `425bbfb1-3eed-420e-bd65-d89afe1e1790`; ключ: `live:usgs:earthquake:us6000u195`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 19:15:02.236165+00; обновлено: 2026-10-30 16:05:00.289387+00

### 327. M5.0 earthquake - 14 km SE of Río Grande, Panama
- ID: `db5a3c9b-7cd3-42b3-b6b4-0654800fae84`; ключ: `live:usgs:earthquake:us6000u197`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 20:15:01.760249+00; обновлено: 2026-10-30 16:05:00.289387+00

### 328. M4.8 earthquake - 14 km SSW of Tebario, Panama
- ID: `3f9f6642-9c27-4439-be46-9ae89611330f`; ключ: `live:usgs:earthquake:us6000u198`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 20:15:01.726869+00; обновлено: 2026-10-30 16:05:00.289387+00

### 329. M4.5 earthquake - 5 km N of Oria Arriba, Panama
- ID: `1a8ad4bc-5f14-42ee-a5f8-7b5e63adabec`; ключ: `live:usgs:earthquake:us6000u19e`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 22:15:01.955841+00; обновлено: 2026-10-30 16:05:00.289387+00

### 330. M5.2 earthquake - 11 km SE of Río Grande, Panama
- ID: `bcdfbc01-2a68-48f7-a216-9afb1ae005e9`; ключ: `live:usgs:earthquake:us6000u19h`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 20:15:01.661116+00; обновлено: 2026-10-30 16:05:00.289387+00

### 331. M4.8 earthquake - 2 km N of Los Asientos, Panama
- ID: `d97f7d16-f987-4ffd-b951-30c88cdecb07`; ключ: `live:usgs:earthquake:us6000u19i`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 22:15:01.929774+00; обновлено: 2026-10-30 16:05:00.289387+00

### 332. M4.9 earthquake - 12 km SSW of Tebario, Panama
- ID: `540ec2af-332f-422e-bef4-5950b0fd974e`; ключ: `live:usgs:earthquake:us6000u19s`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 21:15:02.073363+00; обновлено: 2026-10-30 16:05:00.289387+00

### 333. M5.0 earthquake - 6 km NE of La Tronosa, Panama
- ID: `673715bb-50a6-4659-af33-843da8102868`; ключ: `live:usgs:earthquake:us6000u19t`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 22:15:01.850687+00; обновлено: 2026-10-30 16:05:00.289387+00

### 334. M4.7 earthquake - 121 km S of Kokopo, Papua New Guinea
- ID: `cc1ca9cd-627f-410f-8433-dca17abb185b`; ключ: `live:usgs:earthquake:us6000u19v`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 23:15:01.973318+00; обновлено: 2026-10-30 16:05:00.289387+00

### 335. M6.6 earthquake - 14 km W of Río Grande, Panama
- ID: `45c4a6cd-a65b-4244-a849-847f01f3bb13`; ключ: `live:usgs:earthquake:us6000u19w`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 21:15:02.022192+00; обновлено: 2026-10-30 16:05:00.289387+00

### 336. M4.9 earthquake - 8 km SSE of Leones Arriba, Panama
- ID: `4e165954-bde4-4cbf-bec1-5d3ca4ae4cc6`; ключ: `live:usgs:earthquake:us6000u1a5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 22:15:01.738119+00; обновлено: 2026-10-30 16:05:00.289387+00

### 337. M4.9 earthquake - 16 km SSW of Calidonia, Panama
- ID: `51b82f08-5a39-4b05-a461-8c6b8aaf6ca7`; ключ: `live:usgs:earthquake:us6000u1a6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 23:15:01.832122+00; обновлено: 2026-10-30 16:05:00.289387+00

### 338. M4.9 earthquake - 13 km W of Río Grande, Panama
- ID: `e88dbdc7-d9ce-4286-8bb2-9b119a3266c4`; ключ: `live:usgs:earthquake:us6000u1a9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 22:15:01.678485+00; обновлено: 2026-10-30 16:05:00.289387+00

### 339. M5.0 earthquake - 13 km W of Río Grande, Panama
- ID: `e75c1012-0b1e-457a-bab0-391e46d78b7f`; ключ: `live:usgs:earthquake:us6000u1aa`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 22:15:01.704577+00; обновлено: 2026-10-30 16:05:00.289387+00

### 340. M4.6 earthquake - 96 km NE of Ozernovskiy, Russia
- ID: `6c786b69-6a5d-4c6f-b179-ed755a4a66b9`; ключ: `live:usgs:earthquake:us6000u1ah`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 22:15:01.620556+00; обновлено: 2026-10-30 16:05:00.289387+00

### 341. M4.6 earthquake - 4 km NNE of Río Grande, Panama
- ID: `a5cf6494-e564-4631-940d-e700dec1a269`; ключ: `live:usgs:earthquake:us6000u1ai`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-09 23:15:01.70204+00; обновлено: 2026-10-30 16:05:00.289387+00

### 342. M5.0 earthquake - 8 km ESE of La Tronosa, Panama
- ID: `284141c4-f26f-4679-a5b4-37e234bfc4c9`; ключ: `live:usgs:earthquake:us6000u1ax`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 00:15:01.549132+00; обновлено: 2026-10-30 16:05:00.289387+00

### 343. M5.4 earthquake - 9 km SSE of Los Asientos, Panama
- ID: `d5f479d7-99a6-4817-bec3-e7b175bdf39a`; ключ: `live:usgs:earthquake:us6000u1ay`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 00:15:01.515534+00; обновлено: 2026-10-30 16:05:00.289387+00

### 344. M4.9 earthquake - 9 km SW of Río Grande, Panama
- ID: `28eb2034-7d82-4a7d-8893-2053ea65df51`; ключ: `live:usgs:earthquake:us6000u1az`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 00:15:01.460383+00; обновлено: 2026-10-30 16:05:00.289387+00

### 345. M4.5 earthquake - 45 km SSE of Pedasí, Panama
- ID: `468c0dc6-dda2-45d1-a238-72ab0b408cf1`; ключ: `live:usgs:earthquake:us6000u1b3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 01:15:01.616587+00; обновлено: 2026-10-30 16:05:00.289387+00

### 346. M4.7 earthquake - 14 km W of Río Grande, Panama
- ID: `d0acacf5-fca8-404d-9c3d-a6b672d29fdb`; ключ: `live:usgs:earthquake:us6000u1b4`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 02:15:02.441674+00; обновлено: 2026-10-30 16:05:00.289387+00

### 347. M4.8 earthquake - 5 km SW of Cañas, Panama
- ID: `8bbd148c-d359-4a56-96f0-0195e7a24fa7`; ключ: `live:usgs:earthquake:us6000u1b5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 02:15:02.408818+00; обновлено: 2026-10-30 16:05:00.289387+00

### 348. M4.7 earthquake - 85 km ENE of Tadine, New Caledonia
- ID: `6899552d-c28f-4f4f-a85f-cb496fe54f35`; ключ: `live:usgs:earthquake:us6000u1bh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 03:15:02.723858+00; обновлено: 2026-10-30 16:05:00.289387+00

### 349. M4.6 earthquake - 9 km NNE of La Tronosa, Panama
- ID: `a498fec8-c9ce-4da0-8009-223fcaea398e`; ключ: `live:usgs:earthquake:us6000u1bj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 03:15:02.695745+00; обновлено: 2026-10-30 16:05:00.289387+00

### 350. M4.7 earthquake - 10 km N of La Tronosa, Panama
- ID: `07f3d9a1-b5b6-4c93-b88a-7e123b9392bb`; ключ: `live:usgs:earthquake:us6000u1bl`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 02:15:02.376315+00; обновлено: 2026-10-30 16:05:00.289387+00

### 351. M4.6 earthquake - 10 km S of Río Grande, Panama
- ID: `2b78b43d-cec8-484a-a8b4-1b03ceb5c283`; ключ: `live:usgs:earthquake:us6000u1bp`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 02:15:02.316962+00; обновлено: 2026-10-30 16:05:00.289387+00

### 352. M5.1 earthquake - 133 km WNW of Ternate, Indonesia
- ID: `f5035aa0-1579-47e7-9edd-04e9dd22e1aa`; ключ: `live:usgs:earthquake:us6000u1bs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 03:15:02.60131+00; обновлено: 2026-10-30 16:05:00.289387+00

### 353. M5.1 earthquake - 1 km NNE of Tonosí, Panama
- ID: `739b178a-a848-4d50-b0c2-7ddce92ad832`; ключ: `live:usgs:earthquake:us6000u1bu`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 03:15:02.571799+00; обновлено: 2026-10-30 16:05:00.289387+00

### 354. M4.5 earthquake - 18 km SSE of Río Grande, Panama
- ID: `79498c09-66c1-489c-a7ef-c3750c02f4d5`; ключ: `live:usgs:earthquake:us6000u1bw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 03:15:02.511371+00; обновлено: 2026-10-30 16:05:00.289387+00

### 355. M4.7 earthquake - 8 km N of La Tronosa, Panama
- ID: `6d1f2822-613d-41b2-9aae-d6385102b178`; ключ: `live:usgs:earthquake:us6000u1cb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 05:15:06.774736+00; обновлено: 2026-10-30 16:05:00.289387+00

### 356. M5.3 earthquake - 41 km NNE of Yigo Village, Guam
- ID: `db60c188-5921-451d-9293-6ea36deef72f`; ключ: `live:usgs:earthquake:us6000u1cd`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 04:15:01.837676+00; обновлено: 2026-10-30 16:05:00.289387+00

### 357. M6.0 earthquake - 7 km N of La Tronosa, Panama
- ID: `d3b8e418-2367-4908-986c-e11a1241b56b`; ключ: `live:usgs:earthquake:us6000u1cf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 05:15:06.704768+00; обновлено: 2026-10-30 16:05:00.289387+00

### 358. M4.5 earthquake - 9 km WNW of Flores, Panama
- ID: `b2c9ab38-1f20-4511-9c7c-a2d8750c444f`; ключ: `live:usgs:earthquake:us6000u1ck`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 05:15:06.58944+00; обновлено: 2026-10-30 16:05:00.289387+00

### 359. M5.0 earthquake - 141 km E of Bitung, Indonesia
- ID: `09322b13-388f-4fd2-a8bf-93234cec57e3`; ключ: `live:usgs:earthquake:us6000u1cv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 06:15:01.980924+00; обновлено: 2026-10-30 16:05:00.289387+00

### 360. M4.5 earthquake - 6 km WSW of Filadelfia, Colombia
- ID: `bb59ae2e-aa14-4bb2-ad7d-3544335a8454`; ключ: `live:usgs:earthquake:us6000u1cx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 07:15:02.280286+00; обновлено: 2026-10-30 16:05:00.289387+00

### 361. M4.5 earthquake - 25 km SSE of Pedasí, Panama
- ID: `4be1490a-fde1-46c4-8fcb-bf57a546bda0`; ключ: `live:usgs:earthquake:us6000u1d1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 08:15:01.763434+00; обновлено: 2026-10-30 16:05:00.289387+00

### 362. M4.9 earthquake - 10 km SSW of Cañas, Panama
- ID: `b5b798d6-1ed1-47ac-ba15-da66091dbf86`; ключ: `live:usgs:earthquake:us6000u1d2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 07:15:02.261197+00; обновлено: 2026-10-30 16:05:00.289387+00

### 363. M4.7 earthquake - 26 km S of Pedasí, Panama
- ID: `e0a8ec00-a04e-4469-b44f-dbca2c8c713f`; ключ: `live:usgs:earthquake:us6000u1d5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 07:15:02.241992+00; обновлено: 2026-10-30 16:05:00.289387+00

### 364. M4.9 earthquake - 26 km SSE of Pedasí, Panama
- ID: `24fe88fb-3368-4d12-bbef-7155121aa87d`; ключ: `live:usgs:earthquake:us6000u1d7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 07:15:02.05101+00; обновлено: 2026-10-30 16:05:00.289387+00

### 365. M4.5 earthquake - 10 km SE of Pedasí, Panama
- ID: `e91cf82c-d943-4b93-83a7-7ef4be50e3f6`; ключ: `live:usgs:earthquake:us6000u1db`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 08:15:01.649299+00; обновлено: 2026-10-30 16:05:00.289387+00

### 366. M4.6 earthquake - 6 km SSE of Llano de Piedra, Panama
- ID: `d147a130-2f16-4aba-aa9f-99b9bcb259ce`; ключ: `live:usgs:earthquake:us6000u1dc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 08:15:01.600949+00; обновлено: 2026-10-30 16:05:00.289387+00

### 367. M4.5 earthquake - 61 km N of Hihifo, Tonga
- ID: `18a919ca-911f-4686-8587-b0ef26941d60`; ключ: `live:usgs:earthquake:us6000u1dm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 09:15:01.883971+00; обновлено: 2026-10-30 16:05:00.289387+00

### 368. M4.6 earthquake - 31 km SE of Vanimo, Papua New Guinea
- ID: `f675fba1-b6b1-48cf-ab70-27b916ea67ea`; ключ: `live:usgs:earthquake:us6000u1dy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 13:15:02.264579+00; обновлено: 2026-10-30 16:05:00.289387+00

### 369. M4.8 earthquake - 4 km NE of Río Grande, Panama
- ID: `ff8c0aaa-2db8-47d7-923b-5b4d6863bac1`; ключ: `live:usgs:earthquake:us6000u1e5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 11:15:01.662836+00; обновлено: 2026-10-30 16:05:00.289387+00

### 370. M4.6 earthquake - 268 km WNW of Houma, Tonga
- ID: `0c0992ff-e1df-4b1a-904f-cdaefd9deeaa`; ключ: `live:usgs:earthquake:us6000u1ej`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 13:15:02.069468+00; обновлено: 2026-10-30 16:05:00.289387+00

### 371. M4.5 earthquake - 4 km NW of Los Asientos, Panama
- ID: `5c024ab1-28fb-4561-b87d-0ba23c62abcb`; ключ: `live:usgs:earthquake:us6000u1ev`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 17:15:02.211814+00; обновлено: 2026-10-30 16:05:00.289387+00

### 372. M4.6 earthquake - south of the Fiji Islands
- ID: `e3c70a9f-b21d-443f-ab54-3f4a25dbcf7f`; ключ: `live:usgs:earthquake:us6000u1ew`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 17:15:02.185048+00; обновлено: 2026-10-30 16:05:00.289387+00

### 373. M4.8 earthquake - 12 km NE of La Tronosa, Panama
- ID: `920110e5-9444-4891-b234-90c1ff9910b0`; ключ: `live:usgs:earthquake:us6000u1ex`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 16:15:01.626213+00; обновлено: 2026-10-30 16:05:00.289387+00

### 374. M4.5 earthquake - 10 km NNW of El Cortezo, Panama
- ID: `17153781-236c-47c5-bb4b-aac628ad93a4`; ключ: `live:usgs:earthquake:us6000u1f3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 18:15:01.439197+00; обновлено: 2026-10-30 16:05:00.289387+00

### 375. M4.5 earthquake - 5 km WNW of Guarumal, Panama
- ID: `f7fb7e6e-a159-4167-a6c8-dd9915a36b8d`; ключ: `live:usgs:earthquake:us6000u1f6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 19:15:02.590357+00; обновлено: 2026-10-30 16:05:00.289387+00

### 376. M4.6 earthquake - 51 km NNW of Rabaul, Papua New Guinea
- ID: `64109339-39d3-4385-b4af-cc3f774f1af0`; ключ: `live:usgs:earthquake:us6000u1fa`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 19:15:02.511983+00; обновлено: 2026-10-30 16:05:00.289387+00

### 377. M4.8 earthquake - 11 km SSW of Tebario, Panama
- ID: `a8f07e59-0b47-4266-8466-ef7e5e1cbe83`; ключ: `live:usgs:earthquake:us6000u1fj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 17:15:01.972697+00; обновлено: 2026-10-30 16:05:00.289387+00

### 378. M4.7 earthquake - 2 km WNW of El Cacao, Panama
- ID: `82fe8c87-4037-4b3e-ae2a-6bf71ec5985f`; ключ: `live:usgs:earthquake:us6000u1fk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 17:15:01.894571+00; обновлено: 2026-10-30 16:05:00.289387+00

### 379. M4.9 earthquake - Kermadec Islands region
- ID: `2ebabb66-25ca-4b06-aa08-2dade60a8906`; ключ: `live:usgs:earthquake:us6000u1gm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 21:15:02.427669+00; обновлено: 2026-10-30 16:05:00.289387+00

### 380. M5.3 earthquake - southeast of Easter Island
- ID: `be052e83-17e5-4e24-8eda-6b875b53d6e7`; ключ: `live:usgs:earthquake:us6000u1gs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 22:15:03.471507+00; обновлено: 2026-10-30 16:05:00.289387+00

### 381. M4.5 earthquake - 171 km SSW of Pagar Alam, Indonesia
- ID: `4ed69597-9133-41c9-b269-6ca27eeb5038`; ключ: `live:usgs:earthquake:us6000u1gu`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-10 22:15:03.410808+00; обновлено: 2026-10-30 16:05:00.289387+00

### 382. M4.6 earthquake - 18 km WNW of Río Grande, Panama
- ID: `2a280bdb-eb97-4dc3-b709-35d0bf9c9238`; ключ: `live:usgs:earthquake:us6000u1hj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 01:15:03.313604+00; обновлено: 2026-10-30 16:05:00.289387+00

### 383. M5.0 earthquake - 3 km NW of Flores, Panama
- ID: `9ce23a6b-2fb5-44a3-b3bd-f46772c38217`; ключ: `live:usgs:earthquake:us6000u1hw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 02:15:01.737316+00; обновлено: 2026-10-30 16:05:00.289387+00

### 384. M4.6 earthquake - 109 km SSE of Pondaguitan, Philippines
- ID: `a669bd03-8b6d-460c-93e1-939e74e3c00a`; ключ: `live:usgs:earthquake:us6000u1i0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 03:15:01.537437+00; обновлено: 2026-10-30 16:05:00.289387+00

### 385. M5.2 earthquake - 180 km S of Pelabuhanratu, Indonesia
- ID: `934f7583-1392-46f6-8753-6dd328f5a080`; ключ: `live:usgs:earthquake:us6000u1i6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 04:15:01.775512+00; обновлено: 2026-10-30 16:05:00.289387+00

### 386. M4.7 earthquake - 110 km SSE of Sola, Vanuatu
- ID: `0a7727b4-f9c2-4569-b47f-f0d393c3e517`; ключ: `live:usgs:earthquake:us6000u1il`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 06:15:01.666691+00; обновлено: 2026-10-30 16:05:00.289387+00

### 387. M4.5 earthquake - south of the Fiji Islands
- ID: `60f8ce9a-253f-489b-8058-bc9c088df47f`; ключ: `live:usgs:earthquake:us6000u1j3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 08:15:03.026805+00; обновлено: 2026-10-30 16:05:00.289387+00

### 388. M4.6 earthquake - southern Mid-Atlantic Ridge
- ID: `a103db7b-5dcd-4fe5-b084-a646e9fe3afd`; ключ: `live:usgs:earthquake:us6000u1jt`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 10:15:01.989608+00; обновлено: 2026-10-30 16:05:00.289387+00

### 389. M4.6 earthquake - 260 km WNW of Houma, Tonga
- ID: `0b1f9120-2412-495f-912a-2efb7d963f43`; ключ: `live:usgs:earthquake:us6000u1jv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 11:15:01.669768+00; обновлено: 2026-10-30 16:05:00.289387+00

### 390. M4.6 earthquake - 82 km E of Petropavlovsk-Kamchatsky, Russia
- ID: `c5a5fbb2-c2fe-4471-a809-dbb93e54897f`; ключ: `live:usgs:earthquake:us6000u1k3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 12:15:01.303903+00; обновлено: 2026-10-30 16:05:00.289387+00

### 391. M4.8 earthquake - 165 km SSE of Miyakojima, Japan
- ID: `ed7201d1-1551-4f6a-809f-b7736baa6954`; ключ: `live:usgs:earthquake:us6000u1ka`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 13:15:03.226818+00; обновлено: 2026-10-30 16:05:00.289387+00

### 392. M5.2 earthquake - 18 km SSE of Camaná, Peru
- ID: `4e41c7c8-868c-4b10-86a9-479f1e6a4ec5`; ключ: `live:usgs:earthquake:us6000u1kt`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 14:15:01.76247+00; обновлено: 2026-10-30 16:05:00.289387+00

### 393. M6.2 earthquake - 79 km SSE of Panguna, Papua New Guinea
- ID: `ffafc7f5-2f02-47c5-a3ab-b27ed3b8652e`; ключ: `live:usgs:earthquake:us6000u1kv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 15:15:01.729967+00; обновлено: 2026-10-30 16:05:00.289387+00

### 394. M4.7 earthquake - 6 km ESE of Tōgane, Japan
- ID: `29ddb20e-cc35-4f5b-a6ab-fce1f373a4d0`; ключ: `live:usgs:earthquake:us6000u1l7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 18:15:01.57912+00; обновлено: 2026-10-30 16:05:00.289387+00

### 395. M5.2 earthquake - 101 km SSW of Severo-Kuril’sk, Russia
- ID: `f805a167-bc60-4b8c-bb34-0891d71c279f`; ключ: `live:usgs:earthquake:us6000u1ld`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 18:15:01.546803+00; обновлено: 2026-10-30 16:05:00.289387+00

### 396. M4.8 earthquake - 31 km W of Río Grande, Panama
- ID: `1c7db173-73f1-4454-9968-5653a24c024a`; ключ: `live:usgs:earthquake:us6000u1lf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 18:15:01.505351+00; обновлено: 2026-10-30 16:05:00.289387+00

### 397. M4.7 earthquake - 156 km ESE of Neiafu, Tonga
- ID: `e75621f6-4e6f-49b9-af82-90f03bbdc9fe`; ключ: `live:usgs:earthquake:us6000u1lk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 19:15:02.495639+00; обновлено: 2026-10-30 16:05:00.289387+00

### 398. M4.5 earthquake - 27 km W of Río Grande, Panama
- ID: `bb861a6a-844e-46dc-a1af-bea18666fed9`; ключ: `live:usgs:earthquake:us6000u1me`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 23:15:01.725487+00; обновлено: 2026-10-30 16:05:00.289387+00

### 399. M5.3 earthquake - 150 km W of Gorontalo, Indonesia
- ID: `b6367d24-8d8a-43b2-a6e8-f20982aa39e6`; ключ: `live:usgs:earthquake:us6000u1mj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-11 22:15:02.224616+00; обновлено: 2026-10-30 16:05:00.289387+00

### 400. M4.5 earthquake - 116 km SE of Nabire, Indonesia
- ID: `121e1908-8eaa-43c4-88f6-8c3402f96b87`; ключ: `live:usgs:earthquake:us6000u1mv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 01:15:02.717233+00; обновлено: 2026-10-30 16:05:00.289387+00

### 401. M4.6 earthquake - 0 km NE of Leones Arriba, Panama
- ID: `1f3aaa13-2d18-480e-b277-50dfebab98c2`; ключ: `live:usgs:earthquake:us6000u1mz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 02:15:02.072173+00; обновлено: 2026-10-30 16:05:00.289387+00

### 402. M4.5 earthquake - 103 km SSW of La Libertad, El Salvador
- ID: `7666b90c-00e8-493e-80ba-615f6fad61f4`; ключ: `live:usgs:earthquake:us6000u1n6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 02:15:02.046846+00; обновлено: 2026-10-30 16:05:00.289387+00

### 403. M4.6 earthquake - Volcano Islands, Japan region
- ID: `de877b30-8ba8-445b-8b48-76a6f093509e`; ключ: `live:usgs:earthquake:us6000u1nn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 03:15:01.772049+00; обновлено: 2026-10-30 16:05:00.289387+00

### 404. M4.8 earthquake - 56 km E of Yairipok, India
- ID: `98469686-7a08-4d50-b7bd-b68db72732c7`; ключ: `live:usgs:earthquake:us6000u1nr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 02:15:01.983028+00; обновлено: 2026-10-30 16:05:00.289387+00

### 405. M4.8 earthquake - southern East Pacific Rise
- ID: `5c348388-ebca-4be1-ac13-945c335a853f`; ключ: `live:usgs:earthquake:us6000u1nx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 03:15:01.671652+00; обновлено: 2026-10-30 16:05:00.289387+00

### 406. M4.5 earthquake - 7 km ENE of Lajamina, Panama
- ID: `04b955ae-0070-43c5-bdc8-6d9d3b45f174`; ключ: `live:usgs:earthquake:us6000u1ny`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 04:15:01.918655+00; обновлено: 2026-10-30 16:05:00.289387+00

### 407. M4.5 earthquake - 53 km S of Kushiro, Japan
- ID: `11b7be1c-3a90-4ca9-9cbb-4452b6c11c90`; ключ: `live:usgs:earthquake:us6000u1pa`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 04:15:01.613071+00; обновлено: 2026-10-30 16:05:00.289387+00

### 408. M5.5 earthquake - 122 km W of Neiafu, Tonga
- ID: `3f8ce966-391d-4fcf-bdc8-3a356dbd1368`; ключ: `live:usgs:earthquake:us6000u1pl`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 05:15:01.71396+00; обновлено: 2026-10-30 16:05:00.289387+00

### 409. M4.5 earthquake - south of the Fiji Islands
- ID: `dd611ec0-7a7b-48ef-9a7d-385521bd7bca`; ключ: `live:usgs:earthquake:us6000u1pz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 06:15:01.401374+00; обновлено: 2026-10-30 16:05:00.289387+00

### 410. M4.6 earthquake - 25 km SSE of Blitar, Indonesia
- ID: `5577ff0b-3fe1-416b-8b9d-8da6a3d1cad1`; ключ: `live:usgs:earthquake:us6000u1q2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 07:15:02.422711+00; обновлено: 2026-10-30 16:05:00.289387+00

### 411. M4.5 earthquake - 7 km ESE of Tebario, Panama
- ID: `07ea2afb-8e68-4822-92ef-05159b8e269e`; ключ: `live:usgs:earthquake:us6000u1qd`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 08:15:02.645156+00; обновлено: 2026-10-30 16:05:00.289387+00

### 412. M4.7 earthquake - 219 km E of Lospalos, Timor Leste
- ID: `ca42a8cd-2c46-472d-9205-7f75e84b139f`; ключ: `live:usgs:earthquake:us6000u1qy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 10:15:02.026535+00; обновлено: 2026-10-30 16:05:00.289387+00

### 413. M4.6 earthquake - 122 km SE of Bitung, Indonesia
- ID: `359d336a-c708-48cc-b5f5-35e823630cec`; ключ: `live:usgs:earthquake:us6000u1r3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 14:15:01.34732+00; обновлено: 2026-10-30 16:05:00.289387+00

### 414. M5.4 earthquake - Mid-Indian Ridge
- ID: `60bb35dd-14d0-4da0-a82d-77a8ade1ff4d`; ключ: `live:usgs:earthquake:us6000u1rh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 12:15:02.005764+00; обновлено: 2026-10-30 16:05:00.289387+00

### 415. M4.6 earthquake - 100 km SSW of Kencong, Indonesia
- ID: `93b29645-3d9b-4c34-a0dd-8aa5390496bc`; ключ: `live:usgs:earthquake:us6000u1rm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 13:15:01.409295+00; обновлено: 2026-10-30 16:05:00.289387+00

### 416. M4.5 earthquake - 6 km W of Tonosí, Panama
- ID: `e47d53c7-2b30-4ade-a7c9-b460be697ca6`; ключ: `live:usgs:earthquake:us6000u1rx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 15:15:01.722523+00; обновлено: 2026-10-30 16:05:00.289387+00

### 417. M4.8 earthquake - Mid-Indian Ridge
- ID: `6e0dd7f2-53b5-4f93-b0b9-9cc534cbf3cb`; ключ: `live:usgs:earthquake:us6000u1s2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 14:15:01.2326+00; обновлено: 2026-10-30 16:05:00.289387+00

### 418. M4.6 earthquake - 194 km SE of Attu Station, Alaska
- ID: `48ab325f-0fd3-4a23-8a33-5c0e75eac32d`; ключ: `live:usgs:earthquake:us6000u1s8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 16:15:01.965855+00; обновлено: 2026-10-30 16:05:00.289387+00

### 419. M4.9 earthquake - 283 km SSW of Severo-Kuril’sk, Russia
- ID: `613fd84a-beeb-4228-8c80-01bae81c8eaa`; ключ: `live:usgs:earthquake:us6000u1sn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 16:15:01.890049+00; обновлено: 2026-10-30 16:05:00.289387+00

### 420. M4.8 earthquake - 23 km SW of San Antonio, Chile
- ID: `d064e4d4-ceac-422e-9884-55fb9ce71be7`; ключ: `live:usgs:earthquake:us6000u1uq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 19:15:00.877094+00; обновлено: 2026-10-30 16:05:00.289387+00

### 421. M4.7 earthquake - Mid-Indian Ridge
- ID: `d8c08dd2-4348-4b76-83cf-d8943ba372d4`; ключ: `live:usgs:earthquake:us6000u1ut`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 19:15:00.851859+00; обновлено: 2026-10-30 16:05:00.289387+00

### 422. M4.6 earthquake - Mid-Indian Ridge
- ID: `32552e51-d9ac-4edc-badb-fb0dca9a0eeb`; ключ: `live:usgs:earthquake:us6000u1uv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 19:15:00.746297+00; обновлено: 2026-10-30 16:05:00.289387+00

### 423. M4.8 earthquake - 25 km W of Río Grande, Panama
- ID: `0b785585-e6d4-4a0a-9a54-97da2e073624`; ключ: `live:usgs:earthquake:us6000u1vf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 21:15:01.212303+00; обновлено: 2026-10-30 16:05:00.289387+00

### 424. M4.5 earthquake - 21 km WNW of Río Grande, Panama
- ID: `4cb1ff6c-7b32-4ad4-8494-a4895ebd5783`; ключ: `live:usgs:earthquake:us6000u1w6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 22:15:01.74505+00; обновлено: 2026-10-30 16:05:00.289387+00

### 425. M4.5 earthquake - 5 km WSW of Calidonia, Panama
- ID: `252decf0-d0b7-44ab-9690-9ebb3c0f8b78`; ключ: `live:usgs:earthquake:us6000u1w7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-12 22:15:01.688492+00; обновлено: 2026-10-30 16:05:00.289387+00

### 426. M6.1 earthquake - 17 km W of Río Grande, Panama
- ID: `bace0821-77ef-409c-8106-c7d667e729f7`; ключ: `live:usgs:earthquake:us6000u1wn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 00:15:01.456132+00; обновлено: 2026-10-30 16:05:00.289387+00

### 427. M4.9 earthquake - 17 km W of Río Grande, Panama
- ID: `c1d75c61-0bfa-4984-8d16-b31448c31724`; ключ: `live:usgs:earthquake:us6000u1ww`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 00:15:01.388761+00; обновлено: 2026-10-30 16:05:00.289387+00

### 428. M4.5 earthquake - 24 km SW of Zapotillo, Panama
- ID: `3a84835a-4ca7-4291-89c3-90145c044c7a`; ключ: `live:usgs:earthquake:us6000u1wz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 03:15:01.908832+00; обновлено: 2026-10-30 16:05:00.289387+00

### 429. M4.6 earthquake - 23 km WNW of Río Grande, Panama
- ID: `5ec64aaf-6e1b-43e2-9752-10ec62b1bc0f`; ключ: `live:usgs:earthquake:us6000u1x2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 03:15:01.880062+00; обновлено: 2026-10-30 16:05:00.289387+00

### 430. M4.7 earthquake - 9 km SSE of La Mesa, Panama
- ID: `c7c99797-1c67-4a76-b478-472b963f025f`; ключ: `live:usgs:earthquake:us6000u1y4`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 03:15:01.795458+00; обновлено: 2026-10-30 16:05:00.289387+00

### 431. M5.1 earthquake - 119 km SSW of Gambiran Satu, Indonesia
- ID: `08eb4e85-7a6f-401e-9c13-65271757fe8a`; ключ: `live:usgs:earthquake:us6000u1ye`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 05:15:01.142691+00; обновлено: 2026-10-30 16:05:00.289387+00

### 432. M6.7 earthquake - central Mid-Atlantic Ridge
- ID: `b532ecfe-1e96-43a4-9c8e-693e8236480c`; ключ: `live:usgs:earthquake:us6000u1z5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 06:15:02.225713+00; обновлено: 2026-10-30 16:05:00.289387+00

### 433. M4.7 earthquake - 124 km N of Pagudpud, Philippines
- ID: `177dab05-555f-4751-89f4-405bc6a57f5d`; ключ: `live:usgs:earthquake:us6000u1zc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 07:15:01.574067+00; обновлено: 2026-10-30 16:05:00.289387+00

### 434. M4.7 earthquake - 14 km WNW of Río Grande, Panama
- ID: `be48c9ca-de13-4986-8b56-f7173b75c694`; ключ: `live:usgs:earthquake:us6000u1zh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 08:15:01.493808+00; обновлено: 2026-10-30 16:05:00.289387+00

### 435. M4.6 earthquake - 63 km W of Bayan Hot, China
- ID: `f00225d8-48f0-400e-bba5-d04e036bd235`; ключ: `live:usgs:earthquake:us6000u200`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 14:15:01.329379+00; обновлено: 2026-10-30 16:05:00.289387+00

### 436. M5.3 earthquake - southern Mid-Atlantic Ridge
- ID: `083e07a6-0f24-4d61-8b1c-ec34e89848b4`; ключ: `live:usgs:earthquake:us6000u207`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 09:15:01.432291+00; обновлено: 2026-10-30 16:05:00.289387+00

### 437. M4.7 earthquake - 9 km NE of Boshkengash, Tajikistan
- ID: `40e9ef6c-266b-4e9d-849e-b52be9b3ae1e`; ключ: `live:usgs:earthquake:us6000u20g`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 11:15:01.697304+00; обновлено: 2026-10-30 16:05:00.289387+00

### 438. M4.5 earthquake - 71 km SW of Tambolaka, Indonesia
- ID: `233f010a-08c1-4b7b-9c60-e0de97993c9a`; ключ: `live:usgs:earthquake:us6000u20i`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 11:15:01.63388+00; обновлено: 2026-10-30 16:05:00.289387+00

### 439. M4.9 earthquake - 180 km SE of Vilyuchinsk, Russia
- ID: `5563eb28-b071-4ec9-8538-81221e5bb04a`; ключ: `live:usgs:earthquake:us6000u20z`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 13:15:01.575783+00; обновлено: 2026-10-30 16:05:00.289387+00

### 440. M6.8 earthquake - central Mid-Atlantic Ridge
- ID: `d1cfc7be-aa10-4906-bcce-9b8d34981a89`; ключ: `live:usgs:earthquake:us6000u214`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 13:15:01.520437+00; обновлено: 2026-10-30 16:05:00.289387+00

### 441. M4.5 earthquake - 26 km SSW of Zapotillo, Panama
- ID: `c727a4bf-f56c-4c7c-b444-07eb68e6d185`; ключ: `live:usgs:earthquake:us6000u21d`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 19:15:02.930166+00; обновлено: 2026-10-30 16:05:00.289387+00

### 442. M5.3 earthquake - 122 km S of Kokopo, Papua New Guinea
- ID: `89bff0a1-ae0e-4681-9a06-724458b6231c`; ключ: `live:usgs:earthquake:us6000u21s`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 15:15:01.620552+00; обновлено: 2026-10-30 16:05:00.289387+00

### 443. M4.8 earthquake - 8 km SE of Sarangani, Philippines
- ID: `4e64237f-5def-4744-87a0-7d8654f9e76a`; ключ: `live:usgs:earthquake:us6000u21y`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 18:15:02.370242+00; обновлено: 2026-10-30 16:05:00.289387+00

### 444. M5.1 earthquake - 119 km S of Kokopo, Papua New Guinea
- ID: `d31afcfd-bb8c-443c-b4e6-8e22b500e944`; ключ: `live:usgs:earthquake:us6000u23d`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 17:15:01.053295+00; обновлено: 2026-10-30 16:05:00.289387+00

### 445. M6.0 earthquake - 126 km S of Kokopo, Papua New Guinea
- ID: `129a8a7d-85ec-4058-9f70-44b9ff646650`; ключ: `live:usgs:earthquake:us6000u24c`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 19:15:02.801405+00; обновлено: 2026-10-30 16:05:00.289387+00

### 446. M4.8 earthquake - 5 km NW of Cepitá, Colombia
- ID: `60591862-3ece-46cd-9011-a0a9cea9a0eb`; ключ: `live:usgs:earthquake:us6000u25i`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-13 22:15:01.603309+00; обновлено: 2026-10-30 16:05:00.289387+00

### 447. M5.1 earthquake - 93 km NNW of Coquimbo, Chile
- ID: `8e275e16-c9c6-4c3d-a15c-312aa08ad05f`; ключ: `live:usgs:earthquake:us6000u26c`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-14 01:15:01.475886+00; обновлено: 2026-10-30 16:05:00.289387+00

### 448. M5.0 earthquake - 98 km NW of Coquimbo, Chile
- ID: `a2d342b4-1112-4cf6-bf28-54c6c8906994`; ключ: `live:usgs:earthquake:us6000u26f`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-14 01:15:01.369667+00; обновлено: 2026-10-30 16:05:00.289387+00

### 449. M4.6 earthquake - 75 km E of Kokopo, Papua New Guinea
- ID: `dd4b0ec8-cfb3-4148-874a-d6bfe37d922e`; ключ: `live:usgs:earthquake:us6000u26u`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-14 03:15:01.889095+00; обновлено: 2026-10-30 16:05:00.289387+00

### 450. M4.7 earthquake - 128 km S of Kokopo, Papua New Guinea
- ID: `d1202776-f354-4d19-a3c5-12c9f2fc3296`; ключ: `live:usgs:earthquake:us6000u271`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-14 05:15:03.207141+00; обновлено: 2026-10-30 16:05:00.289387+00

### 451. M4.9 earthquake - 16 km WSW of La Tirana, Chile
- ID: `fb354f8d-d6ce-45e1-9998-a8ef2c1d375b`; ключ: `live:usgs:earthquake:us6000u272`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-14 04:15:01.276746+00; обновлено: 2026-10-30 16:05:00.289387+00

### 452. M4.8 earthquake - North Atlantic Ocean
- ID: `da9f82d5-b78c-4164-8f4d-62f53544f90b`; ключ: `live:usgs:earthquake:us6000u273`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-14 04:15:01.470083+00; обновлено: 2026-10-30 16:05:00.289387+00

### 453. M4.7 earthquake - 10 km S of La Mesa, Panama
- ID: `25b1e58f-c9e9-4dd0-8c0f-a517f8be56dc`; ключ: `live:usgs:earthquake:us6000u27j`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-14 07:15:01.731149+00; обновлено: 2026-10-30 16:05:00.289387+00

### 454. M4.9 earthquake - 121 km S of Kokopo, Papua New Guinea
- ID: `0e4e01b0-931c-4668-b564-f5b8b7517747`; ключ: `live:usgs:earthquake:us6000u27u`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-14 08:15:01.550209+00; обновлено: 2026-10-30 16:05:00.289387+00

### 455. M4.6 earthquake - 42 km NNE of Kilimatinde, Tanzania
- ID: `26da3fa9-e307-4798-9442-e6c94456c5a4`; ключ: `live:usgs:earthquake:us6000u28e`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-14 13:15:01.725324+00; обновлено: 2026-10-30 16:05:00.289387+00

### 456. M5.9 earthquake - Fiji region
- ID: `4602a49a-4517-4506-80f9-148189e8c125`; ключ: `live:usgs:earthquake:us6000u28y`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-14 11:15:01.667204+00; обновлено: 2026-10-30 16:05:00.289387+00

### 457. M4.5 earthquake - 82 km SSW of Mil’kovo, Russia
- ID: `b7e8c866-2f90-47d7-a255-b151cc50a545`; ключ: `live:usgs:earthquake:us6000u2d6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 00:15:02.638516+00; обновлено: 2026-10-30 16:05:00.289387+00

### 458. M5.1 earthquake - 36 km E of Safotu, Samoa
- ID: `14308244-6158-4a3e-b723-679bde30cbd3`; ключ: `live:usgs:earthquake:us6000u2ec`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 04:15:01.455808+00; обновлено: 2026-10-30 16:05:00.289387+00

### 459. M4.8 earthquake - 30 km E of Safotu, Samoa
- ID: `bbdaebef-9c4d-45ec-a35f-93fdd0b9bae5`; ключ: `live:usgs:earthquake:us6000u2eh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 04:15:01.514948+00; обновлено: 2026-10-30 16:05:00.289387+00

### 460. M5.3 earthquake - 43 km SSE of Otorohanga, New Zealand
- ID: `67bc43b0-2981-413a-89cb-3c69dc1919fc`; ключ: `live:usgs:earthquake:us6000u2ev`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 06:15:01.815374+00; обновлено: 2026-10-30 16:05:00.289387+00

### 461. M4.8 earthquake - off the coast of Ecuador
- ID: `4e7fbdcd-5f39-4030-9710-867ebc5a4bd4`; ключ: `live:usgs:earthquake:us6000u2gd`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 12:15:02.373322+00; обновлено: 2026-10-30 16:05:00.289387+00

### 462. M4.7 earthquake - central Mid-Atlantic Ridge
- ID: `009a69e3-9221-4a5f-8c62-7f8ed1b29563`; ключ: `live:usgs:earthquake:us6000u2gk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 12:15:02.642186+00; обновлено: 2026-10-30 16:05:00.289387+00

### 463. M5.2 earthquake - 157 km W of Sola, Vanuatu
- ID: `bb16bc28-5476-4e71-9783-6a845f798f17`; ключ: `live:usgs:earthquake:us6000u2hp`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 14:15:01.759089+00; обновлено: 2026-10-30 16:05:00.289387+00

### 464. M4.7 earthquake - 114 km SSW of Nikolski, Alaska
- ID: `29e95eb2-edd9-4d2a-9209-f46c709bf586`; ключ: `live:usgs:earthquake:us6000u2hr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 14:15:01.727175+00; обновлено: 2026-10-30 16:05:00.289387+00

### 465. M4.5 earthquake - 9 km SSE of Los Asientos, Panama
- ID: `6576ea63-267e-4a73-8b4b-be904720a276`; ключ: `live:usgs:earthquake:us6000u2ht`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 15:15:02.027971+00; обновлено: 2026-10-30 16:05:00.289387+00

### 466. M5.2 earthquake - 107 km NNE of Hihifo, Tonga
- ID: `2fabb604-a2ef-4adb-8d39-4b5dbcb56252`; ключ: `live:usgs:earthquake:us6000u2hv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 14:15:01.688489+00; обновлено: 2026-10-30 16:05:00.289387+00

### 467. M4.9 earthquake - 198 km SSE of Vilyuchinsk, Russia
- ID: `ec00a350-2fc0-43a4-8665-37c131ee5f7b`; ключ: `live:usgs:earthquake:us6000u2i2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 16:15:01.980552+00; обновлено: 2026-10-30 16:05:00.289387+00

### 468. M4.5 earthquake - 22 km W of Tamarindo, Costa Rica
- ID: `09afd9f2-a437-4788-ae97-d78be898aa4d`; ключ: `live:usgs:earthquake:us6000u2i9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 17:15:01.133927+00; обновлено: 2026-10-30 16:05:00.289387+00

### 469. M4.5 earthquake - 44 km SSE of Champerico, Guatemala
- ID: `56749af3-946b-4bb9-93f6-a5cd69994872`; ключ: `live:usgs:earthquake:us6000u2kz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-15 21:15:01.557467+00; обновлено: 2026-10-30 16:05:00.289387+00

### 470. M6.9 earthquake - 76 km NE of Ozernovskiy, Russia
- ID: `cfa883ae-3b0a-4280-a9c8-df9457bcacbc`; ключ: `live:usgs:earthquake:us6000u2mq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 04:15:02.534789+00; обновлено: 2026-10-30 16:05:00.289387+00

### 471. M4.7 earthquake - 95 km SW of Brisas Barra de Suchiate, Mexico
- ID: `470d2167-5e92-4176-99a9-fe4553392763`; ключ: `live:usgs:earthquake:us6000u2n4`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 05:15:01.267139+00; обновлено: 2026-10-30 16:05:00.289387+00

### 472. M4.9 earthquake - 31 km ENE of Kinablangan, Philippines
- ID: `24dec649-34d9-4c12-ae0c-d77e8d391d0f`; ключ: `live:usgs:earthquake:us6000u2p2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 10:15:01.549532+00; обновлено: 2026-10-30 16:05:00.289387+00

### 473. M4.8 earthquake - southern East Pacific Rise
- ID: `bd888792-2040-4665-a755-ff57bc3c74d9`; ключ: `live:usgs:earthquake:us6000u2p5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 10:15:01.619104+00; обновлено: 2026-10-30 16:05:00.289387+00

### 474. M4.8 earthquake - 7 km WSW of Soconusco, Mexico
- ID: `ad140b92-d895-4e6a-974d-788bf59ef5b9`; ключ: `live:usgs:earthquake:us6000u2ph`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 12:15:02.517204+00; обновлено: 2026-10-30 16:05:00.289387+00

### 475. M4.9 earthquake - 119 km SSW of Merizo Village, Guam
- ID: `e34d005b-04c1-488a-a30a-bfcc01f50b75`; ключ: `live:usgs:earthquake:us6000u2pl`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 13:15:01.970187+00; обновлено: 2026-10-30 16:05:00.289387+00

### 476. M4.7 earthquake - 10 km SE of Lamitan, Philippines
- ID: `e7e69c74-688d-4b6a-886f-ea86a5362e92`; ключ: `live:usgs:earthquake:us6000u2pp`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 13:15:01.911204+00; обновлено: 2026-10-30 16:05:00.289387+00

### 477. M4.5 earthquake - 51 km ESE of Juradó, Colombia
- ID: `6d79dd60-76ad-4794-81e2-d9910aa2ecb2`; ключ: `live:usgs:earthquake:us6000u2pw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 19:15:02.732994+00; обновлено: 2026-10-30 16:05:00.289387+00

### 478. M5.0 earthquake - Auckland Islands, New Zealand region
- ID: `5fe4b26e-7d1a-4633-a0fb-369f78cbcb86`; ключ: `live:usgs:earthquake:us6000u2q5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 15:15:04.837244+00; обновлено: 2026-10-30 16:05:00.289387+00

### 479. M4.6 earthquake - 153 km W of Neiafu, Tonga
- ID: `351baccd-b677-4dea-adb3-cdfb8c64ab49`; ключ: `live:usgs:earthquake:us6000u2qd`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 16:15:01.547336+00; обновлено: 2026-10-30 16:05:00.289387+00

### 480. M4.7 earthquake - 186 km SSE of Vilyuchinsk, Russia
- ID: `48566db4-5a46-47c0-8ef7-68d510e70c96`; ключ: `live:usgs:earthquake:us6000u2qf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 19:15:02.637853+00; обновлено: 2026-10-30 16:05:00.289387+00

### 481. M4.6 earthquake - 41 km NNE of Kilimatinde, Tanzania
- ID: `869b6125-d712-4093-be70-0a05f8a34f2d`; ключ: `live:usgs:earthquake:us6000u2qn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 17:15:01.314398+00; обновлено: 2026-10-30 16:05:00.289387+00

### 482. M5.2 earthquake - off the coast of Ecuador
- ID: `cac51a56-b1a3-401e-93e6-7bf34070ce31`; ключ: `live:usgs:earthquake:us6000u2v8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 20:15:02.138315+00; обновлено: 2026-10-30 16:05:00.289387+00

### 483. M4.5 earthquake - south of the Fiji Islands
- ID: `8cb3854c-16ce-434a-bde6-f218997b18e4`; ключ: `live:usgs:earthquake:us6000u2w7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 00:15:02.319976+00; обновлено: 2026-10-30 16:05:00.289387+00

### 484. M4.5 earthquake - 70 km NNE of Mīnāb, Iran
- ID: `40868fa5-846a-4f41-9620-237424b6d3a0`; ключ: `live:usgs:earthquake:us6000u2w9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 00:15:02.177757+00; обновлено: 2026-10-30 16:05:00.289387+00

### 485. M4.6 earthquake - 12 km SSE of Tebario, Panama
- ID: `8e6e1d5b-a2f9-4f06-8760-6fc0c2d66d49`; ключ: `live:usgs:earthquake:us6000u2wn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-16 23:15:01.603022+00; обновлено: 2026-10-30 16:05:00.289387+00

### 486. M4.6 earthquake - 6 km NNE of Sámi, Greece
- ID: `76a57be3-5f76-46ec-9b2d-fc67fd1f70f0`; ключ: `live:usgs:earthquake:us6000u2ww`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 01:15:02.355778+00; обновлено: 2026-10-30 16:05:00.289387+00

### 487. M4.9 earthquake - 115 km SW of Puerto Madero, Mexico
- ID: `e6ae86be-715a-48c7-972e-273e65779573`; ключ: `live:usgs:earthquake:us6000u2x7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 02:15:02.541284+00; обновлено: 2026-10-30 16:05:00.289387+00

### 488. M4.8 earthquake - 196 km SSE of Alo, Wallis and Futuna
- ID: `aa6a9208-9629-4492-8dc2-cbff14d79db0`; ключ: `live:usgs:earthquake:us6000u2xs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 05:15:01.52921+00; обновлено: 2026-10-30 16:05:00.289387+00

### 489. M5.7 earthquake - 48 km WNW of Khuzdar, Pakistan
- ID: `9bd59b82-3eb0-4f40-84de-e0c5fb1f9436`; ключ: `live:usgs:earthquake:us6000u2y1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 06:15:01.874787+00; обновлено: 2026-10-30 16:05:00.289387+00

### 490. M4.5 earthquake - 59 km NNW of Ruteng, Indonesia
- ID: `35580814-4b1e-48f1-8b39-e7097ad4d66d`; ключ: `live:usgs:earthquake:us6000u2yw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 08:15:01.963871+00; обновлено: 2026-10-30 16:05:00.289387+00

### 491. M4.5 earthquake - 80 km NW of Sola, Vanuatu
- ID: `46a1768f-d95a-4dde-ad8d-86c751910079`; ключ: `live:usgs:earthquake:us6000u2yz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 08:15:01.918299+00; обновлено: 2026-10-30 16:05:00.289387+00

### 492. M4.8 earthquake - 110 km NE of Norsup, Vanuatu
- ID: `4d3988af-c486-410d-bc1e-b0fdd6a6a807`; ключ: `live:usgs:earthquake:us6000u2z9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 10:15:02.218718+00; обновлено: 2026-10-30 16:05:00.289387+00

### 493. M4.6 earthquake - 51 km N of Pante Makasar, Timor Leste
- ID: `cafe7955-8e5c-4fd6-8930-5a6ab7803171`; ключ: `live:usgs:earthquake:us6000u2zb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 10:15:02.162556+00; обновлено: 2026-10-30 16:05:00.289387+00

### 494. M4.6 earthquake - 70 km W of Tambolaka, Indonesia
- ID: `c4c063de-cd8f-4f55-b926-eb492a18fc9e`; ключ: `live:usgs:earthquake:us6000u300`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-18 05:15:01.833495+00; обновлено: 2026-10-30 16:05:00.289387+00

### 495. M5.2 earthquake - 86 km SW of Brisas Barra de Suchiate, Mexico
- ID: `152bd75a-c0e2-4d66-a166-74b85f6fcd8d`; ключ: `live:usgs:earthquake:us6000u309`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 15:15:02.075523+00; обновлено: 2026-10-30 16:05:00.289387+00

### 496. M4.6 earthquake - 88 km SSW of Uyuni, Bolivia
- ID: `7232cd1e-a9a0-4886-9d27-fddc3891e4f0`; ключ: `live:usgs:earthquake:us6000u30x`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-17 19:15:02.337192+00; обновлено: 2026-10-30 16:05:00.289387+00

### 497. M4.8 earthquake - 31 km SE of Kainantu, Papua New Guinea
- ID: `c951008f-6a0d-4919-80c5-df79c44e46f0`; ключ: `live:usgs:earthquake:us6000u32r`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-18 01:15:01.680127+00; обновлено: 2026-10-30 16:05:00.289387+00

### 498. M5.2 earthquake - 55 km NNW of Ruteng, Indonesia
- ID: `a58980d3-25f0-4a54-affb-93c4913f560c`; ключ: `live:usgs:earthquake:us6000u34e`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-18 09:15:01.457378+00; обновлено: 2026-10-30 16:05:00.289387+00

### 499. M4.5 earthquake - Kermadec Islands, New Zealand
- ID: `1f2fcc91-dd74-4ac9-a89e-3cf733f0ba67`; ключ: `live:usgs:earthquake:us6000u35l`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-18 13:15:02.883229+00; обновлено: 2026-10-30 16:05:00.289387+00

### 500. M4.6 earthquake - Carlsberg Ridge
- ID: `1758cb81-25f7-4e99-b439-c94b2baee70e`; ключ: `live:usgs:earthquake:us6000u366`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-18 18:15:02.221793+00; обновлено: 2026-10-30 16:05:00.289387+00

### 501. M4.7 earthquake - 20 km SW of Sandy Point Town, Saint Kitts and Nevis
- ID: `a8fac656-99c6-4391-a3a8-94c505a56bc0`; ключ: `live:usgs:earthquake:us6000u36d`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-18 16:15:06.291607+00; обновлено: 2026-10-30 16:05:00.289387+00

### 502. M4.5 earthquake - 0 km NE of Río Grande, Panama
- ID: `955a41c8-cb1c-43fc-87c3-c60e280ac561`; ключ: `live:usgs:earthquake:us6000u36m`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-18 19:15:01.415689+00; обновлено: 2026-10-30 16:05:00.289387+00

### 503. M5.2 earthquake - 71 km ESE of ‘Ohonua, Tonga
- ID: `cb3752e3-cfc9-437e-be41-3023c5ee16d4`; ключ: `live:usgs:earthquake:us6000u37h`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-18 20:15:01.94134+00; обновлено: 2026-10-30 16:05:00.289387+00

### 504. M4.7 earthquake - 147 km SSW of Kokopo, Papua New Guinea
- ID: `e5e73cd3-b947-4c3a-8722-9844931d1e86`; ключ: `live:usgs:earthquake:us6000u38b`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-18 23:15:02.022328+00; обновлено: 2026-10-30 16:05:00.289387+00

### 505. M5.1 earthquake - 129 km SSE of Kokopo, Papua New Guinea
- ID: `e2c09ff6-aac8-4bbd-b79f-e4d654dfd2b8`; ключ: `live:usgs:earthquake:us6000u38g`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-18 23:15:01.906185+00; обновлено: 2026-10-30 16:05:00.289387+00

### 506. M4.5 earthquake - Fiji region
- ID: `472cf9c5-f990-4bbd-a645-8cdb1f767793`; ключ: `live:usgs:earthquake:us6000u38i`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 00:15:01.294619+00; обновлено: 2026-10-30 16:05:00.289387+00

### 507. M4.9 earthquake - 68 km WSW of San Juan del Sur, Nicaragua
- ID: `fe4f43b3-4c45-4aa9-835a-85ef421e82f7`; ключ: `live:usgs:earthquake:us6000u3a8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 06:15:01.345448+00; обновлено: 2026-10-30 16:05:00.289387+00

### 508. M4.5 earthquake - Banda Sea
- ID: `7d38687e-188b-4a55-8fc4-2f6dce8a3b2d`; ключ: `live:usgs:earthquake:us6000u3ar`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 07:15:01.824471+00; обновлено: 2026-10-30 16:05:00.289387+00

### 509. M4.9 earthquake - 203 km WNW of Port-Olry, Vanuatu
- ID: `2a9e44ad-600f-40e4-a827-b3704ae75d86`; ключ: `live:usgs:earthquake:us6000u3b8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 09:15:01.976486+00; обновлено: 2026-10-30 16:05:00.289387+00

### 510. M6.0 earthquake - 186 km NW of Port-Olry, Vanuatu
- ID: `275ca9e3-0630-450c-958b-b8e2efb130c3`; ключ: `live:usgs:earthquake:us6000u3bc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 08:15:02.806828+00; обновлено: 2026-10-30 16:05:00.289387+00

### 511. M5.3 earthquake - 188 km NW of Port-Olry, Vanuatu
- ID: `804f21a0-e154-4fa2-9276-3311f274d1e2`; ключ: `live:usgs:earthquake:us6000u3be`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 08:15:02.737438+00; обновлено: 2026-10-30 16:05:00.289387+00

### 512. M5.4 earthquake - 184 km WNW of Port-Olry, Vanuatu
- ID: `f85a3741-007b-4e72-a5da-c240333dfc17`; ключ: `live:usgs:earthquake:us6000u3bi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 09:15:01.831953+00; обновлено: 2026-10-30 16:05:00.289387+00

### 513. M5.2 earthquake - 211 km WNW of Port-Olry, Vanuatu
- ID: `321eb78f-4ede-49d8-a56f-73e475abee0d`; ключ: `live:usgs:earthquake:us6000u3bk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 09:15:01.749801+00; обновлено: 2026-10-30 16:05:00.289387+00

### 514. M4.5 earthquake - 2 km W of Lunca Jariștei, Romania
- ID: `1b0d7599-b993-4e8c-8e39-7a1b6697cf48`; ключ: `live:usgs:earthquake:us6000u3bs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 10:15:02.260917+00; обновлено: 2026-10-30 16:05:00.289387+00

### 515. M4.9 earthquake - 202 km NW of Port-Olry, Vanuatu
- ID: `1ab2f365-fb50-4da5-a62b-9f49eb7eaee5`; ключ: `live:usgs:earthquake:us6000u3bu`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 11:15:02.393113+00; обновлено: 2026-10-30 16:05:00.289387+00

### 516. M4.7 earthquake - 163 km WNW of Tobelo, Indonesia
- ID: `9824351a-0841-4ecc-8714-ba5fd3913586`; ключ: `live:usgs:earthquake:us6000u3bv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 11:15:02.363383+00; обновлено: 2026-10-30 16:05:00.289387+00

### 517. M4.9 earthquake - 115 km NNW of Sola, Vanuatu
- ID: `e33adda3-76b7-4e09-a704-78273dc28996`; ключ: `live:usgs:earthquake:us6000u3bz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 11:15:02.336963+00; обновлено: 2026-10-30 16:05:00.289387+00

### 518. M4.9 earthquake - 54 km NE of Labuan Bajo, Indonesia
- ID: `b2a8f1f4-e696-4a6e-9a12-f8f93a9499de`; ключ: `live:usgs:earthquake:us6000u3c1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 10:15:02.210673+00; обновлено: 2026-10-30 16:05:00.289387+00

### 519. M4.7 earthquake - 53 km NNE of Labuan Bajo, Indonesia
- ID: `4c9c0403-53b1-463f-8e59-c9134927896b`; ключ: `live:usgs:earthquake:us6000u3c5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 11:15:02.019673+00; обновлено: 2026-10-30 16:05:00.289387+00

### 520. M5.4 earthquake - 196 km NW of Port-Olry, Vanuatu
- ID: `8d0c70f2-a678-430d-a37d-74ae48638192`; ключ: `live:usgs:earthquake:us6000u3c6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 11:15:01.963019+00; обновлено: 2026-10-30 16:05:00.289387+00

### 521. M5.0 earthquake - 31 km NW of Jiangyou, China
- ID: `6b1f688d-5b95-45ff-b8d6-1e84c177a34c`; ключ: `live:usgs:earthquake:us6000u3c7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 12:15:01.891672+00; обновлено: 2026-10-30 16:05:00.289387+00

### 522. M4.8 earthquake - 212 km WNW of Port-Olry, Vanuatu
- ID: `6c150567-6be5-4ed6-bea7-3c101e82d2e2`; ключ: `live:usgs:earthquake:us6000u3ce`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 12:15:01.825805+00; обновлено: 2026-10-30 16:05:00.289387+00

### 523. M4.8 earthquake - 56 km N of Ruteng, Indonesia
- ID: `d83fcfbe-48af-4350-b4bc-f895e006157d`; ключ: `live:usgs:earthquake:us6000u3ch`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 13:15:01.858354+00; обновлено: 2026-10-30 16:05:00.289387+00

### 524. M5.3 earthquake - 116 km WNW of Höfn, Iceland
- ID: `5e2527e2-0374-4ca0-a4e7-2bf8dbd114fa`; ключ: `live:usgs:earthquake:us6000u3ct`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 15:15:01.982206+00; обновлено: 2026-10-30 16:05:00.289387+00

### 525. M4.6 earthquake - 5 km E of San José El Ídolo, Guatemala
- ID: `1aec1f2c-9b06-493e-96e6-1f8dd4566cd1`; ключ: `live:usgs:earthquake:us6000u3cu`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 16:15:01.670509+00; обновлено: 2026-10-30 16:05:00.289387+00

### 526. M4.9 earthquake - 77 km WSW of Murghob, Tajikistan
- ID: `24502ae8-d887-407e-ab39-d1c7915d828e`; ключ: `live:usgs:earthquake:us6000u3d2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 16:15:01.629826+00; обновлено: 2026-10-30 16:05:00.289387+00

### 527. M4.6 earthquake - south of the Fiji Islands
- ID: `1a135587-3622-44e1-9289-cf6b57bff2dc`; ключ: `live:usgs:earthquake:us6000u3db`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 17:15:01.022363+00; обновлено: 2026-10-30 16:05:00.289387+00

### 528. M5.1 earthquake - South Sandwich Islands region
- ID: `77fe453f-8889-4480-82f6-871ec5797a2a`; ключ: `live:usgs:earthquake:us6000u3ft`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 18:15:01.752777+00; обновлено: 2026-10-30 16:05:00.289387+00

### 529. M4.8 earthquake - 88 km WNW of Hihifo, Tonga
- ID: `77efbae0-f8f4-4294-a22b-ffe3b9f7b7f4`; ключ: `live:usgs:earthquake:us6000u3g6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 19:15:01.535073+00; обновлено: 2026-10-30 16:05:00.289387+00

### 530. M5.7 earthquake - 198 km NW of Port-Olry, Vanuatu
- ID: `f8abd0b9-7a1c-489e-85c7-fd843271c9dc`; ключ: `live:usgs:earthquake:us6000u3ga`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 19:15:01.462951+00; обновлено: 2026-10-30 16:05:00.289387+00

### 531. M5.7 earthquake - 203 km WNW of Port-Olry, Vanuatu
- ID: `840bdba3-84c9-4309-b935-e2d2c3392eb4`; ключ: `live:usgs:earthquake:us6000u3ge`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 20:15:01.779229+00; обновлено: 2026-10-30 16:05:00.289387+00

### 532. M4.5 earthquake - Kuril Islands
- ID: `9c07deef-f4ae-48e6-a84a-b2261a230a92`; ключ: `live:usgs:earthquake:us6000u3i2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-19 23:15:02.973949+00; обновлено: 2026-10-30 16:05:00.289387+00

### 533. M4.9 earthquake - 52 km S of Kokopo, Papua New Guinea
- ID: `f9bc3395-78a1-473c-bcdc-0a168f3aad8c`; ключ: `live:usgs:earthquake:us6000u3ic`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 00:15:01.494106+00; обновлено: 2026-10-30 16:05:00.289387+00

### 534. M5.0 earthquake - 205 km NW of Port-Olry, Vanuatu
- ID: `2296b0ab-63ce-4dfe-a181-28252c338a1c`; ключ: `live:usgs:earthquake:us6000u3j1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 01:15:04.570564+00; обновлено: 2026-10-30 16:05:00.289387+00

### 535. M4.5 earthquake - 156 km SE of Kuqa, China
- ID: `2f141279-0a58-4fa9-893e-0ab6aa1395d3`; ключ: `live:usgs:earthquake:us6000u3j5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 02:15:02.129694+00; обновлено: 2026-10-30 16:05:00.289387+00

### 536. M5.0 earthquake - Pagan region, Northern Mariana Islands
- ID: `21ee4af2-70dc-41f3-8414-69ecbc6f0e50`; ключ: `live:usgs:earthquake:us6000u3jd`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 03:15:01.614238+00; обновлено: 2026-10-30 16:05:00.289387+00

### 537. M6.3 earthquake - 197 km NW of Port-Olry, Vanuatu
- ID: `d2d268b1-bfa1-44c7-a93b-f922aefb759a`; ключ: `live:usgs:earthquake:us6000u3jl`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 05:15:01.015405+00; обновлено: 2026-10-30 16:05:00.289387+00

### 538. M5.2 earthquake - 206 km NW of Port-Olry, Vanuatu
- ID: `9cb3659d-9228-47d4-812e-d527850c75c7`; ключ: `live:usgs:earthquake:us6000u3k5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 07:15:02.178684+00; обновлено: 2026-10-30 16:05:00.289387+00

### 539. M4.6 earthquake - 7 km SE of San Julian, Philippines
- ID: `0ea82363-8654-4121-b6ce-0e0be7f81780`; ключ: `live:usgs:earthquake:us6000u3k7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 09:15:02.022365+00; обновлено: 2026-10-30 16:05:00.289387+00

### 540. M5.1 earthquake - 263 km WSW of Yanglong, China
- ID: `87c7429a-9087-430c-8a74-d3d747f5d90f`; ключ: `live:usgs:earthquake:us6000u3ka`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 07:15:02.124191+00; обновлено: 2026-10-30 16:05:00.289387+00

### 541. M4.9 earthquake - Pagan region, Northern Mariana Islands
- ID: `1020ddcb-3bdb-4831-80d7-c06c9a00a202`; ключ: `live:usgs:earthquake:us6000u3kg`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 08:15:02.293985+00; обновлено: 2026-10-30 16:05:00.289387+00

### 542. M4.9 earthquake - 199 km NW of Port-Olry, Vanuatu
- ID: `7b2fe8d6-cc97-4fdc-9a2c-92adf351c662`; ключ: `live:usgs:earthquake:us6000u3l0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 09:15:01.874964+00; обновлено: 2026-10-30 16:05:00.289387+00

### 543. M4.5 earthquake - 100 km SSW of Alo, Wallis and Futuna
- ID: `d8c2421b-569c-4199-8ced-dc808f960467`; ключ: `live:usgs:earthquake:us6000u3l3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 10:15:01.310327+00; обновлено: 2026-10-30 16:05:00.289387+00

### 544. M5.0 earthquake - 81 km S of Sand Point, Alaska
- ID: `4b8dc104-fa85-443e-b67b-13046d98ff21`; ключ: `live:usgs:earthquake:us6000u3lf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 11:15:01.870671+00; обновлено: 2026-10-30 16:05:00.289387+00

### 545. M4.9 earthquake - 184 km NW of Port-Olry, Vanuatu
- ID: `8e8ab152-32fd-4e68-b8b6-41161225b0fe`; ключ: `live:usgs:earthquake:us6000u3li`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 13:15:01.43898+00; обновлено: 2026-10-30 16:05:00.289387+00

### 546. M4.5 earthquake - 142 km SSW of Abepura, Indonesia
- ID: `b1b61b2d-3665-4373-a21b-5c784837f8ab`; ключ: `live:usgs:earthquake:us6000u3lx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 16:15:01.445854+00; обновлено: 2026-10-30 16:05:00.289387+00

### 547. M4.5 earthquake - 111 km S of Kokopo, Papua New Guinea
- ID: `80581b4b-2a7c-427e-b07c-267edf9a8d08`; ключ: `live:usgs:earthquake:us6000u3m7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 17:15:01.501622+00; обновлено: 2026-10-30 16:05:00.289387+00

### 548. M5.0 earthquake - 21 km SW of Meulaboh, Indonesia
- ID: `04fc87b5-62fb-49a7-9c4c-88e5a7e56df4`; ключ: `live:usgs:earthquake:us6000u3nc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 17:15:01.47085+00; обновлено: 2026-10-30 16:05:00.289387+00

### 549. M4.8 earthquake - south of the Fiji Islands
- ID: `40fd2772-b87a-470e-9e63-185517d5e123`; ключ: `live:usgs:earthquake:us6000u3nd`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 17:15:01.421785+00; обновлено: 2026-10-30 16:05:00.289387+00

### 550. M5.4 earthquake - 192 km S of Burica, Panama
- ID: `398c290d-1eb9-435b-b77b-58976969ebb7`; ключ: `live:usgs:earthquake:us6000u3nl`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 18:15:01.016435+00; обновлено: 2026-10-30 16:05:00.289387+00

### 551. M4.5 earthquake - 215 km S of Burica, Panama
- ID: `d29b13c3-a813-40a1-a416-13835d55b113`; ключ: `live:usgs:earthquake:us6000u3nn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 19:15:01.435917+00; обновлено: 2026-10-30 16:05:00.289387+00

### 552. M5.1 earthquake - 39 km W of Mosteiros, Portugal
- ID: `bb825618-8c0f-4048-beed-713ffc124b93`; ключ: `live:usgs:earthquake:us6000u3p1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 19:15:01.376989+00; обновлено: 2026-10-30 16:05:00.289387+00

### 553. M4.7 earthquake - Kuril Islands
- ID: `aa696498-9514-40b4-9c85-4ad80e369c1d`; ключ: `live:usgs:earthquake:us6000u3pm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 21:15:01.468355+00; обновлено: 2026-10-30 16:05:00.289387+00

### 554. M4.9 earthquake - 187 km NW of Port-Olry, Vanuatu
- ID: `c23996f1-ec98-4b6b-b1e4-dca543d75c7c`; ключ: `live:usgs:earthquake:us6000u3pq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-20 21:15:01.419487+00; обновлено: 2026-10-30 16:05:00.289387+00

### 555. M4.6 earthquake - 115 km NNE of Barishal, Pakistan
- ID: `84380546-d2d3-4df7-a505-97656d4a1b99`; ключ: `live:usgs:earthquake:us6000u3r1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 00:15:01.471813+00; обновлено: 2026-10-30 16:05:00.289387+00

### 556. M4.9 earthquake - south of the Fiji Islands
- ID: `002b4ece-cad1-4e62-81d2-e952fe80e4b0`; ключ: `live:usgs:earthquake:us6000u3r3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 00:15:01.427915+00; обновлено: 2026-10-30 16:05:00.289387+00

### 557. M4.5 earthquake - 2 km N of Honchō, Japan
- ID: `2fe8fa3c-33ec-4ee5-905d-e0b9f7cd0ba9`; ключ: `live:usgs:earthquake:us6000u3rn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 02:15:01.11088+00; обновлено: 2026-10-30 16:05:00.289387+00

### 558. M5.0 earthquake - south of Panama
- ID: `427d447b-e120-405a-8330-4a22b5c6a650`; ключ: `live:usgs:earthquake:us6000u3rr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 02:15:01.067488+00; обновлено: 2026-10-30 16:05:00.289387+00

### 559. M4.7 earthquake - 173 km NW of Port-Olry, Vanuatu
- ID: `dab8e536-56c9-46c7-9880-758e19d71f14`; ключ: `live:usgs:earthquake:us6000u3sj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 05:15:01.623027+00; обновлено: 2026-10-30 16:05:00.289387+00

### 560. M5.1 earthquake - 164 km NE of Lospalos, Timor Leste
- ID: `588c94aa-eecc-4251-b792-b474c78eb38f`; ключ: `live:usgs:earthquake:us6000u3t4`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 08:15:01.95934+00; обновлено: 2026-10-30 16:05:00.289387+00

### 561. M5.2 earthquake - 68 km NE of Cabatuan, Philippines
- ID: `6a57edb1-2f4e-4314-b6c5-344342fbea80`; ключ: `live:usgs:earthquake:us6000u3t6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 09:15:01.767202+00; обновлено: 2026-10-30 16:05:00.289387+00

### 562. M4.5 earthquake - 158 km S of False Pass, Alaska
- ID: `6f6809b5-7204-41e4-8c30-0080a1572aac`; ключ: `live:usgs:earthquake:us6000u3tn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 14:15:01.316375+00; обновлено: 2026-10-30 16:05:00.289387+00

### 563. M4.9 earthquake - 207 km WNW of Port-Olry, Vanuatu
- ID: `676d24d0-4484-4a51-9db1-7f355e3060af`; ключ: `live:usgs:earthquake:us6000u3ub`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 17:15:01.738372+00; обновлено: 2026-10-30 16:05:00.289387+00

### 564. M4.7 earthquake - 33 km NE of Shizunai-furukawachō, Japan
- ID: `edc5dcaf-7071-4fcb-9ade-f6616aa1a1f1`; ключ: `live:usgs:earthquake:us6000u3uc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 17:15:01.708159+00; обновлено: 2026-10-30 16:05:00.289387+00

### 565. M5.0 earthquake - 194 km WNW of Port-Olry, Vanuatu
- ID: `f3a007a9-da19-49ce-9c22-f16ea2d8c1f6`; ключ: `live:usgs:earthquake:us6000u3ue`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 16:15:01.605303+00; обновлено: 2026-10-30 16:05:00.289387+00

### 566. M4.9 earthquake - 208 km WNW of Port-Olry, Vanuatu
- ID: `08dad05d-a174-40ff-a791-7055ed27b61d`; ключ: `live:usgs:earthquake:us6000u3uk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 17:15:01.633161+00; обновлено: 2026-10-30 16:05:00.289387+00

### 567. M4.6 earthquake - 208 km SE of Severo-Kuril’sk, Russia
- ID: `b24a2901-2ecc-46c9-a687-e1fcb6aa8eec`; ключ: `live:usgs:earthquake:us6000u3w6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 19:15:01.831281+00; обновлено: 2026-10-30 16:05:00.289387+00

### 568. M5.1 earthquake - south of Africa
- ID: `a618ce4c-de43-48e8-8720-7b6f6a08e4fc`; ключ: `live:usgs:earthquake:us6000u3wh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 19:15:01.739248+00; обновлено: 2026-10-30 16:05:00.289387+00

### 569. M4.7 earthquake - 202 km WNW of Port-Olry, Vanuatu
- ID: `9fa28ec7-06b3-4f76-bd48-c7561a4ddbb6`; ключ: `live:usgs:earthquake:us6000u3ws`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 21:15:02.020694+00; обновлено: 2026-10-30 16:05:00.289387+00

### 570. M5.0 earthquake - Reykjanes Ridge
- ID: `5e8c18ef-37b6-4df6-b1bc-67b48c5452c7`; ключ: `live:usgs:earthquake:us6000u3x2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 20:15:02.723634+00; обновлено: 2026-10-30 16:05:00.289387+00

### 571. M5.0 earthquake - 198 km WNW of Port-Olry, Vanuatu
- ID: `13914523-cee0-49eb-81d9-4cf39972f4b7`; ключ: `live:usgs:earthquake:us6000u3xx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 22:15:01.542742+00; обновлено: 2026-10-30 16:05:00.289387+00

### 572. M4.9 earthquake - 68 km NNW of Khorixas, Namibia
- ID: `c3143b72-775e-4fba-b37d-26d8afe03dcc`; ключ: `live:usgs:earthquake:us6000u3y1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 21:15:01.891804+00; обновлено: 2026-10-30 16:05:00.289387+00

### 573. M5.3 earthquake - Reykjanes Ridge
- ID: `b4f3a819-d0ed-469c-8319-4ad7a0abae89`; ключ: `live:usgs:earthquake:us6000u3yj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 22:15:01.440349+00; обновлено: 2026-10-30 16:05:00.289387+00

### 574. M5.0 earthquake - Reykjanes Ridge
- ID: `ed22faed-9672-45a7-ade3-14c2336c8718`; ключ: `live:usgs:earthquake:us6000u3yp`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-21 22:15:01.387997+00; обновлено: 2026-10-30 16:05:00.289387+00

### 575. M4.6 earthquake - 97 km SW of El Palmarcito, Mexico
- ID: `1f7581cb-e460-4b71-a062-d455f4ad32dd`; ключ: `live:usgs:earthquake:us6000u40r`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 04:15:02.722417+00; обновлено: 2026-10-30 16:05:00.289387+00

### 576. M4.8 earthquake - Reykjanes Ridge
- ID: `f6c1b010-0f9d-4cde-a41a-4426d1f8adf7`; ключ: `live:usgs:earthquake:us6000u411`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 06:15:01.881201+00; обновлено: 2026-10-30 16:05:00.289387+00

### 577. M4.8 earthquake - 86 km S of Kokopo, Papua New Guinea
- ID: `5afbe812-77e7-4b50-909e-613824ca44a4`; ключ: `live:usgs:earthquake:us6000u417`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 06:15:01.840746+00; обновлено: 2026-10-30 16:05:00.289387+00

### 578. M4.8 earthquake - Balleny Islands region
- ID: `79dbbe78-919b-4cc8-a4b1-d32ac44574e2`; ключ: `live:usgs:earthquake:us6000u41y`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 09:15:01.984998+00; обновлено: 2026-10-30 16:05:00.289387+00

### 579. M4.6 earthquake - 49 km NE of Yigo Village, Guam
- ID: `c29eefdf-24eb-42b8-a77d-b1344cc510d4`; ключ: `live:usgs:earthquake:us6000u41z`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 09:15:01.952227+00; обновлено: 2026-10-30 16:05:00.289387+00

### 580. M4.5 earthquake - 136 km NE of Petropavlovsk-Kamchatsky, Russia
- ID: `f1a3aff5-1785-4352-bd70-fb2d504b15ef`; ключ: `live:usgs:earthquake:us6000u423`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 09:15:01.895648+00; обновлено: 2026-10-30 16:05:00.289387+00

### 581. M4.6 earthquake - 11 km W of Ashkāsham, Afghanistan
- ID: `910cf490-b90a-4e45-b6da-748d6c9a6d07`; ключ: `live:usgs:earthquake:us6000u42e`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 11:15:02.485353+00; обновлено: 2026-10-30 16:05:00.289387+00

### 582. M4.9 earthquake - 85 km NNW of Curup, Indonesia
- ID: `7d372b04-1eae-4078-9f9f-6c586316436f`; ключ: `live:usgs:earthquake:us6000u42q`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 12:15:01.48648+00; обновлено: 2026-10-30 16:05:00.289387+00

### 583. M4.9 earthquake - 200 km NW of Port-Olry, Vanuatu
- ID: `d678c968-9ea3-435d-b14e-9e898d1ade56`; ключ: `live:usgs:earthquake:us6000u432`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 13:15:01.554151+00; обновлено: 2026-10-30 16:05:00.289387+00

### 584. M7.0 earthquake - 191 km ENE of Nagqu, China
- ID: `bd3ff852-48be-4f4e-b77e-8e69cc20b65f`; ключ: `live:usgs:earthquake:us6000u43g`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 45.000; последний расчёт: 45.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 15:15:01.392173+00; обновлено: 2026-10-30 16:05:00.289387+00

### 585. M5.2 earthquake - 201 km ENE of Nagqu, China
- ID: `9b84449c-7faf-49b6-a649-0ac3966280cd`; ключ: `live:usgs:earthquake:us6000u44n`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 16:15:02.315342+00; обновлено: 2026-10-30 16:05:00.289387+00

### 586. M4.7 earthquake - 139 km ENE of Kashgar, China
- ID: `a2397fb6-47de-4bc9-a172-4f9d8ba6aba3`; ключ: `live:usgs:earthquake:us6000u44u`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 19:15:01.989616+00; обновлено: 2026-10-30 16:05:00.289387+00

### 587. M4.9 earthquake - western Xizang
- ID: `8a31d7fa-c77e-4151-a83c-481fc54d18fa`; ключ: `live:usgs:earthquake:us6000u44w`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 16:15:02.243453+00; обновлено: 2026-10-30 16:05:00.289387+00

### 588. M4.9 earthquake - 210 km ENE of Nagqu, China
- ID: `96694b97-e90c-43fa-9ad3-171df8cb7090`; ключ: `live:usgs:earthquake:us6000u451`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 19:15:01.932677+00; обновлено: 2026-10-30 16:05:00.289387+00

### 589. M4.6 earthquake - 193 km NE of Nagqu, China
- ID: `c9f92bba-2a6c-4c33-824c-a62d6fa4d567`; ключ: `live:usgs:earthquake:us6000u455`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 20:15:01.540976+00; обновлено: 2026-10-30 16:05:00.289387+00

### 590. M4.5 earthquake - 203 km ENE of Nagqu, China
- ID: `5b51a811-f26a-427f-a963-5f7a937f58e4`; ключ: `live:usgs:earthquake:us6000u458`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 20:15:01.519311+00; обновлено: 2026-10-30 16:05:00.289387+00

### 591. M4.8 earthquake - 144 km SSW of ‘Ohonua, Tonga
- ID: `76e04f65-7642-4932-a5c3-8664d654b2bb`; ключ: `live:usgs:earthquake:us6000u459`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 18:15:01.686061+00; обновлено: 2026-10-30 16:05:00.289387+00

### 592. M4.7 earthquake - 190 km ENE of Nagqu, China
- ID: `1202ea71-4788-4022-9a95-30eff26ea1b4`; ключ: `live:usgs:earthquake:us6000u45a`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 20:15:01.471455+00; обновлено: 2026-10-30 16:05:00.289387+00

### 593. M4.8 earthquake - 39 km NE of Shikotan, Russia
- ID: `554a7fee-cbf7-4043-884e-b07bc087b0ea`; ключ: `live:usgs:earthquake:us6000u45f`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 18:15:01.64399+00; обновлено: 2026-10-30 16:05:00.289387+00

### 594. M5.0 earthquake - 207 km ENE of Nagqu, China
- ID: `e7080b26-f30e-4a61-a4d5-b6ce32a72c18`; ключ: `live:usgs:earthquake:us6000u45j`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 19:15:01.767206+00; обновлено: 2026-10-30 16:05:00.289387+00

### 595. M4.9 earthquake - 104 km NNE of Hihifo, Tonga
- ID: `a8676630-0af0-4ce1-a873-fcf1665771ec`; ключ: `live:usgs:earthquake:us6000u46r`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 20:15:01.368036+00; обновлено: 2026-10-30 16:05:00.289387+00

### 596. M5.0 earthquake - 153 km S of Kokopo, Papua New Guinea
- ID: `0a14bc79-05d7-47e7-8d6d-ec42f2c53f5f`; ключ: `live:usgs:earthquake:us6000u473`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-22 21:15:01.437809+00; обновлено: 2026-10-30 16:05:00.289387+00

### 597. M4.8 earthquake - 269 km SSW of Severo-Kuril’sk, Russia
- ID: `1379996a-5553-4d13-a63e-fbb02991e5dd`; ключ: `live:usgs:earthquake:us6000u47l`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 00:15:02.043967+00; обновлено: 2026-10-30 16:05:00.289387+00

### 598. M4.6 earthquake - 49 km S of Ollagüe, Chile
- ID: `93a36411-4cc3-4175-8391-25f81dfb7611`; ключ: `live:usgs:earthquake:us6000u47n`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 00:15:01.958074+00; обновлено: 2026-10-30 16:05:00.289387+00

### 599. M4.5 earthquake - 102 km W of San Antonio de los Cobres, Argentina
- ID: `2e30af23-586e-4fb8-aa5b-85a5108b56a6`; ключ: `live:usgs:earthquake:us6000u48i`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 02:15:01.86513+00; обновлено: 2026-10-30 16:05:00.289387+00

### 600. M4.5 earthquake - 18 km NNW of Yongning, China
- ID: `2c6f5799-7559-4463-87a8-9fd61437010a`; ключ: `live:usgs:earthquake:us6000u49a`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 03:15:01.687349+00; обновлено: 2026-10-30 16:05:00.289387+00

### 601. M4.5 earthquake - 58 km SW of Atocha, Bolivia
- ID: `2b27d010-74dc-48f5-8da2-b4f01812a08c`; ключ: `live:usgs:earthquake:us6000u49c`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 03:15:01.641827+00; обновлено: 2026-10-30 16:05:00.289387+00

### 602. M4.5 earthquake - 18 km WNW of Bantogon, Philippines
- ID: `b3788cba-cdbc-4ab6-b5b2-88916f17b250`; ключ: `live:usgs:earthquake:us6000u4b3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 10:15:01.450199+00; обновлено: 2026-10-30 16:05:00.289387+00

### 603. M4.9 earthquake - 53 km WNW of Leni, Italy
- ID: `b85d8871-5f09-471d-a35d-ed28eff73380`; ключ: `live:usgs:earthquake:us6000u4bg`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 34.000; последний расчёт: 34.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 10:15:01.377228+00; обновлено: 2026-10-30 16:05:00.289387+00

### 604. M5.7 earthquake - 61 km WNW of Leni, Italy
- ID: `14427e77-2200-4c54-a59f-f7878b3d0d04`; ключ: `live:usgs:earthquake:us6000u4bk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 11:15:02.557968+00; обновлено: 2026-10-30 16:05:00.289387+00

### 605. M4.5 earthquake - 193 km ENE of Levuka, Fiji
- ID: `d13bc974-1246-4121-9470-c25493ab336a`; ключ: `live:usgs:earthquake:us6000u4bv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 13:15:02.306076+00; обновлено: 2026-10-30 16:05:00.289387+00

### 606. M4.5 earthquake - 207 km NE of Lospalos, Timor Leste
- ID: `6b186914-b5a7-4019-b89c-2f246721928a`; ключ: `live:usgs:earthquake:us6000u4bw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 13:15:02.252928+00; обновлено: 2026-10-30 16:05:00.289387+00

### 607. M5.2 earthquake - 50 km WNW of Malfa, Italy
- ID: `e37b43cc-889e-4c0a-bc07-14267262f2f9`; ключ: `live:usgs:earthquake:us6000u4dc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 15:15:01.413314+00; обновлено: 2026-10-30 16:05:00.289387+00

### 608. M4.7 earthquake - 215 km NE of Nagqu, China
- ID: `0222940e-4887-4ff5-9cb0-965755c5b06c`; ключ: `live:usgs:earthquake:us6000u4df`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 19:15:01.921041+00; обновлено: 2026-10-30 16:05:00.289387+00

### 609. M4.5 earthquake - 233 km ENE of Nagqu, China
- ID: `0bca8e1f-b0c1-468b-8c11-7ddf925fe200`; ключ: `live:usgs:earthquake:us6000u4dk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 19:15:01.828514+00; обновлено: 2026-10-30 16:05:00.289387+00

### 610. M4.7 earthquake - 52 km WNW of Malfa, Italy
- ID: `2bdd4302-4859-4602-9b1f-6bf5f6e61a56`; ключ: `live:usgs:earthquake:us6000u4dx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 32.000; последний расчёт: 32.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 18:15:00.963863+00; обновлено: 2026-10-30 16:05:00.289387+00

### 611. M5.1 earthquake - 72 km ENE of Noda, Japan
- ID: `248438b0-1b2e-4841-9333-a2500ec3b519`; ключ: `live:usgs:earthquake:us6000u4e2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 17:15:01.70578+00; обновлено: 2026-10-30 16:05:00.289387+00

### 612. M4.6 earthquake - 91 km ESE of Tuensang, India
- ID: `8d2fdb83-1795-4d2d-9fac-f287dc2d3c22`; ключ: `live:usgs:earthquake:us6000u4f5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 18:15:00.872721+00; обновлено: 2026-10-30 16:05:00.289387+00

### 613. M4.8 earthquake - 209 km ENE of Nagqu, China
- ID: `08347fa1-e38a-45cc-ab0f-e5d619a78bc0`; ключ: `live:usgs:earthquake:us6000u4gj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 21:15:01.401515+00; обновлено: 2026-10-30 16:05:00.289387+00

### 614. M4.9 earthquake - 35 km ESE of Hualien City, Taiwan
- ID: `7717829c-b1ab-4869-83c1-15fce7b156ca`; ключ: `live:usgs:earthquake:us6000u4gm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 22:15:01.27215+00; обновлено: 2026-10-30 16:05:00.289387+00

### 615. M4.6 earthquake - 73 km ENE of Kinablangan, Philippines
- ID: `ebcf30c8-dbd1-42e0-ad77-40751f5dbf2a`; ключ: `live:usgs:earthquake:us6000u4h0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 23:15:01.536871+00; обновлено: 2026-10-30 16:05:00.289387+00

### 616. M5.1 earthquake - 203 km NW of Port-Olry, Vanuatu
- ID: `001f67ad-d6d9-43a4-8c4f-6a64b7885fa5`; ключ: `live:usgs:earthquake:us6000u4h7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 23:15:01.513927+00; обновлено: 2026-10-30 16:05:00.289387+00

### 617. M4.8 earthquake - 6 km ENE of Starobachaty, Russia
- ID: `7d570415-07e9-4b24-8465-cee71ea146c1`; ключ: `live:usgs:earthquake:us6000u4hi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 23:15:01.492117+00; обновлено: 2026-10-30 16:05:00.289387+00

### 618. M4.9 earthquake - 115 km NE of Norsup, Vanuatu
- ID: `4bf880ef-15bb-4316-a595-c13e23c9dc6a`; ключ: `live:usgs:earthquake:us6000u4hr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-23 23:15:01.435884+00; обновлено: 2026-10-30 16:05:00.289387+00

### 619. M4.9 earthquake - 209 km ENE of Nagqu, China
- ID: `ca5d0709-cf0b-40d0-a58f-edacf542ea61`; ключ: `live:usgs:earthquake:us6000u4i8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 01:15:01.45989+00; обновлено: 2026-10-30 16:05:00.289387+00

### 620. M4.5 earthquake - 195 km NW of Port-Olry, Vanuatu
- ID: `1c2c1e5f-f592-436b-b374-3110a4491078`; ключ: `live:usgs:earthquake:us6000u4ib`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 02:15:01.39885+00; обновлено: 2026-10-30 16:05:00.289387+00

### 621. M6.9 earthquake - 197 km WNW of Port-Olry, Vanuatu
- ID: `b55032d6-4231-4b79-ac3c-6f35b0634991`; ключ: `live:usgs:earthquake:us6000u4j2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 49.000; последний расчёт: 49.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 03:15:02.178991+00; обновлено: 2026-10-30 16:05:00.289387+00

### 622. M6.3 earthquake - 170 km NW of Port-Olry, Vanuatu
- ID: `377b1f1d-af8d-45bc-b6e3-41744570dc93`; ключ: `live:usgs:earthquake:us6000u4jb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 46.000; последний расчёт: 46.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 03:15:02.028359+00; обновлено: 2026-10-30 16:05:00.289387+00

### 623. M5.1 earthquake - 170 km NW of Port-Olry, Vanuatu
- ID: `ca45f90f-8fe8-4454-ae3a-1cd3f8d03b3b`; ключ: `live:usgs:earthquake:us6000u4ji`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 04:15:02.201197+00; обновлено: 2026-10-30 16:05:00.289387+00

### 624. M5.2 earthquake - 202 km NW of Port-Olry, Vanuatu
- ID: `cf3b2036-481b-476e-ad70-bcf7abcfb8f2`; ключ: `live:usgs:earthquake:us6000u4jl`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 04:15:02.157483+00; обновлено: 2026-10-30 16:05:00.289387+00

### 625. M4.9 earthquake - 186 km WNW of Port-Olry, Vanuatu
- ID: `87f427d2-7b3c-4c16-89f5-6d978d67724a`; ключ: `live:usgs:earthquake:us6000u4jr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 04:15:02.102886+00; обновлено: 2026-10-30 16:05:00.289387+00

### 626. M5.7 earthquake - 205 km NW of Port-Olry, Vanuatu
- ID: `5b111673-4ed0-4843-aea3-8424d8da1227`; ключ: `live:usgs:earthquake:us6000u4ju`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 05:15:01.714655+00; обновлено: 2026-10-30 16:05:00.289387+00

### 627. M5.8 earthquake - 203 km NW of Port-Olry, Vanuatu
- ID: `32c22cb1-032a-4256-86c5-540c6dc7ee84`; ключ: `live:usgs:earthquake:us6000u4jw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 05:15:01.691316+00; обновлено: 2026-10-30 16:05:00.289387+00

### 628. M5.3 earthquake - 216 km W of Sola, Vanuatu
- ID: `270df37f-3a5e-41a5-8a55-6d81ad607204`; ключ: `live:usgs:earthquake:us6000u4jy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 05:15:01.620743+00; обновлено: 2026-10-30 16:05:00.289387+00

### 629. M5.1 earthquake - 217 km NW of Port-Olry, Vanuatu
- ID: `1003cb1b-e871-4ea1-b02b-82e744c038a1`; ключ: `live:usgs:earthquake:us6000u4k1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 05:15:01.516784+00; обновлено: 2026-10-30 16:05:00.289387+00

### 630. M5.0 earthquake - 161 km NW of Port-Olry, Vanuatu
- ID: `8bad415d-0323-4054-9a39-c5fbfa6fe269`; ключ: `live:usgs:earthquake:us6000u4k2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 05:15:01.575375+00; обновлено: 2026-10-30 16:05:00.289387+00

### 631. M4.8 earthquake - 219 km WNW of Port-Olry, Vanuatu
- ID: `61a0c2f6-329e-4519-956e-b328c77112fd`; ключ: `live:usgs:earthquake:us6000u4k5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 06:15:02.393986+00; обновлено: 2026-10-30 16:05:00.289387+00

### 632. M5.8 earthquake - 182 km NW of Port-Olry, Vanuatu
- ID: `d8fced6f-e0ed-43f2-b158-6f6346782626`; ключ: `live:usgs:earthquake:us6000u4k6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 06:15:02.360459+00; обновлено: 2026-10-30 16:05:00.289387+00

### 633. M4.5 earthquake - 184 km NW of Port-Olry, Vanuatu
- ID: `19cf3d7e-06f7-4d76-8e12-75dc78c75720`; ключ: `live:usgs:earthquake:us6000u4ke`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 06:15:02.326611+00; обновлено: 2026-10-30 16:05:00.289387+00

### 634. M4.5 earthquake - 175 km NW of Port-Olry, Vanuatu
- ID: `72965569-8120-4d50-b566-e248fe8ab1b7`; ключ: `live:usgs:earthquake:us6000u4kh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 06:15:02.266164+00; обновлено: 2026-10-30 16:05:00.289387+00

### 635. M5.3 earthquake - 174 km NW of Port-Olry, Vanuatu
- ID: `512bda2e-7c48-4385-816e-82df17bc368d`; ключ: `live:usgs:earthquake:us6000u4kj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 07:15:02.030829+00; обновлено: 2026-10-30 16:05:00.289387+00

### 636. M5.5 earthquake - 55 km NNE of Port-Olry, Vanuatu
- ID: `8c9cf7e5-fcb6-437c-862b-03e48bdf3c28`; ключ: `live:usgs:earthquake:us6000u4kq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 07:15:01.920667+00; обновлено: 2026-10-30 16:05:00.289387+00

### 637. M4.6 earthquake - 206 km NW of Port-Olry, Vanuatu
- ID: `47b018c3-9a3c-4dc4-9baf-35e56fd7ff2f`; ключ: `live:usgs:earthquake:us6000u4kt`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 07:15:01.957165+00; обновлено: 2026-10-30 16:05:00.289387+00

### 638. M5.0 earthquake - 219 km NW of Port-Olry, Vanuatu
- ID: `5f3d117e-7e44-46e4-b3e6-2face93a9406`; ключ: `live:usgs:earthquake:us6000u4ku`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 07:15:01.855286+00; обновлено: 2026-10-30 16:05:00.289387+00

### 639. M4.7 earthquake - 195 km NW of Port-Olry, Vanuatu
- ID: `c7840bd8-f174-4cd8-b5eb-ffc6dadd2e00`; ключ: `live:usgs:earthquake:us6000u4kw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 08:15:03.945479+00; обновлено: 2026-10-30 16:05:00.289387+00

### 640. M4.7 earthquake - 222 km NW of Port-Olry, Vanuatu
- ID: `90bc097e-87c4-4dd9-bd43-bf81530d8f91`; ключ: `live:usgs:earthquake:us6000u4l8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 10:15:02.173434+00; обновлено: 2026-10-30 16:05:00.289387+00

### 641. M5.1 earthquake - 218 km NW of Port-Olry, Vanuatu
- ID: `083c27b9-e59a-4810-8291-1137534eaa5d`; ключ: `live:usgs:earthquake:us6000u4l9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 09:15:02.520738+00; обновлено: 2026-10-30 16:05:00.289387+00

### 642. M4.9 earthquake - 41 km SSE of Kax, China
- ID: `d5589d78-8a16-4e77-8bcc-920fa336de4d`; ключ: `live:usgs:earthquake:us6000u4lb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 10:15:02.095342+00; обновлено: 2026-10-30 16:05:00.289387+00

### 643. M5.1 earthquake - 209 km NW of Port-Olry, Vanuatu
- ID: `f568c4a8-60b6-4f60-9741-3f7c44905032`; ключ: `live:usgs:earthquake:us6000u4lc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 09:15:02.493188+00; обновлено: 2026-10-30 16:05:00.289387+00

### 644. M4.5 earthquake - 81 km SSE of Akutan, Alaska
- ID: `44ded7a3-4f59-4976-8122-dcb29cce93cb`; ключ: `live:usgs:earthquake:us6000u4ld`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 09:15:02.462655+00; обновлено: 2026-10-30 16:05:00.289387+00

### 645. M5.3 earthquake - 223 km ENE of Nagqu, China
- ID: `18bb75ef-2891-47c0-9c5a-ea6d8acae8a8`; ключ: `live:usgs:earthquake:us6000u4lg`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 09:15:02.424563+00; обновлено: 2026-10-30 16:05:00.289387+00

### 646. M4.7 earthquake - 187 km NW of Port-Olry, Vanuatu
- ID: `ec6b1ca2-e8a8-4fe5-b7b4-000c96d4766a`; ключ: `live:usgs:earthquake:us6000u4ll`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 10:15:02.027439+00; обновлено: 2026-10-30 16:05:00.289387+00

### 647. M5.9 earthquake - 196 km NW of Port-Olry, Vanuatu
- ID: `b29ab950-a1c1-4f1d-8ef3-c7731e6a0ead`; ключ: `live:usgs:earthquake:us6000u4lm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 09:15:02.345094+00; обновлено: 2026-10-30 16:05:00.289387+00

### 648. M5.0 earthquake - 219 km WNW of Port-Olry, Vanuatu
- ID: `e4cac7d6-41fc-4eb8-97cc-dbbefd7c2869`; ключ: `live:usgs:earthquake:us6000u4lp`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 10:15:01.847642+00; обновлено: 2026-10-30 16:05:00.289387+00

### 649. M4.9 earthquake - 169 km NW of Port-Olry, Vanuatu
- ID: `36701d06-053e-44f1-883b-86bacd4a6b61`; ключ: `live:usgs:earthquake:us6000u4lr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 10:15:01.798145+00; обновлено: 2026-10-30 16:05:00.289387+00

### 650. M4.9 earthquake - 196 km W of Sola, Vanuatu
- ID: `298e2873-c276-4f3c-959f-7b12d74367d0`; ключ: `live:usgs:earthquake:us6000u4m5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 12:15:01.595615+00; обновлено: 2026-10-30 16:05:00.289387+00

### 651. M4.9 earthquake - 148 km NNW of Kilmia, Yemen
- ID: `03be5696-8664-450e-889e-4d8a7e5acfb5`; ключ: `live:usgs:earthquake:us6000u4m6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 12:15:01.565413+00; обновлено: 2026-10-30 16:05:00.289387+00

### 652. M4.7 earthquake - 72 km S of Basco, Philippines
- ID: `8f2dde76-2666-499e-9a99-e68bfe95f41d`; ключ: `live:usgs:earthquake:us6000u4m9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 12:15:01.478521+00; обновлено: 2026-10-30 16:05:00.289387+00

### 653. M4.6 earthquake - 195 km NE of Nagqu, China
- ID: `a5f582ee-a2f9-46ef-b8e2-d2c6dc278086`; ключ: `live:usgs:earthquake:us6000u4mg`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 16:15:02.121485+00; обновлено: 2026-10-30 16:05:00.289387+00

### 654. M4.8 earthquake - 216 km NW of Port-Olry, Vanuatu
- ID: `7b6c0716-7351-427d-ad0a-7328a96d8af6`; ключ: `live:usgs:earthquake:us6000u4mi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 15:15:02.129311+00; обновлено: 2026-10-30 16:05:00.289387+00

### 655. M4.8 earthquake - 215 km NW of Port-Olry, Vanuatu
- ID: `6700dd81-f30b-4327-9d16-e28c0f4cbefc`; ключ: `live:usgs:earthquake:us6000u4ml`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 17:15:01.349489+00; обновлено: 2026-10-30 16:05:00.289387+00

### 656. M4.9 earthquake - 217 km NW of Port-Olry, Vanuatu
- ID: `b9cfa557-7b8f-48d9-92e9-a9f251a1dbbc`; ключ: `live:usgs:earthquake:us6000u4mm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 16:15:02.064565+00; обновлено: 2026-10-30 16:05:00.289387+00

### 657. M5.8 earthquake - Bouvet Island region
- ID: `c72c4c9e-7272-465a-8f64-23b8522c0235`; ключ: `live:usgs:earthquake:us6000u4mn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 16:15:01.994555+00; обновлено: 2026-10-30 16:05:00.289387+00

### 658. M4.7 earthquake - 238 km WNW of Port-Olry, Vanuatu
- ID: `ec393b50-c46e-42a4-8cde-6f6adfbba7a9`; ключ: `live:usgs:earthquake:us6000u4my`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 17:15:01.254595+00; обновлено: 2026-10-30 16:05:00.289387+00

### 659. M4.8 earthquake - 153 km NW of Port-Olry, Vanuatu
- ID: `4fd157fb-3e27-4a23-9197-910b1b828937`; ключ: `live:usgs:earthquake:us6000u4n8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 18:15:01.518598+00; обновлено: 2026-10-30 16:05:00.289387+00

### 660. M5.0 earthquake - 193 km NW of Port-Olry, Vanuatu
- ID: `de15a085-df25-4b5d-a8fa-b873038a5602`; ключ: `live:usgs:earthquake:us6000u4nv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 20:15:02.247352+00; обновлено: 2026-10-30 16:05:00.289387+00

### 661. M4.9 earthquake - 73 km SW of Isangel, Vanuatu
- ID: `5da6b39f-0a30-468c-82d5-dc2e8ba21c4f`; ключ: `live:usgs:earthquake:us6000u4ny`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 20:15:02.185996+00; обновлено: 2026-10-30 16:05:00.289387+00

### 662. M5.3 earthquake - 101 km SSE of Vilyuchinsk, Russia
- ID: `d4328859-f84e-44b3-8d6e-6659deee3926`; ключ: `live:usgs:earthquake:us6000u4pa`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 21:15:02.291699+00; обновлено: 2026-10-30 16:05:00.289387+00

### 663. M4.9 earthquake - 53 km NNW of Fef, Indonesia
- ID: `64b4bce0-d544-4970-9fe0-5747ca16750e`; ключ: `live:usgs:earthquake:us6000u4pw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 00:15:02.362633+00; обновлено: 2026-10-30 16:05:00.289387+00

### 664. M5.0 earthquake - 210 km NW of Port-Olry, Vanuatu
- ID: `01701e82-e940-45c6-9d0a-16b367266316`; ключ: `live:usgs:earthquake:us6000u4q8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-24 23:15:01.663646+00; обновлено: 2026-10-30 16:05:00.289387+00

### 665. M4.8 earthquake - 203 km NW of Port-Olry, Vanuatu
- ID: `52e99380-daec-4716-bc8f-216e2dbbf563`; ключ: `live:usgs:earthquake:us6000u4qm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 00:15:02.302394+00; обновлено: 2026-10-30 16:05:00.289387+00

### 666. M5.0 earthquake - 192 km NW of Port-Olry, Vanuatu
- ID: `b498ec86-c6f2-4af5-af77-9b869a5fc321`; ключ: `live:usgs:earthquake:us6000u4qp`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 00:15:02.246461+00; обновлено: 2026-10-30 16:05:00.289387+00

### 667. M5.3 earthquake - 44 km ESE of Miyazaki, Japan
- ID: `793864b2-4c36-42a5-860b-0281b66c42af`; ключ: `live:usgs:earthquake:us6000u4qq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 01:15:01.463862+00; обновлено: 2026-10-30 16:05:00.289387+00

### 668. M5.1 earthquake - 166 km WNW of Port-Olry, Vanuatu
- ID: `ebdc657d-cb1e-40f5-a93b-eeaa72f3067c`; ключ: `live:usgs:earthquake:us6000u4r3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 02:15:01.424693+00; обновлено: 2026-10-30 16:05:00.289387+00

### 669. M5.1 earthquake - 161 km WNW of Port-Olry, Vanuatu
- ID: `6feb019b-e2cc-4477-96f7-ef4352a58b7b`; ключ: `live:usgs:earthquake:us6000u4r7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 03:15:01.552241+00; обновлено: 2026-10-30 16:05:00.289387+00

### 670. M6.5 earthquake - Bonin Islands, Japan region
- ID: `bf56b06a-44d5-49ea-a56d-3f533f8cfac3`; ключ: `live:usgs:earthquake:us6000u4r9`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 49.000; последний расчёт: 49.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 03:15:01.519229+00; обновлено: 2026-10-30 16:05:00.289387+00

### 671. M6.1 earthquake - 25 km ENE of Port-Olry, Vanuatu
- ID: `e38b6df4-6526-43c9-a72b-79e9ba5c2220`; ключ: `live:usgs:earthquake:us6000u4rf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 03:15:01.486636+00; обновлено: 2026-10-30 16:05:00.289387+00

### 672. M4.8 earthquake - Bonin Islands, Japan region
- ID: `13dff61e-0304-475a-b929-2f5182671a8e`; ключ: `live:usgs:earthquake:us6000u4rr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 03:15:01.416723+00; обновлено: 2026-10-30 16:05:00.289387+00

### 673. M5.2 earthquake - 63 km NNE of Lae, Papua New Guinea
- ID: `ce92580c-59f1-4137-88c0-a0a3bdf8a6a7`; ключ: `live:usgs:earthquake:us6000u4s5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 04:15:02.271156+00; обновлено: 2026-10-30 16:05:00.289387+00

### 674. M4.9 earthquake - 17 km SE of Ambelókipoi, Greece
- ID: `b7c3a0b5-890d-4744-8576-bd9cc29bad1c`; ключ: `live:usgs:earthquake:us6000u4sm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 06:15:01.407353+00; обновлено: 2026-10-30 16:05:00.289387+00

### 675. M4.5 earthquake - 74 km SSE of Onagawa Chō, Japan
- ID: `5372ee9c-8336-4dbc-a6bb-2613c264d133`; ключ: `live:usgs:earthquake:us6000u4sv`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 07:15:01.791029+00; обновлено: 2026-10-30 16:05:00.289387+00

### 676. M4.6 earthquake - 50 km SW of Atiquipa, Peru
- ID: `e767e2c1-4356-4f6a-bda8-de28e53a7182`; ключ: `live:usgs:earthquake:us6000u4t4`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 08:15:01.739455+00; обновлено: 2026-10-30 16:05:00.289387+00

### 677. M4.6 earthquake - 82 km SSE of Akutan, Alaska
- ID: `42c338ff-7beb-4b17-87fa-83c1785a5404`; ключ: `live:usgs:earthquake:us6000u4t8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 09:15:01.629566+00; обновлено: 2026-10-30 16:05:00.289387+00

### 678. M5.4 earthquake - 205 km NW of Port-Olry, Vanuatu
- ID: `7d826085-5575-42df-851c-07dd9d5bc38a`; ключ: `live:usgs:earthquake:us6000u4tc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 09:15:01.55448+00; обновлено: 2026-10-30 16:05:00.289387+00

### 679. M4.6 earthquake - Volcano Islands, Japan region
- ID: `e58a563e-7fad-4934-b2dc-8d18dd42c31e`; ключ: `live:usgs:earthquake:us6000u4tf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 10:15:01.208973+00; обновлено: 2026-10-30 16:05:00.289387+00

### 680. M5.4 earthquake - 33 km ESE of Ambunti, Papua New Guinea
- ID: `0dbee80e-d289-4ff2-b6e3-393bc01176f7`; ключ: `live:usgs:earthquake:us6000u4tq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 11:15:01.73228+00; обновлено: 2026-10-30 16:05:00.289387+00

### 681. M5.1 earthquake - 199 km ENE of Nagqu, China
- ID: `cba697a9-0b82-42f5-a84d-dd4dc567c8e0`; ключ: `live:usgs:earthquake:us6000u4tx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 12:15:01.549711+00; обновлено: 2026-10-30 16:05:00.289387+00

### 682. M5.9 earthquake - 218 km ENE of Nagqu, China
- ID: `572e3ce0-92f6-46f6-ad93-c244621d39be`; ключ: `live:usgs:earthquake:us6000u4ty`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 12:15:01.488165+00; обновлено: 2026-10-30 16:05:00.289387+00

### 683. M4.7 earthquake - 19 km NE of Atico, Peru
- ID: `3ec430ec-79e1-4b52-81c4-0602ad852ded`; ключ: `live:usgs:earthquake:us6000u4v1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 18:15:02.114436+00; обновлено: 2026-10-30 16:05:00.289387+00

### 684. M5.2 earthquake - 59 km SW of Ashkāsham, Afghanistan
- ID: `417e3cb3-c4dc-4813-b97c-e87575ed82e3`; ключ: `live:usgs:earthquake:us6000u4va`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 18:15:02.08276+00; обновлено: 2026-10-30 16:05:00.289387+00

### 685. M4.6 earthquake - 153 km WNW of Adak, Alaska
- ID: `54733526-1c82-4ccd-8748-be96c428da65`; ключ: `live:usgs:earthquake:us6000u4vb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 18:15:02.035308+00; обновлено: 2026-10-30 16:05:00.289387+00

### 686. M4.8 earthquake - 167 km WNW of Port-Olry, Vanuatu
- ID: `5ab94588-2a29-43f1-9028-ad5a088f9b58`; ключ: `live:usgs:earthquake:us6000u4vy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 21:15:01.535898+00; обновлено: 2026-10-30 16:05:00.289387+00

### 687. M4.7 earthquake - 170 km ENE of Nagqu, China
- ID: `d1e044a3-9436-49c5-9da1-511b1ab55d31`; ключ: `live:usgs:earthquake:us6000u4wc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 01:15:02.445429+00; обновлено: 2026-10-30 16:05:00.289387+00

### 688. M5.3 earthquake - Bonin Islands, Japan region
- ID: `6a373c62-d6c3-4251-977e-b26158e4775d`; ключ: `live:usgs:earthquake:us6000u4we`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 23:15:01.653138+00; обновлено: 2026-10-30 16:05:00.289387+00

### 689. M4.8 earthquake - Bonin Islands, Japan region
- ID: `88935466-0af9-4c96-8a62-22b99fc5a3db`; ключ: `live:usgs:earthquake:us6000u4wi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-25 23:15:01.601644+00; обновлено: 2026-10-30 16:05:00.289387+00

### 690. M4.9 earthquake - 205 km NW of Port-Olry, Vanuatu
- ID: `b0fc8f09-a158-4e69-9be3-658d36139320`; ключ: `live:usgs:earthquake:us6000u4xa`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 02:15:02.158238+00; обновлено: 2026-10-30 16:05:00.289387+00

### 691. M4.8 earthquake - 41 km WNW of Kupang, Indonesia
- ID: `2e6af3df-2027-433a-8180-c8f5ea4f9f42`; ключ: `live:usgs:earthquake:us6000u4xp`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 05:15:01.46342+00; обновлено: 2026-10-30 16:05:00.289387+00

### 692. M5.0 earthquake - 45 km NNW of Ende, Indonesia
- ID: `81c92977-6f50-4f05-bdc1-c51f538e6e63`; ключ: `live:usgs:earthquake:us6000u4y1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 05:15:01.404743+00; обновлено: 2026-10-30 16:05:00.289387+00

### 693. M4.8 earthquake - 182 km NW of Port-Olry, Vanuatu
- ID: `67c4da62-ff8d-44d1-a8f9-497d85066bfc`; ключ: `live:usgs:earthquake:us6000u4y2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 06:15:00.818698+00; обновлено: 2026-10-30 16:05:00.289387+00

### 694. M4.5 earthquake - 107 km WNW of Tumxuk, China
- ID: `13c664a8-9437-4042-8c8c-21a28c7a0c02`; ключ: `live:usgs:earthquake:us6000u4yi`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 09:15:01.298534+00; обновлено: 2026-10-30 16:05:00.289387+00

### 695. M4.5 earthquake - 56 km S of Kuril’sk, Russia
- ID: `8200bc82-9825-4ff4-b199-239408394404`; ключ: `live:usgs:earthquake:us6000u4yj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 10:15:01.292619+00; обновлено: 2026-10-30 16:05:00.289387+00

### 696. M5.5 earthquake - 283 km E of Levuka, Fiji
- ID: `fac37c8f-5733-4e74-b47d-3b2d8db7e9c2`; ключ: `live:usgs:earthquake:us6000u4yr`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 11:15:02.497629+00; обновлено: 2026-10-30 16:05:00.289387+00

### 697. M4.8 earthquake - South Sandwich Islands region
- ID: `e546c414-b2ff-4383-b134-dded5ce52eee`; ключ: `live:usgs:earthquake:us6000u4z3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 13:15:02.471675+00; обновлено: 2026-10-30 16:05:00.289387+00

### 698. M5.0 earthquake - 218 km NW of Port-Olry, Vanuatu
- ID: `25b500ec-c594-4dae-a6a2-dd037eec9bd8`; ключ: `live:usgs:earthquake:us6000u4z6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 12:15:04.099089+00; обновлено: 2026-10-30 16:05:00.289387+00

### 699. M4.6 earthquake - 81 km SSE of Akutan, Alaska
- ID: `ce926337-88bd-4389-a4fd-5b2c585915b5`; ключ: `live:usgs:earthquake:us6000u4z7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 12:15:03.94142+00; обновлено: 2026-10-30 16:05:00.289387+00

### 700. M5.2 earthquake - 205 km NW of Port-Olry, Vanuatu
- ID: `7673a50f-8d45-4197-86b6-dd4ba39f5c61`; ключ: `live:usgs:earthquake:us6000u4zb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 13:15:02.366389+00; обновлено: 2026-10-30 16:05:00.289387+00

### 701. M4.5 earthquake - 74 km SE of Rasht, Tajikistan
- ID: `5225014f-493e-4268-9029-801da11d6c82`; ключ: `live:usgs:earthquake:us7000ttb5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 19:15:01.314659+00; обновлено: 2026-10-30 16:05:00.289387+00

### 702. M4.9 earthquake - 100 km E of La Tirana, Chile
- ID: `4468d679-960b-4f06-87de-7cb82ac82ec5`; ключ: `live:usgs:earthquake:us7000ttbh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 20:15:01.271864+00; обновлено: 2026-10-30 16:05:00.289387+00

### 703. M4.6 earthquake - 154 km NW of Port-Olry, Vanuatu
- ID: `c3dcc281-2d59-4aac-9048-f9c392106c82`; ключ: `live:usgs:earthquake:us7000ttby`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 21:15:01.148656+00; обновлено: 2026-10-30 16:05:00.289387+00

### 704. M4.5 earthquake - 89 km SSE of Pondaguitan, Philippines
- ID: `adac4941-8e78-4818-a8eb-6a4a5edb8207`; ключ: `live:usgs:earthquake:us7000ttc6`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 22:15:01.276771+00; обновлено: 2026-10-30 16:05:00.289387+00

### 705. M4.6 earthquake - 20 km NNW of La Ligua, Chile
- ID: `194c8d50-cdc3-41bc-ad4b-500dd3e58f8d`; ключ: `live:usgs:earthquake:us7000ttc8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 22:15:01.246989+00; обновлено: 2026-10-30 16:05:00.289387+00

### 706. M4.7 earthquake - 98 km S of Encounter Bay, Australia
- ID: `99b07022-547c-411e-84cb-f316d0c5b17c`; ключ: `live:usgs:earthquake:us7000ttci`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 22:15:01.190781+00; обновлено: 2026-10-30 16:05:00.289387+00

### 707. M4.5 earthquake - 96 km ENE of Pamandzi, Mayotte
- ID: `c1db0373-b45d-4dcf-a937-4ee781ab4293`; ключ: `live:usgs:earthquake:us7000ttd1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-26 23:15:01.210698+00; обновлено: 2026-10-30 16:05:00.289387+00

### 708. M4.5 earthquake - 98 km NNW of Tobelo, Indonesia
- ID: `df95000f-e9a6-409e-b175-37225c75bec3`; ключ: `live:usgs:earthquake:us7000ttd3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 01:15:01.413799+00; обновлено: 2026-10-30 16:05:00.289387+00

### 709. M4.8 earthquake - 54 km E of Tomioka, Japan
- ID: `900467b9-2594-444e-b223-db85e846d836`; ключ: `live:usgs:earthquake:us7000ttdt`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 01:15:01.334202+00; обновлено: 2026-10-30 16:05:00.289387+00

### 710. M4.6 earthquake - 203 km SSE of Tateyama, Japan
- ID: `ba501b12-52f5-4b5e-bf9c-94c9e2eb31e5`; ключ: `live:usgs:earthquake:us7000tte0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 02:15:01.647284+00; обновлено: 2026-10-30 16:05:00.289387+00

### 711. M4.9 earthquake - 69 km WSW of Kirakira, Solomon Islands
- ID: `4820d2ca-6d2e-40fe-875f-9cdab36f4740`; ключ: `live:usgs:earthquake:us7000tte4`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 03:15:01.274855+00; обновлено: 2026-10-30 16:05:00.289387+00

### 712. M5.8 earthquake - 196 km NW of Port-Olry, Vanuatu
- ID: `083f1e9f-4c58-431d-8d6e-9c6012173ee1`; ключ: `live:usgs:earthquake:us7000ttfb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 09:15:01.716679+00; обновлено: 2026-10-30 16:05:00.289387+00

### 713. M5.0 earthquake - 95 km NNE of Hihifo, Tonga
- ID: `99b9c456-1410-43b0-a9b9-6579a32c7c78`; ключ: `live:usgs:earthquake:us7000ttfc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 10:15:01.316055+00; обновлено: 2026-10-30 16:05:00.289387+00

### 714. M5.0 earthquake - 206 km NW of Port-Olry, Vanuatu
- ID: `bc067444-ad0b-4df7-a762-2af7aca4014d`; ключ: `live:usgs:earthquake:us7000ttfe`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 10:15:01.223249+00; обновлено: 2026-10-30 16:05:00.289387+00

### 715. M5.0 earthquake - 184 km NW of Port-Olry, Vanuatu
- ID: `273b34eb-f473-4665-a81f-d7add6049b62`; ключ: `live:usgs:earthquake:us7000ttfj`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 11:15:01.505607+00; обновлено: 2026-10-30 16:05:00.289387+00

### 716. M5.2 earthquake - 191 km NW of Port-Olry, Vanuatu
- ID: `7d03020c-40c9-47df-bfe2-752e42c13e4b`; ключ: `live:usgs:earthquake:us7000ttfk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 11:15:01.417483+00; обновлено: 2026-10-30 16:05:00.289387+00

### 717. M4.6 earthquake - 100 km W of El Aguilar, Argentina
- ID: `8ce6065f-5745-4d37-bdec-928c3b6f840b`; ключ: `live:usgs:earthquake:us7000ttfs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 12:15:01.835807+00; обновлено: 2026-10-30 16:05:00.289387+00

### 718. M4.6 earthquake - 5 km ENE of Tierra y Libertad, Mexico
- ID: `93ccbbb0-5de5-407a-9aac-bdf8b99b43fc`; ключ: `live:usgs:earthquake:us7000ttfx`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 13:15:01.458466+00; обновлено: 2026-10-30 16:05:00.289387+00

### 719. M4.6 earthquake - 41 km S of Farkhār, Afghanistan
- ID: `1a646831-25c7-4f06-855c-c2297d1e9469`; ключ: `live:usgs:earthquake:us7000ttgc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 36.000; последний расчёт: 36.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 18:15:01.728561+00; обновлено: 2026-10-30 16:05:00.289387+00

### 720. M5.4 earthquake - 128 km S of Pundong, Indonesia
- ID: `5a7bf1f8-874a-4e6d-bc49-243d8a95d4f0`; ключ: `live:usgs:earthquake:us7000ttgf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 15:15:01.465905+00; обновлено: 2026-10-30 16:05:00.289387+00

### 721. M4.9 earthquake - 156 km S of Pundong, Indonesia
- ID: `36c06122-d273-46db-8153-a385e22a5160`; ключ: `live:usgs:earthquake:us7000ttgh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 38.000; последний расчёт: 38.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 15:15:01.528536+00; обновлено: 2026-10-30 16:05:00.289387+00

### 722. M5.0 earthquake - 27 km W of Río Grande, Panama
- ID: `b4dc8021-d2f9-4929-984a-701cf1963790`; ключ: `live:usgs:earthquake:us7000ttgm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 16:15:01.208728+00; обновлено: 2026-10-30 16:05:00.289387+00

### 723. M5.0 earthquake - south of the Fiji Islands
- ID: `071da07b-21a9-4987-b8c8-6cfb9bdca030`; ключ: `live:usgs:earthquake:us7000ttgq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 16:15:01.147319+00; обновлено: 2026-10-30 16:05:00.289387+00

### 724. M4.9 earthquake - 70 km WNW of Callaguip, Philippines
- ID: `e2812370-8ad7-4094-bd90-f18c8fcf16d6`; ключ: `live:usgs:earthquake:us7000tth4`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 19:15:01.49459+00; обновлено: 2026-10-30 16:05:00.289387+00

### 725. M5.4 earthquake - 210 km ENE of Nagqu, China
- ID: `3902e82b-4440-4cbd-a6a8-c593779e8e9a`; ключ: `live:usgs:earthquake:us7000ttis`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-27 20:15:02.06481+00; обновлено: 2026-10-30 16:05:00.289387+00

### 726. M5.4 earthquake - 193 km WSW of Merizo Village, Guam
- ID: `f2f1815a-e6b7-407a-8e26-a91aa1494767`; ключ: `live:usgs:earthquake:us7000ttke`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 00:15:01.680094+00; обновлено: 2026-10-30 16:05:00.289387+00

### 727. M5.1 earthquake - 7 km N of Balangonan, Philippines
- ID: `03d65f06-d6c8-480e-9801-d4b02cb6f5f2`; ключ: `live:usgs:earthquake:us7000ttkk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 00:15:01.630022+00; обновлено: 2026-10-30 16:05:00.289387+00

### 728. M5.2 earthquake - 6 km NW of Balangonan, Philippines
- ID: `3d956035-b6e2-49fd-9cf1-fe283415b4c0`; ключ: `live:usgs:earthquake:us7000ttlc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 02:15:01.536953+00; обновлено: 2026-10-30 16:05:00.289387+00

### 729. M5.5 earthquake - 221 km NW of Port-Olry, Vanuatu
- ID: `5917049f-d2fa-4587-a2c6-b51ae654492a`; ключ: `live:usgs:earthquake:us7000ttld`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 02:15:01.421249+00; обновлено: 2026-10-30 16:05:00.289387+00

### 730. M4.8 earthquake - 217 km NW of Port-Olry, Vanuatu
- ID: `3df91248-ca89-42ac-9ead-49baffc95d9e`; ключ: `live:usgs:earthquake:us7000ttli`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 03:15:01.045755+00; обновлено: 2026-10-30 16:05:00.289387+00

### 731. M5.2 earthquake - 220 km NW of Port-Olry, Vanuatu
- ID: `2a96bc91-cb42-438e-b9e6-07119613856b`; ключ: `live:usgs:earthquake:us7000ttlk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 03:15:01.00967+00; обновлено: 2026-10-30 16:05:00.289387+00

### 732. M6.0 earthquake - 214 km NW of Port-Olry, Vanuatu
- ID: `ce277d40-58ce-4599-b919-07f19c51b20c`; ключ: `live:usgs:earthquake:us7000ttlm`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 03:15:00.930395+00; обновлено: 2026-10-30 16:05:00.289387+00

### 733. M5.6 earthquake - 174 km NW of Port-Olry, Vanuatu
- ID: `990e5a97-52bb-4e0d-b813-20b6223ecd61`; ключ: `live:usgs:earthquake:us7000ttlt`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 04:15:01.390361+00; обновлено: 2026-10-30 16:05:00.289387+00

### 734. M5.0 earthquake - 200 km W of Sola, Vanuatu
- ID: `b77c4bbe-c2fe-4e38-9ce5-b81e88824d9e`; ключ: `live:usgs:earthquake:us7000ttm2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 05:15:01.610084+00; обновлено: 2026-10-30 16:05:00.289387+00

### 735. M5.0 earthquake - 205 km SSE of Vilyuchinsk, Russia
- ID: `3579616a-39c6-4962-89ab-17a44098ff5e`; ключ: `live:usgs:earthquake:us7000ttmb`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 07:15:01.796047+00; обновлено: 2026-10-30 16:05:00.289387+00

### 736. M4.7 earthquake - 39 km SSW of Serrezuela, Argentina
- ID: `bff07ff8-9bbc-42d1-ba6f-1579daa219d4`; ключ: `live:usgs:earthquake:us7000ttmh`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 08:15:01.499618+00; обновлено: 2026-10-30 16:05:00.289387+00

### 737. M4.8 earthquake - 29 km SSW of Sarangani, Philippines
- ID: `3700b107-7dc9-4de8-b35f-9f29576a8cf9`; ключ: `live:usgs:earthquake:us7000ttmz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 10:15:01.038708+00; обновлено: 2026-10-30 16:05:00.289387+00

### 738. M5.5 earthquake - Reykjanes Ridge
- ID: `c4d69ef2-ebc5-4275-85f0-6518c674bb81`; ключ: `live:usgs:earthquake:us7000ttnc`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 12:15:02.161489+00; обновлено: 2026-10-30 16:05:00.289387+00

### 739. M5.0 earthquake - Reykjanes Ridge
- ID: `b6482b25-7657-4d98-852a-0a7fb3a47610`; ключ: `live:usgs:earthquake:us7000ttnk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 12:15:02.072415+00; обновлено: 2026-10-30 16:05:00.289387+00

### 740. M4.9 earthquake - 1 km WSW of Butulan, Philippines
- ID: `870165a2-e582-422a-8f46-eee2fdf5e417`; ключ: `live:usgs:earthquake:us7000ttnq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 14:15:02.030694+00; обновлено: 2026-10-30 16:05:00.289387+00

### 741. M4.9 earthquake - 88 km SE of Hihifo, Tonga
- ID: `a6eaadd4-4398-4044-aab4-b0c67627b5c7`; ключ: `live:usgs:earthquake:us7000ttnt`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 13:15:01.018109+00; обновлено: 2026-10-30 16:05:00.289387+00

### 742. M5.0 earthquake - Reykjanes Ridge
- ID: `809e1eb1-d193-49fd-8f4f-1550efb63725`; ключ: `live:usgs:earthquake:us7000ttnz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 13:15:00.943923+00; обновлено: 2026-10-30 16:05:00.289387+00

### 743. M4.6 earthquake - south of the Fiji Islands
- ID: `a00a1e32-b111-49ff-b633-ce4c0b2749b6`; ключ: `live:usgs:earthquake:us7000ttp2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 14:15:01.947773+00; обновлено: 2026-10-30 16:05:00.289387+00

### 744. M4.5 earthquake - 13 km WSW of Āwash, Ethiopia
- ID: `95f6606a-edcf-4123-b044-507438cbf68d`; ключ: `live:usgs:earthquake:us7000ttp7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 14:15:01.882125+00; обновлено: 2026-10-30 16:05:00.289387+00

### 745. M5.5 earthquake - 5 km ESE of Asahi, Japan
- ID: `90f8dfe1-2398-45cc-bcab-bdb5425b8064`; ключ: `live:usgs:earthquake:us7000ttpe`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 16:15:01.351515+00; обновлено: 2026-10-30 16:05:00.289387+00

### 746. M4.7 earthquake - 81 km ENE of Mazha, China
- ID: `d9ef257c-e316-49fc-867f-e5683f057d96`; ключ: `live:usgs:earthquake:us7000ttpk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 17:15:00.94486+00; обновлено: 2026-10-30 16:05:00.289387+00

### 747. M4.7 earthquake - 6 km N of Asahi, Japan
- ID: `3350482c-8e68-423d-9b5c-11301d5091f7`; ключ: `live:usgs:earthquake:us7000ttt2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 22:15:02.230084+00; обновлено: 2026-10-30 16:05:00.289387+00

### 748. M4.7 earthquake - Reykjanes Ridge
- ID: `e9c4766e-a06c-4478-9821-ac75fc617e1a`; ключ: `live:usgs:earthquake:us7000ttt4`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 22:15:02.189475+00; обновлено: 2026-10-30 16:05:00.289387+00

### 749. M5.2 earthquake - Reykjanes Ridge
- ID: `b430f5a9-e49d-41b1-a929-a2d9ea55f108`; ключ: `live:usgs:earthquake:us7000ttth`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 20:15:02.047748+00; обновлено: 2026-10-30 16:05:00.289387+00

### 750. M5.3 earthquake - 159 km WNW of Tobelo, Indonesia
- ID: `046b9838-9c8a-430d-be87-ba59b312dd3c`; ключ: `live:usgs:earthquake:us7000tttl`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 20:15:01.90596+00; обновлено: 2026-10-30 16:05:00.289387+00

### 751. M5.7 earthquake - 271 km WSW of Tual, Indonesia
- ID: `7acc15f3-b2bc-4443-86a1-63c2443c148a`; ключ: `live:usgs:earthquake:us7000ttua`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-28 23:15:01.235139+00; обновлено: 2026-10-30 16:05:00.289387+00

### 752. M4.6 earthquake - 80 km SE of Bole, China
- ID: `bac31c8a-262b-40db-8f0a-e065797469a5`; ключ: `live:usgs:earthquake:us7000ttuq`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 02:15:01.708213+00; обновлено: 2026-10-30 16:05:00.289387+00

### 753. M4.6 earthquake - 17 km N of Kushiro, Japan
- ID: `24cba4d8-00b2-4637-a6fd-c28846c278b9`; ключ: `live:usgs:earthquake:us7000ttv1`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 00:15:01.531588+00; обновлено: 2026-10-30 16:05:00.289387+00

### 754. M5.4 earthquake - 109 km ENE of Luganville, Vanuatu
- ID: `b84b5c90-b3e1-4cae-be02-6d50dc057f48`; ключ: `live:usgs:earthquake:us7000ttvf`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 01:15:01.596008+00; обновлено: 2026-10-30 16:05:00.289387+00

### 755. M4.9 earthquake - 117 km E of Port-Olry, Vanuatu
- ID: `e13c6b6e-720c-4dda-8edd-3bfae7401c1a`; ключ: `live:usgs:earthquake:us7000ttvn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 01:15:01.522719+00; обновлено: 2026-10-30 16:05:00.289387+00

### 756. M4.8 earthquake - western Indian-Antarctic Ridge
- ID: `955c0ca7-ab55-4b2d-acdb-87a46e6dde8d`; ключ: `live:usgs:earthquake:us7000ttvs`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 02:15:01.545539+00; обновлено: 2026-10-30 16:05:00.289387+00

### 757. M4.8 earthquake - 36 km SSW of Merizo Village, Guam
- ID: `a6a9e3ae-68e5-425c-b7aa-61cda9e1a043`; ключ: `live:usgs:earthquake:us7000ttvy`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 03:15:01.717761+00; обновлено: 2026-10-30 16:05:00.289387+00

### 758. M5.4 earthquake - 113 km ENE of Barcelona, Philippines
- ID: `99fb4e49-f0bf-466f-b29f-19c660bc32de`; ключ: `live:usgs:earthquake:us7000ttw2`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 04:15:01.751919+00; обновлено: 2026-10-30 16:05:00.289387+00

### 759. M5.8 earthquake - 110 km ENE of Barcelona, Philippines
- ID: `ac40745e-7bf6-4bc0-9f81-7035dcf0aca0`; ключ: `live:usgs:earthquake:us7000ttw3`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 04:15:01.708355+00; обновлено: 2026-10-30 16:05:00.289387+00

### 760. M5.7 earthquake - 82 km NE of Kiunga, Papua New Guinea
- ID: `94515ebd-870f-48d7-a947-6cd541f8ecd0`; ключ: `live:usgs:earthquake:us7000ttw5`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 04:15:01.638367+00; обновлено: 2026-10-30 16:05:00.289387+00

### 761. M5.4 earthquake - South Sandwich Islands region
- ID: `f333a143-114e-4902-972c-b18b6f027020`; ключ: `live:usgs:earthquake:us7000ttx0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 06:15:01.532936+00; обновлено: 2026-10-30 16:05:00.289387+00

### 762. M5.1 earthquake - Balleny Islands region
- ID: `b813f6b9-b130-4e1f-af5f-81845e0bf98e`; ключ: `live:usgs:earthquake:us7000ttx8`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 06:15:01.467106+00; обновлено: 2026-10-30 16:05:00.289387+00

### 763. M5.4 earthquake - 114 km ENE of Barcelona, Philippines
- ID: `b482f5df-3e97-4127-ba3f-fbfd7473e4ef`; ключ: `live:usgs:earthquake:us7000ttxn`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 08:15:01.687581+00; обновлено: 2026-10-30 16:05:00.289387+00

### 764. M6.4 earthquake - southeast of Easter Island
- ID: `1a5d2c3e-61b1-49c2-9318-35c972413ba8`; ключ: `live:usgs:earthquake:us7000ttxz`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 50.000; последний расчёт: 50.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 08:15:01.617504+00; обновлено: 2026-10-30 16:05:00.289387+00

### 765. M4.6 earthquake - 41 km W of Mosteiros, Portugal
- ID: `a7e21d41-3e54-4d09-9f9c-9d6577580d17`; ключ: `live:usgs:earthquake:us7000tty0`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 09:15:01.107459+00; обновлено: 2026-10-30 16:05:00.289387+00

### 766. M5.1 earthquake - 218 km NNW of Bamboo Flat, India
- ID: `47a59ffd-18ee-4c19-8533-2c0e80776a0b`; ключ: `live:usgs:earthquake:us7000tty7`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 09:15:01.029645+00; обновлено: 2026-10-30 16:05:00.289387+00

### 767. M4.9 earthquake - 111 km SW of Port-Vila, Vanuatu
- ID: `4ced1f11-3ce6-4e37-8d63-b9e281beee7b`; ключ: `live:usgs:earthquake:us7000ttyd`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 42.000; последний расчёт: 42.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 11:15:02.852317+00; обновлено: 2026-10-30 16:05:00.289387+00

### 768. M4.6 earthquake - Pulau Pulau Tanimbar, Indonesia
- ID: `a0033def-8fdf-4d9f-a348-6d4e178a1353`; ключ: `live:usgs:earthquake:us7000ttyk`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 13:15:01.358523+00; обновлено: 2026-10-30 16:05:00.289387+00

### 769. M4.7 earthquake - 6 km SE of Pitaloza Arriba, Panama
- ID: `f8ceba02-159a-4b08-88cf-06eafc311b79`; ключ: `live:usgs:earthquake:us7000ttyw`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 40.000; последний расчёт: 40.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 14:15:01.81679+00; обновлено: 2026-10-30 16:05:00.289387+00

### 770. M4.5 earthquake - 141 km E of Miyako, Japan
- ID: `b6d04f25-7fd0-4cd2-ae2e-b347787d1118`; ключ: `live:usgs:earthquake:us7000tu2j`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 19:15:01.493509+00; обновлено: 2026-10-30 16:05:00.289387+00

### 771. M5.0 earthquake - 143 km S of False Pass, Alaska
- ID: `c7eb02f7-6df5-450a-bc0b-d1adbdab4897`; ключ: `live:usgs:earthquake:us7000tu3j`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 21:15:00.884227+00; обновлено: 2026-10-30 16:05:00.289387+00

### 772. M5.0 earthquake - 131 km NNW of Tual, Indonesia
- ID: `0c4751fa-063d-4f90-9bcd-816e93d10653`; ключ: `live:usgs:earthquake:us7000tu3u`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 21:15:00.809086+00; обновлено: 2026-10-30 16:05:00.289387+00

### 773. M4.7 earthquake - 1 km SSE of Radwanice, Poland
- ID: `e12e29dc-1313-4314-90d1-b8347557b7be`; ключ: `live:usgs:earthquake:us7000tu46`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 22:15:01.557128+00; обновлено: 2026-10-30 16:05:00.289387+00

### 774. M4.6 earthquake - 121 km ENE of Shikotan, Russia
- ID: `2420884b-400c-4a71-b562-5e42892aed08`; ключ: `live:usgs:earthquake:us7000tu4a`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 23:15:01.265394+00; обновлено: 2026-10-30 17:15:01.654984+00

### 775. M6.2 earthquake - 43 km ESE of Port-Olry, Vanuatu
- ID: `41a3d4df-8e3c-4c78-8890-22c4957d483b`; ключ: `live:usgs:earthquake:us7000tu4f`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 52.000; последний расчёт: 52.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-29 22:15:01.49246+00; обновлено: 2026-10-30 17:15:01.62302+00

### 776. M4.6 earthquake - 59 km SW of Port-Vila, Vanuatu
- ID: `e1819cdf-5004-47af-8d6c-612388ded58c`; ключ: `live:usgs:earthquake:us7000tu4z`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-30 00:15:01.339446+00; обновлено: 2026-10-30 17:15:01.595894+00

### 777. M5.1 earthquake - 97 km NNE of Finschhafen, Papua New Guinea
- ID: `ea948951-0f1c-464f-b151-fab42f028e2c`; ключ: `live:usgs:earthquake:us7000tu5q`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 48.000; последний расчёт: 48.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-30 04:15:01.744874+00; обновлено: 2026-10-30 17:15:01.571636+00

### 778. M4.6 earthquake - 51 km ENE of Noda, Japan
- ID: `3cd34346-f8de-41f3-8de4-09d5542dc3c7`; ключ: `live:usgs:earthquake:us7000tu6f`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-30 06:15:01.251149+00; обновлено: 2026-10-30 17:15:01.544767+00

### 779. M4.8 earthquake - Fiji region
- ID: `b5363acb-ceef-4ea7-b51d-54b8a1ec27a2`; ключ: `live:usgs:earthquake:us7000tu6i`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 46.000; последний расчёт: 46.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-30 06:15:01.18109+00; обновлено: 2026-10-30 17:15:01.509442+00

### 780. M4.6 earthquake - 64 km SSW of Shikotan, Russia
- ID: `34bb6bf2-c8e0-4385-9add-bb56b176edf4`; ключ: `live:usgs:earthquake:us7000tu7b`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 44.000; последний расчёт: 44.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-30 09:15:01.128759+00; обновлено: 2026-10-30 17:15:01.486328+00

### 781. M5.1 earthquake - Balleny Islands region
- ID: `9d84feaa-2464-4979-a633-c9deef172d79`; ключ: `live:usgs:earthquake:us7000tu7j`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 51.000; последний расчёт: 51.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-30 11:15:02.337081+00; обновлено: 2026-10-30 17:15:01.440274+00

### 782. M4.5 earthquake - 104 km ENE of Barcelona, Philippines
- ID: `7946b23b-e3de-4780-8743-05752f479a45`; ключ: `live:usgs:earthquake:us7000tu7k`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 47.000; последний расчёт: 47.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-30 11:15:02.262023+00; обновлено: 2026-10-30 17:15:01.410067+00

### 783. M4.7 earthquake - 42 km SE of Sykiá, Greece
- ID: `ee04e37b-ff2a-4c5b-b5d8-0131044c21e1`; ключ: `live:usgs:earthquake:us7000tu7m`
- Сохранённое состояние: `ready_for_research`; сохранённая оценка: 47.000; последний расчёт: 47.00 / hazard_waiting
- Тезис: USGS earthquake event selected for freshness-controlled verification. Treat magnitude, status, alert and tsunami fields as revisable; do not infer impact or safety guidance.
- Коды причин: [
  "live_source",
  "official_api",
  "usgs_earthquake",
  "rapidly_changing_hazard",
  "needs_freshness_recheck"
]
- Создано: 2026-10-30 12:15:01.725181+00; обновлено: 2026-10-30 17:15:01.357218+00

## Все 24 сохранённых редакционных артефакта

### vertical_short_script / 7234047b-b806-4fde-ae23-098aff0454ff
Кандидат `e3dc883f-3c0e-4c3d-9c0b-b79ed90128f2`; режим `seed_import`; сохранённое состояние `validated`; версия 1
```json
{
  "hook": "The camera sensor story starts with a spacecraft power problem, not a phone.",
  "title": "A low-power image sensor developed at JPL for spacecraft became a commercial technology through a JPL-founded spinout, Photobit.",
  "script": "The defensible story is not “NASA invented the phone camera.” It is narrower and better: JPL work produced a specific CMOS active-pixel architecture, and the inventors built a company to move that architecture into commercial markets."
}
```

### vertical_short_script / 02bb6733-a757-4763-a05d-21b19dc61792
Кандидат `f504c2ab-bb94-470f-ae26-b789b0102575`; режим `seed_import`; сохранённое состояние `validated`; версия 1
```json
{
  "hook": "NASA did not invent aerogel. The more interesting story is what it helped make practical.",
  "title": "NASA SBIR work helped Aspen Systems turn fragile aerogel into practical flexible insulation and spin out Aspen Aerogels to commercialize it.",
  "script": "The key correction is the hook itself: aerogel predates NASA. What NASA-backed work changed was the ability to package the material into durable flexible insulation that a company could actually manufacture and sell."
}
```

### vertical_short_script / afb0d28c-4308-4063-b56a-901a88ad47f8
Кандидат `2cd09330-7613-4800-b9a3-d89dc28c8a11`; режим `seed_import`; сохранённое состояние `validated`; версия 1
```json
{
  "hook": "A piece of the Chevy Volt battery started as DOE lab research.",
  "title": "DOE-funded Argonne cathode research became licensed battery technology used by LG Chem in cells supplied for the Chevrolet Volt.",
  "script": "The story is not that Argonne built the Volt battery. The traceable bridge is narrower: Argonne developed patented cathode material technology, LG Chem licensed it, and Argonne records that the licensed material was used in the battery supplied for the Volt."
}
```

### vertical_short_script / ad052a5c-ec8c-4ce8-98b2-829db73db691
Кандидат `26e127de-cdd8-4b3b-b48c-0c608163aa5b`; режим `seed_import`; сохранённое состояние `validated`; версия 1
```json
{
  "hook": "A cancer therapy can take decades to travel from a government lab to a commercial product. Here is the bridge.",
  "title": "Decades of NCI tumor-infiltrating lymphocyte research moved through a CRADA and NIH patent licenses into Iovance development and the 2024 FDA approval of Amtagvi.",
  "script": "This is a commercialization story, not medical advice. The verifiable bridge runs through NCI research, a 2011 cooperative R&D agreement, NIH licensing, and Iovance development before FDA approval in 2024."
}
```

### vertical_short_script / 533b232e-5731-4025-adb4-8db009ee65a4
Кандидат `e129a4fd-0d37-466e-8b86-89d9a4858d8f`; режим `seed_import`; сохранённое состояние `validated`; версия 1
```json
{
  "hook": "What can a laboratory license be worth once it becomes a product platform?",
  "title": "ORNL microfluidic Lab-on-a-chip technology was licensed by Caliper Life Sciences, became part of its commercial platform, and ORNL links that success to PerkinElmer’s 2011 acquisition of Caliper.",
  "script": "The strongest version avoids a tempting exaggeration. The ORNL license was not “worth $600 million” by itself. ORNL says the technology’s success contributed to PerkinElmer’s decision; the SEC separately verifies the acquisition and its roughly $600 million net price."
}
```

### vertical_short_script / 4e633817-6b2b-4618-a0d8-6d31cc128763
Кандидат `44debf27-f78e-4640-a0e2-916172cb039d`; режим `seed_import`; сохранённое состояние `validated`; версия 1
```json
{
  "hook": "Why can a box on a utility pole become a national supply-chain problem? Start with 80,000 varieties.",
  "title": "Distribution transformers are a grid bottleneck because limited domestic capacity, long procurement timelines, foreign dependence and extreme specification fragmentation make rapid substitution/expansion difficult.",
  "script": "The bottleneck is partly physical and partly organizational. DOE points to limited capacity and long procurement timelines, but it also identifies tens of thousands of transformer varieties—meaning factories are not simply making one interchangeable product at scale."
}
```

### vertical_short_script / 07d826f7-15ef-489e-aa6c-783deda03f07
Кандидат `f509144b-c01d-464b-9300-0714226bbb9a`; режим `seed_import`; сохранённое состояние `validated`; версия 1
```json
{
  "hook": "The nuclear-fuel bottleneck is not where uranium comes out of the ground. It is what happens next.",
  "title": "The chokepoint in U.S. nuclear fuel is not simply uranium ore: enrichment services remain heavily foreign-sourced while policy is trying to rebuild domestic capacity.",
  "script": "Ore supply and enrichment are different markets. The current U.S. vulnerability appears downstream: EIA’s latest annual data show most enrichment services bought for civilian reactors in 2025 came from foreign sources."
}
```

### vertical_short_script / add90c14-56b4-416c-a8ae-9fb6c8b34cbc
Кандидат `d6943861-0e23-4a92-b2a4-10af15f5fa02`; режим `seed_import`; сохранённое состояние `validated`; версия 1
```json
{
  "hook": "When a medicine shortage gets bad enough, the supply-chain workaround can cross a border.",
  "title": "A 2026 U.S. cefotaxime shortage became severe enough that FDA coordinated temporary importation of a Canadian-market product, illustrating how limited approved supply can turn an injectable medicine into a supply-chain chokepoint.",
  "script": "The safe story stops where the evidence stops. FDA’s hosted notice establishes a critical shortage and a temporary import response. It does not establish that a particular factory failure, ingredient shortage or quality event caused the shortage."
}
```

### vertical_short_script / 23802ebc-fd97-4635-a83f-c9500cf0ace2
Кандидат `5ec9cea0-3902-4f8a-91fd-4371a907de3e`; режим `seed_import`; сохранённое состояние `validated`; версия 1
```json
{
  "hook": "Mining rare earths is not the same as making the magnet inside a high-performance motor.",
  "title": "Rare-earth permanent magnets are a downstream manufacturing chokepoint: U.S. industry has domestic mineral resources but still depends heavily on foreign processing/material and magnet supply chains.",
  "script": "The useful distinction is between resources and industrial capability. A mine does not automatically provide separated oxides, refined metals, alloy powder and finished high-performance magnets. The bottleneck can migrate downstream as each stage is added."
}
```

### vertical_short_script / 2f0a1d02-1a29-4609-af75-9f247349bc66
Кандидат `0109348d-8097-458b-b89e-c2affaec2a8b`; режим `seed_import`; сохранённое состояние `validated`; версия 1
```json
{
  "hook": "A semiconductor supply chain can depend on a metal the U.S. does not produce in primary form.",
  "title": "Gallium is a semiconductor-material chokepoint because the United States does not produce low-purity primary gallium domestically while global primary production is overwhelmingly concentrated in China.",
  "script": "The cleanest warning is methodological. A customs table can say a shipment came from Canada, Germany or Japan while the underlying material chain began elsewhere. USGS now explicitly models indirect provenance because supplier country and producer country are not always the same thing."
}
```

### social_post / 56051bc1-c993-4dae-ab0a-25bbfc359710
Кандидат `e3dc883f-3c0e-4c3d-9c0b-b79ed90128f2`; режим `medeng_seed_studio_acceptance`; сохранённое состояние `validated`; версия 1
```json
{
  "body": "The defensible story is not “NASA invented the phone camera.” It is narrower and better: JPL work produced a specific CMOS active-pixel architecture, and the inventors built a company to move that architecture into commercial markets.",
  "hook": "The camera sensor story starts with a spacecraft power problem, not a phone.",
  "headline": "A low-power image sensor developed at JPL for spacecraft became a commercial technology through a JPL-founded spinout, Photobit."
}
```

### long_video_script / fb26cc08-5eab-44f1-a737-8a3d273066c7
Кандидат `e3dc883f-3c0e-4c3d-9c0b-b79ed90128f2`; режим `medeng_seed_studio_acceptance`; сохранённое состояние `validated`; версия 1
```json
{
  "closing": "No additional factual assertions beyond the bound factual core.",
  "opening": "The camera sensor story starts with a spacecraft power problem, not a phone.",
  "sections": [
    {
      "kind": "factual_core_summary",
      "text": "The defensible story is not “NASA invented the phone camera.” It is narrower and better: JPL work produced a specific CMOS active-pixel architecture, and the inventors built a company to move that architecture into commercial markets."
    }
  ]
}
```

### narration / d93060d6-1bde-44c8-8616-6ad655b08a3f
Кандидат `e3dc883f-3c0e-4c3d-9c0b-b79ed90128f2`; режим `medeng_seed_studio_acceptance`; сохранённое состояние `validated`; версия 1
```json
{
  "text": "The defensible story is not “NASA invented the phone camera.” It is narrower and better: JPL work produced a specific CMOS active-pixel architecture, and the inventors built a company to move that architecture into commercial markets.",
  "pronunciation_notes": []
}
```

### visual_plan / a8104e0b-e7de-4dc1-98c4-0dcd464cc1c9
Кандидат `e3dc883f-3c0e-4c3d-9c0b-b79ed90128f2`; режим `medeng_seed_studio_acceptance`; сохранённое состояние `validated`; версия 1
```json
{
  "shots": [
    {
      "kind": "title_card",
      "text": "A low-power image sensor developed at JPL for spacecraft became a commercial technology through a JPL-founded spinout, Photobit."
    },
    {
      "kind": "rights_safe_supporting_visuals",
      "instruction": "Use only generated, owned, public-domain, or explicitly rights-cleared visuals."
    },
    {
      "kind": "source_card",
      "instruction": "Preserve research provenance; do not add new factual claims in visuals."
    }
  ]
}
```

### social_post / e9e1e442-5c21-4f2b-a7a2-374de6ff2c0d
Кандидат `74f95f01-33f9-4a92-a6b0-27aed5071f95`; режим `live_verified_editorial_v1`; сохранённое состояние `validated`; версия 1
```json
{
  "body": "NASA Spinoff 2004 reports that Marshall Space Flight Center used smart-camera technology in the DART Advanced Video Guidance Sensor. Southern Vision Systems then developed the commercial SpecterView sensor based on work done in support of that mission, with prototype development beginning in April 2003 and volume manufacturing by April 2004. This is a historical NASA-documented commercialization story; it does not imply that SpecterView is still sold today.",
  "hook": "A camera technology built for autonomous spacecraft docking found a commercial path on Earth.",
  "headline": "From spacecraft docking work to a commercial smart camera",
  "source_note": "Historical facts attributed to NASA Spinoff 2004 and archived in NASA NTRS document 20050031179."
}
```

### social_post / 6b6d4307-4267-4b3f-9520-a854fda1d314
Кандидат `90fc5ca2-d714-4cff-ace6-0a3e6699cbb2`; режим `deterministic_factual_core_v1`; сохранённое состояние `validated`; версия 1
```json
{
  "body": "NASA Spinoff reports Nikon specially modified F3 35mm cameras for Space Shuttle astronauts. NASA Spinoff reports nonmigratory lubricants developed for the space-camera modification were used in commercial F3 variants. NASA Spinoff identifies a coreless motor as another F3 spinoff and reports it allowed 140 rolls of film on one set of batteries.",
  "hook": "A historical technology story documented in NASA Spinoff records.",
  "headline": "Historical NASA Spinoff record: Space Camera",
  "source_note": "Frozen factual-core sources: https://spinoff.nasa.gov/node/9384 | https://ntrs.nasa.gov/citations/20030001791"
}
```

### social_post / e6437342-41e5-4241-afa8-6d5ebf5179f7
Кандидат `8b0e7955-e934-4c11-adc4-ad9553b423a0`; режим `deterministic_factual_core_v1`; сохранённое состояние `validated`; версия 1
```json
{
  "body": "NASA Spinoff reports Nikon cameras were designed for easy, accurate operation by Skylab astronauts in weightlessness. NASA Spinoff reports Nikon later incorporated the plastic-cushioned advance-lever simplification into the commercial Nikon FM compact.",
  "hook": "A historical technology story documented in NASA Spinoff records.",
  "headline": "Historical NASA Spinoff record: Nikon Camera",
  "source_note": "Frozen factual-core sources: https://spinoff.nasa.gov/node/9388 | https://ntrs.nasa.gov/citations/20030004814"
}
```

### social_post / 29b1eb01-eed1-4a5d-bf21-719c03e6774d
Кандидат `3b775603-199b-4fe2-ab04-b73a25248a70`; режим `deterministic_factual_core_v1`; сохранённое состояние `validated`; версия 1
```json
{
  "body": "NASA Spinoff reports JPL and Amber/Raytheon developed QWIP infrared detector technology together. NASA Spinoff reports a QWIP camera identified hot spots during the October 1996 Malibu fires.",
  "hook": "A historical technology story documented in NASA Spinoff records.",
  "headline": "Historical NASA Spinoff record: Infrared Camera",
  "source_note": "Frozen factual-core sources: https://spinoff.nasa.gov/spinoff1997/ps2.html | https://ntrs.nasa.gov/citations/20020076146"
}
```

### social_post / f9674f8d-2140-422b-88b6-d0858fbe6414
Кандидат `e6deba25-ccc8-4250-a16a-7fda70873cc7`; режим `deterministic_factual_core_v1`; сохранённое состояние `validated`; версия 1
```json
{
  "body": "NASA Spinoff reports that Omniview was developed for NASA as a viewing/receiving device for guiding space robots. NASA Spinoff reports that TeleRobotics International developed Omniview under a NASA Small Business Innovation Research contract/grant. NASA Spinoff 1994 reports that Omniview was introduced to the commercial market in 1993.",
  "hook": "A historical technology story documented in NASA Spinoff records.",
  "headline": "Historical NASA Spinoff record: A Motionless Camera",
  "source_note": "Frozen factual-core sources: https://spinoff.nasa.gov/node/9755 | https://ntrs.nasa.gov/citations/20020080109"
}
```

### social_post / 420cbc39-ce48-4fff-8f78-4fb5e00929eb
Кандидат `bd426f29-a549-4e72-a05f-36bb0f26005b`; режим `deterministic_factual_core_v1`; сохранённое состояние `validated`; версия 1
```json
{
  "body": "NASA Spinoff describes PixelVision’s NV652 as a commercial back-illuminated low-light CCD camera. NASA Spinoff identifies former JPL engineer James R. Janesick’s prior CCD expertise as the NASA technology input to the development.",
  "hook": "A historical technology story documented in NASA Spinoff records.",
  "headline": "Historical NASA Spinoff record: Night Vision Camera",
  "source_note": "Frozen factual-core sources: https://spinoff.nasa.gov/spinoff1996/35.html | https://ntrs.nasa.gov/citations/20020079084"
}
```

### social_post / 17c83ada-846b-4dcd-aa04-4af8f6c02ada
Кандидат `549ac962-6c18-4aaa-9641-dedcf9e89bd2`; режим `deterministic_factual_core_v1`; сохранённое состояние `validated`; версия 1
```json
{
  "body": "NASA Spinoff reports SciMeasure developed Little Joe with JPL under NASA SBIR. NASA Spinoff reports the work led to a commercial modular CCD camera sold by SciMeasure. NASA Spinoff reports Phase II was 95 percent smaller, 92 percent lighter, and used 92.5 percent less power than Phase I.",
  "hook": "A historical technology story documented in NASA Spinoff records.",
  "headline": "Historical NASA Spinoff record: New Modular Camera No Ordinary Joe",
  "source_note": "Frozen factual-core sources: https://spinoff.nasa.gov/node/10328 | https://ntrs.nasa.gov/citations/20030099649"
}
```

### social_post / ca9d7467-70ec-4b2e-a5d5-059d4c84e8c3
Кандидат `527fdab2-8418-4aac-b700-895ef63f2aaf`; режим `deterministic_factual_core_v2`; сохранённое состояние `validated`; версия 1
```json
{
  "body": null,
  "hook": "A historical technology story documented in NASA Spinoff records.",
  "headline": "Historical NASA Spinoff record: NIH, CDC and FDA Small Business Innovation Research Grant (Parent SBIR [R43/R44] Clinical Trial Optional)",
  "source_note": "Sources are frozen in the factual core."
}
```

### social_post / 8ffbc89b-0286-41dd-9092-591c471a8021
Кандидат `d13f499f-4caa-4b05-8b3b-ba2fc10e99bd`; режим `deterministic_factual_core_v2`; сохранённое состояние `validated`; версия 1
```json
{
  "body": null,
  "hook": "A historical technology story documented in NASA Spinoff records.",
  "headline": "Historical NASA Spinoff record: Region 4 Small Business Transportation Technical Assistance Center (SBTTAC)",
  "source_note": "Sources are frozen in the factual core."
}
```

### social_post / 09948dcb-83f5-448f-ba4a-4e0c623caa71
Кандидат `deadac24-a079-4f81-bc52-9a2d63c7d63d`; режим `deterministic_factual_core_v2`; сохранённое состояние `validated`; версия 1
```json
{
  "body": null,
  "hook": "A historical technology story documented in NASA Spinoff records.",
  "headline": "Historical NASA Spinoff record: Small Business Innovation Research and Small Business Technology Transfer Programs Phase II",
  "source_note": "Sources are frozen in the factual core."
}
```

## Происхождение и ограничения

- `provenance.json` содержит запросы SQL, время чтения и точные количества. Выбраны только проектные таблицы; данные авторизации, секреты и частные операционные журналы не экспортировались.
- Идентификаторы и контрольные суммы сохранены для сопоставления записей. Имена проверяющих и владельцев, частные примечания и переопределения рабочей области, конфигурация источников не включены.
- Фактическое состояние текущей версии на ПК этим экспортом не проверялось. Публикации, модели, очереди и состояния базы не изменялись.
- Из `source_events.json` удалены 6 вхождений публичных контактных адресов электронной почты.

## Проверка связности и готовности

Связи контента с кандидатом и фактической основой, а также кандидата с событием источника разрешаются внутри пакета; отсутствующих ссылок в этих проверках 0. Пустых полей `thesis`, `summary`, `facts` и объектов контента в сохранённых таблицах 0. Это проверка наличия, не смыслового качества. Все 40 утверждений имеют сохранённый статус `supported`. Среди 89 решений проверки: 73 `invalidated`, 15 `pending`, 1 `approved`. Единственное одобрение относится к конкретной исторической записи, не к текущему продукту. Поэтому 24 материала со статусом `validated` не равны 24 разрешениям публикации. Последние состояния порогов: 727 `hazard_waiting`, 17 `open`, 16 `medical_waiting`, 10 `researched`, 3 `terminal`.
